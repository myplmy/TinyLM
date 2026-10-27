"""Actual TinyLM visibility/CLA/checkpoint and independent shifted-target oracles."""
import ast
import copy
import hashlib
import math
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
import torch.nn.functional as F

from tinylm.config import TMTConfig
from tinylm.model import modules, transformer
from tinylm.model.transformer import TiedMLPTransformer
from tinylm.train import hybrid_mntp as h

torch.set_num_threads(1)
OLD = ROOT / "handoff/audit/oct27_independent/p013_context_source_v2/tinylm/model"
OLD_SHA = {"modules.py": "0C85AC5E087A7003D5BADB90733D2CBF21A2C24B7512D6E196E6E7EFD1954A3C",
           "transformer.py": "BB8D88D8C1BA3475777AA65126AEB6A25C0259CC66D9A3BB5FF3CB3B3A37DA1A"}


def cfg(**kwargs):
    values = dict(vocab_size=128, dim=24, ffn_dim=48, emb_rank=12,
                  n_q_heads=4, n_kv_heads=2, n_prelude=1, n_middle=2,
                  n_coda=1, mlp_group=2, cla_group=2, max_seq_len=16,
                  quantize_embedding=False, quant_anneal=1.0, micro_group=8)
    values.update(kwargs)
    return TMTConfig(**values)


def model_pair(*, checkpoint=False):
    torch.manual_seed(20261027)
    left = TiedMLPTransformer(cfg(grad_checkpoint=checkpoint))
    right = TiedMLPTransformer(copy.deepcopy(left.cfg))
    right.load_state_dict(left.state_dict(), strict=True)
    return left, right


def fixture():
    return (torch.tensor([[40, 41, 42, 43, 44, 45, 0, 0, 0]], dtype=torch.long),
            torch.tensor([[0, 0, 0, 1, 1, 1, -1, -1, -1]], dtype=torch.long))


def selection():
    return torch.tensor([[False, True, False, False, True, False, False, False, False]])


def gradients(model):
    return {n: None if p.grad is None else p.grad.detach().clone()
            for n, p in model.named_parameters()}


def archived_forward(filename, cls_name, namespace):
    source = (OLD / filename).read_bytes()
    if hashlib.sha256(source).hexdigest().upper() != OLD_SHA[filename]:
        raise ValueError("archived old forward source changed")
    tree = ast.parse(source.decode("utf-8"))
    node = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == cls_name)
    fn = next(x for x in node.body if isinstance(x, ast.FunctionDef) and x.name == "forward")
    env = vars(namespace).copy()
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(OLD / filename), "exec"), env)
    return env["forward"]


def install_old_forwards(model):
    af = archived_forward("modules.py", "Attention", modules)
    lf = archived_forward("modules.py", "Layer", modules)
    tf = archived_forward("transformer.py", "TiedMLPTransformer", transformer)
    seen = set()
    for layer in model.layers:
        layer.forward = types.MethodType(lf, layer)
        if id(layer.attn_mod) not in seen:
            seen.add(id(layer.attn_mod))
            layer.attn_mod.forward = types.MethodType(af, layer.attn_mod)
    model.forward = types.MethodType(tf, model)


class TargetContract(unittest.TestCase):
    def test_literal_independent_shift_boundary_and_corruption_oracle(self):
        tokens, docs = fixture()
        original_tokens, original_docs = tokens.clone(), docs.clone()
        causal = h.causal_batch(tokens, docs, vocab_size=128)
        masked = h.mntp_batch(tokens, docs, selection(), vocab_size=128)
        self.assertEqual(causal.targets.tolist(), [[41, 42, -100, 44, 45, -100, -100, -100]])
        self.assertEqual(masked.inputs.tolist(), [[40, 13, 42, 43, 13, 45, 0, 0]])
        self.assertEqual(masked.targets.tolist(), [[41, -100, -100, 44, -100, -100, -100, -100]])
        self.assertEqual((causal.target_count, masked.target_count), (4, 2))
        self.assertTrue(torch.equal(tokens, original_tokens) and torch.equal(docs, original_docs))
        self.assertEqual(masked.executed_input_tokens, 8)

    def test_masks_match_literal_query_key_oracle_including_padding(self):
        _, docs = fixture()
        for bi in (False, True):
            mask = h.document_visibility(docs[:, :-1], bidirectional=bi)
            for q in range(8):
                for k in range(8):
                    expected = (q == k) if docs[0, q] == -1 else (
                        docs[0, k] >= 0 and docs[0, q] == docs[0, k] and (bi or k <= q))
                    self.assertEqual(bool(mask[0, 0, q, k]), bool(expected))

    def test_first_cross_document_special_padding_and_off_window_selection_rejected(self):
        tokens, docs = fixture()
        for position in (0, 3, 6, 8):
            selected = torch.zeros_like(tokens, dtype=torch.bool); selected[0, position] = True
            with self.subTest(position=position), self.assertRaises(ValueError):
                h.mntp_batch(tokens, docs, selected, vocab_size=128)
        tokens[0, 1] = 2
        with self.assertRaises(ValueError):
            h.mntp_batch(tokens, docs, selection(), vocab_size=128)

    def test_reserved_source_collision_and_bad_document_segments_rejected(self):
        tokens, docs = fixture(); tokens[0, 2] = 13
        with self.assertRaises(ValueError): h.mntp_batch(tokens, docs, selection(), vocab_size=128)
        for bad in (torch.tensor([[0, 0, -1, 1]]), torch.tensor([[0, 1, 0, 0]])):
            with self.assertRaises(ValueError): h.document_visibility(bad, bidirectional=True)

    def test_uniform_control_is_reproducible_without_forcing_empty_targets(self):
        tokens, docs = fixture()
        args = dict(vocab_size=128, probability=.3)
        one = h.uniform_mntp_selection(tokens, docs, generator=torch.Generator().manual_seed(3), **args)
        two = h.uniform_mntp_selection(tokens, docs, generator=torch.Generator().manual_seed(3), **args)
        self.assertTrue(torch.equal(one, two))
        all_eligible = h.uniform_mntp_selection(tokens, docs, vocab_size=128, probability=1,
                                                generator=torch.Generator().manual_seed(3))
        self.assertEqual(all_eligible.tolist(), [[False, True, True, False, True, True, False, False, False]])
        for value in (0, -1, float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                h.uniform_mntp_selection(tokens, docs, vocab_size=128, probability=value,
                                         generator=torch.Generator())

    def test_separate_objective_means_match_independent_gradient(self):
        tokens, docs = fixture()
        a = h.causal_batch(tokens, docs, vocab_size=128)
        b = h.mntp_batch(tokens, docs, selection(), vocab_size=128)
        torch.manual_seed(7)
        weight = torch.nn.Parameter(torch.randn(1, 8, 128))
        class Dummy:
            def __call__(self, x, **kwargs): return weight
        expected = weight.detach().clone().requires_grad_(True)
        loss = .75 * F.cross_entropy(expected.reshape(-1, 128), a.targets.flatten(), ignore_index=-100)
        loss = loss + .25 * F.cross_entropy(expected.reshape(-1, 128), b.targets.flatten(), ignore_index=-100)
        loss.backward()
        actual, counts = h.hybrid_backward(Dummy(), a, b, masked_weight=.25)
        self.assertTrue(torch.allclose(weight.grad, expected.grad, atol=1e-8, rtol=1e-6))
        self.assertAlmostEqual(actual, float(loss.detach()), places=6)
        self.assertEqual(counts["executed_input_tokens"], 16)
        self.assertEqual((counts["causal_targets"], counts["masked_targets"], counts["model_forwards"]), (4, 2, 2))

    def test_zero_target_and_bad_weight_fail_before_any_model_call(self):
        tokens, docs = fixture(); a = h.causal_batch(tokens, docs, vocab_size=128)
        b = h.mntp_batch(tokens, docs, torch.zeros_like(tokens, dtype=torch.bool), vocab_size=128)
        calls = []
        def never(*args, **kwargs): calls.append(1); raise AssertionError("should not run")
        for weight in (.5, -1, float("nan"), float("inf"), True):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                h.hybrid_backward(never, a, b, masked_weight=weight)
        self.assertFalse(calls)

    def test_inactive_branch_not_called_and_not_multiplied_by_nan(self):
        tokens, docs = fixture(); a = h.causal_batch(tokens, docs, vocab_size=128)
        w = torch.nn.Parameter(torch.randn(1, 8, 128)); calls = []
        def dummy(*args, **kwargs): calls.append(1); return w
        value, counts = h.hybrid_backward(dummy, a, None, masked_weight=0)
        self.assertTrue(math.isfinite(value)); self.assertEqual(calls, [1])
        self.assertEqual(counts["executed_input_tokens"], 8)


class ModelContract(unittest.TestCase):
    def assert_gradients(self, a, b, *, exact=False):
        ga, gb = gradients(a), gradients(b)
        self.assertEqual(ga.keys(), gb.keys())
        for name in ga:
            self.assertEqual(ga[name] is None, gb[name] is None, name)
            if ga[name] is not None:
                self.assertTrue(torch.isfinite(ga[name]).all(), name)
                check = torch.equal(ga[name], gb[name]) if exact else torch.allclose(ga[name], gb[name], atol=2e-6, rtol=2e-5)
                self.assertTrue(check, name)

    def test_archived_default_full_logits_and_all_gradients_bit_equal(self):
        for ckpt in (False, True):
            current, old = model_pair(checkpoint=ckpt); install_old_forwards(old)
            tokens, _ = fixture(); x = tokens[:, :6]
            current.train(); old.train()
            a, b = current(x), old(x)
            self.assertTrue(torch.equal(a, b))
            a.square().sum().backward(); b.square().sum().backward()
            self.assert_gradients(current, old, exact=True)

    def test_archived_default_same_shape_cache_calls_bit_equal(self):
        current, old = model_pair(); install_old_forwards(old)
        current.eval(); old.eval(); tokens, _ = fixture()
        with torch.no_grad():
            a, ka = current(tokens[:, :4], use_cache=True)
            b, kb = old(tokens[:, :4], use_cache=True)
            self.assertTrue(torch.equal(a, b)); self.assertEqual(ka.keys(), kb.keys())
            for key in ka:
                self.assertTrue(all(torch.equal(x, y) for x, y in zip(ka[key], kb[key])))
            a, ka = current(tokens[:, 4:5], past_kv=ka, use_cache=True)
            b, kb = old(tokens[:, 4:5], past_kv=kb, use_cache=True)
            self.assertTrue(torch.equal(a, b))
            for key in ka:
                self.assertTrue(all(torch.equal(x, y) for x, y in zip(ka[key], kb[key])))

    def test_old_helpers_unchanged_beyond_three_forward_methods(self):
        for filename in OLD_SHA:
            before = ast.parse((OLD / filename).read_text())
            after = ast.parse((ROOT / "tinylm/model" / filename).read_text())
            cls_names = ("Attention", "Layer") if filename == "modules.py" else ("TiedMLPTransformer",)
            for cls in cls_names:
                left = next(n for n in before.body if isinstance(n, ast.ClassDef) and n.name == cls)
                right = next(n for n in after.body if isinstance(n, ast.ClassDef) and n.name == cls)
                old_fns = {x.name: ast.dump(x) for x in left.body if isinstance(x, ast.FunctionDef) and x.name != "forward"}
                new_fns = {x.name: ast.dump(x) for x in right.body if isinstance(x, ast.FunctionDef) and x.name != "forward"}
                self.assertEqual(old_fns, new_fns)
        self.assertEqual(ast.dump(next(x for x in ast.parse((OLD / 'modules.py').read_text()).body if isinstance(x, ast.FunctionDef) and x.name == 'apply_rope')),
                         ast.dump(next(x for x in ast.parse((ROOT / 'tinylm/model/modules.py').read_text()).body if isinstance(x, ast.FunctionDef) and x.name == 'apply_rope')))

    def test_selected_gold_change_cannot_change_corrupted_input_or_logits(self):
        model, _ = model_pair(); model.eval(); tokens, docs = fixture()
        changed = tokens.clone(); changed[0, 1] = 99; changed[0, 4] = 101
        a = h.mntp_batch(tokens, docs, selection(), vocab_size=128)
        b = h.mntp_batch(changed, docs, selection(), vocab_size=128)
        self.assertTrue(torch.equal(a.inputs, b.inputs)); self.assertTrue(torch.equal(a.attention_mask, b.attention_mask))
        with torch.no_grad():
            x = model(a.inputs, attention_mask=a.attention_mask)
            y = model(b.inputs, attention_mask=b.attention_mask)
        self.assertTrue(torch.equal(x, y)); self.assertFalse(torch.equal(a.targets, b.targets))
        self.assertNotEqual(float(h.objective_mean(x, a.targets)[0]), float(h.objective_mean(y, b.targets)[0]))

    def test_other_document_changes_do_not_change_first_document_logits(self):
        model, _ = model_pair(); model.eval(); tokens, docs = fixture()
        a = h.causal_batch(tokens, docs, vocab_size=128)
        changed = a.inputs.clone(); changed[:, 3:6] = torch.tensor([91, 92, 93])
        for bi in (False, True):
            mask = h.document_visibility(docs[:, :-1], bidirectional=bi)
            with torch.no_grad():
                x = model(a.inputs, attention_mask=mask); y = model(changed, attention_mask=mask)
            self.assertTrue(torch.equal(x[:, :3], y[:, :3]))

    def test_causal_future_block_and_bidirectional_future_access(self):
        model, _ = model_pair(); model.eval(); tokens, docs = fixture()
        a = tokens[:, :-1]; b = a.clone(); b[0, 2] = 91
        with torch.no_grad():
            causal = h.document_visibility(docs[:, :-1], bidirectional=False)
            bi = h.document_visibility(docs[:, :-1], bidirectional=True)
            ca, cb = model(a, attention_mask=causal), model(b, attention_mask=causal)
            ba, bb = model(a, attention_mask=bi), model(b, attention_mask=bi)
        self.assertTrue(torch.equal(ca[:, :2], cb[:, :2]))
        self.assertGreater(float((ba[:, 0] - bb[:, 0]).abs().max()), 1e-7)

    def test_pad_and_other_document_input_activation_gradients_are_zero(self):
        model, _ = model_pair(); tokens, docs = fixture(); captured = []
        original_embedding = F.embedding
        def capture(*args, **kwargs):
            out = original_embedding(*args, **kwargs)
            out.retain_grad(); captured.append(out)
            return out
        # The actual Transformer uses F.embedding with its weight accessor,
        # rather than calling model.emb(...); a module hook observes nothing.
        with patch.object(transformer.F, 'embedding', side_effect=capture):
            mask = h.document_visibility(docs[:, :-1], bidirectional=True)
            logits = model(tokens[:, :-1], attention_mask=mask)
            logits[0, 0, 77].backward()
            grad = captured[0].grad
            self.assertGreater(float(grad[0, 2].abs().sum()), 0.)
            self.assertTrue(torch.equal(grad[0, 3:], torch.zeros_like(grad[0, 3:])))
            # A tied output vocabulary row is not a PAD input activation.
            self.assertGreater(float(model.emb.weight.grad[0].abs().sum()), 0.)

    def test_checkpoint_on_off_all_owner_consumer_shared_gradients_match(self):
        off, on = model_pair(); on.cfg.grad_checkpoint = True
        tokens, docs = fixture(); batch = h.mntp_batch(tokens, docs, selection(), vocab_size=128)
        a = off(batch.inputs, attention_mask=batch.attention_mask)
        b = on(batch.inputs, attention_mask=batch.attention_mask)
        self.assertTrue(torch.equal(a, b))
        h.objective_mean(a, batch.targets)[0].backward(); h.objective_mean(b, batch.targets)[0].backward()
        self.assert_gradients(off, on)
        names = gradients(on)
        self.assertTrue(any('k_proj' in n and v is not None for n, v in names.items()))
        self.assertTrue(any('v_proj' in n and v is not None for n, v in names.items()))
        self.assertIs(on.layers[1].mlp[0], on.layers[2].mlp[0])

    def test_caller_mask_mutation_after_forward_cannot_change_checkpoint_backward(self):
        left, right = model_pair(checkpoint=True)
        tokens, docs = fixture(); batch = h.causal_batch(tokens, docs, vocab_size=128)
        a_mask, b_mask = batch.attention_mask.clone(), batch.attention_mask.clone()
        a, b = left(batch.inputs, attention_mask=a_mask), right(batch.inputs, attention_mask=b_mask)
        a_mask.fill_(True)
        h.objective_mean(a, batch.targets)[0].backward(); h.objective_mean(b, batch.targets)[0].backward()
        self.assert_gradients(left, right)

    def test_hybrid_checkpoint_gradients_match_separate_fresh_branch_reference(self):
        actual, reference = model_pair(checkpoint=True)
        tokens, docs = fixture(); ca = h.causal_batch(tokens, docs, vocab_size=128)
        ma = h.mntp_batch(tokens, docs, selection(), vocab_size=128)
        before = {n: p.detach().clone() for n, p in actual.named_parameters()}
        value, counts = h.hybrid_backward(actual, ca, ma, masked_weight=.25)
        for weight, batch in ((.75, ca), (.25, ma)):
            logits = reference(batch.inputs, attention_mask=batch.attention_mask)
            (weight * F.cross_entropy(logits.reshape(-1, 128), batch.targets.flatten(), ignore_index=-100)).backward()
        self.assert_gradients(actual, reference)
        self.assertTrue(math.isfinite(value)); self.assertEqual(counts['model_forwards'], 2)
        for n, p in actual.named_parameters(): self.assertTrue(torch.equal(p, before[n]), n)

    def test_state_keys_shapes_aliases_and_parameter_values_unchanged(self):
        model, _ = model_pair(); tokens, docs = fixture()
        before = {k: v.clone() for k, v in model.state_dict().items()}
        aliases = [id(layer.mlp[0]) for layer in model.layers]
        model(tokens[:, :-1], attention_mask=h.document_visibility(docs[:, :-1], bidirectional=True))
        self.assertEqual(before.keys(), model.state_dict().keys())
        self.assertTrue(all(torch.equal(v, model.state_dict()[k]) for k, v in before.items()))
        self.assertEqual(aliases, [id(layer.mlp[0]) for layer in model.layers])
        self.assertFalse(any('mask' in key for key in model.state_dict()))

    def test_mask_geometry_type_empty_rows_and_empty_cache_rejected(self):
        model, _ = model_pair(); tokens, docs = fixture(); x = tokens[:, :-1]
        mask = h.document_visibility(docs[:, :-1], bidirectional=True)
        bad = (mask.float(), mask[:, 0], mask[:, :, :-1, :-1], torch.zeros_like(mask))
        for candidate in bad:
            with self.assertRaises(ValueError): model(x, attention_mask=candidate)
        for kwargs in ({'past_kv': {}}, {'use_cache': True}, {'logits_last_only': True},
                       {'return_aux': True}, {'return_hidden': True}, {'return_mtp_hidden': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                model(x, attention_mask=mask, **kwargs)

    def test_unsupported_modes_rejected_before_embedding_or_quant_refresh(self):
        tokens, docs = fixture(); x = tokens[:, :-1]
        mask = h.document_visibility(docs[:, :-1], bidirectional=True)
        for name, value in (('mtp_aux', True), ('return_probs', True), ('reuse_attn_on_dup', True),
                            ('n_modes', 2), ('train_repeat', 2.), ('attn_kind', 'unsupported')):
            model, _ = model_pair(); setattr(model.cfg, name, value)
            with patch.object(model, 'refresh_quant', side_effect=AssertionError('must reject first')) as refresh:
                with self.subTest(name=name), self.assertRaises(ValueError): model(x, attention_mask=mask)
                self.assertFalse(refresh.called)

    def test_actual_gqa_explicit_visibility_forward_and_backward(self):
        off, on = model_pair(); on.cfg.sdpa_gqa = True
        tokens, docs = fixture(); batch = h.mntp_batch(tokens, docs, selection(), vocab_size=128)
        a = off(batch.inputs, attention_mask=batch.attention_mask)
        b = on(batch.inputs, attention_mask=batch.attention_mask)
        self.assertTrue(torch.allclose(a, b, atol=2e-6, rtol=2e-5))
        h.objective_mean(a, batch.targets)[0].backward(); h.objective_mean(b, batch.targets)[0].backward()
        self.assert_gradients(off, on)


if __name__ == '__main__':
    unittest.main()
