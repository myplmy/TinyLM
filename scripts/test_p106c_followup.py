#!/usr/bin/env python3
"""Pure data/fixture contracts for P106C follow-up; no checkpoint/model execution."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106c_data as data
from scripts.diag_p106c_prompt_cache import prompt_grid
from scripts.p106c_pair_balance import make_plan
from scripts.diag_p106c_balanced_policy import validate_native_deltas, require_a, POLICY_SHA, PREPARE_SHA, SUBJECTS


class GridTests(unittest.TestCase):
    def test_facts_targets_and_order_are_independently_crossed(self):
        rows=prompt_grid(data.make_role('sealed'))
        self.assertEqual(len(rows),64)
        self.assertEqual(len({r['id'] for r in rows}),64)
        self.assertEqual(Counter(r['language'] for r in rows),{'ko':32,'en':32})
        for r in rows:
            self.assertEqual(r['gold'],r['facts'][r['target']])
            self.assertNotEqual(r['gold'],r['other'])
            self.assertEqual(r['role'],'POSTHOC_DIAGNOSTIC')
        for pair in range(8):
            chunk=rows[pair*8:pair*8+8]
            self.assertEqual(len({r['question'] for r in chunk}),8)
            self.assertEqual(len({tuple(r['facts'].items()) for r in chunk}),1)

    def test_invalid_pair_is_not_silently_rewritten(self):
        rows=data.make_role('sealed')
        rows[1]['pair_id']='another'
        with self.assertRaises(ValueError):prompt_grid(rows)


class BalancedTests(unittest.TestCase):
    def test_both_arms_match_color_pairs_languages_and_token_mass(self):
        train,rehearsal=data.make_role('train'),data.make_role('rehearsal')
        encoded=lambda rows:[([1]*8,[1]*8,2) for r in rows]
        tr,rh=encoded(train),encoded(rehearsal)
        plan=make_plan(train,rehearsal,tr,rh,[12,11])
        self.assertEqual(plan,make_plan(train,rehearsal,tr,rh,[12,11]))
        for left,right in zip(plan['baseline'],plan['selected']):
            self.assertEqual(left['rehearsal'],right['rehearsal'])
            for arm in (left,right):
                ids=arm['candidate']
                counts=Counter((train[i]['language'],train[i]['gold']) for i in ids)
                self.assertEqual(set(counts.values()),{2})
                self.assertEqual(len(counts),8)
                self.assertTrue(all(ids[i+1]==ids[i]+1 and ids[i]%2==0 for i in range(0,16,2)))
            self.assertEqual([train[i]['gold'] for i in left['candidate']], [train[i]['gold'] for i in right['candidate']])
        self.assertLessEqual(max(plan['max_pair_exposures'].values()),16)

    def test_common_boundary_guard_never_compares_unequal_horizons(self):
        self.assertEqual(validate_native_deltas({'baseline':.51,'selected':.53}),{'baseline':.51,'selected':.53})
        with self.assertRaises(ValueError):validate_native_deltas({'baseline':.01})
        with self.assertRaises(ValueError):validate_native_deltas({'baseline':.01,'selected':float('nan')})

    def test_a_completion_is_not_inferred_from_good_answers(self):
        fixture={'status':'PROMPT_CACHE_DIAGNOSTIC_COMPLETE','case_count':384,'path_gate_passed':True,
                 'unresolved_fp32_cache_differences':0,'training_updates':0,'checkpoint_writes':0,
                 'records':[{}]*192,'input':{'policy_sha256':POLICY_SHA,'prepare_sha256':PREPARE_SHA,
                                          'subjects':[list(s) for s in SUBJECTS]}}
        require_a(fixture)
        fixture['unresolved_fp32_cache_differences']=1
        with self.assertRaises(ValueError):require_a(fixture)


if __name__=='__main__':
    unittest.main()
