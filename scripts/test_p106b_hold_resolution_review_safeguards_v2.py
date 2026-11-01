#!/usr/bin/env python3
"""The actual copied TASK012 rows cannot count as its unread source pairs."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_review_safeguards_v2 as safeguards
from scripts import test_p106b_hold_resolution_review_safeguards_v1 as inherited

DIRECTORY = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/root_selected_signal_counter_v2"


def review_ids(path):
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cell = line.split("|")[1].strip(" `*")
        match = re.fullmatch(r"(?:expanded_train:)?([0-9]+)", cell)
        if match:
            ids.add("expanded_train:" + match[1])
    return ids


class ExactTaskAssignment(unittest.TestCase):
    def test_actual_task12_has_the_four_source_ids_not_a_fixed_row_count(self):
        self.assertEqual(safeguards.explicit_task_ids((DIRECTORY / "TASK_012.md").read_text()),
                         {"expanded_train:537274", "expanded_train:271756", "expanded_train:487720", "expanded_train:22822"})

    def test_the_actual_copied_two_rows_do_not_belong_to_task12(self):
        task = (DIRECTORY / "TASK_012.md").read_text()
        rejected = {ident for ident in review_ids(DIRECTORY / "review_012_v2.md") if not safeguards.review_row_matches_task(ident, task)}
        self.assertEqual(rejected, {"expanded_train:115601", "expanded_train:1047633"})

    def test_the_revised_v3_has_all_four_actual_source_pairs(self):
        expected = safeguards.explicit_task_ids((DIRECTORY / "TASK_012.md").read_text())
        self.assertEqual(review_ids(DIRECTORY / "review_012_v3.md"), expected)

    def test_the_same_source_is_valid_in_its_real_previous_task(self):
        self.assertTrue(safeguards.review_row_matches_task("expanded_train:115601", (DIRECTORY / "TASK_011.md").read_text()))

    def test_another_source_with_a_shared_prefix_is_not_the_assigned_id(self):
        self.assertFalse(safeguards.review_row_matches_task("expanded_train:130", "# expanded_train:13\n"))

    def test_missing_task_ids_cannot_be_a_blanket_approval(self):
        with self.assertRaisesRegex(ValueError, "NO_EXPLICIT_SOURCE_IDS"):
            safeguards.review_row_matches_task("expanded_train:13", "# Notes\n")


if __name__ == "__main__":
    classes = [inherited.ExplicitReviewEvidence, inherited.PartialReadingViewBody, ExactTaskAssignment]
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in classes])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
