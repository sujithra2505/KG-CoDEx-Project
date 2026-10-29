from __future__ import annotations

import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(Path(__file__).resolve().parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

import phase4_rule_mining as m  # noqa: E402
import phase5_predict as p5  # noqa: E402
from phase4_fixtures import make_project, record_opened_files  # noqa: E402

FAKE_VIS = "/**\n * vis-network\n * @version 9.1.2\n */\nwindow.vis = {DataSet: function(){}, Network: function(){}};\n"


def fixture_triples() -> list[tuple[str, str, str]]:
    train = []
    for i in range(30):  # spouse: 30 two-way couples + 8 one-way
        a, b = f"Q{100 + 2 * i}", f"Q{101 + 2 * i}"
        train += [(a, "P26", b), (b, "P26", a)]
    train += [(f"Q{200 + 2 * i}", "P26", f"Q{201 + 2 * i}") for i in range(8)]
    for i in range(25):  # citizenship + official language -> language spoken
        person, country, lang = f"Q{300 + i}", f"Q{400 + i % 5}", f"Q{500 + i % 5}"
        train += [(person, "P27", country)]
        if i < 20:
            train.append((person, "P1412", lang))
    train += [(f"Q{400 + k}", "P37", f"Q{500 + k}") for k in range(5)]
    for i in range(25):  # residence: a second route to the same language predictions for persons 20-24
        if i % 2 == 0 or i >= 20:
            train.append((f"Q{300 + i}", "P551", f"Q{400 + i % 5}"))
    for i in range(25):  # place of birth in a country -> citizenship
        train.append((f"Q{300 + i}", "P19", f"Q{600 + i % 5}"))
    train += [(f"Q{600 + k}", "P17", f"Q{400 + k}") for k in range(5)]
    return sorted(set(train))


def write_phase2_exports(root: Path, triples: list[tuple[str, str, str]]) -> None:
    out = root / "outputs" / "phase2"
    out.mkdir(parents=True)
    train_sha = m.sha256_file(root / "data" / "train.txt")
    nodes = sorted({s for s, _, _ in triples} | {o for _, _, o in triples})
    lines = [
        "<?xml version='1.0' encoding='utf-8'?>",
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="d6" for="edge" attr.name="relation_id" attr.type="string" />',
        '  <key id="d1" for="graph" attr.name="source_sha256" attr.type="string" />',
        '  <graph edgedefault="directed">',
        f'    <data key="d1">{train_sha}</data>',
    ]
    lines += [f'    <node id="{escape(n)}" />' for n in nodes]
    lines += [f'    <edge source="{s}" target="{o}" id="{r}"><data key="d6">{r}</data></edge>' for s, r, o in triples]
    lines += ["  </graph>", "</graphml>", ""]
    (out / "training_graph.graphml").write_text("\n".join(lines), encoding="utf-8")
    (out / "filtering_decisions.json").write_text(json.dumps({"source_sha256": train_sha, "unique_valid_triple_count": len(triples)}), encoding="utf-8")
    (out / "interactive_graph.html").write_text(f"<html><style>.vis-network{{}}</style><script>{FAKE_VIS}</script></html>", encoding="utf-8")


def write_rules(root: Path) -> None:
    run = root / "outputs" / "phase4" / "run_grid_ext"
    kwargs = dict(phase3_dir=root / "outputs" / "phase3", train_path=root / "data" / "train.txt",
                  relation_labels_path=root / "data" / "relation_labels.json",
                  entity_labels_path=root / "data" / "entity_labels.json", root=root)
    m.run_mining(run, m.MiningConfig(min_head_triples=5, min_support=5, min_pca_body=5, min_lift=0.0), **kwargs)
    selected = json.loads((run / m.SELECTED_FILE).read_text(encoding="utf-8"))
    doc = {
        "status": "PROPOSED - not approved for Phase 5 yet",
        "source_run": "outputs/phase4/run_grid_ext",
        "source_selected_rules_sha256": m.sha256_file(run / m.SELECTED_FILE),
        "rules": [{k: r[k] for k in ("rule_id", "rule", "display", "head", "type", "support", "pca_confidence", "wilson_lower", "counting", "flags")}
                  for r in selected["rules"]],
    }
    (root / "outputs" / "phase4" / "phase5_candidate_rules_proposed.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")


class Phase5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.train = fixture_triples()
        self.root = make_project(self, self.train)
        write_phase2_exports(self.root, self.train)
        write_rules(self.root)
        self.rules = json.loads((self.root / "outputs" / "phase4" / "phase5_candidate_rules_proposed.json").read_text(encoding="utf-8"))["rules"]

    def run_p5(self, name="phase5", cap=100):
        return p5.run(self.root, self.root / "outputs" / name, cap)

    def predictions(self, paths):
        return json.loads(paths["predictions"].read_text(encoding="utf-8"))["predictions"]

    def test_fixture_produces_predictions_from_several_rules(self) -> None:
        preds = self.predictions(self.run_p5())
        self.assertGreater(len(preds), 0)
        self.assertGreater(len({p["triple"]["relation"] for p in preds}), 1)
        self.assertTrue(any(len(p["supporting_rules"]) > 1 for p in preds))

    def test_deterministic_outputs(self) -> None:
        a, b = self.run_p5("p5_a"), self.run_p5("p5_b")
        for key in ("predictions", "report", "viewer"):
            self.assertEqual(a[key].read_bytes(), b[key].read_bytes(), key)
        ma, mb = (json.loads(p["manifest"].read_text(encoding="utf-8")) for p in (a, b))
        for doc in (ma, mb):
            doc.pop("generated_at"), doc.pop("runtime_seconds")
        self.assertEqual(ma, mb)

    def test_no_overlap_with_training_and_no_duplicates(self) -> None:
        preds = self.predictions(self.run_p5())
        triples = [(p["triple"]["subject"], p["triple"]["relation"], p["triple"]["object"]) for p in preds]
        self.assertFalse(set(triples) & set(self.train))
        self.assertEqual(len(triples), len(set(triples)))
        self.assertTrue(all(s != o for s, _, o in triples))

    def test_provenance_is_valid(self) -> None:
        preds = self.predictions(self.run_p5())
        rules = {r["rule_id"]: r for r in self.rules}
        train = set(self.train)
        for p in preds:
            s, h, o = p["triple"]["subject"], p["triple"]["relation"], p["triple"]["object"]
            self.assertEqual(p["round"], 1)
            self.assertEqual(p["prediction_id"], hashlib.sha256(f"{s}\t{h}\t{o}".encode()).hexdigest()[:16])
            self.assertEqual(p["ranking_score"]["name"], "max_wilson_lower")
            self.assertEqual(p["ranking_score"]["value"], max(r["wilson_lower"] for r in p["supporting_rules"]))
            self.assertEqual(p["ranking_score"]["from_rule_id"], p["supporting_rules"][0]["rule_id"])
            for sr in p["supporting_rules"]:
                rule = rules[sr["rule_id"]]
                self.assertEqual(rule["head"], h)
                self.assertEqual((sr["pca_confidence"], sr["wilson_lower"]), (rule["pca_confidence"], rule["wilson_lower"]))
                self.assertEqual(sr["grounding_count"], len(sr["body_groundings"]))
                body, _ = p5.parse_rule_text(rule["rule"])
                for grounding in sr["body_groundings"]:
                    self.assertEqual(len(grounding), len(body))
                    binding = {"x": s, "z": o}
                    for (rel, a, b), (gs, gr, go) in zip(body, grounding):
                        self.assertIn((gs, gr, go), train)
                        self.assertEqual(rel, gr)
                        for var, val in ((a, gs), (b, go)):
                            self.assertEqual(binding.setdefault(var, val), val)

    def test_cap_and_ranking_order(self) -> None:
        full = self.predictions(self.run_p5("full", cap=1000))
        capped_paths = self.run_p5("capped", cap=2)
        capped = self.predictions(capped_paths)
        per_rel = Counter(p["triple"]["relation"] for p in capped)
        self.assertTrue(all(n <= 2 for n in per_rel.values()))
        for rel in per_rel:
            full_rel = [p for p in full if p["triple"]["relation"] == rel]
            cap_rel = [p for p in capped if p["triple"]["relation"] == rel]
            self.assertEqual([p["prediction_id"] for p in cap_rel], [p["prediction_id"] for p in full_rel[:2]])
            self.assertEqual([p["relation_rank"] for p in cap_rel], list(range(1, len(cap_rel) + 1)))
            scores = [(-p["ranking_score"]["value"], -p["tie_break_values"]["max_pca_confidence"], -p["tie_break_values"]["supporting_rules"],
                       int(p["triple"]["subject"][1:]), int(p["triple"]["object"][1:])) for p in full_rel]
            self.assertEqual(scores, sorted(scores))
        manifest = json.loads(capped_paths["manifest"].read_text(encoding="utf-8"))
        self.assertTrue(any(v["candidates"] > v["retained"] for v in manifest["counts"]["per_relation"].values()))

    def test_protected_files_unchanged_and_split_files_not_opened(self) -> None:
        before = p5.protected_state(self.root)
        rule_list = (self.root / "outputs" / "phase4" / "phase5_candidate_rules_proposed.json").read_bytes()
        with record_opened_files() as opened:
            paths = self.run_p5()
        self.assertEqual(p5.protected_state(self.root), before)
        self.assertEqual((self.root / "outputs" / "phase4" / "phase5_candidate_rules_proposed.json").read_bytes(), rule_list)
        names = [Path(p).name for p in opened]
        self.assertIn("training_graph.graphml", names)
        self.assertFalse([n for n in names if n.startswith(("valid", "test"))])
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        self.assertTrue(manifest["protected_files_unchanged"])
        self.assertFalse(manifest["scored_against_validation_or_test"])
        for name, digest in manifest["outputs"].items():
            self.assertEqual(hashlib.sha256((paths["predictions"].parent / name).read_bytes()).hexdigest(), digest)

    def test_refuses_to_overwrite(self) -> None:
        self.run_p5()
        with self.assertRaises(FileExistsError):
            self.run_p5()

    def test_inconsistent_inputs_are_refused(self) -> None:
        decisions = self.root / "outputs" / "phase2" / "filtering_decisions.json"
        decisions.write_text(json.dumps({"source_sha256": "0" * 64, "unique_valid_triple_count": 1}), encoding="utf-8")
        with self.assertRaises(p5.Phase5Error):
            self.run_p5()

    def test_tampered_rule_source_is_refused(self) -> None:
        selected = self.root / "outputs" / "phase4" / "run_grid_ext" / m.SELECTED_FILE
        selected.write_text(selected.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaises(p5.Phase5Error):
            self.run_p5()

    def test_viewer_marks_predicted_and_training_edges(self) -> None:
        html = self.run_p5()["viewer"].read_text(encoding="utf-8")
        self.assertIn("vis-network", html)
        self.assertIn("dashes: true", html)
        self.assertIn("training evidence", html)
        self.assertNotIn("/*DATA*/", html)


@unittest.skipUnless((p5.OUTPUT_DIR / p5.MANIFEST_FILE).is_file(), "Phase 5 outputs not generated yet")
class CheckedInPhase5Tests(unittest.TestCase):
    def test_outputs_match_manifest_and_cap(self) -> None:
        manifest = json.loads((p5.OUTPUT_DIR / p5.MANIFEST_FILE).read_text(encoding="utf-8"))
        for name, digest in manifest["outputs"].items():
            self.assertEqual(hashlib.sha256((p5.OUTPUT_DIR / name).read_bytes()).hexdigest(), digest, name)
        preds = json.loads((p5.OUTPUT_DIR / p5.PREDICTIONS_FILE).read_text(encoding="utf-8"))["predictions"]
        self.assertTrue(all(n <= 100 for n in Counter(p["triple"]["relation"] for p in preds).values()))
        self.assertEqual(manifest["inputs"]["rule_list"]["rules"], 160)


if __name__ == "__main__":
    unittest.main()
