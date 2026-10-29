# Phase 4 methodology comparison: couple support and sibling transitivity

**Date:** 2026-10-29. **Status:** experimental. Nothing in production was changed.

- **Script:** `outputs/phase4/methodology_comparison/phase4_methodology_experiment.py` (new, read-only).
- **Results:** `methodology_comparison/results.json`; full tables in `methodology_comparison/tables.md`.
- **Unchanged:** `run_default/`, `run_grid_ext/`, the production scripts and
  `phase5_candidate_rules_proposed.json` (hashes checked before and after).
- **Not done:** no test files were opened, no predictions were made, and Phase 5 was not started.

## Method

The script re-scored every swap-invariant candidate recorded in
`run_grid_ext/rule_candidates.jsonl` (133 candidates across 20 head relations)
under four counting modes. It then re-ran the production selection step
(`_select`: thresholds, dominance, no-gain, top-k) for those heads. Rules for the
other heads stay as in `run_grid_ext`.

| Mode | Definition |
|---|---|
| `one` | Couple supports if the head holds in at least one direction (production 4B.2.0) |
| `both` | Couple supports only if the head holds in both directions; head coverage uses two-way couples |
| `ordered` | Ordered pairs (4B.1.0) |
| `hybrid` | `one` for heads stated reciprocally (reciprocity ≥ 0.5), `ordered` otherwise |

The body and PCA-body definitions are the same in all couple modes. **Harness
check:** mode `one` reproduced every `run_grid_ext` status and score, and
reproduced the 160-rule proposed list exactly.

**Head reciprocity** is the share of a relation's triples whose reverse is also
present. Heads split cleanly into two groups:

- reciprocal: P26 spouse 0.87, P3373 sibling 0.88, P451 unmarried partner 0.80, P530 diplomatic relation 0.88
- directional: P737 influenced by 0.012, all other affected heads 0.00

## A. Couple-support definitions

| Rule (head reciprocity) | Mode | Support | PCA | Wilson | Status |
|---|---|---:|---:|---:|---|
| Shared parent → sibling `P40(y,x)&P40(y,z)⇒P3373` (0.88) | one | 127 / 128 | 0.992 | 0.957 | selected |
| | both | 91 / 128 | 0.711 | 0.627 | selected |
| | ordered | 218 / 256 | 0.865 | 0.817 | selected |
| Shared sibling `P3373(x,y)&P3373(z,y)⇒P3373` (0.88) | one | 240 / 259 | 0.927 | 0.888 | selected |
| | both | 192 / 259 | 0.741 | 0.685 | redundant (transitivity kept) |
| | ordered | 432 / 518 | 0.834 | 0.799 | redundant (transitivity kept) |
| Shared child → spouse `P40(x,y)&P40(z,y)⇒P26` (0.87) | one | 36 / 36 | 1.000 | 0.904 | selected |
| | both | 27 / 36 | 0.750 | 0.589 | selected |
| | ordered | 63 / 63 | 1.000 | 0.943 | selected |
| Shared citizen → diplomatic `P27(y,x)&P27(y,z)⇒P530` (0.88) | one | 303 / 772 | 0.392 | 0.359 | selected |
| | both | 246 / 772 | 0.319 | 0.287 | selected |
| Symmetry P26 / P3373 / P451 / P530 | one = both | e.g. P26 335 / 354 | 0.946 | 0.918 | selected |
| Shared influence `P737(x,y)&P737(z,y)⇒P737` (0.012) | one | 210 couples | 0.084 | 0.074 | selected (below 0.10 floor) |
| | both | 2 | – | – | dropped (support < 5) |
| | ordered | 212 pairs | 0.060 | 0.053 | selected (below floor) |
| `P737(y,x)&P737(y,z)⇒P737` (0.012) | one | 207 couples | 0.059 | 0.052 | selected (below floor) |
| | ordered | 208 pairs | 0.030 | 0.026 | rejected (PCA < 0.05) |

Support is shown as support / PCA body. For the symmetry rules, the "both"
head coverage is trivially 1.0.

**Validation at the reference point (0.10, 10), without the six excluded rules,
is the same in every mode:** 160 rules, TP 2,451, FP 594, precision 0.805,
recall 0.238, F1 0.3671. The only change in the rule set is that `both` and
`ordered` keep sibling transitivity instead of shared-sibling. The two rules
cover exactly the same validation triples. So validation cannot choose
between the definitions. The choice has to rest on what each definition means.

**Which definition fits which rule type:**

1. **Symmetry rules `p(z,x)⇒p(x,z)`.** The two definitions are identical by
   construction, because a support pair already needs both directions. Couple
   counting is right here: each couple is one observation of whether the
   reverse fact is stated.
2. **Shared-node bodies with a reciprocal head (spouse, sibling, partner,
   diplomatic relation).** `one` asks whether the couple is linked by the
   head, which is the pattern the rule claims. `both` also asks whether the KG
   recorded the reverse edge. That is a separate gap (12–20% of these facts lack
   their reverse), and the symmetry rules already handle it. So `both` mostly
   penalizes recording incompleteness: shared parent → sibling drops from 0.99
   to 0.71 for that reason. **Use `one` for ranking and eligibility.** Keep
   `both` as a conservative sensitivity figure, because Phase 5 would output
   ordered triples.
3. **Shared-node bodies with a directional head (P737 influenced by, P40, P17,
   P27, …).** Neither couple definition fits. Swapping x and z gives a different
   claim, so the two orders are separate predictions and are not double
   counting. `one` inflates scores: P737 PCA rises from 0.060 to 0.084, and one
   P737 rule is selected only because of that inflation. `both` collapses
   support to nearly 0. **Use ordered pairs.**

**Recommendation: `hybrid`.** Use `one` for reciprocal heads and ordered pairs
for directional heads. In this data it gives the same 160-rule set at (0.10, 10)
as now. It removes the P737 inflation below the floor (193 vs 194 rules selected
overall). Any reciprocity cut-off between 0.02 and 0.80 gives the same split.
Adopting it would be a small production change and needs your approval; it is
not applied.

## B. Sibling transitivity vs shared sibling

| | Transitivity `P3373(x,y)&P3373(y,z)` | Shared sibling `P3373(x,y)&P3373(z,y)` | `P3373(y,x)&P3373(y,z)` |
|---|---:|---:|---:|
| Body / support (ordered pairs) | 526 / 440 | 518 / 432 | 536 / 440 |
| Validation + / − hits | 23 / 1 | 23 / 1 | 23 / 1 |
| Selected under one / both / ordered / hybrid | no / yes / yes / no | yes / no / no / yes | no in all |

- **Overlap:** support Jaccard 0.964 between transitivity and shared sibling (body Jaccard 0.970).
  - Transitivity has 12 support pairs the shared-sibling rule lacks; the shared-sibling rule has 4 that transitivity lacks.
  - The overlap is high because sibling facts are mostly stated in both directions, so the chain and the shared-node paths usually exist together.
- **Validation:** identical hits. Neither rule adds a single validation positive beyond what the other proposed rules already cover (sibling symmetry and shared parent cover all 23). Each causes the same 1 false hit, which no other rule covers.
- **F1 changes:** adding transitivity to the 160-rule set leaves F1 at 0.3671. Removing shared sibling removes 1 false hit (F1 0.36705 → 0.36708, precision 0.8049 → 0.8052).

**Recommendation: retain one, not both.** They are near-duplicates and keeping
both would double-count the same evidence in Phase 5 explanations. Which one is
kept follows from the counting choice: shared sibling under `one`/`hybrid`,
transitivity under `both`/`ordered`. Validation cannot tell them apart.
Transitivity is the more conventional and easier-to-explain form, if you prefer
it on that basis. The other rule stays in the candidates file as a documented
near-duplicate. Both add little: no unique validation coverage and one false
hit. Down-weighting it in Phase 5 is also reasonable.

## Limitations

- Validation metrics are identical across modes at the reference point, so the definition choice rests on reasoning, not validation evidence.
- Reciprocity is measured from the data, not from verified relation semantics. A label suggesting symmetry is still only a hypothesis.
- The PCA body is unchanged in the `both` mode. A stricter `both` could also change the denominator.
- Only candidates recorded in `run_grid_ext` (support ≥ 5 couples) were re-scored. Under `ordered`/`hybrid`, a few rules with 3–4 couples (6–8 ordered pairs) could become candidates below support 10. None of these could enter the (0.10, 10) set.
- Results describe this CoDEx-M training snapshot only and are statistical, not semantic.

## Tests and integrity

- 62 Phase 4 tests pass on your computer (Python 3.10, `unittest`), including 5 new tests in `tests/test_phase4_methodology_experiment.py`. They cover one-vs-both counting, symmetry-rule equivalence, reproduction of production results, no test-file access, no overwrite, and the reciprocity measure.
- Integrity: all 34 files hashed before the work are unchanged. That covers both run folders, `phase5_candidate_rules_proposed.json` (SHA-256 `3723c68a…4a54`), the Phase 4 reports and the production scripts and tests. The script also checks the run files and the candidate list itself.

## Decisions requested

1. Adopt `hybrid` counting (couples for reciprocal heads, ordered pairs otherwise) in a new production run?
2. For siblings, keep shared sibling (current) or switch to transitivity, with the other recorded as a near-duplicate?
