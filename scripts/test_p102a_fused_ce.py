#!/usr/bin/env python3
"""Synthetic CPU adapter contracts. Mocked dispatch is not a fused GPU test."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import torch
import torch.nn.functional as F
from tinylm.train import fused_ce as fast
from tinylm.train import mtp_sft as core


class Head(torch.nn.Module):
    """Only shared linear heads, no Transformer/model asset or corpus."""
    def __init__(self):
        super().__init__()
        torch.manual_seed(19)
        self.emb = torch.nn.Embedding(23, 4)
        self.emb_up = torch.nn.Linear(4, 6, bias=False)
        self.cfg = SimpleNamespace(mtp_aux=True, mtp_horizons=(2, 3, 4))
        for h in (2, 3, 4):
            self.register_parameter(f'mtp_up{h}', torch.nn.Parameter(torch.randn(6, 4) * .1))

    def _emb_w(self):
        return self.emb.weight

    def _emb_up_w(self):
        return self.emb_up.weight

    def _head_logits(self, h):
        return F.linear(F.linear(h, self._emb_up_w().t()), self._emb_w())

    def mtp_aux_logits(self, h, horizon):
        return F.linear(F.linear(h.float(), getattr(self, f'mtp_up{horizon}').float().t()),
                        self._emb_w())

    def input_features(self, ids):
        return F.linear(self.emb(ids), self.emb_up.weight)


def reference_external(projected, table, labels, reduction):
    return F.cross_entropy(F.linear(projected, table).float(), labels,
                           ignore_index=-100, reduction=reduction)


def values():
    torch.manual_seed(9)
    return (torch.randn(7, 4, requires_grad=True),
            torch.randn(23, 4, requires_grad=True),
            torch.tensor([2, -100, 4, 1, 5, 8, 2]))


class AdapterTests(unittest.TestCase):
    def tearDown(self):
        fast._external_function.cache_clear()

    def test_reference_value_and_all_gradients(self):
        p, w, labels = values()
        expected = reference_external(p, w, labels, 'sum')
        actual = fast.linear_ce(p, w, labels)
        self.assertTrue(torch.equal(actual, expected))
        for left, right in zip(torch.autograd.grad(expected, (p, w), retain_graph=True),
                               torch.autograd.grad(actual, (p, w))):
            self.assertTrue(torch.equal(left, right))

    def test_signed_zero_and_nonlinear_upstream(self):
        for multiplier in (-2., 0., .37):
            p, w, labels = values()
            a = fast.linear_ce(p, w, labels)
            b = reference_external(p, w, labels, 'sum')
            for ga, gb in zip(torch.autograd.grad((a * multiplier).square(), (p, w), retain_graph=True),
                               torch.autograd.grad((b * multiplier).square(), (p, w))):
                self.assertTrue(torch.equal(ga, gb))

    def test_per_row_weights_and_ignore(self):
        p, w, labels = values()
        outer = torch.tensor([1., 100., -1., 0., .5, 2., -.3])
        a = fast.linear_ce(p, w, labels, reduction='none')
        b = reference_external(p, w, labels, 'none')
        self.assertEqual(float(a[1].detach()), 0.)
        for ga, gb in zip(torch.autograd.grad((a * outer).sum(), (p, w), retain_graph=True),
                           torch.autograd.grad((b * outer).sum(), (p, w))):
            self.assertTrue(torch.equal(ga, gb))

    def test_noncontiguous_inputs(self):
        p, w, labels = values()
        p = p.t().contiguous().t()
        w = w.t().contiguous().t()
        self.assertFalse(p.is_contiguous())
        self.assertTrue(torch.equal(fast.linear_ce(p, w, labels),
                                    reference_external(p, w, labels, 'sum')))

    def test_empty_and_all_ignored_remain_differentiable(self):
        for size in (0, 7):
            p = torch.randn(size, 4, requires_grad=True)
            w = torch.randn(23, 4, requires_grad=True)
            y = torch.full((size,), -100, dtype=torch.long)
            loss = fast.linear_ce(p, w, y)
            self.assertEqual(float(loss.detach()), 0.)
            loss.backward()
            self.assertEqual(float(w.grad.abs().sum()), 0.)
            self.assertEqual(tuple(fast.linear_ce(p, w, y, reduction='none').shape), (size,))

    def test_official_backend_on_cpu_does_not_fallback_or_import(self):
        for name in ('liger', 'cce_exact'):
            with patch.object(fast, '_external_function') as load:
                with self.assertRaisesRegex(ValueError, 'CUDA'):
                    fast.linear_ce(*values(), backend=name)
                load.assert_not_called()

    def test_invalid_labels_shapes_dtype_backend_reduction(self):
        p, w, labels = values()
        cases = [(p, w, labels.float(), {}), (p, w, labels[:-1], {}),
                 (p, w, torch.full_like(labels, -2), {}),
                 (p, w, torch.full_like(labels, 23), {}),
                 (p, w, labels, {'backend': 'auto'}),
                 (p, w, labels, {'reduction': 'mean'})]
        for a, b, y, kwargs in cases:
            with self.assertRaises(ValueError):
                fast.linear_ce(a, b, y, **kwargs)

    def test_liger_frozen_feature_table_gradient_fail_closed(self):
        p, w, y = values()
        with patch.object(fast, '_require_cuda'), patch.object(fast, '_external_function') as load:
            with self.assertRaisesRegex(ValueError, 'frozen-feature'):
                fast.linear_ce(p.detach(), w, y, backend='liger')
            load.assert_not_called()

    def test_explicit_mocked_dispatch_preserves_tied_input_and_output_gradients(self):
        for backend in ('liger', 'cce_exact'):
            original = Head()
            candidate = copy.deepcopy(original)
            ids = torch.tensor([[1, 2, 1, 3, 4]])
            targets = torch.tensor([[3, -100, 2, 4, 1]])
            before = candidate.emb.weight.data_ptr()
            expected = F.cross_entropy(original._head_logits(original.input_features(ids)).flatten(0, 1),
                                        targets.flatten(), ignore_index=-100, reduction='sum')
            with patch.object(fast, '_require_cuda'), patch.object(fast, '_external_function', return_value=reference_external):
                actual = fast.model_head_ce(candidate, candidate.input_features(ids), targets, backend=backend)
                actual.backward()
            expected.backward()
            self.assertEqual(before, candidate.emb.weight.data_ptr())
            self.assertTrue(torch.equal(expected, actual))
            for name, parameter in original.named_parameters():
                other = dict(candidate.named_parameters())[name]
                if parameter.grad is not None:
                    self.assertTrue(torch.equal(parameter.grad, other.grad), name)

    def test_mtp_projection_matches_original(self):
        for h in (2, 3, 4):
            model = Head()
            x = torch.randn(2, 3, 6, requires_grad=True)
            y = torch.tensor([[1, 2, 3], [4, 5, 6]])
            expected = core.ce_sum(model.mtp_aux_logits(x, h), y, 2)
            actual = fast.model_head_ce(model, x, y, horizon=h)
            self.assertTrue(torch.allclose(actual, expected, atol=1e-6, rtol=1e-6))

    def test_disabled_packed_and_missing_projection_rejected(self):
        model = Head()
        x = torch.randn(1, 2, 6)
        y = torch.tensor([[1, 2]])
        model._emb_fmt = 'int8'
        with self.assertRaisesRegex(ValueError, 'packed'):
            fast.model_head_ce(model, x, y)
        model._emb_fmt = None
        model.cfg.mtp_aux = False
        with self.assertRaisesRegex(ValueError, 'disabled'):
            fast.model_head_ce(model, x, y, horizon=2)
        model.cfg.mtp_aux = True
        model.mtp_up2 = None
        with self.assertRaisesRegex(ValueError, 'absent'):
            fast.model_head_ce(model, x, y, horizon=2)

    def test_components_default_bit_preserved_and_mocked_mask_gradient_pair(self):
        ids = torch.tensor([[1, 2, 3, 4, 5, 6], [2, 1, 2, 1, 3, 0]])
        y = torch.tensor([[-100, 2, 3, 4, 5, 6], [2, 1, -100, 4, 5, -100]])
        turns = torch.tensor([[0, 1, 1, 2, 2, 2], [1, 1, 0, 2, 2, 0]])
        runs = []
        for backend in (None, 'reference', 'liger', 'cce_exact'):
            model = Head()
            kwargs = {} if backend is None else {'ce_backend': backend}
            with patch.object(fast, '_require_cuda'), patch.object(fast, '_external_function', return_value=reference_external):
                sums, counts = core.components(model, model.input_features(ids), y, turns,
                    chunk=5, checkpoint_heads=True, **kwargs)
                loss = core.normalized_loss(sums, counts, {2: .1, 3: .05, 4: .025})
                loss.backward()
            runs.append((loss.detach(), counts,
                         {n: p.grad for n, p in model.named_parameters() if p.grad is not None}))
        for item in runs[1:]:
            self.assertTrue(torch.equal(runs[0][0], item[0]))
            self.assertEqual(runs[0][1], item[1])
            for name in runs[0][2]:
                self.assertTrue(torch.equal(runs[0][2][name], item[2][name]), name)

    def test_no_extra_label_shift_at_dispatch(self):
        model = Head()
        x = torch.randn(1, 3, 6, requires_grad=True)
        y = torch.tensor([[2, 3, 4]])
        seen = []
        def capture(p, w, labels, reduction):
            seen.append(labels.clone())
            return reference_external(p, w, labels, reduction)
        with patch.object(fast, '_require_cuda'), patch.object(fast, '_external_function', return_value=capture):
            fast.model_head_ce(model, x, y, backend='cce_exact')
        self.assertTrue(torch.equal(seen[0], y.flatten()))

    def test_model_per_token_shape_is_preserved(self):
        model = Head()
        x = torch.randn(2, 3, 6)
        y = torch.tensor([[1, 2, 3], [4, -100, 6]])
        result = fast.model_head_ce(model, x, y, reduction='none')
        self.assertEqual(tuple(result.shape), (2, 3))
        self.assertEqual(float(result[1, 1].detach()), 0.)

    def test_cce_factory_explicit_exact_flags(self):
        calls = []
        module = ModuleType('cut_cross_entropy')
        def official(p, w, labels, **kwargs):
            calls.append(kwargs)
            return reference_external(p, w, labels, kwargs['reduction'])
        module.linear_cross_entropy = official
        with patch.object(fast, '_check_version'), patch.dict(sys.modules, {'cut_cross_entropy': module}):
            fn = fast._external_function('cce_exact')
            fn(*values(), 'none')
        options = calls[0]
        self.assertEqual(options['impl'], 'cce_exact')
        self.assertIsNone(options['filter_eps'])
        self.assertTrue(options['accum_e_fp32'] and options['accum_c_fp32'])
        self.assertFalse(options['filter_e_grad'] or options['filter_c_grad'])
        self.assertEqual(options['shift'], 0)
        self.assertEqual(options['ignore_index'], -100)

    def test_liger_factory_exact_flags_and_shared_table_identity(self):
        calls = []
        module = ModuleType('liger_kernel.transformers.fused_linear_cross_entropy')
        class Official:
            def __init__(self, **kwargs):
                self.options = kwargs
            def __call__(self, w, p, labels):
                calls.append((self.options, w))
                return reference_external(p, w, labels, self.options['reduction'])
        module.LigerFusedLinearCrossEntropyLoss = Official
        p, w, y = values()
        with patch.object(fast, '_check_version'), patch.dict(sys.modules,
                {'liger_kernel.transformers.fused_linear_cross_entropy': module}):
            fn = fast._external_function('liger')
            fn(p, w, y, 'sum')
        options, actual_table = calls[0]
        self.assertIs(actual_table, w)
        self.assertEqual(options['accum_dtype'], torch.float32)
        self.assertEqual(options['label_smoothing'], 0.)
        self.assertEqual(options['lse_square_scale'], 0.)
        self.assertFalse(options['use_token_scaling'])
        self.assertIsNone(options['softcap'])

    def test_old_cce_version_is_rejected(self):
        with patch.object(fast.importlib.metadata, 'version', return_value='25.1.1'):
            with self.assertRaisesRegex(RuntimeError, 'uninspected'):
                fast._check_version('cce_exact')


if __name__ == '__main__':
    torch.set_num_threads(1)
    unittest.main()
