#!/usr/bin/env python3
"""Preserve real examples and reject unrelated syntax/lyrics escape hatches."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_policy_v8 as policy
from scripts import test_p106b_hold_resolution_policy_v7 as inherited


class LiteralContext(unittest.TestCase):
    def propose(self,text,**more):
        return policy.propose(dict(id="expanded_train:1",text=text,complete_eos=True,valid_utf8=True,**more))

    def candidate(self,text):
        result=self.propose(text)
        return result.get("candidate",result["text"])

    def test_complete_unaliased_links_keep_the_original_names(self):
        text="People above the bridge are called [[Yoopers]]. Others are [[Trolls]].\n"
        self.assertEqual(self.propose(text)["text"],"People above the bridge are called Yoopers. Others are Trolls.\n")

    def test_wiki_syntax_examples_remain_literal(self):
        text="Wiki XML syntax uses [[name]] to represent a link.\n"
        self.assertEqual(self.candidate(text),text)

    def test_an_unbalanced_link_is_not_completed(self):
        text="People above the bridge are called [[Yoopers.\n"
        self.assertEqual(self.propose(text)["decision"],"PENDING")
        self.assertEqual(self.candidate(text),text)

    def test_balanced_presentation_keeps_content_and_unicode_exactly(self):
        text="<div>A literal decomposed vowel e\u0301 remains here.</div>\n"
        candidate=self.candidate(text)
        self.assertIn("e\u0301",candidate)
        self.assertNotIn("<div>",candidate)

    def test_literal_xml_and_encoding_examples_are_never_rendered(self):
        text='DocBook XML encoding example: <symbol role="symbolfont">≤</symbol>.\nUTF-8 decoded as ISO-8859-1 may contain Â and â€.\n'
        self.assertEqual(self.candidate(text),text)

    def test_function_call_empty_parentheses_remain_exact(self):
        text='numbers = "this 1 2 3"\nprint(sum([int(num) for num in numbers.split(" ") if num.isnumeric()]))\nIn the above code snippet, we sum the numeric values.\n'
        result=self.propose(text)
        self.assertEqual(result["decision"],"KEEP")
        self.assertEqual(result["text"],text)

    def test_lyric_refrains_are_retained_without_deduplication(self):
        text="가람은 노래이다.\n가사\nThe island in the sun.\nThe island in the sun.\n외부 링크\n가람 공식 사이트\n"
        self.assertEqual(self.propose(text)["decision"],"KEEP")
        self.assertEqual(self.propose(text)["text"],text)

    def test_a_lyric_heading_does_not_release_an_unrelated_main_repeat(self):
        text="가람은 노래이다.\nRepeated editorial statement.\nRepeated editorial statement.\n가사\nActual source lyric.\n"
        self.assertEqual(self.propose(text)["decision"],"PENDING")

    def test_populated_sports_values_prevent_legend_removal(self):
        text="가람은 야구 선수이다.\n연도별 타격 성적\n2012년 15홈런\n굵은 글씨는 시즌 최고 성적.\n"
        self.assertEqual(self.candidate(text),text)

    def test_missing_record_table_holds_only_its_empty_label_and_legend(self):
        text="가람은 야구 선수이다.\n\n연도별 타격 성적\n굵은 글씨는 시즌 최고 성적.\n\n연도별 수비 성적\n굵은 글씨는 시즌 최고 성적.\n\n1980년 출생\n살아있는 사람\n"
        candidate=self.candidate(text)
        self.assertNotIn("굵은 글씨",candidate)
        self.assertNotIn("연도별 수비 성적",candidate)
        self.assertIn("1980년 출생",candidate)

    def test_populated_reference_names_remain_under_their_actual_heading(self):
        text="환기미술관은 서울에 위치한 미술관으로 1992년 설립되었다.\n외부 링크\n환기미술관 -\n1992년 설립\n"
        candidate=self.candidate(text)
        self.assertIn("외부 링크\n환기미술관 -",candidate)

    def test_reference_heading_marks_a_real_repeated_topic_list(self):
        text="가람평야는 평야이다.\n참조\n한국의 평야\n\n한국의 평야\n함경남도\n"
        self.assertEqual(self.propose(text)["decision"],"KEEP")
        self.assertEqual(self.candidate(text),text)

    def test_only_information_free_orphan_template_closing_line_is_removed(self):
        text="《Let It Die》는 2004년에 발매된 음반이다.\n곡 목록\n인증\n</ref>}}\n2004년 음반\n"
        self.assertNotIn("</ref>}}",self.candidate(text))
        self.assertIn("2004년 음반",self.candidate(text))

    def test_programming_angle_parameters_are_kept_literally(self):
        text="Lisp function reference.\nSyntax\n(sref <string> <start> <end>)\nThe function returns the specified substring.\n"
        self.assertEqual(self.candidate(text),text)
        self.assertNotIn("MARKUP_OR_TRANSCRIPTION_REQUIRES_CONTEXT",self.propose(text)["reasons"])

    def test_a_complete_book_title_is_not_deleted_as_an_html_tag(self):
        text="저자는 책 <A Complete Title>을 출판하였다.\n"
        self.assertEqual(self.candidate(text),text)
        self.assertNotIn("MARKUP_OR_TRANSCRIPTION_REQUIRES_CONTEXT",self.propose(text)["reasons"])

    def test_unrelated_technical_word_does_not_release_bad_html(self):
        text="A preceding unrelated paragraph mentions HTML.\n\n<div>Incomplete article body.\n"
        self.assertIn("MARKUP_OR_TRANSCRIPTION_REQUIRES_CONTEXT",self.propose(text)["reasons"])

    def test_kind_intro_only_removes_empty_name_shell(self):
        text="BLT 샌드위치()는 샌드위치의 일종으로, 각각의 머리 글자를 따왔다.\n"
        self.assertEqual(self.candidate(text),text.replace("()",""))

    def test_prior_individual_hold_is_still_separate(self):
        text="<p>Ordinary source article.</p>\n"
        result=self.propose(text,previous_holds=["source-specific-review"])
        self.assertEqual(result["decision"],"PENDING")
        self.assertEqual(result["text"],text)


if __name__=="__main__":
    with patch.object(inherited,"policy",policy), \
            patch.object(inherited.inherited,"policy",policy), \
            patch.object(inherited.local_inherited,"policy",policy):
        suite=unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromModule(inherited.inherited),
            unittest.defaultTestLoader.loadTestsFromTestCase(inherited.local_inherited.LocalOptionalFields),
            unittest.defaultTestLoader.loadTestsFromTestCase(inherited.NamedContexts),
            unittest.defaultTestLoader.loadTestsFromTestCase(LiteralContext)])
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
