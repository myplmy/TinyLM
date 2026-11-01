#!/usr/bin/env python3
"""Framing normalization preserves every authored character and strict gate."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_recipe_frame_v1 as frame


class LiteralRecipeFrames(unittest.TestCase):
    def recipe(self, before="alpha", after="ALPHA", number=3):
        return chr(10).join(["# Strict literal edit recipe", "", "source_id: expanded_train_1",
            "base: /workspace/source.txt", "base_sha256: " + frame.strict.sha("alpha beta"), "reason: exact authored edit", "",
            "## Change " + str(number), "ORIGINAL", frame.FENCE, before, frame.FENCE, "REPLACEMENT", frame.FENCE, after, frame.FENCE, ""])

    def compile(self, recipe):
        info = {"path": "source.txt", "sha256": frame.strict.sha("alpha beta")}
        return frame.canonicalize(recipe, source_id="expanded_train:1", paths={"original": info, "candidate": info}, root=Path("/workspace"))

    def test_metadata_and_change_gap_compile_without_changing_literals(self):
        canonical, proof = self.compile(self.recipe())
        text, _ = frame.strict.apply_recipe("alpha beta", canonical, source_id="expanded_train:1")
        self.assertEqual(text, "ALPHA beta")
        self.assertEqual(proof["authored_change_numbers"], [3])
        self.assertTrue(proof["literal_strings_unchanged"])
        self.assertFalse(proof["root_approved"])

    def test_explicit_empty_fence_pair_remains_an_empty_replacement(self):
        canonical, _ = self.compile(self.recipe(after=""))
        self.assertEqual(frame.strict.apply_recipe("alpha beta", canonical, source_id="expanded_train:1")[0], " beta")

    def test_wrong_hash_is_not_replaced_from_the_task(self):
        bad = self.recipe().replace(frame.strict.sha("alpha beta"), "0" * 64)
        with self.assertRaisesRegex(ValueError, "base path/hash"):
            self.compile(bad)

    def test_another_source_id_is_not_inferred(self):
        with self.assertRaisesRegex(ValueError, "source ID differs"):
            self.compile(self.recipe().replace("expanded_train_1", "expanded_train_2"))

    def test_a_single_fence_does_not_mean_an_inferred_empty_replacement(self):
        broken = self.recipe(after="").rsplit(frame.FENCE, 1)[0]
        with self.assertRaisesRegex(ValueError, "closing fence missing"):
            self.compile(broken)

    def test_missing_literal_source_anchor_is_still_rejected(self):
        canonical, _ = self.compile(self.recipe(before="not in the source"))
        with self.assertRaisesRegex(ValueError, "exactly once"):
            frame.strict.apply_recipe("alpha beta", canonical, source_id="expanded_train:1")

    def test_multiple_occurrences_are_not_fuzzily_selected(self):
        canonical, _ = self.compile(self.recipe(before="a"))
        with self.assertRaisesRegex(ValueError, "exactly once"):
            frame.strict.apply_recipe("alpha beta", canonical, source_id="expanded_train:1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
