# Change log: final minimal pass (44 pages)

1. **Section 5.2 and the Fig 5.1 caption: data use.** The old text said "stages 2–7 use the training split only" and then said rule review uses validation, which contradicted it. It now states:
   - **Training data:** graph construction, RDF/OWL generation, rule mining, and candidate generation, scoring and ranking.
   - **Validation data:** only the rule review (stage 4) and the cap/ranking selection (stage 8).
   - **Test data:** evaluation only. The existing disclosure that the test split was used twice is kept.

   The Fig 5.1 caption was reworded to match.
2. **Table 5.2 and Table 1.1: filenames.** These now match the files on disk: `train.txt`, `valid.txt`, `valid_negatives.txt`, `test.txt`, `test_negatives.txt` (and `entity_labels.json`, `relation_labels.json`). The underscores had been dropped in the PDF.
3. **Section 1: Evoda and PCA confidence.** I checked this against the cited paper [2] (Wu et al., ICDE 2022). The paper says the standard confidence is not well suited under the open-world assumption ("Instead, we resort to the PCA confidence") and uses PCA confidence as its fitness function. So the claim is supported and the citation is correct. The sentence now names Evoda as the rule learner of Wu et al. [2], so that [2] is not repeated as if it were a second source. No new reference was added.
4. **Layout.**
   - Table 4.2 is no longer split across pages.
   - Tables that do continue across pages (1.1, 3.2, 3.10, 5.1, 5.3, 5.4, 6.1) now repeat their column headers.
   - The contents, the lists of figures and tables, and all cross-references were rebuilt. There are no undefined references and no build errors.

Results, figures, references and limitations are unchanged.
