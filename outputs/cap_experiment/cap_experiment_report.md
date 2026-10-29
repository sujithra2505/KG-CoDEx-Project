# Cap experiment — validation comparison and selection

Generated 2026-10-29T06:57:32+00:00 by `cap_experiment.py` from the files listed in `validation/validation_manifest.json`.

**Split: validation.** Validation was already used in Phase 4, so these numbers are optimistic. Benchmark precision covers only predictions found in the validation positives or validation negatives; unlabelled predictions are not counted as false.

## Selection rule (frozen before validation)

- Rule `A1`, frozen at 2026-10-29T06:55:34+00:00 (sha256 `332b040ddeb0…`).
- Objective: maximise validation recall = TP / |validation positives| (equivalently TP: same denominator for every configuration).
- Constraint: Wilson 95% lower bound of validation benchmark precision TP/(TP+FP) >= the same bound for the cap-100 configuration of the same ranking version, minus 0.05.
- Ties: smaller cap, then v2 before v1.

## Validation results

| Config | Predictions | Val. positives matched (TP) | Val. negatives matched (FP) | Unlabelled | Precision | Precision 95% lower | Recall | F1 | Positive hit rate | Eligible |
|---|---|---|---|---|---|---|---|---|---|---|
| cap100_v1 | 3,239 | 246 | 12 | 2,981 | 95.35% | 92.05% | 2.39% | 4.66% | 7.59% | yes |
| cap100_v2 | 3,239 | 253 | 11 | 2,975 | 95.83% | 92.69% | 2.45% | 4.79% | 7.81% | yes |
| cap250_v1 | 7,464 | 428 | 21 | 7,015 | 95.32% | 92.96% | 4.15% | 7.96% | 5.73% | yes |
| cap250_v2 | 7,464 | 477 | 19 | 6,968 | 96.17% | 94.09% | 4.63% | 8.83% | 6.39% | yes |
| cap500_v1 | 13,571 | 600 | 40 | 12,931 | 93.75% | 91.60% | 5.82% | 10.96% | 4.42% | yes |
| cap500_v2 | 13,571 | 653 | 38 | 12,880 | 94.50% | 92.54% | 6.33% | 11.87% | 4.81% | yes |
| cap1000_v1 | 23,772 | 816 | 62 | 22,894 | 92.94% | 91.05% | 7.91% | 14.59% | 3.43% | yes |
| cap1000_v2 | 23,772 | 875 | 62 | 22,835 | 93.38% | 91.61% | 8.49% | 15.56% | 3.68% | yes |

**Selected: `cap1000_v2`** (cap 1000, v2).

## Test evaluation

- Previous test evaluation (cap 100, v1 and v2): `outputs/phase6/evaluation_test/` (Phase 6, unchanged).
- Final test evaluation of the selected configuration: gated — `py cap_experiment.py test --i-approve-cap-test-evaluation`. It is a second use of the test split and must not lead to further changes.

## Notes

- `prediction_report.md` files for caps 250/500/1000 come from the unchanged Phase 5 renderer; its fixed sentence "the cap keeps only the top 100 per relation" refers to the baseline — the actual cap is in each manifest's settings.
- Recall is bounded by each cap and by relations without rules; precision is only over labelled predictions.
