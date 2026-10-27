"""CPU scalar oracles, RNG preservation, policy transactions and resume."""
import copy
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

import torch
from tinylm.train import hybrid_mntp as h
from tinylm.train.adaptive_masking import (PolicyConfig,HardMaskPolicy,capped_probabilities,
                                          state_fingerprint,audit_selection,VECTORS)

torch.set_num_threads(1)


def config(**kwargs):
    values = dict(vocab_size=128,mask_rate=.15,ema=.2,refresh_updates=2,unseen_policy='keep',
                  seed=1337,special_max=34,mask_id=13,corpus_sha256='A'*64,run_sha256='B'*64)
    values.update(kwargs)
    return PolicyConfig(**values)


def source(index=0):
    tokens = ((torch.arange(65)[None,:]+torch.arange(2)[:,None]*11+index*7)%80+35).long()
    docs = (torch.arange(65)//16).clamp_max(3)[None,:].expand(2,-1).clone().long()
    return tokens,docs


def known_batch():
    tokens = torch.tensor([[40,41,42,43,44,45,46,47,48]])
    docs = torch.zeros_like(tokens)
    selected = torch.tensor([[False,True,True,False,True,False,False,False,False]])
    batch = h.mntp_batch(tokens,docs,selected,vocab_size=128)
    # Shifted predictions: gold41 is right, gold42 wrong, gold44 right.
    predictions = torch.zeros_like(batch.targets)
    predictions[0,0] = 41; predictions[0,1] = 99; predictions[0,3] = 44
    return batch,predictions


def run_update(policy,index):
    policy.begin_update(index,split='train',expected_observations=1)
    tokens,docs = source(index)
    selected,probabilities = policy.select(tokens,docs,adaptive=True)
    batch = h.mntp_batch(tokens,docs,selected,vocab_size=128)
    predictions = torch.where(batch.targets % 2 == 0,batch.targets,torch.zeros_like(batch.targets)).clamp_min(0)
    policy.observe(batch,predictions,observation_index=0)
    policy.finish_update(accepted=True)
    return selected,probabilities


class ProbabilityContract(unittest.TestCase):
    def test_uniform_and_empty_weights(self):
        self.assertEqual(capped_probabilities(torch.ones(0),.15).numel(),0)
        self.assertTrue(torch.equal(capped_probabilities(torch.ones(5),.15),torch.full((5,),.15,dtype=torch.float64)))
        self.assertTrue(torch.equal(capped_probabilities(torch.tensor([1.,2.,3.]),1),torch.ones(3,dtype=torch.float64)))

    def test_saturation_preserves_budget_instead_of_naive_clip(self):
        # Expected budget1.5: the heavy token saturates at1, remaining tokens .25 each.
        actual = capped_probabilities(torch.tensor([100.,1.,1.],dtype=torch.float64),.5)
        self.assertTrue(torch.allclose(actual,torch.tensor([1.,.25,.25],dtype=torch.float64),atol=1e-12,rtol=0))
        self.assertAlmostEqual(float(actual.sum()),1.5,places=12)

    def test_scalar_bisection_oracle_random_extreme_and_small_rates(self):
        generator = torch.Generator().manual_seed(37)
        for n in (1,2,7,65):
            for rate in (.01,.15,.7,.99):
                weights = (torch.randn(n,generator=generator,dtype=torch.float64)*6).exp()
                low,high = 0.,1.
                values = weights.tolist(); target=rate*n
                while sum(min(high*x,1.) for x in values) < target: high *= 2
                for _ in range(180):
                    mid=(low+high)/2
                    if sum(min(mid*x,1.) for x in values) < target: low=mid
                    else: high=mid
                expected=torch.tensor([min(high*x,1.) for x in values],dtype=torch.float64)
                actual=capped_probabilities(weights,rate)
                self.assertTrue(torch.allclose(actual,expected,atol=1e-10,rtol=1e-9))

    def test_invalid_probabilities_rejected(self):
        for weights in (torch.tensor([0.,1.]),torch.tensor([-1.]),torch.tensor([float('nan')]),torch.ones(1,1)):
            with self.assertRaises(ValueError): capped_probabilities(weights,.15)
        for rate in (0,-1,1.1,float('nan'),True):
            with self.assertRaises(ValueError): capped_probabilities(torch.ones(2),rate)

    def test_extreme_finite_weights_keep_tiny_relative_budget(self):
        for values,rate in (([1e308,5e307],1e-300),([1e-320,2e-320],.15),([1e308,1e-308],.75)):
            actual=capped_probabilities(torch.tensor(values,dtype=torch.float64),rate)
            self.assertTrue(bool(torch.isfinite(actual).all()))
            self.assertLessEqual(abs(float(actual.sum())/(rate*2)-1),5e-12)
        self.assertTrue(torch.allclose(actual,torch.tensor([1.,.5],dtype=torch.float64),atol=1e-12,rtol=0))


class PolicyContract(unittest.TestCase):
    def test_initial_uniform_selection_and_next_rng_equal_original_full_shape(self):
        for adaptive in (False,True):
            policy=HardMaskPolicy(config());policy.begin_update(0,split='train',expected_observations=1)
            generator=torch.Generator().manual_seed(1337)
            for index in range(5):
                tokens,docs=source(index)
                actual,_=policy.select(tokens,docs,adaptive=adaptive)
                expected=h.uniform_mntp_selection(tokens,docs,vocab_size=128,probability=.15,generator=generator)
                self.assertTrue(torch.equal(actual,expected))
                self.assertTrue(torch.equal(policy.generator.get_state(),generator.get_state()))
            policy.finish_update(accepted=False)

    def test_shifted_gold_histogram_not_same_input_position(self):
        policy=HardMaskPolicy(config(refresh_updates=3));policy.begin_update(0,split='train',expected_observations=1)
        batch,predictions=known_batch();policy.observe(batch,predictions,observation_index=0);policy.finish_update(accepted=True)
        self.assertEqual([int(policy.total[i]) for i in (41,42,44)],[1,1,1])
        self.assertEqual([int(policy.correct[i]) for i in (41,42,44)],[1,0,1])
        self.assertEqual(int(policy.total[13]),0)
        self.assertEqual(int(policy.total[40]),0)

    def test_uniform_boundary_draw_rounding_matches_original_python_scalar(self):
        policy=HardMaskPolicy(config(mask_rate=.7));policy.begin_update(0,split='train',expected_observations=1)
        tokens,docs=source();draws=torch.full(tokens.shape,.7,dtype=torch.float32)
        with patch.object(torch,'rand',return_value=draws):
            actual,probabilities=policy.select(tokens,docs,adaptive=True)
            expected=h.uniform_mntp_selection(tokens,docs,vocab_size=128,probability=.7,generator=torch.Generator())
        self.assertTrue(torch.equal(actual,expected));self.assertFalse(bool(actual.any()))
        eligible=h.eligible_mntp(tokens,docs,vocab_size=128)
        self.assertTrue(bool((draws.double()[eligible]<probabilities[eligible]).all()))
        policy.finish_update(accepted=False)

    def test_resume_rejects_different_rng_draw_dtype(self):
        state=HardMaskPolicy(config()).state_dict();before=torch.get_default_dtype()
        try:
            torch.set_default_dtype(torch.float64)
            with self.assertRaises(ValueError):HardMaskPolicy(config()).load_state_dict(state)
        finally:torch.set_default_dtype(before)

    def test_literal_smoothed_accuracy_ema_and_two_unseen_contracts(self):
        for unseen in ('keep','prior'):
            policy=HardMaskPolicy(config(refresh_updates=1,unseen_policy=unseen))
            policy.begin_update(0,split='train',expected_observations=1);batch,predictions=known_batch()
            policy.observe(batch,predictions,observation_index=0);policy.finish_update(accepted=True)
            self.assertAlmostEqual(float(policy.weights[41]),.2+.8*.25,places=12)
            self.assertAlmostEqual(float(policy.weights[42]),.2+.8*.75,places=12)
            self.assertAlmostEqual(float(policy.weights[100]),1. if unseen=='keep' else .6,places=12)
            self.assertEqual(int(policy.total.sum()),0);self.assertEqual(int(policy.correct.sum()),0)
            self.assertEqual(int(policy.lifetime_total.sum()),3)

    def test_duplicate_gold_types_are_summed_not_last_write_wins(self):
        tokens=torch.tensor([[40,41,41,41,42]])
        docs=torch.zeros_like(tokens);selected=torch.tensor([[False,True,True,True,False]])
        batch=h.mntp_batch(tokens,docs,selected,vocab_size=128)
        predictions=torch.tensor([[41,99,41,0]])
        policy=HardMaskPolicy(config(refresh_updates=4));policy.begin_update(0,split='train',expected_observations=1)
        policy.observe(batch,predictions,observation_index=0);policy.finish_update(accepted=True)
        self.assertEqual((int(policy.total[41]),int(policy.correct[41])),(3,2))

    def test_partial_update_discard_restores_rng_stats_and_same_next_selection(self):
        policy=HardMaskPolicy(config());before=policy.state_dict()
        policy.begin_update(0,split='train',expected_observations=1);tokens,docs=source()
        selected,_=policy.select(tokens,docs,adaptive=True)
        batch,predictions=known_batch();policy.observe(batch,predictions,observation_index=0)
        policy.finish_update(accepted=False)
        self.assertEqual(policy.state_dict()['fingerprint'],before['fingerprint'])
        policy.begin_update(0,split='train',expected_observations=1);again,_=policy.select(tokens,docs,adaptive=True)
        self.assertTrue(torch.equal(selected,again));policy.finish_update(accepted=False)

    def test_weights_frozen_during_update_and_state_not_exported_mid_update(self):
        policy=HardMaskPolicy(config(refresh_updates=1));policy.begin_update(0,split='train',expected_observations=1)
        tokens,docs=source();_,before=policy.probabilities(tokens,docs,adaptive=True)
        batch,predictions=known_batch();policy.observe(batch,predictions,observation_index=0)
        _,after=policy.probabilities(tokens,docs,adaptive=True)
        self.assertTrue(torch.equal(before,after))
        with self.assertRaises(ValueError):policy.state_dict()
        policy.finish_update(accepted=True)

    def test_missing_duplicate_or_out_of_order_observations_cannot_commit(self):
        policy=HardMaskPolicy(config());before=policy.state_dict()['fingerprint']
        policy.begin_update(0,split='train',expected_observations=2)
        batch,predictions=known_batch()
        with self.assertRaises(ValueError):policy.observe(batch,predictions,observation_index=1)
        policy.observe(batch,predictions,observation_index=0)
        with self.assertRaises(ValueError):policy.finish_update(accepted=True)
        with self.assertRaises(ValueError):policy.observe(batch,predictions,observation_index=0)
        policy.finish_update(accepted=False)
        self.assertEqual(policy.state_dict()['fingerprint'],before)

    def test_resume_next_selection_next_statistics_and_next_refresh_equal_uninterrupted(self):
        left=HardMaskPolicy(config())
        for update in range(3):run_update(left,update)
        saved=left.state_dict();right=HardMaskPolicy(config());right.load_state_dict(saved)
        for update in range(3,8):
            a,p=run_update(left,update);b,q=run_update(right,update)
            self.assertTrue(torch.equal(a,b));self.assertTrue(torch.equal(p,q))
            self.assertEqual(left.state_dict()['fingerprint'],right.state_dict()['fingerprint'])

    def test_load_clones_state_and_rejects_config_schema_bad_counters_and_fingerprint(self):
        policy=HardMaskPolicy(config());run_update(policy,0);saved=policy.state_dict()
        loaded=HardMaskPolicy(config());loaded.load_state_dict(saved)
        old=loaded.state_dict()['fingerprint'];saved['weights'].fill_(.5)
        self.assertEqual(loaded.state_dict()['fingerprint'],old)
        with self.assertRaises(ValueError):HardMaskPolicy(config(corpus_sha256='C'*64)).load_state_dict(policy.state_dict())
        for kind in ('fingerprint','negative','correct','last_seen','grad'):
            state=policy.state_dict()
            if kind=='fingerprint':state['weights'][41]=.5
            elif kind=='negative':state['total'][41]=-1
            elif kind=='correct':state['correct'][41]=state['total'][41]+1
            elif kind=='last_seen':state['last_seen'][41]=state['next_update']
            else:state['weights'].requires_grad_(True)
            if kind!='fingerprint':state['fingerprint']=state_fingerprint(state)
            with self.subTest(kind=kind),self.assertRaises(ValueError):HardMaskPolicy(config()).load_state_dict(state)

    def test_refingerprinted_unreachable_states_are_rejected_atomically(self):
        for kind in ('initial_observation','initial_weight','initial_rng','old_window','protected','last_seen_window','unseen_weight'):
            origin=HardMaskPolicy(config())
            if kind in ('old_window','protected','unseen_weight'):
                run_update(origin,0);run_update(origin,1)
            elif kind=='last_seen_window':run_update(origin,0)
            state=origin.state_dict()
            if kind=='initial_observation':state['observed_micro_batches']=1
            elif kind in ('initial_weight','unseen_weight'):state['weights'][120]=.5
            elif kind=='initial_rng':state['rng']=torch.Generator().manual_seed(99).get_state()
            elif kind=='old_window':
                state['total'][41]=state['correct'][41]=1
                state['lifetime_total'][41]=max(1,int(state['lifetime_total'][41]));state['last_seen'][41]=1
            elif kind=='protected':
                state['lifetime_total'][13]=1;state['last_seen'][13]=1
            else:
                index=int(torch.nonzero(state['total']>0)[0]);state['total'][index]=state['correct'][index]=0
            state['fingerprint']=state_fingerprint(state)
            destination=HardMaskPolicy(config());before=destination.state_dict()['fingerprint']
            with self.subTest(kind=kind),self.assertRaises(ValueError):destination.load_state_dict(state)
            self.assertEqual(destination.state_dict()['fingerprint'],before)

    def test_cpu_policy_ignores_ambient_meta_factory_device(self):
        tokens,docs=source();expected=HardMaskPolicy(config())
        expected.begin_update(0,split='train',expected_observations=1)
        a,p=expected.select(tokens,docs,adaptive=True)
        with torch.device('meta'):
            actual=HardMaskPolicy(config());actual.begin_update(0,split='train',expected_observations=1)
            b,q=actual.select(tokens,docs,adaptive=True)
            normalized=capped_probabilities(torch.tensor([2.,1.],device='cpu'),.7)
        self.assertTrue(torch.equal(a,b));self.assertTrue(torch.equal(p,q))
        self.assertEqual(normalized.device.type,'cpu')
        actual.finish_update(accepted=False);expected.finish_update(accepted=False)

    def test_first_window_weights_and_lifetime_cannot_be_rewritten(self):
        for kind in ('weight','missing_count'):
            origin=HardMaskPolicy(config());batch,predictions=known_batch()
            origin.begin_update(0,split='train',expected_observations=1)
            origin.observe(batch,predictions,observation_index=0)
            origin.finish_update(accepted=True);state=origin.state_dict()
            if kind=='weight':state['weights'][41]=.5
            else:state['lifetime_total'][41]+=1
            state['fingerprint']=state_fingerprint(state)
            with self.subTest(kind=kind),self.assertRaises(ValueError):HardMaskPolicy(config()).load_state_dict(state)

    def test_long_repeated_fp64_prior_ema_resumes_without_closed_form_rejection(self):
        cfg=config(ema=1-2**-53,refresh_updates=1,unseen_policy='prior')
        origin=HardMaskPolicy(cfg);batch,predictions=known_batch()
        for index in range(20000):
            origin.begin_update(index,split='train',expected_observations=1)
            origin.observe(batch,predictions,observation_index=0);origin.finish_update(accepted=True)
        state=origin.state_dict();loaded=HardMaskPolicy(cfg);loaded.load_state_dict(state)
        self.assertEqual(loaded.state_dict()['fingerprint'],state['fingerprint'])
        self.assertEqual(float(state['weights'][13]),1.)

    def test_non_train_wrong_update_causal_and_empty_observation_rejected(self):
        policy=HardMaskPolicy(config())
        for split in ('dev','test','eval'):
            with self.assertRaises(ValueError):policy.begin_update(0,split=split,expected_observations=1)
        with self.assertRaises(ValueError):policy.begin_update(1,split='train',expected_observations=1)
        policy.begin_update(0,split='train',expected_observations=1);tokens,docs=source()
        for batch in (h.causal_batch(tokens,docs,vocab_size=128),
                      h.mntp_batch(tokens,docs,torch.zeros_like(tokens,dtype=torch.bool),vocab_size=128)):
            with self.assertRaises(ValueError):policy.observe(batch,torch.zeros_like(batch.targets),observation_index=0)
        policy.finish_update(accepted=False)

    def test_all_protected_or_all_pad_never_force_a_target(self):
        policy=HardMaskPolicy(config());policy.begin_update(0,split='train',expected_observations=1)
        for tokens,docs in ((torch.full((1,5),2),torch.zeros(1,5,dtype=torch.long)),
                            (torch.zeros(1,5,dtype=torch.long),torch.full((1,5),-1,dtype=torch.long))):
            selected,probabilities=policy.select(tokens,docs,adaptive=True)
            self.assertFalse(bool(selected.any()));self.assertEqual(float(probabilities.sum()),0.)
        policy.finish_update(accepted=False)

    def test_actual_owned_storage_and_rng_representation_are_separate(self):
        policy=HardMaskPolicy(config());report=policy.storage_audit()
        self.assertEqual(report['owned_tensor_storage_bytes'],128*40)
        self.assertIsNone(report['native_generator_bytes'])
        self.assertEqual(report['state_representation_bytes'],128*40+report['rng_export_bytes'])
        policy.begin_update(0,split='train',expected_observations=1);active=policy.storage_audit()
        self.assertEqual(active['owned_tensor_storage_bytes'],128*56+report['rng_export_bytes'])
        policy.finish_update(accepted=False)

    def test_declared_overlapping_groups_have_independent_denominators(self):
        eligible=torch.tensor([[True,True,True,False]])
        selected=torch.tensor([[True,False,True,False]])
        probabilities=torch.tensor([[.8,.4,.3,0.]],dtype=torch.float64)
        result=audit_selection(eligible,selected,probabilities,
                              {'all':torch.ones_like(eligible),'overlap':torch.tensor([[True,False,True,True]])})
        self.assertEqual((result['all']['eligible'],result['all']['selected']),(3,2))
        self.assertAlmostEqual(result['all']['expected'],1.5)
        self.assertEqual((result['overlap']['eligible'],result['overlap']['selected']),(2,2))


if __name__=='__main__':
    unittest.main()
