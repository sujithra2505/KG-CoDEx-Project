# Phase 3: Ontology Design for CoDEx-M

**Design date:** 2026-10-28  
**Scope:** Design only. No ontology was generated, no rules were mined, and no
inference, prediction, or evaluation was run.

## 1. Current project assessment

The project has a clear phase-output convention, so this report is placed in
`outputs/phase3/` without changing completed outputs. The root contains
`phase2_graph.py`, `display_labels.py`, and two test modules. There is no root
README; Phase 2 usage notes are in [`outputs/phase2/README.md`](../phase2/README.md).

Phase 1 documents the supplied files, validation checks, and exact split
counts. In particular, `data/train.txt` contains 185,584 valid, unique
ID triples, covering 17,050 entities and 51 relations. The positive validation
and test splits each contain 10,310 and 10,311 triples, respectively. Their
triple IDs are tab-delimited, and the entity/relation IDs use `Q...` and `P...`
forms. The local ID-to-label mappings cover the IDs in all supplied splits.

Phase 2, implemented in [`phase2_graph.py`](../../phase2_graph.py), constructs
a directed `MultiDiGraph` from **training triples only**. It preserves IDs as
node and edge keys, retains different relation IDs between the same endpoints,
and removes only exact duplicate rows. The Phase 2 outputs record 185,584
edges, 17,050 nodes, 51 relations, and the training-file SHA-256
`d99c3437ab51690391a26d96976adf6e5494dba7ef6902e77000551bfa566556`.
[`outputs/phase2/relationship_analysis.md`](../phase2/relationship_analysis.md)
explicitly characterizes its path counts as observations, not rules, and says
the mappings contain no entity types, relation domains/ranges, or relation
descriptions. [`outputs/phase2/filtering_decisions.json`](../phase2/filtering_decisions.json)
also records that no validation/test-based or semantic filtering was used.

[`display_labels.py`](../../display_labels.py) and
[`DISPLAY_LABELS.md`](../../DISPLAY_LABELS.md) establish the intended
identifier policy: labels are for presentation, and IDs remain the processing
keys. The existing tests cover graph construction, duplicate handling,
identifier retention, labels, and generation of Phase 2 exports; they do not
currently cover RDF serialization or ontology axioms.

The Phase 1 assessment is [`outputs/phase1_dataset_report.md`](../phase1_dataset_report.md);
the requested Phase 2 assessment files are under `outputs/phase2/`. Source
files and tests are present at the project root and under `tests/`. No
root-level README was found; the Phase 2 README is the project's existing
usage documentation.

## 2. Available semantic information and limitations

| Category | What is actually available | What it supports |
|---|---|---|
| Observed dataset facts | Positive train/validation/test files contain `(subject ID, relation ID, object ID)` rows; negative-example files are separate. Phase 1 reports no exact duplicates within these files or overlap between positive splits. | Treat a training row as an asserted, directed, relation-labelled edge. Do not treat supplied negatives as positive facts. |
| Display metadata | `entity_labels.json` and `relation_labels.json` map IDs to English-readable labels. `display_labels.py` has an ID fallback for unmapped labels. | Add labels for display while preserving the original IDs. A label is not an entity type or a formal relation definition. |
| Statistical graph patterns | Phase 2 reports training relation counts and adjacent two-hop path counts/examples. | Descriptive statistics for later rule-candidate generation and diagnostics only. A path frequency does not establish a logical implication, domain, range, inverse, or symmetry axiom. |
| Verified semantic schema in this project | No entity-type assertions, type hierarchy, relation descriptions, domain/range declarations, inverse-property declarations, symmetry declarations, or composition axioms are supplied in the inspected local files/reports. | No domain-specific classes or relation constraints can currently be asserted from project-local metadata. |
| Hypotheses requiring evidence | Some labels may suggest familiar Wikidata property meanings or likely properties (for example, a label that sounds symmetric). | Treat these as hypotheses only. Verify each claim against an authoritative, versioned source and the actual CoDEx-M extraction/encoding before adding an axiom. Do not infer it from a label or observed co-occurrence alone. |

The CoDEx mappings establish identifier-to-label associations; they do not
provide a local semantic schema. Although identifiers and some labels resemble
Wikidata identifiers/property labels, this design does not assume that
external Wikidata statements, constraints, or ontology axioms were included in
the benchmark or correctly apply to every extracted triple. Any later
enrichment must record its source, version/date, mapping policy, and review
status separately from observed facts.

## 3. Proposed RDF/OWL architecture

### Representation

Use an RDF dataset serialized as TriG (or another named-graph-capable format)
so the asserted training graph is unambiguously separable from schema and
provenance metadata. Keep RDF resources in a project-controlled, documented
namespace; do not use labels as identifiers or silently equate local IDs with
external URIs.

| Resource | Proposed representation |
|---|---|
| Entity | Stable URI derived from the exact source ID, e.g. `urn:codexm:entity:Q108946`; retain the exact ID as a literal identifier too. |
| Relation | Stable URI derived from the exact source ID, e.g. `urn:codexm:relation:P161`; retain the exact ID as a literal identifier too. |
| Triple | Subject URI, relation URI as predicate, object URI. Preserve direction and all three source IDs. |
| Display label | `rdfs:label` with English language tag in a metadata/schema graph. Labels do not replace IDs. |
| Minimal OWL role | Mark entity resources as `owl:NamedIndividual` and relation resources as `owl:ObjectProperty`, or use equivalent generic RDF declarations. These are representation categories, not domain-specific entity typing or relation constraints. |
| Provenance | Record dataset/split name, source path or dataset identifier, source-file hash, row/unique-triple counts, conversion version, and generation timestamp as metadata. |

Illustrative shape only (not a generated artifact):

```trig
@prefix cm:   <urn:codexm:> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .

<urn:codexm:graph:train> {
  cm:entity:Q108946 cm:relation:P161 cm:entity:Q39792 .
}

<urn:codexm:graph:metadata> {
  cm:entity:Q108946 rdf:type owl:NamedIndividual ;
      rdfs:label "A Few Good Men"@en ;
      cm:sourceId "Q108946" .
  cm:relation:P161 rdf:type owl:ObjectProperty ;
      rdfs:label "cast member"@en ;
      cm:sourceId "P161" .
}
```

In the implementation, namespace syntax and URI construction must be tested
with all actual IDs and serialized using an RDF library's URI utilities rather
than string concatenation that could produce invalid or colliding terms.
Metadata may instead use a separate graph/file if that gives downstream
consumers a safer way to select only the assertion graph.

### Semantic guardrails

- The assertion graph must contain exactly the unique training ID triples
  under the reversible ID-to-URI mapping. Do not convert validation, test, or
  negative files into the training ontology.
- Declare no `rdfs:domain`, `rdfs:range`, `owl:inverseOf`,
  `owl:SymmetricProperty`, `owl:TransitiveProperty`, property chain, or
  subproperty axioms in this stage. No reliable project-local metadata supports
  them.
- Do not create domain-specific entity classes from labels or from endpoint
  frequency patterns. A generic serialization-level individual category does
  not claim that entities are all the same real-world kind.
- Do not add `owl:sameAs`, property equivalences, or external identifier links
  without a separately verified mapping.
- Keep ontology declarations/labels outside the assertion graph used for rule
  mining. A consumer must explicitly select the training assertion graph;
  otherwise labels and declarations could be mistaken for data predicates.
- Keep future predictions out of the asserted graph. Represent each later
  prediction as a separate record/graph with a stable prediction ID, rule ID,
  support and confidence counts, and references to its supporting training
  facts/path. Preserve its status as predicted rather than asserted.

This conservative design provides a lossless, queryable RDF representation
and a stable foundation for later analysis, without treating statistical
observations as OWL semantics.

## 4. Comparison with KGRuleMiner

The reference reviewed was
[`shailooz/KGRuleMiner`](https://github.com/shailooz/KGRuleMiner) at commit
[`2080447`](https://github.com/shailooz/KGRuleMiner/tree/2080447dfaf66554b9734139f0acea9bf9587e50).
Relevant files include
[`approximate_ontology.py`](https://github.com/shailooz/KGRuleMiner/blob/2080447dfaf66554b9734139f0acea9bf9587e50/scripts/approximate_ontology.py),
[`mine_rules.py`](https://github.com/shailooz/KGRuleMiner/blob/2080447dfaf66554b9734139f0acea9bf9587e50/scripts/mine_rules.py),
[`infer_edges.py`](https://github.com/shailooz/KGRuleMiner/blob/2080447dfaf66554b9734139f0acea9bf9587e50/scripts/infer_edges.py),
and [`generate_synthetic_kg_with_rules.py`](https://github.com/shailooz/KGRuleMiner/blob/2080447dfaf66554b9734139f0acea9bf9587e50/scripts/generate_synthetic_kg_with_rules.py).
Its README describes a synthetic-KG workflow and a generator that deliberately
plants known rules for testing.

| Reference idea | Reuse/adapt for CoDEx-M |
|---|---|
| RDF as a common graph representation and separate ontology/instance-data artifacts | Reuse the representation goal, but preserve CoDEx IDs and isolate the training assertion graph from metadata. |
| Approximate ontology counts and observed endpoint patterns | Reuse only as clearly labelled statistics/diagnostics. The reference induces domains/ranges from observed `rdf:type`; emitting those observations as OWL `rdfs:domain`/`rdfs:range` axioms can have formal entailments and is not justified for this untyped local dataset. |
| Support and confidence for Horn-rule candidates | Reuse as candidate measures in a later phase, with explicitly defined denominators, distinct-grounding policy, leakage controls, and evaluation. They are not by themselves proof of semantics or calibrated prediction probabilities. |
| Composition, inverse, subrelation, symmetry, and type-propagation rule shapes | Consider as later candidate templates only. Type-propagation is unavailable without types. The other shapes must be mined and independently evaluated, not installed as ontology axioms based on the script's output. |
| Prediction provenance (rule/confidence/iteration) | Reuse the provenance goal, improving it to retain support/body counts, rule version, evidence fact IDs/path, training snapshot hash, and whether a fact is asserted or predicted. |
| Synthetic ground-truth generator | Reuse as a possible unit-test strategy for future rule-miner behavior, not as evidence of CoDEx-M rule quality or benchmark performance. |

The reference ontology script discovers classes from existing `rdf:type`
triples and infers observed domain/range classes. CoDEx-M's supplied local
training rows and label mappings do not include those type assertions, so that
mechanism cannot yield verified CoDEx entity classes here. Also, the reference
rule loader reads non-`rdf:type` predicates from one RDF graph; a CoDEx
implementation should not pass schema/label triples into that loader as if
they were relation facts. The reference's synthetic planted-rule experiment
is a controlled demonstration, not a CoDEx-M evaluation. No CoDEx-M benchmark
success or accuracy is inferred from it.

## 5. Proposed implementation steps

1. Add a dedicated Phase 3 builder (for example, `phase3_ontology.py`) that
   reads only `data/train.txt` and the existing label maps. Reuse the Phase 2
   exact-row validation/deduplication contract where appropriate; do not edit
   or refactor Phase 2 code for this stage.
2. Validate every row and ID mapping, preserve IDs exactly, and fail
   explicitly on malformed data or missing required labels/IDs rather than
   silently normalizing or fabricating metadata. Keep the existing display
   label fallback only if the report clearly records the unmapped ID.
3. Build named training and metadata/provenance graphs. Emit only generic
   representation declarations and labels; add no unsupported schema axioms.
4. Serialize a deterministic TriG artifact (and, if useful, a separate
   concise manifest/report) under a new `outputs/phase3/` path. Record source
   hash/counts, serialization format, converter version, and exact
   duplicate/malformed counts. Refuse accidental overwrite or write atomically
   to a new target.
5. Reload the serialized dataset and run the checks in Section 6 before
   reporting success. Make downstream rule mining take the named training
   graph explicitly, not the union of all graphs.
6. Keep implementation dependencies unchanged unless the selected
   serialization library is demonstrably unavailable and dependency approval
   is appropriate. Do not run rule mining or inference as part of this phase.

## 6. Validation tests

| Test | Required assertion |
|---|---|
| Triple preservation | Parse source training rows into ID triples, map to RDF terms, and compare the assertion graph's complete triple set with the mapped source set. Assert exactly 185,584 unique assertions for the current checked-in snapshot. |
| Entity/relation ID preservation | Every entity and predicate URI reversibly maps to its original `Q...`/`P...` ID; any explicit ID literal agrees. Assert all 17,050 entities and all 51 relations appear. Labels never serve as keys. |
| Direction and relation identity | A known input row appears with the same subject, predicate/relation ID, and object. Two rows sharing endpoints but differing in relation ID remain two assertions. |
| Duplicate handling | A fixture containing an exact repeated row produces one RDF assertion and reports the duplicate count; a distinct relation between the same endpoints remains. The production snapshot currently has zero duplicates. |
| Malformed input | Fixtures with missing columns, empty IDs, or surrounding whitespace produce an explicit validation failure/report consistent with Phase 2 policy; do not silently repair them. |
| Serialization/reload | Serialize to the chosen format, reload it, and compare named-graph assertion triples, identifiers, labels, and metadata. Assert the serializer/parser preserve language-tagged labels and graph separation. |
| Ontology-axiom allowlist | Assert that there are no domain, range, inverse, symmetry, transitivity, property-chain, subproperty, or domain-specific class axioms unless separately approved and evidenced. Validate the expected generic declarations only. |
| Assertion/schema separation | Assert the training named graph contains only source training assertions and no labels, schema declarations, validation/test facts, negative examples, or predictions. |
| Source and output protection | Hash the original five data files, label mappings, and Phase 1/2 output files before/after the build; assert hashes and file contents are unchanged. Assert the builder writes only to a new Phase 3 destination and refuses an unintended existing target. |
| Determinism | Repeated builds from identical source bytes and mappings produce equivalent named-graph contents and stable manifest counts/hash. Byte-for-byte output determinism may additionally require canonical RDF serialization. |

The builder's test fixture should be small and synthetic; production-snapshot
checks should be read-only. Tests must never invoke rule mining, forward
chaining, or validation/test conversion.

## 7. Later-phase integration

- **Phase 4 — rule mining:** Read only the named training assertion graph.
  Represent rule bodies and heads using original relation IDs, and define
  support as the count of distinct satisfying groundings under an explicitly
  documented policy. Define confidence from head-supported body groundings
  divided by all body groundings. Save numerator, denominator, rule form,
  training snapshot hash, and candidate/template details. Treat mined rules
  as empirical patterns, not OWL axioms. Keep metadata graphs excluded from
  joins.
- **Phase 5 — missing-edge prediction:** Apply approved rule candidates to
  training facts only. Store proposed edges separately from assertions.
  Record the complete evidence path (source triple IDs/tuples), rule ID and
  version, support/confidence, and training hash. Render readable labels for
  users but retain IDs in machine-readable outputs. Avoid describing raw
  rule confidence as calibrated probability unless calibration is later
  measured.
- **Phase 6 — split-safe evaluation:** Freeze the training ontology and rule
  candidates before examining test outcomes. Use validation only for
  development choices such as thresholds; do not add validation facts to the
  training ontology or mine rules from validation/test. Evaluate against the
  held-out test split once under a declared protocol. If using the supplied
  negative files, document their construction/meaning and report the exact
  ranking or classification metrics and candidate protocol. Keep negative
  examples distinct from positive facts, and avoid using test positives or
  negatives to filter training, choose rules, or tune thresholds.

## 8. Risks and unresolved questions

- There are no verified entity types or relation schema declarations in the
  local project inputs. This limits semantic rule families and blocks
  trustworthy typed-domain/range validation unless independently sourced
  metadata is approved.
- Relation labels can be ambiguous, abbreviated, or misleading. A familiar
  property ID/label is not sufficient evidence that the benchmark's use of it
  warrants a particular OWL axiom.
- RDF graphs use set semantics. The current training file has no exact
  duplicates, but any future source revision must report row multiplicity
  separately from unique graph triples.
- A URI scheme and ontology namespace should be selected and documented
  before long-lived artifacts or downstream references are published.
- Named graph isolation must be enforced by consumers; querying the dataset
  union could mix labels/schema with the training relation assertions.
- The reference miner's support/confidence implementation and synthetic
  behavior have not been validated for CoDEx-M. Scalability, duplicate
  grounding definitions, open-world incompleteness, popularity effects, and
  leakage need later engineering/evaluation work.
- The provided negative files are not independently verified ground truth.
  Phase 1 reports structural checks, not semantic correctness of every
  negative label.

## 9. Readiness criteria for implementation

Ontology-builder implementation is ready when:

1. The project owner accepts the conservative no-domain/range/no-inverse/no-
   symmetry policy and the choice of local URI namespace and serialization.
2. The builder's input contract is fixed as training-only, with explicit
   failure/reporting behavior for malformed rows, unmapped IDs, duplicates,
   and destination collisions.
3. The RDF dependency/format is chosen without unnecessary environment
   changes, and named-graph support is confirmed.
4. The Section 6 tests are implemented, including a source/Phase 1/Phase 2
   non-modification check.
5. The generated training graph can be reloaded and compared exactly to the
   source ID triple set, with provenance sufficient to identify the input
   snapshot.

No rules, inferred facts, or predicted edges are produced by this design.
