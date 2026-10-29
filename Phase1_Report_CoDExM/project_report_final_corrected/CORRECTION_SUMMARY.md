# Correction summary: KG_CoDExM_Project_Report_Final_Corrected.pdf (44 pages)

The original reports, project code, data, prediction outputs and evaluation files were not changed. The values below were checked against the saved project outputs.

## 1. Title page and headings
- **Front-page heading.** The heading is exactly "Project Report". The added "Experiments on the CoDEx-M benchmark" line was removed, so no subtitle remains.
- **Name and guide emphasis.** **SUGITHRA C S** and **Dr. Shailesh Sivan** are now large bold text, as in the main reference. The register number and the guide's designation are bold.
- **Main section headings** are now bold (large bold, as in the main reference), so they stand out from the body text. Subsections stay bold, in the same size order.
- **Fonts.** The fonts are now sharp vector Computer Modern; they were blurry bitmap fonts before. The typeface and sizes are unchanged.

## 2. Formatting kept from Draft 4
- **Kept unchanged:** page margins, single spacing, table style, the green/lavender/orange colour scheme, page numbering and the order of the front matter.
- **List of Figures and List of Tables** now show short captions.

## 3. Literature review
- **Archive wording removed.** The archive, folder, duplicate-PDF and "selected five" wording is gone, together with the paper-selection flow figure.
- **New opening.** The review now opens with symbolic vs. learned vs. hybrid KGC.
- **Scope section.** It is now called "Scope and review questions". It says plainly that this is a thematic review of 43 papers, not a systematic search.
- **Core papers.** The five core papers are introduced by their content in a table called "Core references of the project".
- **Taxonomy figure.** It was redrawn as a clear chart of the 8 themes, with the number of papers per theme and each theme's status.
- **References.** The references note was reworded to drop the archive wording. All 44 references and the citation numbers are unchanged.

## 4. Figures removed, combined or simplified
| Old figure | Action |
|---|---|
| 1.1 rule example | Redrawn as a readable diagram. Same facts and rule. |
| 3.1 selection flow | Removed (it described the archive). |
| 3.2 taxonomy | Redrawn (now Fig. 3.1). |
| 5.4 graph-viewer screenshots | Replaced by a clean one-hop diagram of Katherine Jackson. It shows all 15 training triples. |
| 5.5 ontology screenshot | Removed. It repeated Table 5.3 in tiny text. |
| 5.6 explorer default view | Removed. Its content is now described in the text. |
| 5.7 entity view + 5.8 evidence view | Combined into one evidence diagram (new Fig. 5.5), shown below the table. |
| 5.9 V1/V2 screenshots | Replaced by a bar chart (new Fig. 5.6): 2,830 kept, 409 dropped, 409 added, 1,499 rank changed. |
| 6.2 eight-panel test chart | Removed. It repeated Table 6.4. |
| 6.3 dashboard screenshot | Removed. It repeated Table 6.4. |

The new evidence diagram (Fig. 5.5) shows:
- known facts as solid edges and the prediction as a dashed edge;
- R1 (symmetry): Wilson bound 0.918, support 335;
- R2 (shared child): Wilson bound 0.904, 9 groundings;
- the score, 0.918, and that the triple is a test positive.

Figures that remain:
- the rule example;
- the taxonomy;
- the literature trends;
- the architecture;
- the workflow;
- relation frequency;
- the graph view;
- the evidence diagram;
- the V1/V2 chart;
- the validation-cap chart;
- the per-relation results;
- the Gantt chart.

## 5. Gantt chart
- Daily scale Jul–Nov 2026 plus an undated Future work block. No semester-end marker or semester row (removed on request).
- Exactly the seven task names. Light green = approximate periods; dark green = dates of saved outputs (28 Oct 2026: dataset, ontology, rules, candidates; 29 Oct 2026: cap experiment, test); yellow = report in progress; blue = planned.
- Seven-row task/evidence table matches the chart.

## 5a. Result images now use original project output
- Fig 6.1: original Phase 6 evaluation chart (cap-100 baseline, V1 vs V2).
- Fig 6.2: original cap-comparison dashboard output (selection summary cards + validation charts), replacing the recreated chart.
- Fig 6.3: original dashboard test-results table (matches Table 6.4).
- Fig 6.4 (per-relation matches, cap 1,000 V2) is still plotted from the saved per-relation results, because the dashboard has no per-relation view.

## 6. Technical and metric fixes
- **Test split used twice.** The final-test section said the selected configuration was "evaluated once on the test split". It now says this was the second use of the test split, after the cap-100 baseline.
- **Dataset table.** The test files were labelled "Final evaluation only". They are now labelled "Test evaluation (used twice)".
- **File paths removed.** Repository file paths were removed from figure and table captions.
- **Metrics re-checked.** All metrics agree across the abstract, tables and conclusion:

| Configuration | Predictions | TP | FP | Unlabelled | Precision | Recall | F1 | Hit rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cap-100 V1 | 3,239 | 257 | 13 | 2,969 | 95.19% | 2.49% | 4.86% | 7.93% |
| cap-100 V2 | 3,239 | 278 | 13 | 2,948 | 95.53% | 2.70% | 5.24% | 8.58% |
| cap-1000 V2 | 23,772 | 927 | 73 | 22,772 | 92.70% | 8.99% | 16.39% | 3.90% |

- **Evidence numbers** for the new diagrams were checked against the saved predictions and the test file. The V1/V2 counts were checked against the saved ranking comparison.

## 7. Unresolved / please check
- **HOD.** The report keeps Draft 4's HOD, Dr. Bijoy A. Jose. The main reference names Dr. Madhu S. Nair. Please confirm.
- **Output dates.** The 28–29 Oct 2026 dates come from the saved output manifests. These may be regeneration dates rather than the first time the work was done.
- **Approximate start dates.** The start dates for tasks 1–5 are approximate.
- **Signatures** are still blank.
- **Validation figure (Fig. 6.1).** Its small summary panel text is legible but small. It was kept because it is the only validation-cap chart.

## 8. Latest update: original project output in Section 5
- Fig 5.4: original training-graph viewer output (one-hop neighbourhood of Katherine Jackson), replacing the redrawn diagram.
- Fig 5.5: original prediction-explorer output: (a) entity view with training and predicted edges, (b) evidence panel of the spouse prediction (V1 rank #7, V2 rank #1, both rules, groundings).
- Fig 5.6: original V1-vs-V2 summary cards of the explorer (3,239 / 3,239 / 2,830 / 409 / 409 / 1,499), replacing the bar chart.
- Fig 5.7 (new): original explorer graphs of the 25 best-ranked predicted part-of (P361) edges in V1 and in V2 (only 21 of 100 shared). Screenshots were taken from the saved explorer files; nothing was changed.
