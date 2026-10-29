# Phase 4: grid extension, couple counting and rule exclusions — summary

**Date:** 2026-10-29. Full tables: `phase4_grid_ext_report.md`; all numbers:
`phase4_grid_ext_comparison.json`. `run_default/` was not changed (8 file hashes
checked before and after; 166 rules still present). No test files were opened,
no predictions were written, and Phase 5 was not started.

## What changed

| Item | Change |
|---|---|
| Miner `4B.2.0` | New setting `symmetric_unit` (default `unordered`; `ordered` reproduces `run_default`) |
| Evaluator `4B.2.0` | Grid values are options (`--grid-min-pca`, `--grid-min-support`); optional exclusion list scored side by side |
| `phase4_compare_runs.py` | New, read-only comparison with the fixed adoption rule; writes the report, the JSON and the proposed candidate list |
| New run | `run_grid_ext/`: `min_support` 5, `min_pca` 0.05, everything else as `run_default` |

### Counting rule for swap-invariant rules (documented and applied to every such rule)

A rule is swap-invariant if renaming x↔z leaves it unchanged: symmetry rules
`p(z,x) ⇒ p(x,z)` and bodies `p(x,y) & p(z,y)` or `p(y,x) & p(y,z)`. For these,
one couple {x,z} is one unit:

- body = couples where the body holds
- support = couples where the head holds **in at least one direction**
- PCA body = couples with at least one ordered pair in the PCA body
- head count = couples linked by the head relation

These numbers feed confidence, PCA confidence, head coverage, the Wilson bound
and the `min_support` / `min_pca_body` limits. Lift and
`unknown_head_pairs_count` stay ordered, and every rule keeps `ordered_counts`.
In `run_grid_ext`, 10 of the 194 selected rules use couple counting.

**Caveat.** The "at least one direction" support rule is lenient when a head
is stated in only one direction. Example: shared parent → sibling had 218
ordered support pairs over 256 body pairs (PCA 0.865). Per couple it has 127 of
128 (PCA 0.992), now rank 1. Each couple counts once, but a one-way sibling
statement now counts as full support. A stricter alternative ("both
directions") is possible if you prefer.

**Correction to the earlier review:** the shared-child → spouse Wilson on
couples is **0.904** (36 of 36 PCA-body couples), not 0.80. The earlier
estimate divided by the 39 body couples.

## Grid result (24 points, fixed adoption rule)

| Variant | Baseline F1 at (0.10, 10) | Best looser point | F1 | Precision | Gain | Decision |
|---|---:|---|---:|---:|---:|---|
| All rules | 0.3675 | (0.05, 10) | 0.3729 | 0.780 | +0.0054 | not adopted |
| Without the 6 rules | 0.3671 | (0.05, 10) | 0.3724 | 0.780 | +0.0054 | not adopted |

Loosening to `min_pca` 0.05 adds 71 true and 117 false validation hits.
Precision stays above 0.75, but the F1 gain is below the 0.01 bar.

## Rule counts and changes

- `run_default`: 166 rules (160 without the six). `run_grid_ext`: 194 rules, of which
  165 meet the old floor (0.10, 10) and 29 sit below it. 164 of the 166 old rules are still selected.
- At (0.10, 10), validation metrics are identical to `run_default`
  (TP 2,455, FP 594, P 0.805, R 0.238, F1 0.3675). Removing the six rules
  costs 4 TP and 0 FP (F1 0.3671).
- Changes at (0.10, 10):
  - removed: `P3373(x,y) & P3373(y,z) => P3373(x,z)` (sibling transitivity). It is now
    `redundant_with` the shared-sibling rule, which rose to rank 5 under couple counting.
  - removed: `P138 … => P3373` (one of the six). It has 10 couples, below `min_pca_body` 20.
  - added: `P3373(x,y) & P3373(z,y) => P3373(x,z)`.
- Symmetry rules now score lower: P530 PCA 0.879 → 0.784, P3373 0.917 → 0.847,
  P451 0.929 → 0.867, P26 0.972 → 0.946.
- Stability (90/10): 181 rules on 90%, overlap 0.85, 5 unstable. 12 rules are hub-flagged.

## Proposed Phase 5 candidate set (not approved)

`phase5_candidate_rules_proposed.json`: **160 rules**. These are the `run_grid_ext`
rules at (0.10, 10) with couple counting, minus the six excluded rules (five of
them are in this run; rank 49 had already dropped out). It is a rule list only.

## Decisions for you

1. Accept the 160-rule proposal, or keep the old `run_default` scoring.
2. Keep "at least one direction" couple support, or switch to "both directions".
3. Accept that sibling transitivity is now dropped as redundant, or keep it explicitly.
