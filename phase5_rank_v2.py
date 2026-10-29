"""Phase 5, ranking v2: same predictions, evidence-aware tie-break.

Re-runs the Phase 5 round-1 candidate generation (``phase5_predict``, unchanged)
and ranks every candidate triple by:

1. highest Wilson lower bound among its supporting rules   (as in v1)
2. highest PCA confidence among its supporting rules        (as in v1)
3. number of distinct supporting body matches               (new)
4. number of distinct supporting rules
5. subject ID number, then object ID number                 (deterministic)

A *body match* is one grounding of a rule body in the training graph, i.e. the
set of training triples that makes the body true for (x, z). Matches are
counted once per distinct set of training triples, across all supporting
rules, so an identical proof reached twice is not counted twice. Matches may
still share individual triples (for example the same first atom with different
middle entities); they are distinct proofs, not independent observations.

Outputs go to ``outputs/phase5/ranking_v2/``. Existing Phase 5 files are never
changed. Validation and test files are never opened, and nothing is scored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import phase4_rule_mining as m
import phase5_predict as p5

ROOT = p5.ROOT
OUTPUT_DIR = ROOT / "outputs" / "phase5" / "ranking_v2"
NAME = "phase5_rank_v2.py"
VERSION = "5.2.0"
COMPARISON_FILE = "ranking_comparison.md"
TIE_BREAK = ["max_pca_confidence desc", "distinct_body_matches desc", "supporting_rules desc",
             "subject ID number asc", "object ID number asc"]
V1_FILES = (p5.PREDICTIONS_FILE, p5.REPORT_FILE, p5.VIEWER_FILE, p5.MANIFEST_FILE, "phase5_report.md")


def body_matches(kg: m.KG, rules: Iterable[dict[str, Any]], x: int, z: int) -> set[frozenset]:
    """Distinct body matches for (x, z): each is the frozenset of training triples (int-coded)."""
    matches: set[frozenset] = set()
    for rule in rules:
        shape = rule["shape"]
        if shape[0] == "1":
            groundings = [m.body_triples(kg, shape, x, None, z)]
        else:
            groundings = [m.body_triples(kg, shape, x, y, z) for y in m.middles(kg, shape, x, z)]
        for g in groundings:
            for s, r, o in g:
                if not kg.has(kg.eid[s], r, kg.eid[o]):
                    raise p5.Phase5Error(f"grounding triple {(s, r, o)} is not in the training graph")
            matches.add(frozenset(tuple(t) for t in g))
    return matches


def rank_v2(kg: m.KG, candidates, rules_by_id, cap: int):
    names = kg.entities
    by_relation = defaultdict(list)
    evidence: dict[tuple[int, str, int], int] = {}
    for key, rule_ids in candidates.items():
        x, h, z = key
        rs = [rules_by_id[r] for r in sorted(set(rule_ids))]
        n_match = len(body_matches(kg, rs, x, z))
        evidence[key] = n_match
        sort_key = (-max(r["wilson_lower"] for r in rs), -max(r["pca_confidence"] for r in rs), -n_match, -len(rs),
                    p5._id_number(names[x]), p5._id_number(names[z]))
        by_relation[h].append((sort_key, key))
    kept, per_relation, ties = [], {}, {}
    for h in sorted(by_relation, key=p5._id_number):
        ranked = sorted(by_relation[h])
        per_relation[h] = {"candidates": len(ranked), "retained": min(cap, len(ranked))}
        ties[h] = tie_stats(ranked, cap)
        for rank, (_, key) in enumerate(ranked[:cap], start=1):
            kept.append((h, rank, key))
    return kept, per_relation, ties, evidence


def tie_stats(ranked: list[tuple[tuple, Any]], cap: int) -> dict[str, Any]:
    """How the cap boundary is decided. ``score_key`` = all criteria before the ID tie-break."""
    if len(ranked) <= cap:
        return {"capped": False}
    keys = [k[:-2] for k, _ in ranked]
    boundary = keys[cap - 1]
    group = sum(1 for k in keys if k == boundary)
    return {
        "capped": True,
        "id_decides_boundary": keys[cap] == boundary,
        "boundary_group_size": group,
        "kept_from_boundary_group": sum(1 for k in keys[:cap] if k == boundary),
        "strictly_better_than_boundary": sum(1 for k in keys if k < boundary),
    }


def tie_stats_v1(kg: m.KG, candidates, rules_by_id, cap: int) -> dict[str, dict[str, Any]]:
    names = kg.entities
    by_relation = defaultdict(list)
    for key, rule_ids in candidates.items():
        x, h, z = key
        rs = [rules_by_id[r] for r in set(rule_ids)]
        by_relation[h].append(((-max(r["wilson_lower"] for r in rs), -max(r["pca_confidence"] for r in rs), -len(rs),
                                p5._id_number(names[x]), p5._id_number(names[z])), key))
    return {h: tie_stats(sorted(v), cap) for h, v in by_relation.items()}


def watched_state(root: Path) -> dict[str, Any]:
    state = p5.protected_state(root)
    for name in V1_FILES + ("phase5_predict.py",):
        path = (root / "outputs" / "phase5" / name) if name != "phase5_predict.py" else root / name
        if path.is_file():
            state[path.relative_to(root).as_posix()] = {"sha256": m.sha256_file(path)}
    return state


def run(root: Path = ROOT, out_dir: Path | None = None, cap: int = p5.DEFAULT_CAP) -> dict[str, Path]:
    out_dir = out_dir or root / "outputs" / "phase5" / "ranking_v2"
    targets = {"predictions": out_dir / p5.PREDICTIONS_FILE, "report": out_dir / p5.REPORT_FILE,
               "viewer": out_dir / p5.VIEWER_FILE, "manifest": out_dir / p5.MANIFEST_FILE,
               "comparison": out_dir / COMPARISON_FILE}
    existing = [str(p) for p in targets.values() if p.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(existing))
    v1_dir = root / "outputs" / "phase5"
    v1_manifest = json.loads((v1_dir / p5.MANIFEST_FILE).read_text(encoding="utf-8"))
    for name, digest in v1_manifest["outputs"].items():
        if m.sha256_file(v1_dir / name) != digest:
            raise p5.Phase5Error(f"v1 file {name} does not match its manifest")
    started = time.time()
    state_before = watched_state(root)

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
    kept, per_relation, ties_v2, evidence = rank_v2(kg, candidates, rules_by_id, cap)
    ties_v1 = tie_stats_v1(kg, candidates, rules_by_id, cap)
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
    comparison = compare(v1_records, records, ties_v1, ties_v2, per_relation, relation_labels)

    settings = {"rounds": p5.ROUND, "cap_per_relation": cap, "ranking_score": p5.RANKING_SCORE, "tie_break": TIE_BREAK,
                "evidence_definition": "distinct sets of training triples that satisfy a supporting rule body for (x, z), "
                                       "deduplicated across rules; matches may share individual triples",
                "candidate_scope": "same as v1 (phase5_predict.generate_candidates)"}
    inputs = {**graph_info, **rule_info, "v1_manifest": {"path": "outputs/phase5/phase5_manifest.json",
                                                          "sha256": m.sha256_file(v1_dir / p5.MANIFEST_FILE)}}
    predictions_doc = {"phase": "5", "tool": NAME, "version": VERSION, "round": p5.ROUND, "settings": settings,
                       "note": "Same candidates as v1; only the tie-break changed. Not merged into training; not scored.",
                       "predictions": records}
    predictions_text = m._json(predictions_doc)
    report_text = p5.render_report(records, per_relation, counts, settings, inputs, relation_labels).replace(
        "# Phase 5: rule-based predictions (round 1)", "# Phase 5: rule-based predictions (round 1, ranking v2)")
    viewer_text = p5.render_viewer(records, vis_js, vis_css, relation_labels).replace(
        "Phase 5 rule-based predictions (round 1)", "Phase 5 rule-based predictions (round 1, ranking v2)")
    comparison_text = render_comparison(comparison, settings)

    if watched_state(root) != state_before:
        raise p5.Phase5Error("protected or v1 files changed during the rerun")
    manifest = {
        "phase": "5", "tool": NAME, "version": VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "runtime_seconds": round(time.time() - started, 1),
        "inputs": inputs, "settings": settings,
        "counts": {**counts, "retained_predictions": len(records), "per_relation": per_relation,
                   "changed_vs_v1": comparison["totals"]},
        "tie_stats_v1": ties_v1, "tie_stats_v2": ties_v2,
        "outputs": {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in (
            (p5.PREDICTIONS_FILE, predictions_text), (p5.REPORT_FILE, report_text),
            (p5.VIEWER_FILE, viewer_text), (COMPARISON_FILE, comparison_text))},
        "files_not_opened": "data/valid*, data/test* (size and mtime recorded only)",
        "protected_files": state_before, "protected_and_v1_files_unchanged": True,
        "scored_against_validation_or_test": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    m._write_new(targets["predictions"], predictions_text)
    m._write_new(targets["report"], report_text)
    m._write_new(targets["viewer"], viewer_text)
    m._write_new(targets["comparison"], comparison_text)
    m._write_new(targets["manifest"], m._json(manifest))
    return targets


def compare(v1, v2, ties_v1, ties_v2, per_relation, relation_labels) -> dict[str, Any]:
    def key(r):
        return (r["triple"]["subject"], r["triple"]["relation"], r["triple"]["object"])
    v1_by = {key(r): r for r in v1}
    v2_by = {key(r): r for r in v2}
    rows, totals = {}, Counter()
    for h in per_relation:
        a = {k for k in v1_by if k[1] == h}
        b = {k for k in v2_by if k[1] == h}
        same = a & b
        moved = sum(1 for k in same if v1_by[k]["relation_rank"] != v2_by[k]["relation_rank"])
        scores_v1 = sorted(v1_by[k]["ranking_score"]["value"] for k in a)
        scores_v2 = sorted(v2_by[k]["ranking_score"]["value"] for k in b)
        provenance_same = all(
            [s["rule_id"] for s in v1_by[k]["supporting_rules"]] == [s["rule_id"] for s in v2_by[k]["supporting_rules"]] for k in same)
        rows[h] = {"label": relation_labels.get(h, h), "candidates": per_relation[h]["candidates"], "retained": len(b),
                   "kept_in_both": len(same), "dropped": len(a - b), "added": len(b - a), "rank_changed": moved,
                   "score_multiset_unchanged": scores_v1 == scores_v2, "provenance_unchanged_for_kept": provenance_same,
                   "v1_tie": ties_v1.get(h, {}), "v2_tie": ties_v2.get(h, {})}
        for f in ("kept_in_both", "dropped", "added", "rank_changed"):
            totals[f] += rows[h][f]
    evid = [r["tie_break_values"]["distinct_body_matches"] for r in v2]
    tiers = Counter("≥ 0.7" if r["ranking_score"]["value"] >= 0.7 else ("0.4–0.7" if r["ranking_score"]["value"] >= 0.4 else "< 0.4") for r in v2)
    totals.update({
        "relations_where_id_decides_cap_v1": sum(1 for t in ties_v1.values() if t.get("id_decides_boundary")),
        "relations_where_id_decides_cap_v2": sum(1 for t in ties_v2.values() if t.get("id_decides_boundary")),
        "relations_all_candidates_tied_v1": sum(1 for t in ties_v1.values() if t.get("capped") and t["strictly_better_than_boundary"] == 0 and t["id_decides_boundary"]),
        "relations_all_candidates_tied_v2": sum(1 for t in ties_v2.values() if t.get("capped") and t["strictly_better_than_boundary"] == 0 and t["id_decides_boundary"]),
    })
    return {"rows": rows, "totals": dict(totals), "score_tiers_v2": dict(tiers),
            "evidence_distribution_v2": {"min": min(evid), "median": sorted(evid)[len(evid) // 2], "max": max(evid),
                                         "one_match": sum(1 for e in evid if e == 1)}}


def render_comparison(c: dict[str, Any], settings: dict[str, Any]) -> str:
    t = c["totals"]
    lines = [
        "# Phase 5 ranking v2 vs v1",
        "",
        "Same candidates, scores and rules as v1. Only the tie-break changed:",
        "",
        "`" + " → ".join(["max Wilson lower bound desc"] + settings["tie_break"]) + "`",
        "",
        f"Evidence count: {settings['evidence_definition']}.",
        "",
        "## Totals",
        "",
        f"- Predictions kept in both versions: {t['kept_in_both']:,}; dropped from v1: {t['dropped']:,}; added in v2: {t['added']:,}",
        f"- Kept predictions whose rank changed: {t['rank_changed']:,}",
        f"- Capped relations where subject/object IDs still decide the cut: v1 {t['relations_where_id_decides_cap_v1']} → v2 {t['relations_where_id_decides_cap_v2']}",
        f"- Capped relations where every candidate ties before the ID step: v1 {t['relations_all_candidates_tied_v1']} → v2 {t['relations_all_candidates_tied_v2']}",
        f"- v2 score tiers: " + ", ".join(f"{k}: {v:,}" for k, v in sorted(c["score_tiers_v2"].items())) + " (identical to v1: the cut only moves inside equal-score groups)",
        f"- Distinct body matches per retained prediction: min {c['evidence_distribution_v2']['min']}, median {c['evidence_distribution_v2']['median']}, "
        f"max {c['evidence_distribution_v2']['max']}; {c['evidence_distribution_v2']['one_match']:,} have exactly one",
        "",
        "## Per relation",
        "",
        "| Relation | Cand. | Kept | Same | Dropped / added | Rank moved | v1 boundary group (ID decides?) | v2 boundary group (ID decides?) |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for h, r in c["rows"].items():
        def b(tie):
            if not tie.get("capped"):
                return "not capped"
            return f"{tie['boundary_group_size']:,} ({'yes' if tie['id_decides_boundary'] else 'no'})"
        lines.append(f"| {r['label']} ({h}) | {r['candidates']:,} | {r['retained']} | {r['kept_in_both']} | {r['dropped']} / {r['added']} | "
                     f"{r['rank_changed']} | {b(r['v1_tie'])} | {b(r['v2_tie'])} |")
    lines += [
        "",
        "Boundary group = candidates sharing every criterion before the ID step with the 100th prediction.",
        "Score multisets per relation are unchanged and provenance (supporting rules) of predictions kept in both versions is unchanged:",
        f"{all(r['score_multiset_unchanged'] for r in c['rows'].values())} / {all(r['provenance_unchanged_for_kept'] for r in c['rows'].values())}.",
        "",
        "## Caveats",
        "",
        "- More body matches is more proof paths, not more independent evidence: matches can share triples, and hubs create many paths.",
        "- No validation or test data was used; whether v2 ranks better is not measured here.",
        "",
    ]
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cap", type=int, default=p5.DEFAULT_CAP)
    args = parser.parse_args(list(argv) if argv is not None else None)
    for name, path in run(ROOT, OUTPUT_DIR, args.cap).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
