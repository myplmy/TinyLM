"""Only closed cost HOLD and the identical complete reference may resume."""
import copy
import unittest
from scripts import diag_p014e_cpu_single_core_resume as resume


def records():
    p = dict(authority_directive=158, authority_end=resume.driver.DEADLINE.isoformat(), torch_threads=1, workers=1, interop_threads=1, affinity=[0])
    first = dict(ordinal=0, arm='REFERENCE', status='CPU1_CHILD_COMPLETE', exit_code=0, affinity=[0],
        physical_state_unchanged=True, model_released=True, worker_threads_released=True, CUDA_initialized=False,
        numeric=[dict(rows=[{}] * 4)] * 4, records=[dict(repeats=[{}] * 3)] * 4, answers=[{}] * 4)
    stopped = dict(ordinal=1, status='CPU1_CHILD_HOLD', exit_code=8, numeric=[], records=[], answers=[],
        error='complete declared CPU1 suite does not fit measured cost', physical_state_unchanged=True,
        model_released=True, worker_threads_released=True, CUDA_initialized=False)
    return p, first, stopped


class ResumeContracts(unittest.TestCase):
    def test_exact_complete_anchor_and_cost_only_hold_are_admissible(self):
        resume.validate_resume_reports(*records())

    def test_changed_threads_or_affinity_cannot_carry_anchor(self):
        for field, value in [('workers', 4), ('affinity', [1])]:
            p, first, stopped = records(); p[field] = value
            with self.assertRaises(ValueError):
                resume.validate_resume_reports(p, first, stopped)

    def test_partial_measurement_or_numerical_failure_is_not_cost_only_hold(self):
        for field, value in [('numeric', [{}]), ('status', 'CPU1_CHILD_NUMERICAL_OR_ID_NEGATIVE'), ('exit_code', 1)]:
            p, first, stopped = records(); stopped[field] = value
            with self.assertRaises(ValueError):
                resume.validate_resume_reports(p, first, stopped)

    def test_incomplete_reference_cannot_be_used_to_reduce_the_declared_suite(self):
        p, first, stopped = records(); first['answers'] = first['answers'][:-1]
        with self.assertRaises(ValueError):
            resume.validate_resume_reports(p, first, stopped)

    def test_failed_resource_closure_prevents_resume(self):
        for target in ('first', 'stopped'):
            p, first, stopped = records()
            (first if target == 'first' else stopped)['model_released'] = False
            with self.assertRaises(ValueError):
                resume.validate_resume_reports(p, first, stopped)


if __name__ == '__main__':
    unittest.main()
