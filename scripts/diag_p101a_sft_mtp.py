#!/usr/bin/env python3
"""User-run frozen8M scratch/parent x NTP/MTP and post-training inference gates.

No model on import/check-only. All old sources/parents remain read-only. New
experimental pseudo-SFT evidence is not formal TRAIN_READY or general ability.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p101a_sft_mtp_data as data
from scripts.p106b_shards import ShardWriter,verify
ARMS=('scratch_ntp','scratch_mtp','parent_ntp','parent_mtp')
SCHEMA='P101A_SFT_MTP_GATE_V1'
PARENT=ROOT/'runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt'
PARENT_SHA='12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950'
CODE=('tinylm/config.py','tinylm/model/transformer.py','tinylm/train/mtp_sft.py',
      'tinylm/infer/generate.py','tinylm/infer/mtp.py','scripts/p101a_sft_mtp_data.py',
      'scripts/diag_p101a_sft_mtp.py','scripts/test_p101a_sft_mtp.py',
      'scripts/test_p101a_sft_mtp_data.py','scripts/p101a_sft_mtp_infer.py',
      'scripts/test_p101a_sft_mtp_driver.py')


def paths(tag):
    if not re.fullmatch(r'p101a_sft_mtp_[a-z0-9_]+',tag):raise ValueError('safe independent MTP tag required')
    corpus=ROOT/'HF/sft_ready'/tag/'corpus';evidence=ROOT/'test_result/evidence'/tag
    if any(p.is_symlink() for target in (corpus,evidence) for p in (target,*target.parents)):
        raise ValueError('linked namespace')
    return corpus,evidence


def write(path,value):
    body=json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if len(body.encode())>20_000_000:raise ValueError('20MB evidence limit')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:stream.write(body)


def checkpoint(tag,arm):
    return ROOT/'runs/ckpt'/('m100s10_ko-en_32M_dense_chat32_'+tag+'_'+arm+'.pt')


def report_path(evidence,arm,calibrate=False):
    return evidence/('calibrate_'+arm if calibrate else arm)/'report.json'


def info(args):
    return dict(schema=SCHEMA,tag=args.tag,seed=1337,micro_bs=8,accum=16,seq=1024,
        checkpoint_on=True,compile='default',lr=1e-4,muon_lr=4e-4,epochs=4,
        unique_train_x_target=8_000_000,processed_x_target_approx=32_000_000,
        horizons=[2,3,4],auxiliary_total_weight=.3,initializers=['scratch','parent'],
        code_sha256={p:data.digest(ROOT/p) for p in CODE},tokenizer_sha256=data.TOK_SHA,
        parent_sha256=PARENT_SHA,model_loading='NOT_RUN',meaningful_training='NOT_RUN',
        formal_train_ready=False,semantic_quality='PSEUDO_UNVERIFIED',
        head_path='assistant-valid gather + recomputed head/CE; both NTP and MTP arms',
        max_wall_sec=args.max_wall_sec)


def corpus_report(corpus):
    report=json.loads((corpus/'report.json').read_text(encoding='utf-8'))
    if (report.get('schema')!=data.VERSION or report.get('status')!='CORPUS_READY'
            or report.get('tokenizer_sha256')!=data.TOK_SHA or report.get('epochs')!=4):
        raise FileNotFoundError('complete frozen8M/val corpus required before model')
    for split,manifest in report['manifests'].items():verify(corpus,manifest)
    return report


def batches(records,epoch):
    order=list(range(len(records)));random.Random(1337+epoch).shuffle(order)
    for start in range(0,len(order),128):
        selected=order[start:start+128]
        yield [[records[i] for i in selected[p:p+8]] for p in range(0,len(selected),8)]


def state_fingerprint(base):
    sha=hashlib.sha256()
    for name,value in sorted(base.state_dict().items()):
        if name in ('mtp_up2','mtp_up3','mtp_up4'):continue
        value=value.detach().cpu().contiguous()
        sha.update((name+str(value.shape)+str(value.dtype)).encode())
        sha.update(value.view(-1).view(__import__('torch').uint8).numpy().tobytes())
    return sha.hexdigest().upper()


def load_runtime(arm):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip
    from scripts.train_sft_p090 import validate_parent_lineage
    if data.digest(PARENT)!=PARENT_SHA or data.digest(data.TOKENIZER)!=data.TOK_SHA:
        raise ValueError('pinned parent/tokenizer identity differs')
    tok=Tokenizer.from_file(str(data.TOKENIZER))
    state=torch.load(PARENT,map_location='cpu',weights_only=True)
    validate_parent_lineage(state,data.TOK_SHA,'chat32',tok)
    cfg=TMTConfig(**state['cfg']);cfg.grad_checkpoint=True;cfg.mtp_aux=False
    cfg.mtp_horizons=(2,3,4)
    if cfg.n_layers!=14 or cfg.tie_mlp or cfg.vocab_size!=32768 or state.get('step')!=2289:
        raise ValueError('declared dense14 chat32 parent geometry differs')
    torch.manual_seed(1337)
    base=TiedMLPTransformer(cfg)
    if arm.startswith('parent_'):base.load_state_dict(_strip(state['model']),strict=True)
    # Scratch reads geometry/tokenizer metadata but NEVER copies learned weights.
    del state;base.set_anneal(1.)
    initial=state_fingerprint(base)
    if arm.endswith('_mtp'):base.attach_mtp_heads((2,3,4))
    return torch,base,cfg,tok,initial


def encoded(corpus,report,tok):
    from tinylm.train.mtp_sft import encode_record
    result={}
    for split in ('train','val'):
        result[split]=[encode_record(row,tok) for row in data.stream_rows(corpus,report['manifests'][split])]
    return result


def optimizers(model):
    import torch
    from tinylm.train.muon import Muon,split_params
    from tinylm.train.optimizer_audit import matrix_decay_groups
    groups,_=matrix_decay_groups(model,1e-4,0)
    matrices,_=split_params(model);matrix_ids={id(p) for p in matrices}
    others=[dict(g,params=[p for p in g['params'] if id(p) not in matrix_ids]) for g in groups]
    others=[g for g in others if g['params']]
    return torch.optim.AdamW(others,betas=(.9,.95),eps=1e-8),Muon(matrices,lr=4e-4,scale_mode='rms',weight_decay=0)


def evaluate(base,records,pad):
    import torch
    from tinylm.train import mtp_sft as core
    totals={1:0.};counts={1:0}
    horizons=tuple(base.cfg.mtp_horizons) if base.cfg.mtp_aux else ()
    for h in horizons:totals[h]=0.;counts[h]=0
    base.eval()
    with torch.no_grad():
        for start in range(0,len(records),8):
            x,y,seg=core.pad_records(records[start:start+8],pad,'cuda',fixed_width=1024,batch_size=8)
            with torch.autocast('cuda',dtype=torch.bfloat16):
                hidden=base(x,return_hidden=True)
                sums,valid=core.components(base,hidden,y,seg,horizons=horizons,checkpoint_heads=False)
            for h in sums:totals[h]+=float(sums[h]);counts[h]+=valid[h]
    base.train()
    return {str(h):{'ce':totals[h]/counts[h] if counts[h] else None,'targets':counts[h]} for h in counts}


def native_ce(base,cache):
    """Same first32 native crops before/after; not full native validation."""
    import numpy as np
    import torch
    from tinylm.train import mtp_sft as core
    path=cache/'val.bin';identity=data.digest(path)
    tokens=np.memmap(path,dtype=np.uint16,mode='r')
    crops=min(32,(len(tokens)-1)//1024)
    if not crops:raise FileNotFoundError('native validation has no complete fixed crop')
    total=0.;count=0
    base.eval();base.freeze_quant()
    try:
        with torch.no_grad():
            for i in range(crops):
                ids=tokens[i*1024:i*1024+1025].astype(np.int64).tolist()
                x=torch.tensor([ids[:-1]],device='cuda')
                y=torch.tensor([ids[1:]],device='cuda');seg=torch.ones_like(y)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=base(x,return_hidden=True)
                    sums,counts=core.components(base,hidden,y,seg,horizons=(),checkpoint_heads=False)
                total+=float(sums[1]);count+=counts[1]
    finally:
        base.clear_quant();base.train()
    if not math.isfinite(total):raise ValueError('nonfinite native crop loss')
    return dict(ce=total/count,targets=count,crops=crops,val_sha256=identity,
        scope='same fixed first32 1024-token crops; not whole-pool native CE')


def train_arm(args,corpus,evidence,metadata,*,calibrate=False):
    arm=args.arm;report=corpus_report(corpus)
    target=report_path(evidence,arm,calibrate)
    out=checkpoint(args.tag,arm)
    if target.exists() or (not calibrate and (out.exists() or out.is_symlink())):
        raise FileExistsError('fresh arm/evidence collision; do not overwrite')
    if not calibrate:
        cost=json.loads(report_path(evidence,arm,True).read_text())
        if (cost.get('status')!='COST_CALIBRATION_COMPLETE' or cost.get('code_sha256')!=metadata['code_sha256']
                or cost.get('corpus_sha256')!=data.digest(corpus/'report.json')):
            raise FileNotFoundError('same-code/corpus successful cost gate required')
    from tinylm.train import mtp_sft as core
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    idle_before_gpu()
    started=time.perf_counter()
    with wall_limit(args.max_wall_sec):
        torch,base,cfg,tok,initial=load_runtime(arm)
        records=encoded(corpus,report,tok)
        expected_steps=4*math.ceil(len(records['train'])/128)
        pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('PAD identity absent')
        idle_before_gpu()
        base=base.cuda();base.train()
        os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p101a_sft_mtp_')
        model=torch.compile(base,mode='default')
        adam,muon=optimizers(model)
        torch.cuda.reset_peak_memory_stats()
        history=[];updates=processed=targets=0;grad_max=0.;head_grad_updates=0;seconds=[]
        head_grad_seen={str(h):0 for h in (2,3,4)}
        stop=False;before_answers=None;before_native=None;before_native_ce=None
        if not calibrate:
            from scripts.p106b_education_followup import answers,native_text_probes,ARMS as STUDENTS
            target.parent.mkdir(parents=True,exist_ok=False)
            before_answers=answers(base,cfg,tok,target.parent,'initial_'+arm)
            before_native=native_text_probes(base,cfg,tok,target.parent,'initial_'+arm,ROOT/STUDENTS['b']['cache'])
            before_native_ce=native_ce(base,ROOT/STUDENTS['b']['cache'])
        initial_val=None if calibrate else evaluate(base,records['val'],pad)
        for epoch in range(4):
            epoch_x=epoch_targets=0;epoch_started=time.perf_counter()
            epoch_nll={h:torch.zeros((),device='cuda') for h in (1,2,3,4)}
            epoch_valid={h:0 for h in (1,2,3,4)}
            for groups in batches(records['train'],epoch):
                tick=time.perf_counter();denominators={h:0 for h in (1,2,3,4)}
                for micro in groups:
                    for rec in micro:
                        for h,c in core.count_record(rec).items():denominators[h]+=c
                weights=core.coefficients(updates,expected_steps) if cfg.mtp_aux else {}
                active=tuple(h for h,v in weights.items() if v)
                adam.zero_grad(set_to_none=True);muon.zero_grad(set_to_none=True)
                for micro in groups:
                    x,y,seg=core.pad_records(micro,pad,'cuda',fixed_width=1024,batch_size=8)
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        hidden=model(x,return_hidden=True)
                        sums,valid=core.components(base,hidden,y,seg,horizons=active)
                        loss=core.normalized_loss(sums,denominators,weights)
                    if not torch.isfinite(loss):raise ValueError('nonfinite masked MTP loss')
                    loss.backward();epoch_x+=sum(r.x_tokens for r in micro)
                    epoch_targets+=sum(r.targets for r in micro)
                    for h,value in sums.items():epoch_nll[h]+=value.detach();epoch_valid[h]+=valid[h]
                grads=[p.grad for p in base.parameters() if p.grad is not None]
                if not grads or not all(torch.isfinite(g).all() for g in grads):raise ValueError('missing/nonfinite gradients')
                grad_max=max(grad_max,max(float(g.abs().max()) for g in grads))
                if any(getattr(base,f'mtp_up{h}') is not None and getattr(base,f'mtp_up{h}').grad is not None
                       and bool(getattr(base,f'mtp_up{h}').grad.ne(0).any()) for h in (2,3,4)):
                    head_grad_updates+=1
                for h in (2,3,4):
                    parameter=getattr(base,f'mtp_up{h}')
                    if parameter is not None and parameter.grad is not None and bool(parameter.grad.ne(0).any()):
                        head_grad_seen[str(h)]+=1
                torch.nn.utils.clip_grad_norm_(base.parameters(),1.)
                adam.step();muon.step();torch.cuda.synchronize()
                updates+=1;processed+=sum(r.x_tokens for micro in groups for r in micro)
                targets+=denominators[1];seconds.append(time.perf_counter()-tick)
                if updates==1 or updates%25==0:
                    print('[SFT_MTP_UPDATE] '+json.dumps(dict(arm=arm,updates=updates,actual_x_tokens=processed,
                        assistant_targets=targets,seconds=seconds[-1],aux_weights=weights)),flush=True)
                if calibrate and updates>=32:stop=True;break
            if not calibrate:
                val=evaluate(base,records['val'],pad)
                history.append(dict(epoch=epoch+1,updates=updates,processed_x_tokens=epoch_x,
                    assistant_targets=epoch_targets,val=val,
                    train_ce={str(h):float(epoch_nll[h])/epoch_valid[h] if epoch_valid[h] else None for h in epoch_nll},
                    active_head_target_counts={str(h):v for h,v in epoch_valid.items()},
                    wall_sec=time.perf_counter()-epoch_started))
            if stop:break
        if not calibrate and (updates!=expected_steps or processed!=4*report['actual_unique_train_x_tokens']):
            raise ValueError('real row/token/four-pass exposure differs')
        result=dict(metadata,arm=arm,initial_core_sha256=initial,
            initializer='SCRATCH_NO_WEIGHT_INIT' if arm.startswith('scratch_') else 'PINNED_PARENT_WEIGHT_ONLY',
            corpus_sha256=data.digest(corpus/'report.json'),updates=updates,expected_full_updates=expected_steps,
            actual_processed_x_tokens=processed,assistant_targets=targets,history=history,
            grad_max=grad_max,aux_nonzero_gradient_updates=head_grad_updates,
            per_head_nonzero_gradient_updates=head_grad_seen,initial_val=initial_val,
            model_loading='MEASURED',meaningful_training='RESOURCE_ONLY' if calibrate else 'EXPERIMENTAL_PSEUDO_SFT',
            head_tensor_bytes=base.mtp_head_bytes(),torch_peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
            torch_peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
            update_seconds=seconds,whole_wall_sec=time.perf_counter()-started,
            actual_x_per_whole_sec=processed/(time.perf_counter()-started),
            code_sha256=metadata['code_sha256'],checkpoint_saved=False)
        if calibrate:
            result['status']='COST_CALIBRATION_COMPLETE'
            result['quality_claim']='NOT_RUN;32 updates measure cost/resource only'
            result['estimated_full_update_sec']=sum(seconds[1:])/max(1,len(seconds)-1)*expected_steps+seconds[0]
        else:
            from scripts.p106b_education_followup import answers,native_text_probes,ARMS as STUDENTS
            result['initial_answers']=before_answers
            result['final_answers']=answers(base,cfg,tok,target.parent,'final_'+arm)
            result['initial_native_text']=before_native
            result['native_text']=native_text_probes(base,cfg,tok,target.parent,'final_'+arm,ROOT/STUDENTS['b']['cache'])
            result['initial_native_ce']=before_native_ce
            result['final_native_ce']=native_ce(base,ROOT/STUDENTS['b']['cache'])
            payload=base.mtp_deployment_payload(keep_aux=True) if cfg.mtp_aux else dict(model=base.state_dict(),cfg=asdict(cfg))
            out.parent.mkdir(parents=True,exist_ok=True)
            with out.open('xb') as stream:
                torch.save(dict(payload,step=updates,tokenizer_sha256=data.TOK_SHA,
                    tokenizer_lineage='chat32',mtp_sft=dict(arm=arm,corpus_sha256=result['corpus_sha256'],
                    initializer=result['initializer'],initial_core_sha256=initial,updates=updates)),stream)
            result.update(status='SFT_MTP_TRAINED_EVAL_PENDING',checkpoint_saved=True,
                checkpoint=str(out.relative_to(ROOT)),checkpoint_sha256=data.digest(out))
        result['whole_wall_sec']=time.perf_counter()-started
        result['actual_x_per_whole_sec']=processed/result['whole_wall_sec']
        result['whole_wall_scope']='runtime input encoding/model/compile/train/eval/checkpoint export; prerequisite hash verification and final report serialization excluded'
        write(target,result)
    print('[SFT_MTP_FINAL] '+json.dumps({k:result.get(k) for k in ('arm','status','updates','actual_processed_x_tokens',
        'head_tensor_bytes','torch_peak_reserved_mib','checkpoint_saved')},ensure_ascii=False),flush=True)
    return 0


def compare(args,evidence):
    results={a:json.loads(report_path(evidence,a).read_text()) for a in ARMS}
    if any(r.get('status')!='SFT_MTP_TRAINED_EVAL_PENDING' or not r.get('checkpoint_saved')
            for r in results.values()):raise FileNotFoundError('all four completed arms required')
    for initializer in ('scratch','parent'):
        left,right=(results[initializer+'_'+h] for h in ('ntp','mtp'))
        for key in ('initial_core_sha256','corpus_sha256','actual_processed_x_tokens','assistant_targets','updates','code_sha256'):
            if left[key]!=right[key]:raise ValueError('NTP/MTP unmatched '+initializer+':'+key)
    summary=dict(schema=SCHEMA,status='PAIRED_RESULTS_READ',results=results,
        comparison='within initializer NTP versus MTP; initializer contrast separate',
        architecture_superiority='NOT_ESTABLISHED_SINGLE_SEED',semantic_quality='RAW_ANSWER_REVIEW_REQUIRED')
    write(evidence/'compare'/'report.json',summary)
    for arm,result in results.items():
        print('[MTP_PAIR] '+json.dumps(dict(arm=arm,val=result['history'][-1]['val'],
            answers=result.get('final_answers'),actual_x=result['actual_processed_x_tokens'],
            whole_sec=result['whole_wall_sec'],head_bytes=result['head_tensor_bytes'])),flush=True)
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('contract','prepare','calibrate','train','compare','infer'),required=True)
    parser.add_argument('--tag',default='p101a_sft_mtp_v1_s1337')
    parser.add_argument('--arm',choices=ARMS,default='scratch_ntp')
    parser.add_argument('--max-wall-sec',type=int,default=10800)
    choice=parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--check-only',action='store_true');choice.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    corpus,evidence=paths(args.tag);metadata=info(args)
    if not 1<=args.max_wall_sec<=21600:raise ValueError('bounded user wall time required')
    if args.check_only:
        print('[CHECK_ONLY] '+json.dumps(dict(metadata,mode=args.mode,arm=args.arm,
            data_ready=(corpus/'report.json').is_file(),model_loading='NOT_RUN'),ensure_ascii=False));return 0
    try:
        if args.mode=='contract':
            for script in ('test_p101a_sft_mtp.py','test_p101a_sft_mtp_data.py','test_p101a_sft_mtp_driver.py'):
                result=subprocess.run([sys.executable,'-B','-X','utf8','scripts/'+script],cwd=ROOT,timeout=600)
                if result.returncode:return result.returncode
            write(evidence/'contract'/'report.json',dict(metadata,status='CPU_CONTRACT_PASS'));return 0
        if args.mode=='prepare':
            contract=json.loads((evidence/'contract'/'report.json').read_text())
            if contract.get('status')!='CPU_CONTRACT_PASS' or contract['code_sha256']!=metadata['code_sha256']:
                raise FileNotFoundError('current code CPU contract required')
            report=data.prepare(corpus)
            print('[MTP_CORPUS] '+json.dumps({k:report[k] for k in ('status','actual_unique_train_x_tokens','target_processed_x_tokens','deficits')}),flush=True)
            return 0 if report['status']=='CORPUS_READY' else 8
        if args.mode in ('train','calibrate'):
            return train_arm(args,corpus,evidence,metadata,calibrate=args.mode=='calibrate')
        if args.mode=='compare':return compare(args,evidence)
        from scripts.p101a_sft_mtp_infer import run
        return run(args,corpus,evidence,metadata)
    except (FileNotFoundError,FileExistsError) as error:
        print('[HOLD] '+str(error),flush=True);return 8
    except BaseException as error:
        rc=130 if isinstance(error,KeyboardInterrupt) else 9
        failure=evidence/('failure_'+args.mode+'_'+args.arm)/'report.json'
        record=dict(metadata,status='INTERRUPTED' if rc==130 else 'EXECUTION_ERROR',returncode=rc,
            mode=args.mode,arm=args.arm,error_type=type(error).__name__,reason=str(error)[:2000],
            partial_outputs='PRESERVED_IF_CREATED; not a completed training/checkpoint proof',
            model_loading='UNKNOWN_RUNTIME_PROGRESS',automatic_retry=False)
        if not failure.exists():write(failure,record)
        print('[EXECUTION_ERROR] '+json.dumps(record,ensure_ascii=False),flush=True)
        return rc


if __name__=='__main__':raise SystemExit(main())
