"""코드/메타데이터와 임시 합성 wire만 검산한다. 실물 자료/CP/모델/GPU는 읽지 않는다."""
from __future__ import annotations

from contextlib import contextmanager, ExitStack, redirect_stdout, redirect_stderr
import copy
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
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_broad_resume as d


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False)


class Tokens:
    def encode(self, text):
        return types.SimpleNamespace(ids=list(text.encode()))


def conversation(index, language='ko'):
    return dict(messages=[dict(role='user', content=f'fixture {index}?'),
        dict(role='assistant', content=f'fixture answer {index}')],
        meta=dict(language=language, source='synthetic', source_id=index))


def cloned(module):
    value = types.ModuleType('_fixture_original_' + module.__name__)
    value.__dict__.update(vars(module))
    return value


@contextmanager
def fixture():
    """정확한 계산 bytecode를 보존하되 원 자산 reader만 합성 producer로 대체한다.

    이 내부 factory fixture는 CLI를 거치지 않는다. 22528개는 payload 소비를
    주장하는 표본이 아니라 geometry 검산용 None 참조이며 wire는 짧은 JSON이다.
    """
    real = d.build_runtime()
    original, old_recovery = real._resume_originals
    baseline, recovered = original.info(), old_recovery.info()
    sources = d.checked_sources()
    with tempfile.TemporaryDirectory(prefix='broad-resume-') as temporary, ExitStack() as stack:
        root = Path(temporary)
        old_cache = root / 'data_cache' / d.ORIGINAL_TAG
        old_evidence = root / 'test_result/evidence' / d.ORIGINAL_TAG
        old_raw = root / 'runs/eval' / d.ORIGINAL_TAG
        manifest = {stem: dict(rows=count, concat_sha256=d.sha(stem), shards=[],
            lineage=dict(tag=d.ORIGINAL_TAG, stem=stem)) for stem, count in
            (('train', 22528), ('dev', 2), ('monitor', 1694), ('dialogues', 16))}
        course = dict(groups_per_pass=176, updates=352, ordered_record_hashes_sha256='A' * 64,
            schedules_sha256='B' * 64, per_pass=dict(totals=dict(x_tokens=22528, assistant_targets=22528)),
            two_pass_totals=dict(x_tokens=45056, assistant_targets=45056))
        put(old_cache / 'course.json', course)
        frozen = dict(recovered, manifests=manifest, source_pins={},
            course_report_sha256=d.file_sha(old_cache / 'course.json'),
            native_train_offsets=list(range(2816)), dev_rows=2, dev_targets=3,
            dialogue_source_turns=17, monitor_cases_sha256='C' * 64, dialogue_cases_sha256='D' * 64,
            dialogue_selection=dict(source_indices=list(range(16))), monitor_display_ids=['c0'],
            monitor_display_selection_sha256=d.sha(['c0']), source_admission=dict(status='ADMISSIBLE'),
            expected_parent_core=d.PARENT_CORE)
        put(old_cache / 'frozen.json', frozen)
        put(old_evidence / 'cpu_contract.json', dict(frozen_sha256=d.file_sha(old_cache / 'frozen.json')))
        receipt = dict(status='SYNTHETIC_EQUIVALENCE_NOT_ACTUAL_DATA', payload_sha256=d.sha(manifest))
        put(old_evidence / 'v1_payload_equivalence.json', receipt)
        stamp = '2026-10-19T13:23:47+00:00'
        put(old_evidence / 'activity_recovery_equivalence.json', dict(schema=old_recovery.RECOVERY_SCHEMA,
            tag=d.ORIGINAL_TAG, key='recovery_equivalence', complete=True, returncode=0,
            code_sha256=recovered['code_sha256'], seconds=7., max_wall_sec=600, recorded_at=stamp))
        put(old_evidence / 'activity_prepare.json', dict(schema=baseline['schema'], tag=d.ORIGINAL_TAG,
            key='prepare', mode='prepare', arm=None, complete=True, returncode=0,
            code_sha256=recovered['code_sha256'], seconds=13., max_wall_sec=600, recorded_at=stamp,
            scope=d.WORKER_SCOPE, report_path=str((old_cache / 'frozen.json').relative_to(root)),
            report_sha256=d.file_sha(old_cache / 'frozen.json')))
        bundle = dict(contract=frozen, course=types.SimpleNamespace(report=course, records=[None] * 22528),
            monitor=[None] * 1694, dialogues=[None] * 16, dev=[None] * 2)
        calls, hooks = [], {}
        def synthetic_prepared(*, completed=True):
            calls.append('prepared')
            if hooks.get('prepared'):
                hooks['prepared']()
            return bundle
        def equivalent():
            calls.append('equivalence')
            if hooks.get('equivalence'):
                hooks['equivalence']()
            if json.loads((old_evidence / 'v1_payload_equivalence.json').read_text()) != receipt:
                raise ValueError('합성 원 receipt 손상')
            return copy.deepcopy(receipt)
        origin, origin_recovery = cloned(original), cloned(old_recovery)
        origin.info = lambda: copy.deepcopy(baseline)
        origin_recovery.info = lambda: copy.deepcopy(recovered)
        origin_recovery.validate_equivalence = equivalent
        def private(relative, data):
            module = types.ModuleType('_fixture_private_' + relative.replace('/', '_'))
            module.__file__ = str(ROOT / relative)
            exec(compile(data, str(ROOT / relative), 'exec', dont_inherit=True), vars(module))
            module.ROOT, module.safe, module.digest = root, lambda p: Path(p), d.file_sha
            def local(function):
                value = types.FunctionType(function.__code__, vars(module), function.__name__,
                    function.__defaults__, function.__closure__)
                value.__kwdefaults__ = function.__kwdefaults__
                return value
            if relative == d.LEGACY:
                module.info = local(lambda: copy.deepcopy(baseline))
                module.prepared = local(synthetic_prepared)
            else:
                module.CACHE, module.EVIDENCE, module.RAW = old_cache, old_evidence, old_raw
                module.info = local(lambda: copy.deepcopy(recovered))
                module.validate_equivalence = local(equivalent)
            module.copy = copy
            return module
        f4 = root / 'f4.json'; put(f4, dict(scope='synthetic fixture only'))
        stack.enter_context(patch.multiple(d, ROOT=root, F4=f4))
        stack.enter_context(patch.object(d, '_private_module', side_effect=private))
        p = d._build_runtime(origin, origin_recovery, sources)
        yield types.SimpleNamespace(p=p, root=root, bundle=bundle, calls=calls, hooks=hooks,
            old_cache=old_cache, old_evidence=old_evidence, origins=(origin, origin_recovery))


def activity(module, mode='readback', arm=None, *, complete=True, seconds=3.):
    key = module.activity_key(mode, arm)
    now = datetime.now(timezone.utc).isoformat()
    return dict(schema=module.SCHEMA, tag=module.TAG, key=key, mode=mode, arm=arm,
        code_sha256=module.info()['code_sha256'], seconds=seconds, complete=complete,
        returncode=0 if complete else 130, max_wall_sec=600, recorded_at=now, started_at=now,
        ended_at=now, pid=3, pgid=3, error_type=None if complete else 'KeyboardInterrupt',
        scope=d.WORKER_SCOPE, **module.completion_binding(mode, arm, required_report=complete))


@contextmanager
def owned_worker_fixture():
    """실제 worker/finally/writer만 임시 파일로 실행한다. 모델 함수는 없다."""
    from scripts import diag_p106b_broad_curriculum as old
    with tempfile.TemporaryDirectory(prefix='broad-worker-') as temporary:
        root = Path(temporary)
        env = dict(vars(old))
        env.update(ROOT=root, TAG=d.TAG, SCHEMA=d.SCHEMA, CACHE=root / 'cache', RAW=root / 'raw',
            EVIDENCE=root / 'evidence', END=d.END, TRAIN_STOP=d.TRAIN_STOP, safe=lambda p: Path(p),
            digest=d.file_sha)
        p = types.SimpleNamespace(**env)
        p.info = lambda: dict(code_sha256={'fixture': 'A' * 64})
        for name in ('required', 'write', 'activity_key', 'completion_report_path', 'completion_binding', 'authority'):
            value = getattr(old, name)
            setattr(p, name, types.FunctionType(value.__code__, env, name, value.__defaults__))
        p.authority = lambda training=False: 100000.
        p.phase_commands = lambda mode, arm, cap: old.phase_commands(mode, arm, cap)
        p.spent_seconds = lambda: 0.
        p.prepare = lambda: p.write(p.CACHE / 'frozen.json', dict(fixture=True)) or 0
        p.readback = lambda: p.write(p.EVIDENCE / 'readback.json', dict(fixture=True)) or 0
        p.source_pins = lambda: {'synthetic': True}
        p.prepared = lambda: {'synthetic': True}
        p.budget = lambda: dict(admission=True)
        # keyword-only default가 있는 completion_binding을 복원한다.
        p.completion_binding.__kwdefaults__ = old.completion_binding.__kwdefaults__
        env.update(vars(p))
        with patch.object(d.os, 'getpid', return_value=7), patch.object(d.os, 'getpgid', return_value=7):
            yield p


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = d.build_runtime()

    def tearDown(self):
        self.p._resume_assert_unchanged()

    def test_code_pins_precede_import(self):
        with patch.object(d, 'checked_sources', side_effect=ValueError('pin')), \
             patch.object(d.importlib, 'import_module') as imported:
            with self.assertRaisesRegex(ValueError, 'pin'):
                d.build_runtime()
        imported.assert_not_called()

    def test_original_source_pins_match_all_six_files(self):
        values = d.checked_sources()
        self.assertEqual(set(values), set(d.SOURCE_PINS))
        self.assertEqual(len(values), 6)

    def test_corrupt_frozen_source_rejected_before_private_exec(self):
        values = d.checked_sources(); values[d.LEGACY] += b'\n'
        with patch.object(d, '_private_module') as private:
            with self.assertRaisesRegex(ValueError, 'source'):
                d._build_runtime(*self.p._resume_originals, values)
        private.assert_not_called()

    def test_full_info_keeps_parent_and_recipe_and_adds_only_controller_pins(self):
        info = self.p.info(); original = self.p._resume_originals[1].info()
        for key in ('parent', 'parent_sha256', 'expected_parent_core', 'tokenizer_sha256', 'arms',
                    'epochs', 'updates', 'rows_per_pass', 'groups_per_pass', 'micro_bs', 'accum', 'seq',
                    'grad_checkpoint', 'adam_lr', 'muon_lr', 'objective', 'scheduler', 'native_windows',
                    'native_binding', 'active_limit_seconds', 'evaluation_reserve_seconds', 'record_reserve_seconds',
                    'dialogue_history', 'selection_tag', 'source_admission_policy'):
            self.assertEqual(info[key], original[key], key)
        self.assertEqual(info['tag'], d.TAG)
        self.assertEqual(info['expected_parent_core'], d.PARENT_CORE)
        self.assertEqual(info['authority_end_utc'], d.END.isoformat())
        self.assertEqual(info['training_stop_utc'], d.TRAIN_STOP.isoformat())
        self.assertEqual(set(info['code_sha256']), set(original['code_sha256']) | {d.SCRIPT, d.TEST})
        self.assertTrue(info['code_complete'])
        self.assertFalse(info['new_corpus'])
        self.assertNotIn('source_admission', info)

    def test_original_and_provider_and_execution_are_distinct_namespaces(self):
        old, recovery = self.p._resume_originals
        self.assertIsNot(self.p, old)
        self.assertIsNot(self.p._resume_provider, old)
        self.assertIsNot(self.p._resume_provider, self.p)
        self.assertIsNot(self.p._resume_recovery, recovery)
        self.assertIs(self.p._resume_recovery.legacy, self.p._resume_provider)
        for name in ('_INFO', '_PHASES', '_DIALOGUES', '_DISPLAY'):
            self.assertIs(inspect_function_globals(getattr(self.p._resume_recovery, name)),
                          vars(self.p._resume_provider))

    def test_all_scientific_bodies_and_captured_globals_are_exact(self):
        old = self.p._resume_originals[0]
        for name in d.BODY_NAMES:
            self.assertEqual(d.body_sha(getattr(self.p, name)), d.body_sha(getattr(old, name)), name)
            self.assertIs(inspect_function_globals(getattr(self.p, name)), vars(self.p), name)
        for function in self.p._resume_captured.values():
            self.assertIs(inspect_function_globals(function), vars(self.p))
        self.assertEqual(set(self.p._resume_binding_names), d.BINDING_ALLOWLIST)

    def test_private_recovery_scope_cannot_mutate_original_modules_even_during_scope(self):
        snapshots = [dict(vars(module)) for module in self.p._resume_originals]
        metadata = [module.info() for module in self.p._resume_originals]
        with self.p._resume_recovery.runtime_scope():
            self.assertEqual(self.p._resume_provider.TAG, d.ORIGINAL_TAG)
            for module, snapshot, info in zip(self.p._resume_originals, snapshots, metadata):
                self.assertEqual(set(vars(module)), set(snapshot))
                self.assertTrue(all(getattr(module, k) is v for k, v in snapshot.items()))
                self.assertEqual(module.info(), info)
        self.p._resume_assert_unchanged()

    def test_provider_metadata_never_uses_v3_dates_or_tag(self):
        with self.p._resume_recovery.runtime_scope():
            info = self.p._resume_provider.info()
        self.assertEqual(info['tag'], d.ORIGINAL_TAG)
        self.assertEqual(info['authority_end_utc'], '2026-10-20T08:00:00+00:00')
        self.assertEqual(info['expected_parent_core'], d.PARENT_CORE)

    def test_actual_hash_selectors_keep_original_v1_semantics(self):
        old = self.p._resume_originals[0]
        rows = [conversation(i, language) for language in ('ko', 'en') for i in range(12)]
        cases = [dict(id=str(i), lane='coded') for i in range(20)] + [dict(id='u', lane='user_seen')]
        self.assertEqual(self.p.select_dialogues(rows, Tokens()), old.select_dialogues(rows, Tokens()))
        self.assertEqual(self.p.monitor_display_ids(cases), old.monitor_display_ids(cases))
        self.assertEqual(self.p.TAG, d.TAG)

    def test_private_body_replacement_is_detected(self):
        saved = self.p.train_updates
        try:
            self.p.train_updates = lambda *args: 0
            with self.assertRaises(ValueError):
                self.p._resume_assert_unchanged()
        finally:
            self.p.train_updates = saved

    def test_foreign_private_binding_is_detected(self):
        try:
            self.p.unregistered_parent_loader = object()
            with self.assertRaises(ValueError):
                self.p._resume_assert_unchanged()
        finally:
            del self.p.unregistered_parent_loader

    def test_native_resume_parent_substitution_is_detected(self):
        saved = self.p._resume_provider
        try:
            self.p._resume_provider = types.SimpleNamespace(TAG='p106b_native_resume_v2_s1337')
            with self.assertRaises(ValueError):
                self.p._resume_assert_unchanged()
        finally:
            self.p._resume_provider = saved

    def test_private_recovery_nested_source_pin_mutation_is_detected(self):
        pins = self.p._resume_recovery.REFERENCE_PINS
        key = next(iter(pins)); before = pins[key]
        try:
            pins[key] = 'F' * 64
            with self.assertRaisesRegex(ValueError, '중첩'):
                self.p._resume_assert_unchanged()
        finally:
            pins[key] = before

    def test_children_always_use_new_driver_and_include_new_regression(self):
        for mode in self.p.MODES:
            arms = self.p.ARMS if mode in ('cost', 'train') else (None, *self.p.ARMS) if mode == 'evaluate' else (None,)
            for arm in arms:
                phases = self.p.phase_commands(mode, arm, 600)
                self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
                self.assertIn('scripts.test_p106b_broad_resume', phases[0][1])
                self.assertIn('scripts.test_p106b_broad_recovery', phases[0][1])
                for _, command in phases[1:]:
                    self.assertEqual(command.count(d.SCRIPT), 1)
                    self.assertNotIn(d.LEGACY, command)
                    self.assertNotIn(d.RECOVERY, command)
        for mode, arm in (('prepare', 'mixed'), ('train', None), ('readback', 'staged')):
            with self.assertRaises(ValueError):
                self.p.phase_commands(mode, arm, 600)

    def test_armless_evaluation_is_parent_and_foreign_arms_rejected(self):
        self.assertEqual(self.p.activity_key('evaluate', None), 'evaluate_parent')
        for arm in self.p.ARMS:
            self.assertIn(d.TAG, str(self.p.checkpoint(arm)))
        for arm in (None, 'parent', 'ternary', 'float'):
            with self.assertRaises(ValueError):
                self.p.checkpoint(arm)

    def test_extended_date_guard_preserves_training_stop_and_final_authority(self):
        self.assertGreater(self.p.authority(True, datetime(2026, 10, 20, 8, tzinfo=timezone.utc)), 0)
        with self.assertRaises(self.p.Pending):
            self.p.authority(True, d.TRAIN_STOP)
        with self.assertRaises(self.p.Pending):
            self.p.authority(False, d.END)
        with self.assertRaises(ValueError):
            self.p.authority(now=datetime(2026, 10, 20))

    def test_check_only_is_no_asset_no_model_no_write(self):
        with patch.object(d, 'build_runtime', return_value=self.p), \
             patch.object(d, 'run_worker', side_effect=AssertionError('worker forbidden')), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(d.main(['--mode', 'evaluate', '--check-only']), 0)
        self.assertEqual(json.loads(output.getvalue().split(' ', 1)[1])['tag'], d.TAG)

    def test_unchanged_launcher_has_own_session_and_devnull_stdin(self):
        process = Mock(); process.wait.return_value = 0
        with patch.object(self.p.subprocess, 'Popen', return_value=process) as popen:
            self.assertEqual(self.p.launch(['fixture'], 60), 0)
        self.assertIs(popen.call_args.kwargs['stdin'], subprocess.DEVNULL)
        self.assertTrue(popen.call_args.kwargs['start_new_session'])


def inspect_function_globals(function):
    import inspect
    return inspect.unwrap(function).__globals__


class BridgeTests(unittest.TestCase):
    def test_source_calls_strict_original_equivalence_and_full_prepared(self):
        with fixture() as f:
            bundle, binding = f.p.source_state()
            self.assertIs(bundle, f.bundle)
            self.assertIn('equivalence', f.calls)
            self.assertIn('prepared', f.calls)
            self.assertEqual(binding['parent']['core_sha256'], d.PARENT_CORE)
            self.assertEqual(binding['original_tag'], d.ORIGINAL_TAG)
            self.assertEqual(binding['rows_per_pass'], 22528)
            self.assertEqual(binding['new_payload_rows'], 0)
            self.assertEqual(sum(v['seconds'] for v in binding['prior_activities']), 20.)
            f.p._resume_assert_unchanged()

    def test_prepare_full_info_serialization_roundtrip_does_not_copy_course_or_wire(self):
        with fixture() as f:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(f.p.prepare(), 0)
            value = f.p.required(f.p.CACHE / 'frozen.json')
            self.assertGreater(len(value), 55)
            self.assertNotIn('source_admission', value)
            self.assertEqual(value['source_admission_policy'], 'CPU_PREPARE_ONLY')
            self.assertIs(f.p.prepared(completed=False), f.bundle)
            self.assertFalse((f.p.CACHE / 'wire').exists())
            self.assertFalse((f.p.CACHE / 'course.json').exists())
            self.assertEqual(list(f.p.RAW.iterdir()), [])

    def test_prepare_is_write_once_and_preserves_old_bytes(self):
        with fixture() as f:
            paths = [*f.old_cache.iterdir(), *f.old_evidence.iterdir()]
            before = {p: d.file_sha(p) for p in paths}
            with redirect_stdout(io.StringIO()):
                f.p.prepare()
            with self.assertRaises(FileExistsError):
                f.p.prepare()
            self.assertEqual(before, {p: d.file_sha(p) for p in paths})

    def test_own_bridge_requires_completed_actual_prepare_activity(self):
        with fixture() as f:
            with redirect_stdout(io.StringIO()):
                f.p.prepare()
            with self.assertRaises(f.p.Pending):
                f.p.prepared()

    def test_failed_original_equivalence_never_enters_new_namespace(self):
        with fixture() as f:
            f.hooks['equivalence'] = lambda: (_ for _ in ()).throw(ValueError('original receipt'))
            with self.assertRaisesRegex(ValueError, 'original receipt'):
                f.p.prepare()
            self.assertFalse(f.p.CACHE.exists())

    def test_changed_original_geometry_parent_and_native_offsets_are_rejected(self):
        for change in ('rows', 'parent', 'windows'):
            with self.subTest(change=change), fixture() as f:
                if change == 'rows':
                    f.bundle['course'].records.pop()
                elif change == 'parent':
                    f.bundle['contract']['expected_parent_core'] = 'F' * 64
                else:
                    f.bundle['contract']['native_train_offsets'].pop()
                with self.assertRaisesRegex(ValueError, 'geometry'):
                    f.p.source_state()

    def test_bridge_and_public_contract_metadata_tampering_is_rejected(self):
        info = d.build_runtime().info()
        binding = dict(original_tag=d.ORIGINAL_TAG, original_raw_directory='old/raw',
            parent=dict(core_sha256=d.PARENT_CORE), cases_sha256='A' * 64)
        expected = d.bridge_value(info, binding)
        public = d.bridge_contract(expected, 'B' * 64)
        d.validate_bridge(json.loads(json.dumps(expected)), public, expected, 'B' * 64)
        for key, value in (('tag', d.ORIGINAL_TAG), ('authority_end_utc', '2026-10-20T08:00:00+00:00'),
                           ('expected_parent_core', 'F' * 64), ('raw_scope', 'ORIGINAL_RAW_OVERWRITE')):
            with self.subTest(key=key):
                changed = copy.deepcopy(expected); changed[key] = value
                with self.assertRaises(ValueError):
                    d.validate_bridge(changed, public, expected, 'B' * 64)
        changed = copy.deepcopy(public); changed['frozen_sha256'] = 'C' * 64
        with self.assertRaises(ValueError):
            d.validate_bridge(expected, changed, expected, 'B' * 64)

    def test_prior_actual_wall_included_once_and_not_promoted_to_new_runtime(self):
        with fixture() as f:
            self.assertEqual(f.p.spent_seconds(), 20.)
            with redirect_stdout(io.StringIO()):
                f.p.prepare()
            own = activity(f.p, 'prepare', seconds=11.)
            f.p.write(f.p.EVIDENCE / 'activity_prepare.json', own)
            self.assertEqual(f.p.spent_seconds(), 31.)
            self.assertEqual(f.p.prepared(), f.bundle)
            self.assertEqual(f.p.required(f.old_evidence / 'activity_prepare.json')['seconds'], 13.)

    def test_old_activity_retag_or_report_sha_damage_is_rejected(self):
        for key, value in (('tag', d.TAG), ('report_sha256', 'F' * 64), ('seconds', float('nan'))):
            with self.subTest(key=key), fixture() as f:
                path = f.old_evidence / 'activity_prepare.json'
                original = json.loads(path.read_text())
                original[key] = value
                with path.open('w', encoding='utf-8') as stream:
                    json.dump(original, stream)
                with self.assertRaises(ValueError):
                    f.p.spent_seconds()


class WorkerTests(unittest.TestCase):
    def test_successful_tiny_worker_records_exact_report_sha_and_pid(self):
        with owned_worker_fixture() as p, redirect_stdout(io.StringIO()):
            self.assertEqual(d.run_worker(p, 'readback', None, 60), 0)
            value = p.required(p.EVIDENCE / 'activity_readback.json')
            d.validate_activity(p, value, 'readback', own=True)
            self.assertTrue(value['complete'])
            self.assertEqual(value['report_sha256'], p.digest(p.EVIDENCE / 'readback.json'))
            self.assertEqual(value['pid'], value['pgid'])

    def test_worker_activity_is_write_once(self):
        with owned_worker_fixture() as p, redirect_stdout(io.StringIO()):
            d.run_worker(p, 'readback', None, 60)
            before = p.digest(p.EVIDENCE / 'activity_readback.json')
            with self.assertRaises(FileExistsError):
                d.run_worker(p, 'readback', None, 60)
            self.assertEqual(before, p.digest(p.EVIDENCE / 'activity_readback.json'))

    def test_failed_worker_never_becomes_complete_and_preserves_partial_report(self):
        with owned_worker_fixture() as p, redirect_stdout(io.StringIO()):
            def fail():
                p.write(p.EVIDENCE / 'readback.json', dict(partial=True))
                raise ValueError('synthetic failure')
            p.readback = fail
            with self.assertRaisesRegex(ValueError, 'synthetic failure'):
                d.run_worker(p, 'readback', None, 60)
            value = p.required(p.EVIDENCE / 'activity_readback.json')
            self.assertFalse(value['complete'])
            self.assertEqual(value['returncode'], 9)
            self.assertEqual(value['error_type'], 'ValueError')
            d.validate_activity(p, value, 'readback', own=True)

    def test_budget_cap_hold_is_recorded_before_any_compute(self):
        with owned_worker_fixture() as p, redirect_stdout(io.StringIO()):
            p.spent_seconds = lambda: p.ACTIVE_LIMIT - 1799
            p.prepare = Mock(side_effect=AssertionError('compute forbidden'))
            with self.assertRaises(p.Pending):
                d.run_worker(p, 'prepare', None, 60)
            p.prepare.assert_not_called()
            value = p.required(p.EVIDENCE / 'activity_prepare.json')
            self.assertFalse(value['complete'])
            self.assertEqual(value['returncode'], 8)

    def test_absolute_deadline_cap_hold_preserves_record_reserve(self):
        with owned_worker_fixture() as p, redirect_stdout(io.StringIO()):
            p.authority = lambda training=False: 659.
            p.readback = Mock(side_effect=AssertionError('compute forbidden'))
            with self.assertRaises(p.Pending):
                d.run_worker(p, 'readback', None, 60)
            p.readback.assert_not_called()

    def test_term_is_130_finally_recorded_and_handler_restored(self):
        before = signal.getsignal(signal.SIGTERM)
        with owned_worker_fixture() as p, redirect_stdout(io.StringIO()):
            def terminate():
                signal.raise_signal(signal.SIGTERM)
            p.readback = terminate
            with self.assertRaises(KeyboardInterrupt):
                d.run_worker(p, 'readback', None, 60)
            value = p.required(p.EVIDENCE / 'activity_readback.json')
            self.assertFalse(value['complete'])
            self.assertEqual(value['returncode'], 130)
            self.assertEqual(value['error_type'], 'KeyboardInterrupt')
            self.assertIsNone(value['report_sha256'])
        self.assertEqual(signal.getsignal(signal.SIGTERM), before)

    def test_term_during_admission_is_also_recorded(self):
        with owned_worker_fixture() as p, redirect_stdout(io.StringIO()):
            p.spent_seconds = lambda: signal.raise_signal(signal.SIGTERM)
            with self.assertRaises(KeyboardInterrupt):
                d.run_worker(p, 'readback', None, 60)
            self.assertEqual(p.required(p.EVIDENCE / 'activity_readback.json')['returncode'], 130)

    def test_foreign_process_group_rejected(self):
        with owned_worker_fixture() as p, patch.object(d.os, 'getpgid', return_value=8):
            with self.assertRaisesRegex(ValueError, 'PGID'):
                d.run_worker(p, 'readback', None, 60)
            self.assertFalse(p.EVIDENCE.exists())

    def test_readonly_modes_create_no_namespace_or_runtime_claim(self):
        for mode in ('source', 'preflight', 'budget'):
            with self.subTest(mode=mode), owned_worker_fixture() as p, redirect_stdout(io.StringIO()) as out:
                self.assertEqual(d.run_worker(p, mode, None, 60), 0)
                self.assertFalse(p.EVIDENCE.exists())
                self.assertIn('BROAD_RESUME_WORKER_FINAL', out.getvalue())

    def test_budget_formula_body_preserved_and_resource_constants_unchanged(self):
        p = d.build_runtime(); old = p._resume_originals[0]
        self.assertEqual(d.body_sha(p._resume_captured['budget']), d.body_sha(old.budget))
        self.assertEqual((p.ACTIVE_LIMIT, p.EVAL_RESERVE, p.RECORD_RESERVE), (10800, 1200, 600))
        self.assertEqual(p.UPDATES * 128, 45056)
        self.assertEqual(p.UPDATES * 8192, 2883584)

    def test_exact_budget_formula_uses_first_and_worst_warm_and_prior_wall(self):
        p = d.build_runtime()
        with tempfile.TemporaryDirectory(prefix='broad-budget-') as directory:
            env = dict(vars(p))
            costs = {'mixed': [100.] + [1.] * 7, 'staged': [1.] + [2.] * 7}
            env.update(EVIDENCE=Path(directory), prepared=lambda: {'fixture': True},
                completed_activity=lambda *args: None,
                read_training=lambda arm, **kwargs: dict(step_seconds=costs[arm]),
                spent_seconds=lambda: 20., authority=lambda training=False: 100000.)
            budget = types.FunctionType(p._resume_captured['budget'].__code__, env)
            value = budget()
            expected = {arm: times[0] + max(times[1:]) * 351 * 1.35 + 300 for arm, times in costs.items()}
            self.assertEqual(value['estimated_training_seconds'], expected)
            self.assertEqual(value['total_reserved_seconds'], 20 + sum(expected.values()) + 1200 + 600)
            env['spent_seconds'] = lambda: 10000.
            with self.assertRaises(p.Pending):
                budget()
            env['spent_seconds'] = lambda: 20.
            env['authority'] = lambda training=False: 1.
            with self.assertRaises(p.Pending):
                budget()

    def test_invalid_activity_values_and_forged_complete_rejected(self):
        with owned_worker_fixture() as p, redirect_stdout(io.StringIO()):
            d.run_worker(p, 'readback', None, 60)
            original = p.required(p.EVIDENCE / 'activity_readback.json')
            for key, value in (('tag', d.ORIGINAL_TAG), ('complete', False), ('returncode', 9),
                               ('pgid', 8), ('seconds', float('inf')), ('max_wall_sec', 0),
                               ('report_sha256', 'F' * 64), ('code_sha256', {})):
                changed = copy.deepcopy(original); changed[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    d.validate_activity(p, changed, 'readback', own=True)

    def test_main_reports_build_failure_without_loading_assets(self):
        with patch.object(d, 'build_runtime', side_effect=ValueError('source pin')), \
             redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
            self.assertEqual(d.main(['--mode', 'source', '--check-only']), 9)
        self.assertIn('BROAD_RESUME_FINAL', out.getvalue())


class IsolatedReaderTests(unittest.TestCase):
    def test_new_cost_reader_rejects_native_parent_and_old_raw_lineage(self):
        p = d.build_runtime()
        with tempfile.TemporaryDirectory(prefix='broad-cost-reader-') as directory:
            root = Path(directory); cache, evidence = root / 'cache', root / 'evidence'
            put(cache / 'frozen.json', {'fixture': True})
            base = dict(p.info(), status='COST8_COMPLETE', arm='mixed', actual_updates=8,
                initial_core_sha256=d.PARENT_CORE, frozen_sha256=d.file_sha(cache / 'frozen.json'),
                checkpoint_written=False, event_manifest=dict(lineage=dict(tag=d.TAG, arm='mixed', cost=True)))
            spy = Mock(side_effect=AssertionError('잘못된 계보 뒤에는 원문을 읽지 않는다'))
            env = dict(vars(p))
            env.update(ROOT=root, CACHE=cache, EVIDENCE=evidence, safe=lambda path: Path(path),
                digest=d.file_sha, required=lambda path: json.loads(Path(path).read_text()),
                monitor=types.SimpleNamespace(base=types.SimpleNamespace(PARENT_CORE=d.PARENT_CORE), read_rows=spy))
            read = types.FunctionType(p.read_training.__code__, env, 'read_training', p.read_training.__defaults__)
            read.__kwdefaults__ = p.read_training.__kwdefaults__
            target = evidence / 'cost_mixed/report.json'
            for kind in ('parent', 'raw'):
                value = copy.deepcopy(base)
                if kind == 'parent':
                    value['initial_core_sha256'] = 'F' * 64
                else:
                    value['event_manifest']['lineage']['tag'] = d.ORIGINAL_TAG
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('w') as stream:
                    json.dump(value, stream)
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    read('mixed', cost=True, bundle={'fixture': True})
            spy.assert_not_called()

    def test_eval_reader_never_consumes_old_raw_namespace_or_retagged_manifest(self):
        p = d.build_runtime()
        with tempfile.TemporaryDirectory(prefix='broad-raw-reader-') as directory:
            root = Path(directory); evidence, raw = root / 'evidence', root / 'new_raw'
            parent = root / 'parent_not_opened.pt'
            base = types.SimpleNamespace(PARENT=parent, PARENT_SHA=d.PARENT_SHA,
                PARENT_CORE=d.PARENT_CORE, NATIVE_VAL_SHA='NATIVE_VAL_METADATA_ONLY')
            lineage = dict(tag=d.TAG, endpoint='parent', checkpoint='parent_not_opened.pt',
                checkpoint_sha256=d.PARENT_SHA, expected_core_sha256=d.PARENT_CORE)
            manifest = dict(lineage=lineage, rows=16)
            source = dict(contract=dict(monitor_cases_sha256='A' * 64, dialogue_cases_sha256='B' * 64))
            report = dict(p.info(), status='ACTUAL_MONITOR_AND_DIALOGUES_RECORDED', lineage=lineage,
                core_before=d.PARENT_CORE, core_after=d.PARENT_CORE, weights_changed=False,
                checkpoints_written=0, monitor_cases_sha256='A' * 64, dialogue_cases_sha256='B' * 64,
                native32_fp32=dict(targets=32768, windows=32, precision='FP32_MATH',
                    val_sha256=base.NATIVE_VAL_SHA, ce=1.), dialogue_manifest=manifest)
            old_path = root / 'old_raw/evaluate_parent/dialogue_answers_shards_manifest.json'
            put(old_path, manifest); report['dialogue_manifest_sha256'] = d.file_sha(old_path)
            put(evidence / 'evaluate_parent/report.json', report)
            spy = Mock(side_effect=AssertionError('잘못된 raw 계보에서 답을 읽으면 안 된다'))
            env = dict(vars(p))
            env.update(ROOT=root, EVIDENCE=evidence, RAW=raw, digest=d.file_sha,
                required=lambda path: json.loads(Path(path).read_text()),
                completed_activity=lambda *args: None, monitor=types.SimpleNamespace(base=base, read_rows=spy))
            read = types.FunctionType(p._read_eval.__code__, env)
            with self.assertRaises(FileNotFoundError):
                read('parent', source, Tokens())
            wrong = copy.deepcopy(manifest); wrong['lineage']['tag'] = d.ORIGINAL_TAG
            new_path = raw / 'evaluate_parent/dialogue_answers_shards_manifest.json'
            put(new_path, wrong)
            with self.assertRaisesRegex(ValueError, 'manifest'):
                read('parent', source, Tokens())
            spy.assert_not_called()


if __name__ == '__main__':
    unittest.main()
