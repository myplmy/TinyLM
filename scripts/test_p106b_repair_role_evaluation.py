#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from tokenizers import Tokenizer
from scripts import p106b_repair_role_evaluation as e
from scripts import p106b_role_bridge as bridge
from scripts import diag_p106b_original_qa3_course as old


class Evaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tok=Tokenizer.from_file(str(old.training.data.TOKENIZER))

    def values(self,language='en',style=0):
        row=bridge.make(bridge.graph(7,'test'),language,2,style,self.tok);seen=[]
        def emit(messages):seen.append(copy.deepcopy(messages));return 'WRONG'+str(len(seen)),dict(finish_reason='STOP')
        events=e.collect(row,emit);return row,seen,events

    def test_actual_wrong_history_not_gold_and_code_scope(self):
        row,calls,events=self.values()
        self.assertEqual(e.source.text(calls[2][1]),'WRONG1');self.assertEqual(e.source.text(calls[2][3]),'WRONG2')
        self.assertEqual(len(events),5)
        self.assertTrue(all(x['source_truth']=='GIVEN_PROGRAM_PRODUCER_RECORD_ONLY' for x in events))
        self.assertIn('view=2',e.counts(events)['producer_slices'])

    def test_neutral_group_keeps_both_language_children_and_styles(self):
        events=[]
        for language in ('ko','en'):
            for style in (0,2):events.extend(self.values(language,style)[2])
        r=e.paired(events,events,neutral=True,draws=20)
        self.assertEqual(r['group_roots'],1);self.assertEqual(r['actual_events'],12)
        self.assertEqual(r['metrics']['literal']['ci95'],[0.,0.])

    def test_missing_cases_and_target_change_rejected(self):
        events=self.values()[2]
        with self.assertRaisesRegex(ValueError,'complete'):e.paired(events,events[:-1],neutral=True,draws=10)
        bad=copy.deepcopy(events);bad[0]['gold']='different';bad[0]['scores']=e.source.score(bad[0])
        with self.assertRaisesRegex(ValueError,'target'):e.paired(events,bad,neutral=True,draws=10)


if __name__=='__main__':unittest.main()
