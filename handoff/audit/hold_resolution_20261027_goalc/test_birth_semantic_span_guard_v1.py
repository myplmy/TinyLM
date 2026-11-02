"""Regression examples preserve field roles and independent stated quantities."""
from pathlib import Path
import importlib.util
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('birth_spans',HERE/'birth_semantic_span_guard_v1.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)


class BirthSpanTests(unittest.TestCase):
    def test_queen_ages_are_not_prince_age(self):
        original='9세인 때. 10세에 11세인 세손과 혼인했다. 69세의 일기로.'
        body='때. 11세인 세손과 혼인했다.'
        self.assertEqual([r['value'] for r in guard.lost_stated_quantities(original,body)],['9세','10세','69세'])

    def test_centuries_and_generations_are_not_age_tokens(self):
        self.assertEqual(guard.lost_stated_quantities('20세기 사람. 제3세대 기술.','사람. 기술.'),[])

    def test_independent_ages_remain_intact(self):
        text='18,19세. 10세에 11세인 세손과 혼인했다.'
        self.assertEqual(guard.lost_stated_quantities(text,text),[])

    def test_relative_three_years_is_a_stated_quantity(self):
        self.assertEqual(guard.lost_stated_quantities('3년 뒤인 1934년에 이주했다.','1934년에 이주했다.')[0]['value'],'3년뒤')

    def test_birth_and_death_categories_have_distinct_roles(self):
        text='인물(1898년 ~ 1938년)은 정치인이다.'+chr(10)*2+'1898년 출생'+chr(10)+'1938년 사망'
        self.assertEqual(guard.suspicious_birth_field_removal(text,text),[])

    def test_lost_consistent_birth_year_is_flagged(self):
        text='인물(1898년 ~ 1938년)은 정치인이다.'+chr(10)*2+'1898년 출생'+chr(10)+'1938년 사망'
        body='인물(1938년 사망)은 정치인이다.'+chr(10)*2+'1938년 사망'
        self.assertEqual(guard.suspicious_birth_field_removal(text,body)[0]['year'],'1898')

    def test_bibliographic_year_is_not_a_category(self):
        text='인물(1818년 ~ 1880년)은 인물이다.'+chr(10)*2+'자료 제목 (1819-1880)'+chr(10)+'1818년 출생'
        self.assertEqual(guard.suspicious_birth_field_removal(text,text),[])

    def test_real_different_birth_category_requires_separate_review(self):
        text='인물(1607년 ~ )은 인물이다.'+chr(10)*2+'1601년 출생'
        self.assertEqual(guard.suspicious_birth_field_removal(text,'인물은 인물이다.'),[])


if __name__=='__main__':unittest.main()
