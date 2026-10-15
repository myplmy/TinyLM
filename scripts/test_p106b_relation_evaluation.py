#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_relation_evaluation as e


class Evaluation(unittest.TestCase):
    def run_case(self,view,first='실제 오답'):
        row=e.factory.make(e.factory.graph(18,'test'),'ko',view);calls=[]
        def emit(messages):
            calls.append(copy.deepcopy(messages));return (first if len(calls)==1 else '실제 둘째'),dict(finish_reason='STOP')
        return row,calls,e.collect(row,emit)

    def test_actual_history_not_gold(self):
        row,calls,events=self.run_case(2)
        self.assertEqual(e.factory_text(calls[1][1]),'실제 오답')
        self.assertEqual(calls[2][1],row['messages'][1])
        self.assertEqual([v['history'] for v in events],['ACTUAL_MODEL','ACTUAL_MODEL','GOLD_REFERENCE'])
        self.assertEqual(events[1]['target_key'],row['meta']['producer_graph']['other'])

    def test_supplied_wrong_context_is_not_self_recovery(self):
        row,calls,events=self.run_case(3)
        self.assertEqual(len(calls),1);self.assertEqual(calls[0],row['messages'][:3])
        self.assertEqual(events[0]['history'],'PROVIDED_WRONG_HISTORY');self.assertEqual(events[0]['turn'],2)

    def test_empty_answer_preserved(self):
        _,calls,events=self.run_case(1,first='')
        self.assertEqual(e.factory_text(calls[1][1]),'');self.assertEqual(events[0]['scores']['empty'],1)

    def test_exact_wrong_field_not_fuzzy_blacklist(self):
        row=e.factory.make(e.factory.graph(18,'test'),'en',0)
        gold=e.factory_text(row['messages'][1]);wrong=e.factory.answer(row['meta']['producer_graph'],'en',row['meta']['producer_graph']['other'])
        values=e.collect(row,lambda m:(gold,dict(finish_reason='STOP')))
        self.assertEqual(values[0]['scores']['literal'],1)
        one=copy.deepcopy(values[0]);one['answer']=wrong
        self.assertEqual(e.score(one)['exact_other_field'],1)
        one['answer']='Maybe '+wrong;self.assertEqual(e.score(one)['exact_other_field'],0)

    def test_all_views_and_clustered_language_children(self):
        values=[]
        for i in range(2):
            for lang in ('ko','en'):
                for view in range(4):values+=e.collect(e.factory.make(e.factory.graph(i,'test'),lang,view),lambda m:('',dict(finish_reason='STOP')))
        self.assertEqual(len(values),40);self.assertEqual(sum(v['cases'] for v in e.summarize(values).values()),40)
        p=e.paired(values,values,draws=20);self.assertEqual(p['roots'],2);self.assertEqual(p['events'],28)
        self.assertEqual(p['ci95'],[0.,0.]);self.assertEqual(p['right_minus_left'],0.)
        with self.assertRaisesRegex(ValueError,'coverage'):e.paired(values,values[:-1])
        with self.assertRaisesRegex(ValueError,'duplicate'):e.summarize(values+values[:1])


if __name__=='__main__':unittest.main()
