from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(Path(__file__).resolve().parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

import cap_experiment as ce  # noqa: E402
import phase5_ui_build as ui  # noqa: E402
from phase4_fixtures import record_opened_files  # noqa: E402
from test_phase6_evaluate import SPLITS  # noqa: E402
from test_prediction_ui import make_phase5_project  # noqa: E402

FIXTURE_CAPS = (3, 4, 6)  # the fixture baseline was built with cap 3


class CapExperimentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, _ = make_phase5_project(self, SPLITS)
        self.out = ce.exp_dir(self.root)

    def test_caps_above_1000_or_unsorted_are_refused(self) -> None:
        for caps in ((100, 250, 500, 1000, 2000), (100, 500, 250), (100, 100)):
            with self.assertRaises(ce.CapExperimentError):
                ce.check_caps(caps)
        ce.check_caps(ce.CAPS)
        self.assertEqual(ce.CAPS, (100, 250, 500, 1000))

    def test_validate_requires_frozen_rule_and_rule_cannot_be_frozen_after(self) -> None:
        ce.generate(self.root, FIXTURE_CAPS)
        with self.assertRaises(ce.CapExperimentError):
            ce.validate(self.root, FIXTURE_CAPS)
        ce.freeze_rule(self.root)
        ce.validate(self.root, FIXTURE_CAPS)
        with self.assertRaises(ce.CapExperimentError):
            ce.freeze_rule(self.root)

    def test_full_pipeline_keeps_baseline_and_never_opens_test_files(self) -> None:
        before = ui.protected_state(self.root)
        ce.freeze_rule(self.root)
        written = ce.generate(self.root, FIXTURE_CAPS)
        self.assertEqual(set(written), {"cap4_v1", "cap4_v2", "cap6_v1", "cap6_v2"})
        self.assertEqual(ui.protected_state(self.root), before)  # all phase 1-5 files incl. cap-3 baseline
        for key, d in written.items():
            doc, manifest = ui.load_version(d)
            self.assertEqual(manifest["settings"]["cap_per_relation"], int(key[3]))
            per_rel = {}
            for r in doc["predictions"]:
                per_rel[r["triple"]["relation"]] = per_rel.get(r["triple"]["relation"], 0) + 1
            self.assertTrue(all(n <= int(key[3]) for n in per_rel.values()))
        v2_manifest = json.loads((written["cap4_v2"] / "phase5_manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(v2_manifest["inputs"]["v1_manifest"]["path"].endswith("cap_4/v1/phase5_manifest.json"))
        with self.assertRaises(FileExistsError):
            ce.generate(self.root, FIXTURE_CAPS)

        with record_opened_files() as opened:
            ce.validate(self.root, FIXTURE_CAPS)
        names = [Path(p).name for p in opened]
        self.assertIn("valid.txt", names)
        self.assertFalse([n for n in names if n.startswith("test")])
        res = json.loads((self.out / "validation" / "validation_results.json").read_text(encoding="utf-8"))
        self.assertEqual(len(res["configs"]), 6)
        for c in res["configs"].values():
            o = c["overall"]
            self.assertEqual(o["predictions"], o["tp_matched_positives"] + o["fp_matched_supplied_negatives"] + o["unlabelled_predictions"])
            self.assertEqual(o["split_positives"], len(SPLITS["valid.txt"]))
        sel = json.loads((self.out / ce.SELECTION_FILE).read_text(encoding="utf-8"))
        self.assertEqual(sel["selected"], ce.apply_rule({k: c["overall"] for k, c in res["configs"].items()}, FIXTURE_CAPS)["selected"])
        self.assertEqual(ui.protected_state(self.root), before)
        with self.assertRaises(FileExistsError):
            ce.validate(self.root, FIXTURE_CAPS)

    def test_test_step_is_gated(self) -> None:
        with record_opened_files() as opened:
            with self.assertRaises(PermissionError):
                ce.test_evaluation(self.root, approved=False)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(ce.main(["test"]), 2)
        self.assertEqual(opened, [])

    def test_test_step_on_fixture_after_selection(self) -> None:
        ce.freeze_rule(self.root)
        ce.generate(self.root, FIXTURE_CAPS)
        ce.validate(self.root, FIXTURE_CAPS)
        ce.test_evaluation(self.root, approved=True)
        res = json.loads((self.out / "test_final" / "test_results.json").read_text(encoding="utf-8"))
        self.assertEqual(res["split"], "test")
        self.assertEqual(res["overall"]["test_positives"], len(SPLITS["test.txt"]))
        with self.assertRaises(FileExistsError):
            ce.test_evaluation(self.root, approved=True)

    def test_dashboard_reads_numbers_from_output_files(self) -> None:
        import cap_dashboard_build as db
        import phase6_evaluate as p6
        p6.run(self.root, approved=True)  # fixture-only baseline test evaluation
        ce.freeze_rule(self.root)
        ce.generate(self.root, FIXTURE_CAPS)
        ce.validate(self.root, FIXTURE_CAPS)
        out = self.root / "outputs" / "cap_comparison_dashboard"
        db.build(self.root, out)
        text = (out / "data" / "cap_results.js").read_text(encoding="utf-8")
        data = json.loads(text[text.index("=") + 1: text.rindex(";")])
        val = json.loads((self.out / "validation" / "validation_results.json").read_text(encoding="utf-8"))
        for k, c in val["configs"].items():
            self.assertEqual(data["validation"][k]["overall"]["tp_matched_positives"], c["overall"]["tp_matched_positives"])
            self.assertEqual(data["validation"][k]["overall"]["precision"], c["overall"]["precision"])
        self.assertIsNone(data["test"]["selected"])
        for name in db.PAGE_FILES:  # page files are copied unchanged from the source folder
            self.assertEqual((out / name).read_text(encoding="utf-8"), (db.SRC_DIR / name).read_text(encoding="utf-8"))
        with self.assertRaises(FileExistsError):
            db.build(self.root, out)
        db.build(self.root, out, replace=True)

    def test_blocked_guard_refuses_test_files(self) -> None:
        with ce.test_files_blocked(self.root):
            with self.assertRaises(ce.CapExperimentError):
                (self.root / "data" / "test.txt").read_text(encoding="utf-8")


class SelectionRuleTests(unittest.TestCase):
    @staticmethod
    def ov(tp, fp):
        return {"tp_matched_positives": tp, "fp_matched_supplied_negatives": fp}

    def test_max_tp_within_precision_floor_with_tie_breaks(self) -> None:
        caps = (100, 250, 500, 1000)
        overall = {
            "cap100_v1": self.ov(250, 13), "cap100_v2": self.ov(270, 13),
            "cap250_v1": self.ov(500, 40), "cap250_v2": self.ov(520, 40),
            "cap500_v1": self.ov(800, 300), "cap500_v2": self.ov(520, 40),   # cap500_v1 fails precision floor
            "cap1000_v1": self.ov(900, 900), "cap1000_v2": self.ov(0, 0),    # fails / undefined
        }
        sel = ce.apply_rule(overall, caps)
        self.assertEqual(sel["selected"], "cap250_v2")  # ties with cap500_v2 on TP -> smaller cap
        self.assertFalse(sel["table"]["cap500_v1"]["eligible"])
        self.assertFalse(sel["table"]["cap1000_v2"]["eligible"])
        self.assertTrue(sel["table"]["cap100_v1"]["eligible"])

    def test_version_tie_prefers_v2(self) -> None:
        caps = (100, 250)
        overall = {"cap100_v1": self.ov(10, 0), "cap100_v2": self.ov(10, 0), "cap250_v1": self.ov(5, 0), "cap250_v2": self.ov(5, 0)}
        self.assertEqual(ce.apply_rule(overall, caps)["selected"], "cap100_v2")

    def test_wilson_lower(self) -> None:
        self.assertIsNone(ce.wilson_lower(0, 0))
        self.assertAlmostEqual(ce.wilson_lower(257, 270), 0.9194, places=4)


if __name__ == "__main__":
    unittest.main()
