"""Empty labels may disappear; populated results, code and note values may not."""
import unittest
from root_empty_section_contract_v3 import mask, possible, preservation


class EmptySections(unittest.TestCase):
    def test_empty_rating_before_notes(self):
        source = '설명이다.\n\n평가\n\n각주\n\n프랑스의 학자\n프랑스의 수학자\n'
        body = '설명이다.\n\n프랑스의 학자\n프랑스의 수학자\n'
        self.assertTrue(possible(source, body))
        self.assertTrue(all(preservation(source, body)['guards'].values()))

    def test_populated_rating_stays(self):
        source = '설명이다.\n\n평가\n\n평점 90점이다.\n\n각주\n'
        self.assertIn('평가', mask(source)[0])
        self.assertFalse(possible(source, '설명이다.'))

    def test_filled_children_not_removed(self):
        source = '설명이다.\n\n자녀\n\n딸 두 명이다.\n\n각주\n'
        self.assertIn('자녀', mask(source)[0])
        self.assertIn('딸 두 명이다.', mask(source)[0])

    def test_fenced_label_is_code(self):
        source = '설명이다.\n\n```text\n평가\n\n각주\n```\n'
        self.assertEqual(source, mask(source)[0])

    def test_orphan_legend_is_not_empty_label(self):
        source = '설명이다.\n\n관직 역임 약력\n※ 날짜는 대부분 음력입니다.\n'
        self.assertEqual(source, mask(source)[0])

    def test_eof_gallery_with_independent_prefix(self):
        source = '독립적으로 완결된 설명이다.\n\n갤러리\n'
        self.assertNotIn('갤러리', mask(source)[0])

    def test_literal_year_medium_platform_footer(self):
        source = '루이지 맨션은 게임이다.\n\n평가\n\n각주\n\n2001년 비디오 게임\n게임큐브 게임\n닌텐도 3DS 게임\n'
        body = '루이지 맨션은 게임이다.\n\n2001년 비디오 게임\n게임큐브 게임\n닌텐도 3DS 게임\n'
        self.assertTrue(possible(source, body))
        self.assertTrue(all(preservation(source, body)['guards'].values()))

    def test_bibliography_is_not_a_game_category_footer(self):
        source = '설명이다.\n\n참고 문헌\n\n저자 2001, 책 제목\n다른 저자 2010, 책 제목\n'
        self.assertIn('참고 문헌', mask(source)[0])


if __name__ == '__main__':
    unittest.main()
