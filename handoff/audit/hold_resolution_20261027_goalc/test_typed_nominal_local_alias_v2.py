"""The observed chemical-name false positive must not become a general proof."""
from pathlib import Path
import importlib.util
import unittest

spec = importlib.util.spec_from_file_location('nominal_alias_v2', Path(__file__).with_name('typed_nominal_local_alias_v2.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class PredicateRoleCounterexamples(unittest.TestCase):
    def test_actual_chemical_object_is_not_a_mountain_role(self):
        source = '아이소프로필말산()은 류신의 생합성 과정의 대사 중간생성물로, 효소에 의해 옥소아이소발레르산으로부터 합성된다.'
        self.assertIsNotNone(helper.previous.prove(source))
        self.assertIsNone(helper.prove(source))

    def test_even_a_complete_acid_role_is_not_geography(self):
        self.assertIsNone(helper.prove('사과산()은 여러 식물에 있는 유기산이다.'))

    def test_an_object_city_is_not_the_subject_role(self):
        self.assertIsNone(helper.prove('새 이름()는 이름을 가리키며, 그 뒤에 도시가 있다.'))

    def test_actual_geographic_mountain_retains_height(self):
        source = '구병산()은 보은군에 위치한 높이 876m의 산이다.'
        self.assertEqual(helper.prove(source)['candidate'], source.replace('()', ''))

    def test_actual_geographic_river_is_retained(self):
        self.assertIsNotNone(helper.prove('이름강()은 어느 나라를 흐르는 강이다.'))

    def test_geographic_context_can_have_actual_tab_whitespace(self):
        self.assertIsNotNone(helper.prove('가산()은 충청도\t동쪽의 산이다.'))

    def test_actual_college_role_is_still_admissible_as_a_proof_candidate(self):
        self.assertIsNotNone(helper.prove('학교 이름()는 패서디나에 있는 공립 커뮤니티 칼리지이며 1924년에 문을 열었다.'))

    def test_a_second_missing_field_still_vetoes_the_proof(self):
        self.assertIsNone(helper.prove('학교 이름()는 어느 도시의 학교이다. 옛 이름()도 있었다.'))


if __name__ == '__main__':
    unittest.main()
