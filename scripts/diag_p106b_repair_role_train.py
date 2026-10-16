#!/usr/bin/env python3
"""Four fixed-parent repair/role recipes, same216 updates and final-only CPT."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime,timezone
import json
import math
import os
import tempfile
import time
from scripts import diag_p106b_repair_role_course as course
from scripts import diag_p106b_original_qa3_train_v2 as previous
from scripts import diag_p106b_relation_train as reference
from scripts.p106b_native_windows import reader as native_reader
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
training=course.training
CODE=(*course.CODE,'scripts/diag_p106b_repair_role_train.py','scripts/test_p106b_repair_role_train.py')


def info():
    r=course.info();r.update(code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        binary_head_lr=.001,binary_head_initialization='carry same parent state; new Adam moments',
        fact_head_updated=False,student_mtp=False)
    return r


def checkpoint(arm):
    return ROOT/'runs/ckpt'/f"m100s10_ko-en_repairrole_dense_chat32_{course.TAG}_{arm}.pt"


def load_parent():
    from tinylm.infer.generate import _strip
    torch,model,cfg,tok,_,old_binary=previous.load_parent()
    if training.data.digest(course.PARENT)!=course.PARENT_SHA:raise ValueError('fixed repair-role parent changed')
    saved=torch.load(course.PARENT,map_location='cpu',weights_only=True)
    if saved['original_qa3_curriculum']!=dict(tag=course.old.TAG,arm='three',epoch=4):raise ValueError('same prelocked three-QA parent lineage')
    model.load_state_dict(_strip(saved['model']),strict=True);binary_state=saved['training_only_binary_auxiliary'];del saved,old_binary
    model.set_anneal(1.);model.train();initial=training.state_fingerprint(model)
    prior=course.producer.required(course.old.EVIDENCE/'evaluate/report.json')
    if initial!=prior['endpoints']['three']['core_before_after_sha256']:raise ValueError('actual CPU parent body differs from previous endpoint')
    return torch,model,cfg,tok,initial,binary_state

def loss_sum(word,n,binary,bn):return reference.normalize(word,n,binary,bn,word*0,0,0.)


def wire():
    import torch
    if torch.cuda.is_initialized():raise ValueError('wire must remain CPU only')
    target=course.EVIDENCE/'actual_cpu_wire.json'
    if target.exists():raise GateNegative('old actual parent/input wire preserved')
    r,rows,labels=course.read_course();torch,model,cfg,tok,initial,binary_state=load_parent()
    before=torch.random.get_rng_state().clone();binary=course.old.prior.data.binding.new_head(cfg.dim,'cpu');binary.load_state_dict(binary_state,strict=True)
    if not torch.equal(before,torch.random.get_rng_state()) or training.state_fingerprint(model)!=initial:raise ValueError('carried binary head changed body/RNG')
    known={};draws={}
    for arm in course.ARMS:
        total=Counter();per_epoch=[]
        for epoch in range(4):
            values=rows[arm+'_train'+str(epoch)];encoded=[course.factory.encode(v,tok)[0] for v in values]
            total.update(x_tokens=sum(x.x_tokens for x in encoded),assistant_targets=sum(x.targets for x in encoded))
            matches=sum(course.conversation_signature(v['messages']) in labels for v in values);per_epoch.append(matches)
            if len(list(training.batches(encoded,epoch)))!=54 or matches!=3072:raise ValueError('actual full216/binary3072 consumer mismatch')
        expected=r['expected_exposures'][arm]
        if any(total[k]!=expected[k] for k in total):raise ValueError('actual encoder differs from frozen counts')
        known[arm]=per_epoch;draws[arm]=dict(total)
    dev=course.development_labels(rows['dev_code'],tok)
    if len(dev)!=512:raise ValueError('original640 development producer contract')
    observation=dict(status='ACTUAL_CPU_PARENT_AND_CONSUMERS_VERIFIED',code_sha256=info()['code_sha256'],
        corpus_sha256=training.data.digest(course.CORPUS/'report.json'),parent_sha256=course.PARENT_SHA,
        initial_core_sha256=initial,known_per_epoch=known,actual_draws=draws,development_binary=512,
        native=course.native_contract(r),binary_carry_and_body_rng_preserved=True,model_loaded_cpu=True,
        cuda_initialized=torch.cuda.is_initialized(),model_forward=False,optimizer_updates=0,checkpoints_written=0)
    if observation['cuda_initialized']:raise ValueError('CPU wire initialized CUDA')
    training.write(target,observation);print('[REPAIR_ROLE_ACTUAL_CPU_WIRE] '+json.dumps(observation),flush=True);return 0


def budget():
    estimates={}
    for arm in course.ARMS:
        r=course.prior.producer.legacy.source.required(course.EVIDENCE/('cost_'+arm)/'report.json')
        if r['code_sha256']!=info()['code_sha256'] or r['updates']!=8:raise ValueError('same-code actual cost8 required')
        warm=r['step_seconds'][1:]
        if len(warm)!=7 or any(not math.isfinite(x) or x<=0 for x in warm):raise ValueError('seven finite warmed steps')
        estimates[arm]=max(warm)*216+900
    completed=[a for a in course.ARMS if (course.EVIDENCE/a/'report.json').exists()]
    needed=sum(t for a,t in estimates.items() if a not in completed)+3600+2700
    remaining=(course.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds()
    return dict(estimates_sec=estimates,completed=completed,needed_sec=needed,remaining_sec=remaining,fits=needed<remaining,
        scope='forecast includes60minute evaluation and45minute closure, not a proven upper bound')


def evaluate_loss(model,binary,tok,rows,labels,pad):
    import torch
    from tinylm.train import mtp_sft as core
    total=Counter();model.eval();model.freeze_quant()
    try:
        with torch.no_grad():
            for start in range(0,len(rows),8):
                chosen=rows[start:start+8];encoded=[course.factory.encode(r,tok)[0] for r in chosen]
                x,y,seg=course.prior.padded(encoded,pad)
                known=[labels.get(course.conversation_signature(r['messages'])) for r in chosen]+[None]*(8-len(chosen))
                bits=[k['bit'] if k else None for k in known];positions=[k['positions'] if k else None for k in known]
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=model(x,return_hidden=True)
                    for kind in ('public_qa','fictional_relation_fields','role_bridge','code'):
                        keep=[r['meta']['kind']==kind if kind!='code' else r['meta']['kind'] not in ('public_qa','fictional_relation_fields','role_bridge') for r in chosen]+[False]*(8-len(chosen))
                        target=y.masked_fill(~torch.tensor(keep,device='cuda')[:,None],-100)
                        sums,n=core.components(model,hidden,target,seg,horizons=(),checkpoint_heads=False)
                        total[kind+'_sum']+=float(sums[1]);total[kind+'_targets']+=n[1]
                    bv,bn,bc,be=course.prior.data.binding.suffix_auxiliary_sum(binary,hidden,y,bits,positions,dense=True)
                total.update(binary_sum=float(bv),binary_rows=bn,binary_correct=bc,binary_position_events=be)
    finally:model.clear_quant();model.train()
    return dict(total,ce={k:total[k+'_sum']/total[k+'_targets'] for k in ('public_qa','fictional_relation_fields','role_bridge','code')},
        scope='same raw-three-QA DEV/fiction/code/role targets; not free-answer quality')


def run(a,cost=False):
    from tinylm.train import mtp_sft as core
    r,rows,labels=course.read_course();arm=a.arm;target=course.EVIDENCE/(('cost_' if cost else '')+arm)
    proof=course.producer.required(course.EVIDENCE/'actual_cpu_wire.json')
    if proof['code_sha256']!=info()['code_sha256'] or proof['status']!='ACTUAL_CPU_PARENT_AND_CONSUMERS_VERIFIED' or proof['corpus_sha256']!=training.data.digest(course.CORPUS/'report.json'):
        raise ValueError('same-code actual CPU parent/data wire required before CUDA')
    if target.exists() or (not cost and checkpoint(arm).exists()):raise GateNegative('old trial preserved')
    if not cost:
        b=budget();print('[REPAIR_ROLE_BUDGET] '+json.dumps(b),flush=True)
        if not b['fits']:raise GateNegative('four full216/evaluation/closure do not fit')
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    with wall_limit(a.max_wall_sec):
        torch,model,cfg,tok,initial,binary_state=load_parent()
        dev_known=course.development_labels(rows['dev_code'],tok)
        model=model.cuda()
        cpu_rng=torch.random.get_rng_state().clone();cuda_rng=torch.cuda.get_rng_state().clone()
        binary=course.prior.data.binding.new_head(cfg.dim,'cuda');binary.load_state_dict(binary_state,strict=True)
        if not torch.equal(cpu_rng,torch.random.get_rng_state()) or not torch.equal(cuda_rng,torch.cuda.get_rng_state()):raise ValueError('binary head changed body/data RNG')
        if training.state_fingerprint(model)!=initial:raise ValueError('adding/carrying head changed body')
        encoded={};known={}
        for epoch in range(4):
            values=rows[arm+'_train'+str(epoch)];encoded[epoch]=[course.factory.encode(row,tok)[0] for row in values]
            for row,rec in zip(values,encoded[epoch]):known[id(rec)]=labels.get(course.conversation_signature(row['messages']))
        pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('pad token absent')
        native=native_reader(ROOT,r);torch.cuda.reset_peak_memory_stats();before=None if cost else training.native_ce(model,course.prior.NATIVE)
        os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_repair_role_')
        compiled=torch.compile(model,mode='default');adam,muon=training.optimizers(model)
        for opt in (adam,muon):
            for group in opt.param_groups:group['lr']*=.5
        bo=torch.optim.AdamW(binary.parameters(),lr=.001,weight_decay=0)
        dev=rows['dev_natural_three']+rows['dev_code']+rows['dev_fiction']+rows['dev_role']
        dev_labels={**labels,**dev_known}
        steps=x_count=target_count=native_x=binary_rows=binary_events=padded=clipped=0;grad_max=0.;times=[];history=[]
        for epoch in range(4):
            for group in training.batches(encoded[epoch],epoch):
                course.prior.producer.legacy.source.deadline();tick=time.perf_counter()
                n=sum(rec.targets for micro in group for rec in micro);bn=sum(known[id(rec)] is not None for micro in group for rec in micro)
                for opt in (adam,muon,bo):opt.zero_grad(set_to_none=True)
                for micro in group:
                    x,y,seg=course.prior.padded(micro,pad);ks=[known[id(rec)] for rec in micro]+[None]*(8-len(micro))
                    bits=[k['bit'] if k else None for k in ks];positions=[k['positions'] if k else None for k in ks]
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        hidden=compiled(x,return_hidden=True);sums,valid=core.components(model,hidden,y,seg,horizons=())
                        bv,bcount,bc,be=course.prior.data.binding.suffix_auxiliary_sum(binary,hidden,y,bits,positions,dense=True)
                        loss=loss_sum(sums[1],n,bv,bn)
                    if not torch.isfinite(loss):raise ValueError('nonfinite loss')
                    loss.backward();x_count+=sum(rec.x_tokens for rec in micro);target_count+=sum(rec.targets for rec in micro);padded+=x.numel();binary_rows+=bcount;binary_events+=be
                nr=[core.Record(v[:-1].astype('int64').tolist(),v[1:].astype('int64').tolist(),[1]*1024) for v in native[steps*8:(steps+1)*8]]
                if len(nr)!=8:raise ValueError('native data exhausted')
                x,y,seg=core.pad_records(nr,pad,'cuda',fixed_width=1024,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=compiled(x,return_hidden=True);sums,valid=core.components(model,hidden,y,seg,horizons=());loss=sums[1]/8192
                loss.backward();native_x+=8192
                grad=torch.nn.utils.clip_grad_norm_([*model.parameters(),*binary.parameters()],1.)
                if not torch.isfinite(grad):raise ValueError('nonfinite gradient')
                grad_max=max(grad_max,float(grad));clipped+=int(grad>1.);adam.step();muon.step()
                if bn:bo.step()
                steps+=1;torch.cuda.synchronize();times.append(time.perf_counter()-tick)
                if steps==1 or steps%25==0:print('[REPAIR_ROLE_UPDATE] '+json.dumps(dict(arm=arm,epoch=epoch+1,updates=steps,x=x_count,targets=target_count,native=native_x,last_sec=times[-1])),flush=True)
                if cost and steps==8:break
            if cost:break
            evaluation=evaluate_loss(model,binary,tok,dev,dev_labels,pad);nv=training.native_ce(model,course.prior.NATIVE)
            h=dict(epoch=epoch+1,updates=steps,dev=evaluation,native=nv,checkpoint=None,checkpoint_sha256=None)
            if epoch==3:
                cp=checkpoint(arm)
                with cp.open('xb') as stream:torch.save(dict(model=model.state_dict(),cfg=asdict(cfg),step=steps,tokenizer_sha256=training.data.TOK_SHA,
                    tokenizer_lineage='chat32',training_only_binary_auxiliary=binary.state_dict(),repair_role_curriculum=dict(tag=course.TAG,arm=arm,epoch=epoch+1),optimizer_saved=False),stream)
                h.update(checkpoint=str(cp.relative_to(ROOT)),checkpoint_sha256=training.data.digest(cp))
            history.append(h)
            print('[REPAIR_ROLE_EPOCH] '+json.dumps(dict(arm=arm,**h)),flush=True)
        expected=r['expected_exposures'][arm]
        if not cost and (steps!=216 or x_count!=expected['x_tokens'] or target_count!=expected['assistant_targets'] or native_x!=expected['native_x_tokens'] or binary_rows!=expected['binary_rows'] or binary_events!=expected['binary_position_events']):raise ValueError('exact planned exposures differ')
        result=dict(info(),status='COST_MEASURED' if cost else 'REPAIR_ROLE_TRAINED_TEST_PENDING',arm=arm,updates=steps,
            corpus_sha256=training.data.digest(course.CORPUS/'report.json'),initial_core_sha256=initial,sft_x_tokens=x_count,assistant_targets=target_count,native_x_tokens=native_x,
            binary_rows=binary_rows,binary_position_events=binary_events,padded_sft_tokens=padded,grad_max=grad_max,clip_events=clipped,
            step_seconds=times,history=history,native_before=before,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,whole_sec=time.perf_counter()-began,optimizer_saved=False)
        if not cost:result.update(checkpoint=str(checkpoint(arm).relative_to(ROOT)),checkpoint_sha256=training.data.digest(checkpoint(arm)))
        training.write(target/'report.json',result)
    print('[REPAIR_ROLE_FINAL] '+json.dumps(dict(arm=arm,status=result['status'],updates=steps,whole_sec=result['whole_sec'])),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('wire','cost','train'),required=True);p.add_argument('--arm',choices=course.ARMS)
    p.add_argument('--max-wall-sec',type=int,default=7200);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=10800:p.error('bounded60..10800')
    if a.check_only:print('[REPAIR_ROLE_TRAIN_CHECK_ONLY] '+json.dumps(info()));return 0
    if a.mode!='wire' and a.arm is None:p.error('explicit arm required for cost/train')
    try:
        course.prior.producer.legacy.source.deadline();a.max_wall_sec=min(a.max_wall_sec,int((course.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if a.max_wall_sec<60:raise GateNegative('45minute closure margin')
        return wire() if a.mode=='wire' else run(a,cost=a.mode=='cost')
    except GateNegative as exc:print('[REPAIR_ROLE_TRAIN_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[REPAIR_ROLE_INTERRUPTED] preserve trial evidence');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[REPAIR_ROLE_TRAIN_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
