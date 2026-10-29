# Phase 4B: Rule mining results (training graph only)

These rules are **statistical patterns** in the CoDEx-M training graph. A high
score does not show that a rule is semantically valid. No inferred or predicted
edges were produced; body pairs without a known head are counted, not listed.

Source: `outputs/phase3/codexm_train_ontology.trig` (named graph `urn:codexm:graph:train`,
SHA-256 `e934ee403f5f49ce6bea437c87159cf0ce248686507c726a25e62bef312ee9a2`), 185,584 training triples.
Miner: `phase4_rule_mining.py` 4B.2.0.

## Thresholds

| Setting | Value |
|---|---|
| `min_head_triples` | 20 |
| `min_support` | 5 |
| `min_pca_body` | 20 |
| `min_head_coverage` | 0.01 |
| `min_pca` | 0.05 |
| `min_lift` | 1.5 |
| `top_k_per_head` | 50 |
| `max_body_paths` | 5000000 |
| `wilson_z` | 1.96 |
| `hub_share` | 0.5 |
| `dominance_jaccard` | 0.9 |
| `no_gain_coverage` | 0.9 |
| `n_examples` | 10 |
| `n_counterexamples` | 10 |
| `n_top_middles` | 5 |
| `symmetric_unit` | unordered |

## Counting

`symmetric_unit = unordered`. With `unordered`, rules that read the same after swapping x and z
(symmetry rules `p(z,x) => p(x,z)` and bodies `p(x,y) & p(z,y)` / `p(y,x) & p(y,z)`) are counted per couple {x,z}:
body, support, PCA body and head count are numbers of couples, and confidence, PCA confidence, head coverage,
Wilson bound and the support/PCA-body thresholds use them. All other rules use ordered pairs. Lift and
`unknown_head_pairs_count` always use ordered pairs; each rule also keeps `ordered_counts`.

## Search summary

- Head relations mined: 43 of 51
- Not mined (fewer than 20 triples): P1056 (2), P113 (1), P2283 (9), P3095 (2), P452 (17), P50 (16), P54 (2), P780 (1)
- Body shapes: 10,506 total, 7,296 not joinable, 3,204 evaluated, 6 skipped as too large
- Rule/head combinations below `min_support`: 1,294
- Candidates scored (support ≥ 5): 991
- Passed all thresholds: 212
- Selected: 194 (hub-dominated: 12)

Rejection reasons (a candidate can have several):

- `head_coverage_below_min`: 485
- `lift_below_min`: 435
- `no_gain_over_shorter`: 7
- `pca_below_min`: 393
- `pca_body_below_min`: 75
- `redundant_with`: 11

Selected rules by type:

- composition_chain: 79
- composition_reversed: 89
- inverse: 2
- subrelation: 19
- symmetry: 4
- transitivity: 1

### Skipped body shapes (over `max_body_paths`)

| Body | Paths | Middle entities |
|---|---:|---:|
| `P106(x,y) & P106(z,y)` | 96,828,205 | 371 |
| `P1303(x,y) & P1303(z,y)` | 7,488,760 | 38 |
| `P1412(x,y) & P1412(z,y)` | 23,417,394 | 62 |
| `P27(x,y) & P27(z,y)` | 27,561,563 | 214 |
| `P27(x,y) & P495(z,y)` | 5,239,219 | 47 |
| `P495(x,y) & P27(z,y)` | 5,239,219 | 47 |

## Stability check (90/10 split of training)

- 90% part: 167,005 triples; held-out 10%: 18,579 (0 with an entity absent from the 90% part)
- Rules selected on 90%: 181; on full training: 194; overlap (Jaccard): 0.847291
- Full-train rules flagged unstable: 5 (not scored on the 90% split, or PCA confidence on 90% below half of the full-train value)

## Top 50 selected rules (global rank)

| # | Rule | Type | Supp | PCA body | PCA conf | Std conf | HC | Lift | Wilson | Flags |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | ∀x,y,z: child [P40](y,x) ∧ child [P40](y,z) → sibling [P3373](x,z) | composition_reversed | 127 | 128 | 0.992 | 0.992 | 0.320 | 164.0 | 0.957 |  |
| 2 | ∀x,y,z: spouse [P26](z,x) → spouse [P26](x,z) | symmetry | 335 | 354 | 0.946 | 0.767 | 0.767 | 596.6 | 0.918 |  |
| 3 | ∀x,y,z: child [P40](x,y) ∧ child [P40](z,y) → spouse [P26](x,z) | composition_reversed | 36 | 36 | 1.000 | 0.923 | 0.082 | 555.2 | 0.904 |  |
| 4 | ∀x,y,z: child [P40](x,y) ∧ sibling [P3373](z,y) → child [P40](x,z) | composition_reversed | 109 | 115 | 0.948 | 0.893 | 0.305 | 211.7 | 0.891 |  |
| 5 | ∀x,y,z: sibling [P3373](x,y) ∧ sibling [P3373](z,y) → sibling [P3373](x,z) | composition_reversed | 240 | 259 | 0.927 | 0.927 | 0.605 | 160.6 | 0.888 |  |
| 6 | ∀x,y,z: educated at [P69](x,y) ∧ country [P17](y,z) → country of citizenship [P27](x,z) | composition_chain | 543 | 646 | 0.841 | 0.781 | 0.036 | 132.0 | 0.810 |  |
| 7 | ∀x,y,z: unmarried partner [P451](z,x) → unmarried partner [P451](x,z) | symmetry | 144 | 166 | 0.867 | 0.673 | 0.673 | 213.1 | 0.807 |  |
| 8 | ∀x,y,z: sibling [P3373](z,x) → sibling [P3373](x,z) | symmetry | 310 | 366 | 0.847 | 0.781 | 0.781 | 168.9 | 0.807 |  |
| 9 | ∀x,y,z: place of death [P20](x,y) ∧ official language [P37](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_chain | 643 | 792 | 0.812 | 0.670 | 0.057 | 33.0 | 0.783 |  |
| 10 | ∀x,y,z: diplomatic relation [P530](z,x) → diplomatic relation [P530](x,z) | symmetry | 2,472 | 3,152 | 0.784 | 0.784 | 0.784 | 7.3 | 0.770 |  |
| 11 | ∀x,y,z: location of formation [P740](y,x) ∧ country of origin [P495](y,z) → country [P17](x,z) | composition_reversed | 24 | 26 | 0.923 | 0.800 | 0.020 | 55.7 | 0.759 |  |
| 12 | ∀x,y,z: sibling [P3373](x,y) ∧ ethnic group [P172](y,z) → ethnic group [P172](x,z) | composition_chain | 33 | 37 | 0.892 | 0.355 | 0.016 | 15.7 | 0.753 |  |
| 13 | ∀x,y,z: place of birth [P19](x,y) ∧ official language [P37](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_chain | 517 | 675 | 0.766 | 0.568 | 0.046 | 28.0 | 0.733 |  |
| 14 | ∀x,y,z: sibling [P3373](y,x) ∧ languages spoken, written, or signed [P1412](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_reversed | 206 | 264 | 0.780 | 0.567 | 0.018 | 27.9 | 0.727 |  |
| 15 | ∀x,y,z: director [P57](x,y) ∧ country of citizenship [P27](y,z) → country of origin [P495](x,z) | composition_chain | 330 | 434 | 0.760 | 0.704 | 0.179 | 22.4 | 0.718 |  |
| 16 | ∀x,y,z: sibling [P3373](x,y) ∧ languages spoken, written, or signed [P1412](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_chain | 205 | 266 | 0.771 | 0.568 | 0.018 | 27.9 | 0.717 |  |
| 17 | ∀x,y,z: headquarters location [P159](y,x) ∧ country [P17](y,z) → country [P17](x,z) | composition_reversed | 45 | 54 | 0.833 | 0.682 | 0.038 | 47.5 | 0.713 |  |
| 18 | ∀x,y,z: location of formation [P740](y,x) ∧ country of citizenship [P27](y,z) → country [P17](x,z) | composition_reversed | 19 | 21 | 0.905 | 0.576 | 0.016 | 40.1 | 0.711 |  |
| 19 | ∀x,y,z: sibling [P3373](y,x) ∧ country of citizenship [P27](y,z) → country of citizenship [P27](x,z) | composition_reversed | 316 | 436 | 0.725 | 0.661 | 0.021 | 111.7 | 0.681 |  |
| 20 | ∀x,y,z: spouse [P26](x,y) ∧ child [P40](y,z) → child [P40](x,z) | composition_chain | 89 | 117 | 0.761 | 0.761 | 0.249 | 180.3 | 0.676 |  |
| 21 | ∀x,y,z: located in the administrative terroritorial entity [P131](y,x) ∧ continent [P30](y,z) → continent [P30](x,z) | composition_reversed | 26 | 31 | 0.839 | 0.703 | 0.072 | 4.5 | 0.674 |  |
| 22 | ∀x,y,z: sibling [P3373](x,y) ∧ country of citizenship [P27](y,z) → country of citizenship [P27](x,z) | composition_chain | 316 | 443 | 0.713 | 0.654 | 0.021 | 110.5 | 0.670 |  |
| 23 | ∀x,y,z: sibling [P3373](y,x) ∧ member of political party [P102](y,z) → member of political party [P102](x,z) | composition_reversed | 37 | 46 | 0.804 | 0.416 | 0.015 | 20.6 | 0.668 |  |
| 24 | ∀x,y,z: sibling [P3373](x,y) ∧ member of political party [P102](y,z) → member of political party [P102](x,z) | composition_chain | 37 | 46 | 0.804 | 0.425 | 0.015 | 21.1 | 0.668 |  |
| 25 | ∀x,y,z: spouse [P26](y,x) ∧ languages spoken, written, or signed [P1412](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_reversed | 344 | 485 | 0.709 | 0.526 | 0.030 | 25.9 | 0.667 |  |
| 26 | ∀x,y,z: founded by [P112](x,y) ∧ country of citizenship [P27](y,z) → country [P17](x,z) | composition_chain | 28 | 34 | 0.824 | 0.651 | 0.024 | 45.3 | 0.665 |  |
| 27 | ∀x,y,z: sibling [P3373](x,y) ∧ place of birth [P19](y,z) → place of birth [P19](x,z) | composition_chain | 136 | 186 | 0.731 | 0.562 | 0.021 | 244.2 | 0.663 |  |
| 28 | ∀x,y,z: sibling [P3373](y,x) ∧ place of birth [P19](y,z) → place of birth [P19](x,z) | composition_reversed | 136 | 186 | 0.731 | 0.560 | 0.021 | 243.1 | 0.663 |  |
| 29 | ∀x,y,z: spouse [P26](y,x) ∧ child [P40](y,z) → child [P40](x,z) | composition_reversed | 89 | 119 | 0.748 | 0.748 | 0.249 | 177.2 | 0.663 |  |
| 30 | ∀x,y,z: spouse [P26](x,y) ∧ languages spoken, written, or signed [P1412](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_chain | 341 | 489 | 0.697 | 0.527 | 0.030 | 25.9 | 0.655 |  |
| 31 | ∀x,y,z: headquarters location [P159](x,z) → located in the administrative terroritorial entity [P131](x,z) | subrelation | 24 | 29 | 0.828 | 0.154 | 0.130 | 14.1 | 0.655 |  |
| 32 | ∀x,y,z: child [P40](x,y) ∧ languages spoken, written, or signed [P1412](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_chain | 153 | 215 | 0.712 | 0.558 | 0.013 | 27.5 | 0.648 |  |
| 33 | ∀x,y,z: unmarried partner [P451](y,x) ∧ languages spoken, written, or signed [P1412](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_reversed | 165 | 233 | 0.708 | 0.545 | 0.015 | 26.8 | 0.647 |  |
| 34 | ∀x,y,z: country of citizenship [P27](x,y) ∧ official language [P37](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_chain | 7,887 | 12,084 | 0.653 | 0.459 | 0.695 | 22.6 | 0.644 |  |
| 35 | ∀x,y,z: child [P40](x,y) ∧ country of citizenship [P27](y,z) → country of citizenship [P27](x,z) | composition_chain | 227 | 329 | 0.690 | 0.634 | 0.015 | 107.1 | 0.638 |  |
| 36 | ∀x,y,z: unmarried partner [P451](x,y) ∧ languages spoken, written, or signed [P1412](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_chain | 158 | 228 | 0.693 | 0.536 | 0.014 | 26.4 | 0.630 |  |
| 37 | ∀x,y,z: located in the administrative terroritorial entity [P131](x,z) → headquarters location [P159](x,z) | subrelation | 24 | 30 | 0.800 | 0.130 | 0.154 | 7.6 | 0.627 |  |
| 38 | ∀x,y,z: child [P40](y,x) ∧ languages spoken, written, or signed [P1412](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_reversed | 151 | 219 | 0.689 | 0.517 | 0.013 | 25.4 | 0.625 |  |
| 39 | ∀x,y,z: spouse [P26](x,y) ∧ country of citizenship [P27](y,z) → country of citizenship [P27](x,z) | composition_chain | 522 | 803 | 0.650 | 0.610 | 0.034 | 103.0 | 0.616 |  |
| 40 | ∀x,y,z: spouse [P26](y,x) ∧ country of citizenship [P27](y,z) → country of citizenship [P27](x,z) | composition_reversed | 526 | 815 | 0.645 | 0.598 | 0.035 | 101.0 | 0.612 |  |
| 41 | ∀x,y,z: child [P40](y,x) ∧ country of citizenship [P27](y,z) → country of citizenship [P27](x,z) | composition_reversed | 240 | 367 | 0.654 | 0.615 | 0.016 | 104.0 | 0.604 |  |
| 42 | ∀x,y,z: record label [P264](x,y) ∧ country [P17](y,z) → country of citizenship [P27](x,z) | composition_chain | 1,077 | 1,790 | 0.602 | 0.516 | 0.071 | 87.1 | 0.579 |  |
| 43 | ∀x,y,z: country [P17](y,x) ∧ continent [P30](y,z) → continent [P30](x,z) | composition_reversed | 72 | 109 | 0.661 | 0.581 | 0.201 | 3.7 | 0.568 |  |
| 44 | ∀x,y,z: child [P40](x,y) ∧ member of political party [P102](y,z) → member of political party [P102](x,z) | composition_chain | 35 | 50 | 0.700 | 0.479 | 0.015 | 23.8 | 0.562 |  |
| 45 | ∀x,y,z: parent organization [P749](x,y) ∧ country [P17](y,z) → country [P17](x,z) | composition_chain | 36 | 52 | 0.692 | 0.621 | 0.031 | 43.2 | 0.557 | hub Q38903 |
| 46 | ∀x,y,z: unmarried partner [P451](y,x) ∧ country of citizenship [P27](y,z) → country of citizenship [P27](x,z) | composition_reversed | 202 | 339 | 0.596 | 0.530 | 0.013 | 89.6 | 0.543 |  |
| 47 | ∀x,y,z: spouse [P26](y,x) ∧ member of political party [P102](y,z) → member of political party [P102](x,z) | composition_reversed | 65 | 102 | 0.637 | 0.376 | 0.027 | 18.6 | 0.541 |  |
| 48 | ∀x,y,z: residence [P551](x,y) ∧ official language [P37](y,z) → languages spoken, written, or signed [P1412](x,z) | composition_chain | 164 | 275 | 0.596 | 0.490 | 0.014 | 24.1 | 0.537 |  |
| 49 | ∀x,y,z: located in the administrative terroritorial entity [P131](x,y) ∧ continent [P30](y,z) → continent [P30](x,z) | composition_chain | 28 | 41 | 0.683 | 0.289 | 0.078 | 1.8 | 0.530 |  |
| 50 | ∀x,y,z: unmarried partner [P451](x,y) ∧ country of citizenship [P27](y,z) → country of citizenship [P27](x,z) | composition_chain | 197 | 340 | 0.579 | 0.527 | 0.013 | 89.0 | 0.526 |  |

## Example evidence for the top 10 rules

**1. `P40(y,x) & P40(y,z) => P3373(x,z)`**
- supports: Tony Curtis —P40→ Jamie Lee Curtis; Tony Curtis —P40→ Kelly Curtis ⇒ Jamie Lee Curtis —P3373→ Kelly Curtis
- supports: Eddie Fisher —P40→ Carrie Fisher; Eddie Fisher —P40→ Joely Fisher ⇒ Carrie Fisher —P3373→ Joely Fisher
- counterexample: body holds, but `Q234388 P3373 Q131324` is absent while Q234388 has another P3373 value

**2. `P26(z,x) => P26(x,z)`**
- supports: William Godwin —P26→ Mary Wollstonecraft ⇒ Mary Wollstonecraft —P26→ William Godwin
- supports: Henrik, Prince Consort of Denmark —P26→ Margrethe II of Denmark ⇒ Margrethe II of Denmark —P26→ Henrik, Prince Consort of Denmark
- counterexample: body holds, but `Q129087 P26 Q102551` is absent while Q129087 has another P26 value

**3. `P40(x,y) & P40(z,y) => P26(x,z)`**
- supports: Mary Wollstonecraft —P40→ Mary Shelley; William Godwin —P40→ Mary Shelley ⇒ Mary Wollstonecraft —P26→ William Godwin
- supports: Bill Clinton —P40→ Chelsea Clinton; Hillary Clinton —P40→ Chelsea Clinton ⇒ Bill Clinton —P26→ Hillary Clinton

**4. `P40(x,y) & P3373(z,y) => P40(x,z)`**
- supports: John Lennon —P40→ Julian Lennon; Sean Lennon —P3373→ Julian Lennon ⇒ John Lennon —P40→ Sean Lennon
- supports: John Lennon —P40→ Sean Lennon; Julian Lennon —P3373→ Sean Lennon ⇒ John Lennon —P40→ Julian Lennon
- counterexample: body holds, but `Q262507 P40 Q108941` is absent while Q262507 has another P40 value

**5. `P3373(x,y) & P3373(z,y) => P3373(x,z)`**
- supports: Macaulay Culkin —P3373→ Rory Culkin; Kieran Culkin —P3373→ Rory Culkin ⇒ Macaulay Culkin —P3373→ Kieran Culkin
- supports: Macaulay Culkin —P3373→ Kieran Culkin; Rory Culkin —P3373→ Kieran Culkin ⇒ Macaulay Culkin —P3373→ Rory Culkin
- counterexample: body holds, but `Q78704 P3373 Q105273` is absent while Q78704 has another P3373 value

**6. `P69(x,y) & P17(y,z) => P27(x,z)`**
- supports: Wanda Gág —P69→ Art Students League of New York; Art Students League of New York —P17→ United States of America ⇒ Wanda Gág —P27→ United States of America
- supports: Sigourney Weaver —P69→ Yale School of Drama; Yale School of Drama —P17→ United States of America ⇒ Sigourney Weaver —P27→ United States of America
- counterexample: body holds, but `Q103784 P27 Q145` is absent while Q103784 has another P27 value

**7. `P451(z,x) => P451(x,z)`**
- supports: Ryan O'Neal —P451→ Farrah Fawcett ⇒ Farrah Fawcett —P451→ Ryan O'Neal
- supports: Marlene Dietrich —P451→ Yul Brynner ⇒ Yul Brynner —P451→ Marlene Dietrich
- counterexample: body holds, but `Q36767 P451 Q126599` is absent while Q36767 has another P451 value

**8. `P3373(z,x) => P3373(x,z)`**
- supports: Kieran Culkin —P3373→ Macaulay Culkin ⇒ Macaulay Culkin —P3373→ Kieran Culkin
- supports: Rory Culkin —P3373→ Macaulay Culkin ⇒ Macaulay Culkin —P3373→ Rory Culkin
- counterexample: body holds, but `Q78704 P3373 Q105273` is absent while Q78704 has another P3373 value

**9. `P20(x,y) & P37(y,z) => P1412(x,z)`**
- supports: Luciano De Crescenzo —P20→ Rome; Rome —P37→ Italian ⇒ Luciano De Crescenzo —P1412→ Italian
- supports: Suetonius —P20→ Roman Empire; Roman Empire —P37→ Latin ⇒ Suetonius —P1412→ Latin
- counterexample: body holds, but `Q10133 P1412 Q35497` is absent while Q10133 has another P1412 value

**10. `P530(z,x) => P530(x,z)`**
- supports: France —P530→ Gabon ⇒ Gabon —P530→ France
- supports: Germany —P530→ Gabon ⇒ Gabon —P530→ Germany
- counterexample: body holds, but `Q148 P530 Q1000` is absent while Q148 has another P530 value

## Limitations

- Statistical co-occurrence only; no entity types, so rules can fire on unsuitable entities.
- Open world: missing triples are unknown. PCA is a heuristic and is weak for many-valued heads such as P106.
- Hubs (for example Q30) can make patterns look strong; see `top_middle_entities` and the hub flag.
- Two-atom bodies only, no constants; skipped shapes are listed above.
- Validation scoring is a separate step (`phase4_rule_evaluation.py`); test files are not used in Phase 4.

Full data: `selected_rules.json`, `rule_candidates.jsonl`, `stability_check.json`, `mining_manifest.json`.
