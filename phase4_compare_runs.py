"""Phase 4: compare a baseline rule run with an extended-grid run (read-only on both).

Reads two mining runs (default ``run_default`` and ``run_grid_ext``), the Phase 3
training graph, and the validation files. Applies an adoption rule that is
fixed before running, reports every grid point with and without an excluded
rule list, and writes:

* ``outputs/phase4/phase4_grid_ext_report.md``
* ``outputs/phase4/phase4_grid_ext_comparison.json``
* ``outputs/phase4/phase5_candidate_rules_proposed.json`` (a rule list only)

Nothing in either run directory is changed (hashes are checked before and
after). No rules are mined, no test file is opened, and no edges are listed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import phase4_rule_evaluation as ev
import phase4_rule_mining as m


COMPARE_NAME = "phase4_compare_runs.py"
COMPARE_VERSION = "4B.2.0"
REPORT_FILE = "phase4_grid_ext_report.md"
COMPARISON_FILE = "phase4_grid_ext_comparison.json"
CANDIDATES_FILE = "phase5_candidate_rules_proposed.json"
DEFAULT_EXCLUDE_RANKS = (49, 65, 69, 145, 160, 166)


def _hash_dir(run_dir: Path) -> dict[str, str]:
    return {p.name: m.sha256_file(p) for p in sorted(run_dir.iterdir()) if p.is_file()}


def _check_run(run_dir: Path) -> dict[str, Any]:
    manifest = json.loads((run_dir / m.MANIFEST_FILE).read_text(encoding="utf-8"))
    for name, digest in manifest["outputs"].items():
        if m.sha256_file(run_dir / name) != digest:
            raise m.Phase4Error(f"{run_dir / name} does not match its mining manifest")
    return manifest


def _point(grid: list[dict[str, Any]], min_pca: float, min_support: int) -> dict[str, Any]:
    for g in grid:
        if abs(g["min_pca"] - min_pca) < 1e-12 and g["min_support"] == min_support:
            return g
    raise m.Phase4Error(f"grid point ({min_pca}, {min_support}) not found")


def decide_adoption(
    grid: list[dict[str, Any]],
    baseline_f1: float,
    reference: tuple[float, int],
    min_f1_gain: float,
    min_precision: float,
) -> dict[str, Any]:
    """Best looser point (min_pca < ref or min_support < ref); adopt only if both criteria hold."""
    looser = [g for g in grid if g["min_pca"] < reference[0] or g["min_support"] < reference[1]]
    if not looser:
        return {"best_looser_point": None, "adopt": False, "reason": "no looser grid point"}
    best = max(looser, key=lambda g: (g["f1"], g["min_pca"], g["min_support"]))
    gain = best["f1"] - baseline_f1
    adopt = gain >= min_f1_gain - 1e-12 and best["precision"] >= min_precision
    reasons = []
    if gain < min_f1_gain - 1e-12:
        reasons.append(f"F1 gain {gain:+.6f} < {min_f1_gain}")
    if best["precision"] < min_precision:
        reasons.append(f"precision {best['precision']:.6f} < {min_precision}")
    return {
        "best_looser_point": best,
        "baseline_f1": baseline_f1,
        "f1_gain": m._r(gain),
        "adopt": adopt,
        "reason": "both criteria met" if adopt else "; ".join(reasons),
    }


def compare_runs(
    baseline_dir: Path,
    extended_dir: Path,
    out_dir: Path = m.OUTPUT_ROOT,
    exclude_ranks: Iterable[int] = DEFAULT_EXCLUDE_RANKS,
    reference: tuple[float, int] = (0.10, 10),
    min_f1_gain: float = 0.01,
    min_precision: float = 0.75,
    valid_path: Path = ev.VALID_PATH,
    valid_negatives_path: Path = ev.VALID_NEGATIVES_PATH,
    phase3_dir: Path = m.PHASE3_DIR,
    train_path: Path = m.TRAIN_PATH,
    root: Path = m.ROOT,
) -> dict[str, Path]:
    targets = {"report": out_dir / REPORT_FILE, "comparison": out_dir / COMPARISON_FILE, "candidates": out_dir / CANDIDATES_FILE}
    existing = [str(p) for p in targets.values() if p.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(existing))

    baseline_hashes_before = _hash_dir(baseline_dir)
    extended_hashes_before = _hash_dir(extended_dir)
    state_before = m.protected_state(root, ev.STAT_ONLY_FOR_EVALUATOR)
    base_manifest = _check_run(baseline_dir)
    ext_manifest = _check_run(extended_dir)
    if base_manifest["inputs"]["phase3_trig"]["sha256"] != ext_manifest["inputs"]["phase3_trig"]["sha256"]:
        raise m.Phase4Error("the two runs were mined from different Phase 3 graphs")

    base_rules = json.loads((baseline_dir / m.SELECTED_FILE).read_text(encoding="utf-8"))["rules"]
    ext_doc = json.loads((extended_dir / m.SELECTED_FILE).read_text(encoding="utf-8"))
    ext_rules = ext_doc["rules"]
    ext_eval = json.loads((extended_dir / ev.EVALUATION_JSON).read_text(encoding="utf-8"))
    base_eval = json.loads((baseline_dir / ev.EVALUATION_JSON).read_text(encoding="utf-8"))
    excluded = ev.rule_ids_by_rank(baseline_dir, list(exclude_ranks))
    excluded_ids = {v["rule_id"] for v in excluded.values()}

    triples, _ = m.load_training_triples(phase3_dir, train_path)
    kg = m.KG(triples)
    positives = ev.read_split(valid_path)
    negatives = ev.read_split(valid_negatives_path)
    union = {r["rule_id"]: r for r in base_rules + ext_rules}
    pos_hits, _ = ev.coverage(kg, list(union.values()), positives)
    neg_hits, _ = ev.coverage(kg, list(union.values()), negatives)
    n_pos = len(positives)

    gp, gs = ext_eval["grid_min_pca"], ext_eval["grid_min_support"]
    grids = {
        "extended_all": ev.score_grid(ext_rules, pos_hits, neg_hits, n_pos, gp, gs),
        "extended_without_excluded": ev.score_grid([r for r in ext_rules if r["rule_id"] not in excluded_ids], pos_hits, neg_hits, n_pos, gp, gs),
        "baseline_all": ev.score_grid(base_rules, pos_hits, neg_hits, n_pos, gp, gs),
        "baseline_without_excluded": ev.score_grid([r for r in base_rules if r["rule_id"] not in excluded_ids], pos_hits, neg_hits, n_pos, gp, gs),
    }
    if grids["extended_all"] != ext_eval["grid"]:
        raise m.Phase4Error("recomputed extended grid differs from validation_evaluation.json")
    for old in base_eval["grid"]:
        new = _point(grids["baseline_all"], old["min_pca"], old["min_support"])
        if (new["tp"], new["fp"], new["rules"]) != (old["tp"], old["fp"], old["rules"]):
            raise m.Phase4Error("recomputed baseline metrics differ from the baseline validation_evaluation.json")

    decisions = {}
    for variant in ("all", "without_excluded"):
        base_ref = _point(grids[f"baseline_{variant}"], *reference)
        ext_ref = _point(grids[f"extended_{variant}"], *reference)
        baseline_f1 = max(base_ref["f1"], ext_ref["f1"])
        decisions[variant] = {
            "baseline_reference": base_ref,
            "extended_reference": ext_ref,
            **decide_adoption(grids[f"extended_{variant}"], baseline_f1, reference, min_f1_gain, min_precision),
        }
    adopt = decisions["all"]["adopt"] and decisions["without_excluded"]["adopt"]
    point = decisions["without_excluded"]["best_looser_point"] if adopt else {"min_pca": reference[0], "min_support": reference[1]}
    proposed = [
        r for r in ext_rules
        if r["pca_confidence"] >= point["min_pca"] and r["support"] >= point["min_support"] and r["rule_id"] not in excluded_ids
    ]

    # Rule-set changes between the baseline and the extended run at the reference point.
    ext_ref_rules = {r["rule_id"]: r for r in ext_rules if r["pca_confidence"] >= reference[0] and r["support"] >= reference[1]}
    base_by_id = {r["rule_id"]: r for r in base_rules}
    ext_candidates = {}
    for line in (extended_dir / m.CANDIDATES_FILE).read_text(encoding="utf-8").splitlines():
        cand = json.loads(line)
        ext_candidates[cand["rule_id"]] = cand
    removed = []
    for rid in sorted(set(base_by_id) - set(ext_ref_rules), key=lambda i: base_by_id[i]["global_rank"]):
        old = base_by_id[rid]
        new = ext_candidates.get(rid)
        removed.append({
            "rule": old["rule"], "baseline_rank": old["global_rank"],
            "baseline": {k: old[k] for k in ("support", "pca_body_size", "pca_confidence", "wilson_lower")},
            "extended": None if new is None else {k: new[k] for k in ("support", "pca_body_size", "pca_confidence", "wilson_lower", "counting", "status", "reasons")},
            "excluded_six": rid in excluded_ids,
        })
    added = [
        {"rule": ext_ref_rules[rid]["rule"], "extended_rank": ext_ref_rules[rid]["global_rank"],
         "support": ext_ref_rules[rid]["support"], "pca_confidence": ext_ref_rules[rid]["pca_confidence"],
         "counting": ext_ref_rules[rid]["counting"]}
        for rid in sorted(set(ext_ref_rules) - set(base_by_id), key=lambda i: ext_ref_rules[i]["global_rank"])
    ]
    recounted = [
        {"rule": r["rule"], "baseline": {k: base_by_id[r["rule_id"]][k] for k in ("support", "body_size", "pca_body_size", "pca_confidence", "wilson_lower")},
         "extended": {k: r[k] for k in ("support", "body_size", "pca_body_size", "pca_confidence", "wilson_lower")},
         "baseline_rank": base_by_id[r["rule_id"]]["global_rank"], "extended_rank": r["global_rank"]}
        for r in ext_rules if r["counting"] == "unordered_couples" and r["rule_id"] in base_by_id
    ]
    below_old_floor = [r for r in ext_rules if r["pca_confidence"] < reference[0] or r["support"] < reference[1]]

    baseline_hashes_after = _hash_dir(baseline_dir)
    extended_hashes_after = _hash_dir(extended_dir)
    if baseline_hashes_after != baseline_hashes_before or extended_hashes_after != extended_hashes_before:
        raise m.Phase4Error("a run directory changed during comparison")
    if m.protected_state(root, ev.STAT_ONLY_FOR_EVALUATOR) != state_before:
        raise m.Phase4Error("protected files changed during comparison")

    comparison = {
        "tool": COMPARE_NAME, "version": COMPARE_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "baseline_run": m._rel(baseline_dir, root), "extended_run": m._rel(extended_dir, root),
        "adoption_rule": {
            "reference_point": {"min_pca": reference[0], "min_support": reference[1]},
            "baseline_f1": "max(baseline run at reference, extended run at reference), per variant",
            "looser_point": "min_pca < reference or min_support < reference",
            "min_f1_gain": min_f1_gain, "min_precision": min_precision,
            "adopt_only_if": "criteria hold both with all rules and without the excluded rules",
        },
        "excluded_rules": {str(k): v for k, v in excluded.items()},
        "excluded_present_in_extended": sorted(excluded_ids & {r["rule_id"] for r in ext_rules}),
        "grids": grids,
        "decisions": decisions,
        "adopted": adopt,
        "proposed_point": {"min_pca": point["min_pca"], "min_support": point["min_support"]},
        "rule_counts": {
            "baseline_selected": len(base_rules),
            "baseline_without_excluded": len([r for r in base_rules if r["rule_id"] not in excluded_ids]),
            "extended_selected": len(ext_rules),
            "extended_at_reference": len(ext_ref_rules),
            "extended_below_old_floor": len(below_old_floor),
            "proposed_phase5_candidates": len(proposed),
            "baseline_rules_also_in_extended_selected": len(set(base_by_id) & {r["rule_id"] for r in ext_rules}),
        },
        "changes_at_reference": {"removed_vs_baseline": removed, "added_vs_baseline": added},
        "symmetric_recounted_rules": recounted,
        "baseline_files_unchanged": True,
        "baseline_file_hashes": baseline_hashes_before,
        "files_not_opened": "data/test*",
        "predictions_written": False,
    }
    candidates_doc = {
        "status": "PROPOSED - not approved for Phase 5 yet",
        "source_run": m._rel(extended_dir, root),
        "source_selected_rules_sha256": m.sha256_file(extended_dir / m.SELECTED_FILE),
        "thresholds": comparison["proposed_point"],
        "adopted_looser_point": adopt,
        "excluded_rules": comparison["excluded_rules"],
        "scoring": f"miner {ext_manifest['miner_version']}, symmetric_unit={ext_doc['config'].get('symmetric_unit', 'ordered')}",
        "baseline_preserved": f"{m._rel(baseline_dir, root)} (166 rules, unchanged)",
        "note": "Rule list only. Statistical patterns from training data; no inferred or predicted edges.",
        "rules": [
            {k: r[k] for k in ("rule_id", "rule", "display", "head", "type", "support", "pca_confidence", "wilson_lower", "counting", "flags")}
            for r in proposed
        ],
    }
    m._write_new(targets["comparison"], m._json(comparison))
    m._write_new(targets["candidates"], m._json(candidates_doc))
    m._write_new(targets["report"], render_report(comparison))
    return targets


def _row(g: dict[str, Any]) -> str:
    return f"| {g['min_pca']} | {g['min_support']} | {g['rules']} | {g['tp']:,} | {g['fp']:,} | {g['precision']:.3f} | {g['recall']:.3f} | {g['f1']:.4f} |"


def render_report(c: dict[str, Any]) -> str:
    rc = c["rule_counts"]
    lines = [
        "# Phase 4: grid extension and couple counting — comparison",
        "",
        f"Baseline `{c['baseline_run']}` (unchanged) vs extended `{c['extended_run']}`. Validation only; "
        "test files not opened; no rules mined here; no edges listed.",
        "",
        "## Adoption rule (fixed before running)",
        "",
        f"Adopt the best looser point (min_pca < {c['adoption_rule']['reference_point']['min_pca']} or "
        f"min_support < {c['adoption_rule']['reference_point']['min_support']}) only if F1 ≥ baseline + "
        f"{c['adoption_rule']['min_f1_gain']} and precision ≥ {c['adoption_rule']['min_precision']}, with all rules "
        "and without the excluded rules. Baseline F1 = higher of the two runs at the reference point.",
        "",
    ]
    for variant, d in c["decisions"].items():
        best = d["best_looser_point"]
        lines.append(
            f"- **{variant}**: baseline F1 {d['baseline_f1']:.4f}; best looser point ({best['min_pca']}, {best['min_support']}) "
            f"F1 {best['f1']:.4f}, precision {best['precision']:.3f}, gain {d['f1_gain']:+.4f} → "
            f"{'adopt' if d['adopt'] else 'do not adopt'} ({d['reason']})"
        )
    lines += [
        "",
        f"**Result:** {'adopted looser point' if c['adopted'] else 'no looser point adopted'}; proposed Phase 5 set uses "
        f"({c['proposed_point']['min_pca']}, {c['proposed_point']['min_support']}) from the extended run minus the excluded rules: "
        f"**{rc['proposed_phase5_candidates']} rules**.",
        "",
        "## Rule counts",
        "",
    ]
    lines += [f"- {k.replace('_', ' ')}: {v}" for k, v in rc.items()]
    for key, title in (
        ("extended_all", "Extended run, all rules"),
        ("extended_without_excluded", "Extended run, without the excluded rules"),
        ("baseline_all", "Baseline run, all 166 rules (same grid; looser points equal the floor)"),
        ("baseline_without_excluded", "Baseline run, without the excluded rules"),
    ):
        lines += ["", f"## {title}", "", "| min_pca | min_support | Rules | TP | FP | Precision | Recall | F1 |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
        lines += [_row(g) for g in c["grids"][key]]
    lines += ["", "## Excluded rules (baseline ranks)", ""]
    present = set(c["excluded_present_in_extended"])
    lines += [f"- {rank}: `{v['rule']}`{' (also selected in extended run)' if v['rule_id'] in present else ' (not selected in extended run)'}" for rank, v in c["excluded_rules"].items()]
    ch = c["changes_at_reference"]
    lines += ["", f"## Selected-rule changes at the reference point ({len(ch['removed_vs_baseline'])} removed, {len(ch['added_vs_baseline'])} added)", ""]
    for r in ch["removed_vs_baseline"]:
        new = r["extended"]
        why = "not a candidate in extended run" if new is None else f"{new['counting']}: support {new['support']}, PCA {new['pca_confidence']:.3f}, status {new['status']} {', '.join(new['reasons'])}".strip()
        lines.append(f"- removed `{r['rule']}` (baseline rank {r['baseline_rank']}, support {r['baseline']['support']}, PCA {r['baseline']['pca_confidence']:.3f}) — {why}")
    for r in ch["added_vs_baseline"]:
        lines.append(f"- added `{r['rule']}` (extended rank {r['extended_rank']}, support {r['support']}, PCA {r['pca_confidence']:.3f}, {r['counting']})")
    lines += ["", "## Symmetric rules recounted per couple (baseline → extended)", "", "| Rule | Support | Body | PCA body | PCA conf | Wilson | Rank |", "|---|---|---|---|---|---|---|"]
    for r in c["symmetric_recounted_rules"]:
        b, e = r["baseline"], r["extended"]
        lines.append(
            f"| `{r['rule']}` | {b['support']} → {e['support']} | {b['body_size']} → {e['body_size']} | {b['pca_body_size']} → {e['pca_body_size']} | "
            f"{b['pca_confidence']:.3f} → {e['pca_confidence']:.3f} | {b['wilson_lower']:.3f} → {e['wilson_lower']:.3f} | {r['baseline_rank']} → {r['extended_rank']} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Precision/recall/F1: TP = validation positives covered by ≥1 rule; FP = supplied validation negatives covered; recall over all 10,310 positives.",
        "- Aggregate precision is on the balanced validation lists only; it is not the precision of rule-derived edges in general.",
        f"- Baseline run files unchanged (hashes checked before and after); all {rc['baseline_selected']} baseline rules remain in `{c['baseline_run']}/selected_rules.json`.",
        "- Rules remain statistical patterns, not semantic claims. Phase 5 not started.",
        "",
    ]
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", default=m.DEFAULT_RUN_NAME)
    parser.add_argument("--extended", default="run_grid_ext")
    parser.add_argument("--exclude-ranks", default=",".join(str(r) for r in DEFAULT_EXCLUDE_RANKS))
    parser.add_argument("--min-f1-gain", type=float, default=0.01)
    parser.add_argument("--min-precision", type=float, default=0.75)
    args = parser.parse_args(list(argv) if argv is not None else None)
    paths = compare_runs(
        m.OUTPUT_ROOT / args.baseline,
        m.OUTPUT_ROOT / args.extended,
        exclude_ranks=[int(v) for v in args.exclude_ranks.split(",") if v],
        min_f1_gain=args.min_f1_gain,
        min_precision=args.min_precision,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
