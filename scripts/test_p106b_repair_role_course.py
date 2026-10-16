#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter
import copy
import json
import unittest
from unittest.mock import patch
from scripts import diag_p106b_repair_role_course as c


class Course(unittest.TestCase):
    def test_explicit_four_recipe_layout_and_native_budget(self):
        self.assertEqual(512+4096+256+2048,6912)
        self.assertEqual(6912//128*4,216);self.assertEqual(216*8192,1769472)
        self.assertEqual(len(c.ARMS),4)
        self.assertEqual(c.info()['parent_sha256'],'567D379E3F8F1B8BBE1F65303DE9AAF1D1F3A33AFE5F9EA51CD12EE06069F9AF')
        self.assertFalse(c.info()['formal_train_ready'])

    def test_data_and_teacher_CODE_are_independent_for_live_production(self):
        self.assertNotIn('scripts/p106b_role_bridge.py',c.producer.CODE)
        self.assertNotIn('scripts/diag_p106b_repair_role_course.py',c.producer.CODE)
        self.assertIn('scripts/p106b_role_bridge.py',c.CODE)

    def test_missing_native_marker_rejected_before_fallback(self):
        r=json.loads((c.old.base.CORPUS/'report.json').read_text());r['native_train_offsets']=r['native_train_offsets'][:1728]
        del r['native_access']
        with self.assertRaisesRegex(ValueError,'explicit indexed'):c.native_contract(r)

    def test_actual_native_fixture_reader_and_slices(self):
        r=json.loads((c.old.base.CORPUS/'report.json').read_text());r['native_train_offsets']=r['native_train_offsets'][:1728]
        o=c.native_contract(r)
        self.assertEqual(o,dict(read_only=True,windows=1728,slices_checked=16))

    def test_interleaved_views_balanced_within_each_family(self):
        tok=c._tokenizer();graphs=c.bridge.graphs(64,'dev');exposure=Counter()
        for epoch in range(4):
            values=c.bridge_views(graphs,epoch,tok)
            self.assertEqual(len(values),128)
            self.assertEqual(Counter(x['meta']['view'] for x in values),{i:32 for i in range(4)})
            for row in values:exposure[row['meta']['neutral_root'],row['meta']['language'],row['meta']['view']]+=1
        self.assertEqual(set(exposure.values()),{1})

    def test_incomplete_teacher_quota_is_not_silently_shrunk(self):
        with patch.object(c.producer,'state',return_value=({},[],set(),Counter(ko=255,en=256),[])):
            with self.assertRaisesRegex(Exception,'512 not complete'):c.selected_teacher()

    def test_counts_use_the_same_wrong_context_mask_as_actual_trainer(self):
        tok=c._tokenizer();row=c.factory.make(c.factory.graph(17),'en',3)
        rec,_=c.factory.encode(row,tok)
        self.assertTrue(all(y==-100 for y,s in zip(rec.y,rec.segments) if s==1))
        self.assertEqual(c.counts([row],tok)['assistant_targets'],rec.targets)


if __name__=='__main__':unittest.main()
