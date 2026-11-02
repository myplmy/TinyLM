from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.p106b_hold_resolution_author_output_bindings_v1 import declared_txt_basename


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path("/tmp/hold_binding_fixture_v1/agents/role/group")
        self.paths = {kind: {"path": "/tmp/hold_binding_fixture_v1/inputs/expanded_train_123_" + kind + ".txt"}
                      for kind in ["original", "candidate"]}

    def bind(self, cell, status="EDIT_TEXT"):
        return declared_txt_basename(cell, "expanded_train:123", self.directory, self.paths, status)

    def test_explicit_authored_variants_remain_exact(self):
        for name in ["revision_123.txt", "expanded_train_123_revised.txt", "expanded_train_123_reviewed_task014_v1.txt"]:
            self.assertEqual(self.bind(str(self.directory / name)), name)

    def test_bare_authored_filename_uses_only_assigned_directory(self):
        self.assertEqual(self.bind("`revision_123.txt`"), "revision_123.txt")

    def test_exact_input_accepts_markdown_or_bare_filename(self):
        chosen = self.paths["candidate"]["path"]
        for cell in ["`" + chosen + "`", "[candidate](" + chosen + ")", Path(chosen).name]:
            self.assertEqual(self.bind(cell, "ADOPT_CANDIDATE"), Path(chosen).name)

    def test_same_basename_in_foreign_folder_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "EXACT_ASSIGNED_INPUT"):
            self.bind("/tmp/foreign/expanded_train_123_candidate.txt", "ADOPT_CANDIDATE")

    def test_other_role_or_input_cannot_be_authored_output(self):
        for value in ["/tmp/other_role/revision_123.txt", self.paths["candidate"]["path"]]:
            with self.assertRaisesRegex(ValueError, "ASSIGNED_DIRECTORY"):
                self.bind(value)

    def test_other_numeric_id_is_rejected(self):
        for name in ["revision_1234.txt", "revision_4123.txt", "revision_124.txt"]:
            with self.assertRaisesRegex(ValueError, "ANOTHER_SOURCE_ID"):
                self.bind(str(self.directory / name))

    def test_two_output_paths_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "MULTIPLE"):
            self.bind(str(self.directory / "revision_123.txt") + " " + str(self.directory / "expanded_train_123_revised.txt"))

    def test_non_output_cell_cannot_be_guessed(self):
        with self.assertRaisesRegex(ValueError, "NO_EXACT"):
            self.bind("candidate와 원문을 유지함")


if __name__ == "__main__":
    unittest.main()
