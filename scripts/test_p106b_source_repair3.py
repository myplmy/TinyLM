#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import json
import unittest
from tokenizers import Tokenizer
from scripts import p106b_source_repair3 as f
from scripts import diag_p106b_original_qa3_course as c
from scripts.test_p106b_public_qa_roles import fixture
from scripts import p106b_public_qa_roles as old


def final():return 'Q1: Who?\nA1: Yes\nQ2: Really?\nA2: Yes\nQ3: Still?\nA3: Yes'


class Repair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tok=Tokenizer.from_file(str(c.training.data.TOKENIZER))

    def job(self):
        _,row=c.natural_views(fixture());return f.from_wrapped(row)

    def test_six_labels_optional_note_and_legitimate_equal_answers(self):
        x=f.parse_fields(final());self.assertEqual(len(x['pairs']),3)
        self.assertEqual([p['answer'] for p in x['pairs']],['Yes']*3)
        self.assertTrue(x['empty_note_filled_by_code']);self.assertEqual(x['duplicate_type'],'UNKNOWN_NO_CONTENT_REGENERATION')

    def test_repeated_structural_label_is_not_repeated_answer(self):
        with self.assertRaisesRegex(ValueError,'field label'):f.parse_fields(final()+'\nQ3: duplicate label')
        self.assertEqual(f.parse_fields(final()+'\nNOTE:')['note'],'')

    def test_preface_not_silently_stripped(self):
        with self.assertRaisesRegex(ValueError,'preface'):f.parse_fields('Analysis before final\n'+final())

    def test_full_source_same_code_wrapping_and_registered_transform(self):
        j=self.job();before=copy.deepcopy(j);x=f.parse_fields(final());r=f.render(j,x['pairs'],self.tok,repaired=True,record_id='fixture')
        self.assertEqual([m['role'] for m in r['messages']],['user','assistant']*3)
        lo,hi=r['meta']['student_reference_range'];self.assertEqual(f.text(r['messages'][0])[lo:hi],j['reference'])
        self.assertEqual(r['meta']['source_transform'],'teacher_answer');self.assertFalse(r['meta']['formal_train_ready'])
        self.assertEqual(j,before)

    def test_raw_and_repaired_use_same_policy_not_teacher_owned_json(self):
        j=self.job();raw=f.render(j,j['raw_pairs'],self.tok,repaired=False)
        repaired=f.render(j,j['raw_pairs'],self.tok,repaired=True)
        self.assertEqual(raw['messages'],repaired['messages'])
        self.assertNotIn('source_transform',raw['meta'])

    def test_reasoning_and_metadata_never_enter_student(self):
        reply=dict(choices=[dict(finish_reason='stop',message=dict(content=final(),reasoning_content='SECRET_INTERNAL_REASONING'))])
        channels=f.channels(reply);parsed=f.parse_fields(channels['final'])
        r=f.render(self.job(),parsed['pairs'],self.tok,repaired=True,note='METADATA_ONLY')
        self.assertNotIn('SECRET_INTERNAL_REASONING',json.dumps(r['messages']))
        self.assertNotIn('METADATA_ONLY',json.dumps(r['messages']))

    def test_three_assistant_segments_and_eot_targets(self):
        from tinylm.train.mtp_sft import encode_record
        r=f.render(self.job(),f.parse_fields(final())['pairs'],self.tok,repaired=True)
        rec=encode_record(r,self.tok)
        self.assertEqual({s for y,s in zip(rec.y,rec.segments) if y!=-100},{1,2,3})
        end=self.tok.token_to_id('<|im_end|>');self.assertEqual(sum(y==end for y in rec.y),3)

    def test_source_prompt_boundaries_and_native_thinking(self):
        j=self.job();request=f.payload(j,7)
        self.assertEqual(request['messages'][1]['content'].count(j['reference']),1)
        self.assertTrue(request['messages'][0]['content'].startswith('<|think|>'))
        self.assertEqual(request['thinking_budget_tokens'],256);self.assertFalse(request['cache_prompt'])
        self.assertIn('missing clarification',request['messages'][0]['content'])
        self.assertEqual(request['top_k'],64)

    def test_new_original_parser_accepts_nonextractive_answer_without_changing_old(self):
        row=fixture();row['messages'][0]['content'][0]['text']=f.text(row['messages'][0]).replace('Nora','Lina').replace('Who wrote WindRoad?','Was Lina born in1902?')
        row['messages'][1]['content'][0]['text']='1. No 2. Yes 3. Maybe 4. Later'
        out=f.original_three(row);self.assertEqual(out['raw_pairs'][0]['answer'],'No')
        self.assertNotIn('No',out['reference'])
        with self.assertRaises(ValueError):old.wrap(row)

    def test_original_parser_keeps_syntax_and_ranges(self):
        row=fixture();before=copy.deepcopy(row);out=f.original_three(row)
        for i,spans in enumerate(out['original_item_ranges']):
            for field,j in (('question',0),('answer',1)):
                a,b=spans[field];self.assertEqual(f.text(row['messages'][j])[a:b].strip(),out['raw_pairs'][i][field])
        self.assertEqual(row,before)
        row['messages'][0]['content'][0]['text']=f.text(row['messages'][0]).replace('3. What','3 years What')
        with self.assertRaisesRegex(ValueError,'boundaries'):f.original_three(row)

    def test_decline_is_self_report_not_truth(self):
        self.assertEqual(f.parse_fields('STATUS: INSUFFICIENT_SOURCE\nmissing reference')['status'],'PRODUCER_DECLINED')

    def test_oversized_field_rejected_for_structure_budget_only(self):
        pairs=f.parse_fields(final())['pairs'];pairs[0]['answer']='long token '*100
        with self.assertRaisesRegex(ValueError,'48 learner'):f.render(self.job(),pairs,self.tok,repaired=True)


if __name__=='__main__':unittest.main()
