"""Counterexamples for the source-layout candidate proof."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import p106b_hold_resolution_repeat_context_v1 as context

A = "This complete source paragraph gives a specific account of the first separate record and preserves its named subject."
B = "This different source paragraph gives another independently complete account of the second record with a different subject."


def pair(label, first=A, second=B):
    return label + "\n\n" + first + "\n\n" + label + "\n\n" + second


class SourceContextProof(unittest.TestCase):
    def test_explicit_heading(self):
        self.assertIsNotNone(context.prove(pair("## Research history")))

    def test_isolated_short_heading(self):
        result = context.prove(pair("Research history"))
        self.assertIsNotNone(result)
        self.assertFalse(result["text_modified"])

    def test_named_byline(self):
        result = context.prove(pair("By Jane Example"))
        self.assertEqual(result["records"][0]["role"], "TYPED_NAMED_BYLINE")

    def test_transport_by_car_is_not_a_named_byline(self):
        self.assertFalse(context.typed_byline("By car"))
        self.assertIsNone(context.prove(pair("by car")))

    def test_single_word_capital_is_not_a_byline(self):
        self.assertFalse(context.typed_byline("By Bike"))

    def test_identical_following_paragraphs_rejected(self):
        self.assertIsNone(context.prove(pair("Research history", A, A)))

    def test_missing_following_body_rejected(self):
        self.assertIsNone(context.prove("Research history\n\nResearch history"))

    def test_advertising_navigation_rejected(self):
        self.assertIsNone(context.prove(pair("Back to Top")))
        self.assertIsNone(context.prove(pair("By Jane Example Read More")))

    def test_unbound_formal_pointer_rejected(self):
        self.assertIsNone(context.prove(pair("임의의 에 대하여,")))

    def test_quoted_refrain_context_rejected(self):
        text = "The following poem contains this refrain.\n\n" + pair("Research history")
        self.assertIsNone(context.prove(text))

    def test_code_contents_not_heading_evidence(self):
        text = "```text\n" + pair("Research history") + "\n```"
        self.assertIsNone(context.prove(text))

    def test_one_unproved_repeat_blocks_whole_source(self):
        text = pair("Research history") + "\n\nunknown = value;\nunknown = value;"
        self.assertIsNone(context.prove(text))

    def test_heading_embedded_in_prose_is_not_isolated(self):
        self.assertIsNone(context.prove("Before.\nResearch history\n" + A + "\nResearch history\n" + B))

    def test_no_repeat_does_not_clear_other_reasons(self):
        self.assertIsNone(context.prove("Only one complete independent paragraph occurs here."))


if __name__ == "__main__":
    unittest.main()
