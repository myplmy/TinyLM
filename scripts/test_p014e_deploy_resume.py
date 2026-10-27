"""Pure continuation admission; no model, checkpoint, GPU or dataset tests."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diag_p014e_deploy_resume as resume


def hold():
    return dict(phase="deploy-cpu", exit_code=8, status="BUDGET_HOLD_NOT_FULL_SUITE", cuda_initialized=False,
                variants=[dict(variant="fp32_unchanged", model_released=True,
                               result=dict(status="BUDGET_HOLD_NOT_FULL_SUITE", records=[], answers=[],
                                           cost_probes=[{}, {}], conservative_seconds=1789.3559989328496))])


class ResumeContract(unittest.TestCase):
    def test_actual_two_variant_estimate_and_original_cap_are_separate(self):
        result = resume.admission(hold(), 5400, 10000)
        self.assertAlmostEqual(result["two_variants_plus_closure_seconds"], 4178.711997865699)
        self.assertEqual(result["previous_phase_cap_seconds"], 1200)
        self.assertEqual(result["current_phase_cap_seconds"], 5400)

    def test_no_smaller_suite_or_unbounded_time_to_manufacture_completion(self):
        for cap, remaining in ((1200, 10000), (5400, 5500), (10000, 20000)):
            with self.assertRaises(ValueError):
                resume.admission(hold(), cap, remaining)

    def test_old_error_complete_or_unreleased_model_refused(self):
        for kind in ("error", "complete", "released", "gpu", "ran"):
            value = hold()
            if kind == "error": value["exit_code"] = 9
            elif kind == "complete": value["status"] = "TECHNICAL_COMPLETE_NOT_QUALITY"
            elif kind == "released": value["variants"][0]["model_released"] = False
            elif kind == "gpu": value["cuda_initialized"] = True
            else: value["variants"][0]["result"]["records"] = [dict(workload="partial")]
            with self.assertRaises(ValueError):
                resume.admission(value, 5400, 10000)

    def test_nonfinite_or_too_large_forecast_refused(self):
        for estimate in (float("nan"), float("inf"), 0, 3000):
            value = deepcopy(hold())
            value["variants"][0]["result"]["conservative_seconds"] = estimate
            with self.assertRaises(ValueError):
                resume.admission(value, 5400, 10000)


if __name__ == "__main__":
    unittest.main()
