import unittest
from types import SimpleNamespace
import torch
from scripts import p108_value_edit as v


class ValueContracts(unittest.TestCase):
    def test_subject_last_token_with_character_offsets(self):
        e = SimpleNamespace(offsets=[(0, 0), (0, 2), (2, 5), (5, 7)])
        self.assertEqual(v.subject_position(e, 1, 5), 2)
        with self.assertRaises(ValueError): v.subject_position(e, 7, 9)

    def test_shift_covers_answer_and_eot_once(self):
        x, y, start = v.target_window([11, 12], [21, 22])
        self.assertEqual((x, y, start), ([11, 12, 21, 22], [21, 22, 4], 1))
        self.assertEqual(len(x) - start, len(y))

    def test_value_hook_gradient_and_cleanup(self):
        m = torch.nn.Linear(3, 2, bias=False)
        d = torch.nn.Parameter(torch.zeros(2))
        x = torch.ones(1, 4, 3)
        old = m(x).detach()
        with v.freeze_parameters(m), v.inject(m, 2, d):
            result = m(x)
            grad, = torch.autograd.grad(result[0, 2].sum(), d)
            self.assertTrue(torch.equal(grad, torch.ones(2)))
            self.assertTrue(torch.equal(result.detach(), old))
            self.assertIsNone(m.weight.grad)
        self.assertFalse(m._forward_hooks)
        self.assertTrue(m.weight.requires_grad)

    def test_hook_not_repeated_at_cached_single_token(self):
        m = torch.nn.Identity()
        with v.inject(m, 3, torch.ones(2)):
            self.assertTrue(torch.equal(m(torch.zeros(1, 1, 2)), torch.zeros(1, 1, 2)))
            self.assertTrue(torch.equal(m(torch.zeros(1, 4, 2))[0, 3], torch.ones(2)))

    def test_exception_removes_hook(self):
        m = torch.nn.Identity()
        with self.assertRaisesRegex(RuntimeError, 'sentinel'):
            with v.inject(m, 1, torch.zeros(2)): raise RuntimeError('sentinel')
        self.assertFalse(m._forward_hooks)

    def test_first_token_injection_is_not_repeated_on_decode(self):
        m = torch.nn.Identity()
        with v.inject(m, 0, torch.ones(2)):
            self.assertTrue(torch.equal(m(torch.zeros(1, 4, 2))[0, 0], torch.ones(2)))
            self.assertTrue(torch.equal(m(torch.zeros(1, 1, 2)), torch.zeros(1, 1, 2)))

    def test_rank_one_exact_key_constraint(self):
        k, val = torch.tensor([1., 2., 3.]), torch.tensor([.2, -.5])
        update, stats = v.rank_one(k, val, torch.diag(torch.tensor([.5, 2., 3.])))
        self.assertTrue(torch.allclose(update @ k, val, atol=1e-6))
        self.assertLess(stats['key_constraint_residual'], 1e-10)
        self.assertEqual(int(torch.linalg.matrix_rank(update)), 1)

    def test_covariance_constraint_minimizes_preservation_energy(self):
        keys = torch.tensor([[10., .1], [-10., .1], [8., -.2]])
        inv, _ = v.inverse_second_moment(keys)
        k, val = torch.ones(2), torch.ones(1)
        corrected, _ = v.rank_one(k, val, inv)
        plain, _ = v.rank_one(k, val, torch.eye(2))
        self.assertLess(float((keys @ corrected.T).square().sum()), float((keys @ plain.T).square().sum()))

    def test_invalid_covariance_and_nan_fail_closed(self):
        for k in (torch.zeros(3, 2), torch.ones(1, 2), torch.full((3, 2), float('nan'))):
            with self.assertRaises(ValueError): v.inverse_second_moment(k)
        with self.assertRaises(ValueError): v.rank_one(torch.zeros(2), torch.ones(1), torch.eye(2))
        with self.assertRaises(ValueError): v.rank_one(torch.ones(2), torch.ones(1), torch.tensor([[1., 2.], [0., 1.]]))

    def test_frozen_facts_split_and_source_pairing(self):
        rows = v.facts()
        self.assertEqual(len(rows), 40)
        self.assertEqual(len({r['fact'] for r in rows}), 8)
        for fact in {r['fact'] for r in rows}:
            self.assertEqual([r['split'] for r in rows if r['fact'] == fact], ['fit', 'fit', 'dev', 'test', 'test'])

    def test_relative_scale_and_new_subjects(self):
        self.assertEqual(v.value_scale(4000., 'relative'), 4000.)
        self.assertEqual(v.value_scale(4000., 'raw'), 1.)
        for n, mode in ((0.,'relative'),(float('nan'),'raw'),(2.,'unknown')):
            with self.assertRaises(ValueError):v.value_scale(n,mode)
        old=v.facts();new=v.relative_facts()
        self.assertFalse({r['subject'] for r in old}&{r['subject'] for r in new})
        self.assertEqual(len(new),40)
        self.assertFalse({r['question'] for r in old}&{r['question'] for r in new})

    def test_real_float_route_value_gradient_preserves_master_contract(self):
        from scripts.test_p108_wsp_attention import fixture
        from scripts.p106b_weight_route import weight_route
        model = fixture()
        delta = torch.nn.Parameter(torch.zeros(2))
        with weight_route(model, 'float') as route:
            with torch.no_grad(): model.freeze_quant()
            with v.freeze_parameters(model), v.inject(model.a, 2, delta):
                output = model(torch.ones(1, 4, 2))
                gradient, = torch.autograd.grad(output.sum(), delta)
                self.assertTrue(torch.isfinite(gradient).all())
                self.assertTrue(all(p.grad is None for p in model.parameters()))
            route.assert_active()

    def test_gradient_after_real_edit_rollback_rebases_identity_views(self):
        from scripts.test_p108_wsp_attention import fixture
        from scripts.p106b_weight_route import weight_route
        from scripts import p108_wsp_attention as editor
        model = fixture(); x = torch.ones(1, 4, 2)
        delta = torch.nn.Parameter(torch.zeros(2))
        with weight_route(model, 'float') as route:
            with torch.no_grad(): model.freeze_quant()
            saved = model.b.weight.detach().clone()
            with editor.edit(model, route, [('mlp:0', torch.full_like(model.b.weight, .01))]):
                with torch.no_grad(): model(x)
            v.refresh_autograd_views(model, route)
            with v.freeze_parameters(model), v.inject(model.a, 2, delta):
                gradient, = torch.autograd.grad(model(x).sum(), delta)
                self.assertTrue(torch.isfinite(gradient).all())
            self.assertTrue(torch.equal(saved, model.b.weight))
            self.assertTrue(all(p.grad is None for p in model.parameters()))


if __name__ == '__main__': unittest.main()
