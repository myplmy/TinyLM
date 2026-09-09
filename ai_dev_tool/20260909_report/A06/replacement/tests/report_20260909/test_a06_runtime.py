import unittest
import torch
from tinylm.eval.runtime_audit import inventory_summary, cached_continuation_nll
from support_report import CharacterTokenizer


class RuntimeTests(unittest.TestCase):
    def test_shared_storage_and_plain_attribute_count_once(self):
        model = torch.nn.Module()
        t = torch.arange(12, dtype=torch.float32)
        model.register_buffer("one", t)
        model.plain = {"alias": t.view(3, 4), "code": torch.ones(5, dtype=torch.uint8)}
        self.assertEqual(inventory_summary(model)["bytes"], 12 * 4 + 5)

    def test_old_new_cache_overlap_is_counted(self):
        old = torch.zeros(1, 1, 3, 2)
        new = torch.zeros(1, 1, 4, 2)
        report = inventory_summary({"kv": old}, {"kv": new})
        self.assertEqual(report["bytes"], (6 + 8) * 4)

    def test_cached_nll_all_answer_positions(self):
        class Uniform:
            def __call__(self, ids, **kwargs):
                return torch.zeros((*ids.shape, 32)), {"kv": None}
        result, error = cached_continuation_nll(Uniform(), CharacterTokenizer(), "질문", "답변",
                                                device="cpu", seq_max=20)
        self.assertIsNone(error)
        self.assertEqual(result["tokens"], 2)
        self.assertAlmostEqual(result["nll_mean"], 5 * __import__("math").log(2), places=5)

    def test_last_position_head_matches_full_head(self):
        from tinylm.config import TMTConfig
        from tinylm.model import TiedMLPTransformer
        cfg = TMTConfig(vocab_size=32, dim=16, ffn_dim=32, n_q_heads=2, n_kv_heads=1,
                        emb_rank=8, n_prelude=1, n_middle=2, n_coda=1, mlp_group=2,
                        micro_group=8, max_seq_len=32)
        model = TiedMLPTransformer(cfg).eval()
        model.freeze_quant()
        x = torch.tensor([[1, 2, 3, 4]])
        with torch.inference_mode():
            full, full_kv = model(x, use_cache=True)
            last, last_kv = model(x, use_cache=True, logits_last_only=True)
        self.assertEqual(tuple(last.shape), (1, 1, 32))
        self.assertTrue(torch.allclose(full[:, -1:], last, atol=1e-5, rtol=1e-5))
        self.assertEqual(set(full_kv), set(last_kv))
        for key in full_kv:
            for a, b in zip(full_kv[key], last_kv[key]):
                self.assertTrue(torch.equal(a, b))
        model.clear_quant()
        model.train()
        with self.assertRaises(ValueError):
            model(x, logits_last_only=True)
