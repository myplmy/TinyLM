#!/usr/bin/env python3
"""Pure CPU fixture for order-independent frozen subset; no source/model reads."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.p101a_sft_mtp_data import Reservoir,lineage,conversation_identity


class Contract(unittest.TestCase):
    def test_order_independent(self):
        rows=[{'messages':[{'role':'user','content':str(i)}]} for i in range(30)]
        outputs=[]
        for order in (rows,list(reversed(rows))):
            pool=Reservoir(100)
            for row in order:pool.add(row,9)
            outputs.append([r for r,_,_ in pool.rows()])
            self.assertGreaterEqual(pool.tokens,100)
            self.assertLess(pool.tokens,109)
        self.assertEqual(outputs[0],outputs[1])

    def test_no_fake_length(self):
        pool=Reservoir(100)
        for length in (0,1025):
            with self.assertRaises(ValueError):pool.add({},length)

    def test_explicit_lineage(self):
        row={'meta':{'language':'ko','capability_profile':'qa','parent_concept_id':'A'*64}}
        self.assertEqual(lineage(row),('ko','qa','A'*64))
        row['meta']['language']='unknown'
        with self.assertRaises(ValueError):lineage(row)

    def test_exact_conversation_dedup_ignores_source_metadata(self):
        left={'messages':[{'role':'user','content':'1만 말해'},{'role':'assistant','content':'1'}],
            'meta':{'parent_concept_id':'A'*64}}
        right=dict(left,meta={'parent_concept_id':'B'*64})
        self.assertEqual(conversation_identity(left),conversation_identity(right))
        right=dict(right,messages=[{'role':'user','content':'1만 말해'},{'role':'assistant','content':'2'}])
        self.assertNotEqual(conversation_identity(left),conversation_identity(right))


if __name__=='__main__':unittest.main()
