# Audit note: KG_CoDExM_Phase1_Literature_Review_Corrected.pdf

Revised 29 Oct 2026. The report is now 50 pages (it was 54). The earlier PDF, draft 4, the project code, the data and all outputs were not changed.

## Corrections made

1. **Guide and HOD in bold everywhere.** "Dr. Shailesh Sivan, Assistant Professor, Department of Computer Science, CUSAT" and "Dr. Bijoy A. Jose, Associate Professor and Head of the Department" are now bold on the title page, in the declaration, in the signature block and in the acknowledgement. Both checked against draft 4; no mismatch found.
2. **Literature review.** It keeps draft 4's eight themes, the paper order and the comparative tables. The tables are titled "Comparative review of existing research approaches", as in draft 4. All 43 papers are still cited, and the five selected papers are still marked †. Hash and SHA-256 wording is removed; duplicates are now described in one plain sentence.
3. **Architecture.** Replaced with 6 simple blocks: Dataset → Graph & Ontology → Rule Mining & Validation → Candidates & Ranking → Evaluation & Cap Selection → Results. Training, validation and test use is colour-coded, Future Work is in a separate dashed box, and the note that the test split was used twice is in the caption.
4. **Workflow.** New separate 10-stage pipeline figure (Fig. 4.2). It shows validation (rule review, cap selection) apart from the final test, plus the earlier cap-100 test baseline.
5. **Figures 5.1 and 5.2 combined.** They are now one figure (new Fig. 5.1), redrawn from `validation_results.json` and `selection.json`. It has a summary of the selected configuration, 7 metric panels across caps 100–1,000 for V1 and V2, the Wilson bound and the A1 floor. The full validation table is kept as Table 5.3. The old dashboard-screenshot figure is removed and the references are renumbered.
6. **Other figures.**
   - The dashboard test table was recaptured at a readable width.
   - The ontology code listing is replaced by a table of genuine triples (Table 4.3).
   - The landscape architecture page is gone.
   - Float placement was tightened.
7. **Gantt chart.** Reduced to **7 tasks**, with monthly columns Jul–Nov 2026 and a separate Future Work column. The task table now has **7 rows** (No. | Simplified Project Task | Status | Evidence / Remarks), using the same names and statuses as the chart. Milestones are reduced to 7, one per task.
8. **Appendix removed.** The repository structure, run commands, output-file table and evaluation-tab screenshot are gone. The References section is complete ([1]–[44]).
9. **Code-oriented text removed.** Script names, CLI flags, file paths and hash details are gone from the body. They are replaced by short conceptual descriptions.
10. **Writing.** The abstract, methodology, protocol and verification sections are rewritten in shorter sentences. Phases 1–6 are defined in Section 4.3.

## Results verified (no change)
Every value in your table matches the saved files: cap-100 V1/V2 from `evaluation_results.json`, and cap-1,000 V2 from `test_final/test_results.json`. There are no discrepancies. The validation split still has 10,310 positives and 10,310 negatives, not 10,311 (already noted in the previous audit).

## Still open / please confirm
- The Gantt months for the literature review and the old prototype are approximate, because no dated files exist for them.
- Future Work has no dates. Please agree them with your guide.
- SLogic [4] and the probabilistic-circuits paper [5] are cited as 2025; their PDF stamps say revised 2026.
- Signatures and the final submission date still need to be filled in.
- The editable source is LaTeX, the original format. It was not converted to DOCX.
