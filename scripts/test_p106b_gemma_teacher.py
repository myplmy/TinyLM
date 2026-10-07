#!/usr/bin/env python3
"""CPU Gemma payload/shape/lifecycle dispatch; real assets/models never read."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import p106b_gemma_teacher as profile


def headers():
    sampler={'general.sampling.top_k':64,'general.sampling.top_p':.95,'general.sampling.temp':1.0}
    base=dict(metadata=dict(sampler,**{'general.architecture':'gemma4','gemma4.block_count':48,'general.file_type':2}),
              tensors={'token_embd.weight':{'shape':[3840,262144]}})
    draft=dict(metadata=dict(sampler,**{'general.architecture':'gemma4-assistant',
                                      'gemma4-assistant.nextn_predict_layers':4,'general.file_type':7}),
        tensors={'token_embd.weight':{'shape':[1024,262144]},'nextn.pre_projection.weight':{'shape':[7680,1024]},
                 'nextn.post_projection.weight':{'shape':[1024,3840]}})
    return base,draft


class GemmaTests(unittest.TestCase):
    def test_paired_assistant_projection_not_equal_embedding_dim(self):
        base,draft=headers();profile.validate_headers(base,draft)
        bad=copy.deepcopy(draft);bad['tensors']['nextn.post_projection.weight']['shape']=[1024,3072]
        with self.assertRaises(ValueError):profile.validate_headers(base,bad)

    def test_wrong_sampler_and_architecture_refused(self):
        base,draft=headers();bad=copy.deepcopy(base);bad['metadata']['general.sampling.top_k']=20
        with self.assertRaises(ValueError):profile.validate_headers(bad,draft)
        bad=copy.deepcopy(draft);bad['metadata']['general.architecture']='qwen35'
        with self.assertRaises(ValueError):profile.validate_headers(base,bad)

    def test_mtp_uses_separate_assistant_and_fixed_backend(self):
        off=profile.command(1234,'fixture',mtp=False);on=profile.command(1234,'fixture',mtp=True)
        self.assertEqual(off[0],'/home/uranus/llama-b11396/llama-server')
        self.assertNotIn('--model-draft',off)
        self.assertEqual(on[on.index('--model-draft')+1],str(profile.DRAFT))
        self.assertEqual(on[on.index('--spec-type')+1],'draft-mtp')
        self.assertEqual(on[on.index('--spec-draft-n-max')+1],'2')
        self.assertIn('--offline',on);self.assertIn('--jinja',on)

    def test_native_thinking_and_card_sampler_not_bonsai_effort(self):
        payload=profile.payload(profile.cases()[0],1337)
        self.assertEqual(payload['top_k'],64);self.assertEqual(payload['temperature'],1.0)
        self.assertEqual(payload['top_p'],.95);self.assertEqual(payload['min_p'],0.0)
        self.assertTrue(payload['messages'][0]['content'].startswith('<|think|>'))
        self.assertNotIn('reasoning_effort',payload)

    def test_defaults_not_mutated_by_payload(self):
        before=copy.deepcopy(profile.SAMPLER);profile.payload(profile.cases()[1],2)
        self.assertEqual(profile.SAMPLER,before)

    def test_grounded_B_preserves_source_context_and_refuses_missing_provenance(self):
        from scripts.test_p106b_capability_prepare import row
        source=row();source['meta'].update(source_repo='public/repo',source_revision='r1',
            source_sha256='A'*64,source_id='id1',source_family='family1')
        before=copy.deepcopy(source)
        payload=profile.grounded_payload(source,'ko','qa',1337)
        self.assertIn('public_context',payload['messages'][1]['content'])
        self.assertIn('Use only',payload['messages'][0]['content'])
        self.assertEqual(source,before)
        bad=copy.deepcopy(source);del bad['meta']['source_sha256']
        with self.assertRaises(ValueError):profile.grounded_payload(bad,'ko','qa',1)

    def test_wire_counts_use_shifted_labels_and_no_semantic_pass(self):
        from tinylm.data.prepare import SyntheticTokenizer
        parsed={'format_status':'TAGGED_COMPLETE','parsed_content':{'user_text':'질문','assistant_text':'답'}}
        counts=profile.wire_counts(parsed,SyntheticTokenizer())
        self.assertTrue(counts['technical_ready']);self.assertGreater(counts['targets'],0)
        self.assertEqual(counts['semantic_truth'],'NOT_REVIEWED')
        self.assertEqual(profile.wire_counts({'format_status':'PARSE_ERROR'},None)['x_tokens'],0)

    def test_gemma_lifecycle_dispatch_does_not_mutate_qwen_profile(self):
        from scripts import diag_p106b_qwen_coload as runtime
        old=runtime.profile;seen=[]
        def fake_enter():
            seen.append(runtime.profile.command(1234,'fixture'));return 'mock session'
        with patch.object(runtime.QwenSession,'__init__',return_value=None),\
             patch.object(runtime.QwenSession,'__enter__',side_effect=fake_enter):
            self.assertEqual(profile.GemmaSession(True).__enter__(),'mock session')
        self.assertIs(runtime.profile,old)
        self.assertIn(str(profile.DRAFT),seen[0])


if __name__=='__main__':unittest.main()
