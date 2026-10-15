from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import p106b_joint_decimal as code


class DecimalContracts(unittest.TestCase):
    def test_independent_decimal_reconstruction_all_pairs(self):
        for a in range(100):
            for b in range(100):
                total,ones,tens,carry=code.decimal_parts(a,b)
                self.assertEqual(total,a+b);self.assertEqual(10*tens+ones,total);self.assertIn(carry,(0,1))
        self.assertEqual(code.decimal_parts(43,28),(71,1,7,1))

    def test_pairs_split_before_language_and_order_views(self):
        rows=code.addition_rows({(2,3)})
        self.assertEqual({s:len(v) for s,v in rows.items()},dict(train=8192,dev=1024,test=1024))
        roots={s:{r['meta']['semantic_root_id'] for r in v} for s,v in rows.items()}
        self.assertFalse(roots['train']&roots['test']);self.assertFalse(roots['dev']&roots['test'])
        for split,values in rows.items():
            self.assertTrue(all(tuple(r['meta']['unordered_pair'])!=(2,3) for r in values))
            self.assertEqual(len({code.source.sha(r['messages']) for r in values}),len(values))
        row=rows['train'][0];legal=code.approved([row]);self.assertGreaterEqual(code.label(row,legal),1000)
        altered=copy.deepcopy(row);altered['meta']['total']+=1
        with self.assertRaises(ValueError):code.label(altered,legal)

    def test_digit_zero_gradient_and_fixed_state_gradient(self):
        import torch
        h=torch.randn(2,8,3,requires_grad=True);y=torch.tensor([[-100,1,2,-100,-100,3,4,-100],[-100,-100,-100,1,2,-100,-100,-100]])
        head=code.new_head(3)
        loss,n,correct,events=code.objective(head,h,y,[1,1217],[[5],[3]],beta=0)
        loss.backward();self.assertEqual((n,events),(2,2))
        self.assertEqual(float(head.weight.grad[2:].abs().sum()),0.)
        self.assertGreater(float(head.weight.grad[:2].abs().sum()),0.)
        head.zero_grad();loss,n,correct,events=code.objective(head,h,y,[1,1217],[[5],[3]],beta=1)
        loss.backward();self.assertGreater(float(head.weight.grad[2:].abs().sum()),0.)
        with self.assertRaises(ValueError):code.objective(head,h,y,[1,1217],[[1],[3]],beta=1)

    def test_head_rng_parameter_and_label_bounds(self):
        import torch
        before=torch.get_rng_state().clone();head=code.new_head(768)
        self.assertTrue(torch.equal(before,torch.get_rng_state()));self.assertEqual(sum(p.numel() for p in head.parameters()),26146)
        for value in (0,1,1000,1398):self.assertEqual(code.valid_label(value),value)
        for value in (2,999,1199,1399):
            with self.assertRaises(ValueError):code.valid_label(value)


if __name__=='__main__':unittest.main()
