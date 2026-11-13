import unittest
import torch
from scripts import p108_query_value as q
from scripts import p108_value_edit as v


class QueryValue(unittest.TestCase):
    def test_prompt_end_is_before_all_teacher_forced_answer_tokens(self):
        x,y,start=v.target_window([11,12,13],[21,22])
        self.assertEqual(q.prompt_end(dict(x=torch.tensor([x]),prompt_ids=[11,12,13],start=start)),2)
        self.assertEqual(len(x)-start,len(y))

    def test_changed_prefix_shift_and_empty_prompt_are_rejected(self):
        for d in [dict(x=torch.tensor([[1,2]]),prompt_ids=[],start=0),
                  dict(x=torch.tensor([[1,3]]),prompt_ids=[1,2],start=1),
                  dict(x=torch.tensor([[1,2]]),prompt_ids=[1,2],start=0)]:
            with self.assertRaises(ValueError):q.prompt_end(d)

    def test_private_adapter_reuses_bytecode_without_mutating_globals(self):
        def original(x):return pack(x)+oracle(x)
        new=q.adapt_optimizer(original,lambda x:x*2,lambda x:x*3)
        self.assertIs(new.__code__,original.__code__)
        self.assertIsNot(new.__globals__,original.__globals__)
        self.assertNotIn('pack',original.__globals__)
        self.assertEqual(new(7),35)

    def test_real_optimizer_adaptation_and_decode_only_once(self):
        from scripts import diag_p108_value_edit as prior
        pack0,oracle0=prior.pack,prior.oracle
        adapted=q.adapt_optimizer(prior.optimize_value,lambda *a:None,lambda *a:None)
        self.assertIs(adapted.__code__,prior.optimize_value.__code__)
        self.assertIs(prior.pack,pack0);self.assertIs(prior.oracle,oracle0)
        m=torch.nn.Identity()
        with v.inject(m,2,torch.ones(4)):
            first=m(torch.zeros(1,3,4));second=m(torch.zeros(1,1,4))
        self.assertTrue(torch.equal(first[0,2],torch.ones(4)))
        self.assertTrue(torch.equal(second,torch.zeros(1,1,4)))

    def test_private_optimizer_value_gradient_uses_prompt_position(self):
        from types import SimpleNamespace
        from contextlib import contextmanager
        from scripts import diag_p108_value_edit as prior
        torch.manual_seed(901)
        module=torch.nn.Linear(3,2,bias=False)
        x=torch.randn(1,4,3)
        def packed(_active,_row):
            return dict(x=x,targets=torch.tensor([0,1]),position=2,start=2)
        @contextmanager
        def local_oracle(_active,m,_row,delta):
            with v.inject(m,2,delta):yield
        adapted=q.adapt_optimizer(prior.optimize_value,packed,local_oracle)
        class CPUOnlyTorch:
            def __getattr__(self,name):return getattr(torch,name)
            def zeros(self,*args,**kwargs):
                if kwargs.get('device')!='cuda':raise AssertionError('explicit experiment device changed')
                return torch.zeros(*args,**dict(kwargs,device='cpu'))
        adapted.__globals__['torch']=CPUOnlyTorch()
        adapted.__globals__['target_nll']=lambda _active,item:torch.nn.functional.cross_entropy(module(item['x'])[0,2:],item['targets'])
        adapted.__globals__['prompt_log_probs']=lambda _active,_row:torch.log_softmax(module(x)[0,2],dim=-1)
        p=dict(value_parameterization='relative',value_lr=.01,value_steps=2,
            value_regularization=.01,value_norm_cap=.75,kl_weight=.0625)
        active=dict(cfg=SimpleNamespace(dim=2))
        with v.freeze_parameters(module):
            key,delta,stats=adapted(active,module,[{},{}],[{},{}],p,SimpleNamespace(check=lambda:None))
        self.assertTrue(torch.isfinite(key).all() and torch.isfinite(delta).all())
        self.assertGreater(float(delta.norm()),0)
        self.assertEqual(stats['supervised_target_token_exposures'],8)
        self.assertIsNone(module.weight.grad)
        self.assertFalse(module._forward_hooks)


if __name__=='__main__':unittest.main()
