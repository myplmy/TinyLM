#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
from collections import Counter
from scripts import diag_p106b_evidence_recovery_course as c


class Course(unittest.TestCase):
    def test_same6912_rows216_updates_and_actual_native_budget(self):
        r=c.info();self.assertEqual((r['rows_per_epoch'],r['updates'],r['micro_bs'],r['accum']),(6912,216,8,16))
        self.assertEqual(216*8192,1769472);self.assertFalse(r['student_mtp']);self.assertEqual(r['teacher_calls'],0)

    def test_actual_consumer_masks_clarification_and_all_later_answers_positive(self):
        tok=c.old._tokenizer();row=c.method.make(c.method.base.graph(3),'en',0,True,0,tok)
        rec,_=c.factory.encode(row,tok)
        self.assertEqual({s for y,s in zip(rec.y,rec.segments) if y!=-100},{1,2,3})
        self.assertEqual(c.old.counts([row],tok)['assistant_targets'],rec.targets)

    def test_train_four_cells_rotate_and_both_languages_share_neutral(self):
        tok=c.old._tokenizer();graphs=c.method.graphs(32,'train');seen=Counter()
        for epoch in range(4):
            rows=c.extras(graphs,epoch,True,tok)
            self.assertEqual(len(rows),64)
            for r in rows:seen[r['meta']['neutral_root'],r['meta']['language'],r['meta']['condition']]+=1
        self.assertEqual(set(seen.values()),{1})

    def test_new_test_excludes_previous_actual_primary_visible_facts(self):
        train,dev,test=c.source_groups();sets=[{c.method.neutral(g) for g in v} for v in (train,dev,test)]
        self.assertEqual([len(v) for v in sets],[1024,64,128]);self.assertFalse(sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])

    def test_parent_is_fixed_raw_role_not_test_selected_new_epoch(self):
        self.assertEqual(c.PARENT_SHA,'7E584E9F0B99CCFC73D12ED9B36376F214990F5860C85F4A413C096B9438B838')
        self.assertEqual(c.PARENT,c.parent_runtime.checkpoint('raw_role'))
        self.assertEqual(c.ARMS,('complete_replay','evidence_recovery'))


if __name__=='__main__':unittest.main()
