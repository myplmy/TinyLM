"""CPU intervention contracts; synthetic matrices only, no model checkpoint."""
from types import SimpleNamespace
import unittest
import torch
from scripts import p108_wsp_attention as w
from scripts import p108_weight_space as old
from scripts.p106b_weight_route import weight_route
from scripts.test_p106b_weight_route import Mini
from scripts.diag_p108_wsp_attention import data


def fixture():
    m=Mini();m.eval()
    m.layers=[SimpleNamespace(attn_mod=SimpleNamespace(o_proj=m.a),mlp=[SimpleNamespace(down_proj=m.b)])]
    m.norm_f=torch.nn.Identity();m.visit_schedule=lambda:[0]
    return m


class WSPAttentionTests(unittest.TestCase):
    def test_head_columns_follow_output_input_axis(self):
        m=fixture()
        self.assertEqual(w.head_columns(m.a,2,1),[1])
        delta=w.head_delta(m.a,2,1)
        self.assertTrue(torch.equal(delta[:,0],torch.zeros(2)))
        self.assertTrue(torch.equal((m.a.weight+delta)[:,1],torch.zeros(2)))

    def test_invalid_head_layouts_fail_closed(self):
        for heads,head in ((3,0),(2,2),(2,-1),(True,0),(2,True)):
            with self.assertRaises(ValueError):w.head_columns(fixture().a,heads,head)

    def test_registered_head_edit_affects_forward_and_restores(self):
        m=fixture();x=torch.tensor([[.4,.7]])
        with weight_route(m,'float') as route,torch.no_grad():
            m.freeze_quant();before=m(x).clone();weight=m.a.weight.clone();cache=m.a._wq
            with w.edit(m,route,[('attention:0',w.head_delta(m.a,2,1))]) as receipt:
                self.assertFalse(torch.equal(before,m(x)))
                self.assertTrue(torch.equal(m.a.weight[:,1],torch.zeros(2)))
                self.assertEqual(receipt[0]['changed_outside_requested'],0)
                self.assertGreater(receipt[0]['master_changed'],0)
            self.assertTrue(torch.equal(weight,m.a.weight));self.assertIs(cache,m.a._wq)
            self.assertTrue(torch.equal(before,m(x)))

    def test_multisite_projection_and_exception_restore(self):
        m=fixture()
        with weight_route(m,'float') as route,torch.no_grad():
            m.freeze_quant();saved={key:(old.tensor_sha(mod.weight),mod._wq) for key,mod in w.outputs(m).items()}
            edits=[(key,old.projection_delta(mod.weight,torch.tensor([.6,.8]),[0,1],1.5)) for key,mod in w.outputs(m).items()]
            with self.assertRaisesRegex(RuntimeError,'sentinel'):
                with w.edit(m,route,edits):raise RuntimeError('sentinel')
            for key,mod in w.outputs(m).items():
                self.assertEqual(old.tensor_sha(mod.weight),saved[key][0]);self.assertIs(mod._wq,saved[key][1])

    def test_noop_preserves_cache_object_and_signed_zero_bits(self):
        m=fixture()
        with torch.no_grad():m.a.weight[0,0]=-0.
        with weight_route(m,'float') as route,torch.no_grad():
            m.freeze_quant();sha=old.tensor_sha(m.a.weight);cache=m.a._wq
            with w.edit(m,route,[('attention:0',torch.zeros_like(m.a.weight))]):
                self.assertEqual(sha,old.tensor_sha(m.a.weight));self.assertIs(cache,m.a._wq)
            self.assertEqual(sha,old.tensor_sha(m.a.weight))

    def test_all_inputs_validated_before_first_edit(self):
        m=fixture()
        with weight_route(m,'float') as route,torch.no_grad():
            m.freeze_quant();sha=old.tensor_sha(m.a.weight)
            with self.assertRaises(ValueError):
                with w.edit(m,route,[('attention:0',torch.ones_like(m.a.weight)),('mlp:0',torch.ones(3,3))]):pass
            self.assertEqual(sha,old.tensor_sha(m.a.weight))

    def test_ternary_route_rejected_instead_of_changing_scales(self):
        m=fixture()
        with weight_route(m,'ternary') as route,torch.no_grad():
            m.freeze_quant()
            with self.assertRaises(ValueError):
                with w.edit(m,route,[('attention:0',torch.zeros_like(m.a.weight))]):pass

    def test_capture_observes_both_output_types_and_removes_hooks(self):
        m=fixture()
        with weight_route(m,'float'),torch.no_grad():
            m.freeze_quant()
            with w.capture(m) as values:m.norm_f(m(torch.ones(1,5,2)))
            self.assertEqual(set(values),{'attention:0','mlp:0','residual'})
            self.assertFalse(m.a._forward_hooks);self.assertFalse(m.norm_f._forward_pre_hooks)

    def test_shared_output_and_nontrained_visit_rejected(self):
        m=fixture();m.layers[0].mlp[0].down_proj=m.a
        with self.assertRaises(ValueError):w.outputs(m)
        m=fixture();m.visit_schedule=lambda:[0,0]
        with self.assertRaises(ValueError):w.outputs(m)

    def test_fresh_rule_splits_counts_and_no_question_overlap(self):
        rows=data()
        self.assertEqual(sum(r['split']=='dev' for r in rows),64)
        self.assertEqual(sum(r['split']=='test' for r in rows),128)
        self.assertEqual(sum(r['split']=='calib' for r in rows),16)
        dev={r['question'] for r in rows if r['split']=='dev'}
        self.assertFalse(dev & {r['question'] for r in rows if r['split']=='test'})


if __name__=='__main__':unittest.main()
