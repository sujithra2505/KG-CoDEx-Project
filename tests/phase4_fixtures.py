"""Small synthetic project folders for Phase 4 tests (never touch the real data)."""

from __future__ import annotations

import builtins
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest import mock

import phase3_ontology as p3


def make_project(test: unittest.TestCase, train: list[tuple[str, str, str]], splits: dict[str, list[tuple[str, str, str]]] | None = None) -> Path:
    """Create data/ files, build the Phase 3 TriG + manifest, and return the root."""
    directory = tempfile.TemporaryDirectory()
    test.addCleanup(directory.cleanup)
    root = Path(directory.name)
    data = root / "data"
    data.mkdir()
    (data / "train.txt").write_text("".join("\t".join(t) + "\n" for t in train), encoding="utf-8")
    entities = sorted({s for s, _, _ in train} | {o for _, _, o in train})
    relations = sorted({r for _, r, _ in train})
    (data / "entity_labels.json").write_text(json.dumps({e: f"entity {e}" for e in entities}), encoding="utf-8")
    (data / "relation_labels.json").write_text(json.dumps({r: f"relation {r}" for r in relations}), encoding="utf-8")
    defaults = {
        "valid.txt": [("Q1", "P1", "Q2")],
        "valid_negatives.txt": [("Q2", "P1", "Q1")],
        "test.txt": [("Q3", "P1", "Q4")],
        "test_negatives.txt": [("Q4", "P1", "Q3")],
    }
    defaults.update(splits or {})
    for name, rows in defaults.items():
        (data / name).write_text("".join("\t".join(t) + "\n" for t in rows), encoding="utf-8")
    p3.write_phase3_outputs(
        root / "outputs" / "phase3",
        data / "train.txt",
        data / "entity_labels.json",
        data / "relation_labels.json",
        root,
    )
    return root


def mining_kwargs(root: Path) -> dict:
    return {
        "phase3_dir": root / "outputs" / "phase3",
        "train_path": root / "data" / "train.txt",
        "relation_labels_path": root / "data" / "relation_labels.json",
        "entity_labels_path": root / "data" / "entity_labels.json",
        "root": root,
    }


@contextmanager
def record_opened_files():
    """Record every path opened through builtins.open / io.open (pathlib uses io.open)."""
    opened: list[str] = []
    real_open = io.open

    def recording_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    patches = [mock.patch.object(builtins, "open", recording_open), mock.patch.object(io, "open", recording_open)]
    accessor = getattr(pathlib, "_NormalAccessor", None)  # Python <= 3.10 binds io.open here at import
    if accessor is not None and hasattr(accessor, "open"):
        patches.append(mock.patch.object(accessor, "open", staticmethod(recording_open)))
    with ExitStack() as stack:
        for patch in patches:
            stack.enter_context(patch)
        yield opened


def symmetric_fixture() -> tuple[list[tuple[str, str, str]], dict[str, list[tuple[str, str, str]]]]:
    """30 two-way P26 pairs, 7 one-way pairs, and unrelated P19 facts.

    Validation positives: the reverse of 5 one-way pairs (covered by the symmetry
    rule) and 3 P19 triples (not covered). Validation negatives: the reverse of
    the other 2 one-way pairs (covered) and 3 uncovered P26 triples.
    """
    train = []
    for i in range(30):
        a, b = f"Q{100 + 2 * i}", f"Q{101 + 2 * i}"
        train += [(a, "P26", b), (b, "P26", a)]
    one_way = [(f"Q{200 + 2 * i}", f"Q{201 + 2 * i}") for i in range(7)]
    train += [(a, "P26", b) for a, b in one_way]
    places = [f"Q{300 + i}" for i in range(25)]
    train += [(f"Q{400 + i}", "P19", places[i]) for i in range(25)]
    positives = [(b, "P26", a) for a, b in one_way[:5]] + [(f"Q{400 + i}", "P19", places[i + 1]) for i in range(3)]
    negatives = [(b, "P26", a) for a, b in one_way[5:]] + [(f"Q{400 + i}", "P26", f"Q{401 + i}") for i in range(3)]
    return train, {"valid.txt": positives, "valid_negatives.txt": negatives}
