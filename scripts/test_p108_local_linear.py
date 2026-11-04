"""CPU mathematical/data oracles for the supervised local P108 correction."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch
from scripts import p108_local_linear as local
from scripts import p108_balanced_practice as data


class LocalSolveTests(unittest.TestCase):
    def test_dual_ridge_matches_independent_primal_normal_equation(self):
        k=torch.tensor([[1.,2.],[3.,-.2],[-.3,.8]],dtype=torch.float64)
        v=torch.tensor([[.1,.2],[-.3,.5],[.8,-.2]],dtype=torch.float64)
        factors,report=local.ridge_factors(k,v,rank=2,ridge=.01)
        norm=k.norm(dim=1)[:,None];kn,vn=k/norm,v/norm
        expected=torch.linalg.solve(kn.T@kn+.01*torch.eye(2,dtype=k.dtype),kn.T@vn).T
        actual=factors['left'].double()@factors['right'].double()
        torch.testing.assert_close(actual,expected,rtol=1e-6,atol=1e-7)
        self.assertLess(report['normal_equation_max_abs'],1e-10)

    def test_margin_value_has_the_requested_first_order_effect(self):
        g=torch.tensor([[3.,4.],[0.,0.],[1.,0.]],dtype=torch.float64)
        v,report=local.margin_targets(g,torch.tensor([-2.,0.,2.]))
        torch.testing.assert_close((g*v).sum(1),torch.tensor([3.,0.,0.],dtype=g.dtype),rtol=0,atol=1e-12)
        self.assertEqual(report['zero_gradient'],1)
        self.assertEqual(report['already_at_margin'],1)

    def test_nonlinear_margin_autograd_matches_central_difference(self):
        h=torch.tensor([.3,-.2,.8],dtype=torch.float64,requires_grad=True)
        readout=torch.tensor([1.,-.7,.2],dtype=h.dtype)
        f=lambda x:(x/torch.sqrt(x.square().mean()+1e-5)*readout).sum()
        g=torch.autograd.grad(f(h),h)[0]
        direction=g/g.norm();eps=1e-5
        measured=(f(h.detach()+eps*direction)-f(h.detach()-eps*direction))/(2*eps)
        torch.testing.assert_close(measured,g.norm(),rtol=1e-7,atol=1e-8)

    def test_rank_and_relative_weight_budget(self):
        torch.manual_seed(11)
        factors,report=local.ridge_factors(torch.randn(8,5),torch.randn(8,4),rank=2)
        weight=torch.randn(4,5)
        delta,budget=local.bounded_delta(factors,weight,.0025)
        self.assertLessEqual(float(delta.norm()),.0025*float(weight.norm())*(1+1e-6))
        self.assertLessEqual(int(torch.linalg.matrix_rank(delta)),2)
        self.assertEqual(report['factor_bytes'],(4*2+2*5)*4)

    def test_duplicate_and_zero_keys_are_handled_explicitly(self):
        local.ridge_factors(torch.ones(3,2),torch.ones(3,2),rank=1)
        with self.assertRaises(ValueError):
            local.ridge_factors(torch.zeros(3,2),torch.ones(3,2),rank=1)

    def test_invalid_numeric_inputs_rejected(self):
        with self.assertRaises(ValueError):
            local.ridge_factors(torch.ones(3,2),torch.ones(3,2),rank=3)
        with self.assertRaises(ValueError):
            local.bounded_delta({'left':torch.ones(2,1),'right':torch.ones(1,2)},torch.ones(2,2),-.1)


class PracticeTests(unittest.TestCase):
    def test_all_expected_rules_and_split_sources(self):
        rows=data.make_data()
        report=data.audit_data(rows)
        self.assertEqual(report['counts'],dict(calib=128,dev=128,test=256))
        self.assertEqual(len({r['question'] for r in rows}),512)
        for family in ('arithmetic','lookup','role','boolean','update','copy','repeat','json'):
            changed=deepcopy(rows)
            next(r for r in changed if r['family']==family)['expected']='wrong'
            with self.subTest(family=family),self.assertRaises(ValueError):data.audit_data(changed)

    def test_strict_scoring_protects_internal_whitespace_and_json_types(self):
        self.assertFalse(data.strict_score(dict(family='copy',expected='10',answer='1 0')))
        self.assertTrue(data.strict_score(dict(family='json',expected='{"answer":"10"}',answer=' { "answer" : "10" } ')))
        self.assertFalse(data.strict_score(dict(family='json',expected='{"answer":"10"}',answer='{"answer":10}')))
        self.assertFalse(data.strict_score(dict(family='json',expected='{"answer":"10"}',answer='{"answer":"wrong","answer":"10"}')))

    def test_actual_serializer_prediction_positions_exclude_future_targets(self):
        from scripts.diag_p108_local_linear import token_contract
        class CharacterTokenizer:
            def encode(self,text):return SimpleNamespace(ids=[ord(c)+10 for c in text])
            def decode(self,ids,**kwargs):return ''.join(chr(v-10) for v in ids)
        ids,positions,targets=token_contract(CharacterTokenizer(),'Question?','42')
        self.assertEqual(targets,[ord('4')+10,ord('2')+10,4])
        self.assertEqual(len(positions),3)
        self.assertEqual(positions[-1],len(ids)-1)
        self.assertEqual(ids[positions[0]+1],targets[0])
        self.assertEqual(ids[positions[1]+1],targets[1])

    def test_existing_evaluator_summary_uses_the_strict_writer_score(self):
        from scripts import diag_p108_weight_space as common
        written=[]
        writer=SimpleNamespace(append=written.append)
        cuda=SimpleNamespace(synchronize=lambda:None,max_memory_allocated=lambda:0,max_memory_reserved=lambda:0)
        row=dict(id='cpu',family='copy',question='Copy 10',expected='10',protected=True)
        gen=dict(generated_ids=[17],terminal_ids=[],generated_tokens=1,finish_reason='STOP_SEQUENCE')
        with patch.object(common.manual,'emit',return_value=('1 0',gen)):
            outputs,summary=common.evaluate(dict(torch=SimpleNamespace(cuda=cuda)),[row],data.StrictWriter(writer),
                'cpu_contract',SimpleNamespace(check=lambda:None),96)
        self.assertEqual(summary['exact'],0)
        self.assertTrue(written[0]['legacy_whitespace_exact'])
        self.assertFalse(outputs[0]['exact'])


if __name__=='__main__':
    unittest.main()
