#!/usr/bin/env python3
"""Recovery counterexamples: lost names/formulas, intact references and code."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_policy as policy


class RecoveryPolicyTests(unittest.TestCase):
    def propose(self,text,**event):
        row=dict(id="expanded_train:0",text=text,complete_eos=True,valid_utf8=True)
        return policy.propose(row,dict(reasons=[],**event))

    def test_populated_references_and_citations_remain(self):
        text="도시의 역사에 관한 설명이다.\n참고 문헌\nSmith, A. (2001). A complete citation.\n외부 링크\nhttps://example.org/history\n"
        r=self.propose(text);self.assertEqual(r["decision"],"KEEP");self.assertEqual(r["text"],text)

    def test_empty_album_sections_are_not_restored_unchanged(self):
        text="이 음반은1973년에 발매된 음반이다.\n곡 목록\n평가\n각주\n"
        r=self.propose(text);self.assertEqual(r["decision"],"EDIT")
        self.assertEqual(r["text"],"이 음반은1973년에 발매된 음반이다.\n")

    def test_optional_alias_can_be_removed_without_names_or_numbers(self):
        text="로하()는 에콰도르의 도시이다. 인구는180,617명(2010년)이다.\n"
        r=self.propose(text);self.assertEqual(r["decision"],"EDIT")
        self.assertEqual(r["text"],text.replace("로하()","로하"))

    def test_empty_alias_is_not_a_function_call_edit(self):
        text="함수 f()는 인수가 없는 함수이다.\n참고 문헌\nA citation."
        r=self.propose(text);self.assertEqual(r["decision"],"HOLD");self.assertEqual(r["text"],text)

    def test_related_topic_names_are_not_mistaken_for_empty_sections(self):
        text="도시에 관한 설명이다.\n같이 보기\n교통\n문화\n인구\n"
        r=self.propose(text);self.assertEqual(r["decision"],"KEEP")
        self.assertEqual(r["text"],text)

    def test_ambiguous_bare_heading_list_is_not_deleted(self):
        text="주제에는 다음 항목이 있다.\n문화\n교통\n"
        r=self.propose(text);self.assertEqual(r["decision"],"HOLD")
        self.assertEqual(r["text"],text)

    def test_missing_formula_and_title_are_not_generated(self):
        for text in ["Relation is a subset of .\nSelect ( )\n", "《》는1991년영화이다.\n"]:
            self.assertEqual(self.propose(text)["decision"],"HOLD")

    def test_source_boundary_and_prior_review_cannot_be_released(self):
        text="독립적인 설명이다.\n"
        self.assertEqual(self.propose(text,manual_hold=True)["decision"],"HOLD")
        row=dict(id="validation:0",text=text,complete_eos=True,valid_utf8=True)
        self.assertEqual(policy.propose(row,dict(reasons=[]))["decision"],"HOLD")

    def test_real_code_bytes_survive_nfc_and_empty_labels(self):
        text='설명이다.\n```py\nname="e\u0301"\nfunction()\n```\n각주\n'
        r=self.propose(text);self.assertEqual(r["decision"],"EDIT")
        self.assertTrue(policy.code_preserved(text,r["text"]))
        self.assertIn('e\u0301',r["text"])

    def test_decorative_tildes_are_distinct_from_real_code(self):
        old="A complete article. Decoration ~~~~~~~~~~~~ here.\n```py\nprint(42)\n```\n"
        good=old.replace("Decoration ~~~~~~~~~~~~ here.","")
        self.assertTrue(policy.code_preserved(old,good))
        self.assertFalse(policy.code_preserved(old,good.replace("42","43")))

    def test_open_real_fence_stays_hold(self):
        self.assertEqual(self.propose("A description.\n```py\nprint(42)\n")["decision"],"HOLD")

    def test_marketing_and_broken_tables_stay_unresolved(self):
        for text in ["A book description.\nAdd to cart\n", "선수 기록이다.\n{|\n|}\n"]:
            self.assertEqual(self.propose(text)["decision"],"HOLD")

    def test_main_prose_repetition_is_not_automatically_deleted(self):
        text="The refrain is repeated.\nThe refrain is repeated.\n"
        r=self.propose(text);self.assertEqual(r["decision"],"HOLD");self.assertEqual(r["text"],text)

    def test_repeated_reference_is_kept_with_its_relationship(self):
        text="A complete source explanation.\nReferences\nSmith (2001).\nSmith (2001).\n"
        r=self.propose(text);self.assertEqual(r["decision"],"KEEP");self.assertEqual(r["text"],text)


if __name__=="__main__":unittest.main()
