import json
import unittest
import torch
from torch.nn import functional as F
from scripts import p108_joint_precision as p
from scripts import p108_weight_space as metrics


class PrecisionContracts(unittest.TestCase):
    def setUp(self):torch.set_num_threads(1)
    def test_actual_fp32_replay_passes_while_old_mixed_precision_difference_fails(self):
        w=torch.tensor([[1e8]],dtype=torch.float32);v=w+8;x=torch.tensor([[[1.1]]])
        result=p.operator_evidence(x,F.linear(x,w),F.linear(x,v),w,v)
        p.require_operator(result)
        self.assertFalse(result['original_gate_close']);self.assertGreater(result['original_gate_max_abs'],.1)
        self.assertLess(result['decomposition_max_abs'],1e-10)
    def test_wrong_actual_module_output_is_not_excused_as_roundoff(self):
        w=torch.tensor([[2.]]);v=w+.1;x=torch.ones(1,2,1)
        result=p.operator_evidence(x,F.linear(x,w),F.linear(x,v)+1,w,v)
        self.assertFalse(result['native_after_exact'])
        with self.assertRaises(RuntimeError):p.require_operator(result)
    def test_frozen_packet_json_reconstructs_exact_bytes_and_rejects_changed_base(self):
        w=torch.tensor([[2.,3.],[4.,5.]]);left=torch.tensor([[.1],[.2]],dtype=torch.float64);right=torch.tensor([[.3],[.4]],dtype=torch.float64)
        delta=(left@right.T).float();record=json.loads(json.dumps(dict(left=left.tolist(),right=right.tolist(),
            base_weight_sha256=metrics.tensor_sha(w),delta_sha256=metrics.tensor_sha(delta))))
        torch.testing.assert_close(p.packet_from_record(record,w),delta,rtol=0,atol=0)
        with self.assertRaises(ValueError):p.packet_from_record(record,w+1)
    def test_replacement_is_exact_once_and_original_module_and_second_call_are_preserved(self):
        module=torch.nn.Linear(2,3,bias=False);x=torch.ones(1,2,2);original=module(x).detach();target=torch.tensor([.01,.02,.03])
        with p.replace_once(module,target)as state:
            first=module(x);second=module(x)
            self.assertTrue(torch.equal(first[0,-1],target));self.assertEqual(state['fires'],1)
            self.assertTrue(torch.equal(second,original));self.assertTrue(torch.equal(first[0,0],original[0,0]))
        self.assertTrue(torch.equal(module(x),original));self.assertEqual(len(module._forward_hooks),0)
    def test_exception_removes_replacement_hook(self):
        module=torch.nn.Linear(2,3,bias=False)
        with self.assertRaisesRegex(RuntimeError,'owned'):
            with p.replace_once(module,torch.zeros(3)):raise RuntimeError('owned')
        self.assertEqual(len(module._forward_hooks),0)
    def test_nonfiring_replacement_and_invalid_shapes_fail_closed(self):
        module=torch.nn.Linear(2,3,bias=False)
        with self.assertRaises(RuntimeError):
            with p.replace_once(module,torch.zeros(3)):pass
        with self.assertRaises(ValueError):p.replace_once(module,torch.zeros(3,dtype=torch.float64)).__enter__()


if __name__=='__main__':unittest.main()
