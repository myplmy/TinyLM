#!/usr/bin/env python3
"""새595 recipe/controller의 작은 CPU/temp 계약. 실물 bin/CP/TinyLM 모델/GPU0."""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native595 as d


class Fixture:
    def __init__(self, directory, info):
        import numpy as np
        from scripts import diag_p106b_native_weight_route as n
        from scripts.p106b_shards import verify
        self.root = Path(directory); self.n = n
        self.original_required = d.required
        def required(path):
            path = Path(path)
            if path.is_relative_to(self.root): return json.loads(path.read_text(encoding='utf-8'))
            return self.original_required(path)
        self.required_patch = patch.object(d, 'required', required); self.required_patch.start()
        namespace = dict(vars(n)); namespace.update(required=required, safe=lambda path: Path(path), verify=verify)
        reader = types.FunctionType(n.read_events.__code__, namespace)
        facade = types.SimpleNamespace(**{name: getattr(n, name) for name in ('Pending', 'schedule', 'make_offsets', 'finite',
            'validate_optimizer_groups', 'actual_lrs', 'validate_route_receipt', 'validate_native32', 'fingerprint',
            'modules', 'termination_guard', 'launch', 'pipeline')}, read_events=reader)
        self.p = d.Runtime(facade, None, None, [], self.root); self.p.info = lambda: deepcopy(info)
        self.p.authority = lambda training=False, now=None: 999999.
        self.offsets = np.arange(d.RECIPE.crops, dtype=np.int64)
        self.reference = dict(cpu_consumer_seconds=.1, synthetic_fixture=True)
        self.p.write(self.p.CACHE / 'reference.json', self.reference)

    def close(self): self.required_patch.stop()

    def groups(self):
        rows = []
        for name, lr, wd, scale in (('AdamW', .001, .1, None), ('Muon', .004, 0., 'rms')):
            rows.append(dict(optimizer=name, group=0, lr=lr, runtime_lr=lr / 10, runtime_weight_decay=wd,
                weight_decay=wd, lr_multiplier=10., parameters=4, names_sha256='A' * 64, scale_mode=scale))
        return rows

    def native32(self): return dict(ce=1., windows=32, targets=32768, val_sha256=d.RECIPE.val_sha256, precision='FP32_MATH')

    def finish(self, *, cost=True):
        from scripts.p106b_shards import ShardWriter
        arm, mode = 'float', 'cost' if cost else 'train'; count = 8 if cost else 4543
        groups = self.groups(); method = self.n.modules()[2]
        route = dict(mode=arm, metadata=method.route_metadata(arm), tlinear_instances=1, owned_tlinear_instances=1,
            refreshed_tlinear_instances=1, forward_methods=['_guarded_forward'], refresh_methods=['_float_refresh'])
        core = 'B' * 64; writer = ShardWriter(self.p.RAW / d.key(mode, arm), 'updates', limit=19_999_999)
        for step in range(count):
            contract = d.RECIPE.update(self.n, step)
            writer.append(dict(update=step + 1, **contract, ce=1., gradient_norm=.5, clipped=False, step_seconds=.01,
                crop_offsets_sha256=d.sha([int(v) for v in self.offsets[step * 128:(step + 1) * 128]]),
                actual_lrs=self.n.actual_lrs(groups, contract['schedule']['lr_factor'])))
        manifest = writer.close(lineage=dict(tag=d.TAG, arm=arm, cost=cost, reference_sha256=d.file_sha(self.p.CACHE / 'reference.json')))
        late = dict(optimizer_updates=0, micro_batches=1, targets=8192, anneal=1., finite=True, core_before=core, core_after=core,
            source_offsets_sha256=d.sha([int(v) for v in self.offsets[:8]]), gradient_norm=.5, seconds=1., peak_allocated_mib=1., peak_reserved_mib=2.)
        cache = dict(optimizer_updates=0, quality_forwards=0, finite=True, core_before=core, core_after=core, route=route,
            cache_tensors=1, seconds=1., cache_nominal_bytes=16, extra_cache_storage_bytes=0, peak_allocated_mib=1., peak_reserved_mib=2.)
        report = dict(self.p.info(), status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE', cost=cost, arm=arm, updates=count,
            reference_sha256=d.file_sha(self.p.CACHE / 'reference.json'), initial_core_sha256=d.RECIPE.scratch_core_sha256,
            final_core_sha256=core, parent_checkpoint_sha256=None, parent_core_sha256=None, checkpoint_writes=0 if cost else 1,
            optimizer_saved=False, event_manifest=manifest, actual_optimizer_groups=groups,
            actual_optimizer_classes=['torch.optim.adamw.AdamW', 'tinylm.train.muon.Muon'], step_seconds=[.01] * count,
            grad_max=.5, clip_events=0, totals=dict(targets=count * d.RECIPE.targets, x_tokens=count * d.RECIPE.targets),
            quantization_route=method.route_metadata(arm), route=route, late_probe=late if cost else None,
            cache_audit=cache if cost else None, native32_fp32=None if cost else self.native32())
        if not cost:
            target = self.p.checkpoint(arm); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b'tiny non-model fixture')
            report.update(checkpoint=str(target.relative_to(self.root)), checkpoint_sha256=d.file_sha(target))
        self.p.write(self.p.path(mode, arm), report)
        return report

    def activity(self, mode='cost', *, complete=True):
        now = datetime.now(timezone.utc).isoformat(); path = self.p.path(mode, 'float')
        value = dict(schema=d.SCHEMA, tag=d.TAG, key=d.key(mode, 'float'), mode=mode, arm='float',
            code_sha256=self.p.info()['code_sha256'], seconds=.1, max_wall_sec=900 if mode == 'cost' else 18000,
            returncode=0 if complete else 9, complete=complete, error_type=None if complete else 'RuntimeError',
            started_at=now, ended_at=now, pid=7, pgid=7, result_sha256=d.file_sha(path) if path.is_file() else None,
            reference_sha256=d.file_sha(self.p.CACHE / 'reference.json'))
        self.p.write(self.p.EVIDENCE / ('activity_' + d.key(mode, 'float') + '.json'), value); return value

    def read(self, cost=True): return d.read_training(self.p, 'float', cost=cost, state=(self.reference, self.offsets))


def worker_fixture(mode, info, *, term=False):
    with tempfile.TemporaryDirectory(prefix='native595_worker_') as directory:
        f = Fixture(directory, info)
        try:
            def finish(_p, _arm, **kw):
                if term: os.kill(os.getpid(), signal.SIGTERM)
                f.finish(cost=kw['cost']); return 0
            with patch.object(d, 'train', finish):
                try: code = d.worker(f.p, mode, 'float', 900)
                except BaseException as exc:
                    value = d.required(f.p.EVIDENCE / ('activity_' + d.key(mode, 'float') + '.json'))
                    print(json.dumps(dict(error=type(exc).__name__, activity=value)), flush=True)
                    return 130 if isinstance(exc, KeyboardInterrupt) else 9
            with patch.object(d, 'prepared', return_value=(f.reference, f.offsets)):
                d.verify(f.p, mode, 'float', 900)
            report = f.read(mode == 'cost')
            print(json.dumps(dict(returncode=code, strict_updates=report['updates'], complete=f.p.completed(mode, 'float')['complete'])), flush=True)
            return 0
        finally: f.close()


class RecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.p = d.build_runtime()

    def test_exact_geometry_source_and_no_controller_rebind(self):
        r = d.RECIPE
        self.assertEqual(r.draw, 595460096); self.assertEqual(r.crops, 581504)
        self.assertEqual(r.pool_train_ids - 2 * r.draw, 196000)
        self.assertEqual(self.p.n.UPDATES, 2281); self.assertEqual(self.p.n.TRAIN_TOKENS, 597995000)
        self.p.check()

    def test_explicit_captured_defaults_are_overridden_by_arguments(self):
        seen = {}
        fake = types.SimpleNamespace(make_offsets=lambda **kw: seen.update(kw), schedule=lambda step, **kw: (step, kw))
        d.RECIPE.offsets(fake)
        self.assertEqual(seen, dict(pool_tokens=1191116192, updates=4543, micro=8, accum=16, seq=1024, seed=1337))
        self.assertEqual(d.RECIPE.schedule(fake, 4542), (4542, dict(updates=4543)))

    def test_full_offset_count_seed_bounds_and_pool2x(self):
        import numpy as np
        a, desc = d.RECIPE.offsets(self.p.n); b, _ = d.RECIPE.offsets(self.p.n)
        self.assertEqual(a.dtype, np.int64); self.assertEqual(len(a), 581504); self.assertTrue(np.array_equal(a, b))
        self.assertEqual(desc['draw_tokens'], 595460096); self.assertEqual(desc['pool_slack'], 196000)
        self.assertTrue(bool((a >= 0).all())); self.assertTrue(bool((a + 1025 <= d.RECIPE.pool_train_ids).all()))
        with self.assertRaises(ValueError): self.p.n.make_offsets(pool_tokens=1191116192, updates=4544, micro=8, accum=16, seq=1024, seed=1337)

    def test_schedule_boundary_wsd_and_quant(self):
        for step in (0, 7, 99, 100, 327, 4542):
            self.assertEqual(d.RECIPE.schedule(self.p.n, step), self.p.n.schedule(step, updates=4543))
        self.assertEqual(d.RECIPE.schedule(self.p.n, 0)['lr_factor'], .01)
        self.assertEqual(d.RECIPE.schedule(self.p.n, 100)['quant_start'], 100 / 4543 + .05)
        self.assertEqual(d.RECIPE.schedule(self.p.n, 4542)['anneal'], 1.)
        with self.assertRaises(ValueError): d.RECIPE.schedule(self.p.n, 4543)

    def test_full_info_json_no_planned_actual_collision(self):
        value = self.p.info(); self.assertEqual(value, json.loads(json.dumps(value, ensure_ascii=False)))
        self.assertNotIn('updates', value); self.assertEqual(value['native_recipe']['updates'], 4543)
        self.assertEqual(value['limits']['followup_training_reserved_seconds'], 7200)

    def test_check_only_assets_forbidden(self):
        with patch.object(d, 'source_state', side_effect=AssertionError('실물0')), patch.object(d, 'prepared', side_effect=AssertionError('실물0')):
            with patch('sys.stdout', io.StringIO()): self.assertEqual(d.main(['--mode', 'source', '--check-only']), 0)

    def test_native_and_global_deadlines(self):
        self.assertEqual(self.p.authority(True, d.NATIVE_STOP - timedelta(seconds=1)), 1)
        with self.assertRaises(self.p.Pending): self.p.authority(True, d.NATIVE_STOP)
        with self.assertRaises(self.p.Pending): self.p.authority(False, d.END - timedelta(seconds=600))

    def test_modes_caps_and_unused_arm(self):
        for mode, cap in (('cost', 901), ('train', 18001), ('evaluate', 1201)):
            with self.assertRaises(ValueError): d.commands(mode, 'float', cap)
        with self.assertRaises(ValueError): d.commands('source', 'float', 900)
        self.assertEqual([a for a, _ in d.commands('train', 'float', 18000)], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])

    def test_source_auditor_wrong_hash_or_nonzero_result_before_binary(self):
        for report_sha, code in (('A' * 64, 0), (d.AUDIT_SHA, 8)):
            calls = []
            fake = types.SimpleNamespace(audit=types.SimpleNamespace(closed_result=lambda _: code))
            with patch.object(d, 'required', return_value=dict(info={})), patch.object(d, 'file_sha', side_effect=lambda path: calls.append(path) or report_sha):
                with self.assertRaises(ValueError): d.source_state(fake)
            self.assertEqual(calls, [d.AUDIT_REPORT])

    def test_source_meta_val0_and_exact_pool_checked_before_binary(self):
        good = dict(train=d.RECIPE.pool_train_ids, val=0, train_sha256=d.RECIPE.pool_sha256,
            tokenizer_sha256=d.RECIPE.tokenizer_sha256, current_val_sha256=d.RECIPE.val_sha256)
        fake = types.SimpleNamespace(audit=types.SimpleNamespace(closed_result=lambda _: 0, preflight_after_claim=lambda: None))
        for changes in (dict(val=3005000), dict(train=597995000), dict(train_sha256='A' * 64), dict(current_val_sha256='B' * 64)):
            calls = []
            with patch.object(d, 'required', side_effect=lambda path: dict(info={}) if path == d.AUDIT_REPORT else dict(good, **changes)), \
                    patch.object(d, 'file_sha', side_effect=lambda path: calls.append(path) or d.AUDIT_SHA):
                with self.assertRaises(ValueError): d.source_state(fake)
            self.assertEqual(calls, [d.AUDIT_REPORT])


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.info = d.build_runtime().info()
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='native595_fixture_'); self.f = Fixture(self.tmp.name, self.info)
    def tearDown(self): self.f.close(); self.tmp.cleanup()

    def test_real_cost_reader_requires_closed_activity(self):
        self.f.finish()
        with self.assertRaises(FileNotFoundError): self.f.read()
        self.f.activity(); self.assertEqual(self.f.read()['updates'], 8)

    def test_actual4543_raw_counts_and_schedule_recount(self):
        report = self.f.finish(cost=False); self.f.activity('train')
        self.assertEqual(self.f.read(False)['totals']['targets'], 595460096)
        self.assertEqual(report['updates'], 4543)

    def test_cost_auxiliary_is_separate_and_core_bound(self):
        report = self.f.finish(); self.f.activity()
        self.assertEqual(self.f.read()['totals']['targets'], 1048576)
        for name, field, bad in (('late_probe', 'optimizer_updates', 1), ('late_probe', 'core_after', 'A' * 64),
                ('late_probe', 'targets', 1048576), ('cache_audit', 'quality_forwards', 1), ('cache_audit', 'seconds', -1.),
                ('cache_audit', 'seconds', 0.), ('cache_audit', 'seconds', float('nan')), ('cache_audit', 'seconds', float('inf'))):
            value = deepcopy(report); value[name][field] = bad
            with self.assertRaises(ValueError): d.validate_auxiliary(self.f.p, value, self.f.offsets)

    def test_header_wrong_source_tag_parent_and_step_rejected(self):
        self.f.finish(); self.f.activity(); original = d.required
        for name, bad in (('tag', 'old'), ('updates', 2281), ('initial_core_sha256', 'A' * 64), ('parent_core_sha256', 'legacy')):
            def read(path, name=name, bad=bad):
                value = original(path)
                if Path(path) == self.f.p.path('cost', 'float'): value[name] = bad
                return value
            with patch.object(d, 'required', read):
                with self.assertRaises(ValueError): self.f.read()

    def test_failed_activity_counted_once_and_not_complete(self):
        self.f.activity(complete=False)
        self.assertEqual(self.f.p.spent(), .1)
        with self.assertRaises(ValueError): self.f.p.completed('cost', 'float')

    def test_activity_cap_and_stop_tamper(self):
        value = self.f.activity(complete=False)
        for changes in (dict(seconds=950), dict(started_at=d.NATIVE_STOP.isoformat()), dict(pgid=8)):
            with self.assertRaises(ValueError): d.validate_activity(self.f.p, dict(value, **changes), 'cost', 'float')

    def test_source_reference_and_writeonce(self):
        self.f.finish(); self.f.activity(); original = d.required
        with patch.object(d, 'required', side_effect=lambda path: dict(original(path), damaged=True) if Path(path) == self.f.p.CACHE / 'reference.json' else original(path)):
            with self.assertRaises(ValueError): self.f.read()
        with self.assertRaises(FileExistsError): self.f.finish()

    def test_budget_slow_cost_holds_and_reserves_followup(self):
        cost = dict(step_seconds=[30.] + [3.] * 7, late_probe=dict(seconds=1.), cache_audit=dict(seconds=1.))
        with patch.object(d, 'prepared', return_value=(self.f.reference, self.f.offsets)), patch.object(d, 'read_training', return_value=cost):
            value = d.budget(self.f.p)
        self.assertFalse(value['fits']); self.assertGreater(value['total_reserved_seconds'], 43200)
        cost['step_seconds'] = [30.] + [1.] * 7
        with patch.object(d, 'prepared', return_value=(self.f.reference, self.f.offsets)), patch.object(d, 'read_training', return_value=cost):
            value = d.budget(self.f.p)
        self.assertGreater(value['total_reserved_seconds'], sum(value['estimates_seconds'].values()) + 9000)


class NumericTests(unittest.TestCase):
    def test_original_native_optimizer_matrix_units_and_wd(self):
        import torch
        from scripts import diag_p106b_native_weight_route as n
        class Small(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.embed = torch.nn.Embedding(4, 2); self.head = torch.nn.Linear(2, 2)
            def param_groups(self, lr):
                return [dict(params=[self.embed.weight, self.head.weight], lr=lr, weight_decay=.1), dict(params=[self.head.bias], lr=lr, weight_decay=0.)]
        model = Small(); opts, groups = n.make_optimizers(model, 'native')
        self.assertEqual(d.optimizer_classes(opts), ['torch.optim.adamw.AdamW', 'tinylm.train.muon.Muon'])
        self.assertIn(.1, [g['weight_decay'] for g in groups if g['optimizer'] == 'AdamW'])
        self.assertEqual(opts[1].param_groups[0]['scale_mode'], 'rms')
        self.assertEqual((opts[1].param_groups[0]['momentum'], opts[1].param_groups[0]['nesterov'], opts[1].param_groups[0]['ns_steps']), (.95, True, 5))
        self.assertEqual(opts[1].param_groups[0]['params'][0].ndim, 2)

    def test_given_model_cost8_updates16micro_and_lr(self):
        import numpy as np
        import torch
        from scripts import diag_p106b_native_weight_route as n
        model = torch.nn.Linear(2, 2); model.set_anneal = lambda value: None
        opts = (torch.optim.AdamW([model.bias], lr=.001),)
        from tinylm.train.muon import Muon
        opts += (Muon([model.weight], lr=.004, scale_mode='rms'),)
        observed = []
        def backward(model, forward, records, denominator, torch):
            observed.append(denominator)
            loss = sum(v.square().sum() for v in model.parameters()) / denominator; loss.backward()
            return float(loss.detach()) * denominator, 8192, 8192
        native = types.SimpleNamespace(schedule=n.schedule, native_records=lambda tokens, chosen: [None] * len(chosen), backward_micro=backward)
        fake_torch = types.SimpleNamespace(nn=torch.nn, isfinite=torch.isfinite, cuda=types.SimpleNamespace(synchronize=lambda: None))
        with tempfile.TemporaryDirectory(prefix='native595_loop_') as directory:
            root = Path(directory); cache = root / 'cache'; cache.mkdir(); (cache / 'reference.json').write_text('{}')
            p = types.SimpleNamespace(n=native, authority=lambda *_: None, base_lrs=[[.001], [.004]], CACHE=cache)
            route = types.SimpleNamespace(mode='float', assert_active=lambda: None)
            with patch('sys.stdout', io.StringIO()):
                result = d.train_updates(p, fake_torch, model, model, None, np.arange(1024), opts, route, root / 'raw', cost=True)
            self.assertEqual(result['updates'], 8); self.assertEqual(len(observed), 128)
            self.assertEqual(set(observed), {131072}); self.assertEqual(result['totals']['targets'], 1048576)
            self.assertTrue(all(float(v['step']) == 8 for v in opts[0].state.values()))

    def test_original_late_probe_restores_anneal_zero_grad_and_no_step(self):
        import numpy as np
        import torch
        from scripts import diag_p106b_native_weight_route as n
        model = torch.nn.Linear(2, 2); model.cfg = types.SimpleNamespace(quant_anneal=.25)
        model.clear_quant = lambda: None; model.set_anneal = lambda value: setattr(model.cfg, 'quant_anneal', value)
        opts = (torch.optim.SGD(model.parameters(), lr=.001),)
        def backward(model, forward, records, denominator, torch):
            self.assertEqual(model.cfg.quant_anneal, 1.); self.assertEqual(denominator, 8192)
            sum(v.square().sum() for v in model.parameters()).backward(); return 8192., 8192, 8192
        namespace = dict(vars(n)); namespace.update(modules=lambda: (types.SimpleNamespace(state_fingerprint=lambda _: 'A' * 64), None, None), backward_micro=backward)
        function = types.FunctionType(n.late_probe.__code__, namespace)
        facade = types.SimpleNamespace(nn=torch.nn, isfinite=torch.isfinite, cuda=types.SimpleNamespace(reset_peak_memory_stats=lambda: None,
            synchronize=lambda: None, max_memory_allocated=lambda: 1024, max_memory_reserved=lambda: 2048))
        before = [v.detach().clone() for v in model.parameters()]
        result = function(facade, model, model, opts, np.ones(1025, dtype=np.uint16), np.zeros(8, dtype=np.int64))
        self.assertEqual(result['optimizer_updates'], 0); self.assertEqual(result['targets'], 8192)
        self.assertEqual(model.cfg.quant_anneal, .25); self.assertTrue(all(v.grad is None for v in model.parameters()))
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(before, model.parameters())))

    def test_original_cache_audit_restores_without_forward_or_step(self):
        import torch
        from scripts import diag_p106b_native_weight_route as n
        model = torch.nn.Module(); model.head = torch.nn.Linear(2, 2); model.cfg = types.SimpleNamespace(quant_anneal=.25)
        route = types.SimpleNamespace(mode='float', metadata=n.modules()[2].route_metadata('float'),
            linears=(model.head,), _versions={}, assert_active=lambda: None)
        def _guarded_forward(_module, *args): raise AssertionError('품질 forward0')
        def _float_refresh(_module): raise AssertionError('직접 refresh0')
        model.head.forward = types.MethodType(_guarded_forward, model.head)
        model.head.refresh_quant = types.MethodType(_float_refresh, model.head)
        model.head._p106b_weight_route = route
        model.clear_quant = lambda: setattr(model.head, '_wq', None)
        model.set_anneal = lambda value: setattr(model.cfg, 'quant_anneal', value)
        def freeze():
            model.head._wq = model.head.weight.detach(); route._versions[id(model.head)] = model.head.weight._version
        model.freeze_quant = freeze
        namespace = dict(vars(n)); namespace['modules'] = lambda: (types.SimpleNamespace(state_fingerprint=lambda _: 'A' * 64), None, None)
        function = types.FunctionType(n.cache_audit.__code__, namespace)
        facade = types.SimpleNamespace(no_grad=torch.no_grad, autocast=lambda *a, **kw: nullcontext(), isfinite=torch.isfinite,
            cuda=types.SimpleNamespace(reset_peak_memory_stats=lambda: None, synchronize=lambda: None,
                max_memory_allocated=lambda: 1024, max_memory_reserved=lambda: 2048))
        before = [v.detach().clone() for v in model.parameters()]
        result = function(facade, model, route)
        self.assertEqual((result['optimizer_updates'], result['quality_forwards']), (0, 0))
        self.assertEqual((result['cache_tensors'], result['cache_nominal_bytes'], result['extra_cache_storage_bytes']), (1, 16, 0))
        self.assertEqual(model.cfg.quant_anneal, .25); self.assertTrue(model.training); self.assertIsNone(model.head._wq)
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(before, model.parameters())))

    def test_cost_auxiliary_original_order_and_exact_source_arguments(self):
        seen = []; inputs = [object() for _ in range(6)]; torch, model_id, forward, optimizers, tokens, offsets = inputs
        model = types.SimpleNamespace(clear_quant=lambda: seen.append('clear'), set_anneal=lambda value: seen.append(('anneal', value)))
        route = object()
        def late(*args):
            self.assertEqual(args, (torch, model, forward, optimizers, tokens, offsets)); seen.append('late'); return 'late_result'
        def cache(*args):
            self.assertEqual(args, (torch, model, route)); seen.append('cache'); return 'cache_result'
        def fingerprint(value): self.assertIs(value, model); seen.append('core'); return 'A' * 64
        native = types.SimpleNamespace(late_probe=late, cache_audit=cache, native_probe=lambda *_: self.fail('cost 품질평가0'),
            modules=lambda: (types.SimpleNamespace(state_fingerprint=fingerprint), None, None))
        result = d.finish_auxiliary(types.SimpleNamespace(n=native), torch, model, forward, optimizers, tokens, offsets, route, cost=True)
        self.assertEqual(seen, ['late', 'clear', ('anneal', 1.), 'core', 'cache'])
        self.assertEqual(result, ('late_result', 'A' * 64, None, 'cache_result'))


class PayloadIdleTests(unittest.TestCase):
    @dataclass
    class Config:
        dim: int = 2

    def test_strict_cp_step_tag_route_and_optimizer(self):
        from scripts import diag_p106b_native_weight_route as n
        p = types.SimpleNamespace(n=n)
        report = dict(tag=d.TAG, arm='float', updates=4543, initial_core_sha256=d.RECIPE.scratch_core_sha256,
            final_core_sha256='B' * 64, parent_checkpoint_sha256=None, parent_core_sha256=None, reference_sha256='C' * 64, optimizer_saved=False)
        payload = dict(model={}, cfg=dict(dim=2), step=4543, tokenizer_sha256=d.RECIPE.tokenizer_sha256,
            tokenizer_lineage='chat32', quantization_route=n.modules()[2].route_metadata('float'), experiment=d.cp_experiment(report))
        d.validate_payload(p, payload, self.Config(), 'float', report)
        for field, bad in (('step', 2281), ('cfg', dict(dim=3)), ('experiment', dict(payload['experiment'], tag='old'))):
            value = dict(payload, **{field: bad})
            with self.assertRaises(ValueError): d.validate_payload(p, value, self.Config(), 'float', report)
        with self.assertRaises(RuntimeError): n.modules()[2].generic_loader_guard(payload)
        value = dict(payload, optimizer={})
        with self.assertRaises(ValueError): d.validate_payload(p, value, self.Config(), 'float', report)

    def test_cpu_state_dtype_shape_and_alias(self):
        import torch
        from scripts import diag_p106b_native_weight_route as n
        model = torch.nn.Module(); model.a = torch.nn.Linear(2, 2); model.b = model.a
        original = {k: v.clone() for k, v in model.state_dict().items()}
        n.validate_cpu_state(model, dict(model=original), torch)
        for key, value in (('a.weight', torch.zeros(3, 2)), ('a.weight', original['a.weight'].double()), ('b.weight', original['b.weight'] + 1)):
            with self.assertRaises(ValueError): n.validate_cpu_state(model, dict(model=dict(original, **{key: value})), torch)

    def test_idle_full_map_and_protected_paths_before_read(self):
        for value in ('datasets/TinyDataset/a.json', '.aws/a.json', '/etc/a.json', d.IDLE_DIR + '/../a.json', d.IDLE_DIR + '/.claude/a.json'):
            with self.assertRaises(ValueError): d.idle_path(value)
        now = datetime(2026, 10, 20, 20, tzinfo=timezone.utc)
        full_code = d.build_runtime().info()['code_sha256']
        proof = dict(schema='P106B_ROOT_IDLE_V1', tag=d.TAG, arm='float', key='cost_float', code_sha256=full_code,
            start_utc=(now - timedelta(seconds=310)).isoformat(), end_utc=(now - timedelta(seconds=10)).isoformat(),
            start_monotonic=100., end_monotonic=400., no_gpu_work=True, no_heavy_cpu=True,
            evidence=[dict(path=d.IDLE_DIR + '/obs.json', sha256='B' * 64)])
        p = types.SimpleNamespace(info=lambda: dict(code_sha256=full_code))
        with patch.object(d, 'required', return_value=proof), patch.object(Path, 'stat', return_value=types.SimpleNamespace(st_size=1)), patch.object(d, 'file_sha', return_value='B' * 64), patch.object(d, 'idle_path', side_effect=lambda v: Path(v)):
            self.assertEqual(d.idle_proof(p, d.IDLE_DIR + '/idle_float.json', 'float', now=now, monotonic=410.), proof)
            proof['code_sha256'] = 'A' * 64
            with self.assertRaises(ValueError): d.idle_proof(p, d.IDLE_DIR + '/idle_float.json', 'float', now=now, monotonic=410.)

    def test_idle_proof_path_rejected_before_json_or_hash(self):
        for relative in ('datasets/TinyDataset/idle_float.json', '.aws/idle_float.json', '.claude/idle_float.json',
                '/etc/idle_float.json', d.IDLE_DIR + '/../idle_float.json'):
            with patch.object(d, 'required', side_effect=AssertionError('읽기 전 거부')), patch.object(d, 'file_sha', side_effect=AssertionError('해시 전 거부')):
                with self.assertRaises(ValueError): d.idle_proof(None, relative, 'float')


class ProcessTests(unittest.TestCase):
    def child(self, mode, term=False):
        info = d.build_runtime().info()
        code = 'from scripts.test_p106b_native595 import worker_fixture; raise SystemExit(worker_fixture(' + repr(mode) + ',' + repr(info) + ',term=' + repr(term) + '))'
        return subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=ROOT, stdin=subprocess.DEVNULL,
            start_new_session=True, capture_output=True, text=True, timeout=40,
            env=dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1'))

    def test_cost_worker_closes_then_real_strict_reader(self):
        result = self.child('cost'); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = json.loads(result.stdout.splitlines()[-1]); self.assertTrue(value['complete']); self.assertEqual(value['strict_updates'], 8)

    def test_train4543_worker_closes_then_real_strict_reader(self):
        result = self.child('train'); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout.splitlines()[-1])['strict_updates'], 4543)

    def test_term_failed_activity_preserved(self):
        result = self.child('cost', True); self.assertEqual(result.returncode, 130, result.stdout + result.stderr)
        self.assertFalse(json.loads(result.stdout.splitlines()[-1])['activity']['complete'])

    def test_three_phase_verify_failure_and_no_duplicate(self):
        command = d.commands('train', 'float', 18000)[-1][1]
        for codes, expected, count in (([0, 0], 0, 2), ([0, 8], 9, 2), ([9], 9, 1)):
            iterator = iter(codes); seen = []
            p = types.SimpleNamespace(authority=lambda: 999999., n=types.SimpleNamespace(launch=lambda c, t: seen.append(c) or next(iterator)))
            with patch('sys.stdout', io.StringIO()): self.assertEqual(d.launch_stage(p, command, 18000), expected)
            self.assertEqual(len(seen), count)
            if count == 2: self.assertIn('--verify-only', seen[-1]); self.assertNotIn('--worker', seen[-1])


if __name__ == '__main__': unittest.main()
