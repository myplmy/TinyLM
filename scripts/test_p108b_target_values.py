"""Target-window gradient/ownership/normalization contracts, CPU only."""
import unittest
import torch
from scripts import p108b_target_values as p
from scripts import p108_value_edit as old


class TargetValueTests(unittest.TestCase):
    def module(self):
        module=torch.nn.Linear(2,2,bias=False)
        with torch.no_grad():module.weight.copy_(torch.eye(2))
        return module

    def test_zero_window_native_identity_and_complete_gradient(self):
        module=self.module();x=torch.randn(1,5,2);reference=module(x).detach();delta=torch.zeros(3,2,requires_grad=True);capture={}
        with p.inject_window(module,1,delta,capture=capture):out=module(x)
        self.assertTrue(torch.equal(reference,out));self.assertEqual(capture['keys'].shape,(3,2))
        gradient,=torch.autograd.grad(out[:,1:4].sum(),delta)
        self.assertTrue(torch.equal(gradient,torch.ones_like(delta)))
        self.assertTrue(torch.equal(module(x).detach(),reference))

    def test_terminal_pointwise_layer_first_slot_cannot_control_later_slot(self):
        module=self.module();x=torch.randn(1,3,2);one=torch.zeros(2,requires_grad=True)
        with old.inject(module,0,one):last=module(x)[:,2].sum()
        gradient,=torch.autograd.grad(last,one);self.assertTrue(torch.equal(gradient,torch.zeros_like(one)))
        many=torch.zeros(3,2,requires_grad=True)
        with p.inject_window(module,0,many):last=module(x)[:,2].sum()
        gradient,=torch.autograd.grad(last,many)
        self.assertTrue(torch.equal(gradient[0],torch.zeros(2)));self.assertTrue(torch.equal(gradient[2],torch.ones(2)))

    def test_shared_intersection_and_separate_position_caps(self):
        norms=torch.tensor([1.,3.])
        for mode in p.MODES:
            parameters=torch.ones(1 if mode=='SHARED'else 2,4,requires_grad=True)
            p.limit_parameters(parameters,mode,norms,.75);field=p.value_field(parameters,mode,norms)
            self.assertTrue(bool((field.norm(dim=1)<=norms*.750001).all()))
            if mode=='SHARED':self.assertTrue(torch.equal(field[0],field[1]))

    def test_repeated_target_positions_do_not_increase_question_weight(self):
        k=torch.tensor([[1.,2.]]);v=torch.tensor([[3.,4.]])
        one=p.question_columns(k,v);many=p.question_columns(k.repeat(4,1),v.repeat(4,1));weight=torch.ones(2,2,dtype=torch.float64)
        a=(weight@one[0]-one[1]).square().sum();b=(weight@many[0]-many[1]).square().sum()
        self.assertAlmostEqual(float(a),float(b))

    def test_partial_decode_and_mismatched_positions_are_rejected(self):
        module=self.module()
        with self.assertRaises(ValueError),p.inject_window(module,2,torch.zeros(3,2)):module(torch.zeros(1,3,2))
        with self.assertRaises(ValueError):p.question_columns(torch.ones(2,3),torch.ones(3,2))
        with self.assertRaises(ValueError):p.value_field(torch.ones(2,3),'SHARED',torch.ones(2))


if __name__=='__main__':unittest.main()
