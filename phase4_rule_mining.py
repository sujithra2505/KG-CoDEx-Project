"""Phase 4B: mine candidate Horn rules from the CoDEx-M Phase 3 training graph.

The miner reads only the named graph ``urn:codexm:graph:train`` from the Phase 3
TriG file (after checking its SHA-256 against the Phase 3 manifest). It never
opens validation or test files; it only records their size and timestamp so a
later run can tell whether they changed.

Rule shapes (head is always ``h(x,z)`` with ``x != z``):

* subrelation        ``p(x,z) -> h(x,z)``            (p != h)
* inverse / symmetry ``p(z,x) -> h(x,z)``            (p == h is symmetry)
* two-atom bodies    ``p1(x,y)|p1(y,x)  &  p2(y,z)|p2(z,y)  -> h(x,z)``
  (the forward chain ``p1(x,y) & p2(y,z)`` covers transitivity when p1=p2=h)

Measures: distinct-pair support, standard confidence, PCA confidence, head
coverage, lift over the head prior, and the 95% Wilson lower bound of the PCA
confidence (the ranking key). Rules are statistical patterns found in the
training data; nothing here claims they are semantically valid.

The miner writes no inferred or predicted edges. Body pairs whose head is not
in the training data are counted, never listed.

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from array import array
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import phase3_ontology as p3


ROOT = Path(__file__).resolve().parent
TRAIN_PATH = ROOT / "data" / "train.txt"
ENTITY_LABELS_PATH = ROOT / "data" / "entity_labels.json"
RELATION_LABELS_PATH = ROOT / "data" / "relation_labels.json"
PHASE3_DIR = ROOT / "outputs" / "phase3"
OUTPUT_ROOT = ROOT / "outputs" / "phase4"
DEFAULT_RUN_NAME = "run_default"

MINER_NAME = "phase4_rule_mining.py"
MINER_VERSION = "4B.2.0"

CANDIDATES_FILE = "rule_candidates.jsonl"
SELECTED_FILE = "selected_rules.json"
REPORT_FILE = "rules_report.md"
STABILITY_FILE = "stability_check.json"
MANIFEST_FILE = "mining_manifest.json"

# Files that must not change. Split files whose facts the miner must not see are
# recorded by size and timestamp only, so the miner never opens them.
PROTECTED_FILES = (
    "DISPLAY_LABELS.md",
    "display_labels.py",
    "phase2_graph.py",
    "phase3_ontology.py",
    "tests/test_display_labels.py",
    "tests/test_phase2_graph.py",
    "tests/test_phase3_ontology.py",
    "outputs/phase1_dataset_report.md",
    "outputs/phase4/phase4_rule_mining_design.md",
)
PROTECTED_GLOBS = ("data/*", "outputs/phase2/*", "outputs/phase3/*")
STAT_ONLY_FOR_MINER = ("data/valid", "data/test")


@dataclass(frozen=True)
class MiningConfig:
    min_head_triples: int = 20
    min_support: int = 10
    min_pca_body: int = 20
    min_head_coverage: float = 0.01
    min_pca: float = 0.10
    min_lift: float = 1.5
    top_k_per_head: int = 50
    max_body_paths: int = 5_000_000
    wilson_z: float = 1.96
    hub_share: float = 0.5
    dominance_jaccard: float = 0.9
    no_gain_coverage: float = 0.9
    n_examples: int = 10
    n_counterexamples: int = 10
    n_top_middles: int = 5
    symmetric_unit: str = "unordered"  # "unordered": count swap-invariant rules per couple; "ordered": 4B.1.0 behaviour


class Phase4Error(RuntimeError):
    """Raised when inputs fail verification or outputs would be overwritten."""


# ----------------------------------------------------------------------- loading


def sha256_file(path: Path) -> str:
    return p3.sha256_file(path)


def load_training_triples(phase3_dir: Path = PHASE3_DIR, train_path: Path = TRAIN_PATH) -> tuple[list[tuple[str, str, str]], dict[str, Any]]:
    """Load ID triples from the Phase 3 training named graph only.

    Checks: TriG hash equals the Phase 3 manifest; train.txt hash equals the
    manifest input hash; the training graph has only entity-relation-entity
    triples and the expected count.
    """
    manifest_path = phase3_dir / p3.MANIFEST_FILENAME
    trig_path = phase3_dir / p3.TRIG_FILENAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trig_bytes = trig_path.read_bytes()
    trig_sha = hashlib.sha256(trig_bytes).hexdigest()
    if trig_sha != manifest["output"]["sha256"]:
        raise Phase4Error(f"{trig_path} hash {trig_sha} does not match the Phase 3 manifest")
    train_sha = sha256_file(train_path)
    if train_sha != manifest["inputs"]["training_triples"]["sha256"]:
        raise Phase4Error(f"{train_path} hash does not match the Phase 3 manifest")

    graphs, _ = p3.parse_canonical_trig(trig_bytes.decode("utf-8"))
    triples = sorted(p3.check_training_graph_purity(graphs[p3.GRAPH_TRAIN]))
    expected = manifest["counts"]["unique_training_triples"]
    if len(triples) != expected:
        raise Phase4Error(f"training graph has {len(triples)} triples, manifest says {expected}")
    info = {
        "phase3_trig": {"path": _rel(trig_path), "sha256": trig_sha},
        "phase3_manifest": {"path": _rel(manifest_path), "sha256": sha256_file(manifest_path)},
        "training_triples_file": {"path": _rel(train_path), "sha256": train_sha},
        "named_graph_used": p3.GRAPH_TRAIN,
        "training_triples": len(triples),
    }
    return triples, info


def _rel(path: Path, root: Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def split_for_stability(triples: Iterable[tuple[str, str, str]]) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """Deterministic 90/10 split: held out when SHA-256 of 's\\tr\\to' mod 10 == 0."""
    train90, held10 = [], []
    for triple in triples:
        digest = hashlib.sha256("\t".join(triple).encode("utf-8")).hexdigest()
        (held10 if int(digest, 16) % 10 == 0 else train90).append(triple)
    return train90, held10


# ------------------------------------------------------------------------- index


class KG:
    """Integer-indexed training graph. Entity integers follow sorted ID order."""

    def __init__(self, triples: Iterable[tuple[str, str, str]]) -> None:
        triples = list(triples)
        self.entities = sorted({s for s, _, _ in triples} | {o for _, _, o in triples})
        self.eid = {e: i for i, e in enumerate(self.entities)}
        self.N = len(self.entities)
        self.relations = sorted({r for _, r, _ in triples})
        self.out: dict[str, dict[int, set[int]]] = {r: defaultdict(set) for r in self.relations}
        self.inn: dict[str, dict[int, set[int]]] = {r: defaultdict(set) for r in self.relations}
        self.pairs: dict[str, set[int]] = {r: set() for r in self.relations}
        self.pair_rels: dict[int, list[str]] = defaultdict(list)
        for s, r, o in triples:
            x, z = self.eid[s], self.eid[o]
            self.out[r][x].add(z)
            self.inn[r][z].add(x)
            code = x * self.N + z
            if code not in self.pairs[r]:
                self.pairs[r].add(code)
                self.pair_rels[code].append(r)
        for r in self.relations:
            self.out[r] = dict(self.out[r])
            self.inn[r] = dict(self.inn[r])
        self.pair_rels = dict(self.pair_rels)
        self.count = {r: len(self.pairs[r]) for r in self.relations}
        self.size = sum(self.count.values())

    def has(self, s: int, r: str, o: int) -> bool:
        return r in self.pairs and (s * self.N + o) in self.pairs[r]


# ------------------------------------------------------------------------ shapes
# A body shape is ("1", p, d) or ("2", p1, d1, p2, d2).
#   1-atom: d="f" -> p(x,z);  d="b" -> p(z,x)
#   2-atom: d1="f" -> p1(x,y), "b" -> p1(y,x);  d2="f" -> p2(y,z), "b" -> p2(z,y)


def _atom_text(rel: str, a: str, b: str) -> str:
    return f"{rel}({a},{b})"


def body_atoms(shape: tuple) -> list[tuple[str, str, str]]:
    if shape[0] == "1":
        _, p, d = shape
        return [(p, "x", "z") if d == "f" else (p, "z", "x")]
    _, p1, d1, p2, d2 = shape
    return [
        (p1, "x", "y") if d1 == "f" else (p1, "y", "x"),
        (p2, "y", "z") if d2 == "f" else (p2, "z", "y"),
    ]


def rule_text(shape: tuple, head: str) -> str:
    body = " & ".join(_atom_text(*atom) for atom in body_atoms(shape))
    return f"{body} => {head}(x,z)"


def rule_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def rule_type(shape: tuple, head: str) -> str:
    if shape[0] == "1":
        _, p, d = shape
        if d == "f":
            return "subrelation"
        return "symmetry" if p == head else "inverse"
    _, p1, d1, p2, d2 = shape
    if d1 == "f" and d2 == "f":
        return "transitivity" if p1 == p2 == head else "composition_chain"
    return "composition_reversed"


def is_swap_invariant(shape: tuple, head: str) -> bool:
    """True if renaming x<->z maps the rule onto itself or its body onto itself.

    Covers symmetry rules p(z,x) => p(x,z) and bodies p(x,y) & p(z,y) or
    p(y,x) & p(y,z). For these, every couple {x,z} appears in both orders, so
    ordered counting would count the same evidence twice.
    """
    if shape[0] == "1":
        _, p, d = shape
        return d == "b" and p == head
    _, p1, d1, p2, d2 = shape
    return p1 == p2 and d1 != d2


def couple(code: int, N: int) -> int:
    """Order-free code for the pair encoded by ``code`` (x*N+z)."""
    x, z = divmod(code, N)
    return x * N + z if x < z else z * N + x


def _left(kg: KG, p1: str, d1: str) -> dict[int, set[int]]:
    """y -> {x} for the first atom."""
    return kg.inn[p1] if d1 == "f" else kg.out[p1]


def _right(kg: KG, p2: str, d2: str) -> dict[int, set[int]]:
    """y -> {z} for the second atom."""
    return kg.out[p2] if d2 == "f" else kg.inn[p2]


def _a_of_x(kg: KG, p1: str, d1: str, x: int) -> set[int]:
    """{y} reachable from x through the first atom."""
    return (kg.out[p1] if d1 == "f" else kg.inn[p1]).get(x, set())


def _b_of_z(kg: KG, p2: str, d2: str, z: int) -> set[int]:
    """{y} reachable from z through the second atom."""
    return (kg.inn[p2] if d2 == "f" else kg.out[p2]).get(z, set())


def body_path_count(kg: KG, shape: tuple) -> tuple[int, int]:
    """(paths, number of middle entities) for a 2-atom shape."""
    _, p1, d1, p2, d2 = shape
    left, right = _left(kg, p1, d1), _right(kg, p2, d2)
    mids = left.keys() & right.keys()
    return sum(len(left[y]) * len(right[y]) for y in mids), len(mids)


def body_pairs(kg: KG, shape: tuple) -> set[int]:
    """Distinct (x,z) pair codes (x*N+z, x != z) for which the body holds."""
    N = kg.N
    if shape[0] == "1":
        _, p, d = shape
        if d == "f":
            return set(kg.pairs[p])
        return {(c % N) * N + (c // N) for c in kg.pairs[p]}
    _, p1, d1, p2, d2 = shape
    left, right = _left(kg, p1, d1), _right(kg, p2, d2)
    pairs: set[int] = set()
    for y in left.keys() & right.keys():
        zs = right[y]
        for x in left[y]:
            base = x * N
            pairs.update(base + z for z in zs)
            if x in zs:
                pairs.discard(base + x)
    return pairs


def middles(kg: KG, shape: tuple, x: int, z: int) -> set[int]:
    _, p1, d1, p2, d2 = shape
    return _a_of_x(kg, p1, d1, x) & _b_of_z(kg, p2, d2, z)


def body_holds(kg: KG, shape: tuple, x: int, z: int) -> bool:
    """True if the body holds for the pair (x, z) in ``kg`` (x != z required)."""
    if x == z:
        return False
    if shape[0] == "1":
        _, p, d = shape
        return kg.has(x, p, z) if d == "f" else kg.has(z, p, x)
    return bool(middles(kg, shape, x, z))


def body_triples(kg: KG, shape: tuple, x: int, y: int | None, z: int) -> list[list[str]]:
    name = kg.entities
    binding = {"x": x, "y": y, "z": z}
    return [[name[binding[a]], rel, name[binding[b]]] for rel, a, b in body_atoms(shape)]


def iter_shapes(kg: KG, relations: list[str]):
    for p in relations:
        for d in "fb":
            yield ("1", p, d)
    for p1 in relations:
        for d1 in "fb":
            for p2 in relations:
                for d2 in "fb":
                    yield ("2", p1, d1, p2, d2)


# ---------------------------------------------------------------------- measures


def wilson_lower(k: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = k / n
    z2 = z * z
    centre = p + z2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return max(0.0, (centre - margin) / (1 + z2 / n))


@dataclass
class HeadInfo:
    relation: str
    count: int
    subjects: set[int]
    objects: set[int]
    pca_side: str  # "subject" or "object"
    prior: float


def head_infos(kg: KG, heads: list[str]) -> dict[str, HeadInfo]:
    infos = {}
    for h in heads:
        subjects, objects = set(kg.out[h]), set(kg.inn[h])
        count = kg.count[h]
        objects_per_subject = count / len(subjects)
        subjects_per_object = count / len(objects)
        side = "subject" if objects_per_subject <= subjects_per_object else "object"
        infos[h] = HeadInfo(h, count, subjects, objects, side, count / (len(subjects) * len(objects)))
    return infos


def _r(value: float) -> float:
    return round(value, 6)


# ------------------------------------------------------------------------ mining


@dataclass
class MiningResult:
    candidates: list[dict[str, Any]]
    selected: list[dict[str, Any]]
    stats: dict[str, Any]


def mine_rules(kg: KG, config: MiningConfig = MiningConfig(), relation_labels: dict[str, str] | None = None) -> MiningResult:
    labels = relation_labels or {}
    N = kg.N
    heads = [r for r in kg.relations if kg.count[r] >= config.min_head_triples]
    head_set = set(heads)
    not_mined = {r: kg.count[r] for r in kg.relations if r not in head_set}
    infos = head_infos(kg, heads)

    stats: dict[str, Any] = {
        "relations": len(kg.relations),
        "head_relations_mined": len(heads),
        "head_relations_not_mined_too_few_triples": not_mined,
        "body_shapes_total": 0,
        "body_shapes_not_joinable": 0,
        "body_shapes_evaluated": 0,
        "body_shapes_skipped_too_large": [],
        "paths_in_evaluated_shapes": 0,
        "rule_head_combinations_with_support_below_min_support": 0,
        "candidates_scored": 0,
    }
    candidates: list[dict[str, Any]] = []

    for shape in iter_shapes(kg, kg.relations):
        stats["body_shapes_total"] += 1
        if shape[0] == "2":
            paths, n_mid = body_path_count(kg, shape)
            if n_mid == 0:
                stats["body_shapes_not_joinable"] += 1
                continue
            if paths > config.max_body_paths:
                stats["body_shapes_skipped_too_large"].append(
                    {"body": " & ".join(_atom_text(*a) for a in body_atoms(shape)), "paths": paths, "middle_entities": n_mid}
                )
                continue
            stats["paths_in_evaluated_shapes"] += paths
        stats["body_shapes_evaluated"] += 1

        pairs = body_pairs(kg, shape)
        if not pairs:
            continue
        support: Counter[str] = Counter()
        for code in pairs:
            rels = kg.pair_rels.get(code)
            if rels:
                support.update(rels)
        x_counts: Counter[int] | None = None
        z_counts: Counter[int] | None = None
        body_couples: int | None = None
        for h, supp in sorted(support.items()):
            if h not in head_set:
                continue
            if shape[0] == "1" and shape[2] == "f" and shape[1] == h:
                continue  # tautology h(x,z) => h(x,z)
            if supp < config.min_support:  # unordered support can only be smaller
                stats["rule_head_combinations_with_support_below_min_support"] += 1
                continue
            info = infos[h]
            unordered = config.symmetric_unit == "unordered" and is_swap_invariant(shape, h)
            if unordered:
                support_set = kg.pairs[h] & pairs
                support_u = len({couple(c, N) for c in support_set})
                if support_u < config.min_support:
                    stats["rule_head_combinations_with_support_below_min_support"] += 1
                    continue
            if info.pca_side == "subject":
                if x_counts is None:
                    x_counts = Counter(code // N for code in pairs)
                keys, counts = info.subjects, x_counts
            else:
                if z_counts is None:
                    z_counts = Counter(code % N for code in pairs)
                keys, counts = info.objects, z_counts
            if len(keys) < len(counts):
                pca_body = sum(counts.get(k, 0) for k in keys)
            else:
                pca_body = sum(c for k, c in counts.items() if k in keys)
            ordered = {"body_size": len(pairs), "support": supp, "pca_body_size": pca_body}
            if unordered:
                if body_couples is None:
                    body_couples = len({couple(c, N) for c in pairs})
                if info.pca_side == "subject":
                    pca_couples = {couple(c, N) for c in pairs if c // N in keys}
                else:
                    pca_couples = {couple(c, N) for c in pairs if c % N in keys}
                counted = {"body_size": body_couples, "support": support_u, "pca_body_size": len(pca_couples),
                           "head_count": len({couple(c, N) for c in kg.pairs[h]}), "unit": "unordered_couples"}
            else:
                counted = dict(ordered, head_count=info.count, unit="ordered_pairs")
            cand = _candidate(shape, h, counted, ordered, info, config, labels)
            if not cand["reasons"]:
                support_set = kg.pairs[h] & pairs
                if len(support_set) != supp:
                    raise Phase4Error(f"support recount mismatch for {cand['rule']}")
                cand["_support"] = array("q", sorted(support_set))
            candidates.append(cand)
            stats["candidates_scored"] += 1

    passed = [c for c in candidates if not c["reasons"]]
    selected = _select(candidates, config)
    _attach_evidence(kg, selected, infos, config)
    for rank, rule in enumerate(selected, start=1):
        rule["global_rank"] = rank
    candidates.sort(key=lambda c: (c["head"], _rank_key(c)))
    for cand in candidates:
        cand.pop("_support", None)

    reasons = Counter(reason.split(":")[0] for c in candidates for reason in c["reasons"])
    stats.update(
        {
            "candidates_passing_thresholds": len(passed),
            "candidates_selected": len(selected),
            "rejection_reason_counts": dict(sorted(reasons.items())),
            "selected_by_type": dict(sorted(Counter(r["type"] for r in selected).items())),
            "selected_by_head": dict(sorted(Counter(r["head"] for r in selected).items())),
            "hub_dominated_selected": sum(1 for r in selected if r["flags"].get("hub_dominated")),
        }
    )
    return MiningResult(candidates, selected, stats)


def _candidate(shape, h, counted: dict[str, int], ordered: dict[str, int], info: HeadInfo, config: MiningConfig, labels) -> dict[str, Any]:
    """Scores use ``counted`` (couples for swap-invariant rules, else ordered pairs).

    Lift and the unknown-head count always use ordered pairs.
    """
    text = rule_text(shape, h)
    body_size, supp, pca_body = counted["body_size"], counted["support"], counted["pca_body_size"]
    conf = supp / body_size
    pca = supp / pca_body if pca_body else 0.0
    hc = supp / counted["head_count"]
    ordered_conf = ordered["support"] / ordered["body_size"]
    lift = ordered_conf / info.prior if info.prior else 0.0
    reasons = []
    if pca_body < config.min_pca_body:
        reasons.append(f"pca_body_below_min:{pca_body}<{config.min_pca_body}")
    if hc < config.min_head_coverage:
        reasons.append(f"head_coverage_below_min:{_r(hc)}<{config.min_head_coverage}")
    if pca < config.min_pca:
        reasons.append(f"pca_below_min:{_r(pca)}<{config.min_pca}")
    if lift < config.min_lift:
        reasons.append(f"lift_below_min:{_r(lift)}<{config.min_lift}")
    atoms = body_atoms(shape)
    display = " ∧ ".join(f"{labels.get(r, r)} [{r}]({a},{b})" for r, a, b in atoms)
    return {
        "rule_id": rule_id(text),
        "rule": text,
        "display": f"∀x,y,z: {display} → {labels.get(h, h)} [{h}](x,z)",
        "type": rule_type(shape, h),
        "length": len(atoms),
        "head": h,
        "body": [list(a) for a in atoms],
        "_shape": list(shape),
        "body_size": body_size,
        "support": supp,
        "pca_body_size": pca_body,
        "pca_side": info.pca_side,
        "head_count": counted["head_count"],
        "counting": counted["unit"],
        "ordered_counts": dict(ordered),
        "unknown_head_pairs_count": ordered["body_size"] - ordered["support"],
        "std_confidence": _r(conf),
        "pca_confidence": _r(pca),
        "head_coverage": _r(hc),
        "head_prior": _r(info.prior),
        "lift": _r(lift),
        "wilson_lower": _r(wilson_lower(supp, pca_body, config.wilson_z)),
        "status": "rejected" if reasons else "candidate",
        "reasons": reasons,
        "flags": {},
    }


def _rank_key(c: dict[str, Any]) -> tuple:
    return (-c["wilson_lower"], -c["support"], c["length"], c["rule_id"])


def _attach_evidence(kg: KG, rules: list[dict[str, Any]], infos: dict[str, HeadInfo], config: MiningConfig) -> None:
    """Examples, PCA counterexamples and middle-entity shares for selected rules."""
    N = kg.N
    names = kg.entities
    for cand in rules:
        shape = tuple(cand["_shape"])
        h = cand["head"]
        middle_counts: Counter[int] = Counter()
        examples = []
        for code in cand["_support"]:
            x, z = divmod(code, N)
            if shape[0] == "1":
                y = None
            else:
                mids = middles(kg, shape, x, z)
                if not mids:
                    raise Phase4Error(f"support pair without middle entity in {cand['rule']}")
                middle_counts.update(mids)
                y = min(mids)
            if len(examples) < config.n_examples:
                examples.append(
                    {
                        "x": names[x], "y": names[y] if y is not None else None, "z": names[z],
                        "body_triples": body_triples(kg, shape, x, y, z),
                        "head_triple": [names[x], h, names[z]],
                    }
                )
        cand["supporting_examples"] = examples
        cand["pca_counterexamples"] = _counterexamples(kg, shape, h, infos[h], config.n_counterexamples)
        top = [
            {"entity": names[y], "support_pairs": n, "share": _r(n / cand["ordered_counts"]["support"])}
            for y, n in sorted(middle_counts.items(), key=lambda item: (-item[1], item[0]))[: config.n_top_middles]
        ]
        cand["top_middle_entities"] = top
        if top and top[0]["share"] > config.hub_share:
            cand["flags"]["hub_dominated"] = top[0]["entity"]


def _counterexamples(kg: KG, shape: tuple, h: str, info: HeadInfo, limit: int) -> list[dict[str, Any]]:
    """Body holds, the PCA key entity already has some h value, but h(x,z) is absent.

    These contradict the rule under the PCA. They are not predictions.
    """
    names = kg.entities
    found: list[dict[str, Any]] = []
    if info.pca_side == "subject":
        for x in sorted(info.subjects):
            zs = _partners(kg, shape, x, from_x=True)
            zs.discard(x)
            for z in sorted(zs - kg.out[h].get(x, set())):
                found.append(_counter_record(kg, shape, h, x, z))
                if len(found) >= limit:
                    return found
    else:
        for z in sorted(info.objects):
            xs = _partners(kg, shape, z, from_x=False)
            xs.discard(z)
            for x in sorted(xs - kg.inn[h].get(z, set())):
                found.append(_counter_record(kg, shape, h, x, z))
                if len(found) >= limit:
                    return found
    return found


def _partners(kg: KG, shape: tuple, entity: int, from_x: bool) -> set[int]:
    if shape[0] == "1":
        _, p, d = shape
        if from_x:  # z with body(x, z)
            return set((kg.out[p] if d == "f" else kg.inn[p]).get(entity, ()))
        return set((kg.inn[p] if d == "f" else kg.out[p]).get(entity, ()))
    _, p1, d1, p2, d2 = shape
    result: set[int] = set()
    if from_x:
        right = _right(kg, p2, d2)
        for y in _a_of_x(kg, p1, d1, entity):
            result |= right.get(y, set())
    else:
        left = _left(kg, p1, d1)
        for y in _b_of_z(kg, p2, d2, entity):
            result |= left.get(y, set())
    return result


def _counter_record(kg: KG, shape: tuple, h: str, x: int, z: int) -> dict[str, Any]:
    names = kg.entities
    y = None if shape[0] == "1" else min(middles(kg, shape, x, z))
    return {
        "x": names[x], "y": names[y] if y is not None else None, "z": names[z],
        "body_triples": body_triples(kg, shape, x, y, z),
        "absent_head": [names[x], h, names[z]],
    }


def _select(candidates: list[dict[str, Any]], config: MiningConfig) -> list[dict[str, Any]]:
    """Greedy per-head selection: dominance, no-gain-over-shorter, top-k."""
    by_head: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cand in candidates:
        if not cand["reasons"]:
            by_head[cand["head"]].append(cand)
    selected: list[dict[str, Any]] = []
    for head in sorted(by_head):
        ranked = sorted(by_head[head], key=_rank_key)
        one_atom = [(c, set(c["_support"])) for c in ranked if c["length"] == 1]
        kept: list[tuple[dict[str, Any], set[int]]] = []
        for cand in ranked:
            s = set(cand["_support"])
            reason = None
            for other, o in kept:
                if len(s & o) / len(s | o) >= config.dominance_jaccard:
                    reason = f"redundant_with:{other['rule_id']}"
                    break
            if reason is None and cand["length"] == 2:
                for short, short_set in one_atom:
                    if short is not cand and short["wilson_lower"] >= cand["wilson_lower"] and len(s & short_set) / len(s) >= config.no_gain_coverage:
                        reason = f"no_gain_over_shorter:{short['rule_id']}"
                        break
            if reason is None and len(kept) >= config.top_k_per_head:
                reason = "beyond_top_k_per_head"
            if reason:
                cand["status"] = "rejected"
                cand["reasons"].append(reason)
            else:
                cand["status"] = "selected"
                kept.append((cand, s))
        selected.extend(c for c, _ in kept)
    texts = {c["rule"]: c["rule_id"] for c in candidates}
    for cand in candidates:
        if cand["type"] in ("inverse", "symmetry"):
            p = cand["body"][0][0]
            paired = texts.get(f"{cand['head']}(z,x) => {p}(x,z)")
            if paired and paired != cand["rule_id"]:
                cand["paired_inverse_rule_id"] = paired
    return sorted(selected, key=_rank_key)


# --------------------------------------------------------------------- stability


def stability_check(triples: list[tuple[str, str, str]], full: MiningResult, config: MiningConfig, labels) -> dict[str, Any]:
    """Mine on a 90% split and score those rules on the held-out 10% only."""
    train90, held10 = split_for_stability(triples)
    kg90 = KG(train90)
    held_set = set(held10)
    if any(t in held_set for t in train90):
        raise Phase4Error("stability split is not disjoint")
    result90 = mine_rules(kg90, config, labels)

    held_by_head: dict[str, list[tuple[int, int]]] = defaultdict(list)
    unreachable = 0
    for s, r, o in held10:
        if s in kg90.eid and o in kg90.eid:
            held_by_head[r].append((kg90.eid[s], kg90.eid[o]))
        else:
            unreachable += 1

    rules90 = []
    covered_by_head: dict[str, set[tuple[int, int]]] = defaultdict(set)
    for rule in result90.selected:
        shape = tuple(rule["_shape"])
        hits = [pair for pair in held_by_head.get(rule["head"], []) if body_holds(kg90, shape, *pair)]
        covered_by_head[rule["head"]].update(hits)
        rules90.append(
            {
                "rule_id": rule["rule_id"], "rule": rule["rule"], "head": rule["head"],
                "support_90": rule["support"], "pca_confidence_90": rule["pca_confidence"],
                "wilson_lower_90": rule["wilson_lower"],
                "held_out_hits": len(hits),
                "held_out_head_triples": len(held_by_head.get(rule["head"], [])),
                "unknown_head_pairs_90": rule["unknown_head_pairs_count"],
                "held_out_precision_lower_bound": _r(len(hits) / rule["unknown_head_pairs_count"]) if rule["unknown_head_pairs_count"] else None,
            }
        )
    scored90 = {c["rule_id"]: c for c in result90.candidates}
    selected90 = {r["rule_id"] for r in result90.selected}
    full_rules = []
    unstable = 0
    for rule in full.selected:
        other = scored90.get(rule["rule_id"])
        pca90 = other["pca_confidence"] if other else None
        is_unstable = other is None or pca90 < 0.5 * rule["pca_confidence"]
        unstable += is_unstable
        full_rules.append(
            {
                "rule_id": rule["rule_id"], "rule": rule["rule"],
                "pca_confidence_full": rule["pca_confidence"], "pca_confidence_90": pca90,
                "selected_in_90": rule["rule_id"] in selected90, "unstable": is_unstable,
            }
        )
    full_ids = {r["rule_id"] for r in full.selected}
    per_head = {
        h: {"held_out_triples": len(pairs), "covered_by_90pct_rules": len(covered_by_head.get(h, ()))}
        for h, pairs in sorted(held_by_head.items())
    }
    return {
        "split": "held out if int(sha256('s\\tr\\to'), 16) % 10 == 0; held-out triples are never used for mining",
        "train90_triples": len(train90),
        "held10_triples": len(held10),
        "held10_unreachable_entities": unreachable,
        "rules_selected_on_90": len(result90.selected),
        "rules_selected_on_full": len(full.selected),
        "selected_overlap_jaccard": _r(len(full_ids & selected90) / len(full_ids | selected90)) if full_ids | selected90 else None,
        "full_rules_unstable": unstable,
        "unstable_definition": "not scored on the 90% split, or PCA confidence on 90% below half of the full-train value",
        "held_out_coverage_by_head": per_head,
        "rules_mined_on_90pct": rules90,
        "full_rule_stability": full_rules,
    }


# ---------------------------------------------------------------- file protection


def protected_state(root: Path = ROOT, stat_only_prefixes: tuple[str, ...] = STAT_ONLY_FOR_MINER) -> dict[str, dict[str, Any]]:
    paths: set[Path] = {root / rel for rel in PROTECTED_FILES}
    for pattern in PROTECTED_GLOBS:
        paths.update(root.glob(pattern))
    state = {}
    for path in sorted(paths):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(stat_only_prefixes):
            st = os.stat(path)
            state[rel] = {"size": st.st_size, "mtime_ns": st.st_mtime_ns, "opened": False}
        else:
            state[rel] = {"sha256": sha256_file(path)}
    return state


def _write_new(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


# ----------------------------------------------------------------------- report


def render_report(result: MiningResult, stability: dict[str, Any], config: MiningConfig, inputs: dict[str, Any], entity_labels: dict[str, str]) -> str:
    s = result.stats
    lines = [
        "# Phase 4B: Rule mining results (training graph only)",
        "",
        "These rules are **statistical patterns** in the CoDEx-M training graph. A high",
        "score does not show that a rule is semantically valid. No inferred or predicted",
        "edges were produced; body pairs without a known head are counted, not listed.",
        "",
        f"Source: `{inputs['phase3_trig']['path']}` (named graph `{inputs['named_graph_used']}`,",
        f"SHA-256 `{inputs['phase3_trig']['sha256']}`), {inputs['training_triples']:,} training triples.",
        f"Miner: `{MINER_NAME}` {MINER_VERSION}.",
        "",
        "## Thresholds",
        "",
        "| Setting | Value |",
        "|---|---|",
    ]
    lines += [f"| `{k}` | {v} |" for k, v in asdict(config).items()]
    lines += [
        "",
        "## Counting",
        "",
        f"`symmetric_unit = {config.symmetric_unit}`. With `unordered`, rules that read the same after swapping x and z",
        "(symmetry rules `p(z,x) => p(x,z)` and bodies `p(x,y) & p(z,y)` / `p(y,x) & p(y,z)`) are counted per couple {x,z}:",
        "body, support, PCA body and head count are numbers of couples, and confidence, PCA confidence, head coverage,",
        "Wilson bound and the support/PCA-body thresholds use them. All other rules use ordered pairs. Lift and",
        "`unknown_head_pairs_count` always use ordered pairs; each rule also keeps `ordered_counts`.",
        "",
        "## Search summary",
        "",
        f"- Head relations mined: {s['head_relations_mined']} of {s['relations']}",
        f"- Not mined (fewer than {config.min_head_triples} triples): "
        + ", ".join(f"{r} ({n})" for r, n in s["head_relations_not_mined_too_few_triples"].items()),
        f"- Body shapes: {s['body_shapes_total']:,} total, {s['body_shapes_not_joinable']:,} not joinable, "
        f"{s['body_shapes_evaluated']:,} evaluated, {len(s['body_shapes_skipped_too_large'])} skipped as too large",
        f"- Rule/head combinations below `min_support`: {s['rule_head_combinations_with_support_below_min_support']:,}",
        f"- Candidates scored (support ≥ {config.min_support}): {s['candidates_scored']:,}",
        f"- Passed all thresholds: {s['candidates_passing_thresholds']:,}",
        f"- Selected: {s['candidates_selected']:,} (hub-dominated: {s['hub_dominated_selected']})",
        "",
        "Rejection reasons (a candidate can have several):",
        "",
    ]
    lines += [f"- `{k}`: {v:,}" for k, v in s["rejection_reason_counts"].items()]
    lines += ["", "Selected rules by type:", ""]
    lines += [f"- {k}: {v}" for k, v in s["selected_by_type"].items()]
    lines += ["", "### Skipped body shapes (over `max_body_paths`)", "", "| Body | Paths | Middle entities |", "|---|---:|---:|"]
    lines += [f"| `{b['body']}` | {b['paths']:,} | {b['middle_entities']:,} |" for b in s["body_shapes_skipped_too_large"]]
    lines += [
        "",
        "## Stability check (90/10 split of training)",
        "",
    ]
    if stability.get("skipped"):
        lines += ["Skipped for this run (`--no-stability`).", ""]
    else:
        lines += [
        f"- 90% part: {stability['train90_triples']:,} triples; held-out 10%: {stability['held10_triples']:,} "
        f"({stability['held10_unreachable_entities']:,} with an entity absent from the 90% part)",
        f"- Rules selected on 90%: {stability['rules_selected_on_90']:,}; on full training: {stability['rules_selected_on_full']:,}; "
        f"overlap (Jaccard): {stability['selected_overlap_jaccard']}",
        f"- Full-train rules flagged unstable: {stability['full_rules_unstable']:,} ({stability['unstable_definition']})",
        "",
        ]
    lines += [
        "## Top 50 selected rules (global rank)",
        "",
        "| # | Rule | Type | Supp | PCA body | PCA conf | Std conf | HC | Lift | Wilson | Flags |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rule in result.selected[:50]:
        flag = f"hub {rule['flags']['hub_dominated']}" if rule["flags"].get("hub_dominated") else ""
        lines.append(
            f"| {rule['global_rank']} | {rule['display']} | {rule['type']} | {rule['support']:,} | {rule['pca_body_size']:,} | "
            f"{rule['pca_confidence']:.3f} | {rule['std_confidence']:.3f} | {rule['head_coverage']:.3f} | {rule['lift']:.1f} | "
            f"{rule['wilson_lower']:.3f} | {flag} |"
        )
    lines += ["", "## Example evidence for the top 10 rules", ""]
    for rule in result.selected[:10]:
        lines.append(f"**{rule['global_rank']}. `{rule['rule']}`**")
        for ex in rule["supporting_examples"][:2]:
            body = "; ".join(f"{entity_labels.get(a, a)} —{r}→ {entity_labels.get(b, b)}" for a, r, b in ex["body_triples"])
            head = ex["head_triple"]
            lines.append(f"- supports: {body} ⇒ {entity_labels.get(head[0], head[0])} —{head[1]}→ {entity_labels.get(head[2], head[2])}")
        for ce in rule["pca_counterexamples"][:1]:
            head = ce["absent_head"]
            lines.append(f"- counterexample: body holds, but `{head[0]} {head[1]} {head[2]}` is absent while {head[0]} has another {head[1]} value")
        lines.append("")
    lines += [
        "## Limitations",
        "",
        "- Statistical co-occurrence only; no entity types, so rules can fire on unsuitable entities.",
        "- Open world: missing triples are unknown. PCA is a heuristic and is weak for many-valued heads such as P106.",
        "- Hubs (for example Q30) can make patterns look strong; see `top_middle_entities` and the hub flag.",
        "- Two-atom bodies only, no constants; skipped shapes are listed above.",
        "- Validation scoring is a separate step (`phase4_rule_evaluation.py`); test files are not used in Phase 4.",
        "",
        "Full data: `selected_rules.json`, `rule_candidates.jsonl`, `stability_check.json`, `mining_manifest.json`.",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------- pipeline


def _public(rule: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in rule.items() if not k.startswith("_")}


def run_mining(
    run_dir: Path,
    config: MiningConfig = MiningConfig(),
    phase3_dir: Path = PHASE3_DIR,
    train_path: Path = TRAIN_PATH,
    relation_labels_path: Path = RELATION_LABELS_PATH,
    entity_labels_path: Path = ENTITY_LABELS_PATH,
    root: Path = ROOT,
    with_stability: bool = True,
) -> dict[str, Path]:
    """Mine rules into a new run directory. Never overwrites."""
    if run_dir.exists():
        raise FileExistsError(f"Refusing to reuse existing run directory {run_dir}; choose a new --run-name")
    started = time.time()
    state_before = protected_state(root)
    triples, inputs = load_training_triples(phase3_dir, train_path)
    relation_labels = p3.load_label_map(relation_labels_path)
    entity_labels = p3.load_label_map(entity_labels_path)

    result = mine_rules(KG(triples), config, relation_labels)
    stability = stability_check(triples, result, config, relation_labels) if with_stability else {"skipped": True}
    if with_stability:
        stab = {r["rule_id"]: r for r in stability["full_rule_stability"]}
        for rule in result.selected:
            rule["flags"]["unstable_on_90pct"] = stab[rule["rule_id"]]["unstable"]

    candidates_text = "".join(json.dumps(_public(c), ensure_ascii=False, sort_keys=True) + "\n" for c in result.candidates)
    selected_doc = {
        "miner": MINER_NAME,
        "miner_version": MINER_VERSION,
        "training_snapshot": inputs,
        "config": asdict(config),
        "note": "Statistical patterns from training data only; not semantic validity claims; no predictions.",
        "rules": [_public(r) for r in result.selected],
    }
    selected_text = _json(selected_doc)
    stability_text = _json(stability)
    report_text = render_report(result, stability, config, inputs, entity_labels)

    state_after = protected_state(root)
    if state_after != state_before:
        changed = sorted(k for k in state_before.keys() | state_after.keys() if state_before.get(k) != state_after.get(k))
        raise Phase4Error(f"protected files changed during mining: {changed}")

    manifest = {
        "phase": "4B",
        "miner": MINER_NAME,
        "miner_version": MINER_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "runtime_seconds": round(time.time() - started, 1),
        "run_dir": _rel(run_dir, root),
        "inputs": inputs,
        "files_not_opened": "data/valid*, data/test* (size and mtime recorded only)",
        "config": asdict(config),
        "stats": result.stats,
        "outputs": {
            CANDIDATES_FILE: hashlib.sha256(candidates_text.encode("utf-8")).hexdigest(),
            SELECTED_FILE: hashlib.sha256(selected_text.encode("utf-8")).hexdigest(),
            STABILITY_FILE: hashlib.sha256(stability_text.encode("utf-8")).hexdigest(),
            REPORT_FILE: hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
        },
        "protected_files": state_before,
        "protected_files_unchanged": True,
        "predictions_written": False,
    }

    run_dir.mkdir(parents=True, exist_ok=False)
    paths = {
        "candidates": run_dir / CANDIDATES_FILE,
        "selected": run_dir / SELECTED_FILE,
        "stability": run_dir / STABILITY_FILE,
        "report": run_dir / REPORT_FILE,
        "manifest": run_dir / MANIFEST_FILE,
    }
    _write_new(paths["candidates"], candidates_text)
    _write_new(paths["selected"], selected_text)
    _write_new(paths["stability"], stability_text)
    _write_new(paths["report"], report_text)
    _write_new(paths["manifest"], _json(manifest))
    return paths


def config_from_args(args: argparse.Namespace) -> MiningConfig:
    fields = asdict(MiningConfig())
    return MiningConfig(**{k: getattr(args, k) for k in fields})


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME, help="new folder under outputs/phase4/")
    parser.add_argument("--no-stability", action="store_true", help="skip the 90/10 stability check")
    for name, default in asdict(MiningConfig()).items():
        parser.add_argument(f"--{name.replace('_', '-')}", dest=name, type=type(default), default=default)
    args = parser.parse_args(list(argv) if argv is not None else None)
    paths = run_mining(OUTPUT_ROOT / args.run_name, config_from_args(args), with_stability=not args.no_stability)
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
