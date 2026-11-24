"""Analytic regularizer confounding and independent original-solver parity."""
import unittest
import torch
from scripts import p108b_quadratic as q
from scripts import p108b_solver as old


class QuadraticTests(unittest.TestCase):
    def test_incremental_preservation_weakens_when_split_into_repeated_steps(self):
        k=torch.eye(2,dtype=torch.float64);r=torch.ones(2,2,dtype=torch.float64);c=k.clone();zero=torch.zeros_like(r)
        first,_=q.solve_increment(k,r,c,zero,10.,total_preservation=False)
        second,_=q.solve_increment(k,r-first.double()@k,c,first.double(),10.,total_preservation=False)
        torch.testing.assert_close(first,torch.full((2,2),.5))
        torch.testing.assert_close(first+second,torch.full((2,2),.75))
        total,_=q.solve_increment(k,r-first.double()@k,c,first.double(),10.,total_preservation=True)
        torch.testing.assert_close(total,torch.zeros_like(total),atol=1e-7,rtol=0)

    def test_total_preservation_repeated_endpoint_matches_one_shot_under_progressive_caps(self):
        torch.manual_seed(8);k=torch.randn(5,3,dtype=torch.float64);r=torch.randn(4,3,dtype=torch.float64);c=torch.eye(5,dtype=torch.float64)
        d=torch.zeros(4,5,dtype=torch.float64)
        one,_=q.solve_increment(k,r,c,d,1.,total_preservation=True)
        for j in range(1,5):
            e,_=q.solve_increment(k,r-d@k,c,d,j/4,total_preservation=True);d=d+e.double()
        torch.testing.assert_close(d,one.double(),atol=1e-7,rtol=1e-6)

    def test_fast_incremental_matches_original_dense_and_sparse(self):
        torch.manual_seed(19);k=torch.randn(8,3,dtype=torch.float64);r=torch.randn(4,3,dtype=torch.float64)
        c=torch.eye(8,dtype=torch.float64);d=torch.randn(4,8,dtype=torch.float64)*.01
        for mask in(None,old.select_support(d,denominator=4)):
            a,sa=old.solve_increment(k,r,c,d,1.,support=mask)
            b,sb=q.solve_increment(k,r,c,d,1.,support=mask,total_preservation=False)
            torch.testing.assert_close(a,b,atol=1e-7,rtol=1e-6)
            self.assertLess(sb['kkt_relative_residual'],1e-10)
            self.assertAlmostEqual(sa['requested_final_norm'],sb['requested_final_norm'],places=10)

    def test_sparse_total_penalty_satisfies_full_coupled_kkt(self):
        torch.manual_seed(31);k=torch.randn(8,3,dtype=torch.float64);r=torch.randn(4,3,dtype=torch.float64)
        v=torch.randn(8,8,dtype=torch.float64);c=v.T@v+torch.eye(8,dtype=torch.float64);d=torch.randn(4,8,dtype=torch.float64)*.01
        mask=old.select_support(d,denominator=4)
        e,s=q.solve_increment(k,r,c,d,1.,support=mask,total_preservation=True)
        final=d+e.double();derivative=e.double()@(k@k.T+c)-r@k.T+d@c+s['multiplier']*final
        self.assertLess(float(derivative[mask].norm()),1e-5)
        self.assertTrue(bool((e[~mask]==0).all()))


if __name__=='__main__':unittest.main()
