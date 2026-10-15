#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
from scripts import diag_p106b_dualqa_eval as e
from scripts import test_p106b_dualqa_course as fixture


class ActualHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.Course.setUpClass();cls.tok=fixture.Course.tok
    def test_second_turn_contains_model_not_gold_answer(self):
        calls=[]
        def emit(messages):
            calls.append(messages)
            return ('모델 오답' if len(calls)==1 else '둘째 답'),dict(finish_reason='STOP')
        result=e.collect(fixture.Course().student(),0,self.tok,emit)
        self.assertEqual(len(calls),3)
        self.assertEqual(e.course.data.text(calls[1][1]),'모델 오답')
        self.assertEqual(e.course.data.text(calls[2][1]),'사서')
        self.assertEqual([r['history'] for r in result],['ACTUAL_MODEL','ACTUAL_MODEL','GOLD_REFERENCE'])
        self.assertEqual(len(calls[0]),1);self.assertEqual(len(calls[1]),3)

    def test_empty_first_answer_still_preserved_in_actual_history(self):
        calls=[]
        def emit(messages):calls.append(messages);return '',dict(finish_reason='STOP')
        result=e.collect(fixture.Course().student(),1,self.tok,emit)
        self.assertEqual(e.course.data.text(calls[1][1]),'')
        self.assertEqual(result[0]['gold'],'화가');self.assertEqual(result[1]['gold'],'사서')

    def test_both_orders_no_first8_slicer(self):
        counter=0
        for i in range(256):
            for order in (0,1):
                events=e.collect(fixture.Course().student(),order,self.tok,lambda x:('답',dict(finish_reason='STOP')))
                counter+=sum(r['history']=='ACTUAL_MODEL' for r in events)
        self.assertEqual(counter,1024)

    def test_literal_not_promoted_to_truth(self):
        r=dict(answer='5',gold='5',generation=dict(finish_reason='STOP'))
        self.assertEqual(e.score(r)['literal'],1);self.assertEqual(e.metadata()['semantic_truth'],'NOT_RUN')
        self.assertFalse(e.metadata()['auxiliary_used_in_inference'])


if __name__=='__main__':unittest.main()
