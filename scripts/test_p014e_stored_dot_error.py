import unittest
from decimal import Decimal
import numpy as np
from scripts.p014e_stored_dot_error import unpack_fp32, decimal_dot_fp32

class StoredDotContracts(unittest.TestCase):
    def test_group_tail_padding_is_discarded_before_next_group(self):
        codes = np.array([[[242, 0], [121, 242]]], dtype=np.uint8)
        scales = np.array([[2., .5]], dtype=np.float32)
        actual = unpack_fp32(codes, scales, group=6, width=12)
        expected = np.array([[2, 2, 2, 2, 2, -2, 0, 0, 0, 0, 0, .5]], dtype=np.float32)
        np.testing.assert_array_equal(actual, expected)

    def test_cancellation_has_independently_known_exact_unit_result(self):
        x = np.array([2**24, 1, -2**24], dtype=np.float32)
        value, flags = decimal_dot_fp32(x, np.ones(3, dtype=np.float32))
        self.assertEqual(value, Decimal(1))
        self.assertFalse(flags['Inexact'])

    def test_bad_codes_dtype_and_nonfinite_or_shape_mismatch_fail(self):
        with self.assertRaises(ValueError):
            unpack_fp32(np.array([[[243]]], dtype=np.uint8), np.ones((1, 1), dtype=np.float32), group=5, width=5)
        with self.assertRaises(ValueError):
            unpack_fp32(np.zeros((1, 1, 1), dtype=np.uint8), np.ones((1, 1), dtype=np.float16), group=5, width=5)
        for x, w in (([1., np.nan], [1., 2.]), ([1.], [1., 2.])):
            with self.subTest(x=x), self.assertRaises(ValueError):
                decimal_dot_fp32(np.array(x, dtype=np.float32), np.array(w, dtype=np.float32))

if __name__ == '__main__':
    unittest.main()
