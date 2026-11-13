"""Pure source binding/denominator contracts for the cost-only controller."""
import copy
import unittest
from scripts import diag_p106b_gsq_objective as cost


def fixture():
    rows = []
    for index in range(1024):
        record = dict(x=[1, 7], y=[7, 4], segments=[0, 0])
        rows.append(dict(language='ko' if index % 2 == 0 else 'en',
            record=record, record_sha256=cost.object_sha(record),
            ce_targets=2, kd_chunks=1,
            chunks=[dict(positions=[0], teacher_logprob=-1.)]))
    prepared = dict(schema='P106B_ALM_REFERENCE_TRAIN_TERNARY_V1',
        status='ALM_TRAIN_PREPARED', rows=1024,
        row_sha256=[cost.object_sha(row) for row in rows])
    return prepared, rows


class CostBindingTests(unittest.TestCase):
    def test_original_balanced128_and_once_shifted_labels_preserved(self):
        prepared, rows = fixture()
        chosen = cost.selected_rows(prepared, rows)
        self.assertEqual(len(chosen), 128)
        self.assertEqual(sum(r['language'] == 'ko' for r in chosen), 64)
        self.assertEqual(chosen[0]['record']['y'], [7, 4])
        self.assertEqual(chosen[0]['chunks'][0]['positions'], [0])

    def test_changed_original_row_fails_before_selection(self):
        prepared, rows = fixture()
        rows[0]['chunks'][0]['teacher_logprob'] = -2.
        with self.assertRaisesRegex(ValueError, 'exact rows'):
            cost.selected_rows(prepared, rows)

    def test_kd_on_eot_is_not_accepted(self):
        prepared, rows = fixture()
        rows[0]['chunks'][0]['positions'] = [1]
        prepared['row_sha256'] = [cost.object_sha(r) for r in rows]
        with self.assertRaisesRegex(ValueError, 'aligned teacher'):
            cost.selected_rows(prepared, rows)

    def test_insufficient_language_quota_is_not_filled_by_duplicates(self):
        prepared, rows = fixture()
        for row in rows:
            row['language'] = 'en'
        prepared['row_sha256'] = [cost.object_sha(r) for r in rows]
        with self.assertRaisesRegex(ValueError, '64'):
            cost.selected_rows(prepared, rows)

    def test_policy_is_standard_geometry_but_only_a_technical_cost(self):
        self.assertEqual((cost.POLICY['micro'],cost.POLICY['accum'],cost.POLICY['width']), (8,16,1024))
        self.assertEqual(cost.POLICY['warmup_updates']+cost.POLICY['timed_updates'], 3)
        self.assertFalse(cost.POLICY['quality_evaluation'])
        self.assertFalse(cost.POLICY['checkpoint_saving'])


if __name__ == '__main__':
    unittest.main()
