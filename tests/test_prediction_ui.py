from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(Path(__file__).resolve().parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

import phase5_predict as p5  # noqa: E402
import phase5_rank_v2 as v2  # noqa: E402
import phase5_ui_build as ui  # noqa: E402
from phase4_fixtures import make_project, record_opened_files  # noqa: E402
from test_phase5_predict import fixture_triples, write_phase2_exports, write_rules  # noqa: E402


def read_payload(path: Path) -> list:
    text = path.read_text(encoding="utf-8").strip()
    inner = text[text.index("(") + 1: text.rindex(")")]
    return json.loads("[" + inner + "]")


def make_phase5_project(test: unittest.TestCase, splits=None) -> tuple[Path, list]:
    train = fixture_triples()
    root = make_project(test, train, splits)
    write_phase2_exports(root, train)
    write_rules(root)
    p5.run(root, root / "outputs" / "phase5", 3)
    v2.run(root, root / "outputs" / "phase5" / "ranking_v2", 3)
    return root, train


class PredictionUIBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root, self.train = make_phase5_project(self)
        self.out = self.root / "outputs" / "prediction_ui"
        self.paths = ui.build(self.root, self.out)
        self.index = read_payload(self.out / "data" / "index.js")[0]
        self.v1 = json.loads((self.root / "outputs" / "phase5" / "predictions.json").read_text(encoding="utf-8"))["predictions"]
        self.v2 = json.loads((self.root / "outputs" / "phase5" / "ranking_v2" / "predictions.json").read_text(encoding="utf-8"))["predictions"]

    def rows(self):
        return [dict(zip(ui.ROW_FIELDS, r)) for r in self.index["rows"]]

    def test_rows_keep_ids_direction_ranks_and_scores(self) -> None:
        rows = {r["pid"]: r for r in self.rows()}
        self.assertEqual(len(rows), len({p["prediction_id"] for p in self.v1 + self.v2}))
        for version, preds in (("v1", self.v1), ("v2", self.v2)):
            for p in preds:
                r = rows[p["prediction_id"]]
                self.assertEqual((r["s"], r["r"], r["o"]), (p["triple"]["subject"], p["triple"]["relation"], p["triple"]["object"]))
                self.assertEqual(r[f"{version}rank"], p["relation_rank"])
                self.assertEqual(r["score"], p["ranking_score"]["value"])
                self.assertEqual(r["nrules"], len(p["supporting_rules"]))
        labels = dict(self.index["entities"])
        for p in self.v1:
            self.assertEqual(labels[p["triple"]["subject"]], p["labels"]["subject"])
            self.assertEqual(self.index["relations"][p["triple"]["relation"]], p["labels"]["relation"])

    def test_no_prediction_is_a_training_fact(self) -> None:
        train = set(self.train)
        self.assertFalse({(r["s"], r["r"], r["o"]) for r in self.rows()} & train)

    def test_provenance_chunks_match_source_files(self) -> None:
        rows = {r["pid"]: r for r in self.rows()}
        seen = set()
        for path in sorted((self.out / "data" / "prov").glob("*.js")):
            rel, prov = read_payload(path)
            for pid, rec in prov.items():
                self.assertEqual(rows[pid]["r"], rel)
                seen.add(pid)
        self.assertEqual(seen, set(rows))
        for version, preds in (("v1", self.v1), ("v2", self.v2)):
            for p in preds:
                rel, prov = read_payload(self.out / "data" / "prov" / f"{p['triple']['relation']}.js")
                rec = prov[p["prediction_id"]]
                self.assertEqual(rec["supporting_rules"], p["supporting_rules"])
                self.assertEqual(rec["round"], 1)
                self.assertEqual(rec[f"rank_{version}"], p["relation_rank"])
                self.assertEqual(rec[f"tie_break_{version}"], p["tie_break_values"])

    def test_evidence_count_matches_v2(self) -> None:
        rows = {r["pid"]: r for r in self.rows()}
        for p in self.v2:
            self.assertEqual(rows[p["prediction_id"]]["evidence"], p["tie_break_values"]["distinct_body_matches"])

    def test_training_buckets_hold_exactly_the_training_graph(self) -> None:
        found = set()
        for path in sorted((self.out / "data" / "train").glob("b*.js")):
            bucket, adj = read_payload(path)
            for entity, edges in adj.items():
                self.assertEqual(ui.bucket_of(entity), bucket)
                for s, r, o in edges:
                    self.assertIn(entity, (s, o))
                    found.add((s, r, o))
        self.assertEqual(found, set(self.train))
        self.assertEqual(self.index["meta"]["training_edges"], len(self.train))

    def test_comparison_matches_v2_manifest(self) -> None:
        manifest = json.loads((self.root / "outputs" / "phase5" / "ranking_v2" / "phase5_manifest.json").read_text(encoding="utf-8"))
        s = self.index["comparison"]["summary"]
        c = manifest["counts"]["changed_vs_v1"]
        self.assertEqual((s["both"], s["v1_only"], s["v2_only"], s["rank_changed"]), (c["kept_in_both"], c["dropped"], c["added"], c["rank_changed"]))
        for rel, v in self.index["comparison"]["per_relation"].items():
            self.assertEqual(v["v1"], sum(1 for p in self.v1 if p["triple"]["relation"] == rel))
            self.assertEqual(sum(v["hist_v2"]), v["v2"])

    def test_deterministic_and_no_overwrite(self) -> None:
        other = self.root / "outputs" / "prediction_ui_2"
        ui.build(self.root, other)
        for path in sorted(self.out.rglob("*")):
            if path.is_file() and path.name != "ui_manifest.json":
                self.assertEqual(path.read_bytes(), (other / path.relative_to(self.out)).read_bytes(), path.name)
        with self.assertRaises(FileExistsError):
            ui.build(self.root, self.out)

    def test_build_leaves_inputs_unchanged_and_never_opens_split_files(self) -> None:
        before = ui.protected_state(self.root)
        with record_opened_files() as opened:
            ui.build(self.root, self.root / "outputs" / "prediction_ui_3")
        self.assertEqual(ui.protected_state(self.root), before)
        names = [Path(p).name for p in opened]
        self.assertIn("predictions.json", names)
        self.assertFalse([n for n in names if n.startswith(("valid", "test"))])

    def test_page_assets_and_evaluation_gate(self) -> None:
        html = (self.out / "index.html").read_text(encoding="utf-8")
        for asset in ("filters.js", "lib/vis-network.js", "app.js", "data/index.js"):
            self.assertIn(asset, html)
            self.assertTrue((self.out / asset).is_file())
        app = (self.out / "app.js").read_text(encoding="utf-8")
        self.assertIn("../phase6/evaluation_test/", app)
        self.assertNotIn("XMLHttpRequest", app)
        self.assertNotIn("fetch(", app)
        self.assertFalse((self.root / "outputs" / "phase6").exists())  # building the UI never creates results

    def test_tampered_prediction_file_is_refused(self) -> None:
        path = self.root / "outputs" / "phase5" / "ranking_v2" / "predictions.json"
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaises(ui.UIBuildError):
            ui.build(self.root, self.root / "outputs" / "prediction_ui_4")


@unittest.skipUnless(shutil.which("node"), "node not installed; JavaScript filter tests skipped")
class JavaScriptFilterTests(unittest.TestCase):
    def test_filters_js(self) -> None:
        result = subprocess.run(["node", str(ROOT / "tests" / "ui" / "filters.test.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


BROWSERS = [Path(p) for p in ("C:/Program Files/Google/Chrome/Application/chrome.exe",
                               "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")]


@unittest.skipUnless(shutil.which("node") and any(b.is_file() for b in BROWSERS) and (ui.OUTPUT_DIR / "index.html").is_file(),
                     "node, Chrome/Edge or the built UI missing; browser smoke test skipped")
class BrowserSmokeTests(unittest.TestCase):
    def test_built_page_loads_searches_and_filters_from_file_url(self) -> None:
        result = subprocess.run(["node", str(ROOT / "tests" / "ui" / "browser_smoke.js"), (ui.OUTPUT_DIR / "index.html").as_uri()],
                                capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless((ui.OUTPUT_DIR / "ui_manifest.json").is_file(), "UI not built yet")
class CheckedInUITests(unittest.TestCase):
    def test_outputs_match_manifest(self) -> None:
        import hashlib
        manifest = json.loads((ui.OUTPUT_DIR / "ui_manifest.json").read_text(encoding="utf-8"))
        for name, digest in manifest["outputs"].items():
            self.assertEqual(hashlib.sha256((ui.OUTPUT_DIR / name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(manifest["counts"]["v1_only"], manifest["counts"]["v2_only"])


if __name__ == "__main__":
    unittest.main()
