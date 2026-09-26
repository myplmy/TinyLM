"""CPU-only regression for P030B descriptive verdicts."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.bench_infer import _speed_transition_verdict
from scripts.mem_runtime import _fp32_one_copy_bound_applies


class P030BReadoutTest(unittest.TestCase):
    def test_tied_storage_residency_does_not_erase_speed_gap(self):
        self.assertIn("미귀속", _speed_transition_verdict(1.0, 1.0, 1.149))

    def test_small_speed_gap_is_labeled_with_explicit_tolerance(self):
        self.assertIn("3%", _speed_transition_verdict(1.3, 1.0, 1.01))

    def test_two_copy_bound_excludes_compressed_storage(self):
        self.assertTrue(_fp32_one_copy_bound_applies(lut=False, int8_store=False))
        self.assertFalse(_fp32_one_copy_bound_applies(lut=True, int8_store=False))
        self.assertFalse(_fp32_one_copy_bound_applies(lut=False, int8_store=True))


if __name__ == "__main__":
    unittest.main()
