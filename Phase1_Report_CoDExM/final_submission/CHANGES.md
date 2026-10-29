# Changes in KG_CoDExM_Project_Report_Final_Submission.pdf (44 pages)

All results, methods, the literature review and the references are unchanged. No experiment was re-run.

- **Cover page.** The register number is now shown as "Register Number: **25021396**" under the name. The declaration signature block uses the same wording. In the acknowledgement, the guide line now ends "..., Department of Computer Science, CUSAT", the same as on the cover and in the declaration. The HOD line was left unchanged.
- **Fig 5.4 (prediction explorer).** The figure is now one large, readable crop of the genuine evidence panel. It shows the triple, score 0.918, V1 #7 / V2 #1, and rule 1 with its grounding. The small entity-view panel and the cut-off rule-2 panel were removed.
- **New Table 5.5.** It lists the full saved evidence for the same prediction:
  - both rules with support, standard confidence, PCA confidence and Wilson bound;
  - all 9 shared children that ground rule 2;
  - the score, matches, ranks and test label.

  The values were checked against the saved predictions file.
- **Fig 5.5 and Table 5.6 (V1/V2).** The content is unchanged. The part-of table is now numbered 5.6 because of the new Table 5.5.
- **Old Fig 6.3 (dashboard test table) removed.** It repeated Table 6.4 exactly. The text now says the dashboard agrees with Table 6.4. Old Fig 6.4 (per-relation matches) is now Fig 6.3. Fig 6.2 (validation cap comparison) is kept.
- **Figure numbering.** No Figure 5.6 existed in the earlier version. The old part-of graph had been replaced by a table, so the List of Figures was correct. The figure, table and section lists, and all cross-references, were rebuilt.
- **Gantt chart.** The month labels are larger and "1–6 Nov" is readable. A colour legend was added below the chart. The seven tasks and the 6 November 2026 deadline are unchanged.
- **Small fixes.** Section 3.7 now refers to the evidence panel and Table 5.5. The last row of Table 5.5 was wrapped so it stays inside the margin.

**Checked:** the final test results (23,772 / 927 / 73 / 22,772 / 92.70% / 8.99% / 16.39% / 3.90%) agree with the saved results file. The text still says that:
- unlabelled predictions are unknown, not false;
- the test split was used twice;
- benchmark precision is not accuracy;
- the ontology is not used in scoring.

**Still open:**
- The Gantt start dates are approximate.
- The HOD details need confirming.
- The signatures are blank.
