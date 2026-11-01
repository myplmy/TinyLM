#!/usr/bin/env python3
"""A newer unread decision cannot revive an older body; a view is not a doc."""
from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_review_safeguards_v1 as safeguards


class ExplicitReviewEvidence(unittest.TestCase):
    def test_actual_unparsed_bold_review_is_a_missing_evidence_signal(self):
        path = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_hangul/repeat_context_counter_v1/review_001_v2.md"
        self.assertEqual(safeguards.unparsed_declared_review_ids(path.read_bytes(), set(), {"expanded_train:306600"}), {"expanded_train:306600"})

    def test_the_newer_canonical_review_has_actual_parsed_evidence(self):
        text = "# ID 306600\n| expanded_train:306600 | REVISE_TEXT | read | new.txt | reason |"
        self.assertFalse(safeguards.unparsed_declared_review_ids(text, {"expanded_train:306600"}, {"expanded_train:306600"}))

    def test_an_incidental_prose_id_is_not_a_declared_decision(self):
        text = "The earlier expanded_train:306600 explains the context.\nREVISE_TEXT\n"
        self.assertFalse(safeguards.unparsed_declared_review_ids(text, set(), {"expanded_train:306600"}))

    def test_another_cohort_id_and_a_question_without_a_decision_are_ignored(self):
        self.assertFalse(safeguards.unparsed_declared_review_ids("# ID 12\nREVISE_TEXT", set(), {"expanded_train:13"}))
        self.assertFalse(safeguards.unparsed_declared_review_ids("# ID 13\nQuestion?", set(), {"expanded_train:13"}))

    def test_a_declared_table_row_not_parsed_cannot_fall_back(self):
        self.assertEqual(safeguards.unparsed_declared_review_ids("| expanded_train:13 | REVISE_TEXT | x |", set(), {"expanded_train:13"}), {"expanded_train:13"})


class PartialReadingViewBody(unittest.TestCase):
    def manifest(self):
        return {"rows": [{"id": "expanded_train:13", "views": {"original": [
            {"sha256": "A", "source_characters": [0, 6000]},
            {"sha256": "B", "source_characters": [6000, 9000]}], "candidate": [
            {"sha256": "C", "source_characters": [0, 6000]},
            {"sha256": "D", "source_characters": [6000, 8000]}]}}]}

    def test_prefix_middle_or_suffix_window_cannot_be_a_full_body(self):
        for key in "ABCD":
            self.assertEqual(len(safeguards.partial_reading_view_collisions("expanded_train:13", key, self.manifest())), 1)

    def test_another_source_and_a_different_short_body_are_not_flagged(self):
        self.assertFalse(safeguards.partial_reading_view_collisions("expanded_train:14", "A", self.manifest()))
        self.assertFalse(safeguards.partial_reading_view_collisions("expanded_train:13", "E", self.manifest()))

    def test_a_single_view_already_covering_the_whole_input_is_valid(self):
        data = self.manifest()
        data["rows"][0]["views"] = {"original": [{"sha256": "A", "source_characters": [0, 9000]}]}
        self.assertFalse(safeguards.partial_reading_view_collisions("expanded_train:13", "A", data))

    def test_actual_failed_32474_window_is_rejected_and_regenerated_full_body_is_not(self):
        base = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
        data = json.loads((base / "root_selected_signal_counter_v2/reading_views_manifest_v1.json").read_text())
        directory = base / "agents/context_hangul/root_selected_signal_counter_v2"
        key = lambda path: hashlib.sha256(path.read_bytes()).hexdigest().upper()
        self.assertTrue(safeguards.partial_reading_view_collisions("expanded_train:32474", key(directory / "expanded_train_32474_v2.txt"), data))
        self.assertFalse(safeguards.partial_reading_view_collisions("expanded_train:32474", key(directory / "expanded_train_32474_v4.txt"), data))


if __name__ == "__main__":
    unittest.main(verbosity=2)
