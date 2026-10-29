"""Phase 3B: build a conservative RDF/TriG representation of CoDEx-M training triples.

The builder reads only ``data/train.txt`` and the two label mappings. It writes a
canonical TriG dataset with three named graphs:

* ``urn:codexm:graph:train``      - the unique training ID triples, nothing else
* ``urn:codexm:graph:labels``     - English display labels, source IDs and the two
                                    generic declarations (owl:NamedIndividual and
                                    owl:ObjectProperty)
* ``urn:codexm:graph:provenance`` - source hashes, counts and converter details

No entity classes, domain/range, inverse, symmetry, transitivity, property-chain,
subproperty or equivalence axioms are produced. Validation, test and negative
files are never parsed; they are only hashed to prove they were not modified.
No rule mining, inference or prediction happens here.

Only the Python standard library is used. The output is a strict, canonical TriG
subset (full IRIs, one triple per line, sorted), and ``parse_canonical_trig``
reloads it so the round trip can be verified without extra dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Tuple, Union


ROOT = Path(__file__).resolve().parent
TRAIN_PATH = ROOT / "data" / "train.txt"
ENTITY_LABELS_PATH = ROOT / "data" / "entity_labels.json"
RELATION_LABELS_PATH = ROOT / "data" / "relation_labels.json"
OUTPUT_DIR = ROOT / "outputs" / "phase3"
TRIG_FILENAME = "codexm_train_ontology.trig"
MANIFEST_FILENAME = "phase3_manifest.json"

CONVERTER_NAME = "phase3_ontology.py"
CONVERTER_VERSION = "3B.1.0"

ENTITY_NS = "urn:codexm:entity:"
RELATION_NS = "urn:codexm:relation:"
VOCAB_NS = "urn:codexm:vocab:"
GRAPH_TRAIN = "urn:codexm:graph:train"
GRAPH_LABELS = "urn:codexm:graph:labels"
GRAPH_PROVENANCE = "urn:codexm:graph:provenance"
DATASET_IRI = "urn:codexm:dataset:train"
GRAPH_ORDER = (GRAPH_TRAIN, GRAPH_LABELS, GRAPH_PROVENANCE)

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_NAMED_INDIVIDUAL = "http://www.w3.org/2002/07/owl#NamedIndividual"
OWL_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#ObjectProperty"
XSD_INTEGER = "http://www.w3.org/2001/XMLSchema#integer"
SOURCE_ID = VOCAB_NS + "sourceId"
LABEL_LANGUAGE = "en"

ALLOWED_TYPE_OBJECTS = frozenset({OWL_NAMED_INDIVIDUAL, OWL_OBJECT_PROPERTY})
FORBIDDEN_TERMS = frozenset(
    {
        "http://www.w3.org/2000/01/rdf-schema#domain",
        "http://www.w3.org/2000/01/rdf-schema#range",
        "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
        "http://www.w3.org/2000/01/rdf-schema#subClassOf",
        "http://www.w3.org/2000/01/rdf-schema#Class",
        "http://www.w3.org/2002/07/owl#Class",
        "http://www.w3.org/2002/07/owl#inverseOf",
        "http://www.w3.org/2002/07/owl#SymmetricProperty",
        "http://www.w3.org/2002/07/owl#AsymmetricProperty",
        "http://www.w3.org/2002/07/owl#TransitiveProperty",
        "http://www.w3.org/2002/07/owl#ReflexiveProperty",
        "http://www.w3.org/2002/07/owl#IrreflexiveProperty",
        "http://www.w3.org/2002/07/owl#FunctionalProperty",
        "http://www.w3.org/2002/07/owl#InverseFunctionalProperty",
        "http://www.w3.org/2002/07/owl#propertyChainAxiom",
        "http://www.w3.org/2002/07/owl#equivalentProperty",
        "http://www.w3.org/2002/07/owl#equivalentClass",
        "http://www.w3.org/2002/07/owl#sameAs",
        "http://www.w3.org/2002/07/owl#disjointWith",
        "http://www.w3.org/2002/07/owl#propertyDisjointWith",
        "http://www.w3.org/2002/07/owl#Restriction",
    }
)

ENTITY_ID_PATTERN = re.compile(r"Q[1-9][0-9]*")
RELATION_ID_PATTERN = re.compile(r"P[1-9][0-9]*")

# Files that must never change during a Phase 3 build (hash-checked before/after).
PROTECTED_FILES = (
    "DISPLAY_LABELS.md",
    "display_labels.py",
    "phase2_graph.py",
    "tests/test_display_labels.py",
    "tests/test_phase2_graph.py",
    "outputs/phase1_dataset_report.md",
    "outputs/phase3/ontology_design.md",
)
PROTECTED_GLOBS = ("data/*", "outputs/phase2/*")


class Phase3ValidationError(ValueError):
    """Raised when the training file or label mappings violate the input contract."""


class Phase3VerificationError(RuntimeError):
    """Raised when a serialized dataset does not reproduce the source exactly."""


# --------------------------------------------------------------------------- terms


@dataclass(frozen=True)
class IRI:
    value: str


@dataclass(frozen=True)
class Literal:
    lexical: str
    language: str | None = None
    datatype: str | None = None


Term = Union[IRI, Literal]
Triple = Tuple[Term, Term, Term]


def entity_iri(entity_id: str) -> IRI:
    if not ENTITY_ID_PATTERN.fullmatch(entity_id):
        raise Phase3ValidationError(f"invalid entity ID: {entity_id!r}")
    return IRI(ENTITY_NS + entity_id)


def relation_iri(relation_id: str) -> IRI:
    if not RELATION_ID_PATTERN.fullmatch(relation_id):
        raise Phase3ValidationError(f"invalid relation ID: {relation_id!r}")
    return IRI(RELATION_NS + relation_id)


def entity_id_from_iri(term: Term) -> str:
    if isinstance(term, IRI) and term.value.startswith(ENTITY_NS):
        identifier = term.value[len(ENTITY_NS):]
        if ENTITY_ID_PATTERN.fullmatch(identifier):
            return identifier
    raise Phase3VerificationError(f"not a reversible entity IRI: {term!r}")


def relation_id_from_iri(term: Term) -> str:
    if isinstance(term, IRI) and term.value.startswith(RELATION_NS):
        identifier = term.value[len(RELATION_NS):]
        if RELATION_ID_PATTERN.fullmatch(identifier):
            return identifier
    raise Phase3VerificationError(f"not a reversible relation IRI: {term!r}")


# ------------------------------------------------------------------------ parsing


@dataclass
class TrainingParse:
    source_path: Path
    source_sha256: str
    row_count: int
    valid_row_count: int
    unique_triples: tuple[tuple[str, str, str], ...]
    duplicate_rows: list[dict[str, Any]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_training_triples(training_path: Path) -> TrainingParse:
    """Parse ``subject<TAB>relation<TAB>object`` rows; fail on any malformed row.

    Row checks follow the Phase 2 contract (three non-empty, tab-separated fields,
    no surrounding whitespace), plus strict Q/P identifier patterns because IDs
    become IRIs. Only exact (subject, relation, object) repeats are duplicates.
    """
    raw_bytes = training_path.read_bytes()
    try:
        rows = raw_bytes.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError as error:
        raise Phase3ValidationError(f"{training_path} is not valid UTF-8: {error}") from error

    errors: list[str] = []
    seen: dict[tuple[str, str, str], int] = {}
    unique: list[tuple[str, str, str]] = []
    duplicates: list[dict[str, Any]] = []
    valid_rows = 0

    for line_number, row in enumerate(rows, start=1):
        fields = row.split("\t")
        if len(fields) != 3:
            errors.append(f"line {line_number}: expected 3 tab-separated fields, found {len(fields)}")
            continue
        if any(not value.strip() for value in fields):
            errors.append(f"line {line_number}: one or more identifiers are empty or whitespace-only")
            continue
        if any(value != value.strip() for value in fields):
            errors.append(f"line {line_number}: identifier contains leading or trailing whitespace")
            continue
        subject_id, relation_id, object_id = fields
        if not ENTITY_ID_PATTERN.fullmatch(subject_id):
            errors.append(f"line {line_number}: invalid subject entity ID {subject_id!r}")
            continue
        if not RELATION_ID_PATTERN.fullmatch(relation_id):
            errors.append(f"line {line_number}: invalid relation ID {relation_id!r}")
            continue
        if not ENTITY_ID_PATTERN.fullmatch(object_id):
            errors.append(f"line {line_number}: invalid object entity ID {object_id!r}")
            continue

        valid_rows += 1
        triple = (subject_id, relation_id, object_id)
        if triple in seen:
            duplicates.append(
                {"line": line_number, "duplicate_of_line": seen[triple], "triple": list(triple)}
            )
            continue
        seen[triple] = line_number
        unique.append(triple)

    if errors:
        shown = "\n  ".join(errors[:20])
        more = f"\n  ... and {len(errors) - 20} more" if len(errors) > 20 else ""
        raise Phase3ValidationError(
            f"{training_path}: {len(errors)} malformed row(s); nothing was written.\n  {shown}{more}"
        )
    if not unique:
        raise Phase3ValidationError(f"{training_path}: no training triples found")

    return TrainingParse(
        source_path=training_path,
        source_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        row_count=len(rows),
        valid_row_count=valid_rows,
        unique_triples=tuple(sorted(unique)),
        duplicate_rows=duplicates,
    )


def load_label_map(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as handle:
        mapping = json.load(handle)
    if not isinstance(mapping, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in mapping.items()
    ):
        raise Phase3ValidationError(f"expected a JSON object of ID-to-label strings in {path}")
    return mapping


# ----------------------------------------------------------------------- building


@dataclass
class Phase3Build:
    training: TrainingParse
    graphs: dict[str, set[Triple]]
    entity_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    unmapped_entity_ids: tuple[str, ...]
    unmapped_relation_ids: tuple[str, ...]
    inputs: dict[str, dict[str, str]] = field(default_factory=dict)


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _integer(value: int) -> Literal:
    return Literal(str(value), datatype=XSD_INTEGER)


def build_dataset(
    training_path: Path = TRAIN_PATH,
    entity_labels_path: Path = ENTITY_LABELS_PATH,
    relation_labels_path: Path = RELATION_LABELS_PATH,
    root: Path = ROOT,
) -> Phase3Build:
    """Build the three named graphs in memory from training data and label maps only."""
    training = parse_training_triples(training_path)
    entity_labels = load_label_map(entity_labels_path)
    relation_labels = load_label_map(relation_labels_path)

    entity_ids = sorted({s for s, _, _ in training.unique_triples} | {o for _, _, o in training.unique_triples})
    relation_ids = sorted({r for _, r, _ in training.unique_triples})

    train_graph: set[Triple] = {
        (entity_iri(s), relation_iri(r), entity_iri(o)) for s, r, o in training.unique_triples
    }

    labels_graph: set[Triple] = set()
    unmapped_entities: list[str] = []
    for entity_id in entity_ids:
        subject = entity_iri(entity_id)
        labels_graph.add((subject, IRI(RDF_TYPE), IRI(OWL_NAMED_INDIVIDUAL)))
        labels_graph.add((subject, IRI(SOURCE_ID), Literal(entity_id)))
        label = entity_labels.get(entity_id)
        if label is None:
            unmapped_entities.append(entity_id)
        else:
            labels_graph.add((subject, IRI(RDFS_LABEL), Literal(label, language=LABEL_LANGUAGE)))
    unmapped_relations: list[str] = []
    for relation_id in relation_ids:
        subject = relation_iri(relation_id)
        labels_graph.add((subject, IRI(RDF_TYPE), IRI(OWL_OBJECT_PROPERTY)))
        labels_graph.add((subject, IRI(SOURCE_ID), Literal(relation_id)))
        label = relation_labels.get(relation_id)
        if label is None:
            unmapped_relations.append(relation_id)
        else:
            labels_graph.add((subject, IRI(RDFS_LABEL), Literal(label, language=LABEL_LANGUAGE)))

    inputs = {
        "training_triples": {
            "path": _display_path(training_path, root),
            "sha256": training.source_sha256,
        },
        "entity_labels": {
            "path": _display_path(entity_labels_path, root),
            "sha256": sha256_file(entity_labels_path),
        },
        "relation_labels": {
            "path": _display_path(relation_labels_path, root),
            "sha256": sha256_file(relation_labels_path),
        },
    }

    dataset = IRI(DATASET_IRI)
    vocab = lambda name: IRI(VOCAB_NS + name)  # noqa: E731
    provenance_values: list[tuple[str, Term]] = [
        ("split", Literal("train")),
        ("sourceFile", Literal(inputs["training_triples"]["path"])),
        ("sourceSha256", Literal(training.source_sha256)),
        ("sourceRowCount", _integer(training.row_count)),
        ("validRowCount", _integer(training.valid_row_count)),
        ("malformedRowCount", _integer(0)),
        ("exactDuplicateCount", _integer(len(training.duplicate_rows))),
        ("uniqueTripleCount", _integer(len(training.unique_triples))),
        ("entityCount", _integer(len(entity_ids))),
        ("relationCount", _integer(len(relation_ids))),
        ("unmappedEntityLabelCount", _integer(len(unmapped_entities))),
        ("unmappedRelationLabelCount", _integer(len(unmapped_relations))),
        ("entityLabelFile", Literal(inputs["entity_labels"]["path"])),
        ("entityLabelSha256", Literal(inputs["entity_labels"]["sha256"])),
        ("relationLabelFile", Literal(inputs["relation_labels"]["path"])),
        ("relationLabelSha256", Literal(inputs["relation_labels"]["sha256"])),
        ("converter", Literal(CONVERTER_NAME)),
        ("converterVersion", Literal(CONVERTER_VERSION)),
        ("serialization", Literal("canonical TriG subset: full IRIs, one sorted triple per line")),
        ("assertionGraph", IRI(GRAPH_TRAIN)),
        ("labelGraph", IRI(GRAPH_LABELS)),
        ("provenanceGraph", IRI(GRAPH_PROVENANCE)),
        (
            "note",
            Literal(
                "Asserted CoDEx-M training facts only. No inferred, predicted, validation, "
                "test or negative triples; no domain, range, inverse, symmetry or other "
                "semantic axioms."
            ),
        ),
    ]
    provenance_graph: set[Triple] = {(dataset, vocab(name), value) for name, value in provenance_values}

    return Phase3Build(
        training=training,
        graphs={GRAPH_TRAIN: train_graph, GRAPH_LABELS: labels_graph, GRAPH_PROVENANCE: provenance_graph},
        entity_ids=tuple(entity_ids),
        relation_ids=tuple(relation_ids),
        unmapped_entity_ids=tuple(unmapped_entities),
        unmapped_relation_ids=tuple(unmapped_relations),
        inputs=inputs,
    )


# ------------------------------------------------------------------ serialization

_IRI_FORBIDDEN = re.compile(r'[\x00-\x20<>"{}|^`\\]')
_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t", "\b": "\\b", "\f": "\\f"}


def _format_iri(value: str) -> str:
    if _IRI_FORBIDDEN.search(value):
        raise Phase3ValidationError(f"IRI contains characters not allowed in TriG: {value!r}")
    return f"<{value}>"


def _escape_string(value: str) -> str:
    parts: list[str] = []
    for char in value:
        if char in _ESCAPES:
            parts.append(_ESCAPES[char])
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            parts.append(f"\\u{ord(char):04X}")
        elif 0xD800 <= ord(char) <= 0xDFFF:
            raise Phase3ValidationError(f"label contains an unpaired surrogate: {value!r}")
        else:
            parts.append(char)
    return "".join(parts)


def format_term(term: Term) -> str:
    if isinstance(term, IRI):
        return _format_iri(term.value)
    text = f'"{_escape_string(term.lexical)}"'
    if term.language is not None:
        if not re.fullmatch(r"[A-Za-z]+(-[A-Za-z0-9]+)*", term.language):
            raise Phase3ValidationError(f"invalid language tag {term.language!r}")
        return f"{text}@{term.language}"
    if term.datatype is not None:
        return f"{text}^^{_format_iri(term.datatype)}"
    return text


def serialize_trig(graphs: dict[str, set[Triple]]) -> str:
    """Return a deterministic TriG document (sorted lines, full IRIs, LF endings)."""
    lines = [
        f"# CoDEx-M Phase 3 RDF dataset generated by {CONVERTER_NAME} {CONVERTER_VERSION}.",
        "# Canonical TriG subset: full IRIs, one triple per line, lines sorted within each graph.",
        f"# <{GRAPH_TRAIN}> holds only asserted training triples; labels and provenance are separate.",
        "",
    ]
    for graph_iri in GRAPH_ORDER:
        lines.append(f"{_format_iri(graph_iri)} {{")
        rendered = sorted(" ".join(format_term(term) for term in triple) + " ." for triple in graphs[graph_iri])
        lines.extend(rendered)
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------------ reloading

_TOKEN = re.compile(
    r"""\s*(?:
        <(?P<iri>[^\x00-\x20<>"{}|^`\\]*)>
      | "(?P<lit>(?:[^"\\\n\r]|\\[tbnrf"'\\]|\\u[0-9A-Fa-f]{4}|\\U[0-9A-Fa-f]{8})*)"
        (?:@(?P<lang>[A-Za-z]+(?:-[A-Za-z0-9]+)*)|\^\^<(?P<dtype>[^\x00-\x20<>"{}|^`\\]*)>)?
    )""",
    re.VERBOSE,
)
_UNESCAPE = re.compile(r"\\(?:u([0-9A-Fa-f]{4})|U([0-9A-Fa-f]{8})|(.))")
_SIMPLE_UNESCAPES = {"t": "\t", "b": "\b", "n": "\n", "r": "\r", "f": "\f", '"': '"', "'": "'", "\\": "\\"}


def _unescape(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(1) or match.group(2):
            return chr(int(match.group(1) or match.group(2), 16))
        return _SIMPLE_UNESCAPES[match.group(3)]

    return _UNESCAPE.sub(replace, text)


def _parse_triple_line(line: str, line_number: int) -> Triple:
    terms: list[Term] = []
    position = 0
    for _ in range(3):
        match = _TOKEN.match(line, position)
        if not match:
            raise Phase3VerificationError(f"line {line_number}: cannot parse term in {line!r}")
        if match.group("iri") is not None:
            terms.append(IRI(match.group("iri")))
        else:
            terms.append(
                Literal(_unescape(match.group("lit")), language=match.group("lang"), datatype=match.group("dtype"))
            )
        position = match.end()
    if line[position:].strip() != ".":
        raise Phase3VerificationError(f"line {line_number}: expected ' .' terminator in {line!r}")
    subject, predicate, obj = terms
    if not isinstance(subject, IRI) or not isinstance(predicate, IRI):
        raise Phase3VerificationError(f"line {line_number}: subject and predicate must be IRIs")
    return subject, predicate, obj


def parse_canonical_trig(text: str) -> tuple[dict[str, set[Triple]], dict[str, int]]:
    """Strictly parse the canonical TriG subset written by ``serialize_trig``.

    Returns the graphs and the number of triple lines per graph, so callers can
    detect duplicated lines (set size smaller than line count).
    """
    graphs: dict[str, set[Triple]] = {}
    line_counts: dict[str, int] = {}
    current: str | None = None
    for line_number, raw in enumerate(text.split("\n"), start=1):
        line = raw.strip()
        if not line or (current is None and line.startswith("#")):
            continue
        if current is None:
            match = re.fullmatch(r"<([^\x00-\x20<>\"{}|^`\\]*)>\s*\{", line)
            if not match:
                raise Phase3VerificationError(f"line {line_number}: expected '<graph> {{', got {line!r}")
            current = match.group(1)
            if current in graphs:
                raise Phase3VerificationError(f"line {line_number}: graph {current} declared twice")
            graphs[current] = set()
            line_counts[current] = 0
            continue
        if line == "}":
            current = None
            continue
        graphs[current].add(_parse_triple_line(line, line_number))
        line_counts[current] += 1
    if current is not None:
        raise Phase3VerificationError(f"graph {current} is not closed")
    return graphs, line_counts


# --------------------------------------------------------------------- verification


def check_axiom_allowlist(graphs: dict[str, set[Triple]]) -> None:
    """Fail if any unsupported semantic axiom or class declaration is present."""
    for graph_iri, triples in graphs.items():
        for triple in triples:
            for term in triple:
                if isinstance(term, IRI) and term.value in FORBIDDEN_TERMS:
                    raise Phase3VerificationError(f"forbidden axiom term {term.value} in graph {graph_iri}")
            subject, predicate, obj = triple
            if predicate == IRI(RDF_TYPE):
                if graph_iri != GRAPH_LABELS:
                    raise Phase3VerificationError(f"rdf:type found outside the labels graph: {triple}")
                if not isinstance(obj, IRI) or obj.value not in ALLOWED_TYPE_OBJECTS:
                    raise Phase3VerificationError(f"unapproved rdf:type object: {triple}")
                expected = OWL_NAMED_INDIVIDUAL if subject.value.startswith(ENTITY_NS) else OWL_OBJECT_PROPERTY
                if obj.value != expected:
                    raise Phase3VerificationError(f"wrong generic declaration: {triple}")


def check_training_graph_purity(train_graph: set[Triple]) -> set[tuple[str, str, str]]:
    """Every training-graph triple must be entity-relation-entity; return the ID triples."""
    id_triples: set[tuple[str, str, str]] = set()
    for subject, predicate, obj in train_graph:
        id_triples.add((entity_id_from_iri(subject), relation_id_from_iri(predicate), entity_id_from_iri(obj)))
    return id_triples


def verify_dataset(
    graphs: dict[str, set[Triple]],
    line_counts: dict[str, int],
    build: Phase3Build,
) -> dict[str, Any]:
    """Compare reloaded graphs with the in-memory build and the parsed source triples."""
    if set(graphs) != set(GRAPH_ORDER):
        raise Phase3VerificationError(f"unexpected named graphs: {sorted(graphs)}")
    for graph_iri in GRAPH_ORDER:
        if line_counts[graph_iri] != len(graphs[graph_iri]):
            raise Phase3VerificationError(f"duplicate triple lines in graph {graph_iri}")
        if graphs[graph_iri] != build.graphs[graph_iri]:
            missing = len(build.graphs[graph_iri] - graphs[graph_iri])
            extra = len(graphs[graph_iri] - build.graphs[graph_iri])
            raise Phase3VerificationError(f"graph {graph_iri} differs: {missing} missing, {extra} unexpected")

    reloaded_ids = check_training_graph_purity(graphs[GRAPH_TRAIN])
    source_ids = set(build.training.unique_triples)
    if reloaded_ids != source_ids:
        raise Phase3VerificationError(
            f"training triples differ from source: {len(source_ids - reloaded_ids)} missing, "
            f"{len(reloaded_ids - source_ids)} unexpected"
        )
    check_axiom_allowlist(graphs)

    entities = {s for s, _, _ in reloaded_ids} | {o for _, _, o in reloaded_ids}
    relations = {r for _, r, _ in reloaded_ids}
    source_id_literals = {
        (s.value, o.lexical)
        for s, p, o in graphs[GRAPH_LABELS]
        if p == IRI(SOURCE_ID) and isinstance(o, Literal)
    }
    for entity_id in entities:
        if (ENTITY_NS + entity_id, entity_id) not in source_id_literals:
            raise Phase3VerificationError(f"sourceId literal missing or wrong for {entity_id}")
    for relation_id in relations:
        if (RELATION_NS + relation_id, relation_id) not in source_id_literals:
            raise Phase3VerificationError(f"sourceId literal missing or wrong for {relation_id}")

    return {
        "named_graphs": list(GRAPH_ORDER),
        "training_triples_reloaded": len(reloaded_ids),
        "training_triples_in_source": len(source_ids),
        "exact_set_match_with_source": True,
        "entities": len(entities),
        "relations": len(relations),
        "direction_and_relation_identity_preserved": True,
        "id_iri_mapping_reversible": True,
        "axiom_allowlist_passed": True,
        "training_graph_contains_only_training_assertions": True,
    }


# ------------------------------------------------------------------ file protection


def protected_file_hashes(root: Path = ROOT) -> dict[str, str]:
    paths: set[Path] = {root / relative for relative in PROTECTED_FILES}
    for pattern in PROTECTED_GLOBS:
        paths.update(root.glob(pattern))
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(paths)
        if path.is_file()
    }


def _write_new_file(path: Path, data: bytes) -> None:
    """Create ``path`` exclusively; never overwrite an existing file."""
    with path.open("xb") as handle:
        handle.write(data)


# ----------------------------------------------------------------------- pipeline


def write_phase3_outputs(
    output_dir: Path = OUTPUT_DIR,
    training_path: Path = TRAIN_PATH,
    entity_labels_path: Path = ENTITY_LABELS_PATH,
    relation_labels_path: Path = RELATION_LABELS_PATH,
    root: Path = ROOT,
) -> dict[str, Path]:
    """Build, verify and write the TriG dataset and manifest to new files only."""
    trig_path = output_dir / TRIG_FILENAME
    manifest_path = output_dir / MANIFEST_FILENAME
    existing = [str(path) for path in (trig_path, manifest_path) if path.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite existing Phase 3 output(s): "
            + ", ".join(existing)
            + ". Choose a new --output-dir."
        )

    hashes_before = protected_file_hashes(root)
    build = build_dataset(training_path, entity_labels_path, relation_labels_path, root)
    trig_text = serialize_trig(build.graphs)

    # Verify in memory before anything touches the disk.
    verify_dataset(*parse_canonical_trig(trig_text), build)
    if serialize_trig(build_dataset(training_path, entity_labels_path, relation_labels_path, root).graphs) != trig_text:
        raise Phase3VerificationError("serialization is not deterministic across two builds")

    output_dir.mkdir(parents=True, exist_ok=True)
    trig_bytes = trig_text.encode("utf-8")
    _write_new_file(trig_path, trig_bytes)

    # Verify again from the bytes actually on disk.
    on_disk = trig_path.read_bytes()
    verification = verify_dataset(*parse_canonical_trig(on_disk.decode("utf-8")), build)
    verification["reloaded_from"] = "disk"
    verification["deterministic_rebuild_identical"] = True

    hashes_after = protected_file_hashes(root)
    if hashes_after != hashes_before:
        changed = sorted(k for k in hashes_before.keys() | hashes_after.keys() if hashes_before.get(k) != hashes_after.get(k))
        raise Phase3VerificationError(f"protected files changed during the build: {changed}")

    manifest = build_manifest(build, trig_path, on_disk, verification, hashes_before, root)
    _write_new_file(manifest_path, (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return {"trig": trig_path, "manifest": manifest_path}


def build_manifest(
    build: Phase3Build,
    trig_path: Path,
    trig_bytes: bytes,
    verification: dict[str, Any],
    protected_hashes: dict[str, str],
    root: Path = ROOT,
) -> dict[str, Any]:
    training = build.training
    return {
        "phase": "3B",
        "converter": CONVERTER_NAME,
        "converter_version": CONVERTER_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": build.inputs,
        "inputs_not_read": "validation, test and negative files are hashed for integrity only; never parsed",
        "output": {
            "path": _display_path(trig_path, root),
            "sha256": hashlib.sha256(trig_bytes).hexdigest(),
            "bytes": len(trig_bytes),
            "format": "TriG (canonical subset: full IRIs, one sorted triple per line, UTF-8, LF)",
        },
        "named_graphs": {
            GRAPH_TRAIN: {"role": "asserted training triples only", "triples": len(build.graphs[GRAPH_TRAIN])},
            GRAPH_LABELS: {
                "role": "rdfs:label@en, sourceId literals, owl:NamedIndividual / owl:ObjectProperty declarations",
                "triples": len(build.graphs[GRAPH_LABELS]),
            },
            GRAPH_PROVENANCE: {"role": "source hashes, counts, converter details", "triples": len(build.graphs[GRAPH_PROVENANCE])},
        },
        "iri_scheme": {
            "entity": ENTITY_NS + "<Q-id>",
            "relation": RELATION_NS + "<P-id>",
            "vocabulary": VOCAB_NS + "<term>",
        },
        "counts": {
            "source_rows": training.row_count,
            "valid_rows_before_deduplication": training.valid_row_count,
            "malformed_rows": 0,
            "exact_duplicates_removed": len(training.duplicate_rows),
            "unique_training_triples": len(training.unique_triples),
            "entities": len(build.entity_ids),
            "relations": len(build.relation_ids),
        },
        "duplicate_rows_removed": training.duplicate_rows,
        "unmapped_entity_labels": list(build.unmapped_entity_ids),
        "unmapped_relation_labels": list(build.unmapped_relation_ids),
        "verification": verification,
        "protected_files_sha256": protected_hashes,
        "protected_files_unchanged": True,
        "policy": [
            "Built from data/train.txt and the two label maps only.",
            "Any malformed row or invalid Q/P identifier stops the build; nothing is repaired.",
            "Only identical (subject, relation, object) rows are duplicates; different relations between the same entities are kept.",
            "Labels and provenance are kept out of the training graph.",
            "No entity classes, domain/range, inverse, symmetry, transitivity, property-chain, subproperty or equivalence axioms.",
            "Existing files are never overwritten.",
            "No rule mining, inference or prediction.",
        ],
    }


def verify_existing_outputs(
    output_dir: Path = OUTPUT_DIR,
    training_path: Path = TRAIN_PATH,
    entity_labels_path: Path = ENTITY_LABELS_PATH,
    relation_labels_path: Path = RELATION_LABELS_PATH,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Read-only check of previously written outputs against the current sources."""
    trig_path = output_dir / TRIG_FILENAME
    manifest_path = output_dir / MANIFEST_FILENAME
    trig_bytes = trig_path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    build = build_dataset(training_path, entity_labels_path, relation_labels_path, root)
    result = verify_dataset(*parse_canonical_trig(trig_bytes.decode("utf-8")), build)
    if hashlib.sha256(trig_bytes).hexdigest() != manifest["output"]["sha256"]:
        raise Phase3VerificationError("TriG file hash does not match the manifest")
    if serialize_trig(build.graphs).encode("utf-8") != trig_bytes:
        raise Phase3VerificationError("a fresh rebuild does not reproduce the TriG file byte-for-byte")
    current = protected_file_hashes(root)
    changed = sorted(
        k for k in manifest["protected_files_sha256"] if current.get(k) != manifest["protected_files_sha256"][k]
    )
    if changed:
        raise Phase3VerificationError(f"protected files differ from the manifest: {changed}")
    result["manifest_hash_match"] = True
    result["byte_identical_rebuild"] = True
    result["protected_files_unchanged_since_build"] = True
    return result


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="new directory or one without Phase 3 outputs")
    parser.add_argument("--verify-only", action="store_true", help="check existing outputs without writing anything")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.verify_only:
        result = verify_existing_outputs(args.output_dir)
        print(json.dumps(result, indent=2))
        return 0
    paths = write_phase3_outputs(args.output_dir)
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
