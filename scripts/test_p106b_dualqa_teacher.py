#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
from unittest.mock import patch
from scripts import p106b_dualqa_teacher as m


def job():return dict(root='A'*64,language='ko',reference='기록: 지아의 직업은 사서이고 준호의 직업은 화가입니다.\n'+'연습용 가상 자료입니다. '*8,bridge_gold='HIDDEN_ONLY',provenance={})
FINAL='Q1:\n지아의 직업은 무엇인가요?\nA1:\n사서\nQ2:\n준호의 직업은 무엇인가요?\nA2:\n화가\nNOTE:'


class Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tokenizers import Tokenizer
        cls.tok=Tokenizer.from_file(str(ROOT/'data_cache/tok-ko-en-32768-chat32.json'))

    def test_one_and_two_labels(self):
        self.assertEqual(len(m.parse_fields(FINAL,2)['pairs']),2)
        self.assertEqual(len(m.parse_fields('Q1: 이름은?\nA1: 지아\nNOTE:',1)['pairs']),1)

    def test_preface_missing_order_rejected(self):
        for s in ('Here\n'+FINAL,FINAL.replace('Q2:','A2:',1),FINAL.replace('NOTE:','')):
            with self.assertRaises(ValueError):m.parse_fields(s,2)

    def test_exact_collision_only_under_declared_plural_contract(self):
        with self.assertRaises(ValueError):m.parse_fields(FINAL.replace('화가','사서'),2)
        single=m.parse_fields('Q1: 1만 쓰세요.\nA1: 1\nNOTE:',1);self.assertEqual(single['pairs'][0]['answer'],'1')

    def test_decline_is_explicit_not_semantic_failure(self):
        self.assertEqual(m.parse_fields('STATUS: INSUFFICIENT_SOURCE',2)['status'],'PRODUCER_DECLINED')

    def test_shared_reference_no_hidden_qa_in_teacher_input(self):
        j=job();p=m.payload(j,2,99)
        self.assertEqual(p['messages'][1]['content'].count(j['reference']),1)
        self.assertNotIn('HIDDEN_ONLY',str(p));self.assertFalse(p['cache_prompt'])
        self.assertEqual((p['thinking_budget_tokens'],p['max_tokens']),(256,3072))

    def test_reasoning_separate_not_wrapped(self):
        reply=dict(choices=[dict(finish_reason='stop',message=dict(content=FINAL,reasoning_content='PRIVATE_THOUGHT'))])
        ch=m.channels(reply);row=m.wrap(job(),m.parse_fields(ch['final'],2),self.tok)
        self.assertEqual(ch['reasoning'],'PRIVATE_THOUGHT');self.assertNotIn('PRIVATE_THOUGHT',str(row['messages']))
        self.assertFalse(row['meta']['teacher_reasoning_in_student'])

    def test_full_reference_and_two_turn_masks(self):
        from tinylm.train.mtp_sft import encode_record
        j=job();row=m.wrap(j,m.parse_fields(FINAL,2),self.tok);body=''.join(x['text'] for x in row['messages'][0]['content'])
        self.assertEqual(body[slice(*row['meta']['student_reference_range'])],j['reference'])
        self.assertEqual({s for s in encode_record(row,self.tok).segments if s},{1,2})

    def test_intended_repeat_control_never_regenerated(self):
        row=m.wrap(job(),m.parse_fields(FINAL,2),self.tok,repeat_first=True)
        self.assertEqual(row['messages'][1]['content'],row['messages'][3]['content'])
        self.assertEqual(row['meta']['known_output_contract'],'FACTORY_REPEAT_QA1_ALLOWED')

    def test_token_budget_is_actual_not_character_guess(self):
        f=m.parse_fields(FINAL,2);f['pairs'][0]['question']='질문 '*200
        with self.assertRaises(ValueError):m.wrap(job(),f,self.tok)

    def test_server_thinking_scope_restored(self):
        from scripts import p106b_gemma_teacher as t
        original=t.THINKING
        with patch.object(t,'THINKING',m.THINKING):
            c=t.command(1234,'not-a-real-key',mtp=True)
            self.assertEqual(c[c.index('--reasoning-budget')+1],'256')
        self.assertEqual(t.THINKING,original)

    def test_retry_budget_shared_and_decline_never_retried(self):
        from collections import Counter
        from scripts import diag_p106b_dualqa_teacher as driver
        class Buffer:
            def __init__(self):self.rows=[]
            def append(self,x):self.rows.append(x)
        class Session:
            def __init__(self,final):self.final=final;self.calls=0
            def check(self):pass
            def request(self,*args,**kwargs):
                self.calls+=1
                return dict(choices=[dict(finish_reason='stop',message=dict(content=self.final))],usage=dict(completion_tokens=9))
        for final,calls,declined in [('invalid preface',3,False),('STATUS: INSUFFICIENT_SOURCE',1,True)]:
            session=Session(final);raw=Buffer();canonical=Buffer();counter=Counter()
            with patch.object(driver,'count_prompt',return_value={'prompt_tokens':100}),patch.object(driver.source,'deadline'),patch('builtins.print'):
                result=driver.one_job(session,job(),2,0,self.tok,raw,canonical,counter)
            self.assertEqual(session.calls,calls);self.assertEqual(len(raw.rows),calls);self.assertEqual(result['declined'],declined)
            self.assertEqual(counter['physical_requests'],calls)

    def test_http_error_preserved_redacted_and_not_text_retried(self):
        from collections import Counter
        from io import BytesIO
        from urllib.error import HTTPError
        from scripts import diag_p106b_dualqa_teacher as driver
        class Buffer:
            def __init__(self):self.rows=[]
            def append(self,x):self.rows.append(x)
        class Session:
            key='SECRET'
            def check(self):pass
            def request(self,*args,**kwargs):raise HTTPError('http://127.0.0.1',500,'error',{},BytesIO(b'Bearer SECRET backend failed'))
        raw=Buffer();counter=Counter()
        with patch.object(driver,'count_prompt',return_value={}),patch.object(driver.source,'deadline'),patch('builtins.print'):
            with self.assertRaises(HTTPError):driver.one_job(Session(),job(),2,0,self.tok,raw,Buffer(),counter)
        self.assertEqual(len(raw.rows),1);self.assertNotIn('SECRET',str(raw.rows));self.assertEqual(counter['physical_requests'],1)


if __name__=='__main__':unittest.main()
