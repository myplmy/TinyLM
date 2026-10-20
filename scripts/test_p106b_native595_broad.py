#!/usr/bin/env python3
"""작은 CPU/temp fixture만 사용한다. 실제 CP·코퍼스·TinyLM 모델·GPU는 읽지 않는다."""
from __future__ import annotations

from contextlib import contextmanager
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
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native595_broad as d


def synthetic_parent(arm, core='B' * 64):
    tag = d.PARENT_RECIPE['tag']
    value = dict(schema='P106B_NATIVE595_PARENT_DESCRIPTOR_V1', arm=arm, original_tag=tag,
        original_training_updates=4543, original_targets=595460096,
        checkpoint='runs/ckpt/m100s10_ko-en_' + tag + '_' + arm + '_native.pt',
        checkpoint_sha256='E' * 64, core_sha256=core, scratch_core_sha256=d.PARENT_RECIPE['scratch_core_sha256'],
        report='test_result/evidence/' + tag + '/train_' + arm + '/report.json', report_sha256='D' * 64,
        activity='test_result/evidence/' + tag + '/activity_train_' + arm + '.json', activity_sha256='F' * 64,
        reference='data_cache/' + tag + '/reference.json', reference_sha256='A' * 64,
        parent_recipe=d.PARENT_RECIPE, normalization=dict(scratch_core_sha256='upstream.initial_core_sha256',
            core_sha256='upstream.final_core_sha256'), original_report_unchanged=True)
    value['descriptor_sha256'] = d.sha(value)
    return value


class Fixture:
    """실제 completed/strict raw reader를 연결하되 입력과 optimizer만 작은 합성물이다."""
    def __init__(self, directory, metadata):
        import numpy as np
        import torch
        from scripts import diag_p106b_native_weight_route as n
        from scripts import diag_p106b_broad_curriculum as core
        from scripts import diag_p106b_relation_bind as relation
        from scripts.p106b_shards import ShardWriter, verify
        from scripts.p106b_native_windows import IndexedNativeWindows
        self.root = Path(directory); self.torch = torch; self.actual = n; self.metadata = deepcopy(metadata)
        self.old_root = d.ROOT; d.ROOT = self.root
        def safe(path):
            path = Path(path)
            if not path.is_absolute() or not path.is_relative_to(self.root) or '..' in path.parts or path.is_symlink():
                raise ValueError('fixture path')
            return path
        def required(path): return json.loads(safe(path).read_text(encoding='utf-8'))
        # 원 read_rows code를 그대로 쓰고 /tmp 허가와 작은 JSON reader만 fixture에 연결한다.
        read_rows = types.FunctionType(core.monitor.read_rows.__code__, dict(safe=safe, required=required,
            verify=verify, json=json, Pending=n.Pending), name='read_rows')
        native = types.SimpleNamespace(Pending=n.Pending, required=required, safe=safe,
            fingerprint=n.fingerprint, modules=n.modules, validate_route_receipt=n.validate_route_receipt,
            validate_native32=n.validate_native32, termination_guard=n.termination_guard, launch=n.launch,
            TOKENIZER_SHA=n.TOKENIZER_SHA, TRAIN_SHA=n.TRAIN_SHA, VAL_SHA=n.VAL_SHA)
        proxy = types.SimpleNamespace(expected_group=core.expected_group,
            monitor=types.SimpleNamespace(read_rows=read_rows, original=core.monitor.original))
        self.p = d.Runtime(native, types.SimpleNamespace(_resume_assert_unchanged=lambda: None), proxy,
            None, [], {})
        self.p.info = lambda: deepcopy(self.metadata)
        self.p.authority = lambda training=False, now=None: 999999.
        class TinyModel(torch.nn.Sequential):
            def param_groups(self, lr):
                return [dict(params=[self[0].weight, self[1].weight], lr=lr, weight_decay=.1),
                    dict(params=[self[1].bias], lr=lr, weight_decay=0.)]
        self.model = TinyModel(torch.nn.Embedding(4, 2), torch.nn.Linear(2, 2))
        self.optimizers = relation.make_optimizers(self.model)
        self.classes = d.validate_optimizers(self.model, self.optimizers, core.monitor.original.validate_groups)
        self.fingerprint = lambda model: d.sha([v.detach().tolist() for v in model.parameters()])
        self.calls = []; self.fail_cycle = None
        self.offsets = [i * d.WIDTH for i in range(d.WINDOWS)]
        # 작은 상수 window를 공유한다. 원 코퍼스나 bin을 만들지 않는다.
        class TinyWindows:
            def __len__(self): return d.WINDOWS
            def __getitem__(self, index): return np.full(d.WIDTH, index % 32000, dtype=np.uint16)
        self.windows = TinyWindows()
        totals = dict(x_tokens=5405444, assistant_targets=552609, content_targets=523053, eot_targets=29556)
        groups = []
        for index in range(176):
            value = {k: v // 176 + (index < v % 176) for k, v in totals.items()}
            value['assistant_targets'] = value['content_targets'] + value['eot_targets']
            ko = 79952 // 176 + (index < 79952 % 176)
            groups.append(dict(lane='grounded' if index < 128 else 'replay' if index < 160 else 'general', totals=value,
                lane_language=[dict(language='ko', assistant_targets=ko),
                    dict(language='en', assistant_targets=value['assistant_targets'] - ko)]))
        self.bundle = dict(contract=dict(cost_group_ids=[0, 128, 160, 1, 129, 161, 2, 162]),
            course=types.SimpleNamespace(schedules=dict(mixed=[list(range(176)), list(range(175, -1, -1))]),
                report=dict(groups=groups)), dev=[])
        initial = self.fingerprint(self.model)
        parent = {a: synthetic_parent(a, initial) for a in d.ARMS}
        self.frozen = dict(binding=dict(parents=parent, native_train_file='data_cache/ko-en_601000000_chat32/train.bin',
            native_train_offsets=self.offsets, native_selection=dict(offsets_sha256=d.sha(self.offsets)),
            ordered_records_sha256='B' * 64, original_schedules_sha256='C' * 64), cpu_consumer_seconds=.1)
        self.p.write(self.p.CACHE / 'frozen_reference.json', self.frozen)
        self.initial = None
        def given_model(model, cfg, tok, bundle, arm, output, *, cost=False, forward=None, native_windows,
                        optimizers=None, device='cuda', probe=None):
            cycle = len(self.calls); self.calls.append((id(model), id(optimizers), id(optimizers[0]), id(optimizers[1])))
            if self.fail_cycle == cycle: raise RuntimeError('fixture cycle failure')
            writer = ShardWriter(output, 'updates', limit=19_999_999); events = []
            count = 8 if cost else 352
            for index in range(count):
                for i in range(index * 8, (index + 1) * 8): native_windows[i]
                for parameter in model.parameters(): parameter.grad = torch.ones_like(parameter) * .01
                optimizers[0].step(); optimizers[1].step()
                epoch, _, group, values = core.expected_group(bundle, arm, index, cost)
                event = dict(update=index + 1, epoch=epoch + 1, group=group,
                    lane=groups[group]['lane'], positive_rows=128, native_targets=8192,
                    native_indices=list(range(index * 8, (index + 1) * 8)), **values,
                    assistant_ce=1., content_ce=1., eot_ce=1., native_ce=1., gradient_norm=.5,
                    clipped=False, step_seconds=.01)
                writer.append(event); events.append(event)
            manifest = writer.close(lineage=dict(tag=d.TAG, arm='mixed', cost=cost))
            return dict(actual_updates=count, totals={k: sum(v[k] for v in events) for k in d.TOTAL_KEYS},
                step_seconds=[.01] * count, grad_max=.5, clip_events=0, actual_optimizer_groups=optimizers[2],
                history=[] if cost else [dict(epoch=1, updates=176, dev=self.dev(), native=self.native()),
                    dict(epoch=2, updates=352, dev=self.dev(), native=self.native())],
                event_manifest=manifest, update_core_seconds=count * .01 + .1)
        self.p.core.train_updates = given_model
        self.window_patch = patch('scripts.p106b_native_windows.reader', lambda *_args: self.windows)
        self.window_patch.start()

    def dev(self): return dict(rows=0, targets=0, ce=1., content_ce=1., eot_ce=1.)

    def native(self):
        return dict(ce=1., windows=32, targets=32768, val_sha256=self.actual.VAL_SHA, precision='FP32_MATH')

    def close(self):
        self.window_patch.stop(); d.ROOT = self.old_root

    def finish(self, *, arm='float', cost=True):
        # 실제 finish와 마찬가지로 reader를 아직 호출하지 않는다. worker finally 이후 검산한다.
        mode = 'cost' if cost else 'train'; self.calls = []
        directory = self.p.RAW / d.key(mode, arm)
        initial = self.fingerprint(self.model)
        cycles = d.run_cycles(self.p, self.model, None, None, self.bundle, self.windows, self.offsets,
            directory, self.optimizers, cost=cost, fingerprint=self.fingerprint)
        results = [v['core_result'] for v in cycles]
        events = [event for index, result in enumerate(results)
            for event in d.core_rows(self.p, directory / ('cycle' + str(index)), result['event_manifest'], 8 if cost else 352)]
        route = self.actual.modules()[2].route_metadata(arm)
        proof = dict(mode=arm, metadata=route, tlinear_instances=1, owned_tlinear_instances=1,
            refreshed_tlinear_instances=1, forward_methods=['_guarded_forward'],
            refresh_methods=['_float_refresh' if arm == 'float' else '_ternary_refresh'])
        report = dict(self.p.info(), status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE', arm=arm, cost=cost, endpoint='native_broad4',
            updates=8 if cost else 704, reference_sha256=d.file_sha(self.p.CACHE / 'frozen_reference.json'),
            parent_checkpoint_sha256=self.frozen['binding']['parents'][arm]['checkpoint_sha256'], parent_core_sha256=initial,
            parent_report_sha256='D' * 64,
            scratch_core_sha256=d.PARENT_RECIPE['scratch_core_sha256'], initial_core_sha256=initial, final_core_sha256=self.fingerprint(self.model),
            native_offsets_sha256=d.sha(self.offsets), ordered_records_sha256='B' * 64, original_schedules_sha256='C' * 64,
            cycles=cycles, totals={k: sum(r['totals'][k] for r in results) for k in d.TOTAL_KEYS},
            language_assistant_targets=d.language_exposure(self.bundle, events),
            step_seconds=[v for r in results for v in r['step_seconds']], grad_max=.5, clip_events=0,
            actual_optimizer_groups=self.optimizers[2], actual_optimizer_classes=self.classes,
            before=dict(dev=self.dev(), native=self.native()), route=proof, quantization_route=route,
            checkpoint_writes=0 if cost else 1, optimizer_saved=False)
        if not cost:
            path = self.p.checkpoint(arm); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'tiny synthetic checkpoint bytes, not a model')
            report.update(checkpoint=str(path.relative_to(self.root)), checkpoint_sha256=d.file_sha(path))
        self.p.write(self.p.path(mode, arm), report)
        return report

    def activity(self, mode='cost', arm='float', *, complete=True, error=None):
        now = datetime.now(timezone.utc).isoformat(); path = self.p.path(mode, arm)
        value = dict(schema=d.SCHEMA, tag=d.TAG, key=d.key(mode, arm), mode=mode, arm=arm, seconds=.1,
            started_at=now, ended_at=now, worker_pid=7, worker_pgid=7, returncode=0 if complete else 9,
            complete=complete, error_type=error, max_wall_sec=600, code_sha256=self.p.info()['code_sha256'],
            result_sha256=d.file_sha(path) if path.is_file() else None,
            reference_sha256=d.file_sha(self.p.CACHE / 'frozen_reference.json'))
        self.p.write(self.p.EVIDENCE / ('activity_' + d.key(mode, arm) + '.json'), value)
        return value

    def read(self, *, cost=True): return d.read_training(self.p, 'float', cost=cost, state=(self.bundle, self.frozen))


def worker_fixture(mode, metadata, *, term=False, fail_cycle=None, verify=False):
    """진짜 자기-PGID worker→finally activity→진짜 strict reader 순서를 자식에서 실행한다."""
    with tempfile.TemporaryDirectory(prefix='p106b_broad4_fixture_') as directory:
        fixture = Fixture(directory, metadata); fixture.fail_cycle = fail_cycle
        p = fixture.p
        try:
            if mode in ('source', 'preflight'):
                p.spent = lambda: (_ for _ in ()).throw(AssertionError('readonly family 계산 금지'))
                with patch.object(d, 'source_state', return_value=None), patch.object(d, 'prepared', return_value=None):
                    rc = d.worker(p, mode, None, 600)
                print(json.dumps(dict(returncode=rc, activities=list(p.EVIDENCE.glob('activity_*.json')))), flush=True)
                return rc
            def finish(_p, _arm, **kw):
                if term: os.kill(os.getpid(), signal.SIGTERM)
                fixture.finish(cost=kw['cost']); return 0
            with patch.object(d, 'train', finish):
                try: rc = d.worker(p, mode, 'float', 600)
                except BaseException as exc:
                    activity = p.n.required(p.EVIDENCE / ('activity_' + d.key(mode, 'float') + '.json'))
                    print(json.dumps(dict(error=type(exc).__name__, activity=activity)), flush=True)
                    return 130 if isinstance(exc, KeyboardInterrupt) else 9
            # 종료 activity를 필수로 요구하는 같은 본래 strict reader로 검산한다.
            if verify:
                p.spent = lambda: (_ for _ in ()).throw(AssertionError('readonly verifier family 계산 금지'))
                with patch.object(d, 'prepared', return_value=(fixture.bundle, fixture.frozen)):
                    d.verify_training(p, mode, 'float', 600)
            report = fixture.read(cost=mode == 'cost')
            print(json.dumps(dict(returncode=rc, strict_updates=report['updates'],
                actual_calls=len(fixture.calls), identities=fixture.calls,
                activity_complete=p.completed(mode, 'float')['complete'])), flush=True)
            return 0
        finally: fixture.close()


class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = d.build_runtime(); cls.info = cls.runtime.info()

    def test_full_info_json_roundtrip(self):
        self.assertEqual(json.loads(json.dumps(self.info, ensure_ascii=False)), self.info)
        self.assertTrue(self.info['code_complete']); self.assertGreater(len(self.info['code_sha256']), 20)
        self.assertEqual(self.info['planned_updates'], 704); self.assertEqual(self.info['passes'], 4)

    def test_parent_source_geometry_not_substituted(self):
        self.assertEqual(self.info['native_parent_tag'], 'p106b_native595_v1_s1337')
        self.assertEqual(self.info['native_replay_provider_tag'], 'p106b_native_weight_route_v1_s1337')
        self.assertNotIn('native_parents', self.info)
        self.assertEqual(self.info['broad_provider_tag'], 'p106b_broad_resume_v3_s1337')
        self.assertFalse(self.info['broad_payload_parent_is_initializer'])

    def test_full_info_has_no_actual_result_key_collisions(self):
        dynamic = {'cycles', 'updates', 'totals', 'status', 'quality', 'arm', 'cost', 'before',
            'initial_core_sha256', 'final_core_sha256', 'monitor_summary', 'dialogue_summary'}
        self.assertFalse(set(self.info) & dynamic)

    def test_frozen_body_and_globals_parity(self):
        self.runtime.check()
        for name in d.BODY_NAMES:
            self.assertEqual(self.runtime.utility.body_sha(getattr(self.runtime.core, name)), self.runtime.parity[name])
        original = __import__('scripts.diag_p106b_broad_curriculum', fromlist=['unused'])
        self.assertEqual(original.TAG, 'p106b_broad_curriculum_v1_s1337')
        self.assertNotEqual(self.runtime.core.authority, original.authority)
        self.assertIs(self.runtime.core.core, original.core)

    def test_private_binding_tamper_rejected(self):
        old = self.runtime.core.UPDATES
        try:
            self.runtime.core.UPDATES = 704
            with self.assertRaises(ValueError): self.runtime.check()
        finally: self.runtime.core.UPDATES = old
        self.runtime.check()

    def test_private_allowed_binding_tamper_rejected(self):
        old = self.runtime.core.TAG
        try:
            self.runtime.core.TAG = 'other'
            with self.assertRaises(ValueError): self.runtime.check()
        finally: self.runtime.core.TAG = old

    def test_check_only_does_not_read_assets(self):
        with patch.object(d, 'source_state', side_effect=AssertionError('assets forbidden')):
            with patch.object(d, 'prepared', side_effect=AssertionError('assets forbidden')):
                with patch('sys.stdout', io.StringIO()):
                    self.assertEqual(d.main(['--mode', 'train', '--arm', 'float', '--check-only']), 0)

    def test_constants_and_exposure(self):
        self.assertEqual(d.EXPECTED['native_targets'], 704 * 8192)
        self.assertEqual(d.EXPECTED['positive_rows'], 22528 * 4)
        self.assertEqual(sum(d.EXPECTED_LANG.values()), d.EXPECTED['assistant_targets'])
        self.assertEqual(self.info['clip'], 1.)
        self.assertEqual(self.info['actual_worker_active_limit_seconds'], 14400)

    def test_real_deadlines(self):
        p = self.runtime; before = d.TRAIN_STOP - timedelta(seconds=1)
        self.assertEqual(p.authority(True, before), 1)
        with self.assertRaises(p.Pending): p.authority(True, d.TRAIN_STOP)
        with self.assertRaises(p.Pending): p.authority(False, d.END - timedelta(seconds=600))
        with self.assertRaises(ValueError): p.authority(now=datetime(2026, 10, 20))

    def test_cli_selectors_and_children(self):
        for mode in d.MODES:
            for arm in d.ARMS if mode in ('cost', 'train', 'evaluate') else (None,):
                phases = d.phase_commands(mode, arm, 600)
                self.assertEqual([v[0] for v in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
                self.assertIn(d.SCRIPT, phases[-1][1]); self.assertNotIn('--arm', phases[1][1])
        for mode, arm in (('source', 'float'), ('train', None), ('evaluate', 'mixed'), ('budget', 'float')):
            with self.assertRaises(ValueError): d.key(mode, arm)

    def test_invalid_caps_and_idle_arguments(self):
        for cap in (0, 59, 7201, True):
            with self.assertRaises(ValueError): d.phase_commands('train', 'float', cap)
        with self.assertRaises(ValueError): d.phase_commands('train', 'float', 600, Path('/tmp/proof'))


class WindowTests(unittest.TestCase):
    def test_seeded_selection_preserves_original_order(self):
        first, report = d.expand_offsets([20, 2], 100, extra=5, width=3)
        self.assertEqual(first[:2], [20, 2]); self.assertEqual(first, d.expand_offsets([20, 2], 100, extra=5, width=3)[0])
        self.assertEqual(report['offsets_sha256'], d.sha(first)); d.validate_offsets(first, 100, width=3)

    def test_unaligned_interval_overlap_and_next_target_excluded(self):
        vector, _ = d.expand_offsets([2, 11], 31, extra=5, width=3)
        for a in vector[2:]:
            self.assertEqual(a % 3, 0)
            self.assertTrue(all(a + 3 <= b or b + 3 <= a for b in (2, 11)))
        self.assertNotIn(30, vector)

    def test_too_small_pool_no_shrink(self):
        with self.assertRaises(ValueError): d.expand_offsets([1], 10, extra=3, width=3)

    def test_duplicate_oob_and_bool_rejected(self):
        for values in ([0, 1], [0, 0], [-1], [8], [True]):
            with self.assertRaises(ValueError): d.validate_offsets(values, 10, width=3)

    def test_absolute_mapping_boundaries(self):
        self.assertEqual(d.update_mapping(0, 351)['absolute_native_indices'][-1], 2815)
        self.assertEqual(d.update_mapping(1, 0)['absolute_native_indices'][0], 2816)
        self.assertEqual(d.update_mapping(1, 351)['absolute_update'], 703)
        for cycle, local in ((2, 0), (0, 352), (True, 0), (0, -1)):
            with self.assertRaises(ValueError): d.update_mapping(cycle, local)

    def test_cycle_view_no_hidden_reindex(self):
        import numpy as np
        class Windows:
            def __len__(self): return 5632
            def __getitem__(self, index): return np.full(1025, index)
        view = d.CycleWindows(Windows(), list(range(5632)), 1)
        self.assertEqual(len(view), 2816); self.assertEqual(int(view[0][0]), 2816)
        self.assertEqual(view.accesses[0]['absolute_index'], 2816)
        with self.assertRaises(ValueError): view[-1]
        with self.assertRaises(ValueError): view[2816]


class IdleTests(unittest.TestCase):
    def proof(self):
        now = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
        value = dict(schema='P106B_ROOT_IDLE_V1', tag=d.TAG, arm='float', key='cost_float', code_sha256={'a': 'A' * 64},
            start_utc=(now - timedelta(seconds=310)).isoformat(), end_utc=(now - timedelta(seconds=10)).isoformat(),
            start_monotonic=100., end_monotonic=400., no_gpu_work=True, no_heavy_cpu=True,
            evidence=[dict(path=d.IDLE_DIRECTORY + '/root_observation.json', sha256='B' * 64)])
        return value, now

    def test_fresh_per_route_idle(self):
        proof, now = self.proof()
        self.assertEqual(d.idle_receipt(proof, proof['code_sha256'], 'float', now=now, monotonic=410.), proof)

    def test_idle_wrong_namespace_or_arm(self):
        for key, value in (('tag', 'old'), ('arm', 'ternary'), ('key', 'cost_ternary'), ('code_sha256', {})):
            proof, now = self.proof(); proof[key] = value
            with self.assertRaises(ValueError): d.idle_receipt(proof, {'a': 'A' * 64}, 'float', now=now, monotonic=410.)

    def test_short_stale_or_clock_mismatch(self):
        for field, value in (('end_monotonic', 399.), ('start_monotonic', 101.), ('no_gpu_work', False), ('no_heavy_cpu', False), ('evidence', [])):
            proof, now = self.proof(); proof[field] = value
            with self.assertRaises(ValueError): d.idle_receipt(proof, proof['code_sha256'], 'float', now=now, monotonic=410.)
        proof, now = self.proof()
        with self.assertRaises(ValueError): d.idle_receipt(proof, proof['code_sha256'], 'float', now=now + timedelta(seconds=601), monotonic=410.)

    def test_protected_absolute_escape_and_other_tag_rejected_before_read(self):
        values = ['datasets/TinyDataset/private.json', '.aws/credentials.json', '.claude/private.json',
            '/etc/private.json', str(ROOT / d.IDLE_DIRECTORY / 'idle_float.json'),
            d.IDLE_DIRECTORY + '/../private.json', d.IDLE_DIRECTORY + '/.aws/private.json',
            d.IDLE_DIRECTORY + '/.claude/private.json', d.IDLE_DIRECTORY + '/datasets/TinyDataset/private.json',
            'handoff/audit/other_tag/idle_float.json', d.IDLE_DIRECTORY + r'\idle_float.json',
            d.IDLE_DIRECTORY + '//idle_float.json']
        p = types.SimpleNamespace(n=types.SimpleNamespace(required=lambda _: self.fail('읽기 전에 거부해야 한다')))
        for value in values:
            with self.subTest(path=value), patch.object(d, 'file_sha', side_effect=AssertionError('hash forbidden')):
                with self.assertRaises(ValueError): d.read_idle_proof(p, value, 'float')
        with patch.object(d, 'build_runtime', side_effect=AssertionError('source 읽기도 금지')):
            with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
                self.assertEqual(d.main(['--mode', 'cost', '--arm', 'float', '--idle-proof', values[0], '--check-only']), 9)

    def test_all_evidence_paths_checked_before_first_hash(self):
        import time
        now = datetime.now(timezone.utc); monotonic = time.monotonic()
        proof, _ = self.proof()
        proof.update(start_utc=(now - timedelta(seconds=301)).isoformat(), end_utc=(now - timedelta(seconds=1)).isoformat(),
            start_monotonic=monotonic - 301, end_monotonic=monotonic - 1)
        proof['evidence'].append(dict(path='datasets/TinyDataset/private.json', sha256='C' * 64))
        p = types.SimpleNamespace(n=types.SimpleNamespace(required=lambda _: proof), info=lambda: dict(code_sha256=proof['code_sha256']))
        with patch.object(d, 'file_sha', side_effect=AssertionError('첫 evidence도 먼저 hash하면 안 된다')):
            with self.assertRaises(ValueError): d.read_idle_proof(p, d.IDLE_DIRECTORY + '/idle_float.json', 'float')

    def test_symlink_proof_and_evidence_rejected_before_read_or_hash(self):
        with tempfile.TemporaryDirectory(prefix='p106b_idle_path_') as directory:
            root = Path(directory); audit = root / d.IDLE_DIRECTORY; audit.mkdir(parents=True)
            outside = root / 'tiny.json'; outside.write_text('{}', encoding='utf-8')
            (audit / 'idle_float.json').symlink_to(outside)
            with patch.object(d, 'ROOT', root):
                p = types.SimpleNamespace(n=types.SimpleNamespace(required=lambda _: self.fail('symlink read 금지')))
                with self.assertRaises(ValueError): d.read_idle_proof(p, d.IDLE_DIRECTORY + '/idle_float.json', 'float')
                (audit / 'evidence.json').symlink_to(outside)
                proof, now = self.proof(); proof['evidence'][0]['path'] = d.IDLE_DIRECTORY + '/evidence.json'
                with self.assertRaises(ValueError): d.idle_receipt(proof, proof['code_sha256'], 'float', now=now, monotonic=410.)


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.metadata = d.build_runtime().info()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='p106b_broad4_')
        try: self.fixture = Fixture(self.tmp.name, self.metadata)
        except BaseException:
            d.ROOT = ROOT; self.tmp.cleanup(); raise

    def tearDown(self): self.fixture.close(); self.tmp.cleanup()

    def test_actual_lowercase_factory_and_real_classes(self):
        f = self.fixture
        self.assertEqual({v['optimizer'] for v in f.optimizers[2]}, {'adamw', 'muon'})
        self.assertEqual({v['actual_class'] for v in f.classes}, {'torch.optim.adamw.AdamW', 'tinylm.train.muon.Muon'})
        self.assertFalse(f.optimizers[0].state); self.assertFalse(f.optimizers[1].state)

    def test_wrong_native_optimizer_return_shape_rejected(self):
        f = self.fixture
        with self.assertRaises(ValueError): d.validate_optimizers(f.model, (f.optimizers[:2], f.optimizers[2]), lambda _: None)

    def test_duplicate_parameter_ownership_rejected(self):
        f = self.fixture; group = f.optimizers[0].param_groups[0]; parameter = group['params'][0]
        group['params'].append(parameter)
        try:
            with self.assertRaises(ValueError): d.validate_optimizers(f.model, f.optimizers, lambda _: None)
        finally: group['params'].pop()

    def test_actual_receipt_tamper_rejected(self):
        f = self.fixture; f.optimizers[2][0]['lr'] *= 2
        with self.assertRaises(ValueError): d.validate_optimizers(f.model, f.optimizers, lambda _: None)

    def test_cost_raw_reader_requires_closed_activity(self):
        f = self.fixture; f.finish(cost=True)
        with self.assertRaises(FileNotFoundError): f.read()
        f.activity(); self.assertEqual(f.read()['updates'], 8)

    def test_same_optimizer_two_cycles_and704_raw_totals(self):
        f = self.fixture; report = f.finish(cost=False); f.activity('train')
        result = f.read(cost=False)
        self.assertEqual(len(f.calls), 2); self.assertEqual(f.calls[0], f.calls[1])
        self.assertEqual(result['totals'], d.EXPECTED)
        self.assertEqual(report['cycles'][0]['optimizer_after'], report['cycles'][1]['optimizer_before'])
        self.assertEqual(report['cycles'][0]['core_after'], report['cycles'][1]['core_before'])

    def test_cycle1_partial_failure_preserves_cycle0(self):
        f = self.fixture; f.fail_cycle = 1
        with self.assertRaises(RuntimeError): f.finish(cost=False)
        path = f.p.RAW / 'train_float'
        partial = f.p.n.required(path / 'partial_failure.json')
        self.assertEqual(partial['completed_cycles'], 1); self.assertEqual(partial['completed_update_lower_bound'], 352)
        self.assertTrue((path / 'cycle0/cycle_receipt.json').is_file())
        self.assertFalse(f.p.path('train', 'float').exists()); self.assertFalse(f.p.checkpoint('float').exists())

    def test_write_once_and_namespace_guards(self):
        f = self.fixture; path = f.p.EVIDENCE / 'tiny.json'
        f.p.write(path, {'a': 1})
        with self.assertRaises(FileExistsError): f.p.write(path, {'a': 2})
        with self.assertRaises(ValueError): f.p.write(f.root / 'outside.json', {})

    def test_failed_activity_not_completed_and_counted_once(self):
        f = self.fixture; f.activity(complete=False, error='RuntimeError')
        self.assertEqual(f.p.spent(), .1)
        with self.assertRaises(ValueError): f.p.completed('cost', 'float')

    def test_activity_rejects_cap_or_authority_timestamp_damage(self):
        f = self.fixture; original = f.activity(complete=False, error='RuntimeError')
        for changes in (dict(seconds=9000), dict(started_at=d.TRAIN_STOP.isoformat()),
                dict(ended_at=(d.TRAIN_STOP + timedelta(seconds=31)).isoformat()),
                dict(started_at=datetime(2026, 10, 20).isoformat())):
            value = dict(original, **changes)
            with self.assertRaises(ValueError): d.validate_activity(f.p, value, 'cost', 'float')
        value = dict(original, seconds=630, started_at=(d.TRAIN_STOP - timedelta(seconds=600)).isoformat(),
            ended_at=(d.TRAIN_STOP + timedelta(seconds=30)).isoformat())
        d.validate_activity(f.p, value, 'cost', 'float')
        value['seconds'] = 630.01
        with self.assertRaises(ValueError): d.validate_activity(f.p, value, 'cost', 'float')

    def test_activity_evaluation_uses_end_not_train_stop(self):
        f = self.fixture; now = (d.TRAIN_STOP + timedelta(seconds=60)).isoformat()
        value = f.activity('evaluate', 'float', complete=False, error='RuntimeError')
        value.update(started_at=now, ended_at=now)
        d.validate_activity(f.p, value, 'evaluate', 'float')
        value.update(started_at=d.END.isoformat(), ended_at=d.END.isoformat())
        with self.assertRaises(ValueError): d.validate_activity(f.p, value, 'evaluate', 'float')

    def test_full_prepare_serialization_roundtrip_and_closed_activity(self):
        f = self.fixture
        f.p.CACHE, f.p.RAW, f.p.EVIDENCE = (f.root / p / 'fresh' for p in ('data_cache', 'runs/eval', 'test_result/evidence'))
        with patch.object(d, 'source_state', return_value=(f.bundle, f.frozen['binding'])):
            self.assertEqual(d.prepare(f.p), 0)
            with self.assertRaises(FileNotFoundError): d.prepared(f.p)
            f.activity('prepare', None)
            bundle, value = d.prepared(f.p)
            self.assertEqual(value['binding'], f.frozen['binding'])
            self.assertEqual(value['planned_updates'], 704)
            self.assertTrue(value['code_complete']); self.assertIs(bundle, f.bundle)
            with self.assertRaises(FileExistsError): d.prepare(f.p)

    def test_prepared_rejects_info_and_public_metadata_damage(self):
        f = self.fixture
        f.p.CACHE, f.p.RAW, f.p.EVIDENCE = (f.root / p / 'fresh' for p in ('data_cache', 'runs/eval', 'test_result/evidence'))
        with patch.object(d, 'source_state', return_value=(f.bundle, f.frozen['binding'])):
            d.prepare(f.p); original = f.p.n.required
            for damaged in ('frozen_reference.json', 'cpu_contract.json'):
                def read(path):
                    value = original(path)
                    if Path(path).name == damaged: value['planned_updates'] = 352
                    return value
                with patch.object(f.p.n, 'required', read):
                    with self.assertRaises(ValueError): d.prepared(f.p, completed=False)

    def test_full_meta_report_tamper_rejected_after_real_activity(self):
        f = self.fixture; report = f.finish(); f.activity()
        original = f.p.n.required
        for name, bad in (('tag', 'old'), ('authority_end_utc', 'old'), ('parent_core_sha256', 'D' * 64),
                          ('updates', 704), ('ordered_records_sha256', 'E' * 64), ('native_offsets_sha256', 'F' * 64)):
            def changed(path, name=name, bad=bad):
                value = original(path)
                if Path(path) == f.p.path('cost', 'float'): value[name] = bad
                return value
            with patch.object(f.p.n, 'required', changed):
                with self.assertRaises(ValueError): f.read()

    def test_partial_manifest_and_raw_counts_rejected(self):
        f = self.fixture; report = f.finish(); f.activity()
        result = deepcopy(report['cycles'][0]['core_result']); result['actual_updates'] = 7
        with self.assertRaises(ValueError): d.validate_core_result(f.p, f.bundle, 0, result, [], cost=True)

    def test_nan_wrong_owner_counts_and_native_indices_rejected(self):
        f = self.fixture; report = f.finish(); result = report['cycles'][0]['core_result']
        events = d.core_rows(f.p, f.p.RAW / 'cost_float/cycle0', result['event_manifest'], 8)
        for field, bad in (('native_indices', list(range(8, 16))), ('assistant_targets', 0),
                           ('gradient_norm', float('nan')), ('clipped', True), ('step_seconds', 0)):
            wrong = deepcopy(events); wrong[0][field] = bad
            with self.assertRaises(ValueError): d.validate_core_result(f.p, f.bundle, 0, result, wrong, cost=True)

    def test_forecast_uses_first_and_maxwarm_and_eval_readback(self):
        f = self.fixture
        cost = dict(step_seconds=[10., 1., 2., 1., 1., 1., 1., 1.])
        with patch.object(d, 'prepared', return_value=(f.bundle, f.frozen)), patch.object(d, 'read_training', return_value=cost):
            result = d.budget(f.p)
        self.assertEqual(result['estimated_training_seconds']['float'], 10 + 2 * 703 * 1.35 + 300)
        self.assertGreater(result['total_reserved_seconds'], sum(result['estimated_training_seconds'].values()) + 1800)

    def test_budget_no_fake_pass_with_slow_cost(self):
        f = self.fixture
        with patch.object(d, 'prepared', return_value=(f.bundle, f.frozen)), patch.object(d, 'read_training', return_value=dict(step_seconds=[100.] * 8)):
            self.assertFalse(d.budget(f.p)['fits'])

    def test_termination_handler_restored(self):
        before = signal.getsignal(signal.SIGTERM)
        with self.assertRaises(KeyboardInterrupt):
            with self.fixture.actual.termination_guard(): os.kill(os.getpid(), signal.SIGTERM)
        self.assertIs(signal.getsignal(signal.SIGTERM), before)


class PayloadTests(unittest.TestCase):
    @dataclass
    class Config:
        dim: int = 2

    def values(self):
        from scripts import diag_p106b_native_weight_route as n
        parent = synthetic_parent('float', 'B' * 64)
        report = dict(tag=d.TAG, arm='float', endpoint='native_broad4', updates=704, passes=4, objective='L0_TOKEN_MEAN_OVER_WHOLE_UPDATE',
            reference_sha256='A' * 64, parent_checkpoint_sha256=parent['checkpoint_sha256'], parent_core_sha256=parent['core_sha256'],
            scratch_core_sha256=parent['scratch_core_sha256'], final_core_sha256='C' * 64, native_offsets_sha256='D' * 64,
            ordered_records_sha256='E' * 64, original_schedules_sha256='F' * 64)
        payload = dict(model={}, cfg=dict(dim=2), step=704, tokenizer_sha256=n.TOKENIZER_SHA,
            tokenizer_lineage='chat32', quantization_route=n.modules()[2].route_metadata('float'), experiment=d.cp_experiment(report))
        facade = types.SimpleNamespace(modules=n.modules, TOKENIZER_SHA=n.TOKENIZER_SHA,
            required=lambda _: dict(binding=dict(parents=dict(float=parent))))
        return types.SimpleNamespace(n=facade, CACHE=Path('/tiny/fixture/cache')), report, payload

    def test_strict_child_metadata(self):
        p, report, payload = self.values(); d.validate_payload(p, payload, self.Config(), 'float', report)

    def test_old_tag_step_parent_and_route_rejected(self):
        for field, value in (('step', 352), ('cfg', dict(dim=3)), ('tokenizer_lineage', 'old')):
            p, report, payload = self.values(); payload[field] = value
            with self.assertRaises(ValueError): d.validate_payload(p, payload, self.Config(), 'float', report)
        for field, value in (('tag', 'old'), ('passes', 2), ('updates', 352), ('parent_core_sha256', 'Z' * 64)):
            p, report, payload = self.values(); report[field] = value; payload['experiment'] = d.cp_experiment(report)
            with self.assertRaises(ValueError): d.validate_payload(p, payload, self.Config(), 'float', report)
        p, report, payload = self.values(); payload['quantization_route'] = p.n.modules()[2].route_metadata('ternary')
        with self.assertRaises(ValueError): d.validate_payload(p, payload, self.Config(), 'float', report)

    def test_no_generic_float_loader(self):
        p, report, payload = self.values()
        with self.assertRaises(RuntimeError): p.n.modules()[2].generic_loader_guard(payload)

    def test_actual_cpu_state_shape_dtype_and_alias_tamper(self):
        import torch
        from scripts import diag_p106b_native_weight_route as n
        class Small(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.a = torch.nn.Linear(2, 2); self.b = self.a
        model = Small(); original = {k: v.detach().clone() for k, v in model.state_dict().items()}
        n.validate_cpu_state(model, dict(model=original), torch)
        for kind in ('shape', 'dtype', 'alias', 'missing'):
            supplied = {k: v.clone() for k, v in original.items()}
            if kind == 'shape': supplied['a.weight'] = torch.zeros(3, 2)
            elif kind == 'dtype': supplied['a.weight'] = supplied['a.weight'].double()
            elif kind == 'alias': supplied['b.weight'] = supplied['b.weight'] + 1
            else: supplied.pop('a.bias')
            with self.assertRaises(ValueError): n.validate_cpu_state(model, dict(model=supplied), torch)


class CoreNumericTests(unittest.TestCase):
    def test_original_cost8_numeric_body_with_tiny_cpu_head(self):
        import numpy as np
        import torch
        from scripts import diag_p106b_broad_curriculum as original
        from scripts import diag_p106b_relation_bind as relation
        from scripts.p106b_shards import verify
        from tinylm.train.mtp_sft import Record
        class TinyHead(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.embed = torch.nn.Embedding(8, 2); self.head = torch.nn.Linear(2, 8)
                self.forwards = 0
            def forward(self, x, return_hidden=False):
                self.forwards += 1; return self.embed(x)
            def _head_logits(self, features): return self.head(features)
            def param_groups(self, lr):
                return [dict(params=[self.embed.weight, self.head.weight], lr=lr, weight_decay=.1),
                    dict(params=[self.head.bias], lr=lr, weight_decay=0.)]
        model = TinyHead(); optimizers = relation.make_optimizers(model)
        record = Record([1, 5, 6, 7], [-100, 6, -100, 4], [0, 1, 1, 1])
        micros = [[record] * 8 for _ in range(16)]
        totals = dict(x_tokens=512, assistant_targets=256, content_targets=128, eot_targets=128)
        namespace = dict(original.train_updates.__globals__)
        namespace.update(TAG=d.TAG, authority=lambda **_: 9999.,
            builder=types.SimpleNamespace(materialize_group=lambda *_: micros, native_indices=original.builder.native_indices),
            expected_group=lambda bundle, arm, index, cost: (0, index, index, totals))
        numerical = types.FunctionType(original.train_updates.__code__, namespace, argdefs=original.train_updates.__defaults__)
        numerical.__kwdefaults__ = original.train_updates.__kwdefaults__
        utility = __import__('scripts.diag_p106b_route_cross_resume', fromlist=['body_sha'])
        self.assertEqual(utility.body_sha(numerical), utility.body_sha(original.train_updates))
        with tempfile.TemporaryDirectory(prefix='p106b_broad4_numeric_') as directory:
            cfg = types.SimpleNamespace(grad_checkpoint=True, mtp_aux=False, max_seq_len=1024)
            course = types.SimpleNamespace(rows=[dict(lane='grounded')], groups=[[0] for _ in range(176)])
            with patch('sys.stdout', io.StringIO()):
                result = numerical(model, cfg, None, dict(course=course), 'mixed', Path(directory), cost=True,
                    native_windows=[np.ones(1025, dtype=np.uint16)] * 2816, optimizers=optimizers, device='cpu')
            verify(Path(directory), result['event_manifest'])
        self.assertEqual(result['actual_updates'], 8); self.assertEqual(model.forwards, 8 * 17)
        self.assertEqual(result['totals']['assistant_targets'], 256 * 8)
        self.assertEqual(result['totals']['native_targets'], 8192 * 8)
        self.assertTrue(all(torch.isfinite(p).all() for p in model.parameters()))
        self.assertTrue(all(float(v['step']) == 8 for v in optimizers[0].state.values()))


class ProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.metadata = d.build_runtime().info()

    def run_fixture(self, mode, **kw):
        code = ('from scripts.test_p106b_native595_broad import worker_fixture; '
            'raise SystemExit(worker_fixture(' + repr(mode) + ',' + repr(self.metadata) + ',**' + repr(kw) + '))')
        return subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=ROOT,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, start_new_session=True, timeout=45,
            env=dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'))

    def test_real_worker_closed_activity_then_cost_reader(self):
        result = self.run_fixture('cost')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = json.loads(result.stdout.splitlines()[-1]); self.assertEqual(value['strict_updates'], 8)
        self.assertTrue(value['activity_complete'])

    def test_real_closed_worker_then_readonly_verifier_without_family_charge(self):
        result = self.run_fixture('cost', verify=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CLOSED_WORKER_STRICTLY_RECOUNTED', result.stdout)

    def test_readonly_workers_exclude_family_and_write_nothing(self):
        for mode in ('source', 'preflight'):
            result = self.run_fixture(mode)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout.splitlines()[-1])['activities'], [])

    def test_real_worker_closed_activity_then704_reader(self):
        result = self.run_fixture('train')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = json.loads(result.stdout.splitlines()[-1]); self.assertEqual(value['strict_updates'], 704)
        self.assertEqual(value['identities'][0], value['identities'][1])

    def test_real_term_writes_failed_activity(self):
        result = self.run_fixture('cost', term=True)
        self.assertEqual(result.returncode, 130, result.stdout + result.stderr)
        value = json.loads(result.stdout.splitlines()[-1]); self.assertFalse(value['activity']['complete'])
        self.assertEqual(value['activity']['returncode'], 130)

    def test_midcycle_failure_is_not_complete(self):
        result = self.run_fixture('train', fail_cycle=1)
        self.assertEqual(result.returncode, 9, result.stdout + result.stderr)
        value = json.loads(result.stdout.splitlines()[-1]); self.assertFalse(value['activity']['complete'])

    def test_verify_only_link_and_three_phase(self):
        p = types.SimpleNamespace(authority=lambda: 9000., n=types.SimpleNamespace(launch=None))
        command = d.phase_commands('train', 'float', 600)[-1][1]
        for returncodes, expected, calls in (([0, 0], 0, 2), ([0, 9], 9, 2), ([0, 8], 9, 2), ([9], 9, 1)):
            values = iter(returncodes); history = []
            p.n.launch = lambda c, t: history.append(c) or next(values)
            with patch('sys.stdout', io.StringIO()): self.assertEqual(d.launch_stage(p, command, 600), expected)
            self.assertEqual(len(history), calls)
            if calls == 2: self.assertIn('--verify-only', history[-1]); self.assertNotIn('--worker', history[-1])

    def test_regression_and_preflight_never_verify(self):
        for _, command in d.phase_commands('cost', 'float', 600)[:2]:
            seen = []; p = types.SimpleNamespace(authority=lambda: 9000., n=types.SimpleNamespace(launch=lambda c, t: seen.append(c) or 0))
            self.assertEqual(d.launch_stage(p, command, 600), 0); self.assertEqual(len(seen), 1)

    def test_actual_three_phase_pipeline_cannot_complete_if_verify_fails(self):
        from scripts.p106b_stage_receipt import pipeline
        codes = iter([0, 0, 0, 9]); seen = []
        p = types.SimpleNamespace(authority=lambda: 9000., n=types.SimpleNamespace(
            launch=lambda c, t: seen.append(c) or next(codes)))
        with patch('sys.stdout', io.StringIO()):
            result = pipeline(d.phase_commands('cost', 'float', 600), lambda c: d.launch_stage(p, c, 600),
                lambda _: None, experiment='CPU_FIXTURE_ONLY')
        self.assertEqual(result['status'], 'ERROR'); self.assertEqual(result['returncode'], 9)
        self.assertTrue(result['main_experiment_invoked']); self.assertEqual(len(seen), 4)


class Parent595Fixture:
    """원595 strict read_training/completed/read_events 본문을 작은 임시 원형에 연결한다."""
    def __init__(self, directory, metadata):
        import numpy as np
        from scripts import diag_p106b_native595 as parent
        from scripts import diag_p106b_native_weight_route as native
        from scripts.p106b_shards import ShardWriter, verify
        self.root = Path(directory); self.parent = parent; self.old_root = d.ROOT; d.ROOT = self.root
        def required(path):
            path = Path(path)
            if not path.is_relative_to(self.root): raise AssertionError('실물 읽기 금지')
            return json.loads(path.read_text(encoding='utf-8'))
        event_namespace = dict(vars(native), required=required, safe=lambda path: Path(path), verify=verify)
        event_reader = types.FunctionType(native.read_events.__code__, event_namespace)
        facade = types.SimpleNamespace(**{name: getattr(native, name) for name in ('Pending', 'schedule', 'finite',
            'validate_optimizer_groups', 'actual_lrs', 'validate_route_receipt', 'validate_native32', 'fingerprint', 'modules')}, read_events=event_reader)
        self.upstream = parent.Runtime(facade, None, None, [], self.root)
        self.upstream.info = lambda: deepcopy(metadata)
        self.offsets = np.arange(parent.RECIPE.crops, dtype=np.int64); self.reference = dict(synthetic_fixture=True)
        self.upstream.write(self.upstream.CACHE / 'reference.json', self.reference)
        namespace = dict(vars(parent), required=required, prepared=lambda _: (self.reference, self.offsets))
        self.upstream.completed = types.MethodType(types.FunctionType(parent.Runtime.completed.__code__, namespace), self.upstream)
        reader = types.FunctionType(parent.read_training.__code__, namespace)
        reader.__kwdefaults__ = parent.read_training.__kwdefaults__
        self.provider = types.SimpleNamespace(TAG=parent.TAG, read_training=reader)
        self.p = types.SimpleNamespace(parent_provider=self.provider, parent_runtime=self.upstream, n=native)
        self.required, self.writer = required, ShardWriter

    def finish(self, arm='float', *, complete=True):
        native = self.p.n; parent = self.parent; core = 'B' * 64
        groups = [dict(optimizer=name, group=0, lr=lr, runtime_lr=lr / 10, runtime_weight_decay=wd,
            weight_decay=wd, lr_multiplier=10., parameters=4, names_sha256='A' * 64, scale_mode=scale)
            for name, lr, wd, scale in (('AdamW', .001, .1, None), ('Muon', .004, 0., 'rms'))]
        writer = self.writer(self.upstream.RAW / ('train_' + arm), 'updates', limit=19_999_999)
        reference_sha = d.file_sha(self.upstream.CACHE / 'reference.json')
        for step in range(4543):
            contract = parent.RECIPE.update(native, step)
            writer.append(dict(update=step + 1, **contract, ce=1., gradient_norm=.5, clipped=False, step_seconds=.01,
                crop_offsets_sha256=parent.sha([int(v) for v in self.offsets[step * 128:(step + 1) * 128]]),
                actual_lrs=native.actual_lrs(groups, contract['schedule']['lr_factor'])))
        manifest = writer.close(lineage=dict(tag=parent.TAG, arm=arm, cost=False, reference_sha256=reference_sha))
        path = self.upstream.checkpoint(arm); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'not a model, synthetic CP hash fixture')
        route = dict(mode=arm, metadata=native.modules()[2].route_metadata(arm), tlinear_instances=1,
            owned_tlinear_instances=1, refreshed_tlinear_instances=1, forward_methods=['_guarded_forward'],
            refresh_methods=['_float_refresh' if arm == 'float' else '_ternary_refresh'])
        report = dict(self.upstream.info(), status='TRAIN_COMPLETE', cost=False, arm=arm, updates=4543,
            reference_sha256=reference_sha, initial_core_sha256=parent.RECIPE.scratch_core_sha256, final_core_sha256=core,
            parent_checkpoint_sha256=None, parent_core_sha256=None, checkpoint_writes=1, optimizer_saved=False,
            event_manifest=manifest, actual_optimizer_groups=groups,
            actual_optimizer_classes=['torch.optim.adamw.AdamW', 'tinylm.train.muon.Muon'], step_seconds=[.01] * 4543,
            grad_max=.5, clip_events=0, totals=dict(targets=595460096, x_tokens=595460096), route=route,
            quantization_route=route['metadata'], late_probe=None, cache_audit=None,
            native32_fp32=dict(ce=1., windows=32, targets=32768, val_sha256=parent.RECIPE.val_sha256, precision='FP32_MATH'),
            checkpoint=str(path.relative_to(self.root)), checkpoint_sha256=d.file_sha(path))
        self.upstream.write(self.upstream.path('train', arm), report)
        now = datetime.now(timezone.utc).isoformat()
        activity = dict(schema=parent.SCHEMA, tag=parent.TAG, key='train_' + arm, mode='train', arm=arm,
            code_sha256=self.upstream.info()['code_sha256'], seconds=.1, max_wall_sec=18000,
            returncode=0 if complete else 9, complete=complete, error_type=None if complete else 'RuntimeError',
            started_at=now, ended_at=now, pid=7, pgid=7,
            result_sha256=d.file_sha(self.upstream.path('train', arm)), reference_sha256=reference_sha)
        self.upstream.write(self.upstream.EVIDENCE / ('activity_train_' + arm + '.json'), activity)
        return report

    def close(self): d.ROOT = self.old_root


class Parent595Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = d.build_runtime(); cls.upstream_info = cls.runtime.parent_runtime.info()

    def test_controller_numeric_reader_eval_and_worker_ast_preserved(self):
        original = (ROOT / d.CONTROLLER_SOURCE).read_text(encoding='utf-8')
        current = (ROOT / d.SCRIPT).read_text(encoding='utf-8')
        parity = d.controller_contract(original, current)
        for name in ('run_cycles', 'validate_core_result', 'evaluate', 'read_evaluation', 'worker', 'launch_stage', 'budget'):
            self.assertIn(name, parity)
        with self.assertRaises(ValueError): d.controller_contract(original, current.replace('max(times[1:])', 'min(times[1:])'))

    def test_pinned_sources_and_explicit_parent_replay_providers(self):
        contract = json.loads(d.F4.read_text(encoding='utf-8'))
        for name, digest in contract['source_pins'].items(): self.assertEqual(d.file_sha(ROOT / name), digest)
        self.assertEqual(self.runtime.parent_provider.TAG, 'p106b_native595_v1_s1337')
        self.assertEqual(self.runtime.parent_provider.RECIPE.updates, 4543)
        self.assertEqual(self.runtime.n.TRAIN_TOKENS, 597995000)
        self.assertNotEqual(self.runtime.n.TRAIN_SHA, self.upstream_info['native_recipe']['pool_sha256'])
        self.assertEqual(self.runtime.info()['evaluation_reserve_seconds'], 3600)
        self.runtime.check()

    def test_complete595_real_raw_and_closed_activity_then_descriptor(self):
        with tempfile.TemporaryDirectory(prefix='parent595_strict_') as directory:
            fixture = Parent595Fixture(directory, self.upstream_info)
            try:
                report = fixture.finish(); before = json.dumps(report, sort_keys=True)
                original, descriptor = d.parent_snapshot(fixture.p, 'float')
                self.assertEqual(before, json.dumps(original, sort_keys=True))
                self.assertEqual(descriptor['scratch_core_sha256'], original['initial_core_sha256'])
                self.assertEqual(descriptor['original_training_updates'], 4543)
                self.assertEqual(descriptor['report_sha256'], d.file_sha(fixture.upstream.path('train', 'float')))
                self.assertNotEqual(descriptor['descriptor_sha256'], descriptor['report_sha256'])
                self.assertEqual(d.parent_report(fixture.p, 'float'), descriptor)
            finally: fixture.close()

    def test_incomplete595_parent_is_not_admitted(self):
        with tempfile.TemporaryDirectory(prefix='parent595_failed_') as directory:
            fixture = Parent595Fixture(directory, self.upstream_info)
            try:
                fixture.finish(complete=False)
                with self.assertRaises(ValueError): d.parent_report(fixture.p, 'float')
            finally: fixture.close()

    def test_parent_header_old299_cost8_wrong_arm_source_and_parent_rejected(self):
        p = types.SimpleNamespace(parent_runtime=types.SimpleNamespace(info=lambda: deepcopy(self.upstream_info),
            checkpoint=lambda arm: ROOT / synthetic_parent(arm)['checkpoint']), n=self.runtime.n)
        good = dict(self.upstream_info, status='TRAIN_COMPLETE', cost=False, arm='float', updates=4543,
            totals=dict(targets=595460096, x_tokens=595460096), initial_core_sha256=d.PARENT_RECIPE['scratch_core_sha256'],
            final_core_sha256='B' * 64, checkpoint_sha256='E' * 64, parent_checkpoint_sha256=None,
            parent_core_sha256=None, checkpoint_writes=1, optimizer_saved=False,
            checkpoint=synthetic_parent('float')['checkpoint'])
        d.validate_parent_header(p, good, 'float')
        for changes in (dict(updates=2281), dict(updates=8, cost=True), dict(arm='ternary'),
                dict(tag='p106b_native_weight_route_v1_s1337'), dict(parent_core_sha256='A' * 64),
                dict(checkpoint_writes=0), dict(initial_core_sha256='A' * 64), dict(code_sha256={})):
            with self.subTest(changes=changes), self.assertRaises(ValueError): d.validate_parent_header(p, dict(good, **changes), 'float')

    def test_descriptor_wrong_parent_paths_recipe_and_normalization_rejected(self):
        value = synthetic_parent('float'); d.validate_parent_descriptor(value, 'float')
        for changes in (dict(original_training_updates=2281), dict(original_targets=298975232),
                dict(checkpoint=synthetic_parent('ternary')['checkpoint']), dict(original_tag='old'),
                dict(normalization={}), dict(scratch_core_sha256='A' * 64), dict(parent_recipe={}),
                dict(original_report_unchanged=False), dict(descriptor_sha256='A' * 64)):
            bad = dict(value, **changes)
            if 'descriptor_sha256' not in changes: bad['descriptor_sha256'] = d.sha({k: v for k, v in bad.items() if k != 'descriptor_sha256'})
            with self.subTest(changes=changes), self.assertRaises(ValueError): d.validate_parent_descriptor(bad, 'float')

    def test_both_parents_required_before_any_broad_or_replay_source(self):
        seen = []
        def get(_p, arm):
            seen.append(arm)
            if arm == 'float': raise FileNotFoundError('두 번째 부모는 아직 없다')
            return synthetic_parent(arm)
        p = types.SimpleNamespace(check=lambda: None, b=types.SimpleNamespace(prepared=lambda: self.fail('부모 선결 전에 교과0')))
        with patch.object(d, 'parent_report', get):
            with self.assertRaises(FileNotFoundError): d.source_state(p)
        self.assertEqual(seen, ['ternary', 'float'])

    def context_fixture(self, *, arm='float'):
        parent = synthetic_parent(arm); report = {'original_report_object': True}; calls = []
        route = types.SimpleNamespace(mode=arm, metadata=self.runtime.n.modules()[2].route_metadata(arm), assert_active=lambda: calls.append('route'))
        model = types.SimpleNamespace(cfg=PayloadTests.Config())
        @contextmanager
        def load(runtime, requested, actual):
            self.assertIs(actual, report); self.assertEqual(requested, arm); calls.append('load')
            try: yield object(), model, route
            finally: calls.append('close')
        facade = types.SimpleNamespace(TOKENIZER=Path('/small/pinned/tokenizer.json'), TOKENIZER_SHA='A' * 64,
            required=lambda _: dict(binding=dict(parents={arm: parent})),
            modules=lambda: (types.SimpleNamespace(state_fingerprint=lambda _: parent['core_sha256']), None, self.runtime.n.modules()[2]),
            routed_runtime=lambda *_: self.fail('옛 native 부모 loader 금지'))
        p = types.SimpleNamespace(n=facade, CACHE=Path('/small/cache'), parent_provider=types.SimpleNamespace(loaded_runtime=load),
            parent_runtime=object(), authority=lambda **kw: calls.append(('authority', kw['training'])) or 9999., check=lambda: None)
        return p, report, parent, model, route, calls

    def test_three_tuple595_context_explicit_cfg_tok_scratch_and_full_route(self):
        p, report, parent, model, route, calls = self.context_fixture(); tok = object()
        with patch.object(d, 'parent_snapshot', return_value=(report, parent)), patch.object(d, 'file_sha', return_value='A' * 64), \
                patch.object(d, 'load_tokenizer', return_value=tok):
            with d.parent_runtime(p, 'float', training=True) as values:
                self.assertEqual(len(values), 6); self.assertIs(values[1], model); self.assertIs(values[2], model.cfg)
                self.assertIs(values[3], tok); self.assertEqual(values[4], d.PARENT_RECIPE['scratch_core_sha256'])
                self.assertIs(values[5], route); self.assertNotIn('close', calls)
        self.assertEqual(calls[-1], 'close'); self.assertEqual(calls.count(('authority', True)), 3)

    def test_late_parent_loader_rechecks_own_deadline_before_model(self):
        p, report, parent, model, route, calls = self.context_fixture()
        count = 0
        def clock(**kw):
            nonlocal count
            count += 1
            if count == 2: raise self.runtime.Pending('CPU 선결 중 학습 종료')
        p.authority = clock
        with patch.object(d, 'parent_snapshot', return_value=(report, parent)), patch.object(d, 'file_sha', return_value='A' * 64), \
                patch.object(d, 'load_tokenizer', return_value=object()):
            with self.assertRaises(self.runtime.Pending):
                with d.parent_runtime(p, 'float', training=True): self.fail('기한 뒤 model진입0')
        self.assertNotIn('load', calls)

    def test_changed_actual_parent_before_load_rejected(self):
        p, report, parent, model, route, calls = self.context_fixture()
        bad = dict(parent, checkpoint_sha256='F' * 64)
        with patch.object(d, 'parent_snapshot', return_value=(report, bad)), patch.object(d, 'load_tokenizer', side_effect=AssertionError('model/tokenizer0')):
            with self.assertRaises(ValueError):
                with d.parent_runtime(p, 'float', training=False): self.fail('다른 실제 부모0')
        self.assertNotIn('load', calls)

    def test_full_code_idle_map_and_cost_cap(self):
        codes = self.runtime.info()['code_sha256']; proof, now = IdleTests().proof()
        proof['code_sha256'] = dict(codes)
        d.idle_receipt(proof, codes, 'float', now=now, monotonic=410.)
        proof['code_sha256'] = codes[d.SCRIPT]
        with self.assertRaises(ValueError): d.idle_receipt(proof, codes, 'float', now=now, monotonic=410.)
        with self.assertRaises(ValueError): d.phase_commands('cost', 'float', 901)


if __name__ == '__main__': unittest.main()
