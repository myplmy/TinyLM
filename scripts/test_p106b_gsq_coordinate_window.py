import inspect
import time
import unittest
from datetime import datetime,timezone
from scripts import diag_p106b_gsq_coordinate_window as window
from scripts import diag_p106b_gsq_coordinates as study
from scripts import diag_p106b_gsq_objective as old


class CoordinateWindow(unittest.TestCase):
    def test_new_authority_does_not_rewrite_old_deadline(self):
        self.assertEqual(window.DEADLINE,datetime(2026,11,13,8,tzinfo=timezone.utc))
        self.assertEqual(old.DEADLINE,datetime(2026,11,5,8,tzinfo=timezone.utc))
        self.assertEqual(window.POLICY,study.POLICY)
        self.assertEqual(window.POLICY['total_updates'],256)

    def test_low_level_measure_exposes_explicit_guard_and_output(self):
        signature=inspect.signature(study.measure)
        for name in ('guard_fn','directory'):
            self.assertEqual(signature.parameters[name].kind,inspect.Parameter.KEYWORD_ONLY)
            self.assertIsNone(signature.parameters[name].default)

    def test_new_guard_rejects_phase_overrun(self):
        with self.assertRaises(TimeoutError):window.guard(time.perf_counter()-20,1)


if __name__=='__main__':unittest.main()
