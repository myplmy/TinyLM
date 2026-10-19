"""Pure/temp controller regressions; no real assets or model/GPU execution."""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import diag_p106b_content_recovery as driver
from scripts.p106b_stage_receipt import pipeline
from tinylm.train.mtp_sft import Record


class PureContract(unittest.TestCase):
    def test_authority_separates_training_and_final_deadlines(self):
        self.assertGreater(driver.authority(training=True, now=driver.TRAIN_STOP - timedelta(seconds=1)), 0)
        with self.assertRaises(driver.Pending):
            driver.authority(training=True, now=driver.TRAIN_STOP)
        self.assertGreater(driver.authority(now=driver.END - timedelta(seconds=1)), 0)
        with self.assertRaises(driver.Pending):
            driver.authority(now=driver.END)
        with self.assertRaises(ValueError):
            driver.authority(now=datetime(2026, 10, 19))

    def test_mode_and_arm_ownership_reject_unused_selectors(self):
        for mode, arm in (('prepare', 'token'), ('train', None), ('cost', 'alien'),
                          ('evaluate', 'parent'), ('readback', 'content')):
            with self.subTest(mode=mode, arm=arm), self.assertRaises(ValueError):
                driver.phase_commands(mode, arm, 600)

    def test_phase_order_includes_real_regressions_and_source_barrier(self):
        phases = driver.phase_commands('prepare', None, 600)
        self.assertEqual([label for label, _ in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertIn('scripts.test_p106b_content_objective', phases[0][1])
        self.assertEqual(phases[1][1][phases[1][1].index('--mode') + 1], 'source')
        self.assertIn('--worker', phases[2][1])
        train = driver.phase_commands('train', 'content', 3600)
        self.assertEqual(train[1][1][train[1][1].index('--mode') + 1], 'preflight')
        self.assertEqual(train[2][1][-2:], ['--arm', 'content'])

    def test_worker_wall_is_bounded_and_not_a_truthy_boolean(self):
        for value in (0, 59, 7201, True, 60.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                driver.phase_commands('prepare', None, value)

    def test_check_only_cannot_start_worker_or_assets(self):
        with mock.patch.object(driver, 'info', return_value={'model': 'NOT_RUN'}), \
                mock.patch.object(driver, 'worker') as worker, \
                mock.patch.object(driver, 'launch') as launch, redirect_stdout(io.StringIO()):
            self.assertEqual(driver.main(['--mode', 'train', '--arm', 'token', '--check-only']), 0)
        worker.assert_not_called()
        launch.assert_not_called()

    def test_failed_preflight_never_invokes_experiment(self):
        phases = driver.phase_commands('train', 'token', 600)
        calls = []
        def launch(command):
            calls.append(command)
            return 0 if len(calls) == 1 else 8
        receipt = pipeline(phases, launch, lambda _: None, experiment='CPU_FIXTURE')
        self.assertEqual(receipt['status'], 'HOLD')
        self.assertFalse(receipt['main_experiment_invoked'])
        self.assertEqual(receipt['phases'][2]['status'], 'NOT_RUN')

    def test_checkpoint_path_rejects_undeclared_arm_before_io(self):
        with self.assertRaises(ValueError):
            driver.checkpoint('parent')
        self.assertIn(driver.TAG, driver.checkpoint('content').name)

    def test_weight_mass_preserves_masked_wrong_owner(self):
        records = [Record([1, 2, 3, 4], [-100, 8, -100, 4], [1, 1, 2, 2]),
                   Record([1, 2, 3, 4], [9, 10, 11, 4], [1, 1, 1, 1])]
        rows = [dict(y=r.y, segments=r.segments, lane='replay', language='ko') for r in records]
        plan = driver.objective.make_weights(records, policy='content')
        values = driver.weight_mass(plan, rows)
        self.assertEqual(values[0]['targets'], 6)
        self.assertEqual(values[0]['content_targets'], 4)
        self.assertEqual(values[0]['eot_targets'], 2)
        self.assertAlmostEqual(values[0]['content_mass'], 4 / 6)
        self.assertAlmostEqual(values[0]['eot_mass'], 2 / 6)
        self.assertEqual(plan.weights[0][0], 0.)
        self.assertEqual(plan.weights[0][2], 0.)

    def test_late_source_failure_precedes_parent_gpu_and_outputs(self):
        with mock.patch.object(driver, 'prepared', side_effect=ValueError('late pass corrupt')), \
                mock.patch.object(driver.source.base, 'load_parent') as model:
            with self.assertRaisesRegex(ValueError, 'late pass'):
                driver.train('content', cost=True)
        model.assert_not_called()

    def test_source_reader_rechecks_all_passes_and_dev(self):
        proof = dict(passes=[dict(masked_positive_owner_rows=64)], dev_rows=384)
        with mock.patch.object(driver.source, 'read_prepared', return_value=({}, [], {})), \
                mock.patch.object(driver, 'info', return_value={'code_complete': True}), \
                mock.patch.object(driver.source, 'validate_training_inputs', return_value=proof) as consume:
            self.assertEqual(driver.source_state()[3], proof)
        consume.assert_called_once_with({}, driver.SOURCE_ARM)


class TemporaryFiles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='content_controller_fixture_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root_patch = mock.patch.object(driver, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.safe = mock.patch.object(driver, 'safe', side_effect=lambda value: Path(value))
        self.safe.start()
        self.addCleanup(self.safe.stop)

    def test_write_is_exclusive_and_rejects_nonfinite_before_touch(self):
        path = self.root / 'one.json'
        driver.write(path, {'value': 1})
        with self.assertRaises(FileExistsError):
            driver.write(path, {'value': 2})
        self.assertEqual(json.loads(path.read_text()), {'value': 1})
        bad = self.root / 'bad.json'
        with self.assertRaises(ValueError):
            driver.write(bad, {'value': float('nan')})
        self.assertFalse(bad.exists())

    def test_single_json_20mb_guard_precedes_file_creation(self):
        path = self.root / 'too_large.json'
        with mock.patch.object(driver.json, 'dumps', return_value='x' * 20_000_000):
            with self.assertRaises(ValueError):
                driver.write(path, {})
        self.assertFalse(path.exists())

    def test_required_does_not_convert_missing_artifact_to_success(self):
        with self.assertRaises(driver.Pending):
            driver.required(self.root / 'missing.json')

    def test_duplicate_worker_activity_rejected_before_execution(self):
        with mock.patch.object(driver, 'EVIDENCE', self.root), \
                mock.patch.object(driver, 'authority', return_value=10000), \
                mock.patch.object(driver, 'spent_seconds', return_value=0), \
                mock.patch.object(driver, 'train') as train:
            driver.write(self.root / 'activity_cost_token.json', {'fixture': True})
            with self.assertRaises(FileExistsError):
                driver.worker('cost', 'token', 600)
        train.assert_not_called()

    def test_incomplete_cost_activity_is_not_a_budget_admission(self):
        activity = dict(schema=driver.SCHEMA, tag=driver.TAG, key='cost_token', mode='cost',
                        arm='token', seconds=17., returncode=None, complete=False,
                        max_wall_sec=600, code_sha256={'fixture': 'sha'})
        with mock.patch.object(driver, 'EVIDENCE', self.root), \
                mock.patch.object(driver, 'prepared', return_value=({}, {})), \
                mock.patch.object(driver, 'info', return_value={'code_sha256': {'fixture': 'sha'}}), \
                mock.patch.object(driver, 'read_training') as read:
            driver.write(self.root / 'activity_cost_token.json', activity)
            with self.assertRaisesRegex(ValueError, 'completed|complete'):
                driver.budget()
        read.assert_not_called()

    def test_completed_worker_rejects_wrong_code_and_exit(self):
        good = dict(schema=driver.SCHEMA, tag=driver.TAG, key='cost_token', mode='cost',
                    arm='token', seconds=17., returncode=0, complete=True,
                    max_wall_sec=600, code_sha256={'fixture': 'sha'})
        for changes in ({'returncode': 8}, {'code_sha256': {}}, {'seconds': float('nan')},
                        {'complete': False}, {'arm': 'content'}):
            value = dict(good, **changes)
            with self.subTest(changes=changes), \
                    mock.patch.object(driver, 'required', return_value=value), \
                    mock.patch.object(driver, 'info', return_value={'code_sha256': {'fixture': 'sha'}}):
                with self.assertRaises(ValueError):
                    driver.completed_activity('cost', 'token')

    def test_eval_worker_keeps_absolute_record_reserve(self):
        with mock.patch.object(driver, 'EVIDENCE', self.root), \
                mock.patch.object(driver, 'authority', return_value=1500), \
                mock.patch.object(driver, 'spent_seconds', return_value=0), \
                mock.patch.object(driver, 'evaluate') as evaluate:
            with self.assertRaises(driver.Pending):
                driver.worker('evaluate', 'token', 1500)
        evaluate.assert_not_called()


class EvaluationIdentity(unittest.TestCase):
    def fixture(self):
        lineage = dict(expected_core_sha256='A' * 64, checkpoint='owned.pt', checkpoint_sha256='B' * 64)
        cases = [{'fixture': 'one'}]
        info = dict(schema=driver.SCHEMA, code_sha256={'fixture': 'sha'}, tag=driver.TAG)
        report = dict(info, status='ACTUAL_FIRST_ANSWERS_RECORDED', arm='token', lineage=lineage,
            cases_sha256=driver.sha(cases), model_training=False, weights_changed=False,
            checkpoints_written=0, core_before='A' * 64, core_after='A' * 64,
            answer_manifest=dict(lineage=lineage), native32_fp32=dict(targets=32768, windows=32,
                precision='FP32_MATH', val_sha256=driver.source.base.NATIVE_VAL_SHA, ce=3.5))
        return report, cases, lineage, info

    def test_complete_identity_passes_without_model_or_data(self):
        report, cases, lineage, info = self.fixture()
        with mock.patch.object(driver, 'info', return_value=info):
            driver.validate_evaluation(report, 'token', cases, lineage)

    def test_report_status_code_tag_and_manifest_are_bound(self):
        for changes in ({'status': 'PARTIAL'}, {'code_sha256': {}}, {'tag': 'alien'},
                        {'answer_manifest': {'lineage': {}}}, {'model_training': True},
                        {'weights_changed': True}, {'cases_sha256': 'C' * 64}):
            report, cases, lineage, info = self.fixture()
            report.update(changes)
            with self.subTest(changes=changes), mock.patch.object(driver, 'info', return_value=info):
                with self.assertRaises(ValueError):
                    driver.validate_evaluation(report, 'token', cases, lineage)

    def test_native_scope_is_not_silently_promoted(self):
        report, cases, lineage, info = self.fixture()
        report['native32_fp32']['targets'] = 1
        with mock.patch.object(driver, 'info', return_value=info), self.assertRaises(ValueError):
            driver.validate_evaluation(report, 'token', cases, lineage)


if __name__ == '__main__':
    unittest.main()
