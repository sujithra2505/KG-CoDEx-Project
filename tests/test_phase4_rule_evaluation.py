from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(Path(__file__).resolve().parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

import phase4_rule_evaluation as ev  # noqa: E402
import phase4_rule_mining as m  # noqa: E402
from phase4_fixtures import make_project, mining_kwargs, record_opened_files, symmetric_fixture  # noqa: E402


def _point(grid, min_pca, min_support):
    return next(g for g in grid if g["min_pca"] == min_pca and g["min_support"] == min_support)


class EvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        train, splits = symmetric_fixture()
        self.root = make_project(self, train, splits)
        self.run_dir = self.root / "outputs" / "phase4" / "run_t"
        m.run_mining(self.run_dir, **mining_kwargs(self.root))

    def evaluate(self):
        return ev.evaluate(
            self.run_dir,
            self.root / "data" / "valid.txt",
            self.root / "data" / "valid_negatives.txt",
            self.root / "outputs" / "phase3",
            self.root / "data" / "train.txt",
            self.root,
        )

    def test_counts_and_threshold_choice(self) -> None:
        paths = self.evaluate()
        result = json.loads(paths["json"].read_text(encoding="utf-8"))
        rule = next(r for r in result["per_rule"] if r["rule"] == "P26(z,x) => P26(x,z)")
        self.assertEqual((rule["val_hits"], rule["val_neg_hits"]), (5, 2))
        self.assertAlmostEqual(rule["val_precision_lower_bound"], 5 / 7, places=6)
        chosen = result["chosen"]
        # The rule has 30 couples of support: points with min_support 50 drop it; among the
        # tied points the strictest (0.5, 20) wins.
        self.assertEqual((chosen["min_pca"], chosen["min_support"]), (0.5, 20))
        self.assertEqual(_point(result["grid"], 0.5, 50)["tp"], 0)
        self.assertEqual((chosen["tp"], chosen["fp"], chosen["fn"]), (5, 2, 3))
        self.assertAlmostEqual(chosen["f1"], 2 * (5 / 7) * (5 / 8) / ((5 / 7) + (5 / 8)), places=5)
        validated = json.loads(paths["validated"].read_text(encoding="utf-8"))
        self.assertIn("P26(z,x) => P26(x,z)", [r["rule"] for r in validated["rules"]])

    def test_evaluator_never_opens_test_files(self) -> None:
        with record_opened_files() as opened:
            self.evaluate()
        names = [Path(p).name for p in opened]
        self.assertIn("valid.txt", names)
        self.assertIn("valid_negatives.txt", names)
        self.assertFalse([n for n in names if n.startswith("test")])

    def test_frozen_rules_are_enforced(self) -> None:
        selected = self.run_dir / m.SELECTED_FILE
        selected.write_text(selected.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaises(m.Phase4Error):
            self.evaluate()

    def test_outputs_list_counts_not_pairs(self) -> None:
        result = json.loads(self.evaluate()["json"].read_text(encoding="utf-8"))
        for rule in result["per_rule"]:
            self.assertTrue(all(not isinstance(v, (list, dict)) for v in rule.values()))

    def test_never_overwrites(self) -> None:
        self.evaluate()
        with self.assertRaises(FileExistsError):
            self.evaluate()

    def test_malformed_validation_file_fails(self) -> None:
        (self.root / "data" / "valid.txt").write_text("Q1 P26 Q2\n", encoding="utf-8")
        with self.assertRaises(m.Phase4Error):
            self.evaluate()

    def test_shape_round_trip(self) -> None:
        for shape in (("1", "P1", "f"), ("1", "P1", "b"), ("2", "P1", "f", "P2", "b"), ("2", "P1", "b", "P2", "f")):
            body = [list(a) for a in m.body_atoms(shape)]
            self.assertEqual(ev.shape_from_body(body), shape)


if __name__ == "__main__":
    unittest.main()
