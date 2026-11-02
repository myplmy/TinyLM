"""Counterexamples for source-role alias proof; no corpus files are opened."""
from pathlib import Path
import importlib.util
import unittest

spec = importlib.util.spec_from_file_location('nominal_alias', Path(__file__).with_name('typed_nominal_local_alias_v1.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class NarrowLeadAlias(unittest.TestCase):
    def test_actual_college_pattern_preserves_every_populated_value(self):
        source = '패서디나 시티 칼리지()는 미국 캘리포니아주 패서디나에 있는 공립 커뮤니티 칼리지이며 1924년에 문을 열었다.\n\n역사\n1928년부터 1953년까지 운영했다.'
        result = helper.prove(source)
        self.assertIsNotNone(result)
        self.assertEqual(result['candidate'], source.replace('칼리지()', '칼리지', 1))

    def test_literal_title_and_release_are_retained(self):
        source = '〈곡 이름〉()는 한 가수의 싱글이다. 2004년 8월 11일에 발매됐다.'
        self.assertEqual(helper.prove(source)['candidate'], source.replace('()', '', 1))

    def test_mathematical_definition_is_not_optional_alias(self):
        self.assertIsNone(helper.prove('육차 방정식()은 최고차항의 차수가 6인 다항 방정식이다.'))

    def test_empty_call_is_not_a_named_subject(self):
        self.assertIsNone(helper.prove('run()은 게임을 시작하는 함수이다.'))

    def test_missing_second_slot_vetoes(self):
        self.assertIsNone(helper.prove('어떤 영화()는 일본의 영화이다. 주인공()도 등장한다.'))

    def test_glyph_teaching_is_not_a_nominal_alias(self):
        self.assertIsNone(helper.prove('문자 이름()는 섬의 발음과 유니코드 기호를 설명하는 문자이다.'))

    def test_quoted_source_is_preserved(self):
        self.assertIsNone(helper.prove('“영화 이름()는 일본의 영화이다.”'))
        self.assertIsNone(helper.prove('영화 이름()는 일본의 영화이다. 인용 문구이다.'))

    def test_a_named_entity_elsewhere_is_not_the_subject_role(self):
        self.assertIsNone(helper.prove('도시 이름()는 아직 정해지지 않았다. 다른 도시의 강을 언급했다.'))

    def test_unfilled_alias_after_the_subject_is_not_the_lead_slot(self):
        self.assertIsNone(helper.prove('도시 이름은 옛 별칭()로 불리는 도시이다.'))

    def test_incomplete_first_paragraph_is_not_admitted(self):
        self.assertIsNone(helper.prove('도시 이름()는 이름이 주어진 도시이며'))

    def test_filled_alias_is_never_deleted(self):
        self.assertIsNone(helper.prove('도시 이름(Actual Name)은 섬에 있는 도시이다.'))

    def test_unbound_typed_word_is_not_a_filled_role(self):
        self.assertIsNone(helper.prove('대상()은 “영화”라는 말 뒤의 이름이 사라졌다.'))


if __name__ == '__main__':
    unittest.main()
