#!/usr/bin/env python3
"""Pure/mock native TF signal contracts; no model or GPU."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import diag_p106b_teacher_tf as m


def reply(chosen=12, value=-3.0):
    return dict(completion_probabilities=[dict(id=chosen, logprob=value,
        top_logprobs=[dict(id=11, logprob=-1.0), dict(id=12, logprob=-3.0)])])


class TFContracts(unittest.TestCase):
    def test_native_request_has_correct_unbiased_keys_and_integer_prefix(self):
        value = m.payload([1, 2], 12, 100)
        self.assertEqual(value['logit_bias'], [[12, 100]])
        self.assertEqual(value['n_predict'], 1)
        self.assertFalse(value['post_sampling_probs'])
        self.assertFalse(value['cache_prompt'])
        self.assertNotIn('max_tokens', value)
        self.assertNotIn('logprobs', value)
        for ids in ([], [True], [-1], ['1'], [1] * 1024):
            with self.assertRaises(ValueError): m.payload(ids)

    def test_profile_command_explicitly_disables_mtp_and_preserves_other_flags(self):
        command = ['server', '--ctx-size', '8192', '--spec-type', 'draft-mtp',
            '--spec-draft-n-max', '2', '--model', 'unchanged']
        profile = SimpleNamespace(command=lambda port, key: list(command))
        actual = m.command(profile, 1, 'key')
        self.assertEqual(actual[actual.index('--spec-type')+1], 'none')
        self.assertNotIn('--spec-draft-n-max', actual)
        self.assertEqual(actual[actual.index('--ctx-size')+1], '1024')
        self.assertEqual(command[command.index('--spec-type')+1], 'draft-mtp')

    def test_pre_sampling_schema_and_independent_absolute_probability(self):
        base = m.probability_entry(reply(11, -1.0))
        actual = [(b, m.probability_entry(reply())) for b in m.BIASES]
        result = m.evaluate_forcing(base['top'][1], actual)
        self.assertTrue(result['passed'])
        changed = copy.deepcopy(actual); changed[1][1]['chosen']['logprob'] = -0.01
        self.assertFalse(m.evaluate_forcing(base['top'][1], changed)['passed'])

    def test_wrong_forced_id_is_not_read_as_target_logprob(self):
        observations = [(b, m.probability_entry(reply(11, -1.0))) for b in m.BIASES]
        result = m.evaluate_forcing(dict(id=12, logprob=-3.0), observations)
        self.assertFalse(result['passed'])
        self.assertTrue(all(r['status'] == 'NOT_FORCED' and r['target_logprob'] is None for r in result['rows']))

    def test_equal_selected_probability_cannot_hide_changed_raw_top_values(self):
        base = m.probability_entry(reply(11, -1.0))
        observations = [(b, m.probability_entry(reply())) for b in m.BIASES]
        self.assertTrue(m.evaluate_forcing(base['top'][1], observations, base['top'])['passed'])
        observations[0][1]['top'][0]['logprob'] = -0.1
        self.assertFalse(m.evaluate_forcing(base['top'][1], observations, base['top'])['passed'])

    def test_sentinel_underflow_nonfinite_and_post_sampling_prob_refused(self):
        for value in (-3.402823e38, float('-inf'), float('nan'), True, 1.0, 'bad'):
            with self.subTest(value=value), self.assertRaises(ValueError): m.probability_entry(reply(value=value))
        for bad in ({}, dict(choices=[]), dict(completion_probabilities=[]),
                    dict(completion_probabilities=[dict(id=12, prob=0.5, top_probs=[])])):
            with self.assertRaises(ValueError): m.probability_entry(bad)

    def test_duplicate_top_ids_and_noninteger_ids_refused(self):
        bad = reply(); bad['completion_probabilities'][0]['top_logprobs'][1]['id'] = 11
        with self.assertRaises(ValueError): m.probability_entry(bad)
        bad = reply(); bad['completion_probabilities'][0]['id'] = True
        with self.assertRaises(ValueError): m.probability_entry(bad)

    def test_check_only_never_calls_runtime_or_assets(self):
        output = io.StringIO()
        with patch.object(m, 'sources', return_value={'mock': 'A'*64}), \
             patch.object(m, 'execute', side_effect=AssertionError('model/GPU')), patch('sys.stdout', output):
            self.assertEqual(m.main(['--check-only']), 0)
        result = json.loads(output.getvalue())
        self.assertEqual((result['model_loads'], result['gpu_calls'], result['asset_reads']), (0, 0, 0))

    def test_reports_are_write_once_and_bounded(self):
        with tempfile.TemporaryDirectory(prefix='p106b_tf_test_') as directory:
            path = Path(directory) / 'report.json'; m.write_report(path, {'state': 'first'})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError): m.write_report(path, {'state': 'second'})
            self.assertEqual(path.read_bytes(), before)

    def test_failed_request_preserves_attempt_without_counting_a_success(self):
        writer = Mock()
        session = SimpleNamespace(key='SECRET', request=Mock(side_effect=TimeoutError('timeout SECRET')))
        report = dict(http_attempted=0, http_succeeded=0, completion_attempted=0, requests=0)
        with self.assertRaises(TimeoutError):
            m.recorded_request(session, writer, report, '/completion', {'prompt':[1]}, 'base')
        self.assertEqual(report, dict(http_attempted=1, http_succeeded=0, completion_attempted=1, requests=0))
        calls = [call.args[0] for call in writer.append.call_args_list]
        self.assertEqual([r['event'] for r in calls], ['request_attempt','request_failed'])
        self.assertEqual(calls[0]['payload'], {'prompt':[1]})
        self.assertNotIn('SECRET', json.dumps(calls))


if __name__ == '__main__': unittest.main()
