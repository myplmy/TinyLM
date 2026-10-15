#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_original_qa3_evaluation as e
from scripts.test_p106b_public_qa_roles import fixture
from scripts import diag_p106b_original_qa3_course as c


class Evaluation(unittest.TestCase):
    def test_real_first_and_second_answers_preserved(self):
        _,row=c.natural_views(fixture());calls=[]
        def emit(messages):calls.append(copy.deepcopy(messages));return 'wrong'+str(len(calls)),dict(finish_reason='STOP')
        events=e.collect(row,emit)
        self.assertEqual(len(events),5);self.assertEqual(e.text(calls[1][1]),'wrong1')
        self.assertEqual(e.text(calls[2][1]),'wrong1');self.assertEqual(e.text(calls[2][3]),'wrong2')
        self.assertEqual(calls[3],row['messages'][:3]);self.assertEqual(calls[4],row['messages'][:5])

    def test_empty_answers_not_replaced_by_gold(self):
        _,row=c.natural_views(fixture());calls=[]
        def emit(messages):calls.append(copy.deepcopy(messages));return '',dict(finish_reason='STOP')
        values=e.collect(row,emit);self.assertEqual(e.text(calls[2][1]),'');self.assertEqual(e.counts(values)['ACTUAL_MODEL/all']['empty'],3)

    def test_three_actual_two_gold_and_no_duplicate_keys(self):
        _,row=c.natural_views(fixture());values=e.collect(row,lambda m:('',dict(finish_reason='STOP')))
        counts=e.counts(values);self.assertEqual(counts['ACTUAL_MODEL/all']['cases'],3);self.assertEqual(counts['GOLD_REFERENCE/all']['cases'],2)
        with self.assertRaisesRegex(ValueError,'duplicate'):e.counts(values+values[:1])

    def test_paired_zero_same_endpoint_and_missing_root_rejected(self):
        _,row=c.natural_views(fixture());values=e.collect(row,lambda m:('',dict(finish_reason='STOP')))
        p=e.paired(values,values,draws=10);self.assertEqual(p['actual_events'],3);self.assertEqual(p['metrics']['literal']['ci95'],[0.,0.])
        with self.assertRaisesRegex(ValueError,'complete'):e.paired(values,values[:-1])


if __name__=='__main__':unittest.main()
