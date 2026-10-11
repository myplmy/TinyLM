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

    def test_format_has_real_paraphrases_with_one_fixed_key(self):
        spec=large.make_spec(large.expanded_recipe("format",7),"en","train")
        rows=list(large.candidates(spec,changed=None,key="answer",seed=1337,count=64))
        import json
        self.assertEqual({next(iter(json.loads(small.text_at(r,-1)))) for r in rows},{"answer"})
        self.assertGreaterEqual(len({small.text_at(r,-2) for r in rows}),8)
        self.assertEqual(len({small.text_at(r,0) for r in rows}),1)

    def test_per_key_token_length_does_not_fake_a_matched_view(self):
        import json
        def codec(row):
            if row["meta"].get("followup_kind")=="C3_VERBATIM_FORMAT":
                key=next(iter(json.loads(small.text_at(row,-1))))
                return 100+large.KEYS.index(key),8
            return fixture_signature(row)
        data=large.build(codec,train_rows=64,val_rows=16,attempts=64)
        self.assertTrue(data["report"]["ready"])
        for i,base in enumerate(data["fixed"]):
            if base["meta"]["root_family"]!="format":continue
            target=small.text_at(base,-1)
            self.assertTrue(all(small.text_at(rows[i],-1)==target for rows in data["epochs"]))

    def test_viable_matching_bucket_need_not_include_first_candidate(self):
        spec=large.make_spec(large.expanded_recipe("format",3),"en","train")
        rows=list(large.candidates(spec,changed=None,key="answer",seed=1337,count=8))
        first=small.text_at(rows[0],-2)
        def sig(r):return (101,9) if small.text_at(r,-2)==first else (100,9)
        base,options,signature=large.matched_class(rows,sig)
        self.assertEqual(signature,(100,9))
        self.assertGreaterEqual(len(options),2)
        self.assertNotEqual(small.text_at(base,-2),first)

if __name__=="__main__": unittest.main(verbosity=2)
