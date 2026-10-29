# Phase 2 graph outputs

From the project root, run:

```powershell
py phase2_graph.py
```

Open `outputs/phase2/interactive_graph.html` in a browser. Search for an entity
by readable name or ID, select a match, and choose **Show neighborhood** to
inspect its incoming and outgoing training relationships. Use **Relation
filter** to view one relation type at a time. Click a node to open that node's
neighborhood; use **Fit view** to refit the current drawing.

The HTML bundles the complete training graph for client-side filtering, while
showing only a bounded neighborhood or relation subgraph at once. The complete
directed, relation-labelled graph is also exported as
`training_graph.graphml`. `filtering_decisions.json` records the source hash,
row parsing, malformed rows, exact duplicates, and filtering policy.

Entity inspection reports all incoming/outgoing counts and lists up to 40
triples in each direction; if more exist, the inspector indicates how many
additional triples were omitted from that panel.
