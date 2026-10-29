# CoDEx-M prediction explorer and Phase 6 dashboard

A static web page for exploring the existing Phase 5 predictions (v1 in
`outputs/phase5/` and ranking v2 in `outputs/phase5/ranking_v2/`). It needs no
server, no internet access and no extra Python packages.

## Open the UI (Windows)

1. Open File Explorer at the project folder
   (`C:\Users\sugit\OneDrive\Desktop\KG-Ontology-Rule-Based-Project`).
2. Open `outputs\prediction_ui\index.html` by double-clicking it, or right-click it and choose
   **Open with → Microsoft Edge / Google Chrome**.

Open the **built** page in `outputs\prediction_ui\`, not `prediction_ui_src\index.html`:
the source folder is only a template and has no `data\` or `lib\` folder.

The page loads data from `.js` files next to it, so it works from `file://`.
A banner under the tabs says "Loading…", then how many predictions loaded, or
names the file that failed. If your browser blocks local scripts (or the banner
reports a failed file), start a local server from the project folder and open:

```powershell
cd C:\Users\sugit\OneDrive\Desktop\KG-Ontology-Rule-Based-Project
py -m http.server 8000
# then open http://localhost:8000/outputs/prediction_ui/index.html
```

## Rebuild the UI data (only if the Phase 5 files change)

```powershell
py phase5_ui_build.py --out-dir outputs\prediction_ui_rebuild
```

The builder only uses the Python standard library and refuses to overwrite an
existing folder. It reads the v1/v2 prediction files and their manifests (and
checks their hashes), the Phase 2 training graph (`training_graph.graphml`),
the label maps, and the vis-network library already embedded in the Phase 2
viewer. It never opens validation or test files.

## What the UI shows

- **Graph:** training facts are drawn as solid grey edges and predictions as dashed edges.
  Prediction colour and width follow the score (green ≥ 0.7, orange 0.4–0.7, red < 0.4).
  - **Default view:** the best-ranked predictions that match the filters, at most 250.
  - **Entity view:** pick an entity (type a Q-ID or name, then click a suggestion or press Enter; or click a node) to see its incoming and
    outgoing training edges (at most 150 drawn, total counts shown) and its predicted edges.
  - **Prediction details:** click a dashed edge for the triple, relation label, score, rank in v1/v2,
    inference round, supporting rule IDs and scores, and every body grounding (training evidence).
    "Show this evidence in the graph" draws that prediction with its supporting training facts.
- **Prediction table:** one row per prediction and version. Every column can be sorted
  (subject, relation, object, version, score, rank, rules, evidence matches). It is paged with 50 rows per page.
- **v1 vs v2:** counts kept in both, only in v1, only in v2 and rank changed (checked against the
  ranking-v2 manifest), a list for each group, and per-relation counts with score histograms.
- **Phase 6 evaluation:** shows "not run" plus the planned protocol until the results file
  `outputs/phase6/evaluation_test/evaluation_results.js` exists. The page never runs an evaluation.

Filters (version, relation, score range, top N per relation, text, entity) apply to every tab.

A higher score is a rule statistic, not proof that a prediction is true.

## Phase 6 evaluation (gated; run only after approval)

```powershell
py phase6_evaluate.py                                      # prints the protocol, reads nothing, exits with code 2
py phase6_evaluate.py --i-approve-phase6-test-evaluation   # labels predictions against the test split
```

The results go to `outputs/phase6/evaluation_test/` (never overwritten). Reload the page to see them.

## Tests

```powershell
py -m pytest tests\test_prediction_ui.py tests\test_phase6_evaluate.py
```

or use `py -m unittest`. The JavaScript filter tests run only if `node` is installed; otherwise they are skipped.

Browser check (needs Node 22+ and Chrome or Edge; drives the real page headless):

```powershell
node tests\ui\browser_smoke.js "file:///C:/Users/sugit/OneDrive/Desktop/KG-Ontology-Rule-Based-Project/outputs/prediction_ui/index.html"
node tests\ui\browser_smoke.js http://localhost:8000/outputs/prediction_ui/index.html   # with the server running
```
