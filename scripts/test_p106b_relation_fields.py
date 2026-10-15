#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_relation_fields as f


class Fields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tokenizers import Tokenizer
        cls.tok=Tokenizer.from_file(str(ROOT/'data_cache/tok-ko-en-32768-chat32.json'))
    def test_deterministic_graph_and_dates(self):
        g=f.graph(5);self.assertEqual(g,f.graph(5))
        years=[]
        for p in g['people']:
            self.assertLess(p['birth_year'],p['publication_year']);self.assertLess(p['publication_year'],p['death_year'])
            years.extend(p[k] for k in ('birth_year','publication_year','death_year'))
        self.assertEqual(len(years),len(set(years)))

    def test_all_fields_have_both_languages_and_three_question_forms(self):
        g=f.graph(0)
        for lang in ('ko','en'):
            for field in f.FIELDS:
                key=[0,field];qs=[f.question(g,lang,key,s) for s in range(3)]
                self.assertEqual(len(set(qs)),3);self.assertTrue(all(f.answer(g,lang,key) not in q for q in qs))
                self.assertIn(f.answer(g,lang,key),f.statement(g,lang,key))

    def test_normal_and_paraphrase_repeat_are_allowed(self):
        g=f.graph(1)
        for lang in ('ko','en'):
            a=f.make(g,lang,0);b=f.make(g,lang,1)
            text=lambda r,i:''.join(x['text'] for x in r['messages'][i]['content'])
            self.assertEqual(text(a,1),text(a,3));self.assertEqual(text(b,1),text(b,3));self.assertNotEqual(text(a,2),text(b,2))

    def test_switch_and_wrong_history_are_distinct_values(self):
        for i in range(20):
            g=f.graph(i)
            for lang in ('ko','en'):
                for view in (2,3):
                    row=f.make(g,lang,view);texts=[''.join(x['text'] for x in m['content']) for m in row['messages']]
                    self.assertNotEqual(texts[1],texts[3])

    def test_wrong_first_all_targets_ignored_including_end(self):
        from tinylm.train import mtp_sft as core
        row=f.make(f.graph(2),'ko',3);before=core.encode_record(row,self.tok);rec,label=f.encode(row,self.tok)
        self.assertTrue(any(y!=-100 and s==1 for y,s in zip(before.y,before.segments)))
        self.assertTrue(all(y==-100 for y,s in zip(rec.y,rec.segments) if s==1))
        self.assertTrue(any(y!=-100 and s==2 for y,s in zip(rec.y,rec.segments)))
        self.assertEqual([q['turn'] for q in label['queries']],[2])

    def test_causal_fact_spans_and_query_predictors(self):
        for i in range(8):
            for lang in ('ko','en'):
                for view in range(4):
                    row=f.make(f.graph(i),lang,view);rec,label=f.encode(row,self.tok)
                    self.assertLessEqual(rec.x_tokens,1024);self.assertEqual(len(label['spans']),12)
                    for q in label['queries']:
                        self.assertTrue(all(max(s)<q['position'] for s in label['spans']))
                        self.assertNotEqual(rec.y[q['position']],-100)

    def test_feedback_does_not_reveal_target_value(self):
        for i in range(80):
            for lang in ('ko','en'):
                row=f.make(f.graph(i),lang,3);last_user=''.join(x['text'] for x in row['messages'][2]['content'])
                self.assertNotIn(row['meta']['gold_value'],last_user)

    def test_unknown_graph_or_modified_source_not_given_labels(self):
        g=f.graph(1);g['people'][0]['birth_year']+=1
        with self.assertRaisesRegex(ValueError,'producer graph'):f.make(g,'ko',0)
        row=f.make(f.graph(1),'ko',0);row['messages'][0]['content'][0]['text']+='변조'
        with self.assertRaisesRegex(ValueError,'exact producer'):f.encode(row,self.tok)

    def test_neutral_root_shared_by_languages_not_splits(self):
        g=f.graph(1)
        self.assertEqual(f.make(g,'ko',0)['meta']['neutral_root'],f.make(g,'en',0)['meta']['neutral_root'])
        self.assertNotEqual(f.graph(1,'train')['root'],f.graph(1,'test')['root'])
        for lang in ('ko','en'):
            self.assertFalse(set(f.NAMES[lang]['train'])&set(f.NAMES[lang]['test']))

    def test_generator_does_not_modify_inputs(self):
        g=f.graph(11);before=copy.deepcopy(g)
        for lang in ('ko','en'):
            for view in range(4):f.make(g,lang,view,self.tok)
        self.assertEqual(g,before)

    def test_linear_source_offsets_match_brute_overlap(self):
        offsets=[(0,0),(0,2),(2,5),(5,9),(9,11),(11,15),(15,15)]
        ranges=[(1,4),(6,10),(12,14)]
        brute=[[i for i,(x,y) in enumerate(offsets) if y>x and x<b and y>a] for a,b in ranges]
        self.assertEqual(f.token_spans(offsets,ranges),brute)


if __name__=='__main__':unittest.main()
