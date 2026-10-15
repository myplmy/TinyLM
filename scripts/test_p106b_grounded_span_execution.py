#!/usr/bin/env python3
"""Strict seed regression and explicit producer/execution separation, CPU only."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from unittest.mock import patch
from scripts import diag_p106b_grounded_span_execution as execution
from scripts import test_p106b_grounded_span as original_tests


class Strict(unittest.TestCase):
    def test_prior_seed_side_effect_and_new_isolation(self):
        import torch
        with patch.object(torch.cuda,'manual_seed_all') as called:
            execution.source.method.new_head(8,rank=4)
            self.assertEqual(called.call_count,1)
        before=torch.random.get_rng_state().clone()
        with patch.object(torch.cuda,'manual_seed_all') as called:
            execution.strict_head(8,rank=4)
            self.assertEqual(called.call_count,0)
        self.assertTrue(torch.equal(before,torch.random.get_rng_state()))
        print('[SEED_CPU_REGRESSION] original CUDA seed calls1; strict0; CPU state unchanged',flush=True)

    def test_repeat_head_is_identical(self):
        import torch
        a=execution.strict_head(8,rank=4);torch.rand(99);b=execution.strict_head(8,rank=4)
        self.assertTrue(all(torch.equal(v,b.state_dict()[k]) for k,v in a.state_dict().items()))

    def test_adapter_never_rewrites_producer(self):
        producer=dict(tag='old',code_sha256={'old':'A'*64},counts={'train':3072});before=copy.deepcopy(producer)
        updated=execution.adapted(producer,dict(code_sha256={'new':'B'*64},source_producer_report_sha256='C'*64))
        self.assertEqual(producer,before);self.assertEqual(updated['source_producer_code_sha256'],producer['code_sha256'])
        self.assertNotEqual(updated['code_sha256'],producer['code_sha256']);self.assertFalse(updated['source_data_changed'])

    def test_context_restores_prior_runtime(self):
        old_tag=execution.source.TAG;old_head=execution.source.method.new_head
        with execution.runtime(dict(code_sha256={}),{'train':[]},{},dict(code_sha256={},source_producer_report_sha256='A'*64)):
            self.assertEqual(execution.source.TAG,execution.TAG)
            self.assertIs(execution.source.method.new_head,execution.strict_head)
        self.assertEqual(execution.source.TAG,old_tag);self.assertIs(execution.source.method.new_head,old_head)


def load_tests(loader,tests,pattern):
    tests.addTests(loader.loadTestsFromTestCase(original_tests.Contract));return tests


if __name__=='__main__':unittest.main()
