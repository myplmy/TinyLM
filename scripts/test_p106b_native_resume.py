"""독립 namespace/메타데이터/임시 raw 회귀. 실물 CP·자료·모델·GPU는 사용하지 않는다."""
from __future__ import annotations

from contextlib import contextmanager, ExitStack, redirect_stdout, redirect_stderr
import copy
import builtins
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
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
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native_resume as d


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as stream: json.dump(value, stream, ensure_ascii=False)


@contextmanager
def fixture(prior_seconds=1234.5):
    """원 모듈 대신 별도 합성 producer를 주입한다. 실제 original 전역은 고치지 않는다."""
    real = d.original_module(); original_info = real.info(); original_bytes = d.SOURCE.read_bytes()
    with tempfile.TemporaryDirectory(prefix='p106b-resume-test-') as directory, ExitStack() as stack:
        root = Path(directory)
        origin = types.ModuleType('_fixture_original_native')
        origin.__dict__.update(vars(real)); origin.ROOT = root
        origin.CACHE = root / 'data_cache' / real.TAG
        origin.RAW = root / 'runs/eval' / real.TAG
        origin.EVIDENCE = root / 'test_result/evidence' / real.TAG
        origin.info = lambda: copy.deepcopy(original_info)
        origin.digest = lambda p: d.file_sha(p)
        origin.result_path = lambda key: origin.EVIDENCE / key / 'report.json'
        origin.checkpoint = lambda arm, endpoint: root / 'runs/ckpt' / ('original_' + arm + '_' + endpoint + '.pt')
        offsets = (1, 5, 9, 13)
        frozen = dict(manifests={'cases': {'rows': 2}}, exposure={real.SOURCE_ARM: [
            dict(counts=dict(assistant_targets=12288, x_tokens=24576), update_target_denominators=[128] * 96) for _ in range(4)]})
        cases = [dict(id='c0', messages=[dict(role='user', content='fixture')]),
                 dict(id='c1', messages=[dict(role='user', content='fixture2')])]
        reference = dict(binding=dict(source='synthetic_only'), offsets=dict(crops=4), display_ids=['c0'],
            offsets_file_sha256='F' * 64, native_schedule=[dict(step=0)])
        put(origin.CACHE / 'frozen_reference.json', reference)
        put(origin.EVIDENCE / 'cpu_contract.json', dict(fixture=True))
        (origin.CACHE / 'native_offsets.npy').write_bytes(b'synthetic offsets metadata only')
        reference['offsets_file_sha256'] = origin.digest(origin.CACHE / 'native_offsets.npy')
        put(origin.CACHE / 'frozen_reference.json', reference)
        hooks = dict(prepared=None)
        def original_prepared():
            if hooks['prepared'] is not None: hooks['prepared']()
            return copy.deepcopy(reference), copy.deepcopy(frozen), copy.deepcopy(cases), offsets
        origin.prepared = original_prepared
        origin.spent_seconds = lambda: prior_seconds
        calls = []
        @contextmanager
        def native_loader(arm, endpoint=None):
            if endpoint != 'native': raise AssertionError('원 loader에는 native만 전달해야 한다')
            calls.append((arm, endpoint)); yield ('SYNTHETIC_ORIGINAL_NATIVE', arm, endpoint)
        origin.routed_runtime = native_loader
        reports = {}
        old_reference_sha = origin.digest(origin.CACHE / 'frozen_reference.json')
        for mode, arm in (('train', 'ternary'), ('train', 'float'), ('sft_cost', 'ternary')):
            key = real.phase_key(mode, arm); native = mode == 'train'
            cp = origin.checkpoint(arm, 'native'); cp.parent.mkdir(parents=True, exist_ok=True)
            if not cp.exists(): cp.write_bytes(('synthetic ' + arm).encode())
            qcp = origin.checkpoint('ternary', 'native')
            r = dict(original_info, status='TRAIN_COMPLETE' if native else 'COST_COMPLETE',
                arm=arm, endpoint='native' if native else 'sft', cost=not native, updates=2281 if native else 8,
                reference_sha256=old_reference_sha, scratch_core_sha256='A' * 64,
                initial_core_sha256='A' * 64 if native else 'B' * 64,
                final_core_sha256=('B' if arm == 'ternary' else 'C') * 64,
                checkpoint_sha256=origin.digest(cp) if native else None,
                checkpoint=str(cp.relative_to(root)) if native else None,
                parent_checkpoint_sha256=None if native else origin.digest(qcp),
                parent_core_sha256=None if native else 'B' * 64, step_seconds=[2.] + [1.] * 7,
                optimizer_saved=False, checkpoint_writes=1 if native else 0)
            reports[(mode, arm)] = r; put(origin.result_path(key), r)
            start = real.TRAIN_STOP - timedelta(hours=1)
            activity = dict(schema=real.SCHEMA, tag=real.TAG, key=key, mode=mode, arm=arm, endpoint=None,
                complete=True, returncode=0, error_type=None, seconds=5., max_wall_sec=600,
                started_at=start.isoformat(), ended_at=(start + timedelta(seconds=5)).isoformat(),
                code_sha256=original_info['code_sha256'], result_sha256=origin.digest(origin.result_path(key)),
                reference_sha256=old_reference_sha)
            put(origin.EVIDENCE / ('activity_' + key + '.json'), activity)
        def completed_activity(mode, arm):
            key = real.phase_key(mode, arm)
            a = json.loads((origin.EVIDENCE / ('activity_' + key + '.json')).read_text())
            real.validate_activity(a, key, True)
            if a['result_sha256'] != origin.digest(origin.result_path(key)): raise ValueError('합성 원 report SHA가 다르다')
            return a
        origin.completed_activity = completed_activity
        def train_report(mode, arm):
            completed_activity(mode, arm)
            value = json.loads(origin.result_path(real.phase_key(mode, arm)).read_text())
            if any(value.get(k) != v for k, v in original_info.items()): raise ValueError('합성 원 조건이 다르다')
            return value
        origin.train_report = train_report
        put(root / 'resume_f4.json', {'fixture': True})
        stack.enter_context(patch.multiple(d, ROOT=root, F4=root / 'resume_f4.json'))
        p = d._build_runtime(origin, original_bytes)
        yield dict(p=p, origin=origin, reports=reports, calls=calls, source=original_bytes,
            reference=reference, frozen=frozen, cases=cases, offsets=offsets, hooks=hooks)


def cp_report(p, arm='float'):
    return dict(arm=arm, endpoint='sft', updates=384, reference_sha256='D' * 64,
        scratch_core_sha256='A' * 64, parent_checkpoint_sha256='E' * 64,
        parent_core_sha256='C' * 64, final_core_sha256='F' * 64)


def owned_cost_fixture(f):
    """동일한 strict reader code를 독립 fixture globals에서 실제 임시 shard에 적용한다."""
    from scripts import p106b_weight_route as method
    p = f['p']; p.worker('prepare', None, None, 600)
    groups = [dict(optimizer=name, group=0, lr=rate * .5, runtime_lr=rate,
        weight_decay=0., runtime_weight_decay=wd, lr_multiplier=.5, parameters=1,
        names_sha256='C' * 64, scale_mode=scale)
        for name, rate, wd, scale in (('AdamW', 1e-4, .1, None), ('Muon', 4e-4, 0., 'rms'))]
    route = dict(mode='float', metadata=method.route_metadata('float'), tlinear_instances=1,
        owned_tlinear_instances=1, refreshed_tlinear_instances=1,
        forward_methods=['_guarded_forward'], refresh_methods=['_float_refresh'])
    records = [types.SimpleNamespace(x_tokens=2, targets=1) for _ in range(128)]
    micros = [list(range(i, i + 8)) for i in range(0, 128, 8)]
    source = types.SimpleNamespace(read_prepared=lambda: (copy.deepcopy(f['frozen']), None, None),
        records_for=lambda *_: records, schedule=lambda _: [micros] * 96)
    env = dict(vars(p)); env['modules'] = lambda: (types.SimpleNamespace(), source, method)
    env['validate_route_receipt'] = types.FunctionType(p.validate_route_receipt.__code__, env)
    reader = types.FunctionType(p._resume_captured['train_report'].__code__, env)
    events = [dict(update=i + 1, **p.update_contract('sft', i, f['frozen']),
        x_tokens=256, ce=1., native_replay_ce=1., gradient_norm=.5, clipped=False, step_seconds=1.,
        actual_lrs=p.actual_lrs(groups)) for i in range(8)]
    key = p.phase_key('sft_cost', 'float'); reference = p.digest(p.CACHE / 'frozen_reference.json')
    writer = p.ShardWriter(p.RAW / key, 'updates', limit=19_999_999)
    for event in events: writer.append(event)
    manifest = writer.close(lineage=dict(tag=p.TAG, arm='float', endpoint='sft', cost=True, reference_sha256=reference))
    parent = p.train_report('train', 'float'); report = dict(p.info(), status='COST_COMPLETE', cost=True,
        arm='float', endpoint='sft', updates=8, reference_sha256=reference,
        scratch_core_sha256='A' * 64, initial_core_sha256=parent['final_core_sha256'], final_core_sha256='F' * 64,
        parent_core_sha256=parent['final_core_sha256'], parent_checkpoint_sha256=parent['checkpoint_sha256'],
        actual_optimizer_groups=groups, quantization_route=method.route_metadata('float'), route=route,
        event_manifest=manifest, step_seconds=[1.] * 8, late_probe=None,
        totals={name: sum(e[name] for e in events) for name in ('targets', 'x_tokens', 'native_replay_targets')},
        max_preclip_gradient=.5, clip_events=0, optimizer_saved=False, checkpoint_writes=0,
        cache_audit=dict(quality_forwards=0, optimizer_updates=0, finite=True, core_before='F' * 64,
            core_after='F' * 64, route=route, cache_tensors=1, cache_nominal_bytes=4,
            extra_cache_storage_bytes=0, seconds=1., peak_allocated_mib=1., peak_reserved_mib=2.))
    p.write(p.result_path(key), report)
    start = p.TRAIN_STOP - timedelta(hours=1)
    p.write(p.EVIDENCE / ('activity_' + key + '.json'), dict(schema=p.SCHEMA, tag=p.TAG, key=key,
        mode='sft_cost', arm='float', endpoint=None, returncode=0, complete=True, error_type=None,
        seconds=5., max_wall_sec=600, started_at=start.isoformat(), ended_at=(start + timedelta(seconds=5)).isoformat(),
        code_sha256=p.info()['code_sha256'], result_sha256=p.digest(p.result_path(key)), reference_sha256=reference))
    return reader, report, env


def endpoint_readback_fixture(f):
    """네 종점의 tiny 실제 JSONL/manifest를 동일 readback bytecode로 소비한다."""
    from scripts import p106b_weight_route as method
    p = f['p']; p.worker('prepare', None, None, 600)
    cases = copy.deepcopy(f['cases']); fixture_info = dict(p.info(), expected_answers=2, fixture_only=True)
    cp = {}
    for arm in p.ARMS:
        cp[('train', arm)] = p.train_report('train', arm)
        cp[('sft', arm)] = dict(cp_report(p, arm), checkpoint_sha256=('D' if arm == 'ternary' else 'E') * 64)
    def classify(case, answer): return dict(fixture_answer_matches=answer == 'fixture-' + case['id'])
    source = types.SimpleNamespace(classify_case=classify,
        recount=lambda events, cases, tokenizer: dict(fixture_events=len(events), cases=len(cases)))
    for arm in p.ARMS:
        for endpoint in p.ENDPOINTS:
            report = cp[('train' if endpoint == 'native' else 'sft', arm)]
            key = p.phase_key('evaluate', arm, endpoint); route = dict(mode=arm, metadata=method.route_metadata(arm),
                tlinear_instances=1, owned_tlinear_instances=1, refreshed_tlinear_instances=1,
                forward_methods=['_guarded_forward'], refresh_methods=['_float_refresh' if arm == 'float' else '_ternary_refresh'])
            lineage = dict(tag=p.TAG, arm=arm, endpoint=endpoint, checkpoint_sha256=report['checkpoint_sha256'],
                core_sha256=report['final_core_sha256'], cases_sha256=p.sha(cases), quantization_route=method.route_metadata(arm))
            writer = p.ShardWriter(p.RAW / key, 'answers', limit=19_999_999)
            for case in cases:
                answer = 'fixture-' + case['id']
                writer.append(dict(id=case['id'], case_sha256=p.sha(case), arm=arm, endpoint=endpoint,
                    checkpoint_sha256=report['checkpoint_sha256'], quantization_route=method.route_metadata(arm),
                    metrics=classify(case, answer), answer=answer,
                    generation=dict(max_new=64, generated_tokens=1, finish_reason='eot')))
            manifest = writer.close(lineage=lineage)
            value = dict(fixture_info, status='ACTUAL_ANSWERS_COLLECTED', arm=arm, endpoint=endpoint,
                checkpoint_sha256=report['checkpoint_sha256'], core_before=report['final_core_sha256'],
                core_after=report['final_core_sha256'], cases_sha256=p.sha(cases), raw_manifest=manifest,
                lineage=lineage, actual_cases=2, route=route, quantization_route=method.route_metadata(arm),
                native32_fp32=dict(ce=1., targets=32768, windows=32, val_sha256=p.VAL_SHA, precision='FP32_MATH',
                    scope='SYNTHETIC_METADATA_NO_MODEL'))
            p.write(p.result_path(key), value)
            start = p.END - timedelta(hours=1)
            p.write(p.EVIDENCE / ('activity_' + key + '.json'), dict(schema=p.SCHEMA, tag=p.TAG, key=key,
                mode='evaluate', arm=arm, endpoint=endpoint, returncode=0, complete=True, error_type=None,
                seconds=1., max_wall_sec=600, started_at=start.isoformat(), ended_at=(start + timedelta(seconds=1)).isoformat(),
                code_sha256=p.info()['code_sha256'], result_sha256=p.digest(p.result_path(key)),
                reference_sha256=p.digest(p.CACHE / 'frozen_reference.json')))
    class TinyTokenizer:
        @staticmethod
        def from_file(_): return TinyTokenizer()
        def encode(self, _): return types.SimpleNamespace(ids=[1])
    def vocabulary(value, adapted, tokenizer):
        if value['generation'].get('max_new') != 64 or adapted['encoding']['ids'] != [1]:
            raise ValueError('합성 생성 영수증이 다르다')
    real_import = builtins.__import__
    def fixture_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'scripts' and 'diag_p106b_span_readout' in fromlist:
            return types.SimpleNamespace(diag_p106b_span_readout=types.SimpleNamespace(validate_vocabulary=vocabulary))
        if name == 'tokenizers': return types.SimpleNamespace(Tokenizer=TinyTokenizer)
        if name == 'tinylm.chat.serialize': return types.SimpleNamespace(serialize=lambda *_, **__: 'fixture prompt')
        return real_import(name, globals, locals, fromlist, level)
    env = dict(vars(p)); env['ANSWERS'] = 2; env['info'] = lambda: copy.deepcopy(fixture_info)
    env['modules'] = lambda: (None, source, method)
    env['train_report'] = lambda mode, arm: cp[(mode, arm)]
    env['validate_route_receipt'] = types.FunctionType(p.validate_route_receipt.__code__, env)
    env['__builtins__'] = dict(vars(builtins), __import__=fixture_import)
    readback = types.FunctionType(p.readback.__code__, env)
    return readback, fixture_info


class FactoryTests(unittest.TestCase):
    def test_real_factory_is_metadata_only_and_preserves_original_globals_info(self):
        original = d.original_module(); before = dict(vars(original)); metadata = original.info()
        a = d.build_runtime(); b = d.build_runtime()
        self.assertEqual(original.info(), metadata)
        self.assertEqual(set(vars(original)), set(before))
        self.assertTrue(all(vars(original)[k] is value for k, value in before.items()))
        self.assertIsNot(a, b); self.assertIs(a.train.__globals__, vars(a)); self.assertIs(b.train.__globals__, vars(b))
        self.assertIsNot(a.train.__globals__, original.train.__globals__)
        a._resume_assert_unchanged(); b._resume_assert_unchanged()

    def test_source_mismatch_rejected_before_namespace_execution(self):
        original = d.original_module(); before = original.info()
        with self.assertRaisesRegex(ValueError, 'SHA'): d._build_runtime(original, b'raise AssertionError("executed")')
        self.assertEqual(original.info(), before)

    def test_public_factory_rejects_bad_source_before_original_import(self):
        with tempfile.TemporaryDirectory(prefix='p106b-resume-pin-') as directory:
            path = Path(directory) / 'bad_source.py'; path.write_bytes(b'raise AssertionError("must not execute")')
            with patch.object(d, 'SOURCE', path), patch.object(d, 'original_module') as original:
                with self.assertRaises(ValueError): d.build_runtime()
                original.assert_not_called()

    def test_public_entrypoint_pin_failure_is_error9_without_original_import(self):
        with tempfile.TemporaryDirectory(prefix='p106b-resume-entry-') as directory:
            path = Path(directory) / 'bad_source.py'; path.write_bytes(b'bad source')
            with patch.object(d, 'SOURCE', path), patch.object(d, 'original_module') as original, \
                    redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()):
                self.assertEqual(d.main(['--mode', 'source', '--check-only']), 9)
                self.assertIn('[NATIVE_RESUME_FINAL]', output.getvalue()); original.assert_not_called()

    def test_unchanged_computational_and_captured_body_bytecodes(self):
        p = d.build_runtime(); original = d.original_module()
        for name in d.BODY_NAMES:
            self.assertEqual(d.body_sha(getattr(p, name)), d.body_sha(getattr(original, name)), name)
        self.assertIs(p._resume_captured['train_report'].__globals__, vars(p))
        self.assertIs(__import__('inspect').unwrap(p._resume_captured['routed_runtime']).__globals__, vars(p))

    def test_allowlist_is_exact_and_extra_binding_is_rejected(self):
        p = d.build_runtime(); self.assertEqual(set(p._resume_binding_names), set(d.BINDING_ALLOWLIST))
        p.UNRELATED = 1
        with self.assertRaises(ValueError): p._resume_assert_unchanged()

    def test_unlisted_private_global_replacement_is_rejected(self):
        p = d.build_runtime(); p.modules = lambda: ()
        with self.assertRaises(ValueError): p._resume_assert_unchanged()

    def test_same_body_with_original_globals_cannot_replace_private_reference(self):
        p = d.build_runtime(); function = p._resume_captured['worker']
        replacement = types.FunctionType(function.__code__, vars(d.original_module()))
        self.assertEqual(d.body_sha(function), d.body_sha(replacement))
        p._resume_captured['worker'] = replacement
        with self.assertRaises(ValueError): p._resume_assert_unchanged()

    def test_original_deadline_mutation_detected_on_fixture_not_real_module(self):
        with fixture() as f:
            p, o = f['p'], f['origin']; original_end = o.END
            o.END = d.END
            with self.assertRaises(ValueError): p._resume_assert_unchanged()
            o.END = original_end; p._resume_assert_unchanged()

    def test_production_info_json_roundtrip_includes_all_legacy_axes_and_new_pins(self):
        p = d.build_runtime(); value = p.info()
        self.assertEqual(value, json.loads(json.dumps(value))); self.assertTrue(value['code_complete'])
        self.assertIn(d.SCRIPT, value['code_sha256']); self.assertIn(d.TEST, value['code_sha256'])
        self.assertEqual(value['native_updates'], 2281); self.assertEqual(value['new_native_updates'], 0)
        self.assertEqual(value['sft_updates'], 384); self.assertEqual(value['expected_answers'], 1694)
        self.assertEqual(value['original_authority_end_utc'], '2026-10-20T08:00:00+00:00')
        self.assertEqual(value['authority_end_utc'], '2026-10-21T08:00:00+00:00')
        self.assertFalse(value['native_pretraining_allowed'])

    def test_new_phase_commands_never_launch_expired_source_or_duplicate_qcost(self):
        p = d.build_runtime(); phases = p.phase_commands('sft_cost', 'float', None, 1800)
        self.assertEqual([label for label, _ in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertIn('scripts.test_p106b_native_resume', phases[0][1])
        self.assertTrue(all(d.SCRIPT in command for _, command in phases[1:]))
        for args in (('cost', 'float', None), ('train', 'float', None), ('sft_cost', 'ternary', None),
                     ('budget', None, 'native'), ('evaluate', 'float', None), ('source', 'float', None)):
            with self.subTest(args=args), self.assertRaises(ValueError): p.phase_key(*args)

    def test_code_only_cli_does_not_touch_original_namespaces(self):
        p = d.build_runtime()
        with redirect_stdout(io.StringIO()) as output: self.assertEqual(p.main(['--mode', 'source', '--check-only']), 0)
        self.assertIn(d.TAG, output.getvalue()); p._resume_assert_unchanged()


class BridgeTests(unittest.TestCase):
    def test_prepare_worker_and_prepared_readback_use_new_bridge_and_same_old_inputs(self):
        with fixture() as f:
            p = f['p']; self.assertEqual(p.worker('prepare', None, None, 600), 0)
            own, frozen, cases, offsets = p.prepared()
            self.assertEqual(own['status'], 'NATIVE_RESUME_BRIDGE_PREPARED')
            self.assertEqual(frozen, f['frozen']); self.assertEqual(cases, f['cases']); self.assertIs(offsets, f['offsets'])
            self.assertEqual(own['display_ids'], f['reference']['display_ids'])
            self.assertFalse((p.CACHE / 'native_offsets.npy').exists())
            self.assertEqual(own['binding']['original_tag'], f['origin'].TAG)
            self.assertFalse(own['binding']['new_native_training'])
            p._resume_assert_unchanged()

    def test_prepare_is_write_once_and_does_not_mutate_origin(self):
        with fixture() as f:
            p, origin = f['p'], f['origin']; before = origin.info()
            old_files = {path: d.file_sha(path) for path in origin.CACHE.rglob('*') if path.is_file()}
            p.worker('prepare', None, None, 600)
            with self.assertRaises(FileExistsError): p.worker('prepare', None, None, 600)
            self.assertEqual(origin.info(), before)
            self.assertTrue(all(d.file_sha(path) == value for path, value in old_files.items()))

    def test_bridge_damage_and_changed_old_source_are_rejected(self):
        with fixture() as f:
            p = f['p']; p.worker('prepare', None, None, 600)
            data = p.required(p.CACHE / 'frozen_reference.json')
            data['binding']['native_parent_cores']['float'] = '0' * 64
            put(p.CACHE / 'frozen_reference.json', data)
            with self.assertRaises(ValueError): p.prepared()

    def test_original_qcost_is_resource_only_and_returned_without_retagging(self):
        with fixture() as f:
            p, origin = f['p'], f['origin']
            q = p.train_report('sft_cost', 'ternary')
            self.assertEqual(q['tag'], origin.TAG); self.assertNotEqual(q['tag'], p.TAG)
            self.assertEqual(q['authority_end_utc'], '2026-10-20T08:00:00+00:00')
            self.assertFalse((p.EVIDENCE / 'sft_cost_ternary').exists())
            with self.assertRaises(ValueError): p.train_report('cost', 'ternary')

    def test_wrong_old_parent_or_original_date_is_rejected(self):
        with fixture() as f:
            p, origin = f['p'], f['origin']; path = origin.result_path('train_float')
            data = json.loads(path.read_text()); data['authority_end_utc'] = d.END.isoformat(); put(path, data)
            with self.assertRaises(ValueError): p.train_report('train', 'float')

    def test_native_loader_keeps_original_context_and_rejects_random_endpoint(self):
        with fixture() as f:
            p = f['p']
            with p.routed_runtime('float', 'native') as loaded: self.assertEqual(loaded[0], 'SYNTHETIC_ORIGINAL_NATIVE')
            self.assertEqual(f['calls'], [('float', 'native')])
            with self.assertRaises(ValueError):
                with p.routed_runtime('float', None): pass

    def test_native_and_owned_sft_checkpoint_metadata_are_separate(self):
        with fixture() as f:
            p, origin = f['p'], f['origin']
            self.assertEqual(p.checkpoint('float', 'native'), origin.checkpoint('float', 'native'))
            self.assertIn(p.TAG, p.checkpoint('float', 'sft').name)
            own = p.cp_experiment(cp_report(p)); prior = origin.cp_experiment(cp_report(p))
            self.assertEqual(own['tag'], p.TAG); self.assertEqual(prior['tag'], origin.TAG)
            self.assertIs(p.cp_experiment.__globals__, vars(p))

    def test_prior_and_owned_activity_seconds_are_counted_once(self):
        with fixture() as f:
            p = f['p']; self.assertEqual(p.spent_seconds(), 1234.5)
            p.worker('prepare', None, None, 600)
            own = p.required(p.EVIDENCE / 'activity_prepare.json')['seconds']
            self.assertAlmostEqual(p.spent_seconds(), 1234.5 + own)

    def test_new_deadline_record_reserve_and_active_cap(self):
        p = d.build_runtime()
        self.assertEqual(p.authority(True, d.TRAIN_STOP - timedelta(seconds=1)), 1.)
        self.assertEqual(p.execution_remaining(False, d.END - timedelta(seconds=601)), 1.)
        with self.assertRaises(p.Pending): p.execution_remaining(False, d.END - timedelta(seconds=600))
        with fixture(prior_seconds=50000.) as f:
            with self.assertRaises(f['p'].Pending): f['p'].worker('source', None, None, 600)

    def test_metadata_worker_term_writes_failure_activity_and_restores_handler(self):
        with fixture() as f:
            p = f['p']; before = signal.getsignal(signal.SIGTERM)
            f['hooks']['prepared'] = lambda: os.kill(os.getpid(), signal.SIGTERM)
            with self.assertRaises(KeyboardInterrupt): p.worker('prepare', None, None, 600)
            activity = p.required(p.EVIDENCE / 'activity_prepare.json')
            self.assertEqual(activity['returncode'], 130); self.assertFalse(activity['complete'])
            self.assertEqual(activity['error_type'], 'KeyboardInterrupt'); self.assertIsNone(activity['result_sha256'])
            self.assertEqual(signal.getsignal(signal.SIGTERM), before)

    def test_owned_cost_strict_body_consumes_real_temporary_raw_shards(self):
        with fixture() as f:
            reader, report, _ = owned_cost_fixture(f)
            self.assertEqual(reader('sft_cost', 'float'), report)
            self.assertEqual(d.body_sha(reader), d.body_sha(f['p']._resume_captured['train_report']))
            f['p']._resume_assert_unchanged()

    def test_owned_cost_cannot_accept_old_info_or_foreign_native_parent(self):
        with fixture() as f:
            reader, report, _ = owned_cost_fixture(f); p = f['p']; key = p.phase_key('sft_cost', 'float')
            for change in ({'tag': f['origin'].TAG}, {'authority_end_utc': f['origin'].END.isoformat()},
                           {'parent_core_sha256': 'B' * 64}, {'parent_checkpoint_sha256': '0' * 64}):
                damaged = dict(report, **change); put(p.result_path(key), damaged)
                activity_path = p.EVIDENCE / ('activity_' + key + '.json')
                activity = p.required(activity_path); activity['result_sha256'] = p.digest(p.result_path(key)); put(activity_path, activity)
                with self.subTest(change=change), self.assertRaises(ValueError): reader('sft_cost', 'float')

    def test_owned_cost_raw_byte_damage_is_rejected(self):
        with fixture() as f:
            reader, report, _ = owned_cost_fixture(f); p = f['p']
            path = p.RAW / p.phase_key('sft_cost', 'float') / report['event_manifest']['shards'][0]['path']
            with path.open('ab') as stream: stream.write(b'corruption')
            with self.assertRaises(ValueError): reader('sft_cost', 'float')

    def test_owned_sft_payload_does_not_accept_original_tag_even_with_same_shape(self):
        from scripts import p106b_weight_route as method
        @dataclass
        class Config:
            dim: int = 768
            n_layers: int = 14
            vocab_size: int = 32768
        with fixture() as f:
            p, origin = f['p'], f['origin']; cfg = Config(); report = cp_report(p)
            expected = p.cp_experiment(report); env = dict(vars(p))
            env['modules'] = lambda: (None, None, method)
            validate = types.FunctionType(p.validate_payload.__code__, env)
            payload = dict(model={}, cfg=asdict(cfg), step=384, tokenizer_sha256=p.TOKENIZER_SHA,
                tokenizer_lineage='chat32', quantization_route=method.route_metadata('float'), experiment=expected)
            validate(payload, cfg, 'float', 'sft', expected)
            payload['experiment'] = origin.cp_experiment(report)
            with self.assertRaises(ValueError): validate(payload, cfg, 'float', 'sft', expected)

    def test_four_endpoint_raw_readback_body_without_models_or_real_tokenizer(self):
        with fixture() as f:
            readback, fixture_info = endpoint_readback_fixture(f); p = f['p']
            self.assertEqual(d.body_sha(readback), d.body_sha(p.readback))
            with redirect_stdout(io.StringIO()): self.assertEqual(readback(), 0)
            result = p.required(p.result_path('readback'))
            self.assertEqual(result['status'], 'ALL_ROUTE_ENDPOINTS_RECOUNTED')
            self.assertEqual(len(result['summaries']), 4); self.assertEqual(result['expected_answers'], 2)
            self.assertEqual(result['tag'], p.TAG); self.assertEqual(result['code_sha256'], fixture_info['code_sha256'])
            self.assertEqual(result['models_loaded'], 0); p._resume_assert_unchanged()

    def test_four_endpoint_raw_count_damage_is_rejected(self):
        with fixture() as f:
            readback, _ = endpoint_readback_fixture(f); p = f['p']
            path = p.result_path(p.phase_key('evaluate', 'float', 'sft'))
            value = p.required(path); value['actual_cases'] = 1; put(path, value)
            activity_path = p.EVIDENCE / ('activity_' + p.phase_key('evaluate', 'float', 'sft') + '.json')
            activity = p.required(activity_path); activity['result_sha256'] = p.digest(path); put(activity_path, activity)
            with self.assertRaises(ValueError): readback()


class ResourceTests(unittest.TestCase):
    def test_forecast_uses_each_eight_costs_without_native_retraining(self):
        result = d.sft_estimates({'ternary': dict(step_seconds=[3.] + [1.] * 7),
                                 'float': dict(step_seconds=[5.] + [2.] * 7)})
        self.assertEqual(result['ternary_sft'], 3 + 383 * 1.35 + 300)
        self.assertEqual(result['float_sft'], 5 + 2 * 383 * 1.35 + 300)
        for bad in ([1.] * 7, [float('nan')] * 8, [True] * 8, [0.] * 8):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                d.sft_estimates({'ternary': dict(step_seconds=bad), 'float': dict(step_seconds=[1.] * 8)})

    def test_original_launch_body_keeps_stdin0_own_session_and_targeted_term(self):
        p = d.build_runtime(); process = Mock(pid=1234, poll=Mock(return_value=None))
        process.wait.side_effect = [subprocess.TimeoutExpired(['fixture'], 1), 0]
        factory = Mock(return_value=process); kill = Mock()
        env = dict(vars(p)); env['subprocess'] = types.SimpleNamespace(Popen=factory,
            DEVNULL=subprocess.DEVNULL, TimeoutExpired=subprocess.TimeoutExpired)
        env['os'] = types.SimpleNamespace(getpgid=lambda _: 1234, killpg=kill)
        launch = types.FunctionType(p.launch.__code__, env)
        self.assertEqual(launch(['fixture'], 1), 124)
        self.assertEqual(factory.call_args.kwargs['stdin'], subprocess.DEVNULL)
        self.assertTrue(factory.call_args.kwargs['start_new_session'])
        kill.assert_called_once_with(1234, signal.SIGTERM)

    def test_no_cuda_or_model_initialization_in_metadata_suite(self):
        import torch
        self.assertFalse(torch.cuda.is_initialized())


if __name__ == '__main__': unittest.main()
