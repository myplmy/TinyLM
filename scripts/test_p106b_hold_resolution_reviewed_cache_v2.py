#!/usr/bin/env python3
"""Additional pairs cannot change baseline guards or cache roster semantics."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_reviewed_cache_v2 as reviewed
from scripts import test_p106b_hold_resolution_reviewed_cache_v1 as inherited


class AdditionalCacheBoundaries(unittest.TestCase):
    def test_additional_registry_and_both_helper_versions_are_pinned(self):
        cases = reviewed.literal.load_registry()
        pins = reviewed.input_pins(cases)
        for path in [reviewed.literal.REGISTRY, reviewed.literal.ADDITIONAL_REGISTRY,
                     'scripts/p106b_hold_resolution_literal_guard_v1.py',
                     'scripts/p106b_hold_resolution_literal_guard_v2.py',
                     'scripts/p106b_hold_resolution_reviewed_cache_v2.py']:
            self.assertIn(path, pins)

    def test_additional_pair_needs_explicit_manual_id_and_residual_state(self):
        row = reviewed.literal.load_registry()['expanded_train:8455']
        raw, clean = ((ROOT / row[key]).read_text() for key in ['original', 'body'])
        engine = object.__new__(reviewed.ReviewedResolutionEngine)
        engine.literal_cases = reviewed.literal.load_registry()
        with patch.object(reviewed.ORIGINAL_ENGINE, 'code_guard', return_value=False):
            for state in [1, 2, 4, 5]:
                engine.current = ({}, state)
                self.assertFalse(engine.code_guard(raw, clean, {'literal_guard_case_id': row['id']}))
            engine.current = ({}, 3)
            self.assertFalse(engine.code_guard(raw, clean))
            self.assertTrue(engine.code_guard(raw, clean, {'literal_guard_case_id': row['id']}))

    def test_context_restores_engine_and_parent_bindings_after_failure(self):
        before_engine = reviewed.final.ResolutionEngine
        before_literal = reviewed.previous.literal
        with self.assertRaisesRegex(RuntimeError, 'controlled-failure'):
            with reviewed.reviewed_inputs():
                self.assertIs(reviewed.final.ResolutionEngine, reviewed.ReviewedResolutionEngine)
                raise RuntimeError('controlled-failure')
        self.assertIs(reviewed.final.ResolutionEngine, before_engine)
        self.assertIs(reviewed.previous.literal, before_literal)


if __name__ == '__main__':
    with patch.object(inherited, 'reviewed', reviewed):
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromTestCase(inherited.ReviewedCacheBoundaries),
            unittest.defaultTestLoader.loadTestsFromTestCase(AdditionalCacheBoundaries)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
