#!/usr/bin/env python3
"""CPU-only topology/path contracts; no models, CUDA, datasets or subprocesses."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_authorized_smoke as smoke


class Contract(unittest.TestCase):
    def test_canonical_children_not_removed(self):
        original = smoke.parse_smoke_module(log_name=smoke.LOGNAME)
        changed, edits = smoke.adapt(original)
        self.assertEqual(len(original), len(changed))
        self.assertEqual(sum('--' in x.argv for x in original), sum('--' in x.argv for x in changed))
        self.assertEqual(len(edits), 2)

    def test_training_unchanged(self):
        original = smoke.parse_smoke_module(log_name=smoke.LOGNAME)
        changed, _ = smoke.adapt(original)
        left = [a.argv for a in original if 'run100m.py' in a.argv]
        right = [a.argv for a in changed if 'run100m.py' in a.argv]
        self.assertGreater(len(left), 20)
        self.assertEqual(left, right)

    def test_legacy_checker_absent(self):
        changed, _ = smoke.adapt(smoke.parse_smoke_module(log_name=smoke.LOGNAME))
        self.assertFalse(any('scripts/check_handoff.py' in x.argv for x in changed))
        self.assertTrue(any(smoke.CODEX_CHECKER in x.argv for x in changed))

    def test_environment_isolated_offline(self):
        env = smoke.environment()
        self.assertEqual(env['TINYLM_DIR'], str(smoke.RUNTIME))
        self.assertNotEqual(Path(env['TINYLM_DIR']), ROOT)
        self.assertEqual(env['TL_WANDB_AUTO'], '0')
        self.assertEqual(env['HF_HUB_OFFLINE'], '1')


if __name__ == '__main__':
    unittest.main()
