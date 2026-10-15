#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_source_template_samples as s


def row(i,t=1):return dict(id=i,inputs='Question '+str(i),targets='Answer '+str(i),dataset_name='HotpotQA (T)',template_id=t,sub_dataset_name='fixture',language='korean')


class Samples(unittest.TestCase):
    def test_file_order_independent_lowest_hash8(self):
        a,b=s.Sampler(),s.Sampler();values=[row(i) for i in range(100)]
        for value in values:a.add(value,'ko',dict(path='fixture'))
        for value in reversed(values):b.add(value,'ko',dict(path='fixture'))
        self.assertEqual(list(a.rows()),list(b.rows()));self.assertEqual(len(list(a.rows())),8)
        self.assertEqual(a.counts(),b.counts());self.assertEqual(next(iter(a.counts().values()))['raw_rows'],100)

    def test_language_and_template_groups_separate(self):
        a=s.Sampler()
        for lang in ('ko','en'):
            for t in (1,3):a.add(row(1,t),lang,{})
        self.assertEqual(len(a.counts()),4);self.assertEqual(len(list(a.rows())),4)

    def test_no_question_mark_is_not_a_semantic_rejection(self):
        a=s.Sampler();r=row(1);r['inputs']='A statement without any request.';a.add(r,'ko',{})
        self.assertEqual(len(list(a.rows())),1);self.assertEqual(next(a.rows())['training_admission'],'NOT_DECIDED')

    def test_empty_input_preserved_for_offline_review(self):
        a=s.Sampler();r=row(1);r['inputs']='';a.add(r,'ko',{})
        self.assertEqual(next(iter(a.counts().values()))['empty_or_nontext'],1);self.assertEqual(len(list(a.rows())),1)

    def test_unknown_family_not_in_scope_and_input_immutable(self):
        a=s.Sampler();r=row(3);old=copy.deepcopy(r);a.add(r,'ko',{});self.assertEqual(r,old)
        r['dataset_name']='SODA-inst';a.add(r,'ko',{});self.assertEqual(sum(x['raw_rows'] for x in a.counts().values()),1)

    def test_packet_row_bytes_bounded(self):
        a=s.Sampler();r=row(1);r['inputs']='x'*(s.MAX_ROW_BYTES+1);a.add(r,'ko',{})
        self.assertFalse(list(a.rows()));self.assertEqual(a.rejections['sample_row_bytes_cap'],1)


if __name__=='__main__':unittest.main()
