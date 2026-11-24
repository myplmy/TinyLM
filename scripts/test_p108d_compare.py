"""Known ray bounds and physical support budgets independent of the model."""
import unittest
import numpy as np
from scripts import p108d_compare as comparison


class PhysicalCompareContracts(unittest.TestCase):
    def test_ray_has_lower_and_upper_bound(self):
        result=comparison.ray_interval(np.array([[0.,1.],[2.,0.]]),
            np.array([[2.,0.],[-1.,0.]]),np.array([0,0]),np.array([.1,.1]))
        self.assertAlmostEqual(result["lower"],.55)
        self.assertAlmostEqual(result["upper"],1.9)

    def test_uncontrollable_class_difference_is_rejected(self):
        result=comparison.ray_interval(np.array([[0.,1.]]),np.zeros((1,2)),np.array([0]),np.array([.1]))
        self.assertEqual(result["status"],"NO_FEASIBLE_RAY_ZERO_SLOPE")

    def test_actual_net_matching_keeps_support(self):
        before=np.ones((3,4),dtype=np.float32)
        direction=np.zeros((3,4));direction[:,1]=[1.,2.,3.]
        after,actual,result=comparison.match_norm(before,direction,.73)
        self.assertAlmostEqual(float(np.linalg.norm(actual)),.73,places=6)
        self.assertTrue(np.all(actual[:,[0,2,3]]==0))
        self.assertEqual(result["comparison"],"MATCHED_ACTUAL_NET")

    def test_ties_select_smaller_coordinate_and_random_is_fixed(self):
        delta=np.ones((2,8));protected=np.ones((3,8))
        selected,_=comparison.column_selection(delta,protected,3)
        np.testing.assert_array_equal(selected,[0,1,2])
        a,_=comparison.column_selection(delta,protected,3,seed=1337)
        b,_=comparison.column_selection(delta,protected,3,seed=1337)
        np.testing.assert_array_equal(a,b)

    def test_score_uses_normal_cost_instead_of_energy_alone(self):
        delta=np.array([[2.,1.]])
        selected,_=comparison.column_selection(delta,np.array([[10.,1.]]),1)
        np.testing.assert_array_equal(selected,[1])

    def test_zero_direction_cannot_be_called_equal_budget(self):
        with self.assertRaises(ValueError):comparison.match_norm(np.zeros((2,2),np.float32),np.zeros((2,2)),1.)

    def test_ray_repair_is_checked_after_fp32_materialization(self):
        before=np.zeros((2,1),np.float32)
        direction=np.array([[.59999],[-.59999]])
        after,diagnostic=comparison.repair_ray(before,direction,np.eye(2),np.array([[0.,1.]]),
            np.ones((1,1)),np.array([0]),1.,np.array([.2]),.36)
        self.assertIsNotNone(after)
        self.assertLessEqual(diagnostic["maximum_raw_violation"],0.)
        self.assertTrue(diagnostic["minimum_norm_numeric_gap_confirmed"])


if __name__=="__main__":unittest.main()
