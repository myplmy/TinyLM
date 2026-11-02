"""Regressions distinguish existing months from partial, signed and merged values."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from numeric_atom_integrity_v1 import numeric_atom_changes
from numeric_local_atom_proof_v1 import prove_flagged_atoms


class LocalAtomProofTests(unittest.TestCase):
    def proofs(self, raw, body):
        flags = numeric_atom_changes(raw, body)
        return prove_flagged_atoms(raw, body, flags)

    def test_existing_month_is_not_a_year_suffix(self):
        raw, body = '김모(1941년 1월 1일생)이다.', '김모(1월 1일생)이다.'
        begin = body.index('1월')
        results = prove_flagged_atoms(raw, body, [dict(body_span=[begin, begin+1], body_token='1', source_token='1941')])
        self.assertTrue(results)
        self.assertTrue(all(r['status'] == 'EXACT_LOCAL_ATOM_AND_UNIT' for r in results))

    def test_partial_number_cannot_be_invented(self):
        self.assertTrue(all(r['status'] == 'MANUAL_CONTEXT_REQUIRED' for r in self.proofs('거리 12km', '거리 1')))

    def test_decimal_prefix_is_not_the_same_value(self):
        self.assertTrue(all(r['status'] == 'MANUAL_CONTEXT_REQUIRED' for r in self.proofs('중력 9.8076 m/s2', '중력 9.8 m/s2')))

    def test_sign_loss_stays_unproved(self):
        results = self.proofs('온도 −12 C', '온도 12 C')
        self.assertTrue(results)
        self.assertEqual(results[0]['status'], 'MANUAL_CONTEXT_REQUIRED')

    def test_unchanged_other_line_cannot_supply_a_digit(self):
        results = self.proofs('첫째 1\n둘째 12km\n', '첫째 1\n둘째 1\n')
        self.assertTrue(results)
        self.assertEqual(results[0]['status'], 'MANUAL_CONTEXT_REQUIRED')

    def test_separate_values_cannot_merge(self):
        self.assertEqual(self.proofs('값 1 2', '값 12')[0]['status'], 'MANUAL_CONTEXT_REQUIRED')

    def test_one_atom_cannot_supply_two_copies(self):
        self.assertEqual(self.proofs('값 1 및 12', '값 1 및 1')[0]['status'], 'MANUAL_CONTEXT_REQUIRED')

    def test_unit_context_cannot_be_borrowed(self):
        raw, body = '기록 1941년 1월; 별개1일', '기록 1일; 별개1일'
        results = self.proofs(raw, body)
        self.assertTrue(results)
        self.assertTrue(any(r['status'] == 'MANUAL_CONTEXT_REQUIRED' for r in results))

    def test_fact_correction_still_needs_independent_evidence(self):
        self.assertEqual(self.proofs('동경 137도', '동경 139도')[0]['status'], 'MANUAL_CONTEXT_REQUIRED')

    def test_whole_atom_quarantine_adds_no_flag(self):
        self.assertEqual(self.proofs('섬 12km\n다음 3km\n', '섬\n다음 3km\n'), [])


if __name__ == '__main__':
    unittest.main()
