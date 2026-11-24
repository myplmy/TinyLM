"""Independent polynomial and numerical-tie counterexamples."""
import unittest
import numpy as np
from scripts import p108e_endpoint_prediction as prediction


class EndpointContracts(unittest.TestCase):
    def test_asymmetric_actual_steps_recover_quadratic(self):
        before=np.array([[2.,3.],[-4.,5.]])
        linear=np.array([[1.,2.],[3.,4.]])
        quadratic=np.array([[.5,-.3],[.7,.8]])
        a,b=.00301,-.00299
        d,q=prediction.secants(before,before+a*linear+a*a*quadratic,
            before+b*linear+b*b*quadratic,a,b)
        np.testing.assert_allclose(d,linear,atol=1e-11)
        np.testing.assert_allclose(q,quadratic,atol=1e-9)

    def test_collapsed_or_wrong_sign_step_is_rejected(self):
        z=np.zeros((2,3))
        for a,b in ((0.,-.1),(.1,.2),(.1,0.)):
            with self.assertRaises(ValueError):prediction.secants(z,z,z,a,b)

    def test_solver_tiny_hinge_does_not_override_fixed_tie(self):
        rows=[dict(layer=12,score=dict(questions_all_gold=24,mean_hinge=2e-9)),
              dict(layer=13,score=dict(questions_all_gold=24,mean_hinge=2e-10)),
              dict(layer=0,score=dict(questions_all_gold=23,mean_hinge=0.))]
        self.assertEqual(prediction.choose(rows)["layer"],12)

    def test_physical_coordinate_separates_perpendicular_rounding(self):
        result=prediction.physical_coordinate(np.zeros((1,2)),np.array([[.6,.01]]),np.array([[2.,0.]]))
        self.assertAlmostEqual(result["scalar"],.3)
        self.assertAlmostEqual(result["orthogonal_rounding_norm"],.01)


if __name__=="__main__":unittest.main()
