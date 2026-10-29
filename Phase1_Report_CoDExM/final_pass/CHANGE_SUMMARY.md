# Change summary: KG_CoDExM_Project_Report_Final_Corrected.pdf (44 pages)

The input report (`KG_CoDExM_Project_Report.pdf`, 45 pages) was left unchanged as the backup. The cover page, title, "Project Report" heading, names, guide/HOD details, colours, fonts, margins, literature review, reference numbering and comparative tables are all unchanged.

## Figures and pages changed
| Old (input PDF) | New | Change |
|---|---|---|
| Fig 5.1 architecture + Fig 5.2 workflow (pp. 18–19) | **Fig 5.1** (p. 19) | Combined into one 8-stage diagram (described below). The text was merged into Section 5.2, "Architecture and workflow of the implemented system". |
| Fig 5.5 explorer (p. 24) | **Fig 5.4** (p. 23) | Re-captured from the original explorer, using the layout with the fewest overlapping labels and the empty interface space cropped. The evidence panel is split into larger parts: (b) the triple, score 0.918, V1 #7 / V2 #1 and rule 1; (c) rule 2 with one grounding. |
| Fig 5.6 V1/V2 summary (p. 24) | **Fig 5.5** | The original summary cards are kept. The caption now says that both versions rank the same 184,487 candidates with the same scores and differ only in tie-break order. |
| Fig 5.7 part-of graphs (p. 25) | **Table 5.5** | The crowded graphs were replaced by a table of the five top-ranked part-of predictions of V1 and of V2 (V1 rank, V2 rank, body matches). The text explains that all 100 have the same score (0.186): V1 orders them by entity ID, V2 by body matches (median 8 vs 2). Only 21 predictions are shared. |
| Gantt chart, Table 7.1, Table 8.1 (pp. 30–31) | **Fig 7.1, Tables 7.1 and 8.1** | Simplified (see the Gantt section below). |

The eight stages in Fig 5.1 are:

1. dataset inspection
2. training graph
3. RDF/OWL
4. rule mining and validation review
5. candidate generation
6. scoring and V1/V2 ranking
7. explanations and explorer
8. evaluation

The new diagram also marks the split use. Stages 2–7 use training data only. Validation is used only for the rule review and the cap selection. The test split is used only in stage 8, for the cap-100 baseline and for cap-1,000 V2, and is never used for rules or candidates. Future work is shown in a separate box.

Fig 5.4 (training-graph viewer) and the Chapter 6 result figures were readable and are unchanged.

## Gantt chart
- The old task names were replaced by the seven simple tasks below. The same names are used in the chart, Table 7.1 (status/evidence) and Table 8.1 (milestones M1–M7).
  1. Literature review and problem definition
  2. Dataset inspection and preparation
  3. Training graph and visualisation
  4. RDF/OWL ontology construction
  5. Rule mining and validation
  6. Candidate prediction, ranking and explorer
  7. Evaluation, report and presentation
- The chart runs from 1 July to 6 November 2026 only, with a red marker labelled "Third semester ends (6 November 2026)". The Future-work block was removed, and planned work is listed in one sentence that points to Section 9.2.
- Colours:
  - Light green: approximate periods, unchanged from the earlier report.
  - Dark green: the dates in the saved output files. 28 Oct 2026 covers the dataset report, ontology, rules, candidates and rankings. 29 Oct 2026 covers the explorer, the cap experiment and the test. The training-graph date is the file date of the graph viewer.
  - Yellow: report and presentation work, in progress until 6 Nov.

## Text corrections
- Internal pipeline labels ("Phase 1", "Phase 3", "Phase 6", "Phase 4 rule review") were removed or replaced with plain descriptions in Sections 3, 4, 5, 6 and 9. The term "Phase 2" (meaning the next project stage) now reads "the next stage of the project".
- The objective O7 evidence now reads "Cap-100 test baseline; validation-based cap selection; test of the selected configuration".

## Checked against saved outputs
These values were re-read from the saved files and agree with the report:
- **Final test result:** 23,772 predictions, 927 TP, 73 FP, 22,772 unlabelled, precision 92.70%, recall 8.99%, F1 16.39%, hit rate 3.90%, recall ceiling 71.97%.
- **V1/V2 comparison:** 2,830 / 409 / 409 / 1,499.
- **Spouse prediction evidence:** score 0.918, V1 #7 / V2 #1, 2 rules, 10 matches.
- **Part-of table:** every row of Table 5.5.

No experiment was re-run and no project file was changed.

## Needs your decision
- **Gantt dates.** The start dates of tasks 1–6 are approximate, as in the earlier report. The dark-green days come from the dates in the saved files, which may be regeneration dates. Confirm, or give the real dates.
- **HOD.** The report keeps Dr. Bijoy A. Jose, Associate Professor and Head of the Department, as before. Please confirm.
- **Signatures** are still blank.
