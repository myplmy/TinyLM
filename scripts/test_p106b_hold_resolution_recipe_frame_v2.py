#!/usr/bin/env python3
"""Qualified source labels preserve hashes, literal blocks and strict failures."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_recipe_frame_v2 as frame
from scripts import test_p106b_hold_resolution_recipe_frame_v1 as inherited


class QualifiedSourceFrames(inherited.LiteralRecipeFrames):
    def test_task_prefix_with_an_exact_full_source_id_is_only_metadata(self):
        for prefix in ['TASK_001:', 'TASK_003 original:', 'TASK_006 candidate:']:
            recipe = self.recipe().replace('expanded_train_1', prefix + 'expanded_train:1')
            canonical, proof = self.compile(recipe)
            self.assertEqual(frame.strict.apply_recipe('alpha beta', canonical, source_id='expanded_train:1')[0], 'ALPHA beta')
            self.assertTrue(proof['source_task_prefix_normalized'])
            self.assertEqual(proof['original_recipe_sha256'], frame.strict.sha(recipe))

    def test_task_prefix_cannot_resolve_a_different_source_id(self):
        recipe = self.recipe().replace('expanded_train_1', 'TASK_001:expanded_train:2')
        with self.assertRaisesRegex(ValueError, 'source ID differs'):
            self.compile(recipe)

    def test_task_prefix_never_corrects_a_wrong_base_sha(self):
        recipe = self.recipe().replace('expanded_train_1', 'TASK_003 original:expanded_train:1')
        recipe = recipe.replace(frame.strict.sha('alpha beta'), '0' * 64)
        with self.assertRaisesRegex(ValueError, 'base path/hash'):
            self.compile(recipe)

    def test_an_unknown_prefix_cannot_be_silently_stripped(self):
        recipe = self.recipe().replace('expanded_train_1', 'arbitrary:expanded_train:1')
        with self.assertRaisesRegex(ValueError, 'source ID differs'):
            self.compile(recipe)


if __name__ == '__main__':
    with patch.object(inherited, 'frame', frame):
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(QualifiedSourceFrames))
    raise SystemExit(0 if result.wasSuccessful() else 1)
