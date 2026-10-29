# Phase 5 ranking v2 vs v1

Same candidates, scores and rules as v1. Only the tie-break changed:

`max Wilson lower bound desc → max_pca_confidence desc → distinct_body_matches desc → supporting_rules desc → subject ID number asc → object ID number asc`

Evidence count: distinct sets of training triples that satisfy a supporting rule body for (x, z), deduplicated across rules; matches may share individual triples.

## Totals

- Predictions kept in both versions: 6,666; dropped from v1: 798; added in v2: 798
- Kept predictions whose rank changed: 3,221
- Capped relations where subject/object IDs still decide the cut: v1 25 → v2 24
- Capped relations where every candidate ties before the ID step: v1 6 → v2 3
- v2 score tiers: 0.4–0.7: 2,276, < 0.4: 3,986, ≥ 0.7: 1,202 (identical to v1: the cut only moves inside equal-score groups)
- Distinct body matches per retained prediction: min 1, median 2, max 553; 3,398 have exactly one

## Per relation

| Relation | Cand. | Kept | Same | Dropped / added | Rank moved | v1 boundary group (ID decides?) | v2 boundary group (ID decides?) |
|---|---:|---:|---:|---:|---:|---|---|
| country (P17) | 4,733 | 250 | 244 | 6 / 6 | 204 | 256 (yes) | 235 (yes) |
| place of birth (P19) | 17,579 | 250 | 250 | 0 / 0 | 128 | 148 (yes) | 147 (yes) |
| place of death (P20) | 19,928 | 250 | 250 | 0 / 0 | 21 | 294 (yes) | 293 (yes) |
| spouse (P26) | 496 | 250 | 250 | 0 / 0 | 7 | 270 (yes) | 270 (yes) |
| country of citizenship (P27) | 32,283 | 250 | 238 | 12 / 12 | 172 | 71 (yes) | 31 (yes) |
| continent (P30) | 126 | 126 | 126 | 0 / 0 | 91 | not capped | not capped |
| official language (P37) | 3,488 | 250 | 215 | 35 / 35 | 186 | 121 (yes) | 5 (yes) |
| child (P40) | 39 | 39 | 39 | 0 / 0 | 0 | not capped | not capped |
| educated at (P69) | 3,540 | 250 | 250 | 0 / 0 | 0 | 3,540 (yes) | 3,540 (yes) |
| field of work (P101) | 974 | 250 | 231 | 19 / 19 | 230 | 502 (yes) | 445 (yes) |
| member of political party (P102) | 272 | 250 | 248 | 2 / 2 | 176 | 60 (yes) | 58 (yes) |
| occupation (P106) | 14,439 | 250 | 118 | 132 / 132 | 116 | 1,117 (yes) | 974 (yes) |
| employer (P108) | 8,011 | 250 | 250 | 0 / 0 | 0 | 8,011 (yes) | 8,011 (yes) |
| place of burial (P119) | 123 | 123 | 123 | 0 / 0 | 38 | not capped | not capped |
| located in the administrative terroritorial entity (P131) | 3,576 | 250 | 200 | 50 / 50 | 63 | 159 (yes) | 12 (yes) |
| movement (P135) | 460 | 250 | 224 | 26 / 26 | 213 | 256 (yes) | 225 (yes) |
| genre (P136) | 4,442 | 250 | 205 | 45 / 45 | 205 | 882 (yes) | 815 (yes) |
| religion (P140) | 2,005 | 250 | 250 | 0 / 0 | 70 | 366 (yes) | 366 (yes) |
| headquarters location (P159) | 160 | 160 | 160 | 0 / 0 | 0 | not capped | not capped |
| cast member (P161) | 379 | 250 | 250 | 0 / 0 | 0 | 379 (yes) | 379 (yes) |
| ethnic group (P172) | 15,063 | 250 | 250 | 0 / 0 | 92 | 55 (no) | 49 (no) |
| record label (P264) | 145 | 145 | 145 | 0 / 0 | 0 | not capped | not capped |
| part of (P361) | 895 | 250 | 126 | 124 / 124 | 126 | 895 (yes) | 136 (yes) |
| unmarried partner (P451) | 908 | 250 | 250 | 0 / 0 | 0 | 642 (yes) | 642 (yes) |
| member of (P463) | 9,673 | 250 | 15 | 235 / 235 | 15 | 7,823 (yes) | 19 (no) |
| country of origin (P495) | 2,968 | 250 | 193 | 57 / 57 | 128 | 1,802 (yes) | 47 (yes) |
| cause of death (P509) | 246 | 246 | 246 | 0 / 0 | 0 | not capped | not capped |
| diplomatic relation (P530) | 3,938 | 250 | 250 | 0 / 0 | 146 | 536 (yes) | 536 (yes) |
| residence (P551) | 20,713 | 250 | 232 | 18 / 18 | 225 | 843 (yes) | 817 (yes) |
| narrative location (P840) | 633 | 250 | 213 | 37 / 37 | 213 | 633 (yes) | 581 (yes) |
| instrument (P1303) | 791 | 250 | 250 | 0 / 0 | 62 | 30 (yes) | 30 (yes) |
| languages spoken, written, or signed (P1412) | 11,336 | 250 | 250 | 0 / 0 | 198 | 115 (yes) | 115 (yes) |
| sibling (P3373) | 125 | 125 | 125 | 0 / 0 | 96 | not capped | not capped |

Boundary group = candidates sharing every criterion before the ID step with the 100th prediction.
Score multisets per relation are unchanged and provenance (supporting rules) of predictions kept in both versions is unchanged:
True / True.

## Caveats

- More body matches is more proof paths, not more independent evidence: matches can share triples, and hubs create many paths.
- No validation or test data was used; whether v2 ranks better is not measured here.
