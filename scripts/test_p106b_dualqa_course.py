#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_dualqa_course as c
from scripts import test_p106b_dualqa_teacher as fixture


class Course(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tokenizers import Tokenizer
        cls.tok=Tokenizer.from_file(str(ROOT/'data_cache/tok-ko-en-32768-chat32.json'))
    def student(self):
        job=fixture.job();job.update(split='train',reference_sha256=c.fields.reference_sha(job['reference']))
        return c.source.render(job,c.fields.parse_fields(fixture.FINAL,2),self.tok,record_id='R')

    def test_four_epoch_marginals_exact(self):
        rows=[self.student()];views,proof=c.marginal_proof(rows,self.tok)
        self.assertEqual(proof['summary']['repeat'],proof['summary']['contrast']);self.assertTrue(proof['token_id_bags_equal'])
        self.assertEqual(c.text(views['repeat',1][0]['messages'][1]),'화가')
        self.assertEqual(c.text(views['repeat',1][0]['messages'][3]),'화가')
        self.assertEqual(c.text(views['contrast',1][0]['messages'][1]),'화가')
        self.assertEqual(c.text(views['contrast',1][0]['messages'][3]),'사서')

    def test_qa_pairs_not_independently_shuffled(self):
        s=self.student();r=c.view(s,'contrast',1,self.tok)
        self.assertIn('준호',c.text(r['messages'][0]));self.assertEqual(c.text(r['messages'][1]),'화가')
        self.assertIn('지아',c.text(r['messages'][2]));self.assertEqual(c.text(r['messages'][3]),'사서')

    def test_source_and_input_immutable(self):
        s=self.student();before=copy.deepcopy(s)
        for a in c.ARMS:
            for parity in (0,1):c.view(s,a,parity,self.tok)
        self.assertEqual(s,before)

    def test_known_source_only_not_teacher_label_guess(self):
        self.assertIsNone(c.binding.binding_bit(self.student(),{}))


if __name__=='__main__':unittest.main()
