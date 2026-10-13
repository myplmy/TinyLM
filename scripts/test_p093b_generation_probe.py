"""CPU probability/prefix fixtures only; no checkpoint, cache, GPU or tokenizer."""
from __future__ import annotations
import inspect
from pathlib import Path
import sys
import unittest
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p093b_generation_probe as probe
from scripts.diag_p093b_calibration_recovery import PROBES

class ProbeTests(unittest.TestCase):
    def test_boundary_token_is_included_and_probability_renormalized(self):
        p=torch.tensor([[.6,.25,.1,.05]])
        self.assertTrue(torch.allclose(probe.nucleus_probs(p,.8),torch.tensor([[.6/.85,.25/.85,0.,0.]])))

    def test_one_never_removes_positive_mass(self):
        p=torch.tensor([[.2,.8]])
        self.assertTrue(torch.allclose(probe.nucleus_probs(p,1),p))

    def test_invalid_probability_and_threshold_fail_closed(self):
        for p,t in ((torch.tensor([[0.,0.]]),.95),(torch.tensor([[float("nan"),1.]]),.95),
                    (torch.tensor([[-1.,2.]]),.95),(torch.ones(1,2),0)):
            with self.assertRaises(ValueError):probe.nucleus_probs(p,t)

    def test_global_sampler_restores_on_failure(self):
        original=torch.multinomial
        with self.assertRaises(RuntimeError),probe.nucleus_scope():
            self.assertIsNot(torch.multinomial,original)
            raise RuntimeError("fixture")
        self.assertIs(torch.multinomial,original)

    def test_example_is_a_prefix_not_a_replacement(self):
        for ident,text in PROBES:
            self.assertEqual(probe.prompt(ident,text,"plain"),text)
            self.assertTrue(probe.prompt(ident,text,"fewshot").endswith(text))
        with self.assertRaises(ValueError):probe.prompt("unknown","x","fewshot")

    def test_existing_sampler_has_no_native_top_p_kwarg(self):
        from tinylm.infer.generate import sample
        self.assertNotIn("top_p",inspect.signature(sample).parameters)

    def test_new_checkonly_never_reads_saved_patch_or_model(self):
        from scripts import diag_p093b_generation_attribution as d
        from unittest.mock import patch
        import io
        with patch.object(sys,"argv",["fixture","--mode","decode","--check-only"]), \
             patch.object(d,"source",side_effect=AssertionError("private patch read")), \
             patch.object(d,"execute",side_effect=AssertionError("model")),patch("sys.stdout",new=io.StringIO()):
            self.assertEqual(d.main(),0)

    def test_new_diagnostic_includes24_cache_off_pairs_and_no_training(self):
        from scripts import diag_p093b_generation_attribution as d
        import argparse
        m=d.metadata(argparse.Namespace(mode="decode",tag="fixture"))
        self.assertEqual(m["new_generations"],192)
        self.assertEqual(m["reused_plain_greedy_answers"],24)
        self.assertEqual(m["optimizer_updates"],0)
        source=inspect.getsource(d.execute)
        self.assertIn("use_cache=False",source)
        self.assertIn('directory/"partial.json"',source)

    def test_representation_separates_legitimate_same_token_pairs(self):
        x=torch.tensor([[1.,0.],[1.,0.],[0.,1.]])
        r=probe.representation_stats(x,[7,7,9])
        self.assertEqual(r["same_token"]["pairs"],1)
        self.assertEqual(r["same_token"]["mean"],1.)
        self.assertEqual(r["different_token"]["pairs"],2)
        self.assertEqual(r["different_token"]["mean"],0.)
        self.assertAlmostEqual(r["centered_covariance_entropy_rank"],1.,places=5)

    def test_representation_constant_directions_are_not_nan_or_semantic_failure(self):
        r=probe.representation_stats(torch.ones(3,2),[1,2,3])
        self.assertAlmostEqual(r["different_token"]["mean"],1.,places=6)
        self.assertEqual(r["centered_covariance_entropy_rank"],0.)
        self.assertTrue(r["decision"].startswith("NONE"))
        self.assertEqual(probe.representation_stats(torch.ones(1,2),[1])["status"],"INSUFFICIENT_POSITIONS")
        with self.assertRaises(ValueError):probe.representation_stats(torch.zeros(2,2),[1,2])

    def test_calibration_allows_only_exact_reviewed_default_off_migration(self):
        from scripts import diag_p093b_generation_attribution as d
        key='tinylm/infer/generate.py';before,after=d.NATIVE_MTP_API_MIGRATION[key]
        updates=d.validate_calibration_sources({key:before,'other':'A'}, {key:after,'other':'A'})
        self.assertEqual(len(updates),1)
        for current in ({key:'unknown','other':'A'}, {key:after,'other':'B'}, {key:after}):
            with self.assertRaises(ValueError):d.validate_calibration_sources({key:before,'other':'A'},current)

    def test_default_ntp_sample_body_matches_archived_pre_mtp_implementation(self):
        import ast,subprocess,hashlib
        archived=subprocess.check_output(['git','show','cb9b335:tinylm/infer/generate.py'],cwd=ROOT,text=True)
        from scripts import diag_p093b_generation_attribution as d
        self.assertEqual(hashlib.sha256(archived.encode()).hexdigest().upper(),
            d.NATIVE_MTP_API_MIGRATION['tinylm/infer/generate.py'][0])
        current=(ROOT/'tinylm/infer/generate.py').read_text()
        def default_body(text):
            fn=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='sample')
            nodes=[n for n in fn.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant)
                and isinstance(n.value.value,str))]
            nodes=[n for n in nodes if not(isinstance(n,ast.If) and isinstance(n.test,ast.Compare)
                and isinstance(n.test.left,ast.Name) and n.test.left.id=='mtp_tokens')]
            return ast.dump(ast.Module(body=nodes,type_ignores=[]),include_attributes=False)
        self.assertEqual(default_body(archived),default_body(current))

if __name__=="__main__":unittest.main(verbosity=2)
