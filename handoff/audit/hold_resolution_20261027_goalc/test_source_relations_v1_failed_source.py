#!/usr/bin/env python3
"""Literal source links cannot gain the nonexistent fourth review mapping."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_source_relations_v1 as relations


class ExactLinkRelations(unittest.TestCase):
    def test_two_individually_present_names_do_not_prove_a_new_pair(self):
        source = "[[현재 이름]]와 옛 이름은 별도 원문이다."
        self.assertTrue(relations.ungrounded_new_link_pairs(source, "[[현재 이름|옛 이름]]"))

    def test_original_piped_target_and_display_can_be_preserved(self):
        text = "[[문서 대상|표시명]]"
        self.assertFalse(relations.ungrounded_new_link_pairs(text, text))

    def test_only_a_missing_wrapper_may_be_completed_without_changing_values(self):
        self.assertFalse(relations.ungrounded_new_link_pairs("[아프로테리아상목|아프로테리아]]", "[[아프로테리아상목|아프로테리아]]"))

    def test_another_display_value_is_not_a_wrapper_repair(self):
        self.assertTrue(relations.ungrounded_new_link_pairs("[문서|표시]]", "[[문서|새 표시]]"))

    def test_duplication_cannot_gain_more_literal_pairs_than_the_source(self):
        self.assertTrue(relations.ungrounded_new_link_pairs("[[대상|표시]]", "[[대상|표시]][[대상|표시]]"))

    def test_actual_1278318_has_three_distinct_pairs_and_no_fabricated_fourth(self):
        base = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
        manifest = json.loads((base / "root_selected_signal_counter_v2/manifest.json").read_text())
        row = next(row for row in manifest["rows"] if row["id"] == "expanded_train:1278318")
        raw = (ROOT / row["original"]["path"]).read_text(encoding="utf-8")
        actual = relations.literal_link_pairs(raw)
        for pair in [("일본 고교야구 전국대회", "선발 고교야구 대회"), ("좆망", "X망"), ("서울 우리카드 위비", "서울 우리캐피탈 드림식스")]:
            self.assertIn(pair, actual)
        self.assertNotIn(("반테린 돔 나고야", "나고야돔"), actual)
        final = base / "agents/historical_review/root_selected_signal_counter_v2/expanded_train_1278318_v4.txt"
        self.assertFalse(relations.ungrounded_new_link_pairs(raw, final.read_text(encoding="utf-8")))
        self.assertTrue(relations.ungrounded_new_link_pairs(raw, final.read_text(encoding="utf-8") + "[[반테린 돔 나고야|나고야돔]]"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
