#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import summarize_p106b_dualqa_eval as s


def events(root,answer='답'):
    result=[]
    for order in (0,1):
        for turn,history in ((1,'ACTUAL_MODEL'),(2,'ACTUAL_MODEL'),(2,'GOLD_REFERENCE')):
            messages=[dict(role='user',content='source question')]
            if turn==2:messages.extend([dict(role='assistant',content='이전 답'),dict(role='user',content='second question')])
            row=dict(root=root,order=order,turn=turn,history=history,language='ko',messages=messages,
                answer=answer,gold='답',generation=dict(finish_reason='STOP'))
            row['scores']=s.evaluate.score(row);result.append(row)
    return result


class Readback(unittest.TestCase):
    def test_bootstrap_clusters_document_not_views(self):
        a=s.indexed(events('a','오답')+events('b','오답'),documents=2)
        b=s.indexed(events('a')+events('b'),documents=2)
        r=s.compare(a,b,repetitions=200)
        self.assertEqual(r['documents'],2);self.assertEqual(r['events'],8)
        self.assertEqual(r['metrics']['literal']['bootstrap95'],[1.,1.])

    def test_actual_first_answer_can_differ_not_user_or_gold(self):
        left=s.indexed(events('a'),documents=1);right=copy.deepcopy(left)
        right['a',0,2,'ACTUAL_MODEL']['messages'][1]['content']='모델마다 다른 첫답'
        s.compare(left,right,repetitions=100)
        right['a',0,2,'ACTUAL_MODEL']['messages'][-1]['content']='바뀐 질문'
        with self.assertRaisesRegex(ValueError,'user questions'):s.compare(left,right,repetitions=100)

    def test_duplicate_or_missing_event_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):s.indexed(events('a')+events('a'),documents=1)
        with self.assertRaisesRegex(ValueError,'all document views'):s.indexed(events('a')[:-1],documents=1)

    def test_raw_count_mismatch_not_trusted(self):
        rows=events('a');rows[0]['scores']['literal']=0
        with self.assertRaisesRegex(ValueError,'stored score'):s.indexed(rows,documents=1)


if __name__=='__main__':unittest.main()
