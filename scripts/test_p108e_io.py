"""CPU fixture coverage of native hook windows and original-centred writes."""
import unittest
import numpy as np
import torch
from scripts import p108e_io as study


class ObservationContracts(unittest.TestCase):
    def test_full_and_target_hooks_keep_all_fourteen_owners(self):
        class Fixture(torch.nn.Module):
            def __init__(self):
                super().__init__();self.emb=torch.nn.Embedding(9,3)
                self.blocks=torch.nn.ModuleList([torch.nn.Linear(3,3,bias=False)for _ in range(14)])
                self.norm_f=torch.nn.Identity();self.head=torch.nn.Linear(3,9,bias=False)
            def forward(self,ids,return_hidden=False):
                hidden=self.emb(ids)
                for block in self.blocks:hidden=hidden+.1*torch.tanh(block(hidden))
                return self.norm_f(hidden)
            def _head_logits(self,hidden):return self.head(hidden)
        model=Fixture();physical=dict(enumerate(model.blocks))
        row=dict(ids=[1,3,4,2],targets=[4,2],start=2)
        for mode,length in (("full",4),("targets",2)):
            logits,saved=study.native_forward(dict(model=model),physical,row,features=mode)
            self.assertEqual(tuple(logits.shape),(2,9))
            self.assertEqual(set(saved),{*range(14),"endpoint"})
            for index in range(14):self.assertEqual(saved[index]["keys"].shape,(length,3))

    def test_target_layout_and_question_balancing_are_exact(self):
        layout=study.target_indices([dict(ids=[1,2,3,4],start=2,targets=[3,4]),
                                     dict(ids=[5,6,7],start=1,targets=[6,7])])
        np.testing.assert_array_equal(layout["target_from_full"],[2,3,5,6])
        self.assertEqual(layout["offsets"],[(0,2),(2,4)])
        self.assertAlmostEqual(float(layout["full_weights"].sum()),2.)
        self.assertAlmostEqual(float(layout["target_weights"].sum()),2.)


if __name__=="__main__":unittest.main()
