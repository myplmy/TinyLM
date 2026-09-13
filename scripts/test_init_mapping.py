#!/usr/bin/env python3
"""CPU/stdlib regression for CLA-aware parent-initialization mapping."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tinylm" / "train" / "init_mapping.py"
SPEC = importlib.util.spec_from_file_location("tinylm_init_mapping", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
MAPPING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAPPING)


class AttentionSourceTests(unittest.TestCase):
    def test_qo_and_qnorm_stay_on_mapped_layer(self) -> None:
        owner = [0, 0, 2, 2, 4, 4]
        for name in ("q_proj.weight", "o_proj.weight", "q_norm.weight"):
            self.assertEqual(MAPPING.teacher_attention_source_index(owner, 3, name), 3)

    def test_kv_and_knorm_follow_cla_owner(self) -> None:
        owner = [0, 0, 2, 2, 4, 4]
        for name in ("k_proj.weight", "v_proj.weight", "k_norm.weight"):
            self.assertEqual(MAPPING.teacher_attention_source_index(owner, 3, name), 2)

    def test_invalid_indices_fail_loudly(self) -> None:
        with self.assertRaises(IndexError):
            MAPPING.teacher_attention_source_index([0, 0], 2, "k_proj.weight")
        with self.assertRaises(IndexError):
            MAPPING.teacher_attention_source_index([3, 3], 1, "v_proj.weight")


if __name__ == "__main__":
    unittest.main(verbosity=2)
