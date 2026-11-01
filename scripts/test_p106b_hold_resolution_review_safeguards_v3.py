"""Copied old TASK rows still fail; the actual structural TASK is explicit."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards
from scripts import test_p106b_hold_resolution_review_safeguards_v2 as inherited


class StructuralTaskLayout(unittest.TestCase):
    def test_actual_structural_task_binds_only_its_source(self):
        path = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/policy_v23_structural_counter_v1/TASK_001.md"
        raw = path.read_text(encoding="utf-8")
        self.assertEqual(safeguards.explicit_task_ids(raw), {"expanded_train:827"})
        self.assertFalse(safeguards.review_row_matches_task("expanded_train:82", raw))

    def test_an_id_in_arbitrary_notes_is_not_a_task_declaration(self):
        for raw in ["# Notes\nexpanded_train:827\nSTART_HERE\n",
                    "discussion\n# TASK_001\nexpanded_train:827\nSTART_HERE\n",
                    "# TASK_001\nsome notes expanded_train:827\nSTART_HERE\n"]:
            with self.assertRaisesRegex(ValueError, "NO_EXPLICIT_SOURCE_IDS"):
                safeguards.explicit_task_ids(raw)


if __name__ == "__main__":
    classes = [inherited.inherited.ExplicitReviewEvidence, inherited.inherited.PartialReadingViewBody,
               inherited.ExactTaskAssignment, StructuralTaskLayout]
    with patch.object(inherited, "safeguards", safeguards):
        result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in classes))
    raise SystemExit(0 if result.wasSuccessful() else 1)
