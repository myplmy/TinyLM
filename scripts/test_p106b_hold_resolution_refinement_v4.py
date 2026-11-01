#!/usr/bin/env python3
"""A frozen terminal cannot bypass a subsequently observed literal-hole guard."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_refinement_v4 as refinement
from scripts import test_p106b_hold_resolution_refinement_v3 as inherited


class RecheckLiteralHoles(unittest.TestCase):
    def make(self, raw, clean, raises=False):
        return inherited.RecheckChangedPreservation.make(self, raw, clean, raises=raises)

    def test_terminal_empty_name_is_sent_back_through_fresh_policy(self):
        raw = '가람은 수학자이다. 비자가 ""이라는 이름으로 발급되었다.'
        row, selector, calls, frozen = self.make(raw, raw)
        self.assertEqual(selector.propose(row)["decision"], "PENDING")
        self.assertEqual(calls, [row["id"]])
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)
        self.assertTrue(selector.last["rechecked_frozen_terminal_literal_holes"])

    def test_terminal_stray_bracket_is_not_reused(self):
        raw = "가람은 휴게소이다. 고속도로]의 시설이다."
        row, selector, calls, _ = self.make(raw, raw)
        self.assertEqual(selector.propose(row)["decision"], "PENDING")
        self.assertEqual(calls, [row["id"]])

    def test_actual_code_empty_string_remains_reusable(self):
        raw = "설명 문장.\n```python\nname = ''\nvalue = a[0]\n```\n"
        row, selector, calls, _ = self.make(raw, raw)
        self.assertEqual(selector.propose(row)["decision"], "EDIT")
        self.assertEqual(calls, [])

    def test_original_frozen_record_is_restored_on_new_policy_error(self):
        raw = '가람은 수학자이다. 비자가 ""이라는 이름으로 발급되었다.'
        row, selector, _, frozen = self.make(raw, raw, raises=True)
        with self.assertRaisesRegex(ValueError, "fresh-policy-error"):
            selector.propose(row)
        self.assertIs(selector.records[row["original_text_sha256"]], frozen)
        self.assertEqual(frozen["decision"], "EDIT")


if __name__ == "__main__":
    v3, v2, v1 = inherited, inherited.inherited, inherited.inherited.inherited
    with patch.object(v3, "refinement", refinement), patch.object(v2, "refinement", refinement), patch.object(v1, "refinement", refinement):
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromTestCase(v1.FrozenDraftTests),
            unittest.defaultTestLoader.loadTestsFromTestCase(v2.OriginalBoundaryCases),
            unittest.defaultTestLoader.loadTestsFromTestCase(v3.RecheckChangedPreservation),
            unittest.defaultTestLoader.loadTestsFromTestCase(RecheckLiteralHoles)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
