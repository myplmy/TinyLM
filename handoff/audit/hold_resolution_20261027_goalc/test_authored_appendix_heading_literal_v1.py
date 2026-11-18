"""Reject value loss, code edits and confusion between body and appendix labels."""
import unittest
from pathlib import Path
import sys
AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(AUDIT), str(AUDIT.parents[2])]
from authored_appendix_heading_literal_v1 import mask, possible, preservation

INTRO = '이 문서는 실제로 확인된 본문과 참고 자료의 관계를 설명하는 완결된 문장이다.\n\n'


class AppendixLabelTests(unittest.TestCase):
    def test_populated_reference_values_retained(self):
        source = INTRO + '참고 문헌\n\n홍길동. 자료 12. 2015.\n'
        final = mask(source)[0]
        self.assertIn('홍길동. 자료 12. 2015.', final)
        self.assertTrue(all(preservation(source, final)['guards'].values()))

    def test_reference_value_loss_rejected(self):
        source = INTRO + '참고 문헌\n\n홍길동. 자료 12. 2015.\n'
        self.assertFalse(possible(source, INTRO))

    def test_negation_not_a_heading(self):
        source = INTRO + '결과는 항상 참인 것은 아니다.\n'
        self.assertFalse(possible(source, INTRO + '결과는 항상 참이다.\n'))

    def test_code_label_untouched(self):
        source = INTRO + '```text\n\n각주\n```\n'
        self.assertEqual(mask(source)[0], source)

    def test_article_title_untouched(self):
        source = '각주\n\n각주는 문서에서 보충 설명을 제공하는 것이다.\n'
        self.assertEqual(mask(source)[0], source)

    def test_inline_words_untouched(self):
        source = INTRO + '이 책의 제목은 참고 문헌이라고 적혀 있다.\n'
        self.assertEqual(mask(source)[0], source)

    def test_populated_content_heading_untouched(self):
        source = INTRO + '자녀\n\n실제 이름과 2001년 출생이라는 관계가 있다.\n'
        self.assertEqual(mask(source)[0], source)

    def test_numeric_change_rejected(self):
        source = INTRO + '외부 링크\n\n통계 1998년 17건\n'
        self.assertFalse(possible(source, mask(source)[0].replace('17건', '19건')))

    def test_reordered_values_rejected(self):
        source = INTRO + '참고 문헌\n\nFirst author\nSecond author\n'
        self.assertFalse(possible(source, INTRO + 'Second author\nFirst author\n'))


if __name__ == '__main__':
    unittest.main()
