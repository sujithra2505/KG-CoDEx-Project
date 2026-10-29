"""Build the static prediction-explorer UI from existing Phase 5 outputs (no new predictions).

Reads (read-only):
  outputs/phase5/predictions.json              (v1) + phase5_manifest.json
  outputs/phase5/ranking_v2/predictions.json   (v2) + phase5_manifest.json
  outputs/phase2/training_graph.graphml        (training edges, via phase5_predict.load_training_graph)
  outputs/phase2/interactive_graph.html        (only to copy its embedded vis-network library)
  data/entity_labels.json, data/relation_labels.json
  prediction_ui_src/*                          (HTML/JS/CSS sources)

Writes a new folder (default ``outputs/prediction_ui/``); refuses to overwrite.
The UI is static: open ``index.html`` in a browser. Validation and test files are
never opened. Phase 6 evaluation is a separate command (``phase6_evaluate.py``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import phase4_rule_mining as m
import phase5_predict as p5

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "prediction_ui_src"
OUTPUT_DIR = ROOT / "outputs" / "prediction_ui"
NAME = "phase5_ui_build.py"
VERSION = "1.0.0"
BUCKETS = 64
ROW_FIELDS = ["pid", "s", "r", "o", "v1rank", "v2rank", "score", "maxpca", "nrules", "evidence"]
SRC_FILES = ("index.html", "app.js", "app.css", "filters.js", "README.md")
HIST_BINS = 10


class UIBuildError(RuntimeError):
    pass


def protected_state(root: Path) -> dict[str, Any]:
    """Phase 1-4 protected files (from phase5_predict) plus every Phase 5 v1/v2 file."""
    state = p5.protected_state(root)
    for pattern in ("outputs/phase5/*", "outputs/phase5/ranking_v2/*"):
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                state[path.relative_to(root).as_posix()] = {"sha256": m.sha256_file(path)}
    for name in ("phase5_predict.py", "phase5_rank_v2.py"):
        if (root / name).is_file():
            state[name] = {"sha256": m.sha256_file(root / name)}
    return state


def bucket_of(entity: str) -> int:
    return int(entity[1:]) % BUCKETS


def js_payload(callback: str, *args: Any) -> str:
    body = ", ".join(json.dumps(a, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for a in args)
    return f"{callback}({body});\n".replace("</", "<\\/")


def load_version(dir_: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = json.loads((dir_ / p5.MANIFEST_FILE).read_text(encoding="utf-8"))
    for name, digest in manifest["outputs"].items():
        if m.sha256_file(dir_ / name) != digest:
            raise UIBuildError(f"{dir_ / name} does not match its manifest")
    doc = json.loads((dir_ / p5.PREDICTIONS_FILE).read_text(encoding="utf-8"))
    return doc, manifest


def distinct_matches(record: dict[str, Any]) -> int:
    return len({frozenset(tuple(t) for t in g) for sr in record["supporting_rules"] for g in sr["body_groundings"]})


def histogram(scores: Iterable[float]) -> list[int]:
    bins = [0] * HIST_BINS
    for s in scores:
        bins[min(HIST_BINS - 1, int(s * HIST_BINS))] += 1
    return bins


def build_data(root: Path) -> dict[str, Any]:
    v1_dir, v2_dir = root / "outputs" / "phase5", root / "outputs" / "phase5" / "ranking_v2"
    v1, v1_manifest = load_version(v1_dir)
    v2, v2_manifest = load_version(v2_dir)
    if v1_manifest["inputs"]["rule_list"]["sha256"] != v2_manifest["inputs"]["rule_list"]["sha256"]:
        raise UIBuildError("v1 and v2 used different rule lists")
    triples, graph_info = p5.load_training_graph(root)
    if graph_info["phase2_graphml"]["sha256"] != v1_manifest["inputs"]["phase2_graphml"]["sha256"]:
        raise UIBuildError("training graph differs from the one used for the predictions")
    train_set = set(triples)
    entity_labels = m.p3.load_label_map(root / "data" / "entity_labels.json")
    relation_labels = m.p3.load_label_map(root / "data" / "relation_labels.json")

    rows: dict[str, dict[str, Any]] = {}
    provenance: dict[str, dict[str, Any]] = {}
    for version, doc in (("v1", v1), ("v2", v2)):
        for rec in doc["predictions"]:
            t = rec["triple"]
            key = (t["subject"], t["relation"], t["object"])
            if key in train_set:
                raise UIBuildError(f"prediction {rec['prediction_id']} is a training triple")
            pid = rec["prediction_id"]
            if pid != hashlib.sha256("\t".join(key).encode("utf-8")).hexdigest()[:16]:
                raise UIBuildError(f"prediction id {pid} does not match its triple")
            evidence = distinct_matches(rec)
            if version == "v2" and evidence != rec["tie_break_values"]["distinct_body_matches"]:
                raise UIBuildError(f"evidence count mismatch for {pid}")
            row = rows.setdefault(pid, {"pid": pid, "s": key[0], "r": key[1], "o": key[2], "v1rank": None, "v2rank": None,
                                        "score": rec["ranking_score"]["value"], "maxpca": rec["tie_break_values"]["max_pca_confidence"],
                                        "nrules": len(rec["supporting_rules"]), "evidence": evidence})
            if (row["s"], row["r"], row["o"]) != key or row["score"] != rec["ranking_score"]["value"] or row["evidence"] != evidence \
                    or row["nrules"] != len(rec["supporting_rules"]):
                raise UIBuildError(f"v1 and v2 disagree on prediction {pid}")
            row[f"{version}rank"] = rec["relation_rank"]
            prov = provenance.setdefault(pid, {"round": rec["round"], "status": rec["status"], "ranking_score": rec["ranking_score"],
                                               "supporting_rules": rec["supporting_rules"]})
            if prov["supporting_rules"] != rec["supporting_rules"] or prov["round"] != rec["round"]:
                raise UIBuildError(f"v1 and v2 provenance differ for {pid}")
            prov[f"tie_break_{version}"] = rec["tie_break_values"]
            prov[f"rank_{version}"] = rec["relation_rank"]

    ordered = sorted(rows.values(), key=lambda r: (int(r["r"][1:]), r["v2rank"] or 10**9, r["v1rank"] or 10**9, r["pid"]))
    summary = Counter()
    per_relation: dict[str, dict[str, Any]] = defaultdict(lambda: Counter())
    for r in ordered:
        cls = "both" if r["v1rank"] and r["v2rank"] else ("v1_only" if r["v1rank"] else "v2_only")
        summary[cls] += 1
        per_relation[r["r"]][cls] += 1
        if cls == "both" and r["v1rank"] != r["v2rank"]:
            summary["rank_changed"] += 1
            per_relation[r["r"]]["rank_changed"] += 1
    expected = v2_manifest["counts"]["changed_vs_v1"]
    if (summary["both"], summary["v1_only"], summary["v2_only"], summary["rank_changed"]) != \
            (expected["kept_in_both"], expected["dropped"], expected["added"], expected["rank_changed"]):
        raise UIBuildError("comparison does not reproduce the v2 manifest's changed_vs_v1 counts")
    comparison = {
        "summary": {**{k: summary[k] for k in ("both", "v1_only", "v2_only", "rank_changed")},
                    "v1_total": len(v1["predictions"]), "v2_total": len(v2["predictions"]),
                    "confirmed_by": "outputs/phase5/ranking_v2/phase5_manifest.json counts.changed_vs_v1"},
        "per_relation": {
            rel: {**{k: per_relation[rel][k] for k in ("both", "v1_only", "v2_only", "rank_changed")},
                  "v1": sum(1 for r in ordered if r["r"] == rel and r["v1rank"]),
                  "v2": sum(1 for r in ordered if r["r"] == rel and r["v2rank"]),
                  "hist_v1": histogram(r["score"] for r in ordered if r["r"] == rel and r["v1rank"]),
                  "hist_v2": histogram(r["score"] for r in ordered if r["r"] == rel and r["v2rank"])}
            for rel in sorted(per_relation, key=lambda x: int(x[1:]))
        },
        "hist_bins": [round(i / HIST_BINS, 1) for i in range(HIST_BINS + 1)],
    }

    entities = sorted({e for s, _, o in triples for e in (s, o)}, key=lambda e: int(e[1:]))
    used_relations = sorted({r for _, r, _ in triples}, key=lambda r: int(r[1:]))
    index = {
        "meta": {
            "builder": NAME, "builder_version": VERSION, "row_fields": ROW_FIELDS, "buckets": BUCKETS,
            "training_edges": len(triples), "entities": len(entities),
            "versions": {
                "v1": {"path": "outputs/phase5/predictions.json", "sha256": m.sha256_file(v1_dir / p5.PREDICTIONS_FILE),
                       "tie_break": v1["settings"]["tie_break"], "cap": v1["settings"]["cap_per_relation"]},
                "v2": {"path": "outputs/phase5/ranking_v2/predictions.json", "sha256": m.sha256_file(v2_dir / p5.PREDICTIONS_FILE),
                       "tie_break": v2["settings"]["tie_break"], "cap": v2["settings"]["cap_per_relation"]},
            },
            "ranking_score": v1["settings"]["ranking_score"],
            "evidence_definition": v2["settings"]["evidence_definition"],
            "round": 1,
        },
        "relations": {r: relation_labels.get(r, r) for r in used_relations},
        "entities": [[e, entity_labels.get(e, e)] for e in entities],
        "rows": [[r[f] for f in ROW_FIELDS] for r in ordered],
        "comparison": comparison,
    }
    prov_by_rel: dict[str, dict[str, Any]] = defaultdict(dict)
    for pid in sorted(provenance):
        prov_by_rel[rows[pid]["r"]][pid] = provenance[pid]
    train_buckets: dict[int, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for s, r, o in triples:
        train_buckets[bucket_of(s)][s].append([s, r, o])
        if o != s:
            train_buckets[bucket_of(o)][o].append([s, r, o])
    inputs = {
        "v1_predictions": index["meta"]["versions"]["v1"], "v2_predictions": index["meta"]["versions"]["v2"],
        "v1_manifest_sha256": m.sha256_file(v1_dir / p5.MANIFEST_FILE), "v2_manifest_sha256": m.sha256_file(v2_dir / p5.MANIFEST_FILE),
        **graph_info,
        "entity_labels_sha256": m.sha256_file(root / "data" / "entity_labels.json"),
        "relation_labels_sha256": m.sha256_file(root / "data" / "relation_labels.json"),
    }
    return {"index": index, "prov": prov_by_rel, "train": train_buckets, "inputs": inputs}


def build(root: Path = ROOT, out_dir: Path | None = None, src_dir: Path | None = None) -> dict[str, Path]:
    out_dir = out_dir or root / "outputs" / "prediction_ui"
    src_dir = src_dir or SRC_DIR
    if out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing UI folder {out_dir}")
    state_before = protected_state(root)
    data = build_data(root)
    vis_js, vis_css = p5.extract_vis_library(root / "outputs" / "phase2" / "interactive_graph.html")

    files: dict[str, str] = {}
    for name in SRC_FILES:
        files[name] = (src_dir / name).read_text(encoding="utf-8")
    files["lib/vis-network.js"] = vis_js + "\n"
    files["lib/vis-network.css"] = vis_css + "\n"
    files["data/index.js"] = js_payload("window.UI_INDEX_LOADED", data["index"])
    for rel, prov in sorted(data["prov"].items()):
        files[f"data/prov/{rel}.js"] = js_payload("window.UI_PROV_LOADED", rel, prov)
    for b in range(BUCKETS):
        adj = {e: sorted(v, key=lambda t: (int(t[1][1:]), int(t[0][1:]), int(t[2][1:]))) for e, v in sorted(data["train"].get(b, {}).items())}
        files[f"data/train/b{b:02d}.js"] = js_payload("window.UI_TRAIN_LOADED", b, adj)

    if protected_state(root) != state_before:
        raise UIBuildError("protected files changed during the build")
    manifest = {
        "tool": NAME, "version": VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": data["inputs"],
        "counts": {"prediction_rows": len(data["index"]["rows"]), **data["index"]["comparison"]["summary"],
                   "relations_with_predictions": len(data["prov"]), "training_edges": data["index"]["meta"]["training_edges"]},
        "outputs": {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in sorted(files.items())},
        "files_not_opened": "data/valid*, data/test*",
        "protected_files": state_before, "protected_files_unchanged": True,
        "note": "Static UI built from existing Phase 5 files; no predictions were generated or changed.",
    }
    out_dir.mkdir(parents=True)
    for name, text in sorted(files.items()):
        path = out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        m._write_new(path, text)
    m._write_new(out_dir / "ui_manifest.json", m._json(manifest))
    return {"index": out_dir / "index.html", "manifest": out_dir / "ui_manifest.json"}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(list(argv) if argv is not None else None)
    for name, path in build(ROOT, args.out_dir).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
