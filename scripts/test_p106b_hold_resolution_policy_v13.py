#!/usr/bin/env python3
"""Date-word, mixed-clause and source colour regressions after real readback."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v13 as policy
from scripts import test_p106b_hold_resolution_policy_v12 as inherited


class SourceValuePreservation(unittest.TestCase):
    def value(self, text):
        return policy.propose(dict(id="expanded_train:13", text=text, complete_eos=True, valid_utf8=True))

    def clean(self, text):
        value = self.value(text)
        return value.get("candidate", value["text"])

    def test_unknown_birth_date_word_never_deletes_family_history(self):
        text = "가람은 조선의 문신이다.\n\n가계 배경\n가람의 정확한 생년월일은 미상이다. 아버지는 윤승순이고 어머니는 단양이씨이다.\n\n역사\n가람은 윤관의 후손이다.\n"
        clean = self.clean(text)
        for sentence in ["생년월일은 미상이다.", "아버지는 윤승순", "어머니는 단양이씨"]:
            self.assertIn(sentence, clean)

    def test_a_real_empty_date_with_separate_units_is_still_a_hole(self):
        text = "가람은 사이트이다.\n년 월 일 기준으로 총 개의 항목이 있다.\n"
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_a_complete_sentence_sharing_a_damaged_paragraph_cannot_disappear(self):
        text = "가람은 수학적 개념이다.\n\n값은 . 가람은 1900년에 처음 소개되었다.\n\n역사\n가람은 오랜 역사를 가진 개념이다.\n"
        clean = self.clean(text)
        self.assertIn("가람은 1900년에 처음 소개되었다.", clean)
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_colour_is_a_value_even_when_a_plain_bullet_remains(self):
        source = '<span style="color:#6EBF46;">●</span> 5번: 항구 ~ 역\n'
        clean = '● 5번: 항구 ~ 역\n'
        self.assertFalse(policy.semantic_style_preserved(source, clean))
        self.assertTrue(policy.semantic_style_preserved(source, source))

    def test_same_colour_count_on_a_different_item_is_rejected(self):
        source = '<span style="color:green;">5번</span>\n10번\n'
        clean = '5번\n<span style="color:green;">10번</span>\n'
        self.assertFalse(policy.semantic_style_preserved(source, clean))

    def test_source_declared_bold_score_cannot_be_flattened(self):
        source = '굵은 글씨는 최고 성적이다.\n<b>20</b>\n'
        self.assertFalse(policy.semantic_style_preserved(source, source.replace('<b>', '').replace('</b>', '')))

    def test_unstyled_balanced_div_can_still_be_rendered(self):
        source = '<div>A literal decomposed vowel e\u0301 remains here.</div>\n'
        self.assertNotIn('<div>', self.clean(source))
        self.assertIn('e\u0301', self.clean(source))

    def test_lost_route_colour_keeps_the_proposal_pending(self):
        source = '가람여객은 대한민국의 버스 회사이다.\n\n운행 노선\n<span style="color:#6EBF46;">●</span> 5번: 항구 ~ 역\n'
        value = self.value(source)
        self.assertEqual(value['decision'], 'PENDING')
        self.assertIn('SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION', value['reasons'])


if __name__ == '__main__':
    v11 = inherited.inherited
    v10 = v11.inherited
    v9 = v10.inherited
    v8 = v9.inherited
    v7 = v8.inherited
    modules = [inherited, v11, v10, v9, v8, v7, v7.inherited, v7.local_inherited]
    with ExitStack() as stack:
        for module in modules:
            stack.enter_context(patch.object(module, 'policy', policy))
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromModule(v7.inherited),
            unittest.defaultTestLoader.loadTestsFromTestCase(v7.local_inherited.LocalOptionalFields),
            unittest.defaultTestLoader.loadTestsFromTestCase(v7.NamedContexts),
            unittest.defaultTestLoader.loadTestsFromTestCase(v8.LiteralContext),
            unittest.defaultTestLoader.loadTestsFromTestCase(v9.LocalFieldsAndPremises),
            unittest.defaultTestLoader.loadTestsFromTestCase(v10.LiteralDamageBoundaries),
            unittest.defaultTestLoader.loadTestsFromTestCase(v11.ObservedTailContexts),
            unittest.defaultTestLoader.loadTestsFromTestCase(inherited.NamedSourcesAndSubjects),
            unittest.defaultTestLoader.loadTestsFromTestCase(SourceValuePreservation)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
