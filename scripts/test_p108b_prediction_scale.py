"""Directional quadratic calibration and explicit invalid-input rejection."""
import unittest
from scripts import diag_p108b_prediction_scale as p


class PredictionTests(unittest.TestCase):
    def test_calibration_recovers_quadratic_and_predicts_unseen_step(self):
        loss=lambda x:5-2*x+3*x*x
        h=1/32;q=p.curvature(loss(0),loss(h),loss(-h),h)
        self.assertAlmostEqual(q,6)
        alpha=.25;r=p.predictions(2*alpha,q,alpha,5)
        self.assertAlmostEqual(r['quadratic'],loss(0)-loss(alpha))
        self.assertNotAlmostEqual(r['linear'],loss(0)-loss(alpha))

    def test_loss_bound_is_separate_and_negative_prediction_not_silently_erased(self):
        r=p.predictions(10,40,.5,3)
        self.assertEqual(r['linear'],10);self.assertEqual(r['bounded_linear'],3)
        self.assertEqual(p.predictions(1,40,.5,3)['quadratic'],-4)
        with self.assertRaises(ValueError):p.curvature(1,2,3,0)
        with self.assertRaises(ValueError):p.predictions(float('nan'),1,.5,3)


if __name__=='__main__':unittest.main()
