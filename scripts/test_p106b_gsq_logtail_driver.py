import unittest
from scripts import diag_p106b_gsq_logtail as driver
from scripts import diag_p106b_gsq_coordinates as prior
from scripts import p106b_gsq_coordinates as coordinates
from scripts.test_p106b_gsq_objective import tiny,data
import torch


class PrivateKernelContracts(unittest.TestCase):
    def test_mechanics_bytecode_and_original_global_factory_remain_unchanged(self):
        old=prior.measure.__globals__['coordinates'];factory=coordinates.scaled_bridge
        private=driver.make_measure({})
        self.assertIs(private.__code__,prior.measure.__code__)
        self.assertIs(prior.measure.__globals__['coordinates'],old)
        self.assertIs(coordinates.scaled_bridge,factory)
        self.assertIsNot(private.__globals__['coordinates'],old)

    def test_private_bridge_records_numeric_observations_and_backward(self):
        observations=dict(forward_calls=0,ordinary_zero_positions=0,old_boundary_chunks=0,min_log_nll=0.,first_boundary_forward=None)
        bridge=driver.make_bridge(tiny().train(),observations)
        x,y,chunks=data()
        with bridge.installed(),bridge.realization(644):
            terms=bridge.loss_terms(x,y,chunks,head_chunk=1)
            bridge.backward(bridge.normalized_loss(terms,1.))
        self.assertEqual(observations['forward_calls'],1)
        self.assertEqual(terms['ce_targets'],6)
        self.assertTrue(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in bridge.banks.parameters()))


if __name__=='__main__':unittest.main()
