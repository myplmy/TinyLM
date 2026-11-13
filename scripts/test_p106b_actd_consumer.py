import copy
import unittest
import torch
from scripts import p106b_actd_consumer as c
from scripts.p106b_actd_anchor import actd_sums


class ACTDConsumerContracts(unittest.TestCase):
    def fixture(self):
        class Head(torch.nn.Module):
            def __init__(self):super().__init__();self.head=torch.nn.Linear(3,5,bias=False,dtype=torch.float64)
            def _head_logits(self,x):return self.head(x)
        torch.manual_seed(9);model=Head();h=torch.randn(2,4,3,dtype=torch.float64,requires_grad=True)
        y=torch.tensor([[-100,2,3,-100],[1,2,-100,4]]);s=y.ne(-100).long()
        p=[dict(batch_row=0,student_prefix_raw_index=1,student_target_raw_index=2,student_target_id=2,owner=1,
            distribution=dict(accepted=True,anchor_ids=[1,1,3],native_logits=[2.,1.,0.])),
           dict(batch_row=1,student_prefix_raw_index=3,student_target_raw_index=4,student_target_id=4,owner=1,
            distribution=dict(accepted=True,anchor_ids=[2,3,4],native_logits=[3.,2.,0.]))]
        return model,h,y,s,p

    def test_global_denominator_and_gradients_match_independent_dense_oracle(self):
        model,h,y,s,p=self.fixture();before=copy.deepcopy(model.state_dict())
        r=c.components(model,h,y,s,p,ce_denominator=5,actd_denominator=2,enable_actd=True,chunk=2)
        logits=model._head_logits(h);keep=y.ne(-100)
        ce=torch.nn.functional.cross_entropy(logits[keep],y[keep],reduction='sum')
        chosen=torch.stack([logits[x['batch_row'],x['student_prefix_raw_index']] for x in p])
        terms=actd_sums(chosen,torch.tensor([x['distribution']['anchor_ids'] for x in p]),
            torch.tensor([x['distribution']['native_logits'] for x in p],dtype=torch.float64),residual_weight=1.)
        oracle=ce/5+terms['loss_sum']/2
        torch.testing.assert_close(r['loss'],oracle,atol=1e-12,rtol=1e-12)
        first=torch.autograd.grad(r['loss'],(h,model.head.weight),retain_graph=True)
        second=torch.autograd.grad(oracle,(h,model.head.weight))
        for a,b in zip(first,second):torch.testing.assert_close(a,b,atol=1e-12,rtol=1e-12)
        for name,value in model.state_dict().items():self.assertTrue(torch.equal(value,before[name]))

    def test_ce_only_keeps_all_targets_even_when_actd_positions_are_a_subset(self):
        model,h,y,s,p=self.fixture();r=c.components(model,h,y,s,p,ce_denominator=5,actd_denominator=2,enable_actd=False,chunk=1)
        logits=model._head_logits(h);oracle=torch.nn.functional.cross_entropy(logits[y.ne(-100)],y[y.ne(-100)],reduction='sum')/5
        torch.testing.assert_close(r['loss'],oracle);self.assertEqual(r['ce_targets'],5);self.assertEqual(r['actd_positions'],0)

    def test_split_microbatches_preserve_full_update_denominators(self):
        model,h,y,s,p=self.fixture();total=h.sum()*0.
        for row in range(2):
            positions=[dict(x,batch_row=0) for x in p if x['batch_row']==row]
            total=total+c.components(model,h[row:row+1],y[row:row+1],s[row:row+1],positions,
                ce_denominator=5,actd_denominator=2,enable_actd=True,chunk=1)['loss']
        whole=c.components(model,h,y,s,p,ce_denominator=5,actd_denominator=2,enable_actd=True)['loss']
        torch.testing.assert_close(total,whole,atol=1e-12,rtol=1e-12)

    def test_owner_shift_duplicate_and_masked_position_are_rejected(self):
        model,h,y,s,p=self.fixture()
        for changed in [p+[p[0]], [dict(p[0],owner=2)], [dict(p[0],student_target_raw_index=3)],
                        [dict(p[0],student_prefix_raw_index=0)]]:
            with self.assertRaises(ValueError):c.components(model,h,y,s,changed,ce_denominator=5,actd_denominator=2,enable_actd=True)


if __name__=='__main__':unittest.main()
