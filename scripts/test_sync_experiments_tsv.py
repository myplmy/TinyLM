#!/usr/bin/env python3
"""Regression for executable post-delete guidance."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("sync_experiments_tsv.py")
SPEC = importlib.util.spec_from_file_location("tinylm_sync_experiments", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


class PostDeleteGuidanceTests(unittest.TestCase):
    def test_ids_guidance_has_required_batch_argument(self) -> None:
        guidance = "\n".join(SYNC.POST_DELETE_GUIDANCE)
        self.assertIn("sync_experiments_tsv.py --apply", guidance)
        self.assertIn("queue_menu.py --audit", guidance)
        self.assertIn("queue_menu.py --ids <배치명...>", guidance)
        self.assertNotIn("queue_menu.py --ids`", guidance)


if __name__ == "__main__":
    unittest.main(verbosity=2)
