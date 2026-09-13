#!/usr/bin/env python3
"""Stdlib-only regression for shared P025B/P092 sparsity accounting."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tinylm" / "train" / "sparsity_contract.py"
SPEC = importlib.util.spec_from_file_location("tinylm_sparsity_contract", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
CONTRACT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CONTRACT
SPEC.loader.exec_module(CONTRACT)


class SparsityContractTests(unittest.TestCase):
    def test_three_sparsity_axes_are_separate(self) -> None:
        snap = CONTRACT.sparsity_snapshot([1, 1, 0, 0], [1, 0, 1, 0])
        self.assertEqual(snap.mask_sparsity, 0.5)
        self.assertEqual(snap.ternary_zero_rate, 0.5)
        self.assertEqual(snap.effective_sparsity, 0.75)

    def test_transition_conservation(self) -> None:
        event = CONTRACT.topology_transition([1, 1, 0, 0], [0, 1, 1, 0])
        self.assertEqual((event.births, event.deaths, event.stayed_active), (1, 1, 1))
        self.assertTrue(event.conserves_active_count)
        self.assertEqual(event.turnover, 0.5)

    def test_nonconserving_transition_is_visible(self) -> None:
        event = CONTRACT.topology_transition([1, 0, 0, 0], [1, 1, 0, 0])
        self.assertFalse(event.conserves_active_count)

    def test_exact_two_of_four(self) -> None:
        CONTRACT.validate_nm([1, 0, 1, 0, 0, 1, 0, 1], 2, 4)

    def test_invalid_two_of_four_fails(self) -> None:
        with self.assertRaises(ValueError):
            CONTRACT.validate_nm([1, 1, 1, 0], 2, 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
