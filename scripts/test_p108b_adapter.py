"""CPU algebra/ownership contracts; actual TinyLM/CUDA is a separate canary."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import torch

from scripts import p108b_tinylm as api


class Layer(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.attn_mod=torch.nn.Module();self.attn_mod.o_proj=torch.nn.Linear(2,2,bias=False)
        mlp=torch.nn.Module();mlp.down_proj=torch.nn.Linear(2,2,bias=False)
        self.mlp=torch.nn.ModuleList([mlp])


class Toy(torch.nn.Module):
    def __init__(self):
        super().__init__();self.layers=torch.nn.ModuleList([Layer() for _ in range(14)]);self.eval()
        with torch.no_grad():
            for layer in self.layers:layer.mlp[0].down_proj.weight.fill_(.1)

    def visit_schedule(self):return range(14)


class AdapterTests(unittest.TestCase):
    def test_mean_question_objective_and_explicit_grads_do_not_update_parameters(self):
        model=Toy();fits=[dict(id=str(i),split='fit') for i in range(24)]
        route=SimpleNamespace(mode='float',assert_active=lambda:None)
        active=dict(model=model,route=route,cfg=SimpleNamespace(dim=2))
        def pack(_active,row):return dict(targets=torch.arange(3),coefficient=int(row['id'])+1)
        def logp(_active,_row):
            s=sum(layer.mlp[0].down_proj.weight.sum() for layer in model.layers)
            return torch.log_softmax(torch.stack([s,-s]),dim=0)
        def loss(_active,item):
            s=sum(layer.mlp[0].down_proj.weight.sum() for layer in model.layers)
            return (s*item['coefficient']).square()
        before={n:p.detach().clone() for n,p in model.named_parameters()}
        with patch.object(api.query,'pack',side_effect=pack), \
             patch.object(api.loss_owner,'prompt_log_probs',side_effect=logp), \
             patch.object(api.loss_owner,'target_nll',side_effect=loss), \
             patch.object(api.value,'refresh_autograd_views'):
            adapter=api.TinyAdapter(active,fits,['cal'+str(i) for i in range(128)],kl_weight=0.)
            observed,gradients=adapter.objective(gradient=True,directions={i:torch.ones(2,2) for i in range(14)})
            reference=sum(float(loss(active,pack(active,row)).detach()) for row in fits)/24
            self.assertAlmostEqual(observed['fit_ce'],reference)
            scale=sum((i+1)**2 for i in range(24))/24
            total=sum(float(layer.mlp[0].down_proj.weight.sum().detach()) for layer in model.layers)
            for derivative in gradients.values():
                torch.testing.assert_close(derivative,torch.full_like(derivative,2*scale*total),rtol=1e-6,atol=1e-3)
            for i in range(14):
                mean_prediction=sum(v[i] for v in observed['predicted_fit_gain_by_id'].values())/24
                self.assertAlmostEqual(mean_prediction,-float(gradients[i].sum()),delta=1e-3)
            self.assertEqual(adapter.counts['supervised_target_tokens_gradient'],72)
            adapter.close()
        for name,p in model.named_parameters():
            self.assertIsNone(p.grad)
            self.assertTrue(torch.equal(p,before[name]))

    def test_endpoint_rotation_is_not_assumed_to_be_scalar_transport(self):
        base=dict(prefix_endpoint=torch.zeros(2,2),answer_endpoint=torch.zeros(1,2))
        target=dict(prefix_endpoint=torch.tensor([[1.,0.],[1.,0.]]),answer_endpoint=torch.tensor([[1.,0.]]))
        rotated=dict(prefix_endpoint=torch.tensor([[0.,1.],[0.,1.]]),answer_endpoint=torch.tensor([[0.,1.]]))
        proof=api.endpoint_transfer(base,target,rotated)
        self.assertEqual(proof['answer_endpoint']['projection'],0.)
        self.assertEqual(proof['answer_endpoint']['orthogonal_ratio'],1.)

    def test_zero_oracle_direction_has_explicit_status(self):
        z=dict(prefix_endpoint=torch.zeros(2,2),answer_endpoint=torch.zeros(1,2))
        proof=api.endpoint_transfer(z,z,z)
        self.assertEqual(proof['answer_endpoint']['status'],'ZERO_ORACLE_DIRECTION')


if __name__=='__main__':unittest.main()
