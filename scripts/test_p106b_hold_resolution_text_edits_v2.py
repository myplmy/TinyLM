"""Check deletion syntax and rejection of ambiguous/incomplete author edits."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_text_edits_v2 as edits
from scripts import test_p106b_hold_resolution_text_edits as original_tests


class EmptyLiteralReplacementTests(unittest.TestCase):
    def recipe(self, body, replacements):
        newline = chr(10)
        parts = ["# P106B_LITERAL_TEXT_EDITS_V1", "source_id: expanded_train:3", "base: original",
                 "base_sha256: " + edits.sha(body), "reason: 원문에서 확인한 빈 항목만 분리", ""]
        for i, (before, after) in enumerate(replacements, 1):
            parts.extend(["## Change " + str(i), "ORIGINAL", edits.FENCE + "text", before, edits.FENCE,
                          "REPLACEMENT", edits.FENCE + "text"])
            if after:
                parts.append(after)
            parts.extend([edits.FENCE, ""])
        return newline.join(parts)

    def test_adjacent_empty_fences_do_not_consume_the_next_block(self):
        body = "완결 설명. 빈항목 하나. 빈항목 둘. 완전한 서지."
        recipe = self.recipe(body, [(" 빈항목 하나.", ""), (" 빈항목 둘.", "")])
        value, proof = edits.apply_recipe(body, recipe, source_id="expanded_train:3")
        self.assertEqual(value, "완결 설명. 완전한 서지.")
        self.assertEqual(len(proof["changes"]), 2)

    def test_v1_separate_blank_line_empty_replacement_still_means_deletion(self):
        body = "독립 본문. 빈항목"
        recipe = self.recipe(body, [(" 빈항목", "")])
        recipe = recipe.replace("REPLACEMENT" + chr(10) + edits.FENCE + "text" + chr(10) + edits.FENCE,
                                "REPLACEMENT" + chr(10) + edits.FENCE + "text" + chr(10) * 2 + edits.FENCE)
        self.assertEqual(edits.apply_recipe(body, recipe, source_id="expanded_train:3")[0], "독립 본문.")

    def test_repeated_short_anchor_remains_rejected(self):
        body = "빈항목 그리고 빈항목과 독립 본문."
        with self.assertRaisesRegex(ValueError, "exactly once"):
            edits.apply_recipe(body, self.recipe(body, [("빈항목", "")]), source_id="expanded_train:3")

    def test_free_text_after_an_empty_replacement_is_rejected(self):
        body = "독립 본문. 빈항목"
        with self.assertRaises(ValueError):
            edits.apply_recipe(body, self.recipe(body, [(" 빈항목", "")]) + "임의로 나머지도 정리", source_id="expanded_train:3")


if __name__ == "__main__":
    with patch.object(original_tests, "edits", edits):
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(original_tests),
                                    unittest.defaultTestLoader.loadTestsFromTestCase(EmptyLiteralReplacementTests)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
