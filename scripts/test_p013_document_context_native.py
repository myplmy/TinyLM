"""CPU regressions for the indexed document source and native G4 causal update."""

from dataclasses import replace
import unittest
from unittest.mock import patch

import torch
from torch.nn import functional as F

from scripts.diag_p107_g4_r2_visibility import prepare_r2
from scripts.test_p107_indexed_document_source import Fixture, rows_for, source
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer, transformer
from tinylm.train.context_curriculum import ContextPlan
from tinylm.train.document_context_curriculum import backward_document_context, regroup_document_context
from tinylm.train.indexed_document_source import IndexedDocumentInput


def g4():
    torch.manual_seed(1337)
    cfg = TMTConfig(vocab_size=64, dim=32, ffn_dim=64, emb_rank=8, max_seq_len=24,
                    n_q_heads=4, n_kv_heads=2, n_prelude=2, n_middle=12, n_coda=2,
                    tie_mlp=True, mlp_group=4, cla_group=2, micro_group=8,
                    grad_checkpoint=True, train_repeat=2.0, infer_repeat=1.0)
    model = TiedMLPTransformer(cfg)
    model.set_anneal(1.)
    return model.train()


def assert_same_draws(actual, expected):
    for (x, dx), (y, dy) in zip(actual, expected, strict=True):
        torch.testing.assert_close(x, y, rtol=0, atol=0)
        torch.testing.assert_close(dx, dy, rtol=0, atol=0)


class NativeDocumentContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_indexed_packed_rows_match_flat_window_oracle(self):
        fixture = Fixture(rows_for([3, 4, 9, 5, 11, 15]))
        stream = source(fixture.load(), packed=True, length=16, batch=2, micros=2)
        tokens = torch.tensor([tok for row in fixture.rows for tok in row["token_ids"]])
        owners = torch.tensor([index for index, row in enumerate(fixture.rows) for _ in row["token_ids"]])
        rng = torch.Generator().manual_seed(19)
        saw_multiple_documents = False
        for _ in range(12):
            expected = []
            for _ in range(stream.micros):
                starts = [int(torch.randint(len(tokens)-16, (1,), generator=rng)) for _ in range(stream.batch)]
                windows = [slice(s, s+17) for s in starts]
                expected.append(tuple(torch.stack([flat[w] for w in windows]) for flat in (tokens, owners)))
            actual = stream.next_update()
            assert_same_draws(actual, expected)
            saw_multiple_documents |= any(bool((docs[:, 1:] != docs[:, :-1]).any()) for _, docs in actual)
        self.assertTrue(saw_multiple_documents)
        self.assertEqual(stream.cursor, 12)
        self.assertTrue(torch.equal(rng.get_state(), stream.state_dict()["rng"]))
        self.assertEqual(stream.contract["sampling"], "UNIFORM_PACKED_WINDOW_WITH_REPLACEMENT")

    def test_packed_partial_read_replays_and_rejects_padded_state(self):
        fixture = Fixture(rows_for([3, 4, 5]))
        packet = fixture.load()
        options = dict(length=11, batch=1, micros=1)
        stream = source(packet, packed=True, **options)
        before = stream.state_dict()
        original = IndexedDocumentInput.read_tokens

        def interrupted(data, index):
            if index == 1:
                raise OSError("interrupted inside a packed row")
            return original(data, index)

        with patch.object(IndexedDocumentInput, "read_tokens", interrupted), self.assertRaises(OSError):
            stream.next_update()
        self.assertEqual(stream.cursor, before["cursor"])
        self.assertTrue(torch.equal(stream.state_dict()["rng"], before["rng"]))
        expected = stream.next_update()
        self.assertEqual(expected[0][1].tolist(), [[0]*3 + [1]*4 + [2]*5])
        resumed = source(fixture.load(), packed=True, **options)
        resumed.load_state_dict(stream.state_dict())
        assert_same_draws(resumed.next_update(), stream.next_update())
        with self.assertRaises(ValueError):
            source(packet, **options).load_state_dict(stream.state_dict())
        with self.assertRaises(ValueError):
            source(packet, packed=True, length=12)

    def test_native_route_rejects_changed_schedule_and_preserves_document_isolation(self):
        model = g4()
        docs = torch.tensor([[0, 0, 0, 0, 1, 1, 1, 1, 1]])
        x = torch.arange(35, 44).reshape(1, -1)
        plan = ContextPlan(((1, 8),), micro_bs=1, base_accum=1, full_length=8)
        batch, = regroup_document_context(((x, docs),), plan, 8, vocab_size=64).batches
        mask, inputs = batch.attention_mask, batch.inputs
        self.assertEqual(len(model.visit_schedule()), 28)
        with self.assertRaises(ValueError):
            model(inputs, attention_mask=mask)
        with self.assertRaises(ValueError):
            model(inputs, allow_fixed_g4_r2=True)
        with self.assertRaises(ValueError):
            model(inputs, attention_mask=mask, allow_fixed_g4_r2=True, use_cache=True)
        wrong = model.visit_schedule()
        wrong[15], wrong[16] = wrong[16], wrong[15]
        with patch.object(model, "visit_schedule", return_value=wrong), self.assertRaises(ValueError):
            model(inputs, attention_mask=mask, allow_fixed_g4_r2=True)
        with torch.no_grad():
            native = model(inputs, attention_mask=mask, allow_fixed_g4_r2=True)
            edited = inputs.clone()
            edited[:, :4] += 10
            updated = model(edited, attention_mask=mask, allow_fixed_g4_r2=True)
            with patch.object(transformer, "prepare_visibility", prepare_r2):
                reference = model(inputs, attention_mask=mask)
        self.assertTrue(torch.equal(native, reference))
        self.assertTrue(torch.equal(native[:, 4:], updated[:, 4:]))
        self.assertFalse(torch.equal(native[:, :4], updated[:, :4]))

    def test_global_target_count_weights_gradients_and_skips_empty_micro(self):
        owners = [[0, 0, 0, 0, 1, 1, 1, 1, 1], [2, 2, 2, -1, -1, -1, -1, -1, -1], [-1]*9]
        windows = tuple((torch.arange(35+i, 44+i).reshape(1, -1).masked_fill(docs < 0, 0), docs)
                        for i, row in enumerate(owners) for docs in (torch.tensor([row]),))
        plan = ContextPlan(((1, 4), (2, 8)), micro_bs=1, base_accum=3, full_length=8)
        update = regroup_document_context(windows, plan, plan.length_at(0), vocab_size=64)
        self.assertEqual([b.target_count for b in update.batches], [7, 2, 0])
        with self.assertRaises(ValueError):
            regroup_document_context((windows[2],)*3, plan, 4, vocab_size=64)
        actual = g4()
        with patch.object(actual, "forward", wraps=actual.forward) as forward:
            with self.assertRaises(ValueError):
                backward_document_context(actual, replace(update, target_count=8))
            self.assertEqual(forward.call_count, 0)
            loss = backward_document_context(actual, update)
            self.assertEqual(forward.call_count, 2)
        reference = g4()
        gradients, means = [], []
        with patch.object(transformer, "prepare_visibility", prepare_r2):
            for batch in update.batches[:2]:
                reference.zero_grad(set_to_none=True)
                logits = reference(batch.inputs, attention_mask=batch.attention_mask)
                value = F.cross_entropy(logits.flatten(0, 1), batch.targets.flatten())
                value.backward()
                means.append(float(value.detach()))
                gradients.append({name: p.grad.clone() for name, p in reference.named_parameters() if p.grad is not None})
        self.assertAlmostEqual(loss, (7*means[0]+2*means[1])/9, places=5)
        max_wrong_weight = 0.
        for name, parameter in actual.named_parameters():
            if name in gradients[0]:
                a, b = gradients[0][name], gradients[1][name]
                torch.testing.assert_close(parameter.grad, (7*a+2*b)/9, atol=2e-6, rtol=2e-5)
                max_wrong_weight = max(max_wrong_weight, float((parameter.grad-(a+b)/2).abs().max()))
            else:
                self.assertIsNone(parameter.grad)
        self.assertGreater(max_wrong_weight, 1e-4)

    def test_packed_source_to_native_g4_optimizer_step(self):
        stream = source(Fixture(rows_for([3, 5, 10, 4, 24, 32])).load(),
                        packed=True, length=16, batch=2, micros=2)
        plan = ContextPlan(((1, 8), (2, 16)), micro_bs=2, base_accum=2, full_length=16)
        model = g4()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        before = model.emb.weight.detach().clone()
        for index in range(2):
            update = regroup_document_context(stream.next_update(), plan, plan.length_at(index), vocab_size=64)
            self.assertEqual(update.input_slots, 64)
            self.assertGreater(update.excluded_targets, 0)
            optimizer.zero_grad(set_to_none=True)
            self.assertGreater(backward_document_context(model, update), 0.)
            optimizer.step()
        self.assertFalse(torch.equal(before, model.emb.weight.detach()))
        self.assertEqual(stream.cursor, 2)
        self.assertFalse(torch.cuda.is_initialized())


if __name__ == "__main__":
    unittest.main()
