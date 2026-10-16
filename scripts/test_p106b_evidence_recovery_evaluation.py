#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_evidence_recovery_evaluation as e
from scripts import diag_p106b_evidence_recovery_course as c


class Evaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tok=c.old._tokenizer()

    def values(self,lang='en',condition=0):
        row=c.method.make(c.method.base.graph(7,'test'),lang,condition,True,2,self.tok);seen=[]
        def emit(messages):seen.append(copy.deepcopy(messages));return 'WRONG'+str(len(seen)),dict(finish_reason='STOP')
        events=e.collect(row,emit);return row,seen,events

    def test_actual_history_and_answer_intent_after_supplement(self):
        row,calls,events=self.values()
        self.assertEqual(e.source.text(calls[2][1]),'WRONG1')
        self.assertEqual(e.source.text(calls[2][3]),'WRONG2')
        self.assertEqual([x['expected_response_intent'] for x in events[:3]],['ASK_FOR_MISSING_FACT','ANSWER','ANSWER'])
        self.assertTrue(e.counts(events)['clarification_exact_match_is_not_semantic_judgment'])

    def test_both_languages_and_all_counterfactuals_cluster_as_one_neutral(self):
        values=[x for l in ('ko','en') for m in range(4) for x in self.values(l,m)[2]]
        r=e.paired(values,values,neutral=True,draws=20)
        self.assertEqual(r['group_roots'],1);self.assertEqual(r['actual_events'],24)

    def test_given_first_answer_oracle_is_not_substituted_for_actual(self):
        _,calls,events=self.values()
        actual=[x for x in events if x['history']=='ACTUAL_MODEL']
        gold=[x for x in events if x['history']=='GOLD_REFERENCE']
        self.assertEqual(len(actual),3);self.assertEqual(len(gold),2)
        self.assertNotEqual(calls[1],calls[3])


if __name__=='__main__':unittest.main()
