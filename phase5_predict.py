"""Phase 5: one round of rule-based missing-edge prediction on the training graph.

Inputs (read-only):

* ``outputs/phase2/training_graph.graphml``  - the Phase 2 training graph (its GraphML
  export; ``phase2_graph.load_training_graph`` needs networkx/pyvis, which are not
  installed here). Checked against ``data/train.txt`` by SHA-256 and edge count.
* ``outputs/phase4/phase5_candidate_rules_proposed.json`` - the frozen 160-rule list.
* ``outputs/phase4/run_grid_ext/selected_rules.json`` - same rules with their body
  atoms and standard confidence (hash must equal the list's
  ``source_selected_rules_sha256``).
* ``data/entity_labels.json`` / ``data/relation_labels.json`` - display labels only.
* ``outputs/phase2/interactive_graph.html`` - only to reuse its embedded vis-network
  library for the prediction viewer.

Method: each rule is applied once (round 1) to training facts only. Every body
pair whose head triple is not in training becomes a candidate; candidates for
the same triple are merged and keep every supporting rule. Each predicted
triple is ranked by the highest Wilson lower bound among its rules (tie-break:
higher PCA confidence, more supporting rules, subject ID number, object ID
number) and at most ``cap_per_relation`` are kept per relation.

Validation and test files are never opened. Predictions are not scored here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Iterable

import phase4_rule_evaluation as ev
import phase4_rule_mining as m


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs" / "phase5"
NAME = "phase5_predict.py"
VERSION = "5.1.0"
ROUND = 1
DEFAULT_CAP = 100

PREDICTIONS_FILE = "predictions.json"
REPORT_FILE = "predictions_report.md"
VIEWER_FILE = "prediction_viewer.html"
MANIFEST_FILE = "phase5_manifest.json"

STAT_ONLY = ("data/valid", "data/test")
PROTECTED_FILES = m.PROTECTED_FILES + (
    "phase4_rule_mining.py", "phase4_rule_evaluation.py", "phase4_compare_runs.py",
)
PROTECTED_GLOBS = ("data/*", "outputs/phase2/*", "outputs/phase3/*", "outputs/phase4/*", "outputs/phase4/*/*")
RANKING_SCORE = "max_wilson_lower"
TIE_BREAK = ["max_pca_confidence desc", "supporting_rules desc", "subject ID number asc", "object ID number asc"]


class Phase5Error(RuntimeError):
    pass


# ----------------------------------------------------------------------- inputs


def load_phase2_graphml(path: Path) -> tuple[list[tuple[str, str, str]], dict[str, str]]:
    """Read the Phase 2 GraphML export. Returns sorted unique ID triples and graph data."""
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
    tree = ET.parse(path)
    root = tree.getroot()
    keys = {k.get("id"): (k.get("for"), k.get("attr.name")) for k in root.findall("g:key", ns)}
    rel_key = next((kid for kid, (kind, name) in keys.items() if kind == "edge" and name == "relation_id"), None)
    if rel_key is None:
        raise Phase5Error("GraphML has no edge attribute 'relation_id'")
    graph = root.find("g:graph", ns)
    graph_data = {keys[d.get("key")][1]: (d.text or "") for d in graph.findall("g:data", ns)}
    triples = []
    for edge in graph.findall("g:edge", ns):
        rel = next((d.text for d in edge.findall("g:data", ns) if d.get("key") == rel_key), None)
        if rel is None or rel != edge.get("id"):
            raise Phase5Error(f"edge {edge.get('source')}->{edge.get('target')} has inconsistent relation id")
        triples.append((edge.get("source"), rel, edge.get("target")))
    if len(set(triples)) != len(triples):
        raise Phase5Error("duplicate edges in the Phase 2 GraphML")
    for s, r, o in triples:
        if not (m.p3.ENTITY_ID_PATTERN.fullmatch(s) and m.p3.RELATION_ID_PATTERN.fullmatch(r) and m.p3.ENTITY_ID_PATTERN.fullmatch(o)):
            raise Phase5Error(f"invalid IDs in GraphML edge {(s, r, o)}")
    return sorted(triples), graph_data


def load_training_graph(root: Path) -> tuple[list[tuple[str, str, str]], dict[str, Any]]:
    graphml = root / "outputs" / "phase2" / "training_graph.graphml"
    decisions = json.loads((root / "outputs" / "phase2" / "filtering_decisions.json").read_text(encoding="utf-8"))
    train_path = root / "data" / "train.txt"
    train_sha = m.sha256_file(train_path)
    triples, graph_data = load_phase2_graphml(graphml)
    if graph_data.get("source_sha256") != train_sha or decisions["source_sha256"] != train_sha:
        raise Phase5Error("Phase 2 graph was not built from the current data/train.txt")
    if len(triples) != decisions["unique_valid_triple_count"]:
        raise Phase5Error(f"Phase 2 graph has {len(triples)} edges, decisions say {decisions['unique_valid_triple_count']}")
    return triples, {
        "phase2_graphml": {"path": _rel(graphml, root), "sha256": m.sha256_file(graphml), "edges": len(triples)},
        "phase2_filtering_decisions": {"path": _rel(root / "outputs" / "phase2" / "filtering_decisions.json", root),
                                       "sha256": m.sha256_file(root / "outputs" / "phase2" / "filtering_decisions.json")},
        "training_source_sha256": train_sha,
    }


def _rel(path: Path, root: Path) -> str:
    return m._rel(path, root)


RULE_ATOM = re.compile(r"(P[1-9][0-9]*)\(([xyz]),([xyz])\)")


def parse_rule_text(text: str) -> tuple[list[list[str]], str]:
    body_text, head_text = text.split(" => ")
    body = [list(a) for a in RULE_ATOM.findall(body_text)]
    head = RULE_ATOM.fullmatch(head_text.strip())
    if not body or head is None or head.group(2, 3) != ("x", "z"):
        raise Phase5Error(f"cannot parse rule {text!r}")
    return body, head.group(1)


def load_frozen_rules(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    list_path = root / "outputs" / "phase4" / "phase5_candidate_rules_proposed.json"
    doc = json.loads(list_path.read_text(encoding="utf-8"))
    source = root / doc["source_run"] / m.SELECTED_FILE
    source_sha = m.sha256_file(source)
    if source_sha != doc["source_selected_rules_sha256"]:
        raise Phase5Error("run_grid_ext/selected_rules.json does not match the frozen rule list's source hash")
    source_rules = {r["rule_id"]: r for r in json.loads(source.read_text(encoding="utf-8"))["rules"]}
    rules = []
    for r in doc["rules"]:
        body, head = parse_rule_text(r["rule"])
        src = source_rules.get(r["rule_id"])
        if src is None or src["rule"] != r["rule"] or src["body"] != body or src["head"] != head or r["head"] != head:
            raise Phase5Error(f"rule {r['rule_id']} does not match its source run")
        if m.rule_id(r["rule"]) != r["rule_id"]:
            raise Phase5Error(f"rule id of {r['rule']} is not the hash of its text")
        for key in ("pca_confidence", "wilson_lower", "support", "counting"):
            if src[key] != r[key]:
                raise Phase5Error(f"rule {r['rule_id']} field {key} differs from its source run")
        rules.append({
            **{k: r[k] for k in ("rule_id", "rule", "display", "head", "type", "support", "pca_confidence", "wilson_lower", "counting")},
            "std_confidence": src["std_confidence"],
            "body": body,
            "shape": ev.shape_from_body(body),
        })
    if len({r["rule_id"] for r in rules}) != len(rules):
        raise Phase5Error("duplicate rule ids in the frozen list")
    info = {
        "rule_list": {"path": _rel(list_path, root), "sha256": m.sha256_file(list_path), "rules": len(rules), "status_field": doc["status"]},
        "rule_source": {"path": _rel(source, root), "sha256": source_sha},
    }
    return rules, info


# ---------------------------------------------------------------------- predict


def _id_number(entity: str) -> int:
    return int(entity[1:])


def generate_candidates(kg: m.KG, rules: list[dict[str, Any]]) -> tuple[dict[tuple[int, str, int], list[str]], dict[str, int]]:
    """Round 1: for each rule, body pairs whose head triple is absent from training."""
    N = kg.N
    candidates: dict[tuple[int, str, int], list[str]] = defaultdict(list)
    counts = {"candidate_records": 0, "body_pairs_already_in_training": 0}
    for rule in rules:
        h = rule["head"]
        head_pairs = kg.pairs.get(h, set())
        for code in m.body_pairs(kg, rule["shape"]):
            if code in head_pairs:
                counts["body_pairs_already_in_training"] += 1
                continue
            x, z = divmod(code, N)
            candidates[(x, h, z)].append(rule["rule_id"])
            counts["candidate_records"] += 1
    counts["unique_candidate_triples"] = len(candidates)
    counts["duplicate_records_merged"] = counts["candidate_records"] - len(candidates)
    return candidates, counts


def rank_and_cap(kg: m.KG, candidates: dict[tuple[int, str, int], list[str]], rules_by_id: dict[str, dict[str, Any]],
                 cap: int) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
    names = kg.entities
    by_relation: dict[str, list[tuple[tuple, tuple[int, str, int]]]] = defaultdict(list)
    for key, rule_ids in candidates.items():
        x, h, z = key
        rs = [rules_by_id[r] for r in set(rule_ids)]
        sort_key = (-max(r["wilson_lower"] for r in rs), -max(r["pca_confidence"] for r in rs), -len(rs),
                    _id_number(names[x]), _id_number(names[z]))
        by_relation[h].append((sort_key, key))
    kept, per_relation = [], {}
    for h in sorted(by_relation, key=lambda r: _id_number(r)):
        ranked = sorted(by_relation[h])
        per_relation[h] = {"candidates": len(ranked), "retained": min(cap, len(ranked))}
        for rank, (_, key) in enumerate(ranked[:cap], start=1):
            kept.append((h, rank, key))
    return kept, per_relation


def build_records(kg: m.KG, kept, candidates, rules_by_id, entity_labels, relation_labels) -> list[dict[str, Any]]:
    names = kg.entities
    records = []
    for h, rank, key in kept:
        x, _, z = key
        s, o = names[x], names[z]
        rule_ids = sorted(set(candidates[key]), key=lambda r: (-rules_by_id[r]["wilson_lower"], -rules_by_id[r]["pca_confidence"], r))
        best = rules_by_id[rule_ids[0]]
        supporting = []
        for rid in rule_ids:
            rule = rules_by_id[rid]
            shape = rule["shape"]
            if shape[0] == "1":
                groundings = [m.body_triples(kg, shape, x, None, z)]
            else:
                groundings = [m.body_triples(kg, shape, x, y, z) for y in sorted(m.middles(kg, shape, x, z))]
            if not groundings:
                raise Phase5Error(f"rule {rid} has no grounding for {(s, h, o)}")
            supporting.append({
                "rule_id": rid, "rule": rule["rule"], "display": rule["display"], "type": rule["type"],
                "counting": rule["counting"], "std_confidence": rule["std_confidence"],
                "pca_confidence": rule["pca_confidence"], "wilson_lower": rule["wilson_lower"], "support": rule["support"],
                "grounding_count": len(groundings), "body_groundings": groundings,
            })
        triple_text = f"{s}\t{h}\t{o}"
        records.append({
            "prediction_id": hashlib.sha256(triple_text.encode("utf-8")).hexdigest()[:16],
            "status": "predicted (not asserted; not in training graph)",
            "round": ROUND,
            "relation_rank": rank,
            "triple": {"subject": s, "relation": h, "object": o},
            "labels": {"subject": entity_labels.get(s, s), "relation": relation_labels.get(h, h), "object": entity_labels.get(o, o)},
            "ranking_score": {"name": RANKING_SCORE, "value": best["wilson_lower"], "from_rule_id": best["rule_id"]},
            "tie_break_values": {"max_pca_confidence": max(r["pca_confidence"] for r in supporting),
                                 "supporting_rules": len(supporting)},
            "supporting_rules": supporting,
        })
    return records


# --------------------------------------------------------------------- outputs


def protected_state(root: Path) -> dict[str, dict[str, Any]]:
    paths = {root / p for p in PROTECTED_FILES}
    for pattern in PROTECTED_GLOBS:
        paths.update(root.glob(pattern))
    state = {}
    for path in sorted(paths):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(STAT_ONLY):
            st = os.stat(path)
            state[rel] = {"size": st.st_size, "mtime_ns": st.st_mtime_ns, "opened": False}
        else:
            state[rel] = {"sha256": m.sha256_file(path)}
    return state


def extract_vis_library(phase2_html: Path) -> tuple[str, str]:
    """Return (vis-network JS, vis CSS) embedded in the Phase 2 viewer."""
    html = phase2_html.read_text(encoding="utf-8")
    start = html.find("/**\n * vis-network")
    if start < 0:
        raise Phase5Error("Phase 2 viewer does not embed vis-network")
    end = html.find("</script>", start)
    js = html[start:end]
    if "@version" not in js[:400]:
        raise Phase5Error("unexpected vis-network block in the Phase 2 viewer")
    css = ""
    for match in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S):
        if ".vis-" in match.group(1):
            css = match.group(1)
            break
    return js, css


def render_viewer(records: list[dict[str, Any]], vis_js: str, vis_css: str, relation_labels: dict[str, str]) -> str:
    preds = []
    context: set[tuple[str, str, str]] = set()
    entities: dict[str, str] = {}
    for rec in records:
        t = rec["triple"]
        entities[t["subject"]] = rec["labels"]["subject"]
        entities[t["object"]] = rec["labels"]["object"]
        ev_triples = []
        for rule in rec["supporting_rules"]:
            for g in rule["body_groundings"][:5]:
                for tr in g:
                    ev_triples.append(tr)
                    context.add(tuple(tr))
        preds.append([t["subject"], t["relation"], t["object"], rec["ranking_score"]["value"], rec["relation_rank"],
                      "; ".join(r["rule"] for r in rec["supporting_rules"]), ev_triples, rec["prediction_id"]])
    data = {
        "predictions": preds,
        "relations": sorted({p[1] for p in preds}, key=lambda r: int(r[1:])),
        "relationLabels": {r: relation_labels.get(r, r) for r in {p[1] for p in preds} | {t[1] for t in context}},
        "entityLabels": entities,
    }
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    return VIEWER_TEMPLATE.replace("/*DATA*/", payload).replace("/*VIS_CSS*/", vis_css).replace("/*VIS_JS*/", vis_js)


VIEWER_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phase 5 predictions</title>
<style>/*VIS_CSS*/</style>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f8fafc;color:#172033}
header{padding:12px 16px;border-bottom:1px solid #d6dde8;background:#fff}
h1{font-size:18px;margin:0 0 4px}
.note{font-size:13px;color:#4a5568}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 16px}
select,input{font-size:14px;padding:4px 6px}
#wrap{display:flex;gap:0;flex-wrap:wrap}
#graph{flex:3 1 520px;height:68vh;background:#f8fafc;border-top:1px solid #d6dde8}
#side{flex:1 1 300px;max-height:68vh;overflow:auto;border-top:1px solid #d6dde8;border-left:1px solid #d6dde8;background:#fff;font-size:13px}
#side table{border-collapse:collapse;width:100%}
#side td{padding:4px 6px;border-bottom:1px solid #edf1f7;vertical-align:top;cursor:pointer}
#side tr:hover{background:#eef4ff}
.legend span{display:inline-block;margin-right:12px}
.sw{display:inline-block;width:26px;height:0;border-top:3px dashed;vertical-align:middle;margin-right:4px}
.solid{border-top-style:solid;border-color:#94a3b8}
#detail{padding:8px 16px;font-size:13px;white-space:pre-wrap}
</style></head><body>
<header><h1>Phase 5 rule-based predictions (round 1)</h1>
<div class="note">Predicted triples are <b>not</b> training facts and were not checked against validation or test data.
Dashed edges are predictions; solid grey edges are the training triples that support them.</div>
<div class="note legend"><span><i class="sw solid"></i>training evidence</span>
<span><i class="sw" style="border-color:#2e7d32"></i>score &ge; 0.7</span>
<span><i class="sw" style="border-color:#ef6c00"></i>0.4&ndash;0.7</span>
<span><i class="sw" style="border-color:#c62828"></i>&lt; 0.4</span>
<span>Score = highest Wilson lower bound among supporting rules; line width grows with score.</span></div></header>
<div class="controls">
<label>Relation filter <select id="rel"></select></label>
<label>Show top <select id="topn"><option>10</option><option selected>25</option><option>50</option><option>100</option></select></label>
<label>Entity search <input id="q" placeholder="name or Q-id"></label>
</div>
<div id="wrap"><div id="graph"></div><div id="side"><table id="list"></table></div></div>
<div id="detail">Click a prediction in the list or a dashed edge for its provenance.</div>
<script>/*VIS_JS*/</script>
<script>
const D = /*DATA*/;
const color = s => s >= 0.7 ? "#2e7d32" : (s >= 0.4 ? "#ef6c00" : "#c62828");
const lab = e => (D.entityLabels[e] || e);
const rlab = r => (D.relationLabels[r] || r);
const relSel = document.getElementById("rel"), topSel = document.getElementById("topn"), q = document.getElementById("q");
relSel.innerHTML = '<option value="">all relations</option>' + D.relations.map(r => `<option value="${r}">${rlab(r)} (${r})</option>`).join("");
let network = null, shown = [];
function current(){
  const rel = relSel.value, n = +topSel.value, term = q.value.trim().toLowerCase();
  let ps = D.predictions.filter(p => (!rel || p[1] === rel) && p[4] <= n);
  if (term) ps = ps.filter(p => p[0].toLowerCase() === term || p[2].toLowerCase() === term || lab(p[0]).toLowerCase().includes(term) || lab(p[2]).toLowerCase().includes(term));
  return ps.slice(0, 400);
}
function draw(){
  shown = current();
  const nodes = new Map(), edges = [];
  const addNode = e => { if (!nodes.has(e)) nodes.set(e, {id: e, label: lab(e), title: `${lab(e)} (${e})`}); };
  const seen = new Set();
  shown.forEach((p, i) => {
    addNode(p[0]); addNode(p[2]);
    edges.push({id: "p" + i, from: p[0], to: p[2], label: `${rlab(p[1])} ${p[3].toFixed(2)}`, dashes: true,
      color: {color: color(p[3])}, width: 1 + 4 * p[3], title: `PREDICTED ${p[0]} ${p[1]} ${p[2]}\\nscore ${p[3]} | rank ${p[4]} in ${p[1]}\\nrules: ${p[5]}`});
    p[6].forEach(t => { const k = t.join("|"); if (seen.has(k)) return; seen.add(k); addNode(t[0]); addNode(t[2]);
      edges.push({from: t[0], to: t[2], label: rlab(t[1]), color: {color: "#94a3b8"}, width: 1, title: `training: ${t[0]} ${t[1]} ${t[2]}`}); });
  });
  const data = {nodes: new vis.DataSet([...nodes.values()]), edges: new vis.DataSet(edges)};
  const options = {nodes: {shape: "dot", size: 12, font: {size: 13}}, edges: {arrows: {to: {enabled: true, scaleFactor: 0.6}}, font: {size: 10, align: "middle"}, smooth: false},
    physics: {solver: "barnesHut", stabilization: {iterations: 150}}, interaction: {hover: true, navigationButtons: true}};
  if (network) network.destroy();
  network = new vis.Network(document.getElementById("graph"), data, options);
  network.on("click", ev => { if (ev.edges.length && String(ev.edges[0]).startsWith("p")) detail(shown[+String(ev.edges[0]).slice(1)]); });
  document.getElementById("list").innerHTML = shown.map((p, i) => `<tr data-i="${i}"><td>${p[4]}</td><td>${lab(p[0])} &rarr; <b>${rlab(p[1])}</b> &rarr; ${lab(p[2])}</td><td style="color:${color(p[3])}">${p[3].toFixed(3)}</td></tr>`).join("");
  document.querySelectorAll("#list tr").forEach(tr => tr.onclick = () => detail(shown[+tr.dataset.i]));
}
function detail(p){
  document.getElementById("detail").textContent = `${lab(p[0])} (${p[0]}) — ${rlab(p[1])} (${p[1]}) → ${lab(p[2])} (${p[2]})\\n` +
    `prediction ${p[7]} | score ${p[3]} | rank ${p[4]} in ${p[1]} | round 1\\nsupporting rules: ${p[5]}\\n` +
    `training evidence shown (up to 5 groundings per rule):\\n` + p[6].map(t => `  ${lab(t[0])} (${t[0]}) —${t[1]}→ ${lab(t[2])} (${t[2]})`).join("\\n");
}
[relSel, topSel].forEach(el => el.onchange = draw); q.oninput = () => { clearTimeout(window._t); window._t = setTimeout(draw, 250); };
draw();
</script></body></html>
"""


def render_report(records, per_relation, counts, settings, inputs, relation_labels) -> str:
    total = len(records)
    tiers = Counter("≥ 0.7" if r["ranking_score"]["value"] >= 0.7 else ("0.4–0.7" if r["ranking_score"]["value"] >= 0.4 else "< 0.4") for r in records)
    multi = sum(1 for r in records if len(r["supporting_rules"]) > 1)
    lines = [
        "# Phase 5: rule-based predictions (round 1)",
        "",
        "Predicted triples are **hypotheses**, not facts. They come from statistical rule patterns in",
        "the training graph and were **not** checked against validation or test data (that is Phase 6).",
        "",
        f"- Training graph: `{inputs['phase2_graphml']['path']}` ({inputs['phase2_graphml']['edges']:,} edges)",
        f"- Rules: `{inputs['rule_list']['path']}` ({inputs['rule_list']['rules']} frozen rules, SHA-256 `{inputs['rule_list']['sha256'][:12]}…`)",
        f"- Rounds: {settings['rounds']}; cap: {settings['cap_per_relation']} per relation",
        f"- Ranking score: `{settings['ranking_score']}` = highest Wilson lower bound among the supporting rules",
        f"- Tie-break: {', '.join(settings['tie_break'])}",
        "",
        "## Counts",
        "",
        f"- Candidate records (rule × pair): {counts['candidate_records']:,}",
        f"- Body pairs skipped because the head triple is already in training: {counts['body_pairs_already_in_training']:,}",
        f"- Duplicate records merged (same triple from several rules): {counts['duplicate_records_merged']:,}",
        f"- Unique candidate triples: {counts['unique_candidate_triples']:,}",
        f"- Retained after the per-relation cap: **{total:,}** ({multi:,} supported by more than one rule)",
        f"- Score tiers: " + ", ".join(f"{k}: {v:,}" for k, v in sorted(tiers.items())),
        "",
        "## Per relation",
        "",
        "| Relation | Candidates | Retained | Top score | Lowest retained score |",
        "|---|---:|---:|---:|---:|",
    ]
    by_rel = defaultdict(list)
    for r in records:
        by_rel[r["triple"]["relation"]].append(r)
    for h, v in per_relation.items():
        rs = by_rel[h]
        lines.append(f"| {relation_labels.get(h, h)} ({h}) | {v['candidates']:,} | {v['retained']} | "
                     f"{rs[0]['ranking_score']['value']:.3f} | {rs[-1]['ranking_score']['value']:.3f} |")
    lines += ["", "## Top 3 predictions per relation", ""]
    for h in per_relation:
        lines.append(f"**{relation_labels.get(h, h)} ({h})**")
        for r in by_rel[h][:3]:
            t, l = r["triple"], r["labels"]
            rule = r["supporting_rules"][0]
            g = rule["body_groundings"][0]
            evidence = "; ".join(f"{a} {p} {b}" for a, p, b in g)
            lines.append(f"- #{r['relation_rank']} {l['subject']} ({t['subject']}) → {l['object']} ({t['object']}) — score {r['ranking_score']['value']:.3f}; "
                         f"{len(r['supporting_rules'])} rule(s); best `{rule['rule']}`; evidence: {evidence}")
        lines.append("")
    lines += [
        "## Limitations",
        "",
        "- Rule scores are training statistics, not calibrated probabilities; a high score is not proof that a triple is true.",
        "- Scores of 8 couple-counted rules are per couple, the others per ordered pair; both are Wilson lower bounds on the same 0–1 scale.",
        "- Hub entities (for example Q30) can generate many candidates; the cap keeps only the top 100 per relation.",
        "- One round only: no prediction is used as evidence for another.",
        "- The Phase 2 graph was read from its GraphML export (networkx/pyvis not available here); it is checked against train.txt.",
        "- No validation or test scoring was done (Phase 6).",
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, out_dir: Path | None = None, cap: int = DEFAULT_CAP) -> dict[str, Path]:
    out_dir = out_dir or root / "outputs" / "phase5"
    targets = {"predictions": out_dir / PREDICTIONS_FILE, "report": out_dir / REPORT_FILE,
               "viewer": out_dir / VIEWER_FILE, "manifest": out_dir / MANIFEST_FILE}
    existing = [str(p) for p in targets.values() if p.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(existing))
    started = time.time()
    state_before = protected_state(root)

    triples, graph_info = load_training_graph(root)
    rules, rule_info = load_frozen_rules(root)
    entity_labels = m.p3.load_label_map(root / "data" / "entity_labels.json")
    relation_labels = m.p3.load_label_map(root / "data" / "relation_labels.json")
    phase2_html = root / "outputs" / "phase2" / "interactive_graph.html"
    vis_js, vis_css = extract_vis_library(phase2_html)

    kg = m.KG(triples)
    rules_by_id = {r["rule_id"]: r for r in rules}
    candidates, counts = generate_candidates(kg, rules)
    kept, per_relation = rank_and_cap(kg, candidates, rules_by_id, cap)
    records = build_records(kg, kept, candidates, rules_by_id, entity_labels, relation_labels)

    train_set = set(triples)
    if any((r["triple"]["subject"], r["triple"]["relation"], r["triple"]["object"]) in train_set for r in records):
        raise Phase5Error("a prediction is already a training triple")

    settings = {"rounds": ROUND, "cap_per_relation": cap, "ranking_score": RANKING_SCORE, "tie_break": TIE_BREAK,
                "candidate_scope": "body pairs of frozen rules on training facts, head triple absent from training, x != z"}
    inputs = {**graph_info, **rule_info,
              "entity_labels": {"path": "data/entity_labels.json", "sha256": m.sha256_file(root / "data" / "entity_labels.json")},
              "relation_labels": {"path": "data/relation_labels.json", "sha256": m.sha256_file(root / "data" / "relation_labels.json")},
              "phase2_viewer_library_source": {"path": _rel(phase2_html, root), "sha256": m.sha256_file(phase2_html)}}
    predictions_doc = {
        "phase": "5", "tool": NAME, "version": VERSION, "round": ROUND, "settings": settings,
        "note": "Predicted triples only; never merged into the training graph. Not scored against validation or test data.",
        "predictions": records,
    }
    predictions_text = m._json(predictions_doc)
    report_text = render_report(records, per_relation, counts, settings, inputs, relation_labels)
    viewer_text = render_viewer(records, vis_js, vis_css, relation_labels)

    state_after = protected_state(root)
    if state_after != state_before:
        raise Phase5Error("protected files changed during prediction")
    manifest = {
        "phase": "5", "tool": NAME, "version": VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "runtime_seconds": round(time.time() - started, 1),
        "inputs": inputs, "settings": settings,
        "counts": {**counts, "retained_predictions": len(records), "relations_with_predictions": len(per_relation),
                   "per_relation": per_relation, "rules_used": len(rules),
                   "rules_with_retained_predictions": len({s["rule_id"] for r in records for s in r["supporting_rules"]})},
        "outputs": {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in
                    ((PREDICTIONS_FILE, predictions_text), (REPORT_FILE, report_text), (VIEWER_FILE, viewer_text))},
        "files_not_opened": "data/valid*, data/test* (size and mtime recorded only)",
        "protected_files": state_before, "protected_files_unchanged": True,
        "scored_against_validation_or_test": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    m._write_new(targets["predictions"], predictions_text)
    m._write_new(targets["report"], report_text)
    m._write_new(targets["viewer"], viewer_text)
    m._write_new(targets["manifest"], m._json(manifest))
    return targets


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cap", type=int, default=DEFAULT_CAP, help="maximum predictions kept per relation")
    parser.add_argument("--out-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(list(argv) if argv is not None else None)
    for name, path in run(ROOT, args.out_dir, args.cap).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
