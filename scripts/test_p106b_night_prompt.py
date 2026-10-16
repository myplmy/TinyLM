"""Small CPU contracts for the separate-mean prompt training controller."""
from pathlib import Path
import copy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_prompt as d


class PromptDriverTests(unittest.TestCase):
    def test_same_natural_occurrences_only_and_replay_has_no_prompt_labels(self):
        masks = [[[1, -100], [2, 3]], [[4], [5, 6]]]
        natural = SimpleNamespace(kind='natural', indices=(1, 0))
        replay = SimpleNamespace(kind='replay', indices=(0, 1))
        self.assertEqual(d.mask_micros(natural, masks), [[4], [5, 6], [1, -100], [2, 3]])
        self.assertEqual(d.mask_micros(replay, masks), [])
        self.assertEqual(d.prompt_denominator([natural, replay], masks), 6)
        with self.assertRaises(ValueError): d.mask_micros(SimpleNamespace(kind='other', indices=()), masks)

    def test_cost_requires_eight_actual_finite_steps_and_same_code(self):
        report = dict(updates=8, code_sha256={'file': 'A'}, actual_oom=False, checkpoint_written=False,
            status='PROMPT_COST_COMPLETE', step_seconds=[99.] + [2.] * 7)
        self.assertEqual(d.cost_estimate(report, {'file': 'A'}, 640), 2180.)
        for key, value in (('updates', 7), ('code_sha256', {}), ('actual_oom', True), ('checkpoint_written', True),
                           ('status', 'ERROR'), ('step_seconds', [2.] * 7)):
            with self.assertRaises(ValueError): d.cost_estimate(dict(report, **{key: value}), {'file': 'A'}, 640)
        for bad in (0., float('nan'), float('inf')):
            changed = copy.deepcopy(report); changed['step_seconds'][3] = bad
            with self.assertRaises(ValueError): d.cost_estimate(changed, {'file': 'A'}, 640)

    def test_registered_betas_and_namespace_do_not_mutate_previous_defaults(self):
        self.assertEqual(d.BETAS, dict(prompt0=0., prompt01=.1))
        self.assertNotEqual(d.CORPUS, d.qa.CORPUS)
        self.assertNotEqual(d.EVIDENCE, d.foundation.data.EVIDENCE)
        self.assertNotEqual(d.checkpoint('prompt0'), d.checkpoint('prompt01'))
        with self.assertRaises(ValueError): d.checkpoint('unknown')

    def test_presence_never_means_valid_completion(self):
        path = SimpleNamespace(exists=lambda: True)
        calls = []
        with patch.object(d.qa, 'required', return_value=dict(status='ERROR')):
            with self.assertRaises(ValueError): d.completion(path, 'COMPLETE', calls.append)
        self.assertFalse(calls)
        with patch.object(d.qa, 'required', side_effect=ValueError('partial JSON')):
            with self.assertRaises(ValueError): d.completion(path, 'COMPLETE', calls.append)
        with patch.object(d.qa, 'required', return_value=dict(status='COMPLETE')):
            self.assertTrue(d.completion(path, 'COMPLETE', calls.append))
        self.assertEqual(calls, [dict(status='COMPLETE')])
        with patch.object(d.qa, 'required', return_value=dict(status='COMPLETE')):
            with self.assertRaises(ValueError):
                d.completion(path, 'COMPLETE', lambda report: (_ for _ in ()).throw(ValueError('wrong conditions')))
        self.assertFalse(d.completion(SimpleNamespace(exists=lambda: False), 'COMPLETE', calls.append))


if __name__ == '__main__': unittest.main()
