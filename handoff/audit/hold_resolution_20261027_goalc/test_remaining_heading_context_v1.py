from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from close_remaining_heading_context_v1 import remaining_headings


class HeadingContext(unittest.TestCase):
    def text(self,body):
        return body+'\n\n일본의 공항\n국제공항\n'

    def test_empty_routes_are_deferred(self):
        self.assertEqual(remaining_headings(self.text('가람 공항이다.\n\n운항 노선\n\n화물 노선')),
                         ['운항 노선','화물 노선'])

    def test_gallery_before_separate_prose_is_deferred(self):
        self.assertEqual(remaining_headings(self.text('가람 교량이다.\n\n갤러리\n\n붕괴 사고\n사고는 1990년에 일어났다.')),['갤러리'])

    def test_heading_with_rows_in_same_block_is_not_this_counterexample(self):
        self.assertEqual(remaining_headings(self.text('가람 공항이다.\n\n운항 노선\n서울 - 부산')),[])

    def test_filled_gallery_caption_is_not_deleted_or_flagged_as_empty(self):
        self.assertEqual(remaining_headings(self.text('가람 교량이다.\n\n갤러리\n2010년 교량 전경')),[])

    def test_mention_in_prose_is_preserved(self):
        self.assertEqual(remaining_headings(self.text('갤러리 전시는 2001년에 열렸다.')),[])

    def test_empty_work_chronology_is_deferred(self):
        self.assertEqual(remaining_headings(self.text('가람은 감독이다.\n\n작품 연보\n\n외부 링크\n공식 사이트')),['작품 연보'])

    def test_existing_empty_education_negative_remains(self):
        self.assertIn('교육 기관',remaining_headings(self.text('가람은 도시이다.\n\n교육 기관')))

    def test_existing_populated_sections_remain(self):
        self.assertEqual(remaining_headings(self.text('가람은 배우이다.\n\n출연\n가람 영화 - 주연')),[])


if __name__=='__main__':
    unittest.main()
