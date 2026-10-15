#!/usr/bin/env python3
"""Same mathematical trainer with root-interleaved source views."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from dataclasses import asdict
from collections import Counter
from datetime import datetime,timezone
import json
import math
import os
import tempfile
import time
from scripts import diag_p106b_relation_interleaved_runtime_v2 as course
from scripts import p106b_relation_fields as factory
from scripts import p106b_relation_auxiliary as fact
from scripts import diag_p101a_sft_mtp as training
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
from scripts.p106b_native_windows import reader as native_reader
ARMS={'fact1':1.}
CODE=(*course.CODE,'scripts/diag_p106b_relation_interleaved_train_v2.py','scripts/test_p106b_relation_interleaved_train_v2.py')


def info():
    r=course.info();r.update(code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        arms=ARMS,binary_auxiliary_parameters=1538,fact_auxiliary_parameters=98304,
        code_head_lr=.001,fact_head_lr=.001,head_weight_decay=0,source_fact_labels_inferred=False)
    return r


def checkpoint(arm,epoch=None):
    return ROOT/'runs/ckpt'/f"m100s10_ko-en_relation_dense_chat32_{course.TAG}_{arm}{'_epoch'+str(epoch) if epoch else ''}.pt"


def load_parent():
    import torch
    from tinylm.infer.generate import _strip
    torch,model,cfg,tok,old=course.prior.load_parent()
    if training.data.digest(course.PARENT)!=course.PARENT_SHA:raise ValueError('fixed DEV-selected parent changed')
    saved=torch.load(course.PARENT,map_location='cpu',weights_only=True)
    if saved['curriculum']!=dict(tag=course.prior.TAG,arm='contrast',epoch=2):raise ValueError('exact prelocked parent lineage')
    model.load_state_dict(_strip(saved['model']),strict=True);del saved;model.set_anneal(1.);model.train()
    return torch,model,cfg,tok,training.state_fingerprint(model)


def normalize(word,word_n,binary,binary_n,selection,selection_n,beta):
    if word_n<=0 or binary_n<0 or selection_n<0:raise ValueError('whole update denominators')
    return word/word_n+(binary/binary_n if binary_n else binary*0)+(beta*selection/selection_n if selection_n else selection*0)


def budget():
    costs={}
    for arm in ARMS:
        r=course.prior.producer.legacy.source.required(course.EVIDENCE/('cost_'+arm)/'report.json')
        if r['code_sha256']!=info()['code_sha256'] or r['updates']!=8:raise ValueError('same-code actual8 costs required')
        steady=r['step_seconds'][1:]
        if len(steady)!=7 or any(not math.isfinite(x) or x<=0 for x in steady):raise ValueError('seven finite warmed observations')
        costs[arm]=max(steady)*688+900
    completed=[a for a in ARMS if (course.EVIDENCE/a/'report.json').exists()]
    needed=sum(t for a,t in costs.items() if a not in completed)+5400+2700
    remaining=(course.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds()
    return dict(costs_sec=costs,completed=completed,needed_sec=needed,remaining_sec=remaining,fits=needed<remaining,
        scope='forecast includes90minute evaluation and45minute closure, not guaranteed upper bound')


def head_delta(head,initial):
    return float(sum((p.detach().cpu()-initial[n]).square().sum() for n,p in head.named_parameters()).sqrt())


def eval_loss(model,binary,selector,tok,rows,binary_labels,pad):
    from tinylm.train import mtp_sft as core
    import torch
    totals=Counter();model.eval();model.freeze_quant()
    try:
        with torch.no_grad():
            for start in range(0,len(rows),8):
                chosen=rows[start:start+8];pairs=[factory.encode(r,tok) for r in chosen];records=[p[0] for p in pairs];fl=[p[1] for p in pairs]+[None]*(8-len(chosen))
                x,y,seg=course.prior.padded(records,pad);known=[binary_labels.get(course.prior.data.binding.prior.source.sha(r['messages'])) for r in chosen]+[None]*(8-len(chosen))
                bits=[k['bit'] if k else None for k in known];windows=[k['positions'] if k else None for k in known]
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=model(x,return_hidden=True)
                    for kind in ('fictional_relation_fields','public_qa','code'):
                        keep=[(r['meta']['kind']==kind if kind!='code' else r['meta']['kind'] not in ('fictional_relation_fields','public_qa')) for r in chosen]+[False]*(8-len(chosen))
                        target=y.masked_fill(~torch.tensor(keep,device='cuda')[:,None],-100)
                        sums,valid=core.components(model,hidden,target,seg,horizons=(),checkpoint_heads=False)
                        totals[kind+'_sum']+=float(sums[1]);totals[kind+'_targets']+=valid[1]
                    bv,bn,bc,be=course.prior.data.binding.suffix_auxiliary_sum(binary,hidden,y,bits,windows,dense=True)
                    fv,fn,fq,fc=fact.auxiliary_sum(selector,hidden,y,seg,fl)
                totals.update(binary_sum=float(bv),binary_rows=bn,binary_correct=bc,fact_row_sum=float(fv),fact_rows=fn,fact_queries=fq,fact_correct=fc)
    finally:model.clear_quant();model.train()
    ce={k:totals[k+'_sum']/totals[k+'_targets'] for k in ('fictional_relation_fields','public_qa','code')}
    return dict(totals,ce=ce,scope='same teacher-forced DEV rows; candidate index is not free-answer or world accuracy')


def run(a,cost=False):
    from tinylm.train import mtp_sft as core
    r,rows,binary_labels=course.read_course();arm=a.arm;beta=ARMS[arm];target=course.EVIDENCE/(('cost_' if cost else '')+arm)
    if target.exists() or (not cost and any(checkpoint(arm,e).exists() for e in (None,1,2,3))):raise GateNegative('old arm outputs preserved')
    if not cost:
        b=budget();print('[RELATION_BUDGET] '+json.dumps(b),flush=True)
        if not b['fits']:raise GateNegative('both arms/evaluation/closure do not fit')
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    with wall_limit(a.max_wall_sec):
        torch,model,cfg,tok,initial=load_parent();model=model.cuda()
        cpu_rng=torch.random.get_rng_state().clone();cuda_rng=torch.cuda.get_rng_state().clone()
        binary=course.prior.data.binding.new_head(cfg.dim,'cuda');selector=fact.new_head(cfg.dim,'cuda',rank=64)
        if not torch.equal(cpu_rng,torch.random.get_rng_state()) or not torch.equal(cuda_rng,torch.cuda.get_rng_state()):raise ValueError('adding heads changed body/data RNG')
        if training.state_fingerprint(model)!=initial:raise ValueError('adding heads changed body')
        initial_head={n:p.detach().cpu().clone() for n,p in selector.named_parameters()}
        encoded={};known_by_id={};fact_by_id={}
        for view in range(4):
            pairs=[factory.encode(row,tok) for row in rows['train'+str(view)]];encoded[view]=[p[0] for p in pairs]
            for row,(rec,label) in zip(rows['train'+str(view)],pairs):
                known_by_id[id(rec)]=binary_labels.get(course.prior.data.binding.prior.source.sha(row['messages']));fact_by_id[id(rec)]=label
        pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('pad absent')
        native=native_reader(ROOT,r);torch.cuda.reset_peak_memory_stats();before=None if cost else training.native_ce(model,course.prior.NATIVE)
        os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_relation_fields_')
        compiled=torch.compile(model,mode='default');adam,muon=training.optimizers(model)
        for opt in (adam,muon):
            for g in opt.param_groups:g['lr']*=.5
        bo=torch.optim.AdamW(binary.parameters(),lr=.001,weight_decay=0);fo=torch.optim.AdamW(selector.parameters(),lr=.001,weight_decay=0)
        steps=sft_x=targets=native_x=binary_rows=binary_events=fact_rows=fact_queries=padded_x=0;times=[];history=[];grad_max=0.;clipped=0
        dev_rows=sum((rows['dev'+str(v)] for v in range(4)),[])+rows['teacher_dev']
        dev_known=course.prior.data.known_contract([x for x in rows['teacher_dev'] if x['meta']['kind']!='public_qa'],tok,course.prior.data.binding.approved_questions('dev'))
        dev_labels={**binary_labels,**dev_known}
        for epoch in range(4):
            for group in training.batches(encoded[epoch],epoch):
                course.prior.producer.legacy.source.deadline();tick=time.perf_counter()
                word_n=sum(rec.targets for micro in group for rec in micro)
                binary_n=sum(known_by_id[id(rec)] is not None for micro in group for rec in micro)
                fact_n=sum(fact_by_id[id(rec)] is not None for micro in group for rec in micro)
                for opt in (adam,muon,bo,fo):opt.zero_grad(set_to_none=True)
                for micro in group:
                    x,y,seg=course.prior.padded(micro,pad);known=[known_by_id[id(rec)] for rec in micro]+[None]*(8-len(micro))
                    bits=[k['bit'] if k else None for k in known];windows=[k['positions'] if k else None for k in known]
                    fl=[fact_by_id[id(rec)] for rec in micro]+[None]*(8-len(micro))
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        hidden=compiled(x,return_hidden=True);sums,valid=core.components(model,hidden,y,seg,horizons=())
                        bv,bn,bc,be=course.prior.data.binding.suffix_auxiliary_sum(binary,hidden,y,bits,windows,dense=True)
                        fv,fn,fq,fc=fact.auxiliary_sum(selector,hidden,y,seg,fl)
                        loss=normalize(sums[1],word_n,bv,binary_n,fv,fact_n,beta)
                    if not torch.isfinite(loss):raise ValueError('nonfinite SFT/query/fact loss')
                    loss.backward();sft_x+=sum(rec.x_tokens for rec in micro);targets+=sum(rec.targets for rec in micro);padded_x+=x.numel()
                    binary_rows+=bn;binary_events+=be;fact_rows+=fn;fact_queries+=fq
                nr=[core.Record(v[:-1].astype('int64').tolist(),v[1:].astype('int64').tolist(),[1]*1024) for v in native[steps*8:(steps+1)*8]]
                if len(nr)!=8:raise ValueError('native windows exhausted')
                x,y,seg=core.pad_records(nr,pad,'cuda',fixed_width=1024,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=compiled(x,return_hidden=True);sums,valid=core.components(model,hidden,y,seg,horizons=());loss=sums[1]/8192
                loss.backward();native_x+=8192
                grad=torch.nn.utils.clip_grad_norm_([*model.parameters(),*binary.parameters(),*selector.parameters()],1.)
                if not torch.isfinite(grad):raise ValueError('nonfinite gradient')
                grad_max=max(grad_max,float(grad));clipped+=int(grad>1.);adam.step();muon.step()
                if binary_n:bo.step()
                if beta and fact_n:fo.step()
                steps+=1;torch.cuda.synchronize();times.append(time.perf_counter()-tick)
                if steps==1 or steps%32==0:print('[RELATION_UPDATE] '+json.dumps(dict(arm=arm,epoch=epoch+1,updates=steps,x=sft_x,targets=targets,native=native_x,fact_rows=fact_rows,fact_queries=fact_queries,last_sec=times[-1])),flush=True)
                if cost and steps==8:break
            if cost:break
            dev=eval_loss(model,binary,selector,tok,dev_rows,dev_labels,pad);native_eval=training.native_ce(model,course.prior.NATIVE)
            cp=checkpoint(arm,None if epoch==3 else epoch+1)
            with cp.open('xb') as stream:torch.save(dict(model=model.state_dict(),cfg=asdict(cfg),step=steps,tokenizer_sha256=training.data.TOK_SHA,
                tokenizer_lineage='chat32',training_only_binary_auxiliary=binary.state_dict(),training_only_fact_auxiliary=selector.state_dict(),
                relation_curriculum=dict(tag=course.TAG,arm=arm,epoch=epoch+1),optimizer_saved=False),stream)
            history.append(dict(epoch=epoch+1,updates=steps,dev=dev,native=native_eval,checkpoint=str(cp.relative_to(ROOT)),checkpoint_sha256=training.data.digest(cp)))
            print('[RELATION_EPOCH] '+json.dumps(dict(arm=arm,**history[-1])),flush=True)
        expected=r['expected_exposures']
        if not cost and (steps!=688 or sft_x!=expected['x_tokens'] or targets!=expected['assistant_targets'] or native_x!=expected['native_x_tokens'] or
            binary_rows!=expected['known_binary_rows'] or binary_events!=expected['known_binary_position_events'] or fact_rows!=expected['fact_rows'] or fact_queries!=expected['fact_queries']):
            raise ValueError('exact planned exposure mismatch')
        delta=head_delta(selector,initial_head)
        if (beta==0 and delta!=0) or (beta>0 and delta==0):raise ValueError('fact0 must stay frozen/fact1 must learn')
        result=dict(info(),status='COST_MEASURED' if cost else 'RELATION_TRAINED_TEST_PENDING',arm=arm,beta=beta,updates=steps,
            corpus_sha256=training.data.digest(course.CORPUS/'report.json'),initial_core_sha256=initial,sft_x_tokens=sft_x,assistant_targets=targets,
            native_x_tokens=native_x,binary_rows=binary_rows,binary_position_events=binary_events,fact_rows=fact_rows,fact_queries=fact_queries,
            fact_parameter_delta_l2=delta,padded_sft_tokens=padded_x,native_before=before,history=history,step_seconds=times,
            grad_max=grad_max,clip_events=clipped,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
            whole_sec=time.perf_counter()-began,optimizer_saved=False,head_in_free_generation=False)
        if not cost:result.update(checkpoint=str(checkpoint(arm).relative_to(ROOT)),checkpoint_sha256=training.data.digest(checkpoint(arm)))
        training.write(target/'report.json',result)
    print('[RELATION_FINAL] '+json.dumps(dict(arm=arm,status=result['status'],updates=steps,whole_sec=result['whole_sec'])),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('cost','train'),required=True);p.add_argument('--arm',choices=tuple(ARMS),required=True)
    p.add_argument('--max-wall-sec',type=int,default=10800);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=14400:p.error('bounded60..14400')
    if a.check_only:print('[RELATION_TRAIN_CHECK_ONLY] '+json.dumps(info()));return 0
    if not a.execute:p.error('explicit execution')
    try:
        course.prior.producer.legacy.source.deadline()
        a.max_wall_sec=min(a.max_wall_sec,int((course.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if a.max_wall_sec<60:raise GateNegative('45minute closure margin')
        return run(a,cost=a.mode=='cost')
    except GateNegative as exc:print('[RELATION_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[RELATION_INTERRUPTED] preserve partial evidence and epoch checkpoints');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[RELATION_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
