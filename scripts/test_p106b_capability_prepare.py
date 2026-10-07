#!/usr/bin/env python3
"""Small CPU data/metadata fixtures; no checkpoint loading, teacher or GPU."""
import copy
import ast
import inspect
import io
from contextlib import redirect_stdout,redirect_stderr
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.p106b_capability_corpus import derive,initialize,index,select,VERSION,CapabilitySelector
from scripts.diag_p106b_epoch_retention import epoch_metadata
from scripts import diag_p106b_epoch_retention as epoch_diag
from scripts import diag_p106b_epoch_retention_recovery as epoch_retry
from tinylm.chat.canonical import normalize
from tinylm.data.sft import conversation_split_key


def row(i=0,family='aya_dataset',language='ko'):
    return normalize(dict(messages=[dict(role='user',content='고유 질문 '+str(i)),
                                    dict(role='assistant',content='원천 답 '+str(i))],
                          meta=dict(language=language,source_family=family)))


class PrepareTests(unittest.TestCase):
    def epoch_state_fixture(self):
        from tinylm.config import TMTConfig
        cfg=TMTConfig(n_prelude=2,n_middle=10,n_coda=2,mlp_group=2,
                      tie_mlp=False,vocab_size=32768)
        hist=[dict(epoch=i,updates=i*10,processed_tokens=100) for i in (1,2,3,4)]
        edu=dict(history=hist,input={'tokenizer_sha256':'fixture'})
        state=dict(epoch=2,input=edu['input'],history=hist[:2],updates=20,
                   step=2309,processed_tokens=200,cfg=dict(cfg.__dict__))
        return state,edu

    def test_epoch_metadata_uses_real_serialized_config_not_derived_property(self):
        state,edu=self.epoch_state_fixture()
        self.assertNotIn('n_layers',state['cfg'])
        before=copy.deepcopy(state)
        epoch_metadata(state,edu,2)
        self.assertEqual(state,before)

    def epoch_persist_fixture(self, label, report, *, fail_flush=False):
        """Run the real nested callback, never execute/load a model or real shard."""
        callback=next(n for n in ast.walk(ast.parse(inspect.getsource(epoch_diag.execute)))
                      if isinstance(n,ast.FunctionDef) and n.name=='persist')
        class Writer:
            def __init__(self):self.rows=[]
            def append(self,item):self.rows.append(copy.deepcopy(item))
        writer=Writer()
        def flush(_writer):
            if fail_flush:raise OSError('fixture flush failed')
        scope=dict(vars(epoch_diag),writer=writer,label=label,report=report,flush_row=flush)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[callback],type_ignores=[])),
                     '<repository epoch persist CPU fixture>','exec'),scope)
        return scope['persist'],writer

    def test_epoch_carried_runtime_row_relabels_without_duplicate_keyword(self):
        report={};persist,writer=self.epoch_persist_fixture('epoch4',report)
        source=dict(model='student',prior_source_model='student',
                    answer_evidence='HASH_LOCKED_PRIOR_COLLECTION',raw_answer='original answer',
                    rendered_answer='original answer')
        before=copy.deepcopy(source);persist(source)
        self.assertEqual(source,before)
        self.assertEqual(writer.rows[0]['model'],'epoch4')
        self.assertEqual(writer.rows[0]['prior_source_model'],'student')
        self.assertEqual(report['actual_carried_rows'],1)
        self.assertEqual(report['actual_raw_rows'],1)
        self.assertEqual(report['actual_answer_rows'],1)

    def test_epoch_new_and_prefix_failure_rows_are_not_carried_answers(self):
        report={};persist,writer=self.epoch_persist_fixture('epoch1',report)
        persist(dict(raw_answer='new',rendered_answer='new'))
        persist(dict(raw_full_text='prefix failure',extraction_status='PREFIX_MISMATCH'))
        self.assertEqual(len(writer.rows),2)
        self.assertEqual(report['actual_new_raw_rows'],2)
        self.assertEqual(report['actual_answer_rows'],1)
        self.assertEqual(report.get('actual_carried_rows',0),0)

    def test_epoch_failed_flush_not_counted_as_confirmed_row(self):
        report={};persist,_writer=self.epoch_persist_fixture('epoch1',report,fail_flush=True)
        with self.assertRaisesRegex(OSError,'flush failed'):
            persist(dict(raw_answer='new',rendered_answer='new'))
        self.assertEqual(report.get('actual_raw_rows',0),0)

    def test_epoch_error_summary_separates_plan_actual_and_cause(self):
        report=dict(status='TOOL_FAILURE',returncode=9,actual_model_calls=0,models={},
                    error_type='TypeError',error='duplicate model keyword',execution_phase='CARRY_PARENT')
        summary=epoch_diag.final_summary(report)
        self.assertEqual(summary['planned_total_answer_rows'],180)
        self.assertEqual(summary['planned_carried_rows'],72)
        self.assertEqual(summary['actual_raw_rows'],0)
        self.assertEqual(summary['actual_answer_rows'],0)
        self.assertEqual(summary['actual_carried_rows'],0)
        self.assertEqual(summary['error_type'],'TypeError')
        self.assertEqual(summary['error'],'duplicate model keyword')
        self.assertEqual(summary['execution_phase'],'CARRY_PARENT')
        self.assertEqual(summary['quality'],'NOT_REVIEWED')
        self.assertNotIn('total_answer_rows',summary)

    def test_epoch_retry_check_only_uses_new_namespace_and_restores_default(self):
        old=epoch_diag.OUTPUT
        observed=[]
        def check():
            observed.append(epoch_diag.OUTPUT);return dict(models=5,planned_model_calls=108)
        with patch.object(sys,'argv',['retry','--check-only']),patch.object(epoch_diag,'check',side_effect=check),\
             patch.object(epoch_diag,'execute',side_effect=AssertionError('model must not execute')),redirect_stdout(io.StringIO()):
            self.assertEqual(epoch_retry.main(),0)
        self.assertEqual(observed,[epoch_retry.OUTPUT]);self.assertNotEqual(old,epoch_retry.OUTPUT)
        self.assertEqual(epoch_diag.OUTPUT,old)

    def test_epoch_retry_hold_preserves_old_output_and_default(self):
        old=epoch_diag.OUTPUT
        with patch.object(sys,'argv',['retry','--execute']),\
             patch.object(epoch_diag,'check',side_effect=FileExistsError('v2 exists; preserve')),\
             patch.object(epoch_diag,'execute',side_effect=AssertionError('model must not execute')),redirect_stderr(io.StringIO()):
            self.assertEqual(epoch_retry.main(),8)
        self.assertEqual(epoch_diag.OUTPUT,old)

    def test_epoch_summary_manifest_count_and_actual_calls_remain_distinct(self):
        report=dict(status='TOOL_FAILURE',returncode=9,actual_model_calls=0,actual_raw_rows=36,
                    actual_answer_rows=36,actual_carried_rows=36,answer_manifests={'parent':{'rows':36}})
        summary=epoch_diag.final_summary(report)
        self.assertEqual(summary['actual_model_calls'],0)
        self.assertEqual(summary['actual_carried_rows'],36)
        self.assertEqual(summary['verified_manifest_rows'],36)
        self.assertEqual(summary['planned_total_answer_rows'],180)

    def test_first_question_group_preserved_all_variants(self):
        profiles=set()
        for i in range(40):
            r=row(i);q=derive(r);profiles.add(q['meta']['capability_profile'])
            self.assertEqual(conversation_split_key(r),conversation_split_key(q))
            self.assertEqual(r['messages'][0]['content'],q['messages'][int(q['messages'][0]['role']=='system')]['content'])
            self.assertEqual(q['meta']['semantic_truth'],'NOT_REVIEWED')
        self.assertEqual(profiles,{'qa','json','multiturn'})

    def test_json_wrapper_and_controlled_turns_not_new_knowledge(self):
        rs=[derive(row(i)) for i in range(40)]
        j=next(r for r in rs if r['meta']['capability_profile']=='json')
        value=json.loads(j['messages'][-1]['content'][0]['text'])
        self.assertEqual(len(value),1)
        self.assertTrue(all(type(v) is int for v in value.values()))
        self.assertEqual(j['meta']['multiturn_kind'],'code_authored_format_followup')
        m=next(r for r in rs if r['meta']['capability_profile']=='multiturn')
        self.assertEqual(len(m['messages']),6)
        self.assertEqual(m['meta']['multiturn_kind'],'code_authored_memory_followup')
        self.assertEqual(json.loads(m['messages'][-1]['content'][0]['text'])['answer'],m['messages'][1]['content'][0]['text'])

    def test_real_multiturn_not_rewritten_or_labeled_synthetic(self):
        r=row();r['messages']+=normalize(dict(messages=[dict(role='user',content='후속 질문'),dict(role='assistant',content='후속 답')]))['messages']
        q=derive(r)
        self.assertEqual(q['messages'],r['messages'])
        self.assertEqual(q['meta']['multiturn_kind'],'source_role_sequence')

    def test_control_value_ranges_follow_actual_split_not_other_hash(self):
        observed=set()
        for i in range(500):
            r=derive(row(i))
            if r['meta']['capability_profile']!='json':continue
            val=int.from_bytes(conversation_split_key(r)[:4],'big')%20==0
            n=r['meta']['control_output_contract']['value'];observed.add(val)
            self.assertTrue(80<=n<=98 if val else 2<=n<=79)
        self.assertEqual(observed,{False,True})

    def test_unknown_task_not_silently_called_qa(self):
        self.assertIsNone(derive(row(family='Wiki-split-inst')))

    def test_observed_collection_question_family_aliases(self):
        for family in ('Flan-Coqa (T)','NQ-Open (T)','NQ-Open'):
            self.assertIsNotNone(derive(row(family=family)))

    def test_additional_panel_excluded_without_semantic_blacklist(self):
        from scripts.p106b_refill_eval_panel import panel
        from tinylm.data.prepare import SyntheticTokenizer
        r=row();r['messages'][0]['content']=normalize(dict(messages=[dict(role='user',content=panel()['singles'][0]['question'])]))['messages'][0]['content']
        selector=CapabilitySelector(SyntheticTokenizer())
        self.assertIsNone(selector.consider(r))
        self.assertEqual(selector.rejections['fixed_probe_question'],1)

    def test_one_source_group_no_repeat_in_index(self):
        c=sqlite3.connect(':memory:');initialize(c)
        r=derive(row());r['meta'].update(parent_concept_id='A',source_split='train',processed_x_tokens=10,
                                        assistant_targets=4,original_source_x_tokens=8)
        index(c,r,0,0);index(c,r,1,1)
        self.assertEqual(c.execute('SELECT COUNT(*) FROM candidates').fetchone()[0],1)
        self.assertEqual(c.execute('SELECT COUNT(*) FROM capability').fetchone()[0],1)
        result=select(c,goal=100)
        self.assertFalse(result['token_target_ready'])
        self.assertTrue(any(result['teacher_deficit_tokens'].values()))
        self.assertEqual(result['capability_selection_version'],VERSION)

    def test_epoch_metadata_is_not_final_format_or_wire(self):
        state,edu=self.epoch_state_fixture()
        epoch_metadata(state,edu,2)
        for key,value in [('epoch',1),('updates',2),('processed_tokens',100),('input',{})]:
            with self.subTest(key=key):
                bad=copy.deepcopy(state);bad[key]=value
                with self.assertRaises(ValueError):epoch_metadata(bad,edu,2)

    def test_epoch_metadata_rejects_real_wrong_dense_tied_vocab_geometry(self):
        state,edu=self.epoch_state_fixture()
        for key,value in [('n_middle',12),('tie_mlp',True),('vocab_size',32000)]:
            with self.subTest(key=key):
                bad=copy.deepcopy(state);bad['cfg'][key]=value
                with self.assertRaises(ValueError):epoch_metadata(bad,edu,2)

    def test_epoch_metadata_rejects_invalid_or_fabricated_saved_config(self):
        state,edu=self.epoch_state_fixture()
        for value in (None,[],{},dict(state['cfg'],n_layers=14)):
            with self.subTest(cfg_type=type(value).__name__):
                bad=copy.deepcopy(state);bad['cfg']=value
                with self.assertRaises(ValueError):epoch_metadata(bad,edu,2)

    def test_legacy_modes_default_are_unchanged_and_profile_has_no_mix(self):
        import inspect
        from scripts.diag_p106b_mixed_repeat4 import check
        self.assertFalse(inspect.signature(check).parameters['capability'].default)


if __name__=='__main__':unittest.main()
