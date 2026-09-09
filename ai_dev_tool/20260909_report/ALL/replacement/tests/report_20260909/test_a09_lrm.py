import unittest
from tinylm.eval.lrm_diagnostics import history_floor, describe_motion


class LrmTests(unittest.TestCase):
    def test_wd_zero_identity(self):
        rows = [{"step": i, "applied": True, "lrm_lr": .1, "lrm_weight_decay": 0}
                for i in range(4)]
        self.assertEqual(history_floor(rows, 4), 1)
        r = describe_motion([1.256241], 1)
        self.assertAlmostEqual(r["max_abs_from_one"], r["max_abs_ratio_from_wd_only"])

    def test_skipped_step_and_checkpoint_boundary(self):
        rows = [{"step": i, "applied": i != 1, "lrm_lr": .1, "lrm_weight_decay": .2}
                for i in range(5)]
        self.assertAlmostEqual(history_floor(rows, 3), .98 ** 2)

    def test_missing_history_and_floor_do_not_make_a_quality_pass(self):
        with self.assertRaises(ValueError):
            history_floor([], 3)
        result = describe_motion([1.2], None)
        self.assertEqual(result["motion_band"], "unresolved")
        self.assertIsNone(result["quality_verdict"])
