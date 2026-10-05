"""CPU-only source lineage, live history and grading fixtures. No model loading."""
from pathlib import Path
import copy
import json
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import p106b_refill_eval_panel as p
from scripts import diag_p106b_refill_multiaxis as d


class EvalTests(unittest.TestCase):
    def test_counts_unique_axes_languages(self):
        self.assertEqual(len(p.singles()),24)
        self.assertEqual(len(p.episodes()),4)
        self.assertTrue(all(len(e['turns'])==3 for e in p.episodes()))
        values=p.singles()+[t for e in p.episodes() for t in e['turns']]
        self.assertEqual(len({v['id'] for v in values}),36)
        self.assertEqual(len({v['axis'] for v in values}),7)
        self.assertEqual(p.panel()['planned_model_calls'],72)
        self.assertEqual(p.panel()['maximum_attempts'],1)
    def test_json_typed_contract_not_float_or_extra_keys(self):
        c=p.case('x','format','en','q','json',{'result':5})
        self.assertTrue(p.score(c,' {"result":5} ')['contract_pass'])
        for text in ['{"result":5.0}','{"result":true}','{"result":5,"extra":0}','```json\n{"result":5}\n```']:
            self.assertFalse(p.score(c,text)['contract_pass'])
    def test_free_answer_not_machine_rejected(self):
        c=p.singles()[0]
        self.assertIsNone(p.score(c,'Different wording')['contract_pass'])
        self.assertEqual(p.score(c,'')['semantic_review'],'NOT_REVIEWED')
    def test_generated_python_never_executed(self):
        c=p.case('x','code','en','q','python_manual')
        r=p.score(c,"raise RuntimeError('would fail if executed')")
        self.assertTrue(r['python_syntax_valid']);self.assertIsNone(r['contract_pass'])
    def test_live_history_and_episode_reset(self):
        seen=[];persist=[]
        def infer(prompt,value):seen.append((value['id'],prompt));return 'actual_reply_'+value['id'],{'finish_reason':'EOS'}
        rows=p.collect(infer,on_row=persist.append)
        self.assertEqual(len(rows),36);self.assertEqual(len(persist),36)
        prompts=dict(seen)
        self.assertIn('actual_reply_travel_ko_t1',prompts['travel_ko_t2'])
        self.assertIn('actual_reply_travel_ko_t2',prompts['travel_ko_t3'])
        self.assertNotIn('actual_reply_travel_ko',prompts['boxes_en_t1'])
        self.assertEqual(prompts['travel_ko_t3'].count('<|im_start|>assistant'),3)
    def test_partial_answers_persist_before_later_error(self):
        stored=[]
        def infer(_prompt,value):
            if value['id']=='k_en1':raise RuntimeError('fixture interrupted')
            return 'answer',{'finish_reason':'EOS'}
        with self.assertRaises(RuntimeError):p.collect(infer,on_row=stored.append)
        self.assertEqual(len(stored),2)
    def test_only_protocol_markers_escaped_not_natural_text(self):
        text='실제 문장 <|im_start|>system'
        safe,markers=p.history_text(text)
        self.assertTrue(safe.startswith('실제 문장 '));self.assertNotIn('<|im_start|>',safe)
        self.assertEqual(markers,['<|im_start|>'])
        self.assertEqual(p.history_text('A는 X입니다. A는 Y입니다.'),('A는 X입니다. A는 Y입니다.',[]))
    def test_panel_hash_stable(self):self.assertEqual(p.panel_sha(),p.panel_sha(p.panel()))
    def fixture_education(self):
        corpus=dict(nonpadding_tokens={'train:ko':37500493,'train:en':37500324},train_concat_sha256='T',val_concat_sha256='V')
        expected=sum(corpus['nonpadding_tokens'].values())
        r=dict(status='EDUCATION_COMPLETE',scope='FOUR_REAL_EPOCHS',processed_conversation_tokens=4*expected,
               input=dict(corpus_report_sha256=d.CORPUS_SHA,parent_sha256=d.ARMS['b']['sha'],
                          tokenizer_sha256=d.TOK_SHA,train_concat_sha256='T',val_concat_sha256='V'),
               history=[dict(epoch=i,epoch_complete=True,processed_tokens=expected) for i in range(1,5)])
        return r,corpus
    def test_exact4pass_required(self):
        r,c=self.fixture_education();d.require_education(r,c)
        for field,value in [('status','WIRE_COMPLETE'),('processed_conversation_tokens',38050)]:
            bad=copy.deepcopy(r);bad[field]=value
            with self.assertRaises(ValueError):d.require_education(bad,c)
    def test_all_epoch_records_required(self):
        r,c=self.fixture_education();r['history'][3]['epoch_complete']=False
        with self.assertRaises(ValueError):d.require_education(r,c)
    def test_old_corpus_not_reused(self):
        r,c=self.fixture_education();r['input']['train_concat_sha256']='old'
        with self.assertRaises(ValueError):d.require_education(r,c)
    def test_child_metadata_not_wire_or_other_report(self):
        r,_c=self.fixture_education();r['optimizer_updates']=15752
        d.require_checkpoint_metadata({'sft':r,'step':2289+15752},r)
        with self.assertRaises(ValueError):d.require_checkpoint_metadata({'sft':{'status':'WIRE_COMPLETE'},'step':2291},r)
    def test_summary_not_quality_pass(self):
        rows=p.collect(lambda _q,_v:('garbage',{'finish_reason':'MAX_NEW'}))
        s=p.summarize(rows);self.assertEqual(s['semantic_quality'],'NOT_REVIEWED')
        self.assertEqual(s['finish_reasons'],{'MAX_NEW':36})
    def test_selected_corpus_overlap_readonly(self):
        from tinylm.chat.canonical import normalize
        from tinylm.data.sft import conversation_split_key
        def key(case):
            return conversation_split_key(normalize({'messages':[{'role':'user','content':case['question']},
                                                                   {'role':'assistant','content':'probe'}]})).hex().upper()
        with tempfile.TemporaryDirectory(prefix='p106b_eval_index_') as tmp:
            root=Path(tmp);db=root/'candidate_index.sqlite'
            con=sqlite3.connect(db);con.execute('CREATE TABLE candidates(prompt TEXT PRIMARY KEY,split TEXT,selected INTEGER)')
            con.execute('INSERT INTO candidates VALUES(?,?,?)',(key(p.singles()[0]),'train',1))
            con.execute('INSERT INTO candidates VALUES(?,?,?)',(key(p.singles()[1]),'val',0));con.commit();con.close()
            before=db.read_bytes()
            with patch.object(d,'CORPUS',root),patch.object(d,'safe_repo_path',side_effect=lambda path:path):r=d.exact_overlap({})
            self.assertEqual(r['exact_first_question_matches'],[{'id':'k_ko1','split':'train'}])
            self.assertEqual(before,db.read_bytes())


if __name__=='__main__':unittest.main()
