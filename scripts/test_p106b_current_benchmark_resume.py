"""고정 공개 평가 재개의 코드·계보·작은 CPU/임시 원형 회귀. 실물 자산은 읽지 않는다."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
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
from scripts import diag_p106b_current_benchmark_resume as d
from scripts import diag_p106b_route_cross_resume as utility
from scripts import test_p106b_current_benchmark as fixtures
from scripts import p106b_weight_route as route
import torch


def local(function, env):
    source = inspect.unwrap(function)
    value = types.FunctionType(source.__code__, env, source.__name__, source.__defaults__, source.__closure__)
    value.__kwdefaults__ = source.__kwdefaults__
    return value


@contextmanager
def reference_fixture():
    """strict producer 호출은 합성 metadata로 대체한다. 원문/CP tensor는 없다."""
    real = d.build_runtime(); memory = fixtures.Memory()
    native = types.SimpleNamespace(**vars(real._resume_native))
    resume = types.SimpleNamespace(**vars(real._resume_sft))
    broad = types.SimpleNamespace(**vars(real._resume_broad))
    reports = {}
    for provider, actual, endpoint in ((native, real._resume_native, 'native'), (resume, real._resume_sft, 'sft')):
        meta = actual.info()
        provider.info = lambda meta=meta: deepcopy(meta)
        provider.modules = lambda: (None, None, route)
        provider.cp_experiment = local(real._resume_native.cp_experiment, {'TAG': provider.TAG})
        for arm, marker in (('ternary', 'B'), ('float', 'C')):
            checkpoint = provider.checkpoint(arm, endpoint)
            memory.files[checkpoint] = ('synthetic checkpoint marker ' + endpoint + arm).encode()
            parent = reports.get(('native', arm))
            report = dict(meta, status='TRAIN_COMPLETE', endpoint=endpoint, arm=arm,
                updates=2281 if endpoint == 'native' else 384, cost=False, optimizer_saved=False,
                checkpoint_writes=1, checkpoint_sha256=memory.digest(checkpoint),
                scratch_core_sha256='A' * 64, initial_core_sha256='A' * 64 if parent is None else parent['final_core_sha256'],
                final_core_sha256=marker * 64 if parent is None else 'D' * 64,
                parent_core_sha256=None if parent is None else parent['final_core_sha256'],
                parent_checkpoint_sha256=None if parent is None else parent['checkpoint_sha256'],
                reference_sha256='F' * 64, quantization_route=route.route_metadata(arm))
            reports[endpoint, arm] = report
            path = provider.result_path(provider.phase_key('train' if endpoint == 'native' else 'sft', arm))
            memory.write(path, report)
        def read(mode, arm, endpoint=endpoint):
            if mode != ('train' if endpoint == 'native' else 'sft'):
                raise AssertionError('native 학습 phase를 resume에서 찾으면 안 된다')
            return reports[endpoint, arm]
        provider.train_report = Mock(side_effect=read)
    broad_metadata = real._resume_broad.info()
    broad.info = lambda: deepcopy(broad_metadata)
    course = dict(updates=352, groups_per_pass=176, schedules={'fixture': True})
    borrowed_path = real.ROOT / 'data_cache/synthetic_original_broad/course.json'
    memory.write(borrowed_path, course)
    bundle = dict(course=types.SimpleNamespace(report=course),
        contract=dict(course_report_sha256=memory.digest(borrowed_path)))
    bridge = dict(broad_metadata, status='BROAD_RESUME_BRIDGE_PREPARED', binding=dict(
        parent=dict(path=broad_metadata['parent'], sha256=d.PARENT_SHA, core_sha256=d.PARENT_CORE),
        files=dict(course=dict(path=str(borrowed_path.relative_to(real.ROOT)), sha256=memory.digest(borrowed_path)))))
    memory.write(broad.CACHE / 'frozen.json', bridge)
    broad.prepared = Mock(return_value=bundle)
    broad.required, broad.digest = memory.read, memory.digest
    broad.completed_activity = Mock()
    for arm in ('mixed', 'staged'):
        checkpoint = broad.checkpoint(arm)
        memory.files[checkpoint] = ('synthetic broad checkpoint marker ' + arm).encode()
        report = dict(broad_metadata, initial_core_sha256=d.PARENT_CORE, actual_updates=352,
            final_core_sha256='E' * 64, checkpoint_sha256=memory.digest(checkpoint))
        reports['broad', arm] = report
        memory.write(broad.EVIDENCE / ('train_' + arm) / 'report.json', report)
    def read_broad(arm, *, cost, bundle):
        if cost or bundle is not broad.prepared.return_value: raise AssertionError('actual prepared bundle이 필요하다')
        return reports['broad', arm]
    broad.read_training = Mock(side_effect=read_broad)
    p = types.SimpleNamespace(**vars(real))
    p.digest = lambda path: d.PARENT_SHA if path == broad.monitor.base.PARENT else memory.digest(path)
    p.model_reference = lambda model_id: d.model_reference_for(p, native, resume, broad, utility, model_id)
    yield types.SimpleNamespace(p=p, real=real, native=native, resume=resume, broad=broad,
        reports=reports, memory=memory, bundle=bundle, bridge=bridge, borrowed=borrowed_path)


@contextmanager
def raw_fixture():
    real = d.build_runtime()
    with tempfile.TemporaryDirectory(prefix='benchmark-resume-') as temporary:
        root = Path(temporary); env = dict(vars(real))
        env.update(ROOT=root, CACHE=root / 'cache', RAW=root / 'raw', EVIDENCE=root / 'evidence',
            info=lambda: real.info(), authority=lambda: 100000.)
        p = types.SimpleNamespace(**env)
        for name in ('safe', 'exists', 'digest', 'raw_bytes', 'required', 'write', 'phase_key', 'result_path',
                     'validate_activity', 'completed_activity', 'spent_seconds', 'remaining_activity', 'worker', 'launch_phase'):
            setattr(p, name, local(getattr(real, name), env))
        env.update(vars(p))
        def prepare():
            p.write(p.CACHE / 'frozen_reference.json', {'fixture': True})
            p.write(p.result_path('prepare'), {'fixture': True})
            return 0
        env['prepare'] = prepare; p.prepare = prepare
        yield p, env, real


def activity(p, seconds=3., complete=True):
    start = d.END - timedelta(hours=2)
    return dict(schema=p.SCHEMA, tag=p.TAG, key='prepare', mode='prepare', model_id=None,
        seconds=seconds, max_wall_sec=60, returncode=0 if complete else 130,
        complete=complete, error_type=None if complete else 'KeyboardInterrupt', worker_pid=7, worker_pgid=7,
        code_sha256=p.info()['code_sha256'], started_at=start.isoformat(),
        ended_at=(start + timedelta(seconds=seconds)).isoformat(), result_sha256=p.digest(p.result_path('prepare')),
        reference_sha256=p.digest(p.CACHE / 'frozen_reference.json'))


class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.p = d.build_runtime()
    def tearDown(self): self.p._resume_assert_unchanged()

    def test_pins_verified_before_any_original_import(self):
        with patch.object(d, 'checked_sources', side_effect=ValueError('pin')), patch.object(d.importlib, 'import_module') as load:
            with self.assertRaises(ValueError): d.build_runtime()
        load.assert_not_called()

    def test_all_six_source_pins_match(self):
        self.assertEqual(set(d.checked_sources()), set(d.SOURCE_PINS))

    def test_info_preserves_six_models_scoring_denominators_and_activity_limits(self):
        now, old = self.p.info(), self.p._resume_original.info()
        for key in old:
            if key not in ('schema', 'tag', 'code_sha256', 'code_complete', 'authority_end_utc'):
                self.assertEqual(now[key], old[key], key)
        self.assertEqual(now['models'], list(self.p.MODELS))
        self.assertEqual((now['requested_rows'], now['expected_scored_rows']), (9216, 9212))
        self.assertEqual((now['active_limit_seconds'], now['record_reserve_seconds']), (3600, 600))
        self.assertEqual(now['mc_primary'], 'ARGMIN_SUM_NLL')
        self.assertEqual(now['new_falcon_calls'], 0)
        self.assertTrue(now['code_complete'])

    def test_all_original_numerical_source_worker_accounting_bodies_match(self):
        for name in d.BODY_NAMES:
            self.assertEqual(utility.body_sha(getattr(self.p, name)), utility.body_sha(getattr(self.p._resume_original, name)), name)
            self.assertIs(inspect.unwrap(getattr(self.p, name)).__globals__, vars(self.p))
        for name in ('__init__', '__getattr__', '__call__'):
            self.assertEqual(utility.body_sha(getattr(self.p.FP32Forward, name)),
                utility.body_sha(getattr(self.p._resume_original.FP32Forward, name)))

    def test_shared_recovery_scope_is_absent_from_private_tag_facade(self):
        self.assertFalse(hasattr(self.p.recovery, 'runtime_scope'))
        self.assertEqual(self.p.recovery.TAG, d.BROAD_TAG)
        self.assertEqual(self.p._resume_original.recovery.TAG, 'p106b_broad_curriculum_v2_s1337')
        self.assertIs(self.p.n, self.p._resume_sft)

    def test_fixed_public_falcon_hashes_and_original_dates_unchanged(self):
        self.assertEqual(self.p.FIXED, self.p._resume_original.FIXED)
        self.assertEqual(self.p._resume_original.END.isoformat(), '2026-10-20T08:00:00+00:00')
        self.assertEqual(self.p.END, d.END)
        self.assertEqual(self.p.authority(d.END - timedelta(seconds=660)), 60.)
        with self.assertRaises(self.p.Pending): self.p.authority(d.END - timedelta(seconds=600))

    def test_fixed_dictionary_in_place_change_is_rejected(self):
        key = next(iter(self.p.FIXED)); before = self.p.FIXED[key]
        try:
            self.p.FIXED[key] = 'F' * 64
            with self.assertRaises(ValueError): self.p._resume_assert_unchanged()
        finally: self.p.FIXED[key] = before

    def test_unapproved_loader_binding_is_rejected(self):
        try:
            self.p.arbitrary_checkpoint_loader = object()
            with self.assertRaises(ValueError): self.p._resume_assert_unchanged()
        finally: del self.p.arbitrary_checkpoint_loader

    def test_all_children_use_new_controller_and_regression(self):
        for mode, model in (('prepare', None), ('evaluate', 'broad_mixed'), ('readback', None)):
            phases = self.p.phase_commands(mode, model, 600)
            self.assertIn('scripts.test_p106b_current_benchmark_resume', phases[0][1])
            for _, command in phases[1:]:
                self.assertEqual(command.count(d.SCRIPT), 1)
                self.assertNotIn(d.SOURCE, command)

    def test_check_only_never_calls_asset_info_or_source_provider(self):
        with patch.object(d, 'build_runtime', return_value=self.p), \
                patch.object(d, 'model_reference_for', side_effect=AssertionError('asset forbidden')), \
                redirect_stdout(io.StringIO()) as output:
            self.assertEqual(d.main(['--mode', 'prepare', '--check-only']), 0)
        self.assertEqual(json.loads(output.getvalue().split(' ', 1)[1])['tag'], d.TAG)

    def test_unadmitted_or_generic_model_is_rejected_before_load(self):
        with self.assertRaises(ValueError):
            with self.p.model_runtime('sft_float', dict(model_id='native_float')): pass

    def test_process_local_admission_refuses_unverified_or_changed_core_before_loader(self):
        with reference_fixture() as f:
            spec = f.p.model_reference('native_float')
            with patch.object(d, 'load_model_for') as load:
                with self.assertRaisesRegex(ValueError, '먼저 검산'):
                    with f.real.model_runtime('native_float', spec): pass
            load.assert_not_called()
            with patch.object(d, 'model_reference_for', return_value=deepcopy(spec)):
                admitted = f.real.model_reference('native_float')
            admitted['core_sha256'] = 'F' * 64
            with patch.object(d, 'load_model_for') as load:
                with self.assertRaisesRegex(ValueError, '동일 참조'):
                    with f.real.model_runtime('native_float', admitted): pass
            load.assert_not_called()


class ReferenceTests(unittest.TestCase):
    def test_all_six_refs_have_endpoint_specific_tag_path_and_exact_broad_parent(self):
        with reference_fixture() as f:
            values = {name: f.p.model_reference(name) for name in f.p.MODELS}
            self.assertEqual(len(values), 6)
            self.assertEqual(values['native_float']['trained_tag'], d.NATIVE_TAG)
            self.assertEqual(values['sft_float']['trained_tag'], d.SFT_TAG)
            self.assertEqual(values['broad_mixed']['trained_tag'], d.BROAD_TAG)
            self.assertEqual(values['broad_mixed']['parent_core_sha256'], d.PARENT_CORE)
            self.assertEqual(values['broad_mixed']['course_report_path'], str(f.borrowed.relative_to(f.p.ROOT)))
            self.assertNotIn(f.broad.CACHE / 'course.json', f.memory.files)
            self.assertIs(f.broad.read_training.call_args.kwargs['bundle'], f.bundle)

    def test_missing_broad_never_becomes_four_model_success(self):
        with reference_fixture() as f:
            f.broad.prepared.side_effect = f.p.Pending('Broad NOT_RUN')
            env = dict(vars(f.p))
            env.update(model_reference=f.p.model_reference, tokenizer=lambda: None,
                read_public=lambda _: ({'manifest': {}}, [], {}), cached_falcon=lambda _: ({}, []))
            source = local(f.real.source_state, env)
            with self.assertRaises(f.p.Pending): source()

    def test_wrong_native_sft_tag_core_route_date_and_cp_hash_rejected(self):
        for key, value in (('tag', d.NATIVE_TAG), ('final_core_sha256', 'bad'),
                           ('authority_end_utc', '2026-10-20T08:00:00+00:00'), ('checkpoint_sha256', 'F' * 64)):
            with self.subTest(key=key), reference_fixture() as f:
                f.reports['sft', 'float'][key] = value
                with self.assertRaises(ValueError): f.p.model_reference('sft_float')

    def test_wrong_broad_bridge_parent_course_or_update_count_rejected(self):
        for kind in ('parent', 'course', 'updates', 'tag'):
            with self.subTest(kind=kind), reference_fixture() as f:
                if kind == 'parent': f.bridge['binding']['parent']['core_sha256'] = 'F' * 64
                elif kind == 'course': f.bundle['contract']['course_report_sha256'] = 'F' * 64
                elif kind == 'updates': f.reports['broad', 'mixed']['actual_updates'] = 351
                else: f.bridge['tag'] = 'p106b_broad_curriculum_v2_s1337'
                f.memory.files[f.broad.CACHE / 'frozen.json'] = json.dumps(f.bridge).encode()
                with self.assertRaises(ValueError): f.p.model_reference('broad_mixed')

    def test_wrong_reference_model_parent_route_and_old_tag_are_rejected(self):
        with reference_fixture() as f:
            broad = f.p.model_reference('broad_mixed'); native = f.p.model_reference('native_float')
            for original, model_id, key, value in (
                    (broad, 'broad_mixed', 'trained_tag', 'p106b_broad_curriculum_v2_s1337'),
                    (broad, 'broad_mixed', 'parent_core_sha256', 'F' * 64),
                    (broad, 'broad_mixed', 'route', {'mode': 'float'}),
                    (native, 'native_float', 'trained_tag', d.SFT_TAG),
                    (native, 'native_float', 'route', route.route_metadata('ternary')),
                    (native, 'native_float', 'model_id', 'sft_float')):
                bad = deepcopy(original); bad[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    d.validate_spec(f.p, f.native, f.resume, f.broad, model_id, bad)

    def test_full_info_prepare_roundtrip_preserves_six_nested_provenances(self):
        with reference_fixture() as f:
            rows = fixtures.all_rows()
            models = {name: f.p.model_reference(name) for name in f.p.MODELS}
            binding = dict(models=models, exclusions={f.p.row_id(row): f.p.eligibility(row, fixtures.Tokens()) for row in rows})
            env = dict(vars(f.p))
            env.update(source_state=lambda: (binding, rows, fixtures.Tokens(), []),
                exists=f.memory.exists, write=f.memory.write, required=f.memory.read,
                digest=f.memory.digest, completed_activity=lambda *args: None)
            prepare, prepared = local(f.real.prepare, env), local(f.real.prepared, env)
            with redirect_stdout(io.StringIO()): self.assertEqual(prepare(), 0)
            reference = prepared()[0]
            self.assertEqual(reference['binding']['models'], models)
            self.assertEqual(reference['models_loaded'], 0)
            with self.assertRaises(FileExistsError): prepare()
            changed = deepcopy(reference); changed['binding']['models']['broad_mixed']['trained_tag'] = d.SFT_TAG
            f.memory.files[f.p.CACHE / 'frozen_reference.json'] = json.dumps(changed).encode()
            with self.assertRaises(ValueError): prepared()


class LoaderTests(unittest.TestCase):
    def test_broad_parent_child_strict_load_and_core_are_before_mock_cuda(self):
        from scripts.diag_p101a_sft_mtp import state_fingerprint
        with reference_fixture() as f:
            class Tiny(torch.nn.Linear):
                def clear_quant(self): self.cleared = True
                def freeze_quant(self): self.frozen = True
                def cuda(self):
                    if state_fingerprint(self) != expected_core:
                        raise AssertionError('CPU child strict load 뒤에만 CUDA로 이동한다')
                    self.moved = True
                    return self
            model, cfg = Tiny(2, 2, bias=False), fixtures.Cfg()
            original_state = deepcopy(model.state_dict())
            child_state = {key: value + .07 for key, value in original_state.items()}
            model.load_state_dict(child_state); expected_core = state_fingerprint(model)
            model.load_state_dict(original_state)
            saved = dict(model=child_state, cfg=asdict(cfg), step=352,
                tokenizer_sha256=f.p.public.TOKENIZER_SHA,
                broad_curriculum=dict(tag=d.BROAD_TAG, arm='mixed', passes=2, objective='token'))
            facade = types.SimpleNamespace(load=Mock(return_value=saved), Tensor=torch.Tensor, equal=torch.equal,
                backends=types.SimpleNamespace(cuda=types.SimpleNamespace(matmul=types.SimpleNamespace(allow_tf32=True)),
                    cudnn=types.SimpleNamespace(allow_tf32=True)), cuda=types.SimpleNamespace(empty_cache=Mock()))
            parent = f.broad.monitor.base.PARENT
            loader = Mock(return_value=(facade, model, cfg, fixtures.Tokens(), d.PARENT_CORE))
            f.broad.monitor = types.SimpleNamespace(base=types.SimpleNamespace(load_parent=loader, PARENT=parent))
            f.reports['broad', 'mixed']['final_core_sha256'] = expected_core
            spec = f.p.model_reference('broad_mixed')
            with d.load_model_for(f.p, f.native, f.resume, f.broad, 'broad_mixed', spec) as value:
                self.assertIs(value[1], model)
                self.assertIsNone(value[4])
                self.assertTrue(model.moved)
                self.assertFalse(model.training)
            facade.load.assert_called_once_with(f.p.ROOT / spec['checkpoint'], map_location='cpu', weights_only=True)
            self.assertTrue(model.cleared)
            loader.return_value = (facade, model, cfg, fixtures.Tokens(), 'F' * 64)
            facade.load.reset_mock()
            with self.assertRaisesRegex(ValueError, '원 P090B'):
                with d.load_model_for(f.p, f.native, f.resume, f.broad, 'broad_mixed', spec): pass
            facade.load.assert_not_called()

    def test_new_broad_payload_preserves_exact_cfg_dtype_alias_and_no_quantization_route(self):
        p = d.build_runtime()
        class Alias(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.a = torch.nn.Linear(2, 2, bias=False); self.alias = self.a
        model, cfg = Alias(), fixtures.Cfg()
        saved = dict(model=deepcopy(model.state_dict()), cfg=asdict(cfg), step=352,
            tokenizer_sha256=p.public.TOKENIZER_SHA,
            broad_curriculum=dict(tag=d.BROAD_TAG, arm='mixed', passes=2, objective='token'))
        p.validate_broad_payload(saved, model, cfg, 'mixed', torch)
        for kind in ('old_tag', 'dtype', 'alias', 'route', 'step'):
            bad = deepcopy(saved)
            if kind == 'old_tag': bad['broad_curriculum']['tag'] = 'p106b_broad_curriculum_v2_s1337'
            elif kind == 'dtype': bad['model']['a.weight'] = bad['model']['a.weight'].double()
            elif kind == 'alias': bad['model']['alias.weight'] = bad['model']['alias.weight'] + 1
            elif kind == 'route': bad['quantization_route'] = route.route_metadata('float')
            else: bad['step'] = 351
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                p.validate_broad_payload(bad, model, cfg, 'mixed', torch)

    def test_native_and_sft_use_different_strict_provider_contexts(self):
        from scripts.diag_p101a_sft_mtp import state_fingerprint
        with reference_fixture() as f:
            class Tiny(torch.nn.Linear):
                def set_anneal(self, value): self.anneal = value
                def freeze_quant(self): self.frozen = True
            for endpoint in ('native', 'sft'):
                model = Tiny(2, 2); provider = f.native if endpoint == 'native' else f.resume
                report = f.reports[endpoint, 'float']; report['final_core_sha256'] = state_fingerprint(model)
                spec = f.p.model_reference(endpoint + '_float')
                handle = types.SimpleNamespace(assert_active=Mock())
                calls = []
                @contextmanager
                def load(arm, ep):
                    calls.append((arm, ep)); yield torch, model, fixtures.Cfg(), fixtures.Tokens(), 'scratch', handle
                provider.routed_runtime = load
                with d.load_model_for(f.p, f.native, f.resume, f.broad, endpoint + '_float', spec) as value:
                    self.assertIs(value[1], model)
                    self.assertFalse(model.training)
                    self.assertTrue(all(parameter.requires_grad for parameter in model.parameters()))
                self.assertEqual(calls, [('float', endpoint)])


class AccountingTests(unittest.TestCase):
    def test_new_read_model_rejects_old_report_or_raw_lineage_before_raw_consumer(self):
        with reference_fixture() as f:
            model_id = 'sft_float'; spec = f.p.model_reference(model_id)
            f.memory.write(f.p.CACHE / 'frozen_reference.json', {'fixture': True})
            cfg = asdict(fixtures.Cfg())
            lineage = dict(tag=d.TAG, model_id=model_id, checkpoint_sha256=spec['checkpoint_sha256'],
                core_sha256=spec['core_sha256'], route=spec['route'], cfg_sha256=d.sha(cfg),
                reference_sha256=f.memory.digest(f.p.CACHE / 'frozen_reference.json'))
            report = dict(f.p.info(), status='CURRENT_PUBLIC_MODEL_COMPLETE', model_id=model_id,
                lineage=lineage, core_before=spec['core_sha256'], core_after=spec['core_sha256'],
                requires_grad_unchanged=True, model_exceptions=0, cfg=cfg, cfg_sha256=d.sha(cfg),
                tokenizer_sha256=f.p.public.TOKENIZER_SHA, checkpoint_sha256=spec['checkpoint_sha256'],
                raw_manifest=dict(lineage=lineage))
            target = f.p.result_path(f.p.phase_key('evaluate', model_id))
            env = dict(vars(f.p)); raw = Mock(side_effect=AssertionError('손상 뒤에는 raw를 읽지 않는다'))
            env.update(completed_activity=lambda *args: None, required=f.memory.read,
                digest=f.memory.digest, read_shards=raw)
            reader = local(f.real.read_model, env)
            reference = dict(binding=dict(models={model_id: spec}))
            for kind in ('old_tag', 'old_raw', 'core', 'model'):
                bad = deepcopy(report)
                if kind == 'old_tag': bad['tag'] = 'p106b_current_benchmark_v1_s1337'
                elif kind == 'old_raw': bad['raw_manifest']['lineage']['tag'] = 'p106b_current_benchmark_v1_s1337'
                elif kind == 'core': bad['core_after'] = 'F' * 64
                else: bad['model_id'] = 'native_float'
                f.memory.files[target] = json.dumps(bad).encode()
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    reader(model_id, reference, [fixtures.row()], fixtures.Tokens())
            raw.assert_not_called()

    def test_aux_worker_dedup_and_direct_failed_worker_accounting_unchanged(self):
        with raw_fixture() as (p, _, _):
            p.prepare(); worker = activity(p, complete=False)
            path = p.EVIDENCE / 'activity_prepare.json'; p.write(path, worker)
            self.assertEqual(p.spent_seconds(), 3.)
            p.write(p.EVIDENCE / 'aux_one.json', dict(tag=p.TAG, code_sha256=p.info()['code_sha256'],
                command_sha256='C' * 64, seconds=5., returncode=130,
                new_worker_key='prepare', new_worker_sha256=p.digest(path)))
            self.assertEqual(p.spent_seconds(), 5.)
            p.write(p.EVIDENCE / 'aux_preflight.json', dict(tag=p.TAG, code_sha256=p.info()['code_sha256'],
                command_sha256='D' * 64, seconds=2., returncode=8, new_worker_key=None, new_worker_sha256=None))
            self.assertEqual(p.spent_seconds(), 7.)

    def test_partial_aux_hash_or_duplicate_worker_link_is_rejected(self):
        with raw_fixture() as (p, _, _):
            p.prepare(); path = p.EVIDENCE / 'activity_prepare.json'; p.write(path, activity(p))
            aux = dict(tag=p.TAG, code_sha256=p.info()['code_sha256'], command_sha256='C' * 64,
                seconds=5., returncode=0, new_worker_key='prepare', new_worker_sha256='F' * 64)
            p.write(p.EVIDENCE / 'aux_one.json', aux)
            with self.assertRaises(ValueError): p.spent_seconds()
            aux['new_worker_sha256'] = p.digest(path)
            with (p.EVIDENCE / 'aux_one.json').open('w') as stream: json.dump(aux, stream)
            p.write(p.EVIDENCE / 'aux_two.json', aux)
            with self.assertRaises(ValueError): p.spent_seconds()

    def test_activity_old_tag_wrong_model_date_or_reference_cannot_complete(self):
        with raw_fixture() as (p, _, _):
            p.prepare(); value = activity(p)
            for key, replacement in (('tag', 'p106b_current_benchmark_v1_s1337'), ('model_id', 'sft_float'),
                                     ('ended_at', (d.END + timedelta(seconds=1)).isoformat()), ('worker_pgid', 8)):
                bad = deepcopy(value); bad[key] = replacement
                with self.subTest(key=key), self.assertRaises(ValueError): p.validate_activity(bad, 'prepare')
            value['result_sha256'] = 'F' * 64
            p.write(p.EVIDENCE / 'activity_prepare.json', value)
            with self.assertRaises(ValueError): p.completed_activity('prepare')

    def test_total_stage3600_and_record600_are_separate_bounds(self):
        with raw_fixture() as (p, env, _):
            env['spent_seconds'] = lambda: 3599.
            self.assertEqual(p.remaining_activity(), 1.)
            env['spent_seconds'] = lambda: 3600.
            with self.assertRaises(p.Pending): p.remaining_activity()

    def test_original_worker_term_records130_without_success_or_report(self):
        with raw_fixture() as (p, env, _):
            before = signal.getsignal(signal.SIGTERM)
            env['prepare'] = lambda: signal.raise_signal(signal.SIGTERM)
            with patch.object(p.os, 'getpid', return_value=7), patch.object(p.os, 'getpgid', return_value=7):
                with self.assertRaises(KeyboardInterrupt): p.worker('prepare', None, 60)
            result = p.required(p.EVIDENCE / 'activity_prepare.json')
            self.assertEqual(result['returncode'], 130)
            self.assertFalse(result['complete'])
            self.assertIsNone(result['result_sha256'])
            self.assertIs(signal.getsignal(signal.SIGTERM), before)


if __name__ == '__main__':
    unittest.main()
