#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
from scripts import diag_p106b_relation_course as c
from scripts import p106b_relation_fields as f


class Corpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tokenizers import Tokenizer
        cls.tok=Tokenizer.from_file(str(c.training.data.TOKENIZER))
    def test_counts_use_masked_not_unmasked_targets(self):
        rows=[f.make(f.graph(i),'ko',v) for i,v in ((1,0),(2,3))]
        r=c.counts(rows,self.tok);self.assertEqual((r['rows'],r['fact_rows'],r['fact_queries']),(2,2,3))
        from tinylm.train.mtp_sft import encode_record
        self.assertLess(r['assistant_targets'],sum(encode_record(x,self.tok).targets for x in rows))

    def test_declared_root_counts_and_replay_views(self):
        self.assertEqual(c.ROOT_COUNTS,dict(train=8192,dev=128,test=256))
        self.assertEqual(c.REPLAY_VIEWS,('repeat0','contrast0','repeat1','contrast1'))

    def test_view_correction_has_one_supervised_query(self):
        rows=[f.make(f.graph(3),'en',v) for v in range(4)];r=c.counts(rows,self.tok)
        self.assertEqual(r['fact_queries'],7);self.assertEqual(r['fact_rows'],4)

    def test_seed_and_language_rows_share_neutral_root(self):
        g=f.graph(8,'test');rows=[f.make(g,l,0) for l in ('ko','en')]
        self.assertEqual(len({x['meta']['neutral_root'] for x in rows}),1)
        self.assertEqual({x['meta']['language'] for x in rows},{'ko','en'})


if __name__=='__main__':unittest.main()
