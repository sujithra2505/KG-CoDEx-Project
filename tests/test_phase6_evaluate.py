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

import phase6_evaluate as p6  # noqa: E402
import phase5_ui_build as ui  # noqa: E402
from phase4_fixtures import record_opened_files  # noqa: E402
from test_prediction_ui import make_phase5_project  # noqa: E402

# With cap 3, the fixture keeps spouse predictions Q201->Q200, Q203->Q202, Q205->Q204
# and language predictions Q320->Q500, Q321->Q501, Q322->Q502.
SPLITS = {
    "test.txt": [("Q201", "P26", "Q200"), ("Q203", "P26", "Q202"), ("Q320", "P1412", "Q500"), ("Q900", "P26", "Q901")],
    "test_negatives.txt": [("Q205", "P26", "Q204"), ("Q902", "P26", "Q903")],
    "valid.txt": [("Q321", "P1412", "Q501")],
    "valid_negatives.txt": [("Q904", "P26", "Q905")],
}


class GateTests(unittest.TestCase):
    def test_cli_without_approval_reads_nothing_and_exits_2(self) -> None:
        with record_opened_files() as opened, redirect_stdout(io.StringIO()) as out:
            code = p6.main([])
        self.assertEqual(code, 2)
        self.assertEqual(opened, [])
        self.assertIn("Not run", out.getvalue())

    def test_run_requires_approval(self) -> None:
        with record_opened_files() as opened:
            with self.assertRaises(PermissionError):
                p6.run(ROOT, approved=False)
        self.assertEqual(opened, [])


class EvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.train = make_phase5_project(self, SPLITS)
        self.out = self.root / "outputs" / "phase6" / "evaluation_test"

    def results(self):
        p6.run(self.root, self.out, approved=True)
        return json.loads((self.out / "evaluation_results.json").read_text())

    def test_labels_and_metrics(self) -> None:
        res = self.results()
        for v in ("v1", "v2"):
            o = res["versions"][v]["overall"]
            self.assertEqual((o["tp_matched_positives"], o["fp_matched_supplied_negatives"]), (3, 1))
            self.assertEqual((o["test_positives"], o["test_negatives"]), (4, 2))
            self.assertEqual(o["unlabelled_predictions"], o["predictions"] - 4)
            self.assertEqual((o["precision"], o["recall"], o["specificity"]), (0.75, 0.75, 0.5))
            self.assertEqual(o["f1"], 0.75)
            self.assertAlmostEqual(o["labelled_coverage"], 4 / o["predictions"], places=6)
            self.assertAlmostEqual(o["positive_hit_rate"], 3 / o["predictions"], places=6)
            self.assertEqual(o["unlabelled_annotations"]["in_valid_positives"], 1)
            labels = {pid: (l, n) for pid, l, n in res["versions"][v]["labels"]}
            self.assertEqual(sorted(l for l, _ in labels.values()).count("test_positive"), 3)
            p26 = res["versions"][v]["per_relation"]["P26"]
            self.assertEqual((p26["tp_matched_positives"], p26["fp_matched_supplied_negatives"], p26["test_positives"]), (2, 1, 3))

    def test_outputs_manifest_and_no_overwrite(self) -> None:
        import hashlib
        before = ui.protected_state(self.root)
        self.results()
        self.assertEqual(ui.protected_state(self.root), before)
        manifest = json.loads((self.out / "evaluation_manifest.json").read_text())
        for name, digest in manifest["outputs"].items():
            self.assertEqual(hashlib.sha256((self.out / name).read_bytes()).hexdigest(), digest)
        self.assertFalse(manifest["predictions_changed"])
        js = (self.out / "evaluation_results.js").read_text()
        self.assertTrue(js.startswith("window.PHASE6_RESULTS = "))
        with self.assertRaises(FileExistsError):
            p6.run(self.root, self.out, approved=True)

    def test_modified_split_file_is_refused(self) -> None:
        path = self.root / "data" / "test_negatives.txt"
        path.write_text(path.read_text() + "Q906\tP26\tQ907\n")
        with self.assertRaises(p6.Phase6Error):
            p6.run(self.root, self.out, approved=True)

    def test_metrics_function_denominators(self) -> None:
        pred = {("a", "P1", "b"), ("c", "P1", "d"), ("e", "P1", "f")}
        mt = p6.metrics(pred, {("a", "P1", "b"), ("x", "P1", "y")}, {("c", "P1", "d")})
        self.assertEqual((mt["tp_matched_positives"], mt["fp_matched_supplied_negatives"], mt["unlabelled_predictions"]), (1, 1, 1))
        self.assertEqual((mt["precision"], mt["recall"]), (0.5, 0.5))
        self.assertEqual(p6.metrics(set(), {("a", "P1", "b")}, set())["precision"], None)

    def test_f1_is_zero_not_none_when_no_true_positives(self) -> None:
        mt = p6.metrics({("c", "P1", "d")}, {("a", "P1", "b")}, {("c", "P1", "d")})
        self.assertEqual((mt["precision"], mt["recall"], mt["f1"]), (0.0, 0.0, 0.0))
        self.assertIsNone(p6.metrics({("e", "P1", "f")}, {("a", "P1", "b")}, set())["f1"])

    def test_recall_denominator_counts_relations_without_predictions(self) -> None:
        records = [{"prediction_id": "p1", "triple": {"subject": "a", "relation": "P1", "object": "b"}}]
        splits = {"test_positive": {("a", "P1", "b"), ("x", "P2", "y"), ("u", "P2", "v")},
                  "test_negative": {("m", "P3", "n")}, "valid_positive": set(), "valid_negative": set()}
        res = p6.evaluate_version(records, splits)
        self.assertEqual(res["overall"]["recall"], round(1 / 3, 6))
        self.assertEqual(res["per_relation"]["P2"]["predictions"], 0)
        self.assertEqual((res["per_relation"]["P2"]["recall"], res["per_relation"]["P2"]["fn_unpredicted_positives"]), (0.0, 2))
        self.assertIn("P3", res["per_relation"])
        self.assertEqual(res["overall"]["recall_ceiling_under_cap"], round(1 / 3, 6))


if __name__ == "__main__":
    unittest.main()
