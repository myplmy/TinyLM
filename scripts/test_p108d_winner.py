"""Independent exact small problems for the constrained affine edit solver."""
import unittest
import numpy as np
from scripts import p108d_winner as study


class WinnerContracts(unittest.TestCase):
    def test_single_halfspace_exact_minimum(self):
        delta, result = study.solve_winners(np.array([[1., 0.], [0., 1.]]),
            np.array([[0., 1.]]), np.array([[1., 0.]]), np.array([0]), 1., np.array([.2]))
        np.testing.assert_allclose(delta, [[.6, 0.], [-.6, 0.]], atol=1e-9)
        self.assertEqual(result["status"], "MINIMUM_NORM_NUMERICALLY_CERTIFIED")

    def test_negative_gate_and_protected_coordinate(self):
        delta, result = study.solve_winners(np.eye(2), np.array([[0., 1.]]),
            np.array([[1., 2.]]), np.array([0]), -2., np.array([.2]), protected=np.array([[0., 1.]]))
        np.testing.assert_allclose(delta, [[-.3, 0.], [.3, 0.]], atol=1e-8)
        self.assertLess(result["protected_response_norm"], 1e-10)

    def test_kronecker_gram_matches_explicit_planes(self):
        rng = np.random.default_rng(7)
        left, right = rng.normal(size=(5, 3)), rng.normal(size=(5, 4))
        explicit = np.stack([np.outer(a, b).reshape(-1) for a, b in zip(left, right)])
        np.testing.assert_allclose(study.plane_gram(left, right), explicit @ explicit.T, atol=1e-12)

    def test_all_competitors_are_checked_after_each_cut(self):
        head = np.array([[1., 0.], [0., 1.], [-1., 0.]])
        delta, result = study.solve_winners(head, np.array([[-2., 1.], [1., -2.]]),
            np.eye(2), np.array([0, 1]), 1., np.array([.1, .2]))
        scores = (np.array([[-2., 1.], [1., -2.]]) + delta.T) @ head.T
        margins, rivals = study.winner_margins(scores, np.array([0, 1]))
        self.assertTrue(np.all(margins >= np.array([.1, .2]) - 1e-5))
        self.assertEqual(result["correct_argmax"], 2)

    def test_full_protection_cannot_change_a_required_winner(self):
        _, result = study.solve_winners(np.eye(2), np.array([[0., 1.]]),
            np.array([[1., 0.]]), np.array([0]), 1., np.array([.1]), protected=np.eye(2))
        self.assertEqual(result["status"], "NO_CONTROLLABLE_DIRECTION_FOR_REQUIRED_CONSTRAINT")

    def test_physical_budget_is_not_claimed_equal_net(self):
        before = np.ones((2, 3), dtype=np.float32)
        requested = np.zeros((2, 3)); requested[0, 1] = .25
        after, actual, result = study.materialize(before, requested, budget=1.)
        self.assertEqual(result["changed"], 1)
        self.assertEqual(result["changed_outside_requested"], 0)
        self.assertEqual(result["comparison"], "WITHIN_COMMON_BUDGET_NOT_EQUAL_NET")
        np.testing.assert_array_equal(after.astype(np.float64) - before, actual)

    def test_bad_coordinate_or_nan_is_rejected(self):
        with self.assertRaises(ValueError):
            study.plane_gram(np.ones((2, 3)), np.ones((3, 4)))
        with self.assertRaises(ValueError):
            study.winner_margins(np.array([[np.nan, 0.]]), np.array([0]))


if __name__ == "__main__":
    unittest.main()
