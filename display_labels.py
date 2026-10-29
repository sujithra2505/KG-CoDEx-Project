"""Display-only labels for CoDEx Wikidata identifiers."""

import json
from pathlib import Path


_DATA_DIR = Path(__file__).resolve().parent / "data"


def _load_labels(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as mapping_file:
        mapping = json.load(mapping_file)
    if not isinstance(mapping, dict) or not all(
        isinstance(identifier, str) and isinstance(label, str)
        for identifier, label in mapping.items()
    ):
        raise ValueError(f"Expected a JSON object of ID-to-label strings in {path}")
    return mapping


class DisplayLabels:
    """Resolve labels for rendering; callers should retain IDs for all processing."""

    def __init__(
        self,
        entity_mapping_path: Path = _DATA_DIR / "entity_labels.json",
        relation_mapping_path: Path = _DATA_DIR / "relation_labels.json",
    ) -> None:
        self._entity_labels = _load_labels(entity_mapping_path)
        self._relation_labels = _load_labels(relation_mapping_path)

    def entity_label(self, entity_id: str) -> str:
        return self._entity_labels.get(entity_id, entity_id)

    def relation_label(self, relation_id: str) -> str:
        return self._relation_labels.get(relation_id, relation_id)

    def prediction_entity(self, entity_id: str) -> str:
        label = self.entity_label(entity_id)
        return f"{label} ({entity_id})" if label != entity_id else entity_id

    def prediction_relation(self, relation_id: str) -> str:
        label = self.relation_label(relation_id)
        return f"{label} ({relation_id})" if label != relation_id else relation_id

    def prediction_triple(
        self, subject_id: str, relation_id: str, object_id: str
    ) -> str:
        return (
            f"{self.prediction_entity(subject_id)} -- "
            f"{self.prediction_relation(relation_id)} --> "
            f"{self.prediction_entity(object_id)}"
        )
