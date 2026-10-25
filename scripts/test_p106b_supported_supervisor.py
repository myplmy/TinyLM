"""모델·GPU·원천 재생 없이 소유 프로세스와 게시 계약을 CPU로 검증한다."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
import ctypes
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_supported_supervisor as diag


def good_result(code=8, status='CLOSED_PRODUCTION_PAUSED'):
    return dict(schema=diag.SCHEMA, process_started=True, actual_producer_exit=code,
        original_error=None, cleanup_errors=[], forced_cleanup=False, parent_witness_errors=[],
        audit_errors=[], subreaper_restored=True, source_inputs_unchanged=True, owned_sessions=[],
        production_verification=dict(status=status), stop_published=False,
        controller_group_cleanup=['GROUP_QUIESCENT'])


class ControlledBudget:
    def __init__(self):
        self.started = time.monotonic()
        self.end = self.started + 60
        self.reserve = 2
        self.expired = False

    def remaining(self):
        return 0. if self.expired else self.end - time.monotonic()

    def check(self, stage):
        if self.expired:
            raise TimeoutError('합성 시간 초과: ' + stage)


class SupervisorTests(unittest.TestCase):
    def arguments(self, **changes):
        values = dict(execute=True, check_only=False, max_wall_sec=600,
            deadline_utc=diag.PRODUCTION_STOP.isoformat(), tag=diag.PREFIX + 'cpu_fixture',
            source_sha256='A' * 64)
        values.update(changes)
        return SimpleNamespace(**values)

    def budget(self, seconds=3., reserve=1.5):
        return diag.Budget(seconds, time.time() + seconds + 10,
            started=time.monotonic(), reserve=reserve)

    def test_explicit_limits_deadline_and_namespace(self):
        now = diag.PRODUCTION_STOP - timedelta(hours=1)
        self.assertEqual(diag.validate_args(self.arguments(), now), diag.PRODUCTION_STOP)
        for change in (dict(execute=False), dict(check_only=True), dict(max_wall_sec=299),
                dict(max_wall_sec=7201), dict(max_wall_sec=True), dict(tag='../bad'),
                dict(tag=diag.PREFIX), dict(source_sha256='bad'),
                dict(deadline_utc='2026-10-25T03:40:00'),
                dict(deadline_utc=(diag.PRODUCTION_STOP + timedelta(seconds=1)).isoformat()),
                dict(deadline_utc=(now + timedelta(seconds=599)).isoformat())):
            with self.subTest(change=change), self.assertRaises((ValueError, TypeError)):
                diag.validate_args(self.arguments(**change), now)

    def test_whole_window_charges_parent_preparation(self):
        now = time.monotonic()
        budget = diag.Budget(10., time.time() + 100, started=now - 3, reserve=2)
        self.assertLessEqual(budget.remaining(), 7.)
        with self.assertRaises(ValueError):
            diag.Budget(2., time.time() + 100, started=now - 1, reserve=2)
        budget.end = time.monotonic() - 1
        with self.assertRaises(TimeoutError):
            budget.check('마감')

    def test_external_alarm_is_not_replaced_and_handler_restores(self):
        budget = self.budget()
        previous = signal.getsignal(signal.SIGALRM)
        with diag.total_budget(budget):
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 0)
            with self.assertRaises(ValueError):
                with diag.total_budget(budget):
                    pass
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0., 0.))

    def test_term_during_preparation_or_terminal_io_is_caught_and_restored(self):
        previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
        with self.assertRaises(InterruptedError):
            with diag.termination_guard():
                os.kill(os.getpid(), signal.SIGTERM)
        self.assertEqual(previous, {sig: signal.getsignal(sig) for sig in previous})

    def test_timer_cleanup_failure_preserves_original_exception(self):
        budget = self.budget()
        previous = signal.getsignal(signal.SIGALRM)
        def timer(which, value):
            if value == 0:
                raise OSError('타이머 해제 오류')
        with patch.object(diag.signal, 'setitimer', new=timer):
            with self.assertRaisesRegex(ValueError, '원 준비 오류') as caught:
                with diag.total_budget(budget):
                    raise ValueError('원 준비 오류')
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous)
        record = diag.error_record(caught.exception, '전체 시간창')
        self.assertEqual(record['cleanup_errors'][0]['message'], '타이머 해제 오류')

    def test_path_guard_protects_tinydataset_links_and_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('datasets/TinyDataset/a', '../escape', '/tmp/escape'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    diag.safe(name, root)
            (root / 'linked').symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                diag.safe('linked/child', root)

    def test_pause8_never_turns_into_zero(self):
        self.assertEqual(diag.disposition(good_result()), ('CLOSED_PRODUCTION_PAUSED', 8))
        self.assertEqual(diag.disposition(good_result(0, 'TARGET_READY')), ('TARGET_READY', 0))
        self.assertEqual(diag.disposition(good_result(8, 'PRE_MODEL_HOLD')), ('PRE_MODEL_HOLD', 8))
        for change in (dict(actual_producer_exit=9), dict(actual_producer_exit=0),
                dict(actual_producer_exit=None), dict(process_started=None), dict(forced_cleanup=True),
                dict(cleanup_errors=[{'message': '정리 오류'}]), dict(original_error={'message': '원 오류'}),
                dict(parent_witness_errors=[{'pid': 1}]), dict(subreaper_restored=False),
                dict(source_inputs_unchanged=False), dict(audit_errors=[{'message': '감사 오류'}])):
            value = good_result()
            value.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                diag.disposition(value)

    def test_pre_model_hold_allows_memory_but_not_teacher(self):
        value = good_result(8, 'PRE_MODEL_HOLD')
        value['owned_sessions'] = [dict(role='memory')]
        self.assertEqual(diag.disposition(value)[1], 8)
        value['owned_sessions'].append(dict(role='teacher'))
        with self.assertRaises(ValueError):
            diag.disposition(value)

    def run_cpu(self, code, *, seconds=3., reserve=1.5, factory=subprocess.Popen,
                roles=None, scan_delay=False):
        def subreaper_value():
            value = ctypes.c_int()
            self.assertEqual(ctypes.CDLL(None).prctl(37, ctypes.byref(value), 0, 0, 0), 0)
            return value.value
        previous_subreaper = subreaper_value()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            stop, marker = directory / 'STOP_CPU_UNIQUE', directory / 'pids.json'
            argv = [sys.executable, '-B', '-c', code, str(stop), str(marker)]
            kwargs = dict(factory=factory)
            real_scan = diag.OwnedSessions.scan
            delayed = [False]
            def scan(tracker):
                if tracker.controller is not None and not delayed[0]:
                    delayed[0] = True
                    time.sleep(.2)
                return real_scan(tracker)
            before = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
            with ExitStack() as stack:
                if scan_delay:
                    stack.enter_context(patch.object(diag.OwnedSessions, 'scan', new=scan))
                result = diag.supervise_process(argv, directory, stop,
                    roles or {'teacher': sys.executable}, self.budget(seconds, reserve), **kwargs)
            result['test_marker'] = json.loads(marker.read_text()) if marker.exists() else {}
            result['test_stop_exists'] = stop.exists()
            result['test_log'] = (directory / 'producer.log').read_text() if (directory / 'producer.log').exists() else ''
            self.assertEqual(before, {sig: signal.getsignal(sig) for sig in before})
            self.assertEqual(subreaper_value(), previous_subreaper)
            for pid in result['test_marker'].get('pids', []):
                with self.assertRaises((FileNotFoundError, ProcessLookupError)):
                    diag.proc.proc_stat(pid)
            self.assertNotIn(diag.OWNER_KEY + '=', json.dumps(result))
            return result

    def test_real_cpu_stop_closes_owned_session_and_keeps_child8(self):
        code = """
import json,os,pathlib,signal,subprocess,sys,time
stop,marker=map(pathlib.Path,sys.argv[1:])
worker=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(30)'],start_new_session=True)
marker.write_text(json.dumps({'pids':[worker.pid]}))
while not stop.exists(): time.sleep(.02)
os.killpg(worker.pid,signal.SIGTERM)
worker.wait(timeout=2)
raise SystemExit(8)
"""
        result = self.run_cpu(code)
        self.assertEqual(result['actual_producer_exit'], 8)
        self.assertTrue(result['stop_published'] and result['test_stop_exists'])
        self.assertFalse(result['forced_cleanup'])
        self.assertIsNone(result['original_error'])
        self.assertFalse(result['cleanup_errors'])
        self.assertTrue(result['subreaper_restored'])
        self.assertTrue(all(row['direct_parent_verified'] for row in result['owned_sessions']))

    def test_real_cpu_leader_first_and_term_ignored_child_are_reaped(self):
        worker = 'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); signal.signal(signal.SIGINT,signal.SIG_IGN); time.sleep(30)'
        code = """
import json,pathlib,subprocess,sys,time
worker=subprocess.Popen([sys.executable,'-B','-c',WORKER],start_new_session=True)
pathlib.Path(sys.argv[2]).write_text(json.dumps({'pids':[worker.pid]}))
time.sleep(.18)
raise SystemExit(0)
""".replace('WORKER', repr(worker))
        result = self.run_cpu(code)
        self.assertEqual(result['actual_producer_exit'], 0)
        self.assertTrue(result['forced_cleanup'])
        self.assertTrue(result['residual_at_producer_exit'])
        signals = [sig for row in result['owned_session_cleanup'] for sig in row['signals']]
        self.assertIn('SIGTERM', signals)
        self.assertIn('SIGKILL', signals)
        self.assertTrue(all(row['group_quiescent'] for row in result['owned_session_cleanup']))
        with self.assertRaises(ValueError):
            diag.disposition(dict(result, source_inputs_unchanged=True, production_verification={'status': 'TARGET_READY'}))

    def test_real_cpu_unseen_original_parent_is_not_claimed_verified(self):
        code = """
import json,pathlib,subprocess,sys
worker=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(30)'],start_new_session=True)
pathlib.Path(sys.argv[2]).write_text(json.dumps({'pids':[worker.pid]}))
raise SystemExit(0)
"""
        result = self.run_cpu(code, scan_delay=True)
        self.assertEqual(result['actual_producer_exit'], 0)
        self.assertTrue(result['parent_witness_errors'])
        self.assertFalse(result['owned_sessions'][0]['direct_parent_verified'])
        self.assertTrue(result['forced_cleanup'])

    def test_real_cpu_separate_group_survives_its_own_leader_and_is_reaped(self):
        worker = """
import json,os,pathlib,signal,sys,time
pid=os.fork()
if pid:
 pathlib.Path(sys.argv[1]).write_text(json.dumps({'pids':[pid]}))
 os._exit(0)
signal.signal(signal.SIGTERM,signal.SIG_IGN)
signal.signal(signal.SIGINT,signal.SIG_IGN)
time.sleep(30)
"""
        code = """
import subprocess,sys,time
worker=subprocess.Popen([sys.executable,'-B','-c',WORKER,sys.argv[2]],start_new_session=True)
worker.wait(timeout=2)
time.sleep(.18)
raise SystemExit(0)
""".replace('WORKER', repr(worker))
        result = self.run_cpu(code)
        self.assertEqual(result['actual_producer_exit'], 0)
        self.assertTrue(result['forced_cleanup'])
        self.assertTrue(any(row.get('orphan_group_member') for row in result['owned_sessions']))
        self.assertFalse(result['cleanup_errors'])

    def test_real_cpu_same_group_short_query_is_not_detached_or_rejected(self):
        sleep = str(Path(shutil.which('sleep')).resolve())
        code = """
import subprocess
subprocess.run([SLEEP,'.25'],check=True)
raise SystemExit(8)
""".replace('SLEEP', repr(sleep))
        result = self.run_cpu(code, roles={'memory': sleep})
        self.assertEqual(result['actual_producer_exit'], 8)
        self.assertFalse(result['forced_cleanup'])
        self.assertFalse(result['owned_sessions'])
        self.assertTrue(result['synchronous_queries'])
        self.assertIsNone(result['original_error'])

    def test_real_cpu_term_to_supervisor_publishes_stop_before_cleanup(self):
        timers = []
        code = """
import pathlib,sys,time
while not pathlib.Path(sys.argv[1]).exists(): time.sleep(.01)
raise SystemExit(8)
"""
        def factory(*args, **kwargs):
            child = subprocess.Popen(*args, **kwargs)
            timer = threading.Timer(.2, lambda: os.kill(os.getpid(), signal.SIGTERM))
            timers.append(timer)
            timer.start()
            return child
        try:
            result = self.run_cpu(code, factory=factory)
        finally:
            for timer in timers:
                timer.cancel()
                timer.join()
        self.assertEqual(result['actual_producer_exit'], 8)
        self.assertEqual(result['deferred_signals'], [int(signal.SIGTERM)])
        self.assertTrue(result['stop_published'])
        self.assertFalse(result['forced_cleanup'])

    def test_preexisting_foreign_process_environ_is_not_read_or_signalled(self):
        foreign = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(30)'],
            start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        original = Path.read_bytes
        def guarded(path, *args, **kwargs):
            if str(path) == '/proc/%s/environ' % foreign.pid:
                raise AssertionError('이전 타 프로세스 environ 읽기 금지')
            return original(path, *args, **kwargs)
        try:
            with patch.object(Path, 'read_bytes', new=guarded):
                result = self.run_cpu('import time; time.sleep(.15); raise SystemExit(8)')
            self.assertIsNone(foreign.poll())
            self.assertIsNone(result['original_error'])
        finally:
            foreign.terminate()
            foreign.wait(timeout=3)

    def test_pid_reuse_veto_precedes_any_signal(self):
        tracker = object.__new__(diag.OwnedSessions)
        tracker.known = {987654: dict(pid=987654, starttime=1, pgid=987654, session=987654)}
        with patch.object(tracker, 'scan', return_value={}), \
                patch.object(diag.proc, 'proc_stat', return_value=dict(pid=987654, starttime=2, pgid=987654, session=987654)), \
                patch.object(diag.os, 'killpg') as kill:
            with self.assertRaisesRegex(ValueError, '시작 시각'):
                diag.cleanup_sessions(tracker, time.monotonic() + 1)
            kill.assert_not_called()

    def test_controller_pid_reuse_is_not_owned_by_old_popen_registration(self):
        saved = dict(starttime=1, ppid=100, pgid=12345, session=12345)
        with patch.object(diag.proc, 'proc_stat', return_value=dict(saved, starttime=2)), \
                patch.object(diag.os, 'killpg') as kill:
            with self.assertRaisesRegex(ValueError, '생산기 PID'):
                diag.assert_controller(SimpleNamespace(pid=12345), saved)
            kill.assert_not_called()

    def test_stale_detached_pgid_without_current_owned_member_never_signals(self):
        tracker = object.__new__(diag.OwnedSessions)
        tracker.known = {987654: dict(pid=987654, starttime=1, pgid=987654, session=987654)}
        with patch.object(tracker, 'scan', return_value={}), \
                patch.object(diag.proc, 'proc_stat', side_effect=FileNotFoundError('과거 leader 부재')), \
                patch.object(diag, 'group_alive', return_value=True), \
                patch.object(tracker, 'live_group_member', return_value=None) as anchor, \
                patch.object(diag.os, 'killpg') as kill:
            with self.assertRaisesRegex(ValueError, '과거 PGID'):
                diag.cleanup_sessions(tracker, time.monotonic() + 1)
            anchor.assert_called_once_with(987654, 987654)
            kill.assert_not_called()

    def test_stale_controller_pgid_without_current_owned_member_never_calls_public_stop(self):
        tracker = SimpleNamespace(controller=dict(pid=987654, starttime=1, ppid=os.getpid(),
            pgid=987654, session=987654), live_group_member=lambda *a, **k: None)
        with patch.object(diag.proc, 'proc_stat', side_effect=FileNotFoundError('과거 leader 부재')), \
                patch.object(diag.smoke, 'owned_group_alive', return_value=True), \
                patch.object(diag.smoke, 'stop_process_group') as stop, \
                patch.object(diag.os, 'killpg') as kill:
            with self.assertRaisesRegex(ValueError, '과거 controller PGID'):
                diag.stop_controller_group(SimpleNamespace(pid=987654), tracker, ControlledBudget(), {})
            stop.assert_not_called()
            kill.assert_not_called()

    def test_current_group_anchor_checks_executable_before_foreign_token(self):
        tracker = object.__new__(diag.OwnedSessions)
        executable = str(Path(sys.executable).resolve())
        tracker.executables = {'teacher': executable}
        tracker.controller = dict(pid=987654, starttime=10, executable=executable)
        tracker.before, tracker.known, tracker.queries = {}, {}, {}
        tracker.token = '합성소유토큰'
        row = dict(pid=987655, starttime=20, pgid=987654, session=987654, state='S', ppid=os.getpid())
        entry = Path('/proc/987655')
        for matches in (False, True):
            calls = []
            def readlink(path):
                calls.append('exe')
                return executable if matches else '/허용하지않은/실행파일'
            def stat(pid):
                calls.append('stat')
                return row
            def environment(path):
                calls.append('environ')
                return (diag.OWNER_KEY + '=다른토큰').encode()
            with self.subTest(matches=matches), patch.object(Path, 'iterdir', return_value=iter([entry])), \
                    patch.object(diag.os, 'readlink', new=readlink), \
                    patch.object(diag.proc, 'proc_stat', new=stat), \
                    patch.object(Path, 'read_bytes', new=environment):
                self.assertIsNone(tracker.live_group_member(987654, 987654))
            self.assertEqual(calls, ['exe', 'stat', 'environ'] if matches else ['exe'])

    def test_cleanup_return_errors_or_forced_signals_veto_actual_pause8(self):
        for note in ('CLEANUP_ERROR:가짜', 'MASK_BLOCK_ERROR:가짜', 'MASK_RESTORE_ERROR:UNCONFIRMED',
                     'INTERRUPT_DURING_CLEANUP:가짜', 'PENDING_INTERRUPT:15',
                     'SIGINT_PROCESS_GROUP', 'SIGKILL_PROCESS_GROUP', '미확인_반환표지'):
            with self.subTest(note=note):
                result = good_result()
                result['controller_group_cleanup'] = [note, 'GROUP_QUIESCENT']
                result['controller_group_quiescent'] = True
                diag.record_cleanup_notes(result, result['controller_group_cleanup'])
                self.assertEqual(result['actual_producer_exit'], 8)
                with self.assertRaises(ValueError):
                    diag.disposition(result)
                with tempfile.TemporaryDirectory() as tmp:
                    code, target = self.mocked_run(Path(tmp), ControlledBudget(), result=result)
                    self.assertEqual(code, 9)
                    receipt = diag.read_json(target / 'supervisor_receipt.json')
                    self.assertEqual(receipt['actual_producer_exit'], 8)
                    self.assertEqual(receipt['controller_group_cleanup'], [note, 'GROUP_QUIESCENT'])

    def test_cleanup_return_audit_never_overwrites_primary_exception(self):
        result = good_result()
        result['original_error'] = {'type': 'ValueError', 'message': '원 실행 예외'}
        diag.record_cleanup_notes(result, ['MASK_RESTORE_ERROR:UNCONFIRMED', 'GROUP_QUIESCENT'])
        self.assertEqual(result['original_error']['message'], '원 실행 예외')
        self.assertEqual(result['cleanup_errors'][0]['notes'], ['MASK_RESTORE_ERROR:UNCONFIRMED'])

    def test_real_preexec_term_is_not_consumed_by_inherited_delayed_handler(self):
        previous = signal.getsignal(signal.SIGTERM)
        delayed = []
        signal.signal(signal.SIGTERM, lambda signum, frame: delayed.append(signum))
        try:
            child = subprocess.Popen([sys.executable, '-B', '-c', 'raise SystemExit(0)'],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                preexec_fn=lambda owner=os.getpid() + 100000: diag.child_limits(owner))
            self.assertEqual(child.wait(timeout=3), -int(signal.SIGTERM))
            self.assertFalse(delayed)
        finally:
            signal.signal(signal.SIGTERM, previous)

    def test_preexisting_enabled_subreaper_is_restored_enabled(self):
        previous = diag.proc.set_subreaper(1)
        try:
            result = self.run_cpu('import time; time.sleep(.12); raise SystemExit(8)')
            self.assertTrue(result['subreaper_restored'])
        finally:
            diag.proc.set_subreaper(previous)

    def test_primary_creation_and_subreaper_cleanup_errors_stay_separate(self):
        calls = []
        def subreaper(value):
            calls.append(value)
            if len(calls) == 2:
                raise OSError('복구 오류')
            return 0
        with tempfile.TemporaryDirectory() as tmp, patch.object(diag.proc, 'set_subreaper', new=subreaper):
            with patch.object(diag, 'child_limits'):
                result = diag.supervise_process(['합성 생성'], Path(tmp), Path(tmp) / 'STOP',
                    {'teacher': sys.executable}, self.budget(),
                    factory=lambda *a, **k: (_ for _ in ()).throw(ValueError('원 생성 오류')))
        self.assertEqual(result['original_error']['message'], '원 생성 오류')
        self.assertEqual(result['cleanup_errors'][0]['message'], '복구 오류')
        self.assertEqual(result['launch_state'], 'UNKNOWN')
        self.assertIsNone(result['process_started'])

    def test_token_original_text_is_redacted_from_exception(self):
        token = '절대출력하지않는고유토큰'
        record = diag.error_record(ValueError('실패 ' + token), '소유 검산', token)
        self.assertNotIn(token, json.dumps(record, ensure_ascii=False))

    def fixture(self, root, *, status='PRODUCTION_PAUSED', code=8, meta_changes=None):
        destination = root / 'production'
        directory = destination / 'batch_000000'
        directory.mkdir(parents=True)
        previous = dict(cursor=[1, 10], nonpadding_tokens={'train:ko': 100},
            assistant_targets={'train:ko': 10}, rows={'train:ko': 1}, token_target_ready=False,
            family_tokens={'train:ko:synthetic': 100}, task_tokens={'train:ko:qa': 100})
        for key in ('teacher_deficit_tokens', 'task_deficit_tokens', 'validation_deficit_tokens'):
            previous[key] = {'ko': 1, 'en': 1}
        diag.proc.write_once(directory / 'report.json', previous)
        budget = ControlledBudget()
        before = diag.production_snapshot(destination, budget)
        directory = destination / 'batch_000001'
        directory.mkdir()
        inputs = {'visible_source_contract': diag.VERSION, 'runtime_code_sha256': '합성'}
        raw = diag.shards.ShardWriter(directory, 'raw')
        thought = '합성 사고'
        raw.append(dict(source={'meta': {'source_id': 'fixture:1'}}, language='ko', task='qa',
            turn=1, attempt=1, payload={'messages': []}, reply={'choices': []},
            parsed={'teacher_reasoning_content': thought},
            producer_learner_turn={'user_text': '합성 질문', 'assistant_text': '합성 답'},
            input_tokens=10, request_sec=.1))
        candidate = diag.shards.ShardWriter(directory, 'candidates')
        meta = dict(visible_source_contract=diag.VERSION, teacher_batch=directory.name,
            source_split='train', language='ko', processed_x_tokens=20, assistant_targets=5,
            selection_family='synthetic', capability_profile='qa', source_id='fixture:1',
            teacher_reasoning_refs=[dict(raw_row_1based=1, in_student=False,
                sha256=diag.hashlib.sha256(thought.encode()).hexdigest().upper())])
        meta.update(meta_changes or {})
        candidate.append({'meta': meta})
        report = dict(schema='P106B_GEMMA_DEFICIT_BATCH_V1', input=inputs, status=status, returncode=code,
            error_type='ProductionBudgetPause', accepted_groups=1, cursor=[1, 11],
            raw_manifest=raw.close(lineage=inputs), candidate_manifest=candidate.close(lineage=inputs),
            nonpadding_tokens={'train:ko': 120}, assistant_targets={'train:ko': 15}, rows={'train:ko': 2},
            family_tokens={'train:ko:synthetic': 120}, task_tokens={'train:ko:qa': 120},
            new_train_x_tokens=20, token_target_ready=False)
        path = directory / 'report.json'
        diag.proc.write_once(path, report)
        log = root / 'producer.log'
        log.write_text('[DEFICIT_FINAL] {}\n')
        return destination, before, inputs, log, budget, report, path

    def test_closed_new_batch_manifest_counters_and_cursor_pause8(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination, before, inputs, log, budget, report, path = self.fixture(Path(tmp))
            result = diag.verify_production(destination, before, inputs, 8, log, budget)
        self.assertEqual(result['status'], 'CLOSED_PRODUCTION_PAUSED')
        self.assertEqual(result['cursor'], [1, 11])
        self.assertEqual(result['new_train_x_tokens'], 20)
        self.assertEqual(result['accepted_groups'], 1)

    def test_missing_bad_or_inconsistent_closed_batch_is_error(self):
        mutations = [lambda r: r.update(nonpadding_tokens={'train:ko': 121}),
            lambda r: r.update(assistant_targets={'train:ko': 14}),
            lambda r: r.update(rows={'train:ko': 1}), lambda r: r.update(cursor=[1, 9]),
            lambda r: r.update(family_tokens={'train:ko:synthetic': 119}),
            lambda r: r.update(task_tokens={'train:ko:qa': 119}),
            lambda r: r.update(accepted_groups=2), lambda r: r.update(new_train_x_tokens=19),
            lambda r: r.update(error_type='RuntimeError'), lambda r: r.update(status='SOURCE_EXHAUSTED'),
            lambda r: r['candidate_manifest'].update(rows=2), lambda r: r.update(returncode=9),
            lambda r: r.update(input={'소스': '변경'}), lambda r: r.pop('candidate_manifest'),
            lambda r: r.pop('raw_manifest')]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as tmp:
                destination, before, inputs, log, budget, report, path = self.fixture(Path(tmp))
                mutate(report)
                path.write_bytes(diag.canonical(report))
                with self.assertRaises((ValueError, KeyError)):
                    diag.verify_production(destination, before, inputs, 8, log, budget)

    def test_changed_old_batch_is_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination, before, inputs, log, budget, report, path = self.fixture(Path(tmp))
            old = destination / 'batch_000000' / 'report.json'
            previous = old.read_bytes()
            old.write_bytes(previous + b' ')
            with self.assertRaisesRegex(ValueError, '기존 배치'):
                diag.verify_production(destination, before, inputs, 8, log, budget)
            self.assertEqual(old.read_bytes(), previous + b' ')

    def test_new_manifest_same_length_changed_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination, before, inputs, log, budget, report, path = self.fixture(Path(tmp))
            shard = path.parent / report['candidate_manifest']['shards'][0]['path']
            original = shard.read_bytes()
            changed = original.replace(b'20', b'21', 1)
            self.assertEqual(len(changed), len(original))
            shard.write_bytes(changed)
            with self.assertRaises(ValueError):
                diag.verify_production(destination, before, inputs, 8, log, budget)

    def test_raw_manifest_disk_or_response_shard_is_required_and_verified(self):
        for change in ('명세없음', '원응답없음', '원응답바이트변경'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                destination, before, inputs, log, budget, report, path = self.fixture(Path(tmp))
                manifest = path.parent / 'raw_shards_manifest.json'
                raw = path.parent / report['raw_manifest']['shards'][0]['path']
                if change == '명세없음':
                    manifest.rename(path.parent / '미완_원응답명세.json')
                elif change == '원응답없음':
                    raw.rename(path.parent / '미완_원응답.jsonl')
                else:
                    raw.write_bytes(raw.read_bytes() + b' ')
                with self.assertRaises((ValueError, FileNotFoundError)):
                    diag.verify_production(destination, before, inputs, 8, log, budget)

    def test_candidate_raw_response_reference_range_and_hash_are_required(self):
        for changes in ({'teacher_reasoning_refs': []},
                {'teacher_reasoning_refs': [dict(raw_row_1based=2, in_student=False, sha256='A' * 64)]},
                {'teacher_reasoning_refs': [dict(raw_row_1based=1, in_student=False, sha256='A' * 64)]},
                {'source_id': 'fixture:다른원천'}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                destination, before, inputs, log, budget, report, path = self.fixture(Path(tmp), meta_changes=changes)
                with self.assertRaises(ValueError):
                    diag.verify_production(destination, before, inputs, 8, log, budget)

    def test_manifest_and_shards_are_frozen_before_and_after_inspection(self):
        for stem in ('raw', 'candidates'):
            with self.subTest(stem=stem), tempfile.TemporaryDirectory() as tmp:
                destination, before, inputs, log, budget, report, path = self.fixture(Path(tmp))
                original = diag.raw_response_index
                def mutate(*args):
                    rows = original(*args)
                    manifest = path.parent / (stem + '_shards_manifest.json')
                    manifest.write_bytes(manifest.read_bytes() + b' ')
                    return rows
                with patch.object(diag, 'raw_response_index', new=mutate), self.assertRaisesRegex(ValueError, '검산 전후'):
                    diag.verify_production(destination, before, inputs, 8, log, budget)

    def test_nonfinite_new_report_is_an_api_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination, before, inputs, log, budget, report, path = self.fixture(Path(tmp))
            report['new_train_x_per_sec'] = float('nan')
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, '비유한'):
                diag.verify_production(destination, before, inputs, 8, log, budget)

    def test_no_new_batch_requires_pre_model_hold_or_actual_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / 'production'
            destination.mkdir()
            directory = destination / 'batch_000000'
            directory.mkdir()
            previous = {'token_target_ready': False}
            diag.proc.write_once(directory / 'report.json', previous)
            budget = ControlledBudget()
            before = diag.production_snapshot(destination, budget)
            log = root / 'producer.log'
            log.write_text('[HOLD] 합성 선결 부족\n')
            self.assertEqual(diag.verify_production(destination, before, {}, 8, log, budget)['status'], 'PRE_MODEL_HOLD')
            with self.assertRaises(ValueError):
                diag.verify_production(destination, before, {}, 0, log, budget)

    def test_exit0_needs_target_ready_and_all_deficits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination, before, inputs, log, budget, report, path = self.fixture(Path(tmp), status='PRODUCTION_READY', code=0)
            report['error_type'] = None
            report['token_target_ready'] = True
            for key in ('teacher_deficit_tokens', 'task_deficit_tokens', 'validation_deficit_tokens'):
                report[key] = {'ko': 0, 'en': 0}
            path.write_bytes(diag.canonical(report))
            self.assertEqual(diag.verify_production(destination, before, inputs, 0, log, budget)['status'], 'TARGET_READY')
            report['teacher_deficit_tokens']['ko'] = 1
            path.write_bytes(diag.canonical(report))
            with self.assertRaises(ValueError):
                diag.verify_production(destination, before, inputs, 0, log, budget)

    def test_write_once_reread_delay_is_inside_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'receipt.json'
            budget = ControlledBudget()
            original = diag.proc.write_once
            def delayed(*args):
                original(*args)
                budget.expired = True
            with patch.object(diag.proc, 'write_once', new=delayed), self.assertRaises(TimeoutError):
                diag.write_once(path, {'원문': '보존'}, budget)
            before = path.read_bytes()
            budget.expired = False
            with self.assertRaises(FileExistsError):
                diag.write_once(path, {'원문': '다름'}, budget)
            self.assertEqual(path.read_bytes(), before)

    def test_append_only_veto_and_size_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            diag.append_terminal(target, {'event': 'FINAL_DISPOSITION', 'intended_supervisor_exit': 8})
            first = (target / 'terminal.jsonl').read_bytes()
            diag.append_terminal(target, {'event': 'TERMINAL_VETO', 'intended_supervisor_exit': 9})
            self.assertTrue((target / 'terminal.jsonl').read_bytes().startswith(first))
            with patch.object(diag, 'MAX_BYTES', 1), self.assertRaises(ValueError):
                diag.append_terminal(target, {'event': '추가'})

    def test_original_shard_exact20mb_bound_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'raw_000000.jsonl'
            path.write_bytes(b'{}\n')
            original = Path.stat
            def stat(value, *args, **kwargs):
                actual = original(value, *args, **kwargs)
                if value == path:
                    values = list(actual)
                    values[6] = diag.MAX_BYTES
                    return os.stat_result(values)
                return actual
            with patch.object(Path, 'stat', new=stat):
                self.assertEqual(diag.bounded_file(path), path)

    def test_stale_source_stops_before_batch_read_or_process_creation(self):
        with patch.object(diag, 'source_receipt', return_value={'source_sha256': 'B' * 64}), \
                patch.object(diag, 'production_snapshot') as snapshot, \
                patch.object(diag, 'supervise_process') as process:
            with self.assertRaisesRegex(ValueError, '영수증'):
                diag.run(self.arguments(), ControlledBudget())
            snapshot.assert_not_called()
            process.assert_not_called()

    def mocked_run(self, root, budget, *, slow_stdout=False, result=None):
        destination = root / diag.OUTPUT
        destination.mkdir(parents=True)
        inputs = {'합성': '입력'}
        diag.proc.write_once(destination / 'inputs.json', inputs)
        preflight = root / diag.PREFLIGHT
        preflight.parent.mkdir(parents=True)
        diag.proc.write_once(preflight, dict(closed_batches=2, cursor=[1, 10], nonpadding_tokens={'train:ko': 100}))
        (root / 'test_result/evidence').mkdir(parents=True)
        receipt = dict(source_sha256='A' * 64, executables={'teacher': {'path': sys.executable}})
        before = dict(batches=2, reports=[dict(cursor=[1, 10], nonpadding_tokens={'train:ko': 100})])
        result = good_result() if result is None else result
        def slow(*args, **kwargs):
            budget.expired = True
        with ExitStack() as stack:
            stack.enter_context(patch.object(diag, 'source_receipt', return_value=receipt))
            stack.enter_context(patch.object(diag, 'safe', new=lambda name: root / name))
            stack.enter_context(patch.object(diag, 'production_snapshot', return_value=before))
            stack.enter_context(patch.object(diag, 'supervise_process', return_value=result))
            stack.enter_context(patch.object(diag, 'verify_production', return_value={'status': 'CLOSED_PRODUCTION_PAUSED'}))
            stack.enter_context(redirect_stdout(io.StringIO()))
            if slow_stdout:
                stack.enter_context(patch('builtins.print', new=slow))
            code = diag.run(self.arguments(), budget)
        return code, root / 'test_result/evidence' / self.arguments().tag

    def test_complete_mock_pause_preserves8_and_final_receipt_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, target = self.mocked_run(Path(tmp), ControlledBudget())
            self.assertEqual(code, 8)
            result = diag.read_json(target / 'supervisor_receipt.json')
            self.assertEqual(result['actual_producer_exit'], 8)
            self.assertEqual(result['intended_supervisor_exit'], 8)
            final = json.loads((target / 'terminal.jsonl').read_text().splitlines()[-1])
            self.assertEqual(final['event'], 'FINAL_DISPOSITION')
            self.assertEqual(final['receipt_sha256'], diag.identity(result))

    def test_stdout_delay_veto_does_not_rewrite_provisional_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, target = self.mocked_run(Path(tmp), ControlledBudget(), slow_stdout=True)
            self.assertEqual(code, 9)
            receipt = diag.read_json(target / 'supervisor_receipt.json')
            self.assertEqual(receipt['actual_producer_exit'], 8)
            self.assertEqual(receipt['intended_supervisor_exit'], 8)
            final = json.loads((target / 'terminal.jsonl').read_text().splitlines()[-1])
            self.assertEqual(final['event'], 'TERMINAL_VETO')
            self.assertEqual(final['intended_supervisor_exit'], 9)

    def test_original_runtime_and_cleanup_errors_survive_final_audit(self):
        value = good_result()
        value['original_error'] = {'message': '원 실행 오류'}
        value['cleanup_errors'] = [{'message': '원 정리 오류'}]
        with tempfile.TemporaryDirectory() as tmp:
            code, target = self.mocked_run(Path(tmp), ControlledBudget(), result=value)
            result = diag.read_json(target / 'supervisor_receipt.json')
            self.assertEqual(code, 9)
            self.assertEqual(result['original_error']['message'], '원 실행 오류')
            self.assertEqual(result['cleanup_errors'][0]['message'], '원 정리 오류')

    def test_check_only_imports_no_framework_and_performs_no_writes_or_replay(self):
        code = (
            "import builtins,sys; original=builtins.__import__; "
            "exec(\"def guarded(name,*a,**k):\\n if name.split('.')[0] in ('torch','triton','tokenizers','tinylm'): raise AssertionError('프레임워크 import 금지')\\n return original(name,*a,**k)\\n\"); "
            "builtins.__import__=guarded; "
            "exec(\"def audit(event,args):\\n if event=='open' and isinstance(args[2],int) and args[2]&1603: raise AssertionError('쓰기 금지')\\n if event in ('os.mkdir','os.remove','os.rmdir','os.rename','os.link','os.symlink','os.truncate','os.chmod','os.chown','os.utime','subprocess.Popen'): raise AssertionError('상태 변경 금지')\\n\"); "
            "sys.addaudithook(audit); from scripts import diag_p106b_supported_supervisor as d; raise SystemExit(d.main(['--check-only']))"
        )
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=ROOT,
            env=dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1'),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report['torch_imported'])
        self.assertEqual(report['model_calls'], 0)
        self.assertEqual(report['gpu_calls'], 0)
        self.assertEqual(report['source_replay_calls'], 0)
        self.assertEqual(report['files_written'], 0)


if __name__ == '__main__':
    unittest.main()
