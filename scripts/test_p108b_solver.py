"""Independent KKT, repeated-budget, sparse and numerical-path contracts."""
import unittest
import torch

from scripts import p108b_solver as solver


class SolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def fixture(self):
        generator = torch.Generator().manual_seed(41)
        k = torch.randn(5, 3, generator=generator, dtype=torch.float64)
        r = torch.randn(2, 3, generator=generator, dtype=torch.float64)
        c = torch.eye(5, dtype=torch.float64)*.7
        return k, r, c, torch.zeros(2, 5, dtype=torch.float64)

    def test_dense_unconstrained_matches_independent_linear_solve(self):
        k, r, c, d = self.fixture()
        e, s = solver.solve_increment(k, r, c, d, 100.)
        reference = torch.linalg.solve(k@k.T+c, k@r.T).T
        torch.testing.assert_close(e.double(), reference, atol=1e-7, rtol=1e-6)
        self.assertEqual(s['multiplier'], 0.)
        self.assertLess(s['kkt_relative_residual'], 1e-12)

    def test_active_dense_constraint_and_kkt(self):
        k, r, c, d = self.fixture()
        e, s = solver.solve_increment(k, r, c, d, .05)
        self.assertGreater(s['multiplier'], 0.)
        self.assertLessEqual(float(e.double().norm()), .05)
        self.assertAlmostEqual(float(e.double().norm()), .05, places=6)
        self.assertLess(s['kkt_relative_residual'], 1e-11)

    def test_same_layer_cancellation_can_exceed_naive_remaining_increment(self):
        k = torch.eye(2, dtype=torch.float64)
        r = torch.tensor([[-3., 0.]], dtype=torch.float64)
        d = torch.tensor([[.9, 0.]], dtype=torch.float64)
        e, s = solver.solve_increment(k, r, .1*k, d, 1.)
        self.assertGreater(float(e.norm()), 1.5)
        self.assertLessEqual(float((d+e.double()).norm()), 1.)
        self.assertLess(s['cross_term'], 0.)
        self.assertLess(s['kkt_relative_residual'], 1e-11)

    def test_sparse_solution_matches_principal_system_not_masked_dense(self):
        k, r, c, d = self.fixture()
        mask = torch.tensor([[1,0,1,0,0],[0,1,0,1,0]], dtype=torch.bool)
        e, s = solver.solve_increment(k, r, c, d, 100., support=mask)
        h, g = k@k.T+c, r@k.T
        reference = torch.zeros_like(d)
        for i in range(2):
            selected = mask[i].nonzero().flatten()
            reference[i,selected] = torch.linalg.solve(h[selected][:,selected],g[i,selected])
        torch.testing.assert_close(e.double(), reference, atol=1e-7, rtol=1e-6)
        dense, _ = solver.solve_increment(k, r, c, d, 100.)
        self.assertFalse(torch.allclose(e, dense*mask))
        self.assertEqual(int(e[~mask].ne(0).sum()), 0)
        self.assertLess(s['kkt_relative_residual'], 1e-12)

    def test_sparse_revisit_constraint_includes_untouched_old_values(self):
        k, r, c, d = self.fixture()
        mask = torch.tensor([[1,0,1,0,0],[0,1,0,1,0]], dtype=torch.bool)
        d[0,1] = .03
        e, _ = solver.solve_increment(k, r, c, d, .05, support=mask)
        self.assertEqual(float((d+e)[0,1]), .03)
        self.assertLessEqual(float((d+e.double()).norm()), .05)
        with self.assertRaisesRegex(ValueError,'INFEASIBLE_FIXED_SUPPORT'):
            solver.solve_increment(k, r, c, d, .01, support=mask)

    def test_random_support_matches_count_rows_and_is_reproducible(self):
        p = torch.ones(4,32)
        a = solver.select_support(p,denominator=8,seed=1337)
        b = solver.select_support(p,denominator=8,seed=1337)
        top = solver.select_support(p,denominator=8)
        self.assertTrue(torch.equal(a,b))
        self.assertTrue(bool((a.sum(1)==4).all()))
        self.assertTrue(bool(top[:,:4].all()))

    def test_different_unique_layers_only_use_orthogonal_budget(self):
        self.assertAlmostEqual(solver.remaining_layer_budget(5.,[torch.tensor([[3.]])]),4.)
        with self.assertRaises(ValueError):
            solver.remaining_layer_budget(3.,[torch.tensor([[3.]])])

    def test_actual_fp32_rounding_and_order_matter(self):
        base = torch.tensor([[1e8]],dtype=torch.float32)
        a = torch.tensor([[-1e8]],dtype=torch.float32)
        b = torch.tensor([[1.]],dtype=torch.float32)
        after_a,_ = solver.physical_change(base,base,a)
        sequential,s = solver.physical_change(base,after_a,b)
        merged,_ = solver.physical_change(base,base,a+b)
        self.assertEqual(float(sequential),1.)
        self.assertEqual(float(merged),0.)
        self.assertEqual(s['step_norm'],1.)

    def test_nonfinite_gradient_or_indefinite_moment_is_rejected(self):
        k,r,c,d = self.fixture()
        with self.assertRaises(ValueError):
            solver.solve_increment(k,r,-c,d,1.)
        with self.assertRaises(ValueError):
            solver.predicted_gain(torch.full_like(d,float('nan')),d)

    def test_terminal_direction_predicts_small_change_not_arbitrary_large_change(self):
        # Rotation plus nonlinear output makes hidden-vector size insufficient.
        rotation = torch.tensor([[0.,-1.],[1.,0.]],dtype=torch.float64)
        w = torch.tensor([[.2,.8]],dtype=torch.float64,requires_grad=True)
        def objective(z):
            y = torch.sin(z@rotation)
            return (y-torch.tensor([[.7,-.2]],dtype=torch.float64)).square().sum()
        gradient, = torch.autograd.grad(objective(w),w)
        small = -gradient.detach()*1e-5
        predicted = solver.predicted_gain(gradient.detach(),small)
        observed = float(objective(w.detach())-objective(w.detach()+small))
        self.assertAlmostEqual(predicted,observed,delta=abs(predicted)*1e-4)
        large = -gradient.detach()/gradient.detach().norm()*4
        observed_large = float(objective(w.detach())-objective(w.detach()+large))
        self.assertGreater(abs(observed_large-solver.predicted_gain(gradient.detach(),large)), .1)


if __name__ == '__main__':
    unittest.main()
