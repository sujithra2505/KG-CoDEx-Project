# Audit note: KG_CoDExM_Phase1_Literature_Review_Final.pdf

Prepared 29 Oct 2026. The project code, data, outputs, dashboards, old report and paper archive were read only. Nothing in them was changed.

## 1. Papers reviewed

- The archive `project research papers KG new.zip` has 50 PDF files: 45 in the main folder and 5 in `selected five`.
- After removing duplicates there are **43 unique papers**, references [1]–[43]. All 43 are cited.
- I checked every title and author list against the first page of its PDF. All 43 match the bibliographic data used in draft 4.
- One reference comes from outside the archive: [44] Safavi & Koutra, *CoDEx: A comprehensive knowledge graph completion benchmark*, EMNLP 2020, pp. 8328–8350. It is cited only as the dataset source. I left out its DOI because I could not check it from the files.

## 2. The five selected papers (marked † in the report)

| No. | Ref | Title |
|---|---|---|
| S1 | [2] | Rule learning over knowledge graphs with genetic logic programming (Wu et al., ICDE 2022) |
| S2 | [4] | SLogic: Subgraph-Informed Logical Rule Learning for Knowledge Graph Completion (Le et al., arXiv 2025) |
| S3 | [5] | Probabilistic Circuits for Knowledge Graph Completion with Reduced Rule Sets (Patil et al., arXiv 2025) |
| S4 | [12] | Differentiable Learning of Logical Rules for Knowledge Base Reasoning (Yang, Yang & Cohen, NIPS 2017) |
| S5 | [39] | Knowledge Graph Embedding: A Survey from the Perspective of Representation Spaces (Cao et al., ACM CSUR 2024) |

## 3. Duplicates excluded (checked by MD5 hash)

- All 5 files in `selected five` are byte-identical copies of files in the main folder.
- `Anytime bottom-up rule learning for large-scale knowledge graph.pdf` is identical to `...knowledge graph completion.pdf`.
- `Knowledge Graph Embedding A Survey from the Perspective.pdf` is the author-deposited (Glasgow eprint) version of the published `Knowledge Graph Embedding_A Survey from the Perspective of Representation Spaces.pdf`. Both are counted as one paper, [39].

## 4. Bibliographic details not fully verified

- [4] SLogic and [5] Probabilistic circuits are arXiv preprints. Their PDF stamps say v3 (22 Aug 2026) and v2 (9 Aug 2026), but the arXiv IDs (2510.*, 2508.*) point to first submission in 2025. I used **2025** as the year, the same as draft 4. Please confirm which year you want to cite.
- [11] (IEEE Computer, 2025) has no volume or page numbers in the PDF.
- Page numbers and volumes for the other papers are as in draft 4 and agree with the PDF headers I checked.

## 5. Administrative details to confirm

- I kept the student name, register number, guide, HOD, department, university and the date "November 2026" from draft 4.
- I kept the registered project title, *Confidence-Aware Ontology-Based Inference for Missing Edge Prediction in Knowledge Graphs*, and **added a subtitle**: "Rule-Based Knowledge Graph Completion on the CoDEx-M Benchmark", plus the line "Phase 1 Project Report: Literature Review and Implementation Progress". Please confirm that this wording is acceptable.
- The signatures and the submission date still need to be filled in.

## 6. Values that differ from the starting points in the request

- **There are 10,310 validation positives and 10,310 validation negatives, not 10,311.** This was verified from `data/valid.txt`, `phase1_dataset_report.md` and the evaluation manifests. The test split does have 10,311 positives and 10,311 negatives. The report uses the verified values.
- All the metrics in the request table (cap-100 V1/V2 and cap-1,000 V2) match `evaluation_results.json` and `test_final/test_results.json` exactly.

## 7. Implementation facts to keep in mind

- The ontology (`codexm_train_ontology.trig`) holds only `owl:NamedIndividual` / `owl:ObjectProperty` declarations and labels. It has no domain, range or class axioms. The rule miner reads its training named graph as a source of triples, but **no ontology semantics influence scoring**. The report states this.
- No MRR, Hits@K, embedding or neural baseline exists in the project, and the report does not claim one.
- The test split was used twice: the Phase 6 cap-100 baseline, then the cap-1,000 V2 final test. The report says so in Sections 4.2, 5.7 and 7.2.
- To check the worked examples, I read `data/test.txt` once, only to confirm that two quoted triples are test positives. Nothing was tuned on it.

## 8. Screenshots and evidence

- All screenshots are genuine. I captured them from your project files (prediction explorer, cap dashboard, Phase 2 graph viewer) in a headless Chromium browser. Nothing in them was edited apart from cropping.
- All charts were plotted from the saved JSON/CSV results. The architecture, ontology and taxonomy diagrams are drawn from the code and the real TriG triples. Their editable DOT sources are in `architecture/`.
- There are no missing screenshots. Optional: if your guide prefers screenshots taken on your own Windows browser, recapture the same views (explorer: Graph, Entity "Katherine Jackson", Evidence view, Prediction table, v1 vs v2; dashboard: full page).
- The Gantt bars for the literature review, the problem formulation and the earlier FB15K-237 prototype are approximate, because there are no dated files for them. The planned months m1–m6 need confirmation with your guide.

## 9. Files delivered

- `KG_CoDExM_Phase1_Literature_Review_Final.pdf` – the report: 54 pages (10 front-matter pages and 44 numbered pages).
- `latex_source/` – the editable LaTeX source (`main.tex` plus the chapter files). It builds with `pdflatex main.tex`, run twice. The folder also has the chart, Gantt and screenshot scripts.
- `KG_CoDExM_Project_Architecture.png` and `architecture/` (`.svg`, `.pdf` and the editable `.dot`).
- `figures/` – every chart and screenshot used in the report.
