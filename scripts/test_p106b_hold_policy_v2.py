#!/usr/bin/env python3
"""Independent-review regressions: Unicode examples, missing units and widgets."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_policy as old
from scripts import p106b_hold_policy_v2 as policy
from scripts import test_p106b_hold_policy as original_tests


class RetainedGuards(original_tests.RecoveryPolicyTests):
    def setUp(self):
        change=patch.object(original_tests,"policy",policy);change.start();self.addCleanup(change.stop)


class IndependentCounterexamples(unittest.TestCase):
    def propose(self,text):
        return policy.propose(dict(id="expanded_train:0",text=text,complete_eos=True,valid_utf8=True),dict(reasons=[]))

    def test_compatibility_codepoint_examples_and_nfd_are_literal(self):
        text="문자 코드 설명이다. U+FA2E(郞), U+FA2F(隷), U+FAD4(䀹). e\u0301.\n각주\n"
        result=self.propose(text)
        self.assertEqual(result["decision"],"EDIT")
        self.assertEqual(result["text"],text.removesuffix("각주\n"))
        self.assertTrue(policy.unicode_examples_preserved(text,result["text"]))

    def test_old_engine_bindings_are_restored(self):
        before=(old.normalize_outside_code,old.LABELS)
        self.propose("완결된 설명이다.\n각주\n")
        self.assertEqual((old.normalize_outside_code,old.LABELS),before)

    def test_missing_scientific_quantities_are_not_admitted(self):
        result=self.propose("A star cluster is described.\nIts electron densities – cm and pressures – K cm.\n")
        self.assertEqual(result["decision"],"HOLD")
        self.assertIn("MISSING_QUANTITY_IN_SCIENTIFIC_STATEMENT",result["reasons"])

    def test_categories_are_not_relabelled_as_populated_external_links(self):
        text="이 영화는 일본의 영화이다.\n외부 링크\n2017년 영화\n일본의 영화 작품\n"
        result=self.propose(text);self.assertEqual(result["decision"],"HOLD")
        self.assertEqual(result["text"],text)

    def test_complete_bibliography_and_real_link_stay_intact(self):
        text="An article about films.\nReferences\nSmith (2017). A film history.\nExternal links\nhttps://example.org/film\n"
        self.assertEqual(self.propose(text)["text"],text)
        self.assertEqual(self.propose(text)["decision"],"KEEP")

    def test_broken_stub_is_removed_without_touching_prose_or_citation(self):
        text="A beaver is described.\nSmith (2001).\nThis species stub needs .\n"
        result=self.propose(text);self.assertEqual(result["decision"],"EDIT")
        self.assertEqual(result["text"],"A beaver is described.\nSmith (2001).\n")

    def test_observed_ui_is_held_while_literal_technical_example_is_kept(self):
        result=self.propose("A dictionary definition.\nSelect another language:\n")
        self.assertEqual(result["decision"],"HOLD")
        result=self.propose('Example.\n```txt\nSelect another language:\n```\n')
        self.assertEqual(result["decision"],"KEEP")

    def test_birth_conflict_is_not_fact_corrected(self):
        text="홍길동(, 1992년 1월 31일 ~ )은 축구 선수이다.\n1991년 출생\n"
        result=self.propose(text);self.assertEqual(result["decision"],"HOLD")
        self.assertEqual(result["text"],text)


if __name__=="__main__":unittest.main()
