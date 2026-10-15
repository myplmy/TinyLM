from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from unittest.mock import patch
from scripts import diag_p106b_state_update_aux as code


class Driver(unittest.TestCase):
    def test_cost_nearest_rank_and_deadline_margins(self):
        reports={a:dict(step_seconds=[100,1,2,3,4,5,6,7]) for a in code.ARMS}
        r=code.forecast(reports,11000)
        self.assertEqual(r['arms']['aux0']['p95'],7);self.assertTrue(r['fits'])
        self.assertEqual(r['needed_sec'],2*(7*416+300)+3600)
        self.assertFalse(code.forecast(reports,100)['fits'])
        self.assertFalse(code.forecast(reports,10000)['fits'])
        self.assertLess(code.forecast(reports,11000,('aux0',))['needed_sec'],r['needed_sec'])

    def test_runtime_callbacks_restore_without_model_load(self):
        original=code.driver.method.suffix_auxiliary_sum;tag=code.driver.TAG;loader=code.driver.base.training.load_runtime
        with code.runtime():
            self.assertEqual(code.driver.TAG,code.TAG)
            self.assertIs(code.driver.method.suffix_auxiliary_sum,code.method.final_auxiliary_sum)
            self.assertIs(code.driver.base.training.load_runtime,code.load_from_parent)
        self.assertEqual(code.driver.TAG,tag);self.assertIs(code.driver.method.suffix_auxiliary_sum,original)
        self.assertIs(code.driver.base.training.load_runtime,loader)


if __name__=='__main__':unittest.main()
