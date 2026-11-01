#!/usr/bin/env python3
"""Source-derived v2 regressions and retained first-version counterexamples."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v2 as policy
from scripts import test_p106b_hold_resolution_policy as prior_tests


class RetainedDraftGuards(prior_tests.DraftPolicyTests):
    def setUp(self):
        change = patch.object(prior_tests, "policy", policy)
        change.start()
        self.addCleanup(change.stop)


class NewSourceShapes(unittest.TestCase):
    def propose(self, text, **kwargs):
        row = dict(id="expanded_train:1", text=text, complete_eos=True, valid_utf8=True)
        row.update(kwargs)
        return policy.propose(row)

    def test_populated_chinese_name_is_preserved_while_empty_slot_disappears(self):
        text = "국민회의(國民會議, )는 자문위원회이다.\n"
        value = self.propose(text)
        self.assertEqual(value["decision"], "EDIT")
        self.assertEqual(value["text"], "국민회의(國民會議)는 자문위원회이다.\n")

    def test_filled_route_abbreviation_survives_leading_empty_alias(self):
        value = self.propose("도시철도 1호선(, L1)은 철도 노선이다.\n")
        self.assertEqual(value["text"], "도시철도 1호선(L1)은 철도 노선이다.\n")

    def test_later_explicit_nickname_empty_translation_is_not_a_formula(self):
        text = "가람은 일본의 기수이다.\n\n경마 팬들에게 명수()란 애칭으로 알려졌다.\n"
        value = self.propose(text)
        self.assertEqual(value["decision"], "EDIT")
        self.assertIn("명수란 애칭", value["text"])

    def test_all_populated_aliases_are_byte_identical(self):
        text = "가람(John,  Smith)은 작가이다.\n"
        self.assertEqual(self.propose(text)["text"], text)

    def test_literal_function_call_is_not_a_missing_field(self):
        text = "Python examples call helper().\n"
        value = self.propose(text)
        self.assertEqual(value["decision"], "KEEP")
        self.assertEqual(value["text"], text)

    def test_nameless_value_is_not_released_by_programming_keyword(self):
        self.assertEqual(self.propose("Python input has value ().\n")["decision"], "PENDING")

    def test_unknown_category_words_do_not_hide_both_explicit_biographical_anchors(self):
        text = "김가람은 일본의 전 축구 선수이다.\n외부 링크\n1983년 출생\n살아있는 사람\n남자 축구 수비수\n20세기 일본 사람\n"
        value = self.propose(text)
        self.assertEqual(value["decision"], "EDIT")
        self.assertNotIn("외부 링크", value["text"])
        self.assertIn("남자 축구 수비수\n20세기 일본 사람", value["text"])

    def test_real_social_link_labels_and_categories_all_survive(self):
        text = "김가람은 스웨덴의 가수이다.\n외부 링크\n김가람 - 인스타그램\n김가람 - 트위터\n1973년 출생\n살아있는 사람\n스웨덴의 여자 싱어송라이터\n"
        value = self.propose(text)
        self.assertEqual(value["decision"], "KEEP")
        self.assertEqual(value["text"], text)

    def test_latin_album_title_with_korean_intro_and_explicit_album_categories(self):
        text = "《Reunion》는 1998년에 발매된 음반이다.\n곡 목록\n인증\n평가\n각주\n1998년 라이브 음반\n블랙 사바스의 라이브 음반\n"
        value = self.propose(text)
        self.assertEqual(value["decision"], "EDIT")
        self.assertNotIn("각주", value["text"])
        self.assertIn("1998년 라이브 음반", value["text"])

    def test_year_only_birth_and_full_death_date_are_not_conflicting_birth_years(self):
        text = "김가람(1900년 ~ 1980년 3월 4일)은 작가이다.\n1900년 출생\n1980년 사망\n"
        value = self.propose(text)
        self.assertEqual(value["decision"], "KEEP")
        self.assertEqual(value["text"], text)

    def test_unknown_birth_side_cannot_borrow_a_known_death_year(self):
        text = "김가람(? ~ 1980년 3월 4일)은 작가이다.\n1900년 출생\n"
        self.assertEqual(self.propose(text)["decision"], "PENDING")

    def test_remaining_measured_quantity_is_not_a_ready_document(self):
        value = self.propose("이 물건은 금속 제품이다. 평균 의 발사 속도를 보였다.\n")
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn("OBSERVED_MISSING_MEASURED_QUANTITY", value["reasons"])

    def test_legend_requires_value_context_even_if_its_words_are_unchanged(self):
        text = "이것은 방송 프로그램이다.\n아래의 파란색 숫자는 최저 시청률이고 빨간색 숫자는 최고 시청률입니다.\n"
        self.assertEqual(self.propose(text)["decision"], "PENDING")

    def test_local_missing_plot_is_retained_for_context_review(self):
        text = "가람은 도시이다.\n역사적 인구는 다음 도표에 나와 있다.\n국가중요문화재\n유적이 있다.\n"
        value = self.propose(text)
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn("LOCAL_FIGURE_OR_TABLE_TARGET_NEEDS_CONTEXT", value["reasons"])

    def test_span_level_prior_hold_needs_root_evidence_even_when_plaintext_looks_clean(self):
        value = self.propose("가람은 도시이다.\n", previous_holds=[dict(reason="prior source-span review")])
        self.assertEqual(value["decision"], "PENDING")


if __name__ == "__main__":
    unittest.main()
