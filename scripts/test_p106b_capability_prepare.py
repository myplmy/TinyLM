#!/usr/bin/env python3
"""Small CPU data/metadata fixtures; no checkpoint loading, teacher or GPU."""
import copy
import json
from pathlib import Path
import sqlite3
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.p106b_capability_corpus import derive,initialize,index,select,VERSION,CapabilitySelector
from scripts.diag_p106b_epoch_retention import epoch_metadata
from tinylm.chat.canonical import normalize
from tinylm.data.sft import conversation_split_key


def row(i=0,family='aya_dataset',language='ko'):
    return normalize(dict(messages=[dict(role='user',content='고유 질문 '+str(i)),
                                    dict(role='assistant',content='원천 답 '+str(i))],
                          meta=dict(language=language,source_family=family)))


class PrepareTests(unittest.TestCase):
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
        hist=[dict(epoch=i,updates=i*10,processed_tokens=100) for i in (1,2,3,4)]
        edu=dict(history=hist,input={'tokenizer_sha256':'test'})
        state=dict(epoch=2,input=edu['input'],history=hist[:2],updates=20,step=2309,processed_tokens=200,
                   cfg=dict(n_layers=14,tie_mlp=False,vocab_size=32768))
        epoch_metadata(state,edu,2)
        for key,value in [('epoch',1),('updates',2),('processed_tokens',100),('input',{})]:
            with self.subTest(key=key):
                bad=copy.deepcopy(state);bad[key]=value
                with self.assertRaises(ValueError):epoch_metadata(bad,edu,2)

    def test_legacy_modes_default_are_unchanged_and_profile_has_no_mix(self):
        import inspect
        from scripts.diag_p106b_mixed_repeat4 import check
        self.assertFalse(inspect.signature(check).parameters['capability'].default)


if __name__=='__main__':unittest.main()
