from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import p106b_conditional_orpo as data


class Contracts(unittest.TestCase):
    def row(self):return data.source.binding_rows('train',per_family=1)[0]

    def test_only_producer_byte_contract(self):
        row=self.row();proof={data.source.sha(row['messages'])}
        pair=data.make_pair(row,proof)
        self.assertNotEqual(data.source.text(pair['chosen'],-1),data.source.text(pair['rejected'],-1))
        with self.assertRaises(ValueError):data.make_pair(row,set())
        altered=copy.deepcopy(row);altered['messages'][0]['content'][0]['text']='Repeat the answer three times.'
        with self.assertRaises(ValueError):data.make_pair(altered,proof)

    def test_public_or_ambiguous_not_classified(self):
        row=self.row();row['meta']['kind']='public_qa'
        with self.assertRaises(ValueError):data.make_pair(row,{data.source.sha(row['messages'])})
        row=self.row();row['meta']['mapping']={k:'red' for k in row['meta']['mapping']}
        with self.assertRaises(ValueError):data.make_pair(row,{data.source.sha(row['messages'])})

    def test_both_negative_modes(self):
        rows=data.source.binding_rows('train',per_family=2)
        proof={data.source.sha(r['messages']) for r in rows}
        self.assertEqual({data.make_pair(r,proof)['mode'] for r in rows},{'wrong_target','unrequested_repeat'})

    def test_odds_match_direct_formula(self):
        import torch
        c=torch.tensor([.2,.6],dtype=torch.float64).log()
        r=torch.tensor([.1,.3],dtype=torch.float64).log()
        actual=data.preference_loss(c,r)
        ratio=(c.exp()/(1-c.exp()))/(r.exp()/(1-r.exp()))
        expected=-torch.log(ratio/(1+ratio))
        self.assertTrue(torch.allclose(actual,expected,atol=1e-12))

    def test_gradient_direction_and_near_one(self):
        import torch
        c=torch.tensor([-1.,-1e-10],requires_grad=True)
        r=torch.tensor([-2.,-.2],requires_grad=True)
        loss=data.preference_loss(c,r).sum();gc,gr=torch.autograd.grad(loss,(c,r))
        self.assertTrue(torch.isfinite(loss));self.assertTrue(bool((gc<=0).all()))
        self.assertTrue(bool((gr>=0).all()))

    def test_zero_weight_gradient_unchanged(self):
        import torch
        x=torch.tensor([-.8,-1.6],requires_grad=True)
        main=x.square().sum();extra=data.preference_loss(x[:1],x[1:]).sum()
        self.assertTrue(torch.equal(torch.autograd.grad(main+0.*extra,x,retain_graph=True)[0],
                                    torch.autograd.grad(main,x)[0]))

    def test_per_sequence_masked_mean(self):
        import torch
        from tinylm.data.sft import IGNORE
        class Head:
            def _head_logits(self,h):return h
        hidden=torch.randn(2,4,7,requires_grad=True)
        y=torch.tensor([[1,2,IGNORE,IGNORE],[3,4,5,IGNORE]])
        actual=data.sequence_logps(Head(),hidden,y)
        lp=hidden.log_softmax(-1)
        expected=torch.stack([(lp[0,0,1]+lp[0,1,2])/2,
                              (lp[1,0,3]+lp[1,1,4]+lp[1,2,5])/3])
        self.assertTrue(torch.allclose(actual,expected,atol=1e-6))
        actual.sum().backward();self.assertEqual(float(hidden.grad[0,2:].abs().sum()),0.)

    def test_fresh_test_is_disjoint(self):
        rows=data.source.code_rows();fresh=data.fresh_test(rows)
        self.assertEqual(len(fresh),640)
        original={data.source.sha(r['messages']) for v in rows.values() for r in v}
        self.assertFalse(original & {data.source.sha(r['messages']) for r in fresh})

    def test_real_linear_head_autocast_gradient(self):
        import torch
        class Head(torch.nn.Module):
            def __init__(self):
                super().__init__();self.projection=torch.nn.Linear(4,7,bias=False)
            def _head_logits(self,h):return self.projection(h)
        model=Head();hidden=torch.randn(8,3,4,requires_grad=True)
        labels=torch.tensor([[1,2,-100]]*4+[[3,2,-100]]*4)
        with torch.autocast('cpu',dtype=torch.bfloat16):
            lp=data.sequence_logps(model,hidden,labels)
            loss=data.preference_loss(lp[:4],lp[4:]).mean()
        loss.backward()
        self.assertTrue(bool(torch.isfinite(model.projection.weight.grad).all()))
        self.assertGreater(float(model.projection.weight.grad.abs().sum()),0.)

    def test_positive_control_has_no_rejected_gradient(self):
        import torch
        c=torch.tensor([-1.],requires_grad=True);r=torch.tensor([-2.],requires_grad=True)
        loss=data.extra_loss('positive030',c,r).sum()
        gc,gr=torch.autograd.grad(loss,(c,r),allow_unused=True)
        self.assertEqual(float(gc),-1.);self.assertIsNone(gr)

    def test_scoped_own_particle_repair(self):
        rows=data.source.binding_rows('train',per_family=8)
        repaired=[data.correct_own_question(row) for row in rows]
        self.assertTrue(any('의 색상는' in data.source.text(r,0) for r in rows))
        self.assertFalse(any('의 색상는' in data.source.text(r,0) for r in repaired))
        self.assertEqual([data.source.text(r,-1) for r in rows],[data.source.text(r,-1) for r in repaired])
        public=copy.deepcopy(rows[0]);public['meta']['kind']='public_qa'
        self.assertEqual(data.correct_own_question(public),public)


if __name__=='__main__':unittest.main()
