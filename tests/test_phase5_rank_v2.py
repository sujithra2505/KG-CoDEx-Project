from __future__ import annotations

import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(Path(__file__).resolve().parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

import phase4_rule_evaluation as ev  # noqa: E402
import phase4_rule_mining as m  # noqa: E402
import phase5_predict as p5  # noqa: E402
import phase5_rank_v2 as v2  # noqa: E402
from phase4_fixtures import make_project, record_opened_files  # noqa: E402
from test_phase5_predict import fixture_triples, write_phase2_exports, write_rules  # noqa: E402


def rule(text: str, rid: str, wilson=0.5, pca=0.5) -> dict:
    body, head = p5.parse_rule_text(text)
    return {"rule_id": rid, "rule": text, "head": head, "body": body, "shape": ev.shape_from_body(body),
            "wilson_lower": wilson, "pca_confidence": pca}


class EvidenceCountTests(unittest.TestCase):
    def setUp(self) -> None:
        # Q1 -> Q10/Q11 -> Q9 : two middles for P1(x,y) & P2(y,z); also P3(x,z) directly.
        self.kg = m.KG([("Q1", "P1", "Q10"), ("Q1", "P1", "Q11"), ("Q10", "P2", "Q9"), ("Q11", "P2", "Q9"), ("Q1", "P3", "Q9")])
        self.x, self.z = self.kg.eid["Q1"], self.kg.eid["Q9"]

    def test_each_middle_is_one_match(self) -> None:
        matches = v2.body_matches(self.kg, [rule("P1(x,y) & P2(y,z) => P4(x,z)", "a")], self.x, self.z)
        self.assertEqual(len(matches), 2)
        self.assertIn(frozenset({("Q1", "P1", "Q10"), ("Q10", "P2", "Q9")}), matches)

    def test_matches_from_different_rules_add_up(self) -> None:
        rules = [rule("P1(x,y) & P2(y,z) => P4(x,z)", "a"), rule("P3(x,z) => P4(x,z)", "b")]
        self.assertEqual(len(v2.body_matches(self.kg, rules, self.x, self.z)), 3)

    def test_duplicate_proofs_are_not_double_counted(self) -> None:
        # The same rule listed twice (two records of one proof) must not add evidence.
        same = [rule("P1(x,y) & P2(y,z) => P4(x,z)", "a"), rule("P1(x,y) & P2(y,z) => P4(x,z)", "a2")]
        self.assertEqual(len(v2.body_matches(self.kg, same, self.x, self.z)), 2)

    def test_shared_triples_still_give_distinct_matches(self) -> None:
        matches = v2.body_matches(self.kg, [rule("P1(x,y) & P2(y,z) => P4(x,z)", "a")], self.x, self.z)
        shared = set.intersection(*(set(mt) for mt in matches))
        self.assertEqual(shared, set())  # here the two proofs share no triple
        kg = m.KG([("Q1", "P1", "Q10"), ("Q10", "P2", "Q9"), ("Q10", "P5", "Q9")])
        rules = [rule("P1(x,y) & P2(y,z) => P4(x,z)", "a"), rule("P1(x,y) & P5(y,z) => P4(x,z)", "b")]
        matches = v2.body_matches(kg, rules, kg.eid["Q1"], kg.eid["Q9"])
        self.assertEqual(len(matches), 2)  # share ("Q1","P1","Q10") but differ in the second triple

    def test_tie_order_uses_evidence_then_rules_then_ids(self) -> None:
        kg = m.KG([("Q1", "P1", "Q10"), ("Q1", "P1", "Q11"), ("Q10", "P2", "Q9"), ("Q11", "P2", "Q9"),
                   ("Q2", "P1", "Q12"), ("Q12", "P2", "Q8"), ("Q2", "P3", "Q8"),
                   ("Q3", "P1", "Q13"), ("Q13", "P2", "Q7")])
        r1, r2 = rule("P1(x,y) & P2(y,z) => P4(x,z)", "a"), rule("P3(x,z) => P4(x,z)", "b")
        e = kg.eid
        candidates = {(e["Q1"], "P4", e["Q9"]): ["a"], (e["Q2"], "P4", e["Q8"]): ["a", "b"], (e["Q3"], "P4", e["Q7"]): ["a"]}
        kept, _, _, evidence = v2.rank_v2(kg, candidates, {"a": r1, "b": r2}, cap=10)
        order = [kg.entities[k[0]] for _, _, k in kept]
        # Q1: 2 matches / 1 rule; Q2: 2 matches / 2 rules; Q3: 1 match.
        self.assertEqual(order, ["Q2", "Q1", "Q3"])
        self.assertEqual(evidence[(e["Q1"], "P4", e["Q9"])], 2)


class RankingV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.train = fixture_triples()
        self.root = make_project(self, self.train)
        write_phase2_exports(self.root, self.train)
        write_rules(self.root)
        p5.run(self.root, self.root / "outputs" / "phase5", 3)
        self.v1_dir = self.root / "outputs" / "phase5"

    def run_v2(self, name="ranking_v2", cap=3):
        return v2.run(self.root, self.v1_dir / name, cap)

    def test_v1_files_unchanged_and_split_files_not_opened(self) -> None:
        before = {p.name: p.read_bytes() for p in self.v1_dir.iterdir() if p.is_file()}
        with record_opened_files() as opened:
            paths = self.run_v2()
        self.assertEqual({p.name: p.read_bytes() for p in self.v1_dir.iterdir() if p.is_file()}, before)
        self.assertFalse([n for n in (Path(p).name for p in opened) if n.startswith(("valid", "test"))])
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        self.assertTrue(manifest["protected_and_v1_files_unchanged"])
        for name, digest in manifest["outputs"].items():
            self.assertEqual(hashlib.sha256((paths["manifest"].parent / name).read_bytes()).hexdigest(), digest)

    def test_deterministic_and_no_overwrite(self) -> None:
        a, b = self.run_v2("v2a"), self.run_v2("v2b")
        for key in ("predictions", "report", "viewer", "comparison"):
            self.assertEqual(a[key].read_bytes(), b[key].read_bytes(), key)
        with self.assertRaises(FileExistsError):
            self.run_v2("v2a")

    def test_no_training_overlap_cap_and_evidence_fields(self) -> None:
        preds = json.loads(self.run_v2()["predictions"].read_text(encoding="utf-8"))["predictions"]
        triples = {(p["triple"]["subject"], p["triple"]["relation"], p["triple"]["object"]) for p in preds}
        self.assertFalse(triples & set(self.train))
        self.assertTrue(all(n <= 3 for n in Counter(t[1] for t in triples).values()))
        for p in preds:
            distinct = {frozenset(tuple(t) for t in g) for sr in p["supporting_rules"] for g in sr["body_groundings"]}
            self.assertEqual(p["tie_break_values"]["distinct_body_matches"], len(distinct))
            self.assertEqual(p["tie_break_values"]["supporting_rules"], len(p["supporting_rules"]))

    def test_same_candidates_scores_and_provenance_as_v1(self) -> None:
        v1 = json.loads((self.v1_dir / p5.PREDICTIONS_FILE).read_text(encoding="utf-8"))["predictions"]
        new = json.loads(self.run_v2()["predictions"].read_text(encoding="utf-8"))["predictions"]
        for rel in {p["triple"]["relation"] for p in v1}:
            s1 = sorted(p["ranking_score"]["value"] for p in v1 if p["triple"]["relation"] == rel)
            s2 = sorted(p["ranking_score"]["value"] for p in new if p["triple"]["relation"] == rel)
            self.assertEqual(s1, s2, rel)
        by1 = {p["prediction_id"]: p for p in v1}
        for p in new:
            if p["prediction_id"] in by1:
                self.assertEqual(p["supporting_rules"], by1[p["prediction_id"]]["supporting_rules"])

    def test_ranking_order_within_relation(self) -> None:
        new = json.loads(self.run_v2(cap=1000)["predictions"].read_text(encoding="utf-8"))["predictions"]
        for rel in {p["triple"]["relation"] for p in new}:
            rows = [p for p in new if p["triple"]["relation"] == rel]
            keys = [(-p["ranking_score"]["value"], -p["tie_break_values"]["max_pca_confidence"],
                     -p["tie_break_values"]["distinct_body_matches"], -p["tie_break_values"]["supporting_rules"],
                     int(p["triple"]["subject"][1:]), int(p["triple"]["object"][1:])) for p in rows]
            self.assertEqual(keys, sorted(keys))


@unittest.skipUnless((v2.OUTPUT_DIR / p5.MANIFEST_FILE).is_file(), "ranking_v2 not generated yet")
class CheckedInV2Tests(unittest.TestCase):
    def test_outputs_match_manifest_and_v1_intact(self) -> None:
        manifest = json.loads((v2.OUTPUT_DIR / p5.MANIFEST_FILE).read_text(encoding="utf-8"))
        for name, digest in manifest["outputs"].items():
            self.assertEqual(hashlib.sha256((v2.OUTPUT_DIR / name).read_bytes()).hexdigest(), digest, name)
        v1 = json.loads((p5.OUTPUT_DIR / p5.MANIFEST_FILE).read_text(encoding="utf-8"))
        for name, digest in v1["outputs"].items():
            self.assertEqual(hashlib.sha256((p5.OUTPUT_DIR / name).read_bytes()).hexdigest(), digest, name)


if __name__ == "__main__":
    unittest.main()
