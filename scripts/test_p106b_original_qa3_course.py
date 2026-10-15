#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import json
import unittest
from scripts import diag_p106b_original_qa3_course as c
from scripts.test_p106b_public_qa_roles import fixture


class Course(unittest.TestCase):
    def test_first_pair_identical_and_no_stale_json_contract(self):
        original=fixture();before=copy.deepcopy(original);first,triple=c.natural_views(original)
        self.assertEqual(first['messages'],triple['messages'][:2]);self.assertEqual(len(first['messages']),2);self.assertEqual(len(triple['messages']),6)
        self.assertEqual(first['meta']['semantic_root_id'],triple['meta']['semantic_root_id'])
        self.assertNotIn('control_output_contract',triple['meta']);self.assertEqual(original,before)

    def test_three_turn_targets_and_no_wrong_turn_supervision(self):
        from tokenizers import Tokenizer
        tok=Tokenizer.from_file(str(c.training.data.TOKENIZER));first,triple=c.natural_views(fixture())
        a,_=c.factory.encode(first,tok);b,_=c.factory.encode(triple,tok)
        self.assertGreater(b.targets,a.targets);self.assertEqual({s for y,s in zip(b.y,b.segments) if y!=-100},{1,2,3})
        bad=c.factory.make(c.factory.graph(2),'ko',3);rec,_=c.factory.encode(bad,tok)
        self.assertTrue(all(y==-100 for y,s in zip(rec.y,rec.segments) if s==1))

    def test_whole_update_count_and_last_partial_batch(self):
        groups=list(c.training.batches(list(range(6356)),0))
        self.assertEqual(len(groups),50);self.assertEqual(sum(len(m) for m in groups[-1]),84)
        self.assertEqual(sorted(i for g in groups for m in g for i in m),list(range(6356)))
        self.assertEqual(4*50,200);self.assertEqual(200*8192,1638400)

    def test_actual_readonly_native_consumer(self):
        r=json.loads((c.base.CORPUS/'report.json').read_text());r['native_train_offsets']=r['native_train_offsets'][:1600]
        v=c.check_native(r);self.assertTrue(v['reader_verified']);self.assertTrue(v['read_only']);self.assertEqual(v['windows_checked'],16)

    def test_native_contract_missing_marker_fails_before_legacy_branch(self):
        r=json.loads((c.base.CORPUS/'report.json').read_text());r['native_train_offsets']=r['native_train_offsets'][:1600]
        del r['native_access']
        with self.assertRaisesRegex(ValueError,'explicit indexed'):c.check_native(r)

    def test_new_paths_and_fixed_parent_not_a_test_winner(self):
        self.assertNotEqual(c.EVIDENCE,c.parent_runtime.course.EVIDENCE);self.assertNotEqual(c.CORPUS,c.parent_runtime.course.CORPUS)
        self.assertEqual(c.PARENT_SHA,'687EBCC5E30EA674EF4742BFC2BA6B98BCAB937541BD5498F567A9084387E831')
        self.assertEqual(c.info()['fact_weight'],0.);self.assertEqual(c.info()['arms'],['first','three'])


if __name__=='__main__':unittest.main()
