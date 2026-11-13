import unittest
import torch
from scripts import p108_joint_write as j
from scripts import p108_value_edit as old


class JointWriteContracts(unittest.TestCase):
    def fixture(self):
        torch.manual_seed(81)
        keys=torch.randn(5,4,dtype=torch.float64);values=torch.randn(3,4,dtype=torch.float64)
        x=torch.randn(17,5,dtype=torch.float64);c,_=j.covariance(x)
        w=torch.randn(3,5,dtype=torch.float64)*100
        return keys,values,c,w

    def test_unconstrained_matches_independent_dense_solve_and_kkt(self):
        k,r,c,w=self.fixture();p=j.joint_packet(k,r,c,w)
        oracle=torch.linalg.solve(k@k.T+c,k@r.T).T
        torch.testing.assert_close(p['delta'],oracle,atol=1e-10,rtol=1e-10)
        self.assertEqual(p['stats']['multiplier'],0.)
        self.assertLess(p['stats']['kkt_relative_residual'],1e-10)

    def test_active_bound_is_fixed_and_stationary_with_positive_multiplier(self):
        k,r,c,w=self.fixture();w=w/1000;p=j.joint_packet(k,r,c,w,relative_cap=.05)
        self.assertGreater(p['stats']['multiplier'],0.)
        self.assertLessEqual(p['stats']['relative_norm'],.05)
        self.assertAlmostEqual(p['stats']['relative_norm'],.05*(1-1e-5),places=10)
        residual=p['delta']@(k@k.T+c)+p['stats']['multiplier']*p['delta']-r@k.T
        self.assertLess(float(residual.norm()),1e-9)

    def test_covariance_is_the_existing_regularized_second_moment(self):
        torch.manual_seed(11);x=torch.randn(13,5,dtype=torch.float64)
        c,stats=j.covariance(x);inverse,prior=old.inverse_second_moment(x)
        torch.testing.assert_close(c@inverse,torch.eye(5,dtype=torch.float64),atol=1e-10,rtol=1e-10)
        self.assertEqual(stats,prior)

    def test_solution_is_covariant_under_orthogonal_input_basis_change(self):
        k,r,c,w=self.fixture();q=torch.linalg.qr(torch.randn(5,5,dtype=torch.float64))[0]
        a=j.joint_packet(k,r,c,w/1000);b=j.joint_packet(q@k,r,q@c@q.T,w@q.T/1000)
        torch.testing.assert_close(b['delta'],a['delta']@q.T,atol=1e-10,rtol=1e-10)

    def test_conflicting_duplicate_keys_remain_finite_and_have_real_residual(self):
        k,r,c,w=self.fixture();k[:,1]=k[:,0];r[:,1]=-r[:,0]
        p=j.joint_packet(k,r,c,w)
        self.assertTrue(bool(torch.isfinite(p['delta']).all()))
        self.assertGreater(p['stats']['target_residual_norm'],0.)

    def test_fp32_materialization_retains_conservative_norm_budget(self):
        k,r,c,w=self.fixture();w=(w/1000).float();p=j.joint_packet(k.float(),r.float(),c.float(),w)
        actual=(w+p['delta'])-w
        self.assertLessEqual(float(actual.double().norm())/float(w.double().norm()),.05)

    def test_random_controls_match_spectrum_and_reproduce_only_their_seed(self):
        k,r,c,w=self.fixture();p=j.joint_packet(k,r,c,w)
        a=j.random_spectral_packet(p,seed=10007);b=j.random_spectral_packet(p,seed=10007);d=j.random_spectral_packet(p,seed=10009)
        self.assertTrue(torch.equal(a['delta'],b['delta']));self.assertFalse(torch.equal(a['delta'],d['delta']))
        torch.testing.assert_close(torch.linalg.svdvals(a['delta']),torch.linalg.svdvals(p['delta']),atol=1e-10,rtol=1e-10)

    def test_invalid_shapes_nonfinite_covariance_and_gradients_fail_closed(self):
        k,r,c,w=self.fixture()
        for kk,rr,cc,ww in [(k,r[:,:2],c,w),(k,r,c*float('nan'),w),(k,r,-c,w),(k.clone().requires_grad_(),r,c,w)]:
            with self.assertRaises(ValueError):j.joint_packet(kk,rr,cc,ww)

    def test_common_layer_selection_uses_fit_only_and_requires_complete_candidates(self):
        records=[]
        for fact in ['a','b']:
            for layer in (2,5,8,11):records.append(dict(fact=fact,layer=layer,oracle_fit=dict(exact=2 if layer==8 else 0,items=2),
                optimization=dict(trace=[dict(nll=1. if layer==8 else 3.)]),dev_exact=999 if layer==2 else 0))
        selected,scores=j.choose_common_layer(records,families=['a','b']);self.assertEqual(selected,8)
        with self.assertRaises(ValueError):j.choose_common_layer(records[:-1],families=['a','b'])


if __name__=='__main__':unittest.main()
