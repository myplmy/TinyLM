#!/usr/bin/env python3
"""Source identity, literal anchors, overlaps and byte/line-ending regressions."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_text_edits as edits


def recipe(base, changes, source="expanded_train:1", selection="original"):
    head = ["# P106B_LITERAL_TEXT_EDITS_V1", "source_id: " + source, "base: " + selection,
            "base_sha256: " + edits.sha(base), "reason: 원문에서 확인한 빈 절만 분리", ""]
    for number, (before, after) in enumerate(changes, 1):
        head += ["## Change " + str(number), "ORIGINAL", edits.FENCE + "text", before,
                 edits.FENCE, "REPLACEMENT", edits.FENCE + "text", after, edits.FENCE, ""]
    return chr(10).join(head)


class LiteralEdits(unittest.TestCase):
    def test_deletion_keeps_names_values_and_original_order(self):
        base = "김가람은 작가이다.\n빈 절\n2000년 작품\n"
        text, proof = edits.apply_recipe(base, recipe(base, [("빈 절\n", "")]), source_id="expanded_train:1")
        self.assertEqual(text, "김가람은 작가이다.\n2000년 작품\n")
        self.assertEqual(proof["base_sha256"], edits.sha(base))

    def test_changed_source_or_candidate_identity_is_rejected(self):
        base = "A complete source.\n"
        data = recipe(base, [("complete", "intact")])
        for source, selection, text in [("expanded_train:2", "original", base), ("expanded_train:1", "candidate", base), ("expanded_train:1", "original", base + "x")]:
            with self.subTest(source=source, selection=selection), self.assertRaises(ValueError):
                edits.apply_recipe(text, data, source_id=source, base=selection)

    def test_nonunique_source_cannot_be_silently_replaced_everywhere(self):
        base = "Name A. Name A.\n"
        with self.assertRaises(ValueError):
            edits.apply_recipe(base, recipe(base, [("Name A", "Name B")]), source_id="expanded_train:1")

    def test_overlaps_are_not_sequentially_interpreted(self):
        base = "abcdefghi\n"
        with self.assertRaises(ValueError):
            edits.apply_recipe(base, recipe(base, [("abcde", "x"), ("defgh", "y")]), source_id="expanded_train:1")

    def test_two_replacements_use_original_positions(self):
        base = "Before. Bad field. Middle. Other bad field. After.\n"
        text, _ = edits.apply_recipe(base, recipe(base, [("Bad field. ", ""), ("Other bad field. ", "")]), source_id="expanded_train:1")
        self.assertEqual(text, "Before. Middle. After.\n")

    def test_literal_code_unicode_and_crlf_are_not_normalized(self):
        base = "Intro.\r\n```python\r\nf()\r\n```\r\nU+F900 (豈)\r\nBad\r\n"
        text, _ = edits.apply_recipe(base, recipe(base, [("Bad", "")]), source_id="expanded_train:1")
        self.assertEqual(text, base.replace("Bad", ""))

    def test_freeform_extra_text_or_empty_result_is_rejected(self):
        base = "Only body."
        with self.assertRaises(ValueError):
            edits.apply_recipe(base, recipe(base, [(base, "")]), source_id="expanded_train:1")
        with self.assertRaises(ValueError):
            edits.apply_recipe(base, recipe(base, [("Only", "One")]) + "unparsed memo", source_id="expanded_train:1")


if __name__ == "__main__":
    unittest.main()
