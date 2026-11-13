import math
import unittest
import torch
from scripts import p108_distributed_residual as d


class DistributedContracts(unittest.TestCase):
    def setUp(self):torch.set_num_threads(1)
    def test_two_layer_budget_is_not_twice_the_single_layer_physical_budget(self):
        a=torch.eye(3,dtype=torch.float32);b=2*a;p=d.shared_budget([a,b])
        self.assertAlmostEqual(p['absolute_total_cap'],.05*math.sqrt(3))
        self.assertAlmostEqual(math.sqrt(2*p['distributed_each_cap']**2),p['single_layer_cap'])
        self.assertLess(p['distributed_each_cap'],p['single_layer_cap'])
    def test_signed_gate_and_remaining_layers_recover_the_requested_block_residual(self):
        desired=torch.tensor([[2.,4.],[6.,8.]]);current=torch.ones_like(desired)
        for gate in [.25,-.5]:
            target=d.residual_target(desired,current,remaining=2,gate=gate)
            torch.testing.assert_close(2*gate*target,desired.double()-current.double(),atol=0,rtol=0)
    def test_recomputed_residual_improves_identity_transport_toy_over_stale_two_halves(self):
        k=torch.eye(3,dtype=torch.float64);moment=.01*k;w=torch.eye(3,dtype=torch.float32)
        target=torch.full((3,3),.02,dtype=torch.float64);zero=torch.zeros_like(target)
        first=d.packet(k,target,zero,moment,w,remaining=2,gate=.5,absolute_cap=1.)
        current=.5*first['delta'].double()@k
        second=d.packet(k,target,current,moment,w,remaining=1,gate=.25,absolute_cap=1.)
        stale=d.packet(k,target,zero,moment,w,remaining=2,gate=.25,absolute_cap=1.)
        actual=current+.25*second['delta'].double()@k;old=current+.25*stale['delta'].double()@k
        self.assertLess(float((actual-target).norm()),float((old-target).norm()))
        self.assertLess(float((actual-target).norm()),float(target.norm()))
    def test_combined_realized_fp32_norm_exceeding_the_shared_cap_is_rejected(self):
        w=torch.eye(2,dtype=torch.float32);delta=.01*w
        good=d.realized_total([w,w],[delta,delta],absolute_cap=.021)
        self.assertTrue(good['within_total_budget'])
        with self.assertRaises(ValueError):d.realized_total([w,w],[delta,delta],absolute_cap=.019)
    def test_zero_or_nonfinite_gate_wrong_shapes_and_oversized_primary_cap_fail_closed(self):
        x=torch.ones(2,3)
        for gate in [0.,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):d.residual_target(x,x,remaining=2,gate=gate)
        with self.assertRaises(ValueError):d.residual_target(x,x[:,:1],remaining=1,gate=1.)
        with self.assertRaises(ValueError):d.shared_budget([x,x],relative_cap=.06)


if __name__=='__main__':unittest.main()
