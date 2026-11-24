"""Model-free metamorphic/safety contracts for the new precision factors."""
import itertools
import unittest
import torch
from scripts.p005b_adamuon_precision import local_step,NS_ORDERS,TAILS

class PrecisionContracts(unittest.TestCase):
    def setUp(self):
        self.w=torch.linspace(-1,1,21).reshape(3,7)
        self.g=torch.tensor([[1,-2,3,-4,5,-6,7],[-7,6,-5,4,-3,2,-1],[2,3,-1,-4,5,0,6]],dtype=torch.float32)

    def run_factor(self,ns,tail,**kw):
        values=[self.w,self.g,torch.zeros_like(self.w),torch.zeros_like(self.w,dtype=torch.float32 if tail==TAILS[0]else torch.bfloat16)]
        return local_step(*values,ns_order=ns,tail=tail,**kw)

    def test_input_buffers_are_observational_and_storage_does_not_alias(self):
        for ns,tail in itertools.product(NS_ORDERS,TAILS):
            values=[self.w.clone(),self.g.clone(),torch.zeros_like(self.w),torch.zeros_like(self.w,dtype=torch.float32 if tail==TAILS[0]else torch.bfloat16)]
            before=[v.clone()for v in values]
            out=local_step(*values,ns_order=ns,tail=tail)
            self.assertTrue(all(torch.equal(a,b)for a,b in zip(values,before)))
            for result in(out['weight'],out['momentum'],out['variance'],out['update']):
                self.assertTrue(all(result.untyped_storage().data_ptr()!=v.untyped_storage().data_ptr()for v in values))

    def test_positive_gradient_scaling_preserves_sign_ns_update_from_zero_history(self):
        for ns,tail in itertools.product(NS_ORDERS,TAILS):
            a=self.run_factor(ns,tail)
            old=self.g
            try:
                self.g=self.g*8
                b=self.run_factor(ns,tail)
            finally:self.g=old
            self.assertTrue(torch.equal(a['weight'],b['weight']))
            self.assertTrue(torch.equal(a['variance'],b['variance']))

    def test_transposing_all_inputs_transposes_the_step(self):
        for ns,tail in itertools.product(NS_ORDERS,TAILS):
            a=self.run_factor(ns,tail)
            old_w,old_g=self.w,self.g
            try:
                self.w,self.g=self.w.T,self.g.T
                b=self.run_factor(ns,tail)
            finally:self.w,self.g=old_w,old_g
            self.assertTrue(torch.equal(a['weight'].T,b['weight']))
            self.assertTrue(torch.equal(a['variance'].T,b['variance']))

    def test_zero_history_and_gradient_give_only_declared_weight_decay(self):
        old=self.g
        try:
            self.g=torch.zeros_like(self.g)
            for ns,tail in itertools.product(NS_ORDERS,TAILS):
                a=self.run_factor(ns,tail,lr=.125,weight_decay=.25)
                self.assertTrue(torch.equal(a['weight'],self.w*(1-.125*.25)))
                self.assertTrue(torch.count_nonzero(a['update'])==0)
        finally:self.g=old

    def test_state_storage_is_exact_six_or_eight_bytes_per_element(self):
        for ns,tail in itertools.product(NS_ORDERS,TAILS):
            a=self.run_factor(ns,tail)
            self.assertEqual(a['state_bytes'],self.w.numel()*(8 if tail==TAILS[0]else 6))
            self.assertEqual(a['variance'].dtype,torch.float32 if tail==TAILS[0]else torch.bfloat16)

    def test_invalid_v_or_nonfinite_gradient_rejects_without_caller_changes(self):
        for tail in TAILS:
            dtype=torch.float32 if tail==TAILS[0]else torch.bfloat16
            w=self.w.clone();m=torch.zeros_like(w);v=torch.zeros_like(w,dtype=dtype)
            bad=self.g.clone();bad[0,0]=float('nan')
            with self.assertRaises(ValueError):local_step(w,bad,m,v,ns_order=NS_ORDERS[0],tail=tail)
            self.assertTrue(torch.equal(w,self.w));self.assertTrue(torch.count_nonzero(m)==0)
            with self.assertRaises(ValueError):local_step(w,self.g,m,v+(-1),ns_order=NS_ORDERS[0],tail=tail)

if __name__=='__main__':
    torch.set_num_threads(2)
    unittest.main()
