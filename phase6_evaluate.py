"""Phase 6: label the frozen Phase 5 predictions against the held-out TEST split.

GATED. Nothing is read from the split files unless the command line contains
``--i-approve-phase6-test-evaluation``. Without it the script prints the
protocol summary and exits with status 2. The UI never runs this script.

Protocol (see outputs/phase6/phase6_protocol.md):

* Predictions: the existing v1 and v2 files (3,239 each), unchanged. Both were
  generated from the training graph only, with rules mined from training only.
* Each prediction is labelled exactly once:
    test_positive  - the triple is in data/test.txt
    test_negative  - the triple is in data/test_negatives.txt (supplied negatives)
    unlabelled     - in neither file. NOT treated as false. It is annotated (for
                     information only) if it appears in data/valid.txt or
                     data/valid_negatives.txt.
* Benchmark-universe metrics use U = test positives ∪ supplied test negatives:
    TP = predictions in test positives, FP = predictions in test negatives,
    FN = test positives not predicted, TN = test negatives not predicted.
    precision = TP/(TP+FP), recall = TP/|test positives|, F1, specificity = TN/|test negatives|.
  Unlabelled predictions are outside U and are reported separately.
* Prediction-side rates use all predictions as the denominator:
    labelled_coverage = (TP+FP)/|predictions|, positive_hit_rate = TP/|predictions|.
* recall_ceiling = Σ_r min(|predictions_r|, |test positives_r|) / |test positives|
  (the 100-per-relation cap bounds recall).

Thresholds, rules and rankings are not changed; validation data is not used to tune anything.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import phase4_rule_evaluation as ev
import phase4_rule_mining as m
import phase5_predict as p5
import phase5_ui_build as ui

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs" / "phase6" / "evaluation_test"
APPROVAL_FLAG = "--i-approve-phase6-test-evaluation"
NAME = "phase6_evaluate.py"
VERSION = "6.0.1"
SPLIT_FILES = {
    "test_positive": "data/test.txt",
    "test_negative": "data/test_negatives.txt",
    "valid_positive": "data/valid.txt",
    "valid_negative": "data/valid_negatives.txt",
}
RESULT_FILES = ("evaluation_results.json", "evaluation_results.js", "predictions_labelled.csv",
                "per_relation_metrics.csv", "evaluation_manifest.json")


class Phase6Error(RuntimeError):
    pass


def _div(a: float, b: float) -> float | None:
    return None if b == 0 else round(a / b, 6)


def metrics(pred: set, pos: set, neg: set) -> dict[str, Any]:
    tp, fp = len(pred & pos), len(pred & neg)
    unl = len(pred) - tp - fp
    fn, tn = len(pos) - tp, len(neg) - fp
    precision, recall = _div(tp, tp + fp), _div(tp, len(pos))
    # F1 from counts (2TP / (2TP+FP+FN)); 0.0 when TP = 0, None only when P or R is undefined.
    f1 = None if precision is None or recall is None else _div(2 * tp, 2 * tp + fp + fn)
    return {
        "predictions": len(pred), "test_positives": len(pos), "test_negatives": len(neg),
        "tp_matched_positives": tp, "fp_matched_supplied_negatives": fp, "unlabelled_predictions": unl,
        "fn_unpredicted_positives": fn, "tn_unpredicted_negatives": tn,
        "precision": precision, "recall": recall, "f1": f1, "specificity": _div(tn, len(neg)),
        "labelled_coverage": _div(tp + fp, len(pred)), "positive_hit_rate": _div(tp, len(pred)),
    }


def evaluate_version(records: list[dict[str, Any]], splits: dict[str, set]) -> dict[str, Any]:
    pos, neg = splits["test_positive"], splits["test_negative"]
    pred = {(r["triple"]["subject"], r["triple"]["relation"], r["triple"]["object"]) for r in records}
    if len(pred) != len(records):
        raise Phase6Error("duplicate predictions in a version")
    overall = metrics(pred, pos, neg)
    rels = sorted({t[1] for t in pred} | {t[1] for t in pos} | {t[1] for t in neg}, key=lambda r: int(r[1:]))
    per_relation, ceiling = {}, 0
    for rel in rels:
        p_r = {t for t in pred if t[1] == rel}
        pos_r = {t for t in pos if t[1] == rel}
        per_relation[rel] = metrics(p_r, pos_r, {t for t in neg if t[1] == rel})
        ceiling += min(len(p_r), len(pos_r))
    overall["recall_ceiling_under_cap"] = _div(ceiling, len(pos))
    labels = []
    for r in records:
        t = (r["triple"]["subject"], r["triple"]["relation"], r["triple"]["object"])
        label = "test_positive" if t in pos else "test_negative" if t in neg else "unlabelled"
        note = "valid_positive" if t in splits["valid_positive"] else "valid_negative" if t in splits["valid_negative"] else ""
        labels.append([r["prediction_id"], label, note if label == "unlabelled" else ""])
    unl_notes = Counter(n for _, l, n in labels if l == "unlabelled")
    overall["unlabelled_annotations"] = {"in_valid_positives": unl_notes["valid_positive"],
                                         "in_valid_negatives": unl_notes["valid_negative"],
                                         "in_neither": unl_notes[""]}
    return {"overall": overall, "per_relation": per_relation, "labels": labels}


def load_splits(root: Path) -> tuple[dict[str, set], dict[str, Any]]:
    p3_manifest = json.loads((root / "outputs" / "phase3" / "phase3_manifest.json").read_text(encoding="utf-8"))
    expected = p3_manifest["protected_files_sha256"]
    splits, info = {}, {}
    for key, rel in SPLIT_FILES.items():
        path = root / rel
        digest = m.sha256_file(path)
        if expected.get(rel) != digest:
            raise Phase6Error(f"{rel} hash does not match the Phase 3 manifest")
        triples = ev.read_split(path)
        splits[key] = set(triples)
        if len(splits[key]) != len(triples):
            raise Phase6Error(f"{rel} contains duplicate rows")
        info[key] = {"path": rel, "sha256": digest, "triples": len(triples)}
    if splits["test_positive"] & splits["test_negative"]:
        raise Phase6Error("test positives and supplied negatives overlap")
    return splits, info


def run(root: Path = ROOT, out_dir: Path | None = None, approved: bool = False) -> dict[str, Path]:
    if not approved:
        raise PermissionError(f"Phase 6 evaluation is gated: pass {APPROVAL_FLAG} after approving the protocol")
    out_dir = out_dir or root / "outputs" / "phase6" / "evaluation_test"
    existing = [str(out_dir / n) for n in RESULT_FILES if (out_dir / n).exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(existing))
    state_before = ui.protected_state(root)
    versions = {}
    for name, dir_ in (("v1", root / "outputs" / "phase5"), ("v2", root / "outputs" / "phase5" / "ranking_v2")):
        doc, manifest = ui.load_version(dir_)
        versions[name] = {"doc": doc, "manifest_sha256": m.sha256_file(dir_ / p5.MANIFEST_FILE),
                          "predictions_sha256": m.sha256_file(dir_ / p5.PREDICTIONS_FILE)}
    train_triples, graph_info = p5.load_training_graph(root)
    splits, split_info = load_splits(root)
    train = set(train_triples)
    leakage = {k: len(v & train) for k, v in splits.items()}
    if any(leakage.values()):
        raise Phase6Error(f"split triples found in the training graph: {leakage}")

    results = {"status": "complete", "split": "test", "protocol": __doc__, "versions": {}}
    csv_rows = []
    for name, v in versions.items():
        res = evaluate_version(v["doc"]["predictions"], splits)
        results["versions"][name] = {"overall": res["overall"], "per_relation": res["per_relation"], "labels": res["labels"]}
        by_pid = {r["prediction_id"]: r for r in v["doc"]["predictions"]}
        for pid, label, note in res["labels"]:
            r = by_pid[pid]
            csv_rows.append([name, pid, r["triple"]["subject"], r["labels"]["subject"], r["triple"]["relation"],
                             r["labels"]["relation"], r["triple"]["object"], r["labels"]["object"],
                             r["ranking_score"]["value"], r["relation_rank"], len(r["supporting_rules"]), label, note])
    a, b = results["versions"]["v1"]["overall"], results["versions"]["v2"]["overall"]
    results["comparison"] = {k: {"v1": a[k], "v2": b[k]} for k in
                             ("tp_matched_positives", "fp_matched_supplied_negatives", "unlabelled_predictions",
                              "precision", "recall", "f1", "labelled_coverage", "positive_hit_rate")}
    results["inputs"] = {"splits": split_info, **graph_info,
                         **{f"{n}_predictions_sha256": v["predictions_sha256"] for n, v in versions.items()},
                         **{f"{n}_manifest_sha256": v["manifest_sha256"] for n, v in versions.items()}}
    results["leakage_check"] = {"split_triples_in_training_graph": leakage}
    results["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    header = ["version", "prediction_id", "subject", "subject_label", "relation", "relation_label", "object", "object_label",
              "score", "rank_in_relation", "supporting_rules", "test_label", "unlabelled_annotation"]
    pred_csv = _csv([header] + csv_rows)
    rel_header = ["version", "relation"] + list(metrics(set(), set(), set()).keys())
    rel_rows = [[n, rel] + list(mt.values()) for n in ("v1", "v2") for rel, mt in results["versions"][n]["per_relation"].items()]
    rel_csv = _csv([rel_header] + rel_rows)
    results_json = m._json(results)
    results_js = "window.PHASE6_RESULTS = " + json.dumps(results, ensure_ascii=False, sort_keys=True).replace("</", "<\\/") + ";\n"
    if ui.protected_state(root) != state_before:
        raise Phase6Error("protected files changed during evaluation")
    texts = {"evaluation_results.json": results_json, "evaluation_results.js": results_js,
             "predictions_labelled.csv": pred_csv, "per_relation_metrics.csv": rel_csv}
    manifest = {"tool": NAME, "version": VERSION, "generated_at": results["generated_at"], "approved_by_flag": APPROVAL_FLAG,
                "inputs": results["inputs"], "outputs": {k: hashlib.sha256(t.encode("utf-8")).hexdigest() for k, t in texts.items()},
                "protected_files_unchanged": True, "predictions_changed": False, "thresholds_changed": False}
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        m._write_new(out_dir / name, text)
    m._write_new(out_dir / "evaluation_manifest.json", m._json(manifest))
    return {name: out_dir / name for name in RESULT_FILES}


def _csv(rows: list[list[Any]]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(APPROVAL_FLAG, dest="approved", action="store_true", help="required to read the test split")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.approved:
        print(__doc__)
        print(f"Not run. Re-run with {APPROVAL_FLAG} after approving outputs/phase6/phase6_protocol.md.")
        return 2
    for name, path in run(ROOT, approved=True).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
