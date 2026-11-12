"""Negative cases for metadata preservation independently of the edit producer."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_event_metadata_literal_delta_v1 import evaluate


class EventLiteralTests(unittest.TestCase):
    def source(self,body='가람은 단체이다. 원래 인용과 acques Perrin 이름을 그대로 보존한다.'):
        return body+'\n\n각주\n\n대한민국의 정당\n1945년 설립\n1945년 폐지'

    def candidate(self,source):
        return source.replace('\n\n각주\n\n','\n\n',1)

    def test_only_actually_empty_footer_before_identical_metadata_passes(self):
        source=self.source()
        self.assertTrue(evaluate(source,self.candidate(source))['eligible_narrow_literal_delta'])

    def test_populated_name_loss_fails(self):
        source=self.source()
        self.assertFalse(evaluate(source,self.candidate(source).replace('acques Perrin',''))['eligible_narrow_literal_delta'])

    def test_category_word_loss_fails(self):
        source=self.source()
        self.assertFalse(evaluate(source,self.candidate(source).replace('대한민국의 정당','대한민국'))['eligible_narrow_literal_delta'])

    def test_date_change_fails(self):
        source=self.source()
        self.assertFalse(evaluate(source,self.candidate(source).replace('1945년 폐지','1946년 폐지'))['eligible_narrow_literal_delta'])

    def test_same_values_reordered_still_fail(self):
        source=self.source()
        self.assertFalse(evaluate(source,self.candidate(source).replace('1945년 설립\n1945년 폐지','1945년 폐지\n1945년 설립'))['eligible_narrow_literal_delta'])

    def test_reference_below_heading_cannot_be_removed(self):
        source=self.source().replace('각주','참고문헌\n김가람, 원래 서지 2005년')
        candidate=source.replace('참고문헌\n김가람, 원래 서지 2005년\n\n','')
        self.assertFalse(evaluate(source,candidate)['eligible_narrow_literal_delta'])

    def test_normal_word_inside_body_is_not_an_empty_footer(self):
        source=self.source('이 문장은 각주라는 단어 자체를 설명한다.')
        self.assertFalse(evaluate(source,self.candidate(source).replace('각주라는','라는'))['eligible_narrow_literal_delta'])

    def test_single_date_does_not_establish_independent_boundary(self):
        source=self.source().replace('1945년 폐지','지역의 단체')
        self.assertFalse(evaluate(source,self.candidate(source))['eligible_narrow_literal_delta'])

    def test_code_literal_word_must_survive(self):
        fence=chr(96)*3
        source=self.source(fence+'python\nx="각주"\n'+fence)
        self.assertFalse(evaluate(source,self.candidate(source).replace('x="각주"','x=""'))['eligible_narrow_literal_delta'])

    def test_one_terminal_lf_does_not_invent_metadata_values(self):
        source=self.source()
        self.assertTrue(evaluate(source,self.candidate(source)+'\n')['eligible_narrow_literal_delta'])


if __name__=='__main__':
    unittest.main(verbosity=2)
