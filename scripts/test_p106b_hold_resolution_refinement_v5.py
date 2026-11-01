#!/usr/bin/env python3
"""A terminal replay must recheck newly observed source-context holes."""
from contextlib import contextmanager
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_refinement_v5 as refinement
from scripts import test_p106b_hold_resolution_refinement_v4 as inherited


@contextmanager
def fake_replay(*args):
    yield None


class NewContextHoleReplay(unittest.TestCase):
    def check_fresh(self, raw):
        with patch.object(refinement.previous, "refinement", fake_replay):
            with refinement.refinement(None, "old", refinement.policy, []):
                with patch.object(inherited.inherited, "refinement", refinement.previous):
                    row, selector, calls, frozen = inherited.inherited.RecheckChangedPreservation.make(self, raw, raw)
                    result = selector.propose(row)
                    self.assertEqual(result["decision"], "PENDING")
                    self.assertEqual(calls, [row["id"]])
                    self.assertIs(selector.records[row["original_text_sha256"]], frozen)

    def test_same_year_different_birth_day_is_freshly_rechecked(self):
        self.check_fresh("가람(1989.6.17~)는 일본의 작가이다.\n\n생년월일은 1989년 6월 7일이다.\n")

    def test_same_year_different_death_day_is_freshly_rechecked(self):
        self.check_fresh("가람(1928년 11월 20일 ~ 2010년 3월 16일)은 대한민국의 기업인이다.\n\n사망\n2010년 3월 18일 병원에서 타계하였다.\n")

    def test_newly_observed_family_hole_is_freshly_rechecked(self):
        self.check_fresh("가람은 대한민국의 정치인이다.\n\n가족\n부인:\n차남:\n딸: ?(1937년 - )\n")

    def test_announced_missing_quotation_is_freshly_rechecked(self):
        self.check_fresh("가람은 대한민국의 작가이다.\n\n구니는 이렇게 말한다.\n\n이 말은 오싱에게 영향을 준다.\n")

    def test_proven_empty_footer_is_not_reused_under_an_old_terminal_label(self):
        self.check_fresh("가람은 대한민국의 작가이다.\n\n각주\n \n\n \n1900년 출생\n1980년 사망\n김해 김씨\n")

    def test_context_restores_the_frozen_policy_on_exception(self):
        before = refinement.previous.policy
        with patch.object(refinement.previous, "refinement", fake_replay):
            with self.assertRaisesRegex(ValueError, "context-end"):
                with refinement.refinement(None, "old", refinement.policy, []):
                    self.assertIs(refinement.previous.policy, refinement.policy)
                    raise ValueError("context-end")
        self.assertIs(refinement.previous.policy, before)


if __name__ == "__main__":
    v4, v3 = inherited, inherited.inherited
    v2, v1 = v3.inherited, v3.inherited.inherited
    with patch.object(refinement.previous, "policy", refinement.policy), \
            patch.object(v3, "refinement", refinement.previous), \
            patch.object(v2, "refinement", refinement.previous), \
            patch.object(v1, "refinement", refinement.previous):
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromTestCase(v1.FrozenDraftTests),
            unittest.defaultTestLoader.loadTestsFromTestCase(v2.OriginalBoundaryCases),
            unittest.defaultTestLoader.loadTestsFromTestCase(v3.RecheckChangedPreservation),
            unittest.defaultTestLoader.loadTestsFromTestCase(v4.RecheckLiteralHoles),
            unittest.defaultTestLoader.loadTestsFromTestCase(NewContextHoleReplay)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
