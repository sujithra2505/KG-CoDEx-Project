# Phase 6 results — held-out test split

Source: `outputs/phase6/evaluation_test/evaluation_results.json` (evaluator v6.0.1). Predictions are the frozen Phase 5 files; nothing was re-ranked, re-thresholded or re-generated.

**Read this first.** Benchmark precision is measured only on predictions that appear in the supplied test positives or supplied test negatives. It is *not* accuracy over all predicted triples, and not accuracy over all unknown KG triples. Unlabelled predictions are neither true nor false here.

## 1. Overall metrics

| Metric | Formula | v1 | v2 | Better |
|---|---|---|---|---|
| benchmark precision | TP/(TP+FP) | 257/270 = 95.19% | 278/291 = 95.53% | v2 |
| benchmark recall | TP/\|test positives\| | 257/10,311 = 2.49% | 278/10,311 = 2.70% | v2 |
| benchmark F1 | 2TP/(2TP+FP+FN) | 514/10,581 = 4.86% | 556/10,602 = 5.24% | v2 |
| specificity | TN/\|supplied negatives\| | 10,298/10,311 = 99.87% | 10,298/10,311 = 99.87% | tie |
| labelled coverage | (TP+FP)/\|predictions\| | 270/3,239 = 8.34% | 291/3,239 = 8.98% | v2 |
| positive hit rate (lower bound) | TP/\|predictions\| | 257/3,239 = 7.93% | 278/3,239 = 8.58% | v2 |
| recall ceiling under cap | Σ min(pred_r, pos_r)/\|test positives\| | 2,468/10,311 = 23.94% | 2,468/10,311 = 23.94% | tie |

Wilson 95% interval for benchmark precision: v1 91.94%–97.16%, v2 92.51%–97.37%. The intervals overlap almost fully.

## 2. Prediction labels

| Label | v1 | v2 |
|---|---|---|
| Matches held-out test positive | 257 | 278 |
| Matches supplied test negative | 13 | 13 |
| Unlabelled (not in test files) | 2,969 | 2,948 |
| — of which in validation positives (info only) | 246 | 253 |
| — of which in validation negatives (info only) | 12 | 11 |
| — in no split file | 2,711 | 2,684 |
| Total | 3,239 | 3,239 |

v1 and v2 share 2,830 predictions; each has 409 the other lacks. v1-only: {'test_positive': 14, 'test_negative': 1, 'unlabelled': 394}. v2-only: {'test_positive': 35, 'test_negative': 1, 'unlabelled': 373}.

## 3. Coverage and the 100-per-relation cap

- 44 relations appear in predictions or the test files; 33 have predictions.
- No predictions for 11 relations (P50, P57, P112, P138, P407, P641, P737, P740, P749, P1050, P2348); they hold 162 test positives, all counted as FN in recall.
- 32 relations hit the 100 cap. 7,681 test positives lie beyond the cap in their relation.
- Best possible TP under the cap = 2,468 of 10,311 → recall ceiling 23.94% for both versions.
- Top TP relations — v1: {'P26': 48, 'P530': 38, 'P3373': 31, 'P495': 24}; v2: {'P26': 48, 'P530': 38, 'P3373': 31, 'P495': 24}.

## 4. Per-relation results

| Relation | Pos | Neg | Preds | Status | v1 TP/FP/Unl | v1 P | v1 R | v2 TP/FP/Unl | v2 P | v2 R | ΔTP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| country [P17] | 79 | 168 | 100 | capped (100) | 7/0/93 | 1.0000 | 0.0886 | 7/0/93 | 1.0000 | 0.0886 | +0 |
| place of birth [P19] | 339 | 940 | 100 | capped (100) | 7/0/93 | 1.0000 | 0.0206 | 7/0/93 | 1.0000 | 0.0206 | +0 |
| place of death [P20] | 260 | 717 | 100 | capped (100) | 1/0/99 | 1.0000 | 0.0038 | 1/0/99 | 1.0000 | 0.0038 | +0 |
| spouse [P26] | 53 | 259 | 100 | capped (100) | 48/0/52 | 1.0000 | 0.9057 | 48/0/52 | 1.0000 | 0.9057 | +0 |
| country of citizenship [P27] | 829 | 2884 | 100 | capped (100) | 18/0/82 | 1.0000 | 0.0217 | 18/0/82 | 1.0000 | 0.0217 | +0 |
| continent [P30] | 18 | 114 | 100 | capped (100) | 5/4/91 | 0.5556 | 0.2778 | 5/4/91 | 0.5556 | 0.2778 | +0 |
| official language [P37] | 13 | 129 | 100 | capped (100) | 1/3/96 | 0.2500 | 0.0769 | 1/3/96 | 0.2500 | 0.0769 | +0 |
| child [P40] | 15 | 55 | 39 | below cap | 3/0/36 | 1.0000 | 0.2000 | 3/0/36 | 1.0000 | 0.2000 | +0 |
| author [P50] | 0 | 2 | 0 | no predictions | 0/0/0 | — | — | 0/0/0 | — | — | +0 |
| director [P57] | 31 | 101 | 0 | no predictions | 0/0/0 | — | 0.0000 | 0/0/0 | — | 0.0000 | +0 |
| educated at [P69] | 498 | 369 | 100 | capped (100) | 3/0/97 | 1.0000 | 0.0060 | 3/0/97 | 1.0000 | 0.0060 | +0 |
| field of work [P101] | 126 | 98 | 100 | capped (100) | 2/0/98 | 1.0000 | 0.0159 | 3/0/97 | 1.0000 | 0.0238 | +1 |
| member of political party [P102] | 133 | 115 | 100 | capped (100) | 7/0/93 | 1.0000 | 0.0526 | 6/0/94 | 1.0000 | 0.0451 | -1 |
| occupation [P106] | 3635 | 532 | 100 | capped (100) | 14/1/85 | 0.9333 | 0.0039 | 15/1/84 | 0.9375 | 0.0041 | +1 |
| employer [P108] | 259 | 106 | 100 | capped (100) | 0/0/100 | — | 0.0000 | 0/0/100 | — | 0.0000 | +0 |
| founded by [P112] | 3 | 27 | 0 | no predictions | 0/0/0 | — | 0.0000 | 0/0/0 | — | 0.0000 | +0 |
| place of burial [P119] | 91 | 26 | 100 | capped (100) | 3/0/97 | 1.0000 | 0.0330 | 3/0/97 | 1.0000 | 0.0330 | +0 |
| located in the administrative terroritorial entity [P131] | 12 | 9 | 100 | capped (100) | 0/0/100 | — | 0.0000 | 0/0/100 | — | 0.0000 | +0 |
| movement [P135] | 19 | 15 | 100 | capped (100) | 0/0/100 | — | 0.0000 | 0/0/100 | — | 0.0000 | +0 |
| genre [P136] | 591 | 788 | 100 | capped (100) | 1/2/97 | 0.3333 | 0.0017 | 1/2/97 | 0.3333 | 0.0017 | +0 |
| named after [P138] | 2 | 10 | 0 | no predictions | 0/0/0 | — | 0.0000 | 0/0/0 | — | 0.0000 | +0 |
| religion [P140] | 120 | 84 | 100 | capped (100) | 2/0/98 | 1.0000 | 0.0167 | 2/0/98 | 1.0000 | 0.0167 | +0 |
| headquarters location [P159] | 8 | 3 | 100 | capped (100) | 0/0/100 | — | 0.0000 | 0/0/100 | — | 0.0000 | +0 |
| cast member [P161] | 448 | 389 | 100 | capped (100) | 2/1/97 | 0.6667 | 0.0045 | 2/1/97 | 0.6667 | 0.0045 | +0 |
| ethnic group [P172] | 132 | 135 | 100 | capped (100) | 3/0/97 | 1.0000 | 0.0227 | 3/0/97 | 1.0000 | 0.0227 | +0 |
| record label [P264] | 169 | 291 | 100 | capped (100) | 3/0/97 | 1.0000 | 0.0178 | 3/0/97 | 1.0000 | 0.0178 | +0 |
| part of [P361] | 12 | 15 | 100 | capped (100) | 0/1/99 | 0.0000 | 0.0000 | 3/1/96 | 0.7500 | 0.2500 | +3 |
| language of work or name [P407] | 1 | 2 | 0 | no predictions | 0/0/0 | — | 0.0000 | 0/0/0 | — | 0.0000 | +0 |
| unmarried partner [P451] | 20 | 69 | 100 | capped (100) | 11/0/89 | 1.0000 | 0.5500 | 11/0/89 | 1.0000 | 0.5500 | +0 |
| member of [P463] | 583 | 164 | 100 | capped (100) | 3/0/97 | 1.0000 | 0.0051 | 17/0/83 | 1.0000 | 0.0292 | +14 |
| country of origin [P495] | 115 | 177 | 100 | capped (100) | 24/1/75 | 0.9600 | 0.2087 | 24/1/75 | 0.9600 | 0.2087 | +0 |
| cause of death [P509] | 148 | 180 | 100 | capped (100) | 1/0/99 | 1.0000 | 0.0068 | 1/0/99 | 1.0000 | 0.0068 | +0 |
| diplomatic relation [P530] | 297 | 6 | 100 | capped (100) | 38/0/62 | 1.0000 | 0.1279 | 38/0/62 | 1.0000 | 0.1279 | +0 |
| residence [P551] | 104 | 65 | 100 | capped (100) | 0/0/100 | — | 0.0000 | 0/0/100 | — | 0.0000 | +0 |
| sport [P641] | 11 | 28 | 0 | no predictions | 0/0/0 | — | 0.0000 | 0/0/0 | — | 0.0000 | +0 |
| influenced by [P737] | 71 | 154 | 0 | no predictions | 0/0/0 | — | 0.0000 | 0/0/0 | — | 0.0000 | +0 |
| location of formation [P740] | 8 | 6 | 0 | no predictions | 0/0/0 | — | 0.0000 | 0/0/0 | — | 0.0000 | +0 |
| parent organization [P749] | 1 | 23 | 0 | no predictions | 0/0/0 | — | 0.0000 | 0/0/0 | — | 0.0000 | +0 |
| narrative location [P840] | 85 | 27 | 100 | capped (100) | 0/0/100 | — | 0.0000 | 0/0/100 | — | 0.0000 | +0 |
| medical condition [P1050] | 20 | 12 | 0 | no predictions | 0/0/0 | — | 0.0000 | 0/0/0 | — | 0.0000 | +0 |
| instrument [P1303] | 297 | 41 | 100 | capped (100) | 1/0/99 | 1.0000 | 0.0034 | 1/0/99 | 1.0000 | 0.0034 | +0 |
| languages spoken, written, or signed [P1412] | 598 | 862 | 100 | capped (100) | 18/0/82 | 1.0000 | 0.0301 | 21/0/79 | 1.0000 | 0.0351 | +3 |
| time period [P2348] | 14 | 0 | 0 | no predictions | 0/0/0 | — | 0.0000 | 0/0/0 | — | 0.0000 | +0 |
| sibling [P3373] | 43 | 114 | 100 | capped (100) | 31/0/69 | 1.0000 | 0.7209 | 31/0/69 | 1.0000 | 0.7209 | +0 |

P = — means no prediction matched either test file (precision undefined, not zero).

## 5. Interpretation and limitations

- **v1 vs v2.** v2 is equal or higher on every metric, but the gap is 21 TP (257 → 278) with the same 13 FP. Precision differs by 0.35 points inside overlapping 95% intervals: not a meaningful precision difference. The gain is concentrated in P463 (+14), P1412 (+3), P361 (+3), P101/P106 (+1 each); P102 loses 1.
- **Precision is benchmark-specific.** It is computed on 270 (v1) / 291 (v2) of 3,239 predictions (8–9%). The other ~91% are unlabelled: they may be true facts missing from the benchmark or wrong. The positive hit rate (7.9% / 8.6%) is only a lower bound on the share of correct predictions.
- **Concentration.** Four symmetric/structural relations (P26, P530, P3373, P495) give 141 of the TP in both versions, so overall precision mostly reflects those relations.
- **Low-precision relations.** P37 (1 TP / 3 neg.), P136 (1/2), P30 (5/4), P161 (2/1) and P361 in v1 (0/1) collide with supplied negatives; all are tiny counts.
- **Recall is structurally capped.** The 100-per-relation cap and 11 relations with no rules bound recall at 23.94%; observed recall 2.5–2.7% is about 11% of that ceiling. P106 alone has 3,635 positives vs 100 predictions.
- **Supplied negatives** were only checked structurally; FP counts collisions with this particular negative set.
- **Validation annotation** (246 / 253 unlabelled predictions in valid.txt) is information only and was not used to change anything; validation is not clean held-out data (used in Phase 4).
- **Single run, no tuning.** Test results were not used to choose thresholds, rules, rankings or a model.

## 6. Charts

- `fig1_label_composition.png`
- `fig2_overall_metrics.png`
- `fig3_per_relation_tp.png`
