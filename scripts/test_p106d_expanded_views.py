"""Balanced4096 CPU codecs only; no actual tokenizer, model or protected IO."""
from __future__ import annotations
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106d_expanded_views as large
from scripts import p106d_views as small
from scripts.test_p106d_views import fixture_signature

class ExpandedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=large.build(fixture_signature,train_rows=64,val_rows=16,attempts=16)

    def test_ready_and_balanced_changed_and_unchanged(self):
        r=self.data["report"]
        self.assertTrue(r["ready"])
        self.assertEqual(r["curriculum_policy_rows"],{"ANSWER_UNCHANGED":24,"ANSWER_CHANGED":24,"FORMAT_VERBATIM":16})

    def test_each_arm_has_same_gold_change_policy(self):
        for i,base in enumerate(self.data["fixed"]):
            expected=base["meta"]["curriculum_policy"]
            for rows in self.data["epochs"]:
                row=rows[i]
                self.assertEqual(row["meta"]["curriculum_policy"],expected)
                if expected!="FORMAT_VERBATIM":
                    changed=small.text_at(row,-1)!=small.text_at(row,1)
                    self.assertEqual(changed,expected=="ANSWER_CHANGED")

    def test_matching_and_at_least_two_views(self):
        for i,base in enumerate(self.data["fixed"]):
            views=[rows[i] for rows in self.data["epochs"]]
            self.assertTrue(all(fixture_signature(r)==fixture_signature(base) for r in views))
            self.assertGreaterEqual(len({(small.text_at(r,-2),small.text_at(r,-1)) for r in views}),2)

    def test_old_val_roots_and_questions_are_excluded(self):
        excluded=self.data["report"]["roots"]["val"]
        questions=[small.text_at(r,0) for r in self.data["probes"]]
        d=large.build(fixture_signature,train_rows=64,val_rows=16,attempts=16,excluded_roots=excluded,excluded_questions=questions)
        self.assertFalse(set(excluded)&set(d["report"]["roots"]["train"]+d["report"]["roots"]["val"]))
        self.assertTrue(all(small.text_at(r,0) not in questions for r in d["fixed"]+d["probes"]))

    def test_more_than80_boolean_roots_without_enum_fake_uniqueness(self):
        roots={small.hash_object(small.root_definition(large.expanded_recipe("boolean",i))) for i in range(1600)}
        self.assertGreater(len(roots),512)
        a=large.expanded_recipe("boolean",0); b=large.expanded_recipe("boolean",1600)
        self.assertEqual(small.root_definition(a),small.root_definition(b))

    def test_c3_fixed_contains_all_known_keys_not_only_answer(self):
        rows=[r for r in self.data["fixed"] if r["meta"]["root_family"]=="format"]
        import json
        keys={next(iter(json.loads(small.text_at(r,-1)))) for r in rows}
        self.assertEqual(keys,set(large.KEYS))

    def test_expired_wall_budget_stops_before_codec(self):
        def forbidden(_row):
            self.fail("expired budget must stop before tokenizer callback")
        with self.assertRaises(TimeoutError):
            large.build(forbidden,train_rows=64,val_rows=16,deadline=0)

if __name__=="__main__": unittest.main(verbosity=2)
