"""합성 CPU와 모의 제어 검증만 수행한다. 모델·원자료·CUDA는 실행하지 않는다."""
from __future__ import annotations

import copy
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import gc
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import weakref

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p102a_fused_ce_fp32 as diag
from scripts.test_p102a_fused_ce_driver import cpu_capture, Journal, ControlledGuard
import torch
from tinylm.train import muon


def report_fixture():
    comparisons = {}
    for key in (*diag.fused.FULL_FIELDS, *diag.fused.MATRIX_FIELDS, 'optimizer'):
        count = diag.fused.ALL_COUNT if key in diag.fused.FULL_FIELDS else diag.fused.MATRIX_COUNT
        if key == 'optimizer':
            count = diag.fused.MATRIX_COUNT + 3 * (diag.fused.ALL_COUNT - diag.fused.MATRIX_COUNT)
        comparisons[key] = dict(close=True, tensors=count,
            per_parameter=[dict(name='synthetic.' + str(i), finite=True, close=True) for i in range(count)])
    for key in ('loss', 'preclip_norm'):
        comparisons[key] = dict(close=True, left=1., right=1.)
    matrix = dict(identical_gradient_control=dict(exact=True),
        actual_reproduction={label: dict(exact=True) for label in ('reference', 'candidate')},
        original_pair=dict(close=True))
    replay = dict(complete=True, matrix_count=85,
        same_gradient_controls_exact=True, actual_updates_reproduced_exactly=True,
        matrices={'synthetic.' + str(i): copy.deepcopy(matrix) for i in range(85)})
    pair = dict(close=True, comparisons=comparisons, replay=replay)
    return dict(schema=diag.SCHEMA, tag=diag.TAG_PREFIX + 'cpu_fixture',
        checkpoint_writes=0, actual_process_exit='PENDING_SUPERVISOR_AND_EXTERNAL_CALLER',
        canaries=dict(complete=True, close=True, precisions={diag.PRECISION: {
            backend: dict(status='COMPLETE', close=True) for backend in diag.fused.BACKENDS}}),
        updates=[dict(precision=diag.PRECISION, ce_backend=backend) for backend in diag.fused.BACKENDS],
        pairs={backend: copy.deepcopy(pair) for backend in diag.fused.BACKENDS[1:]},
        assets_before=None, errors=[], cleanup_errors=[],
        sources_unchanged=True, wrapper_sources_unchanged=True, dependencies_unchanged=True,
        installed_sources_unchanged=True, original_muon_globals_unchanged=True,
        final_allocated_bytes=0)


class ClockGuard:
    def __init__(self):
        self.started, self.current, self.expired = 0., 1., False
        self.seconds, self.deadline = 600, datetime(2026, 10, 25, 4, tzinfo=timezone.utc)
        self.checks = []

    def check(self, stage):
        self.checks.append(stage)
        if self.expired:
            raise TimeoutError('합성 시간창 초과: ' + stage)

    def remaining(self):
        return 100.

    def clock(self):
        return self.current


class Capture(dict):
    pass


class FP32Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        with patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA 금지')):
            cls.initial, cls.capture = cpu_capture()

    def setUp(self):
        self.cuda_patch = patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA 금지'))
        self.cuda_patch.start()
        self.addCleanup(self.cuda_patch.stop)

    def arguments(self, **changes):
        values = dict(check_only=False, execute=True, _worker=False,
            tag=diag.TAG_PREFIX + 'cpu_fixture', deadline='2026-10-25T04:00:00+00:00',
            max_wall_sec=600, source_sha256='A' * 64, dependency_sha256='B' * 64, _started=None)
        values.update(changes)
        return SimpleNamespace(**values)

    def test_original_precision_backend_and_historical_deadlines_unchanged(self):
        self.assertEqual(diag.fused.PRECISIONS, ('fp32_math', 'bf16_eager'))
        self.assertEqual(diag.fused.BACKENDS, ('reference', 'liger', 'cce_exact'))
        self.assertNotEqual(diag.TAG_PREFIX, diag.fused.TAG_PREFIX)
        self.assertLess(diag.old.HARD_STOP, diag.HARD_STOP)
        self.assertLess(diag.trace.HARD_STOP, diag.HARD_STOP)
        self.assertFalse(diag.fused.matrix_complete(report_fixture()))

    def test_explicit_window_and_absolute_deadline(self):
        now = datetime(2026, 10, 25, 3, tzinfo=timezone.utc)
        self.assertEqual(diag.validate_execution(self.arguments(), now), diag.HARD_STOP)
        for change in (dict(deadline=None), dict(deadline='2026-10-25T04:00:00'),
                dict(deadline=now.isoformat()), dict(deadline='2026-10-25T04:00:01+00:00'),
                dict(max_wall_sec=59), dict(max_wall_sec=901), dict(max_wall_sec=True),
                dict(deadline=(now + timedelta(seconds=599)).isoformat()),
                dict(execute=False), dict(_worker=True), dict(check_only=True),
                dict(source_sha256='stale'), dict(dependency_sha256=None)):
            with self.subTest(change=change), self.assertRaises((ValueError, TypeError)):
                diag.validate_execution(self.arguments(**change), now)

    def test_worker_charges_parent_start_without_requiring_new_full_reservation(self):
        now = diag.HARD_STOP - timedelta(seconds=599)
        args = self.arguments(execute=False, _worker=True)
        self.assertEqual(diag.validate_execution(args, now), diag.HARD_STOP)
        with patch.object(diag.time, 'perf_counter', return_value=11.):
            guard = diag.Guard(diag.HARD_STOP, 600, started=1., reserve=15)
        self.assertEqual(guard.seconds, 585)
        self.assertEqual(guard.deadline, diag.HARD_STOP - timedelta(seconds=15))
        with patch.object(diag.old, 'utc_now', return_value=diag.HARD_STOP - timedelta(seconds=500)), \
                patch.object(diag.time, 'perf_counter', return_value=12.):
            self.assertEqual(guard.remaining(), 485.)
        with patch.object(diag.time, 'perf_counter', return_value=11.):
            for started in (float('nan'), -1., 12.):
                with self.subTest(started=started), self.assertRaises(ValueError):
                    diag.Guard(diag.HARD_STOP, 60, started=started)

    def test_cpu_interpreter_cannot_substitute_for_cuda_execution(self):
        now = datetime(2026, 10, 25, 3, tzinfo=timezone.utc)
        with patch.dict(os.environ, {'TRITON_INTERPRET': '1'}), self.assertRaisesRegex(ValueError, '인터프리터'):
            diag.validate_execution(self.arguments(), now)

    def test_fresh_namespace_and_original_namespace_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for tag in (diag.fused.TAG_PREFIX + 'x', diag.TAG_PREFIX, '../escape', diag.TAG_PREFIX + 'X'):
                with self.subTest(tag=tag), self.assertRaises(ValueError):
                    diag.output_path(tag, root)
            target = diag.output_path(self.arguments().tag, root)
            target.mkdir(parents=True)
            prior = target / 'keep.txt'
            prior.write_text('기존 증거', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                diag.output_path(self.arguments().tag, root)
            self.assertEqual(prior.read_text(encoding='utf-8'), '기존 증거')

    def test_same_length_changed_bytes_change_source_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (diag.SCRIPT, diag.TEST, *diag.SUPERVISION):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'abcd')
            with patch.object(diag.fused, 'sources', return_value={'original.py': 'C' * 64}):
                first = diag.sources(root)
                (root / diag.SCRIPT).write_bytes(b'abce')
                second = diag.sources(root)
            self.assertEqual((root / diag.SCRIPT).stat().st_size, 4)
            self.assertNotEqual(diag.old.identity(first), diag.old.identity(second))
            self.assertEqual(first['original.py'], second['original.py'])

    def test_pin_failure_stops_before_dependency_source_or_gpu_admission(self):
        guard = ClockGuard()
        with patch.object(diag, 'sources', return_value={'x': 'Y'}), \
                patch.object(diag.fused, 'dependency_metadata') as metadata, \
                patch.object(diag.fused, 'verify_installed_sources') as installed, \
                patch.object(diag.old, 'gpu_admission', side_effect=AssertionError('CUDA 입장 금지')):
            with self.assertRaisesRegex(ValueError, '소스'):
                diag.check_pins(self.arguments(), guard)
            metadata.assert_not_called()
            installed.assert_not_called()

    def test_dependency_stale_or_not_ready_is_rejected(self):
        source_map, dependencies = {'x': 'Y'}, {'ready': True}
        with patch.object(diag, 'sources', return_value=source_map), \
                patch.object(diag.fused, 'dependency_metadata', return_value=dependencies), \
                patch.object(diag.fused, 'verify_installed_sources') as installed:
            args = self.arguments(source_sha256=diag.old.identity(source_map))
            with self.assertRaisesRegex(ValueError, '설치'):
                diag.check_pins(args, ClockGuard())
            installed.assert_not_called()
            args.dependency_sha256 = diag.old.identity(dependencies)
            installed.return_value = {'verified': True}
            self.assertEqual(diag.check_pins(args, ClockGuard()), (source_map, dependencies, {'verified': True}))
            dependencies['ready'] = False
            args.dependency_sha256 = diag.old.identity(dependencies)
            with self.assertRaises(ValueError):
                diag.check_pins(args, ClockGuard())

    def test_metadata_delay_is_inside_guard(self):
        guard = ClockGuard()
        def metadata():
            guard.expired = True
            return {'ready': True}
        with patch.object(diag, 'sources', return_value={'x': 'Y'}), \
                patch.object(diag.fused, 'dependency_metadata', side_effect=metadata), \
                patch.object(diag.fused, 'verify_installed_sources') as installed:
            args = self.arguments(source_sha256=diag.old.identity({'x': 'Y'}))
            with self.assertRaises(TimeoutError):
                diag.check_pins(args, guard)
            installed.assert_not_called()

    def test_complete_three_arms_is_separate_from_original_six(self):
        result = report_fixture()
        self.assertTrue(diag.three_complete(result))
        self.assertEqual(diag.classify(result), ('FP32_NUMERICAL_PASS_NOT_ADOPTED', 0))
        self.assertFalse(diag.fused.matrix_complete(result))
        result['pairs']['liger']['close'] = False
        self.assertEqual(diag.classify(result)[1], 8)

    def test_duplicate_missing_extra_or_wrong_precision_arm_is_incomplete(self):
        mutations = [lambda r: r['updates'].pop(),
            lambda r: r['updates'].append(copy.deepcopy(r['updates'][0])),
            lambda r: r['updates'][1].update(ce_backend='reference'),
            lambda r: r['updates'][0].update(precision='bf16_eager'),
            lambda r: r['pairs'].pop('liger'),
            lambda r: r['pairs'].update(extra=copy.deepcopy(r['pairs']['liger']))]
        for index, mutate in enumerate(mutations):
            result = report_fixture()
            mutate(result)
            with self.subTest(index=index):
                self.assertFalse(diag.three_complete(result))
                self.assertEqual(diag.classify(result)[1], 9)

    def test_every_tensor_and_replay_control_is_required(self):
        mutations = [lambda r: r['pairs']['liger']['comparisons']['raw'].update(tensors=156),
            lambda r: r['pairs']['liger']['comparisons']['raw']['per_parameter'].pop(),
            lambda r: r['pairs']['liger']['comparisons']['optimizer'].update(tensors=300),
            lambda r: r['pairs']['liger']['comparisons'].pop('buffers'),
            lambda r: r['pairs']['liger']['replay'].update(matrix_count=84),
            lambda r: r['pairs']['liger']['replay']['matrices'].pop('synthetic.0'),
            lambda r: r['pairs']['liger']['replay'].update(same_gradient_controls_exact=False),
            lambda r: r['pairs']['liger']['replay']['matrices']['synthetic.0']['actual_reproduction']['reference'].update(exact=False)]
        for index, mutate in enumerate(mutations):
            result = report_fixture()
            mutate(result)
            with self.subTest(index=index):
                self.assertEqual(diag.classify(result)[1], 9)

    def test_nonfinite_and_runtime_errors_are_not_numeric_negative(self):
        for mutate in (
                lambda r: r['pairs']['liger']['comparisons']['loss'].update(nonfinite=True),
                lambda r: r['updates'][0].update(loss=float('inf')),
                lambda r: r['pairs']['liger']['comparisons']['raw']['per_parameter'][0].update(finite=False),
                lambda r: r['errors'].append({'message': '원 오류'}),
                lambda r: r['cleanup_errors'].append({'message': '정리 오류'})):
            result = report_fixture()
            mutate(result)
            self.assertEqual(diag.classify(result)[1], 9)

    def test_replay_numeric_difference_cannot_hide_behind_pair_flag(self):
        result = report_fixture()
        result['pairs']['liger']['replay']['matrices']['synthetic.0']['original_pair']['close'] = False
        self.assertTrue(diag.three_complete(result))
        self.assertEqual(diag.classify(result)[1], 8)

    def test_canary_numeric_negative_does_not_admit_parent(self):
        result = report_fixture()
        result.update(updates=[], pairs={}, assets_before=None, canary_negative={'message': '원 문턱 음성'})
        result['canaries']['close'] = False
        result['canaries']['precisions'][diag.PRECISION]['liger']['close'] = False
        self.assertEqual(diag.classify(result)[1], 8)
        result['assets_before'] = {'parent': '이미 읽음'}
        self.assertEqual(diag.classify(result)[1], 9)

    def test_canary_calls_original_function_only_fp32_and_releases_each_arm(self):
        calls, releases = [], []
        value = dict(loss=2., gradients={'projected': torch.tensor([1.]), 'shared_table': torch.tensor([2.])})
        def arm(torch_, features, table, labels, backend, precision, guard):
            self.assertEqual(tuple(features.shape), (8, 256))
            self.assertEqual(tuple(table.shape), (32768, 256))
            self.assertEqual(labels.tolist(), [0, 1, -100, 32767, 9, 100, 200, 300])
            calls.append((backend, precision))
            return copy.deepcopy(value)
        result = {}
        with patch.object(diag.fused, 'kernel_canary_arm', new=arm), \
                patch.object(diag.trace, 'release_cuda', new=lambda _: releases.append(True)), \
                patch.object(diag.fused, 'run_canaries', side_effect=AssertionError('원 6팔 canary 호출 금지')):
            diag.run_fp32_canaries(torch, diag.old.literal_tolerances(), ClockGuard(), Journal(), result)
        self.assertEqual(calls, [(backend, 'fp32_math') for backend in diag.fused.BACKENDS])
        self.assertEqual(len(releases), 3)
        self.assertTrue(result['complete'] and result['close'])

    def test_canary_finite_mismatch_and_api_error_are_distinct(self):
        def run(error=False):
            def arm(torch_, features, table, labels, backend, precision, guard):
                if error and backend == 'liger':
                    raise RuntimeError('원 커널 오류')
                return dict(loss=2. if backend == 'reference' else 3.,
                    gradients={'x': torch.tensor([1.])})
            result = {}
            with patch.object(diag.fused, 'kernel_canary_arm', new=arm), \
                    patch.object(diag.trace, 'release_cuda'):
                with self.assertRaises(ValueError) as caught:
                    diag.run_fp32_canaries(torch, diag.old.literal_tolerances(), ClockGuard(), Journal(), result)
            return result, caught.exception
        result, error = run()
        self.assertIsInstance(error, diag.fused.NumericalCanaryNegative)
        self.assertTrue(result['complete'])
        result, error = run(True)
        self.assertNotIsInstance(error, diag.fused.NumericalCanaryNegative)
        self.assertFalse(result['complete'])

    def test_real_cpu_compare_and_original_muon_replay_reuse_three_arms(self):
        calls, capture_refs = [], []
        original_replay = diag.fused.replay_pair
        globals_before = dict(vars(muon))
        result = dict(updates=[], pairs={}, tolerances=diag.old.literal_tolerances())
        def capture(*args):
            backend, precision, index = args[8], args[9], args[-1]
            if index == 2:
                gc.collect()
                self.assertIsNone(capture_refs[1]())
                self.assertIsNotNone(capture_refs[0]())
            value = Capture(copy.deepcopy(self.capture))
            value['update'].update(precision=precision, ce_backend=backend)
            calls.append((backend, precision, index))
            capture_refs.append(weakref.ref(value))
            return value
        def replay(*args, **kwargs):
            return original_replay(*args, **kwargs, device='cpu')
        with patch.object(diag.fused, 'released_capture', new=capture), \
                patch.object(diag.fused, 'replay_pair', new=replay), \
                patch.object(diag.old, 'gpu_admission', return_value={}), \
                patch.object(diag.trace, 'release_cuda'):
            diag.execute_three(torch, None, muon, None, None, self.initial, 'synthetic', 0,
                [], {}, ClockGuard(), Journal(), result)
        self.assertEqual(calls, [('reference', 'fp32_math', 0), ('liger', 'fp32_math', 1), ('cce_exact', 'fp32_math', 2)])
        self.assertEqual(len(result['updates']), 3)
        self.assertEqual(result['pairs']['liger']['comparisons']['optimizer']['tensors'], 301)
        self.assertTrue(result['pairs']['liger']['replay']['actual_updates_reproduced_exactly'])
        self.assertTrue(result['pairs']['cce_exact']['replay']['same_gradient_controls_exact'])
        self.assertTrue(all(ref() is None for ref in capture_refs))
        self.assertEqual(set(vars(muon)), set(globals_before))
        self.assertTrue(all(vars(muon)[name] is value for name, value in globals_before.items()))

    def test_original_compare_detects_missing_or_boundary_gradient_and_keeps_tolerance(self):
        tolerance = diag.old.literal_tolerances()
        candidate = copy.deepcopy(self.capture)
        name = next(iter(candidate['raw']))
        candidate['raw'][name][0, 0] += .001
        pair = diag.fused.compare_pair(torch, self.capture, candidate, tolerance)
        self.assertFalse(pair['comparisons']['raw']['close'])
        self.assertEqual(tolerance['gradients_and_update'], {'atol': 2e-6, 'rtol': 1e-5})
        candidate['raw'].pop(name)
        with self.assertRaises(ValueError):
            diag.fused.compare_pair(torch, self.capture, candidate, tolerance)

    def test_memory_budget_stops_before_compare_or_replay(self):
        result = dict(updates=[], pairs={}, tolerances=diag.old.literal_tolerances())
        def capture(*args):
            return copy.deepcopy(self.capture)
        with patch.object(diag.fused, 'released_capture', new=capture), \
                patch.object(diag.fused, 'capture_bytes', return_value=diag.trace.CPU_CAPTURE_LIMIT), \
                patch.object(diag.fused, 'compare_pair') as compare, patch.object(diag.fused, 'replay_pair') as replay:
            with self.assertRaises(MemoryError):
                diag.execute_three(torch, None, None, None, None, self.initial, 'x', 0,
                    [], {}, ClockGuard(), Journal(), result)
            compare.assert_not_called()
            replay.assert_not_called()

    def test_terminal_success_is_provisional_and_write_once(self):
        result, guard = report_fixture(), ClockGuard()
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            target = Path(tmp)
            self.assertEqual(diag.terminalize(target, Journal(), guard, result), 0)
            before = (target / 'report.json').read_bytes()
            events = [json.loads(line) for line in (target / 'terminal.jsonl').read_text().splitlines()]
            self.assertEqual(events[-1]['event'], 'WORKER_AUDIT_COMPLETE')
            self.assertTrue(events[-1]['report_roundtrip'])
            self.assertEqual(diag.terminalize(target, Journal(), guard, result), 9)
            self.assertEqual(before, (target / 'report.json').read_bytes())

    def test_report_write_delay_and_stdout_delay_veto_success(self):
        for delayed in ('write', 'stdout'):
            with self.subTest(delayed=delayed), tempfile.TemporaryDirectory() as tmp:
                guard, result = ClockGuard(), report_fixture()
                original = diag.old.write_new
                def slow_write(path, value):
                    original(path, value)
                    guard.expired = True
                def slow_print(*args, **kwargs):
                    guard.expired = True
                with ExitStack() as stack:
                    stack.enter_context(redirect_stdout(io.StringIO()))
                    if delayed == 'write':
                        stack.enter_context(patch.object(diag.old, 'write_new', new=slow_write))
                    else:
                        stack.enter_context(patch('builtins.print', new=slow_print))
                    self.assertEqual(diag.terminalize(Path(tmp), Journal(), guard, result), 9)
                self.assertTrue(result['errors'])
                events = [json.loads(line) for line in (Path(tmp) / 'terminal.jsonl').read_text().splitlines()]
                self.assertTrue(any(event['event'] == 'TERMINAL_VETO' for event in events))

    def test_primary_and_cleanup_and_storage_errors_are_preserved(self):
        result = report_fixture()
        result['errors'].append({'message': '원 실행 오류'})
        result['cleanup_errors'].append({'message': '원 정리 오류'})
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()), \
                patch.object(diag.fused, 'append_terminal', side_effect=OSError('추가 저장 오류')):
            diag.failure(Path(tmp), result, '종결', TimeoutError('원 시간 초과'))
        self.assertEqual(result['errors'][0]['message'], '원 실행 오류')
        self.assertEqual(result['cleanup_errors'][0]['message'], '원 정리 오류')
        self.assertTrue(any(error.get('message') == '원 시간 초과' for error in result['errors']))
        self.assertTrue(any(error.get('message') == '추가 저장 오류' for error in result['errors']))
        self.assertEqual(diag.classify(result)[1], 9)

    def test_report_size_and_symlink_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            path = target / 'large.json'
            path.write_bytes(b' ' * 65)
            with patch.object(diag, 'MAX_BYTES', 64), self.assertRaises(ValueError):
                diag.read_json(path)
            linked = target / 'linked.json'
            linked.symlink_to(path)
            with self.assertRaises(ValueError):
                diag.read_json(linked)

    def saved_worker(self, target, args, *, negative=False):
        result = report_fixture()
        result['sources'], result['dependencies'] = {'source': 'x'}, {'ready': True}
        args.source_sha256 = diag.old.identity(result['sources'])
        args.dependency_sha256 = diag.old.identity(result['dependencies'])
        result.update(source_sha256=args.source_sha256, dependency_sha256=args.dependency_sha256)
        if negative:
            result['pairs']['liger']['close'] = False
        result['status'], result['returncode'] = diag.classify(result)
        diag.old.write_new(target / 'report.json', result)
        diag.fused.append_terminal(target, dict(event='WORKER_AUDIT_COMPLETE',
            report_roundtrip=True, report_sha256=diag.old.identity(result), returncode=result['returncode']))
        return result, dict(status='COMPLETE', unsafe_process_state=False,
            process_started=True, returncode=result['returncode'])

    def test_actual_worker_exit_and_report_terminal_must_agree(self):
        for negative in (False, True):
            with self.subTest(negative=negative), tempfile.TemporaryDirectory() as tmp:
                args, target = self.arguments(), Path(tmp)
                result, state = self.saved_worker(target, args, negative=negative)
                self.assertEqual(diag.verify_worker(target, args, state, ClockGuard()), 8 if negative else 0)
                state['returncode'] = 0 if negative else 8
                with self.assertRaises(ValueError):
                    diag.verify_worker(target, args, state, ClockGuard())

    def test_terminal_veto_and_unsafe_process_and_cleanup_audit_cannot_pass(self):
        for mutation in ('veto', 'unsafe', 'cleanup', 'allocated', 'source'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                args, target = self.arguments(), Path(tmp)
                result, state = self.saved_worker(target, args)
                if mutation == 'veto':
                    diag.fused.append_terminal(target, {'event': 'TERMINAL_VETO', 'returncode': 9})
                elif mutation == 'unsafe':
                    state['unsafe_process_state'] = True
                elif mutation == 'source':
                    args.source_sha256 = 'D' * 64
                else:
                    result['final_allocated_bytes' if mutation == 'allocated' else 'installed_sources_unchanged'] = 1 if mutation == 'allocated' else False
                    (target / 'report.json').write_bytes(diag.old.canonical(result))
                    (target / 'terminal.jsonl').write_bytes(diag.old.canonical(dict(event='WORKER_AUDIT_COMPLETE',
                        report_roundtrip=True, report_sha256=diag.old.identity(result), returncode=0)) + b'\n')
                with self.assertRaises(ValueError):
                    diag.verify_worker(target, args, state, ClockGuard())

    def test_supervision_reuses_owned_group_and_preserves_primary_state(self):
        calls, state = [], {}
        def run_child(command, **kwargs):
            calls.append(kwargs)
            kwargs['monitor']()
            kwargs['state_sink'].update(status='TOOL_ERROR', returncode=7,
                error='원 worker 오류', unsafe_process_state=True)
            return kwargs['state_sink']
        tools = SimpleNamespace(run_child=run_child, BudgetExpired=TimeoutError)
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'worker.log'
            log.write_bytes(b'')
            result = diag.run_owned_worker(['모의 명령'], {}, log, ClockGuard(), tools=tools, state=state)
        self.assertIs(result, state)
        self.assertEqual(state['returncode'], 7)
        self.assertEqual(state['error'], '원 worker 오류')
        self.assertIs(calls[0]['state_sink'], state)
        self.assertEqual(calls[0]['work_expires'], 93.)
        self.assertEqual(calls[0]['expires'], 98.)

    def test_supervisor_handler_cleanup_failure_does_not_erase_worker_exit(self):
        state = {}
        def run_child(command, **kwargs):
            kwargs['state_sink'].update(status='COMPLETE', returncode=8, process_started=True)
            return kwargs['state_sink']
        tools = SimpleNamespace(run_child=run_child, BudgetExpired=TimeoutError)
        previous = signal.getsignal(signal.SIGTERM)
        def handler(sig, value):
            if value is previous:
                raise OSError('handler 정리 오류')
        with tempfile.TemporaryDirectory() as tmp, patch.object(diag.signal, 'signal', new=handler):
            log = Path(tmp) / 'worker.log'
            log.write_bytes(b'')
            diag.run_owned_worker(['모의 명령'], {}, log, ClockGuard(), tools=tools, state=state)
        self.assertEqual(state['returncode'], 8)
        self.assertTrue(state['unsafe_process_state'])
        self.assertEqual(state['adapter_cleanup_error']['message'], 'handler 정리 오류')

    def test_real_cpu_child_exit8_is_reaped_by_original_owned_group_supervisor(self):
        guard = diag.Guard(diag.old.utc_now() + timedelta(minutes=2), 60, started=diag.time.perf_counter())
        state = {}
        with tempfile.TemporaryDirectory() as tmp:
            logfile = Path(tmp) / 'worker.log'
            with logfile.open('xb') as stream:
                def factory(argv, **options):
                    return subprocess.Popen(argv, **options, stdout=stream, stderr=subprocess.STDOUT)
                diag.run_owned_worker([sys.executable, '-B', '-c', 'raise SystemExit(8)'],
                    dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1'),
                    logfile, guard, factory=factory, state=state)
        self.assertEqual(state['status'], 'COMPLETE')
        self.assertEqual(state['returncode'], 8)
        self.assertFalse(state['unsafe_process_state'])
        self.assertIn('GROUP_QUIESCENT', state['termination'])

    def test_existing_namespace_failure_does_not_append_veto(self):
        with patch.object(diag, 'validate_execution', return_value=diag.HARD_STOP), \
                patch.object(diag, 'Guard'), patch.object(diag.fused, 'total_budget'), \
                patch.object(diag, 'supervise', side_effect=FileExistsError('기존 namespace')), \
                patch.object(diag.fused, 'append_terminal') as append, redirect_stderr(io.StringIO()):
            code = diag.main(['--execute', '--tag', self.arguments().tag])
        self.assertEqual(code, 9)
        append.assert_not_called()

    def test_worker_direct_entry_is_rejected_before_any_model_or_gpu(self):
        with patch.dict(os.environ, {diag.WORKER_ENV: '0'}), \
                patch.object(diag, 'runtime', side_effect=AssertionError('모델 실행 금지')), \
                patch.object(diag.old, 'gpu_admission', side_effect=AssertionError('GPU 입장 금지')):
            with self.assertRaises(ValueError):
                diag.worker(self.arguments(execute=False, _worker=True, _started='1'))

    def test_check_only_in_fresh_process_imports_no_torch_and_writes_nothing(self):
        code = (
            "import builtins,json,sys; "
            "original=builtins.__import__; "
            "exec(\"def guarded(name,*a,**k):\\n if name.split('.')[0] in ('torch','triton','tinylm'): raise AssertionError('프레임워크 import 금지')\\n return original(name,*a,**k)\\n\"); "
            "builtins.__import__=guarded; "
            "exec(\"def audit(event,args):\\n if event=='open' and isinstance(args[2],int) and args[2] & 1603: raise AssertionError('파일 쓰기 금지')\\n if event in ('os.mkdir','os.remove','os.rmdir','os.rename','os.link','os.symlink','os.truncate','os.chmod','os.chown','os.utime'): raise AssertionError('파일 변경 금지')\\n\"); "
            "sys.addaudithook(audit); from scripts import diag_p102a_fused_ce_fp32 as d; raise SystemExit(d.main(['--check-only']))"
        )
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=ROOT,
            env=dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1'),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertFalse(value['torch_imported'])
        self.assertEqual(value['cuda_calls'], 0)
        self.assertEqual(value['asset_reads'], 0)
        self.assertEqual(value['files_written'], 0)
        self.assertEqual(value['original_precisions'], ['fp32_math', 'bf16_eager'])


if __name__ == '__main__':
    unittest.main()
