"""Reject invented facts, changed conditions and code under a closure repair."""
import unittest
from authored_round_closure_preservation_v1 import preservation


class RoundClosure(unittest.TestCase):
    def passed(self, source, body):
        return all(preservation(source, body)['guards'].values())

    def test_nominal_citation_closure(self):
        proof = preservation('인물(1900~1980, 임명 기록', '인물(1900~1980), 임명 기록')
        self.assertTrue(all(proof['guards'].values()))
        self.assertFalse(proof['legacy_deletion_only_observations']['guards']['ordered'])
        self.assertNotIn('ordered', proof['guards'])

    def test_added_name_is_not_punctuation(self):
        self.assertFalse(self.passed('인물(1900', '인물 홍길동(1900)'))

    def test_changed_numeric_value_fails(self):
        self.assertFalse(self.passed('인물(1900', '인물(1901)'))

    def test_removed_negation_fails(self):
        self.assertFalse(self.passed('인물(가입하지 않았다', '인물(가입했다)'))

    def test_code_modification_is_not_prose_repair(self):
        self.assertFalse(self.passed('```python\nf(\n```', '```python\nf()\n```'))

    def test_remaining_crossed_brackets_fail(self):
        self.assertFalse(self.passed('표제([내용)', '표제([내용))'))

    def test_reordered_dates_fail(self):
        self.assertFalse(self.passed('인물(1900~1980', '인물(1980~1900)'))

    def test_new_operator_is_not_a_closer(self):
        self.assertFalse(self.passed('설명(값', '설명(값=)'))


if __name__ == '__main__':
    unittest.main()
