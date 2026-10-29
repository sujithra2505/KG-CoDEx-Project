"""Cap experiment: per-relation caps 100 (existing baseline), 250, 500 and 1000 for ranking v1 and v2.

Steps (run in this order; every step refuses to overwrite its outputs):

  py cap_experiment.py freeze-rule   write the selection rule BEFORE any validation result exists
  py cap_experiment.py generate      v1 and v2 predictions for caps 250, 500, 1000 (frozen rules,
                                     same candidate generation, scoring and ranking as Phase 5)
  py cap_experiment.py validate      label all 8 configurations against the VALIDATION split only
                                     (test files are blocked), then apply the frozen rule
  py cap_experiment.py test --i-approve-cap-test-evaluation
                                     GATED: the selected configuration on the TEST split

The cap-100 baseline is read from outputs/phase5/ and outputs/phase5/ranking_v2/ and is never
rewritten. No cap above 1000 is accepted. Metrics reuse phase6_evaluate.metrics/evaluate_version.
Validation was already used in Phase 4 (rule set and thresholds), so validation scores are
optimistic; it is used here only to choose a cap, keeping the test split for the final check.
"""

from __future__ import annotations

import argparse
import builtins
import csv
import hashlib
import io
import json
import math
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from unittest import mock

import phase4_rule_evaluation as ev
import phase4_rule_mining as m
import phase5_predict as p5
import phase5_rank_v2 as v2
import phase5_ui_build as ui
import phase6_evaluate as p6

ROOT = Path(__file__).resolve().parent
NAME = "cap_experiment.py"
VERSION = "1.0.0"
CAPS = (100, 250, 500, 1000)
MAX_CAP = 1000
VERSIONS = ("v1", "v2")
APPROVAL_FLAG = "--i-approve-cap-test-evaluation"
RULE_FILE, SELECTION_FILE = "selection_rule.json", "selection.json"
VALID_FILES = {"positive": "data/valid.txt", "negative": "data/valid_negatives.txt"}

# Fixed before any validation result was produced (choice A1).
SELECTION_RULE = {
    "id": "A1",
    "objective": "maximise validation recall = TP / |validation positives| (equivalently TP: same denominator for every configuration)",
    "constraint": "Wilson 95% lower bound of validation benchmark precision TP/(TP+FP) >= "
                  "the same bound for the cap-100 configuration of the same ranking version, minus 0.05",
    "margin": 0.05,
    "wilson_z": 1.96,
    "reference": "cap-100 baseline of the same version (v1 -> outputs/phase5, v2 -> outputs/phase5/ranking_v2)",
    "ineligible": "configurations whose validation precision is undefined (no labelled predictions)",
    "tie_break": ["smaller cap", "v2 before v1"],
    "candidates": "caps 100, 250, 500, 1000 x versions v1, v2 (8 configurations)",
    "unlabelled_predictions": "not counted as false; they do not enter precision",
}


class CapExperimentError(RuntimeError):
    pass


# ----------------------------------------------------------------------- paths


def exp_dir(root: Path) -> Path:
    return root / "outputs" / "cap_experiment"


def config_dir(root: Path, cap: int, version: str, baseline_cap: int) -> Path:
    if cap == baseline_cap:
        return root / "outputs" / "phase5" / ("" if version == "v1" else "ranking_v2")
    return exp_dir(root) / f"cap_{cap}" / version


def config_key(cap: int, version: str) -> str:
    return f"cap{cap}_{version}"


def check_caps(caps: tuple[int, ...]) -> None:
    if list(caps) != sorted(set(caps)) or any(c < 1 or c > MAX_CAP for c in caps):
        raise CapExperimentError(f"caps must be increasing, unique and at most {MAX_CAP}: {caps}")


def baseline_cap_of(root: Path) -> int:
    manifest = json.loads((root / "outputs" / "phase5" / p5.MANIFEST_FILE).read_text(encoding="utf-8"))
    return manifest["settings"]["cap_per_relation"]


def canonical_sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ----------------------------------------------------------------- freeze rule


def freeze_rule(root: Path = ROOT) -> Path:
    out = exp_dir(root)
    if (out / "validation").exists() or (out / SELECTION_FILE).exists():
        raise CapExperimentError("validation results already exist; the rule can only be frozen before them")
    out.mkdir(parents=True, exist_ok=True)
    doc = {"tool": NAME, "version": VERSION, "frozen_at": now(), "rule": SELECTION_RULE,
           "rule_sha256": canonical_sha(SELECTION_RULE), "validation_results_existed": False}
    m._write_new(out / RULE_FILE, m._json(doc))
    return out / RULE_FILE


# -------------------------------------------------------------------- generate


def build_v2(root: Path, cap: int, v1_dir: Path) -> dict[str, Any]:
    """phase5_rank_v2.run, step for step, but compared with the v1 run of the SAME cap (v1_dir)."""
    v1_manifest = json.loads((v1_dir / p5.MANIFEST_FILE).read_text(encoding="utf-8"))
    for name, digest in v1_manifest["outputs"].items():
        if m.sha256_file(v1_dir / name) != digest:
            raise p5.Phase5Error(f"v1 file {name} does not match its manifest")
    if v1_manifest["settings"]["cap_per_relation"] != cap:
        raise CapExperimentError(f"{v1_dir} was built with cap {v1_manifest['settings']['cap_per_relation']}, not {cap}")
    started = time.time()
    state_before = v2.watched_state(root)

    triples, graph_info = p5.load_training_graph(root)
    rules, rule_info = p5.load_frozen_rules(root)
    if rule_info["rule_list"]["sha256"] != v1_manifest["inputs"]["rule_list"]["sha256"]:
        raise p5.Phase5Error("rule list differs from the one used for v1")
    if graph_info["phase2_graphml"]["sha256"] != v1_manifest["inputs"]["phase2_graphml"]["sha256"]:
        raise p5.Phase5Error("training graph differs from the one used for v1")
    entity_labels = m.p3.load_label_map(root / "data" / "entity_labels.json")
    relation_labels = m.p3.load_label_map(root / "data" / "relation_labels.json")
    vis_js, vis_css = p5.extract_vis_library(root / "outputs" / "phase2" / "interactive_graph.html")

    kg = m.KG(triples)
    rules_by_id = {r["rule_id"]: r for r in rules}
    candidates, counts = p5.generate_candidates(kg, rules)
    if counts != {k: v1_manifest["counts"][k] for k in counts}:
        raise p5.Phase5Error("candidate generation does not reproduce v1 counts")
    kept, per_relation, ties_v2, evidence = v2.rank_v2(kg, candidates, rules_by_id, cap)
    ties_v1 = v2.tie_stats_v1(kg, candidates, rules_by_id, cap)
    records = p5.build_records(kg, kept, candidates, rules_by_id, entity_labels, relation_labels)
    for rec in records:
        t = rec["triple"]
        key = (kg.eid[t["subject"]], t["relation"], kg.eid[t["object"]])
        distinct = {frozenset(tuple(x) for x in g) for sr in rec["supporting_rules"] for g in sr["body_groundings"]}
        if len(distinct) != evidence[key]:
            raise p5.Phase5Error(f"evidence count mismatch for {rec['prediction_id']}")
        rec["tie_break_values"] = {"max_pca_confidence": rec["tie_break_values"]["max_pca_confidence"],
                                   "distinct_body_matches": evidence[key],
                                   "supporting_rules": rec["tie_break_values"]["supporting_rules"]}
    train_set = set(triples)
    if any((r["triple"]["subject"], r["triple"]["relation"], r["triple"]["object"]) in train_set for r in records):
        raise p5.Phase5Error("a prediction is already a training triple")

    v1_records = json.loads((v1_dir / p5.PREDICTIONS_FILE).read_text(encoding="utf-8"))["predictions"]
    comparison = v2.compare(v1_records, records, ties_v1, ties_v2, per_relation, relation_labels)

    settings = {"rounds": p5.ROUND, "cap_per_relation": cap, "ranking_score": p5.RANKING_SCORE, "tie_break": v2.TIE_BREAK,
                "evidence_definition": "distinct sets of training triples that satisfy a supporting rule body for (x, z), "
                                       "deduplicated across rules; matches may share individual triples",
                "candidate_scope": "same as v1 (phase5_predict.generate_candidates)"}
    inputs = {**graph_info, **rule_info, "v1_manifest": {"path": m._rel(v1_dir / p5.MANIFEST_FILE, root),
                                                          "sha256": m.sha256_file(v1_dir / p5.MANIFEST_FILE)}}
    predictions_doc = {"phase": "5", "tool": v2.NAME, "version": v2.VERSION, "round": p5.ROUND, "settings": settings,
                       "note": "Same candidates as v1; only the tie-break changed. Not merged into training; not scored.",
                       "predictions": records}
    texts = {
        p5.PREDICTIONS_FILE: m._json(predictions_doc),
        p5.REPORT_FILE: p5.render_report(records, per_relation, counts, settings, inputs, relation_labels).replace(
            "# Phase 5: rule-based predictions (round 1)", "# Phase 5: rule-based predictions (round 1, ranking v2)"),
        p5.VIEWER_FILE: p5.render_viewer(records, vis_js, vis_css, relation_labels).replace(
            "Phase 5 rule-based predictions (round 1)", "Phase 5 rule-based predictions (round 1, ranking v2)"),
        v2.COMPARISON_FILE: v2.render_comparison(comparison, settings),
    }
    if v2.watched_state(root) != state_before:
        raise p5.Phase5Error("protected or v1 files changed during the rerun")
    manifest = {
        "phase": "5", "tool": v2.NAME, "version": v2.VERSION, "driver": f"{NAME} {VERSION}",
        "generated_at": now(), "runtime_seconds": round(time.time() - started, 1),
        "inputs": inputs, "settings": settings,
        "counts": {**counts, "retained_predictions": len(records), "per_relation": per_relation,
                   "changed_vs_v1": comparison["totals"]},
        "tie_stats_v1": ties_v1, "tie_stats_v2": ties_v2,
        "outputs": {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in texts.items()},
        "files_not_opened": "data/valid*, data/test* (size and mtime recorded only)",
        "protected_files": state_before, "protected_and_v1_files_unchanged": True,
        "scored_against_validation_or_test": False,
    }
    return {"texts": texts, "manifest": manifest}


def verify_v2_reproduces_baseline(root: Path, baseline_cap: int) -> None:
    """The driver must rebuild the existing cap-baseline v2 files byte for byte (checked in memory)."""
    built = build_v2(root, baseline_cap, root / "outputs" / "phase5")
    expected = json.loads((root / "outputs" / "phase5" / "ranking_v2" / p5.MANIFEST_FILE).read_text(encoding="utf-8"))["outputs"]
    if built["manifest"]["outputs"] != expected:
        raise CapExperimentError("v2 driver does not reproduce the baseline ranking_v2 outputs")


def generate(root: Path = ROOT, caps: tuple[int, ...] = CAPS) -> dict[str, Path]:
    check_caps(caps)
    base = baseline_cap_of(root)
    if caps[0] != base:
        raise CapExperimentError(f"first cap must be the existing baseline cap {base}")
    targets = [config_dir(root, c, v, base) for c in caps[1:] for v in VERSIONS]
    existing = [str(t) for t in targets if t.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(existing))
    baseline_before = baseline_state(root, base)
    verify_v2_reproduces_baseline(root, base)
    written = {}
    for cap in caps[1:]:
        d1, d2 = config_dir(root, cap, "v1", base), config_dir(root, cap, "v2", base)
        p5.run(root, d1, cap)
        built = build_v2(root, cap, d1)
        d2.mkdir(parents=True)
        for name, text in built["texts"].items():
            m._write_new(d2 / name, text)
        m._write_new(d2 / p5.MANIFEST_FILE, m._json(built["manifest"]))
        written[config_key(cap, "v1")], written[config_key(cap, "v2")] = d1, d2
    if baseline_state(root, base) != baseline_before:
        raise CapExperimentError("baseline files changed during generation")
    return written


def baseline_state(root: Path, base: int) -> dict[str, str]:
    return {m._rel(p, root): m.sha256_file(p) for v in VERSIONS for p in sorted(config_dir(root, base, v, base).glob("*"))
            if p.is_file()}


# -------------------------------------------------------------------- evaluate


@contextmanager
def test_files_blocked(root: Path):
    """Any attempt to open data/test* raises, so the validation step provably never reads them."""
    real_open = io.open
    blocked = (root / "data").resolve()

    def guarded(file, *args, **kwargs):
        p = Path(file) if isinstance(file, (str, Path)) else None
        if p is not None and p.name.startswith("test") and p.resolve().parent == blocked:
            raise CapExperimentError(f"validation step tried to open a test file: {p}")
        return real_open(file, *args, **kwargs)

    with mock.patch.object(builtins, "open", guarded), mock.patch.object(io, "open", guarded):
        yield


def load_validation(root: Path) -> tuple[dict[str, set], dict[str, Any]]:
    expected = json.loads((root / "outputs" / "phase3" / "phase3_manifest.json").read_text(encoding="utf-8"))["protected_files_sha256"]
    splits, info = {}, {}
    for key, rel in VALID_FILES.items():
        digest = m.sha256_file(root / rel)
        if expected.get(rel) != digest:
            raise CapExperimentError(f"{rel} hash does not match the Phase 3 manifest")
        triples = ev.read_split(root / rel)
        splits[key] = set(triples)
        if len(splits[key]) != len(triples):
            raise CapExperimentError(f"{rel} contains duplicate rows")
        info[key] = {"path": rel, "sha256": digest, "triples": len(triples)}
    if splits["positive"] & splits["negative"]:
        raise CapExperimentError("validation positives and negatives overlap")
    return splits, info


def load_config(root: Path, cap: int, version: str, base: int) -> tuple[dict[str, Any], dict[str, Any], Path]:
    d = config_dir(root, cap, version, base)
    doc, manifest = ui.load_version(d)  # checks every output hash against its manifest
    if manifest["settings"]["cap_per_relation"] != cap or doc["settings"]["cap_per_relation"] != cap:
        raise CapExperimentError(f"{d} is not a cap-{cap} run")
    return doc, manifest, d


def wilson_lower(tp: int, n: int, z: float = SELECTION_RULE["wilson_z"]) -> float | None:
    if n == 0:
        return None
    p = tp / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def apply_rule(overall: dict[str, dict[str, Any]], caps: tuple[int, ...]) -> dict[str, Any]:
    """overall: config key -> metrics (tp_matched_positives, fp_matched_supplied_negatives). Pure function."""
    rows = {}
    for cap in caps:
        for v in VERSIONS:
            o = overall[config_key(cap, v)]
            tp, fp = o["tp_matched_positives"], o["fp_matched_supplied_negatives"]
            rows[config_key(cap, v)] = {"cap": cap, "version": v, "tp": tp, "fp": fp, "precision_wilson_lower": wilson_lower(tp, tp + fp)}
    for r in rows.values():
        ref = rows[config_key(caps[0], r["version"])]["precision_wilson_lower"]
        r["reference_wilson_lower"] = ref
        r["threshold"] = None if ref is None else ref - SELECTION_RULE["margin"]
        r["eligible"] = r["precision_wilson_lower"] is not None and ref is not None and r["precision_wilson_lower"] >= r["threshold"] - 1e-12
    eligible = [k for k, r in rows.items() if r["eligible"]]
    if not eligible:
        raise CapExperimentError("no configuration satisfies the selection rule")
    best = max(eligible, key=lambda k: (rows[k]["tp"], -rows[k]["cap"], rows[k]["version"] == "v2"))
    return {"selected": best, "selected_cap": rows[best]["cap"], "selected_version": rows[best]["version"], "table": rows}


def rename_split_keys(obj: Any) -> Any:
    """phase6 metric names say 'test'; here the split is validation."""
    if isinstance(obj, dict):
        return {k.replace("test_positives", "split_positives").replace("test_negatives", "split_negatives"): rename_split_keys(v)
                for k, v in obj.items()}
    return obj


def validate(root: Path = ROOT, caps: tuple[int, ...] = CAPS) -> dict[str, Path]:
    check_caps(caps)
    out, vdir = exp_dir(root), exp_dir(root) / "validation"
    rule_doc = json.loads((out / RULE_FILE).read_text(encoding="utf-8")) if (out / RULE_FILE).is_file() else None
    if rule_doc is None:
        raise CapExperimentError(f"run `py {NAME} freeze-rule` first: the selection rule must exist before validation")
    if rule_doc["rule"] != SELECTION_RULE or rule_doc["rule_sha256"] != canonical_sha(SELECTION_RULE):
        raise CapExperimentError("frozen selection rule differs from the rule in this script")
    if vdir.exists() or (out / SELECTION_FILE).exists():
        raise FileExistsError(f"Refusing to overwrite {vdir} / {out / SELECTION_FILE}")
    base = baseline_cap_of(root)
    if caps[0] != base:
        raise CapExperimentError(f"first cap must be the existing baseline cap {base}")
    with test_files_blocked(root):
        splits, split_info = load_validation(root)
        train = set(p5.load_training_graph(root)[0])
        leakage = {k: len(s & train) for k, s in splits.items()}
        if any(leakage.values()):
            raise CapExperimentError(f"validation triples found in the training graph: {leakage}")
        p6_splits = {"test_positive": splits["positive"], "test_negative": splits["negative"],
                     "valid_positive": set(), "valid_negative": set()}
        configs, rel_rows, inputs = {}, [], {}
        for cap in caps:
            for v in VERSIONS:
                doc, manifest, d = load_config(root, cap, v, base)
                res = p6.evaluate_version(doc["predictions"], p6_splits)
                key = config_key(cap, v)
                overall = rename_split_keys(res["overall"])
                overall.pop("unlabelled_annotations", None)
                tp, fp = overall["tp_matched_positives"], overall["fp_matched_supplied_negatives"]
                overall["precision_wilson95_lower"] = None if tp + fp == 0 else round(wilson_lower(tp, tp + fp), 6)
                configs[key] = {"cap": cap, "version": v, "path": m._rel(d, root), "overall": overall,
                                "candidates_total": manifest["counts"]["unique_candidate_triples"],
                                "relations_still_capped": sum(1 for r in manifest["counts"]["per_relation"].values() if r["candidates"] > cap),
                                "per_relation": rename_split_keys(res["per_relation"])}
                inputs[key] = {"predictions_sha256": m.sha256_file(d / p5.PREDICTIONS_FILE),
                               "manifest_sha256": m.sha256_file(d / p5.MANIFEST_FILE)}
                for rel, mt in configs[key]["per_relation"].items():
                    rel_rows.append([key, cap, v, rel] + list(mt.values()))
    selection = apply_rule({k: c["overall"] for k, c in configs.items()}, caps)
    results = {"split": "validation", "status": "complete", "generated_at": now(), "caps": list(caps),
               "selection_rule": SELECTION_RULE, "selection_rule_sha256": rule_doc["rule_sha256"],
               "note": "Validation was used in Phase 4 (rule set and thresholds); these scores are optimistic and are used "
                       "only to choose a configuration. Unlabelled predictions are not counted as false.",
               "splits": split_info, "leakage_check": leakage, "configs": configs}
    texts = {
        "validation_results.json": m._json(results),
        "per_relation_metrics.csv": _csv([["config", "cap", "version", "relation"] +
                                          list(rename_split_keys(p6.metrics(set(), set(), set())).keys())] + rel_rows),
    }
    sel_doc = {"tool": NAME, "version": VERSION, "selected_at": now(), "rule_file": f"outputs/cap_experiment/{RULE_FILE}",
               "rule_sha256": rule_doc["rule_sha256"], "rule_frozen_at": rule_doc["frozen_at"], **selection,
               "selected_path": configs[selection["selected"]]["path"],
               "selected_predictions_sha256": inputs[selection["selected"]]["predictions_sha256"],
               "validation_results_sha256": hashlib.sha256(texts["validation_results.json"].encode("utf-8")).hexdigest()}
    manifest = {"tool": NAME, "version": VERSION, "generated_at": results["generated_at"], "inputs": inputs,
                "splits": split_info, "outputs": {k: hashlib.sha256(t.encode("utf-8")).hexdigest() for k, t in texts.items()},
                "test_files_opened": False, "predictions_changed": False}
    vdir.mkdir(parents=True)
    for name, text in texts.items():
        m._write_new(vdir / name, text)
    m._write_new(vdir / "validation_manifest.json", m._json(manifest))
    m._write_new(out / SELECTION_FILE, m._json(sel_doc))
    m._write_new(out / "cap_experiment_report.md", render_report(results, sel_doc))
    return {"validation": vdir / "validation_results.json", "selection": out / SELECTION_FILE}


def _csv(rows: list[list[Any]]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.2f}%"


def render_report(results: dict[str, Any], sel: dict[str, Any]) -> str:
    L = ["# Cap experiment — validation comparison and selection", "",
         f"Generated {results['generated_at']} by `{NAME}` from the files listed in `validation/validation_manifest.json`.", "",
         "**Split: validation.** Validation was already used in Phase 4, so these numbers are optimistic. "
         "Benchmark precision covers only predictions found in the validation positives or validation negatives; "
         "unlabelled predictions are not counted as false.", "",
         "## Selection rule (frozen before validation)", "",
         f"- Rule `{SELECTION_RULE['id']}`, frozen at {sel['rule_frozen_at']} (sha256 `{sel['rule_sha256'][:12]}…`).",
         f"- Objective: {SELECTION_RULE['objective']}.", f"- Constraint: {SELECTION_RULE['constraint']}.",
         f"- Ties: {', then '.join(SELECTION_RULE['tie_break'])}.", "",
         "## Validation results", "",
         "| Config | Predictions | Val. positives matched (TP) | Val. negatives matched (FP) | Unlabelled | Precision | Precision 95% lower | Recall | F1 | Positive hit rate | Eligible |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, c in results["configs"].items():
        o, t = c["overall"], sel["table"][key]
        L.append(f"| {key} | {o['predictions']:,} | {o['tp_matched_positives']} | {o['fp_matched_supplied_negatives']} | "
                 f"{o['unlabelled_predictions']:,} | {_pct(o['precision'])} | {_pct(o['precision_wilson95_lower'])} | {_pct(o['recall'])} | "
                 f"{_pct(o['f1'])} | {_pct(o['positive_hit_rate'])} | {'yes' if t['eligible'] else 'no'} |")
    L += ["", f"**Selected: `{sel['selected']}`** (cap {sel['selected_cap']}, {sel['selected_version']}).", "",
          "## Test evaluation", "",
          "- Previous test evaluation (cap 100, v1 and v2): `outputs/phase6/evaluation_test/` (Phase 6, unchanged).",
          f"- Final test evaluation of the selected configuration: gated — `py {NAME} test {APPROVAL_FLAG}`. "
          "It is a second use of the test split and must not lead to further changes.", "",
          "## Notes", "",
          "- `prediction_report.md` files for caps 250/500/1000 come from the unchanged Phase 5 renderer; its fixed sentence "
          "\"the cap keeps only the top 100 per relation\" refers to the baseline — the actual cap is in each manifest's settings.",
          "- Recall is bounded by each cap and by relations without rules; precision is only over labelled predictions.", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ gated test


def test_evaluation(root: Path = ROOT, approved: bool = False) -> dict[str, Path]:
    if not approved:
        raise PermissionError(f"The cap test evaluation is gated: pass {APPROVAL_FLAG} after approving it")
    out, tdir = exp_dir(root), exp_dir(root) / "test_final"
    if tdir.exists():
        raise FileExistsError(f"Refusing to overwrite {tdir}")
    sel = json.loads((out / SELECTION_FILE).read_text(encoding="utf-8"))
    vtext = (out / "validation" / "validation_results.json").read_text(encoding="utf-8")
    if hashlib.sha256(vtext.encode("utf-8")).hexdigest() != sel["validation_results_sha256"]:
        raise CapExperimentError("validation results changed after selection")
    base = baseline_cap_of(root)
    doc, manifest, d = load_config(root, sel["selected_cap"], sel["selected_version"], base)
    if m.sha256_file(d / p5.PREDICTIONS_FILE) != sel["selected_predictions_sha256"]:
        raise CapExperimentError("selected predictions changed after selection")
    splits, split_info = p6.load_splits(root)
    train = set(p5.load_training_graph(root)[0])
    leakage = {k: len(v & train) for k, v in splits.items()}
    if any(leakage.values()):
        raise CapExperimentError(f"split triples found in the training graph: {leakage}")
    res = p6.evaluate_version(doc["predictions"], splits)
    baseline_path = root / "outputs" / "phase6" / "evaluation_test" / "evaluation_results.json"
    results = {"split": "test", "status": "complete", "generated_at": now(), "selected": sel["selected"],
               "selected_cap": sel["selected_cap"], "selected_version": sel["selected_version"], "selected_path": m._rel(d, root),
               "note": "Second use of the test split (the first was Phase 6, cap 100). The configuration was chosen on "
                       "validation with a rule frozen beforehand; nothing may be tuned on these numbers.",
               "overall": res["overall"], "per_relation": res["per_relation"], "labels": res["labels"],
               "baseline_test_evaluation": ({"path": m._rel(baseline_path, root), "sha256": m.sha256_file(baseline_path)}
                                            if baseline_path.is_file() else None),
               "splits": split_info, "leakage_check": leakage}
    texts = {"test_results.json": m._json(results),
             "per_relation_metrics.csv": _csv([["relation"] + list(p6.metrics(set(), set(), set()).keys())] +
                                              [[rel] + list(mt.values()) for rel, mt in res["per_relation"].items()])}
    manifest_doc = {"tool": NAME, "version": VERSION, "generated_at": results["generated_at"], "approved_by_flag": APPROVAL_FLAG,
                    "selection_sha256": m.sha256_file(out / SELECTION_FILE), "predictions_sha256": sel["selected_predictions_sha256"],
                    "outputs": {k: hashlib.sha256(t.encode("utf-8")).hexdigest() for k, t in texts.items()}}
    tdir.mkdir(parents=True)
    for name, text in texts.items():
        m._write_new(tdir / name, text)
    m._write_new(tdir / "test_manifest.json", m._json(manifest_doc))
    return {"test": tdir / "test_results.json"}


# ------------------------------------------------------------------------- CLI


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["freeze-rule", "generate", "validate", "test"])
    parser.add_argument(APPROVAL_FLAG, dest="approved", action="store_true", help="required for the test step")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.step == "freeze-rule":
        print(freeze_rule(ROOT))
    elif args.step == "generate":
        for k, p in generate(ROOT).items():
            print(f"{k}: {p}")
    elif args.step == "validate":
        for k, p in validate(ROOT).items():
            print(f"{k}: {p}")
    else:
        if not args.approved:
            print(f"Not run. The test step is gated: re-run with {APPROVAL_FLAG} after approval.")
            return 2
        for k, p in test_evaluation(ROOT, approved=True).items():
            print(f"{k}: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
