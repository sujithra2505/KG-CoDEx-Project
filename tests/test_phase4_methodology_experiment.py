from __future__ import annotations

import importlib.util
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
from phase4_fixtures import make_project, record_opened_files, symmetric_fixture  # noqa: E402

SCRIPT = ROOT / "outputs" / "phase4" / "methodology_comparison" / "phase4_methodology_experiment.py"
spec = importlib.util.spec_from_file_location("phase4_methodology_experiment", SCRIPT)
exp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exp)


def family_fixture():
    """symmetric_fixture plus 14 two-child families; siblings stated two-way in 7, one-way in 7."""
    train, splits = symmetric_fixture()
    for i in range(14):
        parent, a, b = f"Q{1000 + 3 * i}", f"Q{1001 + 3 * i}", f"Q{1002 + 3 * i}"
        train += [(parent, "P40", a), (parent, "P40", b), (a, "P3373", b)]
        if i < 7:
            train.append((b, "P3373", a))
    return train, splits


class ExperimentTests(unittest.TestCase):
    def setUp(self) -> None:
        train, splits = family_fixture()
        self.root = make_project(self, train, splits)
        phase4 = self.root / "outputs" / "phase4"
        kwargs = dict(phase3_dir=self.root / "outputs" / "phase3", train_path=self.root / "data" / "train.txt",
                      relation_labels_path=self.root / "data" / "relation_labels.json",
                      entity_labels_path=self.root / "data" / "entity_labels.json", root=self.root)
        m.run_mining(phase4 / "run_default", m.MiningConfig(symmetric_unit="ordered", min_support=5, min_pca_body=5), **kwargs)
        m.run_mining(phase4 / "run_grid_ext", m.MiningConfig(min_support=5, min_pca=0.05, min_pca_body=5), **kwargs)
        ekw = dict(valid_path=self.root / "data" / "valid.txt", valid_negatives_path=self.root / "data" / "valid_negatives.txt",
                   phase3_dir=self.root / "outputs" / "phase3", train_path=self.root / "data" / "train.txt", root=self.root)
        ev.evaluate(phase4 / "run_default", **ekw)
        ev.evaluate(phase4 / "run_grid_ext", grid_min_pca=(0.05, 0.075, 0.10, 0.20, 0.30, 0.50), grid_min_support=(5, 10, 20, 50), **ekw)
        cmp.compare_runs(phase4 / "run_default", phase4 / "run_grid_ext", phase4, exclude_ranks=(), **ekw)
        self.phase4 = phase4

    def run_exp(self):
        return exp.run_experiment(self.root, exclude_ranks=())

    def rows(self, results):
        return {r["rule"]: r for r in results["swap_invariant_rules"]}

    def test_both_direction_counts_only_two_way_couples(self) -> None:
        results = json.loads(self.run_exp()["results"].read_text(encoding="utf-8"))
        row = self.rows(results)["P40(y,x) & P40(y,z) => P3373(x,z)"]
        self.assertEqual(row["one"]["support"], 14)
        self.assertEqual(row["both"]["support"], 7)
        self.assertEqual(row["one"]["body_size"], row["both"]["body_size"])
        self.assertEqual(row["ordered"]["support"], 21)
        self.assertEqual((row["one"]["pca_confidence"], row["both"]["pca_confidence"]), (1.0, 0.5))

    def test_symmetry_rule_identical_in_one_and_both(self) -> None:
        results = json.loads(self.run_exp()["results"].read_text(encoding="utf-8"))
        row = self.rows(results)["P26(z,x) => P26(x,z)"]
        for key in ("support", "body_size", "pca_body_size", "std_confidence", "pca_confidence", "wilson_lower", "status"):
            self.assertEqual(row["one"][key], row["both"][key], key)

    def test_harness_reproduces_production_and_files_unchanged(self) -> None:
        before = {p: p.read_bytes() for d in ("run_default", "run_grid_ext") for p in (self.phase4 / d).iterdir()}
        proposed = (self.phase4 / "phase5_candidate_rules_proposed.json").read_bytes()
        with record_opened_files() as opened:
            results = json.loads(self.run_exp()["results"].read_text(encoding="utf-8"))
        self.assertIn("reproduced", results["harness_check"])
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.assertEqual((self.phase4 / "phase5_candidate_rules_proposed.json").read_bytes(), proposed)
        self.assertFalse([n for n in (Path(p).name for p in opened) if n.startswith("test")])
        self.assertFalse(results["predictions_written"])

    def test_refuses_to_overwrite(self) -> None:
        self.run_exp()
        with self.assertRaises(FileExistsError):
            self.run_exp()

    def test_reciprocity(self) -> None:
        kg = m.KG([("Q1", "P1", "Q2"), ("Q2", "P1", "Q1"), ("Q3", "P1", "Q4"), ("Q5", "P2", "Q6")])
        self.assertAlmostEqual(exp.reciprocity(kg, "P1"), 2 / 3)
        self.assertEqual(exp.reciprocity(kg, "P2"), 0.0)


if __name__ == "__main__":
    unittest.main()
