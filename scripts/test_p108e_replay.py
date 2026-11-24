import unittest
import numpy as np
from scripts.p108e_replay import two_addends


class ExactAfterContracts(unittest.TestCase):
    def test_cancellation_needs_and_accepts_second_addend(self):
        before=np.array([[1e20]],np.float32);after=np.array([[1.]],np.float32)
        first,second=two_addends(before,after)
        self.assertNotEqual(float((before+first)[0,0]),1.)
        np.testing.assert_array_equal((before+first+second).view(np.uint32),after.view(np.uint32))

    def test_native_roundtrip_and_signed_values(self):
        before=np.array([[.1,-3.,0.,1e-12]],np.float32);after=before+np.array([[.001,.002,.003,-1e-12]],np.float32)
        first,second=two_addends(before,after)
        np.testing.assert_array_equal((before+first+second).view(np.uint32),after.view(np.uint32))

    def test_mixed_precision_is_rejected(self):
        with self.assertRaises(ValueError):two_addends(np.ones((2,2),np.float16),np.ones((2,2),np.float32))


if __name__=="__main__":unittest.main()
