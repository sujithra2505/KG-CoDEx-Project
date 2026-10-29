# Phase 3 ontology outputs

From the project root, run:

```powershell
py phase3_ontology.py
```

This builds an RDF dataset from `data/train.txt` and the two label maps only, and
writes two new files:

- `codexm_train_ontology.trig`: TriG dataset with three named graphs
  - `urn:codexm:graph:train`: the 185,584 unique training triples, as
    `<urn:codexm:entity:Q…> <urn:codexm:relation:P…> <urn:codexm:entity:Q…>`.
    No labels, types or provenance appear here.
  - `urn:codexm:graph:labels`: English `rdfs:label`s, `urn:codexm:vocab:sourceId`
    literals holding the original IDs, and only the generic declarations
    `owl:NamedIndividual` (entities) and `owl:ObjectProperty` (relations).
  - `urn:codexm:graph:provenance`: source path and SHA-256, row, duplicate,
    entity and relation counts, label-file hashes, and converter version.
- `phase3_manifest.json`: counts, input/output hashes, verification results,
  hashes of protected Phase 1/2 and data files, and the generation time.

The builder never overwrites files. If either output already exists it stops
with an error; pass `--output-dir <new folder>` to build elsewhere. To recheck
the existing outputs without writing anything:

```powershell
py phase3_ontology.py --verify-only
```

Tests: `py -m pytest tests/test_phase3_ontology.py` (or
`py -m unittest tests.test_phase3_ontology`). The builder and tests need only
the Python standard library. If `rdflib` happens to be installed, one extra test
also reloads the TriG file with it.

Design rules (see `ontology_design.md`): training data only (validation, test
and negative files are hashed for integrity but never parsed); IDs and triple
direction kept exactly; malformed rows stop the build; no entity classes,
domain/range, inverse, symmetry, transitivity or other unsupported axioms; no
rule mining, inference or prediction. Consumers must select
`urn:codexm:graph:train` explicitly rather than querying the union of graphs.
