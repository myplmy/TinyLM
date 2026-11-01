#!/usr/bin/env python3
"""Meaningful positive/negative source-structure and local-context counters."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_structure_v1 as structure


class ActualRepetitionContexts(unittest.TestCase):
    def test_different_inline_program_values_are_not_full_line_copies(self):
        text = "DISPLAY `Content-type: text/html`.\nDISPLAY `<HTML><BODY>`.\nDISPLAY `</BODY></HTML>`.\n"
        self.assertTrue(structure.actual_repeat_contexts(text))

    def test_repeated_unscoped_prose_is_still_unproved(self):
        self.assertFalse(structure.actual_repeat_contexts("같은 사건을 설명한 문장이다.\n같은 사건을 설명한 문장이다.\n"))

    def test_same_credit_belongs_to_two_actual_track_names(self):
        text = "수록곡\nDisc1\nFirst Song\n가: Singer\n작사: Person\nSecond Song\n가: Singer\n작사: Person\n"
        self.assertTrue(structure.actual_repeat_contexts(text))

    def test_two_copies_inside_one_track_do_not_gain_a_new_context(self):
        self.assertFalse(structure.actual_repeat_contexts("수록곡\nFirst Song\n작사: Person\n작사: Person\n"))

    def test_cast_role_is_tied_to_different_populated_character_actor_records(self):
        text = "등장 인물\n미즈노: 배우가\n고등학교 학생.\n다카시: 배우나\n고등학교 학생.\n"
        self.assertTrue(structure.actual_repeat_contexts(text))

    def test_repeated_role_under_the_same_person_is_not_proved(self):
        self.assertFalse(structure.actual_repeat_contexts("등장 인물\n미즈노: 배우가\n고등학교 학생.\n고등학교 학생.\n"))

    def test_comments_for_actual_distinct_expressions_remain(self):
        text = "//숫자를 문자열로\nstring = StringFromNumber(number);\n//숫자를 문자열로\nstring = number.StringValue();\n"
        self.assertTrue(structure.actual_repeat_contexts(text))

    def test_two_identical_comment_expression_blocks_are_not_excused(self):
        block = "//숫자를 문자열로\nstring = number.StringValue();\n"
        self.assertFalse(structure.actual_repeat_contexts(block + block))


class CompleteStructuredBodies(unittest.TestCase):
    def test_valid_python_is_parsed_without_execution(self):
        self.assertTrue(structure.complete_fenced_code_body("```python\ndef greet():\n    return 'hello'\n```\n"))

    def test_missing_definition_name_is_not_a_complete_code_body(self):
        self.assertFalse(structure.complete_fenced_code_body("```python\ndef\n```\n"))

    def test_unclosed_fence_and_extra_unexplained_fragment_are_rejected(self):
        self.assertFalse(structure.complete_fenced_code_body("```python\nx = 1\n"))
        self.assertFalse(structure.complete_fenced_code_body("fragment\n```python\nx = 1\n```\n"))

    def test_json_structure_is_parsed_without_running_source_commands(self):
        self.assertTrue(structure.complete_fenced_code_body('```json\n{"command": "do not execute"}\n```\n'))

    def test_braced_source_function_may_contain_brace_characters_in_strings(self):
        self.assertTrue(structure.complete_fenced_code_body('```c\nint main() { printf("{"); return 0; }\n```\n'))

    def test_a_missing_function_body_close_is_not_complete(self):
        self.assertFalse(structure.complete_fenced_code_body("```c\nint main() { return 0;\n```\n"))

    def test_filled_markdown_rows_keep_their_explicit_header_relations(self):
        self.assertTrue(structure.complete_markdown_table_body("|이름|값|\n|---|---|\n|가|1|\n"))
        self.assertFalse(structure.complete_markdown_table_body("|이름|값|\n|---|---|\n|가||\n"))


class SourceWikiAndStyle(unittest.TestCase):
    def test_filled_rectangular_wiki_table_and_original_values_are_retained(self):
        text = '{| class="wikitable"\n! 이름 !! 값\n|-\n| 가 || 1\n|-\n| 나 || 2\n|}\n'
        self.assertTrue(structure.complete_wiki_tables_cover_markup(text))

    def test_missing_cell_different_width_and_unclosed_table_are_rejected(self):
        for text in ["{|\n! 이름 !! 값\n|-\n| 가 ||\n|}\n", "{|\n! 이름 !! 값\n|-\n| 가\n|}\n", "{|\n! 이름\n|-\n| 가\n"]:
            self.assertFalse(structure.complete_wiki_tables_cover_markup(text))

    def test_filled_attributes_do_not_make_an_empty_header_populated(self):
        text = '{|\n! style="color:red"| !! 값\n|-\n| 가 || 1\n|}\n'
        self.assertFalse(structure.complete_wiki_tables_cover_markup(text))

    def test_other_unclosed_markup_outside_a_valid_table_is_not_hidden(self):
        table = "{|\n! 이름\n|-\n| 가\n|}\n"
        self.assertFalse(structure.complete_wiki_tables_cover_markup(table + "{{미완\n"))

    def test_rowspan_or_unfilled_link_does_not_obtain_a_rectangular_proof(self):
        for text in ['{|\n! 이름\n|-\n| rowspan="2"|가\n|}\n', "{|\n! 이름\n|-\n| [[가|]]\n|}\n"]:
            self.assertFalse(structure.complete_wiki_tables_cover_markup(text))

    def test_source_color_and_emphasis_are_not_discarded(self):
        self.assertTrue(structure.complete_semantic_inline_markup('<span style="color:red"><b>조건</b></span>'))

    def test_unclosed_crossed_or_empty_emphasis_is_not_complete(self):
        for text in ["<b>조건", "<b><i>조건</b></i>", "<i></i>", "<b>조건</b><span"]:
            self.assertFalse(structure.complete_semantic_inline_markup(text))

    def test_page_widget_or_event_handler_attributes_are_not_semantic_style(self):
        self.assertFalse(structure.complete_semantic_inline_markup('<span onclick="run()">조건</span>'))
        self.assertFalse(structure.complete_semantic_inline_markup('<span style="display:none">조건</span>'))

    def test_a_sports_legend_is_not_filled_by_an_unrelated_prose_number(self):
        text = '연도별 투수 성적\n굵은 글씨는 시즌 최고 성적, <span\nstyle="color:red">붉은색 글씨</span>는 역대 최고 성적.\n2000이닝 이상인 투수는 4명이다.\n'
        self.assertTrue(structure.unbound_source_record_legend(text))

    def test_an_actual_season_value_row_can_support_its_legend(self):
        text = '연도별 투수 성적\n굵은 글씨는 시즌 최고 성적.\n1957 42 11 1.06\n'
        self.assertFalse(structure.unbound_source_record_legend(text))

    def test_another_sections_values_cannot_fill_a_missing_record_table(self):
        text = '연도별 투수 성적\n굵은 글씨는 시즌 최고 성적.\n같이 보기\n1957 42 11 1.06\n'
        self.assertTrue(structure.unbound_source_record_legend(text))

    def test_a_route_color_item_is_not_a_missing_sports_record_table(self):
        text = '운행 노선\n<span style="color:red">●</span> 5번: 항구 ~ 역\n'
        self.assertFalse(structure.unbound_source_record_legend(text))


if __name__ == "__main__":
    unittest.main(verbosity=2)
