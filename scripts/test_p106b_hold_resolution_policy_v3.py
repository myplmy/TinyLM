#!/usr/bin/env python3
"""Retain all 29 draft regressions and compare old/new intro semantics."""
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v2 as old
from scripts import p106b_hold_resolution_policy_v3 as policy
from scripts import test_p106b_hold_resolution_policy_v2 as prior_tests


class RetainedDraftGuards(prior_tests.RetainedDraftGuards):
    def setUp(self):
        change = patch.object(prior_tests, "policy", policy)
        change.start()
        self.addCleanup(change.stop)
        super().setUp()


class RetainedNewSourceShapes(prior_tests.NewSourceShapes):
    def setUp(self):
        change = patch.object(prior_tests, "policy", policy)
        change.start()
        self.addCleanup(change.stop)


class IntroSemantics(unittest.TestCase):
    def test_equivalent_subject_search_over_short_adversarial_paragraphs(self):
        rng = random.Random(10627)
        pieces = ["A", "한", "은 ", "는 ", "이다.", "있다 ", "은", "는", " ", "\t", "\n", "\n\n", "《Reunion》", "단어"]
        for _ in range(1500):
            text = "".join(rng.choice(pieces) for _ in range(rng.randrange(1, 25)))
            self.assertEqual(policy.intro(text), old.intro(text), repr(text))

    def test_very_long_english_paragraph_needs_no_subject_search_restart(self):
        text = "English scientific prose without a Korean subject. " * 6000
        self.assertIsNone(policy.intro(text))

    def test_english_title_then_explicit_latin_named_korean_prose(self):
        text = "Title\n\n《Reunion》는 라이브 음반이다.\n\n곡 목록\n"
        self.assertEqual(policy.intro(text), old.intro(text))


if __name__ == "__main__":
    unittest.main()
