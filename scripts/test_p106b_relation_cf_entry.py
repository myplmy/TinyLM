import contextlib
import io
import subprocess
import sys
import unittest
from unittest.mock import patch
from scripts import p106b_relation_cf_entry as entry


class EntryTests(unittest.TestCase):
    def test_prepare_uses_real_check_and_source_action(self):
        phases = entry.phase_commands('prepare')
        self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertEqual(phases[1][1][-1], '--check-only')
        self.assertEqual(phases[2][1][-1], '--execute')
        self.assertNotIn('--model', phases[2][1])

    def test_each_endpoint_and_bounded_wall_reach_real_driver(self):
        for label in ('parent', 'ce', 'contrast'):
            phases = entry.phase_commands('evaluate', label, 720)
            command = phases[2][1]
            self.assertEqual(command[command.index('--model') + 1], label)
            self.assertEqual(command[command.index('--max-wall-sec') + 1], '720')

    def test_invalid_dispatch_is_rejected(self):
        for args in (('prepare', 'ce'), ('readback', 'parent'), ('evaluate', None),
                     ('train', None), ('evaluate', 'ce', 0)):
            with self.assertRaises(ValueError): entry.phase_commands(*args)

    def test_early_failure_preserves_receipt_and_no_execute(self):
        calls = []
        def fake(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 9)
        output = io.StringIO()
        with patch.object(entry.subprocess, 'run', side_effect=fake), contextlib.redirect_stdout(output):
            self.assertEqual(entry.run('prepare'), 9)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][1]['stdin'], subprocess.DEVNULL)
        self.assertIn('[EXPERIMENT_FINAL]', output.getvalue())
        self.assertIn('NOT_RUN', output.getvalue())

    def test_fresh_process_check_only_no_driver_execution(self):
        result = subprocess.run([sys.executable, '-I', '-B',
            str(entry.ROOT / 'scripts/p106b_relation_cf_entry.py'), '--mode', 'evaluate',
            '--model', 'ce', '--check-only'], cwd=entry.ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"model_loaded": false', result.stdout)
        self.assertNotIn('[PHASE_BEGIN]', result.stdout)


if __name__ == '__main__': unittest.main()
