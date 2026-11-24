"""Exercise the explicit batch integration using fresh, tiny numerical tensors."""

import copy
import hashlib
import json
import math
import random
import unittest
from unittest.mock import patch

import numpy as np
import torch
from torch.nn import functional as F

from scripts import p106b_dskdv2_contract as dense
from scripts import p106b_dskdv2_training as fixed
from scripts import test_p106b_dskdv2_microbatch as fixtures
from scripts import test_p106b_dskdv2_training as counted
from scripts.p106b_dskdv2_microbatch_training import BatchedScheduledFeatureTrainer, PackedFeatureTrainingUpdate, RAW_POLICY, UPDATE_SCHEMA
from scripts.p106b_dskdv2_scheduled_training import ConsumedGroupSchedule
from scripts.p106b_feature_window import FeatureWindow
from scripts.p107_scaled_optimizer_group import ScaleConfig
from tinylm.train.anneal_schedule import lr_factor
from tinylm.train.mtp_sft import Record, pad_records


CONTROLS = []
BASE_RATES = (.005, .001, .001)
CLIP = .03


class PackedSource:
    """Give each update a KD subset chosen by a checkpointed private RNG."""

    def __init__(self, fixture, phases):
        self.fixture, self.phases = fixture, tuple(phases)
        self.private = random.Random(20261118)
        self.cursor = 0
        self.bad_update = None
        self.contract = dict(schema='NUMERICAL_PACKED_SOURCE_V1', packed_update_schema=UPDATE_SCHEMA,
            student_tokens_policy=RAW_POLICY, phases=list(phases), fixture_manifest_sha256=hashlib.sha256(
                (fixture.root/'fixture_tokens_and_positions.json').read_bytes()).hexdigest().upper(),
            private_rng_semantics='ONE_DROP_INDEX_DRAW_PER_CONSUMED_GROUP')

    def state_dict(self):
        return dict(cursor=self.cursor, private_rng=self.private.getstate())

    def validate_checkpoint(self, state):
        if (type(state) is not dict or set(state) != {'cursor','private_rng'}
                or type(state['cursor']) is not int or not 0 <= state['cursor'] <= len(self.phases)):
            raise ValueError('exact numerical packed-source cursor required')
        random.Random(0).setstate(state['private_rng'])
        return copy.deepcopy(state)

    def load_state_dict(self, state):
        checked = self.validate_checkpoint(state)
        self.cursor = checked['cursor']
        self.private.setstate(checked['private_rng'])

    def next_update(self):
        if self.cursor == len(self.phases):
            raise StopIteration
        ordinal = self.cursor
        self.cursor += 1
        drop = self.private.randrange(len(self.fixture.records))
        rows = copy.deepcopy(self.fixture.rows)
        packed = copy.deepcopy(self.fixture.packed)
        kept = [record for index,record in enumerate(self.fixture.records) if index!=drop]
        reader = FeatureWindow(kept,root=self.fixture.root,
            identities={key:letter*64 for key,letter in zip(
                ('teacher_sha256','tokenizer_sha256','mapping_sha256','data_sha256'),'ABCD')},
            split='train',hidden_width=4,batch_positions=5) if self.phases[ordinal] else None
        if self.bad_update == 'untyped':
            return fixed.FeatureTrainingUpdate(ordinal,rows,reader)
        if self.bad_update == 'shift':
            packed[0]['labels'][1] = (packed[0]['ids'][1]+1) % 11
        return PackedFeatureTrainingUpdate(ordinal,rows,reader,packed)


def fresh_parameters(fixture):
    model = fixtures.TinyTokenStudent(torch.float32,dropout=.25,checkpoint_body=True)
    projector = torch.nn.Parameter(fixture.t2s.detach().clone())
    optimizers = [counted.CountedMuon([model.body,model.input_projection,model.up],lr=BASE_RATES[0],scale_mode='rms'),
        counted.CountedAdamW([model.embedding],lr=BASE_RATES[1]),
        counted.CountedAdamW([projector],lr=BASE_RATES[2],weight_decay=.1)]
    return model,projector,optimizers


def manual_update(fixture, model, projector, optimizers, source, schedule):
    update = source.next_update()
    kd_rows = {} if update.reader is None else {r['row_id']:r for r in update.reader.contract['records']}
    ce_count = sum(row['ce_targets'] for row in update.ce_rows)
    kd_count = sum(len(row['positions']) for row in kd_rows.values())
    records = [Record(row['ids'][:-1],row['labels'][1:],row['turn_ids'][1:]) for row in update.packed_students]
    total = 0.
    for start in range(0,len(records),8):
        x,y,_ = pad_records(records[start:start+8],0,'cpu',fixed_width=8,batch_size=8)
        hidden = model(x,return_hidden=True,use_cache=False,past_kv=None)
        student_head = model.up@model.embedding.T
        logits = hidden@student_head
        loss = F.cross_entropy(logits.reshape(-1,11),y.reshape(-1),ignore_index=-100,reduction='sum')/ce_count
        for j,row in enumerate(update.ce_rows[start:start+8]):
            if row['row_id'] not in kd_rows:
                continue
            positions = kd_rows[row['row_id']]['positions']
            student = [pos['student_predictor_raw_index'] for pos in positions]
            teacher = [pos['teacher_predictor_raw_index'] for pos in positions]
            labels = torch.tensor([pos['mapped_student_argmax'] for pos in positions])
            features = torch.tensor(fixture.features[row['row_id']][teacher])
            terms = dense.dskd_sums(hidden[j,student],features,student_head,fixture.teacher.T,
                projector,fixture.s2t,labels)
            loss = loss+.3*terms['total_sum']/kd_count
        loss.backward()
        total += float(loss.detach())
    active = [0,1,2] if kd_count else [0,1]
    params = list(model.parameters())+([projector] if kd_count else [])
    norm = float(torch.nn.utils.clip_grad_norm_(params,CLIP,error_if_nonfinite=True))
    factor = lr_factor(update.ordinal,schedule.warm,schedule.steps,schedule.sched,schedule.decay_frac)
    for index in active:
        optimizers[index].param_groups[0]['lr'] = BASE_RATES[index]*factor
        optimizers[index].step()
        optimizers[index].zero_grad(set_to_none=True)
    return dict(loss=total,kd_count=kd_count,norm=norm,factor=factor)


class BatchedTrainingTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(12345)
        random.seed(19)
        np.random.seed(23)
        self.fixture = fixtures.Fixture(dtype=torch.float32,dropout=.25,checkpoint_body=True)

    def trainer(self, phases, *, batch_size=8, pad_id=0):
        model,projector,optimizers = fresh_parameters(self.fixture)
        teacher_identity = hashlib.sha256(self.fixture.teacher.numpy().tobytes()).hexdigest().upper()
        return BatchedScheduledFeatureTrainer(model,optimizers,PackedSource(self.fixture,phases),
            schedule=ConsumedGroupSchedule(len(phases),warm=2,sched='cosine'),batch_size=batch_size,pad_id=pad_id,
            signature='F'*64,up=model.up,embedding=model.embedding,teacher_head=self.fixture.teacher,
            t2s=projector,s2t=self.fixture.s2t.detach().clone(),teacher_head_identity=teacher_identity,
            student_width=8,teacher_width=8,mapping=self.fixture.mapping,mapping_modes=self.fixture.modes,
            chunk_positions=2,ce_chunk=3,kd_rate=.3,clip=CLIP,scale_config=ScaleConfig(init_scale=128.,growth_interval=2))

    @staticmethod
    def boundary(owner):
        return owner.state_dict()['scheduled_boundary']['boundary']

    def test_complete_updates_match_manual_fixed_batch_reference(self):
        phases=(True,False,True,True)
        owner = self.trainer(phases)
        initial = self.boundary(owner)
        actual = [owner.step() for _ in phases]
        completed = self.boundary(owner)
        model,projector,optimizers = fresh_parameters(self.fixture)
        source = PackedSource(self.fixture,phases)
        owner._restore_rng(initial['rng'])
        expected = [manual_update(self.fixture,model,projector,optimizers,source,owner.schedule) for _ in phases]
        self.assertTrue(fixed._same(completed['source'],source.state_dict()))
        self.assertTrue(fixed._same(completed['rng'],owner._rng()))
        self.assertEqual(int(model.forward_count),12)
        self.assertEqual(int(owner.model.forward_count),12)
        for got,want in zip(actual,expected):
            self.assertTrue(math.isclose(got['group']['normalized_total'],want['loss'],abs_tol=3e-5,rel_tol=3e-4))
            self.assertTrue(math.isclose(got['scaled_optimizer_group']['pre_clip_gradient_norm'],want['norm'],abs_tol=3e-5,rel_tol=3e-4))
            self.assertEqual(got['group']['global_kd_denominator'],want['kd_count'])
            self.assertEqual(got['group']['global_ce_denominator'],68)
            self.assertEqual(got['group']['microbatch_frames']['released_microbatch_callbacks'],3)
            self.assertEqual(got['lr_schedule']['factor'],want['factor'])
        torch.testing.assert_close(completed['model'],model.state_dict(),atol=3e-6,rtol=5e-5)
        torch.testing.assert_close(completed['external_projectors']['t2s'],projector,atol=3e-6,rtol=5e-5)
        for actual_optimizer, reference_optimizer in zip(completed['optimizers'], optimizers, strict=True):
            reference_state = reference_optimizer.state_dict()
            self.assertEqual(actual_optimizer.keys(), reference_state.keys())
            self.assertEqual(actual_optimizer['param_groups'], reference_state['param_groups'])
            torch.testing.assert_close(actual_optimizer['state'], reference_state['state'], atol=3e-6, rtol=5e-5)
        max_difference = max(float((owner_param.detach()-reference_param.detach()).abs().max())
            for owner_param,reference_param in zip(owner.parameters,[*model.parameters(),projector]))
        CONTROLS.append(dict(name='DENSE_MANUAL_UPDATE',groups=4,parameters=55,max_parameter_error=max_difference,
            max_loss_error=max(abs(a['group']['normalized_total']-b['loss']) for a,b in zip(actual,expected)),
            phases=phases,source_rng_exact=True,global_rng_exact=True,full_optimizer_state_close=True))

    def test_safe_fresh_restore_matches_future_updates_private_rng_and_full_state(self):
        phases=(True,False,True,False,True,True)
        owner=self.trainer(phases)
        owner.step()
        owner.step()
        saved=owner.state_dict()
        path=self.fixture.root/'new_batched_schedule_boundary.pt'
        with path.open('xb') as stream:
            torch.save(saved,stream)
        expected=[owner.step() for _ in range(4)]
        expected_state=owner.state_dict()
        fresh=self.trainer(phases)
        fresh.load_state_dict(torch.load(path,map_location='cpu',weights_only=True))
        replay=[fresh.step() for _ in range(4)]
        self.assertTrue(fixed._same(replay,expected))
        self.assertTrue(fixed._same(fresh.state_dict(),expected_state))
        self.assertEqual(fresh.source.cursor,len(phases))
        stopped=fresh.source.state_dict()
        with self.assertRaises(StopIteration):
            fresh.step()
        self.assertTrue(fixed._same(fresh.source.state_dict(),stopped))
        CONTROLS.append(dict(name='FRESH_SAFE_RESTORE',after_groups=2,future_groups=4,full_state_and_reports_exact=True,
            source_rng_exact=True,global_rng_exact=True,new_checkpoint=str(path),checkpoint_bytes=path.stat().st_size))

    def test_inactive_projector_keeps_value_moment_step_and_learning_rate(self):
        owner=self.trainer((True,False,False,True))
        owner.step()
        before=copy.deepcopy(owner.optimizers[2].state_dict())
        value=owner.t2s.detach().clone()
        for _ in range(2):
            row=owner.step()
            self.assertTrue(row['inactive_projector_optimizer'])
            self.assertTrue(fixed._same(owner.optimizers[2].state_dict(),before))
            self.assertTrue(torch.equal(value,owner.t2s))
        self.assertEqual(owner.state_dict()['scheduled_boundary']['lr_schedule']['last_active_ordinals'],[2,2,0])
        CONTROLS.append(dict(name='ZERO_KD_FULL_STATE',zero_KD_groups=2,projector_rate_and_optimizer_exact=True))

    def test_batched_overflow_consumes_group_and_skips_all_optimizer_steps(self):
        owner=self.trainer((True,False,True))
        old=owner.state_dict()
        before=self.boundary(owner)
        op_count=len(counted.STEP_CALLS)
        handle=owner.model.body.register_hook(lambda grad:torch.full_like(grad,float('inf')))
        try:
            report=owner.step()
        finally:
            handle.remove()
        self.assertEqual(report['scaled_optimizer_group']['status'],'SKIPPED_ALL_NONFINITE')
        self.assertEqual(len(counted.STEP_CALLS),op_count)
        after=self.boundary(owner)
        self.assertEqual((after['completed_groups'],after['applied_groups'],after['skipped_groups']),(1,0,1))
        self.assertEqual(after['source']['cursor'],1)
        self.assertFalse(fixed._same(before['source'],after['source']))
        self.assertTrue(torch.equal(before['external_projectors']['t2s'],after['external_projectors']['t2s']))
        for name,_ in owner.model.named_parameters():
            self.assertTrue(torch.equal(before['model'][name],after['model'][name]))
        self.assertEqual(report['lr_schedule']['consumed_ordinal'],0)
        self.assertNotEqual(old['scheduled_boundary']['lr_schedule'],owner.state_dict()['scheduled_boundary']['lr_schedule'])
        saved=owner.state_dict()
        expected=owner.step()
        fresh=self.trainer((True,False,True))
        fresh.load_state_dict(saved)
        self.assertTrue(fixed._same(fresh.step(),expected))
        self.assertTrue(fixed._same(fresh.state_dict(),owner.state_dict()))
        CONTROLS.append(dict(name='OVERFLOW',optimizer_calls_on_bad_group=0,consumed_and_skipped=1,
            future_report_and_full_state_exact=True,scale=report['scaled_optimizer_group']['scale_after']))

    def test_type_shift_and_envelope_errors_are_rejected_before_forward_or_lr_update(self):
        owner=self.trainer((True,False,True))
        initial=owner.state_dict()
        wrong=copy.deepcopy(initial)
        wrong['policy']['pad_id']=1
        for invalid in (initial['scheduled_boundary'],wrong):
            with self.assertRaisesRegex(ValueError,'batched scheduled CPU checkpoint'):
                owner.load_state_dict(invalid)
            self.assertTrue(fixed._same(owner.state_dict(),initial))
        incompatible=self.trainer((True,False,True),batch_size=4)
        with self.assertRaises(ValueError):
            incompatible.load_state_dict(initial)
        for invalid in ('untyped','shift'):
            owner.source.bad_update=invalid
            before_ops=len(counted.STEP_CALLS)
            with self.assertRaises(ValueError):
                owner.step()
            self.assertTrue(owner.dirty)
            self.assertEqual(int(owner.model.forward_count),0)
            self.assertEqual(len(counted.STEP_CALLS),before_ops)
            self.assertEqual([opt.param_groups[0]['lr'] for opt in owner.optimizers],list(BASE_RATES))
            self.assertTrue(fixed._same(owner.source.state_dict(),initial['scheduled_boundary']['boundary']['source']))
            owner.load_state_dict(initial)
        CONTROLS.append(dict(name='PREFLIGHT_REJECTION',wrong_envelopes=3,wrong_inputs=2,
            optimizer_calls=0,forward_calls=0,learning_rates_held=True))

    def test_partial_microbatch_failure_requires_complete_restore(self):
        owner=self.trainer((True,False,True))
        initial=owner.state_dict()
        forward=owner.model.forward
        def fail_second_batch(*args,**kwargs):
            if int(owner.model.forward_count)==1:
                raise RuntimeError('injected second microbatch failure')
            return forward(*args,**kwargs)
        with patch.object(owner.model,'forward',side_effect=fail_second_batch):
            with self.assertRaisesRegex(RuntimeError,'second microbatch failure'):
                owner.step()
        self.assertTrue(owner.dirty)
        self.assertEqual(int(owner.model.forward_count),1)
        self.assertTrue(all(p.grad is None for p in owner.parameters))
        self.assertTrue(fixed._same(owner.source.state_dict(),initial['scheduled_boundary']['boundary']['source']))
        with self.assertRaises(RuntimeError):
            owner.state_dict()
        with self.assertRaises(RuntimeError):
            owner.step()
        owner.load_state_dict(initial)
        self.assertEqual(int(owner.model.forward_count),0)
        expected=owner.step()
        after=owner.state_dict()
        fresh=self.trainer((True,False,True))
        fresh.load_state_dict(initial)
        self.assertTrue(fixed._same(fresh.step(),expected))
        self.assertTrue(fixed._same(fresh.state_dict(),after))
        CONTROLS.append(dict(name='PARTIAL_FORWARD_FAILURE',partial_forward=1,dirty_checkpoint_rejected=True,
            restored_complete_future_exact=True))


if __name__ == '__main__':
    unittest.main()
