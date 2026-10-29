# Prediction UI and Phase 6 evaluation UI — implementation report

**Date:** 2026-10-29. Phase 6 evaluation was **not** run.

## Inspected before coding

- **Phase 2:** the viewer (pyvis HTML with vis-network 9.1.2 embedded) and `training_graph.graphml`.
  `phase2_graph.py` needs networkx/pyvis, which are not installed on this computer's Linux shell.
- **Phase 4:** the frozen 160-rule list and its source run.
- **Phase 5:** the v1 and v2 `predictions.json` files (schema: triple, labels, ranking_score,
  tie_break_values, supporting_rules with body_groundings, relation_rank, round) and their manifests.
  The v2 manifest confirms 2,830 kept, 409 dropped, 409 added and 1,499 rank changes.
- **Data:** split definitions and the Phase 1 report.

## Files created (nothing existing was changed)

| File | Purpose |
|---|---|
| `phase5_ui_build.py` | Builds the static UI from the existing v1/v2 files (stdlib only; refuses overwrite; hash checks) |
| `prediction_ui_src/index.html`, `app.js`, `app.css`, `filters.js`, `README.md` | UI sources (`filters.js` = pure filter/sort/search/compare logic) |
| `outputs/prediction_ui/` | Built UI: `index.html`, sources, `lib/vis-network.*` (copied from the Phase 2 viewer), `data/index.js`, 33 `data/prov/*.js`, 64 `data/train/b*.js`, `ui_manifest.json`, `README.md` |
| `phase6_evaluate.py` | Gated evaluation runner (not run) |
| `outputs/phase6/phase6_protocol.md` | Evaluation protocol for your approval |
| `tests/test_prediction_ui.py`, `tests/test_phase6_evaluate.py`, `tests/ui/filters.test.js` | New tests |
| `outputs/ui_phase6_implementation_report.md` | This report |

## Design notes

- **Static pages, no server.** Data is shipped as `.js` files, so `index.html` works by double-click
  (`file://`) in Edge or Chrome. `py -m http.server` is the documented fallback.
- **Size and loading.** The UI is 16 MB in total:
  - The index (all 3,648 unique predictions, i.e. 6,478 version rows, plus 17,050 entity labels) loads at start.
  - Provenance (one file per relation) and training edges (64 entity buckets) load only when needed.
  - The graph draws at most 250 predicted and 150 training edges at a time and prints the full counts.
- **Kept exactly from the source files:** IDs, relation direction, labels, ranks, scores and provenance.
  The build fails if v1 and v2 disagree on a triple's score, rules or provenance, if any prediction is a
  training triple, if a prediction ID does not match its triple, or if the comparison does not
  reproduce the v2 manifest's counts.
- **Evidence matches.** For v1 they are derived from v1's own stored groundings, using the same
  definition as v2, and cross-checked against v2 where a prediction is in both.
- **Evaluation gate.** The dashboard only loads `outputs/phase6/evaluation_test/evaluation_results.js` if
  it exists, and shows "not run" otherwise. The page has no way to run Python.
  `phase6_evaluate.py` without the approval flag prints the protocol and exits with code 2, reading nothing.

## Commands run (on your computer's Linux shell, Python 3.10, Node available)

```
python3 phase5_ui_build.py                    # built outputs/prediction_ui/ (29.7 s)
python3 -m unittest tests.test_prediction_ui tests.test_phase6_evaluate tests.test_phase5_predict \
    tests.test_phase5_rank_v2 tests.test_phase4_rule_mining tests.test_phase4_rule_evaluation \
    tests.test_phase4_grid_ext tests.test_phase4_methodology_experiment
python3 phase6_evaluate.py                    # gate check: exit code 2, no results written
```

## Test results

- **102 tests pass, none skipped.**
- **New UI tests:**
  - row IDs, direction, ranks, scores and labels match the sources
  - no prediction is a training triple
  - provenance chunks equal the source records
  - evidence counts match v2
  - the training buckets contain exactly the training graph
  - the comparison equals the v2 manifest
  - the build is deterministic and refuses to overwrite
  - the build leaves inputs unchanged and never opens validation/test files
  - the page assets exist and the page does not run evaluation
  - a tampered prediction file is refused
  - the built UI matches its manifest
- **JavaScript filter tests (Node):** version, relation, score range, top-N, entity, text and comparison filters;
  sorting; paging; entity search; the evaluation status.
- **Phase 6 runner tests (on a synthetic fixture only, never the real test split):**
  - the CLI gate reads nothing and exits with code 2, and `run()` refuses without approval
  - labels and metrics with hand-computed numbers, including per relation and validation annotation
  - output hashes match and existing results are not overwritten
  - a modified split file is refused
  - the metric denominators
- **Browser check (headless Chromium, on a copy of part of the UI):**
  - graph, entity view, table sorting, provenance panel, evidence view and comparison work, with no script errors
  - the Phase 6 tab shows "not run"
  - on the synthetic fixture with results, the dashboard tables and charts render
- **Not run:** `tests/test_display_labels.py` (it reads the test split files) and the Phase 2 tests (networkx missing).

## Integrity

- All 63 previously hashed files are unchanged: data (excluding the split files), Phase 1–5 outputs, earlier scripts and tests.
- The validation/test files have the same size and timestamp.
- `outputs/phase6/evaluation_test/` does not exist.
- **Disclosure:** one shell command during inspection opened `data/test.txt` and discarded its first 600 bytes
  unseen (`head -c 600 … > /dev/null`). Nothing was read into any process or used.

## Limitations

- **Graph caps.** The graph view draws a capped subset. Every prediction is still searchable and filterable
  in the table, which is paged.
- **Entity search scope.** It covers the 17,050 training entities (all prediction endpoints are among them).
- **Browser settings.** Opening from `file://` relies on the browser allowing local script files (Edge and Chrome do by
  default). Otherwise use `py -m http.server`.
- **Metric interpretation.** Phase 6 metrics will describe agreement with this benchmark's labelled
  triples only; see `outputs/phase6/phase6_protocol.md`.
