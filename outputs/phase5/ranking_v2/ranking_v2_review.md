# Ranking v2 review

**Date:** 2026-10-29. Full numbers: `ranking_comparison.md` and `phase5_manifest.json`
in this folder. Phase 6 not started. No validation or test file was opened, no
thresholds were tuned, and nothing was scored.

## What changed

- **New tie-break order:** Wilson → PCA → **distinct body matches** → supporting rules → subject ID → object ID.
- **Body match (evidence count):** one set of training triples that makes a supporting rule's body true for (x, z).
  - Matches are deduplicated across rules as sets of triples, so the same proof found twice counts once.
  - Every counted triple is checked to be in the training graph.
  - The count is cross-checked against the stored `body_groundings` of each retained prediction.
- **Why the count is defensible:** v1 already stored every grounding for retained predictions. The same
  definition is recomputed from the training graph for all 184,487 candidates, so no proxy is used.
- **What the count is not:** proofs can share a triple (same first atom, different middle entity), so a
  higher count means more proof paths, not more independent evidence.

## Results

- **Changed predictions:** 409 of 3,239 were replaced (kept in both: 2,830). 1,499 kept predictions changed rank.
  - Largest changes: P463 (97 of 100), P361 (79), P840 (47), P106 (40), P136 (39), P101 (38), P1412 (38).
- **Unchanged:**
  - candidates, scores and supporting rules
  - per-relation score multisets and score tiers (778 / 1,036 / 1,425)
  - provenance of every prediction kept in both versions
  - no overlap with training
- **Ties:** relations where every candidate ties before the ID step went from 9 to 6.
  - The boundary group shrank in many relations, for example P463 7,823 → 10 and P136 882 → 52.
  - IDs still decide the cut in 32 of 32 capped relations.
  - In 14 relations the boundary group did not shrink at all, because the tied candidates have equal match counts
    (often a single 1-atom rule gives each exactly one match): P26, P27, P69, P108, P119, P131, P159, P161, P172,
    P264, P451, P495, P509 and P3373.
  - P106 moved from "rule count decides" (v1) to "IDs decide" (v2), because evidence now comes before rule count.
- **Evidence distribution:** median 2 matches, max 553. 1,394 retained predictions have exactly one match.

## Caution: hubs win the new tie-break

More proof paths often come from hub entities:

- "Paris → official language → French" (553 matches) is plausible.
- P463 member of now starts with "Taiwan → Interpol / ITU / IBRD / UNESCO" (155–159 matches each), via
  Taiwan's many diplomatic relations. Several of these are likely false in the real world.
- P361 part of: "Germany → part of → Latin America" is now rank 2.

So v2 removes much of the arbitrary ID ordering, but it can push hub-driven errors up. Whether v1 or v2
ranks better can only be measured on held-out data (Phase 6).

## Tests and integrity

- 84 Phase 4 and Phase 5 tests pass on your computer (Python 3.10, `unittest`). The 11 new tests in
  `tests/test_phase5_rank_v2.py` cover:
  - evidence counting: one match per middle, matches add across rules, duplicate proofs are not
    double-counted, shared-triple proofs count as distinct
  - tie order: evidence, then rules, then IDs
  - v1 files unchanged and split files never opened
  - determinism and no overwrite
  - no training overlap, the cap, and evidence fields that match the stored groundings
  - same scores and provenance as v1, and sorted order
- All 44 previously hashed files are unchanged: data, Phase 1–5 outputs, `phase5_predict.py` and the Phase 4 scripts.
  The validation and test files have the same size and timestamp.
- New files: `phase5_rank_v2.py`, `tests/test_phase5_rank_v2.py` and this folder.

## Decision for you

Keep v2 for Phase 6 (and evaluate v1 and v2 side by side there), or keep v1 only.
