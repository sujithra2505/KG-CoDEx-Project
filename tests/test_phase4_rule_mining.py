from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(Path(__file__).resolve().parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

import phase4_rule_mining as m  # noqa: E402
from phase4_fixtures import make_project, mining_kwargs, record_opened_files, symmetric_fixture  # noqa: E402

OPEN = m.MiningConfig(
    min_head_triples=1, min_support=1, min_pca_body=1, min_head_coverage=0.0,
    min_pca=0.0, min_lift=0.0, top_k_per_head=1000, dominance_jaccard=1.01, no_gain_coverage=1.01,
)


def candidate(result: m.MiningResult, text: str) -> dict:
    matches = [c for c in result.candidates if c["rule"] == text]
    if not matches:
        raise AssertionError(f"{text} not among candidates: {[c['rule'] for c in result.candidates]}")
    return matches[0]


class MeasureTests(unittest.TestCase):
    def test_worked_example_composition(self) -> None:
        triples = [
            ("Q1", "P27", "Q10"), ("Q2", "P27", "Q10"), ("Q3", "P27", "Q11"), ("Q4", "P27", "Q10"),
            ("Q10", "P37", "Q20"), ("Q11", "P37", "Q21"),
            ("Q1", "P1412", "Q20"), ("Q2", "P1412", "Q22"), ("Q3", "P1412", "Q21"),
        ]
        c = candidate(m.mine_rules(m.KG(triples), OPEN), "P27(x,y) & P37(y,z) => P1412(x,z)")
        self.assertEqual((c["body_size"], c["support"], c["pca_body_size"]), (4, 2, 3))
        self.assertEqual(c["std_confidence"], 0.5)
        self.assertAlmostEqual(c["pca_confidence"], 2 / 3, places=6)
        self.assertAlmostEqual(c["head_coverage"], 2 / 3, places=6)
        self.assertAlmostEqual(c["wilson_lower"], 0.207655, places=5)
        self.assertAlmostEqual(c["lift"], 1.5, places=6)
        self.assertEqual(c["pca_side"], "subject")
        self.assertEqual(c["unknown_head_pairs_count"], 2)
        self.assertEqual(c["type"], "composition_chain")

    def test_worked_example_symmetry(self) -> None:
        triples = [("Q1", "P26", "Q2"), ("Q2", "P26", "Q1"), ("Q3", "P26", "Q4")]
        # Default 4B.2.0 scoring counts a symmetry rule per couple: {Q1,Q2} supports, {Q3,Q4} does not.
        c = candidate(m.mine_rules(m.KG(triples), OPEN), "P26(z,x) => P26(x,z)")
        self.assertEqual(c["counting"], "unordered_couples")
        self.assertEqual((c["body_size"], c["support"], c["pca_body_size"]), (2, 1, 1))
        self.assertEqual(c["ordered_counts"], {"body_size": 3, "support": 2, "pca_body_size": 2})
        self.assertEqual((c["std_confidence"], c["pca_confidence"]), (0.5, 1.0))
        self.assertAlmostEqual(c["wilson_lower"], m._r(m.wilson_lower(1, 1)), places=6)
        self.assertEqual(c["type"], "symmetry")

    def test_worked_example_symmetry_ordered_mode_reproduces_4b1(self) -> None:
        triples = [("Q1", "P26", "Q2"), ("Q2", "P26", "Q1"), ("Q3", "P26", "Q4")]
        config = m.MiningConfig(**{**m.asdict(OPEN), "symmetric_unit": "ordered"})
        c = candidate(m.mine_rules(m.KG(triples), config), "P26(z,x) => P26(x,z)")
        self.assertEqual(c["counting"], "ordered_pairs")
        self.assertEqual((c["body_size"], c["support"], c["pca_body_size"]), (3, 2, 2))
        self.assertAlmostEqual(c["wilson_lower"], 0.342372, places=5)

    def test_wilson_bounds(self) -> None:
        self.assertEqual(m.wilson_lower(0, 0), 0.0)
        self.assertEqual(m.wilson_lower(0, 10), 0.0)
        self.assertLess(m.wilson_lower(10, 10), 1.0)
        self.assertGreater(m.wilson_lower(100, 100), m.wilson_lower(10, 10))


class SupportCountingTests(unittest.TestCase):
    def test_support_counts_distinct_pairs_not_paths(self) -> None:
        triples = [("Q1", "P1", f"Q{10 + i}") for i in range(5)] + [(f"Q{10 + i}", "P2", "Q9") for i in range(5)]
        triples.append(("Q1", "P3", "Q9"))
        kg = m.KG(triples)
        shape = ("2", "P1", "f", "P2", "f")
        self.assertEqual(m.body_path_count(kg, shape), (5, 5))
        c = candidate(m.mine_rules(kg, OPEN), "P1(x,y) & P2(y,z) => P3(x,z)")
        self.assertEqual((c["body_size"], c["support"]), (1, 1))

    def test_x_equal_z_pairs_are_excluded(self) -> None:
        triples = [("Q1", "P1", "Q5"), ("Q2", "P1", "Q5"), ("Q1", "P2", "Q2")]
        kg = m.KG(triples)
        pairs = m.body_pairs(kg, ("2", "P1", "f", "P1", "b"))
        self.assertEqual({divmod(c, kg.N) for c in pairs}, {(kg.eid["Q1"], kg.eid["Q2"]), (kg.eid["Q2"], kg.eid["Q1"])})

    def test_no_tautologies_or_self_subrelations(self) -> None:
        triples = [(f"Q{i}", "P1", f"Q{i + 50}") for i in range(10)] + [(f"Q{i}", "P2", f"Q{i + 50}") for i in range(10)]
        result = m.mine_rules(m.KG(triples), OPEN)
        texts = {c["rule"] for c in result.candidates}
        self.assertNotIn("P1(x,z) => P1(x,z)", texts)
        self.assertNotIn("P2(x,z) => P2(x,z)", texts)
        self.assertIn("P1(x,z) => P2(x,z)", texts)
        for c in result.candidates:
            if c["length"] == 1 and c["body"][0][1:] == ["x", "z"]:
                self.assertNotEqual(c["body"][0][0], c["head"])

    def test_recounted_support_matches(self) -> None:
        train, _ = symmetric_fixture()
        result = m.mine_rules(m.KG(train), OPEN)
        for rule in result.selected:
            self.assertLessEqual(len(rule["supporting_examples"]), OPEN.n_examples)
            for ex in rule["supporting_examples"]:
                self.assertIn(tuple(ex["head_triple"]), set(train))
                for t in ex["body_triples"]:
                    self.assertIn(tuple(t), set(train))


class SymmetricCountingTests(unittest.TestCase):
    def test_swap_invariant_shapes(self) -> None:
        self.assertTrue(m.is_swap_invariant(("1", "P26", "b"), "P26"))
        self.assertFalse(m.is_swap_invariant(("1", "P26", "b"), "P451"))  # inverse, not symmetry
        self.assertFalse(m.is_swap_invariant(("1", "P26", "f"), "P451"))
        self.assertTrue(m.is_swap_invariant(("2", "P40", "f", "P40", "b"), "P26"))  # P40(x,y) & P40(z,y)
        self.assertTrue(m.is_swap_invariant(("2", "P40", "b", "P40", "f"), "P3373"))  # P40(y,x) & P40(y,z)
        self.assertFalse(m.is_swap_invariant(("2", "P40", "f", "P40", "f"), "P40"))  # chain
        self.assertFalse(m.is_swap_invariant(("2", "P40", "f", "P26", "b"), "P26"))

    def test_shared_child_spouse_counts_each_couple_once(self) -> None:
        triples = [("Q1", "P40", "Q9"), ("Q2", "P40", "Q9"), ("Q1", "P26", "Q2"), ("Q2", "P26", "Q1"),
                   ("Q3", "P40", "Q8"), ("Q4", "P40", "Q8"), ("Q5", "P26", "Q6")]
        c = candidate(m.mine_rules(m.KG(triples), OPEN), "P40(x,y) & P40(z,y) => P26(x,z)")
        self.assertEqual(c["ordered_counts"], {"body_size": 4, "support": 2, "pca_body_size": 2})
        self.assertEqual((c["body_size"], c["support"], c["pca_body_size"]), (2, 1, 1))
        self.assertEqual(c["head_count"], 2)  # couples {Q1,Q2} and {Q5,Q6}
        self.assertEqual(c["head_coverage"], 0.5)

    def test_min_support_applies_to_couples(self) -> None:
        triples = []
        for i in range(6):  # 6 two-way couples = 12 ordered support pairs
            a, b = f"Q{10 + 2 * i}", f"Q{11 + 2 * i}"
            triples += [(a, "P26", b), (b, "P26", a)]
        base = dict(min_head_triples=1, min_support=10, min_pca_body=1, min_lift=0.0)
        unordered = m.mine_rules(m.KG(triples), m.MiningConfig(**base))
        ordered = m.mine_rules(m.KG(triples), m.MiningConfig(**base, symmetric_unit="ordered"))
        self.assertFalse(any(c["rule"] == "P26(z,x) => P26(x,z)" for c in unordered.candidates))
        self.assertEqual(candidate(ordered, "P26(z,x) => P26(x,z)")["support"], 12)

    def test_non_symmetric_rules_keep_ordered_counts(self) -> None:
        triples = [("Q1", "P27", "Q10"), ("Q2", "P27", "Q10"), ("Q10", "P37", "Q20"), ("Q1", "P1412", "Q20")]
        c = candidate(m.mine_rules(m.KG(triples), OPEN), "P27(x,y) & P37(y,z) => P1412(x,z)")
        self.assertEqual(c["counting"], "ordered_pairs")
        self.assertEqual((c["body_size"], c["support"]), (c["ordered_counts"]["body_size"], c["ordered_counts"]["support"]))

    def test_hub_share_uses_ordered_support(self) -> None:
        triples = [(f"Q{10 + i}", "P40", "Q99") for i in range(6)]
        triples += [(f"Q{10 + i}", "P3373", f"Q{10 + j}") for i in range(6) for j in range(6) if i != j]
        result = m.mine_rules(m.KG(triples), m.MiningConfig(min_head_triples=1, min_support=5, min_pca_body=5, min_lift=0.0, dominance_jaccard=1.01, no_gain_coverage=1.01))
        rule = next(r for r in result.selected if r["rule"] == "P40(x,y) & P40(z,y) => P3373(x,z)")
        self.assertEqual(rule["support"], 15)
        self.assertEqual(rule["top_middle_entities"][0]["share"], 1.0)


class DirectionTests(unittest.TestCase):
    def setUp(self) -> None:
        # Q5 is the parent of Q1 and Q2; Q1 and Q2 are siblings in one direction only.
        self.triples = [("Q5", "P40", "Q1"), ("Q5", "P40", "Q2"), ("Q1", "P3373", "Q2"), ("Q7", "P40", "Q8")]
        self.result = m.mine_rules(m.KG(self.triples), OPEN)

    def test_reversed_atoms_bind_the_right_variables(self) -> None:
        c = candidate(self.result, "P40(y,x) & P40(y,z) => P3373(x,z)")
        self.assertEqual((c["body_size"], c["support"]), (1, 1))  # one couple {Q1,Q2}
        self.assertEqual((c["ordered_counts"]["body_size"], c["ordered_counts"]["support"]), (2, 1))
        self.assertEqual(c["type"], "composition_reversed")
        rule = next(r for r in self.result.selected if r["rule_id"] == c["rule_id"])
        example = rule["supporting_examples"][0]
        self.assertEqual(example["body_triples"], [["Q5", "P40", "Q1"], ["Q5", "P40", "Q2"]])
        self.assertEqual(example["head_triple"], ["Q1", "P3373", "Q2"])

    def test_forward_chain_does_not_match_reversed_data(self) -> None:
        self.assertFalse(any(c["rule"] == "P40(x,y) & P40(y,z) => P3373(x,z)" for c in self.result.candidates))

    def test_inverse_rule_direction(self) -> None:
        c = candidate(self.result, "P3373(z,x) => P40(x,z)") if any(
            c["rule"] == "P3373(z,x) => P40(x,z)" for c in self.result.candidates) else None
        self.assertIsNone(c)  # Q2->Q1 has no P40 fact, so this inverse rule has no support
        kg = m.KG(self.triples)
        self.assertTrue(m.body_holds(kg, ("1", "P3373", "b"), kg.eid["Q2"], kg.eid["Q1"]))
        self.assertFalse(m.body_holds(kg, ("1", "P3373", "b"), kg.eid["Q1"], kg.eid["Q2"]))


class FilterTests(unittest.TestCase):
    def test_duplicate_support_sets_are_marked_redundant(self) -> None:
        pairs = [(f"Q{i}", f"Q{i + 100}") for i in range(25)]
        triples = [(a, r, b) for a, b in pairs for r in ("P2", "P3", "P4")]
        config = m.MiningConfig(min_head_triples=1, min_support=5, min_pca_body=5, min_lift=0.0)
        result = m.mine_rules(m.KG(triples), config)
        p4_rules = [c for c in result.candidates if c["head"] == "P4" and c["length"] == 1 and c["type"] == "subrelation"]
        self.assertEqual(len(p4_rules), 2)
        statuses = sorted(c["status"] for c in p4_rules)
        self.assertEqual(statuses, ["rejected", "selected"])
        rejected = next(c for c in p4_rules if c["status"] == "rejected")
        kept = next(c for c in p4_rules if c["status"] == "selected")
        self.assertIn(f"redundant_with:{kept['rule_id']}", rejected["reasons"])

    def test_no_gain_over_shorter(self) -> None:
        pairs = [(f"Q{i}", f"Q{i + 100}") for i in range(25)]
        triples = [(a, "P2", b) for a, b in pairs] + [(a, "P4", b) for a, b in pairs]
        for i, (a, b) in enumerate(pairs):
            triples += [(a, "P5", f"Q{300 + i}"), (f"Q{300 + i}", "P6", b)]
        for i in range(5):  # extra body pairs without the head lower the 2-atom rule's score
            triples += [(f"Q{400 + i}", "P5", f"Q{500 + i}"), (f"Q{500 + i}", "P6", f"Q{600 + i}"), (f"Q{400 + i}", "P4", f"Q{700 + i}")]
        config = m.MiningConfig(min_head_triples=1, min_support=5, min_pca_body=5, min_lift=0.0, dominance_jaccard=1.01)
        result = m.mine_rules(m.KG(triples), config)
        long_rule = candidate(result, "P5(x,y) & P6(y,z) => P4(x,z)")
        short_rule = candidate(result, "P2(x,z) => P4(x,z)")
        self.assertEqual(short_rule["status"], "selected")
        self.assertIn(f"no_gain_over_shorter:{short_rule['rule_id']}", long_rule["reasons"])

    def test_thresholds_record_reasons(self) -> None:
        triples = [("Q1", "P27", "Q10"), ("Q10", "P37", "Q20"), ("Q1", "P1412", "Q20")]
        result = m.mine_rules(m.KG(triples), m.MiningConfig(min_head_triples=1, min_support=1))
        c = candidate(result, "P27(x,y) & P37(y,z) => P1412(x,z)")
        self.assertEqual(c["status"], "rejected")
        self.assertTrue(any(r.startswith("pca_body_below_min") for r in c["reasons"]))

    def test_top_k_per_head(self) -> None:
        pairs = [(f"Q{i}", f"Q{i + 100}") for i in range(25)]
        triples = [(a, r, b) for a, b in pairs for r in ("P2", "P3", "P4", "P5")]
        config = m.MiningConfig(min_head_triples=1, min_support=5, min_pca_body=5, min_lift=0.0, dominance_jaccard=1.01, top_k_per_head=1)
        result = m.mine_rules(m.KG(triples), config)
        for head, n in result.stats["selected_by_head"].items():
            self.assertEqual(n, 1, head)
        self.assertTrue(any("beyond_top_k_per_head" in c["reasons"] for c in result.candidates))


class HubAndCapTests(unittest.TestCase):
    def hub_triples(self) -> list[tuple[str, str, str]]:
        people = [f"Q{10 + i}" for i in range(30)]
        triples = [(p, "P27", "Q100") for p in people] + [("Q100", "P37", "Q200")]
        triples += [(p, "P1412", "Q200") for p in people]
        return triples

    def test_hub_heavy_bodies_are_flagged(self) -> None:
        config = m.MiningConfig(min_head_triples=1, min_lift=0.0)
        result = m.mine_rules(m.KG(self.hub_triples()), config)
        rule = next(r for r in result.selected if r["rule"] == "P27(x,y) & P37(y,z) => P1412(x,z)")
        self.assertEqual(rule["flags"]["hub_dominated"], "Q100")
        self.assertEqual(rule["top_middle_entities"][0], {"entity": "Q100", "support_pairs": 30, "share": 1.0})

    def test_large_bodies_are_skipped_and_logged(self) -> None:
        config = m.MiningConfig(min_head_triples=1, min_lift=0.0, max_body_paths=29)
        result = m.mine_rules(m.KG(self.hub_triples()), config)
        skipped = {s["body"]: s["paths"] for s in result.stats["body_shapes_skipped_too_large"]}
        self.assertEqual(skipped.get("P27(x,y) & P37(y,z)"), 30)
        self.assertFalse(any(c["rule"].startswith("P27(x,y) & P37(y,z)") for c in result.candidates))
        self.assertEqual(skipped.get("P27(x,y) & P27(z,y)"), 900)

    def test_cap_is_configurable(self) -> None:
        result = m.mine_rules(m.KG(self.hub_triples()), m.MiningConfig(min_head_triples=1, min_lift=0.0, max_body_paths=10_000))
        self.assertEqual(result.stats["body_shapes_skipped_too_large"], [])


class LeakageAndOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        train, splits = symmetric_fixture()
        self.train = train
        self.root = make_project(self, train, splits)

    def run_mining(self, name: str = "run_t", **kwargs):
        return m.run_mining(self.root / "outputs" / "phase4" / name, **mining_kwargs(self.root), **kwargs)

    def test_miner_never_opens_validation_or_test_files(self) -> None:
        with record_opened_files() as opened:
            self.run_mining()
        names = [Path(p).name for p in opened]
        self.assertIn("codexm_train_ontology.trig", names)
        for name in names:
            self.assertFalse(name.startswith(("valid", "test")), name)

    def test_validation_content_cannot_change_mined_rules(self) -> None:
        other = make_project(self, self.train, {"valid.txt": [("Q201", "P26", "Q200")] * 3, "valid_negatives.txt": []})
        first = self.run_mining()
        second = m.run_mining(other / "outputs" / "phase4" / "run_t", **mining_kwargs(other))
        for key in ("candidates", "stability"):
            self.assertEqual(first[key].read_bytes(), second[key].read_bytes(), key)
        # The Phase 3 manifest hash differs (it holds a timestamp); the rules must not.
        a, b = (json.loads(p["selected"].read_text(encoding="utf-8")) for p in (first, second))
        self.assertEqual(a["rules"], b["rules"])
        self.assertEqual(a["training_snapshot"]["phase3_trig"], b["training_snapshot"]["phase3_trig"])

    def test_loader_uses_only_the_training_named_graph(self) -> None:
        triples, info = m.load_training_triples(self.root / "outputs" / "phase3", self.root / "data" / "train.txt")
        self.assertEqual(set(triples), set(self.train))
        self.assertEqual(info["named_graph_used"], "urn:codexm:graph:train")
        self.assertFalse(any(r.startswith("http") for _, r, _ in triples))

    def test_tampered_phase3_graph_is_refused(self) -> None:
        trig = self.root / "outputs" / "phase3" / "codexm_train_ontology.trig"
        trig.write_text(trig.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaises(m.Phase4Error):
            m.load_training_triples(self.root / "outputs" / "phase3", self.root / "data" / "train.txt")

    def test_stability_split_is_disjoint_and_held_out_is_not_mined(self) -> None:
        train90, held10 = m.split_for_stability(self.train)
        self.assertEqual(len(train90) + len(held10), len(self.train))
        self.assertFalse(set(train90) & set(held10))
        self.assertEqual(m.split_for_stability(self.train), (train90, held10))
        kg90 = m.KG(train90)
        for s, r, o in held10:
            if s in kg90.eid and o in kg90.eid:
                self.assertFalse(kg90.has(kg90.eid[s], r, kg90.eid[o]))
        paths = self.run_mining()
        stability = json.loads(paths["stability"].read_text(encoding="utf-8"))
        self.assertEqual(stability["train90_triples"], len(train90))
        self.assertEqual(stability["held10_triples"], len(held10))

    def test_outputs_contain_no_predictions(self) -> None:
        paths = self.run_mining()
        selected = json.loads(paths["selected"].read_text(encoding="utf-8"))
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        self.assertFalse(manifest["predictions_written"])
        train = set(self.train)
        for rule in selected["rules"]:
            self.assertFalse({"predictions", "new_pairs", "predicted_edges"} & set(rule))
            self.assertIsInstance(rule["unknown_head_pairs_count"], int)
            for ce in rule["pca_counterexamples"]:
                x, h, z = ce["absent_head"]
                self.assertNotIn((x, h, z), train)
                self.assertTrue(any(s == x and r == h for s, r, _ in train) or any(r == h and o == z for _, r, o in train))
        for line in paths["candidates"].read_text(encoding="utf-8").splitlines():
            self.assertNotIn("predict", json.loads(line))

    def test_outputs_are_deterministic(self) -> None:
        a = self.run_mining("run_a")
        b = self.run_mining("run_b")
        for key in ("candidates", "selected", "stability", "report"):
            self.assertEqual(a[key].read_bytes(), b[key].read_bytes(), key)
        ma = json.loads(a["manifest"].read_text(encoding="utf-8"))
        mb = json.loads(b["manifest"].read_text(encoding="utf-8"))
        for doc in (ma, mb):
            for key in ("generated_at", "runtime_seconds", "run_dir"):
                doc.pop(key)
        self.assertEqual(ma, mb)

    def test_existing_run_directory_is_never_reused(self) -> None:
        paths = self.run_mining()
        before = paths["selected"].read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_mining()
        self.assertEqual(paths["selected"].read_bytes(), before)

    def test_manifest_records_hashes_and_unopened_files(self) -> None:
        paths = self.run_mining()
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        import hashlib
        for name, digest in manifest["outputs"].items():
            self.assertEqual(hashlib.sha256((paths["selected"].parent / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(manifest["protected_files"]["data/valid.txt"]["opened"], False)
        self.assertIn("sha256", manifest["protected_files"]["data/train.txt"])
        self.assertTrue(manifest["protected_files_unchanged"])

    def test_symmetry_rule_found_in_fixture(self) -> None:
        selected = json.loads(self.run_mining()["selected"].read_text(encoding="utf-8"))
        rule = next(r for r in selected["rules"] if r["rule"] == "P26(z,x) => P26(x,z)")
        self.assertEqual((rule["support"], rule["body_size"], rule["pca_body_size"]), (30, 37, 30))
        self.assertEqual(rule["ordered_counts"], {"body_size": 67, "support": 60, "pca_body_size": 60})


@unittest.skipUnless((ROOT / "outputs" / "phase3" / "phase3_manifest.json").is_file(), "Phase 3 outputs not present")
class ProductionSnapshotTests(unittest.TestCase):
    """Read-only checks on the real training graph (no files written)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.state_before = m.protected_state(m.ROOT)
        with record_opened_files() as opened:
            triples, cls.info = m.load_training_triples()
            cls.result = m.mine_rules(m.KG(triples), m.MiningConfig(), m.p3.load_label_map(m.RELATION_LABELS_PATH))
        cls.opened = [Path(p).name for p in opened]
        cls.state_after = m.protected_state(m.ROOT)

    def test_counts_match_phase3(self) -> None:
        self.assertEqual(self.info["training_triples"], 185584)
        self.assertEqual(self.result.stats["relations"], 51)
        self.assertEqual(self.result.stats["head_relations_mined"], 43)

    def test_skipped_shapes_are_the_six_largest(self) -> None:
        skipped = {s["body"]: s["paths"] for s in self.result.stats["body_shapes_skipped_too_large"]}
        self.assertEqual(len(skipped), 6)
        self.assertEqual(skipped["P106(x,y) & P106(z,y)"], 96828205)
        self.assertTrue(all(p > 5_000_000 for p in skipped.values()))

    def test_no_split_files_opened_and_protected_files_unchanged(self) -> None:
        self.assertIn("codexm_train_ontology.trig", self.opened)  # the recorder really saw file opens
        self.assertFalse([n for n in self.opened if n.startswith(("valid", "test"))])
        self.assertEqual(self.state_before, self.state_after)

    def test_selected_rules_meet_thresholds(self) -> None:
        config = m.MiningConfig()
        self.assertGreater(len(self.result.selected), 0)
        for rule in self.result.selected:
            self.assertGreaterEqual(rule["support"], config.min_support)
            self.assertGreaterEqual(rule["pca_confidence"], config.min_pca)
            self.assertGreaterEqual(rule["lift"], config.min_lift)


@unittest.skipUnless((m.OUTPUT_ROOT / m.DEFAULT_RUN_NAME / m.MANIFEST_FILE).is_file(), "default run not generated yet")
class CheckedInRunTests(unittest.TestCase):
    def test_output_hashes_match_manifest(self) -> None:
        import hashlib
        run = m.OUTPUT_ROOT / m.DEFAULT_RUN_NAME
        manifest = json.loads((run / m.MANIFEST_FILE).read_text(encoding="utf-8"))
        for name, digest in manifest["outputs"].items():
            self.assertEqual(hashlib.sha256((run / name).read_bytes()).hexdigest(), digest, name)


if __name__ == "__main__":
    unittest.main()
