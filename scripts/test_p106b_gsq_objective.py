"""CPU technical contracts only; no student-quality or training-scale claims."""
import copy
from contextlib import ExitStack
import unittest
from unittest.mock import patch

import torch

from scripts.p106b_gsq_objective import ObjectiveBridge, GSQBank
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer


def tiny(checkpoint=False):
    torch.manual_seed(61105)
    cfg = TMTConfig(vocab_size=31, dim=16, ffn_dim=32,
        n_prelude=1, n_middle=2, n_coda=1, n_q_heads=4, n_kv_heads=2,
        emb_rank=8, max_seq_len=16, tie_mlp=True, mlp_group=2,
        cla_group=1, micro_group=4, grad_checkpoint=checkpoint, n_modes=1)
    return TiedMLPTransformer(cfg)


def data():
    x = torch.tensor([[1, 2, 3, 4], [4, 3, 2, 1]])
    y = torch.tensor([[2, 3, -100, 5], [3, 2, 1, -100]])
    chunks = [dict(row=0, positions=[0, 1], teacher_logprob=-3.),
              dict(row=1, positions=[1, 2], teacher_logprob=-4.)]
    return x, y, chunks


def bytes_of(model):
    return {name: p.detach().view(torch.uint8).clone()
            for name, p in model.named_parameters()}


class ObjectiveBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_same_initial_hard_numeric_values(self):
        model = tiny().eval()
        matrices = []
        for arm in ('ste', 'gsq'):
            bridge = ObjectiveBridge(model, arm)
            with bridge.installed(), torch.no_grad(), bridge.realization(11):
                matrices.append({k: v.clone() for k, v in bridge._current.items()})
        self.assertEqual(set(matrices[0]), set(matrices[1]))
        for key in matrices[0]:
            # Signed-zero bit equality is deliberately not asserted here.
            self.assertTrue(torch.equal(matrices[0][key], matrices[1][key]), key)

    def test_shared_physical_weight_and_main_head_use_one_bank(self):
        model = tiny().eval()
        bridge = ObjectiveBridge(model, 'gsq')
        expected = {id(m.weight) for m, _ in bridge.bindings}
        expected.update((id(model.emb.weight), id(model.emb_up.weight)))
        self.assertEqual(len(bridge.banks), len(expected))
        self.assertIs(model.layers[1].mlp[0], model.layers[2].mlp[0])
        with bridge.installed(), torch.no_grad(), bridge.realization(7):
            self.assertIs(model._emb_w(), bridge._current[bridge.embedding])
            self.assertIs(model._emb_up_w(), bridge._current[bridge.embedding_up])

    def test_training_forward_is_hard_ternary(self):
        model = tiny().train()
        bridge = ObjectiveBridge(model, 'gsq')
        with bridge.installed(), bridge.realization(8, backward_expected=False):
            for key, bank in bridge.banks.items():
                values = bridge._current[key].reshape_as(bank.mask_logit) / bank.scale
                self.assertTrue(bool(((values == -1) | (values == 0) | (values == 1)).all()))

    def test_sampling_is_seeded_and_does_not_consume_dropout_rng(self):
        bridge = ObjectiveBridge(tiny().train(), 'gsq')
        before = torch.get_rng_state().clone()
        values = []
        with bridge.installed():
            for seed in (91, 91, 92):
                with bridge.realization(seed, backward_expected=False):
                    values.append({k: v.detach().clone() for k, v in bridge._current.items()})
                self.assertTrue(torch.equal(before, torch.get_rng_state()))
        self.assertTrue(all(torch.equal(values[0][k], values[1][k]) for k in values[0]))
        self.assertTrue(any(not torch.equal(values[0][k], values[2][k]) for k in values[0]))

    def test_mask_denominators_and_scalar_objective(self):
        bridge = ObjectiveBridge(tiny().train(), 'gsq')
        x, y, chunks = data()
        with bridge.installed(), bridge.realization(13):
            terms = bridge.loss_terms(x, y, chunks, head_chunk=1)
            self.assertEqual(terms['ce_targets'], 6)
            self.assertEqual(terms['kl_chunks'], 2)
            self.assertTrue(torch.equal(terms['nll'][~terms['supervised']], torch.zeros(2)))
            loss = bridge.normalized_loss(terms, 3.)
            manual = terms['ce_sum'] / 6 + 3 * terms['kl_sum'] / 2
            self.assertTrue(torch.equal(loss, manual))
            bridge.backward(loss)

    def test_all_gsq_parameter_kinds_receive_finite_signal(self):
        bridge = ObjectiveBridge(tiny().train(), 'gsq')
        x, y, chunks = data()
        with bridge.installed(), bridge.realization(17):
            bridge.backward(bridge.normalized_loss(bridge.loss_terms(x, y, chunks), 1.))
        for kind in ('mask_logit', 'sign_logit', 'scale'):
            gradients = [getattr(bank, kind).grad for bank in bridge.banks.values()]
            self.assertTrue(all(g is not None and bool(torch.isfinite(g).all()) for g in gradients))
            self.assertGreater(sum(float(g.abs().sum()) for g in gradients), 0.)

    def test_layer_and_head_checkpoint_match_gradients(self):
        outputs = []
        x, y, chunks = data()
        for checkpoint in (False, True):
            bridge = ObjectiveBridge(tiny(checkpoint).train(), 'gsq')
            with bridge.installed(), bridge.realization(19):
                loss = bridge.normalized_loss(bridge.loss_terms(x, y, chunks, head_chunk=1), 1.)
                bridge.backward(loss)
            outputs.append((loss.detach(), {n: p.grad.clone() for n, p in bridge.banks.named_parameters()}))
        self.assertTrue(torch.allclose(outputs[0][0], outputs[1][0], atol=1e-7, rtol=1e-6))
        for name, gradient in outputs[0][1].items():
            self.assertTrue(torch.allclose(gradient, outputs[1][1][name], atol=2e-6, rtol=2e-5), name)

    def test_one_head_realization_across_chunks_and_backward_recompute(self):
        bridge = ObjectiveBridge(tiny(True).train(), 'gsq')
        bank = bridge.banks[bridge.embedding]
        x, y, chunks = data()
        with patch.object(bank, 'matrix', wraps=bank.matrix) as observed:
            with bridge.installed(), bridge.realization(23):
                bridge.backward(bridge.normalized_loss(bridge.loss_terms(x, y, chunks, head_chunk=1), 1.))
        self.assertEqual(observed.call_count, 1)

    def test_optimizer_owns_unique_banks_and_norms_not_original_masters(self):
        bridge = ObjectiveBridge(tiny().train(), 'gsq')
        originals = {id(p) for p in bridge.masters.values()}
        with bridge.installed():
            parameters = bridge.parameters_for_optimizer()
            self.assertEqual(len(parameters), len({id(p) for p in parameters}))
            self.assertFalse(originals & {id(p) for p in parameters})
            self.assertTrue(all(not p.requires_grad for p in bridge.masters.values()))
        self.assertTrue(all(p.requires_grad for p in bridge.masters.values()))

    def test_real_update_does_not_edit_original_matrix_bytes(self):
        model = tiny().train()
        bridge = ObjectiveBridge(model, 'gsq')
        before = {k: p.detach().view(torch.uint8).clone() for k, p in bridge.masters.items()}
        x, y, chunks = data()
        with bridge.installed():
            opt = torch.optim.AdamW(bridge.parameters_for_optimizer(), lr=1e-3, weight_decay=0.)
            with bridge.realization(29):
                bridge.backward(bridge.normalized_loss(bridge.loss_terms(x, y, chunks), 1.))
            opt.step()
            bridge.project()
        for key, parameter in bridge.masters.items():
            self.assertTrue(torch.equal(parameter.detach().view(torch.uint8), before[key]))

    def test_exception_restores_source_parameters_accessors_and_caches(self):
        model = tiny().eval()
        before = bytes_of(model)
        original_accessor, original_refresh = model._emb_w, model.refresh_quant
        bridge = ObjectiveBridge(model, 'gsq')
        caches = [m._wq for m, _ in bridge.bindings]
        with self.assertRaisesRegex(RuntimeError, 'fixture'):
            with bridge.installed(), bridge.realization(31, backward_expected=False):
                raise RuntimeError('fixture')
        self.assertEqual(model._emb_w, original_accessor)
        self.assertEqual(model.refresh_quant, original_refresh)
        self.assertTrue(all(m._wq is q for (m, _), q in zip(bridge.bindings, caches)))
        for name, raw in bytes_of(model).items():
            self.assertTrue(torch.equal(raw, before[name]), name)

    def test_missing_backward_fails_after_cache_restoration(self):
        bridge = ObjectiveBridge(tiny(True).train(), 'gsq')
        caches = [m._wq for m, _ in bridge.bindings]
        with self.assertRaisesRegex(RuntimeError, 'backward must finish'):
            with bridge.installed(), bridge.realization(37):
                bridge.model(data()[0], return_hidden=True)
        self.assertFalse(bridge._active)
        self.assertFalse(bridge._installed)
        self.assertTrue(all(m._wq is q for (m, _), q in zip(bridge.bindings, caches)))


if __name__ == '__main__':
    unittest.main()
