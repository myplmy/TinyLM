import unittest
from datetime import timedelta
import torch
from scripts import p108b_norm_sweep as helper
from scripts import p108b_target_protection as morning


class NormSweepTests(unittest.TestCase):
    def fixture(self):
        keys = torch.tensor([[1., 1.], [2., -1.], [1., 2.]], dtype=torch.float64)
        values = torch.tensor([[3., 4.], [1., -2.]], dtype=torch.float64)
        protected = torch.tensor([[1., 0., 0.]], dtype=torch.float64)
        return keys, values, protected

    def test_full_signal_solves_targets_and_keeps_protected_directions(self):
        k, v, p = self.fixture()
        full, stats = helper.full_solution(k, v, p)
        for scale in (.5, 1., 2.):
            delta = helper.at_signal(full, scale)
            result = helper.delivery(delta, k, v, p, scale)
            self.assertLess(result['target_relative_residual'], 1e-6)
            self.assertAlmostEqual(result['target_signal_projection'], scale, places=6)
            self.assertLess(result['protected_output_l2'], 1e-12)
        self.assertEqual(stats['protected_rank'], 1)

    def test_morning_cap_is_exactly_reproducible(self):
        k, v, p = self.fixture()
        full, _ = helper.full_solution(k, v, p)
        delta = helper.at_signal(full, .25 * (1-1e-6) / float(full.norm()))
        old, _ = morning.candidate(k, v, p, .25, protect=True)
        self.assertTrue(torch.equal(delta, old))

    def test_unprotected_control_can_be_matched_to_same_physical_request_norm(self):
        k, v, p = self.fixture()
        protected, _ = helper.full_solution(k, v, p)
        other, stats = helper.full_solution(k, v, p, protect=False)
        delta = helper.at_signal(other, float(protected.norm()) / float(other.norm()))
        self.assertAlmostEqual(float(delta.double().norm()), float(protected.norm()), places=6)
        self.assertGreater(float((delta.double() @ p.T).norm()), 0)
        self.assertEqual(stats['protected_rank'], 0)

    def test_invalid_signal_and_infeasible_protection_fail_closed(self):
        for scale in (0., -1., float('nan'), float('inf')):
            with self.assertRaises(ValueError):helper.at_signal(torch.eye(2), scale)
        with self.assertRaisesRegex(ValueError, 'infeasible'):
            helper.full_solution(torch.eye(2), torch.eye(2), torch.eye(2))

    def test_run_and_authority_boundaries_are_independent(self):
        b = helper.Budget(10)
        b.check(now=helper.AUTHORITY_END-timedelta(seconds=1201), elapsed=9)
        with self.assertRaises(TimeoutError):b.check(now=helper.AUTHORITY_END-timedelta(seconds=1200), elapsed=0)
        with self.assertRaises(TimeoutError):b.check(now=helper.AUTHORITY_END-timedelta(hours=1), elapsed=10)

    def test_protection_and_content_precede_repetition_and_size_in_selection(self):
        def row(name, lost, exact, empty, repeat, norm):
            return dict(name=name, lost_original_protected_ids=list(range(lost)),
                        dev=dict(target_exact=exact, other_exact=0, empty=empty,
                                 unwanted_loops=repeat, question_echoes=0), physical=dict(net_norm=norm))
        good = row('good', 0, 2, 0, 10, 4.)
        unsafe = row('unsafe', 1, 24, 0, 0, 1.)
        empty = row('empty', 0, 2, 5, 0, 2.)
        self.assertEqual(min([unsafe, empty, good], key=helper.selection_key)['name'], 'good')


if __name__ == '__main__':unittest.main()
