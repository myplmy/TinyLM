"""Synthetic CPU checkpoint/eager parity for existing P078 route APIs.

Only small fresh random weights and in-memory SFT records are used. The eager
reference executes the very same checkpoint callables directly: production
configuration/route guards and sft_update are not modified or reimplemented.
No checkpoint asset, tokenizer, corpus, driver, CUDA run or new CLI is used.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack, contextmanager
import copy
from dataclasses import replace
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import p078_route_training as route
from scripts.test_p078_route_training import cfg as existing_toy_config

import torch
import torch.utils.checkpoint as checkpoint_api
from tinylm.model import transformer
from tinylm.train import mtp_sft as core

# Reuse the pre-existing P070B/P078 toy tolerances; never fit them to a result.
ATOL, RTOL = 1e-5, 1e-4
OBSERVATIONS = []


def records(count):
    result = []
    for i in range(count):
        prefix = [3, 7] + ([8] if i % 2 else [])
        answer = [11 + (i + j) % 40 for j in range(1 + i % 3)]
        ids = prefix + answer + [4]
        labels = [-100] * len(prefix) + answer + [4]
        y = labels[1:]
        result.append(core.Record(ids[:-1], y, [int(v != -100) for v in y]))
    return result


def model_pair(arm):
    policy = route.Policy(arm)
    # Dense14/CLA2 and quantized embedding follow the real parent's geometry,
    # with tiny widths/vocabulary. Existing toy configuration is the source.
    config = replace(existing_toy_config(policy.cap), dim=16, ffn_dim=32,
        n_q_heads=2, n_kv_heads=1, emb_rank=4, n_prelude=2, n_middle=10,
        n_coda=2, tie_mlp=False, quantize_embedding=True, max_seq_len=16)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(20261022)
        enabled = route.build_model(copy.deepcopy(config), policy)
        eager = route.build_model(copy.deepcopy(config), policy)
    eager.load_state_dict(enabled.state_dict(), strict=True)
    for model in (enabled, eager):
        model.set_anneal(1.)
        if any(p.device.type != 'cpu' for p in model.parameters()):
            raise AssertionError('only fresh CPU synthetic parameters are allowed')
    return enabled, eager


def eager_checkpoint(function, *args, **_kwargs):
    """Reference at the checkpoint API, with exactly the same callable/inputs."""
    return function(*args)


class RecomputeTrace:
    def __init__(self, case, model, expected):
        self.case, self.model, self.expected = case, model, expected
        self.active = None
        self.serial = 0
        self.forward = []
        self.recompute = []
        self.micro_shapes = []
        self.mutation_rejected = False
        self.layer_index = {id(layer): i for i, layer in enumerate(model.layers)}

    def assert_lease(self):
        self.case.assertIsNotNone(self.model._lease)
        self.case.assertEqual(self.model._lease[0], 'train')
        self.case.assertEqual(self.model._plan['receipt_sha256'], self.expected['receipt_sha256'])
        self.case.assertEqual(tuple(self.model.visit_schedule()), tuple(self.expected['route']))
        self.model._assert_route()

    @contextmanager
    def context(self, phase, serial):
        previous = self.active
        self.active = phase, serial
        try:
            self.assert_lease()
            if phase == 'recompute' and not self.mutation_rejected:
                before = tuple(self.model.visit_schedule())
                with self.case.assertRaisesRegex(RuntimeError, 'frozen'):
                    self.model.set_route(before)
                with self.case.assertRaisesRegex(RuntimeError, 'nested|overlapping'):
                    with self.model.route_scope(0, 4):
                        self.case.fail('a nested route lease must not be entered')
                self.case.assertEqual(tuple(self.model.visit_schedule()), before)
                self.mutation_rejected = True
            yield
        finally:
            self.active = previous

    def checkpoint(self, function, *args, **kwargs):
        self.case.assertIs(kwargs.get('use_reentrant'), False)
        self.case.assertNotIn('context_fn', kwargs)
        serial = self.serial
        self.serial += 1
        return checkpoint_api.checkpoint(function, *args, **kwargs,
            context_fn=lambda: (self.context('forward', serial), self.context('recompute', serial)))

    def layer_hook(self, layer, _inputs):
        self.assert_lease()
        self.case.assertIsNotNone(self.active, 'a logical layer bypassed the actual checkpoint context')
        phase, serial = self.active
        target = self.forward if phase == 'forward' else self.recompute
        target.append((serial, self.layer_index[id(layer)]))

    def micro_hook(self, _model, inputs):
        self.assert_lease()
        self.micro_shapes.append(tuple(inputs[0].shape))
        self.case.assertEqual(inputs[0].device.type, 'cpu')

    @contextmanager
    def observe(self):
        handles = [self.model.register_forward_pre_hook(self.micro_hook)]
        handles.extend(layer.register_forward_pre_hook(self.layer_hook) for layer in self.model.layers)
        try:
            with patch.object(transformer, 'checkpoint', self.checkpoint):
                yield
        finally:
            for handle in handles:
                handle.remove()

    def assert_complete(self, micros, width):
        visits = self.expected['route']
        self.case.assertEqual(self.micro_shapes, [(8, width)] * micros)
        self.case.assertEqual([i for _, i in self.forward], visits * micros)
        self.case.assertEqual(len(self.forward), micros * len(visits))
        self.case.assertEqual(Counter(s for s, _ in self.forward), Counter(range(self.serial)))
        self.case.assertEqual(Counter(self.recompute), Counter(self.forward))
        self.case.assertTrue(self.mutation_rejected, 'backward never exercised the real recomputation path')
        self.case.assertIsNone(self.model._lease, 'the completed update leaked a route lease')


def gradients(model):
    return {name: None if p.grad is None else p.grad.detach().clone()
            for name, p in model.named_parameters()}


class CheckpointParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)
        print('[P078_CHECKPOINT_PARITY_CPU] ' + json.dumps(OBSERVATIONS, sort_keys=True))

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for owner, name in ((torch, 'load'), (torch, 'save'), (torch.nn.Module, 'cuda'),
                            (torch.Tensor, 'cuda'), (torch.cuda, 'init')):
            self.stack.enter_context(patch.object(owner, name,
                side_effect=AssertionError('real checkpoint/CUDA IO is forbidden in this synthetic test')))
        self.addCleanup(lambda: self.assertFalse(torch.cuda.is_initialized()))

    def assert_gradients_equal(self, left, right):
        self.assertEqual(left.keys(), right.keys())
        maximum, checked = 0., 0
        for name, first in left.items():
            second = right[name]
            if first is None or second is None:
                self.assertIs(first, None, name)
                self.assertIs(second, None, name)
                continue
            self.assertTrue(bool(torch.isfinite(first).all()), name)
            self.assertTrue(bool(torch.isfinite(second).all()), name)
            torch.testing.assert_close(first, second, atol=ATOL, rtol=RTOL, msg=name)
            maximum = max(maximum, float((first - second).abs().max()))
            checked += 1
        self.assertGreater(checked, 0)
        return maximum, checked

    def one_micro(self, model, index, total, *, checkpointed):
        batch = records(8)
        expected = route.plan(model.cfg, model.owner, model.policy, index, total)
        tracer = RecomputeTrace(self, model, expected)
        model.clear_quant(); model.train(); model.zero_grad(set_to_none=True)
        if checkpointed:
            context = tracer.observe()
        else:
            context = ExitStack()
            context.enter_context(patch.object(transformer, 'checkpoint', eager_checkpoint))
            context.enter_context(patch.object(checkpoint_api, 'checkpoint', eager_checkpoint))
        with context, model.route_scope(index, total) as receipt:
            x, y, owners = core.pad_records(batch, 0, 'cpu', fixed_width=8, batch_size=8)
            sums, counts = core.components(model, model(x, return_hidden=True), y, owners, horizons=())
            self.assertEqual(counts[1], sum(r.targets for r in batch))
            objective = sums[1] / counts[1]
            objective.backward()
            result = float(objective.detach()), gradients(model), receipt
        if checkpointed:
            tracer.assert_complete(1, 8)
        return result

    def test_balanced_r1_r2_r3_and_two_shuffle_policies_match_eager_loss_and_gradients(self):
        plans = [('balanced_count', i, 4) for i in range(4)]
        plans += [('fixed_shuffle_r2', 0, 8), ('update_shuffle_r2', 0, 8), ('update_shuffle_r2', 1, 8)]
        balanced = []
        for arm, index, total in plans:
            with self.subTest(arm=arm, index=index):
                on, off = model_pair(arm)
                before = torch.random.get_rng_state().clone(); python_before = random.getstate()
                a, ga, receipt = self.one_micro(on, index, total, checkpointed=True)
                b, gb, other = self.one_micro(off, index, total, checkpointed=False)
                self.assertEqual(receipt, other)
                torch.testing.assert_close(torch.tensor(a), torch.tensor(b), atol=ATOL, rtol=RTOL)
                maximum, tensors = self.assert_gradients_equal(ga, gb)
                self.assertTrue(torch.equal(torch.random.get_rng_state(), before))
                self.assertEqual(random.getstate(), python_before)
                if arm == 'balanced_count': balanced.append(receipt['actual_repeats'])
                if arm.endswith('shuffle_r2'): self.assertFalse(receipt['identity_order'])
                OBSERVATIONS.append(dict(kind='one_micro', arm=arm, index=index,
                    repeats=receipt['actual_repeats'], loss_abs_diff=abs(a - b),
                    raw_gradient_max_abs_diff=maximum, gradient_tensors=tensors))
        self.assertEqual(sorted(balanced), [1, 2, 2, 3])

    def full_update(self, model, optimizer, index, total, rows, *, checkpointed):
        expected = route.plan(model.cfg, model.owner, model.policy, index, total)
        tracer = RecomputeTrace(self, model, expected)
        captured = []
        original_clip = torch.nn.utils.clip_grad_norm_
        def capture_clip(parameters, *args, **kwargs):
            captured.append(gradients(model))
            return original_clip(parameters, *args, **kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch.object(torch.nn.utils, 'clip_grad_norm_', capture_clip))
            if checkpointed:
                stack.enter_context(tracer.observe())
            else:
                stack.enter_context(patch.object(transformer, 'checkpoint', eager_checkpoint))
                stack.enter_context(patch.object(checkpoint_api, 'checkpoint', eager_checkpoint))
            result = route.sft_update(model, rows, (optimizer,), index, total,
                                      pad_id=0, width=8, device='cpu', amp=False)
        self.assertEqual(len(captured), 1)
        self.assertEqual(result['assistant_targets'], sum(r.targets for r in rows))
        self.assertEqual(result['actual_rows'], len(rows))
        self.assertEqual(result['dummy_rows'], 128 - len(rows))
        self.assertEqual((result['micro_bs'], result['accum']), (8, 16))
        if checkpointed:
            tracer.assert_complete(16, 8)
        return result, captured[0], tracer

    def test_production_sixteen_micro_update_and_recomputation_keep_one_frozen_route(self):
        for arm in ('balanced_count', 'fixed_shuffle_r2', 'update_shuffle_r2'):
            on, off = model_pair(arm)
            a_opt = torch.optim.SGD(on.parameters(), lr=.01, momentum=.1)
            b_opt = torch.optim.SGD(off.parameters(), lr=.01, momentum=.1)
            a_id, b_id = id(a_opt), id(b_opt)
            if arm == 'balanced_count':
                indices = [next(i for i in range(4) if route.bounded_count(on.policy, i, 4, 'train') == 3)]
                total = 4
            else:
                indices, total = ([0, 1] if arm == 'update_shuffle_r2' else [0]), 8
            for index in indices:
                with self.subTest(arm=arm, index=index):
                    rows = records(103 if arm == 'balanced_count' else 128)
                    before = torch.random.get_rng_state().clone(); python_before = random.getstate()
                    a, ga, trace = self.full_update(on, a_opt, index, total, rows, checkpointed=True)
                    b, gb, _ = self.full_update(off, b_opt, index, total, rows, checkpointed=False)
                    self.assertEqual(a['route'], b['route'])
                    self.assertEqual(a['optimizer_ids'], [a_id]); self.assertEqual(b['optimizer_ids'], [b_id])
                    for key in ('ce', 'gradient_norm', 'gradient_max'):
                        torch.testing.assert_close(torch.tensor(a[key]), torch.tensor(b[key]), atol=ATOL, rtol=RTOL, msg=key)
                    maximum, tensors = self.assert_gradients_equal(ga, gb)
                    parameter_delta = 0.
                    for (name, p), (other_name, q) in zip(on.named_parameters(), off.named_parameters()):
                        self.assertEqual(name, other_name)
                        torch.testing.assert_close(p, q, atol=ATOL, rtol=RTOL, msg=name)
                        parameter_delta = max(parameter_delta, float((p - q).detach().abs().max()))
                    self.assertTrue(torch.equal(torch.random.get_rng_state(), before))
                    self.assertEqual(random.getstate(), python_before)
                    OBSERVATIONS.append(dict(kind='production16micro', arm=arm, index=index,
                        repeats=a['route']['actual_repeats'], real_rows=len(rows),
                        loss_abs_diff=abs(a['ce'] - b['ce']), raw_gradient_max_abs_diff=maximum,
                        gradient_tensors=tensors, parameter_max_abs_diff=parameter_delta,
                        checkpoint_calls=trace.serial, recompute_calls=len(trace.recompute)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
