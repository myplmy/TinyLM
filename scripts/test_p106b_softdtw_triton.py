import unittest
import torch
from scripts.p106b_softdtw_triton import soft_dtw


class SoftDtwInterfaceContracts(unittest.TestCase):
    def test_cpu_tensor_is_not_silently_moved_to_cuda(self):
        with self.assertRaises(ValueError):soft_dtw(torch.zeros(2,3,dtype=torch.float64),gamma=.1)
    def test_non_tensor_and_invalid_gamma_do_not_start_gpu(self):
        for value in [None,[[0.]]]:
            with self.assertRaises(ValueError):soft_dtw(value,gamma=.1)
        with self.assertRaises(ValueError):soft_dtw(torch.zeros(2,3,dtype=torch.float64),gamma=0.)
    def test_import_and_interface_checks_leave_cuda_uninitialized(self):self.assertFalse(torch.cuda.is_initialized())


if __name__=='__main__':unittest.main()
