#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import json
import subprocess
import unittest
from unittest.mock import patch
import torch
from scripts import diag_p106b_source_window as d


class ActualConsumers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(torch,'load',side_effect=AssertionError('no model loading in input proof')):
            with patch.object(torch.nn.Module,'cuda',side_effect=AssertionError('CPU proof only')):
                cls.report,cls.cases,cls.observation=d.construct()

    def test_all_actual384_prefixes_and1920_descriptors(self):
        o=self.observation
        self.assertEqual(o['cases'],384);self.assertEqual(o['source_roots'],64)
        self.assertEqual(sum(len(x['variants']) for x in self.cases),1920)
        self.assertTrue(o['fixed_previous_answers_verified']);self.assertTrue(o['full_reconstruction_verified'])
        for endpoint in d.ENDPOINTS:
            for mode in ('FULL','QUERY','RANDOM','REMOVE_REFERENCE'):
                self.assertEqual(o['eligibility'][endpoint][mode],192)
        self.assertFalse(torch.cuda.is_initialized())

    def test_all_complete_actual_token_budgets(self):
        for case in self.cases:
            self.assertFalse(case['train_ready'])
            for variant in case['variants']:
                if variant['eligible']:
                    self.assertLess(variant['prompt_tokens'],1024)
                    self.assertGreater(variant['prompt_tokens'],0)

    def test_actual_input_construction_is_deterministic(self):
        _,cases,observation=d.construct()
        self.assertEqual(observation,self.observation)
        self.assertEqual(d.method.sha(cases),self.observation['input_signature'])

    def test_actual_history_provider_mutation_fails_before_model(self):
        original=d.training.data.stream_rows
        parent_dir=ROOT/self.report['endpoints']['parent']['metrics']['natural']['directory']
        def altered(directory,manifest):
            rows=list(original(directory,manifest))
            if Path(directory)==parent_dir:
                rows=copy.deepcopy(rows)
                item=next(x for x in rows if x['history']=='ACTUAL_MODEL' and x['turn']==2)
                item['messages'][1]['content'][0]['text']+=' altered'
            return iter(rows)
        with patch.object(d.training.data,'stream_rows',side_effect=altered):
            with self.assertRaisesRegex(ValueError,'actual previous answer'):d.source_inputs()

    def test_check_only_creates_no_new_namespace(self):
        before=(d.CORPUS.exists(),d.EVIDENCE.exists(),d.LOCAL.exists())
        result=subprocess.run([sys.executable,'-B','-X','utf8',d.__file__,'--mode','probe','--check-only'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn(d.TAG,result.stdout)
        self.assertEqual(before,(d.CORPUS.exists(),d.EVIDENCE.exists(),d.LOCAL.exists()))


if __name__=='__main__':unittest.main()
