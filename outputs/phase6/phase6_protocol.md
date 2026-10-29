# Phase 6 evaluation protocol (for approval — NOT yet executed)

**Status:** not run. The runner `phase6_evaluate.py` reads no split file unless it is called with
`--i-approve-phase6-test-evaluation`. The prediction UI only displays results that already exist.

## 1. What is evaluated

| Item | Source (unchanged) |
|---|---|
| v1 predictions | `outputs/phase5/predictions.json` — 3,239 triples, top 100 per relation |
| v2 predictions | `outputs/phase5/ranking_v2/predictions.json` — 3,239 triples, same candidates and scores, evidence tie-break |
| Held-out positives | `data/test.txt` — 10,311 triples (counts from the Phase 1 report) |
| Supplied negatives | `data/test_negatives.txt` — 10,311 triples |
| Annotation only | `data/valid.txt`, `data/valid_negatives.txt` (not used for any metric or choice) |

No rules are mined, no thresholds or rankings are changed, and no prediction is added or removed.

## 2. Leakage review

- **Predictions use training data only.**
  - Rules were mined from the Phase 3 training named graph.
  - Predictions were generated from the Phase 2 training graph.
  - Phase 4 and Phase 5 tests record every file opened and confirm the miners and predictors never open validation or test files.
- **Validation is not clean held-out data.** It was used in Phase 4 to score the rule set, review the threshold grid, choose the six excluded rules and compare methods. Validation is therefore not used as the evaluation split. It only annotates unlabelled predictions.
- **Test-file access history.** Test content was read, but never for mining, thresholds, rankings or predictions:
  - Phase 1 inspected the test files (row counts and overlap checks).
  - Phase 3 hashed them.
  - The existing test `tests/test_display_labels.py::test_mapping_covers_identifiers_in_all_local_triple_files` reads every `data/*.txt` (including the test files) to check label coverage whenever that suite runs.
  - During this UI task, one shell command opened `data/test.txt` and discarded its first 600 bytes without displaying them (`head -c 600 … > /dev/null`). This was an error; nothing was seen or used.
  - The UI build and the UI tests do not open validation or test files.
- **Runner safeguards:**
  - It checks that the SHA-256 of each split file equals the hash in `outputs/phase3/phase3_manifest.json`.
  - It checks that no split triple is in the training graph.
  - It checks that test positives and supplied negatives do not overlap.

## 3. Labels (no closed-world assumption)

Each prediction gets exactly one label:

- `test_positive`: the triple is in `data/test.txt`.
- `test_negative`: the triple is in `data/test_negatives.txt` (supplied negative).
- `unlabelled`: in neither file. **Not treated as false.** It is annotated, for information only, if it
  appears in the validation positives or validation negatives.

## 4. Metrics and denominators

The benchmark universe is U = test positives ∪ supplied test negatives (about 20,622 triples). The
prediction universe (3,239 top-ranked rule candidates) is different. Most predictions are expected to fall
outside U, so metrics are split into two families.

**Over U (benchmark-side):**

| Metric | Definition |
|---|---|
| TP | predictions that are test positives |
| FP | predictions that are supplied negatives |
| FN | test positives not predicted |
| TN | supplied negatives not predicted |
| Precision | TP / (TP + FP) — labelled predictions only |
| Recall | TP / all test positives |
| F1 | harmonic mean of the precision and recall above |
| Specificity | TN / all supplied negatives |

**Prediction-side:**

| Metric | Definition |
|---|---|
| Labelled coverage | (TP + FP) / all predictions |
| Positive hit rate | TP / all predictions — a lower bound, because unlabelled predictions may be true |
| Recall ceiling under the cap | Σ_r min(predictions_r, test positives_r) / all test positives |

All metrics are also reported per relation, and for v1 and v2 under identical conditions.

**Not reported:**

- Precision over all predictions (it would need unlabelled = false).
- Ranking metrics such as MRR or Hits@k. The predictions are capped lists per relation, not answers to per-query rankings.

## 5. Known limitations

- **Small overlap expected.** The candidate universe was never built to cover U. Expect many unlabelled
  predictions, low labelled coverage and low recall. Recall is also capped at 100 predictions per relation.
- **Supplied negatives.** They were only checked structurally (Phase 1). Their semantic correctness and
  their construction method were not verified, so FP counts only collisions with this particular set.
- **Incomplete KG.** An unlabelled prediction may be true or false. A test positive that is not predicted may be
  missing because of the cap, a missing rule or an unseen pattern.
- **v1 vs v2.** They differ only in tie-breaks inside equal-score groups. Differences in metrics may be small,
  and should not be over-interpreted without per-relation counts.

## 6. Command (only after approval)

```powershell
py phase6_evaluate.py --i-approve-phase6-test-evaluation
```

Outputs go to `outputs/phase6/evaluation_test/` and are never overwritten:

- `evaluation_results.json` and `.js`
- `predictions_labelled.csv`
- `per_relation_metrics.csv`
- `evaluation_manifest.json`

Reload `outputs/prediction_ui/index.html` (Phase 6 tab) to view them.
