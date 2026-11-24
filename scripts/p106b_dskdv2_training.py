"""Original CE population plus a bounded KD subset; no model is loaded.

CEKDGroup owns a single loss/backward accounting boundary, not optimizers,
source/model restoration, dataset admission or actual model provenance.
"""
from __future__ import annotations

import copy
import json
import math
import re

import torch

from scripts import p106b_actd_consumer as original_ce
from scripts.p106b_dskdv2_window import NativeFeatureUpdate,StudentFrame
from scripts.p106b_feature_window import FeatureWindow

GROUP_SCHEMA='P106B_COMPLETE_CE_AND_FEATURE_KD_GROUP_V1'
SHA=re.compile(r'[0-9A-F]{64}')

def _integer(value,label,minimum=1):
    if type(value)is not int or value<minimum:raise ValueError('CE/KD invalid integer: '+label)

class CEKDGroup:
    """Consume every original CE row once and add only the explicit KD subset.

    Provider returns the original full StudentFrame for the supplied CE metadata.
    The caller's backward(loss, context) must honor context['retain_graph'] and
    defer all optimizer/parameter mutation until this whole group closes.
    Any failure invalidates this object and all partial gradients/forward state.
    """
    def __init__(self,model,ce_rows,*,up,embedding,student_width,reader=None,
                 teacher_head=None,t2s=None,s2t=None,teacher_width=None,
                 mapping=None,mapping_modes=None,chunk_positions=8,ce_chunk=64,
                 checkpoint_heads=True,kd_rate=1.,parameters=None,
                 max_teacher_frame_values=260000000):
        _integer(student_width,'student_width');_integer(ce_chunk,'ce_chunk');_integer(chunk_positions,'chunk_positions')
        if (student_width>4096 or type(checkpoint_heads)is not bool
                or type(kd_rate)not in(int,float)or not math.isfinite(kd_rate)or kd_rate<0):
            raise ValueError('explicit bounded CE/KD policy required')
        if(not callable(getattr(model,'_head_logits',None))or not callable(getattr(model,'_emb_w',None))
                or not callable(getattr(model,'_emb_up_w',None))or model._emb_w()is not embedding or model._emb_up_w()is not up):
            raise ValueError('CE and KD must bind the same native factored master head objects')
        quantized=getattr(model,'embedding_quantized',None)
        if callable(quantized)and quantized()is not None:raise ValueError('unexported master factored head required')
        if(any(not isinstance(p,torch.Tensor)or p.ndim!=2 or not p.is_leaf or not p.requires_grad for p in(up,embedding))
                or up.shape[1]!=embedding.shape[1]or len(embedding)<2 or up.device!=embedding.device):
            raise ValueError('same-device trainable leaf factored head required')
        if parameters is None:
            parameters=[p for p in model.parameters()if p.requires_grad]
            if t2s is not None and t2s.requires_grad and all(t2s is not p for p in parameters):parameters.append(t2s)
        self.parameters=tuple(parameters)
        if(not self.parameters or len({id(p)for p in self.parameters})!=len(self.parameters)
                or any(not isinstance(p,torch.Tensor)or not p.is_leaf or not p.requires_grad
                    or p.device!=up.device or p.dtype not in(torch.float32,torch.float64)or p.grad is not None for p in self.parameters)
                or not{id(up),id(embedding)}<={id(p)for p in self.parameters}):
            raise ValueError('unique original trainable masters with empty gradients required')
        if not isinstance(ce_rows,(list,tuple))or not 0<len(ce_rows)<=1024:raise ValueError('bounded original CE rows required')
        raw=json.dumps(ce_rows,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
        if len(raw.encode('utf-8'))>8*(1<<20):raise ValueError('original CE metadata quota exceeded')
        self._rows=json.loads(raw);self._row_index={};self.ce_denominator=0
        shared=('row_id','semantic_root_id','record_sha256','source_row_sha256','student_tokens','split')
        for index,row in enumerate(self._rows):
            if type(row)is not dict or not (set(shared)|{'ce_targets'})<=set(row)or row['split']!='train':
                raise ValueError('explicit original TRAIN CE identity/count metadata required')
            for key in('row_id','semantic_root_id'):
                if type(row[key])is not str or not 0<len(row[key])<=256:raise ValueError('bounded original CE IDs required')
            for key in('record_sha256','source_row_sha256'):
                if type(row[key])is not str or not SHA.fullmatch(row[key]):raise ValueError('exact original CE identity SHA required')
            _integer(row['student_tokens'],'student_tokens');_integer(row['ce_targets'],'ce_targets')
            if not row['ce_targets']<=row['student_tokens']<=student_width or row['row_id']in self._row_index:
                raise ValueError('original CE row count/width/unique ID contract differs')
            self._row_index[row['row_id']]=index;self.ce_denominator+=row['ce_targets']
        self.model=model;self.up=up;self.embedding=embedding;self.student_width=student_width
        self.ce_chunk=ce_chunk;self.checkpoint_heads=checkpoint_heads;self.kd_rate=float(kd_rate)
        self._kd=None;self._kd_ids=set();self.kd_positions=0;kd_callbacks=0
        self._arguments=dict(up=up,embedding=embedding,teacher_head=teacher_head,t2s=t2s,s2t=s2t)
        if reader is not None:
            if not isinstance(reader,FeatureWindow)or reader.contract['split']!='train':raise ValueError('explicit fresh TRAIN feature window required')
            contract=reader.contract;previous=-1
            for record in contract['records']:
                index=self._row_index.get(record['row_id'],-1)
                if index<=previous or any(record.get(key)!=self._rows[index][key]for key in shared):
                    raise ValueError('KD records must preserve the original CE identity and ordered subsequence')
                previous=index
                if record['positions']:self._kd_ids.add(record['row_id'])
            if(any(not isinstance(p,torch.Tensor)or p.requires_grad for p in(teacher_head,s2t))
                    or not isinstance(t2s,torch.Tensor)or id(t2s)not in{id(p)for p in self.parameters}):
                raise ValueError('frozen teacher/reverse projector and declared trainable forward projector required')
            self.kd_positions=contract['selected_positions']
            self._kd=NativeFeatureUpdate(reader,window_sha256=reader.window_sha256,global_positions=self.kd_positions,
                student_width=student_width,teacher_width=teacher_width,student_vocab=len(embedding),teacher_vocab=len(teacher_head),
                mapping=mapping,mapping_modes=mapping_modes,chunk_positions=chunk_positions,
                max_teacher_frame_values=max_teacher_frame_values,kd_rate=self.kd_rate)
            self._kd._parameters_for(up,embedding,teacher_head,t2s,s2t)
            ids=[record['row_id']for record in contract['records']for _ in record['positions']]
            batch=contract['options']['batch_positions']
            for start in range(0,len(ids),batch):
                index=start;end=min(start+batch,len(ids))
                while index<end:
                    stop=index+1
                    while stop<end and ids[stop]==ids[index]and stop-index<chunk_positions:stop+=1
                    kd_callbacks+=1;index=stop
        self.expected_backward_calls=len(self._rows)-len(self._kd_ids)+kd_callbacks
        self._watched=list(self.parameters)
        for value in(teacher_head,s2t):
            if value is not None and all(value is not p for p in self._watched):self._watched.append(value)
        self._versions=tuple(p._version for p in self._watched)
        self.phase='READY';self._cursor=0;self._current=None;self._provider=self._backward=None
        self._ce_sum=0.;self._ce_targets=self._backwards=0;self._loss_sum=0.;self._order=[]

    def _unchanged(self):
        if tuple(p._version for p in self._watched)!=self._versions:
            raise ValueError('CE/KD parameters changed before whole-group closure')

    def _load_frame(self,row):
        self._unchanged();frame=self._provider(copy.deepcopy(row));self._unchanged()
        if(not isinstance(frame,StudentFrame)or frame.row_id!=row['row_id']or frame.semantic_root_id!=row['semantic_root_id']
                or frame.record_sha256!=row['record_sha256']or not isinstance(frame.hidden,torch.Tensor)
                or frame.hidden.shape!=(self.student_width,self.up.shape[0])or frame.hidden.device!=self.up.device
                or frame.hidden.dtype not in(torch.float16,torch.bfloat16,torch.float32,torch.float64)
                or not bool(torch.isfinite(frame.hidden).all())):raise ValueError('exact original CE full frame required')
        for value in(frame.targets,frame.owners):
            if not isinstance(value,torch.Tensor)or value.shape!=(self.student_width,)or value.dtype!=torch.long or value.device!=self.up.device:
                raise ValueError('original CE full shifted targets/owners required')
        valid=frame.targets.ne(-100)
        if(int(valid.sum())!=row['ce_targets']or bool((frame.targets[valid]<0).any())
                or bool((frame.targets[valid]>=len(self.embedding)).any())or bool((frame.owners[valid]<1).any())
                or bool((frame.owners[~valid]!=0).any())or bool(valid[row['student_tokens']:].any())):
            raise ValueError('original CE count/targets/owners/padding differs')
        parts=original_ce.components(self.model,frame.hidden.unsqueeze(0),frame.targets.unsqueeze(0),frame.owners.unsqueeze(0),[],
            ce_denominator=self.ce_denominator,actd_denominator=1,enable_actd=False,
            chunk=self.ce_chunk,checkpoint_heads=self.checkpoint_heads)
        if(parts['ce_targets']!=row['ce_targets']or parts['actd_positions']!=0
                or not bool(torch.isfinite(parts['loss']))or not parts['loss'].requires_grad):
            raise ValueError('finite original full-row CE objective/count required')
        self._ce_sum+=float(parts['ce_sum'].detach());self._ce_targets+=parts['ce_targets'];self._order.append(row['row_id'])
        return frame,parts['loss']

    def _emit(self,loss,context):
        self._unchanged()
        if not isinstance(loss,torch.Tensor)or loss.ndim or not bool(torch.isfinite(loss))or not loss.requires_grad:
            raise ValueError('finite caller-normalized CE/KD scalar required')
        self._backward(loss,context);self._unchanged()
        self._backwards+=1;self._loss_sum+=float(loss.detach())

    def _ce_only(self,row):
        frame,loss=self._load_frame(row)
        self._emit(loss,dict(row_id=row['row_id'],semantic_root_id=row['semantic_root_id'],
            loss_scope='CE_ONLY',row_complete=True,retain_graph=False,ce_attached=True,
            global_ce_targets=self.ce_denominator,global_kd_positions=self.kd_positions))
        del frame,loss

    def _provide_kd(self,metadata):
        row_id=metadata['row_id']
        while self._cursor<len(self._rows)and self._rows[self._cursor]['row_id']!=row_id:
            row=self._rows[self._cursor]
            if row['row_id']in self._kd_ids:raise ValueError('original CE/KD provider order changed')
            self._ce_only(row);self._cursor+=1
        if self._cursor>=len(self._rows)or self._current is not None:raise ValueError('one original KD row frame at a time required')
        row=self._rows[self._cursor];frame,ce_loss=self._load_frame(row);self._cursor+=1
        self._current=(row_id,frame,ce_loss)
        return frame

    def _backward_kd(self,loss,context):
        if self._current is None or self._current[0]!=context['row_id']:raise ValueError('original CE/KD active frame differs')
        final=context['row_complete'];combined=loss+self._current[2]if final else loss
        owned=dict(context,loss_scope='CE_PLUS_KD'if final else'KD_ONLY',retain_graph=not final,
            ce_attached=final,global_ce_targets=self.ce_denominator,global_kd_positions=self.kd_positions)
        self._emit(combined,owned)
        if final:self._current=None

    def consume(self,provider,backward):
        if self.phase!='READY':raise RuntimeError('CE/KD group already consumed/failed; discard partial state')
        if not callable(provider)or not callable(backward):raise ValueError('explicit original frame/backward callbacks required')
        self.phase='RUNNING';self._provider=provider;self._backward=backward
        try:
            kd_report=None
            if self._kd is not None:
                seen=0
                while seen<self.kd_positions:
                    result=self._kd.consume_next(self._provide_kd,self._backward_kd,**self._arguments)
                    if not seen<result['positions_consumed']<=self.kd_positions:raise ValueError('KD consumer failed to advance exact source accounting')
                    seen=result['positions_consumed']
                kd_report=self._kd.close_accounting()
            while self._cursor<len(self._rows):
                row=self._rows[self._cursor]
                if row['row_id']in self._kd_ids:raise ValueError('unconsumed original KD row')
                self._ce_only(row);self._cursor+=1
            self._unchanged()
            if(self._current is not None or self._ce_targets!=self.ce_denominator
                    or self._order!=[row['row_id']for row in self._rows]or self._backwards!=self.expected_backward_calls):
                raise ValueError('complete original CE/KD group accounting differs')
            self.phase='CLOSED'
            return dict(schema=GROUP_SCHEMA,ce_rows=len(self._rows),kd_rows=len(self._kd_ids),
                ce_only_rows=len(self._rows)-len(self._kd_ids),original_ce_order=copy.deepcopy(self._order),
                original_ce_targets=self._ce_targets,global_ce_denominator=self.ce_denominator,
                selected_kd_positions=self.kd_positions,global_kd_denominator=self.kd_positions,
                ce_sum=self._ce_sum,normalized_ce=self._ce_sum/self.ce_denominator,
                normalized_kd=0. if kd_report is None else kd_report['normalized_loss'],
                normalized_total=self._loss_sum,expected_backward_calls=self.expected_backward_calls,
                backward_callback_calls=self._backwards,feature_accounting=kd_report,
                actual_model_provenance='CALLER_OWNED_NOT_CERTIFIED',actual_backward_execution='CALLER_OWNED_NOT_CERTIFIED',
                optimizer_steps=0,full_training_checkpoint_or_resume=False,corpus_admitted=False)
        except BaseException:self.phase='FAILED';raise
        finally:self._current=self._provider=self._backward=None


# The following owner is separate from the closed loss/backward group above.
from collections import OrderedDict
from dataclasses import dataclass,asdict
import random
import numpy as np
from scripts.p107_scaled_optimizer_group import ScaledOptimizerGroup,ScaleConfig,checksum as scale_checksum
from tinylm.train.adaptive_training import cpu_copy
from tinylm.train.muon import Muon

TRAINING_SCHEMA='P106B_SCALED_FEATURE_TRAINING_BOUNDARY_V1'
CARRY_SCHEMA='P106B_FEATURE_PUBLIC_SCALER_CARRY_V1'
OVERFLOW_POLICY='CONSUME_COMPLETE_FINITE_LOSS_GROUP_SKIP_ALL_ACTIVE_OPTIMIZERS_V1'

def _same(left,right):
    if isinstance(left,torch.Tensor)or isinstance(right,torch.Tensor):
        return isinstance(left,torch.Tensor)and isinstance(right,torch.Tensor)and left.dtype==right.dtype and left.shape==right.shape and torch.equal(left.cpu(),right.cpu())
    if isinstance(left,dict)or isinstance(right,dict):
        return isinstance(left,dict)and isinstance(right,dict)and set(left)==set(right)and all(_same(left[k],right[k])for k in left)
    if isinstance(left,(list,tuple))or isinstance(right,(list,tuple)):
        return type(left)is type(right)and len(left)==len(right)and all(_same(a,b)for a,b in zip(left,right))
    return type(left)is type(right)and left==right

def _json_copy(value):return json.loads(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False))
def _tensor_layout(values):return {name:dict(shape=list(value.shape),dtype=str(value.dtype))for name,value in values.items()}

@dataclass(frozen=True)
class FeatureTrainingUpdate:
    ordinal:int
    ce_rows:tuple|list
    reader:FeatureWindow|None

class ScaledFeatureTrainer:
    """Explicit CPU dense-FP32 training boundary, exercised with tiny fixtures.

    Source provides contract/next_update/state_dict/load_state_dict and a pure
    validate_checkpoint(state)->checked_state. Provider(model, CE metadata)
    returns the original StudentFrame. Fixed teacher assets are a caller-owned
    identity reference. This class never loads an existing model or dataset.
    A dedicated projector optimizer is required for complete zero-KD groups.
    """
    def __init__(self,model,optimizers,source,provider,*,signature,up,embedding,
                 teacher_head,t2s,s2t,teacher_head_identity,student_width,teacher_width,
                 mapping,mapping_modes,chunk_positions=8,ce_chunk=64,checkpoint_heads=True,
                 kd_rate=1.,clip=1.,scale_config=ScaleConfig(),max_teacher_frame_values=260000000):
        if(not isinstance(signature,str)or not SHA.fullmatch(signature)or not isinstance(scale_config,ScaleConfig)
                or not callable(provider)or type(clip)not in(int,float)or not math.isfinite(clip)or clip<=0
                or not isinstance(teacher_head_identity,str)or not SHA.fullmatch(teacher_head_identity)):
            raise ValueError('explicit CPU trainer signature/provider/scale/clip/teacher declaration required')
        self.model=model;self.optimizers=tuple(optimizers);self.source=source;self.provider=provider
        self.signature=signature;self.scale_config=scale_config;self.clip=float(clip)
        self.up=up;self.embedding=embedding;self.teacher_head=teacher_head;self.t2s=t2s;self.s2t=s2t
        self.completed_groups=self.applied_groups=self.skipped_groups=0
        self.active=self.dirty=False;self._carry=None
        if(not all(callable(getattr(source,name,None))for name in('next_update','state_dict','load_state_dict','validate_checkpoint'))
                or not isinstance(getattr(source,'contract',None),dict)):
            raise ValueError('explicit source and pure checkpoint-validation protocol required')
        self._source_contract=_json_copy(source.contract)
        named=dict(model.named_parameters());registered=dict(named);registered.update(dict(model.named_buffers()))
        model_parameters=[p for p in named.values()if p.requires_grad]
        self.parameters=tuple(model_parameters+([]if any(t2s is p for p in model_parameters)else[t2s]))
        if(not self.parameters or len({id(p)for p in self.parameters})!=len(self.parameters)
                or any(not isinstance(p,torch.Tensor)or p.device.type!='cpu'or p.dtype!=torch.float32
                    or not p.is_leaf or not p.requires_grad or p.layout!=torch.strided or p.grad is not None for p in self.parameters)
                or not{id(up),id(embedding)}<={id(p)for p in model_parameters}):
            raise ValueError('CPU dense FP32 original student masters and forward projector required')
        if(any(not isinstance(p,torch.Tensor)or p.device.type!='cpu'or p.dtype!=torch.float32
                or p.requires_grad or p.layout!=torch.strided or not bool(torch.isfinite(p).all())for p in(teacher_head,s2t))
                or any(teacher_head is p for p in registered.values())):
            raise ValueError('external frozen CPU teacher and frozen reverse projector required')
        self._external={name:p for name,p in dict(t2s=t2s,s2t=s2t).items()if not any(p is q for q in registered.values())}
        self._parameter_indices={id(p):i for i,p in enumerate(self.parameters)}
        self._projector_index=self._parameter_indices[id(t2s)]
        self._teacher_version=teacher_head._version;self._s2t_version=s2t._version
        self._group_options=dict(up=up,embedding=embedding,teacher_head=teacher_head,t2s=t2s,s2t=s2t,
            student_width=student_width,teacher_width=teacher_width,mapping=copy.deepcopy(mapping),
            mapping_modes=copy.deepcopy(mapping_modes),chunk_positions=chunk_positions,ce_chunk=ce_chunk,
            checkpoint_heads=checkpoint_heads,kd_rate=kd_rate,parameters=self.parameters,
            max_teacher_frame_values=max_teacher_frame_values)
        owners=[]
        for index,opt in enumerate(self.optimizers):
            if not isinstance(opt,(torch.optim.AdamW,torch.optim.SGD,Muon)):raise ValueError('explicit dense AdamW/SGD/Muon optimizer required')
            members=[p for group in opt.param_groups for p in group['params']]
            owners.extend(id(p)for p in members)
            if any(t2s is p for p in members):
                if len(members)!=1:raise ValueError('forward projector requires its own optimizer')
                self._projector_optimizer=index
        if(not self.optimizers or len(set(owners))!=len(owners)or set(owners)!=set(self._parameter_indices)
                or not hasattr(self,'_projector_optimizer')):raise ValueError('every original trainable master needs one explicit optimizer')
        self._student_indices=[i for i in range(len(self.parameters))if i!=self._projector_index]
        self._student_optimizers=[i for i in range(len(self.optimizers))if i!=self._projector_optimizer]
        if not self._student_indices or not self._student_optimizers:raise ValueError('student and separate projector optimizers required')
        values=model.state_dict()
        if any(not isinstance(v,torch.Tensor)or v.device.type!='cpu'or v.layout!=torch.strided for v in values.values()):
            raise ValueError('CPU dense tensor model/buffer state required')
        self._model_layout=_tensor_layout(values);self._external_layout=_tensor_layout(self._external)
        self._optimizer_layout=self._optimizer_binding()
        self.contract=dict(schema=TRAINING_SCHEMA,signature=signature,
            model_type=type(model).__module__+'.'+type(model).__qualname__,model_layout=self._model_layout,
            external_projector_layout=self._external_layout,optimizer_layout=self._optimizer_layout,
            parameter_layout=[dict(shape=list(p.shape),dtype=str(p.dtype))for p in self.parameters],
            source_contract=self._source_contract,teacher_head_identity=teacher_head_identity,
            teacher_head_layout=dict(shape=list(teacher_head.shape),dtype=str(teacher_head.dtype)),
            scale_config=asdict(scale_config),clip=self.clip,overflow_policy=OVERFLOW_POLICY,
            group_options={k:v for k,v in self._group_options.items()if k not in('up','embedding','teacher_head','t2s','s2t','parameters')},
            projector_parameter_index=self._projector_index,projector_optimizer_index=self._projector_optimizer,
            scope='CPU_COMPLETE_STUDENT_BOUNDARY_FIXED_TEACHER_ASSETS_CALLER_OWNED_NOT_CERTIFIED')
        self.contract=_json_copy(self.contract)
        self._checked_source(self.source.state_dict())
        self._controller(list(range(len(self.parameters))),list(range(len(self.optimizers))),1)

    def _optimizer_binding(self):
        result=[]
        for opt in self.optimizers:
            groups=[]
            for group in opt.param_groups:
                indices=[self._parameter_indices.get(id(p),-1)for p in group['params']]
                if not indices or min(indices)<0:raise ValueError('optimizer ownership changed')
                settings=_json_copy({k:v for k,v in group.items()if k!='params'})
                groups.append(dict(parameter_indices=indices,settings=settings))
            result.append(dict(type=type(opt).__module__+'.'+type(opt).__qualname__,groups=groups))
        return result

    def _binding(self,*,restoring=False):
        if(self.teacher_head._version!=self._teacher_version or (not restoring and self.s2t._version!=self._s2t_version)
                or self.teacher_head.requires_grad or self.s2t.requires_grad
                or any(not p.requires_grad or p.device.type!='cpu' or p.dtype!=torch.float32 or not p.is_leaf for p in self.parameters)
                or _tensor_layout(self.model.state_dict())!=self._model_layout
                or _tensor_layout(self._external)!=self._external_layout
                or self._optimizer_binding()!=self._optimizer_layout
                or _json_copy(self.source.contract)!=self._source_contract
                or self.model._emb_w()is not self.embedding or self.model._emb_up_w()is not self.up):
            raise ValueError('CPU trainer model/head/optimizer/source binding changed')

    def _checked_source(self,state):
        state=cpu_copy(state);before=cpu_copy(self.source.state_dict())
        checked=self.source.validate_checkpoint(cpu_copy(state))
        if not _same(checked,state)or not _same(before,self.source.state_dict()):
            raise ValueError('source checkpoint validator must be pure and return the exact checked state')
        return checked

    def _controller(self,parameter_indices,optimizer_indices,backwards):
        return ScaledOptimizerGroup([self.parameters[i]for i in parameter_indices],
            [self.optimizers[i]for i in optimizer_indices],run_signature=self.signature,
            expected_backwards=backwards,config=self.scale_config)

    def _validate_carry(self,carry,completed,applied,skipped):
        if carry is None:
            if completed or applied or skipped:raise ValueError('missing scaler carry after completed input groups')
            return None
        fields={'schema','parameter_indices','optimizer_indices','fixed_state'}
        if type(carry)is not dict or set(carry)!=fields or carry['schema']!=CARRY_SCHEMA:
            raise ValueError('exact public scaler carry schema required')
        full=(list(range(len(self.parameters))),list(range(len(self.optimizers))))
        student=(self._student_indices,self._student_optimizers)
        pair=(carry['parameter_indices'],carry['optimizer_indices'])
        if any(type(values)is not list or any(type(i)is not int for i in values)for values in pair):
            raise ValueError('integer active parameter/optimizer indices required')
        if pair!=full and pair!=student:raise ValueError('scaler carry active membership differs')
        state=carry['fixed_state']
        if type(state)is not dict or type(state.get('expected_backwards'))is not int:raise ValueError('fixed scalar state/backward count required')
        probe=self._controller(*pair,state['expected_backwards']);checked=probe.validate_checkpoint(state)
        if(checked['attempts']!=completed or checked['steps']!=applied or checked['skips']!=skipped):
            raise ValueError('scaler carry and consumed/applied/skipped group counters differ')
        return copy.deepcopy(carry)

    def _fresh_bound_controller(self,parameters,optimizers,backwards):
        old=self._validate_carry(self._carry,self.completed_groups,self.applied_groups,self.skipped_groups)
        group=self._controller(parameters,optimizers,backwards)
        migration=dict(policy='VALIDATED_PUBLIC_SCALARS_IN_FRESH_DECLARED_BINDING_V1',
            parameter_indices=parameters,optimizer_indices=optimizers,expected_backwards=backwards,
            previous_fixed_state_sha256=None if old is None else old['fixed_state']['state_sha256'])
        if old is not None:
            state=group.state_dict()
            for key in('scaler','attempts','steps','skips'):state[key]=copy.deepcopy(old['fixed_state'][key])
            state['state_sha256']=scale_checksum({k:v for k,v in state.items()if k!='state_sha256'})
            group.load_state_dict(state)
        return group,migration

    def _rng(self):
        ns=np.random.get_state()
        return dict(torch=torch.get_rng_state().clone(),python=random.getstate(),
            numpy=(ns[0],ns[1].tolist(),ns[2],ns[3],ns[4]))

    def _validate_rng(self,state):
        if type(state)is not dict or set(state)!={'torch','python','numpy'}:raise ValueError('exact CPU RNG state required')
        value=state['torch']
        if not isinstance(value,torch.Tensor)or value.dtype!=torch.uint8 or value.device.type!='cpu':raise ValueError('CPU byte RNG state required')
        torch.Generator(device='cpu').manual_seed(0).set_state(value)
        random.Random(0).setstate(state['python'])
        ns=state['numpy']
        if not isinstance(ns,(tuple,list))or len(ns)!=5:raise ValueError('exact NumPy legacy RNG state required')
        np.random.RandomState(0).set_state((ns[0],np.array(ns[1],dtype=np.uint32),*ns[2:]))

    def _restore_rng(self,state):
        torch.set_rng_state(state['torch']);random.setstate(state['python'])
        ns=state['numpy'];np.random.set_state((ns[0],np.array(ns[1],dtype=np.uint32),*ns[2:]))

    def _discard_failed(self,source_before,rng_before):
        self.dirty=True
        for opt in self.optimizers:opt.zero_grad(set_to_none=True)
        self.source.load_state_dict(cpu_copy(source_before));self._restore_rng(rng_before)

    def _group_consumer(self,group,update):
        def consume(controller):
            return group.consume(lambda row:self.provider(self.model,row),
                lambda loss,context:controller.backward(loss,retain_graph=context['retain_graph']))
        return consume

    def step(self):
        if self.active or self.dirty:raise RuntimeError('CPU trainer active/dirty; complete restore required')
        self._binding()
        source_before=self._checked_source(self.source.state_dict());rng_before=self._rng();self.active=True
        try:
            try:update=self.source.next_update()
            except StopIteration:
                if not _same(source_before,self.source.state_dict()):raise ValueError('source exhaustion advanced state')
                self._restore_rng(rng_before);self.active=False;raise
            if(not isinstance(update,FeatureTrainingUpdate)or type(update.ordinal)is not int
                    or update.ordinal!=self.completed_groups):raise ValueError('explicit consecutive original update ordinal required')
            group=CEKDGroup(self.model,update.ce_rows,reader=update.reader,**self._group_options)
            consume=self._group_consumer(group,update)
            if update.reader is None:
                parameters=list(self._student_indices);optimizers=list(self._student_optimizers)
            else:
                parameters=list(range(len(self.parameters)));optimizers=list(range(len(self.optimizers)))
            controller,migration=self._fresh_bound_controller(parameters,optimizers,group.expected_backward_calls)
            report=consume(controller)
            scaled=controller.finish(clip_norm=self.clip)
            self.completed_groups+=1;self.applied_groups+=int(scaled['status']=='STEPPED_ALL')
            self.skipped_groups+=int(scaled['status']=='SKIPPED_ALL_NONFINITE')
            self._carry=dict(schema=CARRY_SCHEMA,parameter_indices=parameters,optimizer_indices=optimizers,fixed_state=controller.state_dict())
            self._checked_source(self.source.state_dict());self._binding()
            return dict(group=report,scaled_optimizer_group=scaled,scaler_rebinding=migration,
                consumed_groups=self.completed_groups,applied_groups=self.applied_groups,skipped_groups=self.skipped_groups,
                inactive_projector_optimizer=update.reader is None,overflow_policy=OVERFLOW_POLICY,
                actual_model_provenance='CALLER_OWNED_NOT_CERTIFIED',language_quality='NOT_EVALUATED')
        except StopIteration as exc:
            if self.active:
                self._discard_failed(source_before,rng_before)
                raise RuntimeError('unexpected exhaustion inside an active CPU update')from exc
            raise
        except BaseException:
            self._discard_failed(source_before,rng_before);raise
        finally:self.active=False

    def state_dict(self):
        if self.active or self.dirty or any(p.grad is not None for p in self.parameters):
            raise RuntimeError('CPU checkpoint requires a healthy complete gradient-free boundary')
        self._binding();self._validate_carry(self._carry,self.completed_groups,self.applied_groups,self.skipped_groups)
        values=self.model.state_dict()
        return dict(schema=TRAINING_SCHEMA,contract=copy.deepcopy(self.contract),
            completed_groups=self.completed_groups,applied_groups=self.applied_groups,skipped_groups=self.skipped_groups,
            model=cpu_copy(values),model_state_metadata=cpu_copy(getattr(values,'_metadata',{})),
            module_training_flags={name:module.training for name,module in self.model.named_modules()},
            external_projectors={name:cpu_copy(value)for name,value in self._external.items()},
            optimizers=[cpu_copy(opt.state_dict())for opt in self.optimizers],
            source=self._checked_source(self.source.state_dict()),scaler_carry=copy.deepcopy(self._carry),rng=self._rng())

    def _validate_optimizer_state(self,index,value):
        if type(value)is not dict or set(value)!={'state','param_groups'}or not isinstance(value['state'],dict):
            raise ValueError('exact optimizer snapshot required')
        layout=self._optimizer_layout[index];groups=value['param_groups']
        if type(groups)is not list or len(groups)!=len(layout['groups']):raise ValueError('optimizer group layout differs')
        param_map={}
        for saved,expected in zip(groups,layout['groups']):
            if not isinstance(saved,dict)or _json_copy({k:v for k,v in saved.items()if k!='params'})!=expected['settings']:
                raise ValueError('fixed optimizer settings differ')
            ids=saved.get('params')
            if(type(ids)is not list or len(ids)!=len(expected['parameter_indices'])
                    or any(type(i)is not int or i<0 or i in param_map for i in ids)or len(set(ids))!=len(ids)):
                raise ValueError('optimizer parameter-ID layout differs')
            param_map.update(zip(ids,(self.parameters[i]for i in expected['parameter_indices'])))
        if not set(value['state'])<=set(param_map):raise ValueError('optimizer state has foreign parameter IDs')
        opt=self.optimizers[index]
        allowed={'buf'}if isinstance(opt,Muon)else({'momentum_buffer'}if isinstance(opt,torch.optim.SGD)else{'step','exp_avg','exp_avg_sq','max_exp_avg_sq'})
        for ident,entry in value['state'].items():
            if type(ident)is not int or type(entry)is not dict or not set(entry)<=allowed:raise ValueError('optimizer state fields differ')
            required={'buf'}if isinstance(opt,Muon)else({'momentum_buffer'}if isinstance(opt,torch.optim.SGD)else{'step','exp_avg','exp_avg_sq'})
            if not required<=set(entry):raise ValueError('optimizer state is incomplete')
            for name,tensor in entry.items():
                if not isinstance(tensor,torch.Tensor)or tensor.device.type!='cpu'or not bool(torch.isfinite(tensor).all()):
                    raise ValueError('finite CPU optimizer-state tensors required')
                if name=='step':
                    if tensor.shape!=torch.Size([])or tensor.dtype not in(torch.float32,torch.float64)or float(tensor)<0 or float(tensor)!=int(float(tensor)):
                        raise ValueError('optimizer step scalar differs')
                elif tensor.shape!=param_map[ident].shape or tensor.dtype!=param_map[ident].dtype:
                    raise ValueError('optimizer state shape/dtype differs')

    def load_state_dict(self,state):
        if self.active:raise RuntimeError('cannot restore an active CPU update')
        self._binding(restoring=True);state=cpu_copy(state)
        fields={'schema','contract','completed_groups','applied_groups','skipped_groups','model','model_state_metadata',
            'module_training_flags','external_projectors','optimizers','source','scaler_carry','rng'}
        if(type(state)is not dict or set(state)!=fields or state['schema']!=TRAINING_SCHEMA
                or json.dumps(state['contract'],sort_keys=True,allow_nan=False)!=json.dumps(self.contract,sort_keys=True,allow_nan=False)):
            raise ValueError('exact CPU complete-boundary contract required')
        for name in('completed_groups','applied_groups','skipped_groups'):_integer(state[name],name,0)
        if state['completed_groups']!=state['applied_groups']+state['skipped_groups']:raise ValueError('input/applied/skipped counters differ')
        for saved,current in[(state['model'],self.model.state_dict()),(state['external_projectors'],self._external)]:
            if not isinstance(saved,dict)or set(saved)!=set(current):raise ValueError('complete model/projector keys differ')
            for name,value in saved.items():
                if(not isinstance(value,torch.Tensor)or value.shape!=current[name].shape or value.dtype!=current[name].dtype
                        or value.device.type!='cpu'or not bool(torch.isfinite(value).all())):raise ValueError('complete model/projector shape/dtype/value differs')
        if not _same(state['model_state_metadata'],cpu_copy(getattr(self.model.state_dict(),'_metadata',{}))):
            raise ValueError('model state metadata/version differs')
        modes=state['module_training_flags']
        if(not isinstance(modes,dict)or set(modes)!={name for name,_ in self.model.named_modules()}
                or any(type(v)is not bool for v in modes.values())):raise ValueError('module training flags differ')
        if type(state['optimizers'])is not list or len(state['optimizers'])!=len(self.optimizers):raise ValueError('all optimizer snapshots required')
        for i,value in enumerate(state['optimizers']):self._validate_optimizer_state(i,value)
        checked_source=self._checked_source(state['source'])
        checked_carry=self._validate_carry(state['scaler_carry'],state['completed_groups'],state['applied_groups'],state['skipped_groups'])
        self._validate_rng(state['rng'])
        self.dirty=True
        try:
            values=OrderedDict(state['model']);values._metadata=copy.deepcopy(state['model_state_metadata'])
            self.model.load_state_dict(values,strict=True)
            with torch.no_grad():
                for name,value in self._external.items():value.copy_(state['external_projectors'][name])
            for opt,saved in zip(self.optimizers,state['optimizers']):opt.load_state_dict(cpu_copy(saved));opt.zero_grad(set_to_none=True)
            self.source.load_state_dict(cpu_copy(checked_source))
            if not _same(self.source.state_dict(),checked_source):raise ValueError('source did not restore exact state')
            for name,module in self.model.named_modules():module.training=modes[name]
            if callable(getattr(self.model,'clear_quant',None)):self.model.clear_quant()
            self.completed_groups,self.applied_groups,self.skipped_groups=(state[k]for k in('completed_groups','applied_groups','skipped_groups'))
            self._carry=copy.deepcopy(checked_carry);self._s2t_version=self.s2t._version
            self._restore_rng(state['rng']);self.dirty=False
        except BaseException:raise
