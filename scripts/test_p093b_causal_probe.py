"""CPU synthetic tiny-architecture intervention contracts. No private IO."""
from contextlib import nullcontext
from unittest import mock
import unittest
import torch
from tinylm.config import TMTConfig
from tinylm.model.transformer import TiedMLPTransformer
from scripts import p093b_causal_probe as core


class CausalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def model(self):
        torch.manual_seed(1337)
        cfg = TMTConfig(vocab_size=32, dim=16, ffn_dim=32, n_q_heads=4, n_kv_heads=2,
            emb_rank=0, n_prelude=1, n_middle=2, n_coda=1, tie_mlp=False, mlp_group=1,
            micro_group=4, max_seq_len=64)
        m = TiedMLPTransformer(cfg).eval()
        m.set_anneal(1.); m.freeze_quant()
        return m

    def test_controls_preserve_anchor_length_and_last_token(self):
        anchor, body = [1, 2, 3], [4, 5, 6] * 8
        c = core.history_controls(anchor, body)
        self.assertEqual(len({len(v) for v in c.values()}), 1)
        self.assertTrue(all(v[:3] == anchor and v[-1] == body[-1] for v in c.values()))
        self.assertEqual(sorted(c["order_shuffle"][3:]), sorted(body))
        self.assertEqual(c, core.history_controls(anchor, body))

    def test_single_token_shuffle_degeneracy_remains_explicit(self):
        c = core.history_controls([1,2,3], [5] * 8)
        self.assertEqual(c["observed"], c["order_shuffle"])
        self.assertNotEqual(c["observed"], c["prompt_cycle"])

    def test_same_activation_patch_is_noop_weights_and_hooks_preserved(self):
        m = self.model()
        before = {k:v.clone() for k,v in m.state_dict().items()}
        a, states, visits = core.controlled_forward(m, [1,4,5])
        b, _, _ = core.controlled_forward(m, [1,4,5], patches={i:states[(i,0)] for i in range(4)})
        self.assertTrue(torch.equal(a,b))
        self.assertEqual(visits, list(range(4)))
        self.assertTrue(all(torch.equal(before[k],v) for k,v in m.state_dict().items()))
        self.assertTrue(all(not l._forward_hooks for l in m.layers))

    def test_donor_patch_changes_output_without_overwriting_source_tensor(self):
        m = self.model()
        a, states, _ = core.controlled_forward(m, [1,4,5])
        donor = states[(3,0)].clone(); before = donor.clone()
        donor[0] += 2.
        modified = donor.clone()
        b, _, _ = core.controlled_forward(m, [1,4,5], patches={3:donor})
        self.assertFalse(torch.equal(a,b))
        self.assertTrue(torch.equal(donor,modified))
        self.assertTrue(torch.equal(before,states[(3,0)]))

    def test_shape_error_restores_all_hooks(self):
        m = self.model()
        with self.assertRaises(ValueError):
            core.controlled_forward(m, [1,2], patches={0:torch.zeros(3)})
        self.assertTrue(all(not l._forward_hooks for l in m.layers))

    def test_recurrence_restored_even_when_forward_fails(self):
        m = self.model()
        with self.assertRaises(RuntimeError):
            with core.recurrence(m, 2.):
                self.assertEqual(len(m.visit_schedule()), 6)
                raise RuntimeError("fixture")
        self.assertEqual(m.cfg.infer_repeat, 1.)

    def test_actual_R2_visits_and_occurrence_keys_recorded(self):
        m = self.model()
        with core.recurrence(m, 2.):
            a, states, visits = core.controlled_forward(m, [1,2])
            self.assertEqual(len(visits), 6)
            self.assertIn((1,1),states); self.assertIn((2,1),states)
            with self.assertRaises(ValueError):
                core.controlled_forward(m, [1,2], patches={1:states[(1,0)]})
        self.assertEqual(m.visit_schedule(), list(range(4)))

    def test_training_recurrence_not_silently_infer_changed(self):
        m=self.model(); m.cfg.train_repeat=2.
        with self.assertRaises(ValueError):
            with core.recurrence(m,2.): pass

    def test_small_logit_gap_does_not_claim_normalized_causal_recovery(self):
        r={"focus_minus_eos_logit":1., "focus_probability":.1}
        p={"focus_minus_eos_logit":2., "focus_probability":.2}
        self.assertIsNone(core.patch_effect(p,r,r)["normalized_recovery"])
        self.assertEqual(core.patch_effect(p,r,r)["delta_focus_minus_eos_logit"],1.)

    def test_metrics_finite_and_explicit_not_quality_gate(self):
        d=core.output_metrics(torch.tensor([0.,2.,1.,-1.]),1,3,str)
        self.assertEqual(d["focus_minus_eos_logit"],3.)
        self.assertEqual(d["argmax_id"],1)
        with self.assertRaises(ValueError):
            core.output_metrics(torch.tensor([float("nan"),0.]),1,0,str)

    def test_forced_cache_replay_is_same_prefix_not_free_generations(self):
        m=self.model()
        rows=core.cache_prefix_pairs(m,[1,2],[3,4,5], [1,2,4], mode="fp32_math")
        self.assertEqual([r["step"] for r in rows],[1,2,4])
        self.assertTrue(all(r["max_abs"]<1e-4 for r in rows))

    def test_precision_restores_global_setting_after_exception(self):
        before=torch.backends.cuda.matmul.fp32_precision
        with self.assertRaises(RuntimeError):
            with core.precision("fp32_math"): raise RuntimeError("fixture")
        self.assertEqual(torch.backends.cuda.matmul.fp32_precision,before)

    def test_driver_checkonly_has_no_private_source_or_model_loading(self):
        from scripts import diag_p093b_causal_probe as driver
        import io
        with mock.patch.object(driver,"source_rows",side_effect=AssertionError("private source")), \
             mock.patch.object(driver,"execute",side_effect=AssertionError("model")), \
             mock.patch("sys.argv",["fixture","--mode","intervene","--check-only"]), \
             mock.patch("sys.stdout",new=io.StringIO()):
            self.assertEqual(driver.main(),0)

    def test_case_builder_keeps_real_block_anchor_and_listing_source_distinct(self):
        from scripts import diag_p093b_causal_probe as driver
        from types import SimpleNamespace
        tok=SimpleNamespace(encode=lambda text:SimpleNamespace(ids=[1,2]))
        rows=[]
        for subject,q,block,leading in [("parent","ko_context",[3,4],[]),
                ("shared","ko_context",[5],[6,7]),("parent","en_math",[8,9],[])]:
            ids=leading+block*8
            rows.append({"subject":subject,"id":q,"prompt":"fixture","generated_token_ids":ids,
                "loop_candidates":[{"first_block_token":len(leading)+1,"onset_token":len(leading)+len(block)+1,
                "period":len(block),"block_ids":block}]})
        listing=sum(([10,11,12,20+i,13,14,15,16,17] for i in range(8)),[])
        rows.append({"subject":"rank64","id":"ko_math","prompt":"fixture","generated_token_ids":listing})
        result=driver.cases(rows,tok)
        self.assertEqual(len(result),4)
        self.assertEqual(result[1]["anchor"],[1,2,6,7])
        self.assertEqual(result[2]["bodies"][8],listing)


if __name__ == "__main__":
    unittest.main(verbosity=2)
