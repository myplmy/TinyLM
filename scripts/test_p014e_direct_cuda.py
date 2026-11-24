"""CPU admission boundaries; CUDA arithmetic remains a separate actual gate."""
import unittest
import torch
from scripts import p014e_direct_cuda as direct


def record():
    values=torch.tensor([[-1.,0.,1.,0.]*32,[0.,1.,-1.,0.]*32])
    return direct.reference.pack_weight(values,128)


class DirectPackedCPUContracts(unittest.TestCase):
    def test_original_scale_and_group_padding_are_retained(self):
        r=record();r["scales"][0]=2.**-50
        op=direct.DirectPackedOperator(r,device="cpu")
        self.assertTrue(torch.equal(op.packed_codes,r["codes"]))
        self.assertTrue(torch.equal(op.group_scales,r["scales"]))
        self.assertEqual(op.storage_bytes(),2*26+2*4)
        self.assertEqual(list(op.parameters()),[])

    def test_reserved_byte_rejected_before_device_transfer(self):
        r=record();r["codes"][0,0,0]=255
        with self.assertRaisesRegex(ValueError,"reserved"):direct.DirectPackedOperator(r,device="cpu")

    def test_noncanonical_group_tail_rejected(self):
        r=record();r["codes"][0,0,-1]=0
        with self.assertRaisesRegex(ValueError,"padding"):direct.DirectPackedOperator(r,device="cpu")

    def test_cpu_or_autograd_never_silently_falls_back(self):
        op=direct.DirectPackedOperator(record(),device="cpu")
        with self.assertRaisesRegex(RuntimeError,"no_grad"):op(torch.ones(1,128))
        with torch.no_grad(),self.assertRaisesRegex(ValueError,"CUDA"):op(torch.ones(1,128))
        with self.assertRaisesRegex(RuntimeError,"inference-only"):op.train()

    def test_scale_shape_mismatch_rejected(self):
        r=record();r["scales"]=r["scales"].reshape(-1)
        with self.assertRaisesRegex(ValueError,"scale shape"):direct.DirectPackedOperator(r,device="cpu")


if __name__=="__main__":unittest.main()
