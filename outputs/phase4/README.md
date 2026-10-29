# Phase 4 rule mining outputs

From the project root, run:

```powershell
py phase4_rule_mining.py          # mines into outputs/phase4/run_default/
py phase4_rule_evaluation.py      # scores the frozen rules on validation
```

Use `--run-name <new folder>` for another run; existing runs are never
overwritten. Every threshold is a flag (for example `--max-body-paths`, `--min-pca`).
Only the Python standard library is needed.

- `phase4_rule_mining_design.md`: approved Phase 4A design.
- `run_default/rule_candidates.jsonl`: every candidate with support >= 10, with
  status and rejection reasons.
- `run_default/selected_rules.json`: the frozen rule set with scores and evidence
  (supporting examples, PCA counterexamples, top middle entities, flags).
- `run_default/rules_report.md`: readable summary, skipped body shapes, top rules.
- `run_default/stability_check.json`: 90/10 training split check; the held-out 10%
  is never used for mining.
- `run_default/mining_manifest.json`: settings, input/output hashes, counts,
  protected-file state.
- `run_default/validation_evaluation.json` / `.md`, `validated_rule_set.json`:
  validation-only scoring and threshold choice.

The miner reads only the Phase 3 training named graph and never opens
validation or test files. The evaluator opens only `valid.txt` and
`valid_negatives.txt`, never the test files. Rules are statistical patterns,
not semantic claims, and no predicted edges are written. Tests:
`py -m pytest tests/test_phase4_rule_mining.py tests/test_phase4_rule_evaluation.py`
(or `py -m unittest`).

## Grid extension (4B.2.0)

- `run_grid_ext/`: new run (`--min-support 5 --min-pca 0.05`, couple counting for
  swap-invariant rules), scored on a 24-point validation grid.
- `py phase4_compare_runs.py`: read-only comparison of `run_default` and `run_grid_ext`
  with the fixed adoption rule; writes `phase4_grid_ext_report.md`,
  `phase4_grid_ext_comparison.json` and `phase5_candidate_rules_proposed.json`.
- Short summary: `phase4_grid_ext_summary.md`. `run_default/` is kept unchanged as the baseline.
