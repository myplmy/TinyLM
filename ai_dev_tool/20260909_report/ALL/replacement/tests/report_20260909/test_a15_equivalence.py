import unittest
import torch
from scripts.check_training_equivalence import tensor_difference


class EquivalenceMetricTests(unittest.TestCase):
    def test_printed_equality_is_not_bit_equality(self):
        a = torch.tensor([1.000001], dtype=torch.float32)
        b = torch.tensor([1.000002], dtype=torch.float32)
        result = tensor_difference(a, b, atol=1e-5, rtol=0)
        self.assertTrue(result["allclose"])
        self.assertFalse(result["bit_equal"])

    def test_dtype_mismatch_is_not_bit_equality(self):
        result = tensor_difference(torch.ones(2), torch.ones(2, dtype=torch.bfloat16),
                                    atol=0, rtol=0)
        self.assertTrue(result["allclose"])
        self.assertFalse(result["bit_equal"])

    def test_signed_zero_requires_byte_comparison(self):
        result = tensor_difference(torch.tensor([0.0]), torch.tensor([-0.0]), atol=0, rtol=0)
        self.assertTrue(result["allclose"])
        self.assertFalse(result["bit_equal"])
