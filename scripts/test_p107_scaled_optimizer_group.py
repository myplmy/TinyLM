"""Small CPU parameter/optimizer arithmetic only; no model or old checkpoint."""
from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

import torch

from scripts import p107_scaled_optimizer_group as core


class ScaledGroupContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():raise RuntimeError('CPU scaler tests require uninitialized CUDA')

    @classmethod
    def tearDownClass(cls):
        if torch.cuda.is_initialized():raise RuntimeError('CPU scaler tests initialized CUDA')

    def fixture(self,**options):
        params=[torch.tensor([[.3,-.2,.1],[.4,.5,-.1]],requires_grad=True),
                torch.tensor([-.2,.1,.3],requires_grad=True)]
        opts=[torch.optim.SGD([params[0]],lr=.03,momentum=.9,weight_decay=.01,foreach=False),
              torch.optim.AdamW([params[1]],lr=.003,betas=(.9,.99),eps=1e-8,weight_decay=.02,foreach=False)]
        settings=dict(run_signature='A'*64,expected_backwards=2,
                      config=core.ScaleConfig(init_scale=64.,growth_interval=2))
        settings.update(options)
        return params,opts,core.ScaledOptimizerGroup(params,opts,**settings)

    def losses(self,params):
        xs=[torch.tensor([[.2,-.1],[.4,.3]]),torch.tensor([[-.2,.5],[.1,.7],[.6,-.4]])]
        ys=[torch.tensor([[.3,.4,-.2],[-.1,.2,.6]]),torch.tensor([[.5,-.2,.1],[.1,.4,-.3],[-.2,.6,.2]])]
        return [((x@params[0]+params[1]-y).square().sum()/15)for x,y in zip(xs,ys)]

    def accumulated(self,params,group,overflow=None):
        handle=None
        if overflow is not None:handle=params[overflow].register_hook(lambda value:value*float('inf'))
        try:
            for loss in self.losses(params):group.backward(loss)
        finally:
            if handle is not None:handle.remove()

    def step(self,params,group,overflow=None,clip=.1):
        self.accumulated(params,group,overflow)
        return group.finish(clip_norm=clip)

    def tree_equal(self,a,b):
        self.assertEqual(type(a),type(b))
        if isinstance(a,torch.Tensor):self.assertTrue(torch.equal(a,b))
        elif isinstance(a,dict):
            self.assertEqual(set(a),set(b))
            for key in a:self.tree_equal(a[key],b[key])
        elif isinstance(a,(tuple,list)):
            self.assertEqual(len(a),len(b))
            for x,y in zip(a,b):self.tree_equal(x,y)
        else:self.assertEqual(a,b)

    def test_finite_accumulation_unscale_clip_and_two_updates_match_unscaled_reference(self):
        expected,optimizers,_unused=self.fixture()
        actual,other,group=self.fixture()
        for index in range(2):
            for loss in self.losses(expected):loss.backward()
            norm=float(torch.nn.utils.clip_grad_norm_(expected,.1,error_if_nonfinite=True))
            for optimizer in optimizers:optimizer.step();optimizer.zero_grad(set_to_none=True)
            row=self.step(actual,group)
            self.assertEqual(row['status'],'STEPPED_ALL')
            self.assertAlmostEqual(row['pre_clip_gradient_norm'],norm,delta=1e-7)
            self.assertEqual(row['optimizer_step_calls'],2)
            for x,y in zip(expected,actual):torch.testing.assert_close(x,y,atol=1e-7,rtol=1e-6)
            for a,b in zip(optimizers,other):self.tree_equal(a.state_dict(),b.state_dict())

    def test_overflow_in_either_optimizer_skips_both_without_parameter_or_optimizer_state_changes(self):
        for overflow in(0,1):
            params,optimizers,group=self.fixture()
            before=[p.detach().clone()for p in params];states=[copy.deepcopy(o.state_dict())for o in optimizers]
            self.accumulated(params,group,overflow)
            with (patch.object(optimizers[0],'step',side_effect=AssertionError('finite peer must not step')),
                  patch.object(optimizers[1],'step',side_effect=AssertionError('overflow peer must not step'))):
                row=group.finish(clip_norm=.1)
            self.assertEqual(row['status'],'SKIPPED_ALL_NONFINITE')
            self.assertEqual((row['optimizer_step_calls'],row['scale_before'],row['scale_after']),(0,64.,32.))
            for x,y in zip(params,before):self.assertTrue(torch.equal(x,y))
            for optimizer,state in zip(optimizers,states):self.tree_equal(optimizer.state_dict(),state)
            self.assertTrue(all(p.grad is None for p in params))
            self.assertEqual((group.attempts,group.steps,group.skips),(1,0,1))

    def test_scale_growth_backoff_and_valid_scales_below_one_follow_group_boundaries(self):
        params,opts,group=self.fixture(config=core.ScaleConfig(init_scale=.5,growth_interval=2))
        rows=[self.step(params,group),self.step(params,group),self.step(params,group,overflow=1),self.step(params,group)]
        self.assertEqual([r['scale_after']for r in rows],[.5,1.,.5,.5])
        self.assertEqual((group.attempts,group.steps,group.skips),(4,3,1))
        self.assertEqual(group.state_dict()['scaler']['_growth_tracker'],1)

    def test_scale_config_normalization_uses_CPU_even_under_another_default_device(self):
        with torch.device('meta'):
            config=core.ScaleConfig(init_scale=.1)
        self.assertEqual(config.init_scale,float(torch.tensor(.1,dtype=torch.float32,device='cpu')))
        self.assertFalse(torch.cuda.is_initialized())

    def test_non_binary_fraction_initial_scale_is_normalized_before_lazy_initialization(self):
        params,opts,group=self.fixture(config=core.ScaleConfig(init_scale=.1,growth_interval=2))
        row=self.step(params,group)
        self.assertEqual(row['scale_before'],float(torch.tensor(.1,dtype=torch.float32)))
        self.assertEqual(row['scale_before'],row['scale_after'])

    def test_all_optimizers_unscale_once_before_clip_and_scale_update_once(self):
        params,opts,group=self.fixture();events=[]
        unscale=group._scaler.unscale_;update=group._scaler.update
        def observed_unscale(optimizer):events.append('unscale'+str(opts.index(optimizer)));return unscale(optimizer)
        def observed_update(*args,**kwargs):events.append('update');return update(*args,**kwargs)
        with patch.object(group._scaler,'unscale_',side_effect=observed_unscale),patch.object(group._scaler,'update',side_effect=observed_update):
            self.step(params,group)
        self.assertEqual(events,['unscale0','unscale1','update'])

    def test_complete_scaler_state_and_caller_owned_optimizer_resume_match_next_step(self):
        params,opts,group=self.fixture();self.step(params,group)
        saved=json.loads(json.dumps(group.state_dict()))
        weights=[p.detach().clone()for p in params];states=[copy.deepcopy(o.state_dict())for o in opts]
        wanted=self.step(params,group);expected=group.state_dict()
        other,other_opts,resumed=self.fixture()
        with torch.no_grad():
            for p,value in zip(other,weights):p.copy_(value)
        for optimizer,state in zip(other_opts,states):optimizer.load_state_dict(state)
        resumed.load_state_dict(saved);actual=self.step(other,resumed)
        self.assertEqual(wanted,actual)
        self.assertEqual(expected,resumed.state_dict())
        for x,y in zip(params,other):self.assertTrue(torch.equal(x,y))
        for a,b in zip(opts,other_opts):self.tree_equal(a.state_dict(),b.state_dict())

    def test_fresh_restore_does_not_reuse_an_interrupted_unscaled_optimizer_stage(self):
        params,opts,group=self.fixture();saved=group.state_dict();self.accumulated(params,group)
        group._scaler.unscale_(opts[0]);group._scaler.load_state_dict(saved['scaler'])
        with self.assertRaisesRegex(RuntimeError,'unscale_'):
            group._scaler.unscale_(opts[0])
        for optimizer in opts:optimizer.zero_grad(set_to_none=True)
        fresh=core.ScaledOptimizerGroup(params,opts,run_signature='A'*64,expected_backwards=2,config=group.config)
        fresh.load_state_dict(saved)
        self.assertEqual(self.step(params,fresh)['status'],'STEPPED_ALL')

    def test_mid_group_export_restore_and_premature_finish_are_rejected(self):
        params,opts,group=self.fixture();saved=group.state_dict()
        group.backward(self.losses(params)[0])
        with self.assertRaises(RuntimeError):group.state_dict()
        with self.assertRaises(RuntimeError):group.load_state_dict(saved)
        with self.assertRaises(RuntimeError):group.finish()
        group.backward(self.losses(params)[1]);self.assertEqual(group.finish()['status'],'STEPPED_ALL')

    def test_partial_optimizer_exception_is_failed_and_not_claimed_as_rollback(self):
        params,opts,group=self.fixture();before=params[0].detach().clone();self.accumulated(params,group)
        with patch.object(opts[1],'step',side_effect=RuntimeError('second optimizer failure')):
            with self.assertRaisesRegex(RuntimeError,'second optimizer failure'):group.finish()
        self.assertFalse(torch.equal(before,params[0]))
        self.assertEqual(group.phase,'FAILED')
        with self.assertRaises(RuntimeError):group.state_dict()
        with self.assertRaises(RuntimeError):group.backward(self.losses(params)[0])

    def test_missing_gradients_fail_before_any_optimizer_step(self):
        params,opts,group=self.fixture()
        for _ in range(2):group.backward(params[0].square().sum())
        with patch.object(opts[0],'step',side_effect=AssertionError('step forbidden')):
            with self.assertRaisesRegex(ValueError,'complete dense gradients'):group.finish()
        self.assertEqual(group.phase,'FAILED')

    def test_scale_or_parameter_changes_during_accumulation_fail_closed(self):
        for kind in('scale','parameter'):
            params,opts,group=self.fixture();group.backward(self.losses(params)[0])
            if kind=='scale':group._scaler.update(new_scale=32.)
            else:
                with torch.no_grad():params[0].add_(.1)
            with self.assertRaisesRegex(ValueError,'changed during accumulation'):
                group.backward(self.losses(params)[1])
            with self.assertRaises(RuntimeError):group.state_dict()

    def test_duplicate_missing_unsupported_or_non_FP32_parameter_ownership_is_rejected(self):
        p=torch.tensor([1.,2.],requires_grad=True);q=torch.tensor([3.],requires_grad=True)
        for parameters,optimizers in[((p,q),[torch.optim.SGD([p],lr=.1)]),
            ((p,),[torch.optim.SGD([p],lr=.1),torch.optim.SGD([p],lr=.1)]),
            ((p,),[torch.optim.SGD([p],lr=.1,differentiable=True)])]:
            with self.assertRaises(ValueError):core.ScaledOptimizerGroup(parameters,optimizers,run_signature='A'*64,expected_backwards=1)
        value=torch.tensor([1.],dtype=torch.float64,requires_grad=True)
        with self.assertRaises(ValueError):core.ScaledOptimizerGroup([value],[torch.optim.SGD([value],lr=.1)],run_signature='A'*64,expected_backwards=1)

    def test_bad_state_hash_identity_counters_and_public_scaler_fields_do_not_mutate_fresh_controller(self):
        params,opts,prior=self.fixture();self.step(params,prior);saved=prior.state_dict()
        variants=[]
        for key,value in(('run_signature','B'*64),('attempts',True),('attempts',99),('source_scope','wrong')):
            item=copy.deepcopy(saved);item[key]=value;variants.append(item)
        for key,value in(('scale',0.),('scale',float('inf')),('_growth_tracker',True),('_growth_tracker',2),('growth_factor',4.)):
            item=copy.deepcopy(saved);item['scaler'][key]=value;variants.append(item)
        for item in variants:
            if item['scaler']['scale']==float('inf'):
                item['state_sha256']='F'*64
            else:item['state_sha256']=core.checksum({k:v for k,v in item.items()if k!='state_sha256'})
            other,other_opts,fresh=self.fixture();before=fresh.state_dict()
            with self.assertRaises((ValueError,TypeError)):fresh.load_state_dict(item)
            self.assertEqual(fresh.state_dict(),before)

    def test_exported_state_is_independent_and_scope_omits_model_optimizer_data_and_rng(self):
        params,opts,group=self.fixture();saved=group.state_dict();original=copy.deepcopy(saved)
        saved['scaler']['scale']=1.;saved['layout']['parameters'][0]['shape'][0]=99
        self.assertEqual(group.state_dict(),original)
        self.assertIn('NOT_MODEL_OPTIMIZER_SOURCE_POLICY_SCHEDULE_OR_RNG',original['source_scope'])
        for key in('model','optimizers','source','rng'):self.assertNotIn(key,original)


if __name__=='__main__':unittest.main()
