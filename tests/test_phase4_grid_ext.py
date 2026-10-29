from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(Path(__file__).resolve().parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

import phase4_compare_runs as cmp  # noqa: E402
import phase4_rule_evaluation as ev  # noqa: E402
import phase4_rule_mining as m  # noqa: E402
from phase4_fixtures import make_project, mining_kwargs, record_opened_files, symmetric_fixture  # noqa: E402

GRID_PCA = (0.05, 0.075, 0.10, 0.20, 0.30, 0.50)
GRID_SUPPORT = (5, 10, 20, 50)


def g(min_pca, min_support, f1, precision, rules=1):
    return {"min_pca": min_pca, "min_support": min_support, "f1": f1, "precision": precision, "rules": rules}


class AdoptionRuleTests(unittest.TestCase):
    def test_adopts_only_when_both_criteria_hold(self) -> None:
        grid = [g(0.10, 10, 0.37, 0.80), g(0.05, 5, 0.381, 0.76)]
        decision = cmp.decide_adoption(grid, 0.37, (0.10, 10), 0.01, 0.75)
        self.assertTrue(decision["adopt"])
        self.assertEqual(decision["best_looser_point"]["min_pca"], 0.05)

    def test_rejects_small_gain(self) -> None:
        decision = cmp.decide_adoption([g(0.10, 10, 0.37, 0.8), g(0.05, 10, 0.379, 0.8)], 0.37, (0.10, 10), 0.01, 0.75)
        self.assertFalse(decision["adopt"])
        self.assertIn("F1 gain", decision["reason"])

    def test_rejects_low_precision(self) -> None:
        decision = cmp.decide_adoption([g(0.10, 10, 0.37, 0.8), g(0.05, 5, 0.40, 0.74)], 0.37, (0.10, 10), 0.01, 0.75)
        self.assertFalse(decision["adopt"])
        self.assertIn("precision", decision["reason"])

    def test_only_looser_points_are_considered_and_ties_go_stricter(self) -> None:
        grid = [g(0.20, 10, 0.50, 0.9), g(0.05, 10, 0.40, 0.8), g(0.075, 10, 0.40, 0.8)]
        decision = cmp.decide_adoption(grid, 0.37, (0.10, 10), 0.01, 0.75)
        self.assertEqual(decision["best_looser_point"]["min_pca"], 0.075)


class GridAndExclusionTests(unittest.TestCase):
    def setUp(self) -> None:
        train, splits = symmetric_fixture()
        self.root = make_project(self, train, splits)
        self.kwargs = mining_kwargs(self.root)
        self.base = self.root / "outputs" / "phase4" / "run_base"
        self.ext = self.root / "outputs" / "phase4" / "run_ext"
        m.run_mining(self.base, m.MiningConfig(symmetric_unit="ordered"), **self.kwargs)
        m.run_mining(self.ext, m.MiningConfig(min_support=5, min_pca=0.05), **self.kwargs)
        self.eval_kwargs = dict(
            valid_path=self.root / "data" / "valid.txt",
            valid_negatives_path=self.root / "data" / "valid_negatives.txt",
            phase3_dir=self.root / "outputs" / "phase3",
            train_path=self.root / "data" / "train.txt",
            root=self.root,
        )

    def test_configurable_grid_has_24_points_and_exclusion_variant(self) -> None:
        symmetry_id = ev.rule_ids_by_rank(self.base, [1])[1]["rule_id"]
        paths = ev.evaluate(self.ext, grid_min_pca=GRID_PCA, grid_min_support=GRID_SUPPORT, exclude_rule_ids=[symmetry_id], **self.eval_kwargs)
        result = json.loads(paths["json"].read_text(encoding="utf-8"))
        self.assertEqual(len(result["grid"]), 24)
        self.assertEqual({(p["min_pca"], p["min_support"]) for p in result["grid"]}, {(a, b) for a in GRID_PCA for b in GRID_SUPPORT})
        self.assertEqual(result["excluded_rule_ids_present_in_run"], [symmetry_id])
        self.assertTrue(all(p["tp"] == 0 for p in result["grid_without_excluded_rules"]))
        self.assertTrue(any(p["tp"] == 5 for p in result["grid"]))

    def test_rank_lookup(self) -> None:
        found = ev.rule_ids_by_rank(self.base, [1])
        self.assertEqual(found[1]["rule"], "P26(z,x) => P26(x,z)")
        with self.assertRaises(m.Phase4Error):
            ev.rule_ids_by_rank(self.base, [999])

    def run_compare(self, exclude=(1,)):
        ev.evaluate(self.base, **self.eval_kwargs)
        ev.evaluate(self.ext, grid_min_pca=GRID_PCA, grid_min_support=GRID_SUPPORT, **self.eval_kwargs)
        return cmp.compare_runs(self.base, self.ext, self.root / "outputs" / "phase4", exclude_ranks=exclude, **self.eval_kwargs)

    def test_compare_keeps_baseline_unchanged_and_never_opens_test_files(self) -> None:
        ev.evaluate(self.base, **self.eval_kwargs)
        ev.evaluate(self.ext, grid_min_pca=GRID_PCA, grid_min_support=GRID_SUPPORT, **self.eval_kwargs)
        before = {p.name: p.read_bytes() for p in self.base.iterdir()}
        with record_opened_files() as opened:
            paths = cmp.compare_runs(self.base, self.ext, self.root / "outputs" / "phase4", exclude_ranks=(1,), **self.eval_kwargs)
        self.assertEqual({p.name: p.read_bytes() for p in self.base.iterdir()}, before)
        names = [Path(p).name for p in opened]
        self.assertIn("valid.txt", names)
        self.assertFalse([n for n in names if n.startswith("test")])
        comparison = json.loads(paths["comparison"].read_text(encoding="utf-8"))
        self.assertEqual(len(comparison["grids"]["extended_all"]), 24)
        self.assertFalse(comparison["predictions_written"])

    def test_excluded_rules_never_reach_the_proposed_set(self) -> None:
        paths = self.run_compare(exclude=(1,))
        excluded_id = ev.rule_ids_by_rank(self.base, [1])[1]["rule_id"]
        proposed = json.loads(paths["candidates"].read_text(encoding="utf-8"))
        self.assertNotIn(excluded_id, [r["rule_id"] for r in proposed["rules"]])
        self.assertEqual(proposed["status"], "PROPOSED - not approved for Phase 5 yet")
        comparison = json.loads(paths["comparison"].read_text(encoding="utf-8"))
        self.assertEqual(comparison["rule_counts"]["baseline_selected"], len(json.loads((self.base / m.SELECTED_FILE).read_text())["rules"]))

    def test_symmetric_recount_is_reported(self) -> None:
        comparison = json.loads(self.run_compare(exclude=())["comparison"].read_text(encoding="utf-8"))
        rec = next(r for r in comparison["symmetric_recounted_rules"] if r["rule"] == "P26(z,x) => P26(x,z)")
        self.assertEqual((rec["baseline"]["support"], rec["extended"]["support"]), (60, 30))

    def test_compare_refuses_to_overwrite(self) -> None:
        self.run_compare()
        with self.assertRaises(FileExistsError):
            cmp.compare_runs(self.base, self.ext, self.root / "outputs" / "phase4", exclude_ranks=(1,), **self.eval_kwargs)

    def test_tampered_baseline_is_refused(self) -> None:
        ev.evaluate(self.base, **self.eval_kwargs)
        ev.evaluate(self.ext, grid_min_pca=GRID_PCA, grid_min_support=GRID_SUPPORT, **self.eval_kwargs)
        selected = self.base / m.SELECTED_FILE
        selected.write_text(selected.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaises(m.Phase4Error):
            cmp.compare_runs(self.base, self.ext, self.root / "outputs" / "phase4", exclude_ranks=(1,), **self.eval_kwargs)


@unittest.skipUnless((m.OUTPUT_ROOT / "run_grid_ext" / m.MANIFEST_FILE).is_file(), "run_grid_ext not generated yet")
class CheckedInGridExtTests(unittest.TestCase):
    def test_run_hashes_match_manifests_and_baseline_kept(self) -> None:
        import hashlib
        for name in ("run_default", "run_grid_ext"):
            run = m.OUTPUT_ROOT / name
            manifest = json.loads((run / m.MANIFEST_FILE).read_text(encoding="utf-8"))
            for file, digest in manifest["outputs"].items():
                self.assertEqual(hashlib.sha256((run / file).read_bytes()).hexdigest(), digest, f"{name}/{file}")
        baseline = json.loads((m.OUTPUT_ROOT / "run_default" / m.SELECTED_FILE).read_text(encoding="utf-8"))
        self.assertEqual(len(baseline["rules"]), 166)
        self.assertEqual(baseline["miner_version"], "4B.1.0")
        ext = json.loads((m.OUTPUT_ROOT / "run_grid_ext" / m.SELECTED_FILE).read_text(encoding="utf-8"))
        self.assertEqual(ext["config"]["symmetric_unit"], "unordered")


if __name__ == "__main__":
    unittest.main()
