"""CPU fixture dispatch, shared-owner coverage and exception restoration."""
import unittest
import torch
from scripts import p014e_direct_decode_adapter as adapter
from scripts.test_p014e_direct_head_adapter import fixture


class CPUOperator:
    def __init__(self,module):
        self.module=module;self.in_f=module.in_f;self.out_f=module.out_f;self.group=module.group
        self.packed_codes=module.packed_codes;self.group_scales=module.group_scales
        self.reference=module.forward;self.calls=0
    def __call__(self,x,mode_p=None):self.calls+=1;return self.reference(x,mode_p)


class DecodeDispatchContracts(unittest.TestCase):
    def test_one_row_and_prefill_have_explicit_distinct_paths(self):
        model,_=fixture();op=CPUOperator(model.fixture_body)
        with torch.no_grad(),adapter.one_row_body(model,[(model.fixture_body,op)]) as proof:
            model.fixture_body(torch.ones(1,2));model.fixture_body(torch.ones(1,1,2));model.fixture_body(torch.ones(8,2))
        self.assertEqual(op.calls,2)
        self.assertEqual(proof["counts"],dict(direct_one_row_calls=2,reference_multirow_calls=1))
        self.assertTrue(proof["restored"] and proof["physical_state_unchanged"])

    def test_alias_owner_is_patched_once(self):
        model,_=fixture();model.shared_body=model.fixture_body;op=CPUOperator(model.fixture_body)
        with torch.no_grad(),adapter.one_row_body(model,[(model.fixture_body,op)]) as proof:
            model.shared_body(torch.ones(1,2))
        self.assertEqual(proof["physical_body_owners"],1);self.assertEqual(op.calls,1)
        with torch.no_grad(),self.assertRaisesRegex(ValueError,"coverage"):
            with adapter.one_row_body(model,[(model.fixture_body,op)]*2):pass

    def test_exception_restores_every_method(self):
        model,_=fixture();op=CPUOperator(model.fixture_body);function=model.fixture_body.forward.__func__
        with torch.no_grad(),self.assertRaisesRegex(RuntimeError,"sentinel"):
            with adapter.one_row_body(model,[(model.fixture_body,op)]) as proof:raise RuntimeError("sentinel")
        self.assertIs(model.fixture_body.forward.__func__,function);self.assertTrue(proof["restored"])

    def test_uncovered_owner_and_empty_activation_refused(self):
        model,_=fixture();op=CPUOperator(model.fixture_body)
        with torch.no_grad(),self.assertRaisesRegex(ValueError,"coverage"):
            with adapter.one_row_body(model,[]):pass
        with torch.no_grad(),adapter.one_row_body(model,[(model.fixture_body,op)]),self.assertRaisesRegex(ValueError,"nonempty"):
            model.fixture_body(torch.ones(0,2))


if __name__=="__main__":unittest.main()
