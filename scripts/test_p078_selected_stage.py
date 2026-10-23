"""Selected-admission CPU mocks only: no torch, corpus, real CP or GPU."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p078_selected_stage as s
from scripts import diag_p078_route_training as native
from scripts.test_p078_route_protocol import actual_readers

NOW = datetime(2026, 10, 22, 0, tzinfo=timezone.utc)


def arguments(mode='train'):
    return SimpleNamespace(mode=mode, arm='uniform_r2', corpus=native.CLEAN_CORPUS,
        corpus_sha256='C' * 64, adam_lr=5e-5, muon_lr=2e-4,
        authorization='handoff/audit/new_authority.json', authorization_sha256='E' * 64,
        selection='handoff/audit/selected.json', selection_sha256='D' * 64,
        max_wall_sec=600, worker=True, execute=True, check_only=False)


def sources():
    return {name: dict(path=name, bytes=123, sha256='A' * 64)
            for name in (s.SCRIPT, s.TEST, 'scripts/diag_p078_route_training.py')}


class Fixture:
    def __init__(self, root):
        self.root = root; self.args = arguments(); self.sources = sources()
        route = SimpleNamespace(ARMS=s.ORIGINAL_ARMS, sha=native.route.sha, plan=lambda *_a, **_k: ((0, 0),))
        self.info = dict(frozen_input='MOCK_ONLY')
        self.auth = dict(expires_at=s.HARD_STOP.isoformat(),
            selected_stage_descriptor=self.args.selection, selected_stage_sha256=self.args.selection_sha256,
            selected_stage_adapter_sha256=self.sources[s.SCRIPT]['sha256'])
        self.driver = SimpleNamespace(route=route, CLEAN_CORPUS=native.CLEAN_CORPUS, READY=True, Hold=native.Hold,
            signature=Mock(return_value=self.info), authority=Mock(return_value=8000.), read=Mock(return_value=self.auth),
            inputs=Mock(return_value=dict(manifests=dict(train=dict(rows=22528), val=dict(rows=512)))),
            update_count=native.update_count, actual_spent=Mock(return_value=850.),
            path=lambda relative: root / relative, digest=Mock(return_value='B' * 64),
            report_name=native.report_name, activity_name=native.activity_name, cp_name=native.cp_name)
        self.selection = dict(schema=s.SCHEMA, tag=s.TAG, decision_owner='ROOT_EXECUTION_PRIORITIZATION',
            selected_arms=list(s.SELECTED), deferred_arms=list(s.DEFERRED),
            original_input_signature_sha256=route.sha(self.info), adapter_source_sha256=s.source_hashes(self.sources),
            corpus_sha256=self.args.corpus_sha256, max_family_seconds=144000, reserve_seconds=1800,
            created_at=(NOW - timedelta(minutes=1)).isoformat(), expires_at=s.HARD_STOP.isoformat(),
            reason='orchestrator time prioritization, not a user choice or quality-based selection', router_execution=False)
        self.full = dict(status='HOLD_BUDGET', fits=False, actual_spent_seconds=850.,
            train_forecast_seconds=dict(uniform_r2=1000., balanced_count=1200.,
                fixed_shuffle_r2=10000., update_shuffle_r2=10000.),
            evaluation_forecast_seconds={a: 100. for a in s.ORIGINAL_ARMS},
            total_pending_seconds=24400., reserve_seconds=1800, family_cap_seconds=144000)
        self.reports = {}
        self.driver.closed = Mock(side_effect=lambda _a, _m, arm: copy.deepcopy(self.reports[arm]))
        self.driver.cost_receipt = lambda *_a: self.driver.route.plan()
        self.driver.budget = Mock(side_effect=lambda _a: copy.deepcopy(self.full))
        self.driver.readback = Mock(side_effect=AssertionError('original all-four readback forbidden'))

    def loaded(self):
        return copy.deepcopy(self.selection), self.sources, self.info, self.driver.authority.return_value

    def completed(self, arm):
        for name in (native.report_name('train', arm, self.args), native.activity_name('train', arm, self.args)):
            target = self.root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('{}')
        self.reports[arm] = dict(status='ROUTE_SFT_COMPLETE_EVAL_REVIEW_REQUIRED', updates=704,
            checkpoint_writes=1, checkpoint=native.cp_name(arm, self.args), authorization=copy.deepcopy(self.auth))
        self.full['train_forecast_seconds'][arm] = self.full['evaluation_forecast_seconds'][arm] = 0.


class SelectedTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        folder = self.stack.enter_context(tempfile.TemporaryDirectory(prefix='p078_selected_mock_'))
        self.fixture = Fixture(Path(folder)); self.f = self.fixture; self.d = self.f.driver; self.a = self.f.args
        self.stack.enter_context(patch.object(s, 'utc_now', return_value=NOW))
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('noninteractive only')))
        self.stack.enter_context(patch.object(native, 'loaded', side_effect=AssertionError('real model/CP forbidden')))
        self.stack.enter_context(patch.object(native, 'run_training', side_effect=AssertionError('real training forbidden')))

    def validate(self, value=None):
        return s.validate_descriptor(self.f.selection if value is None else value,
            self.a, self.d, self.f.sources, NOW)

    def budget(self):
        with patch.object(s, 'load_selection', side_effect=lambda *_a: self.f.loaded()):
            return s.selected_budget(self.a, self.d, self.d.budget)

    def test_exact_orchestrator_selection_binds_original_source_corpus_and_new_authority(self):
        _, info, remaining = self.validate()
        self.assertEqual(info, self.f.info); self.assertEqual(remaining, 8000.)
        self.d.authority.assert_called_once_with(self.a, self.f.info)
        self.assertEqual(tuple(self.d.route.ARMS), s.ORIGINAL_ARMS)

    def test_selection_is_not_a_generic_arm_filter_or_router_permission(self):
        changes = dict(schema='other', decision_owner='USER_SELECTED', selected_arms=list(reversed(s.SELECTED)),
            deferred_arms=[], adapter_source_sha256={}, original_input_signature_sha256='wrong',
            corpus_sha256='wrong', max_family_seconds=144001, reserve_seconds=1799,
            router_execution=True, reason='')
        for key, value in changes.items():
            with self.subTest(key=key):
                bad = copy.deepcopy(self.f.selection); bad[key] = value
                with self.assertRaises(ValueError): self.validate(bad)
        self.d.route.ARMS = s.SELECTED
        with self.assertRaises(ValueError): self.validate()

    def test_today17_hard_stop_expiration_naive_and_future_issue_are_not_waived(self):
        for key, value in (('expires_at', (s.HARD_STOP + timedelta(seconds=1)).isoformat()),
                           ('expires_at', NOW.isoformat()), ('expires_at', '2026-10-22T17:00:00'),
                           ('created_at', (NOW + timedelta(seconds=1)).isoformat())):
            bad = copy.deepcopy(self.f.selection); bad[key] = value
            with self.assertRaises((ValueError, native.Hold)): self.validate(bad)
        with self.assertRaises(native.Hold):
            s.validate_descriptor(self.f.selection, self.a, self.d, self.f.sources, s.HARD_STOP)

    def test_old_or_mismatched_authority_cannot_admit_selected_training(self):
        for key, value in (('selected_stage_descriptor', 'old.json'), ('selected_stage_sha256', 'old'),
                           ('selected_stage_adapter_sha256', 'old'),
                           ('expires_at', (s.HARD_STOP + timedelta(seconds=1)).isoformat())):
            original = self.f.auth[key]; self.f.auth[key] = value
            with self.assertRaises(ValueError): self.validate()
            self.f.auth[key] = original
        self.d.authority.side_effect = native.Hold('original authority/PGID/family guard must remain')
        with self.assertRaises(native.Hold): self.validate()

    def test_selected_forecast_retains_false_full_forecast_deferred_work_and_all_four_costs(self):
        result = self.budget()
        self.assertTrue(result['fits']); self.assertFalse(result['original_all_pending_forecast']['fits'])
        self.assertEqual(result['actual_spent_seconds'], 850.)
        self.assertEqual(result['total_pending_seconds'], 4200.)
        self.assertEqual(set(result['all_four_cost_receipts']), set(s.ORIGINAL_ARMS))
        self.assertEqual(set(result['deferred_forecast_seconds']), set(s.DEFERRED))
        self.assertEqual(result['deferred_forecast_seconds']['fixed_shuffle_r2']['train'], 10000.)
        self.assertEqual(result['completed_original_arms'], 0)
        self.assertFalse(result['original_four_arm_study_complete'])

    def test_expensive_or_failed_family_cannot_be_reset_by_subset_selection(self):
        self.d.actual_spent.return_value = self.f.full['actual_spent_seconds'] = 143000.
        self.assertFalse(self.budget()['fits'])
        self.d.budget.side_effect = native.Hold('prior failed activity')
        with self.assertRaises(native.Hold): self.budget()

    def test_whole_worker_cap_is_checked_before_original_activity_can_start(self):
        with patch.object(s, 'load_selection', side_effect=lambda *_a: self.f.loaded()):
            s.worker_cap_preflight(self.a, self.d)
            for spent, remaining in ((850., 599.), (143401., 8000.), (float('nan'), 8000.)):
                self.d.actual_spent.return_value = spent; self.d.authority.return_value = remaining
                with self.assertRaises(native.Hold): s.worker_cap_preflight(self.a, self.d)

    def test_remaining_window_and_ledger_mismatch_block_admission(self):
        self.d.authority.return_value = 4000.
        self.assertFalse(self.budget()['fits'])
        self.d.actual_spent.return_value = 849.
        with self.assertRaises(ValueError): self.budget()

    def test_already_closed_selected_stage_is_zero_pending_but_deferred_stage_is_not_hidden(self):
        self.f.completed('uniform_r2'); result = self.budget()
        self.assertEqual(result['selected_completed'], ['uniform_r2'])
        self.assertEqual(result['train_forecast_seconds']['uniform_r2'], 0.)
        self.assertEqual(result['total_pending_seconds'], 3100.)
        self.f.completed('fixed_shuffle_r2')
        with self.assertRaises(native.Hold): self.budget()

    def test_completed_arm_from_another_admission_cannot_be_retroactively_selected(self):
        self.f.completed('uniform_r2')
        self.f.reports['uniform_r2']['authorization']['selected_stage_sha256'] = 'other'
        with self.assertRaises(ValueError): self.budget()

    def test_admission_scope_changes_budget_explicitly_and_restores_every_original_function(self):
        original = self.d.budget, self.d.cost_receipt, self.d.readback, self.d.route.plan
        with patch.object(s, 'load_selection', side_effect=lambda *_a: self.f.loaded()):
            with s.admission_scope(self.d, self.a):
                result = self.d.budget(self.a)
                self.assertTrue(result['fits'])
                self.assertEqual(self.d.route.plan(), ((0, 0),))
                self.assertEqual(tuple(self.d.route.ARMS), s.ORIGINAL_ARMS)
        self.assertEqual((self.d.budget, self.d.cost_receipt, self.d.readback, self.d.route.plan), original)
        self.d.readback.assert_not_called()

    def test_partial_readback_requires_both_original704_closed_stages_and_never_calls_full_reader(self):
        self.f.completed('uniform_r2'); self.f.completed('balanced_count')
        summary = dict(initial_core_sha256='same', actual_x_tokens=100, assistant_targets=20)
        verifier = Mock(return_value=summary)
        with patch.object(s, 'load_selection', side_effect=lambda *_a: self.f.loaded()), \
             patch.object(s, 'single_arm_verifier', return_value=verifier):
            result = s.partial_readback(self.a, self.d, self.d.budget)
        self.assertEqual((result['selected_complete'], result['original_total']), (2, 4))
        self.assertFalse(result['original_four_arm_study_complete'])
        self.assertEqual([c.args[1] for c in verifier.call_args_list], list(s.SELECTED))
        self.d.readback.assert_not_called()
        self.f.reports['balanced_count']['updates'] = 703
        with patch.object(s, 'load_selection', side_effect=lambda *_a: self.f.loaded()), \
             patch.object(s, 'single_arm_verifier', return_value=verifier):
            with self.assertRaises(ValueError): s.partial_readback(self.a, self.d, self.d.budget)

    def test_partial_pair_rejects_parent_or_exposure_mismatch(self):
        self.f.completed('uniform_r2'); self.f.completed('balanced_count')
        summaries = [dict(initial_core_sha256='same', actual_x_tokens=100, assistant_targets=20),
                     dict(initial_core_sha256='different', actual_x_tokens=100, assistant_targets=20)]
        with patch.object(s, 'load_selection', side_effect=lambda *_a: self.f.loaded()), \
             patch.object(s, 'single_arm_verifier', return_value=Mock(side_effect=summaries)):
            with self.assertRaises(ValueError): s.partial_readback(self.a, self.d, self.d.budget)

    def test_missing_selected_peer_blocks_partial_closure(self):
        self.f.completed('uniform_r2')
        with patch.object(s, 'load_selection', side_effect=lambda *_a: self.f.loaded()):
            with self.assertRaises(native.Hold): s.partial_readback(self.a, self.d, self.d.budget)

    def test_worker_main_reinstalls_selected_budget_and_separates_partial_readback_output(self):
        original_budget, original_readback = self.d.budget, self.d.readback
        original_plan = self.d.route.plan
        observed = []
        def work(args):
            observed.append(args.mode)
            self.assertIs(self.d.route.plan, original_plan)
            self.assertIsNot(self.d.budget, original_budget)
            self.assertTrue(self.d.budget(args)['fits'])
            self.assertEqual(tuple(self.d.route.ARMS), s.ORIGINAL_ARMS)
            if args.mode == 'selected_readback':
                self.assertIsNot(self.d.readback, original_readback)
                self.assertEqual(self.d.readback(args), {'partial': True})
                self.assertNotEqual(self.d.report_name(args.mode, args.arm, args),
                    self.d.report_name('readback', args.arm, args))
            else:
                self.assertEqual(args.mode, 'train')
            return 0
        self.d.worker = Mock(side_effect=work)
        def record(_driver, _args, _argv, action, role, details=None):
            self.assertEqual(role, 'OWNED_SELECTED_WORKER')
            code, result_details = action()
            self.assertEqual(result_details['completion_scope'], 'TWO_OF_ORIGINAL_FOUR')
            self.assertFalse(details['pre_execution_admission']['original_all_pending_forecast']['fits'])
            return code
        with patch.object(s.protocol, 'load_driver', return_value=self.d), \
             patch.object(s, 'load_selection', side_effect=lambda *_a: self.f.loaded()), \
             patch.object(s, 'recorded', side_effect=record), \
             patch.object(s, 'partial_readback', return_value={'partial': True}), \
             patch.object(s, 'launch', side_effect=AssertionError('worker must not recurse into launch')):
            for mode in ('train', 'readback'):
                self.assertEqual(s.main(['--mode', mode, '--execute', '--worker']), 0)
        self.assertEqual(observed, ['train', 'selected_readback'])
        self.assertIs(self.d.budget, original_budget)
        self.assertIs(self.d.readback, original_readback)
        self.d.readback.assert_not_called()

    def test_bad_cap_parent_is_not_launched_and_original_worker_is_not_called(self):
        self.d.authority.return_value = 599.
        self.d.worker = Mock(side_effect=AssertionError('bad cap must not start original activity'))
        def record(_driver, _args, _argv, action, _role, details=None):
            with self.assertRaises(native.Hold): action()
            return 8
        with patch.object(s.protocol, 'load_driver', return_value=self.d), \
             patch.object(s, 'load_selection', side_effect=lambda *_a: self.f.loaded()), \
             patch.object(s, 'recorded', side_effect=record), \
             patch.object(s, 'launch', side_effect=AssertionError('bad cap must not spawn child')):
            for worker in ([], ['--worker']):
                self.assertEqual(s.main(['--mode', 'train', '--max-wall-sec', '600', '--execute', *worker]), 8)
        self.d.worker.assert_not_called()

    def test_false_selected_forecast_is_retained_without_worker_or_parent_launch(self):
        self.d.authority.return_value = 4000.
        self.d.worker = Mock(side_effect=AssertionError('unfit budget must not start original activity'))
        observed = []
        def record(_driver, _args, _argv, action, role, details=None):
            with self.assertRaises(native.Hold): action()
            self.assertFalse(details['pre_execution_admission']['fits'])
            self.assertEqual(details['pre_execution_admission']['original_all_pending_forecast'], self.f.full)
            observed.append(role)
            return 8
        with patch.object(s.protocol, 'load_driver', return_value=self.d), \
             patch.object(s, 'load_selection', side_effect=lambda *_a: self.f.loaded()), \
             patch.object(s, 'recorded', side_effect=record), \
             patch.object(s, 'launch', side_effect=AssertionError('unfit budget must not spawn child')):
            for worker in ([], ['--worker']):
                self.assertEqual(s.main(['--mode', 'train', '--max-wall-sec', '600', '--execute', *worker]), 8)
        self.d.worker.assert_not_called()
        self.assertEqual(observed, ['SELECTED_PARENT_LAUNCH', 'OWNED_SELECTED_WORKER'])

    def test_post_admission_exception_retains_both_forecasts_in_failure_receipt(self):
        details = {}
        def fail():
            details['pre_execution_admission'] = self.budget()
            raise RuntimeError('mock failure after admission')
        captured = []
        with patch.object(s, 'source_identity', return_value=self.f.sources), \
             patch.object(s, 'metadata', return_value={}), \
             patch.object(s, 'write_receipt', side_effect=lambda value: captured.append(value)), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(s.recorded(self.d, self.a, [], fail, 'MOCK', details), 9)
        receipt = captured[0]
        self.assertFalse(receipt['details']['pre_execution_admission']['original_all_pending_forecast']['fits'])
        self.assertTrue(receipt['details']['pre_execution_admission']['fits'])
        self.assertEqual(receipt['returncode'], 9)


class OriginalReaderProjectionTests(unittest.TestCase):
    def test_exact_pinned_per_arm_reader_accepts_original_raw_without_shrinking_arms(self):
        with actual_readers('train') as (args, _):
            verifier = s.single_arm_verifier(native)
            with s.protocol.normalized_plans(native.route):
                result = verifier(args, 'balanced_count')
            self.assertEqual(result['initial_core_sha256'], 'D' * 64)
            self.assertEqual(tuple(native.route.ARMS), s.ORIGINAL_ARMS)

    def test_exact_original_raw_checks_still_reject_tampered_update(self):
        def damage(event, index):
            if index == 0: event['actual_rows'] -= 1
        with actual_readers('train', damage) as (args, _):
            verifier = s.single_arm_verifier(native)
            with s.protocol.normalized_plans(native.route):
                with self.assertRaises(ValueError): verifier(args, 'uniform_r2')


class LaunchAndCliTests(unittest.TestCase):
    def test_child_reenters_selected_adapter_with_descriptor_and_original_process_isolation(self):
        argv = ['--mode', 'train', '--selection', 'handoff/audit/mock.json', '--selection-sha256', 'A' * 64, '--execute']
        process = Mock(pid=123456); process.wait.return_value = 0
        with patch.object(s.protocol.subprocess, 'Popen', return_value=process) as popen:
            self.assertEqual(s.launch(argv, 900), 0)
        command = popen.call_args.args[0]
        self.assertEqual(command[4], str(ROOT / s.SCRIPT))
        self.assertEqual(command[5:], argv + ['--worker'])
        self.assertEqual(popen.call_args.kwargs['stdin'], subprocess.DEVNULL)
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        process.wait.assert_called_once_with(timeout=900)

    def test_timeout_uses_original_process_group_termination_without_signaling_real_process(self):
        process = Mock(pid=123456)
        process.wait.side_effect = [subprocess.TimeoutExpired('mock', 900), 0]
        with patch.object(s.protocol.subprocess, 'Popen', return_value=process), patch.object(s.protocol.os, 'killpg') as kill:
            self.assertEqual(s.launch(['--mode', 'train', '--execute'], 900), 130)
        kill.assert_called_once_with(123456, signal.SIGTERM)

    def test_check_only_in_a_new_cpu_process_reads_no_assets_and_imports_no_torch(self):
        code = ("from scripts import diag_p078_selected_stage as s; import sys; "
                "assert 'torch' not in sys.modules; "
                "assert s.main(['--mode','train','--check-only']) == 0; "
                "assert 'torch' not in sys.modules")
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=ROOT,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"corpus_reads": 0', result.stdout)
        self.assertIn('"router_execution": false', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
