import unittest
from pathlib import Path

from display_labels import DisplayLabels


ROOT = Path(__file__).resolve().parents[1]


class DisplayLabelsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.labels = DisplayLabels()

    def test_actual_dataset_triple_has_readable_labels(self) -> None:
        with (ROOT / "data" / "train.txt").open(encoding="utf-8") as triples:
            subject_id, relation_id, object_id = next(triples).rstrip("\n").split("\t")

        self.assertEqual(subject_id, "Q108946")
        self.assertEqual(relation_id, "P161")
        self.assertEqual(object_id, "Q39792")
        self.assertEqual(self.labels.entity_label(subject_id), "A Few Good Men")
        self.assertEqual(self.labels.relation_label(relation_id), "cast member")
        self.assertEqual(self.labels.entity_label(object_id), "Jack Nicholson")

    def test_prediction_includes_labels_and_original_ids(self) -> None:
        self.assertEqual(
            self.labels.prediction_triple("Q108946", "P161", "Q39792"),
            "A Few Good Men (Q108946) -- cast member (P161) --> "
            "Jack Nicholson (Q39792)",
        )

    def test_unknown_identifiers_fall_back_to_the_original_id(self) -> None:
        self.assertEqual(self.labels.entity_label("Q999999999"), "Q999999999")
        self.assertEqual(self.labels.relation_label("P999999999"), "P999999999")
        self.assertEqual(
            self.labels.prediction_triple("Q999999999", "P999999999", "Q108946"),
            "Q999999999 -- P999999999 --> A Few Good Men (Q108946)",
        )

    def test_mapping_covers_identifiers_in_all_local_triple_files(self) -> None:
        for triple_file in (ROOT / "data").glob("*.txt"):
            with triple_file.open(encoding="utf-8") as triples:
                for line in triples:
                    subject_id, relation_id, object_id = line.rstrip("\n").split("\t")
                    self.assertNotEqual(self.labels.entity_label(subject_id), subject_id)
                    self.assertNotEqual(self.labels.relation_label(relation_id), relation_id)
                    self.assertNotEqual(self.labels.entity_label(object_id), object_id)


if __name__ == "__main__":
    unittest.main()
