#!/usr/bin/env python3
"""CPU-only public-benchmark contracts, no model or source data loaded."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_authorized_benchmark as bench


class Contract(unittest.TestCase):
    def test_sample_prefix_is_reproducible(self):
        self.assertEqual(bench.sampled_indices(20,100),bench.sampled_indices(20,100))
        self.assertEqual(len(set(bench.sampled_indices(20,100))),20)

    def test_no_protected_tasks(self):
        self.assertNotIn('stage1_heldout',bench.TASKS)
        self.assertNotIn('sft_fresh_eval',bench.TASKS)
        self.assertEqual(len(bench.TASKS),7)

    def test_numbers_not_collapsed(self):
        self.assertNotEqual(bench.normalized('1.2'),bench.normalized('12'))
        self.assertNotEqual(bench.normalized('-1'),bench.normalized('1'))
        self.assertEqual(bench.answer_scores('얼음',['얼음'])['whitespace_nfkc_exact'],1)
        self.assertEqual(bench.answer_scores('이',['얼음'])['whitespace_nfkc_exact'],0)

    def test_numeric_contract(self):
        self.assertEqual(bench.numerical('#### 1,200'),'1.2E+3')
        self.assertEqual(bench.numerical('5.0'),bench.numerical('5'))
        self.assertIsNone(bench.numerical('I think 5'))

    def test_same_context_budget(self):
        self.assertEqual(bench.CONTEXT,1024)
        self.assertEqual(bench.MAX_NEW,128)
        self.assertLess(bench.GEN_N,bench.MC_N)


if __name__=='__main__':unittest.main()
