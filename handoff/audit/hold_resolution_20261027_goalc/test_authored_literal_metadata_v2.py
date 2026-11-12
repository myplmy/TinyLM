from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from authored_literal_metadata_readiness_v2 import preservation


class AuthoredMetadataPreservation(unittest.TestCase):
    def source(self):
        return '가람()은 대한민국의 배우이다. 1990년에 영화에 출연했다.\n\n외부 링크\n\n대한민국의 배우\n대한민국의 영화 배우\n'

    def candidate(self):
        return self.source().replace('()','').replace('\n외부 링크\n','\n')

    def test_empty_footer_before_typed_metadata_passes(self):
        self.assertTrue(preservation(self.source(),self.candidate())['eligible_narrow_literal_delta'])

    def test_filled_reference_must_keep_its_heading(self):
        source=self.source().replace('대한민국의 배우\n대한민국의 영화 배우','김가람 1990. 서울 출판사.')
        target=source.replace('()','').replace('\n외부 링크\n','\n')
        self.assertFalse(preservation(source,target)['eligible_narrow_literal_delta'])

    def test_populated_cast_name_deletion_fails(self):
        self.assertFalse(preservation(self.source(),self.candidate().replace('가람',''))['eligible_narrow_literal_delta'])

    def test_numeric_change_fails(self):
        self.assertFalse(preservation(self.source(),self.candidate().replace('1990','1991'))['eligible_narrow_literal_delta'])

    def test_known_eof_header_needs_no_metadata_invention(self):
        source='가람은 배우이다.\n\n각주\n'
        self.assertTrue(preservation(source,'가람은 배우이다.\n')['eligible_narrow_literal_delta'])

    def test_complete_internal_code_is_unchanged(self):
        source='함수 예제이다.\n\n```python\ncall()\n```\n\n각주\n'
        target=source.removesuffix('\n각주\n')+'\n'
        self.assertTrue(preservation(source,target)['guards']['code'])
        self.assertFalse(preservation(source,target.replace('call()','call'))['guards']['code'])

    def test_unknown_suffix_is_not_a_category_list(self):
        source=self.source().replace('대한민국의 배우\n대한민국의 영화 배우','가람\n나래')
        self.assertFalse(preservation(source,source.replace('\n외부 링크\n','\n'))['eligible_narrow_literal_delta'])


if __name__=='__main__':
    unittest.main()
