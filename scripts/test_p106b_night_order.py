"""Independent order controller contracts without models, source data or GPU."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_order as d


class OrderRuntimeTests(unittest.TestCase):
    def test_same_training_geometry_and_independent_view_identity(self):
        with patch.object(d.qa.data, 'digest', return_value='HASH'):
            r = d.info()
        self.assertEqual(r['training_views'], [0, 3]); self.assertFalse(r['held_wrapper2_training'])
        self.assertEqual((r['micro_bs'], r['accum'], r['seq'], r['updates_planned']), (8, 16, 1024, 640))
        self.assertEqual(r['natural_epoch'], 1); self.assertEqual(r['schema'], 'P106B_NIGHT_FIELD_ORDER_ACTUAL_V1')
        self.assertNotEqual(d.CORPUS, d.diversity.CORPUS)

    def test_no_partial_or_failed_cost_opens_main(self):
        for r in ({}, dict(status='ORDER_COST_COMPLETE', updates=7, step_seconds=[1.] * 8)):
            with self.assertRaises(ValueError): d.cost_forecast(r)

    def test_cost_uses_actual_warm_max_and_same_cpu(self):
        r = dict(status='ORDER_COST_COMPLETE', updates=8, step_seconds=[30.] + [2.] * 7,
            code_sha256={'c':'1'}, cpu_contract_sha256='HASH')
        with patch.object(d, 'info', return_value=dict(code_sha256={'c':'1'})), patch.object(d.qa.data, 'digest', return_value='HASH'):
            self.assertEqual(d.cost_forecast(r), 1880.)
            with self.assertRaises(ValueError): d.cost_forecast(dict(r, cpu_contract_sha256='OTHER'))

    def test_original_recount_must_not_be_empty_status_only(self):
        from scripts import diag_p106b_night_eval_recovery as e
        audit = dict(status='RAW_RECOUNTED', errors=0, code_sha256={'c':'1'}, endpoints_sha256={})
        with patch.object(d.qa, 'required', return_value=audit), patch.object(e, 'info', return_value=dict(code_sha256={'c':'1'})):
            with self.assertRaisesRegex(ValueError, 'endpoint set'): d.finished_original_work()

    def test_complete_contract_rejects_old_views_or_claimed_held_training(self):
        proof = dict(actual_exposure=dict(x_tokens=100, assistant_targets=20), initial_core_sha256='BODY')
        r = dict(code_sha256={'c':'1'}, updates=640, cpu_contract_sha256='HASH', initial_core_sha256='BODY',
            initializer_sha256=d.foundation.data.PARENT_SHA, actual_x_tokens=100, assistant_targets=20,
            native_x_tokens=5242880, padded_slots=83886080, pairs_seen=32768, natural_epoch=1, logical_quarters=4,
            training_views=[0, 3], held_wrapper2_training=False, actual_oom=False, checkpoint_written=True,
            checkpoint=str(d.checkpoint().relative_to(ROOT)), checkpoint_sha256='HASH', event_manifest=dict(rows=640))
        def invoke(value):
            def complete(path, status, validator): validator(value); return True
            with patch.object(d.other, 'completion', side_effect=complete): return d.completed(proof)
        with patch.object(d, 'info', return_value=dict(code_sha256={'c':'1'})), patch.object(d.qa.data, 'digest', return_value='HASH'), patch.object(d, 'verify'):
            self.assertTrue(invoke(r))
            with self.assertRaises(ValueError): invoke(dict(r, training_views=[0, 1]))
            with self.assertRaises(ValueError): invoke(dict(r, held_wrapper2_training=True))


if __name__ == '__main__': unittest.main()
