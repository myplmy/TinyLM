#!/usr/bin/env python3
"""CPU contracts and mocked orchestration; no real model/GPU/server."""
from __future__ import annotations
import contextlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.p106b_mtp_teacher import (gguf_metadata,validate_layout,server_command,parse_wire,
    CONDITIONS,ORDERS,cases,sampling_payload,response_metrics,summarize,paired_comparisons,
    validate_refusal_labels,text_sha,validate_refusal_trigger,MODEL_SHA)
from scripts import diag_p106b_mtp_teacher as driver


def reply(content=None):
    if content is None:content='[[QUESTION]]\nQ\n[[/QUESTION]]\n[[ANSWER]]\nA\n[[/ANSWER]]\n[[NOTE]]\n\n[[/NOTE]]'
    return {'choices':[{'finish_reason':'stop','message':{'content':content,'reasoning_content':'private trace'}}],
            'usage':{'completion_tokens':100},'timings':{'predicted_n':100,'predicted_ms':2000,'prompt_per_second':1000}}


class MtpTeacherTests(unittest.TestCase):
    def test_four_commands_change_only_mtp_and_lora_options(self):
        common=None
        for name,(mtp,lora) in CONDITIONS.items():
            cmd=server_command(name,12345,'test-key')
            self.assertEqual(cmd[cmd.index('--spec-type')+1],'draft-mtp' if mtp else 'none')
            self.assertEqual(cmd[cmd.index('--spec-draft-n-max')+1],'2')
            self.assertEqual('--lora-scaled' in cmd,lora)
            stripped=cmd[:];at=stripped.index('--spec-type');del stripped[at:at+2]
            if lora:at=stripped.index('--lora-scaled');del stripped[at:at+2]
            if common is None:common=stripped
            self.assertEqual(stripped,common)
    def test_sampler_and_crossed_orders_preserve_current_settings(self):
        self.assertEqual([r['language'] for r in cases()],['ko','en','ko','en'])
        for orders in ORDERS.values():self.assertEqual(orders[0],tuple(reversed(orders[1])))
        p=sampling_payload(cases()[0],1337)
        self.assertEqual([p[k] for k in ('temperature','top_p','top_k','min_p','repeat_penalty')],[1.,.95,20,.05,1.])
        self.assertEqual(p['reasoning_effort'],'xhigh');self.assertFalse(p['cache_prompt'])
    def test_short_or_unbounded_gguf_is_rejected(self):
        with self.assertRaises(ValueError):gguf_metadata(io.BytesIO(b'GGUF'))
        with self.assertRaises(ValueError):gguf_metadata(io.BytesIO(b'GGUF'+struct.pack('<IQQ',3,100001,0)))
    def test_header_reader_stops_before_weight_bytes(self):
        result=gguf_metadata(io.BytesIO(b'GGUF'+struct.pack('<IQQ',3,0,0)+b'weights-not-read'))
        self.assertEqual(result['tensor_count'],0);self.assertEqual(result['header_bytes'],24)
    def test_linear_and_embedding_lora_have_different_axis_conventions(self):
        m={'metadata':{'general.architecture':'qwen35','qwen35.nextn_predict_layers':1},
           'tensors':{'nextn.foo':{'shape':[1]},'blk.0.ffn_down.weight':{'shape':[8,4]},'token_embd.weight':{'shape':[4,10]}}}
        a={'metadata':{'general.architecture':'qwen35','general.type':'adapter','adapter.type':'lora'},
           'tensors':{'blk.0.ffn_down.weight.lora_a':{'shape':[8,1]},'blk.0.ffn_down.weight.lora_b':{'shape':[1,4]},
                      'token_embd.weight.lora_a':{'shape':[1,10]},'token_embd.weight.lora_b':{'shape':[1,4]}}}
        self.assertEqual(validate_layout(m,a)['adapter_pairs'],2)
        a['tensors']['token_embd.weight.lora_b']['shape']=[1,5]
        with self.assertRaises(ValueError):validate_layout(m,a)
    def test_decoder_and_whole_request_denominators_differ(self):
        m=response_metrics(reply(),4)
        self.assertEqual(m['completion_tok_per_sec'],25);self.assertEqual(m['decode_tok_per_sec'],50)
        self.assertIsNone(m['draft_tokens']);self.assertEqual(m['semantic_refusal'],'NOT_REVIEWED')
    def test_missing_usage_and_nonfinite_clock_are_not_zero_passes(self):
        r=reply();r['usage']={}
        with self.assertRaises(ValueError):response_metrics(r,1)
        with self.assertRaises(ValueError):response_metrics(reply(),float('nan'))
    def test_zero_token_empty_reply_is_preserved_without_ratio(self):
        r=reply('');r['usage']['completion_tokens']=0
        m=response_metrics(r,1)
        self.assertTrue(m['empty_final']);self.assertEqual(m['completion_tok_per_sec'],0)
    def test_explicit_draft_counts_only(self):
        r=reply();r['timings'].update(draft_n=10,draft_n_accepted=7)
        self.assertEqual(response_metrics(r,1)['draft_acceptance'],.7)
        r['timings']['draft_n_accepted']=11
        self.assertIsNone(response_metrics(r,1)['draft_acceptance'])
    def test_single_wire_uses_the_actual_parser_status(self):
        self.assertTrue(parse_wire(reply(),cases()[0])['wire_ready'])
        self.assertFalse(parse_wire(reply('I will not answer.'),cases()[0])['wire_ready'])
    def test_partial_panel_cannot_get_speed_ratio(self):
        r={'kind':'response','id':'r0_base_qa_ko','condition':'base','round':0,'metrics':response_metrics(reply(),1),'wire':{'wire_ready':True}}
        self.assertEqual(paired_comparisons([r],[],'mtp')[0]['rounds'][0]['status'],'INCOMPLETE_NO_RATIO')
        self.assertIsNone(summarize([r],'mtp')['mtp']['completion_tok_per_sec'])
    def test_quoted_refusal_phrase_is_not_automatically_a_refusal(self):
        t='The phrase "I cannot" is quoted as an example; here is the requested answer.'
        r={'kind':'response','id':'row1','condition':'base','metrics':response_metrics(reply(t),1)}
        label={'id':'row1','final_sha256':text_sha(t),'label':'ANSWER','reviewer':'human','reason':'context reviewed'}
        self.assertEqual(validate_refusal_labels([r],[label])['base']['refusal_rate'],0)
        label['final_sha256']='F'*64
        with self.assertRaises(ValueError):validate_refusal_labels([r],[label])
    def test_empty_or_incomplete_review_is_rejected(self):
        with self.assertRaises(ValueError):validate_refusal_labels([],[])
        r={'kind':'response','id':'1','condition':'base','metrics':response_metrics(reply(),1)}
        with self.assertRaises(ValueError):validate_refusal_labels([r],[])
    def test_choice_c_requires_offline_context_observation_and_hashes(self):
        row={'question':'A permitted educational question','final':'An observed refusal'}
        e={'schema':'P106B_LORA_OBSERVED_REFUSAL_V1','allowed_educational_request':True,'observed_refusal':True,
           'reviewer':'GPT','reason':'question and answer reviewed','source_model_sha256':MODEL_SHA,
           'question_path':['question'],'answer_path':['final'],
           'question_sha256':text_sha(row['question']),'final_sha256':text_sha(row['final'])}
        self.assertEqual(validate_refusal_trigger(e,row)['basis'],'OFFLINE_CONTEXT_REVIEW')
        e['observed_refusal']=False
        with self.assertRaises(ValueError):validate_refusal_trigger(e,row)
    def test_lora_execution_cannot_start_without_c_trigger(self):
        with patch.object(driver,'lora_refusal_gate',side_effect=FileNotFoundError('absent')), \
             patch.object(driver,'metadata_preflight') as metadata:
            with self.assertRaises(FileNotFoundError):driver.preflight('lora',True)
            metadata.assert_not_called()


class MockedExecutionTests(unittest.TestCase):
    def run_fixture(self,expire=False):
        clock=[0.];response_calls=[]
        class FakeSession:
            def __init__(self,condition):
                self.condition=condition;self.key='fake-key';self.tail=[];self.errors=[];self.signals={}
            def __enter__(self):self.startup_sec=1;self.props={'total_slots':1};return self
            def __exit__(self,*_):pass
            def check(self):pass
            def memory(self):return {'sampled_gpu_increment_mib':1,'owned_server_peak_rss_mib':1}
            def request(self,route,payload=None,timeout=10):
                if route=='/apply-template':return {'prompt':'same-rendered-prompt'}
                if route=='/tokenize':return {'tokens':[1,2]}
                response_calls.append(payload);clock[0]+=4000 if expire else 1
                if expire:raise TimeoutError('mocked hard deadline')
                if '[[ANSWER_1]]' in payload['messages'][0]['content']:
                    return reply('[[QUESTION]]\nQ\n[[/QUESTION]]\n[[ANSWER_1]]\nA\n[[/ANSWER_1]]\n[[ANSWER_2]]\nB\n[[/ANSWER_2]]')
                return reply()
        with tempfile.TemporaryDirectory(prefix='p106b_mtp_fixture_') as directory:
            with patch.object(driver,'OUTPUT',Path(directory)),patch.object(driver,'Session',FakeSession), \
                 patch.object(driver,'time',SimpleNamespace(perf_counter=lambda:clock[0])), \
                 patch('scripts.p106b_gate_runtime.wall_limit',lambda _:contextlib.nullcontext()),contextlib.redirect_stdout(io.StringIO()):
                rc=driver.execute('mtp',{'max_wall_sec':3600,'request_count':16,'fixture':True})
            report=json.loads((Path(directory)/'mtp/report.json').read_text())
            self.assertTrue((Path(directory)/'mtp/raw_shards_manifest.json').is_file())
            self.assertTrue((Path(directory)/'mtp/review_packet.md').is_file())
        return rc,report,response_calls
    def test_all_crossed_requests_and_raw_answers_are_preserved(self):
        rc,r,requests=self.run_fixture()
        self.assertEqual(rc,0);self.assertEqual(r['observed_requests'],16);self.assertEqual(len(requests),16)
        self.assertEqual(r['summary']['base']['wire_ready'],8)
        self.assertEqual(r['refusal_rate'],'NOT_REVIEWED')
    def test_arm_error_cannot_swallow_the_whole_wall_limit(self):
        rc,r,requests=self.run_fixture(True)
        self.assertNotEqual(rc,0);self.assertEqual(len(requests),1)
        self.assertEqual(r['observed_requests'],0);self.assertEqual(len(r['arms']),1)


if __name__=='__main__':unittest.main()
