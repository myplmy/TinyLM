import unittest
import numpy as np
from scripts import p108e_span_control as study


class AffineOffsetContracts(unittest.TestCase):
    def test_nonzero_offset_is_not_lost_by_head_projection(self):
        theta,record=study.solve(np.array([[1.],[-1.]]),np.array([[0.,1.]]),np.ones((1,1)),
            np.array([0]),1.,np.array([.2]),10.)
        self.assertAlmostEqual(theta[0,0],.6,places=6)
        self.assertEqual(record["correct"],1)

    def test_previous_competitor_remains_after_a_new_one_is_added(self):
        head=np.array([[1.,0.],[0.,0.],[1.,1.]])
        theta,record=study.solve(head,np.array([[0.,1.,0.]]),np.ones((1,1)),np.array([0]),1.,np.array([.1]),10.)
        self.assertGreaterEqual(len(record["constraints"]),2)
        self.assertEqual(record["correct"],1)
        self.assertGreaterEqual(theta[0,0],1.1-1e-6)
        self.assertLessEqual(theta[1,0],-.1+1e-6)

    def test_budget_failure_is_not_relabelled_mathematical_impossibility(self):
        theta,record=study.solve(np.array([[1.],[-1.]]),np.array([[0.,10.]]),np.ones((1,1)),
            np.array([0]),1.,np.array([.2]),1.)
        self.assertNotEqual(record["status"],"ALL_AFFINE_WINNER_CONSTRAINTS_FEASIBLE")
        self.assertLessEqual(np.linalg.norm(theta),1.)


if __name__=="__main__":unittest.main()
