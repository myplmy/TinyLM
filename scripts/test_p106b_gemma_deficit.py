#!/usr/bin/env python3
"""CPU synthetic quota/replay/learner routing, no real corpus/teacher/model."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_gemma_deficit as control
from scripts import diag_p106b_gemma_deficit_production as run
from scripts.p106b_teacher_wrapper import wrap_turns
from tinylm.data.prepare import SyntheticTokenizer
from tinylm.chat.canonical import normalize
from tinylm.data.sft import conversation_split_key


def row(index=1,*,language='en',profile='qa',family='family0',key=None):
    item=wrap_turns([dict(user_text='question '+str(index),assistant_text='a source-grounded answer')],
        source_id='source'+str(index),source_sha256='A'*64,teacher_model_sha256='B'*64,
        language=language,source_license='fixture-only',generation_id='fixture'+str(index),
        source_repo='public/fixture',source_revision='revision',source_object_id=str(index),
        source_transform='teacher_answer',parent_concept_id=key or ('00000001'+str(index).zfill(56)),
        source_rights_status='CARD_ONLY')
    item['meta'].update(source_family=family,task_profile=profile)
    return item


class DeficitTests(unittest.TestCase):
    def state(self):return control.Quotas(SyntheticTokenizer(),goal=4000)

    def test_metadata_source_split_not_generated_question_split(self):
        state=control.Quotas(SyntheticTokenizer(),goal=40000);key='00000000'+'A'*56
        item=row(key=key);before=copy.deepcopy(item)
        result=state.admit(item)
        self.assertEqual(result['meta']['source_split'],'val')
        self.assertEqual(result['meta']['parent_concept_id'],key)
        self.assertEqual(item,before)

    def test_same_original_language_not_new_unique_knowledge(self):
        state=self.state();a=row();self.assertIsNotNone(state.admit(a))
        b=row(2,key=a['meta']['parent_concept_id'])
        self.assertIsNone(state.admit(b))
        self.assertEqual(state.counts['train:en'],1)

    def test_identical_learner_question_not_recounted(self):
        state=self.state();a=row();self.assertIsNotNone(state.admit(a))
        b=row(2);b['messages']=copy.deepcopy(a['messages'])
        self.assertIsNone(state.admit(b))

    def test_original_fixed_eval_excluded_before_teacher_request(self):
        state=self.state();key=next(iter(state.validation.probes)).hex().upper()
        self.assertIsNone(state.profile(state.source_split(key),'en','family0',key))

    def test_original_family_near_full_no_wasted_requests(self):
        state=self.state();state.family['train:en:NQ-Open']=996
        self.assertIsNone(state.profile('train','en','NQ-Open','00000001'+'A'*56))

    def test_profile_prioritizes_largest_real_shortfall(self):
        state=self.state()
        self.assertEqual(state.profile('train','en','family0','00000001'+'A'*56),'qa')
        state.task['train:en:qa']=1900
        self.assertIn(state.profile('train','en','family0','00000001'+'A'*56),('json','multiturn'))

    def test_family_cap_is_original_not_teacher_label(self):
        state=self.state();state.family['train:en:NQ-Open']=990
        self.assertIsNone(state.admit(row(family='NQ-Open')))
        self.assertNotIn(('00000001'+str(1).zfill(56),'en'),state.seen)

    def test_bad_context_mask_never_contributes_tokens(self):
        state=self.state();a=row();a['messages'][1]['content'][0]['text']='x'*6000
        self.assertIsNone(state.admit(a));self.assertEqual(sum(state.tokens.values()),0)

    def test_quantity_truth_and_train_ready_separate(self):
        state=self.state()
        for lang in ('ko','en'):
            state.tokens['train:'+lang]=4000;state.tokens['val:'+lang]=4000//19
            for task,share in control.WEIGHTS.items():state.task['train:'+lang+':'+task]=int(4000*share)
        report=state.report();self.assertTrue(report['token_target_ready'])
        self.assertFalse(report['formal_train_ready']);self.assertEqual(report['semantic_quality'],'NOT_REVIEWED')
        state.task['train:ko:qa']=0;self.assertFalse(state.report()['token_target_ready'])

    def test_val_shortfall_does_not_disappear_into_train75M(self):
        state=self.state();state.tokens['train:ko']=4000;state.tokens['train:en']=4000
        report=state.report();self.assertEqual(report['teacher_deficit_tokens'],{'ko':0,'en':0})
        self.assertFalse(report['token_target_ready']);self.assertGreater(report['validation_deficit_tokens']['en'],0)

    def test_learner_rejects_deficit_before_model_loader(self):
        with patch.object(control,'safe_repo_path') as path,patch.object(control,'digest'),\
             patch('scripts.diag_p106b_mixed_repeat4.execute',side_effect=AssertionError('forbidden')):
            path.return_value.read_text.return_value=json.dumps({'token_target_ready':False})
            with self.assertRaises(FileNotFoundError):control.learner(True,execute=True)

    def test_check_only_cannot_allocate_teacher(self):
        with patch.object(sys,'argv',['producer','--mode','produce','--check-only']),\
             patch.object(run,'require_pilots',return_value={'ready':'fixture'}),\
             patch.object(control,'base_report',return_value={}),\
             patch.object(run,'production',side_effect=AssertionError('forbidden')),redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(),0)

    def test_finalize_shortage_cannot_publish_or_load_student(self):
        with tempfile.TemporaryDirectory(prefix='gemma_deficit_fixture_') as tmp,\
             patch.object(control,'CORPUS',Path(tmp)/'new'),patch.object(control,'safe_repo_path'),\
             patch.object(control,'base_report',return_value={}),\
             patch.object(control,'base_rows',return_value=iter([])),\
             patch.object(control,'generated_rows',return_value=iter([])),\
             patch.object(control,'ShardWriter',side_effect=AssertionError('must not publish')):
            with self.assertRaises(FileNotFoundError):control.finalize(SyntheticTokenizer())

    def test_actual_producer_publishes_batch_cursor_and_replay(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        class Session:
            def __init__(self,*args):self.requests=0
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def check(self):pass
            def memory(self):return {'fixture':'no realGPU'}
            def request(self,path,payload,**kwargs):
                if path=='/apply-template':return {'prompt':'fixture'}
                if path=='/tokenize':return {'tokens':[1]}
                self.requests+=1
                return {'choices':[{'finish_reason':'stop','message':{
                    'content':'QUESTION: new question '+str(self.requests)+'\nANSWER: source answer\nNOTE:\n',
                    'reasoning_content':'sidecar'}}]}
        info={'source':'fixture'};identity={'model_sha256':'B'*64,'draft_sha256':'D'*64}
        base=dict(nonpadding_tokens={},sources=[{'path':'HF/sft_sources/fixture.json','sha256':'A'*64}])
        with tempfile.TemporaryDirectory(prefix='gemma_deficit_fixture_') as tmp,\
             patch.object(control,'OUTPUT',Path(tmp)/'production'),\
             patch.object(control,'safe_repo_path',side_effect=lambda p:p),\
             patch.object(run,'safe_repo_path',side_effect=lambda p:p),\
             patch.object(run,'require_pilots',return_value=info),patch.object(control,'base_report',return_value=base),\
             patch.object(control,'base_rows',side_effect=lambda b:iter([])),\
             patch.object(run,'english_rows',side_effect=lambda s:iter([row(1),row(2)])),\
             patch.object(run,'digest',side_effect=lambda p:run.TOK_SHA if p==run.TOKENIZER else 'A'*64),\
             patch('tokenizers.Tokenizer.from_file',return_value=SyntheticTokenizer()),\
             patch.object(teacher:=run.teacher,'assets',return_value=identity),\
             patch.object(run.gate,'read_report',return_value={'input':{'asset_identity':identity}}),\
             patch.object(teacher,'GemmaSession',Session),patch.object(run,'idle_before_gpu'),\
             patch.object(run,'wall_limit',return_value=nullcontext()),\
             patch('shutil.disk_usage',return_value=SimpleNamespace(free=100*(1<<30))),redirect_stdout(io.StringIO()):
            self.assertEqual(run.production(max_wall_sec=60),8)
            directory=control.OUTPUT/'batch_000000'
            report=json.loads((directory/'report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['status'],'SOURCE_EXHAUSTED');self.assertEqual(report['accepted_groups'],2)
            self.assertEqual(report['cursor'],[0,1]);self.assertEqual(report['raw_manifest']['rows'],2)
            state,cursor,number=run.state_from_saved(SyntheticTokenizer(),base)
            self.assertEqual(sum(state.counts.values()),2);self.assertEqual(cursor,(0,1));self.assertEqual(number,1)
            with self.assertRaises(FileNotFoundError):run.production(resume=True,max_wall_sec=60)

    def test_new_posteval_adapter_restores_old_namespace(self):
        from scripts import diag_p106b_refill_multiaxis as old
        before=(old.CORPUS,old.OUTPUT,old.CORPUS_SHA,old.CHILD,old.CHILD_LOG);seen=[]
        def check():
            seen.append((old.CORPUS,old.OUTPUT,old.CHILD));return {'planned_model_calls':72}
        with patch.object(control,'safe_repo_path',side_effect=lambda p:p),\
             patch.object(control,'digest',return_value='A'*64),patch.object(old,'check',side_effect=check),\
             patch.object(old,'execute',side_effect=AssertionError('must not execute')):
            self.assertEqual(control.evaluate(execute=False)['planned_model_calls'],72)
        self.assertEqual((old.CORPUS,old.OUTPUT,old.CORPUS_SHA,old.CHILD,old.CHILD_LOG),before)
        self.assertEqual(seen[0][0],control.CORPUS)
        self.assertIn(control.TAG,seen[0][2].name)

    def test_final_merge_publishes_hashes_masks_and_actual_question_index(self):
        import sqlite3
        class ReadyFixture:
            def __init__(self,tok):pass
            def admit(self,value,**kwargs):return value
            def report(self):return {'token_target_ready':True,'production_version':'fixture'}
        originals=[]
        for i,(lang,split) in enumerate((('ko','train'),('en','train'),('ko','val'),('en','val')),1):
            value=row(i,language=lang);value['meta']['source_split']=split;originals.append(value)
        with tempfile.TemporaryDirectory(prefix='gemma_merge_fixture_') as tmp,\
             patch.object(control,'CORPUS',Path(tmp)/'new'),patch.object(control,'safe_repo_path'),\
             patch.object(control,'Quotas',ReadyFixture),patch.object(control,'base_report',return_value={'sources':[]}),\
             patch.object(control,'base_rows',side_effect=lambda b:iter(copy.deepcopy(originals))),\
             patch.object(control,'generated_rows',side_effect=lambda:iter([])):
            report=control.finalize(SyntheticTokenizer())
            self.assertEqual(report['epochs'],4);self.assertEqual(report['student_accum'],16)
            for split in ('train','val'):
                manifest=json.loads((control.CORPUS/(split+'_shards_manifest.json')).read_text(encoding='utf-8'))
                observed=list(control.rows(control.CORPUS,manifest))
                self.assertEqual(len(observed),2)
                self.assertTrue(all(r['meta']['processed_x_tokens']>0 for r in observed))
                self.assertEqual(report[split+'_concat_sha256'],manifest['concat_sha256'])
            connection=sqlite3.connect(control.CORPUS/'candidate_index.sqlite')
            try:self.assertEqual(connection.execute('SELECT COUNT(*) FROM candidates WHERE selected=1').fetchone()[0],4)
            finally:connection.close()


if __name__=='__main__':unittest.main()
