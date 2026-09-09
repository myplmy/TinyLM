import unittest
import torch
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from tinylm.train.optimizer_audit import matrix_decay_groups
from tinylm.train.muon import split_params


class OptimizerRecipeTests(unittest.TestCase):
    def test_matrix_only_wd_override_keeps_embedding_and_lrm_groups(self):
        cfg = TMTConfig(vocab_size=32, dim=16, ffn_dim=32, n_q_heads=2, n_kv_heads=1,
                        emb_rank=8, n_prelude=1, n_middle=2, n_coda=1, mlp_group=2,
                        micro_group=8, max_seq_len=32, mlp_lrm=True, mlp_lrm_wd=0.03)
        model = TiedMLPTransformer(cfg)
        groups, matrices = matrix_decay_groups(model, 0.001, 0.0)
        mids = {id(p) for p in matrices}
        self.assertEqual(mids, {id(p) for p in split_params(model)[0]})
        assigned = [id(p) for g in groups for p in g["params"]]
        self.assertEqual(len(assigned), len(set(assigned)))
        self.assertEqual(set(assigned), {id(p) for p in model.parameters() if p.requires_grad})
        by_id = {id(p): g for g in groups for p in g["params"]}
        self.assertTrue(all(by_id[i]["weight_decay"] == 0 for i in mids))
        self.assertEqual(by_id[id(model.emb.weight)]["weight_decay"], 0.1)
        for name, p in model.named_parameters():
            if name.endswith(".lrm"):
                self.assertEqual(by_id[id(p)]["weight_decay"], 0.03)
