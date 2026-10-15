#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import summarize_p106b_grounded_span as code


def row(key,good=True,language='ko'):
    return dict(meta=dict(semantic_root_id=key,language=language),messages=[dict(role='user',content='same'+key)],gold='answer',answer='answer' if good else 'other')


class Readback(unittest.TestCase):
    def test_exact_pair_and_order(self):
        a=code.indexed([row('a',False),row('b',False)]);b=code.indexed([row('b'),row('a')])
        r=code.paired(a,b,repetitions=100);self.assertEqual(r['delta_literal'],1);self.assertEqual(r['bootstrap95'],[1,1])

    def test_duplicate_root_rejected(self):
        with self.assertRaises(ValueError):code.indexed([row('a'),row('a')])

    def test_prompt_drift_rejected(self):
        a=code.indexed([row('a')]);b=copy.deepcopy(a);b['a']['messages'][0]['content']='different'
        with self.assertRaises(ValueError):code.paired(a,b,repetitions=100)

    def test_language_separation(self):
        a=code.indexed([row('a',False,'ko'),row('b',True,'en')]);b=code.indexed([row('a',True,'ko'),row('b',False,'en')])
        self.assertEqual(code.paired(a,b,'ko',100)['delta_literal'],1)
        self.assertEqual(code.paired(a,b,'en',100)['delta_literal'],-1)


if __name__=='__main__':unittest.main()
