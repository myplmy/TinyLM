"""Independent CPU equations/safety/resume for the opt-in AdaMuon adaptation."""
import copy
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from tinylm.train.adamuon import AdaMuon, parameter_groups, SCHEMA
from tinylm.train.muon import Muon
from tinylm.train.normuon import NorMuon


def oracle(weight, gradient, momentum, variance, *, beta=.95, lr=.02,
           nesterov=True, steps=5, eps=1e-8, decay=0.):
    """Literal independent NS algebra; never call the optimizer/production NS."""
    momentum = momentum * beta + gradient
    direction = gradient + beta * momentum if nesterov else momentum
    x = torch.sign(direction).to(torch.bfloat16)
    transpose = x.shape[0] > x.shape[1]
    if transpose:
        x = x.T
    x = x / (torch.linalg.vector_norm(x) + 1e-7)
    for _ in range(steps):
        gram = x @ x.T
        polynomial = -4.7750 * gram + 2.0315 * (gram @ gram)
        x = 3.4445 * x + polynomial @ x
    if transpose:
        x = x.T
    x = x.float()
    variance = beta * variance + (1 - beta) * x.square()
    update = x / (variance.sqrt() + eps)
    update = update * (.2 * math.sqrt(weight.numel()) / (update.norm() + eps))
    return weight * (1 - lr * decay) - lr * update, momentum, variance


class AdaMuonContract(unittest.TestCase):
    def test_independent_multistep_tall_wide_nesterov_and_decay(self):
        for shape in ((3, 7), (7, 3), (4, 4)):
            for nesterov in (False, True):
                rng = torch.Generator().manual_seed(19)
                p = torch.nn.Parameter(torch.randn(shape, generator=rng))
                w = p.detach().clone()
                m, v = torch.zeros_like(p), torch.zeros_like(p)
                opt = AdaMuon([p], lr=.01, momentum=.8, nesterov=nesterov, weight_decay=.1)
                for _ in range(5):
                    grad = torch.randn(shape, generator=rng)
                    p.grad = grad.clone()
                    w, m, v = oracle(w, grad, m, v, lr=.01, beta=.8, nesterov=nesterov, decay=.1)
                    opt.step()
                    self.assertTrue(torch.allclose(p, w, atol=2e-7, rtol=1e-6))
                    self.assertTrue(torch.allclose(opt.state[p]["momentum_buffer"], m, atol=2e-7, rtol=1e-6))
                    self.assertTrue(torch.allclose(opt.state[p]["v_buffer"], v, atol=2e-7, rtol=1e-6))
                    self.assertTrue(torch.equal(p.grad, grad))

    def test_sign_is_before_ns_not_only_after(self):
        p = torch.nn.Parameter(torch.zeros(2, 3))
        p.grad = torch.tensor([[.1, -2., 4.], [0., .001, -12.]])
        with patch("tinylm.train.adamuon._newton_schulz", side_effect=lambda x, **kw: x) as ns:
            AdaMuon([p]).step()
        self.assertTrue(torch.equal(ns.call_args.args[0], torch.sign(p.grad)))

    def test_rms_point_two_not_double_muon_shape_scale(self):
        for shape in ((2, 7), (7, 2)):
            p = torch.nn.Parameter(torch.zeros(shape))
            p.grad = torch.arange(1, p.numel() + 1, dtype=torch.float32).reshape(shape)
            AdaMuon([p], lr=.01).step()
            self.assertAlmostEqual(float((p.detach() / .01).square().mean().sqrt()), .2, places=6)

    def test_none_skips_state_and_decay(self):
        p = torch.nn.Parameter(torch.ones(3, 4))
        opt = AdaMuon([p], weight_decay=.5)
        opt.step()
        self.assertFalse(opt.state)
        self.assertTrue(torch.equal(p, torch.ones_like(p)))

    def test_zero_gradient_has_finite_zero_update_without_history(self):
        p = torch.nn.Parameter(torch.ones(3, 4))
        p.grad = torch.zeros_like(p)
        opt = AdaMuon([p])
        opt.step()
        self.assertTrue(torch.equal(p, torch.ones_like(p)))
        self.assertTrue(torch.equal(opt.state[p]["v_buffer"], torch.zeros_like(p)))

    def test_zero_gradient_keeps_nonzero_history_active(self):
        p = torch.nn.Parameter(torch.zeros(3, 4))
        opt = AdaMuon([p])
        p.grad = torch.ones_like(p)
        opt.step()
        before = p.detach().clone()
        p.grad.zero_()
        opt.step()
        self.assertFalse(torch.equal(p, before))

    def test_fp32_full_variance_state_and_exact_byte_cost(self):
        p = torch.nn.Parameter(torch.zeros(3, 4))
        p.grad = torch.ones_like(p)
        opt = AdaMuon([p])
        opt.step()
        self.assertEqual(set(opt.state[p]), {"momentum_buffer", "v_buffer"})
        self.assertEqual(opt.state[p]["v_buffer"].shape, p.shape)
        self.assertEqual(sum(t.numel() * t.element_size() for t in opt.state[p].values()), 8 * p.numel())

    def test_resume_preserves_next_step_and_original_state_dictionary(self):
        p = torch.nn.Parameter(torch.randn(3, 4))
        opt = AdaMuon([p])
        p.grad = torch.arange(12.).reshape(3, 4)
        opt.step()
        saved = copy.deepcopy(opt.state_dict())
        original = copy.deepcopy(saved)
        q = torch.nn.Parameter(p.detach().clone())
        restored = AdaMuon([q])
        restored.load_state_dict(saved)
        for candidate in (p, q):
            candidate.grad = torch.arange(12., 0., -1.).reshape(3, 4)
        opt.step()
        restored.step()
        self.assertTrue(torch.equal(p, q))
        for key in ("momentum_buffer", "v_buffer"):
            self.assertTrue(torch.equal(opt.state[p][key], restored.state[q][key]))
            self.assertTrue(torch.equal(saved["state"][0][key], original["state"][0][key]))

    def test_invalid_resume_state_and_schema_are_rejected(self):
        p = torch.nn.Parameter(torch.ones(3, 4))
        p.grad = torch.ones_like(p)
        opt = AdaMuon([p])
        opt.step()
        for mutation in ("negative", "row_shape", "dtype", "schema"):
            saved = copy.deepcopy(opt.state_dict())
            if mutation == "negative":
                saved["state"][0]["v_buffer"][0, 0] = -1
            elif mutation == "row_shape":
                saved["state"][0]["v_buffer"] = torch.ones(3, 1)
            elif mutation == "dtype":
                saved["state"][0]["v_buffer"] = saved["state"][0]["v_buffer"].bfloat16()
            else:
                saved["param_groups"][0]["schema"] = "OLD_V1_OR_MUON"
            with self.assertRaises(ValueError):
                opt.load_state_dict(saved)

    def test_resume_duplicate_ids_and_orphan_state_are_rejected(self):
        params = [torch.nn.Parameter(torch.ones(2, 3)) for _ in range(2)]
        opt = AdaMuon(params)
        for p in params: p.grad = torch.ones_like(p)
        opt.step()
        for mutation in ("duplicate", "orphan"):
            saved = copy.deepcopy(opt.state_dict())
            if mutation == "duplicate":
                saved["param_groups"][0]["params"] = [0, 0]
            else:
                saved["state"][12345] = copy.deepcopy(saved["state"][0])
            with self.assertRaises(ValueError):
                opt.load_state_dict(saved)

    def test_nonfinite_later_gradient_does_not_modify_earlier_parameter(self):
        a, b = [torch.nn.Parameter(torch.ones(2, 3)) for _ in range(2)]
        a.grad, b.grad = torch.ones_like(a), torch.full_like(b, float("nan"))
        opt = AdaMuon([a, b])
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            opt.step()
        self.assertTrue(torch.equal(a, torch.ones_like(a)))
        self.assertFalse(opt.state)

    def test_duplicate_sparse_half_vector_empty_inputs_refused(self):
        p = torch.nn.Parameter(torch.ones(2, 3))
        for values in ([p, p], [torch.nn.Parameter(torch.ones(3))],
                       [torch.nn.Parameter(torch.ones(2, 3, dtype=torch.bfloat16))],
                       [torch.nn.Parameter(torch.zeros(0, 3))]):
            with self.assertRaises(ValueError):
                AdaMuon(values)
        p.grad = torch.ones_like(p).to_sparse()
        with self.assertRaises(ValueError):
            AdaMuon([p]).step()

    def test_bad_hyperparameters_refused(self):
        p = torch.nn.Parameter(torch.ones(2, 3))
        for kw in (dict(lr=-1), dict(lr=float("nan")), dict(momentum=1), dict(momentum=True),
                   dict(eps=0), dict(eps=1e-90), dict(ns_steps=0), dict(ns_steps=True), dict(nesterov=1)):
            with self.assertRaises(ValueError):
                AdaMuon([p], **kw)

    def test_actual_add_param_group_rejects_cross_group_duplicate(self):
        p = torch.nn.Parameter(torch.ones(2, 3))
        opt = AdaMuon([p])
        with self.assertRaises(ValueError):
            opt.add_param_group(dict(params=[p]))

    def test_tied_embedding_head_and_1d_routing(self):
        class Toy(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.emb = torch.nn.Embedding(7, 3)
                self.body = torch.nn.Linear(3, 4)
                self.lm_head = torch.nn.Linear(4, 7, bias=False)
                self.norm = torch.nn.LayerNorm(3)
        toy = Toy()
        matrices, groups = parameter_groups(toy, weight_decay=.1)
        self.assertEqual({id(p) for p in matrices}, {id(toy.body.weight)})
        no_decay = next(g for g in groups if g["group_kind"] == "adamw_no_decay")
        self.assertEqual(no_decay["weight_decay"], 0)
        self.assertIn(id(toy.lm_head.weight), {id(p) for g in groups for p in g["params"]})
        self.assertEqual(len({id(p) for p in matrices + [p for g in groups for p in g["params"]]}), len(list(toy.parameters())))

    def test_actually_tied_output_is_not_routed_twice(self):
        model = torch.nn.Module()
        model.emb = torch.nn.Embedding(7, 3)
        model.body = torch.nn.Linear(3, 3, bias=False)
        model.lm_head = torch.nn.Linear(3, 7, bias=False)
        model.lm_head.weight = model.emb.weight
        matrix, groups = parameter_groups(model, weight_decay=.1)
        self.assertEqual({id(p) for p in matrix}, {id(model.body.weight)})
        all_parameters = matrix + [p for g in groups for p in g["params"]]
        self.assertEqual(sum(p is model.emb.weight for p in all_parameters), 1)

    def test_sibling_optimizers_have_distinct_updates(self):
        g = torch.tensor([[1., -2., .01], [3., 4., -7.]])
        values = []
        for cls, kwargs in ((Muon, dict(scale_mode="rms")), (NorMuon, dict(scale_mode="rms")), (AdaMuon, {})):
            p = torch.nn.Parameter(torch.zeros_like(g))
            p.grad = g.clone()
            cls([p], lr=.01, **kwargs).step()
            values.append(p.detach().clone())
        self.assertFalse(torch.equal(values[0], values[2]))
        self.assertFalse(torch.equal(values[1], values[2]))

    def test_actual_tlinear_ste_gradient_reaches_master_update(self):
        from tinylm.config import TMTConfig
        from tinylm.model.ternary import TLinear
        layer = TLinear(TMTConfig(), 128, 64)
        before = layer.weight.detach().clone()
        layer.refresh_quant(torch.tensor(1.))
        output = layer(torch.randn(3, 128))
        output.square().mean().backward()
        self.assertIsNotNone(layer.weight.grad)
        gradient = layer.weight.grad.clone()
        self.assertTrue(torch.isfinite(gradient).all())
        AdaMuon([layer.weight], lr=.01).step()
        self.assertFalse(torch.equal(before, layer.weight))
        self.assertTrue(torch.equal(layer.weight.grad, gradient))

    def test_multigroup_resume_includes_lazy_none_state(self):
        params = [torch.nn.Parameter(torch.ones(2, 3)) for _ in range(3)]
        groups = [dict(params=params[:2], lr=.01), dict(params=params[2:], lr=.02, nesterov=False)]
        opt = AdaMuon(groups)
        params[0].grad, params[2].grad = torch.ones_like(params[0]), -torch.ones_like(params[2])
        opt.step()
        values = [torch.nn.Parameter(p.detach().clone()) for p in params]
        restored = AdaMuon([dict(params=values[:2]), dict(params=values[2:])])
        restored.load_state_dict(copy.deepcopy(opt.state_dict()))
        self.assertNotIn(values[1], restored.state)
        for a, b in zip(params, values):
            a.grad, b.grad = torch.ones_like(a), torch.ones_like(b)
        opt.step()
        restored.step()
        for a, b in zip(params, values):
            self.assertTrue(torch.equal(a, b))

    def test_late_arithmetic_error_is_explicitly_not_atomic_rollback(self):
        params = [torch.nn.Parameter(torch.zeros(2, 3)) for _ in range(2)]
        for p in params: p.grad = torch.ones_like(p)
        opt = AdaMuon(params)
        results = [torch.ones(2, 3), torch.full((2, 3), float("nan"))]
        with patch("tinylm.train.adamuon._newton_schulz", side_effect=results):
            with self.assertRaisesRegex(ValueError, "NS output"):
                opt.step()
        self.assertFalse(torch.equal(params[0], torch.zeros_like(params[0])))
        self.assertTrue(torch.equal(params[1], torch.zeros_like(params[1])))
        self.assertTrue(torch.equal(opt.state[params[1]]["momentum_buffer"], torch.ones_like(params[1])))


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main()
