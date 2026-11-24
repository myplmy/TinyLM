"""CPU scope-model contracts with independent known feature labels."""
import unittest
import inspect
from datetime import datetime, timezone
import numpy as np
from scripts import p108c_scope as s
from scripts import p108c_limits as limits


class ScopeContracts(unittest.TestCase):
    def setUp(self):
        self.x = np.array([[2., 1., .3], [2., .8, .4], [-2., 1., .5], [-2., .9, .3]])
        self.y = np.array([1, 1, 0, 0])
        self.groups = ["edit", "edit", "other", "other"]
        self.delta = np.array([[.7, -.3, .1]])

    def test_group_and_class_mass(self):
        w = s.group_weights([1, 1, 0, 0, 0], ["a", "a", "b", "b", "c"])
        np.testing.assert_allclose(w, [.25, .25, .125, .125, .25])

    def test_weight_duplication_does_not_increase_group_mass(self):
        w = s.group_weights([1, 0, 0, 0], ["a", "b", "b", "b"])
        self.assertAlmostEqual(w[1:].sum(), .5)

    def test_unit_scale_invariance_and_large_finite_values(self):
        np.testing.assert_allclose(s.unit(self.x), s.unit(self.x * 1e200))

    def test_zero_and_nonfinite_features_rejected(self):
        for x in (np.zeros((1, 3)), np.array([[np.nan, 1, 2]])):
            with self.assertRaises(ValueError):
                s.unit(x)

    def test_shape_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            s.matrix(self.x, width=4)

    def test_two_classes_and_explicit_groups_required(self):
        for y, groups in (([1, 1], ["a", "b"]), ([1, 0], ["a"])):
            with self.assertRaises(ValueError):
                s.group_weights(y, groups)

    def test_response_matches_independent_dot(self):
        model = dict(kind="delta_response", delta=self.delta)
        expected = [abs(float(row @ self.delta[0])) / np.sqrt(sum(row**2)) for row in self.x]
        np.testing.assert_allclose(s.score(model, self.x), expected)

    def test_runtime_has_no_question_id_gold_or_group_argument(self):
        self.assertEqual(list(inspect.signature(s.score).parameters), ["model", "x"])
        self.assertEqual(list(inspect.signature(s.route).parameters), ["model", "x", "threshold"])
        models, _ = s.fit_models(self.x, self.y, self.groups, self.delta)
        for model in models:
            a = s.score(model, self.x.copy())
            b = s.score(model, self.x.copy())
            np.testing.assert_array_equal(a, b)

    def test_nearest_raw_independent_similarity(self):
        models, _ = s.fit_models(self.x, self.y, self.groups, self.delta)
        m = next(m for m in models if m["name"] == "NEAREST_RAW")
        z = self.x / np.linalg.norm(self.x, axis=1)[:, None]
        expected = (z @ z[:2].T).max(1) - (z @ z[2:].T).max(1)
        np.testing.assert_allclose(s.score(m, self.x), expected)

    def test_ridge_weighted_primal_solution(self):
        models, report = s.fit_models(self.x, self.y, self.groups, self.delta, ridge_values=(.1,))
        m = next(m for m in models if m["kind"] == "ridge")
        z = s.transformed(m, self.x)
        w = np.array(report["class_group_weights"]) * len(self.x)
        primal = np.linalg.solve(z.T @ (z * w[:, None]) + .1 * np.eye(3),
                                 z.T @ (np.where(self.y, 1., -1.) * w))
        np.testing.assert_allclose(m["coefficient"], primal, atol=1e-12)

    def test_thresholds_cover_all_on_and_off_without_final_scores(self):
        ts = s.thresholds([1., 1., 2.])
        self.assertLess(ts[0], 1.)
        self.assertGreater(ts[-1], 2.)
        self.assertEqual(len(ts), 3)

    def test_confusion_independent_counts(self):
        self.assertEqual(s.confusion(np.array([True, False, True, False]), [1, 1, 0, 0]),
                         dict(tp=1, fn=1, fp=1, tn=1))

    def test_selected_gate_respects_three_negative_constraints(self):
        models, _ = s.fit_models(self.x, self.y, self.groups, self.delta)
        m, report = s.select(models, self.x, self.y, self.x, self.y, self.x[2:])
        chosen = report["selected"]
        self.assertEqual(chosen["train"]["fp"], 0)
        self.assertEqual(chosen["dev"]["fp"], 0)
        self.assertEqual(chosen["guard_false_positives"], 0)
        self.assertEqual(chosen["dev"]["tp"], 2)
        self.assertEqual(int(s.route(m, self.x, chosen["threshold"]).sum()), 2)

    def test_off_wins_when_no_dev_positive_is_recoverable(self):
        m = dict(name="flat", kind="delta_response", delta=np.zeros((1, 3)))
        chosen, _ = s.select([m], self.x, self.y, self.x, self.y, self.x[:1])
        self.assertEqual(chosen["kind"], "off")

    def test_invalid_ridge_and_threshold_are_not_silently_replaced(self):
        with self.assertRaises(ValueError):
            s.fit_models(self.x, self.y, self.groups, self.delta, ridge_values=(0.,))
        with self.assertRaises(ValueError):
            s.route(dict(kind="off"), self.x, float("nan"))

    def test_unknown_scoring_kind_rejected(self):
        with self.assertRaises(ValueError):
            s.score(dict(kind="oracle"), self.x)

    def test_invalid_standardization_rejected(self):
        with self.assertRaises(ValueError):
            s.transformed(dict(center=np.zeros(3), scale=np.zeros(3)), self.x)


class NightBoundaryContracts(unittest.TestCase):
    def test_current_authority_does_not_use_old_afternoon_deadline(self):
        self.assertEqual(limits.AUTHORITY_END.isoformat(), "2026-11-16T23:00:00+00:00")
        limits.Budget(60).check(now=datetime(2026, 11, 16, 10, tzinfo=timezone.utc),
                               elapsed=0, admission=True)

    def test_cleanup_and_phase_limit_fail_closed(self):
        with self.assertRaises(TimeoutError):
            limits.Budget(60).check(now=datetime(2026, 11, 16, 22, 40, tzinfo=timezone.utc), elapsed=0)
        with self.assertRaises(TimeoutError):
            limits.Budget(60).check(now=datetime(2026, 11, 16, 10, tzinfo=timezone.utc), elapsed=60)

    def test_late_admission_and_naive_clock_rejected(self):
        with self.assertRaises(TimeoutError):
            limits.Budget(90).check(now=datetime(2026, 11, 16, 22, 39, tzinfo=timezone.utc),
                                   elapsed=0, admission=True)
        with self.assertRaises(ValueError):
            limits.Budget().check(now=datetime(2026, 11, 16, 10), elapsed=0)


if __name__ == "__main__":
    unittest.main()
