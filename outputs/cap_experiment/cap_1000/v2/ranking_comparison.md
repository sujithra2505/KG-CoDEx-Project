# Phase 5 ranking v2 vs v1

Same candidates, scores and rules as v1. Only the tie-break changed:

`max Wilson lower bound desc → max_pca_confidence desc → distinct_body_matches desc → supporting_rules desc → subject ID number asc → object ID number asc`

Evidence count: distinct sets of training triples that satisfy a supporting rule body for (x, z), deduplicated across rules; matches may share individual triples.

## Totals

- Predictions kept in both versions: 22,408; dropped from v1: 1,364; added in v2: 1,364
- Kept predictions whose rank changed: 13,103
- Capped relations where subject/object IDs still decide the cut: v1 17 → v2 17
- Capped relations where every candidate ties before the ID step: v1 3 → v2 2
- v2 score tiers: 0.4–0.7: 6,145, < 0.4: 15,414, ≥ 0.7: 2,213 (identical to v1: the cut only moves inside equal-score groups)
- Distinct body matches per retained prediction: min 1, median 1, max 553; 13,726 have exactly one

## Per relation

| Relation | Cand. | Kept | Same | Dropped / added | Rank moved | v1 boundary group (ID decides?) | v2 boundary group (ID decides?) |
|---|---:|---:|---:|---:|---:|---|---|
| country (P17) | 4,733 | 1000 | 960 | 40 / 40 | 871 | 114 (yes) | 8 (yes) |
| place of birth (P19) | 17,579 | 1000 | 1000 | 0 / 0 | 128 | 1,294 (yes) | 1,294 (yes) |
| place of death (P20) | 19,928 | 1000 | 1000 | 0 / 0 | 21 | 1,290 (yes) | 1,290 (yes) |
| spouse (P26) | 496 | 496 | 496 | 0 / 0 | 7 | not capped | not capped |
| country of citizenship (P27) | 32,283 | 1000 | 978 | 22 / 22 | 803 | 127 (yes) | 36 (yes) |
| continent (P30) | 126 | 126 | 126 | 0 / 0 | 91 | not capped | not capped |
| official language (P37) | 3,488 | 1000 | 999 | 1 / 1 | 970 | 580 (yes) | 561 (yes) |
| child (P40) | 39 | 39 | 39 | 0 / 0 | 0 | not capped | not capped |
| educated at (P69) | 3,540 | 1000 | 1000 | 0 / 0 | 0 | 3,540 (yes) | 3,540 (yes) |
| field of work (P101) | 974 | 974 | 974 | 0 / 0 | 947 | not capped | not capped |
| member of political party (P102) | 272 | 272 | 272 | 0 / 0 | 184 | not capped | not capped |
| occupation (P106) | 14,439 | 1000 | 980 | 20 / 20 | 978 | 1,117 (yes) | 974 (yes) |
| employer (P108) | 8,011 | 1000 | 1000 | 0 / 0 | 0 | 8,011 (yes) | 8,011 (yes) |
| place of burial (P119) | 123 | 123 | 123 | 0 / 0 | 38 | not capped | not capped |
| located in the administrative terroritorial entity (P131) | 3,576 | 1000 | 1000 | 0 / 0 | 415 | 687 (yes) | 687 (yes) |
| movement (P135) | 460 | 460 | 460 | 0 / 0 | 434 | not capped | not capped |
| genre (P136) | 4,442 | 1000 | 962 | 38 / 38 | 921 | 841 (yes) | 73 (yes) |
| religion (P140) | 2,005 | 1000 | 986 | 14 / 14 | 560 | 466 (yes) | 26 (yes) |
| headquarters location (P159) | 160 | 160 | 160 | 0 / 0 | 0 | not capped | not capped |
| cast member (P161) | 379 | 379 | 379 | 0 / 0 | 0 | not capped | not capped |
| ethnic group (P172) | 15,063 | 1000 | 949 | 51 / 51 | 791 | 14,109 (yes) | 14,056 (yes) |
| record label (P264) | 145 | 145 | 145 | 0 / 0 | 0 | not capped | not capped |
| part of (P361) | 895 | 895 | 895 | 0 / 0 | 895 | not capped | not capped |
| unmarried partner (P451) | 908 | 908 | 908 | 0 / 0 | 0 | not capped | not capped |
| member of (P463) | 9,673 | 1000 | 209 | 791 / 791 | 209 | 7,823 (yes) | 115 (yes) |
| country of origin (P495) | 2,968 | 1000 | 841 | 159 / 159 | 776 | 1,802 (yes) | 1,517 (yes) |
| cause of death (P509) | 246 | 246 | 246 | 0 / 0 | 0 | not capped | not capped |
| diplomatic relation (P530) | 3,938 | 1000 | 772 | 228 / 228 | 236 | 1,136 (yes) | 76 (yes) |
| residence (P551) | 20,713 | 1000 | 1000 | 0 / 0 | 971 | 3,754 (yes) | 3,754 (yes) |
| narrative location (P840) | 633 | 633 | 633 | 0 / 0 | 632 | not capped | not capped |
| instrument (P1303) | 791 | 791 | 791 | 0 / 0 | 446 | not capped | not capped |
| languages spoken, written, or signed (P1412) | 11,336 | 1000 | 1000 | 0 / 0 | 683 | 155 (yes) | 154 (yes) |
| sibling (P3373) | 125 | 125 | 125 | 0 / 0 | 96 | not capped | not capped |

Boundary group = candidates sharing every criterion before the ID step with the 100th prediction.
Score multisets per relation are unchanged and provenance (supporting rules) of predictions kept in both versions is unchanged:
True / True.

## Caveats

- More body matches is more proof paths, not more independent evidence: matches can share triples, and hubs create many paths.
- No validation or test data was used; whether v2 ranks better is not measured here.
