from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import phase3_ontology as p3
from phase3_ontology import (
    GRAPH_LABELS,
    GRAPH_PROVENANCE,
    GRAPH_TRAIN,
    IRI,
    Literal,
    Phase3ValidationError,
    Phase3VerificationError,
    build_dataset,
    check_axiom_allowlist,
    parse_canonical_trig,
    serialize_trig,
    verify_dataset,
    write_phase3_outputs,
)

try:  # Optional third-party cross-check; the builder itself needs only the stdlib.
    import rdflib
except ImportError:  # pragma: no cover - depends on the local environment
    rdflib = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PRODUCTION_TRAIN_SHA256 = "d99c3437ab51690391a26d96976adf6e5494dba7ef6902e77000551bfa566556"

ENTITY_LABELS = {
    "Q108946": "A Few Good Men",
    "Q39792": "Jack Nicholson",
    "Q1041": "Senegal",
    "Q7809": "UNESCO",
    "Q42": 'Quote " back\\slash\nnew line é 中 \U0001F600',
}
RELATION_LABELS = {"P161": "cast member", "P26": "spouse", "P463": "member of"}


class Fixture:
    """A small synthetic project directory; never touches the real data."""

    def __init__(self, test: unittest.TestCase, train_rows: list[str], entity_labels=None) -> None:
        directory = tempfile.TemporaryDirectory()
        test.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "data").mkdir()
        self.train = self.root / "data" / "train.txt"
        self.train.write_text("\n".join(train_rows) + "\n", encoding="utf-8")
        self.entities = self.root / "data" / "entity_labels.json"
        self.relations = self.root / "data" / "relation_labels.json"
        self.entities.write_text(json.dumps(entity_labels if entity_labels is not None else ENTITY_LABELS), encoding="utf-8")
        self.relations.write_text(json.dumps(RELATION_LABELS), encoding="utf-8")
        self.output = self.root / "outputs" / "phase3"

    def build(self):
        return build_dataset(self.train, self.entities, self.relations, self.root)

    def write(self, output_dir: Path | None = None):
        return write_phase3_outputs(output_dir or self.output, self.train, self.entities, self.relations, self.root)


def ids(build):
    return p3.check_training_graph_purity(build.graphs[GRAPH_TRAIN])


class InputContractTests(unittest.TestCase):
    def test_exact_duplicates_collapse_but_different_relations_remain(self) -> None:
        build = Fixture(self, ["Q108946\tP161\tQ39792", "Q108946\tP161\tQ39792", "Q108946\tP26\tQ39792"]).build()
        self.assertEqual(build.training.row_count, 3)
        self.assertEqual(len(build.training.duplicate_rows), 1)
        self.assertEqual(build.training.duplicate_rows[0]["line"], 2)
        self.assertEqual(ids(build), {("Q108946", "P161", "Q39792"), ("Q108946", "P26", "Q39792")})

    def test_malformed_rows_fail_with_line_numbers(self) -> None:
        cases = {
            "missing column": "Q108946\tP161",
            "empty identifier": "Q108946\t\tQ39792",
            "surrounding whitespace": "Q108946 \tP161\tQ39792",
            "space separated": "Q108946 P161 Q39792",
            "bad entity pattern": "X108946\tP161\tQ39792",
            "bad relation pattern": "Q108946\tQ161\tQ39792",
            "leading zero": "Q0108946\tP161\tQ39792",
            "blank line": "",
        }
        for name, bad_row in cases.items():
            with self.subTest(name):
                fixture = Fixture(self, ["Q108946\tP161\tQ39792", bad_row])
                with self.assertRaisesRegex(Phase3ValidationError, "line 2"):
                    fixture.build()
                self.assertFalse(fixture.output.exists())

    def test_malformed_input_writes_nothing(self) -> None:
        fixture = Fixture(self, ["Q108946\tP161"])
        with self.assertRaises(Phase3ValidationError):
            fixture.write()
        self.assertFalse((fixture.output / p3.TRIG_FILENAME).exists())

    def test_direction_and_relation_identity_preserved(self) -> None:
        build = Fixture(self, ["Q108946\tP161\tQ39792", "Q39792\tP161\tQ108946"]).build()
        train = build.graphs[GRAPH_TRAIN]
        self.assertIn((IRI("urn:codexm:entity:Q108946"), IRI("urn:codexm:relation:P161"), IRI("urn:codexm:entity:Q39792")), train)
        self.assertIn((IRI("urn:codexm:entity:Q39792"), IRI("urn:codexm:relation:P161"), IRI("urn:codexm:entity:Q108946")), train)
        self.assertEqual(len(train), 2)

    def test_validation_test_and_negative_files_never_enter_the_ontology(self) -> None:
        fixture = Fixture(self, ["Q108946\tP161\tQ39792"])
        for name in ("valid.txt", "test.txt", "valid_negatives.txt", "test_negatives.txt"):
            (fixture.root / "data" / name).write_text("Q1041\tP463\tQ7809\nnot a triple\n", encoding="utf-8")
        paths = fixture.write()
        graphs, _ = parse_canonical_trig(paths["trig"].read_text(encoding="utf-8"))
        self.assertEqual(p3.check_training_graph_purity(graphs[GRAPH_TRAIN]), {("Q108946", "P161", "Q39792")})
        all_terms = {t for triples in graphs.values() for triple in triples for t in triple}
        self.assertNotIn(IRI("urn:codexm:entity:Q1041"), all_terms)
        self.assertNotIn(IRI("urn:codexm:relation:P463"), all_terms)

    def test_unmapped_labels_are_reported_not_fabricated(self) -> None:
        labels = dict(ENTITY_LABELS)
        del labels["Q39792"]
        fixture = Fixture(self, ["Q108946\tP161\tQ39792"], entity_labels=labels)
        build = fixture.build()
        self.assertEqual(build.unmapped_entity_ids, ("Q39792",))
        subject = IRI("urn:codexm:entity:Q39792")
        self.assertFalse(any(s == subject and p == IRI(p3.RDFS_LABEL) for s, p, _ in build.graphs[GRAPH_LABELS]))
        manifest = json.loads(fixture.write()["manifest"].read_text(encoding="utf-8"))
        self.assertEqual(manifest["unmapped_entity_labels"], ["Q39792"])


class GraphStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.build = Fixture(self, ["Q108946\tP161\tQ39792", "Q1041\tP463\tQ7809", "Q42\tP26\tQ39792"]).build()

    def test_training_graph_contains_only_training_assertions(self) -> None:
        train = self.build.graphs[GRAPH_TRAIN]
        for subject, predicate, obj in train:
            self.assertTrue(subject.value.startswith(p3.ENTITY_NS))
            self.assertTrue(predicate.value.startswith(p3.RELATION_NS))
            self.assertIsInstance(obj, IRI)
            self.assertTrue(obj.value.startswith(p3.ENTITY_NS))
        self.assertEqual(len(train), 3)

    def test_labels_and_provenance_live_in_their_own_graphs(self) -> None:
        labels = self.build.graphs[GRAPH_LABELS]
        provenance = self.build.graphs[GRAPH_PROVENANCE]
        self.assertIn(
            (IRI("urn:codexm:entity:Q108946"), IRI(p3.RDFS_LABEL), Literal("A Few Good Men", language="en")), labels
        )
        self.assertIn((IRI("urn:codexm:relation:P161"), IRI(p3.SOURCE_ID), Literal("P161")), labels)
        self.assertIn(
            (IRI(p3.DATASET_IRI), IRI(p3.VOCAB_NS + "uniqueTripleCount"), Literal("3", datatype=p3.XSD_INTEGER)),
            provenance,
        )
        self.assertTrue(all(s == IRI(p3.DATASET_IRI) for s, _, _ in provenance))

    def test_only_generic_declarations_are_present(self) -> None:
        check_axiom_allowlist(self.build.graphs)
        types = {(s.value, o.value) for s, p, o in self.build.graphs[GRAPH_LABELS] if p == IRI(p3.RDF_TYPE)}
        self.assertIn(("urn:codexm:entity:Q108946", p3.OWL_NAMED_INDIVIDUAL), types)
        self.assertIn(("urn:codexm:relation:P161", p3.OWL_OBJECT_PROPERTY), types)
        self.assertEqual({o for _, o in types}, {p3.OWL_NAMED_INDIVIDUAL, p3.OWL_OBJECT_PROPERTY})

    def test_axiom_allowlist_rejects_unsupported_axioms(self) -> None:
        relation = IRI("urn:codexm:relation:P26")
        for forbidden in (
            (relation, IRI("http://www.w3.org/2000/01/rdf-schema#domain"), IRI("urn:x:Person")),
            (relation, IRI(p3.RDF_TYPE), IRI("http://www.w3.org/2002/07/owl#SymmetricProperty")),
            (relation, IRI("http://www.w3.org/2002/07/owl#inverseOf"), IRI("urn:codexm:relation:P161")),
            (IRI("urn:codexm:entity:Q42"), IRI(p3.RDF_TYPE), IRI("urn:x:Human")),
        ):
            graphs = {name: set(triples) for name, triples in self.build.graphs.items()}
            graphs[GRAPH_LABELS].add(forbidden)
            with self.subTest(forbidden[1].value), self.assertRaises(Phase3VerificationError):
                check_axiom_allowlist(graphs)

    def test_serialized_text_has_no_forbidden_vocabulary(self) -> None:
        text = serialize_trig(self.build.graphs)
        for term in p3.FORBIDDEN_TERMS:
            self.assertNotIn(term, text)


class SerializationTests(unittest.TestCase):
    def test_round_trip_preserves_every_graph_and_escaped_labels(self) -> None:
        build = Fixture(self, ["Q42\tP161\tQ39792", "Q108946\tP161\tQ39792"]).build()
        text = serialize_trig(build.graphs)
        graphs, counts = parse_canonical_trig(text)
        self.assertEqual(graphs, build.graphs)
        verify_dataset(graphs, counts, build)
        label = next(o for s, p, o in graphs[GRAPH_LABELS] if s == IRI("urn:codexm:entity:Q42") and p == IRI(p3.RDFS_LABEL))
        self.assertEqual(label, Literal(ENTITY_LABELS["Q42"], language="en"))

    def test_tampered_serialization_is_detected(self) -> None:
        build = Fixture(self, ["Q108946\tP161\tQ39792", "Q1041\tP463\tQ7809"]).build()
        text = serialize_trig(build.graphs)
        reversed_edge = text.replace(
            "<urn:codexm:entity:Q108946> <urn:codexm:relation:P161> <urn:codexm:entity:Q39792> .",
            "<urn:codexm:entity:Q39792> <urn:codexm:relation:P161> <urn:codexm:entity:Q108946> .",
        )
        dropped = text.replace("<urn:codexm:entity:Q1041> <urn:codexm:relation:P463> <urn:codexm:entity:Q7809> .\n", "")
        duplicated = text.replace(
            "<urn:codexm:entity:Q1041> <urn:codexm:relation:P463> <urn:codexm:entity:Q7809> .\n",
            "<urn:codexm:entity:Q1041> <urn:codexm:relation:P463> <urn:codexm:entity:Q7809> .\n" * 2,
        )
        for name, bad in (("reversed", reversed_edge), ("dropped", dropped), ("duplicated", duplicated)):
            with self.subTest(name):
                self.assertNotEqual(bad, text)
                with self.assertRaises(Phase3VerificationError):
                    verify_dataset(*parse_canonical_trig(bad), build)

    def test_parser_is_strict(self) -> None:
        for bad in (
            "<urn:g> {\n<urn:a> <urn:b> <urn:c>\n}\n",  # missing terminator
            "<urn:a> <urn:b> <urn:c> .\n",  # triple outside graph
            "<urn:g> {\n<urn:a> <urn:b> <urn:c> .\n",  # unclosed graph
            '<urn:g> {\n"lit" <urn:b> <urn:c> .\n}\n',  # literal subject
        ):
            with self.subTest(bad), self.assertRaises(Phase3VerificationError):
                parse_canonical_trig(bad)

    def test_builds_are_deterministic(self) -> None:
        rows = ["Q1041\tP463\tQ7809", "Q108946\tP161\tQ39792", "Q108946\tP26\tQ39792"]
        fixture = Fixture(self, rows)
        first = fixture.write(fixture.root / "out_a")
        second = fixture.write(fixture.root / "out_b")
        self.assertEqual(first["trig"].read_bytes(), second["trig"].read_bytes())
        manifest_a = json.loads(first["manifest"].read_text(encoding="utf-8"))
        manifest_b = json.loads(second["manifest"].read_text(encoding="utf-8"))
        for manifest in (manifest_a, manifest_b):
            manifest.pop("generated_at")
            manifest["output"].pop("path")
        self.assertEqual(manifest_a, manifest_b)
        # Row order in the source does not change the output graph contents.
        shuffled = Fixture(self, list(reversed(rows))).build()
        original = fixture.build()
        for graph_iri in (GRAPH_TRAIN, GRAPH_LABELS):
            self.assertEqual(shuffled.graphs[graph_iri], original.graphs[graph_iri])

    @unittest.skipIf(rdflib is None, "rdflib not installed; stdlib reload checks still run")
    def test_rdflib_parses_the_same_named_graphs(self) -> None:
        fixture = Fixture(self, ["Q42\tP161\tQ39792", "Q108946\tP161\tQ39792", "Q1041\tP463\tQ7809"])
        paths = fixture.write()
        dataset = rdflib.Dataset()
        dataset.parse(paths["trig"], format="trig")
        graphs, _ = parse_canonical_trig(paths["trig"].read_text(encoding="utf-8"))
        for graph_iri, triples in graphs.items():
            rdflib_triples = {
                tuple(str(term) for term in triple) for triple in dataset.graph(rdflib.URIRef(graph_iri))
            }
            ours = {tuple(t.value if isinstance(t, IRI) else t.lexical for t in triple) for triple in triples}
            self.assertEqual(rdflib_triples, ours, graph_iri)


class OutputProtectionTests(unittest.TestCase):
    def test_existing_targets_are_never_overwritten(self) -> None:
        fixture = Fixture(self, ["Q108946\tP161\tQ39792"])
        fixture.output.mkdir(parents=True)
        existing = fixture.output / p3.TRIG_FILENAME
        existing.write_text("keep me", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            fixture.write()
        self.assertEqual(existing.read_text(encoding="utf-8"), "keep me")
        self.assertFalse((fixture.output / p3.MANIFEST_FILENAME).exists())

    def test_second_write_to_same_directory_is_refused(self) -> None:
        fixture = Fixture(self, ["Q108946\tP161\tQ39792"])
        paths = fixture.write()
        before = {name: path.read_bytes() for name, path in paths.items()}
        with self.assertRaises(FileExistsError):
            fixture.write()
        self.assertEqual({name: path.read_bytes() for name, path in paths.items()}, before)

    def test_manifest_records_hashes_and_counts(self) -> None:
        fixture = Fixture(self, ["Q108946\tP161\tQ39792", "Q108946\tP161\tQ39792"])
        paths = fixture.write()
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        self.assertEqual(manifest["output"]["sha256"], hashlib.sha256(paths["trig"].read_bytes()).hexdigest())
        self.assertEqual(manifest["inputs"]["training_triples"]["sha256"], hashlib.sha256(fixture.train.read_bytes()).hexdigest())
        self.assertEqual(manifest["counts"]["exact_duplicates_removed"], 1)
        self.assertEqual(manifest["counts"]["unique_training_triples"], 1)
        self.assertTrue(manifest["protected_files_unchanged"])
        self.assertIn("data/train.txt", manifest["protected_files_sha256"])


@unittest.skipUnless((DATA / "train.txt").is_file(), "production training file not present")
class ProductionSnapshotTests(unittest.TestCase):
    """Read-only checks against the checked-in CoDEx-M snapshot (writes go to a temp dir)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.protected_before = p3.protected_file_hashes(ROOT)
        cls.temporary = tempfile.TemporaryDirectory()
        cls.paths = write_phase3_outputs(Path(cls.temporary.name) / "phase3")
        cls.protected_after = p3.protected_file_hashes(ROOT)
        cls.build = build_dataset()
        cls.graphs, cls.counts = parse_canonical_trig(cls.paths["trig"].read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_source_snapshot_is_the_expected_file(self) -> None:
        self.assertEqual(self.build.training.source_sha256, PRODUCTION_TRAIN_SHA256)

    def test_every_source_triple_survives_serialization_and_reload_exactly(self) -> None:
        with (DATA / "train.txt").open(encoding="utf-8") as handle:
            source = {tuple(line.rstrip("\n").split("\t")) for line in handle}
        reloaded = p3.check_training_graph_purity(self.graphs[GRAPH_TRAIN])
        self.assertEqual(reloaded, source)
        self.assertEqual(len(reloaded), 185584)
        self.assertEqual(self.counts[GRAPH_TRAIN], 185584)

    def test_entity_and_relation_counts(self) -> None:
        reloaded = p3.check_training_graph_purity(self.graphs[GRAPH_TRAIN])
        self.assertEqual(len({s for s, _, _ in reloaded} | {o for _, _, o in reloaded}), 17050)
        self.assertEqual(len({r for _, r, _ in reloaded}), 51)
        self.assertEqual(self.build.unmapped_entity_ids, ())
        self.assertEqual(self.build.unmapped_relation_ids, ())

    def test_known_triple_direction(self) -> None:
        reloaded = p3.check_training_graph_purity(self.graphs[GRAPH_TRAIN])
        self.assertIn(("Q108946", "P161", "Q39792"), reloaded)
        self.assertNotIn(("Q39792", "P161", "Q108946"), reloaded)

    def test_full_verification_and_allowlist(self) -> None:
        result = verify_dataset(self.graphs, self.counts, self.build)
        self.assertTrue(result["exact_set_match_with_source"])
        self.assertTrue(result["axiom_allowlist_passed"])

    def test_protected_files_unchanged(self) -> None:
        self.assertEqual(self.protected_before, self.protected_after)
        self.assertIn("data/train.txt", self.protected_before)
        self.assertIn("phase2_graph.py", self.protected_before)
        self.assertIn("outputs/phase1_dataset_report.md", self.protected_before)

    def test_deterministic_against_fresh_rebuild(self) -> None:
        self.assertEqual(serialize_trig(build_dataset().graphs).encode("utf-8"), self.paths["trig"].read_bytes())


@unittest.skipUnless((p3.OUTPUT_DIR / p3.TRIG_FILENAME).is_file(), "Phase 3 outputs not generated yet")
class CheckedInOutputTests(unittest.TestCase):
    def test_existing_outputs_verify_read_only(self) -> None:
        result = p3.verify_existing_outputs()
        self.assertEqual(result["training_triples_reloaded"], 185584)
        self.assertTrue(result["manifest_hash_match"])
        self.assertTrue(result["byte_identical_rebuild"])


if __name__ == "__main__":
    unittest.main()
