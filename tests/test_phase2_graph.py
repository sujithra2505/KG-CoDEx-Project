import json
import tempfile
import unittest
from pathlib import Path

from display_labels import DisplayLabels
from phase2_graph import load_training_graph, write_phase2_outputs


ROOT = Path(__file__).resolve().parents[1]


class Phase2GraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.labels = DisplayLabels()

    def build_from_rows(self, rows: list[str]):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        training_path = Path(temporary_directory.name) / "train.txt"
        training_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return temporary_directory, load_training_graph(training_path, self.labels)

    def test_exact_duplicates_are_removed_but_different_relations_remain(self) -> None:
        _, build = self.build_from_rows(
            [
                "Q108946\tP161\tQ39792",
                "Q108946\tP161\tQ39792",
                "Q108946\tP26\tQ39792",
            ]
        )

        self.assertEqual(build.decisions["row_count"], 3)
        self.assertEqual(build.decisions["valid_row_count_before_deduplication"], 3)
        self.assertEqual(build.decisions["exact_duplicate_count"], 1)
        self.assertEqual(len(build.unique_triples), 2)
        self.assertEqual(build.graph.number_of_edges(), 2)
        self.assertEqual(
            {key for _, _, key in build.graph.edges(keys=True)}, {"P161", "P26"}
        )

    def test_original_ids_are_graph_keys_and_labels_are_display_attributes(self) -> None:
        _, build = self.build_from_rows(["Q108946\tP161\tQ39792"])

        self.assertIn("Q108946", build.graph)
        self.assertEqual(build.graph.nodes["Q108946"]["entity_id"], "Q108946")
        self.assertEqual(build.graph.nodes["Q108946"]["label"], "A Few Good Men")
        self.assertTrue(build.graph.has_edge("Q108946", "Q39792", key="P161"))
        edge = build.graph["Q108946"]["Q39792"]["P161"]
        self.assertEqual(edge["relation_id"], "P161")
        self.assertEqual(edge["label"], "cast member")

    def test_malformed_rows_are_recorded_and_excluded(self) -> None:
        _, build = self.build_from_rows(
            [
                "Q108946\tP161\tQ39792",
                "Q108946\t\tQ39792",
                "Q108946 P161 Q39792",
            ]
        )

        self.assertEqual(build.decisions["row_count"], 3)
        self.assertEqual(build.decisions["valid_row_count_before_deduplication"], 1)
        self.assertEqual(build.decisions["malformed_row_count"], 2)
        self.assertEqual(build.graph.number_of_edges(), 1)
        self.assertEqual(
            [row["line"] for row in build.decisions["malformed_rows"]], [2, 3]
        )

    def test_every_unique_valid_triple_is_an_edge(self) -> None:
        _, build = self.build_from_rows(
            [
                "Q108946\tP161\tQ39792",
                "Q108946\tP26\tQ39792",
                "Q108946\tP161\tQ39792",
            ]
        )

        self.assertEqual(build.graph.number_of_edges(), len(build.unique_triples))
        graph_triples = {
            (subject, relation_id, object_id)
            for subject, object_id, relation_id in build.graph.edges(keys=True)
        }
        self.assertEqual(graph_triples, set(build.unique_triples))

    def test_actual_training_graph_keeps_all_valid_unique_rows(self) -> None:
        build = load_training_graph(ROOT / "data" / "train.txt", self.labels)

        self.assertEqual(build.decisions["row_count"], 185584)
        self.assertEqual(build.decisions["malformed_row_count"], 0)
        self.assertEqual(build.decisions["exact_duplicate_count"], 0)
        self.assertEqual(build.graph.number_of_nodes(), 17050)
        self.assertEqual(build.graph.number_of_edges(), 185584)
        self.assertEqual(len(build.relation_counts), 51)

    def test_visualization_and_exports_generate_successfully(self) -> None:
        temporary_directory, build = self.build_from_rows(
            [
                "Q108946\tP161\tQ39792",
                "Q1041\tP463\tQ7809",
            ]
        )
        output_dir = Path(temporary_directory.name) / "outputs"
        paths = write_phase2_outputs(build, output_dir, self.labels)

        for path in paths.values():
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 0)
        html = paths["html"].read_text(encoding="utf-8")
        self.assertIn("A Few Good Men", html)
        self.assertIn("cast member", html)
        self.assertIn("Show neighborhood", html)
        self.assertIn("Relation filter", html)
        self.assertIn("phase2Triples", html)
        statistics = json.loads(paths["statistics"].read_text(encoding="utf-8"))
        self.assertEqual(statistics["graph_edges"], 2)
        self.assertEqual(statistics["unique_valid_triples"], 2)


if __name__ == "__main__":
    unittest.main()
