from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import view_p106b_learning_answers as code


class Views(unittest.TestCase):
    def test_actual_question_answers_and_unverified_scope_shown(self):
        row=dict(messages=[dict(role='user',content=[dict(type='text',text='2+3?')])],gold='5',answer='6',
            meta=dict(language='ko',kind='arithmetic'),generation=dict(finish_reason='STOP'))
        other=copy.deepcopy(row);other['answer']='5'
        result=code.render(dict(code=dict(parent=[row],student=[other]),public=dict(parent=[row],student=[other])))
        for text in ('2+3?','6','5','미검증','parent 실제 첫 답','student 실제 첫 답'):
            self.assertIn(text,result)

    def test_different_cases_or_gold_are_rejected(self):
        a=dict(messages=[dict(role='user',content='question')],gold='5',answer='5',
            meta=dict(language='en',kind='arithmetic'),generation=dict(finish_reason='STOP'))
        b=copy.deepcopy(a);b['gold']='6'
        with self.assertRaises(ValueError):code.render(dict(code=dict(a=[a],b=[b])))
        b['messages'][0]['content']='different'
        with self.assertRaises(ValueError):code.render(dict(code=dict(a=[a],b=[b])))


if __name__=='__main__':unittest.main()
