#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import diag_p106b_foundation_panel as code


def fixtures():
    return [dict(meta=dict(language=l,semantic_root_id=l+f'{i:03d}'),messages=[dict(role='user',content=[dict(type='text',text=str(i))]),dict(role='assistant',content=[dict(type='text',text='gold')])]) for l in ('ko','en') for i in range(128)]


class Contract(unittest.TestCase):
    def test_same_balanced_subset_when_input_reversed(self):
        rows=fixtures();a=code.select64(rows);b=code.select64(list(reversed(rows)))
        self.assertEqual(a,b);self.assertEqual(len(a),64)
        self.assertEqual([r['meta']['semantic_root_id'] for r in a[:3]],['ko000','ko004','ko008'])

    def test_missing_source_rejected(self):
        with self.assertRaises(ValueError):code.select64(fixtures()[:-1])

    def test_cached_prompt_and_gold_required(self):
        selected=code.select64(fixtures());answers=[dict(meta=r['meta'],messages=r['messages'][:-1],gold='gold') for r in selected]
        code.verify_same_inputs(selected,answers);broken=copy.deepcopy(answers);broken[0]['gold']='other'
        with self.assertRaises(ValueError):code.verify_same_inputs(selected,broken)

    def test_distinct_source_root_required(self):
        rows=fixtures();rows[0]=copy.deepcopy(rows[1])
        with self.assertRaises(ValueError):code.select64(rows)


if __name__=='__main__':unittest.main()
