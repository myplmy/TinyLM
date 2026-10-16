"""Independent namespace/complete endpoint and native-unit CPU contracts."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_diversity_eval as d


class DiversityEvalTests(unittest.TestCase):
    def test_two_endpoints_independent_and_reject_unknown(self):
        self.assertEqual(d.ENDPOINTS, ('unique32k', 'unique32k_best'))
        self.assertNotEqual(d.FROZEN, d.evaluation.FROZEN)
        with self.assertRaises(ValueError): d.checkpoint_spec('other')

    def test_missing_lanes_never_complete(self):
        r = dict(status='ACTUAL_EVALUATION_COMPLETE', endpoint='unique32k', updates=0,
            checkpoints_written=0, body_unchanged=True,
            directory=str((d.LOCAL / 'unique32k').relative_to(ROOT)), outputs={}, receipt_sha256={})
        with self.assertRaises(ValueError): d.endpoint_contract(r, 'unique32k', {})

    def test_native_actual_units_not_rows(self):
        inputs = dict(native_val_sha256='V', native256_val_offsets=[32])
        r = dict(ce=3., val_sha256='V', crops=32, targets=32768)
        d.evaluation.native_contract('native32', r, inputs)
        with self.assertRaises(ValueError): d.evaluation.native_contract('native32', dict(r, targets=32), inputs)

    def test_eval_preserves_old_source_and_does_not_train(self):
        self.assertTrue(callable(d.evaluation.lane_events)); self.assertTrue(callable(d.training.completed))
        self.assertEqual(d.training.info()['natural_epoch'], 1)
        self.assertEqual(d.training.info()['logical_quarters'], 4)
        self.assertEqual(d.training.info()['updates_planned'], 640)


if __name__ == '__main__': unittest.main()
