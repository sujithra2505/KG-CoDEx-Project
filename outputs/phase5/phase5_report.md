# Phase 5 report: one-round rule-based prediction

**Date:** 2026-10-29. Phase 6 not started. Predictions were **not** scored against
validation or test data, and no validation or test file was opened.

## What was run

| Item | Value |
|---|---|
| Script | `phase5_predict.py` (new, v5.1.0); tests `tests/test_phase5_predict.py` (new) |
| Training graph | Phase 2 graph, read from `outputs/phase2/training_graph.graphml` (185,584 edges) |
| Graph checks | GraphML `source_sha256` = `data/train.txt` hash; edge count matches `filtering_decisions.json`; no duplicates |
| Rules | `outputs/phase4/phase5_candidate_rules_proposed.json`, unchanged (SHA-256 `3723c68a…4a54`), 160 rules |
| Rule details | Bodies and standard confidence read from `run_grid_ext/selected_rules.json`; its hash equals the list's `source_selected_rules_sha256`, and every rule's text, ID, head, PCA, Wilson, support and counting match |
| Rounds | 1: rules are applied to training facts only, and predictions are never reused as evidence |
| Ranking score | `max_wilson_lower` = highest Wilson lower bound among the rules that predict the triple |
| Tie-break | higher max PCA confidence → more supporting rules → lower subject ID number → lower object ID number |
| Cap | at most 100 per relation, after merging duplicates and dropping triples already in training |

**Why the GraphML export:** `phase2_graph.load_training_graph()` needs `networkx`
and `pyvis`. They are not installed in this environment, and package downloads
are blocked. The GraphML file is that function's own export of the same graph.

## Results

- **Candidates:** 212,342 rule × pair records. 65,813 body pairs were skipped
  because the head is already a training triple. 27,855 duplicate records were
  merged, leaving 184,487 unique candidate triples.
- **Retained:** **3,239 predictions** across 33 relations (the cap of 100 applies in
  32; P40 child has only 39 candidates). 1,396 are supported by more than one rule.
  143 of the 160 rules support at least one retained prediction.
- **Score tiers:** 778 at ≥ 0.7, 1,036 between 0.4 and 0.7, 1,425 below 0.4.
- **Provenance:** each prediction lists all of its rules, with standard
  confidence, PCA confidence, Wilson score, support, counting unit and every
  body grounding (11,059 groundings, up to 323 for one rule).
- **Files:** `predictions.json` (7.6 MB), `predictions_report.md` (per relation,
  top 3 with evidence), `prediction_viewer.html` and `phase5_manifest.json`
  (input hashes, settings, counts, output hashes).
- **Viewer:** reuses the vis-network 9.1.2 library embedded in the Phase 2
  viewer. Predicted edges are dashed and colored by score (green ≥ 0.7,
  orange 0.4–0.7, red < 0.4) with width growing with score. Supporting
  training triples are solid grey. It has a relation filter, top-N, entity
  search and a provenance panel. It was opened in a headless browser: no
  script errors, and the relation filter and provenance panel work.

## Important findings

1. **The cap is mostly decided by tie-breaks.** Many candidates share the same
   score because one rule produces them all. In 31 of the 32 capped relations
   the 100th and 101st candidates tie on score, PCA and rule count, so subject
   and object ID numbers decide which ones are kept.
   - In 9 relations every candidate ties, so the ID numbers alone pick the 100:
     P69, P108, P159, P161, P264, P361, P463, P509 and P840.
   - The selection is deterministic and documented, but it is **not** a quality
     ranking. Lower Q-numbers (usually older, better-known Wikidata items) are favored.
2. **High scores do not mean true.** Example: rank 2 for P17 is "London →
   country → United States of America", score 0.759. It comes from
   `P740(y,x) & P495(y,z) ⇒ P17(x,z)` (a band formed in London whose country of
   origin is the USA). This is a hub-driven pattern, not a fact.
3. **Some relations only get low scores.** The best predictions for P840, P361,
   P136, P69, P101 and P108 are all below 0.25.

## Tests

- **Phase 5:** 11 tests pass on your computer (Python 3.10, `unittest`). They cover:
  - outputs are byte-identical across runs
  - no overlap with training, no duplicates, no self-loops
  - provenance is valid: each grounding uses training triples and binds x and z to the predicted triple; scores match the frozen rules
  - the cap is enforced and the ranking order and ranks are correct
  - protected files are unchanged and validation/test files are never opened
  - overwrite is refused, inconsistent inputs and a tampered rule source are refused
  - the viewer marks predicted and training edges
  - the checked-in outputs match the manifest
- **Phase 4:** all 62 tests pass again.
- **Not run:** the Phase 2 tests, because `networkx` is missing here.

## Integrity

- 35 hashed files are unchanged: the data, Phase 1–4 outputs and the rule list.
- The validation and test files have the same size and timestamp, and were never opened.
- The script also checks its protected inputs itself.

## Limitations

- Rule scores are training statistics, not calibrated probabilities.
- The 8 couple-counted rules score per couple; the other rules score per ordered pair.
- One round only.
- Hub entities generate many candidates.
- The cap is decided by ID number inside tie groups (finding 1).
- Validation and test scoring is left to Phase 6.

## Decisions for you

1. Accept the cap as is (documented, deterministic). Or add an evidence-based
   tie-break before ID numbers, such as the number of body groundings, and rerun
   into a new folder.
2. Approve moving on to Phase 6 planning.
