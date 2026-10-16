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


if __name__ == '__main__': unittest.main()
