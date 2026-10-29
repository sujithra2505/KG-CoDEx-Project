"""Build and export a display-labelled graph from CoDEx-M training triples."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
from pyvis.network import Network

from display_labels import DisplayLabels


ROOT = Path(__file__).resolve().parent
TRAIN_PATH = ROOT / "data" / "train.txt"
OUTPUT_DIR = ROOT / "outputs" / "phase2"
INITIAL_ENTITY_ID = "Q30"
NEIGHBORHOOD_EDGE_LIMIT = 300
NEIGHBORHOOD_NODE_LIMIT = 120
RELATION_EDGE_LIMIT = 500
RELATION_NODE_LIMIT = 400


@dataclass
class GraphBuild:
    graph: nx.MultiDiGraph
    unique_triples: tuple[tuple[str, str, str], ...]
    relation_counts: Counter[str]
    decisions: dict[str, Any]


def _triple_sort_key(triple: tuple[str, str, str]) -> tuple[str, str, str]:
    return triple


def load_training_graph(
    training_path: Path = TRAIN_PATH, labels: DisplayLabels | None = None
) -> GraphBuild:
    """Parse training rows and deduplicate only exact (subject, relation, object) tuples."""
    labels = labels or DisplayLabels()
    raw_bytes = training_path.read_bytes()
    rows = raw_bytes.decode("utf-8-sig").splitlines()
    seen: dict[tuple[str, str, str], int] = {}
    unique_triples: list[tuple[str, str, str]] = []
    malformed_rows: list[dict[str, Any]] = []
    duplicate_rows: list[dict[str, Any]] = []
    valid_row_count = 0

    for line_number, row in enumerate(rows, start=1):
        fields = row.split("\t")
        if len(fields) != 3:
            malformed_rows.append(
                {
                    "line": line_number,
                    "reason": f"expected 3 tab-separated fields, found {len(fields)}",
                    "raw_row": row,
                }
            )
            continue
        if any(not field.strip() for field in fields):
            malformed_rows.append(
                {
                    "line": line_number,
                    "reason": "one or more identifiers are empty or whitespace-only",
                    "raw_row": row,
                }
            )
            continue
        if any(field != field.strip() for field in fields):
            malformed_rows.append(
                {
                    "line": line_number,
                    "reason": "identifier contains leading or trailing whitespace",
                    "raw_row": row,
                }
            )
            continue

        subject_id, relation_id, object_id = fields
        triple = (subject_id, relation_id, object_id)
        valid_row_count += 1
        if triple in seen:
            duplicate_rows.append(
                {"line": line_number, "duplicate_of_line": seen[triple], "triple": list(triple)}
            )
            continue
        seen[triple] = line_number
        unique_triples.append(triple)

    graph = nx.MultiDiGraph(
        source_file=str(training_path.resolve()),
        source_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        construction="CoDEx-M training triples only; no inferred edges",
    )
    relation_counts: Counter[str] = Counter()
    for subject_id, relation_id, object_id in unique_triples:
        for entity_id in (subject_id, object_id):
            if entity_id not in graph:
                label = labels.entity_label(entity_id)
                graph.add_node(
                    entity_id,
                    entity_id=entity_id,
                    label=label,
                    title=f"{label} ({entity_id})",
                )
        relation_label = labels.relation_label(relation_id)
        graph.add_edge(
            subject_id,
            object_id,
            key=relation_id,
            relation_id=relation_id,
            label=relation_label,
            title=f"{relation_label} ({relation_id})",
        )
        relation_counts[relation_id] += 1

    decisions: dict[str, Any] = {
        "source_file": str(training_path.resolve()),
        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "format": "UTF-8 text, one subject<TAB>relation<TAB>object triple per row",
        "row_count": len(rows),
        "valid_row_count_before_deduplication": valid_row_count,
        "malformed_row_count": len(malformed_rows),
        "malformed_rows": malformed_rows,
        "exact_duplicate_count": len(duplicate_rows),
        "duplicate_rows_removed": duplicate_rows,
        "unique_valid_triple_count": len(unique_triples),
        "policy": [
            "Only train.txt is used for graph construction.",
            "Rows must contain exactly three non-empty tab-separated identifiers.",
            "Whitespace surrounding an identifier is rejected rather than silently changed.",
            "Only identical (subject, relation, object) tuples are duplicates.",
            "Different relation IDs between the same subject and object are retained.",
            "No frequency, label, semantic, validation, or test-based filtering is applied.",
        ],
    }
    if graph.number_of_edges() != len(unique_triples):
        raise RuntimeError(
            "Graph edge count does not equal the number of unique valid triples"
        )
    return GraphBuild(graph, tuple(unique_triples), relation_counts, decisions)


def _graph_triples(graph: nx.MultiDiGraph) -> list[tuple[str, str, str]]:
    return sorted(
        (subject, relation_id, object_id)
        for subject, object_id, relation_id in graph.edges(keys=True)
    )


def _selected_edges(
    triples: list[tuple[str, str, str]],
    selected_entity: str | None = None,
    relation_id: str | None = None,
    edge_limit: int = NEIGHBORHOOD_EDGE_LIMIT,
    node_limit: int = NEIGHBORHOOD_NODE_LIMIT,
) -> list[tuple[str, str, str]]:
    if selected_entity is not None:
        candidates = [
            triple
            for triple in triples
            if triple[0] == selected_entity or triple[2] == selected_entity
        ]
    elif relation_id is not None:
        candidates = [triple for triple in triples if triple[1] == relation_id]
    else:
        candidates = []

    selected: list[tuple[str, str, str]] = []
    nodes = {selected_entity} if selected_entity is not None else set()
    for triple in candidates:
        new_nodes = {triple[0], triple[2]} - nodes
        if len(selected) >= edge_limit or len(nodes) + len(new_nodes) > node_limit:
            continue
        selected.append(triple)
        nodes.update(new_nodes)
    return selected


def _example_string(
    triple: tuple[str, str, str], labels: DisplayLabels
) -> str:
    subject_id, relation_id, object_id = triple
    return (
        f"{labels.prediction_entity(subject_id)} -- "
        f"{labels.prediction_relation(relation_id)} --> "
        f"{labels.prediction_entity(object_id)}"
    )


def _javascript_json(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("&", r"\u0026")
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
        .replace("\u2028", r"\u2028")
        .replace("\u2029", r"\u2029")
    )


def _relationship_analysis(
    build: GraphBuild, labels: DisplayLabels
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    examples: dict[str, tuple[str, str, str]] = {}
    for triple in build.unique_triples:
        examples.setdefault(triple[1], triple)
    relation_rows = [
        {
            "relation_id": relation_id,
            "label": labels.relation_label(relation_id),
            "count": count,
            "example_triple": list(examples[relation_id]),
            "example_display": _example_string(examples[relation_id], labels),
        }
        for relation_id, count in build.relation_counts.most_common()
    ]

    incoming_by_entity: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    outgoing_by_entity: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for triple in build.unique_triples:
        subject_id, _, object_id = triple
        outgoing_by_entity[subject_id].append(triple)
        incoming_by_entity[object_id].append(triple)

    pair_counts: Counter[tuple[str, str]] = Counter()
    pair_examples: dict[
        tuple[str, str], tuple[tuple[str, str, str], tuple[str, str, str]]
    ] = {}
    for pivot in sorted(set(incoming_by_entity) & set(outgoing_by_entity)):
        incoming = sorted(incoming_by_entity[pivot])
        outgoing = sorted(outgoing_by_entity[pivot])
        incoming_counts = Counter(triple[1] for triple in incoming)
        outgoing_counts = Counter(triple[1] for triple in outgoing)
        for first_relation, first_count in incoming_counts.items():
            for second_relation, second_count in outgoing_counts.items():
                pair_counts[(first_relation, second_relation)] += (
                    first_count * second_count
                )
        for first in incoming:
            for second in outgoing:
                key = (first[1], second[1])
                if key not in pair_examples:
                    pair_examples[key] = (first, second)

    two_hop_rows = []
    for (first_relation, second_relation), count in pair_counts.most_common(10):
        first, second = pair_examples[(first_relation, second_relation)]
        two_hop_rows.append(
            {
                "first_relation_id": first_relation,
                "first_relation_label": labels.relation_label(first_relation),
                "second_relation_id": second_relation,
                "second_relation_label": labels.relation_label(second_relation),
                "observed_training_paths": count,
                "shared_entity_id": first[2],
                "shared_entity_label": labels.entity_label(first[2]),
                "first_triple": list(first),
                "second_triple": list(second),
                "first_display": _example_string(first, labels),
                "second_display": _example_string(second, labels),
            }
        )
    return relation_rows, two_hop_rows


def _write_interactive_html(
    build: GraphBuild,
    labels: DisplayLabels,
    output_path: Path,
    relation_rows: list[dict[str, Any]],
) -> None:
    all_triples = _graph_triples(build.graph)
    entities = [
        [entity_id, build.graph.nodes[entity_id]["label"]]
        for entity_id in sorted(build.graph.nodes)
    ]
    relations = [
        [row["relation_id"], row["label"]] for row in relation_rows
    ]
    initial_entity = (
        INITIAL_ENTITY_ID
        if INITIAL_ENTITY_ID in build.graph
        else min(build.graph.nodes, default=None)
    )
    initial_triples = _selected_edges(
        all_triples, selected_entity=initial_entity
    )

    network = Network(
        height="68vh",
        width="100%",
        directed=True,
        bgcolor="#f8fafc",
        font_color="#172033",
        cdn_resources="in_line",
    )
    network.set_options(
        """
        {
          "nodes": {"shape": "dot", "size": 16, "font": {"size": 14}},
          "edges": {
            "arrows": {"to": {"enabled": true, "scaleFactor": 0.65}},
            "font": {"size": 11, "align": "middle"},
            "smooth": {"enabled": false}
          },
          "interaction": {
            "hover": true, "navigationButtons": true, "keyboard": true,
            "multiselect": true
          },
          "physics": {
            "enabled": true, "solver": "barnesHut",
            "stabilization": {"iterations": 150}
          }
        }
        """
    )
    for subject_id, relation_id, object_id in initial_triples:
        for entity_id in (subject_id, object_id):
            if entity_id not in network.get_nodes():
                label = labels.entity_label(entity_id)
                network.add_node(
                    entity_id,
                    label=label,
                    title=f"{label} ({entity_id})",
                )
        relation_label = labels.relation_label(relation_id)
        network.add_edge(
            subject_id,
            object_id,
            id=f"{subject_id}|{relation_id}|{object_id}",
            label=relation_label,
            title=f"{relation_label} ({relation_id})",
            arrows="to",
        )
    if initial_entity is not None and initial_entity not in network.get_nodes():
        label = labels.entity_label(initial_entity)
        network.add_node(initial_entity, label=label, title=f"{label} ({initial_entity})")

    html = network.generate_html(notebook=False)
    controls = """
    <section id="phase2-controls">
      <h1>CoDEx-M training graph explorer</h1>
      <p id="graph-summary"></p>
      <div class="control-row">
        <label for="entity-search">Find entity by name or ID</label>
        <input id="entity-search" type="search" placeholder="e.g. United States or Q30" autocomplete="off">
        <button id="entity-search-button">Find</button>
        <select id="entity-matches" aria-label="Matching entities"></select>
        <button id="neighborhood-button">Show neighborhood</button>
      </div>
      <div class="control-row">
        <label for="relation-filter">Relation filter</label>
        <select id="relation-filter"></select>
        <button id="relation-button">Show relation</button>
        <button id="fit-button">Fit view</button>
      </div>
      <p id="view-status" role="status"></p>
      <div id="entity-inspector"><strong>Selected entity relationships</strong><div id="relationship-details"></div></div>
      <p class="legend"><strong>Legend:</strong> circles are entities; arrows are directed training triples;
      edge text is the readable relation label. Hover for IDs. Search or click a node to inspect its
      one-hop neighborhood and incoming/outgoing triples. Relation mode shows a deterministic capped
      view for one relation type. These are views of the complete training graph, not filtered graph data
      exports.</p>
    </section>
    """
    script = """
    <script>
    const phase2Entities = __ENTITIES__;
    const phase2Triples = __TRIPLES__;
    const phase2Relations = __RELATIONS__;
    const entityById = new Map(phase2Entities.map(([id, label]) => [id, label]));
    const relationById = new Map(phase2Relations.map(([id, label]) => [id, label]));
    const entitySearch = document.getElementById("entity-search");
    const entityMatches = document.getElementById("entity-matches");
    const relationFilter = document.getElementById("relation-filter");
    const status = document.getElementById("view-status");
    const relationshipDetails = document.getElementById("relationship-details");
    let activeEntity = __INITIAL_ENTITY__;
    const neighborhoodEdgeLimit = __NEIGHBORHOOD_EDGE_LIMIT__;
    const neighborhoodNodeLimit = __NEIGHBORHOOD_NODE_LIMIT__;
    const relationEdgeLimit = __RELATION_EDGE_LIMIT__;
    const relationNodeLimit = __RELATION_NODE_LIMIT__;
    document.getElementById("graph-summary").textContent =
      `Complete graph: ${phase2Entities.length.toLocaleString()} entities, ` +
      `${phase2Triples.length.toLocaleString()} unique directed relation-labelled triples. ` +
      `Only a manageable subgraph is drawn at once.`;

    function entityOptionText(id) {
      return `${entityById.get(id) || id} (${id})`;
    }
    for (const [id, label] of phase2Relations) {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = `${label} (${id})`;
      relationFilter.append(option);
    }
    function findEntities(query) {
      const q = query.trim().toLocaleLowerCase();
      if (!q) return [];
      const exactId = phase2Entities.find(([id]) => id.toLocaleLowerCase() === q);
      if (exactId) return [exactId[0]];
      const exactLabels = phase2Entities.filter(([, label]) => label.toLocaleLowerCase() === q);
      if (exactLabels.length) return exactLabels.map(([id]) => id);
      return phase2Entities
        .filter(([id, label]) => id.toLocaleLowerCase().includes(q) || label.toLocaleLowerCase().includes(q))
        .slice(0, 100)
        .map(([id]) => id);
    }
    function refreshEntityMatches() {
      const matches = findEntities(entitySearch.value);
      entityMatches.replaceChildren();
      for (const id of matches) {
        const option = document.createElement("option");
        option.value = id;
        option.textContent = entityOptionText(id);
        entityMatches.append(option);
      }
      if (matches.length) entityMatches.value = matches[0];
    }
    entitySearch.addEventListener("input", refreshEntityMatches);

    function showInspector(entityId) {
      activeEntity = entityId;
      entitySearch.value = entityId;
      const incoming = [];
      const outgoing = [];
      for (const [subject, relation, object] of phase2Triples) {
        if (object === entityId) incoming.push([subject, relation, object]);
        if (subject === entityId) outgoing.push([subject, relation, object]);
      }
      function rows(items) {
        const cap = 40;
        const lines = items.slice(0, cap).map(([subject, relation, object]) => {
          const other = subject === entityId ? object : subject;
          const arrow = subject === entityId ? "→" : "←";
          return `<li>${arrow} ${escapeHtml(entityById.get(other) || other)} (${escapeHtml(other)}) — ` +
            `${escapeHtml(relationById.get(relation) || relation)} (${escapeHtml(relation)})</li>`;
        }).join("");
        const more = items.length > cap ? `<li>… ${items.length - cap} more</li>` : "";
        return `<ul>${lines}${more}</ul>`;
      }
      relationshipDetails.innerHTML =
        `<p><strong>${escapeHtml(entityOptionText(entityId))}</strong>` +
        ` — ${incoming.length} incoming, ${outgoing.length} outgoing triples</p>` +
        `<div class="inspector-columns"><div><strong>Incoming</strong>${rows(incoming)}</div>` +
        `<div><strong>Outgoing</strong>${rows(outgoing)}</div></div>`;
    }
    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, ch =>
        ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
    }
    function renderTriples(candidates, selectedEntity, edgeLimit, nodeLimit, description) {
      const selected = [];
      const visibleNodes = new Set(selectedEntity ? [selectedEntity] : []);
      for (const triple of candidates) {
        const [subject, relation, object] = triple;
        const newNodes = [subject, object].filter(id => !visibleNodes.has(id));
        if (selected.length >= edgeLimit || visibleNodes.size + new Set(newNodes).size > nodeLimit) continue;
        selected.push(triple);
        visibleNodes.add(subject); visibleNodes.add(object);
      }
      nodes.clear();
      edges.clear();
      for (const id of [...visibleNodes].sort()) {
        const label = entityById.get(id) || id;
        nodes.add({id, label, title: `${label} (${id})`});
      }
      for (const [subject, relation, object] of selected) {
        const label = relationById.get(relation) || relation;
        edges.add({
          id: `${subject}|${relation}|${object}`,
          from: subject, to: object, label,
          title: `${label} (${relation})`, arrows: "to"
        });
      }
      if (selectedEntity) network.selectNodes([selectedEntity]);
      network.fit({animation: true});
      status.textContent =
        `${description}: showing ${selected.length.toLocaleString()} of ` +
        `${candidates.length.toLocaleString()} matching triples and ` +
        `${visibleNodes.size.toLocaleString()} entities. ` +
        `Stable ID/triple order is used when display caps apply.`;
      if (selectedEntity) showInspector(selectedEntity);
      else relationshipDetails.textContent = "Select an entity in the graph to inspect its relationships.";
    }
    function showNeighborhood(entityId) {
      if (!entityById.has(entityId)) {
        status.textContent = "Entity ID was not found in the training graph.";
        return;
      }
      const matches = phase2Triples.filter(([subject, , object]) =>
        subject === entityId || object === entityId);
      renderTriples(matches, entityId, neighborhoodEdgeLimit, neighborhoodNodeLimit,
        `One-hop neighborhood of ${entityOptionText(entityId)}`);
    }
    document.getElementById("entity-search-button").addEventListener("click", () => {
      refreshEntityMatches();
      if (!entityMatches.options.length) {
        status.textContent = "No matching entity found in the training graph.";
        return;
      }
      showNeighborhood(entityMatches.value);
      if (findEntities(entitySearch.value).length > 1) {
        status.textContent += " If this is not the intended match, choose another candidate and show its neighborhood.";
      }
    });
    document.getElementById("neighborhood-button").addEventListener("click", () => {
      const matches = findEntities(entitySearch.value);
      const entityId = matches.includes(entityMatches.value) ? entityMatches.value : matches[0];
      if (entityId) showNeighborhood(entityId);
      else status.textContent = "Enter a readable entity name or ID, then choose a match.";
    });
    document.getElementById("relation-button").addEventListener("click", () => {
      const relationId = relationFilter.value;
      const matches = phase2Triples.filter(([, relation]) => relation === relationId);
      renderTriples(matches, null, relationEdgeLimit, relationNodeLimit,
        `Relation filter ${relationById.get(relationId) || relationId} (${relationId})`);
    });
    document.getElementById("fit-button").addEventListener("click", () => network.fit({animation: true}));
    network.on("selectNode", event => {
      if (event.nodes.length) showNeighborhood(String(event.nodes[0]));
    });
    network.on("deselectNode", () => {});
    showNeighborhood(activeEntity);
    </script>
    """
    script = (
        script.replace("__ENTITIES__", _javascript_json(entities))
        .replace("__TRIPLES__", _javascript_json(all_triples))
        .replace("__RELATIONS__", _javascript_json(relations))
        .replace("__INITIAL_ENTITY__", _javascript_json(initial_entity))
        .replace("__NEIGHBORHOOD_EDGE_LIMIT__", str(NEIGHBORHOOD_EDGE_LIMIT))
        .replace("__NEIGHBORHOOD_NODE_LIMIT__", str(NEIGHBORHOOD_NODE_LIMIT))
        .replace("__RELATION_EDGE_LIMIT__", str(RELATION_EDGE_LIMIT))
        .replace("__RELATION_NODE_LIMIT__", str(RELATION_NODE_LIMIT))
    )
    style = """
    <style>
      body { margin: 0; background: #f8fafc; font-family: Segoe UI, Arial, sans-serif; color: #172033; }
      #phase2-controls { padding: 14px 18px; background: white; border-bottom: 1px solid #d5deea; }
      #phase2-controls h1 { margin: 0 0 6px; font-size: 20px; }
      #phase2-controls p { margin: 8px 0; }
      .control-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 8px 0; }
      input, select, button { padding: 7px 9px; font-size: 14px; }
      #entity-search { width: min(360px, 42vw); }
      #entity-matches { width: min(440px, 48vw); }
      button { cursor: pointer; }
      #view-status { color: #334e68; min-height: 1.2em; }
      #entity-inspector { max-height: 230px; overflow: auto; padding: 9px; background: #f1f5f9; border-radius: 6px; }
      .inspector-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
      .inspector-columns ul { margin-top: 4px; padding-left: 18px; }
      .inspector-columns li { margin: 3px 0; }
      .legend { color: #475569; font-size: 13px; }
      #mynetwork { height: 68vh !important; }
      @media (max-width: 700px) { .inspector-columns { grid-template-columns: 1fr; } }
    </style>
    """
    html = html.replace("<body>", f"<body>\n{style}\n{controls}", 1)
    html = html.replace("</body>", f"{script}\n</body>", 1)
    output_path.write_text(html, encoding="utf-8")


def _write_relationship_report(
    build: GraphBuild,
    labels: DisplayLabels,
    output_path: Path,
    relation_rows: list[dict[str, Any]],
    two_hop_rows: list[dict[str, Any]],
) -> None:
    graph = build.graph
    lines = [
        "# Phase 2: Training Graph and Relationship Analysis",
        "",
        "## Scope and construction",
        "",
        "The graph was constructed from `data/train.txt` only. Validation, test,",
        "and negative-example files were not loaded for graph construction.",
        "Each unique valid `(subject ID, relation ID, object ID)` tuple becomes",
        "one directed edge in a NetworkX `MultiDiGraph`. This preserves separate",
        "relation types between the same entities. Node and edge keys remain the",
        "original IDs; readable labels are presentation attributes only.",
        "",
        f"- Original training rows: {build.decisions['row_count']:,}",
        f"- Valid parsed rows before deduplication: {build.decisions['valid_row_count_before_deduplication']:,}",
        f"- Malformed rows recorded and excluded: {build.decisions['malformed_row_count']:,}",
        f"- Exact duplicate rows excluded: {build.decisions['exact_duplicate_count']:,}",
        f"- Unique valid training triples / graph edges: {graph.number_of_edges():,}",
        f"- Entities / graph nodes: {graph.number_of_nodes():,}",
        f"- Relation types: {len(build.relation_counts):,}",
        f"- Training file SHA-256: `{build.decisions['source_sha256']}`",
        "",
        "Malformed rows, duplicate line numbers, the original-file hash, and",
        "the filtering policy are recorded in `filtering_decisions.json`.",
        "No frequency- or label-based filtering was applied.",
        "",
        "## Relation frequencies",
        "",
        "Counts are unique training triples per relation. Examples are actual",
        "source triples and display both readable labels and original IDs.",
        "",
        "| Count | Relation | Example training triple |",
        "|---:|---|---|",
    ]
    for row in relation_rows[:20]:
        lines.append(
            f"| {row['count']:,} | {row['label']} (`{row['relation_id']}`) "
            f"| {row['example_display']} |"
        )
    lines.extend(
        [
            "",
            "All relation counts and examples are available in `graph_statistics.json`.",
            "",
            "## Repeated two-hop path observations",
            "",
            "These are adjacent directed training-triple paths sharing the middle",
            "entity. They are descriptive observations—not inference rules,",
            "validated implications, or evidence for a missing edge. Counts are",
            "path occurrences and can be large around high-degree entities.",
            "",
        ]
    )
    for index, row in enumerate(two_hop_rows, start=1):
        lines.extend(
            [
                f"{index}. **{row['observed_training_paths']:,} paths:** "
                f"{row['first_relation_label']} (`{row['first_relation_id']}`) → "
                f"{row['second_relation_label']} (`{row['second_relation_id']}`)",
                f"   - {row['first_display']}",
                f"   - {row['second_display']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Semantic compatibility and limitations",
            "",
            "The local label mappings provide names but no entity types, relation",
            "domain/range declarations, or relation descriptions. Consequently,",
            "this phase cannot substantiate domain/range violations or semantic",
            "incompatibilities. Unusual-looking or rare triples are retained for",
            "manual review; no fact is marked false or removed based on frequency.",
            "",
            "The interactive HTML bundles the complete training-edge data for",
            "client-side search and filtering, but draws only a bounded view at a",
            "time. Its initial view is the one-hop neighborhood of the stable",
            "entity ID `Q30` (United States of America), capped at 300 edges and",
            "120 nodes. Relation mode is capped at 500 edges and 400 nodes, in",
            "stable ID/triple order. The entity inspector shows counts for all",
            "incoming/outgoing triples and lists up to 40 in each direction.",
            "The complete graph remains in",
            "`training_graph.graphml` and in the HTML's bundled data.",
            "",
            "No ontology generation, rule learning, inferred edges, edge",
            "prediction, or final evaluation was performed.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_phase2_outputs(
    build: GraphBuild, output_dir: Path = OUTPUT_DIR, labels: DisplayLabels | None = None
) -> dict[str, Path]:
    labels = labels or DisplayLabels()
    output_dir.mkdir(parents=True, exist_ok=True)
    relation_rows, two_hop_rows = _relationship_analysis(build, labels)
    stats = {
        "source_file": build.decisions["source_file"],
        "source_sha256": build.decisions["source_sha256"],
        "original_training_rows": build.decisions["row_count"],
        "valid_rows_before_deduplication": build.decisions[
            "valid_row_count_before_deduplication"
        ],
        "malformed_rows": build.decisions["malformed_row_count"],
        "exact_duplicate_rows": build.decisions["exact_duplicate_count"],
        "unique_valid_triples": len(build.unique_triples),
        "graph_edges": build.graph.number_of_edges(),
        "graph_nodes": build.graph.number_of_nodes(),
        "relation_types": len(build.relation_counts),
        "relation_frequencies": relation_rows,
        "repeated_two_hop_path_observations": two_hop_rows,
        "graph_type": "NetworkX MultiDiGraph",
        "construction_scope": "train.txt only; no inferred edges",
    }
    if stats["graph_edges"] != stats["unique_valid_triples"]:
        raise RuntimeError("Graph edge count does not equal the unique triple count")

    stats_path = output_dir / "graph_statistics.json"
    decisions_path = output_dir / "filtering_decisions.json"
    graphml_path = output_dir / "training_graph.graphml"
    analysis_path = output_dir / "relationship_analysis.md"
    html_path = output_dir / "interactive_graph.html"

    stats_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    decisions_path.write_text(
        json.dumps(build.decisions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    nx.write_graphml(build.graph, graphml_path)
    _write_relationship_report(
        build, labels, analysis_path, relation_rows, two_hop_rows
    )
    _write_interactive_html(build, labels, html_path, relation_rows)
    return {
        "statistics": stats_path,
        "decisions": decisions_path,
        "graphml": graphml_path,
        "analysis": analysis_path,
        "html": html_path,
    }


def build_phase2_outputs(
    training_path: Path = TRAIN_PATH,
    output_dir: Path = OUTPUT_DIR,
    labels: DisplayLabels | None = None,
) -> tuple[GraphBuild, dict[str, Path]]:
    labels = labels or DisplayLabels()
    build = load_training_graph(training_path, labels)
    return build, write_phase2_outputs(build, output_dir, labels)


if __name__ == "__main__":
    result, output_paths = build_phase2_outputs()
    print(
        "Training rows={:,}; valid={:,}; malformed={:,}; exact duplicates={:,}; "
        "unique triples/edges={:,}; entities={:,}; relations={:,}".format(
            result.decisions["row_count"],
            result.decisions["valid_row_count_before_deduplication"],
            result.decisions["malformed_row_count"],
            result.decisions["exact_duplicate_count"],
            result.graph.number_of_edges(),
            result.graph.number_of_nodes(),
            len(result.relation_counts),
        )
    )
    for name, path in output_paths.items():
        print(f"{name}: {path}")
