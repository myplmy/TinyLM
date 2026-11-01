#!/usr/bin/env python3
"""TASK shorthands remain exact IDs and cannot repair a hash or source anchor."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_recipe_frame_v3 as frame
from scripts import test_p106b_hold_resolution_recipe_frame_v2 as inherited


class TaskShorthandFrames(inherited.QualifiedSourceFrames):
    def test_observed_task_shorthands_resolve_only_the_matching_id(self):
        for prefix in ['TASK:expanded_train:1', 'TASK:1', 'TASK_005:1']:
            recipe = self.recipe().replace('expanded_train_1', prefix)
            canonical, proof = self.compile(recipe)
            self.assertEqual(frame.strict.apply_recipe('alpha beta', canonical, source_id='expanded_train:1')[0], 'ALPHA beta')
            self.assertEqual(proof['original_recipe_sha256'], frame.strict.sha(recipe))

    def test_a_different_numeric_tail_is_not_inferred(self):
        with self.assertRaisesRegex(ValueError, 'source ID differs'):
            self.compile(self.recipe().replace('expanded_train_1', 'TASK_005:2'))

    def test_shorthand_still_cannot_replace_an_unmatched_literal_anchor(self):
        recipe = self.recipe(before='missing source anchor').replace('expanded_train_1', 'TASK:1')
        canonical, _ = self.compile(recipe)
        with self.assertRaisesRegex(ValueError, 'exactly once'):
            frame.strict.apply_recipe('alpha beta', canonical, source_id='expanded_train:1')


if __name__ == '__main__':
    with patch.object(inherited.inherited, 'frame', frame), patch.object(inherited, 'frame', frame):
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TaskShorthandFrames))
    raise SystemExit(0 if result.wasSuccessful() else 1)
