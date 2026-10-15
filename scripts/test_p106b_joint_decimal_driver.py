from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from scripts import diag_p106b_joint_decimal as code


class JointDriver(unittest.TestCase):
    def test_nearest_rank_budget_and_complete_arm_exclusion(self):
        reports={a:dict(step_seconds=[100,1,2,3,4,5,6,7]) for a in code.ARMS}
        r=code.forecast(reports,15000)
        self.assertTrue(r['fits']);self.assertEqual(r['needed_sec'],2*(7*672+300)+3600)
        self.assertFalse(code.forecast(reports,1000)['fits'])
        self.assertLess(code.forecast(reports,15000,('digits0',))['needed_sec'],r['needed_sec'])

    def test_scope_restores_callbacks_beta_and_parameter_factory(self):
        original=code.driver.method.new_head;tag=code.driver.TAG;before=code.BETA
        with code.runtime('digits1'):
            self.assertEqual(code.BETA,1.);self.assertEqual(code.driver.TAG,code.TAG)
            self.assertIs(code.driver.method.new_head,code.owned_head)
            self.assertEqual(code.driver.method.maybe_flip(1217,'root',False),1217)
        self.assertEqual(code.BETA,before);self.assertIs(code.driver.method.new_head,original);self.assertEqual(code.driver.TAG,tag)


if __name__=='__main__':unittest.main()
