"""CPU preflight for bounded causal-KD cost driver, no model construction."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import tinylm
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import diag_p107_causal_kd_cost as driver


class KdDriverTests(unittest.TestCase):
    def test_current_deadline_and_no_old_default_implicit(self):
        self.assertEqual(driver.DEADLINE.isoformat(),'2026-11-01T06:00:00+00:00')
        self.assertIs(driver.base.cost,driver.cost)
        self.assertEqual(driver.ORDER,('none','causal_kl','causal_kl','none'))
        self.assertLess(driver.ALLOCATOR_CAP,driver.LIMIT)

    def test_identity_includes_kl_and_old_product_loss(self):
        names=driver.base.identity()['files']
        for name in ('causal_teacher.py','adaptive_training.py','trainer.py','hybrid_session.py'):
            self.assertIn('tinylm/train/'+name,names)

    def test_wrong_contract_refused_without_model(self):
        args=SimpleNamespace(profile='fixture',profile_sha256='x',mode='cost',max_wall_sec=900)
        with patch.object(driver.base.resource,'read_ref',return_value=dict(schema='wrong')):
            with self.assertRaises(ValueError):driver.validate(args)

    def test_telemetry_reports_actual_limit_and_no_gpu_queries_here(self):
        watch=driver.KdWatch()
        proof=watch.stop()
        self.assertEqual(proof['policy']['shared_increment_limit_bytes'],driver.LIMIT)
        self.assertEqual(proof['client']['successful_queries'],0)


if __name__=='__main__':unittest.main()
