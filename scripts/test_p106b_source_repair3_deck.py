#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter
import unittest
from unittest.mock import patch
from tokenizers import Tokenizer
import torch
from scripts import diag_p106b_source_repair3 as d


class Deck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok=Tokenizer.from_file(str(d.training.data.TOKENIZER))
        with patch.object(torch,'load',side_effect=AssertionError('no model in source-deck proof')):
            cls.jobs,cls.test,cls.supply=d.make_jobs(cls.tok)

    def test_actual_source640_and_new_test64(self):
        self.assertEqual(len(self.jobs),640);self.assertEqual(len({x['root'] for x in self.jobs}),640)
        self.assertEqual(Counter(j['language'] for j in self.jobs),dict(ko=320,en=320))
        self.assertEqual(Counter(j['language'] for j in self.jobs[:16]),dict(ko=8,en=8))
        self.assertEqual(len(self.test),64);self.assertEqual(Counter(x['meta']['language'] for x in self.test),dict(ko=32,en=32))
        self.assertFalse(torch.cuda.is_initialized())

    def test_raw_common_policy_complete_masks_and_source_bytes(self):
        for job in self.jobs:
            self.assertLessEqual(len(self.tok.encode(job['reference']).ids),640)
            row=d.fields.render(job,job['raw_pairs'],self.tok,repaired=False)
            self.assertEqual(row['meta']['assistant_turns'],3)
            self.assertLessEqual(row['meta']['actual_x_tokens'],1024)

    def test_new_test_not_training_or_duplicate_reference(self):
        train={x['root'] for x in self.jobs};test={x['meta']['semantic_root_id'] for x in self.test}
        self.assertEqual(len(test),64);self.assertFalse(train&test)
        self.assertTrue(self.supply['fresh_public']['excludes_previous_ids_references_and_exact24word'])
        self.assertTrue(self.supply['fresh_public']['span_uniqueness_not_a_general_SFT_requirement'])


if __name__=='__main__':unittest.main()
