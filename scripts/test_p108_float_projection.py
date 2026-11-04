"""Prove why duplicate effective/latent float search arms are unnecessary."""
import unittest
import torch
from scripts.p106b_weight_route import weight_route
from scripts.test_p108_weight_space import fixture
from scripts import p108_weight_space as repair


class FloatEquivalenceTests(unittest.TestCase):
    def test_nonzero_cache_and_latent_edits_are_bit_equal_in_float_route(self):
        model=fixture()
        with weight_route(model,'float') as route,torch.no_grad():
            model.freeze_quant()
            for gain in (.25,.5,1.,2.):
                delta=repair.projection_delta(model.a.weight,torch.tensor([.6,.8]),[0,1],gain)
                values=[]
                for realization in ('effective','latent'):
                    with repair.edit_weights(model,route,[(0,delta)],realization):
                        values.append((repair.tensor_sha(model.a._wq),model(torch.tensor([[.3,-.2]])).clone()))
                self.assertEqual(values[0][0],values[1][0])
                self.assertTrue(torch.equal(values[0][1],values[1][1]))


if __name__=='__main__':
    unittest.main()
