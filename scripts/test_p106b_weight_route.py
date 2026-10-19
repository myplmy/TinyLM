#!/usr/bin/env python3
"""Small synthetic CPU routes only; no real model, checkpoint or asset I/O."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
import torch.nn.functional as F
from tinylm.model.ternary import TLinear
from tinylm.model.transformer import TiedMLPTransformer
from scripts import p106b_weight_route as r


def cfg():
    return SimpleNamespace(micro_group=2, twn_thr_ratio=.7, ste_clip=2.5,
                           n_modes=1, mode_rank=0, quant_anneal=1., tie_mlp=False,
                           wq_dtype='fp32', center_weights=False, sparse34=False)


class Mini(torch.nn.Module):
    """Eight synthetic weights plus one alias; uses real lifecycle methods."""
    refresh_quant = TiedMLPTransformer.refresh_quant
    clear_quant = TiedMLPTransformer.clear_quant
    freeze_quant = TiedMLPTransformer.freeze_quant
    set_anneal = TiedMLPTransformer.set_anneal

    def __init__(self, share=None):
        super().__init__()
        self.cfg = cfg() if share is None else share.cfg
        self.a = TLinear(self.cfg, 2, 2) if share is None else share
        self.alias = self.a
        self.b = TLinear(self.cfg, 2, 2)
        with torch.no_grad():
            self.a.weight.copy_(torch.tensor([[.1, .9], [-.4, -.7]]))
            self.b.weight.copy_(torch.tensor([[.8, -.2], [.3, .5]]))
        self._tlinear_cache = [self.a, self.b]
        self.register_buffer('_anneal', torch.tensor(1.), persistent=False)
        self._quant_frozen = False
        self._p102a_quant_update = None
        self._arena = None
        self._arena_v = 0.

    def forward(self, x, *, use_cache=False, past=None):
        if not self._quant_frozen and self._p102a_quant_update is None:
            self.refresh_quant()
        all_x = x if past is None else torch.cat((past, x), dim=1)
        output = self.b(self.a(all_x))
        return (output[:, -x.shape[1]:], all_x.detach()) if use_cache else output


def payload(model, mode):
    return dict(model={k: v.detach().clone() for k, v in model.state_dict().items()},
                quantization_route=r.route_metadata(mode))


class RouteTests(unittest.TestCase):
    def test_float_forward_and_input_weight_gradients_equal_plain_linear(self):
        model = Mini()
        x = torch.tensor([[.7, -1.1], [2., .3]], requires_grad=True)
        expected_x = x.detach().clone().requires_grad_()
        wa = model.a.weight.detach().clone().requires_grad_()
        wb = model.b.weight.detach().clone().requires_grad_()
        expected = F.linear(F.linear(expected_x, wa), wb)
        expected.square().sum().backward()
        with r.weight_route(model, 'float'):
            actual = model(x)
            actual.square().sum().backward()
            torch.testing.assert_close(actual, expected, rtol=0, atol=0)
            for actual_grad, target in ((x.grad, expected_x.grad),
                                        (model.a.weight.grad, wa.grad), (model.b.weight.grad, wb.grad)):
                torch.testing.assert_close(actual_grad, target, rtol=0, atol=0)
            self.assertNotIsInstance(model.a._wq, torch.nn.Parameter)
            self.assertEqual(model.a._wq.data_ptr(), model.a.weight.data_ptr())

    def test_anneal_zero_still_has_ste_and_is_not_float_gradient(self):
        model = Mini();model.set_anneal(0.)
        model.refresh_quant()
        model.a(torch.ones(1, 2)).sum().backward()
        ste_gradient = model.a.weight.grad.clone()
        model.zero_grad(set_to_none=True)
        with r.weight_route(model, 'float'):
            model.refresh_quant();model.a(torch.ones(1, 2)).sum().backward()
            self.assertTrue(torch.equal(model.a.weight.grad, torch.ones(2, 2)))
        self.assertFalse(torch.equal(ste_gradient, torch.ones(2, 2)))

    def test_sixteen_micro_accumulation_matches_direct_linear(self):
        model = Mini()
        wa = model.a.weight.detach().clone().requires_grad_()
        wb = model.b.weight.detach().clone().requires_grad_()
        with r.weight_route(model, 'float'):
            for i in range(16):
                x = torch.tensor([[i / 16., 1. - i / 32.]])
                (model(x).square().sum() / 16).backward()
                (F.linear(F.linear(x, wa), wb).square().sum() / 16).backward()
            torch.testing.assert_close(model.a.weight.grad, wa.grad, rtol=0, atol=0)
            torch.testing.assert_close(model.b.weight.grad, wb.grad, rtol=0, atol=0)

    def test_nonreentrant_checkpoint_backward_keeps_identity_route(self):
        from torch.utils.checkpoint import checkpoint
        model = Mini()
        wa = model.a.weight.detach().clone().requires_grad_()
        wb = model.b.weight.detach().clone().requires_grad_()
        x = torch.tensor([[.3, -.8]], requires_grad=True)
        baseline_x = x.detach().clone().requires_grad_()
        baseline = F.linear(F.linear(baseline_x, wa), wb)
        baseline.square().sum().backward()
        with r.weight_route(model, 'float'):
            actual = checkpoint(model, x, use_reentrant=False)
            actual.square().sum().backward()
            for left, right in ((actual, baseline), (x.grad, baseline_x.grad),
                                (model.a.weight.grad, wa.grad), (model.b.weight.grad, wb.grad)):
                torch.testing.assert_close(left, right, rtol=0, atol=0)

    def test_eager_backend_compilation_keeps_float_route_across_updates(self):
        model = Mini();baseline = Mini()
        optimizer = torch.optim.SGD(model.parameters(), lr=.03)
        reference_optimizer = torch.optim.SGD(baseline.parameters(), lr=.03)
        x = torch.tensor([[.2, -.7]])
        self.assertFalse(torch.cuda.is_initialized())
        with r.weight_route(model, 'float'), patch.object(torch.cuda, 'is_available', return_value=False), \
                patch.object(torch.cuda, 'device_count', return_value=0):
            compiled = torch.compile(model, backend='eager', fullgraph=True)
            for _ in range(2):
                optimizer.zero_grad();reference_optimizer.zero_grad()
                actual = compiled(x)
                expected = F.linear(F.linear(x, baseline.a.weight), baseline.b.weight)
                torch.testing.assert_close(actual, expected, rtol=0, atol=0)
                actual.square().sum().backward();expected.square().sum().backward()
                optimizer.step();reference_optimizer.step()
            self.assertTrue(all(torch.equal(a, b) for a, b in zip(model.parameters(), baseline.parameters())))
        del compiled
        self.assertFalse(torch.cuda.is_initialized())

    def test_ternary_route_reproduces_original_forward_and_gradients(self):
        original, actual = Mini(), Mini()
        original.set_anneal(.4);actual.set_anneal(.4)
        x = torch.tensor([[.3, -.7]])
        target = original(x);target.sum().backward()
        with r.weight_route(actual, 'ternary'):
            value = actual(x);value.sum().backward()
            torch.testing.assert_close(value, target, rtol=0, atol=0)
            for a, b in zip(actual.parameters(), original.parameters()):
                torch.testing.assert_close(a.grad, b.grad, rtol=0, atol=0)

    def test_keys_aliases_parameter_and_optimizer_identity_do_not_change(self):
        model = Mini();optimizer = torch.optim.SGD(model.parameters(), lr=.1)
        keys, params = tuple(model.state_dict()), tuple(model.parameters())
        with r.weight_route(model, 'float'):
            model(torch.ones(1, 2)).sum().backward();optimizer.step()
            self.assertEqual(tuple(model.state_dict()), keys)
            self.assertTrue(all(a is b for a, b in zip(model.parameters(), params)))
            self.assertTrue(all(a is b for a, b in zip(optimizer.param_groups[0]['params'], params)))
            self.assertIs(model.a, model.alias)
            self.assertNotIn('_wq', model.a._parameters)
        self.assertIs(model.a, model.alias)

    def test_exception_restores_methods_flags_anneal_and_unchanged_cache(self):
        model = Mini();model.eval();model.freeze_quant()
        old_cache, old_anneal = model.a._wq, model.a._anneal_t
        old_refresh, old_forward = model.a.refresh_quant, model.a.forward
        with self.assertRaisesRegex(RuntimeError, 'fixture'):
            with r.weight_route(model, 'float') as route:
                model.set_anneal(.2);model.train();model(torch.ones(1, 2))
                raise RuntimeError('fixture')
        self.assertEqual(model.a.refresh_quant, old_refresh)
        self.assertEqual(model.a.forward, old_forward)
        self.assertIs(model.a._wq, old_cache)
        self.assertIs(model.a._anneal_t, old_anneal)
        self.assertTrue(model._quant_frozen)
        self.assertFalse(model.training)
        self.assertEqual(float(model._anneal), 1.)
        self.assertEqual(model.cfg.quant_anneal, 1.)
        self.assertTrue(route.cache_restored)
        self.assertFalse(route.active)

    def test_weight_update_invalidates_old_frozen_cache_on_exit(self):
        model = Mini();model.eval();model.freeze_quant()
        with r.weight_route(model, 'float') as route:
            with torch.no_grad():model.a.weight.add_(.1)
            model(torch.ones(1, 2))
        self.assertTrue(route.cache_invalidated)
        self.assertIsNone(model.a._wq)
        self.assertIsNone(model.a._anneal_t)
        self.assertFalse(model._quant_frozen)

    def test_different_models_are_independent_and_class_is_unchanged(self):
        first, second = Mini(), Mini()
        class_refresh, class_forward = TLinear.refresh_quant, TLinear.forward
        original = second(torch.ones(1, 2)).detach().clone()
        with r.weight_route(first, 'float'):
            self.assertIs(TLinear.refresh_quant, class_refresh)
            self.assertIs(TLinear.forward, class_forward)
            torch.testing.assert_close(second(torch.ones(1, 2)), original, rtol=0, atol=0)
            with r.weight_route(second, 'ternary'):
                torch.testing.assert_close(second(torch.ones(1, 2)), original, rtol=0, atol=0)
            first(torch.ones(1, 2))
        self.assertNotIn('refresh_quant', first.a.__dict__)

    def test_same_model_and_shared_tlinear_nesting_are_rejected(self):
        first = Mini();second = Mini(share=first.a)
        with r.weight_route(first, 'float'):
            with self.assertRaises(RuntimeError):
                with r.weight_route(first, 'float'):pass
            with self.assertRaises((RuntimeError, ValueError)):
                with r.weight_route(second, 'ternary'):pass
            first(torch.ones(1, 2))

    def test_missing_refresh_is_error_and_cannot_fall_back_to_ternary(self):
        model = Mini()
        for mode in r.MODES:
            with r.weight_route(model, mode):
                with self.assertRaisesRegex(RuntimeError, 'fallback'):
                    model.a(torch.ones(1, 2))
                model.refresh_quant();model.clear_quant()
                with self.assertRaisesRegex(RuntimeError, 'fallback'):
                    model.a(torch.ones(1, 2))
                model(torch.ones(1, 2))

    def test_eval_freeze_clear_and_prefix_cache_match_full_float_computation(self):
        model = Mini();model.eval()
        x = torch.tensor([[[.2, .4], [.6, .8], [1., 1.2]]])
        with r.weight_route(model, 'float'):
            model.freeze_quant()
            with torch.no_grad():
                full = model(x)
                first, past = model(x[:, :2], use_cache=True)
                last, _ = model(x[:, 2:], use_cache=True, past=past)
                torch.testing.assert_close(torch.cat((first, last), dim=1), full, rtol=0, atol=0)
            model.clear_quant();self.assertFalse(model._quant_frozen)
            torch.testing.assert_close(model(x), full, rtol=0, atol=0)

    def test_stale_frozen_cache_and_training_with_frozen_cache_are_errors(self):
        model = Mini();model.eval()
        with r.weight_route(model, 'float'):
            model.freeze_quant()
            with torch.no_grad():model.a.weight.add_(.1)
            with self.assertRaisesRegex(RuntimeError, 'stale'):
                model(torch.ones(1, 2))
            model.freeze_quant();model.train()
            with self.assertRaisesRegex(RuntimeError, 'training'):
                model(torch.ones(1, 2))

    def test_rng_unchanged_by_route_entry_projection_and_exit(self):
        model = Mini();before = torch.random.get_rng_state().clone()
        with r.weight_route(model, 'float'):
            model(torch.ones(1, 2))
        self.assertTrue(torch.equal(before, torch.random.get_rng_state()))

    def test_ambient_bf16_amp_is_preserved_and_matches_plain_linear(self):
        model = Mini();x = torch.tensor([[.2, .7]])
        with r.weight_route(model, 'float'), torch.autocast('cpu', dtype=torch.bfloat16):
            actual = model(x)
            expected = F.linear(F.linear(x, model.a.weight), model.b.weight)
        self.assertEqual(actual.dtype, torch.bfloat16)
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)

    def test_unsupported_cfg_features_are_rejected_before_mutation(self):
        changes = dict(center_weights=True, sparse34=True, use_ternary_kernel=True,
                       ternary_kernel_triton=True, fused_int8=True, arenas=True,
                       mlp_lora_rank=1, n_modes=2, mode_rank=1, mlp_film=True,
                       mlp_lrm=True, mtp_aux=True, qk_gain_learnable=True,
                       train_repeat=2., infer_repeat=2., tie_mlp=True,
                       connectivity_mode='static', connectivity_density=.5,
                       wq_dtype='bf16', kv_dtype='bf16', attn_kind='gdn', x2_active_tiles=(0,))
        for name, value in changes.items():
            model = Mini();setattr(model.cfg, name, value)
            with self.subTest(name=name), self.assertRaises(ValueError):
                with r.weight_route(model, 'float'):pass
            self.assertNotIn('refresh_quant', model.a.__dict__)
            self.assertNotIn(r._MARKER, model.__dict__)

    def test_packed_latent_drop_connectivity_and_special_model_states_are_rejected(self):
        for name in ('_i8', '_alpha', '_lut_codes', '_lut_alpha', '_latent_shape',
                     '_i8_cache', '_i8_cache_gen', '_unpack_gen', 'connectivity_mask'):
            model = Mini();setattr(model.a, name, torch.ones(1))
            with self.subTest(name=name), self.assertRaises(ValueError):
                with r.weight_route(model, 'float'):pass
        for name, value in (('_p102a_quant_update', []), ('_int8_store', True),
                            ('_unpack_cache', True), ('_emb_fmt', 'bf16'), ('_arena', torch.tensor(0.))):
            model = Mini();setattr(model, name, value)
            with self.subTest(name=name), self.assertRaises(ValueError):
                with r.weight_route(model, 'float'):pass

    def test_runtime_unsupported_centering_mode_arena_and_update_cache_are_errors(self):
        model = Mini()
        with r.weight_route(model, 'float'):
            model.cfg.center_weights = True
            with self.assertRaises(ValueError):model.refresh_quant()
            model.cfg.center_weights = False
            with self.assertRaises(ValueError):model.a.refresh_quant(model._anneal, torch.tensor(0.))
            model.refresh_quant()
            with self.assertRaises(ValueError):model.a(torch.ones(1, 2), torch.ones(1))
            model._p102a_quant_update = []
            with self.assertRaises(ValueError):model.a(torch.ones(1, 2))
            model._p102a_quant_update = None

    def test_exception_restores_unsupported_cfg_and_update_cache_flags(self):
        model = Mini()
        with self.assertRaises(ValueError):
            with r.weight_route(model, 'float'):
                model.cfg.center_weights = True
                model._p102a_quant_update = []
                model(torch.ones(1, 2))
        self.assertFalse(model.cfg.center_weights)
        self.assertIsNone(model._p102a_quant_update)
        self.assertNotIn('forward', model.a.__dict__)

    def test_parameter_cache_registration_and_incomplete_cache_are_rejected(self):
        model = Mini();model.a._wq = model.a.weight
        with self.assertRaises(ValueError):
            with r.weight_route(model, 'float'):pass
        model = Mini();model._tlinear_cache = [model.a]
        with self.assertRaises(ValueError):
            with r.weight_route(model, 'float'):pass

    def test_state_identity_change_is_reported_after_method_restoration(self):
        model = Mini()
        with self.assertRaisesRegex(RuntimeError, 'identity'):
            with r.weight_route(model, 'float'):
                model.extra = torch.nn.Parameter(torch.tensor(1.))
        self.assertNotIn('forward', model.a.__dict__)
        self.assertNotIn(r._MARKER, model.__dict__)

    def test_invalid_mode_and_inactive_guard_are_errors(self):
        model = Mini()
        for mode in ('fp32', None, True):
            with self.assertRaises(ValueError):
                with r.weight_route(model, mode):pass
        with self.assertRaises(RuntimeError):r.assert_route_active(model)
        with r.weight_route(model, 'float') as route:
            self.assertIs(route.assert_active(), route)
            with self.assertRaises(RuntimeError):r.assert_route_active(model, 'ternary')


class LoaderTests(unittest.TestCase):
    def test_metadata_is_exact_explicit_and_does_not_default_to_anneal(self):
        for mode in r.MODES:
            self.assertEqual(r.validate_route_metadata(r.route_metadata(mode), mode), mode)
        for metadata in (None, {}, dict(r.route_metadata('float'), backward='ORIGINAL_STE_WINDOW'),
                         dict(r.route_metadata('float'), extra=True),
                         dict(r.route_metadata('float'), dedicated_loader_required=1)):
            with self.assertRaises(ValueError):r.validate_route_metadata(metadata)
        with self.assertRaises(ValueError):r.validate_route_metadata(r.route_metadata('float'), 'ternary')

    def test_generic_loader_refuses_float_and_missing_route(self):
        with self.assertRaises(RuntimeError):r.generic_loader_guard({'quantization_route': r.route_metadata('float')})
        with self.assertRaises(ValueError):r.generic_loader_guard({})
        self.assertEqual(r.generic_loader_guard({'quantization_route': r.route_metadata('ternary')}), 'ternary')

    def test_float_strict_reload_requires_active_matching_route_and_preserves_outputs(self):
        source = Mini();saved = payload(source, 'float');target = Mini()
        with torch.no_grad():target.a.weight.add_(5.)
        with self.assertRaises(RuntimeError):r.load_routed_state(target, saved, 'float')
        with r.weight_route(source, 'float'), r.weight_route(target, 'float'):
            result = r.load_routed_state(target, saved, 'float')
            self.assertFalse(result.missing_keys or result.unexpected_keys)
            torch.testing.assert_close(source(torch.ones(1, 2)), target(torch.ones(1, 2)), rtol=0, atol=0)

    def test_bad_metadata_keys_shapes_dtypes_are_rejected_before_any_copy(self):
        model = Mini();valid = payload(model, 'float')
        bad = []
        item = copy.deepcopy(valid);item.pop('quantization_route');bad.append(item)
        item = copy.deepcopy(valid);item['quantization_route'] = r.route_metadata('ternary');bad.append(item)
        item = copy.deepcopy(valid);item['model']['extra'] = torch.ones(1);bad.append(item)
        item = copy.deepcopy(valid);item['model']['a.weight'] = torch.ones(1, 1);bad.append(item)
        item = copy.deepcopy(valid);item['model']['a.weight'] = item['model']['a.weight'].double();bad.append(item)
        before = {k: v.clone() for k, v in model.state_dict().items()}
        with r.weight_route(model, 'float'):
            for item in bad:
                with self.assertRaises(ValueError):r.load_routed_state(model, item, 'float')
                self.assertTrue(all(torch.equal(v, model.state_dict()[k]) for k, v in before.items()))

    def test_shared_parameter_checkpoint_aliases_must_agree_before_copy(self):
        model = Mini();saved = payload(model, 'float')
        saved['model']['alias.weight'].add_(1.)
        before = model.a.weight.detach().clone()
        with r.weight_route(model, 'float'):
            with self.assertRaisesRegex(ValueError, 'shared Parameter'):
                r.load_routed_state(model, saved, 'float')
            self.assertTrue(torch.equal(model.a.weight, before))


if __name__ == '__main__':
    torch.set_num_threads(1)
    unittest.main()
