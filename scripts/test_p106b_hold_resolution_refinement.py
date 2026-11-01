"""Source-boundary, literal integrity and individual-HOLD reuse regressions."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_refinement as refinement


def source(text):
    return dict(id="expanded_train:1",source="expanded_train",split="train",source_ids=[0,17],
                source_ids_sha256="A"*64,original_text_sha256=refinement.inv.sha(text),input_ids=17,text=text,
                complete_eos=True,valid_utf8=True)


class FrozenDraftTests(unittest.TestCase):
    def make(self,text,decision="KEEP",replacement=None,new=None):
        row=source(text)
        old={key:value for key,value in row.items()if key!="text"}
        old.update(decision=decision,reasons=["frozen-evidence"],changes=[],clean_text_sha256=None)
        if decision in{"KEEP","EDIT"}:
            body=replacement if decision=="EDIT"else text
            old["clean_text_sha256"]=refinement.inv.sha(body)
            if decision=="EDIT":
                old["text"]=body
        calls=[]
        def propose(fresh,individual=False):
            calls.append(fresh["id"])
            return new if new is not None else dict(decision="PENDING",text=fresh["text"],reasons=["still-needs-context"],changes=[])
        policy=SimpleNamespace(RULES="TEST_NEW_RULE",propose=propose)
        return row,refinement.FrozenDraftSelector([old],policy),calls

    def test_keep_is_reproduced_without_reprocessing_it_as_a_new_example(self):
        row,selector,calls=self.make("완결된 설명이다.")
        value=selector.propose(row)
        self.assertEqual(value["text"],row["text"])
        self.assertEqual(calls,[])

    def test_edit_reproduces_the_exact_frozen_body(self):
        row,selector,calls=self.make("완결 설명. 빈표제", "EDIT", "완결 설명.")
        self.assertEqual(selector.propose(row)["text"],"완결 설명.")
        self.assertEqual(calls,[])

    def test_only_pending_calls_the_new_policy(self):
        row,selector,calls=self.make("빈 값 ().", "PENDING")
        self.assertEqual(selector.propose(row)["decision"],"PENDING")
        self.assertEqual(calls,[row["id"]])

    def test_changed_interval_is_rejected_even_when_body_is_identical(self):
        row,selector,_=self.make("완결 설명.")
        row["source_ids"]=[1,18]
        with self.assertRaisesRegex(ValueError,"identity/interval"):
            selector.propose(row)

    def test_changed_body_cannot_borrow_a_known_hash(self):
        row,selector,_=self.make("완결 설명.")
        row["text"]="다른 설명."
        with self.assertRaisesRegex(ValueError,"body"):
            selector.propose(row)

    def test_individual_hold_is_never_released_by_a_frozen_positive(self):
        row,selector,_=self.make("완결 설명.")
        with self.assertRaisesRegex(ValueError,"individual HOLD"):
            selector.propose(row,True)

    def test_an_automatic_new_name_or_number_is_rejected(self):
        new=dict(decision="EDIT",text="원래 이름은 가람이고 값은 99이다.",reasons=["bad-new-fact"],changes=[])
        row,selector,_=self.make("원래 이름은 가람이다.","PENDING",new=new)
        with self.assertRaisesRegex(ValueError,"literal"):
            selector.propose(row)

    def test_new_policy_cannot_release_an_inherited_pending_source(self):
        new=dict(decision="KEEP",text="완결 설명.",reasons=["bad-individual-release"],changes=[])
        row,selector,_=self.make("완결 설명.","PENDING",new=new)
        row["previous_holds"]=["source-span-review"]
        with self.assertRaisesRegex(ValueError,"individual HOLD"):
            selector.propose(row)

    def test_reordered_existing_words_are_rejected(self):
        new=dict(decision="EDIT",text="셋 둘 하나",reasons=["bad-order"],changes=[])
        row,selector,_=self.make("하나 둘 셋", "PENDING",new=new)
        with self.assertRaisesRegex(ValueError,"literal"):
            selector.propose(row)

    def test_deleting_part_of_real_code_is_rejected(self):
        before="설명.\n```python\nhelper()\n```\n"
        new=dict(decision="EDIT",text=before.replace("helper()","helper"),reasons=["bad-code"],changes=[])
        row,selector,_=self.make(before,"PENDING",new=new)
        with self.assertRaisesRegex(ValueError,"literal"):
            selector.propose(row)


if __name__=="__main__":
    unittest.main()
