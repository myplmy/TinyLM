"""Mocked/temp-only regression tests; never execute a real smoke child."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import codex_smoke as smoke
from scripts.smoke_execution_contract import CODEX_CHECKER


BAT = r'''@echo off
setlocal enabledelayedexpansion
python scripts\runlog.py --name !TL_LOGNAME! --note "[tool] instrumentation contract smoke test"
python scripts\runlog.py --name !TL_LOGNAME! -- python scripts\check_handoff.py
timeout /t 15 /nobreak
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --tiny --data synthetic --steps 1 --tag sm_fixture
python scripts\runlog.py --name !TL_LOGNAME! -- python scripts\check_smoke.py
exit /b 0
'''


class Clock:
    def __init__(self):
        self.value = 0.
        self.start = datetime(2031, 4, 3, 10, tzinfo=timezone.utc)

    def tick(self):
        return self.value

    def now(self):
        return self.start + timedelta(seconds=self.value)

    def sleep(self, value):
        self.value += value


class FakeSignals:
    """Virtual masks/handlers only; never send or mask a host signal."""
    def __init__(self, mask=()):
        self.mask = set(mask)
        self.handlers = {signal.SIGINT: 'OLD_INT', signal.SIGTERM: 'OLD_TERM'}
        self.pending = set()
        self.calls = []
        self.restore_interrupts = 0

    def getsignal(self, sig):
        return self.handlers[sig]

    def handler(self, sig, value):
        before = self.handlers[sig]
        self.handlers[sig] = value
        return before

    def sigpending(self):
        return set(self.pending)

    def pthread_sigmask(self, operation, values):
        self.calls.append((operation, set(values)))
        before = set(self.mask)
        if operation == signal.SIG_BLOCK:
            self.mask.update(values)
        elif operation == signal.SIG_SETMASK:
            self.mask = set(values)
            deliver = self.pending - self.mask
            if deliver:
                self.pending.difference_update(deliver)
                raise KeyboardInterrupt('virtual pending signal delivered AFTER mask restoration')
            if self.restore_interrupts:
                self.restore_interrupts -= 1
                raise KeyboardInterrupt('virtual repeated restoration interrupt')
        else:
            raise AssertionError('unexpected mask operation')
        return before

    def patches(self):
        stack = ExitStack()
        for name, target in (('getsignal', self.getsignal), ('signal', self.handler),
                             ('pthread_sigmask', self.pthread_sigmask),
                             ('sigpending', self.sigpending)):
            stack.enter_context(mock.patch.object(smoke.signal, name, side_effect=target))
        return stack


class FakeProcess:
    pid = 999999999

    def __init__(self, clock, code=0, hang=False):
        self.clock, self.code, self.hang = clock, code, hang
        self.returncode = None

    def wait(self, timeout=None):
        if self.hang and self.returncode is None:
            self.clock.value += timeout or 0.
            raise subprocess.TimeoutExpired('MOCK_ONLY', timeout)
        self.clock.value += .01
        if self.returncode is None:
            self.returncode = self.code
        return self.returncode

    def poll(self):
        return self.returncode


class FakeLauncher:
    """All process effects are ordinary text inside the temporary repo."""
    def __init__(self, root, clock, behaviors=None, silent=False, callback=None,
                 payload='fixture output\n'):
        self.root, self.clock = root, clock
        self.behaviors = behaviors or {}
        self.silent, self.callback, self.payload = silent, callback, payload
        self.calls = []

    def __call__(self, argv, **kwargs):
        index = len(self.calls)
        self.calls.append((list(argv), kwargs))
        behavior = self.behaviors.get(index, 0)
        if isinstance(behavior, BaseException):
            raise behavior
        env = kwargs['env']
        if not self.silent:
            out = self.root / 'smoketest_logs'
            path = out / (env['TL_STAMP'] + '_' + env['TL_LOGNAME'] + '_nogit.txt')
            with path.open('a', encoding='utf-8') as stream:
                if '--' in argv:
                    child = argv[argv.index('--') + 1:]
                    stream.write('[runlog] cmd=' + ' '.join(child) + '\n')
                else:
                    stream.write('[tool] instrumentation contract smoke test\n')
                stream.write(self.payload)
                if behavior != 'timeout':
                    stream.write('[runlog] 종료코드 ' + str(behavior) + ' 소요0분\n')
        if self.callback is not None:
            self.callback(index, argv, kwargs)
        return FakeProcess(self.clock, code=behavior if type(behavior) is int else 0,
                           hang=behavior == 'timeout')


class TemporaryRepo(unittest.TestCase):
    def setUp(self):
        # Virtual process tests deliberately exercise the engine beneath its
        # production dependency HOLD. This never authorizes a real child.
        dependency = mock.patch.object(smoke, 'FULL_EXECUTION_DEPENDENCY_HOLD', None)
        dependency.start()
        self.addCleanup(dependency.stop)
        self.temp = tempfile.TemporaryDirectory(prefix='codex_smoke_fixture_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clock = Clock()
        self.signals = FakeSignals()
        self.sid = 'fixture_session'
        self.write(smoke.CANONICAL_SOURCE, BAT)
        for name in (smoke.NEW_DRIVER, smoke.CONTRACT_MODULE, CODEX_CHECKER,
                     'scripts/runlog.py', 'scripts/smoke_module.py',
                     'scripts/summarize_smoke.py', 'scripts/check_smoke.py',
                     'scripts/check_handoff.py', 'scripts/smoke_diag_contract.tsv',
                     'run100m.py'):
            self.write(name, '# bounded fake source: ' + name + '\n')

    def write(self, rel, value):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding='utf-8')
        return path

    def report(self):
        return json.loads(smoke.destinations(self.root, self.sid)['report'].read_text(encoding='utf-8'))

    def full(self, *, behaviors=None, silent=False, callback=None, payload='fixture output\n',
             wall=90., deadline=None, launcher=None, stop_callback=None):
        launcher = launcher or FakeLauncher(self.root, self.clock, behaviors=behaviors,
                                             silent=silent, callback=callback, payload=payload)

        def stop(process, expires, clock):
            if process.returncode is None:
                process.returncode = 130
            process.hang = False
            return ['MOCK_SIGINT_PROCESS_GROUP', 'GROUP_QUIESCENT']

        with self.signals.patches(), \
                mock.patch.object(smoke, 'owned_group_alive', return_value=False), \
                mock.patch.object(smoke, 'stop_process_group', side_effect=stop_callback or stop), \
                mock.patch.object(smoke.subprocess, 'Popen', side_effect=AssertionError('REAL CHILD FORBIDDEN')), \
                redirect_stdout(io.StringIO()):
            code = smoke.full(
                self.root, self.sid, deadline or self.clock.start + timedelta(hours=1),
                wall, clock=self.clock.tick, now=self.clock.now, sleep=self.clock.sleep,
                process_factory=launcher)
        return code, launcher


class PlanTests(TemporaryRepo):
    def test_exact_two_substitutions_and_unchanged_training(self):
        target, original, adapted, edits = smoke.build_plan(self.root, self.sid)
        self.assertEqual([e['kind'] for e in edits],
                         ['codex_document_checker', 'isolated_field_log_path'])
        self.assertEqual(len(original), 5)
        self.assertEqual([a.kind for a in adapted], ['run', 'run', 'sleep', 'run', 'run'])
        training = next(i for i, a in enumerate(original) if 'run100m.py' in a.argv)
        self.assertEqual(original[training].argv, adapted[training].argv)
        self.assertIn(CODEX_CHECKER, adapted[1].argv)
        self.assertEqual(list(adapted[-1].argv[-5:]),
                         [smoke.NEW_DRIVER, '--mode', 'contract', '--session-id', self.sid])
        self.assertEqual(target['log_name'], 'smoke_codex_' + self.sid)

    def test_check_has_no_children_or_synthetic_snapshot_or_writes(self):
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*'))
        with mock.patch.object(smoke.subprocess, 'Popen') as child, \
                mock.patch.object(smoke, 'original_snapshot') as original, \
                redirect_stdout(io.StringIO()) as output:
            self.assertEqual(smoke.check(self.root, self.sid, 321), 0)
        child.assert_not_called()
        original.assert_not_called()
        self.assertEqual(before, sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*')))
        data = json.loads(output.getvalue().split(' ', 1)[1])
        self.assertEqual(data['max_wall_sec'], 321)
        self.assertEqual(data['model_execution'], 'NOT_RUN')
        self.assertEqual(data['profile_id'], 'codex_isolated_smoke_v1')
        self.assertEqual(data['action_count'], 5)
        self.assertEqual(data['child_count'], 3)
        self.assertEqual(data['training_count'], 1)

    def test_missing_one_approved_substitution_is_not_silently_accepted(self):
        self.write(smoke.CANONICAL_SOURCE, BAT.replace('scripts\\check_handoff.py', 'scripts\\check_links.py'))
        with self.assertRaises(ValueError):
            smoke.build_plan(self.root, self.sid)

    def test_safe_session_names(self):
        for value in ('', '../old', '/tmp/other', 'nested/name', 'a.b', 'a\\b', 'x' * 65):
            with self.subTest(value=value), self.assertRaises(ValueError):
                smoke.build_plan(self.root, value)

    def test_action_manifest_is_the_adapted_canonical_dataclass(self):
        target, original, actual, edits = smoke.build_plan(self.root, self.sid)
        data = smoke.metadata(self.root, self.sid, target, original, actual, edits)
        self.assertEqual(data['action_manifest'], [smoke.asdict(a) for a in actual])
        self.assertEqual(data['raw_log_directory'], 'smoketest_logs')


class PathAndSnapshotTests(TemporaryRepo):
    def test_snapshot_only_original_synthetic_whitelist(self):
        selected = ('runs/ckpt/tiny_synthetic_2M_sm_fixture.pt',
                    'runs/logs/tiny_synthetic_2M_sm_fixture.json',
                    'data_cache/synthetic_fixture/train.bin',
                    'data_cache/synthetic_fixture/val.bin',
                    'data_cache/synthetic_fixture/meta.json')
        for name in selected:
            self.write(name, 'FAKE ONLY:' + name)
        for name in ('runs/ckpt/private.pt', 'runs/logs/private.json',
                     'data_cache/private/train.bin', 'datasets/TinyDataset/private.json',
                     'HF/private/model.pt'):
            self.write(name, 'NEVER READ')
        real_digest = smoke.digest
        observed = []

        def restricted(path, **kwargs):
            rel = path.relative_to(self.root).as_posix()
            self.assertIn(rel, selected)
            observed.append(rel)
            return real_digest(path, **kwargs)

        with mock.patch.object(smoke, 'digest', side_effect=restricted):
            snapshot = smoke.original_snapshot(self.root)
        self.assertEqual(set(snapshot), set(selected))
        self.assertEqual(set(observed), set(selected))
        self.assertTrue(all(len(x) == 64 for x in snapshot.values()))

    def test_snapshot_final_file_link_rejected_before_digest(self):
        target = self.write('private/secret', 'FAKE PRIVATE')
        folder = self.root / 'runs/ckpt'
        folder.mkdir(parents=True)
        (folder / 'tiny_synthetic_bad.pt').symlink_to(target)
        with mock.patch.object(smoke, 'digest') as digest, self.assertRaises(smoke.SafetyError):
            smoke.original_snapshot(self.root)
        digest.assert_not_called()

    def test_snapshot_parent_link_rejected_before_enumeration(self):
        target = self.root / 'fake_other'
        target.mkdir()
        (self.root / 'runs').mkdir()
        (self.root / 'runs/ckpt').symlink_to(target, target_is_directory=True)
        with mock.patch.object(smoke, 'digest') as digest, self.assertRaises(smoke.SafetyError):
            smoke.original_snapshot(self.root)
        digest.assert_not_called()

    def test_snapshot_expired_even_if_empty(self):
        with self.assertRaises(smoke.BudgetExpired):
            smoke.original_snapshot(self.root, expires=0., clock=self.clock.tick)

    def test_new_destination_parent_link_is_rejected(self):
        outside = self.root / 'other'
        outside.mkdir()
        (self.root / 'test_result').mkdir()
        (self.root / 'test_result/evidence').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.full()
        self.assertFalse(any(outside.iterdir()))

    def test_safe_path_rejects_absolute_escape_and_parent(self):
        for path in (self.root / '..' / 'elsewhere', Path('/not-this-root/file'), 'a\\b'):
            with self.subTest(path=path), self.assertRaises(smoke.SafetyError):
                smoke.safe_path(self.root, path)

    def test_write_report_never_overwrites(self):
        path = self.write('out/report.json', 'historical bytes\n')
        with self.assertRaises(FileExistsError):
            smoke.write_report(self.root, path, dict(new=True))
        self.assertEqual(path.read_text(), 'historical bytes\n')

    def test_write_report_link_never_opens_target(self):
        target = self.write('private/original.json', 'old')
        link = self.root / 'report.json'
        link.symlink_to(target)
        with self.assertRaises(smoke.SafetyError):
            smoke.write_report(self.root, link, {})
        self.assertEqual(target.read_text(), 'old')

    def test_raw_link_rejected_without_hash(self):
        target = self.write('private/not_a_log', 'private')
        folder = self.root / 'smoketest_logs'
        folder.mkdir()
        (folder / ('1_smoke_codex_' + self.sid + '_nogit.txt')).symlink_to(target)
        with mock.patch.object(smoke, 'digest') as digest, self.assertRaises(smoke.SafetyError):
            self.full()
        digest.assert_not_called()


class FullReceiptTests(TemporaryRepo):
    def test_success_exact_actions_summary_full_raw_and_one_lf(self):
        code, launch = self.full(payload='unabridged line A\nunabridged line B\n')
        self.assertEqual(code, 0)
        r = self.report()
        self.assertTrue(r['complete'])
        self.assertEqual(r['failed_calls'], 0)
        self.assertEqual(len(r['receipts']), r['action_count'])
        self.assertEqual(len(launch.calls), 5)  # four runlog actions plus summary
        self.assertEqual(r['summary_returncode'], 0)
        self.assertEqual(r['summary_status'], 'COMPLETE')
        target, original, actual, _ = smoke.build_plan(self.root, self.sid)
        expected_runs = [a.argv for a in actual if a.kind == 'run']
        self.assertEqual([c[0] for c in launch.calls[:-1]], [list(a) for a in expected_runs])
        for got, before, after in zip(r['receipts'], original, actual):
            self.assertEqual(got['original_argv'], list(before.argv))
            self.assertEqual(got['executed_argv'], list(after.argv))
            self.assertEqual(got['kind'], after.kind)
            self.assertEqual(got['line'], after.line)
            self.assertEqual(got['status'], 'COMPLETE')
            self.assertEqual(got['returncode'], 0)
        for argv, kwargs in launch.calls:
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertTrue(kwargs['start_new_session'])
            self.assertNotIn('stdout', kwargs)
            self.assertNotIn('stderr', kwargs)
            self.assertNotIn('capture_output', kwargs)
            self.assertEqual(kwargs['cwd'], self.root)
        self.assertEqual(launch.calls[-1][0], r['summary_command'])
        self.assertTrue(r['source_pins_unchanged'])
        self.assertTrue(r['original_synthetic_unchanged'])
        self.assertTrue(r['original_synthetic_before_complete'])
        self.assertTrue(r['original_synthetic_after_complete'])
        raw = (self.root / r['log']).read_bytes()
        self.assertEqual(raw.count(b'unabridged line A'), 5)
        self.assertEqual(raw.count(b'unabridged line B'), 5)
        self.assertEqual(hashlib.sha256(raw).hexdigest().upper(), r['log_sha256'])
        self.assertEqual(len(raw), r['log_bytes'])
        self.assertLess(len(raw), 20_000_000)
        report_bytes = target['report'].read_bytes()
        self.assertTrue(report_bytes.endswith(b'\n'))
        self.assertFalse(report_bytes.endswith(b'\n\n'))

    def test_nonzero_child_continues_but_never_becomes_success(self):
        code, launch = self.full(behaviors={1: 7})
        r = self.report()
        self.assertEqual(code, 1)
        self.assertTrue(r['complete'])  # attempted/finished, not success
        self.assertEqual(r['failed_calls'], 1)
        self.assertEqual(r['receipts'][1]['returncode'], 7)
        self.assertEqual(len(launch.calls), 5)
        self.assertIn(b'\xec\xa2\x85\xeb\xa3\x8c\xec\xbd\x94\xeb\x93\x9c 7', (self.root / r['log']).read_bytes())

    def test_launch_exception_is_unknown_and_stops_after_preserving_raw(self):
        code, launch = self.full(behaviors={1: OSError('fixture process failed')})
        r = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(len(launch.calls), 2)
        self.assertFalse(r['complete'])
        self.assertEqual(r['receipts'][1]['status'], 'TOOL_ERROR')
        self.assertIsNone(r['receipts'][1]['returncode'])
        self.assertIsNone(r['receipts'][1]['process_started'])
        self.assertEqual(r['receipts'][1]['launch_state'], 'UNKNOWN')
        self.assertTrue(r['receipts'][1]['unsafe_process_state'])
        self.assertIn('fixture process failed', r['receipts'][1]['error'])
        self.assertEqual(r['receipts'][3]['status'], 'NOT_RUN')

    def test_interrupt_records_unrun_actions_and_keeps_partial_raw(self):
        code, launch = self.full(behaviors={1: KeyboardInterrupt()})
        r = self.report()
        self.assertEqual(code, 130)
        self.assertEqual(len(launch.calls), 2)
        self.assertTrue(r['interrupted'])
        self.assertEqual([x['status'] for x in r['receipts']],
                         ['COMPLETE', 'INTERRUPTED', 'NOT_RUN', 'NOT_RUN', 'NOT_RUN'])
        self.assertTrue(all(x['returncode'] is None for x in r['receipts'][1:]))
        self.assertEqual(r['summary_status'], 'NOT_RUN')
        self.assertGreater((self.root / r['log']).stat().st_size, 0)

    def test_abnormal_interrupt_leader_stops_remaining_actions_with_started_receipt(self):
        code, launch = self.full(behaviors={1: -int(signal.SIGTERM)})
        r = self.report()
        self.assertEqual(code, 130)
        self.assertEqual(len(launch.calls), 2)
        self.assertEqual(r['receipts'][1]['status'], 'INTERRUPTED')
        self.assertTrue(r['receipts'][1]['process_started'])
        self.assertEqual(r['receipts'][1]['returncode'], -int(signal.SIGTERM))
        self.assertEqual([x['status'] for x in r['receipts'][2:]], ['NOT_RUN'] * 3)
        self.assertEqual(self.signals.handlers, {signal.SIGINT: 'OLD_INT', signal.SIGTERM: 'OLD_TERM'})

    def test_ordinary_failure_cannot_continue_after_unresolved_group_cleanup(self):
        code, launch = self.full(
            behaviors={1: 7}, stop_callback=lambda *a: ['CLEANUP_ERROR:GROUP_STATE_UNRESOLVED'])
        r = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(len(launch.calls), 2)
        self.assertTrue(r['receipts'][1]['unsafe_process_state'])
        self.assertEqual([x['status'] for x in r['receipts'][2:]], ['NOT_RUN'] * 3)

    def test_started_action_state_survives_interrupt_at_helper_return_boundary(self):
        def interrupted(*a, state_sink=None, **k):
            state_sink.update(status='RUNNING', process_started=True, returncode=None)
            raise KeyboardInterrupt('virtual helper return-boundary interrupt')

        with mock.patch.object(smoke, 'run_child', side_effect=interrupted):
            code, _ = self.full()
        r = self.report()
        self.assertEqual(code, 130)
        self.assertEqual(r['receipts'][0]['status'], 'INTERRUPTED')
        self.assertTrue(r['receipts'][0]['process_started'])
        self.assertEqual([x['status'] for x in r['receipts'][1:]], ['NOT_RUN'] * 4)

    def test_started_summary_state_survives_interrupt_at_helper_return_boundary(self):
        child = smoke.run_child

        def interrupted(argv, **kwargs):
            if 'scripts/summarize_smoke.py' in argv:
                kwargs['state_sink'].update(status='RUNNING', process_started=True, returncode=None)
                raise KeyboardInterrupt('virtual summary return-boundary interrupt')
            return child(argv, **kwargs)

        with mock.patch.object(smoke, 'run_child', side_effect=interrupted):
            code, _ = self.full()
        r = self.report()
        self.assertEqual(code, 130)
        self.assertTrue(all(x['status'] == 'COMPLETE' for x in r['receipts']))
        self.assertEqual(r['summary_status'], 'INTERRUPTED')
        self.assertTrue(r['summary_receipt']['process_started'])

    def test_timeout_preserves_actual_stop_returncode_and_unrun_denominator(self):
        code, _ = self.full(behaviors={1: 'timeout'}, wall=8)
        r = self.report()
        self.assertEqual(code, 124)
        self.assertTrue(r['timed_out'])
        self.assertEqual(r['receipts'][1]['status'], 'TIMED_OUT')
        self.assertEqual(r['receipts'][1]['returncode'], 130)  # observed mock process rc
        self.assertEqual(len(r['receipts']), 5)
        self.assertEqual(sum(x['status'] == 'NOT_RUN' for x in r['receipts']), 3)
        self.assertLessEqual(r['whole_sec'], 8)
        self.assertIn('MOCK_SIGINT_PROCESS_GROUP', r['receipts'][1]['termination'])

    def test_canonical_sleep_cannot_escape_wall_budget(self):
        code, launch = self.full(wall=6)
        r = self.report()
        self.assertEqual(code, 124)
        self.assertEqual(len(launch.calls), 2)
        self.assertEqual(r['receipts'][2]['kind'], 'sleep')
        self.assertEqual(r['receipts'][2]['status'], 'TIMED_OUT')
        self.assertIsNone(r['receipts'][2]['returncode'])
        self.assertLessEqual(r['whole_sec'], 6)

    def test_absolute_deadline_caps_larger_requested_budget(self):
        code, _ = self.full(wall=90, deadline=self.clock.start + timedelta(seconds=3))
        r = self.report()
        self.assertEqual(code, 124)
        self.assertLessEqual(r['whole_sec'], 3)
        self.assertEqual(r['max_wall_sec'], 90)

    def test_summary_nonzero_separate_from_canonical_failed_calls(self):
        code, _ = self.full(behaviors={4: 4})
        r = self.report()
        self.assertEqual(code, 1)
        self.assertTrue(r['complete'])
        self.assertEqual(r['failed_calls'], 0)
        self.assertEqual(r['summary_returncode'], 4)

    def test_summary_timeout_not_reported_as_success(self):
        code, _ = self.full(behaviors={4: 'timeout'}, wall=20)
        r = self.report()
        self.assertEqual(code, 124)
        self.assertTrue(all(x['status'] == 'COMPLETE' for x in r['receipts']))
        self.assertEqual(r['summary_status'], 'TIMED_OUT')
        self.assertFalse(r['complete'])

    def test_silent_zero_children_without_raw_are_not_a_success(self):
        code, launch = self.full(silent=True)
        r = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(len(launch.calls), 4)
        self.assertTrue(all(x['returncode'] == 0 for x in r['receipts']))
        self.assertEqual(r['summary_status'], 'NOT_RUN')
        self.assertIsNone(r['log'])
        self.assertFalse(r['complete'])

    def test_source_change_is_a_negative_receipt_without_restoring_it(self):
        def change(index, argv, kwargs):
            if index == 2:
                self.write('run100m.py', '# changed fixture source\n')
        code, _ = self.full(callback=change)
        r = self.report()
        self.assertEqual(code, 1)
        self.assertFalse(r['source_pins_unchanged'])
        self.assertNotEqual(r['source_pins_before'], r['source_pins_after'])
        self.assertEqual((self.root / 'run100m.py').read_text(), '# changed fixture source\n')

    def test_original_synthetic_change_preserved_and_not_success(self):
        path = self.write('runs/ckpt/tiny_synthetic_2M_old.pt', 'FAKE OLD')

        def change(index, argv, kwargs):
            if index == 2:
                path.write_text('FAKE CHANGED', encoding='utf-8')
        code, _ = self.full(callback=change)
        r = self.report()
        self.assertEqual(code, 1)
        self.assertFalse(r['original_synthetic_unchanged'])
        self.assertEqual(path.read_text(), 'FAKE CHANGED')

    def test_original_synthetic_addition_is_detected(self):
        def change(index, argv, kwargs):
            if index == 2:
                self.write('runs/logs/tiny_synthetic_new.json', '{}')
        code, _ = self.full(callback=change)
        r = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(r['original_synthetic_before'], {})
        self.assertEqual(len(r['original_synthetic_after']), 1)

    def test_snapshot_exception_before_actions_keeps_negative_receipt(self):
        with mock.patch.object(smoke, 'original_snapshot', side_effect=OSError('fixture snapshot failure')):
            code, launch = self.full()
        r = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(launch.calls, [])
        self.assertTrue(all(x['status'] == 'NOT_RUN' for x in r['receipts']))
        self.assertTrue(all(x['returncode'] is None for x in r['receipts']))
        self.assertFalse(r['original_synthetic_before_complete'])

    def test_duplicate_raw_stops_and_keeps_both_files(self):
        def duplicate(index, argv, kwargs):
            if index == 0:
                self.write('smoketest_logs/duplicate_smoke_codex_' + self.sid + '_other.txt', 'second raw')
        code, launch = self.full(callback=duplicate)
        r = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(len(launch.calls), 1)
        self.assertEqual(len(r['raw_logs']), 2)
        self.assertTrue(all((self.root / p).exists() for p in r['raw_logs']))
        self.assertFalse(r['complete'])

    def test_twenty_mb_guard_preserves_full_raw_without_truncation(self):
        with mock.patch.object(smoke, 'MAX_LOG_BYTES', 100):
            code, launch = self.full(payload='X' * 250 + '\n')
        r = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(len(launch.calls), 1)
        self.assertFalse(r['complete'])
        self.assertIn(b'X' * 250, (self.root / r['log']).read_bytes())
        self.assertGreater(r['log_bytes'], 100)

    def test_reusing_completed_runtime_or_evidence_refuses_no_overwrite(self):
        self.full()
        before = smoke.destinations(self.root, self.sid)['report'].read_bytes()
        with mock.patch.object(smoke, 'original_snapshot') as snapshot, self.assertRaises(FileExistsError):
            self.full()
        snapshot.assert_not_called()
        self.assertEqual(smoke.destinations(self.root, self.sid)['report'].read_bytes(), before)

    def test_preexisting_raw_refuses_before_namespace_reservation(self):
        self.write('smoketest_logs/old_smoke_codex_' + self.sid + '_nogit.txt', 'historical raw')
        with mock.patch.object(smoke, 'original_snapshot') as snapshot, self.assertRaises(FileExistsError):
            self.full()
        snapshot.assert_not_called()
        self.assertFalse(smoke.destinations(self.root, self.sid)['runtime'].exists())

    def test_expired_deadline_creates_nothing_and_starts_nothing(self):
        with redirect_stdout(io.StringIO()):
            code, launch = self.full(deadline=self.clock.start - timedelta(seconds=1))
        self.assertEqual(code, 8)
        self.assertEqual(launch.calls, [])
        self.assertFalse(smoke.destinations(self.root, self.sid)['runtime'].exists())

    def test_signal_handler_restored_after_full(self):
        before = signal.getsignal(signal.SIGTERM)
        self.full()
        self.assertEqual(signal.getsignal(signal.SIGTERM), before)

    def test_signal_install_failure_leaves_negative_receipt_and_no_children(self):
        with mock.patch.object(self.signals, 'handler', side_effect=ValueError('not main thread')):
            code, launch = self.full()
        self.assertEqual(code, 1)
        self.assertEqual(launch.calls, [])
        self.assertTrue(all(r['status'] == 'NOT_RUN' for r in self.report()['receipts']))

    def test_full_restores_virtual_handlers_even_when_report_write_fails(self):
        initial = dict(self.signals.handlers)
        with mock.patch.object(smoke, 'write_report', side_effect=OSError('fixture write failure')):
            with self.assertRaises(OSError):
                self.full()
        self.assertEqual(self.signals.handlers, initial)
        self.assertEqual(self.signals.mask, set())
        self.assertEqual(smoke._OWNED_GROUPS, {})

    def test_full_restores_virtual_handlers_after_snapshot_exception(self):
        initial = dict(self.signals.handlers)
        with mock.patch.object(smoke, 'original_snapshot', side_effect=[{}, OSError('after snapshot')]):
            code, _ = self.full()
        self.assertEqual(code, 1)
        self.assertEqual(self.signals.handlers, initial)
        self.assertEqual(self.signals.mask, set())


class EnvironmentAndContractTests(TemporaryRepo):
    def test_offline_controls_fixed_stamp_and_no_secrets_in_receipt(self):
        target = smoke.destinations(self.root, self.sid)
        env = smoke.environment(target['runtime'], target['log_name'], '20310403100000',
                                {'SECRET_API_TOKEN': 'not-for-report', 'TL_STAMP': 'old',
                                 'WANDB_MODE': 'online', 'CUDA_VISIBLE_DEVICES': ''})
        public = smoke.public_environment(env)
        self.assertEqual(env['SECRET_API_TOKEN'], 'not-for-report')
        self.assertNotIn('SECRET_API_TOKEN', public)
        self.assertEqual(public['TL_STAMP'], '20310403100000')
        self.assertEqual(public['TL_OUTDIR'], 'smoketest_logs')
        self.assertEqual(public['TL_WANDB_AUTO'], '0')
        self.assertEqual(public['WANDB_MODE'], 'disabled')
        self.assertEqual(public['HF_HUB_OFFLINE'], '1')
        self.assertEqual(public['HF_DATASETS_OFFLINE'], '1')
        self.assertEqual(public['TL_NOPAUSE'], '1')
        self.assertEqual(public['TINYLM_DIR'], str(target['runtime']))

    def test_environment_and_stamp_identical_for_all_canonical_and_summary_calls(self):
        _, launch = self.full()
        observed = [smoke.public_environment(kwargs['env']) for _, kwargs in launch.calls]
        self.assertTrue(all(x == observed[0] for x in observed))
        self.assertEqual(observed[0], self.report()['environment'])

    def test_receipt_allowlist_does_not_claim_child_credential_isolation(self):
        with mock.patch.dict(os.environ, {'FAKE_PRIVATE_CREDENTIAL': 'fixture-secret'}):
            _, launcher = self.full()
        r = self.report()
        self.assertTrue(all(k['env']['FAKE_PRIVATE_CREDENTIAL'] == 'fixture-secret'
                            for _, k in launcher.calls))
        self.assertNotIn('FAKE_PRIVATE_CREDENTIAL', r['environment'])
        self.assertNotIn('fixture-secret', json.dumps(r))
        self.assertIn('inherits the full parent environment', r['environment_scope'])
        self.assertIn('not a security sandbox', r['environment_scope'])

    def test_contract_reuses_original_main_and_restores_globals(self):
        from scripts import check_smoke
        target = smoke.destinations(self.root, self.sid)
        path = target['runtime'] / 'runs/logs'
        path.mkdir(parents=True)
        (path / 'tiny_synthetic_2M_sm_fixture.json').write_text('{}', encoding='utf-8')
        old_logs, old_argv = check_smoke.LOGS, sys.argv

        def checker():
            self.assertEqual(check_smoke.LOGS, path)
            self.assertEqual(sys.argv, [smoke.NEW_DRIVER])
            return 17

        with mock.patch.object(check_smoke, 'main', side_effect=checker) as call:
            self.assertEqual(smoke.contract(self.root, self.sid, {'TINYLM_DIR': str(target['runtime'])}), 17)
        call.assert_called_once_with()
        self.assertEqual(check_smoke.LOGS, old_logs)
        self.assertIs(sys.argv, old_argv)

    def test_contract_wrong_runtime_never_calls_original_checker(self):
        from scripts import check_smoke
        with mock.patch.object(check_smoke, 'main') as call, self.assertRaises(smoke.SafetyError):
            smoke.contract(self.root, self.sid, {'TINYLM_DIR': str(self.root)})
        call.assert_not_called()

    def test_contract_linked_json_rejected_before_original_checker(self):
        from scripts import check_smoke
        target = smoke.destinations(self.root, self.sid)
        path = target['runtime'] / 'runs/logs'
        path.mkdir(parents=True)
        fake = self.write('fake_protected_source.json', '{}')
        (path / 'tiny_synthetic_2M_sm_bad.json').symlink_to(fake)
        with mock.patch.object(check_smoke, 'main') as call, self.assertRaises(smoke.SafetyError):
            smoke.contract(self.root, self.sid, {'TINYLM_DIR': str(target['runtime'])})
        call.assert_not_called()

    def test_contract_restores_globals_on_original_exception(self):
        from scripts import check_smoke
        target = smoke.destinations(self.root, self.sid)
        (target['runtime'] / 'runs/logs').mkdir(parents=True)
        before, argv = check_smoke.LOGS, sys.argv
        with mock.patch.object(check_smoke, 'main', side_effect=ValueError('fixture')):
            with self.assertRaises(ValueError):
                smoke.contract(self.root, self.sid, {'TINYLM_DIR': str(target['runtime'])})
        self.assertEqual(check_smoke.LOGS, before)
        self.assertIs(sys.argv, argv)


class CliAndTerminationTests(TemporaryRepo):
    def test_deadline_parser_requires_aware_time_and_accepts_offsets(self):
        for value in ('2031-04-03T12:00:00', 'not-time', None):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                smoke.aware_deadline(value)
        self.assertEqual(smoke.aware_deadline('2031-04-03T12:00:00+09:00'),
                         datetime(2031, 4, 3, 3, tzinfo=timezone.utc))
        self.assertEqual(smoke.aware_deadline('2031-04-03T03:00:00Z').utcoffset(), timedelta(0))

    def test_wall_parser_rejects_unbounded_nan_zero_and_negative(self):
        for value in ('nan', 'inf', '0', '-1', '1800.1', 'not-number'):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                smoke.wall_seconds(value)
        self.assertEqual(smoke.wall_seconds('1800'), 1800)

    def test_full_requires_execute_and_deadline_before_any_plan_or_assets(self):
        for args in (['--mode', 'full', '--session-id', self.sid],
                     ['--mode', 'full', '--session-id', self.sid, '--execute'],
                     ['--mode', 'full', '--session-id', self.sid, '--deadline-utc', '2031-04-03T10:00:00Z']):
            with self.subTest(args=args), mock.patch.object(smoke, 'build_plan') as plan, \
                    redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_:
                smoke.main(args)
            self.assertEqual(exit_.exception.code, 2)
            plan.assert_not_called()

    def test_production_dependency_hold_precedes_plan_paths_or_any_child(self):
        with mock.patch.object(smoke, 'FULL_EXECUTION_DEPENDENCY_HOLD', 'registry unverified'), \
                mock.patch.object(smoke, 'build_plan') as plan, \
                mock.patch.object(Path, 'mkdir') as mkdir, \
                mock.patch.object(smoke.subprocess, 'Popen') as process, \
                redirect_stdout(io.StringIO()) as output:
            code = smoke.full(self.root, self.sid,
                              self.clock.start + timedelta(hours=1), 1200)
        self.assertEqual(code, 8)
        self.assertIn('[CODEX_SMOKE_HOLD]', output.getvalue())
        plan.assert_not_called()
        mkdir.assert_not_called()
        process.assert_not_called()

    def test_main_full_keeps_production_dependency_hold_and_creates_no_namespace(self):
        with mock.patch.object(smoke, 'ROOT', self.root), \
                mock.patch.object(smoke, 'FULL_EXECUTION_DEPENDENCY_HOLD', 'registry unverified'), \
                mock.patch.object(smoke, 'build_plan') as plan, \
                mock.patch.object(smoke.subprocess, 'Popen') as process, \
                redirect_stdout(io.StringIO()):
            code = smoke.main(['--mode', 'full', '--session-id', self.sid,
                '--execute', '--deadline-utc', '2031-04-03T12:00:00Z'])
        self.assertEqual(code, 8)
        plan.assert_not_called()
        process.assert_not_called()
        self.assertFalse(smoke.destinations(self.root, self.sid)['runtime'].exists())

    def test_main_modes_dispatch_exactly_and_session_required(self):
        with mock.patch.object(smoke, 'ROOT', self.root), \
                mock.patch.object(smoke, 'check', return_value=11) as check, \
                mock.patch.object(smoke, 'contract', return_value=12) as contract, \
                mock.patch.object(smoke, 'full', return_value=13) as full:
            self.assertEqual(smoke.main(['--mode', 'check', '--session-id', self.sid, '--max-wall-sec', '321']), 11)
            check.assert_called_once_with(self.root, self.sid, 321.)
            self.assertEqual(smoke.main(['--mode', 'contract', '--session-id', self.sid]), 12)
            contract.assert_called_once_with(self.root, self.sid)
            deadline = '2031-04-03T12:00:00Z'
            self.assertEqual(smoke.main(['--mode', 'full', '--session-id', self.sid,
                                         '--execute', '--deadline-utc', deadline]), 13)
            full.assert_called_once_with(self.root, self.sid, smoke.aware_deadline(deadline), 1200)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
            smoke.main(['--mode', 'check'])
        self.assertEqual(e.exception.code, 2)

    def test_execute_rejected_in_read_only_modes(self):
        for mode in ('check', 'contract'):
            with self.subTest(mode=mode), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                smoke.main(['--mode', mode, '--session-id', self.sid, '--execute'])

    def test_absolute_entry_help_from_unrelated_cwd_has_no_asset_or_child_work(self):
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            with mock.patch.object(sys, 'argv', [str(ROOT / smoke.NEW_DRIVER), '--help']), \
                    mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('NO CHILD')), \
                    redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as e:
                runpy.run_path(str(ROOT / smoke.NEW_DRIVER), run_name='__main__')
            self.assertEqual(e.exception.code, 0)
        finally:
            os.chdir(previous)

    def test_full_rejects_naive_deadline_even_for_direct_api(self):
        with self.assertRaises(ValueError):
            smoke.full(self.root, self.sid, datetime(2031, 4, 3), 90)

    def test_process_group_termination_has_grace_then_kill(self):
        child = mock.Mock()
        child.pid = 123456789
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired('fake', .1), -9]
        smoke._register_owned(child, start_new_session=True)
        self.addCleanup(smoke._forget_owned, child)

        def signal_group(pgid, sig):
            if sig == 0:
                raise ProcessLookupError('virtual group gone')

        with self.signals.patches(), mock.patch.object(smoke.os, 'killpg', side_effect=signal_group) as kill:
            notes = smoke.stop_process_group(child, 2., lambda: 0.)
        self.assertEqual([c for c in kill.call_args_list if c.args[1] != 0],
                         [mock.call(child.pid, signal.SIGINT), mock.call(child.pid, signal.SIGKILL)])
        self.assertEqual(notes, ['SIGINT_PROCESS_GROUP', 'SIGKILL_PROCESS_GROUP', 'GROUP_QUIESCENT'])

    def test_interrupt_cleanup_kills_group_even_if_wrapper_exits_during_grace(self):
        child = mock.Mock()
        child.pid = 123456789
        child.poll.side_effect = [None, 130]
        child.wait.return_value = 130
        smoke._register_owned(child, start_new_session=True)
        self.addCleanup(smoke._forget_owned, child)

        def signal_group(pgid, sig):
            if sig == 0:
                raise ProcessLookupError('virtual group gone')

        with self.signals.patches(), mock.patch.object(smoke.os, 'killpg', side_effect=signal_group) as kill:
            notes = smoke.stop_process_group(child, 2., lambda: 0.)
        self.assertEqual([c for c in kill.call_args_list if c.args[1] != 0],
                         [mock.call(child.pid, signal.SIGINT), mock.call(child.pid, signal.SIGKILL)])
        self.assertEqual(child.wait.call_count, 1)
        self.assertEqual(notes, ['SIGINT_PROCESS_GROUP', 'SIGKILL_PROCESS_GROUP', 'GROUP_QUIESCENT'])

    def test_unresolved_process_cleanup_is_not_marked_safe_to_continue(self):
        child = mock.Mock()
        child.pid = 123456785
        child.wait.side_effect = OSError('fixture wait failure')
        child.poll.return_value = None
        with self.signals.patches(), \
                mock.patch.object(smoke, 'stop_process_group', side_effect=OSError('fixture cleanup failure')):
            receipt = smoke.run_child(
                ['MOCK'], root=self.root, env={}, work_expires=5., expires=6.,
                clock=self.clock.tick, monitor=lambda: None,
                process_factory=lambda *a, **k: child)
        self.assertEqual(receipt['status'], 'TOOL_ERROR')
        self.assertTrue(receipt['process_started'])
        self.assertTrue(receipt['unsafe_process_state'])
        self.assertIsNone(receipt['returncode'])


class CleanupRevisionTests(TemporaryRepo):
    def invoke(self, child, *, pending_on_kill=False, repeated=False,
               persistent=False, signals=None):
        signals = self.signals if signals is None else signals
        state = dict(alive=True, calls=[], int_attempts=0, kill_attempts=0)

        def signal_group(pgid, sig):
            state['calls'].append((pgid, sig))
            self.assertEqual(pgid, child.pid)
            if sig == 0:
                if not state['alive']:
                    raise ProcessLookupError('virtual group gone')
                return
            if sig == signal.SIGINT:
                state['int_attempts'] += 1
                if repeated:
                    raise KeyboardInterrupt('virtual repeated SIGINT during teardown')
            if sig == signal.SIGKILL:
                state['kill_attempts'] += 1
                if repeated and state['kill_attempts'] == 1:
                    raise KeyboardInterrupt('virtual interrupt at final kill')
                if not persistent:
                    state['alive'] = False
                if pending_on_kill:
                    signals.pending.add(signal.SIGTERM)

        with signals.patches(), \
                mock.patch.object(smoke.os, 'killpg', side_effect=signal_group), \
                mock.patch.object(smoke.time, 'sleep', side_effect=self.clock.sleep), \
                mock.patch.object(smoke.subprocess, 'Popen', side_effect=AssertionError('NO REAL CHILD')):
            result = smoke.run_child(
                ['MOCK'], root=self.root, env={}, work_expires=10., expires=11.,
                clock=self.clock.tick, monitor=lambda: None,
                process_factory=lambda *a, **k: child)
        self.assertEqual(smoke._OWNED_GROUPS, {})
        return result, state

    def test_signal_exit_leaders_are_interrupted_and_descendants_are_cleaned(self):
        for code in (-int(signal.SIGINT), -int(signal.SIGTERM), 130, 143):
            with self.subTest(code=code):
                child = FakeProcess(self.clock, code=code)
                r, state = self.invoke(child)
                self.assertEqual(r['status'], 'INTERRUPTED')
                self.assertEqual(r['returncode'], code)
                self.assertTrue(r['process_started'])
                self.assertFalse(r['unsafe_process_state'])
                self.assertFalse(state['alive'])
                self.assertIn((child.pid, signal.SIGKILL), state['calls'])
                self.assertIn('GROUP_QUIESCENT', r['termination'])

    def test_ordinary_nonzero_leader_only_continues_after_verified_quiescence(self):
        child = FakeProcess(self.clock, code=7)
        r, state = self.invoke(child)
        self.assertEqual(r['status'], 'COMPLETE')
        self.assertEqual(r['returncode'], 7)
        self.assertFalse(r['unsafe_process_state'])
        self.assertFalse(state['alive'])
        self.assertIn('GROUP_QUIESCENT', r['termination'])

    def test_successful_leader_with_background_descendant_is_not_positive(self):
        child = FakeProcess(self.clock, code=0)
        r, state = self.invoke(child)
        self.assertEqual(r['status'], 'TOOL_ERROR')
        self.assertEqual(r['returncode'], 0)
        self.assertIn('surviving owned group', r['error'])
        self.assertFalse(state['alive'])
        self.assertIn((child.pid, 0), state['calls'])
        self.assertIn((child.pid, signal.SIGKILL), state['calls'])

    def test_clean_zero_leader_is_probed_but_no_interrupt_signal_is_sent(self):
        child = FakeProcess(self.clock, code=0)
        with self.signals.patches(), \
                mock.patch.object(smoke.os, 'killpg', side_effect=ProcessLookupError('gone')) as kill:
            r = smoke.run_child(
                ['MOCK'], root=self.root, env={}, work_expires=10., expires=11.,
                clock=self.clock.tick, monitor=lambda: None,
                process_factory=lambda *a, **k: child)
        self.assertEqual(r['status'], 'COMPLETE')
        self.assertEqual(kill.call_args_list, [mock.call(child.pid, 0)])
        self.assertEqual(self.signals.mask, set())
        self.assertEqual(smoke._OWNED_GROUPS, {})

    def test_repeated_interrupts_still_kill_reap_and_return_started_receipt(self):
        class FirstInterrupt(FakeProcess):
            def __init__(self, clock):
                super().__init__(clock)
                self.waits = 0

            def wait(self, timeout=None):
                self.waits += 1
                if self.waits <= 2:
                    raise KeyboardInterrupt('virtual first/grace interrupt')
                self.returncode = -9
                return -9

        child = FirstInterrupt(self.clock)
        r, state = self.invoke(child, repeated=True, pending_on_kill=True)
        self.assertEqual(r['status'], 'INTERRUPTED')
        self.assertTrue(r['process_started'])
        self.assertTrue(r['interrupted_during_cleanup'])
        self.assertFalse(r['unsafe_process_state'])
        self.assertFalse(state['alive'])
        self.assertGreaterEqual(state['kill_attempts'], 2)
        self.assertIn('GROUP_QUIESCENT', r['termination'])
        self.assertTrue(any(x.startswith('PENDING_INTERRUPT:') for x in r['termination']))
        self.assertTrue(any('MASK_RESTORE_DELIVERY' in x for x in r['termination']))
        self.assertEqual(self.signals.mask, set())
        self.assertEqual(self.signals.pending, set())
        self.assertEqual(self.signals.handlers, {signal.SIGINT: 'OLD_INT', signal.SIGTERM: 'OLD_TERM'})
        self.assertLessEqual(r['cleanup_duration_sec'], 5.)

    def test_prior_mask_and_already_blocked_pending_signal_are_preserved(self):
        state = FakeSignals(mask={signal.SIGTERM})
        state.pending.add(signal.SIGTERM)
        child = FakeProcess(self.clock, code=7)
        r, _ = self.invoke(child, signals=state)
        self.assertEqual(state.mask, {signal.SIGTERM})
        self.assertEqual(state.pending, {signal.SIGTERM})
        self.assertEqual(r['status'], 'INTERRUPTED')
        self.assertTrue(r['interrupted_during_cleanup'])

    def test_interrupt_after_mask_block_takes_effect_restores_prior_mask(self):
        original = self.signals.pthread_sigmask
        raised = [False]

        def mask(operation, values):
            before = original(operation, values)
            if operation == signal.SIG_BLOCK and values and not raised[0]:
                raised[0] = True
                raise KeyboardInterrupt('virtual interrupt AFTER mask update')
            return before

        child = FakeProcess(self.clock, code=7)
        with mock.patch.object(self.signals, 'pthread_sigmask', side_effect=mask):
            r, _ = self.invoke(child)
        self.assertEqual(self.signals.mask, set())
        self.assertEqual(r['status'], 'INTERRUPTED')
        self.assertFalse(r['unsafe_process_state'])

    def test_group_that_cannot_be_confirmed_quiescent_is_bounded_and_unsafe(self):
        child = FakeProcess(self.clock, code=7)
        r, state = self.invoke(child, persistent=True)
        self.assertTrue(state['alive'])
        self.assertTrue(r['unsafe_process_state'])
        self.assertIn('CLEANUP_ERROR:GROUP_STATE_UNRESOLVED', r['termination'])
        self.assertLessEqual(r['cleanup_duration_sec'], 5.)
        self.assertEqual(self.signals.mask, set())

    def test_unsafe_and_current_group_ids_are_rejected_before_any_signal(self):
        for pgid in (-1, 0, 1, True, os.getpid(), os.getpgrp()):
            child = mock.Mock()
            child.pid = pgid
            with self.subTest(pgid=pgid), mock.patch.object(smoke.os, 'killpg') as kill:
                with self.assertRaises(smoke.SafetyError):
                    smoke._register_owned(child, start_new_session=True)
                with self.assertRaises(smoke.SafetyError):
                    smoke.stop_process_group(child, 2., self.clock.tick)
                kill.assert_not_called()

    def test_unregistered_or_different_process_object_is_never_signalled(self):
        child = FakeProcess(self.clock)
        other = FakeProcess(self.clock)
        with mock.patch.object(smoke.os, 'killpg') as kill:
            with self.assertRaises(smoke.SafetyError):
                smoke.stop_process_group(child, 2., self.clock.tick)
            smoke._register_owned(child, start_new_session=True)
            try:
                with self.assertRaises(smoke.SafetyError):
                    smoke.stop_process_group(other, 2., self.clock.tick)
            finally:
                smoke._forget_owned(child)
            kill.assert_not_called()

    def test_owned_registration_requires_a_new_session(self):
        child = FakeProcess(self.clock)
        with self.assertRaises(smoke.SafetyError):
            smoke._register_owned(child, start_new_session=False)
        self.assertEqual(smoke._OWNED_GROUPS, {})


class SetupBudgetRevisionTests(TemporaryRepo):
    def test_plan_time_is_inside_budget_before_any_namespace_or_child(self):
        parse = smoke.parse_smoke_module

        def slow_plan(*a, **k):
            self.clock.value += 2.
            return parse(*a, **k)

        with mock.patch.object(smoke, 'parse_smoke_module', side_effect=slow_plan), \
                mock.patch.object(smoke, 'execution_source_pins') as pins:
            code, launch = self.full(wall=1.)
        self.assertEqual(code, 124)
        self.assertEqual(launch.calls, [])
        pins.assert_not_called()
        self.assertFalse(smoke.destinations(self.root, self.sid)['runtime'].exists())

    def test_absolute_deadline_is_rechecked_after_planning(self):
        parse = smoke.parse_smoke_module

        def wall_jump(*a, **k):
            result = parse(*a, **k)
            self.clock.start += timedelta(hours=2)
            return result

        with mock.patch.object(smoke, 'parse_smoke_module', side_effect=wall_jump):
            code, launch = self.full(wall=90., deadline=self.clock.start + timedelta(hours=1))
        self.assertEqual(code, 124)
        self.assertEqual(launch.calls, [])
        self.assertEqual(self.clock.value, 0.)
        self.assertFalse(smoke.destinations(self.root, self.sid)['runtime'].exists())

    def test_budget_expiring_between_reservations_preserves_partial_namespace(self):
        mkdir = Path.mkdir
        runtime = smoke.destinations(self.root, self.sid)['runtime']

        def consume(path, *a, **k):
            result = mkdir(path, *a, **k)
            if path == runtime:
                self.clock.value += 2.
            return result

        with mock.patch.object(Path, 'mkdir', autospec=True, side_effect=consume):
            code, launch = self.full(wall=1.)
        self.assertEqual(code, 124)
        self.assertEqual(launch.calls, [])
        self.assertTrue(runtime.is_dir())
        self.assertFalse(smoke.destinations(self.root, self.sid)['report'].exists())

    def test_both_source_pin_phases_receive_live_guard_callbacks(self):
        pins = smoke.execution_source_pins(self.root)
        observed = []

        def source(root, *, guard=None):
            self.assertIsNotNone(guard)
            guard()
            observed.append(guard)
            return dict(pins)

        with mock.patch.object(smoke, 'execution_source_pins', side_effect=source):
            code, _ = self.full()
        self.assertEqual(code, 0)
        self.assertEqual(len(observed), 2)
        self.assertEqual(self.report()['source_pins_before'], pins)
        self.assertEqual(self.report()['source_pins_after'], pins)

    def test_expiry_during_after_pin_phase_stops_hashing_and_keeps_raw(self):
        pins = smoke.execution_source_pins(self.root)
        phases = []
        calls = [0]

        def bounded_source(root, *, guard=None):
            calls[0] += 1
            if calls[0] == 2:
                self.clock.value += 100.
            guard()
            phases.append('hashed')
            return dict(pins)

        with mock.patch.object(smoke, 'execution_source_pins', side_effect=bounded_source):
            code, _ = self.full(wall=90.)
        r = self.report()
        self.assertEqual(code, 124)
        self.assertEqual(phases, ['hashed'])
        self.assertEqual(r['source_pins_after'], {})
        self.assertTrue(r['timed_out'])
        self.assertIsNone(r['log_sha256'])
        self.assertGreater((self.root / r['log']).stat().st_size, 0)

    def test_setup_duration_is_included_in_reported_whole_time(self):
        parse = smoke.parse_smoke_module

        def setup(*a, **k):
            self.clock.value += 2.
            return parse(*a, **k)

        with mock.patch.object(smoke, 'parse_smoke_module', side_effect=setup):
            code, _ = self.full(wall=90.)
        self.assertEqual(code, 0)
        r = self.report()
        self.assertEqual(r['setup_sec'], 2.)
        self.assertGreaterEqual(r['whole_sec'], 17.)


class LaunchAndLivePauseRevisionTests(TemporaryRepo):
    def direct(self, factory, *, register=None):
        cleaned = []

        def cleanup(process, expires, clock):
            self.assertEqual(smoke._owned_pgid(process), process.pid)
            cleaned.append(process.pid)
            if process.returncode is None:
                process.returncode = 130
            return ['GROUP_QUIESCENT']

        with ExitStack() as stack:
            stack.enter_context(self.signals.patches())
            stack.enter_context(mock.patch.object(smoke, 'owned_group_alive', return_value=False))
            stack.enter_context(mock.patch.object(smoke, 'stop_process_group', side_effect=cleanup))
            stack.enter_context(mock.patch.object(smoke.subprocess, 'Popen',
                                                  side_effect=AssertionError('NO REAL CHILD')))
            if register is not None:
                stack.enter_context(mock.patch.object(smoke, '_register_owned', side_effect=register))
            result = smoke.run_child(
                ['MOCK'], root=self.root, env={}, work_expires=10., expires=11.,
                clock=self.clock.tick, monitor=lambda: None, process_factory=factory)
        self.assertEqual(smoke._OWNED_GROUPS, {})
        return result, cleaned

    def test_constructor_that_spawns_then_raises_interrupt_is_unknown_not_safe(self):
        state = dict(spawned=False, alive=False)

        def factory(*a, **kwargs):
            self.assertTrue(kwargs['start_new_session'])
            state.update(spawned=True, alive=True)
            raise KeyboardInterrupt('virtual after-spawn/pre-return interrupt')

        r, cleaned = self.direct(factory)
        self.assertTrue(state['alive'])  # Unknown handle cannot be fabricated.
        self.assertEqual(r['status'], 'INTERRUPTED')
        self.assertEqual(r['launch_state'], 'UNKNOWN')
        self.assertIsNone(r['process_started'])
        self.assertTrue(r['creation_attempted'])
        self.assertTrue(r['unsafe_process_state'])
        self.assertEqual(cleaned, [])
        self.assertEqual(self.signals.handlers, {signal.SIGINT: 'OLD_INT', signal.SIGTERM: 'OLD_TERM'})

    def test_launch_preserves_ignored_and_defers_default_dispositions(self):
        for initial in (
                {signal.SIGINT: signal.SIG_IGN, signal.SIGTERM: signal.SIG_DFL},
                {signal.SIGINT: signal.SIG_DFL, signal.SIGTERM: signal.SIG_IGN},
                {signal.SIGINT: signal.SIG_IGN, signal.SIGTERM: signal.SIG_IGN},
                {signal.SIGINT: signal.SIG_DFL, signal.SIGTERM: signal.SIG_DFL}):
            with self.subTest(initial=initial):
                self.signals = FakeSignals()
                self.signals.handlers = dict(initial)

                def factory(*a, **kwargs):
                    self.assertTrue(kwargs['start_new_session'])
                    self.assertEqual(self.signals.mask, set())
                    self.assertEqual(self.signals.calls, [])
                    for sig, disposition in initial.items():
                        if disposition == signal.SIG_IGN:
                            self.assertEqual(self.signals.handlers[sig], signal.SIG_IGN)
                            self.assertFalse(callable(self.signals.handlers[sig]))
                        else:
                            self.assertTrue(callable(self.signals.handlers[sig]))
                    return FakeProcess(self.clock)

                r, cleaned = self.direct(factory)
                self.assertEqual(r['status'], 'COMPLETE')
                self.assertEqual(r['deferred_launch_signals'], [])
                self.assertEqual(r['preserved_ignored_launch_signals'],
                                 [int(sig) for sig, value in initial.items() if value == signal.SIG_IGN])
                self.assertEqual(self.signals.handlers, initial)
                self.assertEqual(self.signals.mask, set())
                self.assertEqual(cleaned, [])

    def test_full_preserves_ignored_sigint_or_sigterm_for_every_factory(self):
        for i, initial in enumerate((
                {signal.SIGINT: signal.SIG_IGN, signal.SIGTERM: signal.SIG_DFL},
                {signal.SIGINT: signal.SIG_DFL, signal.SIGTERM: signal.SIG_IGN},
                {signal.SIGINT: signal.SIG_IGN, signal.SIGTERM: signal.SIG_IGN})):
            with self.subTest(initial=initial):
                self.sid = 'ignored_' + str(i)
                self.signals = FakeSignals()
                self.signals.handlers = dict(initial)
                observed = []

                def observe(index, argv, kwargs):
                    for sig, disposition in initial.items():
                        if disposition == signal.SIG_IGN:
                            self.assertEqual(self.signals.handlers[sig], signal.SIG_IGN)
                        else:
                            self.assertTrue(callable(self.signals.handlers[sig]))
                    observed.append(index)

                code, _ = self.full(callback=observe)
                r = self.report()
                self.assertEqual(code, 0)
                self.assertEqual(len(observed), 5)
                ignored = [int(sig) for sig, value in initial.items() if value == signal.SIG_IGN]
                for receipt in [x for x in r['receipts'] if x['kind'] == 'run'] + [r['summary_receipt']]:
                    self.assertEqual(receipt['preserved_ignored_launch_signals'], ignored)
                self.assertEqual(self.signals.handlers, initial)

    def test_constructor_exception_without_handle_is_also_unknown(self):
        def factory(*a, **kwargs):
            raise OSError('virtual factory could have spawned before raising')

        r, cleaned = self.direct(factory)
        self.assertEqual(r['status'], 'TOOL_ERROR')
        self.assertEqual(r['launch_state'], 'UNKNOWN')
        self.assertIsNone(r['process_started'])
        self.assertTrue(r['unsafe_process_state'])
        self.assertEqual(cleaned, [])

    def test_parent_interrupts_are_deferred_through_launch_and_ownership_without_mask_inheritance(self):
        initial_mask = {signal.SIGUSR1}
        self.signals.mask = set(initial_mask)
        child = FakeProcess(self.clock)
        original_register = smoke._register_owned

        def factory(*a, **kwargs):
            self.assertTrue(kwargs['start_new_session'])
            self.assertNotIn('preexec_fn', kwargs)
            self.assertEqual(self.signals.mask, initial_mask)
            self.assertEqual(self.signals.calls, [])
            self.signals.handlers[signal.SIGINT](signal.SIGINT, None)
            self.signals.handlers[signal.SIGTERM](signal.SIGTERM, None)
            return child

        def register(process, **kwargs):
            self.assertEqual(self.signals.mask, initial_mask)
            self.signals.handlers[signal.SIGTERM](signal.SIGTERM, None)
            return original_register(process, **kwargs)

        r, cleaned = self.direct(factory, register=register)
        self.assertEqual(r['status'], 'INTERRUPTED')
        self.assertTrue(r['process_started'])
        self.assertEqual(r['launch_state'], 'OWNED')
        self.assertEqual(r['deferred_launch_signals'],
                         [int(signal.SIGINT), int(signal.SIGTERM), int(signal.SIGTERM)])
        self.assertEqual(cleaned, [child.pid])
        self.assertEqual(self.signals.mask, initial_mask)
        # Restoration masks only AFTER factory+registration have completed;
        # both callbacks above asserted no mask operation existed yet.
        self.assertTrue(self.signals.calls)
        self.assertEqual(self.signals.handlers, {signal.SIGINT: 'OLD_INT', signal.SIGTERM: 'OLD_TERM'})

    def test_interrupt_delivered_during_launch_handler_restoration_keeps_owned_receipt(self):
        child = FakeProcess(self.clock)
        original = self.signals.handler
        once = [False]

        def setter(sig, value):
            result = original(sig, value)
            if sig == signal.SIGTERM and value == 'OLD_TERM' and not once[0]:
                once[0] = True
                raise KeyboardInterrupt('virtual interrupt AFTER handler restoration')
            return result

        with mock.patch.object(self.signals, 'handler', side_effect=setter):
            r, cleaned = self.direct(lambda *a, **k: child)
        self.assertEqual(r['status'], 'INTERRUPTED')
        self.assertTrue(r['launch_restore_interrupted'])
        self.assertTrue(r['process_started'])
        self.assertEqual(r['launch_state'], 'OWNED')
        self.assertEqual(cleaned, [child.pid])
        self.assertEqual(self.signals.handlers, {signal.SIGINT: 'OLD_INT', signal.SIGTERM: 'OLD_TERM'})

    def test_pending_signal_during_post_factory_restore_is_delivered_after_handlers_are_restored(self):
        child = FakeProcess(self.clock)
        original = self.signals.handler
        once = [False]

        def setter(sig, value):
            result = original(sig, value)
            if sig == signal.SIGTERM and value == 'OLD_TERM' and not once[0]:
                once[0] = True
                self.assertTrue({signal.SIGINT, signal.SIGTERM} <= self.signals.mask)
                self.signals.pending.add(signal.SIGINT)
            return result

        with mock.patch.object(self.signals, 'handler', side_effect=setter):
            r, cleaned = self.direct(lambda *a, **k: child)
        self.assertEqual(r['status'], 'INTERRUPTED')
        self.assertTrue(r['process_started'])
        self.assertEqual(r['launch_state'], 'OWNED')
        self.assertIn(int(signal.SIGINT), r['deferred_launch_signals'])
        self.assertTrue(r['launch_restore_interrupted'])
        self.assertEqual(cleaned, [child.pid])
        self.assertEqual(self.signals.mask, set())
        self.assertEqual(self.signals.pending, set())
        self.assertEqual(self.signals.handlers, {signal.SIGINT: 'OLD_INT', signal.SIGTERM: 'OLD_TERM'})

    def test_registration_failure_never_invents_ownership(self):
        child = FakeProcess(self.clock)

        def registration(*a, **k):
            raise smoke.SafetyError('virtual unsafe ownership')

        with self.signals.patches(), \
                mock.patch.object(smoke, '_register_owned', side_effect=registration), \
                mock.patch.object(smoke.os, 'killpg') as signal_group:
            r = smoke.run_child(
                ['MOCK'], root=self.root, env={}, work_expires=10., expires=11.,
                clock=self.clock.tick, monitor=lambda: None,
                process_factory=lambda *a, **k: child)
        self.assertEqual(r['launch_state'], 'UNKNOWN')
        self.assertTrue(r['process_started'])
        self.assertTrue(r['unsafe_process_state'])
        signal_group.assert_not_called()
        self.assertEqual(smoke._OWNED_GROUPS, {})

    def test_runner_path_walk_is_root_first_before_any_link_descendant_metadata(self):
        seen = []

        def linked(path):
            seen.append(str(path))
            return str(path) == '/repo/scripts'

        with mock.patch.object(Path, 'is_symlink', autospec=True, side_effect=linked):
            with self.assertRaises(smoke.SafetyError):
                smoke.safe_path('/repo', '/repo/scripts/batch/tool_smoke.bat')
        self.assertEqual(seen, ['/repo', '/repo/scripts'])

    def test_linked_root_and_output_ancestor_stop_before_descendants(self):
        for linked_name in ('/repo', '/repo/test_result/evidence'):
            seen = []

            def linked(path):
                seen.append(str(path))
                return str(path) == linked_name

            with self.subTest(link=linked_name), \
                    mock.patch.object(Path, 'is_symlink', autospec=True, side_effect=linked):
                with self.assertRaises(smoke.SafetyError):
                    smoke.safe_path('/repo', '/repo/test_result/evidence/codex_smoke/s/report.json')
            self.assertEqual(seen[-1], linked_name)
            self.assertTrue(all(not x.startswith(linked_name + '/') for x in seen))

    def test_expired_utc_guard_before_pause_requests_no_sleep(self):
        sleeps = []

        def expired():
            raise smoke.BudgetExpired('virtual absolute UTC already expired')

        with self.assertRaises(smoke.BudgetExpired):
            smoke.bounded_pause(300, work_expires=900., clock=lambda: 0.,
                                guard=expired, sleep=sleeps.append)
        self.assertEqual(sleeps, [])

    def test_live_utc_jump_during_pause_stops_before_next_bounded_chunk(self):
        deadline = self.clock.start + timedelta(seconds=10)
        sleeps = []

        def guard():
            if self.clock.now() >= deadline:
                raise smoke.BudgetExpired('virtual UTC jump')

        def pause(value):
            sleeps.append(value)
            self.clock.sleep(value)
            self.clock.start += timedelta(hours=1)

        with self.assertRaises(smoke.BudgetExpired):
            smoke.bounded_pause(300, work_expires=900., clock=self.clock.tick,
                                guard=guard, sleep=pause)
        self.assertEqual(sleeps, [smoke.SLEEP_CHUNK_SECONDS])
        self.assertEqual(self.clock.value, smoke.SLEEP_CHUNK_SECONDS)

    def test_uninterrupted_pause_preserves_total_canonical_duration(self):
        sleeps = []

        def pause(value):
            sleeps.append(value)
            self.clock.sleep(value)

        smoke.bounded_pause(300, work_expires=900., clock=self.clock.tick,
                            guard=lambda: None, sleep=pause)
        self.assertEqual(sum(sleeps), 300.)
        self.assertEqual(self.clock.value, 300.)
        self.assertTrue(all(0 < x <= smoke.SLEEP_CHUNK_SECONDS for x in sleeps))

    def test_full_checks_utc_immediately_before_the_canonical_pause(self):
        original = smoke.bounded_pause

        def jumped(*a, **k):
            self.clock.start += timedelta(hours=2)
            return original(*a, **k)

        with mock.patch.object(smoke, 'bounded_pause', side_effect=jumped), \
                mock.patch.object(self.clock, 'sleep', wraps=self.clock.sleep) as sleep:
            code, launch = self.full()
        r = self.report()
        self.assertEqual(code, 124)
        self.assertEqual(len(launch.calls), 2)
        self.assertEqual(r['receipts'][2]['status'], 'TIMED_OUT')
        sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
