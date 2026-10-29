# Phase 4 results review (`run_default`) before Phase 5

**Review date:** 2026-10-29
**Scope:** Read-only review of `outputs/phase4/run_default/`. No rules were mined,
no predictions were generated, no test file was opened, and no existing result
was changed (all 8 run files have the same SHA-256 before and after the review).
Validation figures below were recomputed independently from
`selected_rules.json`, the Phase 3 training graph, `data/valid.txt` and
`data/valid_negatives.txt`.

## 1. Validation metric definitions (confirmed from `phase4_rule_evaluation.py`)

A validation triple `(s, r, o)` is **covered** if at least one rule in the
subset has head `r` and its body holds for `(s, o)` in the training graph.

| Quantity | Exact definition | `run_default` value |
|---|---|---|
| TP | Distinct validation **positives** covered by at least one rule | 2,455 |
| FP | Distinct supplied validation **negatives** covered by at least one rule | 594 |
| FN | All 10,310 validation positives − TP (includes 159 positives whose relation has no rule) | 7,855 |
| Precision | TP / (TP + FP) | 0.805 |
| Recall | TP / 10,310 | 0.238 |
| F1 | 2PR / (P + R) | 0.368 |
| Per-rule `val_precision_lower_bound` | rule's validation-positive hits / **all** body pairs with no training head (`unknown_head_pairs_count`) | median 0.017 |
| Grid choice | max F1 over 12 points; ties → stricter | `min_pca` 0.10, `min_support` 10 (the grid floor) |

The independent recomputation gave exactly the same TP, FP, precision,
recall and F1. True negatives are not used. A triple covered by several rules
counts once: the rules' individual hits add up to 3,657, but there are 2,455
distinct covered positives.

## 2. Why per-rule bounds are tiny but aggregate precision is high

The two numbers have **different denominators**, so they measure different things.

- **Per-rule bound.** The denominator is every pair the rule's body reaches
  without a training head. Across the 166 rules that is 213,028 pairs
  (median 314 per rule). Validation holds about 5% of the known positive facts
  (10,310 of 206,205 across train/valid/test). Most true facts are missing from
  the KG altogether, so a correct new pair is rarely in `valid.txt`. A bound of
  0.02–0.05 is therefore expected even for a good rule. It does **not** show
  the rules are 95–98% wrong. It also does not show they are right: open-world
  precision is unknown.
- **Aggregate precision.** The denominator is only the validation triples the
  rules cover: a nearly balanced, fixed set of 10,310 positives and 10,310
  supplied negatives. It answers a narrower question: on these listed
  candidates, does rule coverage separate positives from negatives? It is not
  the precision of the rules' wider output.
- **Relation mix inflates it.** Negatives are not spread like positives. P530 has
  302 positives but only 5 negatives, and the P530 symmetry rule alone gives
  271 TP that cannot become FP. P26 has 41 positives and 280 negatives with 0
  negatives covered, which is a real but small signal. P27 has 2,898 negatives
  and gives 240 of the 594 FP. Per-relation precision ranges from 0.29 (P37)
  and 0.46 (P136) to 1.0.
- **Concentration.** The top 5 rules give 50% of TP; the top 10 give 64%.
- **Optimism.** Thresholds were picked on the same validation set (12 grid
  points). The winning point is the grid edge, so the true optimum is untested.
- **Negatives.** The supplied negatives were not independently verified (Phase 1).

Fair summary: rule coverage separates the supplied validation positives from
the supplied negatives fairly well (P 0.81, R 0.24), with large differences by
relation. These results do not establish how accurate rule-derived edges would
be in general.

## 3. Proposed controlled extension of the threshold grid (not run)

The existing run cannot be loosened in place. Candidates with support below
10 were never recorded, and selection (dominance, top-k) happens at mining
time. Proposal for a **new, separate run** (`run_default` stays untouched):

1. **New mining run** `outputs/phase4/run_grid_ext/` with only two settings
   changed: `--min-support 5 --min-pca 0.05`. All else is as in `run_default`
   (`min_pca_body` 20, `min_head_coverage` 0.01, `min_lift` 1.5, `top_k_per_head` 50,
   `max_body_paths` 5,000,000). Sizing from the existing candidate file: 25
   recorded candidates fail only on `pca < 0.10` with PCA in [0.05, 0.10) (11 in
   [0.075, 0.10)). The support 5–9 range is unrecorded (1,562 rule/head
   combinations sit below support 10 at any PCA), so the added count is
   unknown until the run.
2. **Extended grid:** `min_pca` ∈ {0.05, 0.075, 0.10, 0.20, 0.30, 0.50} ×
   `min_support` ∈ {5, 10, 20, 50} (24 points). The current 12 points are a subset.
3. **Nesting check:** report whether the new run's rules with PCA ≥ 0.10 and
   support ≥ 10 are exactly the 166 `run_default` rules. Report any rule
   displaced by the greedy dominance or top-k step.
4. **Decision rule, fixed in advance:** adopt a looser point only if F1 rises by
   ≥ 0.01 over (0.10, 10) **and** precision stays ≥ 0.75. Otherwise keep
   `run_default`. Report per-relation TP/FP changes.
5. **Sensitivity view:** also score each grid point with single-hub rules
   (one middle entity carries 100% of support), unstable rules and tiny-relation
   bodies removed (Section 4).
6. Same guards as before: no test files, no listed new pairs, new folder only.

Needs code changes before running (to be approved): the evaluator's grid
constants must become command-line options, and it needs a read-only
comparison step against `run_default`.

## 4. Top rules, hub flags and unstable rules

**Top 10 (by Wilson bound):** 4 symmetry rules (P26 spouse, P451 unmarried
partner, P3373 sibling, P530 diplomatic relation), 3 family compositions
(shared child → spouse; child-of-sibling → child; shared parent → sibling),
P3373 transitivity, and two chains (educated at + country → citizenship; place
of death + official language → language spoken). All 10 have 0–1 validation
negative hits, and all are stable on the 90% split (PCA drop ≤ 0.09).

**Symmetric bodies double-count evidence.** In 8 selected rules, swapping x
and z gives the same body (symmetry rules, shared-parent/shared-child
bodies). Each pair is then counted in both orders, so `support` and the
Wilson `n` are inflated about 2×. Rankings of these rules are therefore
optimistic. Proposal for a later run: compute Wilson on unordered pairs for
symmetric bodies.

**Hub-dominated (10 rules).** These mostly reflect one entity, not a
general pattern:

- Three rules rely 100% on one middle entity:
  - `P138(y,x) & P138(y,z) => P3373(x,z)`: The Jackson 5
  - `P17(x,y) & P159(y,z) => P17(x,z)`: Kingdom of Prussia
  - `P140 & P3095 → P172` and its reverse: Judaism / Jewish people, through
    **P3095**, which has only 2 training triples
- The two EU rules (`P530`/`P463 → P530`) rely 95% on the European Union.
- `P27 & P172 → P172` relies 76% on the USA. `P530 & P463 → P463` relies 75%
  on Germany, but it has 170 validation hits and only 7 negative hits.

**Unstable (5 rules).** None of the 5 was scored on the 90% split (support fell
below 10 or the shape stopped joining). Three are the single-hub rules above.
The other two (ranks 160 and 166, PCA 0.16 and 0.11) have 0 validation hits.

**Recommended before Phase 5 (needs approval; not applied):** exclude or
down-weight rules that are unstable, rely on one middle entity for 100% of
support, or use a body relation with fewer than 20 training triples. That is
6 rules: ranks 49, 65, 69, 145, 160 and 166. Keep the EU, Germany and USA hub
rules (ranks 96, 101, 107, 108) flagged rather than removed, because they have
validation support.

### Shared child → spouse: `P40(x,y) & P40(z,y) => P26(x,z)`

| Measure | Value |
|---|---|
| Support / body / PCA body | 63 / 78 / 63 ordered pairs |
| PCA / standard confidence | 1.00 / 0.81 |
| Distinct couples (unordered) | 36 supporting, 39 body pairs |
| Wilson as reported (n = 63) | 0.94 |
| Wilson on unordered pairs (36 of 39) | 0.80 |
| Children involved | 54, at most 2 supporting pairs per child (no hub) |
| PCA counterexamples | 0 |
| Validation | 4 hits, 0 negative hits (P26 has 280 negatives in validation) |
| 90% split | PCA 0.96, selected again, stable |

Examples: Mary Wollstonecraft & William Godwin (child Mary Shelley); Bill &
Hillary Clinton; Indira & Feroze Gandhi; Yoko Ono & John Lennon.

Assessment: a consistent pattern **in this dataset**, but on a small and
selective base. P40 (child) has only 357 training triples, and only 57
children list two parents. These are mostly famous families where both
parents are notable and usually married. The same body did not reach
`min_support` for P451 (unmarried partner). In the wider world many co-parents
are not spouses, so PCA 1.0 should not be read as "co-parents are married".
Corrected for double counting, the evidence is 36 couples. Recommendation:
keep it, add a note about its small, selective base, and use the
unordered-pair Wilson (0.80) when comparing it with other rules.

## 5. Decisions requested

1. Approve (or change) the grid-extension run in Section 3, including the
   evaluator option change and the fixed adoption rule.
2. Approve the exclusion/down-weighting criteria in Section 4 for the rule
   set passed to Phase 5.
3. Approve an unordered-pair Wilson for symmetric bodies in the next run.

Phase 5 has not been started.
