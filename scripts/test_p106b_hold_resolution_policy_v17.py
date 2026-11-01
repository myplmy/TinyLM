#!/usr/bin/env python3
"""Metadata evidence and literal-field regressions plus the frozen 201 tests."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v17 as policy
from scripts import test_p106b_hold_resolution_policy_v16 as inherited


class ExplicitMetadataAndFlatFields(unittest.TestCase):
    def value(self, text):
        return policy.propose(dict(id="expanded_train:17", text=text, complete_eos=True, valid_utf8=True))

    def test_life_pair_preserves_unknown_family_and_profession_values(self):
        text = "가람은 대한민국의 정치인이다.\n\n각주\n\n1900년 출생\n살아있는 사람\n일반경비 지도사\n김해 김씨\n"
        clean, changes, proven = policy.separate_metadata_suffix(text)
        self.assertTrue(proven)
        self.assertNotIn("각주", clean)
        self.assertIn("1900년 출생\n살아있는 사람\n일반경비 지도사\n김해 김씨", clean)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["metadata_values_deleted"], 0)

    def test_single_year_and_unknown_nouns_are_insufficient(self):
        text = "가람은 대한민국의 정치인이다.\n\n각주\n\n1900년 출생\n아직 구분할 수 없는 항목\n또 다른 명사\n"
        self.assertFalse(policy.separate_metadata_suffix(text)[2])

    def test_actual_reference_and_related_items_are_not_empty_footers(self):
        text = "가람은 대한민국의 정치인이다.\n\n참고 문헌\n자료 제목 — 저자, 1980\n\n같이 보기\n가람의 역사\n\n1900년 출생\n1980년 사망\n김해 김씨\n"
        clean, changes, proven = policy.separate_metadata_suffix(text)
        self.assertTrue(proven)
        self.assertEqual(clean, text)
        self.assertEqual(changes, [])

    def test_year_and_two_typed_categories_preserve_an_unknown_member(self):
        text = "가람은 대한민국의 가수이다.\n\n각주\n\n2001년 음반\n대한민국의 가수\n대한민국의 작곡가\n이름 그대로 남길 명목 항목\n"
        self.assertTrue(policy.separate_metadata_suffix(text)[2])

    def test_birth_conflict_is_never_released_by_extra_metadata(self):
        text = "가람(1900년 1월 1일 ~ 1980년 1월 1일)은 대한민국의 작가이다.\n\n각주\n\n1910년 출생\n1980년 사망\n김해 김씨\n"
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_mixed_sentence_is_not_a_nominal_metadata_boundary(self):
        text = "가람은 대한민국의 작가이다.\n\n각주\n\n1900년 출생\n1980년 사망\n그는 다른 나라에서 살았다.\n"
        self.assertFalse(policy.separate_metadata_suffix(text)[2])

    def test_code_example_is_not_a_metadata_suffix(self):
        text = "가람은 대한민국의 작가이다.\n\n```text\n각주\n\n1900년 출생\n1980년 사망\n김해 김씨\n```\n"
        self.assertFalse(policy.separate_metadata_suffix(text)[2])

    def test_new_proof_cannot_accept_an_automatically_deleted_paragraph(self):
        text = "가람은 대한민국의 작가이다.\n\n독립된 역사 설명이다.\n\n각주\n\n1900년 출생\n1980년 사망\n김해 김씨\n"
        old = dict(decision="PENDING", text=text, candidate=text.replace("독립된 역사 설명이다.", ""),
                   reasons=["APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT"],
                   changes=[dict(reason=policy.QUARANTINE, original="독립된 역사 설명이다.")])
        with patch.object(policy.previous, "propose", return_value=old):
            value = self.value(text)
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn("PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE", value["reasons"])

    def test_album_instrumental_predicate_recovers_only_empty_optional_alias(self):
        text = "《멈추었던 시계》()는 일본의 밴드 ZARD의 열 번째 정규 앨범으로, 2004년 1월 28일 발매되었다.\n"
        value = self.value(text)
        self.assertEqual(value["decision"], "EDIT", value)
        self.assertEqual(value["text"], text.replace("()", ""))

    def test_political_party_preserves_actual_abbreviation(self):
        text = "칠레 민주당(, PPD)은 칠레의 사회민주주의 정당으로 1987년 창당되었다.\n"
        value = self.value(text)
        self.assertEqual(value["decision"], "EDIT", value)
        self.assertIn("칠레 민주당(PPD)", value["text"])
        self.assertIn("1987년", value["text"])

    def sample(self, fields="", suffix=None):
        return "{{문화재 정보\n|이름=가람\n|소재지=서울특별시\n|수량=1점\n|그림=\n" + fields + "}}" + (suffix or "가람은 대한민국의 건축물이다.\n")

    def test_generic_flat_info_preserves_each_label_and_value(self):
        source = self.sample()
        flat = policy.flat_labelled_prefix(source)
        self.assertIsNotNone(flat)
        self.assertEqual(flat["populated"], ["이름=가람", "소재지=서울특별시", "수량=1점"])
        value = self.value(source)
        self.assertEqual(value["decision"], "EDIT", value)
        for record in flat["populated"]:
            self.assertIn(record, value["text"])
        self.assertTrue(policy.ordered_deletion(source, value["text"]))

    def test_flat_info_requires_the_actual_independent_subject(self):
        self.assertIsNone(policy.flat_labelled_prefix(self.sample(suffix="나래는 가람 근처의 건축물이다.\n")))

    def test_flat_info_rejects_nested_cells_and_duplicate_labels(self):
        for fields in ["|설명={{다른 틀}}\n", "|설명=값|다른 값\n", "|이름=나래\n"]:
            self.assertIsNone(policy.flat_labelled_prefix(self.sample(fields)))

    def test_flat_info_does_not_turn_a_syntax_tutorial_into_records(self):
        text = self.sample(suffix="가람은 위키 문법의 예제이다.\n")
        self.assertIsNone(policy.flat_labelled_prefix(text))

    def test_formula_and_missing_quantity_are_not_optional_name_aliases(self):
        for text in ["가람()은 함수이다.\n", "인구()는 도시의 인구 수이다.\n"]:
            self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_existing_football_helper_remains_a_narrow_public_helper(self):
        self.assertIsNone(policy.flat_football(self.sample()))

    def test_space_only_blocks_do_not_hide_empty_footers(self):
        text = "가람은 대한민국의 축구단이다.\n\n역대 성적\n\n참고 문헌\n \n\n \nK5리그 구단\nK6리그 구단\n1998년 설립된 축구단\n대한민국의 축구단\n"
        clean, changes, proven = policy.separate_metadata_suffix(text)
        self.assertTrue(proven)
        self.assertNotIn("참고 문헌", clean)
        self.assertNotIn("역대 성적", clean)
        self.assertIn("K5리그 구단\nK6리그 구단\n1998년 설립된 축구단", clean)
        value = self.value(text)
        self.assertNotIn("참고 문헌", value.get("candidate", value["text"]))
        self.assertNotIn("역대 성적", value.get("candidate", value["text"]))

    def test_same_year_different_explicit_birth_day_is_pending(self):
        text = "가람(大島, 1989.6.17~)는 일본의 작가이다.\n\n생년월일은 1989년 6월 7일이다.\n\n1989년 출생\n살아있는 사람\n김해 김씨\n"
        self.assertIn("DIFFERENT_EXPLICIT_BIRTH_DATES_REQUIRE_SOURCE_CONTEXT", policy.literal_holes(text))
        self.assertEqual(self.value(text)["decision"], "PENDING")

    def test_same_year_different_explicit_death_day_is_pending(self):
        text = "가람(1928년 11월 20일 ~ 2010년 3월 16일)은 대한민국의 기업인이다.\n\n사망\n2010년 3월 18일 병원에서 타계하였다.\n"
        self.assertIn("DIFFERENT_EXPLICIT_DEATH_DATES_REQUIRE_SOURCE_CONTEXT", policy.literal_holes(text))

    def test_explicit_different_calendars_are_not_silently_conflated(self):
        text = "가람(음력 1928년 11월 20일 ~ 2010년 3월 16일)은 대한민국의 기업인이다.\n\n생년월일은 양력 1928년 12월 1일이다.\n"
        self.assertNotIn("DIFFERENT_EXPLICIT_BIRTH_DATES_REQUIRE_SOURCE_CONTEXT", policy.literal_holes(text))

    def test_empty_family_labels_do_not_pass_as_filled_values(self):
        text = "가람은 대한민국의 정치인이다.\n\n가족\n아버지: 나래\n여동생:\n부인:\n장남: 다람(1933년 - )\n차남:\n딸: ?(1937년 - )\n"
        self.assertIn("EMPTY_FAMILY_RELATION_VALUE_REQUIRES_SOURCE_CONTEXT", policy.literal_holes(text))

    def test_filled_next_line_and_literal_unknown_family_values_are_preserved(self):
        text = "가람은 대한민국의 정치인이다.\n\n가족\n부인:\n나래\n딸: ?(1937년 - )\n"
        self.assertNotIn("EMPTY_FAMILY_RELATION_VALUE_REQUIRES_SOURCE_CONTEXT", policy.literal_holes(text))

    def test_missing_announced_quote_and_its_dependent_stay_pending(self):
        text = "가람은 대한민국의 작가이다.\n\n구니는 이렇게 말한다.\n\n이 말은 오싱에게 영향을 준다.\n"
        self.assertIn("MISSING_ANNOUNCED_QUOTATION_AND_EXPLICIT_DEPENDENT", policy.literal_holes(text))

    def test_actual_quote_is_not_an_empty_announced_quote(self):
        text = '가람은 대한민국의 작가이다.\n\n구니는 이렇게 말한다.\n\n"스스로 배워야 한다."\n\n이 말은 오싱에게 영향을 준다.\n'
        self.assertNotIn("MISSING_ANNOUNCED_QUOTATION_AND_EXPLICIT_DEPENDENT", policy.literal_holes(text))

    def test_unfilled_software_section_is_not_a_populated_parent(self):
        text = "가람은 일본의 영화이다.\n\n수록 소프트\n\n기타\n노래의 실제 제목\n"
        self.assertIn("UNFILLED_OPTIONAL_LEAF_SECTION_REQUIRES_SOURCE_CONTEXT", policy.literal_holes(text))

    def test_unfilled_plot_does_not_borrow_a_populated_cast_section(self):
        text = "가람은 일본의 영화이다.\n\n줄거리\n\n배역\n\n영어\n나래\n"
        self.assertIn("UNFILLED_PLOT_SECTION_BEFORE_POPULATED_CAST_REQUIRES_SOURCE_CONTEXT", policy.literal_holes(text))

    def test_unnamed_album_release_is_still_a_complete_source_statement(self):
        text = '가람은 브라질의 싱어송라이터이다. 2016년 첫 라이브 앨범 을 발매했다.\n\n두 번째 앨범 <i id="mwDw">Realidade</i> 는 2017년에 발매되었다.\n'
        value = self.value(text)
        clean = value.get("candidate", value["text"])
        self.assertIn("2016년 첫 라이브 앨범 을 발매했다.", clean)
        self.assertIn("Realidade", clean)

    def test_list_source_does_not_supply_the_absent_credit_list(self):
        text = "가람은 대한민국의 음반이다.\n\n참여\n이 목록은 해당 앨범의 부클릿 〈staff〉목록에서 발췌하였다.\n\n1994년 음반\n대한민국의 음반\n"
        self.assertIn("ANNOUNCED_LIST_SOURCE_WITHOUT_LIST_BEFORE_METADATA", policy.literal_holes(text))

    def test_populated_credit_list_is_preserved(self):
        text = "가람은 대한민국의 음반이다.\n\n참여\n이 목록은 해당 앨범의 부클릿 〈staff〉목록에서 발췌하였다.\n가람: 보컬\n나래: 기타\n\n1994년 음반\n대한민국의 음반\n"
        self.assertNotIn("ANNOUNCED_LIST_SOURCE_WITHOUT_LIST_BEFORE_METADATA", policy.literal_holes(text))

    def test_empty_chart_children_before_metadata_do_not_keep_an_empty_parent(self):
        text = '"Step Up"은 대한민국의 그룹 미스에이의 두 번째 싱글 음반으로, 2010년 9월 27일 발매되었다.\n\n활동 사항\n"Breathe"는 10월 21일 차트에서 1위를 수상하였다.\n\n수록 곡 목록\n\n차트 성과\n\n주간 차트\n\n연말 차트\n\n카카오엔터테인먼트의 음반\n대한민국의 팝 음반\n한국어 음반\n2010년 싱글\n2010년 음반\n미쓰에이의 음반\n'
        value = self.value(text)
        clean = value.get("candidate", value["text"])
        for title in ["수록 곡 목록", "차트 성과", "주간 차트", "연말 차트"]:
            self.assertNotIn(title, clean)
        self.assertIn('"Breathe"는 10월 21일 차트에서 1위를 수상하였다.', clean)
        self.assertIn("2010년 싱글\n2010년 음반\n미쓰에이의 음반", clean)


if __name__ == "__main__":
    v16, v15 = inherited, inherited.inherited
    v14, v13 = v15.inherited, v15.inherited.inherited
    v12, v11 = v13.inherited, v13.inherited.inherited
    v10, v9 = v11.inherited, v11.inherited.inherited
    v8, v7 = v9.inherited, v9.inherited.inherited
    modules = [v16, v15, v14, v13, v12, v11, v10, v9, v8, v7, v7.inherited, v7.local_inherited]
    classes = [v7.local_inherited.LocalOptionalFields, v7.NamedContexts, v8.LiteralContext,
               v9.LocalFieldsAndPremises, v10.LiteralDamageBoundaries, v11.ObservedTailContexts,
               v12.NamedSourcesAndSubjects, v13.SourceValuePreservation, v14.FlatFieldsAndTenure,
               v15.ScheduleAndNestedAliases, v16.SeparateMetadataAndLiteralHoles, ExplicitMetadataAndFlatFields]
    with ExitStack() as stack:
        for module in modules:
            stack.enter_context(patch.object(module, "policy", policy))
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(v7.inherited),
                                   *(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in classes)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
