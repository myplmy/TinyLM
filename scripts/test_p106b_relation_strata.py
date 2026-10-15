#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_relation_strata as s


def events():
    out=[]
    for i in range(2):
        for lang in ('ko','en'):
            for view in range(4):out+=s.method.collect(s.method.factory.make(s.method.factory.graph(i,'test'),lang,view),lambda m:('',dict(finish_reason='STOP')))
    return out


class Strata(unittest.TestCase):
    def test_history_scopes_never_pooled(self):
        rows=events();r=s.counts(rows)
        self.assertEqual(r['ACTUAL_MODEL/all']['cases'],24);self.assertEqual(r['PROVIDED_WRONG_HISTORY/all']['cases'],4)
        self.assertEqual(r['GOLD_REFERENCE/all']['cases'],12)
        p=s.pairs_by_lane(rows,rows,draws=10)
        self.assertEqual(p['ACTUAL_MODEL/all']['literal']['events'],24)
        self.assertEqual(p['PROVIDED_WRONG_HISTORY/all']['literal']['events'],4)
        self.assertNotIn('GOLD_REFERENCE/all',p)

    def test_first_same_input_and_output_invariance(self):
        rows=events();r=s.first_invariance(rows);self.assertEqual(r['root_language_groups'],4);self.assertEqual(r['first_output_disagreements'],0)
        changed=copy.deepcopy(rows);one=next(e for e in changed if e['view']==1 and e['history']=='ACTUAL_MODEL' and e['turn']==1)
        one['answer']='changed';one['scores']=s.method.score(one)
        self.assertEqual(s.first_invariance(changed)['first_output_disagreements'],1)

    def test_micro_weighting_not_mean_of_unequal_root_means(self):
        rows=[e for e in events() if e['history']=='ACTUAL_MODEL'];roots=sorted({e['root'] for e in rows})
        left=[next(e for e in rows if e['root']==roots[0])]+[e for e in rows if e['root']==roots[1]][:3]
        self.assertEqual([e['root'] for e in left].count(left[0]['root']),1)
        right=copy.deepcopy(left);right[0]['answer']=right[0]['gold'];right[0]['scores']=s.method.score(right[0])
        p=s.weighted_pair(left,right,draws=50);self.assertEqual(p['right_minus_left'],.25);self.assertEqual(p['neutral_roots'],2)

    def test_duplicate_and_mismatched_pair_rejected(self):
        rows=events()
        with self.assertRaisesRegex(ValueError,'duplicate'):s.index(rows+rows[:1])
        with self.assertRaisesRegex(ValueError,'coverage'):s.pairs_by_lane(rows,rows[:-1])

    def test_identical_endpoint_differences_zero(self):
        rows=events();p=s.weighted_pair(rows,rows,draws=50)
        self.assertEqual(p['right_minus_left'],0.);self.assertEqual(p['ci95'],[0.,0.])


if __name__=='__main__':unittest.main()
