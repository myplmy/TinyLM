from datetime import datetime,timezone,timedelta
import unittest
from scripts import diag_p106b_qwen35_fixedshape as d


class FixedDriverContracts(unittest.TestCase):
    def test_official_evaluator_bytecode_is_reused_without_global_mutation(self):
        self.assertIs(d.EVALUATE.__code__,d.q.evaluate.__code__)
        self.assertIsNot(d.EVALUATE.__globals__,d.q.evaluate.__globals__)
        self.assertEqual(d.EVALUATE.__globals__['TAG'],d.TAG)
        self.assertNotEqual(d.q.TAG,d.TAG)

    def test_current_authority_phase_budget_preserves_cleanup_and_rejects_expired(self):
        self.assertEqual(d.phase_budget('canary',d.DEADLINE-timedelta(hours=2)),1200)
        self.assertEqual(d.phase_budget('full',d.DEADLINE-timedelta(hours=2)),6300)
        for now in [d.DEADLINE,d.DEADLINE-timedelta(minutes=16)]:
            with self.assertRaises(TimeoutError):d.phase_budget('cost',now)

    def test_forecast_requires_complete_finite_tasks_and_available_time(self):
        timing={n:1. for n in d.q.official.TASK_COUNTS}
        cost=dict(task_evaluation_seconds=timing,pre_evaluation_seconds=20.)
        r=d.full_forecast(cost,5000)
        self.assertGreater(r['seconds'],100);self.assertFalse(r['quality_claim'])
        with self.assertRaises(TimeoutError):d.full_forecast(cost,200)
        for bad in [{},dict(timing,piqa=float('nan'))]:
            with self.assertRaises(ValueError):d.full_forecast(dict(cost,task_evaluation_seconds=bad),5000)


if __name__=='__main__':unittest.main()
