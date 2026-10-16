"""Synthetic causal-prefix contracts; no actual assets or model loading."""
import copy
import unittest
import torch
from scripts import diag_p106b_night_causal_readback as d
from scripts.test_p106b_night_question_scores import cases,Tokenizer


class CausalTests(unittest.TestCase):
    def test_shifted_prefix_matches_actual_prompt_without_future_answer(self):
        tok=Tokenizer();bundle=d.prior.method.build_records(cases(),tok)
        values=d.prefixes(bundle,tok)
        self.assertEqual(len(values),2)
        for value in values:
            for cell in value['cells']:
                self.assertEqual(len(value['prefix']),cell['content_positions'][0]+1)
                self.assertNotEqual(value['prefix'],cell['x'])

    def test_corrupted_cell_and_missing_candidate_refused(self):
        tok=Tokenizer();bundle=d.prior.method.build_records(cases(),tok)
        bad=copy.deepcopy(bundle);bad['cells'][0]['x'][0]+=1
        with self.assertRaises(ValueError):d.prefixes(bad,tok)
        bad=copy.deepcopy(bundle);bad['cells'].pop()
        with self.assertRaises(ValueError):d.prefixes(bad,tok)

    def test_exact_and_changed_vectors_report_without_threshold(self):
        a=torch.tensor([1.,2.]);same=d.delta(a,a.clone());other=d.delta(a,torch.tensor([1.,4.]))
        self.assertTrue(same['exact_equal']);self.assertEqual(same['max_abs'],0.)
        self.assertFalse(other['exact_equal']);self.assertEqual(other['max_abs'],2.)
        self.assertNotIn('pass',other)

    def test_shape_empty_nonfinite_rejected(self):
        for a,b in ((torch.ones(2),torch.ones(3)),(torch.empty(0),torch.empty(0)),
                    (torch.tensor([float('nan')]),torch.zeros(1))):
            with self.assertRaises(ValueError):d.delta(a,b)

    def test_source_selection_coverage_not_answer_based(self):
        rows=[dict(source_bundle_id=str(i),bundle=dict(language='ko' if i<2 else 'en')) for i in range(4)]
        self.assertEqual(d.selected(rows,['0','1','2','3']),rows)
        with self.assertRaises(ValueError):d.selected(rows,['0','0','2','3'])
        with self.assertRaises(ValueError):d.selected(rows,['0','1','2','4'])

    def test_no_cuda_training_or_checkpoint_save_path(self):
        text=(d.ROOT/'scripts/diag_p106b_night_causal_readback.py').read_text()
        for fragment in ('device=\'cuda\'', 'optimizer.step(', '.backward(', 'torch.save(', 'empty_cache('):
            self.assertNotIn(fragment,text)
        self.assertIn("device='cpu'",text);self.assertIn('wall_limit(600)',text)


if __name__=='__main__':unittest.main()
