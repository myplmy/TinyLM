"""CPU-only controls, including quantization spill outside selected columns."""
import unittest
import torch
from scripts.p108_signed_control import row_sign_control, control_receipt


class SignedControlTests(unittest.TestCase):
    def test_support_values_and_spectrum_are_preserved(self):
        torch.manual_seed(9)
        delta = torch.randn(9, 13)
        delta[delta.abs() < .4] = 0
        result = row_sign_control(delta, 17)
        receipt = control_receipt(delta, result)
        self.assertTrue(receipt['same_support'])
        self.assertTrue(receipt['same_absolute_coefficients'])
        self.assertGreater(receipt['sign_changed_nonzero'], 0)
        torch.testing.assert_close(torch.linalg.svdvals(delta), torch.linalg.svdvals(result), rtol=1e-5, atol=1e-6)

    def test_quantization_spill_support_is_also_matched(self):
        delta = torch.tensor([[.1, .2, 0., -.3], [0., -.4, .5, .6]])
        result = row_sign_control(delta, 29)
        self.assertTrue(torch.equal(delta.ne(0), result.ne(0)))
        self.assertTrue(torch.equal(delta.abs(), result.abs()))

    def test_seed_is_deterministic(self):
        value = torch.ones(10, 7)
        self.assertTrue(torch.equal(row_sign_control(value, 3), row_sign_control(value, 3)))
        self.assertFalse(torch.equal(row_sign_control(value, 3), row_sign_control(value, 5)))

    def test_invalid_input_is_rejected(self):
        for value in (torch.ones(3), torch.ones(3, 2, dtype=torch.int32), torch.tensor([[float('nan')]])):
            with self.assertRaises(ValueError):
                row_sign_control(value, 3)


if __name__ == '__main__':
    unittest.main()
