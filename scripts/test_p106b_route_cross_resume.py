"""endpoint 계보·메타데이터·임시 raw와 작은 CPU mock만 사용하는 회귀."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout, redirect_stderr
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import inspect
import io
import json
from pathlib import Path
import signal
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_route_cross_resume as d
from scripts import diag_p106b_route_cross_readout as old
from scripts import test_p106b_route_cross_readout as fixtures
from scripts.test_p106b_route_cross_readout import (Memory, FixtureModel, Tokens, cases,
    classify, emit, core)
from scripts import p106b_weight_route as route


def local(function, env):
    original = inspect.unwrap(function)
    value = types.FunctionType(original.__code__, env, original.__name__, original.__defaults__, original.__closure__)
    value.__kwdefaults__ = original.__kwdefaults__
    return value


def providers(p, memory):
    native, resume = (types.SimpleNamespace(**vars(module)) for module in (p._resume_native, p._resume_sft))
    for provider, actual in ((native, p._resume_native), (resume, p._resume_sft)):
        metadata = actual.info()
        provider.info = lambda metadata=metadata: deepcopy(metadata)
        provider.required, provider.digest = memory.required, memory.digest
        provider.cp_experiment = local(p._resume_native.cp_experiment, {'TAG': provider.TAG})
    resume_phase = resume.phase_key
    def resumed_phase(mode, arm=None, endpoint=None):
        if mode == 'train': raise AssertionError('resume에서 native train phase를 찾으면 안 된다')
        return resume_phase(mode, arm, endpoint)
    resume.phase_key = resumed_phase
    reports = {}
    for endpoint in ('native', 'sft'):
        provider = native if endpoint == 'native' else resume
        mode = 'train' if endpoint == 'native' else 'sft'
        for arm, marker in (('ternary', 'B'), ('float', 'C')):
            cp = provider.checkpoint(arm, endpoint)
            memory.files[cp] = ('synthetic CP byte marker ' + endpoint + arm).encode()
            parent = reports.get(('native', arm))
            report = dict(provider.info(), status='TRAIN_COMPLETE', arm=arm, endpoint=endpoint,
                updates=2281 if endpoint == 'native' else 384, cost=False,
                checkpoint_writes=1, optimizer_saved=False, checkpoint_sha256=memory.digest(cp),
                reference_sha256='F' * 64, scratch_core_sha256='A' * 64,
                initial_core_sha256='A' * 64 if parent is None else parent['final_core_sha256'],
                final_core_sha256=marker * 64 if parent is None else ('D' if arm == 'ternary' else 'E') * 64,
                parent_core_sha256=None if parent is None else parent['final_core_sha256'],
                parent_checkpoint_sha256=None if parent is None else parent['checkpoint_sha256'])
            reports[endpoint, arm] = report
            key = provider.phase_key(mode, arm)
            memory.write(provider.result_path(key), report)
            memory.write(provider.EVIDENCE / ('activity_' + key + '.json'), {'synthetic': key})
    for provider, endpoint in ((native, 'native'), (resume, 'sft')):
        def training(mode, arm, endpoint=endpoint):
            if mode != ('train' if endpoint == 'native' else 'sft'):
                raise AssertionError('다른 endpoint의 training provider를 사용했다')
            return reports[endpoint, arm]
        provider.train_report = Mock(side_effect=training)
        provider.completed_activity = Mock(return_value={'fixture': True})
    return native, resume, reports


@contextmanager
def source_fixture():
    p = d.build_runtime(); memory = Memory()
    native, resume, reports = providers(p, memory)
    cc = [dict(id=f'fixture_{i:04d}', lane='user_seen' if i >= 1688 else 'fixture') for i in range(1694)]
    original_ref = dict(tag=d.NATIVE_TAG, binding=dict(source_cases_sha256=d.sha(cc), mask='synthetic'))
    memory.write(native.CACHE / 'frozen_reference.json', original_ref)
    reference = dict(tag=d.SFT_TAG, status='NATIVE_RESUME_BRIDGE_PREPARED',
        binding=dict(original_tag=d.NATIVE_TAG, cases_sha256=d.sha(cc),
            original_reference_sha256=memory.digest(native.CACHE / 'frozen_reference.json'),
            original_source_binding_sha256=d.sha(original_ref['binding'])))
    memory.write(resume.CACHE / 'frozen_reference.json', reference)
    memory.write(resume.EVIDENCE / 'cpu_contract.json', {'synthetic': True})
    resume.prepared = Mock(return_value=(reference, {}, cc, []))
    def diagonal(trained, endpoint, training, cc, tok):
        key = resume.phase_key('evaluate', trained, endpoint)
        memory.write(resume.result_path(key), {'synthetic': key})
        memory.write(resume.EVIDENCE / ('activity_' + key + '.json'), {'synthetic': key})
        manifest = dict(rows=1694, source='synthetic; no model answers')
        memory.write(resume.RAW / key / 'answers_shards_manifest.json', manifest)
        return dict(raw_manifest=manifest, native32_fp32={'fixture': True}), [None] * 1694, {'fixture': True}
    env = types.SimpleNamespace(**vars(p))
    env.digest, env.tokenizer, env.prefix_case = memory.digest, lambda: None, Mock()
    env.diagonal = Mock(side_effect=diagonal)
    yield types.SimpleNamespace(p=env, native=native, resume=resume, reports=reports, cc=cc,
        reference=reference, original_ref=original_ref, memory=memory)


@contextmanager
def raw_fixture():
    """원 worker/reader 본문을 임시 namespace에서 실행한다. 실물 source_state는 부르지 않는다."""
    real = d.build_runtime()
    with tempfile.TemporaryDirectory(prefix='route-cross-resume-') as temporary:
        root = Path(temporary); env = dict(vars(real))
        env.update(ROOT=root, CACHE=root / 'cache', RAW=root / 'raw', EVIDENCE=root / 'evidence',
            info=lambda: real.info(), authority=lambda: 100000.)
        p = types.SimpleNamespace(**env)
        for name in ('safe', 'exists', 'digest', 'raw_bytes', 'required', 'write', 'result_path', 'phase_key',
                     'read_answers', 'validate_activity', 'completed_activity'):
            setattr(p, name, local(getattr(real, name), env))
        env.update(vars(p))
        def prepare():
            p.write(p.CACHE / 'frozen_reference.json', {'fixture': True})
            p.write(p.result_path('prepare'), {'fixture': True})
            return 0
        env['prepare'] = prepare
        p.prepare = prepare
        p.spent_seconds = lambda: d.spent_seconds_for(p)
        yield p, env, real


def completed_record(p, *, seconds=10., complete=True):
    started = d.END - timedelta(hours=1)
    return dict(schema=p.SCHEMA, tag=p.TAG, key='prepare', mode='prepare', trained_mode=None,
        inference_mode=None, endpoint=None, seconds=seconds, max_wall_sec=60, worker_pid=7, worker_pgid=7,
        returncode=0 if complete else 130, complete=complete,
        error_type=None if complete else 'KeyboardInterrupt', code_sha256=p.info()['code_sha256'],
        started_at=started.isoformat(), ended_at=(started + timedelta(seconds=seconds)).isoformat(),
        result_sha256=p.digest(p.result_path('prepare')) if p.exists(p.result_path('prepare')) else None,
        reference_sha256=p.digest(p.CACHE / 'frozen_reference.json') if p.exists(p.CACHE / 'frozen_reference.json') else None)


class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.p = d.build_runtime()

    def tearDown(self): self.p._resume_assert_unchanged()

    def test_pin_verification_precedes_import(self):
        with patch.object(d, 'checked_sources', side_effect=ValueError('pin')), patch.object(d.importlib, 'import_module') as load:
            with self.assertRaises(ValueError): d.build_runtime()
        load.assert_not_called()

    def test_four_frozen_code_pins_match(self):
        self.assertEqual(set(d.checked_sources()), set(d.SOURCE_PINS))

    def test_bad_cross_bytes_are_rejected_before_private_execution(self):
        with self.assertRaisesRegex(ValueError, 'source'):
            d._build_runtime(self.p._resume_original, self.p._resume_native, self.p._resume_sft, b'bad source')

    def test_info_preserves_protocol_and_explicitly_separates_three_provider_roles(self):
        info = self.p.info(); original = self.p._resume_original.info()
        for key in ('cases_per_cell', 'new_off_diagonal_cells', 'new_answers', 'reused_diagonal_cells',
                    'reused_answers', 'max_new', 'precision', 'greedy', 'kv_on', 'mtp',
                    'record_reserve_seconds', 'optimizer_updates', 'checkpoint_writes', 'intervention'):
            self.assertEqual(info[key], original[key], key)
        self.assertEqual(info['native_training_tag'], d.NATIVE_TAG)
        self.assertEqual(info['sft_training_tag'], d.SFT_TAG)
        self.assertEqual(info['diagonal_provider_tag'], d.SFT_TAG)
        self.assertEqual(info['family_active_limit_seconds'], 8400)
        self.assertEqual(info['authority_end_utc'], d.END.isoformat())
        self.assertTrue(info['code_complete'])

    def test_all_compute_bodies_and_private_globals_match_original(self):
        for name in d.BODY_NAMES:
            function = getattr(self.p, name)
            self.assertEqual(d.body_sha(function), d.body_sha(getattr(self.p._resume_original, name)), name)
            self.assertIs(inspect.unwrap(function).__globals__, vars(self.p), name)
        for value in self.p._resume_captured.values():
            self.assertIs(inspect.unwrap(value).__globals__, vars(self.p))

    def test_shared_original_n_and_dates_never_change(self):
        self.assertIs(self.p._resume_original.n, self.p._resume_native)
        self.assertIsNot(self.p.n, self.p._resume_native)
        self.assertEqual(self.p._resume_original.END.isoformat(), '2026-10-20T08:00:00+00:00')
        self.assertEqual(self.p._resume_native.END.isoformat(), '2026-10-20T08:00:00+00:00')
        self.assertEqual(self.p._resume_sft.END, d.END)

    def test_facade_is_frozen_and_numerical_helpers_are_original_objects(self):
        with self.assertRaises(AttributeError): self.p.n.TAG = d.NATIVE_TAG
        with self.assertRaises(AttributeError): self.p.n.arbitrary_loader = object()
        for name in ('validate_payload', 'validate_cpu_state', 'native_probe', 'route_receipt', 'modules'):
            self.assertIs(getattr(self.p.n, name), getattr(self.p._resume_native, name))

    def test_checkpoint_dispatch_and_forbidden_resume_native_train_phase(self):
        for arm in ('ternary', 'float'):
            self.assertEqual(self.p.n.checkpoint(arm, 'native'), self.p._resume_native.checkpoint(arm, 'native'))
            self.assertEqual(self.p.n.checkpoint(arm, 'sft'), self.p._resume_sft.checkpoint(arm, 'sft'))
        with self.assertRaises(ValueError): self.p._resume_sft.phase_key('train', 'float')
        with self.assertRaises(ValueError): self.p.n.checkpoint('float', 'foreign')

    def test_children_use_new_script_and_both_regressions(self):
        for mode, args in (('prepare', (None, None, None)), ('evaluate', ('ternary', 'float', 'sft'))):
            phases = self.p.phase_commands(mode, *args, 600)
            self.assertIn('scripts.test_p106b_route_cross_resume', phases[0][1])
            self.assertIn('scripts.test_p106b_route_cross_readout', phases[0][1])
            for _, command in phases[1:]:
                self.assertEqual(command.count(d.SCRIPT), 1)
                self.assertNotIn(d.SOURCE, command)

    def test_extended_authority_keeps_original_record_reserve(self):
        self.assertEqual(self.p.authority(d.END - timedelta(seconds=660)), 60.)
        self.assertGreater(self.p.authority(datetime(2026, 10, 20, 8, tzinfo=timezone.utc)), 0)
        for value in (d.END, d.END - timedelta(seconds=600), datetime(2026, 10, 21)):
            with self.assertRaises((ValueError, self.p.Pending)): self.p.authority(value)

    def test_unapproved_private_binding_is_detected(self):
        try:
            self.p.unapproved_loader = object()
            with self.assertRaises(ValueError): self.p._resume_assert_unchanged()
        finally: del self.p.unapproved_loader

    def test_compute_replacement_is_detected(self):
        before = self.p.cross_runtime
        try:
            self.p.cross_runtime = lambda *args: None
            with self.assertRaises(ValueError): self.p._resume_assert_unchanged()
        finally: self.p.cross_runtime = before

    def test_guard_detects_in_place_body_mutation_on_synthetic_module(self):
        module = types.ModuleType('_synthetic_guard_only')
        module.compute = lambda: 1
        guard = d.ModuleGuard(module)
        before = module.compute.__code__
        try:
            module.compute.__code__ = (lambda: 2).__code__
            with self.assertRaisesRegex(ValueError, '함수 본문'): guard.check()
        finally: module.compute.__code__ = before
        guard.check()

    def test_check_only_does_not_consume_any_actual_provider(self):
        with patch.object(d, 'build_runtime', return_value=self.p), \
                patch.object(d, 'source_state_for', side_effect=AssertionError('assets forbidden')), \
                redirect_stdout(io.StringIO()) as output:
            self.assertEqual(d.main(['--mode', 'source', '--check-only']), 0)
        self.assertEqual(json.loads(output.getvalue().split(' ', 1)[1])['tag'], d.TAG)


class ProviderTests(unittest.TestCase):
    def test_cross_lineage_names_actual_training_tag_separately_from_cases_source(self):
        with source_fixture() as f:
            for endpoint in ('native', 'sft'):
                report = f.reports[endpoint, 'float']
                lineage = f.p.cross_lineage(report, 'float', 'ternary', endpoint, f.cc)
                self.assertEqual(lineage['training_tag'], d.NATIVE_TAG if endpoint == 'native' else d.SFT_TAG)
                self.assertEqual(lineage['source_tag'], d.SFT_TAG)
                self.assertEqual(lineage['cases_provider_tag'], d.SFT_TAG)

    def test_source_uses_original_native_paths_and_new_sft_and_diagonal_paths(self):
        with source_fixture() as f:
            result = d.source_state_for(f.p, f.native, f.resume)
            binding = result[2]
            for arm in f.p.ROUTES:
                self.assertEqual(binding['endpoints']['native_' + arm]['training_tag'], d.NATIVE_TAG)
                self.assertIn(d.NATIVE_TAG, binding['endpoints']['native_' + arm]['training_report_path'])
                self.assertIn(d.SFT_TAG, binding['endpoints']['sft_' + arm]['training_report_path'])
                self.assertIn(d.SFT_TAG, binding['endpoints']['native_' + arm]['diagonal_report_path'])
            self.assertEqual(f.native.train_report.call_count, 2)
            self.assertEqual(f.resume.train_report.call_count, 2)
            self.assertEqual(binding['case_key_bridge']['original_value'], binding['case_key_bridge']['resume_value'])
            self.assertEqual(len(result[0]), 1694)
            self.assertEqual(f.p.prefix_case.call_count, 1694)

    def test_wrong_case_key_order_or_original_reference_hash_rejected(self):
        for kind in ('new_key', 'old_key', 'order', 'reference', 'tag'):
            with self.subTest(kind=kind), source_fixture() as f:
                if kind == 'new_key': f.reference['binding']['cases_sha256'] = 'F' * 64
                elif kind == 'old_key':
                    changed = deepcopy(f.original_ref); changed['binding']['source_cases_sha256'] = 'F' * 64
                    f.memory.files[f.native.CACHE / 'frozen_reference.json'] = json.dumps(changed).encode()
                elif kind == 'order': f.cc.reverse()
                elif kind == 'reference': f.reference['binding']['original_reference_sha256'] = 'F' * 64
                else: f.reference['tag'] = d.NATIVE_TAG
                with self.assertRaises(ValueError): d.source_state_for(f.p, f.native, f.resume)
                f.p.diagonal.assert_not_called()

    def test_training_header_wrong_endpoint_tag_core_date_parent_or_count_rejected(self):
        for key, value in (('tag', d.NATIVE_TAG), ('endpoint', 'native'), ('final_core_sha256', 'bad'),
                           ('authority_end_utc', '2026-10-20T08:00:00+00:00'), ('updates', 383),
                           ('initial_core_sha256', 'F' * 64), ('parent_checkpoint_sha256', None)):
            with self.subTest(key=key), source_fixture() as f:
                f.reports['sft', 'float'][key] = value
                with self.assertRaises(ValueError): d.source_state_for(f.p, f.native, f.resume)

    def test_sft_parent_must_be_same_arm_original_native_cp(self):
        with source_fixture() as f:
            wrong = f.reports['sft', 'float']; other = f.reports['native', 'ternary']
            wrong['parent_core_sha256'] = wrong['initial_core_sha256'] = other['final_core_sha256']
            wrong['parent_checkpoint_sha256'] = other['checkpoint_sha256']
            with self.assertRaisesRegex(ValueError, '같은 원 native'):
                d.source_state_for(f.p, f.native, f.resume)

    def test_missing_any_diagonal_is_pending_not_current_completion(self):
        with source_fixture() as f:
            f.p.diagonal.side_effect = f.p.Pending('four diagonals NOT_RUN')
            before = deepcopy(f.memory.files)
            with self.assertRaises(f.p.Pending): d.source_state_for(f.p, f.native, f.resume)
            self.assertEqual(f.memory.files, before)

    def test_facade_cp_experiment_uses_exact_training_tag_and_does_not_retag_report(self):
        with source_fixture() as f:
            facade = d.make_facade(f.native, f.resume)
            before = deepcopy(f.reports)
            for endpoint in ('native', 'sft'):
                report = f.reports[endpoint, 'float']
                result = facade.cp_experiment(report)
                self.assertEqual(result['tag'], d.NATIVE_TAG if endpoint == 'native' else d.SFT_TAG)
                self.assertEqual(result['core_sha256'], report['final_core_sha256'])
            self.assertEqual(f.reports, before)
            changed = deepcopy(f.reports['native', 'float']); changed['tag'] = d.SFT_TAG
            with self.assertRaises(ValueError): facade.cp_experiment(changed)

    def test_shared_scratch_core_and_all_six_user_cases_required(self):
        for kind in ('scratch', 'users'):
            with self.subTest(kind=kind), source_fixture() as f:
                if kind == 'scratch':
                    f.reports['sft', 'float']['scratch_core_sha256'] = 'F' * 64
                else:
                    f.cc[-1]['lane'] = 'fixture'
                    # source hash 계약도 새 합성 cases에 맞춘 뒤 USER_CASES 경계만 확인한다.
                    f.original_ref['binding']['source_cases_sha256'] = d.sha(f.cc)
                    path = f.native.CACHE / 'frozen_reference.json'
                    f.memory.files[path] = json.dumps(f.original_ref).encode()
                    f.reference['binding'].update(cases_sha256=d.sha(f.cc),
                        original_reference_sha256=f.memory.digest(path),
                        original_source_binding_sha256=d.sha(f.original_ref['binding']))
                with self.assertRaises(ValueError): d.source_state_for(f.p, f.native, f.resume)


class NumericBoundaryTests(unittest.TestCase):
    def runtime(self, trained, endpoint):
        p = d.build_runtime(); memory = Memory()
        native, resume, _ = providers(p, memory)
        facade = d.make_facade(native, resume)
        model, prior, saved, torch_facade, runtime = fixtures.RuntimeTests().fixture(trained, endpoint)
        provider = native if endpoint == 'native' else resume
        training = dict(provider.info())
        training.update(prior)
        training.update(status='TRAIN_COMPLETE', cost=False,
            checkpoint_writes=1, optimizer_saved=False, tag=provider.TAG,
            initial_core_sha256=prior['scratch_core_sha256'] if endpoint == 'native' else 'F' * 64,
            parent_core_sha256=None if endpoint == 'native' else 'F' * 64,
            parent_checkpoint_sha256=None if endpoint == 'native' else 'E' * 64)
        saved['experiment'] = facade.cp_experiment(training)
        native.modules = lambda: (runtime, None, route)
        # 새 facade만 재생성한다. 실제 원 native/modules를 patch하지 않는다.
        facade = d.make_facade(native, resume)
        env = dict(vars(p)); env.update(n=facade, digest=lambda _: training['checkpoint_sha256'])
        context = contextmanager(local(p.cross_runtime, env))
        return p, model, training, saved, torch_facade, runtime, context

    def test_both_endpoints_load_exact_training_tag_on_cpu_and_close_before_other_route(self):
        for endpoint in ('native', 'sft'):
            for trained, infer in (('ternary', 'float'), ('float', 'ternary')):
                with self.subTest(endpoint=endpoint, trained=trained):
                    p, model, training, saved, torch_facade, _, context = self.runtime(trained, endpoint)
                    with context(trained, infer, endpoint, training) as values:
                        self.assertIs(values[1], model)
                        self.assertEqual(values[4].mode, infer)
                        self.assertEqual(model.cuda_calls, ['CPU_ROUTE_CLOSED'])
                        self.assertEqual(core(model), training['final_core_sha256'])
                        self.assertTrue(values[5]['training_context_closed_before_cuda'])
                    self.assertIsNone(getattr(model, '_p106b_weight_route', None))
                    torch_facade.load.assert_called_once_with(p.n.checkpoint(trained, endpoint), map_location='cpu', weights_only=True)
                    self.assertEqual(saved['experiment']['tag'], d.NATIVE_TAG if endpoint == 'native' else d.SFT_TAG)

    def test_wrong_cp_experiment_tag_dtype_or_core_is_before_cuda(self):
        for kind in ('tag', 'dtype', 'core'):
            with self.subTest(kind=kind):
                _, model, training, saved, _, _, context = self.runtime('float', 'sft')
                if kind == 'tag': saved['experiment']['tag'] = d.NATIVE_TAG
                elif kind == 'dtype': saved['model']['a.weight'] = saved['model']['a.weight'].double()
                else: saved['experiment']['core_sha256'] = 'F' * 64
                with self.assertRaises(ValueError):
                    with context('float', 'ternary', 'sft', training): pass
                self.assertEqual(model.cuda_calls, [])

    def test_generic_float_guard_is_not_relaxed(self):
        _, _, _, saved, _, _, _ = self.runtime('float', 'sft')
        with self.assertRaises(RuntimeError): route.generic_loader_guard(saved)


class DiagonalTests(unittest.TestCase):
    def fixture(self, endpoint='native'):
        p = d.build_runtime(); memory = Memory()
        native, resume, reports = providers(p, memory)
        cc, tok, trained = cases(), Tokens(), 'float'
        training = reports[endpoint, trained]
        source = types.SimpleNamespace(classify_case=classify,
            recount=lambda rows, cases, tokenizer: dict(actual_answers=len(rows)))
        native.modules = lambda: (None, source, route)
        facade = d.make_facade(native, resume)
        key = resume.phase_key('evaluate', trained, endpoint)
        lineage = dict(tag=d.SFT_TAG, arm=trained, endpoint=endpoint,
            checkpoint_sha256=training['checkpoint_sha256'], core_sha256=training['final_core_sha256'],
            cases_sha256=d.sha(cc), quantization_route=route.route_metadata(trained))
        events = []
        writer = memory.writer(resume.RAW / key, 'answers', 19_999_999)
        mock_model = types.SimpleNamespace(training=False, parameters=lambda: [])
        for case in cc:
            answer, generation = emit(mock_model, None, tok, case['messages'])
            event = dict(id=case['id'], case_sha256=d.sha(case), answer=answer, generation=generation,
                metrics=classify(case, answer), arm=trained, endpoint=endpoint,
                checkpoint_sha256=training['checkpoint_sha256'], quantization_route=route.route_metadata(trained))
            events.append(event); writer.append(event)
        manifest = writer.close(lineage=lineage)
        receipt = dict(mode=trained, metadata=route.route_metadata(trained), tlinear_instances=1,
            owned_tlinear_instances=1, refreshed_tlinear_instances=1,
            forward_methods=['_guarded_forward'], refresh_methods=['_float_refresh'])
        report = dict(resume.info(), status='ACTUAL_ANSWERS_COLLECTED', arm=trained, endpoint=endpoint,
            actual_cases=2, checkpoint_sha256=training['checkpoint_sha256'],
            core_before=training['final_core_sha256'], core_after=training['final_core_sha256'],
            cases_sha256=d.sha(cc), lineage=lineage, raw_manifest=manifest,
            quantization_route=route.route_metadata(trained), route=receipt,
            native32_fp32=dict(ce=1., targets=32768, windows=32, precision='FP32_MATH', val_sha256=native.VAL_SHA))
        memory.write(resume.result_path(key), report)
        env = dict(vars(p)); env.update(n=facade, ANSWERS=2, required=memory.required,
            raw_bytes=memory.raw, digest=memory.digest)
        for name in ('read_answers', 'prefix_case', 'validate_event'):
            env[name] = local(getattr(p, name), env)
        diagonal = local(p.diagonal, env)
        return diagonal, native, resume, training, cc, tok, report, events, memory, key

    def test_new_diagonal_tag_is_resume_even_for_original_native_weights(self):
        for endpoint in ('native', 'sft'):
            with self.subTest(endpoint=endpoint):
                diagonal, _, resume, training, cc, tok, _, events, _, _ = self.fixture(endpoint)
                self.assertEqual(diagonal('float', endpoint, training, cc, tok)[1], events)
                resume.completed_activity.assert_called_once_with('evaluate', 'float', endpoint)

    def test_old_diagonal_tag_wrong_endpoint_core_or_code_not_promoted(self):
        for key, value in (('tag', d.NATIVE_TAG), ('endpoint', 'sft'), ('core_after', 'F' * 64),
                           ('authority_end_utc', '2026-10-20T08:00:00+00:00'), ('code_sha256', {})):
            with self.subTest(key=key):
                diagonal, _, resume, training, cc, tok, report, _, memory, phase = self.fixture()
                report[key] = value
                memory.files[resume.result_path(phase)] = json.dumps(report).encode()
                with self.assertRaises(ValueError): diagonal('float', 'native', training, cc, tok)

    def test_diagonal_partial_bytes_and_not_run_activity_rejected(self):
        diagonal, _, resume, training, cc, tok, _, _, memory, phase = self.fixture()
        memory.files[resume.RAW / phase / 'answers_000000.jsonl'] += b' '
        with self.assertRaises(ValueError): diagonal('float', 'native', training, cc, tok)
        resume.completed_activity.side_effect = old.Pending('diagonal NOT_RUN')
        with self.assertRaises(old.Pending): diagonal('float', 'native', training, cc, tok)


class RawAndWorkerTests(unittest.TestCase):
    def test_full_info_prepare_serialization_and_partial_hash_rejection(self):
        with raw_fixture() as (p, env, real):
            cc = [dict(id=str(i), lane='user_seen' if i >= 1688 else 'fixture') for i in range(1694)]
            state = (cc, {}, {'native_tag': d.NATIVE_TAG, 'sft_tag': d.SFT_TAG}, {}, None)
            env['source_state'] = lambda: state
            env['completed_activity'] = lambda *args: None
            prepare, prepared = local(real.prepare, env), local(real.prepared, env)
            self.assertEqual(prepare(), 0)
            self.assertEqual(prepared()[1], cc)
            frozen = p.required(p.CACHE / 'frozen_reference.json')
            self.assertGreater(len(frozen), 35)
            self.assertEqual(frozen['native_training_tag'], d.NATIVE_TAG)
            self.assertEqual(frozen['models_loaded'], 0)
            with self.assertRaises(FileExistsError): prepare()
            contract = p.required(p.EVIDENCE / 'cpu_contract.json'); contract['reference_sha256'] = 'F' * 64
            with (p.EVIDENCE / 'cpu_contract.json').open('w') as stream: json.dump(contract, stream)
            with self.assertRaises(ValueError): prepared()

    def test_closed_raw_manifest_bytes_order_and_missing_manifest_are_checked(self):
        with raw_fixture() as (p, _, _):
            from scripts.p106b_shards import ShardWriter
            target = p.RAW / 'fixture'
            writer = ShardWriter(target, 'answers', limit=19_999_999)
            for index in range(2): writer.append(dict(id=str(index)))
            manifest = writer.close(lineage=dict(tag=d.TAG))
            self.assertEqual([e['id'] for e in p.read_answers(target, manifest, 2)], ['0', '1'])
            changed = deepcopy(manifest); changed['shards'][0]['path'] = '../answers_000000.jsonl'
            with self.assertRaises(ValueError): p.read_answers(target, changed, 2)
            with (target / 'answers_000000.jsonl').open('ab') as stream: stream.write(b' ')
            with self.assertRaises(ValueError): p.read_answers(target, manifest, 2)
            with self.assertRaises(p.Pending): p.read_answers(p.RAW / 'other_namespace', manifest, 2)

    def test_original_worker_term_records130_and_restores_handler(self):
        with raw_fixture() as (p, env, real):
            original_handler = signal.getsignal(signal.SIGTERM)
            env['prepare'] = lambda: signal.raise_signal(signal.SIGTERM)
            worker = local(real._resume_captured['worker'], env)
            with patch.object(old.os, 'getpid', return_value=7), patch.object(old.os, 'getpgid', return_value=7):
                with self.assertRaises(KeyboardInterrupt): worker('prepare', None, None, None, 60)
            value = p.required(p.EVIDENCE / 'activity_prepare.json')
            self.assertEqual(value['returncode'], 130)
            self.assertFalse(value['complete'])
            self.assertIsNone(value['result_sha256'])
            self.assertIs(signal.getsignal(signal.SIGTERM), original_handler)

    def test_actual_family_wall_once_and_all_completed_hashes_checked(self):
        with raw_fixture() as (p, _, _):
            p.prepare(); value = completed_record(p)
            p.write(p.EVIDENCE / 'activity_prepare.json', value)
            self.assertEqual(d.spent_seconds_for(p), 10.)
            self.assertEqual(d.require_family_budget(p, 60), 10.)
            self.assertEqual(d.require_family_budget(p, 7200), 10.)
            damaged = deepcopy(value); damaged['result_sha256'] = 'F' * 64
            with (p.EVIDENCE / 'activity_prepare.json').open('w') as stream: json.dump(damaged, stream)
            with self.assertRaises(ValueError): d.spent_seconds_for(p)

    def test_family_cap600reserve_holds_before_work(self):
        with raw_fixture() as (p, _, _):
            p.prepare()
            value = completed_record(p, seconds=1500.)
            value['max_wall_sec'] = 1800
            p.write(p.EVIDENCE / 'activity_prepare.json', value)
            with self.assertRaises(p.Pending): d.require_family_budget(p, 7200)
            self.assertEqual(d.require_family_budget(p, 600), 1500.)

    def test_failed_partial_activity_counts_once_but_never_completes(self):
        with raw_fixture() as (p, _, _):
            p.prepare(); value = completed_record(p, complete=False)
            p.write(p.EVIDENCE / 'activity_prepare.json', value)
            self.assertEqual(d.spent_seconds_for(p), 10.)
            with self.assertRaises(p.Pending): p.completed_activity('prepare')
            with (p.result_path('prepare')).open('w') as stream: json.dump({'changed': True}, stream)
            with self.assertRaises(ValueError): d.spent_seconds_for(p)

    def test_wrong_activity_date_endpoint_tag_and_raw_reference_rejected(self):
        with raw_fixture() as (p, _, _):
            p.prepare(); value = completed_record(p)
            for key, changed in (('tag', d.ORIGINAL_TAG), ('endpoint', 'sft'), ('worker_pgid', 8),
                                 ('ended_at', (d.END + timedelta(seconds=1)).isoformat()),
                                 ('started_at', (d.END - timedelta(seconds=500)).isoformat())):
                bad = deepcopy(value); bad[key] = changed
                with self.subTest(key=key), self.assertRaises(ValueError): p.validate_activity(bad, 'prepare')


if __name__ == '__main__':
    unittest.main()
