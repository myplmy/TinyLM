"""Fresh tiny numerical fixtures; no Native/pretrained model or old data."""
from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
from pathlib import Path
import random
import tempfile
import unittest

import numpy as np
import torch
from torch.nn import functional as F

from scripts import p106b_dskdv2_training as core
from scripts import p106b_dskdv2_contract as dense
from scripts.p106b_dskdv2_window import StudentFrame
from scripts.p106b_feature_window import FeatureWindow

FIXTURE_BASES=[]
NUMERICAL_CONTROLS=[]

class TinyStudent(torch.nn.Module):
    def __init__(self,generator,dtype,dropout=0.):
        super().__init__()
        self.body=torch.nn.Parameter(torch.randn((3,3),generator=generator,dtype=dtype))
        self.up=torch.nn.Parameter(torch.randn((3,2),generator=generator,dtype=dtype))
        self.embedding=torch.nn.Parameter(torch.randn((9,2),generator=generator,dtype=dtype))
        self.dropout=torch.nn.Dropout(dropout)
        self.register_buffer('forward_count',torch.zeros((),dtype=torch.long))
    def _emb_w(self):return self.embedding
    def _emb_up_w(self):return self.up
    def embedding_quantized(self):return None
    def _head_logits(self,hidden):return F.linear(F.linear(hidden,self.up.T),self.embedding)
    def forward(self,values):
        self.forward_count+=1
        return self.dropout(torch.tanh(values@self.body))

class Fixture:
    def __init__(self,root,*,dtype=torch.float64,write=True,dropout=0.,external_random=False):
        self.root=Path(root);self.dtype=dtype;self.order=['c0','k0','c1','k1','c2'];self.width=8
        generator=torch.Generator(device='cpu').manual_seed(1337)
        self.model=TinyStudent(generator,dtype,dropout)
        self.teacher_head=torch.randn((11,4),generator=generator,dtype=dtype)
        self.t2s=torch.nn.Parameter(torch.randn((4,3),generator=generator,dtype=dtype))
        self.s2t=torch.randn((3,4),generator=generator,dtype=dtype)
        self.inputs={name:torch.randn((8,3),generator=generator,dtype=dtype)for name in self.order}
        self.mapping=[i%9 for i in range(11)];self.modes=[1 if i%2 else 3 for i in range(11)]
        self.rows=[];self.targets={};self.owners={};self.provider_order=[];self.external_random=external_random
        supervised=([0,1],[0,2,3,4,5],[1,2,4],[0,1,3,4],[2])
        for index,(name,indices)in enumerate(zip(self.order,supervised)):
            targets=torch.full((8,),-100,dtype=torch.long);owners=torch.zeros(8,dtype=torch.long)
            for position in indices:targets[position]=(position+index)%9;owners[position]=index+1
            self.targets[name]=targets;self.owners[name]=owners
            self.rows.append(dict(row_id=name,semantic_root_id='root_'+name,record_sha256='ABCDE'[index]*64,
                source_row_sha256=str(index+1)*64,student_tokens=6,split='train',ce_targets=len(indices)))
        self.arrays=[np.linspace(-.7,.8,20,dtype=np.float32).reshape(5,4),
            np.linspace(.4,-.6,28,dtype=np.float32).reshape(7,4)]
        self.records=[]
        for row,array,ti,si in zip((self.rows[1],self.rows[3]),self.arrays,([4,0,2],[2,6,1,3]),([3,0,4],[4,1,0,3])):
            path=self.root/(row['row_id']+'.npy')
            if write:
                with path.open('xb')as stream:np.save(stream,array,allow_pickle=False)
            positions=[]
            for teacher_index,student_index in zip(ti,si):
                native=(teacher_index+1)%11
                positions.append(dict(teacher_predictor_raw_index=teacher_index,student_predictor_raw_index=student_index,
                    teacher_target_raw_index=teacher_index+1,student_target_raw_index=student_index+1,
                    student_target_id=int(self.targets[row['row_id']][student_index]),teacher_native_argmax=native,
                    mapped_student_argmax=self.mapping[native],mapping_mode=self.modes[native],
                    owner=int(self.owners[row['row_id']][student_index]),lookahead_bytes=0,accepted=True))
            self.records.append(dict(row,feature_file=path.name,feature_sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                teacher_tokens=len(array),positions=positions))
        self.identities={name:letter*64 for name,letter in zip(
            ('teacher_sha256','tokenizer_sha256','mapping_sha256','data_sha256'),'ABCD')}

    def parameters(self):return list(self.model.parameters())+[self.t2s]
    def reader(self,batch=3,records=None):
        return FeatureWindow(self.records if records is None else records,root=self.root,identities=self.identities,
            split='train',hidden_width=4,batch_positions=batch)
    def provider(self,row):
        name=row['row_id'];self.provider_order.append(name);values=self.inputs[name]
        if self.external_random:values=values*(1.+random.random()*.01+float(np.random.random())*.01)
        return StudentFrame(name,row['semantic_root_id'],row['record_sha256'],self.model(values),
            self.targets[name].clone(),self.owners[name].clone())
    def group(self,*,batch=3,chunk=2,reader=True,rows=None,records=None,**options):
        return core.CEKDGroup(self.model,self.rows if rows is None else rows,up=self.model.up,embedding=self.model.embedding,
            student_width=8,reader=self.reader(batch,records)if reader else None,teacher_head=self.teacher_head,t2s=self.t2s,s2t=self.s2t,
            teacher_width=9,mapping=self.mapping,mapping_modes=self.modes,chunk_positions=chunk,ce_chunk=2,
            parameters=self.parameters(),**options)
    def independent(self,*,rate=.3,records=None,kd=True):
        frames={row['row_id']:self.provider(row)for row in self.rows}
        ce_sum=0
        for row in self.rows:
            frame=frames[row['row_id']];valid=frame.targets.ne(-100)
            logits=frame.hidden[valid]@self.model.up@self.model.embedding.T
            ce_sum=ce_sum+F.cross_entropy(logits,frame.targets[valid],reduction='sum')
        ce_loss=ce_sum/sum(row['ce_targets']for row in self.rows);kd_sum=0;positions=0
        if kd:
            for record,array in zip(self.records if records is None else records,self.arrays):
                p=record['positions']
                if not p:continue
                hs=frames[record['row_id']].hidden[[x['student_predictor_raw_index']for x in p]]
                ht=torch.tensor(array[[x['teacher_predictor_raw_index']for x in p]],dtype=self.dtype)
                labels=torch.tensor([x['mapped_student_argmax']for x in p],dtype=torch.long)
                terms=dense.dskd_sums(hs,ht,self.model.up@self.model.embedding.T,self.teacher_head.T,self.t2s,self.s2t,labels)
                kd_sum=kd_sum+terms['total_sum'];positions+=len(p)
        return ce_loss+(rate*kd_sum/positions if positions else 0),ce_sum

class CEKDGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():raise RuntimeError('CPU numerical controls require uninitialized CUDA')
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix='p106b-dskd-training-A-',dir='/tmp'));FIXTURE_BASES.append(self.root)
        self.fixture=Fixture(self.root)
    def fresh(self,**options):return Fixture(self.root,write=False,**options)
    def consume(self,fixture,group=None,callback=None):
        group=fixture.group(kd_rate=.3)if group is None else group;contexts=[]
        def backward(loss,context):
            contexts.append(copy.deepcopy(context))
            if callback is None:loss.backward(retain_graph=context['retain_graph'])
            else:callback(loss,context)
        return group.consume(fixture.provider,backward),contexts

    def test_complete_five_row_CE_and_two_row_KD_gradient_matches_independent_dense(self):
        reference=self.fixture;wanted,ce=reference.independent()
        gradients=torch.autograd.grad(wanted,reference.parameters(),allow_unused=True)
        actual=self.fresh();teacher=actual.teacher_head.clone();reverse=actual.s2t.clone()
        group=actual.group(kd_rate=.3);self.assertEqual(group.expected_backward_calls,8)
        report,contexts=self.consume(actual,group)
        self.assertAlmostEqual(report['normalized_total'],float(wanted.detach()),delta=1e-10)
        self.assertAlmostEqual(report['ce_sum'],float(ce.detach()),delta=1e-10)
        maximum=0.
        for parameter,want in zip(actual.parameters(),gradients):
            self.assertIsNotNone(want);self.assertIsNotNone(parameter.grad)
            torch.testing.assert_close(parameter.grad,want,atol=1e-10,rtol=1e-10)
            maximum=max(maximum,float((parameter.grad-want).abs().max()))
        self.assertEqual(actual.provider_order,actual.order)
        self.assertEqual((report['ce_rows'],report['kd_rows'],report['ce_only_rows']),(5,2,3))
        self.assertEqual((report['original_ce_targets'],report['selected_kd_positions']),(15,7))
        self.assertEqual(sum(c['ce_attached']for c in contexts),5)
        self.assertTrue(torch.equal(actual.teacher_head,teacher));self.assertTrue(torch.equal(actual.s2t,reverse))
        self.assertIsNone(actual.teacher_head.grad);self.assertIsNone(actual.s2t.grad)
        NUMERICAL_CONTROLS.append(dict(original_CE_rows=5,KD_rows=2,CE_only_rows=3,CE_targets=15,KD_positions=7,
            expected_backwards=8,loss=float(wanted.detach()),max_gradient_abs_error=maximum,
            trainable_parameter_elements=sum(p.numel()for p in actual.parameters()),exact_original_row_order=True))

    def test_CE_only_group_keeps_all_rows_and_targets_without_feature_consumption(self):
        reference=self.fixture;wanted,_=reference.independent(kd=False)
        gradients=torch.autograd.grad(wanted,list(reference.model.parameters()))
        actual=self.fresh();report,_=self.consume(actual,actual.group(reader=False))
        self.assertEqual((report['ce_rows'],report['kd_rows'],report['original_ce_targets']),(5,0,15))
        self.assertEqual(report['backward_callback_calls'],5);self.assertEqual(report['normalized_kd'],0.)
        self.assertAlmostEqual(report['normalized_total'],float(wanted.detach()),delta=1e-10)
        for parameter,want in zip(actual.model.parameters(),gradients):torch.testing.assert_close(parameter.grad,want,atol=1e-10,rtol=1e-10)
        self.assertIsNone(actual.t2s.grad)

    def test_batch_and_chunk_boundaries_preserve_full_objective_and_gradients(self):
        wanted,_=self.fixture.independent();gradients=torch.autograd.grad(wanted,self.fixture.parameters())
        for batch,chunk,count in((1,1,10),(3,2,8),(7,8,5)):
            actual=self.fresh();group=actual.group(batch=batch,chunk=chunk,kd_rate=.3)
            self.assertEqual(group.expected_backward_calls,count)
            report,_=self.consume(actual,group)
            self.assertAlmostEqual(report['normalized_total'],float(wanted.detach()),delta=1e-10)
            for parameter,want in zip(actual.parameters(),gradients):torch.testing.assert_close(parameter.grad,want,atol=1e-10,rtol=1e-10)

    def test_existing_CE_head_checkpoint_on_off_has_same_full_gradient(self):
        first=self.fixture;second=self.fresh()
        a,_=self.consume(first,first.group(checkpoint_heads=True,kd_rate=.3))
        b,_=self.consume(second,second.group(checkpoint_heads=False,kd_rate=.3))
        self.assertAlmostEqual(a['normalized_total'],b['normalized_total'],delta=1e-10)
        for x,y in zip(first.parameters(),second.parameters()):torch.testing.assert_close(x.grad,y.grad,atol=1e-10,rtol=1e-10)

    def test_bad_declared_CE_identity_order_split_and_counts_reject_before_forward(self):
        variants=[]
        rows=copy.deepcopy(self.fixture.rows);rows[1],rows[3]=rows[3],rows[1];variants.append(rows)
        rows=copy.deepcopy(self.fixture.rows);rows[1]['source_row_sha256']='F'*64;variants.append(rows)
        rows=copy.deepcopy(self.fixture.rows);rows[0]['split']='dev';variants.append(rows)
        rows=copy.deepcopy(self.fixture.rows);rows[0]['ce_targets']=7;variants.append(rows)
        for rows in variants:
            with self.assertRaises(ValueError):self.fixture.group(rows=rows)
        self.assertEqual(int(self.fixture.model.forward_count),0)

    def test_actual_CE_target_count_mismatch_fails_and_group_cannot_be_reused(self):
        rows=copy.deepcopy(self.fixture.rows);rows[0]['ce_targets']=3
        group=self.fixture.group(rows=rows)
        with self.assertRaisesRegex(ValueError,'count/targets'):self.consume(self.fixture,group)
        self.assertEqual(group.phase,'FAILED')
        with self.assertRaises(RuntimeError):self.consume(self.fixture,group)
        self.assertTrue(all(p.grad is None for p in self.fixture.parameters()))

    def test_original_frame_owner_padding_and_identity_errors_are_not_skipped(self):
        for field in('owner','padding','identity'):
            fixture=self.fresh();group=fixture.group();provider=fixture.provider
            def bad(row):
                frame=provider(row)
                if field=='owner':frame.owners[0]=0
                elif field=='padding':frame.targets[7]=1;frame.owners[7]=1
                else:frame=replace(frame,record_sha256='F'*64)
                return frame
            with self.subTest(field=field),self.assertRaises(ValueError):group.consume(bad,lambda *args:self.fail('backward must not run'))
            self.assertEqual(group.phase,'FAILED')

    def test_selected_KD_target_mismatch_retains_failure_instead_of_dropping_CE_row(self):
        fixture=self.fixture;group=fixture.group();provider=fixture.provider
        def bad(row):
            frame=provider(row)
            if row['row_id']=='k0':frame.targets[3]=(int(frame.targets[3])+1)%9
            return frame
        with self.assertRaisesRegex(ValueError,'target or owner'):
            group.consume(bad,lambda loss,c:loss.backward(retain_graph=c['retain_graph']))
        self.assertEqual(group.phase,'FAILED');self.assertIsNotNone(fixture.model.body.grad)

    def test_injected_backward_failure_keeps_partial_gradients_invalid(self):
        group=self.fixture.group();calls=[]
        def fail(loss,context):
            calls.append(context['row_id'])
            if len(calls)==2:raise RuntimeError('injected backward failure')
            loss.backward(retain_graph=context['retain_graph'])
        with self.assertRaisesRegex(RuntimeError,'backward failure'):self.consume(self.fixture,group,fail)
        self.assertEqual(group.phase,'FAILED');self.assertIsNotNone(self.fixture.model.body.grad)
        with self.assertRaises(RuntimeError):self.consume(self.fixture,group)

    def test_parameter_mutation_during_callback_is_refused(self):
        group=self.fixture.group()
        def bad(loss,context):
            loss.backward(retain_graph=context['retain_graph'])
            with torch.no_grad():self.fixture.model.up.add_(1.)
        with self.assertRaisesRegex(ValueError,'parameters changed'):self.consume(self.fixture,group,bad)
        self.assertEqual(group.phase,'FAILED')

    def test_foreign_master_or_preexisting_gradients_are_refused(self):
        with self.assertRaises(ValueError):core.CEKDGroup(self.fixture.model,self.fixture.rows,
            up=self.fixture.model.up.clone(),embedding=self.fixture.model.embedding,student_width=8)
        self.fixture.model.body.grad=torch.zeros_like(self.fixture.model.body)
        with self.assertRaises(ValueError):self.fixture.group()

    def test_trainable_teacher_or_reverse_projector_is_refused(self):
        self.fixture.teacher_head.requires_grad_(True)
        with self.assertRaises(ValueError):self.fixture.group()
        self.fixture.teacher_head.requires_grad_(False);self.fixture.s2t.requires_grad_(True)
        with self.assertRaises(ValueError):self.fixture.group()

    def test_provider_failure_after_completed_prefix_requires_discard(self):
        group=self.fixture.group();provider=self.fixture.provider
        def fail(row):
            if row['row_id']=='c1':raise RuntimeError('injected middle CE provider failure')
            return provider(row)
        with self.assertRaisesRegex(RuntimeError,'middle CE provider'):
            group.consume(fail,lambda loss,c:loss.backward(retain_graph=c['retain_graph']))
        self.assertEqual(group.phase,'FAILED');self.assertIsNotNone(self.fixture.model.body.grad)

    def test_zero_position_feature_row_still_contributes_original_CE(self):
        records=copy.deepcopy(self.fixture.records);records[0]['positions']=[]
        wanted,_=self.fixture.independent(records=records)
        gradients=torch.autograd.grad(wanted,self.fixture.parameters())
        actual=self.fresh();report,_=self.consume(actual,actual.group(records=records,kd_rate=.3))
        self.assertEqual((report['ce_rows'],report['kd_rows'],report['ce_only_rows']),(5,1,4))
        self.assertEqual((report['original_ce_targets'],report['selected_kd_positions']),(15,4))
        self.assertAlmostEqual(report['normalized_total'],float(wanted.detach()),delta=1e-10)
        for parameter,want in zip(actual.parameters(),gradients):torch.testing.assert_close(parameter.grad,want,atol=1e-10,rtol=1e-10)

import json
from scripts.p107_scaled_optimizer_group import ScaleConfig
from tinylm.train.muon import Muon

STEP_CALLS=[]
BOUNDARY_CONTROLS=[]

class CountedMuon(Muon):
    def step(self,*args,**kwargs):
        result=super().step(*args,**kwargs);STEP_CALLS.append('muon');return result

class CountedAdamW(torch.optim.AdamW):
    def step(self,*args,**kwargs):
        result=super().step(*args,**kwargs);STEP_CALLS.append('adamw');return result

class CountedSGD(torch.optim.SGD):
    def step(self,*args,**kwargs):
        result=super().step(*args,**kwargs);STEP_CALLS.append('sgd');return result

class UpdateSource:
    def __init__(self,fixture,phases=(True,False,True,True)):
        self.fixture=fixture;self.phases=tuple(phases);self.cursor=0
        digest=hashlib.sha256()
        for name in fixture.order:
            for tensor in(fixture.inputs[name],fixture.targets[name],fixture.owners[name]):
                digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
        self.contract=dict(schema='AUTHORED_FULL_CE_KD_UPDATE_SOURCE_V1',root=str(fixture.root),
            phases=list(phases),input_target_owner_sha256=digest.hexdigest().upper(),
            rows=copy.deepcopy(fixture.rows),feature_refs=[dict(path=r['feature_file'],sha256=r['feature_sha256'])for r in fixture.records])
        self.signature=hashlib.sha256(json.dumps(self.contract,sort_keys=True).encode()).hexdigest().upper()
    def state_dict(self):return dict(schema='AUTHORED_FULL_CE_KD_CURSOR_V1',signature=self.signature,cursor=self.cursor)
    def validate_checkpoint(self,state):
        if(type(state)is not dict or set(state)!={'schema','signature','cursor'}or state['schema']!='AUTHORED_FULL_CE_KD_CURSOR_V1'
                or state['signature']!=self.signature or type(state['cursor'])is not int or not 0<=state['cursor']<=len(self.phases)):
            raise ValueError('authored original source checkpoint differs')
        return copy.deepcopy(state)
    def load_state_dict(self,state):self.cursor=self.validate_checkpoint(state)['cursor']
    def next_update(self):
        if self.cursor==len(self.phases):raise StopIteration
        ordinal=self.cursor;reader=self.fixture.reader()if self.phases[ordinal]else None;self.cursor+=1
        return core.FeatureTrainingUpdate(ordinal,copy.deepcopy(self.fixture.rows),reader)

class ScaledFeatureTrainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():raise RuntimeError('CPU boundary fixtures require uninitialized CUDA')
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix='p106b-dskd-training-B-',dir='/tmp'));FIXTURE_BASES.append(self.root)
        torch.manual_seed(2024);random.seed(19);np.random.seed(23)
        self.fixture=Fixture(self.root,dtype=torch.float32,dropout=.2,external_random=True)

    def fresh(self):return Fixture(self.root,dtype=torch.float32,write=False,dropout=.2,external_random=True)
    def trainer(self,fixture=None,phases=(True,False,True,True),body='muon',provider=None):
        fixture=self.fixture if fixture is None else fixture
        if body=='muon':opt=CountedMuon([fixture.model.body,fixture.model.up],lr=.01,scale_mode='rms')
        elif body=='sgd':opt=CountedSGD([fixture.model.body,fixture.model.up],lr=.001,momentum=.9)
        else:opt=CountedAdamW([fixture.model.body,fixture.model.up],lr=.001)
        optimizers=[opt,CountedAdamW([fixture.model.embedding],lr=.001),CountedAdamW([fixture.t2s],lr=.001,weight_decay=.1)]
        source=UpdateSource(fixture,phases)
        def frame(model,row):
            if model is not fixture.model:raise ValueError('provider bound to a different student')
            return fixture.provider(row)
        return core.ScaledFeatureTrainer(fixture.model,optimizers,source,frame if provider is None else provider,
            signature='9'*64,up=fixture.model.up,embedding=fixture.model.embedding,
            teacher_head=fixture.teacher_head,t2s=fixture.t2s,s2t=fixture.s2t,teacher_head_identity='F'*64,
            student_width=8,teacher_width=9,mapping=fixture.mapping,mapping_modes=fixture.modes,
            chunk_positions=2,ce_chunk=2,kd_rate=.3,scale_config=ScaleConfig(init_scale=128.,growth_interval=2))

    def test_fresh_safe_disk_restore_matches_complete_future_state_losses_and_three_RNGs(self):
        trainer=self.trainer();first=trainer.step();checkpoint=trainer.state_dict()
        path=self.root/'new_numerical_boundary.pt'
        with path.open('xb')as stream:torch.save(checkpoint,stream)
        wanted=[]
        for _ in range(3):wanted.append(trainer.step()['group']['normalized_total'])
        expected=trainer.state_dict()
        fresh=self.trainer(self.fresh())
        saved=torch.load(path,map_location='cpu',weights_only=True);fresh.load_state_dict(saved)
        actual=[fresh.step()['group']['normalized_total']for _ in range(3)]
        self.assertEqual(actual,wanted);self.assertTrue(core._same(fresh.state_dict(),expected))
        self.assertEqual((fresh.completed_groups,fresh.applied_groups,fresh.skipped_groups),(4,4,0))
        self.assertEqual(int(fresh.model.forward_count),20)
        self.assertEqual(float(fresh.optimizers[2].state[fresh.t2s]['step']),3.)
        self.assertEqual(first['scaled_optimizer_group']['backward_calls'],8)
        self.assertEqual(fresh._carry['fixed_state']['scaler']['scale'],512.)
        BOUNDARY_CONTROLS.append(dict(scope='FRESH_OBJECTS_IN_SAME_CPU_PROCESS',consumed=4,applied=4,skipped=0,
            student_optimizer_types=['Muon','AdamW'],dedicated_projector_optimizer='AdamW',
            complete_state_and_future_losses_exact=True,Python_NumPy_Torch_RNG_exact=True,
            forward_calls=20,projector_optimizer_steps=3,safe_new_checkpoint_bytes=path.stat().st_size,
            final_scale=512.,language_training_tokens=0))

    def test_zero_KD_group_preserves_projector_weights_decay_moments_and_old_carry(self):
        trainer=self.trainer();trainer.step();old=trainer._carry;old_copy=copy.deepcopy(old)
        value=trainer.t2s.detach().clone();state=copy.deepcopy(trainer.optimizers[2].state_dict());calls=len(STEP_CALLS)
        report=trainer.step()
        self.assertTrue(torch.equal(trainer.t2s,value));self.assertTrue(core._same(trainer.optimizers[2].state_dict(),state))
        self.assertEqual(len(STEP_CALLS)-calls,2);self.assertTrue(report['inactive_projector_optimizer'])
        self.assertEqual(report['scaled_optimizer_group']['backward_calls'],5)
        self.assertEqual(report['scaler_rebinding']['previous_fixed_state_sha256'],old['fixed_state']['state_sha256'])
        self.assertTrue(core._same(old,old_copy));self.assertEqual(trainer._carry['optimizer_indices'],[0,1])
        trainer.step();self.assertEqual(trainer._carry['optimizer_indices'],[0,1,2])
        self.assertEqual(trainer._carry['fixed_state']['scaler']['scale'],256.)

    def test_gradient_overflow_consumes_source_and_skips_all_active_optimizers(self):
        trainer=self.trainer(phases=(True,True));before=[p.detach().clone()for p in trainer.parameters]
        calls=len(STEP_CALLS);hook=trainer.model.body.register_hook(lambda grad:torch.full_like(grad,float('inf')))
        try:report=trainer.step()
        finally:hook.remove()
        self.assertEqual(report['scaled_optimizer_group']['status'],'SKIPPED_ALL_NONFINITE')
        self.assertEqual((trainer.completed_groups,trainer.applied_groups,trainer.skipped_groups),(1,0,1))
        self.assertEqual(trainer.source.cursor,1);self.assertEqual(int(trainer.model.forward_count),5)
        self.assertEqual(len(STEP_CALLS),calls)
        self.assertTrue(all(torch.equal(p,value)for p,value in zip(trainer.parameters,before)))
        self.assertEqual(trainer._carry['fixed_state']['scaler']['scale'],64.)
        report=trainer.step();self.assertEqual(report['scaled_optimizer_group']['status'],'STEPPED_ALL')
        self.assertEqual((trainer.completed_groups,trainer.applied_groups,trainer.skipped_groups),(2,1,1))
        self.assertEqual(trainer.state_dict()['source']['cursor'],2)

    def test_partial_optimizer_failure_is_dirty_until_full_restore(self):
        trainer=self.trainer(phases=(True,));initial=trainer.state_dict()
        original=trainer.optimizers[1].step
        def fail(*args,**kwargs):raise RuntimeError('injected second optimizer failure')
        trainer.optimizers[1].step=fail
        with self.assertRaisesRegex(RuntimeError,'second optimizer'):trainer.step()
        trainer.optimizers[1].step=original
        self.assertTrue(trainer.dirty);self.assertEqual(trainer.source.cursor,0)
        self.assertFalse(torch.equal(trainer.model.body,initial['model']['body']))
        with self.assertRaises(RuntimeError):trainer.state_dict()
        with self.assertRaises(RuntimeError):trainer.step()
        trainer.load_state_dict(initial);self.assertFalse(trainer.dirty);trainer.step();wanted=trainer.state_dict()
        fresh=self.trainer(self.fresh(),phases=(True,));fresh.load_state_dict(initial);fresh.step()
        self.assertTrue(core._same(fresh.state_dict(),wanted))

    def test_provider_failure_clears_gradients_but_requires_full_buffer_source_RNG_restore(self):
        enabled=[True]
        def provider(model,row):
            if enabled[0]and row['row_id']=='c1':raise RuntimeError('injected CE provider failure')
            return self.fixture.provider(row)
        trainer=self.trainer(phases=(True,),provider=provider);initial=trainer.state_dict()
        with self.assertRaisesRegex(RuntimeError,'CE provider'):trainer.step()
        self.assertTrue(trainer.dirty);self.assertEqual(trainer.source.cursor,0)
        self.assertEqual(int(trainer.model.forward_count),2);self.assertTrue(all(p.grad is None for p in trainer.parameters))
        trainer.load_state_dict(initial);self.assertEqual(int(trainer.model.forward_count),0)
        enabled[0]=False;self.assertEqual(trainer.step()['consumed_groups'],1)

    def test_invalid_snapshot_fields_are_rejected_before_any_live_copy(self):
        trainer=self.trainer();trainer.step();initial=trainer.state_dict()
        for field in('model','rng','source','carry','optimizer','counter','modes'):
            bad=copy.deepcopy(initial)
            if field=='model':bad['model']['body']=torch.zeros(1)
            elif field=='rng':bad['rng']['torch']=torch.zeros(4)
            elif field=='source':bad['source']['cursor']=99
            elif field=='carry':bad['scaler_carry']['parameter_indices'][0]=False
            elif field=='optimizer':bad['optimizers'][1]['state'][0]['exp_avg']=torch.zeros(1)
            elif field=='counter':bad['completed_groups']=True
            else:bad['module_training_flags']['dropout']=0
            with self.subTest(field=field),self.assertRaises(ValueError):trainer.load_state_dict(bad)
            self.assertFalse(trainer.dirty);self.assertTrue(core._same(trainer.state_dict(),initial))

    def test_failed_restore_remains_dirty_and_can_retry_a_complete_snapshot(self):
        trainer=self.trainer();trainer.step();saved=trainer.state_dict()
        fresh=self.trainer(self.fresh());original=fresh.source.load_state_dict
        def fail(state):raise RuntimeError('injected source restore failure')
        fresh.source.load_state_dict=fail
        with self.assertRaisesRegex(RuntimeError,'source restore'):fresh.load_state_dict(saved)
        self.assertTrue(fresh.dirty)
        with self.assertRaises(RuntimeError):fresh.state_dict()
        fresh.source.load_state_dict=original;fresh.load_state_dict(saved)
        self.assertFalse(fresh.dirty);self.assertTrue(core._same(fresh.state_dict(),saved))

    def test_declared_ordinal_and_unexpected_provider_exhaustion_are_failures(self):
        trainer=self.trainer(phases=(True,));original=trainer.source.next_update
        def wrong():
            update=original();return core.FeatureTrainingUpdate(9,update.ce_rows,update.reader)
        trainer.source.next_update=wrong
        with self.assertRaisesRegex(ValueError,'ordinal'):trainer.step()
        self.assertTrue(trainer.dirty);self.assertEqual(int(trainer.model.forward_count),0)
        def exhausted(*args):raise StopIteration
        other=self.trainer(self.fresh(),phases=(True,),provider=exhausted)
        with self.assertRaisesRegex(RuntimeError,'unexpected exhaustion'):other.step()
        self.assertTrue(other.dirty)

    def test_module_modes_external_projectors_and_normal_exhaustion(self):
        trainer=self.trainer(phases=(True,));trainer.model.dropout.eval();trainer.step();saved=trainer.state_dict()
        fresh=self.trainer(self.fresh(),phases=(True,));fresh.load_state_dict(saved)
        self.assertTrue(fresh.model.training);self.assertFalse(fresh.model.dropout.training)
        self.assertTrue(torch.equal(fresh.t2s,trainer.t2s));self.assertTrue(torch.equal(fresh.s2t,trainer.s2t))
        with torch.no_grad():fresh.s2t.add_(1.)
        with self.assertRaises(ValueError):fresh.step()
        fresh.load_state_dict(saved);self.assertTrue(torch.equal(fresh.s2t,trainer.s2t))
        before=fresh.state_dict()
        with self.assertRaises(StopIteration):fresh.step()
        self.assertFalse(fresh.dirty);self.assertTrue(core._same(fresh.state_dict(),before))
        with torch.no_grad():fresh.teacher_head.add_(1.)
        with self.assertRaises(ValueError):fresh.load_state_dict(saved)

    def test_SGD_and_AdamW_student_optimizer_state_roundtrips(self):
        for kind in('sgd','adamw'):
            trainer=self.trainer(self.fresh(),phases=(True,True),body=kind);trainer.step();saved=trainer.state_dict()
            trainer.step();wanted=trainer.state_dict()
            fresh=self.trainer(self.fresh(),phases=(True,True),body=kind);fresh.load_state_dict(saved);fresh.step()
            self.assertTrue(core._same(fresh.state_dict(),wanted))

if __name__=='__main__':unittest.main()
