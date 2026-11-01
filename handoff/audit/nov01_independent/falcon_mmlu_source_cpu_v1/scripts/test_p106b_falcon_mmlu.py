"""Falcon 연결의 순수 토큰·자원·예외 계측 경계만 확인한다. 모델/GPU를 열지 않는다."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import diag_p106b_falcon_mmlu as driver


class FalconContract(unittest.TestCase):
    def setUp(self):
        self.source=dict(files={},sha256='fixture')
        self.cost=dict(status='LIMITED_COST_DIAGNOSTIC',final_exit=0,model='falcon90m',shots=5,
            actual_rows=114,profile_sha256='profile',source=self.source,policy=driver.prior.policy(5),
            audits={str(i):{} for i in range(57)},scorer_seconds=10.,scored_input_positions=100.)
        self.now=driver.prior.DEADLINE.timestamp()-20000

    def admit(self,cost=None,now=None):
        with patch.object(driver,'identity',return_value=self.source):
            return driver.admit_full(cost or self.cost,'profile',5,1000,self.now if now is None else now)

    def test_official_token_methods_used_without_model(self):
        from lm_eval.api.model import TemplateLM
        from lm_eval.models.huggingface import HFLM
        seen=[]
        def encode(text,**kwargs):
            seen.append(kwargs)
            return [ord(c) for c in text]
        tokenizer=SimpleNamespace(bos_token_id=0,eos_token_id=2,decode=lambda _:'<s>',encode=encode)
        proxy=driver.tokenizer_only(tokenizer)
        self.assertIs(proxy.tok_encode.__func__,HFLM.tok_encode)
        self.assertIs(proxy._encode_pair.__func__,TemplateLM._encode_pair)
        self.assertEqual(proxy._encode_pair('A ',' B'),([65],[32,32,66]))
        self.assertTrue(all(r['add_special_tokens'] is False for r in seen))

    def test_cost_scales_actual_input_not_document_count(self):
        self.assertEqual(self.admit()['forecast_seconds'],480.)

    def test_stale_profile_source_or_model_rejected(self):
        for key,value in [('profile_sha256','other'),('source',{}),('model','native595-q'),('shots',0)]:
            row=dict(self.cost);row[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.admit(row)

    def test_partial_cost_and_missing_subject_rejected(self):
        for key,value in [('actual_rows',113),('final_exit',8),('audits',{}),('status','HOLD')]:
            row=dict(self.cost);row[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.admit(row)

    def test_nonfinite_boolean_or_zero_cost_rejected(self):
        for key in ['scorer_seconds','scored_input_positions']:
            for value in [0,True,float('nan'),float('inf')]:
                row=dict(self.cost);row[key]=value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.admit(row)

    def test_deadline_reserve_enforced(self):
        with self.assertRaises(driver.ResourceHold):self.admit(now=driver.prior.DEADLINE.timestamp()-500)

    def test_ninety_minute_limit_enforced(self):
        row=dict(self.cost,scorer_seconds=1000.)
        with self.assertRaises(driver.ResourceHold):self.admit(row)

    def test_interrupted_observer_restores_methods_and_records_work(self):
        lm=SimpleNamespace()
        def forward(inputs):return ['unchanged']
        lm._model_call=forward
        def likelihood(requests,**kwargs):
            result=lm._model_call(SimpleNamespace(numel=lambda:12))
            self.assertEqual(result,['unchanged'])
            raise TimeoutError('fixture interruption')
        lm._loglikelihood_tokens=likelihood
        torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda:None,
            max_memory_allocated=lambda:17,max_memory_reserved=lambda:23))
        report=dict(scorer_seconds=0.,completed_forward_batches=0,completed_forward_padded_positions=0)
        with self.assertRaises(TimeoutError):
            with driver.observe_backend(lm,torch,report):lm._loglikelihood_tokens([])
        self.assertIs(lm._model_call,forward)
        self.assertIs(lm._loglikelihood_tokens,likelihood)
        self.assertEqual(report['completed_forward_batches'],1)
        self.assertEqual(report['completed_forward_padded_positions'],12)
        self.assertGreater(report['scorer_seconds'],0.)
        self.assertEqual(report['peak_reserved_bytes'],23)


if __name__=='__main__':
    unittest.main()
