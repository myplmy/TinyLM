"""Real shared-pipeline connection tests; no model, source, tokenizer or GPU."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from scripts import p106b_subject_role_entry as entry


class PhaseTests(unittest.TestCase):
    def cases(self):
        for mode in ('prepare', 'preflight', 'readback', 'budget'):
            yield dict(mode=mode)
        for mode in ('cost', 'train'):
            for arm in entry.ARMS:
                yield dict(mode=mode, arm=arm)
        for endpoint in ('parent', *entry.ARMS):
            yield dict(mode='evaluate', endpoint=endpoint)
        for model in ('ce', 'contrast'):
            yield dict(mode='probe_old', model=model)

    def test_every_phase_executes_the_real_three_phase_pipeline(self):
        for values in self.cases():
            with self.subTest(values=values), patch.object(entry.subprocess, 'run') as launch:
                launch.return_value.returncode = 0
                with contextlib.redirect_stdout(io.StringIO()) as stream:
                    self.assertEqual(entry.run(**values), 0)
                commands = entry.phase_commands(**values)
                self.assertEqual([x[0] for x in commands], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
                self.assertEqual([c.args[0] for c in launch.call_args_list], [x[1] for x in commands])
                self.assertTrue(all(c.kwargs['stdin'] == subprocess.DEVNULL for c in launch.call_args_list))
                self.assertTrue(all(c.kwargs['timeout'] == 7800 for c in launch.call_args_list))
                receipt = next(line for line in stream.getvalue().splitlines() if line.startswith('[EXPERIMENT_FINAL] '))
                self.assertEqual(json.loads(receipt.split(' ', 1)[1])['status'], 'COMPLETE')

    def test_preparation_does_not_require_uncreated_corpus(self):
        phases = entry.phase_commands('prepare')
        self.assertEqual(phases[1][1][-1], '--check-only')
        self.assertIn('prepare', phases[1][1])
        self.assertIn('--execute', phases[2][1])
        self.assertEqual(entry.phase_commands('train', arm='ce')[1][1][-3:],
                         ['--mode', 'preflight', '--execute'])

    def test_failure_stops_later_phases_and_never_promotes_hold(self):
        for index in range(3):
            for code in (1, 8, 9, 130):
                with self.subTest(index=index, code=code), patch.object(entry.subprocess, 'run') as launch:
                    launch.side_effect = [subprocess.CompletedProcess([], 0)] * index + [subprocess.CompletedProcess([], code)]
                    with contextlib.redirect_stdout(io.StringIO()) as stream:
                        # A regression process returning8 is still a broken
                        # regression, not missing GPU/data prerequisites.
                        expected = 9 if index == 0 and code == 8 else code
                        self.assertEqual(entry.run('train', arm='all_axes'), expected)
                    self.assertEqual(launch.call_count, index + 1)
                    receipt = next(line for line in stream.getvalue().splitlines() if line.startswith('[EXPERIMENT_FINAL] '))
                    value = json.loads(receipt.split(' ', 1)[1])
                    self.assertNotEqual(value['status'], 'COMPLETE')
                    self.assertEqual(value['main_experiment_invoked'], index == 2)

    def test_invalid_selectors_and_nonfinite_or_unbounded_budgets_refused(self):
        bad = [dict(mode='cost'), dict(mode='train', arm='contrast'),
            dict(mode='prepare', arm='ce'), dict(mode='evaluate'),
            dict(mode='evaluate', endpoint='contrast'), dict(mode='readback', endpoint='ce'),
            dict(mode='probe_old'), dict(mode='probe_old', model='all_axes'),
            dict(mode='prepare', model='ce'), dict(mode='missing')]
        for wall in (True, 0, 59, 21601, 3.5):
            bad.append(dict(mode='prepare', max_wall_sec=wall))
        for hours in (True, 0, -1., float('inf'), float('nan'), 8.001, 25.):
            bad.append(dict(mode='prepare', budget_hours=hours))
        for values in bad:
            with self.subTest(values=values), self.assertRaises(ValueError):
                entry.phase_commands(**values)

    def test_check_only_uses_no_children_and_validates_selectors(self):
        with patch.object(entry.subprocess, 'run') as launch:
            with contextlib.redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(entry.main(['--mode', 'cost', '--arm', 'ce', '--check-only']), 0)
            value = json.loads(stream.getvalue())
            self.assertFalse(value['model_loaded']); self.assertFalse(value['source_read'])
            self.assertEqual(launch.call_count, 0)
        for args in (['--mode', 'prepare'], ['--mode', 'train', '--check-only'],
                     ['--mode', 'prepare', '--execute', '--check-only']):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                entry.main(args)

    def test_timeout_and_interrupt_are_not_success(self):
        for exc, code in ((subprocess.TimeoutExpired(['fixture'], 60), 9),
                          (FileNotFoundError('fixture'), 9), (KeyboardInterrupt(), 130)):
            with patch.object(entry.subprocess, 'run', side_effect=exc), contextlib.redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(entry.run('prepare'), code)
            receipt = next(line for line in stream.getvalue().splitlines() if line.startswith('[EXPERIMENT_FINAL] '))
            value = json.loads(receipt.split(' ', 1)[1])
            self.assertEqual(value['returncode'], code)
            self.assertFalse(value['main_experiment_invoked'])

    def test_source_free_cli_help_and_check_only(self):
        script = Path(entry.__file__)
        for flags in (['--help'], ['--mode', 'prepare', '--check-only'],
                      ['--mode', 'probe_old', '--model', 'contrast', '--check-only']):
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(script), *flags],
                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
