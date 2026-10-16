from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
import numpy as np
import torch
from scripts import diag_p106b_night_foundation as d


class RuntimeContract(unittest.TestCase):
    def test_arms_have_independent_weight_paths(self):
        self.assertEqual(len({d.checkpoint(a) for a in d.ARMS}), 3)
        self.assertNotEqual(d.checkpoint('base_qa'), d.checkpoint('base_qa', True))
        with self.assertRaises(ValueError): d.checkpoint('native', True)

    def test_fixed_recipe_and_original_parent(self):
        i = d.info()
        self.assertEqual(i['parent_sha256'], d.data.PARENT_SHA)
        self.assertEqual((i['micro_bs'], i['accum'], i['seq']), (8, 16, 1024))
        self.assertEqual((i['cpt_lr'], i['qa_lr']), (1e-4, 5e-5))
        self.assertEqual(i['consistency_weight'], 0.)
        self.assertTrue(i['fresh_optimizer_each_phase'])
        self.assertFalse(i['mtp'])

    def test_source_native_groups_have_full_macro_denominator(self):
        c = d.data.make_contract(4 * 2 * d.data.UPDATE_TARGETS, d.data.TRAIN_SHA, d.data.VAL_SHA)
        for group in d.data.native_groups(c):
            self.assertEqual(sum(len(m) * 1024 for m in group), 131072)
        self.assertEqual(c['actual_draw_tokens'], 4 * 131072)

    def test_actual_native_batch_shift_via_cpu_tensor_adapter(self):
        class CPU:
            long = torch.long
            @staticmethod
            def tensor(value, dtype, device): return torch.tensor(value, dtype=dtype, device='cpu')
            @staticmethod
            def ones_like(value): return torch.ones_like(value)
        windows = [np.arange(1025, dtype=np.uint16) + i for i in range(12)]
        order = [9, 1, 7, 3, 0, 5, 8, 11]
        x, y, seg = d.native_batch(CPU, windows, order)
        self.assertEqual(tuple(x.shape), (8, 1024))
        self.assertTrue(torch.equal(y[:, :-1], x[:, 1:]))
        self.assertEqual(x[:, 0].tolist(), order)
        self.assertEqual(y[:, -1].tolist(), [i + 1024 for i in order])
        self.assertTrue(bool(seg.eq(1).all()))

    def test_full_target_micro_mean_gradient_matches_macro(self):
        weight = torch.tensor(1.2, requires_grad=True)
        chunks = [torch.tensor([i + 1., i + 2.]) for i in range(16)]
        denominator = sum(value.numel() for value in chunks)
        for value in chunks: ((value * weight).square().sum() / denominator).backward()
        first = weight.grad.clone(); weight.grad = None
        (torch.cat(chunks) * weight).square().mean().backward()
        self.assertTrue(torch.allclose(first, weight.grad, atol=1e-5))

    def test_no_model_or_cuda_on_import(self):
        import torch
        self.assertFalse(torch.cuda.is_initialized())


if __name__ == '__main__': unittest.main()
