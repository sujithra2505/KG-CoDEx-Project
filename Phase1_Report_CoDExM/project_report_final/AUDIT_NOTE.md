# Audit note: KG_CoDExM_Project_Report_Final.pdf (47 pages)

Project code, datasets, prediction outputs, evaluation files, both earlier PDFs and the paper archive were not changed. Everything is new output.

## 1. Formatting restored from Draft 4
The previous template-style redesign was dropped: no blue title, no "Chapter N" headings and no running header. Draft 4's layout was measured and copied.

- **Page and type:** article class, 11 pt Computer Modern, and the same text block. The left margin is 2.8 cm and the text width is 15.9 cm. Body text is single-spaced.
- **Headings:** sections are numbered, use large non-bold type and do not start a new page. Subsections are bold.
- **Front-matter headings:** DECLARATION, Abstract and ACKNOWLEDGEMENT use bold headings at Draft 4's size. Their position matches Draft 4 to within 2 pt.
- **Word widths:** the widths of the title, front-matter and body words match Draft 4 exactly.
- **Reused from Draft 4:**
  - the colour scheme (green for implemented, lavender for experiment, dashed orange for planned);
  - booktabs tables;
  - bold numbered captions;
  - "10 References" as a numbered section;
  - the Contents layout.

## 2. Front page
- The heading is exactly **Project Report**. The words "Phase 1 Project Report" and "Literature Review and Implementation Progress" are not used anywhere.
- The front page carries:
  - the title "Confidence-Aware Ontology-Based Inference for Missing Edge Prediction in Knowledge Graphs";
  - the degree;
  - **SUGITHRA C S** and **25021396**;
  - the guide, **Dr. Shailesh Sivan, Assistant Professor, Department of Computer Science, CUSAT**;
  - the department, CUSAT and November 2026.
- **Highlighting** uses Draft 4's own typography (size and bold), with no new colours or boxes. The highlighted items are the name, register number, title, **CoDEx-M**, the guide and the HOD (**Dr. Bijoy A. Jose, Associate Professor and Head of the Department**). The guide and HOD are bold at every occurrence.
- **Added line:** a small line, "Experiments on the **CoDEx-M** benchmark", was placed under the title so that CoDEx-M is highlighted on the front page. This is the only addition to Draft 4's title-page layout. Remove it if it is not wanted.
- **Stage wording:** "Phase 1" was replaced by "current stage" in the stage wording. "Phase 1–6" in Section 5 still refers to the numbered pipeline stages of the code.

## 3. Literature review (in the style of the Agentic AI review)
Draft 4's eight KG themes and its citation numbers [1]–[44] were kept. The following were added:

- an introduction with the contributions of the review;
- the scope and four review questions (LQ1–LQ4);
- the eligibility criteria and a selection-flow figure (50 PDFs → 7 repeats → 43 unique → 8 themes);
- a data-charting paragraph;
- a comparison table with the 14 existing surveys;
- publication trends by year and by theme;
- a charting table of the 29 method papers;
- the theme-by-theme comparison tables;
- the development of the field;
- a new section, "Common limitations and open challenges" (C1–C5);
- trends and key lessons;
- the gap analysis.

The review is explicitly described as a structured thematic review of the supplied archive. It does not claim PRISMA or a systematic database search.

## 4. Figure corrections
- **Architecture (Fig. 5.1):** seven simple blocks with the training, validation and test roles labelled separately. Future work is a separate dashed box, and the crossing arrow was removed.
- **Workflow (Fig. 5.2):** a separate 10-stage figure. It notes that cap-100 V1 and V2 were evaluated on test before the cap experiment.
- **Validation figures:** the two earlier validation figures were combined into one.
- **Captions** state that the test split was used twice.

## 5. Gantt chart reduced
The chart has exactly seven tasks, with the requested names, drawn in pgfgantt in Draft 4's style:

- two title rows (months, then week ranges);
- Jul–Nov 2026 plus a Future Work block;
- dotted grid;
- light green for approximate, dark green for dated, yellow for ongoing and blue for planned;
- a red line at the end of November 2026.

The task table has 7 rows with the columns No. | Task | Status | Evidence. The appendix, code listings, commands and repository instructions are not in the report. All 44 references were kept.

## 6. Results check
All test metrics were re-checked against the saved evaluation files.

| Configuration | Predictions | TP | FP | Unlabelled | Precision | Recall | F1 | Hit rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cap-100 V1 | 3,239 | 257 | 13 | 2,969 | 95.19% | 2.49% | 4.86% | 7.93% |
| cap-100 V2 | 3,239 | 278 | 13 | 2,948 | 95.53% | 2.70% | 5.24% | 8.58% |
| cap-1000 V2 | 23,772 | 927 | 73 | 22,772 | 92.70% | 8.99% | 16.39% | 3.90% |

The report also states that:

- benchmark precision is not accuracy;
- unlabelled predictions are unknown, not false;
- the test split was used twice;
- the ontology is not used in scoring;
- no MRR/Hits@K or embedding baselines were run.

## 7. Unresolved / please check
- **HOD.** Draft 4 names Dr. Bijoy A. Jose and the template ZIP names Dr. Madhu S. Nair. Draft 4 was kept; please confirm.
- **Validation positives.** Validation has 10,310 positives, not 10,311 (the test split has 10,311). The report uses 10,310.
- **Citation years.** SLogic [4] and Probabilistic Circuits [5] are cited as 2025 preprints.
- **Gantt dates.** The months for the literature review and the early prototype are approximate. Future Work has no dates yet.
- **Signatures** are blank. The submission date is set to November 2026.
- **Front-page subtitle.** The "Experiments on the CoDEx-M benchmark" line is an addition (see Section 2).
