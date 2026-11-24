"""Refuse expired authority, input escape, altered conditions and empty success."""
from datetime import timedelta
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from scripts import diag_p014e_cpu_single_core as driver


class AdmissionContracts(unittest.TestCase):
    def test_virtual_dependency_module_label_is_not_a_repository_source(self):
        virtual = SimpleNamespace(__file__='_nonexistent_generated_module.py', __name__='external.generated')
        physical = SimpleNamespace(__file__=str(driver.ROOT / 'scripts/diag_p014e_cpu_single_core.py'), __name__='owned.driver')
        sources, generated = driver.repository_module_sources([virtual, physical])
        self.assertEqual(sources, {driver.ROOT / 'scripts/diag_p014e_cpu_single_core.py'})
        self.assertEqual(generated, [dict(module='external.generated', virtual_file='_nonexistent_generated_module.py')])

    def test_expired_authority_cannot_start_even_with_wall_budget(self):
        budget = driver.Budget(9000, now=lambda: driver.NEW_WORK_CUTOFF, monotonic=lambda: 0.)
        with self.assertRaises(TimeoutError):
            budget.check(admission=True)

    def test_local_wall_cap_cannot_be_extended_by_authority_window(self):
        clock = iter([0., 101.])
        budget = driver.Budget(100, now=lambda: driver.NEW_WORK_CUTOFF - timedelta(hours=2), monotonic=lambda: next(clock))
        with self.assertRaises(TimeoutError):
            budget.check()

    def test_stop_file_closes_owned_work(self):
        class Present:
            def exists(self):
                return True
        budget = driver.Budget(9000, now=lambda: driver.NEW_WORK_CUTOFF - timedelta(hours=2), monotonic=lambda: 0., stop_file=Present())
        with self.assertRaises(TimeoutError):
            budget.check()

    def test_protected_and_escaping_inputs_are_refused_before_read(self):
        for name in ('../x', '/tmp/x', '.claude/x', '.codex/x', '.agents/x', 'datasets/TinyDataset/x'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                driver.checked_relative(name)

    def test_empty_or_partial_measurements_cannot_claim_completion(self):
        for result in ({}, dict(numeric=[dict(rows=[{}] * 4)] * 4, records=[], answers=[{}] * 4),
                       dict(numeric=[dict(rows=[{}] * 3)] * 4, records=[dict(repeats=[{}] * 3)] * 4, answers=[{}] * 4)):
            with self.assertRaises(ValueError):
                driver.require_full_child(result)

    def test_changed_condition_refused_before_reading_frozen_inputs(self):
        p = dict(schema=driver.SCHEMA, authority_directive=158, authority_end=driver.DEADLINE.isoformat(),
                 new_work_cutoff=driver.NEW_WORK_CUTOFF.isoformat(), order=list(driver.ORDER), anchor_ordinals=[0, 4],
                 workers=4, torch_threads=1, interop_threads=1, affinity=[0], models=[{}, {}], linear_rtol=.00002, linear_atol=.000002)
        with patch.object(driver, 'sha', side_effect=AssertionError('must not read inputs')):
            with self.assertRaises(ValueError):
                driver.validate_profile(p)


if __name__ == '__main__':
    unittest.main()
