#!/usr/bin/env python3
"""Same64 updates/input/contrast computations, beta0 versus beta0.1."""
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
from scripts import diag_p106b_evidence_preference_course as course
from scripts import diag_p106b_evidence_recovery_train as upstream
from scripts.p106b_native_windows import reader as native_reader
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
training=course.training
CODE=(*course.CODE,'scripts/diag_p106b_evidence_preference_train.py','scripts/test_p106b_evidence_preference_train.py')


def info():
    r=course.info();r.update(code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        binary_head_lr=.001,binary_head_initialization='same E970 state, fresh Adam moments',
        comparison='DIRECT_PAIRED beta only; both arms evaluate chosen/rejected16 pairs/update',
        objective='token normalized word/native/binary plus beta times sequence-normalized odds preference')
    return r


def checkpoint(arm):return ROOT/'runs/ckpt'/f'm100s10_ko-en_evidencepref_dense_chat32_{course.TAG}_{arm}.pt'


def encode(row,tok):
    # The exact fictional correction producer masks its old wrong first answer.
    # Generic encode_record does NOT interpret supervised_assistant_turns meta.
    return course.upstream.factory.encode(row,tok)[0]


def load_parent():
    from tinylm.infer.generate import _strip
    torch,model,cfg,tok,_,_=upstream.load_parent()
    if training.data.digest(course.PARENT)!=course.PARENT_SHA:raise ValueError('E970 parent changed')
    saved=torch.load(course.PARENT,map_location='cpu',weights_only=True)
    if saved['evidence_recovery_curriculum']!=dict(tag=course.upstream.TAG,arm='evidence_recovery',epoch=4):raise ValueError('fixed E970 final4 lineage')
    model.load_state_dict(_strip(saved['model']),strict=True);binary=saved['training_only_binary_auxiliary'];del saved
    model.set_anneal(1.);model.train();initial=training.state_fingerprint(model)
    if initial!=course.upstream.producer.required(course.PARENT_REPORT)['core_before_after_sha256']:raise ValueError('parent core differs from actual endpoint')
    return torch,model,cfg,tok,initial,binary


def wire():
    import torch
    from tinylm.train.mtp_sft import encode_record
    if torch.cuda.is_initialized():raise ValueError('CPU only wire')
    out=course.EVIDENCE/'actual_cpu_wire.json'
    if out.exists():raise GateNegative('old preference wire preserved')
    r,rows,labels,pairs=course.read_course();torch,model,cfg,tok,initial,bs=load_parent()
    before=torch.random.get_rng_state().clone();binary=course.upstream.prior.data.binding.new_head(cfg.dim,'cpu');binary.load_state_dict(bs,strict=True)
    if not torch.equal(before,torch.random.get_rng_state()) or training.state_fingerprint(model)!=initial:raise ValueError('head changed body/RNG')
    records=[encode(v,tok) for v in rows['train']];signatures={id(v):course.upstream.conversation_signature(row['messages']) for v,row in zip(records,rows['train'])}
    pair_ids={id(rec):row['meta']['semantic_root_id'] if row['meta']['kind']=='evidence_preference' else None for rec,row in zip(records,rows['train'])}
    legal=set(course.method.index_pairs(pairs));sizes=[sum(pair_ids[id(v)] in legal for micro in b for v in micro) for b in training.batches(records,0)]
    if len(sizes)!=64 or min(sizes)<16 or sum(s in labels for s in signatures.values())!=3072:raise ValueError('actual64/16pair/binary3072 consumers')
    for p in pairs:
        if p['source_signature']!=course.upstream.conversation_signature(p['chosen']['messages']):raise ValueError('actual pair signature owner mismatch')
        a,b=(encode(p[k],tok) for k in ('chosen','rejected'))
        if not a.targets or not b.targets or max(a.x_tokens,b.x_tokens)>1024:raise ValueError('complete chosen/rejected masks')
        if p['chosen']['messages'][0]!=p['rejected']['messages'][0]:raise ValueError('same pair prompt required')
    if (sum(x.x_tokens for x in records),sum(x.targets for x in records))!=(r['counts']['x_tokens'],r['counts']['assistant_targets']):raise ValueError('actual full encoder count mismatch')
    proof=dict(status='ACTUAL_CPU_PREFERENCE_PARENT_CONSUMERS_VERIFIED',code_sha256=info()['code_sha256'],
        corpus_sha256=training.data.digest(course.CORPUS/'report.json'),parent_sha256=course.PARENT_SHA,initial_core_sha256=initial,
        rows=len(records),updates=64,min_pair_candidates=min(sizes),pairs=len(pairs),binary_rows=3072,
        body_rng_preserved=True,cuda_initialized=torch.cuda.is_initialized(),model_forward=False,optimizer_updates=0,checkpoint_written=False)
    training.write(out,proof);print('[EVIDENCE_PREFERENCE_CPU_WIRE] '+json.dumps(proof),flush=True);return 0


def budget():
    estimates={}
    for arm in course.ARMS:
        r=course.upstream.producer.required(course.EVIDENCE/('cost_'+arm)/'report.json')
        if r['code_sha256']!=info()['code_sha256'] or r['updates']!=8:raise ValueError('two same-code costs8 required')
        if any(not math.isfinite(x) or x<=0 for x in r['step_seconds']):raise ValueError('finite actual step costs required')
        estimates[arm]=max(r['step_seconds'][1:])*64+1.5*r['step_seconds'][0]+300
    completed=[a for a in course.ARMS if (course.EVIDENCE/a/'report.json').exists()]
    needed=sum(x for a,x in estimates.items() if a not in completed)+2700+2700
    remaining=(course.upstream.producer.original.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds()
    return dict(estimates_sec=estimates,completed=completed,needed_sec=needed,remaining_sec=remaining,fits=needed<remaining,
        scope='forecast: warmed64 plus first-update1.5 and300seconds, evaluation45min based on previous24.4min, closure45min; not guaranteed upper bound')


def run(a,cost=False):
    from tinylm.train import mtp_sft as core
    r,rows,labels,pairs=course.read_course();arm=a.arm;beta=course.ARMS[arm];target=course.EVIDENCE/(('cost_' if cost else '')+arm)
    proof=course.upstream.producer.required(course.EVIDENCE/'actual_cpu_wire.json')
    if (proof['status']!='ACTUAL_CPU_PREFERENCE_PARENT_CONSUMERS_VERIFIED' or proof['code_sha256']!=info()['code_sha256']
            or proof['corpus_sha256']!=training.data.digest(course.CORPUS/'report.json')):raise ValueError('same-code actual CPU wire required')
    if target.exists() or target.is_symlink() or (not cost and (checkpoint(arm).exists() or checkpoint(arm).is_symlink())):raise GateNegative('old preference trial preserved')
    if not cost:
        b=budget();print('[EVIDENCE_PREFERENCE_BUDGET] '+json.dumps(b),flush=True)
        if not b['fits']:raise GateNegative('two64/evaluation/closure do not fit')
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);started=time.perf_counter()
    with wall_limit(a.max_wall_sec):
        torch,model,cfg,tok,initial,bs=load_parent();model=model.cuda()
        cpu_rng=torch.random.get_rng_state().clone();cuda_rng=torch.cuda.get_rng_state().clone()
        binary=course.upstream.prior.data.binding.new_head(cfg.dim,'cuda');binary.load_state_dict(bs,strict=True)
        if not torch.equal(cpu_rng,torch.random.get_rng_state()) or not torch.equal(cuda_rng,torch.cuda.get_rng_state()):raise ValueError('binary carry changed RNG')
        if training.state_fingerprint(model)!=initial:raise ValueError('binary carry changed body')
        records=[encode(row,tok) for row in rows['train']]
        signatures={id(rec):course.upstream.conversation_signature(row['messages']) for rec,row in zip(records,rows['train'])}
        pair_ids={id(rec):row['meta']['semantic_root_id'] if row['meta']['kind']=='evidence_preference' else None for rec,row in zip(records,rows['train'])}
        paired={p['root']:(encode(p['chosen'],tok),encode(p['rejected'],tok),p['mode']) for p in course.method.index_pairs(pairs).values()}
        pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('actual pad token required')
        native=native_reader(ROOT,r);os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_evidence_preference_')
        compiled=torch.compile(model,mode='default');adam,muon=training.optimizers(model)
        for opt in (adam,muon):
            for group in opt.param_groups:group['lr']*=.5
        bo=torch.optim.AdamW(binary.parameters(),lr=.001,weight_decay=0)
        torch.cuda.reset_peak_memory_stats();before=None if cost else training.native_ce(model,course.upstream.prior.NATIVE)
        steps=x_count=targets=native_x=binary_rows=binary_events=pair_count=pair_x=pair_y=clipped=0;grad_max=0.;times=[];modes=Counter()
        for batch in training.batches(records,0):
            course.upstream.producer.original.prior.producer.legacy.source.deadline();tick=time.perf_counter()
            n=sum(v.targets for micro in batch for v in micro);bn=sum(signatures[id(v)] in labels for micro in batch for v in micro)
            for opt in (adam,muon,bo):opt.zero_grad(set_to_none=True)
            for micro in batch:
                x,y,seg=course.upstream.prior.padded(micro,pad);known=[labels.get(signatures[id(v)]) for v in micro]+[None]*(8-len(micro))
                bits=[k['bit'] if k else None for k in known];positions=[k['positions'] if k else None for k in known]
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    h=compiled(x,return_hidden=True);sums,valid=core.components(model,h,y,seg,horizons=())
                    bv,bcount,bc,be=course.upstream.prior.data.binding.suffix_auxiliary_sum(binary,h,y,bits,positions,dense=True)
                    loss=upstream.loss_sum(sums[1],n,bv,bn)
                if not torch.isfinite(loss):raise ValueError('nonfinite word/binary loss')
                loss.backward();x_count+=sum(v.x_tokens for v in micro);targets+=sum(v.targets for v in micro);binary_rows+=bcount;binary_events+=be
            native_records=[core.Record(v[:-1].astype('int64').tolist(),v[1:].astype('int64').tolist(),[1]*1024) for v in native[steps*8:(steps+1)*8]]
            if len(native_records)!=8:raise ValueError('native prefix exhausted')
            x,y,seg=core.pad_records(native_records,pad,'cuda',fixed_width=1024,batch_size=8)
            with torch.autocast('cuda',dtype=torch.bfloat16):
                h=compiled(x,return_hidden=True);sums,valid=core.components(model,h,y,seg,horizons=());loss=sums[1]/8192
            loss.backward();native_x+=8192
            selected=[paired[pair_ids[id(v)]] for micro in batch for v in micro if pair_ids[id(v)] in paired][:16]
            if len(selected)!=16:raise ValueError('sixteen actual matched pairs required')
            for start in range(0,16,4):
                chunk=selected[start:start+4];values=[v[0] for v in chunk]+[v[1] for v in chunk]
                x,y,seg=core.pad_records(values,pad,'cuda',fixed_width=1024,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    h=compiled(x,return_hidden=True);logps=course.method.odds.sequence_logps(model,h,y)
                loss=beta*course.method.odds.preference_loss(logps[:4],logps[4:]).sum()/16
                if not torch.isfinite(loss):raise ValueError('finite odds loss required')
                loss.backward();pair_count+=4;pair_x+=sum(v.x_tokens for v in values);pair_y+=sum(v.targets for v in values);modes.update(v[2] for v in chunk)
            grad=torch.nn.utils.clip_grad_norm_([*model.parameters(),*binary.parameters()],1.)
            if not torch.isfinite(grad):raise ValueError('finite gradient required')
            grad_max=max(grad_max,float(grad));clipped+=int(grad>1);adam.step();muon.step()
            if bn:bo.step()
            steps+=1;torch.cuda.synchronize();times.append(time.perf_counter()-tick)
            if steps==1 or steps%16==0:print('[EVIDENCE_PREFERENCE_UPDATE] '+json.dumps(dict(arm=arm,updates=steps,x=x_count,targets=targets,native=native_x,pairs=pair_count,last_sec=times[-1])),flush=True)
            if cost and steps==8:break
        evaluation=None;nv=None
        if not cost:
            exp=r['expected_exposures']
            if (steps,x_count,targets,native_x,binary_rows,pair_count)!=(64,exp['x_tokens'],exp['assistant_targets'],524288,3072,1024):raise ValueError('planned actual64 exposures differ')
            dev=rows['dev_natural_three']+rows['dev_code']+rows['dev_fiction']+rows['dev_role']+rows['dev_evidence']
            evaluation=upstream.evaluate_loss(model,binary,tok,dev,{**labels,**course.upstream.development_labels(rows['dev_code'],tok)},pad)
            nv=training.native_ce(model,course.upstream.prior.NATIVE)
            with checkpoint(arm).open('xb') as stream:torch.save(dict(model=model.state_dict(),cfg=asdict(cfg),step=steps,
                tokenizer_sha256=training.data.TOK_SHA,tokenizer_lineage='chat32',training_only_binary_auxiliary=binary.state_dict(),
                evidence_preference=dict(tag=course.TAG,arm=arm,updates=64),optimizer_saved=False),stream)
        report=dict(info(),status='COST_MEASURED' if cost else 'EVIDENCE_PREFERENCE_TRAINED_TEST_PENDING',arm=arm,beta=beta,updates=steps,
            initial_core_sha256=initial,corpus_sha256=training.data.digest(course.CORPUS/'report.json'),sft_x_tokens=x_count,assistant_targets=targets,
            native_x_tokens=native_x,binary_rows=binary_rows,binary_position_events=binary_events,contrast_pairs=pair_count,pair_x_tokens=pair_x,
            pair_scored_targets=pair_y,contrast_modes=dict(modes),grad_max=grad_max,clip_events=clipped,step_seconds=times,
            native_before=before,native_after=nv,dev=evaluation,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
            whole_sec=time.perf_counter()-started,optimizer_saved=False)
        if not cost:report.update(checkpoint=str(checkpoint(arm).relative_to(ROOT)),checkpoint_sha256=training.data.digest(checkpoint(arm)))
        training.write(target/'report.json',report)
    print('[EVIDENCE_PREFERENCE_FINAL] '+json.dumps(dict(arm=arm,status=report['status'],updates=steps,whole_sec=report['whole_sec'])),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('wire','cost','train'),required=True);p.add_argument('--arm',choices=course.ARMS)
    p.add_argument('--max-wall-sec',type=int,default=1800);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=3600:p.error('bounded60..3600')
    if a.check_only:print(json.dumps(info()));return 0
    if a.mode!='wire' and a.arm is None:p.error('explicit arm required')
    try:
        course.upstream.producer.original.prior.producer.legacy.source.deadline()
        remaining=(course.upstream.producer.original.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds()
        if remaining<a.max_wall_sec+2700 and a.mode!='wire':raise GateNegative('bounded operation plus45minute closure required')
        return wire() if a.mode=='wire' else run(a,cost=a.mode=='cost')
    except GateNegative as exc:print('[EVIDENCE_PREFERENCE_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[EVIDENCE_PREFERENCE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
