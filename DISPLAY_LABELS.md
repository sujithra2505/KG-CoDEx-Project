# CoDEx display labels

`display_labels.py` provides presentation-only labels. Keep Wikidata identifiers
as the graph's node and relation keys for graph processing, rule learning,
inference, and evaluation. Use `DisplayLabels.entity_label(id)` for node text
and `DisplayLabels.relation_label(id)` for directed-edge text. Use
`DisplayLabels.prediction_triple(subject, relation, object)` when prediction
output should show both labels and original identifiers.

The JSON files under `data/` are label-only projections of the official English
CoDEx mappings:

- [Entity mapping](https://github.com/tsafavi/codex/blob/3132e426c2a6b643b70bad679905a3a6270be440/data/entities/en/entities.json)
- [Relation mapping](https://github.com/tsafavi/codex/blob/3132e426c2a6b643b70bad679905a3a6270be440/data/relations/en/relations.json)

The original dataset files are unchanged. IDs absent from a mapping display as
their original IDs.

The local triple counts and identifier totals match the official CoDEx-M
statistics (185,584 training triples, 17,050 entities, and 51 relations), not
CoDEx-S. The mappings include every identifier in the local triple files.
