#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
from scripts import p106b_dualqa_dialogue_controls as c
from scripts import test_p106b_dualqa_course as fixture
from scripts import summarize_p106b_dualqa_eval as summaries


def emit():return lambda messages:('모델 출력',dict(finish_reason='STOP'))


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.Course.setUpClass();cls.tok=fixture.Course.tok
    def row(self):return fixture.Course().student()

    def test_mixed_matches_original_collector(self):
        row=self.row();a=c.collect(row,0,self.tok,emit(),'contrast');b=c.reference.collect(row,0,self.tok,emit())
        for item in a:item.pop('test_pattern')
        self.assertEqual(a,b)

    def test_same_first_prompt_and_normal_repeated_gold(self):
        for parity in (0,1):
            a=c.collect(self.row(),parity,self.tok,emit(),'contrast');b=c.collect(self.row(),parity,self.tok,emit(),'repeat')
            self.assertEqual(a[0]['messages'],b[0]['messages']);self.assertEqual(a[0]['gold'],b[0]['gold'])
            self.assertNotEqual(a[0]['gold'],a[1]['gold']);self.assertEqual(b[0]['gold'],b[1]['gold'])

    def test_actual_wrong_first_not_gold_injected(self):
        b=c.collect(self.row(),0,self.tok,emit(),'repeat')
        self.assertEqual(c.reference.course.data.text(b[1]['messages'][1]),'모델 출력')
        self.assertEqual(c.reference.course.data.text(b[2]['messages'][1]),'사서')

    def test_empty_actual_first_retained(self):
        b=c.collect(self.row(),1,self.tok,lambda m:('',dict(finish_reason='STOP')),'repeat')
        self.assertEqual(c.reference.course.data.text(b[1]['messages'][1]),'')

    def test_copying_wrong_answer_not_a_quality_pass(self):
        mixed=[];repeat=[]
        for p in (0,1):
            mixed+=c.collect(self.row(),p,self.tok,emit(),'contrast')
            repeat+=c.collect(self.row(),p,self.tok,emit(),'repeat')
        for event in mixed+repeat:event['scores']=c.reference.score(event)
        b=c.behaviour(summaries.indexed(mixed,documents=1),summaries.indexed(repeat,documents=1))
        self.assertEqual(b['repeat_copy_first'],2);self.assertEqual(b['repeat_both_literal'],0)
        self.assertFalse(b['automatic_quality_pass']);self.assertEqual(b['first_output_disagreements'],0)

    def test_unsupported_pattern_rejected(self):
        with self.assertRaises(ValueError):c.collect(self.row(),0,self.tok,emit(),'unknown')


if __name__=='__main__':unittest.main()
