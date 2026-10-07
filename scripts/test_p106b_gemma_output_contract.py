#!/usr/bin/env python3
"""CPU fixtures only: explicit contracts, shared retry and real canonical mask."""
import copy
from contextlib import nullcontext, redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_gemma_output_contract as output
from scripts import p106b_gemma_task_contract_v2 as tasks
from scripts import diag_p106b_gemma_output_recovery as recovery
from scripts import diag_p106b_gemma_task_pilot as gate
from scripts import diag_p106b_gemma_deficit_production as producer
from scripts import p106b_gemma_deficit as control
from scripts.test_p106b_gemma_task_contract import source


class OutputTests(unittest.TestCase):
    def test_simple_plain_and_closed_fence_preserve_value(self):
        spec=output.contract('ANSWER_ENVELOPE')
        for raw in ('2016년', '{"answer":"2016년"}', '```json\n{"answer":"2016년"}\n```'):
            answer,trace=output.render(raw,spec)
            self.assertEqual(json.loads(answer),{'answer':'2016년'})
            self.assertEqual(trace['original_teacher_answer'],raw)
            self.assertEqual(trace['structure_status'],'CODE_RENDERED_ENVELOPE')
            self.assertEqual(trace['semantic_truth'],'NOT_REVIEWED')

    def test_simple_does_not_hide_complex_or_broken_structure(self):
        for raw in ('[]','{"name":"Mina"}','{"answer":[]}','{"answer":1,"extra":2}',
                    '```json\n{"answer":1}', '{"answer":', '{"answer":1,"answer":2}', 'NaN'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                output.render(raw,output.contract('ANSWER_ENVELOPE'))

    def test_simple_scalars_are_not_double_wrapped(self):
        for value in (2016,True,None,'text'):
            answer,_=output.render(json.dumps(value),output.contract('ANSWER_ENVELOPE'))
            self.assertEqual(json.loads(answer),{'answer':value})

    def test_unknown_does_not_guess_from_json_keyword(self):
        raw='[not JSON; preserve this answer]'
        answer,trace=output.render(raw,output.contract('UNKNOWN'))
        self.assertEqual(answer,raw)
        self.assertEqual(trace['structure_status'],'NOT_ASSESSED')
        self.assertNotIn('rendered_student_answer',trace)

    def test_no_teacher_or_source_self_classification_is_authority(self):
        for key,value in (('authority','teacher'),('producer','source_meta'),('kind','ARRAY_GUESS')):
            spec=output.contract('UNKNOWN');spec[key]=value
            with self.assertRaises(ValueError):output.render('a',spec)

    def test_complex_array_is_not_answer_string(self):
        value=[{'name':'Mina','age':20},{'name':'Jun','age':30}]
        spec=output.contract('STRUCTURED_JSON',schema=recovery.SCHEMAS['array'])
        rendered,trace=output.render('```json\n'+json.dumps(value)+'\n```',spec)
        self.assertEqual(json.loads(rendered),value)
        self.assertEqual(trace['structure_status'],'DECLARED_STRUCTURE_PASS')

    def test_nested_structure_and_boolean_not_integer(self):
        value={'people':[{'name':'Mina','age':20},{'name':'Jun','age':30}],'count':2}
        spec=output.contract('STRUCTURED_JSON',schema=recovery.SCHEMAS['nested'])
        self.assertEqual(json.loads(output.render(json.dumps(value),spec)[0]),value)
        for bad in (dict(value,count=True),dict(value,extra=1),{'people':value['people']}):
            with self.assertRaises(ValueError):output.render(json.dumps(bad),spec)

    def test_unsupported_schema_fails_before_request(self):
        for schema in ({'type':'array'}, {'type':'object','patternProperties':{}},
                       {'type':'string'}, {'type':'object','required':['missing']},
                       {'type':'array','items':{'type':'integer'},'minItems':3,'maxItems':2}):
            with self.assertRaises(ValueError):output.contract('STRUCTURED_JSON',schema=schema)

    def test_schema_depth_is_bounded(self):
        schema={'type':'string'}
        for _ in range(14):schema={'type':'array','items':schema}
        with self.assertRaises(ValueError):output.contract('STRUCTURED_JSON',schema=schema)

    def test_structure_checks_not_truth_checks(self):
        value=[{'name':'unknown factual truth','age':99999},{'name':'other','age':-20}]
        spec=output.contract('STRUCTURED_JSON',schema=recovery.SCHEMAS['array'])
        rendered,trace=output.render(json.dumps(value),spec)
        self.assertEqual(json.loads(rendered),value)
        self.assertEqual(trace['semantic_truth'],'NOT_REVIEWED')

    def test_complete_fence_only_not_substring_extraction(self):
        spec=output.contract('STRUCTURED_JSON',schema=recovery.SCHEMAS['array'])
        for raw in ('prefix\n```json\n[]\n```','```json\n[]\n```\nextra','```json\n[]'):
            with self.assertRaises(ValueError):output.render(raw,spec)

    def test_prompt_simple_content_without_contradictory_json_demand(self):
        p=tasks.payload(source(),'ko','json',7)
        system=p['messages'][0]['content']
        self.assertIn('not JSON',system)
        self.assertNotIn('Put exactly one JSON',system)
        self.assertNotIn('requested_task',json.loads(p['messages'][1]['content'])['source'])
        self.assertEqual((p['temperature'],p['top_p'],p['top_k'],p['min_p']),(1.,.95,64,0.))
        self.assertEqual((p['max_tokens'],p['thinking_budget_tokens']),(3072,1024))

    def test_untrusted_source_metadata_does_not_choose_output_type(self):
        s=source();s['meta']['output_contract']=output.contract('ANSWER_ENVELOPE')
        self.assertEqual(tasks.producer_kwargs({'original':s},[]),{})
        turn,trace=tasks.render_turn({'user_text':'Please produce JSON.','assistant_text':'raw'},'en','qa')
        self.assertEqual(turn['assistant_text'],'raw')
        self.assertEqual(trace['output_contract']['kind'],'UNKNOWN')

    def test_three_turn_state_and_reasoning_exclusion(self):
        history=[]
        for answer in ('2016년','형식을 바꾸겠습니다.','2016년'):
            turn,trace=tasks.render_turn({'user_text':'언제인가요?','assistant_text':answer},'ko','multiturn',history=history)
            history.append(turn)
        self.assertEqual(history[2]['user_text'],tasks.STATE_RULE['ko'][2])
        self.assertEqual(json.loads(history[2]['assistant_text']),{'answer':'2016년'})
        with self.assertRaises(ValueError):tasks.payload(source(),'ko','multiturn',2,history=history)

    def test_complex_fixed_question_and_feedback_in_system(self):
        job=recovery.structure_jobs()[0]
        kwargs=tasks.producer_kwargs(job,[])
        p=tasks.payload(job['original'],job['language'],'qa',7,feedback='$.age requires integer',**kwargs)
        self.assertIn('Declared bounded schema',p['messages'][0]['content'])
        self.assertIn('$.age requires integer',p['messages'][0]['content'])
        self.assertNotIn('Structural retry feedback',p['messages'][1]['content'])
        self.assertEqual(len(recovery.structure_jobs()),4)

    def test_scope_restores_old_modules_and_outputs(self):
        before=(gate.tasks,gate.OUTPUTS,producer.tasks,control.OUTPUT,control.CORPUS,control.TAG,control.EVALUATION)
        with self.assertRaises(RuntimeError),recovery.recovery_scope():
            self.assertIs(gate.tasks,tasks);self.assertEqual(control.CORPUS,recovery.PATHS['CORPUS'])
            raise RuntimeError('fixture')
        self.assertEqual(before,(gate.tasks,gate.OUTPUTS,producer.tasks,control.OUTPUT,control.CORPUS,control.TAG,control.EVALUATION))

    def test_check_only_does_not_allocate_or_write(self):
        with patch.object(sys,'argv',['r','--mode','contract16','--check-only']),\
             patch.object(gate,'check',return_value=([],{})),patch.object(recovery,'digest',return_value='A'*64),\
             patch.object(gate,'execute',side_effect=AssertionError('forbidden')),redirect_stdout(io.StringIO()):
            self.assertEqual(recovery.main(),0)

    def test_missing_new_corpus_holds_before_any_model(self):
        with patch.object(sys,'argv',['r','--mode','wire','--check-only']),\
             patch.object(control,'completed_corpus_report',side_effect=FileNotFoundError('absent')),\
             redirect_stderr(io.StringIO()):
            self.assertEqual(recovery.main(),8)

    def run_fixture(self,directory,answers,*,complex_task=False):
        from tinylm.data.prepare import SyntheticTokenizer
        payloads=[]
        class Session:
            def __init__(self,*args):self.calls=0
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def check(self):pass
            def memory(self):return {'fixture_only':True}
            def request(self,path,data,**kwargs):
                if path=='/apply-template':return {'prompt':'fixture'}
                if path=='/tokenize':return {'tokens':[1]}
                payloads.append(copy.deepcopy(data));answer=answers[min(self.calls,len(answers)-1)];self.calls+=1
                return {'choices':[{'finish_reason':'stop','message':{'content':'QUESTION: q\nANSWER: '+answer+'\nNOTE:\n','reasoning_content':'fixture thought'}}]}
        jobs=[recovery.structure_jobs()[0]] if complex_task else [dict(original=source(),language='ko',task='json',source_family='fixture',source_group_id='A'*64)]
        info={'teacher_identity':{'model_sha256':'B'*64,'draft_sha256':'D'*64}}
        with recovery.recovery_scope(),patch.dict(gate.OUTPUTS,contract16=directory),\
             patch.object(gate.teacher,'assets',return_value=info['teacher_identity']),\
             patch.object(gate.teacher,'GemmaSession',Session),patch.object(gate,'idle_before_gpu'),\
             patch.object(gate,'wall_limit',return_value=nullcontext()),\
             patch('tokenizers.Tokenizer.from_file',return_value=SyntheticTokenizer()),redirect_stdout(io.StringIO()):
            rc=gate.execute('contract16',jobs,info)
        report=json.loads((directory/'report.json').read_text(encoding='utf-8'))
        return rc,report,payloads

    def test_actual_simple_wrapper_mask_trace_and_original_preservation(self):
        with tempfile.TemporaryDirectory(prefix='p106b_output_fixture_') as tmp:
            directory=Path(tmp)/'new';rc,report,_=self.run_fixture(directory,['2016년'])
            self.assertEqual(rc,0);self.assertEqual(report['attempts'],1)
            row=gate.records(directory,report['candidate_manifest'])[0]
            trace=row['meta']['producer_output_traces'][0]
            self.assertEqual(trace['original_teacher_answer'],'2016년')
            self.assertEqual(trace['transform'],'RENDER_ANSWER_ENVELOPE')
            self.assertGreater(report['accepted_targets'],0)
            self.assertNotIn('fixture thought',json.dumps(row['messages']))
            self.assertFalse(report['new75M_ready'])

    def test_complex_feedback_then_recovery_shared_total_three(self):
        good=json.dumps([{'name':'Mina','age':20},{'name':'Jun','age':30}])
        with tempfile.TemporaryDirectory(prefix='p106b_output_fixture_') as tmp:
            directory=Path(tmp)/'new';rc,report,payloads=self.run_fixture(directory,['[]',good],complex_task=True)
            self.assertEqual((rc,report['attempts']),(0,2))
            self.assertIn('array size differs',payloads[1]['messages'][0]['content'])
            row=gate.records(directory,report['candidate_manifest'])[0]
            self.assertIsInstance(json.loads(row['messages'][1]['content'][0]['text']),list)

    def test_complex_all_three_rejected_not_extra_retry_budget(self):
        with tempfile.TemporaryDirectory(prefix='p106b_output_fixture_') as tmp:
            rc,report,payloads=self.run_fixture(Path(tmp)/'new',['[]'],complex_task=True)
            self.assertEqual((rc,report['attempts'],len(payloads)),(8,3,3))
            self.assertNotIn('candidate_manifest',report)

    def test_bulk_label_and_body_retries_share_three_attempts(self):
        calls=[]
        class Raw:
            _total_rows=0
            def append(self,value):self._total_rows+=1;calls.append(value)
        class Session:
            def check(self):pass
            def request(self,path,data,**kwargs):
                if path=='/apply-template':return {'prompt':'fixture'}
                if path=='/tokenize':return {'tokens':[1]}
                values=('QUESTION: q\nANSWER: a','QUESTION: q\nANSWER: {}\nNOTE:',
                        'QUESTION: q\nANSWER: scalar\nNOTE:')
                return {'choices':[{'finish_reason':'stop','message':{'content':values[len(calls)]}}]}
        with recovery.recovery_scope(),redirect_stdout(io.StringIO()):
            result=producer.produce_group(Session(),source(),'ko','json',100,Raw(),{'model_sha256':'B'*64})
        self.assertEqual(len(calls),3)
        self.assertEqual(json.loads(result['messages'][1]['content'][0]['text']),{'answer':'scalar'})
        self.assertEqual(result['meta']['producer_output_traces'][0]['original_teacher_answer'],'scalar')
        self.assertIn('Structural retry feedback',calls[2]['payload']['messages'][0]['content'])

    def test_bulk_exhaustion_does_not_add_another_render_retry(self):
        calls=[]
        class Raw:
            _total_rows=0
            def append(self,value):self._total_rows+=1;calls.append(value)
        class Session:
            def check(self):pass
            def request(self,path,data,**kwargs):
                if path=='/apply-template':return {'prompt':'fixture'}
                if path=='/tokenize':return {'tokens':[1]}
                return {'choices':[{'finish_reason':'stop','message':{'content':'QUESTION: q\nANSWER: []\nNOTE:'}}]}
        with recovery.recovery_scope(),redirect_stdout(io.StringIO()):
            result=producer.produce_group(Session(),source(),'ko','json',100,Raw(),{'model_sha256':'B'*64})
        self.assertIsNone(result);self.assertEqual(len(calls),3)


if __name__=='__main__':unittest.main()
