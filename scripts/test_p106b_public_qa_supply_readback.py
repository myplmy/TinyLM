"""Frozen-inventory recovery; pure synthetic files and no learned assets/GPU."""
from contextlib import redirect_stdout, redirect_stderr
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from scripts import p106b_public_qa_supply_readback as d


class WireAndCoreTests(unittest.TestCase):
    def test_frozen_source_tuple_json_array_round_trip_is_same_wire_value(self):
        sources = copy.deepcopy(d.frozen.data.SOURCES)
        saved = json.loads(json.dumps(sources))
        self.assertNotEqual(saved, sources)
        self.assertEqual(d.wire(saved), d.wire(sources))
        for language in ('ko', 'en'):
            for split in ('train', 'dev'):
                changed = copy.deepcopy(saved); changed[language][split][1] = 'CHANGED'
                self.assertNotEqual(d.wire(changed), d.wire(sources))
        changed = copy.deepcopy(saved); changed['ko']['train'].reverse()
        self.assertNotEqual(d.wire(changed), d.wire(sources))

    def test_wire_does_not_coerce_bool_int_float_string_nan_or_order(self):
        for a, b in ((False, 0), (True, 1), (1, 1.), (1, '1'), ([1, 2], [2, 1]), (None, 'null')):
            self.assertNotEqual(d.wire(a), d.wire(b))
        self.assertEqual(d.wire({'b': (1, 2), 'a': 0}), d.wire({'a': 0, 'b': [1, 2]}))
        for value in (float('nan'), float('inf'), float('-inf')):
            with self.assertRaises(ValueError): d.wire(value)

    def test_original_failure_is_reproduced_before_any_source_model_or_baseline(self):
        current = dict(sources=copy.deepcopy(d.frozen.data.SOURCES))
        report = dict(json.loads(json.dumps(current)), status='CPU_PUBLIC_QA_SUPPLY_COMPLETE_NO_TRAINING_CLAIM')
        with patch.object(d.frozen, 'required', return_value=report), patch.object(d.frozen, 'info', return_value=current), \
                patch.object(d.frozen, 'load_baseline', side_effect=AssertionError('source must not be read')) as baseline:
            with self.assertRaisesRegex(ValueError, 'contract changed'): d.frozen.check()
            baseline.assert_not_called()
        self.assertTrue(all(d.wire(report.get(k)) == d.wire(v) for k, v in current.items()))

    def test_every_other_source_raw_policy_guard_matches_frozen_character_and_ast(self):
        self.assertTrue(d.core_equivalence()['ast_and_character_equal_after_declared_edits'])
        source = Path(d.__file__).read_text()
        for old, new in [("report.get('cuda_initialized') is not False", "False"),
                         ("cohort.get('policy') !=", "cohort.get('policy') =="),
                         ("require_all=cap == 2", "require_all=False"),
                         ("frozen.data.digest(frozen.safe", "frozen.data.digest(str")]:
            self.assertIn(old, source)
            with self.subTest(old=old), self.assertRaises(ValueError):
                d.core_equivalence(candidate=source.replace(old, new, 1))
        original = Path(d.frozen.__file__).read_text()
        with self.assertRaises(ValueError): d.core_equivalence(original=original.replace('report.get(k) != v', 'True', 1))

    def test_original_full_synthetic_fixture_recounts_and_rejects_raw_policy_tamper(self):
        from scripts.test_p106b_public_qa_supply import StorageTests
        fixture = StorageTests('test_saved_inventory_check_recounts_raw_and_rejects_count_or_policy_tamper')
        result = unittest.TestResult()
        with patch.object(d.frozen, 'check', d.check_inventory), redirect_stdout(io.StringIO()):
            fixture.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])


class EntryTests(unittest.TestCase):
    def test_actual_three_phase_pipeline_devnull_timeout_and_failure_receipts(self):
        phases = d.phase_commands()
        self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        for failed, code in ((None, 0), (0, 1), (1, 8), (2, 9), (2, 130)):
            values = [subprocess.CompletedProcess([], 0) for _ in range(3)]
            if failed is not None: values[failed] = subprocess.CompletedProcess([], code)
            with patch.object(d.subprocess, 'run', side_effect=values) as launch, redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(d.run_pipeline(), code)
            count = 3 if failed is None else failed + 1
            self.assertEqual(launch.call_count, count)
            self.assertTrue(all(c.kwargs['stdin'] == subprocess.DEVNULL and c.kwargs['timeout'] == 300 for c in launch.call_args_list))
            receipt = json.loads(next(line.split(' ', 1)[1] for line in stream.getvalue().splitlines() if line.startswith('[EXPERIMENT_FINAL] ')))
            self.assertEqual(receipt['main_experiment_invoked'], failed in (None, 2))

    def test_write_once_recovery_and_no_source_text_or_training_adoption(self):
        report = dict(cohorts={'2': dict(summary={'fixture': 1})}, cap_comparison={'fixture': 2})
        with patch.object(d, 'check_inventory', return_value=0) as check, \
                patch.object(d.frozen, 'required', return_value=report), \
                patch.object(d.frozen, 'write') as write, patch.object(d.frozen.data, 'digest', return_value='HASH'), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(d.run_check(), 0)
        check.assert_called_once_with()
        args = write.call_args.args
        self.assertEqual(args[0], d.frozen.EVIDENCE / 'raw_readback_v1.json')
        self.assertFalse(args[1]['model_loaded']); self.assertFalse(args[1]['training'])
        self.assertFalse(args[1]['source_text_or_qa_copied_to_output'])
        self.assertEqual(args[1]['existing29m_overlap'], 'NOT_MEASURED')
        self.assertEqual(args[1]['status'], 'FROZEN_INVENTORY_RAW_READBACK_COMPLETE')
        with patch.object(d.frozen, 'write', side_effect=FileExistsError('old preserved')), \
                patch.object(d, 'check_inventory', return_value=0), patch.object(d.frozen, 'required', return_value=report), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(['--execute']), 9)

    def test_check_only_and_errors_do_not_call_any_action(self):
        with patch.object(d, 'run_check') as action, patch.object(d, 'run_pipeline') as pipeline, redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(['--mode', 'check', '--check-only']), 0)
            action.assert_not_called(); pipeline.assert_not_called()
        with patch.object(d, 'run_check', side_effect=d.PrerequisitePending('missing')), redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(['--execute']), 8)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit): d.main([])
        for flags in (['--help'], ['--check-only']):
            p = subprocess.run([sys.executable, '-B', '-X', 'utf8', d.__file__, *flags],
                capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=20)
            self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == '__main__': unittest.main(verbosity=2)
