#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter
import copy
import unittest
from tokenizers import Tokenizer
from scripts import p106b_role_bridge as f
from scripts import diag_p106b_original_qa3_course as original
from tinylm.train.mtp_sft import encode_record


class Bridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok=Tokenizer.from_file(str(original.training.data.TOKENIZER))
        cls.approved=f.binding.approved_questions('train')

    def test_balanced_unique_graphs_and_split_names(self):
        for split in ('train','dev','test'):
            graphs=f.graphs(128,split)
            self.assertEqual(len({g['root'] for g in graphs}),128)
            self.assertEqual(Counter(g['family'] for g in graphs),{k:32 for k in f.FAMILIES})
        for language in f.NAMES:
            a,b,c=[set(f.NAMES[language][s]) for s in ('train','dev','test')]
            self.assertFalse(a&b or a&c or b&c)

    def test_fact_identity_does_not_count_unused_random_fields_as_new_facts(self):
        g=f.graph(0);self.assertEqual(g['family'],'people')
        self.assertEqual(g,f.graph(0));self.assertEqual(f.values(g,'en')['boy_age'],str(g['ages'][0]))
        changed=copy.deepcopy(g);changed['ages'][0]+=1
        with self.assertRaisesRegex(ValueError,'exact signed'):f.values(changed,'en')

    def test_all_families_views_languages_and_styles_are_complete(self):
        for index in range(8):
            g=f.graph(index)
            for language in ('ko','en'):
                for view in range(4):
                    for style in (0,2):
                        row=f.make(g,language,view,style,self.tok);rec=encode_record(row,self.tok)
                        self.assertLessEqual(rec.x_tokens,1024)
                        self.assertEqual({s for y,s in zip(rec.y,rec.segments) if y!=-100},{1,2,3})
                        self.assertEqual(row['meta']['label_status'],'CODE_PRODUCER_TARGETS')
                        self.assertEqual(row['meta']['teacher_calls'],0)
                        self.assertFalse(row['meta']['formal_train_ready'])

    def test_intentional_repeat_and_paraphrase_are_correct_positive_targets(self):
        for index in range(4):
            g=f.graph(index)
            for language in ('ko','en'):
                repeat,_=f.qa_pairs(g,language,0);paraphrase,_=f.qa_pairs(g,language,1)
                self.assertEqual(len({x['question'] for x in repeat}),1)
                self.assertEqual(len({x['answer'] for x in repeat}),1)
                self.assertEqual(paraphrase[0]['answer'],paraphrase[1]['answer'])
                self.assertNotEqual(paraphrase[0]['question'],paraphrase[1]['question'])

    def test_program_known_numeric_update_and_unchanged_other_field(self):
        for index,key in ((0,'boy_age'),(1,'area')):
            g=f.graph(index);before=f.values(g,'en');pairs,requested=f.qa_pairs(g,'en',3)
            self.assertEqual(pairs[1]['answer'],str(int(before[key])+g['delta']))
            self.assertEqual(pairs[2]['answer'],before[requested[2]])

    def test_duration_recomputed_when_end_year_changes(self):
        g=f.graph(3);pairs,requested=f.qa_pairs(g,'en',3)
        self.assertEqual(requested,['end','end','duration'])
        self.assertEqual(pairs[1]['answer'],str(g['end']+g['delta']))
        self.assertEqual(pairs[2]['answer'],str(g['end']+g['delta']-g['start']))

    def test_recipient_update_does_not_change_sender(self):
        g=f.graph(2);v=f.values(g,'ko');pairs,requested=f.qa_pairs(g,'ko',3)
        self.assertEqual(requested,['recipient','recipient','sender'])
        self.assertEqual(pairs[1]['answer'],v['replacement']);self.assertEqual(pairs[2]['answer'],v['sender'])

    def test_seen_and_heldout_question_forms_are_distinct(self):
        for g in [f.graph(i) for i in range(4)]:
            for language in ('ko','en'):
                for key in f.keys(g):
                    self.assertEqual(len({f.question(key,language,s) for s in (0,1,2,3)}),4)
                pairs,_=f.qa_pairs(g,language,1,2)
                self.assertNotEqual(pairs[0]['question'],pairs[1]['question'])

    def test_same_neutral_facts_have_separate_language_child_roots(self):
        g=f.graph(1);ko=f.make(g,'ko',2,0,self.tok);en=f.make(g,'en',2,0,self.tok)
        self.assertEqual(ko['meta']['neutral_root'],en['meta']['neutral_root'])
        self.assertNotEqual(ko['meta']['semantic_root_id'],en['meta']['semantic_root_id'])
        self.assertEqual(ko['meta']['answer_types'],en['meta']['answer_types'])

    def test_repeat_control_uses_exact_producer_not_self_declared_metadata(self):
        item=f.binding.prior.correct_own_question(f.binding.prior.source.binding_rows('train',per_family=1)[0])
        row=f.repeat_control(item,self.tok,self.approved)
        self.assertTrue(row['meta']['intentional_duplicate_allowed'])
        self.assertEqual(len({f.wrap.text(x) for x in row['messages'][1::2]}),1)
        changed=copy.deepcopy(item);changed['messages'][1]['content'][0]['text']='untrusted'
        with self.assertRaises(ValueError):f.repeat_control(changed,self.tok,self.approved)

    def test_reference_is_exact_given_fiction_and_complete_ranges(self):
        g=f.graph(2);row=f.make(g,'en',2,0,self.tok);lo,hi=row['meta']['student_reference_range']
        self.assertEqual(f.wrap.text(row['messages'][0])[lo:hi],f.reference(g,'en'))
        self.assertIn('fictional',f.reference(g,'en'))


if __name__=='__main__':unittest.main()
