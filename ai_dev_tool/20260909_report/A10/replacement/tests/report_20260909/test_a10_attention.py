import unittest
import torch
from tinylm.eval.attention_stats import causal_null, attention_mass


class SinkTests(unittest.TestCase):
    def test_correct_1024_query_null(self):
        self.assertAlmostEqual(causal_null(1024, 4, 256)["sink"], 0.0251009466, places=9)

    def test_uniform_causal_mass_matches_null_and_union(self):
        seq = 8
        p = torch.ones(seq, seq).tril()
        p = (p / p.sum(-1, keepdim=True))[None, None]
        for start in (0, 4, 7):
            row = attention_mass(p, 2, 3, start)
            for key in ("sink", "window", "union"):
                self.assertAlmostEqual(row["observed"][key], row["uniform_causal_null"][key], places=6)
            self.assertLessEqual(row["observed"]["union"], 1)

    def test_future_attention_fails(self):
        p = torch.ones(1, 1, 3, 3) / 3
        with self.assertRaises(ValueError):
            attention_mass(p, 1, 1)
