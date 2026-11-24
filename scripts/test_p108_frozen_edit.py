"""CPU fail-closed contracts for lossless frozen edit replay; no model load."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import torch
from scripts import p108_frozen_edit as replay
from scripts.p108_weight_space import tensor_sha


def fixture():
    a = torch.tensor([[.1, .2], [.3, .4]], dtype=torch.float64)
    b = torch.tensor([[.5, .6], [.7, .8], [.9, 1.]], dtype=torch.float64)
    d = (a @ b.T).float()
    w = torch.arange(6, dtype=torch.float32).reshape(2, 3)
    p = dict(left=a.tolist(), right=b.tolist(), layer=11, intended_factor_columns=2,
             delta_sha256=tensor_sha(d), base_weight_sha256=tensor_sha(w))
    return p, d, w


class ReplayTests(unittest.TestCase):
    def test_exact_double_then_float(self):
        p, d, _ = fixture()
        self.assertTrue(torch.equal(replay.decode(p), d))

    def test_before_after_exact(self):
        p, d, w = fixture()
        saved = w.clone()
        self.assertTrue(replay.validate_base_and_after(p, d, w, tensor_sha(w+d))['exact'])
        self.assertTrue(torch.equal(w, saved))

    def test_corrupt_factor_rejected(self):
        p, _, _ = fixture(); p['left'][0][0] += .01
        with self.assertRaisesRegex(ValueError, 'exact frozen'): replay.decode(p)

    def test_nonfinite_rejected(self):
        p, _, _ = fixture(); p['left'][0][0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite'): replay.decode(p)

    def test_factor_width_rejected(self):
        p, _, _ = fixture(); p['intended_factor_columns'] = 3
        with self.assertRaisesRegex(ValueError, 'matching'): replay.decode(p)

    def test_wrong_base_rejected(self):
        p, d, w = fixture()
        with self.assertRaisesRegex(ValueError, 'base weight'):
            replay.validate_base_and_after(p, d, w+1, tensor_sha(w+d))

    def test_wrong_after_rejected(self):
        p, d, w = fixture()
        with self.assertRaisesRegex(ValueError, 'edited weight'):
            replay.validate_base_and_after(p, d, w, '0'*64)

    def test_wrong_dtype_rejected(self):
        p, d, w = fixture()
        with self.assertRaisesRegex(ValueError, 'FP32'):
            replay.validate_base_and_after(p, d, w.half(), tensor_sha(w+d))

    def test_file_bytes_and_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)/'p.json'; f.write_text('{"x":1,"x":2}')
            with self.assertRaises(ValueError): replay.read_pinned(f, replay.digest(f))
            with self.assertRaisesRegex(ValueError, 'artifact SHA'): replay.read_pinned(f, '0'*64)

    def test_project_cache_policy_precedes_task_loading(self):
        from unittest.mock import patch
        from scripts import diag_p108_frozen_edit_official as driver
        events = []
        with patch('scripts.prepare_p106b_official_eval.configure_hf_cache',
                   side_effect=lambda: events.append('cache')), \
             patch.object(driver.suite, 'load_tasks', side_effect=lambda: events.append('tasks')):
            driver.prepare_tasks()
        self.assertEqual(events, ['cache', 'tasks'])


if __name__ == '__main__':
    unittest.main()
