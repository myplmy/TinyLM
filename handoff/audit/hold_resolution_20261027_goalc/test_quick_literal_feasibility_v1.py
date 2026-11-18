"""Cheap rejection cannot substitute for code, numeric or meaning checks."""
import unittest
from quick_literal_feasibility_v1 import possible


class Feasibility(unittest.TestCase):
    def test_optional_alias_delimiter_is_potentially_valid(self):
        self.assertTrue(possible('이름()', '이름'))

    def test_complete_empty_appendix(self):
        self.assertTrue(possible('본문이다.\n\n각주\n', '본문이다.'))

    def test_geography_empty_section(self):
        self.assertTrue(possible('도시\n\n인구\n\n교통\n도로 1\n', '도시\n\n교통\n도로 1\n'))

    def test_lost_name_requires_a_different_contract(self):
        self.assertFalse(possible('사람 이름과 설명', '설명'))

    def test_lost_numeric_value_is_not_literal_preservation(self):
        self.assertFalse(possible('역사 1900년', '역사'))

    def test_possible_does_not_certify_code(self):
        # This prefilter intentionally ignores round punctuation. A separate
        # actual code-preservation check must reject this changed invocation.
        self.assertTrue(possible('```python\nf()\n```', '```python\nf\n```'))


if __name__ == '__main__':
    unittest.main()
