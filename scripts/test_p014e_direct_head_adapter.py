"""CPU-only projection delegation, alias safety and exception restoration."""
import unittest
import torch
from torch.nn import functional as F
from scripts import p014e_direct_head_adapter as adapter


class CPUOperator:
    def __init__(self,table):self.packed_codes=table.packed_codes;self.group_scales=table.group_scales;self.table=table
    def weights(self):
        raw=adapter.packed.unpack_trits(self.packed_codes,self.table.emb_rank).reshape(self.table.vocab_size,-1)
        return raw.float()*self.group_scales
    def lookup(self,ids):return self.weights()[ids]
    def __call__(self,x):return F.linear(x,self.weights())


def fixture():
    record=adapter.packed.pack_weight(torch.tensor([[1.,-1.],[0.,2.],[-3.,0.]]),2)
    model=adapter.packed.PackedTransformer.__new__(adapter.packed.PackedTransformer)
    torch.nn.Module.__init__(model)
    model.emb_up=torch.nn.Linear(2,3,bias=False)
    model.packed_embedding=adapter.packed.PackedTernaryTable(record,head_rows=2)
    model.fixture_body=adapter.packed.PackedGroupLinear(record,tile_rows=3)
    return model,CPUOperator(model.packed_embedding)


class DirectHeadContracts(unittest.TestCase):
    def test_same_projection_lookup_and_no_new_state(self):
        model,operator=fixture();x=torch.tensor([[1.,2.,3.]]);keys=tuple(model.state_dict())
        with torch.no_grad():
            expected=model._head_logits(x);wanted=model.packed_embedding.rows(torch.tensor([2,0]))
            with adapter.direct_head(model,operator) as proof:
                torch.testing.assert_close(model._head_logits(x),expected,rtol=0,atol=0)
                torch.testing.assert_close(model.packed_embedding.rows(torch.tensor([2,0])),wanted,rtol=0,atol=0)
            self.assertTrue(proof["restored"] and proof["body_owners_unchanged"])
        self.assertEqual(keys,tuple(model.state_dict()))

    def test_exception_restores_methods(self):
        model,operator=fixture();original=model._head_logits.__func__
        with torch.no_grad(),self.assertRaisesRegex(RuntimeError,"sentinel"):
            with adapter.direct_head(model,operator) as proof:raise RuntimeError("sentinel")
        self.assertTrue(proof["restored"]);self.assertIs(model._head_logits.__func__,original)

    def test_nonaliased_duplicate_buffer_refused(self):
        model,operator=fixture();operator.packed_codes=operator.packed_codes.clone()
        with torch.no_grad(),self.assertRaisesRegex(ValueError,"alias"):
            with adapter.direct_head(model,operator):pass

    def test_autograd_and_unbounded_slice_refused(self):
        model,operator=fixture()
        with self.assertRaisesRegex(ValueError,"no-grad"):
            with adapter.direct_head(model,operator):pass
        with torch.no_grad(),adapter.direct_head(model,operator),self.assertRaisesRegex(ValueError,"bounded"):
            model.packed_embedding.rows(slice(None))


if __name__=="__main__":unittest.main()
