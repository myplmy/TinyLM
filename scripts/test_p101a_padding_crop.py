#!/usr/bin/env python3
"""Root-run synthetic CPU regression; constructing this file is NOT a PASS.

Compare identical ordered eight-slot micros and whole-128-record denominators
at width1024 versus ceil(max real x length /128)*128. No optimizer step, data
asset, learned checkpoint, CUDA, torch.compile, timing or quality benchmark.
The random tiny model/CPU forward-backward tests must be run by the root only.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

import torch
from scripts import diag_p101a_sft_mtp as driver
from scripts import test_p101a_sft_mtp as prior_mtp
from scripts import test_p070b_cla_routes as prior_cla
from tinylm.chat.serialize import SPECS, loss_spans
from tinylm.data.prepare import SyntheticTokenizer
from tinylm.data.sft import IGNORE, encode_conversation
from tinylm.model import TiedMLPTransformer
from tinylm.train import mtp_sft as core

PAD, FIXED, QUANTUM, MICRO = 0, 1024, 128, 8
HORIZONS = (1, 2, 3, 4)
# These are existing regression rules, not new training/production thresholds.
# Prefix/CLA/checkpoint: scripts/test_p070b_cla_routes.py ATOL/RTOL.
# Whole-update accumulation: prior_mtp.Contracts.test_accumulated_gradient_matches_combined_update.
ACCUM_ATOL, ACCUM_RTOL = 2e-6, 1e-5
DEPENDENCIES = (
    'scripts/test_p101a_padding_crop.py', 'scripts/test_p101a_sft_mtp.py',
    'scripts/test_p070b_cla_routes.py', 'scripts/p070b_cla_routes.py',
    'scripts/diag_p101a_sft_mtp.py', 'tinylm/train/mtp_sft.py',
    'tinylm/model/transformer.py', 'tinylm/model/modules.py', 'tinylm/model/ternary.py',
    'tinylm/model/ternary_kernel.py', 'tinylm/config.py', 'tinylm/data/sft.py',
    'tinylm/data/prepare.py', 'tinylm/chat/serialize.py', 'tinylm/chat/canonical.py',
)


def dependency_hashes():
    """Code files only; no data tree, tokenizer file, CP or artifact traversal."""
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest().upper() for name in DEPENDENCIES}


def encoded_fixture():
    tok = SyntheticTokenizer(vocab_size=31, span=31)
    rows, records = [], []
    for index in range(128):
        question = 'question' + str(index) + ('x' * 130 if index % 16 == 15 else '')
        messages = [dict(role='user', content=question), dict(role='assistant', content='answer' + str(index))]
        if index % 16 == 8:
            messages.extend((dict(role='user', content='changed condition'), dict(role='assistant', content='updated answer')))
        row = dict(messages=messages)
        rows.append(row); records.append(core.encode_record(row, tok, context=FIXED))
    return tok, rows, records


def record_snapshot(records): return [(r.x[:], r.y[:], r.segments[:]) for r in records]


def denominators(records):
    return {h: sum(core.count_record(r)[h] for r in records) for h in HORIZONS}


def crop_width(records):
    longest = max(len(r.x) for r in records)
    return QUANTUM * ((longest + QUANTUM - 1) // QUANTUM)


def tensors(records, width):
    return core.pad_records(records, PAD, 'cpu', fixed_width=width, batch_size=MICRO)


def random_tiny(cla=1, repeat=1., checkpoint=False):
    # The existing fixture supplies geometry and auxiliary-head policy. Follow
    # its existing CLA/repeat reconstruction pattern; no saved weights loaded.
    seed_model, cfg = prior_mtp.tiny(True)
    del seed_model
    cfg.max_seq_len = FIXED; cfg.cla_group = cla; cfg.train_repeat = repeat
    cfg.grad_checkpoint = checkpoint
    torch.manual_seed(17)
    model = TiedMLPTransformer(cfg); model.train()
    return model


def gradients(model):
    return {name: None if p.grad is None else p.grad.detach().clone() for name, p in model.named_parameters()}


class PaddingCrop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code_before = dependency_hashes()
        print('[PADDING_CROP_CODE_HASHES] ' + json.dumps(cls.code_before, sort_keys=True), flush=True)

    @classmethod
    def tearDownClass(cls):
        if dependency_hashes() != cls.code_before: raise AssertionError('source changed during synthetic regression')

    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for name in ('load', 'save', 'compile'):
            self.stack.enter_context(patch.object(torch, name, side_effect=AssertionError('no CP/compile: ' + name)))
        self.stack.enter_context(patch.object(torch.cuda, '_lazy_init', side_effect=AssertionError('CUDA forbidden')))
        self.stack.enter_context(patch.object(torch.nn.Module, 'cuda', side_effect=AssertionError('CUDA forbidden')))
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('noninteractive synthetic test')))
        self.observed = {}

    def tearDown(self):
        print('[PADDING_CROP_OBSERVATION] ' + json.dumps(dict(test=self.id(), observations=self.observed,
            model_scope='random tiny CPU only; no learned CP', optimizer_updates=0,
            gpu_calls=0, compile_performance='NOT_RUN', long_term_quality='NOT_RUN'), sort_keys=True), flush=True)

    def close_observed(self, name, left, right, *, atol=None, rtol=None):
        if atol is None: atol = prior_cla.ATOL
        if rtol is None: rtol = prior_cla.RTOL
        self.assertEqual(left.shape, right.shape)
        self.assertTrue(bool(torch.isfinite(left).all())); self.assertTrue(bool(torch.isfinite(right).all()))
        self.observed[name] = dict(max_abs=float((left.detach().double() - right.detach().double()).abs().max())
            if left.numel() else 0., atol=atol, rtol=rtol)
        torch.testing.assert_close(left, right, atol=atol, rtol=rtol)

    def compare_gradients(self, name, left, right, *, atol=None, rtol=None):
        self.assertEqual(set(left), set(right)); count = 0
        for key in left:
            if left[key] is None or right[key] is None:
                self.assertIsNone(left[key], key); self.assertIsNone(right[key], key); continue
            self.close_observed(name + '/' + key, left[key], right[key], atol=atol, rtol=rtol); count += 1
        self.assertGreater(count, 0)
        for horizon in (2, 3, 4):
            self.assertIn('mtp_up' + str(horizon), left)
            self.assertGreater(float(left['mtp_up' + str(horizon)].abs().sum()), 0.)

    def test_fixed128_membership_and_h1_to_h4_counts_survive_all_micro_crops(self):
        _, _, records = encoded_fixture(); before = record_snapshot(records)
        groups = next(driver.batches(records, 0)); repeated = next(driver.batches(records, 0))
        ids = [[id(r) for r in micro] for micro in groups]
        self.assertEqual(ids, [[id(r) for r in micro] for micro in repeated])
        self.assertEqual(len(groups), 16); self.assertTrue(all(len(micro) == MICRO for micro in groups))
        self.assertEqual(len(set(i for micro in ids for i in micro)), 128)
        expected = denominators(records); total_fixed = Counter(); total_crop = Counter(); widths = set()
        for micro in groups:
            width = crop_width(micro); widths.add(width)
            self.assertLessEqual(width, FIXED); self.assertEqual(width % QUANTUM, 0)
            fx, fy, fs = tensors(micro, FIXED); cx, cy, cs = tensors(micro, width)
            for left, right in ((fx, cx), (fy, cy), (fs, cs)):
                torch.testing.assert_close(left[:, :width], right, atol=0, rtol=0)
            for row, record in enumerate(micro):
                self.assertEqual(cx[row, :len(record.x)].tolist(), record.x)
                self.assertEqual(cy[row, :len(record.y)].tolist(), record.y)
                self.assertEqual(cs[row, :len(record.segments)].tolist(), record.segments)
            self.assertTrue(bool(fy[:, width:].eq(IGNORE).all())); self.assertTrue(bool(fs[:, width:].eq(0).all()))
            for h in HORIZONS:
                ft, fv = core.horizon_targets(fy, fs, h); ct, cv = core.horizon_targets(cy, cs, h)
                torch.testing.assert_close(ft[:, :ct.shape[1]], ct, atol=0, rtol=0)
                torch.testing.assert_close(fv[:, :cv.shape[1]], cv, atol=0, rtol=0)
                self.assertFalse(bool(fv[:, cv.shape[1]:].any()))
                total_fixed[h] += int(fv.sum()); total_crop[h] += int(cv.sum())
                self.assertEqual(int(cv.sum()), sum(core.count_record(r)[h] for r in micro))
        self.assertEqual(dict(total_fixed), expected); self.assertEqual(dict(total_crop), expected)
        self.assertEqual(ids, [[id(r) for r in micro] for micro in groups])
        self.assertEqual(record_snapshot(records), before)
        self.observed.update(whole_update_denominators=expected, ordered128_membership_unchanged=True,
            micro_count=16, slots_per_micro=8, crop_widths=sorted(widths))

    def test_shifted_eot_targets_and_assistant_boundaries_survive_crop(self):
        tok, rows, records = encoded_fixture(); record = records[8]; row = rows[8]
        ids, labels, text = encode_conversation(row, tok, 'chatml'); encoded = tok.encode(text)
        self.assertEqual(record.x, ids[:-1]); self.assertEqual(record.y, labels[1:])
        self.assertEqual({s for s in record.segments if s}, {1, 2})
        micro = [record, *records[:6], core.Record([], [], [])]; width = crop_width(micro)
        _, fy, fs = tensors(micro, FIXED); _, cy, cs = tensors(micro, width)
        marker = SPECS['chatml']['end']; eot_windows = 0
        for owner, (_start, end) in enumerate(loss_spans(row, 'chatml'), 1):
            self.assertEqual(text[end - len(marker):end], marker)
            raw_index = max(i for i, (a, b) in enumerate(encoded.offsets) if b > a and b == end)
            target_index = raw_index - 1
            self.assertEqual(record.y[target_index], ids[raw_index]); self.assertEqual(record.segments[target_index], owner)
            self.assertNotEqual(record.y[target_index], IGNORE)
            for h in HORIZONS:
                start = target_index - h + 1
                ft, fv = core.horizon_targets(fy, fs, h); ct, cv = core.horizon_targets(cy, cs, h)
                self.assertTrue(bool(fv[0, start])); self.assertTrue(bool(cv[0, start]))
                self.assertEqual(int(ct[0, start]), ids[raw_index]); self.assertEqual(int(ft[0, start]), ids[raw_index])
                eot_windows += 1
        for h in (2, 3, 4):
            _, valid = core.horizon_targets(cy, cs, h)
            for start in range(len(record.y) - h + 1):
                owners = record.segments[start:start + h]
                if 0 in owners or len(set(owners)) > 1: self.assertFalse(bool(valid[0, start]))
        self.observed.update(eot_endpoint_windows_checked=eot_windows, shifted_once=True, two_assistant_owners=True)

    def test_empty_record_equals_core_dummy_pad_row_and_has_zero_horizon_mass(self):
        _, _, records = encoded_fixture(); real = records[:7]; empty = core.Record([], [], [])
        width = crop_width(real)
        for execution_width in (FIXED, width):
            implicit = tensors(real, execution_width); explicit = tensors(real + [empty], execution_width)
            for left, right in zip(implicit, explicit): torch.testing.assert_close(left, right, atol=0, rtol=0)
            x, y, owners = explicit
            self.assertTrue(bool(x[-1].eq(PAD).all())); self.assertTrue(bool(y[-1].eq(IGNORE).all()))
            self.assertTrue(bool(owners[-1].eq(0).all()))
            for h in HORIZONS:
                target, valid = core.horizon_targets(y, owners, h)
                self.assertFalse(bool(valid[-1].any())); self.assertTrue(bool(target[-1].eq(IGNORE).all()))
        self.assertEqual(core.count_record(empty), dict.fromkeys(HORIZONS, 0))
        self.assertEqual(denominators(records), denominators(records + [empty]))

    def run_micro(self, micro, whole_denominators, width, cla, repeat, checkpoint):
        model = random_tiny(cla, repeat, checkpoint)
        self.assertTrue(all(p.device.type == 'cpu' for p in model.parameters()))
        before = {n: p.detach().clone() for n, p in model.named_parameters()}
        x, y, owners = tensors(micro, width); hidden = model(x, return_hidden=True)
        prefix = hidden[:, :crop_width(micro)].detach().clone()
        sums, counts = core.components(model, hidden, y, owners, checkpoint_heads=checkpoint)
        self.assertEqual(counts, denominators(micro))
        weights = core.coefficients(35, 704)
        loss = core.normalized_loss(sums, whole_denominators, weights); loss.backward()
        result = dict(hidden=prefix, loss=loss.detach().clone(), gradients=gradients(model),
            counts=counts, owners=model.owner[:], schedule=model.visit_schedule())
        for name, value in model.named_parameters():
            torch.testing.assert_close(value.detach(), before[name], atol=0, rtol=0)
        model.clear_quant(); return result

    def test_same_eight_slot_micro_causal_cla_r2_prefix_loss_and_gradient(self):
        _, _, records = encoded_fixture(); whole = denominators(records)
        # Seven encoded conversations plus one deliberately empty execution row.
        # This is a micro contribution scaled by the SAME whole128 denominators,
        # not a claim that127 real conversations equal128 real conversations.
        micro = [*records[8:15], core.Record([], [], [])]; before = record_snapshot(micro)
        for cla, repeat, checkpoint in ((1, 1., False), (2, 1., False), (2, 2., False), (2, 2., True)):
            with self.subTest(cla=cla, repeat=repeat, checkpoint=checkpoint), torch.random.fork_rng(devices=[]):
                left = self.run_micro(micro, whole, FIXED, cla, repeat, checkpoint)
                right = self.run_micro(micro, whole, crop_width(micro), cla, repeat, checkpoint)
                key = f'cla{cla}_R{repeat}_checkpoint{checkpoint}'
                self.assertEqual(left['counts'], right['counts']); self.assertEqual(left['owners'], right['owners'])
                self.assertEqual(left['schedule'], right['schedule'])
                self.assertEqual(len(left['schedule']), 4 if repeat == 1. else 6)
                self.close_observed(key + '/hidden_prefix', left['hidden'], right['hidden'])
                self.close_observed(key + '/whole128_normalized_micro_loss', left['loss'], right['loss'])
                self.compare_gradients(key + '/gradient', left['gradients'], right['gradients'])
        self.assertEqual(record_snapshot(micro), before); self.assertEqual(whole, denominators(records))

    def test_changed_future_pad_values_do_not_change_real_cla_r2_prefix(self):
        _, _, records = encoded_fixture(); micro = [*records[8:15], core.Record([], [], [])]
        with torch.random.fork_rng(devices=[]):
            model = random_tiny(cla=2, repeat=2., checkpoint=False)
            x, _, _ = tensors(micro, FIXED); changed = x.clone()
            for index, record in enumerate(micro): changed[index, len(record.x):] = 30
            with torch.no_grad(): left = model(x, return_hidden=True); right = model(changed, return_hidden=True)
            self.assertEqual(len(model.visit_schedule()), 6)
            for index, record in enumerate(micro):
                if record.x:
                    self.close_observed('poison_future/' + str(index), left[index, :len(record.x)], right[index, :len(record.x)])
            model.clear_quant()

    def test_checkpoint_on_matches_off_for_the_same_cropped_micro(self):
        _, _, records = encoded_fixture(); micro = [*records[8:15], core.Record([], [], [])]
        with torch.random.fork_rng(devices=[]):
            left = self.run_micro(micro, denominators(records), crop_width(micro), 2, 2., False)
            right = self.run_micro(micro, denominators(records), crop_width(micro), 2, 2., True)
            self.close_observed('checkpoint/hidden', left['hidden'], right['hidden'])
            self.close_observed('checkpoint/loss', left['loss'], right['loss'])
            self.compare_gradients('checkpoint/gradient', left['gradients'], right['gradients'])

    def test_full128_accumulated_gradient_keeps_membership_denominators_and_no_step(self):
        # This complete-update case uses128 encoded conversations, not dummy rows.
        _, _, records = encoded_fixture(); before_records = record_snapshot(records)
        whole = denominators(records); weights = core.coefficients(35, 704); results = []
        groups = next(driver.batches(records, 0)); membership = [[id(r) for r in m] for m in groups]
        for cropped in (False, True):
            with torch.random.fork_rng(devices=[]):
                model = random_tiny(cla=2, repeat=2., checkpoint=True)
                before_parameters = {n: p.detach().clone() for n, p in model.named_parameters()}
                total_counts = Counter(); total_loss = 0.
                for micro in groups:
                    x, y, owners = tensors(micro, crop_width(micro) if cropped else FIXED)
                    hidden = model(x, return_hidden=True)
                    sums, counts = core.components(model, hidden, y, owners, checkpoint_heads=True)
                    loss = core.normalized_loss(sums, whole, weights); loss.backward()
                    total_counts.update(counts); total_loss += float(loss.detach())
                self.assertEqual(dict(total_counts), whole)
                for name, value in model.named_parameters():
                    torch.testing.assert_close(value.detach(), before_parameters[name], atol=0, rtol=0)
                results.append(dict(loss=torch.tensor(total_loss, dtype=torch.float64), gradients=gradients(model)))
                model.clear_quant()
        self.assertEqual(membership, [[id(r) for r in m] for m in groups])
        self.assertEqual(record_snapshot(records), before_records); self.assertEqual(denominators(records), whole)
        self.close_observed('full128/loss', results[0]['loss'], results[1]['loss'], atol=ACCUM_ATOL, rtol=ACCUM_RTOL)
        self.compare_gradients('full128/gradient', results[0]['gradients'], results[1]['gradients'],
            atol=ACCUM_ATOL, rtol=ACCUM_RTOL)
        self.observed.update(whole_update_denominators=whole, encoded_conversations=128, micro_count=16,
            checkpoint_backbone=True, checkpoint_heads=True, optimizer_steps=0)


if __name__ == '__main__': unittest.main()
