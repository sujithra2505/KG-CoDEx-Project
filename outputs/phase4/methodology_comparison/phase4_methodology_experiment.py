"""Experimental, read-only comparison of couple-support definitions (Phase 4).

Not a production script. It re-scores the swap-invariant candidates already
recorded in ``run_grid_ext/rule_candidates.jsonl`` under four counting modes,
re-runs the production selection step (``phase4_rule_mining._select``) for the
affected head relations, and scores the resulting rule sets on validation:

* ``one``     couple counts as support if the head holds in at least one direction
              (production 4B.2.0 behaviour; must reproduce run_grid_ext exactly)
* ``both``    couple counts only if the head holds in both directions
* ``ordered`` ordered pairs (4B.1.0 behaviour)
* ``hybrid``  ``one`` for heads recorded reciprocally (reciprocity >= 0.5), ``ordered`` otherwise

It also compares sibling transitivity with the shared-sibling rules.

Nothing is mined from scratch, no test file is opened, no edges are listed,
and all outputs go to ``outputs/phase4/methodology_comparison/`` (never overwritten).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

import phase4_rule_evaluation as ev  # noqa: E402
import phase4_rule_mining as m  # noqa: E402

MODES = ("one", "both", "ordered", "hybrid")
RECIPROCITY_THRESHOLD = 0.5
TRANSITIVITY = "P3373(x,y) & P3373(y,z) => P3373(x,z)"
SHARED_SIBLING = ("P3373(x,y) & P3373(z,y) => P3373(x,z)", "P3373(y,x) & P3373(y,z) => P3373(x,z)")
RESULTS_FILE = "results.json"
TABLES_FILE = "tables.md"


def reciprocity(kg: m.KG, h: str) -> float:
    pairs = kg.pairs[h]
    N = kg.N
    return sum(1 for c in pairs if (c % N) * N + c // N in pairs) / len(pairs) if pairs else 0.0


def support_set(kg: m.KG, shape: tuple, h: str) -> set[int]:
    """Ordered pairs where the head and the body both hold (production definition)."""
    N = kg.N
    return {c for c in kg.pairs[h] if m.body_holds(kg, shape, c // N, c % N)}


def both_direction_couples(kg: m.KG, h: str, pairs: Iterable[int]) -> set[int]:
    N = kg.N
    head = kg.pairs[h]
    return {m.couple(c, N) for c in pairs if c in head and (c % N) * N + c // N in head}


def rescore(kg: m.KG, cand: dict[str, Any], mode: str, info: m.HeadInfo, symmetric_heads: set[str],
            config: m.MiningConfig, labels: dict[str, str]) -> dict[str, Any]:
    shape = ev.shape_from_body(cand["body"])
    h = cand["head"]
    ordered = dict(cand["ordered_counts"])
    swap = m.is_swap_invariant(shape, h)
    use = mode if mode != "hybrid" else ("one" if h in symmetric_heads else "ordered")
    S = None
    if not swap or use == "ordered":
        counted = dict(ordered, head_count=info.count, unit="ordered_pairs")
    else:
        S = support_set(kg, shape, h)
        N = kg.N
        if use == "one":
            support_u = len({m.couple(c, N) for c in S})
            head_count = len({m.couple(c, N) for c in kg.pairs[h]})
        else:  # both
            support_u = len(both_direction_couples(kg, h, S))
            head_count = len(both_direction_couples(kg, h, kg.pairs[h]))
        counted = {"body_size": cand["body_size"], "support": support_u, "pca_body_size": cand["pca_body_size"],
                   "head_count": head_count, "unit": f"couples_{use}"}
        if cand["counting"] != "unordered_couples":
            raise m.Phase4Error(f"expected couple counting in run_grid_ext for {cand['rule']}")
    if counted["support"] < config.min_support:
        new = {**cand, "support": counted["support"], "status": "rejected",
               "reasons": [f"support_below_min:{counted['support']}<{config.min_support}"], "flags": {}}
        return new
    new = m._candidate(shape, h, counted, ordered, info, config, labels)
    if not new["reasons"]:
        new["_support"] = sorted(S if S is not None else support_set(kg, shape, h))
    return new


def run_experiment(project: Path = PROJECT, out_dir: Path | None = None,
                   exclude_ranks: Iterable[int] = (49, 65, 69, 145, 160, 166),
                   reference: tuple[float, int] = (0.10, 10)) -> dict[str, Path]:
    phase4 = project / "outputs" / "phase4"
    out_dir = out_dir or phase4 / "methodology_comparison"
    targets = {"results": out_dir / RESULTS_FILE, "tables": out_dir / TABLES_FILE}
    existing = [str(p) for p in targets.values() if p.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(existing))
    base_dir, ext_dir = phase4 / "run_default", phase4 / "run_grid_ext"
    proposed_path = phase4 / "phase5_candidate_rules_proposed.json"
    watched = sorted([p for d in (base_dir, ext_dir) for p in d.iterdir() if p.is_file()] + [proposed_path])
    hashes_before = {str(p.relative_to(project)): m.sha256_file(p) for p in watched}
    state_before = m.protected_state(project, ev.STAT_ONLY_FOR_EVALUATOR)

    ext_doc = json.loads((ext_dir / m.SELECTED_FILE).read_text(encoding="utf-8"))
    config = m.MiningConfig(**ext_doc["config"])
    cands = [json.loads(l) for l in (ext_dir / m.CANDIDATES_FILE).read_text(encoding="utf-8").splitlines()]
    proposed = json.loads(proposed_path.read_text(encoding="utf-8"))
    excluded_ids = {v["rule_id"] for v in ev.rule_ids_by_rank(base_dir, list(exclude_ranks)).values()}
    labels = m.p3.load_label_map(project / "data" / "relation_labels.json")

    triples, _ = m.load_training_triples(project / "outputs" / "phase3", project / "data" / "train.txt")
    kg = m.KG(triples)
    recip = {h: reciprocity(kg, h) for h in kg.relations}
    symmetric_heads = {h for h, v in recip.items() if v >= RECIPROCITY_THRESHOLD}

    affected = sorted({c["head"] for c in cands if c["counting"] == "unordered_couples"})
    infos = m.head_infos(kg, affected)
    ext_selected = {r["rule_id"]: r for r in ext_doc["rules"]}
    unaffected_rules = [r for r in ext_doc["rules"] if r["head"] not in affected]

    per_mode: dict[str, dict[str, Any]] = {}
    rescored_all: dict[str, dict[str, dict[str, Any]]] = {}
    for mode in MODES:
        rescored = []
        for cand in cands:
            if cand["head"] not in affected:
                continue
            rescored.append(rescore(kg, cand, mode, infos[cand["head"]], symmetric_heads, config, labels))
        selected = m._select(rescored, config)
        rescored_all[mode] = {c["rule_id"]: c for c in rescored}
        rules = unaffected_rules + [{k: v for k, v in r.items() if not k.startswith("_")} for r in selected]
        per_mode[mode] = {"selected": rules}

    # The 'one' mode must reproduce run_grid_ext exactly for the affected heads.
    for rid, c in rescored_all["one"].items():
        orig = next(x for x in cands if x["rule_id"] == rid)
        if (c["status"], [r.split(":")[0] for r in c["reasons"]]) != (orig["status"], [r.split(":")[0] for r in orig["reasons"]]):
            raise m.Phase4Error(f"harness does not reproduce run_grid_ext for {orig['rule']}")
        if (c["support"], c["pca_confidence"], c["wilson_lower"]) != (orig["support"], orig["pca_confidence"], orig["wilson_lower"]):
            raise m.Phase4Error(f"harness scores differ from run_grid_ext for {orig['rule']}")

    positives = ev.read_split(project / "data" / "valid.txt")
    negatives = ev.read_split(project / "data" / "valid_negatives.txt")
    union = {r["rule_id"]: r for mode in MODES for r in per_mode[mode]["selected"]}
    by_text = {x["rule"]: x for x in cands}
    part_b_available = all(t in by_text for t in (TRANSITIVITY,) + SHARED_SIBLING)
    if part_b_available:
        for text in (TRANSITIVITY,) + SHARED_SIBLING:
            union.setdefault(by_text[text]["rule_id"], by_text[text])
    pos_hits, _ = ev.coverage(kg, list(union.values()), positives)
    neg_hits, _ = ev.coverage(kg, list(union.values()), negatives)

    def metrics(rules: list[dict[str, Any]]) -> dict[str, Any]:
        tp = set().union(*(pos_hits[r["rule_id"]] for r in rules)) if rules else set()
        fp = set().union(*(neg_hits[r["rule_id"]] for r in rules)) if rules else set()
        return {"rules": len(rules), **ev._f1(len(tp), len(fp), len(positives))}

    summary = {}
    for mode in MODES:
        ref = [r for r in per_mode[mode]["selected"] if r["pca_confidence"] >= reference[0] and r["support"] >= reference[1]]
        ref_wo = [r for r in ref if r["rule_id"] not in excluded_ids]
        summary[mode] = {
            "selected_total": len(per_mode[mode]["selected"]),
            "at_reference": metrics(ref),
            "at_reference_without_excluded": metrics(ref_wo),
            "rule_ids_at_reference_without_excluded": sorted(r["rule_id"] for r in ref_wo),
        }
    if set(summary["one"]["rule_ids_at_reference_without_excluded"]) != {r["rule_id"] for r in proposed["rules"]}:
        raise m.Phase4Error("mode 'one' does not reproduce phase5_candidate_rules_proposed.json")

    # Per-rule table for every swap-invariant candidate that is selected or near-eligible in any mode.
    rule_rows = []
    for rid in sorted({rid for mode in MODES for rid, c in rescored_all[mode].items() if c.get("counting") != "ordered_pairs" or c["status"] == "selected"}):
        orig = next(x for x in cands if x["rule_id"] == rid)
        if orig["counting"] != "unordered_couples":
            continue
        row = {"rule": orig["rule"], "head": orig["head"], "head_reciprocity": m._r(recip[orig["head"]]),
               "swap_type": "symmetry" if orig["length"] == 1 else "shared-node body",
               "val_hits": len(pos_hits.get(rid, ())) if rid in pos_hits else None,
               "val_neg_hits": len(neg_hits.get(rid, ())) if rid in neg_hits else None}
        for mode in MODES:
            c = rescored_all[mode][rid]
            row[mode] = {k: c.get(k) for k in ("support", "body_size", "pca_body_size", "std_confidence", "pca_confidence", "head_coverage", "wilson_lower", "status")}
            row[mode]["reasons"] = [r.split(":")[0] for r in c["reasons"]]
            row[mode]["in_reference_set"] = rid in set(summary[mode]["rule_ids_at_reference_without_excluded"])
        if any(row[mode]["status"] == "selected" for mode in MODES) or any(
                (row[mode]["pca_confidence"] or 0) >= 0.05 for mode in MODES):
            rule_rows.append(row)

    # Part B: sibling transitivity vs shared-sibling rules.
    part_b: dict[str, Any] = {"available": part_b_available}
    if part_b_available:
        N = kg.N
        texts = (TRANSITIVITY,) + SHARED_SIBLING
        body_sets = {t: m.body_pairs(kg, ev.shape_from_body(next(x for x in cands if x["rule"] == t)["body"])) for t in texts}
        supp_sets = {t: body_sets[t] & kg.pairs["P3373"] for t in texts}
        ids = {t: next(x for x in cands if x["rule"] == t)["rule_id"] for t in texts}
        ref_one = set(summary["one"]["rule_ids_at_reference_without_excluded"])
        others_pos = set().union(*(pos_hits[r] for r in ref_one if r not in ids.values()))
        others_neg = set().union(*(neg_hits[r] for r in ref_one if r not in ids.values()))
        for t in texts:
            part_b[t] = {
                "rule_id": ids[t], "body_pairs": len(body_sets[t]), "support_pairs": len(supp_sets[t]),
                "file_status": next(x for x in cands if x["rule"] == t)["status"],
                "file_reasons": next(x for x in cands if x["rule"] == t)["reasons"],
                "val_hits": len(pos_hits[ids[t]]), "val_neg_hits": len(neg_hits[ids[t]]),
                "val_hits_not_covered_by_other_proposed_rules": len(pos_hits[ids[t]] - others_pos),
                "val_neg_hits_not_covered_by_other_proposed_rules": len(neg_hits[ids[t]] - others_neg),
                "status_by_mode": {mode: rescored_all[mode][ids[t]]["status"] for mode in MODES},
                "reasons_by_mode": {mode: rescored_all[mode][ids[t]]["reasons"] for mode in MODES},
            }
        a, b = TRANSITIVITY, SHARED_SIBLING[0]
        jac = lambda s1, s2: m._r(len(s1 & s2) / len(s1 | s2)) if s1 | s2 else None  # noqa: E731
        part_b["overlap"] = {
            "support_jaccard_T_S1": jac(supp_sets[a], supp_sets[b]),
            "support_jaccard_T_S2": jac(supp_sets[a], supp_sets[SHARED_SIBLING[1]]),
            "body_jaccard_T_S1": jac(body_sets[a], body_sets[b]),
            "support_only_T_vs_S1": len(supp_sets[a] - supp_sets[b]),
            "support_only_S1_vs_T": len(supp_sets[b] - supp_sets[a]),
            "body_only_T_vs_S1": len(body_sets[a] - body_sets[b]),
            "body_only_S1_vs_T": len(body_sets[b] - body_sets[a]),
            "val_hits_only_T_vs_S1": len(pos_hits[ids[a]] - pos_hits[ids[b]]),
            "val_hits_only_S1_vs_T": len(pos_hits[ids[b]] - pos_hits[ids[a]]),
            "val_neg_only_T_vs_S1": len(neg_hits[ids[a]] - neg_hits[ids[b]]),
            "val_neg_only_S1_vs_T": len(neg_hits[ids[b]] - neg_hits[ids[a]]),
            "proposed_set_plus_T": metrics([union[r] for r in ref_one] + [union[ids[a]]]),
            "proposed_set": metrics([union[r] for r in ref_one]),
            "proposed_set_minus_S1": metrics([union[r] for r in ref_one if r != ids[b]]),
        }

    hashes_after = {str(p.relative_to(project)): m.sha256_file(p) for p in watched}
    if hashes_after != hashes_before:
        raise m.Phase4Error("an original run file or the candidate list changed")
    if m.protected_state(project, ev.STAT_ONLY_FOR_EVALUATOR) != state_before:
        raise m.Phase4Error("protected files changed")

    results = {
        "tool": "phase4_methodology_experiment.py (experimental)",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "modes": {
            "one": "couple supports if the head holds in at least one direction (production 4B.2.0)",
            "both": "couple supports only if the head holds in both directions; head coverage over two-way couples",
            "ordered": "ordered pairs (4B.1.0)",
            "hybrid": f"'one' for heads with reciprocity >= {RECIPROCITY_THRESHOLD}, 'ordered' otherwise",
        },
        "pca_body_definition": "unchanged in all couple modes: couples with at least one ordered pair in the PCA body",
        "reciprocity": {h: m._r(v) for h, v in sorted(recip.items()) if h in affected},
        "symmetric_heads": sorted(symmetric_heads),
        "affected_heads": affected,
        "harness_check": "mode 'one' reproduced run_grid_ext statuses/scores and the 160-rule proposed list exactly",
        "summary": {k: {kk: vv for kk, vv in v.items() if kk != "rule_ids_at_reference_without_excluded"} for k, v in summary.items()},
        "reference_set_differences_vs_one": {
            mode: {
                "added": sorted(union[r]["rule"] for r in set(summary[mode]["rule_ids_at_reference_without_excluded"]) - set(summary["one"]["rule_ids_at_reference_without_excluded"])),
                "removed": sorted(union[r]["rule"] for r in set(summary["one"]["rule_ids_at_reference_without_excluded"]) - set(summary[mode]["rule_ids_at_reference_without_excluded"])),
            } for mode in MODES if mode != "one"
        },
        "swap_invariant_rules": rule_rows,
        "sibling_transitivity": part_b,
        "files_checked_unchanged": hashes_before,
        "files_not_opened": "data/test*",
        "predictions_written": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    m._write_new(targets["results"], m._json(results))
    m._write_new(targets["tables"], render_tables(results))
    return targets


def render_tables(r: dict[str, Any]) -> str:
    lines = ["# Methodology comparison tables (experimental)", "", "## Rule-set validation at (0.10, 10), without the six excluded rules", "",
             "| Mode | Rules | TP | FP | Precision | Recall | F1 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for mode, s in r["summary"].items():
        g = s["at_reference_without_excluded"]
        lines.append(f"| {mode} | {g['rules']} | {g['tp']:,} | {g['fp']:,} | {g['precision']:.4f} | {g['recall']:.4f} | {g['f1']:.4f} |")
    lines += ["", "## Set differences vs mode 'one'", ""]
    for mode, d in r["reference_set_differences_vs_one"].items():
        lines.append(f"- **{mode}**: added {d['added'] or 'none'}; removed {d['removed'] or 'none'}")
    lines += ["", "## Swap-invariant rules (selected in some mode, or PCA ≥ 0.05 in some mode)", "",
              "| Rule | Recip. | Mode | Support | Body | PCA body | Conf | PCA | HC | Wilson | Status | In set |", "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for row in r["swap_invariant_rules"]:
        for mode in MODES:
            c = row[mode]
            lines.append(f"| `{row['rule']}` | {row['head_reciprocity']} | {mode} | {c['support']} | {c['body_size']} | {c['pca_body_size']} | "
                         f"{c['std_confidence']} | {c['pca_confidence']} | {c['head_coverage']} | {c['wilson_lower']} | {c['status']} {','.join(c['reasons'])} | {c['in_reference_set']} |")
    lines += ["", "## Sibling transitivity vs shared-sibling", "", "```json", json.dumps(r["sibling_transitivity"], indent=1), "```", ""]
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(list(argv) if argv is not None else None)
    for name, path in run_experiment().items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
