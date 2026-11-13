"""Counterexamples for independent terminal metadata deduplication."""
import unittest
from pathlib import Path
import sys
AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(AUDIT), str(AUDIT.parents[2])]
from verify_typed_metadata_repeats_v1 import evaluate


class TypedMetadataRepeats(unittest.TestCase):
    def setUp(self):
        self.prefix = '김가나는 축구 선수이다. 2010년부터 활동했다.\n\n각주\n\n'
        self.tail = '대한민국의 축구 선수\n서울 출신\n대한민국의 축구 선수'
        self.clean = '김가나는 축구 선수이다. 2010년부터 활동했다.\n\n대한민국의 축구 선수\n서울 출신\n'

    def proof(self, source=None, target=None, decision='EDIT'):
        return evaluate(self.prefix + self.tail if source is None else source,
                        self.clean if target is None else target, decision)

    def test_only_duplicate_tag_removed(self):
        self.assertTrue(self.proof()['eligible_narrow_literal_delta'])

    def test_new_name_rejected(self):
        self.assertFalse(self.proof(target=self.clean.replace('김가나', '이다라'))['eligible_narrow_literal_delta'])

    def test_number_or_negation_changed_rejected(self):
        self.assertFalse(self.proof(target=self.clean.replace('2010', '2011'))['eligible_narrow_literal_delta'])
        self.assertFalse(self.proof(target=self.clean.replace('활동했다', '활동하지 않았다'))['eligible_narrow_literal_delta'])

    def test_numeric_repeated_tag_rejected(self):
        source = self.prefix + self.tail + '\n2010년 설립\n2010년 설립'
        self.assertFalse(self.proof(source=source)['eligible_narrow_literal_delta'])

    def test_same_tag_in_body_rejected(self):
        source = '대한민국의 축구 선수\n\n' + self.prefix + self.tail
        target = '대한민국의 축구 선수\n\n' + self.clean
        self.assertFalse(self.proof(source, target)['eligible_narrow_literal_delta'])

    def test_reordered_unique_tags_rejected(self):
        self.assertFalse(self.proof(target=self.clean.replace('대한민국의 축구 선수\n서울 출신', '서울 출신\n대한민국의 축구 선수'))['eligible_narrow_literal_delta'])

    def test_untyped_or_question_source_rejected(self):
        self.assertFalse(self.proof(source=self.prefix + '정답 A\n정답 B\n정답 A')['eligible_narrow_literal_delta'])
        self.assertFalse(self.proof(source='Answers: 1. A\n\n' + self.prefix + self.tail)['eligible_narrow_literal_delta'])


if __name__ == '__main__':
    unittest.main()
