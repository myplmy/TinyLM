#!/usr/bin/env python3
"""CPU-only independent recount fixtures; imports no primary benchmark code."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import read_p106b_authorized_benchmark as read


class Contract(unittest.TestCase):
    def test_mc_recomputed_from_scores(self):
        row=dict(sum_nll=[3.,2.],mean_nll=[1.5,1.],n_tokens=[2,2],n_chars=[2,2],
                 score=[2.,1.],pred_harness=1,pred_harness_norm=1,pred_internal=1,gold=1)
        self.assertEqual(read.recount(row),1)
        row['pred_harness']=0
        with self.assertRaises(AssertionError):read.recount(row)

    def test_qa_and_skip(self):
        row=dict(task='korquad_free',answer=' 얼음 ',golds=['얼음'],scores={'whitespace_nfkc_exact':1})
        self.assertEqual(read.recount(row),1)
        self.assertIsNone(read.recount({'skipped':True}))
        self.assertNotEqual(read.text_key('1.2'),read.text_key('12'))

    def test_numeric(self):
        self.assertEqual(read.numeric('#### 1,000'),read.numeric('1000.0'))
        self.assertIsNone(read.numeric('maybe 1000'))

    def test_paired_groups(self):
        keys=[('task',str(i)) for i in range(5)]
        r=read.interval(dict.fromkeys(keys,1),{k:k for k in keys},draws=100)
        self.assertEqual(r['delta'],1)
        self.assertEqual(r['ci'],[1.,1.])


if __name__=='__main__':unittest.main()
