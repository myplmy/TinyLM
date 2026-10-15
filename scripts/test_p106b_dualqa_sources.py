#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_dualqa_sources as s
from scripts import p106b_dualqa_teacher as f
from scripts import test_p106b_dualqa_teacher as fixture


class Sources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tokenizers import Tokenizer
        cls.tok=Tokenizer.from_file(str(ROOT/'data_cache/tok-ko-en-32768-chat32.json'))

    def test_scope_and_reference_bytes(self):
        job=fixture.job();job.update(split='train',reference_sha256=f.reference_sha(job['reference']))
        row=s.render(job,f.parse_fields(fixture.FINAL,2),self.tok)
        self.assertTrue(row['messages'][2]['content'][0]['text'].startswith(s.SCOPE['ko']))
        lo,hi=row['meta']['student_reference_range'];self.assertEqual(row['messages'][0]['content'][0]['text'][lo:hi],job['reference'])

    def test_intentional_repeat_reuses_same_q1_target(self):
        job=fixture.job();job.update(split='train',reference_sha256=f.reference_sha(job['reference']))
        diverse=s.render(job,f.parse_fields(fixture.FINAL,2),self.tok,record_id='A')
        repeat=s.repeat_from_student(diverse,self.tok)
        self.assertEqual(repeat['messages'][1]['content'],repeat['messages'][3]['content'])
        self.assertIn('지아',repeat['messages'][2]['content'][0]['text']);self.assertNotIn('준호',repeat['messages'][2]['content'][0]['text'])
        self.assertEqual(diverse['messages'][0],repeat['messages'][0])

    def test_no_input_mutation(self):
        job=fixture.job();job.update(split='dev',reference_sha256=f.reference_sha(job['reference']));before=copy.deepcopy(job)
        s.render(job,f.parse_fields(fixture.FINAL,2),self.tok);self.assertEqual(job,before)

    def test_two_turn_masks_and_no_note_in_training(self):
        from tinylm.train.mtp_sft import encode_record
        job=fixture.job();job.update(split='train',reference_sha256=f.reference_sha(job['reference']))
        parsed=f.parse_fields(fixture.FINAL+'PRIVATE_NOTE',2);row=s.render(job,parsed,self.tok)
        self.assertNotIn('PRIVATE_NOTE',str(row['messages']));self.assertEqual({x for x in encode_record(row,self.tok).segments if x},{1,2})


if __name__=='__main__':unittest.main()
