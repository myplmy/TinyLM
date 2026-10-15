#!/usr/bin/env python3
"""No-update right-padding comparison on one exact joint-course update."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from contextlib import nullcontext
from datetime import datetime,timezone
import json
import math
import os
import tempfile
import time
from scripts import diag_p106b_joint_decimal as course
from scripts import p106b_padding_probe as method
from scripts.p106b_native_windows import reader as native_reader
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit,GateNegative
TAG='p106b_padding_probe_v1_s1337'
EVIDENCE=ROOT/'test_result/evidence'/TAG
CODE=('scripts/p106b_padding_probe.py','scripts/test_p106b_padding_probe.py','scripts/diag_p106b_padding_probe.py')


def census(rows):
    lengths=[r['meta']['actual_x_tokens'] for r in rows]
    return dict(rows=len(rows),actual_x_tokens=sum(lengths),fixed_positions=1024*len(rows),
        maximum=max(lengths),rowwise_aligned_positions=sum(method.width([v],True) for v in lengths),
        note='rowwise ideal is not real batched width; public QA is not added to this course')


def gradient_comparison(model,reference):
    import torch
    norm=diff=dot=other_norm=0.;maximum=0.;count=0
    for name,p in model.named_parameters():
        previous=reference[name]
        if (p.grad is None)!=(previous is None):raise ValueError('gradient presence differs')
        if previous is None:continue
        now=p.grad.detach().cpu().double();old=previous.double();delta=now-old
        norm+=float(old.square().sum());other_norm+=float(now.square().sum())
        diff+=float(delta.square().sum());dot+=float((old*now).sum());maximum=max(maximum,float(delta.abs().max()))
        count+=now.numel()
    if not norm or not other_norm:raise ValueError('nonzero whole-body gradients required')
    return dict(relative_l2=math.sqrt(diff/norm),cosine=dot/math.sqrt(norm*other_norm),
        maximum_abs=maximum,reference_l2=math.sqrt(norm),compared_parameters=count,gradient_presence_equal=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    p.add_argument('--max-wall-sec',type=int,default=600);args=p.parse_args()
    if not 60<=args.max_wall_sec<=600:p.error('bounded60..600')
    driver=course.driver;driver.base.deadline();r,rows=course.read_course();summary=census(rows['train'])
    parent=course.prior.parent_ref(True)
    if EVIDENCE.exists():raise FileExistsError('old padding observation preserved')
    if args.check_only:
        print('[PADDING_PREFLIGHT] '+json.dumps(dict(tag=TAG,parent=parent,census=summary,model_loaded=False)),flush=True);return 0
    remaining=(driver.base.DEADLINE-datetime.now(timezone.utc)).total_seconds()
    if remaining<args.max_wall_sec+2700:raise GateNegative('retain17 closing margin')
    from tinylm.train import mtp_sft as core
    from torch.nn.attention import SDPBackend,sdpa_kernel
    import numpy as np
    idle_before_gpu();began=time.perf_counter()
    with wall_limit(args.max_wall_sec):
        torch,model,cfg,tok,initial=course.prior.load_from_parent('parent_ntp')
        records=[core.encode_record(row,tok) for row in rows['train']]
        groups=next(driver.base.training.batches(records,0))
        if sum(len(v) for v in groups)!=128:raise ValueError('exact first128 whole update required')
        metadata={id(rec):row['meta'] for rec,row in zip(records,rows['train'])}
        input_ids=[id(rec) for micro in groups for rec in micro]
        counts=Counter(metadata[k]['language']+':'+metadata[k]['kind'] for k in input_ids)
        denominator=sum(rec.targets for micro in groups for rec in micro)
        native=native_reader(ROOT,r)
        native_records=[core.Record(a[:-1].astype(np.int64).tolist(),a[1:].astype(np.int64).tolist(),[1]*1024) for a in native[:8]]
        pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('pad absent')
        widths=[method.width([len(rec.x) for rec in micro],True) for micro in groups]
        model=model.cuda();model.train()
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False

        def one_update(forward,trim,bf16):
            model.zero_grad(set_to_none=True);torch.cuda.synchronize();tick=time.perf_counter();sft_loss=0.;targets=0
            for micro in groups:
                width=method.width([len(rec.x) for rec in micro],trim)
                x,y,seg=core.pad_records(micro,pad,'cuda',fixed_width=width,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16) if bf16 else nullcontext():
                    hidden=forward(x,return_hidden=True);sums,valid=core.components(model,hidden,y,seg,horizons=())
                    loss=sums[1]/denominator
                if not torch.isfinite(loss):raise ValueError('nonfinite word loss')
                loss.backward();sft_loss+=float(loss.detach());targets+=valid[1]
            x,y,seg=core.pad_records(native_records,pad,'cuda',fixed_width=1024,batch_size=8)
            with torch.autocast('cuda',dtype=torch.bfloat16) if bf16 else nullcontext():
                hidden=forward(x,return_hidden=True);sums,valid=core.components(model,hidden,y,seg,horizons=());native_loss=sums[1]/8192
            native_loss.backward();torch.cuda.synchronize()
            if targets!=denominator or valid[1]!=8192:raise ValueError('actual targets changed by padding')
            return dict(sec=time.perf_counter()-tick,sft_ce=sft_loss,native_ce=float(native_loss.detach()),
                loss=sft_loss+float(native_loss.detach()),assistant_targets=targets,native_targets=valid[1],optimizer_updates=0)

        with sdpa_kernel(SDPBackend.MATH):
            fixed_fp32=one_update(model,False,False)
            reference={name:None if p.grad is None else p.grad.detach().cpu().clone() for name,p in model.named_parameters()}
            trimmed_fp32=one_update(model,True,False);grad=gradient_comparison(model,reference);del reference
        close=method.close_fp32(fixed_fp32['loss'],trimmed_fp32['loss'],grad['relative_l2'],grad['cosine'])
        os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_padding_probe_')
        compiled=torch.compile(model,mode='default');cold={}
        for label,trim in (('fixed1024',False),('right_trimmed',True)):
            driver.base.deadline();cold[label]=one_update(compiled,trim,True)
        timings=[]
        for pair,order in enumerate(((False,True),(True,False))):
            for trim in order:
                driver.base.deadline();value=one_update(compiled,trim,True)
                timings.append(dict(pair=pair,variant='right_trimmed' if trim else 'fixed1024',**value))
        ratios=[]
        for pair in range(2):
            values={v['variant']:v for v in timings if v['pair']==pair}
            ratios.append(values['fixed1024']['sec']/values['right_trimmed']['sec'])
        final=driver.base.training.state_fingerprint(model)
        if final!=initial:raise ValueError('no-update probe changed model body')
        result=dict(schema='P106B_RIGHT_PADDING_NO_UPDATE_V1',tag=TAG,status='RIGHT_PADDING_DIAGNOSTIC_COMPLETE',
            source_course_sha256=driver.base.training.data.digest(course.CORPUS/'report.json'),
            source_code_sha256=r['code_sha256'],code_sha256={v:driver.base.training.data.digest(ROOT/v) for v in CODE},
            parent=parent,census=summary,first_update_kind_counts=dict(counts),assistant_targets=denominator,
            actual_sft_x=sum(rec.x_tokens for micro in groups for rec in micro),native_targets_per_observation=8192,
            first_update_trimmed_micro_widths=widths,fixed_sft_positions=128*1024,
            trimmed_sft_positions=sum(8*v for v in widths),native_positions=8192,
            fp32=dict(fixed=fixed_fp32,trimmed=trimmed_fp32,gradient=grad,within_descriptive_bounds=close),
            compiled_bf16_cold=cold,compiled_bf16_warm=timings,paired_forward_backward_speed_ratios=ratios,
            body_before=initial,body_after=final,optimizer_updates=0,checkpoints_saved=0,
            peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,whole_sec=time.perf_counter()-began,
            memory_scope='one process/shared allocator and compiler caches; not independent variant memory comparison',
            missing_recipe_terms='state/decimal auxiliary, clipping and optimizer deliberately excluded',
            default_adopted=False,quality_eval='NOT_RUN',scope='same first128 word/native gradients and warm cost only; not whole-training parity, semantic quality or end-to-end speed guarantee')
        driver.base.training.write(EVIDENCE/'report.json',result)
    print('[PADDING_OBSERVATION] '+json.dumps(dict(status=result['status'],census=summary,widths=widths,
        fp32_close=close,gradient=grad,speed_ratios=ratios,whole_sec=result['whole_sec'],updates=0,default_adopted=False)),flush=True);return 0


if __name__=='__main__':raise SystemExit(main())
