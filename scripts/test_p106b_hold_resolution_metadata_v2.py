"""Challenge only the new boundary proof; these fixtures are never corpus data."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_metadata_v2 as metadata
from scripts import p106b_hold_resolution_policy_v26 as policy


class TypedOrdinalMetadata(unittest.TestCase):
    intro = '가람(1989년 1월 1일 ~ )은 독일의 축구 선수이다.' + chr(10) * 2
    tail = chr(10).join(['1989년 출생', '살아있는 사람', '1. FC 가람의 축구 선수',
                         '2. 분데스리가의 축구 선수', '남자 축구 미드필더',
                         '3. 리가의 축구 선수']) + chr(10)

    def source(self, middle='각주'):
        return self.intro + middle + chr(10) * 2 + self.tail

    def row(self, text, **kw):
        return dict(id='expanded_train:987654321', text=text, complete_eos=True, valid_utf8=True, **kw)

    def test_typed_values_survive_and_only_isolated_footer_changes(self):
        value = metadata.prove(self.source())
        self.assertIsNotNone(value)
        self.assertTrue(value['candidate'].endswith(self.tail))
        self.assertNotIn('각주', value['candidate'])
        self.assertEqual(value['proof']['values_deleted_or_reordered'], 0)

    def test_ordinary_prose_period_is_not_an_ordinal_category(self):
        self.assertIsNone(metadata.prove(self.source().replace('1. FC 가람의 축구 선수', '참고문헌. 실제 저자')))

    def test_exclamation_and_quotes_do_not_get_a_waiver(self):
        for extra in ['헬로! 프로젝트', '"1. FC 다른의 축구 선수"', '1. FC 다른의 축구 선수.']:
            self.assertIsNone(metadata.prove(self.source() + extra + chr(10)))

    def test_no_explicit_year_or_life_anchor_is_not_proven(self):
        raw = self.source().replace('1989년 출생' + chr(10), '').replace('살아있는 사람' + chr(10), '')
        self.assertIsNone(metadata.prove(raw))

    def test_populated_reference_and_its_heading_are_retained(self):
        middle = '외부 링크' + chr(10) + '실제 선수 자료 https://example.test/players'
        value = metadata.prove(self.source(middle))
        self.assertIsNotNone(value)
        self.assertIn(middle, value['candidate'])

    def test_known_ordinal_category_is_required(self):
        self.assertFalse(metadata.typed_ordinal_category('1. 이 문장은 끝났다'))
        self.assertFalse(metadata.typed_ordinal_category('A. FC 가람의 축구 선수'))
        self.assertTrue(metadata.typed_ordinal_category('1. FC 가람의 축구 선수'))

    def test_policy_never_releases_individual_or_previous_holds(self):
        raw = self.source()
        self.assertEqual(policy.propose(self.row(raw), True)['decision'], 'PENDING')
        self.assertEqual(policy.propose(self.row(raw, previous_holds=['EXACT_PRIOR_HOLD']))['decision'], 'PENDING')

    def test_actual_missing_formula_is_still_pending(self):
        raw = self.source('여기서 은 주어진 계수이다.' + chr(10) * 2 + '각주')
        value = policy.propose(self.row(raw))
        self.assertEqual(value['decision'], 'PENDING')

    def test_boundary_release_keeps_every_literal_category_value(self):
        raw = self.source('외부 링크' + chr(10) + '가람 -Transfermarkt')
        before = policy.previous.propose(self.row(raw))
        self.assertEqual(before['decision'], 'PENDING')
        value = policy.propose(self.row(raw))
        self.assertIn(value['decision'], {'KEEP', 'EDIT'})
        self.assertTrue(value['text'].endswith(self.tail))
        self.assertEqual(value['metadata_boundary_proof']['values_deleted_or_reordered'], 0)

    def test_source_period_values_and_unit_characters_are_not_changed(self):
        raw = self.source('이 선수의 기록은 3.5 km이다.' + chr(10) * 2 + '각주')
        value = policy.propose(self.row(raw))
        clean = value.get('candidate', value['text'])
        self.assertIn('3.5 km', clean)
        self.assertIn('2. 분데스리가의 축구 선수', clean)


if __name__ == '__main__':
    unittest.main()
