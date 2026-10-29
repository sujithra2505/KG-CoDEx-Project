# Phase 2: Training Graph and Relationship Analysis

## Scope and construction

The graph was constructed from `data/train.txt` only. Validation, test,
and negative-example files were not loaded for graph construction.
Each unique valid `(subject ID, relation ID, object ID)` tuple becomes
one directed edge in a NetworkX `MultiDiGraph`. This preserves separate
relation types between the same entities. Node and edge keys remain the
original IDs; readable labels are presentation attributes only.

- Original training rows: 185,584
- Valid parsed rows before deduplication: 185,584
- Malformed rows recorded and excluded: 0
- Exact duplicate rows excluded: 0
- Unique valid training triples / graph edges: 185,584
- Entities / graph nodes: 17,050
- Relation types: 51
- Training file SHA-256: `d99c3437ab51690391a26d96976adf6e5494dba7ef6902e77000551bfa566556`

Malformed rows, duplicate line numbers, the original-file hash, and
the filtering policy are recorded in `filtering_decisions.json`.
No frequency- or label-based filtering was applied.

## Relation frequencies

Counts are unique training triples per relation. Examples are actual
source triples and display both readable labels and original IDs.

| Count | Relation | Example training triple |
|---:|---|---|
| 64,345 | occupation (`P106`) | Anthony Edwards (Q314924) -- occupation (P106) --> actor (Q33999) |
| 15,169 | country of citizenship (`P27`) | Franz Werfel (Q78514) -- country of citizenship (P27) --> Republic of German-Austria (Q268970) |
| 11,352 | languages spoken, written, or signed (`P1412`) | Jan Hus (Q43977) -- languages spoken, written, or signed (P1412) --> Latin (Q397) |
| 10,621 | genre (`P136`) | Dirty Dancing (Q253978) -- genre (P136) --> romance film (Q1054574) |
| 10,340 | member of (`P463`) | Senegal (Q1041) -- member of (P463) --> UNESCO (Q7809) |
| 8,772 | educated at (`P69`) | Flannery O'Connor (Q234579) -- educated at (P69) --> University of Iowa (Q182973) |
| 8,366 | cast member (`P161`) | A Few Good Men (Q108946) -- cast member (P161) --> Jack Nicholson (Q39792) |
| 6,470 | place of birth (`P19`) | Franz Werfel (Q78514) -- place of birth (P19) --> Prague (Q1085) |
| 5,626 | diplomatic relation (`P530`) | Niger (Q1032) -- diplomatic relation (P530) --> France (Q142) |
| 5,462 | instrument (`P1303`) | Willie Nelson (Q206112) -- instrument (P1303) --> guitar (Q6607) |
| 4,872 | place of death (`P20`) | Panait Istrati (Q344179) -- place of death (P20) --> Bucharest (Q19660) |
| 4,301 | employer (`P108`) | Johann Samuel Ersch (Q65084) -- employer (P108) --> University of Jena (Q154561) |
| 3,104 | record label (`P264`) | Johnny Nash (Q49735) -- record label (P264) --> Epic (Q216364) |
| 2,898 | cause of death (`P509`) | Kurt Waldheim (Q1260) -- cause of death (P509) --> heart failure (Q181754) |
| 2,399 | member of political party (`P102`) | Nikolai Shchelokov (Q1322959) -- member of political party (P102) --> Communist Party of the Soviet Union (Q79854) |
| 2,397 | religion (`P140`) | Bruce Sterling (Q312995) -- religion (P140) --> atheism (Q7066) |
| 2,156 | field of work (`P101`) | Mstislav Keldysh (Q246497) -- field of work (P101) --> mechanics (Q41217) |
| 2,054 | ethnic group (`P172`) | Langston Hughes (Q188093) -- ethnic group (P172) --> African Americans (Q49085) |
| 1,842 | country of origin (`P495`) | Before Night Falls (Q246997) -- country of origin (P495) --> United States of America (Q30) |
| 1,790 | place of burial (`P119`) | Édouard Drumont (Q274297) -- place of burial (P119) --> Père Lachaise Cemetery (Q311) |

All relation counts and examples are available in `graph_statistics.json`.

## Repeated two-hop path observations

These are adjacent directed training-triple paths sharing the middle
entity. They are descriptive observations—not inference rules,
validated implications, or evidence for a missing edge. Counts are
path occurrences and can be large around high-degree entities.

1. **1,425,045 paths:** country of citizenship (`P27`) → diplomatic relation (`P530`)
   - Ludacris (Q193676) -- country of citizenship (P27) --> Gabon (Q1000)
   - Gabon (Q1000) -- diplomatic relation (P530) --> France (Q142)
2. **339,698 paths:** country of citizenship (`P27`) → member of (`P463`)
   - Ludacris (Q193676) -- country of citizenship (P27) --> Gabon (Q1000)
   - Gabon (Q1000) -- member of (P463) --> Multilateral Investment Guarantee Agency (Q1043527)
3. **334,763 paths:** diplomatic relation (`P530`) → diplomatic relation (`P530`)
   - France (Q142) -- diplomatic relation (P530) --> Gabon (Q1000)
   - Gabon (Q1000) -- diplomatic relation (P530) --> France (Q142)
4. **235,245 paths:** country of origin (`P495`) → diplomatic relation (`P530`)
   - L'Obs (Q1044328) -- country of origin (P495) --> France (Q142)
   - France (Q142) -- diplomatic relation (P530) --> Gabon (Q1000)
5. **107,316 paths:** diplomatic relation (`P530`) → member of (`P463`)
   - France (Q142) -- diplomatic relation (P530) --> Gabon (Q1000)
   - Gabon (Q1000) -- member of (P463) --> Multilateral Investment Guarantee Agency (Q1043527)
6. **65,980 paths:** country (`P17`) → diplomatic relation (`P530`)
   - Aachen (Q1017) -- country (P17) --> France (Q142)
   - France (Q142) -- diplomatic relation (P530) --> Gabon (Q1000)
7. **52,374 paths:** country of origin (`P495`) → member of (`P463`)
   - L'Obs (Q1044328) -- country of origin (P495) --> France (Q142)
   - France (Q142) -- member of (P463) --> United Nations (Q1065)
8. **44,153 paths:** cast member (`P161`) → occupation (`P106`)
   - Superman (Q213053) -- cast member (P161) --> Larry Hagman (Q100440)
   - Larry Hagman (Q100440) -- occupation (P106) --> film actor (Q10800557)
9. **27,311 paths:** country of citizenship (`P27`) → continent (`P30`)
   - Ludacris (Q193676) -- country of citizenship (P27) --> Gabon (Q1000)
   - Gabon (Q1000) -- continent (P30) --> Africa (Q15)
10. **19,000 paths:** country of citizenship (`P27`) → official language (`P37`)
   - Ludacris (Q193676) -- country of citizenship (P27) --> Gabon (Q1000)
   - Gabon (Q1000) -- official language (P37) --> French (Q150)

## Semantic compatibility and limitations

The local label mappings provide names but no entity types, relation
domain/range declarations, or relation descriptions. Consequently,
this phase cannot substantiate domain/range violations or semantic
incompatibilities. Unusual-looking or rare triples are retained for
manual review; no fact is marked false or removed based on frequency.

The interactive HTML bundles the complete training-edge data for
client-side search and filtering, but draws only a bounded view at a
time. Its initial view is the one-hop neighborhood of the stable
entity ID `Q30` (United States of America), capped at 300 edges and
120 nodes. Relation mode is capped at 500 edges and 400 nodes, in
stable ID/triple order. The entity inspector shows counts for all
incoming/outgoing triples and lists up to 40 in each direction.
The complete graph remains in
`training_graph.graphml` and in the HTML's bundled data.

No ontology generation, rule learning, inferred edges, edge
prediction, or final evaluation was performed.
