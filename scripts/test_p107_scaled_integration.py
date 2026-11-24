"""Synthetic CPU consumed-group scaling integration; never construct Native."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

import numpy as np
import torch
from torch import nn

from scripts.p107_scaled_optimizer_group import ScaledOptimizerGroup,ScaleConfig,checksum
from tinylm.train.adaptive_training import AdaptiveMNTPTrainer,SyntheticDocumentStream,CONSUME_SCALED_GROUP,SCALED_SCHEMA,SCALED_KD_SCHEMA
from tinylm.train.adaptive_masking import PolicyConfig
from tinylm.train.causal_teacher import CausalTeacherKL
from tinylm.train.hybrid_session import HybridTrainingSession
from scripts import test_p107_adaptive_training as old_fixture

ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'handoff/audit/research_20261118_01a1e647'
spec=importlib.util.spec_from_file_location('p107_before_scaled_digest',A/'capture_p107_before_scaled_bridge_v1.py')
oracle_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle_module)


class ToyBuffered(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding=nn.Embedding(64,8);self.body=nn.Linear(8,8)
        self.dropout=nn.Dropout(.2);self.head=nn.Linear(8,64)
        self.register_buffer('seen_forwards',torch.zeros((),dtype=torch.long))

    def forward(self,tokens,attention_mask):
        if self.training:self.seen_forwards.add_(1)
        h=self.embedding(tokens);mask=attention_mask[:,0].to(h.dtype)
        mixed=mask@h/mask.sum(-1,keepdim=True)
        return self.head(self.dropout(torch.tanh(self.body(mixed))))


def make(*,enabled=True,kd=False,policy=CONSUME_SCALED_GROUP,backwards=4,factory_signature='C'*64):
    torch.set_num_threads(1);random.seed(211);np.random.seed(307);torch.manual_seed(1337)
    model=ToyBuffered();parameters=list(model.parameters())
    matrix=[model.body.weight];aux=[p for p in parameters if p is not model.body.weight]
    optimizers=[torch.optim.SGD(matrix,lr=.01,momentum=.9),torch.optim.AdamW(aux,lr=.001)]
    config=PolicyConfig(64,.5,.2,2,'keep',23,34,13,'A'*64,'B'*64)
    teacher=None
    options=dict(policy_config=config,mode='adaptive',masked_micros=2,signature='C'*64,
                 collect_ids=old_fixture.predictions)
    if kd:
        teacher=ToyBuffered().eval().requires_grad_(False)
        options['causal_distillation']=CausalTeacherKL(teacher,vocab_size=64,
            student_tokenizer_sha256='D'*64,teacher_tokenizer_sha256='D'*64,
            teacher_identity_sha256='E'*64,chunk_rows=3)
    if enabled:
        def factory():
            return ScaledOptimizerGroup(parameters,optimizers,run_signature=factory_signature,
                expected_backwards=backwards,config=ScaleConfig(init_scale=64.,growth_interval=2))
        options.update(scaled_group_factory=factory,overflow_policy=policy)
    trainer=AdaptiveMNTPTrainer(model,optimizers,SyntheticDocumentStream(),**options)
    return trainer,teacher


class ScaledTrainerContracts(unittest.TestCase):
    assert_tree=old_fixture.TrainingBoundaryTests.assert_tree

    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():raise RuntimeError('CPU integration requires uninitialized CUDA')

    @classmethod
    def tearDownClass(cls):
        if torch.cuda.is_initialized():raise RuntimeError('CPU integration initialized CUDA')

    def overflow_update(self,trainer):
        handle=trainer.model.body.weight.register_hook(lambda value:value*float('inf'))
        try:return trainer.update()
        finally:handle.remove()

    def test_none_default_three_modes_match_all_before_source_loss_and_state_hashes(self):
        before=json.loads((A/'P107_BEFORE_SCALED_BRIDGE_NONE_ORACLE_v1.json').read_text())
        for mode,expected in before['modes'].items():
            random.seed(211);np.random.seed(307);torch.manual_seed(1337)
            trainer=old_fixture.make(mode)
            for index,wanted in enumerate(expected['rows']):
                row=trainer.update()
                self.assertEqual({key:row[key]for key in wanted},wanted)
                self.assertEqual(oracle_module.state_sha(trainer.state_dict()),expected['complete_state_hashes'][index])
            self.assertNotIn('scaled_optimizer_group',trainer.state_dict())

    def test_finite_scaled_trainer_matches_same_unscaled_synthetic_reference(self):
        reference,_=make(enabled=False);expected_rows=[reference.update()for _ in range(3)];state=reference.state_dict()
        current,_=make();rows=[current.update()for _ in range(3)];actual=current.state_dict()
        for a,b in zip(expected_rows,rows):
            for name in('loss','causal_targets','masked_targets','policy_commit'):
                self.assert_tree(a[name],b[name])
            self.assertTrue(b['optimizer_applied']);self.assertEqual(b['completion_unit'],'CONSUMED_INPUT_GROUP')
        for name in('model','optimizers','policy','source','rng','uniform_rng'):
            self.assert_tree(state[name],actual[name])
        self.assertEqual(actual['schema'],SCALED_SCHEMA)
        self.assertEqual((current.cursor,current.scaled_group.steps,current.scaled_group.skips),(3,3,0))

    def test_overflow_consumes_one_source_policy_buffer_group_without_any_optimizer_step(self):
        trainer,_=make();before=trainer.state_dict()
        row=self.overflow_update(trainer);after=trainer.state_dict()
        self.assertFalse(row['optimizer_applied']);self.assertIsNone(row['pre_clip_gradient_norm'])
        self.assertEqual(row['scaled_optimizer_group']['status'],'SKIPPED_ALL_NONFINITE')
        for name,value in trainer.model.named_parameters():self.assertTrue(torch.equal(value,before['model'][name]))
        self.assert_tree(before['optimizers'],after['optimizers'])
        self.assertEqual((trainer.cursor,trainer.source.cursor,trainer.policy.next_update),(1,1,1))
        self.assertEqual((trainer.scaled_group.attempts,trainer.scaled_group.steps,trainer.scaled_group.skips),(1,0,1))
        self.assertEqual(int(trainer.model.seen_forwards),4)
        self.assertEqual(trainer.policy.observed_micro_batches,2)
        self.assertEqual(after['scaled_optimizer_group']['scaler']['scale'],32.)
        self.assertFalse(torch.equal(before['rng']['torch'],after['rng']['torch']))

    def test_fresh_complete_resume_after_overflow_reproduces_next_two_updates_and_full_state(self):
        trainer,_=make();self.overflow_update(trainer);saved=trainer.state_dict()
        expected=[trainer.update()for _ in range(2)];wanted=trainer.state_dict()
        resumed,_=make();old_scaler=resumed.scaled_group
        resumed.load_state_dict(saved);self.assertIsNot(resumed.scaled_group,old_scaler)
        actual=[resumed.update()for _ in range(2)]
        for a,b in zip(expected,actual):
            for key in('loss','masked_targets','causal_targets','policy_commit','scaled_optimizer_group'):
                self.assert_tree(a[key],b[key])
        self.assert_tree(wanted,resumed.state_dict())

    def test_schedule_advances_by_consumed_groups_and_reports_applied_steps_separately(self):
        trainer,_=make();session=HybridTrainingSession(trainer,total_updates=5,warmup_updates=1,schedule='cosine')
        handle=trainer.model.body.weight.register_hook(lambda value:value*float('inf'))
        try:skipped=session.update()
        finally:handle.remove()
        self.assertFalse(skipped['optimizer_applied'])
        self.assertEqual(session.cursor,1);self.assertEqual(trainer.scaled_group.steps,0)
        row=session.update();saved=session.state_dict()
        expected=session.update();wanted=session.state_dict()
        other,_=make();resumed=HybridTrainingSession(other,total_updates=5,warmup_updates=1,schedule='cosine')
        resumed.load_state_dict(saved);actual=resumed.update()
        self.assertEqual(expected['schedule_lrs'],actual['schedule_lrs'])
        self.assertEqual(expected['loss'],actual['loss']);self.assert_tree(wanted,resumed.state_dict())
        self.assertEqual((session.cursor,trainer.scaled_group.steps,trainer.scaled_group.skips),(3,2,1))

    def test_causal_teacher_stays_frozen_and_scaled_kd_boundary_resumes(self):
        trainer,teacher=make(kd=True);before=copy.deepcopy(teacher.state_dict())
        with patch.object(teacher,'forward',wraps=teacher.forward)as calls:row=trainer.update()
        self.assertEqual(calls.call_count,2);self.assertEqual(row['teacher_forwards'],2)
        self.assert_tree(before,teacher.state_dict());self.assertTrue(all(p.grad is None for p in teacher.parameters()))
        saved=trainer.state_dict();self.assertEqual(saved['schema'],SCALED_KD_SCHEMA)
        wanted_row=trainer.update();wanted=trainer.state_dict()
        other,_=make(kd=True);other.load_state_dict(saved);actual=other.update()
        self.assertEqual(wanted_row['loss'],actual['loss']);self.assert_tree(wanted,other.state_dict())

    def test_exact_policy_and_factory_run_binding_are_required(self):
        for policy in(None,'REPLAY','ABORT'):
            with self.assertRaises(ValueError):make(policy=policy)
        with self.assertRaises(ValueError):make(factory_signature='F'*64)

    def test_wrong_backward_count_is_refused_before_forward_and_source_is_restored(self):
        trainer,_=make(backwards=3);before=trainer.state_dict()
        with patch.object(trainer.model,'forward',side_effect=AssertionError('forward forbidden')):
            with self.assertRaisesRegex(ValueError,'all supplied micros'):trainer.update()
        self.assertFalse(trainer.dirty);self.assert_tree(before,trainer.state_dict())

    def test_corrupt_scaler_checkpoint_is_rejected_before_any_model_weight_copy(self):
        trainer,_=make();trainer.update();saved=trainer.state_dict()
        saved['model']['body.weight'].fill_(999.)
        saved['scaled_optimizer_group']['scaler']['scale']=0.
        value=saved['scaled_optimizer_group']
        value['state_sha256']=checksum({k:v for k,v in value.items()if k!='state_sha256'})
        other,_=make();before=other.state_dict()
        with self.assertRaisesRegex(ValueError,'saved scale'):other.load_state_dict(saved)
        self.assert_tree(before,other.state_dict())

    def test_partial_optimizer_failure_requires_full_restore_and_fresh_controller(self):
        trainer,_=make();saved=trainer.state_dict();prior=trainer.scaled_group
        with patch.object(trainer.optimizers[1],'step',side_effect=RuntimeError('partial optimizer failure')):
            with self.assertRaisesRegex(RuntimeError,'partial optimizer failure'):trainer.update()
        self.assertTrue(trainer.dirty);self.assertEqual(prior.phase,'FAILED')
        with self.assertRaises(ValueError):trainer.state_dict()
        checked=prior.validate_checkpoint(saved['scaled_optimizer_group'])
        self.assertEqual(checked,saved['scaled_optimizer_group'])
        trainer.load_state_dict(saved);self.assertIsNot(trainer.scaled_group,prior)
        self.assertFalse(trainer.dirty);self.assert_tree(saved,trainer.state_dict())
        self.assertTrue(trainer.update()['optimizer_applied'])

    def test_scaled_and_unscaled_boundary_schemas_cannot_be_silently_cross_loaded(self):
        scaled,_=make();a=scaled.state_dict();plain,_=make(enabled=False);b=plain.state_dict()
        with self.assertRaises(ValueError):plain.load_state_dict(a)
        with self.assertRaises(ValueError):scaled.load_state_dict(b)


if __name__=='__main__':unittest.main()
