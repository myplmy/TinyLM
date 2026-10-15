from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from scripts.diag_p106b_validation_cost import projection,new_head


class ValidationProjection(unittest.TestCase):
    def test_actual_state_and_joint_head_factories(self):
        self.assertEqual(tuple(new_head('state',12).weight.shape),(2,12))
        self.assertEqual(tuple(new_head('joint',12).weight.shape),(34,12))

    def test_validation_is_charged_per_epoch_not_once(self):
        value=projection(2.,416,100.)
        self.assertEqual(value['estimated_train_sec'],832+600+300)
        self.assertEqual(value['epochs'],4)

    def test_invalid_or_unobserved_values_rejected(self):
        for step,cost in ((0,100),(2,0),(float('nan'),100),(2,float('inf'))):
            with self.assertRaises(ValueError):projection(step,416,cost)
        with self.assertRaises(ValueError):projection(2,0,100)


if __name__=='__main__':unittest.main()
