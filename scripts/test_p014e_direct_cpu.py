"""Meaningful local ABI, digit/group-boundary and lifetime safety contracts."""
import os
import unittest
import torch
from scripts import p014e_direct_cpu as direct
from scripts.diag_p014e_direct_cuda import synthetic_record


class CPUABIContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=os.environ["P014E_CPU_LIBRARY_PATH"];cls.sha=os.environ["P014E_CPU_LIBRARY_SHA256"]
        cls.runtime=direct.KernelRuntime(cls.path,cls.sha,workers=4)

    @classmethod
    def tearDownClass(cls):cls.runtime.close()

    def test_all243_bytes_group_boundaries_and_lookup_order(self):
        record=synthetic_record();op=direct.PackedCPUOperator(record,self.runtime)
        ids=torch.tensor([243,*range(243),1,0],dtype=torch.long)
        expected=direct.reference.PackedGroupLinear(record,tile_rows=244).unpack_rows(0,244)[ids]
        with torch.no_grad():actual=op.lookup(ids)
        self.assertTrue(torch.equal(actual.view(torch.int32),expected.view(torch.int32)))

    def test_linear_matches_float64_source_dot(self):
        record=synthetic_record();op=direct.PackedCPUOperator(record,self.runtime)
        source=direct.reference.PackedGroupLinear(record,tile_rows=244).unpack_rows(0,244)
        x=torch.arange(8*256,dtype=torch.float32).reshape(8,256).remainder(11)*.125
        expected=(x.double()@source.double().t()).float()
        with torch.no_grad():actual=op(x)
        self.assertTrue(torch.equal(actual.view(torch.int32),expected.view(torch.int32)))

    def test_worker_partition_is_bit_identical(self):
        runtime=direct.KernelRuntime(self.path,self.sha,workers=1)
        try:
            record=synthetic_record();a=direct.PackedCPUOperator(record,runtime);b=direct.PackedCPUOperator(record,self.runtime)
            with torch.no_grad():
                x=torch.arange(256,dtype=torch.float32).reshape(1,256)*.25
                self.assertTrue(torch.equal(a(x).view(torch.int32),b(x).view(torch.int32)))
        finally:runtime.close()

    def test_python_dtype_grad_and_id_boundaries(self):
        op=direct.PackedCPUOperator(synthetic_record(),self.runtime)
        with self.assertRaisesRegex(RuntimeError,"no_grad"):op(torch.ones(1,256))
        with torch.no_grad():
            with self.assertRaises(ValueError):op(torch.ones(1,256,dtype=torch.float64))
            with self.assertRaises(ValueError):op.lookup(torch.tensor([-1]))
            with self.assertRaises(ValueError):op(torch.ones(0,256))

    def test_C_rejects_bad_dimensions_before_writing(self):
        record=synthetic_record();x=torch.ones(1,256);y=torch.full((244,),-999.)
        code=self.runtime.linear_fn(x.data_ptr(),record["codes"].data_ptr(),record["scales"].data_ptr(),y.data_ptr(),
                                    1,244,256,0,0,244)
        self.assertEqual(code,1);self.assertTrue(bool((y==-999).all()))

    def test_C_rejects_outside_ID_without_writing(self):
        record=synthetic_record();ids=torch.tensor([-1],dtype=torch.long);y=torch.full((1,256),-999.)
        code=self.runtime.lookup_fn(record["codes"].data_ptr(),record["scales"].data_ptr(),ids.data_ptr(),y.data_ptr(),
                                    1,244,256,128)
        self.assertEqual(code,2);self.assertTrue(bool((y==-999).all()))


if __name__=="__main__":unittest.main()
