#!/usr/bin/env python3
"""No model/child process: phase binding, noninteractive launch and final verdict."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contextlib import redirect_stdout
import io
import subprocess
import unittest
from unittest.mock import patch
from scripts import p106b_relation_bind_entry as e


class EntryTests(unittest.TestCase):
    def test_exact_phase_order_and_explicit_matching_arms(self):
        for mode in e.MODES:
            phases = e.phase_commands(mode)
            self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
            self.assertIn('--execute', phases[2][1])
            if mode.startswith(('cost_', 'train_')):
                phase, arm = mode.split('_', 1)
                self.assertEqual(phases[2][1][phases[2][1].index('--arm') + 1], arm)
                self.assertEqual(phases[2][1][phases[2][1].index('--mode') + 1], phase)
            self.assertFalse(any('input(' in str(p) for p in phases))
        with self.assertRaises(ValueError): e.phase_commands('unregistered')

    def test_subprocess_stdin_is_disabled_and_failure_keeps_execute_not_run(self):
        notes = io.StringIO()
        with patch.object(e.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0),
                                                          subprocess.CompletedProcess([], 8)]) as child, redirect_stdout(notes):
            rc = e.run('cost_ce')
        self.assertEqual(rc, 8); self.assertEqual(child.call_count, 2)
        for call in child.call_args_list: self.assertIs(call.kwargs['stdin'], subprocess.DEVNULL)
        self.assertIn('"main_experiment_invoked": false', notes.getvalue())
        self.assertIn('"status": "NOT_RUN"', notes.getvalue())

    def test_complete_receipt_is_phase_completion_not_quality(self):
        notes = io.StringIO()
        with patch.object(e.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), redirect_stdout(notes):
            self.assertEqual(e.run('prepare'), 0)
        self.assertIn('CPU data preparation only', notes.getvalue())
        self.assertIn('"status": "COMPLETE"', notes.getvalue())
        self.assertIn('not model quality', notes.getvalue())

    def test_check_only_never_launches_children(self):
        with patch.object(sys, 'argv', ['entry', '--mode', 'train_contrast', '--check-only']), \
                patch.object(e.subprocess, 'run', side_effect=AssertionError('child execution forbidden')), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(e.main(), 0)


if __name__ == '__main__': unittest.main(verbosity=2)
