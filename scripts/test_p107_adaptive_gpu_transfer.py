"""CPU oracle for the synthetic GPU argmax/transfer diagnostic."""
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import torch
from scripts import diag_p107_adaptive_gpu_transfer as d


class ArgmaxContract(unittest.TestCase):
    def test_full_and_gathered_ids_match_a_literal_shifted_oracle(self):
        targets=torch.tensor([[41,-100,43],[-100,45,46]])
        logits=torch.full((2,3,64),-9.)
        expected=torch.tensor([[41,0,0],[0,45,0]])
        for b in range(2):
            for t in range(3):logits[b,t,expected[b,t]]=3.
        for mode in ('full','selected'):
            actual,metrics=d.collect_ids(logits,targets,mode)
            self.assertTrue(torch.equal(actual,expected))
            self.assertEqual(metrics['transferred_id_bytes'],48 if mode=='full' else 32)
            self.assertEqual(metrics['extra_gather_logit_bytes'],0 if mode=='full' else 4*64*4)

    def test_non_selected_rows_do_not_contribute_to_observation(self):
        batch,expected=d.prepare_fixture(32768)
        self.assertEqual(int((batch.targets!=-100).sum()),batch.target_count)
        self.assertTrue(bool((expected[batch.targets==-100]==0).all()))

    def test_empty_or_bad_shapes_are_rejected(self):
        with self.assertRaises(ValueError):d.collect_ids(torch.zeros(1,3,64),torch.full((1,3),-100),'full')
        with self.assertRaises(ValueError):d.collect_ids(torch.zeros(1,3,64),torch.ones(2,3,dtype=torch.long),'full')


if __name__=='__main__':unittest.main()
