# Phase 1: Dataset Inspection and Relationship Analysis

**Inspection date:** 2026-10-28  
**Workspace:** `C:\Users\sugit\OneDrive\Desktop\KG-Ontology-Rule-Based-Project`  
**Scope:** Inspect the supplied CoDEx-M splits and mappings. No graph was
constructed, and no ontology, rules, inference, predictions, or evaluation
were produced.

## Files and observed format

The five dataset files are in `data\`. All files were read as UTF-8 text. Every
non-empty row in each file had exactly two tab characters and parsed as
`subject ID`, `relation ID`, `object ID`. Entity IDs matched `Q` followed by
digits; relation IDs matched `P` followed by digits. No header row was present.

The existing display mappings are `data\entity_labels.json` and
`data\relation_labels.json`; `display_labels.py` loads ID-to-label JSON maps.
The mappings resolved every entity and relation ID observed in these five
files. Labels below are for readability only; the inspected triples retain
their original IDs.

## Split statistics and row quality

“Unique entities” counts distinct IDs appearing in either endpoint column.
“Duplicate triples” counts repeated rows after the first occurrence within a
file. Negative files are reported as supplied negative examples, not treated
as positive facts.

| File | Rows / parsed triples | Unique entities | Unique relations | Duplicate triples | Malformed rows | Empty IDs | Invalid-format IDs | Unmapped entity / relation IDs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `train.txt` | 185,584 | 17,050 | 51 | 0 | 0 | 0 | 0 | 0 / 0 |
| `valid.txt` | 10,310 | 9,124 | 45 | 0 | 0 | 0 | 0 | 0 / 0 |
| `test.txt` | 10,311 | 9,137 | 43 | 0 | 0 | 0 | 0 | 0 / 0 |
| `valid_negatives.txt` | 10,310 | 4,990 | 43 | 0 | 0 | 0 | 0 | 0 / 0 |
| `test_negatives.txt` | 10,311 | 4,972 | 43 | 0 | 0 | 0 | 0 | 0 / 0 |

The supplied row counts and training totals agree with the official
[CoDEx-M statistics](https://github.com/tsafavi/codex). There were no
malformed rows, blank identifiers, invalid-format IDs, or repeated triples
within any file. The mapping files have 17,050 entity labels and 51 relation
labels, and all IDs used in these local files are covered.

## Positive-split overlap

Exact triple intersections were checked using the original three IDs:

| Split pair | Shared positive triples |
|---|---:|
| Train / validation | 0 |
| Train / test | 0 |
| Validation / test | 0 |

Both negative files have the same number of rows as their corresponding
validation/test positives. Their rows are unique, none is an exact match for a
positive triple in any of the three positive splits, and no negative row is
equal to the positive at the same row position. This is a structural check
only; it does not independently establish the semantic validity of every
negative label.

## Frequent relations

Counts below are from the union of the positive train, validation, and test
files. Each example is an actual triple from those files; labels are followed
by their source IDs.

| Count | Relation label (ID) | Example |
|---:|---|---|
| 71,596 | occupation (`P106`) | Anthony Edwards (`Q314924`) — occupation (`P106`) → actor (`Q33999`) |
| 16,828 | country of citizenship (`P27`) | Franz Werfel (`Q78514`) — country of citizenship (`P27`) → Republic of German-Austria (`Q268970`) |
| 12,584 | languages spoken, written, or signed (`P1412`) | Jan Hus (`Q43977`) — languages spoken, written, or signed (`P1412`) → Latin (`Q397`) |
| 11,761 | genre (`P136`) | Dirty Dancing (`Q253978`) — genre (`P136`) → romance film (`Q1054574`) |
| 11,490 | member of (`P463`) | Senegal (`Q1041`) — member of (`P463`) → UNESCO (`Q7809`) |
| 9,752 | educated at (`P69`) | Flannery O'Connor (`Q234579`) — educated at (`P69`) → University of Iowa (`Q182973`) |
| 9,249 | cast member (`P161`) | A Few Good Men (`Q108946`) — cast member (`P161`) → Jack Nicholson (`Q39792`) |
| 7,214 | place of birth (`P19`) | Franz Werfel (`Q78514`) — place of birth (`P19`) → Prague (`Q1085`) |

## Observed two-hop paths for inspection

The following are examples of directed paths found by joining training triples
where the first triple's object ID equals the second triple's subject ID.
Counts are occurrences of these adjacent triple pairs in the training data.
They are descriptive patterns only—not validated ontology rules or evidence
that a missing third triple should be inferred.

1. **1,425,045 paths — country of citizenship (`P27`) → diplomatic relation (`P530`)**
   - Dustin Hoffman (`Q42930`) — country of citizenship (`P27`) → United States of America (`Q30`)
   - United States of America (`Q30`) — diplomatic relation (`P530`) → Laos (`Q819`)
2. **339,698 paths — country of citizenship (`P27`) → member of (`P463`)**
   - Dustin Hoffman (`Q42930`) — country of citizenship (`P27`) → United States of America (`Q30`)
   - United States of America (`Q30`) — member of (`P463`) → International Telecommunication Union (`Q376150`)
3. **334,763 paths — diplomatic relation (`P530`) → diplomatic relation (`P530`)**
   - Niger (`Q1032`) — diplomatic relation (`P530`) → France (`Q142`)
   - France (`Q142`) — diplomatic relation (`P530`) → Angola (`Q916`)
4. **235,245 paths — country of origin (`P495`) → diplomatic relation (`P530`)**
   - Before Night Falls (`Q246997`) — country of origin (`P495`) → United States of America (`Q30`)
   - United States of America (`Q30`) — diplomatic relation (`P530`) → Laos (`Q819`)
5. **107,316 paths — diplomatic relation (`P530`) → member of (`P463`)**
   - Niger (`Q1032`) — diplomatic relation (`P530`) → France (`Q142`)
   - France (`Q142`) — member of (`P463`) → Asian Development Bank (`Q188822`)

These large path counts reflect the number of matching adjacent triple pairs,
including combinations through high-degree entities; they should not be read
as rule confidence or prediction quality.

## Phase 1 findings and data-quality notes

- The local data is consistent with CoDEx-M and the official split sizes.
- The inspected files have consistent tab-delimited triple structure and no
  row-level ID or duplicate issues under the checks above.
- Positive splits have no exact triple leakage between train, validation, and
  test.
- Both provided negative files are well-formed and have no exact overlap with
  known positive triples. Their semantic correctness was not independently
  assessed.
- No triples were filtered or changed. Low-frequency or unfamiliar relations
  were not discarded.
- Phase 1 stops here: no graph construction or downstream modeling was done.
