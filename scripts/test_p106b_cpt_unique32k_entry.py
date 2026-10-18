#!/usr/bin/env python3
"""CPU-only fourth-cell phase and shared receipt regression."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import subprocess
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch
from scripts import p106b_cpt_unique32k_entry as entry


class FourthCellEntryTests(unittest.TestCase):
    def test_prepare_freezes_training_in_exact_three_phases(self):
        phases = entry.phase_commands('prepare')
        self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertIn('--check-only', phases[1][1])
        self.assertEqual(phases[2][1][-3:], ['--mode', 'prepare', '--execute'])

    def test_evaluation_freeze_is_a_separate_standard_phase(self):
        phases = entry.phase_commands('prepare_eval')
        self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertEqual(phases[1][1][-3:], ['--mode', 'preflight', '--execute'])
        self.assertEqual(phases[2][1][-3:], ['--mode', 'freeze', '--execute'])

    def test_every_mode_invokes_real_shared_pipeline_with_exact_three_children(self):
        for mode in entry.MODES:
            runner = Mock(return_value=subprocess.CompletedProcess([], 0))
            with patch.object(entry.subprocess, 'run', runner), redirect_stdout(StringIO()):
                self.assertEqual(entry.run(mode), 0, mode)
            self.assertEqual(runner.call_count, 3, mode)
            self.assertTrue(all(call.kwargs['stdin'] is subprocess.DEVNULL for call in runner.call_args_list))

    def test_old_four_phase_prepare_is_rejected_before_any_launch(self):
        malformed = entry.phase_commands('prepare') + [('EVALUATION_FREEZE', ['not-run'])]
        with patch.object(entry, 'phase_commands', return_value=malformed), \
                patch.object(entry.subprocess, 'run') as launch, redirect_stdout(StringIO()):
            with self.assertRaisesRegex(ValueError, 'three exact phases'):
                entry.run('prepare')
        launch.assert_not_called()

    def test_cost_and_train_are_fresh_explicit_bounded_phases(self):
        for mode, bound in (('cost', '3600'), ('train', '10800')):
            phases = entry.phase_commands(mode)
            self.assertEqual(phases[1][1][-3:], ['--mode', 'preflight', '--execute'])
            self.assertIn(bound, phases[2][1])
            self.assertEqual(phases[2][1][-1], '--execute')

    def test_final_and_dev_endpoints_are_not_interchanged(self):
        for mode, expected in (('eval_final', 'cpt_unique32k'), ('eval_best', 'cpt_unique32k_best')):
            command = entry.phase_commands(mode)[-1][1]
            self.assertEqual(command[command.index('--endpoint') + 1], expected)

    def test_readback_is_cpu_driver_not_training(self):
        command = entry.phase_commands('readback')[-1][1]
        self.assertIn('scripts/diag_p106b_cpt_unique32k_eval.py', command)
        self.assertEqual(command[-3:], ['--mode', 'readback', '--execute'])

    def test_unregistered_mode_rejected(self):
        with self.assertRaises(ValueError):
            entry.phase_commands('resume-old-expired-night')

    def test_shared_pipeline_stops_and_preserves_negative_status(self):
        runner = Mock(side_effect=[subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 8)])
        with patch.object(entry.subprocess, 'run', runner), redirect_stdout(StringIO()):
            self.assertEqual(entry.run('train'), 8)
        self.assertEqual(runner.call_count, 2)
        self.assertTrue(all(call.kwargs['stdin'] is subprocess.DEVNULL for call in runner.call_args_list))

    def test_metadata_check_never_launches_subprocess(self):
        with patch.object(sys, 'argv', ['entry', '--mode', 'prepare', '--check-only']), \
                patch.object(entry.subprocess, 'run') as runner, redirect_stdout(StringIO()):
            self.assertEqual(entry.main(), 0)
        runner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
