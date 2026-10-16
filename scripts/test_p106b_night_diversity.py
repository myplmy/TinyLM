"""Controller preflight, local geometry and no-presence-as-completion tests."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_diversity as d


class DiversityTests(unittest.TestCase):
    def test_independent_namespace_and_original_parent(self):
        self.assertNotEqual(d.CORPUS, d.qa.CORPUS)
        self.assertEqual(d.TAG, 'p106b_night_diversity_v1_s1337')
        self.assertEqual(d.data.PARENT_SHA, d.foundation.data.PARENT_SHA)
        self.assertEqual(d.checkpoint().name, 'm100s10_ko-en_night_p106b_night_diversity_v1_s1337.pt')
        self.assertNotEqual(d.checkpoint(), d.checkpoint(True))

    def test_failed_or_partial_cost_never_opens_full_training(self):
        with self.assertRaises(ValueError): d.cost_forecast(dict(status='ERROR', step_seconds=[1.] * 8))
        with self.assertRaises(ValueError): d.cost_forecast(dict(status='DIVERSITY_COST_COMPLETE', updates=7, step_seconds=[1.] * 8))

    def test_actual_successful_cost_requires_frozen_code_and_source(self):
        report = dict(status='DIVERSITY_COST_COMPLETE', updates=8, code_sha256={'a':'1'}, cpu_contract_sha256='CPU', step_seconds=[10.] + [2.] * 7)
        with patch.object(d, 'info', return_value=dict(code_sha256={'a':'1'})), patch.object(d.qa.data, 'digest', return_value='CPU'):
            self.assertEqual(d.cost_forecast(report), 1880.)
            with self.assertRaises(ValueError): d.cost_forecast(dict(report, cpu_contract_sha256='wrong'))
            with self.assertRaises(ValueError): d.cost_forecast(dict(report, code_sha256={'a':'changed'}))
            with self.assertRaises(ValueError): d.cost_forecast(dict(report, step_seconds=[10.] + [float('nan')] * 7))

    def test_existing_schedule_is_balanced_and_quarter_seed_changes_order(self):
        a = d.method.schedule(8192, 4096, 0); b = d.method.schedule(8192, 4096, 1)
        self.assertEqual(len(a), 160); self.assertEqual(len(b), 160)
        self.assertNotEqual(a, b)
        self.assertEqual(sum(len(m.indices) for g in a for m in g if m.kind == 'natural'), 8192)
        self.assertEqual(sum(len(m.indices) for g in a for m in g if m.kind == 'replay'), 4096)

    def test_completion_uses_status_and_validator_not_file_presence(self):
        with patch.object(d.other, 'completion', return_value=False) as complete:
            self.assertFalse(d.completed({}))
            self.assertEqual(complete.call_args.args[1], 'DIVERSITY_TRAIN_COMPLETE')
            self.assertTrue(callable(complete.call_args.args[2]))

    def test_complete_proof_rejects_wrong_exposure_checkpoint_and_partial_events(self):
        proof = dict(actual_exposure=dict(x_tokens=100, assistant_targets=20), initial_core_sha256='BODY')
        report = dict(code_sha256={'code':'X'}, updates=640, cpu_contract_sha256='HASH', initial_core_sha256='BODY',
            initializer_sha256=d.foundation.data.PARENT_SHA, actual_x_tokens=100, assistant_targets=20,
            native_x_tokens=5242880, padded_slots=83886080, pairs_seen=32768, natural_epoch=1, logical_quarters=4,
            actual_oom=False, checkpoint_written=True, checkpoint=str(d.checkpoint().relative_to(ROOT)),
            checkpoint_sha256='HASH', event_manifest=dict(rows=640))
        def try_report(value):
            def invoke(path, status, validator): validator(value); return True
            with patch.object(d.other, 'completion', side_effect=invoke): return d.completed(proof)
        with patch.object(d, 'info', return_value=dict(code_sha256={'code':'X'})), patch.object(d.qa.data, 'digest', return_value='HASH'), patch.object(d, 'verify'):
            self.assertTrue(try_report(report))
            for change in (dict(updates=639), dict(assistant_targets=21), dict(actual_x_tokens=101),
                           dict(pairs_seen=8192), dict(actual_oom=True), dict(checkpoint_written=False),
                           dict(event_manifest=dict(rows=8)), dict(initializer_sha256='OTHER')):
                with self.assertRaises(ValueError): try_report(dict(report, **change))


if __name__ == '__main__': unittest.main()
