"""CPU-only deterministic corpus/QA contract fixtures. No tokenizer/model IO."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106d_views as views
from scripts import p106b_rule_views as rules
from tinylm.chat.serialize import serialize,loss_spans


def fixture_signature(row):
    # A pure codec fixture, explicitly not the project's real tokenizer evidence.
    def units(text):
        return len(re.sub(r"true|false|answer|result|value|reply|-?\d+","#",text))
    rendered=serialize(row)
    spans=loss_spans(row)
    return units(rendered)-1,sum(units(rendered[a:b]) for a,b in spans)


class RuleCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=views.build(fixture_signature,train_rows=32,val_rows=16,attempts=16)

    def test_ready_balanced_rows_and_roots(self):
        r=self.data["report"]
        self.assertTrue(r["ready"]); self.assertEqual(r["train_rows"],32)
        self.assertEqual(r["root_instances"],{"train":16,"val":8})
        self.assertFalse(set(r["roots"]["train"])&set(r["roots"]["val"]))

    def test_token_target_mass_matched_at_each_slot(self):
        expected=[fixture_signature(r) for r in self.data["fixed"]]
        for rows in self.data["epochs"]: self.assertEqual([fixture_signature(r) for r in rows],expected)
        self.assertEqual(self.data["report"]["four_epoch_processed_tokens"],4*sum(n for n,t in expected))

    def test_first_user_and_source_root_preserved(self):
        for i,base in enumerate(self.data["fixed"]):
            for epoch in self.data["epochs"]:
                self.assertEqual(views.text_at(base,0),views.text_at(epoch[i],0))
                self.assertEqual(base["meta"]["root_concept_id"],epoch[i]["meta"]["root_concept_id"])

    def test_language_children_same_split(self):
        mapping={}
        for row in self.data["fixed"]+self.data["probes"]:
            m=row["meta"]; mapping.setdefault(m["root_concept_id"],set()).add(m["split"])
        self.assertTrue(all(len(s)==1 for s in mapping.values()))

    def test_view_diversity_and_no_fake_knowledge_claim(self):
        for index in range(len(self.data["fixed"])):
            rows=[epoch[index] for epoch in self.data["epochs"]]
            self.assertGreaterEqual(len({(views.text_at(r,-2),views.text_at(r,-1)) for r in rows}),2)
            self.assertTrue(all(r["meta"]["unique_knowledge_claim"] is False for r in rows))

    def test_new_probes_do_not_call_train_augmenter(self):
        self.assertTrue(all(row["meta"]["source"]=="p106d_code_probe" for row in self.data["probes"]))
        data=views.recipe("arithmetic",1); spec=views.spec_for(data,"ko","val")
        with self.assertRaises(ValueError): rules.make_condition_followup(spec,seed=1,view_index=0)

    def test_repeat_recipe_does_not_change_source_root(self):
        a=views.recipe("boolean",0); b=views.recipe("boolean",80)
        self.assertEqual(views.hash_object(views.root_definition(a)),views.hash_object(views.root_definition(b)))

    def test_real_signature_needs_valid_assistant_targets(self):
        class Codec:
            def encode(self,*args,**kwargs): raise ValueError("fixture codec refuses")
        with self.assertRaises(ValueError): views.real_signature(self.data["fixed"][0],Codec())

    def test_known_format_key_and_verbatim_roundtrip(self):
        spec=views.spec_for(views.recipe("format",7),"ko","train")
        row=rules.make_format_followup(spec,field_name="result")
        self.assertEqual(json.loads(views.text_at(row,-1)),{"result":"7"})
        with self.assertRaises(ValueError): rules.make_format_followup(spec,field_name="unknown")


if __name__=="__main__": unittest.main(verbosity=2)
