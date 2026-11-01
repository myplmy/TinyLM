#!/usr/bin/env python3
"""Baseline priority, explicit exception scope and adapter dispatch checks."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_reviewed_cache_v1 as reviewed


class ReviewedCacheBoundaries(unittest.TestCase):
    def engine(self, state=3):
        result = object.__new__(reviewed.ReviewedResolutionEngine)
        result.current = ({}, state)
        result.literal_cases = reviewed.literal.load_registry()
        return result

    def texts(self):
        row = reviewed.literal.load_registry()["expanded_train:1242413"]
        return tuple((ROOT / row[key]).read_bytes().decode("utf-8") for key in ["original", "body"])

    def test_an_existing_baseline_guard_failure_cannot_borrow_new_exception(self):
        original, clean = self.texts()
        with patch.object(reviewed.ORIGINAL_ENGINE, "code_guard", return_value=False):
            for state in [1, 2, 4, 5]:
                self.assertFalse(self.engine(state).code_guard(original, clean, {"literal_guard_case_id": "expanded_train:1242413"}))

    def test_a_reviewed_residual_pair_requires_its_explicit_manual_binding(self):
        original, clean = self.texts()
        with patch.object(reviewed.ORIGINAL_ENGINE, "code_guard", return_value=False):
            engine = self.engine()
            self.assertFalse(engine.code_guard(original, clean))
            self.assertTrue(engine.code_guard(original, clean, {"literal_guard_case_id": "expanded_train:1242413"}))

    def test_the_original_guard_still_handles_other_actual_code(self):
        with patch.object(reviewed.ORIGINAL_ENGINE, "code_guard", return_value=True):
            self.assertTrue(self.engine().code_guard("```x```", "```x```"))

    def test_partial_and_final_schemas_are_not_converted(self):
        with patch.object(reviewed.final.engine.cache, "read", return_value={"schema": reviewed.partial.SCHEMA}):
            self.assertIs(reviewed.selected_adapter(Path("roster")), reviewed.partial)
        with patch.object(reviewed.final.engine.cache, "read", return_value={"schema": reviewed.final.SCHEMA}):
            self.assertIs(reviewed.selected_adapter(Path("roster")), reviewed.final)
        with patch.object(reviewed.final.engine.cache, "read", return_value={"schema": "DRAFT"}):
            with self.assertRaisesRegex(ValueError, "unknown reviewed roster"):
                reviewed.selected_adapter(Path("roster"))

    def test_all_literal_review_inputs_are_runtime_pinned(self):
        cases = reviewed.literal.load_registry()
        pins = reviewed.input_pins(cases)
        self.assertIn(reviewed.literal.REGISTRY, pins)
        for row in cases.values():
            for path in [row["original"], row["body"], row["evidence"]["path"]]:
                self.assertIn(path, pins)
        before = reviewed.final.ResolutionEngine
        with reviewed.reviewed_inputs():
            self.assertIs(reviewed.final.ResolutionEngine, reviewed.ReviewedResolutionEngine)
        self.assertIs(reviewed.final.ResolutionEngine, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
