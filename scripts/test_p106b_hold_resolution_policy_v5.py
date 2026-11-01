#!/usr/bin/env python3
"""Metadata-prefix and real-reference counterexamples plus 44 prior guards."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v5 as policy
from scripts import test_p106b_hold_resolution_policy_v4 as prior_tests


class RetainedOriginal(prior_tests.RetainedDraftGuards):
    def setUp(self):
        first = patch.object(prior_tests.prior_tests, "policy", policy)
        first.start()
        self.addCleanup(first.stop)
        # The inherited setUp would repatch this symbol to v4. Its only effect
        # is that binding, so bind the original test module directly instead.
        second = patch.object(prior_tests.prior_tests.prior_tests, "policy", policy)
        second.start()
        self.addCleanup(second.stop)


class RetainedV2(prior_tests.RetainedV2Boundaries):
    def setUp(self):
        change = patch.object(prior_tests.prior_tests, "policy", policy)
        change.start()
        self.addCleanup(change.stop)


class RetainedV4(prior_tests.SourceContexts):
    def setUp(self):
        change = patch.object(prior_tests, "policy", policy)
        change.start()
        self.addCleanup(change.stop)


class MetadataStart(unittest.TestCase):
    def propose(self, text):
        return policy.propose(dict(id="expanded_train:1", text=text, complete_eos=True, valid_utf8=True))

    def test_unknown_nominal_suffix_after_explicit_birth_and_alive_is_preserved(self):
        text = "김가람은 축구 선수이다.\n외부 링크\n1983년 출생\n살아있는 사람\n남자 축구 측면 미드필더\n알려지지 않은 분류 표현\n"
        result = self.propose(text)
        self.assertEqual(result["decision"], "EDIT")
        self.assertEqual(result["text"], text.replace("외부 링크\n", ""))

    def test_unknown_named_reference_before_anchor_cannot_be_consumed(self):
        text = "김가람은 축구 선수이다.\n외부 링크\n김가람 자료 모음\n1983년 출생\n살아있는 사람\n"
        result = self.propose(text)
        self.assertIn("외부 링크", result.get("candidate", result["text"]))
        self.assertIn("김가람 자료 모음", result.get("candidate", result["text"]))

    def test_actual_korean_profile_and_all_metadata_words_survive(self):
        text = "김가람은 사격 선수이다.\n외부 링크\n김가람 프로필 - ISSF\n1976년 출생\n살아있는 사람\n낯선 메타데이터\n"
        result = self.propose(text)
        self.assertEqual(result["text"], text)

    def test_known_categories_before_first_anchor_can_establish_the_same_tail(self):
        text = "김가람은 야구 선수다.\n각주\n대한민국의 야구 선수\n1962년 출생\n살아있는 사람\n다른 분류의 원문\n"
        result = self.propose(text)
        self.assertEqual(result["text"], text.replace("각주\n", ""))


if __name__ == "__main__":
    unittest.main()
