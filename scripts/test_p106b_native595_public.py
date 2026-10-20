#!/usr/bin/env python3
"""합성 provider/메모리 원형/작은 Torch CPU만 검사한다. 실물 pack/CP/모델/GPU0."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import inspect
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
from unittest.mock import Mock, patch
import warnings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native595_public as d
from scripts import diag_p106b_route_cross_resume as utility
from scripts import test_p106b_current_benchmark as fixtures
from scripts import p106b_weight_route as method
from scripts.test_p106b_native595_broad import synthetic_parent
import torch


def local(function, env):
    source = inspect.unwrap(function)
    value = types.FunctionType(source.__code__, env, source.__name__, source.__defaults__, source.__closure__)
    value.__kwdefaults__ = source.__kwdefaults__
    return value


@contextmanager
def reference_fixture():
    real = d.build_runtime(); memory = fixtures.Memory(); owners, reports, states, closed = {}, {}, {}, {}
    class MemoryPath(type(Path())):
        def is_file(self): return memory.exists(Path(self))
        def exists(self): return memory.exists(Path(self))
    for role, original in real._public_providers.items():
        runtime = types.SimpleNamespace(**vars(original.runtime)); meta = original.runtime.info()
        runtime.info = lambda meta=meta: deepcopy(meta); runtime.check = lambda: None
        runtime.CACHE, runtime.EVIDENCE = MemoryPath(runtime.CACHE), MemoryPath(runtime.EVIDENCE)
        runtime.checkpoint = lambda arm, actual=original.runtime: MemoryPath(actual.checkpoint(arm))
        runtime.path = lambda mode, arm, actual=original.runtime: MemoryPath(actual.path(mode, arm))
        module = types.SimpleNamespace(**vars(original.module))
        runtime.completed = Mock(side_effect=lambda mode, arm, role=role: closed[role, arm])
        reference = runtime.CACHE / ('reference.json' if role == 'native595' else 'frozen_reference.json')
        state = dict(binding=dict(parents={}), synthetic=True)
        memory.write(reference, state)
        for arm in ('ternary', 'float'):
            checkpoint = runtime.checkpoint(arm); memory.files[checkpoint] = ('synthetic ' + role + arm).encode()
            if role == 'newbroad': parent = synthetic_parent(arm)
            elif role == 'oldbroad':
                known = module.PARENTS[arm]
                parent = dict(original_tag='p106b_native_weight_route_v1_s1337', original_training_updates=2281,
                    checkpoint_sha256=known['sha256'], core_sha256=known['core'], report_sha256='D' * 64)
            else: parent = None
            if parent is not None: state['binding']['parents'][arm] = parent
            core = {'native595': 'B', 'oldbroad': 'C', 'newbroad': 'E'}[role] * 64
            report = dict(meta, status='TRAIN_COMPLETE', cost=False, arm=arm,
                updates=4543 if role == 'native595' else 704, checkpoint_writes=1, optimizer_saved=False,
                checkpoint_sha256=memory.digest(checkpoint), final_core_sha256=core,
                initial_core_sha256=module.RECIPE.scratch_core_sha256 if role == 'native595' else parent['core_sha256'],
                parent_checkpoint_sha256=None if parent is None else parent['checkpoint_sha256'],
                parent_core_sha256=None if parent is None else parent['core_sha256'],
                quantization_route=method.route_metadata(arm))
            if parent is None: report['totals'] = dict(targets=595460096, x_tokens=595460096)
            else:
                report.update(endpoint='native_broad4', passes=4, objective='L0_TOKEN_MEAN_OVER_WHOLE_UPDATE',
                    totals=module.EXPECTED, scratch_core_sha256='028C46B232D6D4C5205CAF15A7C259E3B1687347FC4838D00B3F3CB938C0D1C5',
                    parent_report_sha256=parent['report_sha256'], native_offsets_sha256='D' * 64,
                    ordered_records_sha256='E' * 64, original_schedules_sha256='F' * 64)
            reports[role, arm] = report
        # reference 바이트는 양쪽 부모 descriptor를 넣은 뒤 동결한다. 원 파일은 없다.
        memory.files[reference] = json.dumps(state).encode()
        states[role] = (deepcopy(state), []) if role == 'native595' else ({'synthetic_course': True}, deepcopy(state))
        for arm in ('ternary', 'float'):
            report = reports[role, arm]; report['reference_sha256'] = memory.digest(reference)
            path = runtime.path('train', arm); memory.write(path, report)
            stamp = datetime(2026, 10, 20, 20, tzinfo=timezone.utc).isoformat()
            activity = dict(schema=module.SCHEMA, tag=module.TAG, key='train_' + arm, mode='train', arm=arm,
                complete=True, returncode=0, error_type=None, code_sha256=meta['code_sha256'],
                result_sha256=memory.digest(path), reference_sha256=memory.digest(reference),
                started_at=stamp, ended_at=stamp, seconds=.1, max_wall_sec=18000 if role == 'native595' else 7200,
                **(dict(pid=7, pgid=7) if role == 'native595' else dict(worker_pid=7, worker_pgid=7)))
            closed[role, arm] = activity
            memory.write(runtime.EVIDENCE / ('activity_train_' + arm + '.json'), activity)
        module.prepared = Mock(side_effect=lambda rt, role=role: states[role])
        def read(rt, arm, *, cost, state=None, role=role):
            if cost or state is not None and state is not states[role]: raise AssertionError('정확한 costFalse/동결 state가 필요하다')
            return reports[role, arm]
        module.read_training = Mock(side_effect=read)
        activity_env = dict(vars(original.module), file_sha=memory.digest)
        module.validate_activity = local(original.module.validate_activity, activity_env)
        owners[role] = d.Provider(role, module, runtime)
    p = types.SimpleNamespace(**vars(real)); p.digest, p.required = memory.digest, memory.read
    p.tokenizer = lambda: fixtures.Tokens()
    p.authority = lambda: 100000.
    p.model_reference = lambda model: d.model_reference_for(p, owners, model)
    yield types.SimpleNamespace(real=real, p=p, memory=memory, owners=owners, reports=reports, states=states, closed=closed)


@contextmanager
def raw_fixture():
    real = d.build_runtime(); meta = real.info()
    with tempfile.TemporaryDirectory(prefix='native595_public_') as directory:
        root = Path(directory); env = dict(vars(real))
        env.update(ROOT=root, CACHE=root / 'cache', RAW=root / 'raw', EVIDENCE=root / 'evidence',
            info=lambda: deepcopy(meta), authority=lambda: 100000.)
        p = types.SimpleNamespace(**env)
        names = ('safe', 'exists', 'digest', 'raw_bytes', 'required', 'write', 'phase_key', 'result_path',
            'completed_activity', 'spent_seconds', 'remaining_activity', 'launch_phase')
        for name in names: setattr(p, name, local(getattr(real, name), env))
        p.worker = local(real._public_captured['worker'], env)
        p.validate_activity = local(real._public_captured['validate_activity'], env)
        env.update(vars(p))
        def prepare():
            p.write(p.CACHE / 'frozen_reference.json', dict(synthetic=True))
            p.write(p.result_path('prepare'), dict(synthetic=True)); return 0
        env['prepare'] = prepare; p.prepare = prepare
        yield p, env, real


def activity(p, seconds=3., *, complete=True):
    start = d.END - timedelta(hours=2)
    return dict(schema=p.SCHEMA, tag=p.TAG, key='prepare', mode='prepare', model_id=None,
        seconds=seconds, max_wall_sec=60, returncode=0 if complete else 130,
        complete=complete, error_type=None if complete else 'KeyboardInterrupt', worker_pid=7, worker_pgid=7,
        code_sha256=p.info()['code_sha256'], started_at=start.isoformat(), ended_at=(start + timedelta(seconds=seconds)).isoformat(),
        result_sha256=p.digest(p.result_path('prepare')), reference_sha256=p.digest(p.CACHE / 'frozen_reference.json'))


def worker_fixture(term=False):
    with raw_fixture() as (p, env, real):
        if term: env['prepare'] = lambda: signal.raise_signal(signal.SIGTERM)
        try: result = p.worker('prepare', None, 60)
        except KeyboardInterrupt:
            saved = p.required(p.EVIDENCE / 'activity_prepare.json')
            print(json.dumps(dict(activity=saved)), flush=True); return 130
        saved = p.completed_activity('prepare')
        print(json.dumps(dict(returncode=result, complete=saved['complete'])), flush=True); return result


def generation(row, tok):
    ids = tok.encode(row['prompt']).ids; new = [88, 4]; decoded = tok.decode(ids + new)
    return dict(precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False, max_new=128,
        requested_max_new=128, effective_max_new=128, prompt_sha256=d.sha(row['prompt']), prompt_ids=ids,
        prompt_ids_sha256=d.sha(ids), requested_prompt_tokens=len(ids), effective_prompt_tokens=len(ids), truncated=False,
        eos_token_available=True, stop_at_eos_requested=True, stop_at_eos_effective=True, stop_token_sequences=[[4]],
        historical_answer_extraction=True, generated_ids=new, generated_ids_sha256=d.sha(new), generated_tokens=2,
        terminal_ids=[4], finish_reason='STOP_SEQUENCE', matched_stop_sequence=[4], decoded_total=decoded,
        body='X', raw_new_text='X<|im_end|>')


class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.p = d.build_runtime()
    def tearDown(self): self.p._public_assert_unchanged()

    def test_source_pins_before_import_and_exact_root_f4(self):
        with patch.object(d, 'checked_sources', side_effect=ValueError('pin')), patch.object(d.importlib, 'import_module') as load:
            with self.assertRaises(ValueError): d.build_runtime()
        load.assert_not_called()
        self.assertEqual(set(d.checked_sources()), set(d.SOURCE_PINS))

    def test_exact_named_six_and_student_cohorts(self):
        self.assertEqual(self.p.MODELS, d.MODELS); self.assertEqual(self.p.STUDENTS, d.MODELS[2:])
        self.assertTrue(all('mixed' not in name and 'staged' not in name for name in self.p.MODELS))
        rows = fixtures.all_rows(); tok = fixtures.Tokens()
        requested = [len(self.p.cohort(rows, name)) for name in self.p.MODELS]
        scored = [sum(self.p.eligibility(r, tok) is None for r in self.p.cohort(rows, name)) for name in self.p.MODELS]
        self.assertEqual(requested, [768, 768, 1920, 1920, 1920, 1920]); self.assertEqual(sum(requested), 9216)
        self.assertEqual(scored, [768, 768, 1919, 1919, 1919, 1919]); self.assertEqual(sum(scored), 9212)

    def test_full_info_serialization_and_original_scoring_fields(self):
        now, old = self.p.info(), self.p._public_original.info()
        self.assertEqual(now, json.loads(json.dumps(now)))
        for name in old:
            if name not in ('schema', 'tag', 'models', 'code_sha256', 'code_complete', 'authority_end_utc'):
                self.assertEqual(now[name], old[name], name)
        self.assertEqual(now['maximum_worker_seconds'], 1800)
        self.assertEqual(now['actual_model_references'], 'ONLY_CPU_PREPARE_AFTER_ALL_SIX_COMPLETED')

    def test_private_bodies_captured_globals_and_fp32_class_are_exact(self):
        p = self.p
        for name in d.BODY_NAMES:
            self.assertEqual(utility.body_sha(getattr(p, name)), utility.body_sha(getattr(p._public_original, name)))
            self.assertIs(inspect.unwrap(getattr(p, name)).__globals__, vars(p))
        for name in d.CAPTURED_NAMES:
            self.assertEqual(utility.body_sha(p._public_captured[name]), utility.body_sha(getattr(p._public_original, name)))
            self.assertIs(inspect.unwrap(p._public_captured[name]).__globals__, vars(p))
        for name in ('__init__', '__getattr__', '__call__'):
            self.assertEqual(utility.body_sha(getattr(p.FP32Forward, name)), utility.body_sha(getattr(p._public_original.FP32Forward, name)))

    def test_original_models_dates_globals_and_fixed_pack_are_unchanged(self):
        p = self.p
        self.assertEqual(p._public_original.MODELS, ('native_ternary', 'native_float', 'sft_ternary', 'sft_float', 'broad_mixed', 'broad_staged'))
        self.assertEqual(p._public_original.END.isoformat(), '2026-10-20T08:00:00+00:00')
        self.assertEqual(p.FIXED, p._public_original.FIXED); self.assertIs(p.n, p._public_original.n)
        self.assertFalse(hasattr(p.recovery, 'runtime_scope'))

    def test_binding_fixed_map_and_captured_body_tamper_rejected(self):
        p = self.p; previous = p.STUDENTS
        try:
            p.STUDENTS = p.MODELS
            with self.assertRaises(ValueError): p._public_assert_unchanged()
        finally: p.STUDENTS = previous
        key = next(iter(p.FIXED)); old = p.FIXED[key]
        try:
            p.FIXED[key] = 'F' * 64
            with self.assertRaises(ValueError): p._public_assert_unchanged()
        finally: p.FIXED[key] = old
        try:
            p.forbidden_extra_loader = object()
            with self.assertRaises(ValueError): p._public_assert_unchanged()
        finally: del p.forbidden_extra_loader

    def test_own_declared_cohort_and_captured_reference_mutation_rejected(self):
        p = self.p; old = d.MODEL_TABLE[0]['cohort']
        try:
            d.MODEL_TABLE[0]['cohort'] = 'FULL_PUBLIC1919_scored_requested1920'
            with self.assertRaises(ValueError): p._public_assert_unchanged()
        finally: d.MODEL_TABLE[0]['cohort'] = old
        old = p._public_captured['model_reference']
        try:
            p._public_captured['model_reference'] = lambda *_: None
            with self.assertRaises(ValueError): p._public_assert_unchanged()
        finally: p._public_captured['model_reference'] = old

    def test_phase_commands_all_new_driver_and_worker_cap(self):
        for mode, model in (('prepare', None), ('evaluate', 'newbroad_float'), ('readback', None)):
            phases = self.p.phase_commands(mode, model, 1800)
            self.assertEqual([label for label, _ in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
            self.assertIn(d.TEST[:-3].replace('/', '.'), phases[0][1])
            for _, command in phases[1:]: self.assertEqual(command.count(d.SCRIPT), 1)
        for cap in (59, 1801, True):
            with self.assertRaises(ValueError): self.p.phase_commands('evaluate', 'native595_float', cap)
        with self.assertRaises(ValueError): self.p.worker('source', None, 1801)
        with self.assertRaises(ValueError): self.p.validate_activity(dict(max_wall_sec=1801), 'prepare')

    def test_deadline_record_and_check_only_read_no_assets(self):
        p = self.p; self.assertEqual(p.authority(d.END - timedelta(seconds=660)), 60.)
        with self.assertRaises(p.Pending): p.authority(d.END - timedelta(seconds=600))
        with patch.object(d, 'build_runtime', return_value=p), patch.object(d, 'model_reference_for', side_effect=AssertionError('자산0')):
            with redirect_stdout(io.StringIO()) as out: self.assertEqual(d.main(['--mode', 'prepare', '--check-only']), 0)
        self.assertEqual(json.loads(out.getvalue().split(' ', 1)[1])['tag'], d.TAG)

    def test_unadmitted_reference_and_old_or_generic_model_rejected(self):
        with self.assertRaises(ValueError):
            with self.p.model_runtime('sft_float', {}): self.fail('옛ID0')
        with reference_fixture() as f:
            spec = f.p.model_reference('native595_float')
            with patch.object(d, 'load_model_for') as load:
                with self.assertRaises(ValueError):
                    with self.p.model_runtime('native595_float', spec): self.fail('미검산0')
            load.assert_not_called()
            with patch.object(d, 'model_reference_for', return_value=spec): admitted = self.p.model_reference('native595_float')
            changed = dict(admitted, core_sha256='F' * 64)
            with self.assertRaises(ValueError):
                with self.p.model_runtime('native595_float', changed): self.fail('변조0')


class ReferenceTests(unittest.TestCase):
    def test_six_actual_reference_roles_and_no_retag(self):
        with reference_fixture() as f:
            before = deepcopy(f.reports); values = {model: f.p.model_reference(model) for model in d.MODELS}
            self.assertEqual(f.reports, before)
            self.assertEqual([v['provider_role'] for v in values.values()], ['native595'] * 2 + ['oldbroad'] * 2 + ['newbroad'] * 2)
            self.assertEqual([v['updates'] for v in values.values()], [4543] * 2 + [704] * 4)
            self.assertTrue(all(v['family'] == 'native_weight_route' for v in values.values()))
            for owner in f.owners.values():
                self.assertFalse(owner.module.read_training.call_args.kwargs['cost'])
                self.assertIs(owner.module.read_training.call_args.kwargs['state'], f.states[owner.role])

    def test_any_missing_sixth_endpoint_holds_entire_source(self):
        with reference_fixture() as f:
            f.owners['newbroad'].module.read_training.side_effect = f.p.Pending('학생 미완료')
            env = dict(vars(f.p), tokenizer=lambda: fixtures.Tokens(), read_public=lambda _: ({'manifest': {}}, [], {}),
                cached_falcon=lambda _: ({}, []), model_reference=f.p.model_reference)
            with self.assertRaises(f.p.Pending): local(f.real.source_state, env)()

    def test_valid_failed_upstream_holds_but_tampered_activity_is_error(self):
        for damaged in (False, True):
            with self.subTest(damaged=damaged), reference_fixture() as f:
                owner = f.owners['native595']; path = owner.runtime.EVIDENCE / 'activity_train_float.json'
                value = f.memory.read(path); value.update(complete=False, returncode=130, error_type='KeyboardInterrupt')
                if damaged: value['code_sha256'] = {}
                f.memory.files[path] = json.dumps(value).encode()
                with self.assertRaises(ValueError if damaged else f.p.Pending): f.p.model_reference('native595_float')
                owner.module.prepared.assert_not_called(); owner.module.read_training.assert_not_called()

    def test_wrong_report_tag_arm_step_route_core_and_info_date_rejected(self):
        for role, arm, name, bad in (('native595', 'float', 'updates', 8), ('native595', 'float', 'updates', 2281),
                ('native595', 'float', 'tag', d.PROVIDER_TAGS['oldbroad']), ('newbroad', 'float', 'arm', 'ternary'),
                ('oldbroad', 'float', 'passes', 2), ('oldbroad', 'float', 'final_core_sha256', 'bad'),
                ('newbroad', 'float', 'authority_end_utc', '2026-10-20T08:00:00+00:00'),
                ('native595', 'float', 'quantization_route', method.route_metadata('ternary'))):
            with self.subTest(name=name), reference_fixture() as f:
                f.reports[role, arm][name] = bad
                with self.assertRaises(ValueError): f.p.model_reference(role + '_' + arm)

    def test_checkpoint_report_activity_reference_wrong_sha_rejected(self):
        for field in ('checkpoint_sha256', 'reference_sha256'):
            with self.subTest(field=field), reference_fixture() as f:
                f.reports['native595', 'float'][field] = 'F' * 64
                with self.assertRaises(ValueError): f.p.model_reference('native595_float')
        for field, bad in (('result_sha256', 'F' * 64), ('reference_sha256', 'F' * 64), ('tag', 'old'), ('complete', False), ('code_sha256', {})):
            with self.subTest(field=field), reference_fixture() as f:
                f.closed['newbroad', 'float'][field] = bad
                with self.assertRaises(ValueError): f.p.model_reference('newbroad_float')

    def test_newbroad_parent_descriptor_old299_or_wrong_core_rejected(self):
        for field, bad in (('original_training_updates', 2281), ('original_tag', 'old'), ('core_sha256', 'F' * 64)):
            with self.subTest(field=field), reference_fixture() as f:
                f.states['newbroad'][1]['binding']['parents']['float'][field] = bad
                with self.assertRaises(ValueError): f.p.model_reference('newbroad_float')
        with reference_fixture() as f:
            f.reports['oldbroad', 'float']['parent_core_sha256'] = 'F' * 64
            with self.assertRaises(ValueError): f.p.model_reference('oldbroad_float')

    def test_reference_wrong_role_tag_paths_route_and_missing_fields_rejected(self):
        with reference_fixture() as f:
            spec = f.p.model_reference('newbroad_float')
            for field, bad in (('family', 'broad_v2'), ('provider_role', 'oldbroad'), ('trained_tag', d.PROVIDER_TAGS['oldbroad']),
                    ('model_id', 'native595_float'), ('route', method.route_metadata('ternary')), ('updates', 352),
                    ('training_report', 'test_result/evidence/old/report.json'), ('checkpoint', 'runs/ckpt/old.pt'),
                    ('provider_info_sha256', 'F' * 64), ('parent_core_sha256', None)):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    d.validate_spec(f.p, f.owners, 'newbroad_float', dict(spec, **{field: bad}))
            partial = dict(spec); partial.pop('training_activity_sha256')
            with self.assertRaises(ValueError): d.validate_spec(f.p, f.owners, 'newbroad_float', partial)
            native = f.p.model_reference('native595_float')
            for field in ('initial_core_sha256', 'scratch_core_sha256'):
                with self.assertRaises(ValueError):
                    d.validate_spec(f.p, f.owners, 'native595_float', dict(native, **{field: 'F' * 64}))

    def test_full_info_prepare_roundtrip_binds_all_six_and_is_writeonce(self):
        with reference_fixture() as f:
            rows = fixtures.all_rows(); models = {m: f.p.model_reference(m) for m in d.MODELS}
            binding = dict(models=models, exclusions={f.p.row_id(row): f.p.eligibility(row, fixtures.Tokens()) for row in rows})
            env = dict(vars(f.p), source_state=lambda: (binding, rows, fixtures.Tokens(), []), exists=f.memory.exists,
                write=f.memory.write, required=f.memory.read, digest=f.memory.digest, completed_activity=lambda *_: None)
            prepare, prepared = local(f.real.prepare, env), local(f.real.prepared, env)
            with redirect_stdout(io.StringIO()): self.assertEqual(prepare(), 0)
            value = prepared()[0]; self.assertEqual(value['binding']['models'], models); self.assertEqual(value['models_loaded'], 0)
            with self.assertRaises(FileExistsError): prepare()
            changed = deepcopy(value); changed['binding']['models'].pop('newbroad_float')
            f.memory.files[f.p.CACHE / 'frozen_reference.json'] = json.dumps(changed).encode()
            with self.assertRaises(ValueError): prepared()


class LoaderTests(unittest.TestCase):
    class Tiny(torch.nn.Linear):
        def clear_quant(self): self.cleared = True
        def set_anneal(self, value): self.anneal = value
        def freeze_quant(self): self.frozen = True

    def fixture_context(self, f, role, arm):
        from scripts.diag_p101a_sft_mtp import state_fingerprint
        model = self.Tiny(2, 2); model.cfg = fixtures.Cfg(); owner = f.owners[role]; calls = []
        tok = fixtures.Tokens(); route = types.SimpleNamespace(mode=arm, metadata=method.route_metadata(arm), assert_active=Mock())
        report = f.reports[role, arm]; report['final_core_sha256'] = state_fingerprint(model)
        path = owner.runtime.path('train', arm); f.memory.files[path] = json.dumps(report).encode()
        f.closed[role, arm]['result_sha256'] = f.memory.digest(path)
        activity_path = owner.runtime.EVIDENCE / ('activity_train_' + arm + '.json')
        f.memory.files[activity_path] = json.dumps(f.closed[role, arm]).encode()
        @contextmanager
        def context(runtime, actual_arm, actual_report):
            self.assertIs(runtime, owner.runtime); self.assertIs(actual_report, report); self.assertEqual(actual_arm, arm)
            calls.append('enter')
            try: yield (torch, model, route) if role == 'native595' else (torch, model, model.cfg, tok, route)
            finally: calls.append('exit')
        if role == 'native595': owner.module.loaded_runtime = context
        else: owner.module.child_runtime = context
        return model, tok, route, calls

    def test_native3_to5_and_broad5_tuples_use_exact_own_context(self):
        for role in d.PROVIDER_TAGS:
            with self.subTest(role=role), reference_fixture() as f:
                model, tok, route, calls = self.fixture_context(f, role, 'float')
                spec = f.p.model_reference(role + '_float'); before = [v.detach().clone() for v in model.parameters()]
                with d.load_model_for(f.p, f.owners, role + '_float', spec) as values:
                    self.assertEqual(len(values), 5); self.assertIs(values[1], model); self.assertIs(values[2], model.cfg)
                    self.assertIs(values[4], route); self.assertFalse(model.training); self.assertTrue(model.frozen)
                    self.assertTrue(all(v.requires_grad for v in model.parameters())); self.assertEqual(calls, ['enter'])
                self.assertEqual(calls, ['enter', 'exit']); self.assertTrue(model.cleared)
                self.assertTrue(all(torch.equal(a, b) for a, b in zip(before, model.parameters())))

    def test_deadline_before_source_and_late_model_entry(self):
        with reference_fixture() as f:
            model, _, _, calls = self.fixture_context(f, 'native595', 'float'); spec = f.p.model_reference('native595_float')
            times = iter([100., f.p.Pending('기한')])
            def clock():
                value = next(times)
                if isinstance(value, BaseException): raise value
                return value
            f.p.authority = clock
            with self.assertRaises(f.p.Pending):
                with d.load_model_for(f.p, f.owners, 'native595_float', spec): self.fail('기한 뒤 모델0')
            self.assertEqual(calls, [])

    def test_wrong_actual_route_core_or_cfg_never_yields(self):
        for kind in ('route', 'core', 'cfg'):
            with self.subTest(kind=kind), reference_fixture() as f:
                model, _, route, calls = self.fixture_context(f, 'newbroad', 'float'); spec = f.p.model_reference('newbroad_float')
                if kind == 'route': route.mode = 'ternary'
                elif kind == 'core':
                    with torch.no_grad(): model.weight.add_(.1)
                else: model.cfg.max_seq_len = 512
                with self.assertRaises(ValueError):
                    with d.load_model_for(f.p, f.owners, 'newbroad_float', spec): self.fail('잘못된 실제모델0')
                self.assertEqual(calls, ['enter', 'exit'])


class NumericalRawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.p = d.build_runtime()

    def test_fp32_wrapper_actual_small_cpu_scorer_under_outer_bf16(self):
        import torch.nn.functional as F
        model = fixtures.Toy(); before = torch.cuda.is_initialized()
        with warnings.catch_warnings(), torch.autocast('cpu', dtype=torch.bfloat16):
            warnings.simplefilter('ignore', UserWarning)
            result = self.p.suite.run_mc('piqa', [fixtures.row()['item']], self.p.FP32Forward(model), fixtures.Tokens(), 'cpu', 1024, torch, F, True)
        self.assertEqual(len(result['rows']), 1); self.assertFalse(result['skip_rows'])
        self.assertTrue(all(v['dtype'] == torch.float32 and not v['cpu_autocast'] and v['math'] and not v['flash'] for v in model.observed))
        self.assertEqual(torch.cuda.is_initialized(), before)

    def test_mc_primary_sum_and_char_diagnostic_are_preserved(self):
        p = self.p; row = fixtures.row(); event = dict(p.event_base(row, {}), skipped=False,
            scores=fixtures.scores(row), encoding=p.mc_encoding(row, fixtures.Tokens()))
        p.validate_event(event, row, fixtures.Tokens(), {}, None)
        event['scores']['pred_harness'] = 1
        with self.assertRaises(ValueError): p.validate_event(event, row, fixtures.Tokens(), {}, None)

    def test_raw_shard_partial_wrong_hash_and_path_rejected_before_consumer(self):
        p = self.p; memory = fixtures.Memory(); directory = p.RAW / 'synthetic_only'
        manifest = memory.shards(directory, 'answers', [dict(i=1)])
        env = dict(vars(p), required=memory.read, raw_bytes=memory.raw)
        reader = local(p.read_shards, env)
        self.assertEqual(reader(directory, manifest, 'answers', 1), [dict(i=1)])
        for changes in (dict(rows=2), dict(concat_sha256='F' * 64), dict(limit_bytes=20_000_001)):
            with self.assertRaises(ValueError): reader(directory, dict(manifest, **changes), 'answers', 1)
        bad = deepcopy(manifest); bad['shards'][0]['path'] = '../answers_000000.jsonl'
        with self.assertRaises(ValueError): reader(directory, bad, 'answers', 1)

    def test_protected_and_escaped_paths_rejected_without_open(self):
        p = self.p
        for path in (ROOT / 'datasets/TinyDataset/private.txt', ROOT / '.aws/credentials', ROOT / '.claude/a',
                ROOT / '../outside', Path('/etc/private.txt')):
            with self.subTest(path=str(path)), patch.object(Path, 'open', side_effect=AssertionError('읽기 전에 거부')):
                with self.assertRaises(ValueError): p.raw_bytes(path)

    def test_greedy128_receipt_free_score_and_length_negative(self):
        p = self.p; tok = fixtures.Tokens(); row = fixtures.row('gsm8k_free'); value = generation(row, tok)
        p.validate_generation('X', value, row, tok)
        for field, bad in (('effective_max_new', 64), ('truncated', True), ('body', 'bad'), ('generated_ids', [88, 2])):
            with self.subTest(field=field), self.assertRaises(ValueError): p.validate_generation('X', dict(value, **{field: bad}), row, tok)
        row['golds'] = ['12']; self.assertEqual(p.score_free(row, 'answer is 12')['numeric_exact'], 0)
        self.assertEqual(p.score_free(row, 'work #### 12')['numeric_exact'], 1)
        long = fixtures.row('korquad_free'); long.update(prompt='L' * 897, prompt_tokens=897)
        self.assertEqual(p.eligibility(long, tok), 'full_prompt_plus128_exceeds1024')

    def test_all9216_requested9212_raw_readback_with_real_recount_and_cached_ids(self):
        with reference_fixture() as f:
            p = f.p; rows = fixtures.all_rows(); tok = fixtures.Tokens(); memory = f.memory
            originals, cached_events = fixtures.cache_fixture(rows)
            cached = p.validate_cached_mc(originals, cached_events, rows, tok)
            models = {name: p.model_reference(name) for name in d.MODELS}
            exclusions = {p.row_id(row): p.eligibility(row, tok) for row in rows}
            reference = dict(binding=dict(models=models, exclusions=exclusions, cached_falcon=dict(reused_rows=768)))
            memory.write(p.CACHE / 'frozen_reference.json', reference)
            env = dict(vars(p), required=memory.read, raw_bytes=memory.raw, digest=memory.digest, write=memory.write,
                completed_activity=lambda *_: None, prepared=lambda: (reference, rows, tok, cached), authority=lambda: 100000.)
            env['read_shards'] = local(p.read_shards, env); env['read_model'] = local(p.read_model, env)
            for name in d.MODELS:
                spec = models[name]; selected = p.cohort(rows, name); cfg = asdict(fixtures.Cfg())
                lineage = dict(tag=d.TAG, model_id=name, checkpoint_sha256=spec['checkpoint_sha256'], core_sha256=spec['core_sha256'],
                    route=spec['route'], cfg_sha256=d.sha(cfg), reference_sha256=memory.digest(p.CACHE / 'frozen_reference.json'))
                events = []
                for row in selected:
                    event = dict(p.event_base(row, lineage)); exclusion = exclusions[p.row_id(row)]
                    if exclusion: event.update(skipped=True, reason=exclusion)
                    elif row['kind'] == 'mc': event.update(skipped=False, scores=fixtures.scores(row), encoding=p.mc_encoding(row, tok))
                    else: event.update(skipped=False, answer='X', generation=generation(row, tok), scores=p.score_free(row, 'X'))
                    events.append(event)
                manifest = memory.shards(p.RAW / p.phase_key('evaluate', name), 'answers', events, lineage)
                route = dict(mode=spec['arm'], metadata=spec['route'], tlinear_instances=1, owned_tlinear_instances=1,
                    refreshed_tlinear_instances=1, forward_methods=['_guarded_forward'],
                    refresh_methods=['_float_refresh' if spec['arm'] == 'float' else '_ternary_refresh'])
                report = dict(p.info(), status='CURRENT_PUBLIC_MODEL_COMPLETE', model_id=name, lineage=lineage, cfg=cfg,
                    cfg_sha256=d.sha(cfg), core_before=spec['core_sha256'], core_after=spec['core_sha256'], requires_grad_unchanged=True,
                    model_exceptions=0, tokenizer_sha256=p.public.TOKENIZER_SHA, checkpoint_sha256=spec['checkpoint_sha256'],
                    raw_manifest=manifest, route=route, summary=p.recount(events, selected), requested=len(selected),
                    scored=sum(not event['skipped'] for event in events), length_excluded=sum(event['skipped'] for event in events))
                memory.write(p.result_path(p.phase_key('evaluate', name)), report)
            self.assertEqual(local(p.readback, env)(), 0)
            result = memory.read(p.result_path('readback'))
            self.assertEqual((result['actual_requested_rows'], result['actual_scored_rows'], result['actual_length_excluded']), (9216, 9212, 4))
            self.assertEqual(set(result['summaries']), set(d.MODELS))


class AccountingTests(unittest.TestCase):
    def test_aux_worker_failed_direct_and_linked_are_counted_once(self):
        with raw_fixture() as (p, env, real):
            p.prepare(); path = p.EVIDENCE / 'activity_prepare.json'; p.write(path, activity(p, complete=False))
            self.assertEqual(p.spent_seconds(), 3.)
            p.write(p.EVIDENCE / 'aux_link.json', dict(tag=p.TAG, code_sha256=p.info()['code_sha256'], command_sha256='C' * 64,
                seconds=5., returncode=130, new_worker_key='prepare', new_worker_sha256=p.digest(path)))
            self.assertEqual(p.spent_seconds(), 5.)
            p.write(p.EVIDENCE / 'aux_readonly.json', dict(tag=p.TAG, code_sha256=p.info()['code_sha256'], command_sha256='D' * 64,
                seconds=2., returncode=8, new_worker_key=None, new_worker_sha256=None))
            self.assertEqual(p.spent_seconds(), 7.)

    def test_wrong_aux_hash_link_or_duplicate_cannot_complete(self):
        with raw_fixture() as (p, env, real):
            p.prepare(); path = p.EVIDENCE / 'activity_prepare.json'; p.write(path, activity(p))
            aux = dict(tag=p.TAG, code_sha256=p.info()['code_sha256'], command_sha256='C' * 64,
                seconds=5., returncode=0, new_worker_key='prepare', new_worker_sha256='F' * 64)
            p.write(p.EVIDENCE / 'aux_one.json', aux)
            with self.assertRaises(ValueError): p.spent_seconds()

    def test_original_activity_bad_tag_date_pgid_and_partial_result_rejected(self):
        with raw_fixture() as (p, env, real):
            p.prepare(); value = activity(p)
            for field, bad in (('tag', 'old'), ('model_id', 'sft_float'), ('worker_pgid', 8),
                    ('ended_at', (d.END + timedelta(seconds=1)).isoformat()), ('seconds', float('nan'))):
                with self.subTest(field=field), self.assertRaises(ValueError): p.validate_activity(dict(value, **{field: bad}), 'prepare')
            value['result_sha256'] = 'F' * 64; p.write(p.EVIDENCE / 'activity_prepare.json', value)
            with self.assertRaises(ValueError): p.completed_activity('prepare')

    def test_family3600_limit_and_writeonce(self):
        with raw_fixture() as (p, env, real):
            p.prepare()
            with self.assertRaises(FileExistsError): p.prepare()
            env['spent_seconds'] = lambda: 3599.
            self.assertEqual(p.remaining_activity(), 1.)
            env['spent_seconds'] = lambda: 3600.
            with self.assertRaises(p.Pending): p.remaining_activity()

    def test_own_pgid_worker_closes_before_reader_and_term_keeps_failure(self):
        for term, code in ((False, 0), (True, 130)):
            command = 'from scripts.test_p106b_native595_public import worker_fixture; raise SystemExit(worker_fixture(' + repr(term) + '))'
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', command], cwd=ROOT, stdin=subprocess.DEVNULL,
                start_new_session=True, capture_output=True, text=True, timeout=45,
                env=dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1'))
            self.assertEqual(result.returncode, code, result.stdout + result.stderr)
            saved = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual(saved['activity']['complete'] if term else saved['complete'], not term)


if __name__ == '__main__': unittest.main()
