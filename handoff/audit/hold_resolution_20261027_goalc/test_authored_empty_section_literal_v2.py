"""Empty neighboring sections must not authorize populated or quoted deletions."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import authored_empty_section_literal_v2 as current


class GeographyEmptySectionTests(unittest.TestCase):
    def test_empty_population_before_transport_is_proved(self):
        a='오이정은 정이다.'+chr(10)*2+'인구'+chr(10)*2+'교통'+chr(10)*2+'철도'+chr(10)+'고텐바 선'
        b=a.replace('인구'+chr(10)*2,'')
        self.assertTrue(current.preservation(a,b)['eligible_narrow_literal_delta'])

    def test_empty_population_and_climate_chain_is_proved(self):
        a='마을 설명'+chr(10)*2+'인구'+chr(10)*2+'기후'+chr(10)*2+'교통'+chr(10)*2+'도로'+chr(10)+'국도 7호선'
        b=a.replace('인구'+chr(10)*2,'').replace('기후'+chr(10)*2,'')
        self.assertTrue(current.preservation(a,b)['eligible_narrow_literal_delta'])

    def test_filled_population_heading_cannot_be_deleted(self):
        for content in ['100명','인구는 증가한다.']:
            a='마을'+chr(10)*2+'인구'+chr(10)*2+content+chr(10)*2+'교통'+chr(10)+'철도'
            b=a.replace('인구'+chr(10)*2,'')
            self.assertFalse(current.preservation(a,b)['eligible_narrow_literal_delta'])

    def test_only_empty_heading_is_removed_filled_climate_stays(self):
        a='마을'+chr(10)*2+'인구'+chr(10)*2+'기후'+chr(10)+'여름은 덥다.'
        b=a.replace('인구'+chr(10)*2,'')
        self.assertTrue(current.preservation(a,b)['eligible_narrow_literal_delta'])
        self.assertFalse(current.preservation(a,b.replace('여름은 덥다.',''))['eligible_narrow_literal_delta'])

    def test_arbitrary_line_death_at_eof_and_adjacent_lists_not_accepted(self):
        for a,b in [('연대기'+chr(10)*2+'사망','연대기'),
                    ('인구'+chr(10)+'역사','역사'),
                    ('인구'+chr(10)*2+'알 수 없는 표제','알 수 없는 표제')]:
            self.assertFalse(current.preservation(a,b)['eligible_narrow_literal_delta'])

    def test_code_quote_indent_and_bullet_are_not_empty_sections(self):
        for line in ['> 인구','    인구','* 인구']:
            a=line+chr(10)*2+'교통'+chr(10)*2+'도로'
            self.assertEqual(current.mask_empty_sections(a)[1],[])
        a='```'+chr(10)+'인구'+chr(10)*2+'교통'+chr(10)+'```'
        self.assertEqual(current.mask_empty_sections(a)[1],[])

    def test_populated_values_numeric_and_negation_changes_fail(self):
        a='명칭: 오이정. 1956년 이전은 아니다.'+chr(10)*2+'인구'+chr(10)*2+'교통'+chr(10)+'국도 7호선'
        b=a.replace('인구'+chr(10)*2,'')
        for changed in [b.replace('1956','1957'),b.replace('아니다','맞다'),b.replace('오이정','다른정')]:
            self.assertFalse(current.preservation(a,changed)['eligible_narrow_literal_delta'])


if __name__=='__main__':unittest.main()
