"""CPU-only shared-budget regression: no GPU, data sources or teacher calls."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.p106b_request_budget import RequestBudget


class Tests(unittest.TestCase):
    def test_mixed_failures_cannot_extend_existing_ceiling(self):
        budget = RequestBudget()
        for reason in ("initial", "http_recovery", "parse_recovery"):
            budget.take(reason)
        self.assertEqual(budget.remaining, 0)
        with self.assertRaises(RuntimeError):
            budget.take("duplicate_recovery")

    def test_iterator_and_variant_call_share_one_object(self):
        budget = RequestBudget()
        iterator = budget.attempts()
        self.assertEqual(next(iterator), 1)
        self.assertEqual(budget.take("future_approved_variant"), 2)
        self.assertEqual(next(iterator), 3)
        self.assertEqual(list(iterator), [])

    def test_ceiling_cannot_be_raised_to_five(self):
        for value in (0, 4, 5, True):
            with self.assertRaises(ValueError):
                RequestBudget(value)


if __name__ == "__main__":
    unittest.main()
