"""Phase 4B: score a frozen Phase 4 rule set on the validation split only.

Reads ``selected_rules.json`` from a mining run (refusing to run if its hash
differs from ``mining_manifest.json``), the Phase 3 training graph, and
``data/valid.txt`` / ``data/valid_negatives.txt``. Test files are never opened.

For each rule it counts validation positives and supplied validation negatives
whose (x, z) pair the rule body covers in the training graph. A small declared
grid of stricter thresholds is scored by F1 of "some rule covers this triple"
on positives versus negatives; the chosen thresholds give the validated rule
set. Rules are never re-mined here, and no new edges are listed or written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import phase3_ontology as p3
import phase4_rule_mining as m


ROOT = m.ROOT
VALID_PATH = ROOT / "data" / "valid.txt"
VALID_NEGATIVES_PATH = ROOT / "data" / "valid_negatives.txt"
EVALUATOR_NAME = "phase4_rule_evaluation.py"
EVALUATOR_VERSION = "4B.2.0"

GRID_MIN_PCA = (0.10, 0.20, 0.30, 0.50)
GRID_MIN_SUPPORT = (10, 20, 50)
STAT_ONLY_FOR_EVALUATOR = ("data/test",)

EVALUATION_JSON = "validation_evaluation.json"
EVALUATION_MD = "validation_evaluation.md"
VALIDATED_SET = "validated_rule_set.json"


def read_split(path: Path) -> list[tuple[str, str, str]]:
    """Strictly parse a tab-separated triple file (fails on any malformed row)."""
    triples = []
    for line_number, row in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        fields = row.split("\t")
        if (
            len(fields) != 3
            or not p3.ENTITY_ID_PATTERN.fullmatch(fields[0])
            or not p3.RELATION_ID_PATTERN.fullmatch(fields[1])
            or not p3.ENTITY_ID_PATTERN.fullmatch(fields[2])
        ):
            raise m.Phase4Error(f"{path} line {line_number}: malformed row {row!r}")
        triples.append((fields[0], fields[1], fields[2]))
    return triples


def shape_from_body(body: list[list[str]]) -> tuple:
    if len(body) == 1:
        (p, a, b), = body
        if (a, b) == ("x", "z"):
            return ("1", p, "f")
        if (a, b) == ("z", "x"):
            return ("1", p, "b")
    elif len(body) == 2:
        (p1, a1, b1), (p2, a2, b2) = body
        d1 = {"xy": "f", "yx": "b"}.get(a1 + b1)
        d2 = {"yz": "f", "zy": "b"}.get(a2 + b2)
        if d1 and d2:
            return ("2", p1, d1, p2, d2)
    raise m.Phase4Error(f"unsupported rule body {body}")


def _f1(tp: int, fp: int, positives: int) -> dict[str, Any]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / positives if positives else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": positives - tp, "precision": m._r(precision), "recall": m._r(recall), "f1": m._r(f1)}


def coverage(kg: m.KG, rules: list[dict[str, Any]], triples: list[tuple[str, str, str]]) -> tuple[dict[str, set[int]], int]:
    """rule_id -> indices of triples whose pair the rule body covers; plus unreachable count."""
    by_head: dict[str, list[tuple[int, int, int]]] = {}
    unreachable = 0
    for index, (s, r, o) in enumerate(triples):
        if s in kg.eid and o in kg.eid:
            by_head.setdefault(r, []).append((index, kg.eid[s], kg.eid[o]))
        else:
            unreachable += 1
    hits = {}
    for rule in rules:
        shape = shape_from_body(rule["body"])
        hits[rule["rule_id"]] = {
            index for index, x, z in by_head.get(rule["head"], []) if m.body_holds(kg, shape, x, z)
        }
    return hits, unreachable


def score_grid(
    rules: list[dict[str, Any]],
    pos_hits: dict[str, set[int]],
    neg_hits: dict[str, set[int]],
    n_positives: int,
    grid_min_pca: Iterable[float],
    grid_min_support: Iterable[int],
) -> list[dict[str, Any]]:
    """TP/FP/precision/recall/F1 of 'covered by at least one rule' at each grid point."""
    grid = []
    for min_pca in grid_min_pca:
        for min_support in grid_min_support:
            subset = [r for r in rules if r["pca_confidence"] >= min_pca and r["support"] >= min_support]
            tp_set: set[int] = set().union(*(pos_hits[r["rule_id"]] for r in subset)) if subset else set()
            fp_set: set[int] = set().union(*(neg_hits[r["rule_id"]] for r in subset)) if subset else set()
            grid.append({"min_pca": min_pca, "min_support": min_support, "rules": len(subset), **_f1(len(tp_set), len(fp_set), n_positives)})
    return grid


def rule_ids_by_rank(run_dir: Path, ranks: Iterable[int]) -> dict[int, dict[str, str]]:
    """Read-only lookup of rule IDs/texts by global rank in a mining run."""
    rules = json.loads((run_dir / m.SELECTED_FILE).read_text(encoding="utf-8"))["rules"]
    by_rank = {r["global_rank"]: r for r in rules}
    missing = [k for k in ranks if k not in by_rank]
    if missing:
        raise m.Phase4Error(f"ranks not found in {run_dir}: {missing}")
    return {k: {"rule_id": by_rank[k]["rule_id"], "rule": by_rank[k]["rule"]} for k in ranks}


def evaluate(
    run_dir: Path,
    valid_path: Path = VALID_PATH,
    valid_negatives_path: Path = VALID_NEGATIVES_PATH,
    phase3_dir: Path = m.PHASE3_DIR,
    train_path: Path = m.TRAIN_PATH,
    root: Path = ROOT,
    grid_min_pca: Iterable[float] = GRID_MIN_PCA,
    grid_min_support: Iterable[int] = GRID_MIN_SUPPORT,
    exclude_rule_ids: Iterable[str] = (),
) -> dict[str, Path]:
    grid_min_pca, grid_min_support = tuple(sorted(grid_min_pca)), tuple(sorted(grid_min_support))
    exclude_rule_ids = sorted(set(exclude_rule_ids))
    targets = {"json": run_dir / EVALUATION_JSON, "md": run_dir / EVALUATION_MD, "validated": run_dir / VALIDATED_SET}
    existing = [str(p) for p in targets.values() if p.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(existing))

    manifest = json.loads((run_dir / m.MANIFEST_FILE).read_text(encoding="utf-8"))
    selected_bytes = (run_dir / m.SELECTED_FILE).read_bytes()
    selected_sha = hashlib.sha256(selected_bytes).hexdigest()
    if selected_sha != manifest["outputs"][m.SELECTED_FILE]:
        raise m.Phase4Error("selected_rules.json does not match the mining manifest; rules must stay frozen")
    selected = json.loads(selected_bytes.decode("utf-8"))

    state_before = m.protected_state(root, STAT_ONLY_FOR_EVALUATOR)
    triples, inputs = m.load_training_triples(phase3_dir, train_path)
    if inputs["phase3_trig"]["sha256"] != manifest["inputs"]["phase3_trig"]["sha256"]:
        raise m.Phase4Error("Phase 3 training graph changed since mining")
    kg = m.KG(triples)
    positives = read_split(valid_path)
    negatives = read_split(valid_negatives_path)
    rules = selected["rules"]

    pos_hits, pos_unreachable = coverage(kg, rules, positives)
    neg_hits, neg_unreachable = coverage(kg, rules, negatives)

    per_rule = []
    for rule in rules:
        rid = rule["rule_id"]
        vh, vn = len(pos_hits[rid]), len(neg_hits[rid])
        unknown = rule["unknown_head_pairs_count"]
        per_rule.append(
            {
                "rule_id": rid, "rule": rule["rule"], "head": rule["head"], "type": rule["type"],
                "support": rule["support"], "pca_confidence": rule["pca_confidence"], "wilson_lower": rule["wilson_lower"],
                "val_hits": vh, "val_neg_hits": vn,
                "val_precision_lower_bound": m._r(vh / unknown) if unknown else None,
                "pos_neg_ratio": m._r((vh + 1) / (vn + 1)),
            }
        )

    grid = score_grid(rules, pos_hits, neg_hits, len(positives), grid_min_pca, grid_min_support)
    kept = [r for r in rules if r["rule_id"] not in set(exclude_rule_ids)]
    grid_excluded = score_grid(kept, pos_hits, neg_hits, len(positives), grid_min_pca, grid_min_support) if exclude_rule_ids else None
    chosen = max(grid, key=lambda g: (g["f1"], g["min_pca"], g["min_support"]))
    chosen_rules = [r for r in rules if r["pca_confidence"] >= chosen["min_pca"] and r["support"] >= chosen["min_support"]]

    heads = sorted({r["head"] for r in rules})
    per_head = {}
    for h in heads:
        h_rules = [r["rule_id"] for r in chosen_rules if r["head"] == h]
        cov_pos = set().union(*(pos_hits[i] for i in h_rules)) if h_rules else set()
        cov_neg = set().union(*(neg_hits[i] for i in h_rules)) if h_rules else set()
        per_head[h] = {
            "rules": len(h_rules),
            "valid_positives": sum(1 for _, r, _ in positives if r == h),
            "valid_negatives": sum(1 for _, r, _ in negatives if r == h),
            "positives_covered": len(cov_pos),
            "negatives_covered": len(cov_neg),
        }

    state_after = m.protected_state(root, STAT_ONLY_FOR_EVALUATOR)
    if state_after != state_before:
        raise m.Phase4Error("protected files changed during evaluation")
    if hashlib.sha256((run_dir / m.SELECTED_FILE).read_bytes()).hexdigest() != selected_sha:
        raise m.Phase4Error("selected_rules.json changed during evaluation")

    inputs_doc = {
        "selected_rules": {"path": m._rel(run_dir / m.SELECTED_FILE, root), "sha256": selected_sha},
        "validation_positives": {"path": m._rel(valid_path, root), "sha256": m.sha256_file(valid_path), "triples": len(positives)},
        "validation_negatives": {"path": m._rel(valid_negatives_path, root), "sha256": m.sha256_file(valid_negatives_path), "triples": len(negatives)},
        "training": inputs,
    }
    evaluation = {
        "phase": "4B-validation",
        "evaluator": EVALUATOR_NAME,
        "evaluator_version": EVALUATOR_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": inputs_doc,
        "files_not_opened": "data/test* (size and mtime recorded only)",
        "selection_objective": "F1 of 'covered by at least one rule' on validation positives vs supplied validation negatives; ties -> stricter",
        "grid_min_pca": list(grid_min_pca),
        "grid_min_support": list(grid_min_support),
        "grid": grid,
        "chosen": chosen,
        "chosen_note": "argmax F1 over the grid (ties -> stricter); adoption against a baseline is decided separately (phase4_compare_runs.py)",
        "excluded_rule_ids": exclude_rule_ids,
        "excluded_rule_ids_present_in_run": sorted(set(exclude_rule_ids) & {r["rule_id"] for r in rules}),
        "grid_without_excluded_rules": grid_excluded,
        "unreachable": {"positives": pos_unreachable, "negatives": neg_unreachable},
        "per_head_with_chosen_thresholds": per_head,
        "per_rule": per_rule,
        "notes": [
            "Validation precision is a lower bound: validation holds only a sample of true facts.",
            "Supplied negatives were not independently verified (Phase 1).",
            "Only counts are reported; no uncovered or new pairs are listed.",
            "Test files were not opened.",
        ],
        "protected_files": state_before,
    }
    validated = {
        "phase": "4B-validated-rule-set",
        "thresholds_chosen_on_validation": {"min_pca": chosen["min_pca"], "min_support": chosen["min_support"]},
        "mining_config": selected["config"],
        "source_selected_rules_sha256": selected_sha,
        "training_snapshot": selected["training_snapshot"],
        "note": "Rule subset chosen on validation; still statistical patterns, not semantic claims. Test split untouched.",
        "rules": [{"rule_id": r["rule_id"], "rule": r["rule"], "display": r["display"], "head": r["head"], "type": r["type"]} for r in chosen_rules],
    }
    md = render_markdown(evaluation, chosen_rules, per_rule)

    m._write_new(targets["json"], m._json(evaluation))
    m._write_new(targets["validated"], m._json(validated))
    m._write_new(targets["md"], md)
    return targets


def render_markdown(evaluation: dict[str, Any], chosen_rules: list[dict[str, Any]], per_rule: list[dict[str, Any]]) -> str:
    chosen = evaluation["chosen"]
    lines = [
        "# Phase 4B: Validation scoring of frozen rules",
        "",
        f"Rules: `{evaluation['inputs']['selected_rules']['path']}` (SHA-256 `{evaluation['inputs']['selected_rules']['sha256']}`), frozen before this step.",
        f"Validation: {evaluation['inputs']['validation_positives']['triples']:,} positives, "
        f"{evaluation['inputs']['validation_negatives']['triples']:,} supplied negatives. Test files were not opened.",
        "",
        "Rules were not re-mined. Validation only scores the frozen rules at the grid points below.",
        "",
        "## Threshold grid",
        "",
        "| min_pca | min_support | Rules | TP | FP | Precision | Recall | F1 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for g in evaluation["grid"]:
        mark = " **(chosen)**" if g is chosen or g == chosen else ""
        lines.append(f"| {g['min_pca']} | {g['min_support']} | {g['rules']} | {g['tp']:,} | {g['fp']:,} | {g['precision']:.3f} | {g['recall']:.3f} | {g['f1']:.3f}{mark} |")
    if evaluation.get("grid_without_excluded_rules"):
        lines += [
            "",
            f"### Same grid without the {len(evaluation['excluded_rule_ids'])} excluded rules "
            f"({len(evaluation['excluded_rule_ids_present_in_run'])} present in this run)",
            "",
            "| min_pca | min_support | Rules | TP | FP | Precision | Recall | F1 |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for g in evaluation["grid_without_excluded_rules"]:
            lines.append(f"| {g['min_pca']} | {g['min_support']} | {g['rules']} | {g['tp']:,} | {g['fp']:,} | {g['precision']:.3f} | {g['recall']:.3f} | {g['f1']:.3f} |")
    lines += [
        "",
        f"Arg-max F1 point (not an adoption decision): `min_pca = {chosen['min_pca']}`, `min_support = {chosen['min_support']}` → {len(chosen_rules)} rules.",
        f"Validation triples with an entity unseen in training (no rule can reach them): "
        f"{evaluation['unreachable']['positives']:,} positives, {evaluation['unreachable']['negatives']:,} negatives.",
        "",
        "## Per head relation (chosen thresholds)",
        "",
        "| Head | Rules | Valid + | Covered + | Valid − | Covered − |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for h, v in evaluation["per_head_with_chosen_thresholds"].items():
        lines.append(f"| {h} | {v['rules']} | {v['valid_positives']:,} | {v['positives_covered']:,} | {v['valid_negatives']:,} | {v['negatives_covered']:,} |")
    lines += [
        "",
        "## Top 30 rules by validation hits",
        "",
        "| Rule | Val + hits | Val − hits | Precision lower bound | Wilson (train) |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in sorted(per_rule, key=lambda r: (-r["val_hits"], r["val_neg_hits"], r["rule_id"]))[:30]:
        lb = "n/a" if r["val_precision_lower_bound"] is None else f"{r['val_precision_lower_bound']:.4f}"
        lines.append(f"| `{r['rule']}` | {r['val_hits']:,} | {r['val_neg_hits']:,} | {lb} | {r['wilson_lower']:.3f} |")
    lines += ["", "## Notes", ""] + [f"- {n}" for n in evaluation["notes"]] + [""]
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-name", default=m.DEFAULT_RUN_NAME)
    parser.add_argument("--grid-min-pca", default=",".join(str(v) for v in GRID_MIN_PCA), help="comma-separated PCA thresholds")
    parser.add_argument("--grid-min-support", default=",".join(str(v) for v in GRID_MIN_SUPPORT), help="comma-separated support thresholds")
    parser.add_argument("--exclude-ranks-from", default=None, help="run name whose global ranks identify rules to exclude")
    parser.add_argument("--exclude-ranks", default="", help="comma-separated global ranks in --exclude-ranks-from")
    args = parser.parse_args(list(argv) if argv is not None else None)
    exclude: list[str] = []
    if args.exclude_ranks:
        if not args.exclude_ranks_from:
            parser.error("--exclude-ranks needs --exclude-ranks-from")
        ranks = [int(v) for v in args.exclude_ranks.split(",")]
        exclude = [v["rule_id"] for v in rule_ids_by_rank(m.OUTPUT_ROOT / args.exclude_ranks_from, ranks).values()]
    paths = evaluate(
        m.OUTPUT_ROOT / args.run_name,
        grid_min_pca=[float(v) for v in args.grid_min_pca.split(",")],
        grid_min_support=[int(v) for v in args.grid_min_support.split(",")],
        exclude_rule_ids=exclude,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
