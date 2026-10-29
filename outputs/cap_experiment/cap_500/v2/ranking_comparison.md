# Phase 5 ranking v2 vs v1

Same candidates, scores and rules as v1. Only the tie-break changed:

`max Wilson lower bound desc → max_pca_confidence desc → distinct_body_matches desc → supporting_rules desc → subject ID number asc → object ID number asc`

Evidence count: distinct sets of training triples that satisfy a supporting rule body for (x, z), deduplicated across rules; matches may share individual triples.

## Totals

- Predictions kept in both versions: 12,403; dropped from v1: 1,168; added in v2: 1,168
- Kept predictions whose rank changed: 6,653
- Capped relations where subject/object IDs still decide the cut: v1 22 → v2 22
- Capped relations where every candidate ties before the ID step: v1 5 → v2 2
- v2 score tiers: 0.4–0.7: 3,567, < 0.4: 8,302, ≥ 0.7: 1,702 (identical to v1: the cut only moves inside equal-score groups)
- Distinct body matches per retained prediction: min 1, median 1, max 553; 6,885 have exactly one

## Per relation

| Relation | Cand. | Kept | Same | Dropped / added | Rank moved | v1 boundary group (ID decides?) | v2 boundary group (ID decides?) |
|---|---:|---:|---:|---:|---:|---|---|
| country (P17) | 4,733 | 500 | 411 | 89 / 89 | 324 | 459 (yes) | 13 (yes) |
| place of birth (P19) | 17,579 | 500 | 500 | 0 / 0 | 128 | 1,294 (yes) | 1,294 (yes) |
| place of death (P20) | 19,928 | 500 | 500 | 0 / 0 | 21 | 1,290 (yes) | 1,290 (yes) |
| spouse (P26) | 496 | 496 | 496 | 0 / 0 | 7 | not capped | not capped |
| country of citizenship (P27) | 32,283 | 500 | 491 | 9 / 9 | 398 | 34 (yes) | 26 (yes) |
| continent (P30) | 126 | 126 | 126 | 0 / 0 | 91 | not capped | not capped |
| official language (P37) | 3,488 | 500 | 483 | 17 / 17 | 454 | 580 (yes) | 561 (yes) |
| child (P40) | 39 | 39 | 39 | 0 / 0 | 0 | not capped | not capped |
| educated at (P69) | 3,540 | 500 | 500 | 0 / 0 | 0 | 3,540 (yes) | 3,540 (yes) |
| field of work (P101) | 974 | 500 | 498 | 2 / 2 | 497 | 502 (yes) | 445 (yes) |
| member of political party (P102) | 272 | 272 | 272 | 0 / 0 | 184 | not capped | not capped |
| occupation (P106) | 14,439 | 500 | 387 | 113 / 113 | 385 | 1,117 (yes) | 974 (yes) |
| employer (P108) | 8,011 | 500 | 500 | 0 / 0 | 0 | 8,011 (yes) | 8,011 (yes) |
| place of burial (P119) | 123 | 123 | 123 | 0 / 0 | 38 | not capped | not capped |
| located in the administrative terroritorial entity (P131) | 3,576 | 500 | 470 | 30 / 30 | 330 | 222 (yes) | 112 (yes) |
| movement (P135) | 460 | 460 | 460 | 0 / 0 | 434 | not capped | not capped |
| genre (P136) | 4,442 | 500 | 484 | 16 / 16 | 484 | 882 (yes) | 815 (yes) |
| religion (P140) | 2,005 | 500 | 483 | 17 / 17 | 74 | 467 (yes) | 48 (yes) |
| headquarters location (P159) | 160 | 160 | 160 | 0 / 0 | 0 | not capped | not capped |
| cast member (P161) | 379 | 379 | 379 | 0 / 0 | 0 | not capped | not capped |
| ethnic group (P172) | 15,063 | 500 | 447 | 53 / 53 | 289 | 14,109 (yes) | 14,056 (yes) |
| record label (P264) | 145 | 145 | 145 | 0 / 0 | 0 | not capped | not capped |
| part of (P361) | 895 | 500 | 391 | 109 / 109 | 391 | 895 (yes) | 553 (yes) |
| unmarried partner (P451) | 908 | 500 | 500 | 0 / 0 | 0 | 642 (yes) | 642 (yes) |
| member of (P463) | 9,673 | 500 | 57 | 443 / 443 | 57 | 7,823 (yes) | 56 (yes) |
| country of origin (P495) | 2,968 | 500 | 267 | 233 / 233 | 202 | 1,802 (yes) | 181 (yes) |
| cause of death (P509) | 246 | 246 | 246 | 0 / 0 | 0 | not capped | not capped |
| diplomatic relation (P530) | 3,938 | 500 | 500 | 0 / 0 | 146 | 536 (yes) | 536 (yes) |
| residence (P551) | 20,713 | 500 | 490 | 10 / 10 | 483 | 843 (yes) | 817 (yes) |
| narrative location (P840) | 633 | 500 | 483 | 17 / 17 | 483 | 633 (yes) | 581 (yes) |
| instrument (P1303) | 791 | 500 | 499 | 1 / 1 | 285 | 207 (yes) | 199 (yes) |
| languages spoken, written, or signed (P1412) | 11,336 | 500 | 491 | 9 / 9 | 372 | 226 (yes) | 195 (yes) |
| sibling (P3373) | 125 | 125 | 125 | 0 / 0 | 96 | not capped | not capped |

Boundary group = candidates sharing every criterion before the ID step with the 100th prediction.
Score multisets per relation are unchanged and provenance (supporting rules) of predictions kept in both versions is unchanged:
True / True.

## Caveats

- More body matches is more proof paths, not more independent evidence: matches can share triples, and hubs create many paths.
- No validation or test data was used; whether v2 ranks better is not measured here.
