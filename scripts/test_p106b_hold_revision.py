#!/usr/bin/env python3
"""Regressions for explicit-category footer recovery and reviewed decoration."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_revision as revision
from scripts import p106b_hold_policy_v3 as policy
from scripts import test_p106b_hold_policy as original_tests
from scripts import test_p106b_hold_policy_v2 as unicode_tests
from scripts import test_p106b_hold_cache as cache_tests


class RetainedOriginalGuards(original_tests.RecoveryPolicyTests):
    def setUp(self):
        change=patch.object(original_tests,"policy",policy);change.start();self.addCleanup(change.stop)


class LiteralUnicodeGuards(unicode_tests.IndependentCounterexamples):
    def setUp(self):
        change=patch.object(unicode_tests,"policy",policy);change.start();self.addCleanup(change.stop)

    def test_categories_are_not_relabelled_as_populated_external_links(self):
        text="이 영화는 일본의 영화이다.\n외부 링크\n2017년 영화\n일본의 영화 작품\n"
        result=self.propose(text);self.assertEqual(result["decision"],"EDIT")
        self.assertEqual(result["text"],text.replace("외부 링크\n",""))

    def test_a_single_booklike_title_does_not_trigger_category_stripping(self):
        text="An article about films.\nExternal links\n2017년 영화\n"
        result=self.propose(text);self.assertEqual(result["decision"],"HOLD")
        self.assertEqual(result["text"],text)


class RetainedCacheContracts(cache_tests.RecoveryIntegration):
    def setUp(self):
        context=revision.revision();context.__enter__();self.addCleanup(context.__exit__,None,None,None)


class ReviewedDecoration(unittest.TestCase):
    def test_only_source_bound_decorative_marker_can_be_ignored(self):
        original="A complete article.\n~~~~~~~The 14 Biggest Lies\nA complete joke.\nLeave a comment\n"
        cleaned="A complete article.\nThe 14 Biggest Lies\nA complete joke.\n"
        obj=object.__new__(revision.engine.RecoveryEngine);obj.current=(dict(text=original),3)
        manual=dict(code_exception=dict(kind="DECORATIVE_TILDE_MARKERS",original_text_sha256=revision.engine.sha(original),
            decorative_lines=["~~~~~~~The 14 Biggest Lies"]))
        self.assertTrue(revision.reviewed_code_guard(obj,original,cleaned,manual))
        self.assertFalse(revision.reviewed_code_guard(obj,original,cleaned,None))
        wrong=dict(code_exception=dict(manual["code_exception"],original_text_sha256="F"*64))
        self.assertFalse(revision.reviewed_code_guard(obj,original,cleaned,wrong))

    def test_decoration_exception_does_not_relax_real_code_or_unicode(self):
        original="```py\nprint(42)\n```\n~~~~~~~A heading\nA complete body.\n"
        obj=object.__new__(revision.engine.RecoveryEngine);obj.current=(dict(text=original),3)
        manual=dict(code_exception=dict(kind="DECORATIVE_TILDE_MARKERS",original_text_sha256=revision.engine.sha(original),
            decorative_lines=["~~~~~~~A heading"]))
        changed=original.replace("~~~~~~~","").replace("42","43")
        self.assertFalse(revision.reviewed_code_guard(obj,original,changed,manual))


if __name__=="__main__":unittest.main()
