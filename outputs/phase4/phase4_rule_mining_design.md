# Phase 4A: Logical Rule Mining Design for CoDEx-M

**Design date:** 2026-10-29
**Scope:** Design only. No rules were mined, no rule confidences were computed,
no inferred or predicted edges were generated, and Phase 5 was not started.
Phase 1, Phase 2 and Phase 3 outputs and the dataset were not modified.

## 0. What was inspected

**Project (actual files, read on the local machine):**

| Path | Role for Phase 4 |
|---|---|
| `data/train.txt` (185,584 rows, SHA-256 `d99c3437…6556`) | Only source of facts for mining (through the Phase 3 graph) |
| `data/valid.txt`, `data/valid_negatives.txt` | Used only by the separate Phase 4 evaluation step, after rules are frozen |
| `data/test.txt`, `data/test_negatives.txt` | Never read in Phase 4 (hashed for integrity only) |
| `data/entity_labels.json`, `data/relation_labels.json` | Display labels only |
| `outputs/phase1_dataset_report.md` | Split sizes; no train/valid/test triple overlap |
| `outputs/phase2/relationship_analysis.md`, `graph_statistics.json` | Relation counts and two-hop path counts (descriptive only) |
| `outputs/phase3/codexm_train_ontology.trig` | Phase 3 RDF dataset; graph `urn:codexm:graph:train` holds the 185,584 training triples |
| `outputs/phase3/phase3_manifest.json` | Output hash `e934ee40…e9a2`, counts, protected-file hashes |
| `phase3_ontology.py` | Provides `parse_canonical_trig`, `verify_existing_outputs`, `protected_file_hashes` |
| `tests/` | `test_display_labels.py` (4), `test_phase2_graph.py` (6), `test_phase3_ontology.py` (27) = 37 tests |

There is no `outputs/phase4/` folder before this report and no top-level README.
This report creates `outputs/phase4/` following the `outputs/phaseN/` convention.

**Reference:** [`shailooz/KGRuleMiner`](https://github.com/shailooz/KGRuleMiner)
at commit `2080447` (only commit), mainly `scripts/mine_rules.py`,
`scripts/infer_edges.py`, `scripts/generate_synthetic_kg_with_rules.py`,
`data/ground_truth_rules.md` and `output/rules.md`.

**Sizing measurements (training split only, counts of bodies and paths, not
rule scores).** These were computed on a read-only copy to size the search.
No head relation was joined and no confidence was computed.

| Measurement | Value |
|---|---|
| Relations / entities / triples | 51 / 17,050 / 185,584 |
| Self-loops (`x r x`) | 0 |
| Entity pairs linked by more than one relation | 2,565 |
| Triples whose reversed pair `(o, s)` also exists (any relation) | 6,641 |
| Highest-degree entities | `Q30` (6,224), `Q36180` (4,441), `Q1860` (4,024), `Q33999` (3,756) |
| Median entity degree | 12 |
| Two-atom chain bodies `p1(x,y) ∧ p2(y,z)` that join at all | 595 of 2,601 |
| Paths over those chain bodies | 2,966,413 |
| Largest chain body `P27(x,y) ∧ P530(y,z)` | 1,425,045 paths → 1,363,143 distinct `(x,z)` pairs |
| Two-atom bodies with any edge direction that join | 3,108 of 10,404 |
| Paths over all-direction bodies | 196,108,794 |
| Largest: `P106(x,y) ∧ P106(z,y)` ("share an occupation") | 96,828,205 paths |
| Bodies over 1M / 5M paths | 15 / 6 (top 10 bodies hold 88% of all paths) |
| Relations with fewer than 20 training triples | P452 (17), P50 (16), P2283 (9), P3095, P54, P1056 (2 each), P113, P780 (1 each) |

Conclusion: a naive all-direction enumeration is dominated by a few
"shared object" bodies through hub entities (occupations, countries,
languages). Explosion control (Section 3) is required, not optional.

## 1. Rule types for CoDEx-M

Notation: `r(x,y)` means the training triple `x —r→ y` exists. Variables are
universally quantified. Rules are closed (every variable appears at least
twice) and connected. Relation IDs (`P…`) are the rule vocabulary; labels are
only for display.

| ID | Rule type | Form | Justification from local data | Status |
|---|---|---|---|---|
| T1 | Inverse / symmetry | `p(x,y) → q(y,x)` (`p = q` is symmetry) | 6,641 triples have a reversed pair; relations such as P26, P3373, P451, P530 have labels that suggest symmetry, but this is a hypothesis to test, not a fact | Include |
| T2 | Subrelation / co-occurrence | `p(x,y) → q(x,y)`, `p ≠ q` | 2,565 entity pairs carry more than one relation | Include |
| T3 | Two-hop composition (chain) | `p1(x,y) ∧ p2(y,z) → h(x,z)` | 595 joinable chain bodies (Phase 2 path counts) | Include |
| T4 | Two-hop with reversed atoms | `p1(y,x) ∧ p2(y,z) → h(x,z)`, `p1(x,y) ∧ p2(z,y) → h(x,z)`, `p1(y,x) ∧ p2(z,y) → h(x,z)` | Needed for patterns that go through a shared subject or shared object (for example two people sharing a film) | Include, with hub caps |
| T5 | Transitivity | `p(x,y) ∧ p(y,z) → p(x,z)` | Special case of T3 | Include (no separate code path) |
| T6 | Type propagation | `C(x) ∧ p(x,y) → D(y)` | Not possible: Phase 3 confirmed there are no entity types | Excluded |
| T7 | Rules with constants | for example `P27(x, Q30) → P1412(x, Q1860)` | May be useful, but adds 17,050 constants per position | Deferred; needs separate approval |
| T8 | Longer bodies (3+ atoms) | | Search space grows by about a factor of 100 per atom | Deferred |

All rules have a single head atom `h(x,z)` with `x ≠ z`. Because there are no
self-loops, `x ≠ z` also guarantees the middle variable `y` differs from both.

**Trivial rules excluded by construction:** `h(x,z) → h(x,z)`; T2 with `p = q`;
any body that contains the head atom itself; duplicate rules that differ only
by variable renaming (removed by canonicalization, Section 4).

No rule will be called "valid", "true" or "semantic". The report will use
"candidate rule" and "statistical pattern". A rule such as
`P27(x,y) ∧ P530(y,z) → h(x,z)` may score above a threshold only because
`Q30` is a hub. That is a property of the data, not of the meaning of
"citizenship" or "diplomatic relation".

## 2. Support and confidence: exact definitions

Let `G` be the set of training triples in `urn:codexm:graph:train` and `R` be a
rule `B(x,z) → h(x,z)`, where `B` is the body (one or two atoms).

| Measure | Definition |
|---|---|
| Body pairs | `Body(R) = {(x,z) : x ≠ z, and some binding of the body variables makes every body atom a triple in G}` — distinct pairs, not paths |
| Body size | `|Body(R)|` |
| Support | `supp(R) = |{(x,z) ∈ Body(R) : h(x,z) ∈ G}|` |
| Standard confidence | `conf(R) = supp(R) / |Body(R)|` (treats every missing head as false) |
| PCA body | `PCABody(R) = {(x,z) ∈ Body(R) : ∃ z'. h(x,z') ∈ G}` |
| PCA confidence | `pca(R) = supp(R) / |PCABody(R)|` (only counts a body pair as a counterexample if `x` already has some `h` value) |
| Head coverage | `hc(R) = supp(R) / |{(x,z) : h(x,z) ∈ G}|` |
| Wilson lower bound | 95% Wilson lower bound of `pca(R)` with `n = |PCABody(R)|`; penalizes small counts |
| Head prior | `prior(h) = |h| / (|subjects of h| × |objects of h|)`; `lift = conf(R) / prior(h)` is a weak "better than chance" check |

**PCA direction.** The PCA uses the subject side (`∃ z'. h(x,z')`) by default.
If `h` has many more objects per subject than subjects per object, the object
side (`∃ x'. h(x',z)`) is used instead, and the chosen side is recorded per rule.
The PCA assumption does not hold well for many-valued relations such as P106
(occupation: about 4.9 objects per subject). For those heads the report will
show standard confidence next to PCA confidence.

**Counting rules.** Support counts distinct `(x,z)` pairs. A pair reached by
200 different middle entities counts once. This stops hubs from inflating
support. Path counts (the Phase 2 numbers) are kept only as diagnostics.

### Worked example 1 (synthetic toy data, not CoDEx facts)

Facts: `P26(A,B)`, `P26(B,A)`, `P26(C,D)`.
Rule T1: `P26(x,y) → P26(y,x)`. For this rule the head pair is `(y,x)`.

| Body pair `(x,y)` | Head `P26(y,x)` in G? | Does `y` have any P26 fact? |
|---|---|---|
| (A,B) | yes, `P26(B,A)` | yes |
| (B,A) | yes, `P26(A,B)` | yes |
| (C,D) | no | no |

Body size 3, support 2, `conf = 2/3 = 0.667`. `D` has no P26 fact, so `(C,D)`
is not a PCA counterexample: PCA body size 2, `pca = 2/2 = 1.0`.
Head coverage is `2/3`. Wilson lower bound with `n = 2` is 0.34, so the
rule still ranks low because it has very little evidence.

### Worked example 2 (synthetic toy data)

Facts: `P27(a,F)`, `P27(b,F)`, `P27(c,G)`, `P27(d,F)`, `P37(F,fr)`, `P37(G,de)`,
`P1412(a,fr)`, `P1412(b,en)`, `P1412(c,de)`.
Rule T3: `P27(x,y) ∧ P37(y,z) → P1412(x,z)`.

| Body pair `(x,z)` | Head in G? | `x` has some P1412? |
|---|---|---|
| (a,fr) | yes | yes |
| (b,fr) | no | yes (en): counterexample |
| (c,de) | yes | yes |
| (d,fr) | no | no: unknown, not counted by PCA |

Body size 4, support 2, `conf = 0.50`, PCA body size 3, `pca = 0.667`,
head coverage `2/3`, Wilson lower bound (`n = 3`) = 0.21.
The rule reads "citizenship plus official language suggests a spoken
language", but that reading is a label-based interpretation. A high score
on real data would still be only a statistical pattern.

## 3. Discovery and ranking without candidate explosion

Rules are generated by joining existing triples, never by listing all
relation combinations and testing each one.

1. **Language bias.** At most 2 body atoms, closed and connected rules,
   head `h(x,z)` with `x ≠ z`, no constants (T7 deferred).
2. **Head-first search.** For each head relation `h` with at least
   `min_head_triples` training triples (default 20), mine T1, T2, then T3/T4.
   Heads below the minimum are listed as "not mined: too few triples" (8 relations
   at present).
3. **Join-driven body enumeration.** For T3/T4, take only body shapes whose
   relations share at least one middle entity (3,108 of 10,404 shapes). Shapes
   with no shared middle entity are never built.
4. **Cost bound before materialization.** For each body shape, compute the path
   count `Σ_y |left(y)| × |right(y)|` cheaply. If it is above
   `max_body_paths` (default 5,000,000; currently affects 6 shapes, all
   "shared object" shapes such as `P106(x,y) ∧ P106(z,y)`), the shape is not
   evaluated. It is listed in the manifest as `skipped_too_large` with its
   path count. Nothing is skipped silently, and nothing is sampled at random.
5. **Head pruning before counting.** For a body shape, compute `Body(R)` once,
   then score every head relation against it with set lookups. A head is
   dropped as soon as its support cannot reach `min_support`
   (support ≤ `|h|`, and ≤ `|Body(R)|`).
6. **Thresholds** (starting values, to be tuned on validation in Section 6):
   `min_support = 10`, `min_head_coverage = 0.01`, `min_pca = 0.10`,
   `min_body_size = 20`.
7. **Ranking** inside each head relation: Wilson lower bound of PCA confidence
   (descending), then support (descending), then rule length (shorter first),
   then rule ID (stable tiebreak). A global ranking uses the same key. Keep at
   most `top_k_per_head` (default 50) candidates per head in the selected set.
   All scored candidates, including rejected ones, stay in the candidate file.

Memory estimate: the largest evaluated body (`P27 ∧ P530`) has 1.36M distinct
pairs. Shapes are processed one at a time and released, so peak memory stays
at roughly one large pair set plus the graph indexes.

## 4. Filtering weak or redundant rules, and evidence

Each candidate gets a `status` (`selected` / `rejected`) and a list of reasons.
Nothing is deleted without a recorded reason.

| Filter | Rule |
|---|---|
| Weak | Below any threshold in Section 3 step 6 |
| No lift | `lift < 1.5` (barely above the relation prior) |
| Small body | `|PCABody(R)| < min_body_size` |
| Duplicate | Same canonical form after variable renaming and atom ordering; keep one |
| Inverse-duplicate | `p(x,y) → q(y,x)` and `q(x,y) → p(y,x)` are kept as two rules (different directions and scores) but linked as a pair |
| Dominated (same head) | Two rules with the same head whose supported pair sets have Jaccard ≥ 0.9: keep the higher-ranked one; mark the other `redundant_with` |
| Length-2 not better | A length-2 rule whose Wilson bound is not above the best length-1 rule for the same head and same supported pairs is marked `no_gain_over_shorter` |
| Hub-dominated (flag) | One middle entity accounts for over 50% of support. Kept, but flagged with that entity (often `Q30`) |
| Low-count head | Head relation has fewer than `min_head_triples` triples |

**Evidence stored per rule:**

- `rule_id`: SHA-256 of the canonical rule string (first 16 hex digits)
- the rule as relation IDs and as a display string with labels
- `body_size`, `support`, `pca_body_size`, `pca_side`, `head_count`,
  `conf`, `pca`, `head_coverage`, `wilson_lower`, `lift`
- `top_middle_entities`: top 5 middle entities with their share of support
- `supporting_examples`: up to 10 groundings `(x, y, z)` where body and head are
  both training triples, chosen in sorted ID order (deterministic), with the
  exact training triples as evidence
- `counterexamples`: up to 10 PCA counterexamples (body true, `x` has a
  different known `h` value, head absent). These are contradicting evidence,
  not predictions.
- status and reasons, and the training snapshot hash and miner version

Body pairs with an unknown head (the PCA "unknown" pairs) are counted but
never listed. Listing them would effectively be a prediction file, which is
Phase 5 work.

## 5. Preventing validation and test leakage

| Risk | Control |
|---|---|
| Mining sees validation or test facts | The miner reads only `urn:codexm:graph:train` from the Phase 3 TriG through `phase3_ontology.parse_canonical_trig`, after `verify_existing_outputs` confirms the manifest hash. It has no code path that opens `valid*.txt` or `test*.txt`. |
| Labels or metadata treated as facts | Only the training named graph is loaded. Predicates must start with `urn:codexm:relation:`; anything else fails the load. (KGRuleMiner loads the whole RDF graph, which here would mix in labels and the `owl:NamedIndividual` types.) |
| Thresholds tuned on test | The evaluation script accepts only `valid.txt` and `valid_negatives.txt`. Test files are not opened in Phase 4. |
| Rules changed after looking at validation | Mining writes `selected_rules.json` with its SHA-256. The evaluation step refuses to run if the file hash differs from the mining manifest. Any threshold change on validation creates a new run folder, with the grid and the choice recorded. |
| Validation facts flowing back into training | Validation triples are never added to the graph used for body or support counting. |
| Test used for a "quick check" | A test monkeypatches file opening during mining and evaluation and fails if any `test*.txt` path is opened. |
| Protected files changed | `protected_file_hashes` (from Phase 3) is compared before and after each run. |

Known dataset-level effect: some relations may appear in both directions
across splits (for example a spouse pair split between train and validation).
Inverse and symmetry rules will look strong on validation for that reason.
This is reported per relation, not hidden, and it is not the same as leakage
from our pipeline.

## 6. Evaluating candidate rules (training and validation only)

**Stage A: training-only checks (during mining).**

- All measures in Section 2.
- Optional stability check: split the training triples deterministically
  (SHA-256 of the triple, 90/10). Mine on 90%, and report for each selected
  rule how many of its body pairs in the 10% part have the head present. This
  checks overfitting without touching validation. Rules whose stability
  confidence drops by more than half are flagged.

**Stage B: validation scoring (separate script, after freezing).**
For each frozen rule `R` with head `h`:

- `New(R) = Body(R) minus pairs whose head is already in G` is computed in
  memory only and never written out.
- `val_hits = |New(R) ∩ valid_positives(h)|`
- `val_neg_hits = |New(R) ∩ valid_negatives(h)|`
- `val_precision_lb = val_hits / |New(R)|`. This is a lower bound: validation
  is a small sample of true facts, so most correct pairs will not be in it.
- `pos_neg_ratio = (val_hits + 1) / (val_neg_hits + 1)`. This uses the supplied
  negatives, whose semantic correctness was not independently verified
  (Phase 1).
- `val_recall(h)` for the selected rule set: share of validation triples with
  head `h` that at least one rule reaches from training facts. Validation
  triples whose entities do not appear in training are counted separately
  as unreachable.

Report per head relation and macro-averaged. Use validation only to choose
thresholds (`min_support`, `min_pca`, `top_k_per_head`, lift) from a small,
declared grid. Do not use it to hand-pick individual rules. No ranking metric
such as MRR or Hits@k is computed here; that needs a prediction protocol and
belongs to Phase 5/6. The test split stays closed until Phase 6.

## 7. Proposed implementation

**Dependencies:** Python standard library only (`collections`, `itertools`,
`hashlib`, `json`, `math`, `argparse`). The miner reuses parsing and
verification functions from `phase3_ontology.py` by import, without changing
that file. No `rdflib`, `numpy` or `pandas` is needed.

**New files (Phase 4B):**

| File | Purpose |
|---|---|
| `phase4_rule_mining.py` | Load and verify the Phase 3 training graph; build indexes; enumerate T1–T4/T5 candidates; score; filter; rank; write outputs |
| `phase4_rule_evaluation.py` | Read frozen `selected_rules.json` plus `valid.txt` / `valid_negatives.txt`; write validation scores only |
| `tests/test_phase4_rule_mining.py` | Unit tests for the miner |
| `tests/test_phase4_rule_evaluation.py` | Unit tests for the evaluation step |

**Outputs (`outputs/phase4/`, new files only, refuse to overwrite):**

| File | Content |
|---|---|
| `phase4_rule_mining_design.md` | This report |
| `rule_candidates.jsonl` | One JSON object per scored candidate, selected or rejected, with reasons and evidence |
| `selected_rules.json` | Frozen ranked rule set (IDs, forms, scores, evidence pointers) |
| `rules_report.md` | Readable report: rules in first-order form with labels and IDs, per-head tables, hub flags, skipped shapes, limitations |
| `mining_manifest.json` | Parameters, input hashes (TriG, manifest, `train.txt`), counts per stage, skipped shapes with path counts, `selected_rules.json` hash, protected-file hashes, run time |
| `validation_evaluation.json` / `validation_evaluation.md` | Stage B results, written by the second script only |

**Tests (synthetic fixtures, hand-computed answers):**

1. Worked examples 1 and 2 give the exact body size, support, conf, PCA,
   head coverage and Wilson values above.
2. Planted-rule fixture (as in KGRuleMiner's generator): known rules are found;
   a random-noise relation produces nothing above threshold.
3. Distinct-pair counting: a hub with 100 middle paths to the same `(x,z)`
   counts once.
4. `x ≠ z` is enforced; tautologies and `p = q` subrelations are never produced.
5. Direction variants T4 produce the right pairs; canonical forms remove
   renamed duplicates.
6. Threshold boundaries (equal to threshold is accepted) and ranking tiebreaks
   are deterministic.
7. `max_body_paths` skips a large shape and records it; nothing is sampled.
8. Hub-dominated flag and `redundant_with` / `no_gain_over_shorter` reasons.
9. Loader takes only `urn:codexm:graph:train`; a fixture TriG with labels and
   types shows they never become relations.
10. Mining never opens `valid*`/`test*` files; evaluation never opens `test*`
    files (monkeypatched file opening).
11. Evaluation refuses a `selected_rules.json` whose hash differs from the manifest.
12. Output files contain no list of unknown-head body pairs (schema check).
13. Two runs give byte-identical candidate and selected-rule files (only the
    manifest timestamp differs).
14. Refuse to overwrite existing outputs; protected-file hashes unchanged.
15. Read-only production check: the miner runs on the real snapshot within
    the time and memory budget, and the manifest counts match Phase 3
    (185,584 / 17,050 / 51).

## 8. Limitations and comparison with KGRuleMiner

**Limitations**

- **Statistics are not meaning.** A high-scoring rule shows co-occurrence in
  this Wikidata extract. It does not prove a semantic law, and correlated
  patterns through hubs (`Q30`, common occupations, English) can look strong.
- **Open world.** Missing triples are unknown, not false. Standard confidence
  understates rules; PCA is a heuristic that fails for many-valued relations.
- **No types.** Rules cannot be restricted to people, films or countries, so
  some rules fire on unsuitable entities.
- **Sparse relations.** Eight relations have under 20 triples and cannot
  support reliable rules.
- **Search limits.** Two-atom bodies only, no constants, and 6 large shapes
  skipped. Longer or instantiated patterns are not found.
- **Validation limits.** Validation is incomplete, so precision is a lower
  bound. The negatives are supplied, not independently verified.
- **Popularity bias.** Rules about frequent relations get more support and more
  stable scores than rules about rare relations.

**Comparison**

| Aspect | KGRuleMiner (`mine_rules.py`, `infer_edges.py`) | Proposed Phase 4 |
|---|---|---|
| Input | Any RDF file parsed into one `rdflib.Graph`; all non-`rdf:type` triples become relations; names shortened with `local_name` | Only the verified Phase 3 training named graph; IDs kept in full |
| Rule shapes | Composition (forward chain only), inverse/symmetric, subrelation, type propagation | Inverse, subrelation, chains with all four direction variants; type propagation excluded (no types) |
| Body counting | Distinct `(x,z)` pairs with `x ≠ z` (same idea) | Same, plus PCA body and hub diagnostics |
| Measures | `support`, `body_size`, standard confidence | Standard confidence, PCA confidence, head coverage, Wilson bound, lift |
| Thresholds | `--min-support 3`, `--min-confidence 0.3`; `min_support` also used as minimum body size | Tuned on validation from a declared grid; separate support and body thresholds |
| Explosion control | Loops over every relation combination (`product(preds, repeat=2)` × heads) | Join-driven, cost bound, recorded skips |
| Ranking | Confidence, then support; keeps global top 25 | Wilson bound, support, length, ID; top-k per head; all candidates kept with reasons |
| Redundancy | None | Canonical dedupe, Jaccard dominance, no-gain-over-shorter |
| Evidence | Rule text and counts | Counts, examples, counterexamples, hub shares, hashes |
| Leakage | No split handling | Train-only mining, frozen rule hash, validation-only tuning, test never opened |
| Inference | Forward chaining adds predictions back into the facts | Not in Phase 4; Phase 5 work |
| Validation of the method | Synthetic KG with 5 planted rules (`data/ground_truth_rules.md`) | Planted-rule fixtures for unit tests only; no claim about CoDEx-M quality from them |
| Dependencies | `rdflib` and a large stack | Standard library only |

What to reuse: the AMIE-style distinct-pair counting, the rule-shape list,
the readable first-order output format, and the planted-rule test idea.
What not to reuse: loading the whole RDF graph, type-propagation rules,
global top-25 truncation, and feeding predictions back into the facts.

## 9. Decisions needed before Phase 4B

1. Approve rule types T1–T5, with T6 excluded and T7/T8 deferred.
2. Approve PCA confidence as the main score (with standard confidence shown),
   ranked by its Wilson lower bound.
3. Approve the starting thresholds and `max_body_paths = 5,000,000`, with
   final values chosen on validation.
4. Approve the two-script split (mining, then frozen validation scoring) and
   the output file names.
5. Decide whether to run the optional 90/10 training stability check.
