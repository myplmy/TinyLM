"""Counterexamples for saved authored empty-section deltas."""
from pathlib import Path
import sys
import unittest

AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(AUDIT), str(AUDIT.parents[2])]
from authored_empty_section_literal_v1 import mask_empty_sections, preservation

NL = chr(10)


class EmptySectionTests(unittest.TestCase):
    def test_empty_population_before_see_also_keeps_filled_values(self):
        source = 'A섬 인구는 123명이다.' + NL*2 + '인구' + NL*2 + '같이 보기' + NL + 'B섬'
        body = source.replace('인구' + NL*2, '', 1)
        self.assertTrue(preservation(source, body)['eligible_narrow_literal_delta'])

    def test_populated_population_cannot_be_removed(self):
        source = 'A섬이다.' + NL*2 + '인구' + NL + '123명이다.' + NL*2 + '같이 보기' + NL + 'B섬'
        body = source.replace('인구' + NL + '123명이다.' + NL*2, '')
        self.assertFalse(preservation(source, body)['eligible_narrow_literal_delta'])

    def test_heading_word_inside_sentence_is_not_a_section(self):
        source = '인구는 줄었지만 이 조건에서는 증가할 수 있다.' + NL*2 + '각주'
        body = source.replace('인구', '')
        self.assertFalse(preservation(source, body)['eligible_narrow_literal_delta'])

    def test_unproved_death_and_unknown_heading_are_not_waived(self):
        for label in ['사망', '평가', '임의 절']:
            source = '1436년에 태어났다.' + NL*2 + label
            self.assertFalse(preservation(source, '1436년에 태어났다.')['eligible_narrow_literal_delta'])

    def test_filled_external_links_cannot_be_removed(self):
        source = 'A섬이다.' + NL*2 + '외부 링크' + NL + 'A섬 공식 홈페이지'
        self.assertFalse(preservation(source, 'A섬이다.')['eligible_narrow_literal_delta'])

    def test_code_quote_list_and_transcription_are_not_masked(self):
        for value in ['```'+NL+'인구'+NL*2+'각주'+NL+'```', '> 인구'+NL*2+'각주',
                      '* 인구'+NL*2+'각주', '    인구'+NL*2+'각주']:
            _, removed = mask_empty_sections(value)
            self.assertNotIn('인구', [row['label'] for row in removed])

    def test_missing_numeric_value_is_never_accepted(self):
        source = 'A섬 인구는 123명이다.' + NL*2 + '인구' + NL*2 + '각주'
        body = 'A섬 인구는 명이다.'
        self.assertFalse(preservation(source, body)['eligible_narrow_literal_delta'])

    def test_content_heading_at_eof_needs_more_evidence(self):
        for label in ['인구', '기후', '갤러리', '사진']:
            source = 'A섬이다.' + NL*2 + label
            self.assertFalse(preservation(source, 'A섬이다.')['eligible_narrow_literal_delta'])

    def test_relation_condition_and_negation_are_preserved(self):
        source = 'A가 B이면 C가 아니며 가능성이 있다.' + NL*2 + '인구' + NL*2 + '각주'
        self.assertFalse(preservation(source, 'A가 B이면 C이며 확실하다.')['eligible_narrow_literal_delta'])


if __name__ == '__main__':
    unittest.main()
