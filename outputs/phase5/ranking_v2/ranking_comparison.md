# Phase 5 ranking v2 vs v1

Same candidates, scores and rules as v1. Only the tie-break changed:

`max Wilson lower bound desc → max_pca_confidence desc → distinct_body_matches desc → supporting_rules desc → subject ID number asc → object ID number asc`

Evidence count: distinct sets of training triples that satisfy a supporting rule body for (x, z), deduplicated across rules; matches may share individual triples.

## Totals

- Predictions kept in both versions: 2,830; dropped from v1: 409; added in v2: 409
- Kept predictions whose rank changed: 1,499
- Capped relations where subject/object IDs still decide the cut: v1 31 → v2 32
- Capped relations where every candidate ties before the ID step: v1 9 → v2 6
- v2 score tiers: 0.4–0.7: 1,036, < 0.4: 1,425, ≥ 0.7: 778 (identical to v1: the cut only moves inside equal-score groups)
- Distinct body matches per retained prediction: min 1, median 2, max 553; 1,394 have exactly one

## Per relation

| Relation | Cand. | Kept | Same | Dropped / added | Rank moved | v1 boundary group (ID decides?) | v2 boundary group (ID decides?) |
|---|---:|---:|---:|---:|---:|---|---|
| country (P17) | 4,733 | 100 | 93 | 7 / 7 | 53 | 24 (yes) | 6 (yes) |
| place of birth (P19) | 17,579 | 100 | 99 | 1 / 1 | 98 | 21 (yes) | 20 (yes) |
| place of death (P20) | 19,928 | 100 | 100 | 0 / 0 | 21 | 294 (yes) | 293 (yes) |
| spouse (P26) | 496 | 100 | 100 | 0 / 0 | 7 | 90 (yes) | 90 (yes) |
| country of citizenship (P27) | 32,283 | 100 | 100 | 0 / 0 | 87 | 59 (yes) | 59 (yes) |
| continent (P30) | 126 | 100 | 100 | 0 / 0 | 91 | 69 (yes) | 58 (yes) |
| official language (P37) | 3,488 | 100 | 98 | 2 / 2 | 90 | 31 (yes) | 26 (yes) |
| child (P40) | 39 | 39 | 39 | 0 / 0 | 0 | not capped | not capped |
| educated at (P69) | 3,540 | 100 | 100 | 0 / 0 | 0 | 3,540 (yes) | 3,540 (yes) |
| field of work (P101) | 974 | 100 | 62 | 38 / 38 | 61 | 502 (yes) | 445 (yes) |
| member of political party (P102) | 272 | 100 | 98 | 2 / 2 | 70 | 90 (yes) | 88 (yes) |
| occupation (P106) | 14,439 | 100 | 60 | 40 / 40 | 58 | 42 (no) | 28 (yes) |
| employer (P108) | 8,011 | 100 | 100 | 0 / 0 | 0 | 8,011 (yes) | 8,011 (yes) |
| place of burial (P119) | 123 | 100 | 100 | 0 / 0 | 38 | 78 (yes) | 78 (yes) |
| located in the administrative terroritorial entity (P131) | 3,576 | 100 | 100 | 0 / 0 | 0 | 129 (yes) | 129 (yes) |
| movement (P135) | 460 | 100 | 93 | 7 / 7 | 90 | 193 (yes) | 171 (yes) |
| genre (P136) | 4,442 | 100 | 61 | 39 / 39 | 61 | 882 (yes) | 52 (yes) |
| religion (P140) | 2,005 | 100 | 100 | 0 / 0 | 70 | 103 (yes) | 90 (yes) |
| headquarters location (P159) | 160 | 100 | 100 | 0 / 0 | 0 | 160 (yes) | 160 (yes) |
| cast member (P161) | 379 | 100 | 100 | 0 / 0 | 0 | 379 (yes) | 379 (yes) |
| ethnic group (P172) | 15,063 | 100 | 100 | 0 / 0 | 56 | 87 (yes) | 87 (yes) |
| record label (P264) | 145 | 100 | 100 | 0 / 0 | 0 | 145 (yes) | 145 (yes) |
| part of (P361) | 895 | 100 | 21 | 79 / 79 | 21 | 895 (yes) | 33 (yes) |
| unmarried partner (P451) | 908 | 100 | 100 | 0 / 0 | 0 | 642 (yes) | 642 (yes) |
| member of (P463) | 9,673 | 100 | 3 | 97 / 97 | 3 | 7,823 (yes) | 10 (yes) |
| country of origin (P495) | 2,968 | 100 | 100 | 0 / 0 | 74 | 63 (yes) | 63 (yes) |
| cause of death (P509) | 246 | 100 | 100 | 0 / 0 | 0 | 246 (yes) | 246 (yes) |
| diplomatic relation (P530) | 3,938 | 100 | 94 | 6 / 6 | 94 | 130 (yes) | 112 (yes) |
| residence (P551) | 20,713 | 100 | 94 | 6 / 6 | 87 | 110 (yes) | 98 (yes) |
| narrative location (P840) | 633 | 100 | 53 | 47 / 47 | 53 | 633 (yes) | 581 (yes) |
| instrument (P1303) | 791 | 100 | 100 | 0 / 0 | 62 | 216 (yes) | 215 (yes) |
| languages spoken, written, or signed (P1412) | 11,336 | 100 | 62 | 38 / 38 | 58 | 150 (yes) | 103 (yes) |
| sibling (P3373) | 125 | 100 | 100 | 0 / 0 | 96 | 27 (yes) | 27 (yes) |

Boundary group = candidates sharing every criterion before the ID step with the 100th prediction.
Score multisets per relation are unchanged and provenance (supporting rules) of predictions kept in both versions is unchanged:
True / True.

## Caveats

- More body matches is more proof paths, not more independent evidence: matches can share triples, and hubs create many paths.
- No validation or test data was used; whether v2 ranks better is not measured here.
