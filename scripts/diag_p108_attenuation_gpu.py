#!/usr/bin/env python3
"""Fixed four-calibration-example nonlinear margin check, never a test search."""
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import argparse
import gc
import json
import os
from pathlib import Path
import re
import time

import torch

from scripts import diag_p108_attenuation as cpu
from scripts import diag_p108_local_linear as previous
from scripts import interactive_research_infer as manual
from scripts import p108_balanced_practice as practice
from scripts import p108_local_linear as local
from scripts import p108_weight_space as surgery
from scripts.diag_p107_hybrid_mntp import independent_final_checks, close_owned_cuda

BASE = cpu.BASE
PROFILE = BASE/'gpu_profile_v2.json'
CPU_LOG = cpu.ROOT/'test_result/108_log_20261104_P108_Stage6c0W_local_hook_cleanup_cpu.txt'
SOURCES = ('scripts/diag_p108_attenuation_gpu.py','scripts/test_p108_attenuation_gpu.py')
IDS = tuple('calib_arithmetic_'+format(i,'03d') for i in range(4))


@contextmanager
def patch_activation(module, positions, values):
    if (not positions or len(positions) != len(set(positions)) or min(positions)<0
            or values.ndim != 2 or values.shape[0] != len(positions)
            or not bool(torch.isfinite(values).all())):
        raise ValueError('distinct positions and finite paired activation values required')
    seen=[]
    def hook(_m,_args,out):
        if seen or out.ndim != 3 or out.shape[0] != 1 or max(positions)>=out.shape[1] or out.shape[2]!=values.shape[1]:
            raise ValueError('single last-down call and output shape required')
        seen.append(True)
        if not bool((values != 0).any()):
            return out
        changed=out.clone()
        changed[0,positions]+=values.to(out)
        return changed
    handle=module.register_forward_hook(hook)
    try:
        yield
        if len(seen)!=1:
            raise ValueError('expected exactly one last-down call')
    finally:
        handle.remove()


def first_rows(capture):
    rows=[r for r in practice.make_data() if r['split']=='calib'][:4]
    if tuple(r['id'] for r in rows)!=IDS or tuple(r['id'] for r in capture['rows'][:4])!=IDS:
        raise ValueError('predeclared first four calibration IDs differ')
    offsets=[];offset=0
    for row in capture['rows'][:4]:
        offsets.append((offset,offset+row['targets']));offset+=row['targets']
    return rows,offsets


def prepare():
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='' or torch.cuda.is_initialized():
        raise RuntimeError('metadata preparation is CPU-only')
    if PROFILE.exists():
        raise FileExistsError(PROFILE)
    old=previous.verify()
    capture=previous.common.read_json(previous.BASE/'capture/report.json')
    analysis=previous.common.read_json(BASE/'cpu/report.json')
    raw=CPU_LOG.read_text(encoding='utf-8')
    if (analysis['actual_exit']!=0 or analysis['actual_cuda_initialized']
            or re.findall(r'종료코드\s+(-?\d+)',raw)!=['0'] or 'Ran 7 tests' not in raw or '\nOK\n' not in raw):
        raise ValueError('closed CPU signal/hook prerequisites required')
    rows,offsets=first_rows(capture)
    pins={str(path.relative_to(cpu.ROOT)):manual.file_sha(path) for path in
        [BASE/'profile.json',BASE/'cpu/report.json',CPU_LOG,
         *(cpu.ROOT/p for p in SOURCES),cpu.ROOT/'scripts/diag_p108_attenuation.py',
         cpu.ROOT/'scripts/diag_p107_hybrid_mntp.py',cpu.ROOT/'scripts/diag_p106b_resource_matrix.py',
         cpu.ROOT/'handoff/audit/nov04_weight_space/ATTENUATION_FIRST_FAILURE_v1.json',
         BASE/'gpu_profile.json']}
    profile=dict(schema='P108_CALIBRATION_LOCAL_ACTUAL_PROFILE_V1',authority_directive=107,
        deadline=previous.common.DEADLINE.isoformat(),max_phase_seconds=300,
        model=previous.MODEL,rows=rows,offsets=offsets,source_pins=pins,
        previous_profile_sha256=manual.file_sha(previous.BASE/'profile.json'),
        previous_capture_sha256=manual.file_sha(previous.BASE/'capture/report.json'),
        previous_packet_sha256=capture['packet_sha256'],layer=old['layer'],
        variants=['original','selected_cap_0.0025','rank16_unbounded','input_specific_oracle','original_after'],
        precision='FP32_MATH',quality_claim=False,new_test_selection=False,
        optimizer_updates=0,checkpoint_writes=0,oracle_uses_gold=True,
        allocator_cap_bytes=6*1024**3)
    previous.common.write_json(PROFILE,profile)
    print(json.dumps(dict(profile_sha256=manual.file_sha(PROFILE),ids=list(IDS),model_loads=0,actual_cuda_initialized=False)))


def verify():
    profile=previous.common.read_json(PROFILE)
    if (profile['schema']!='P108_CALIBRATION_LOCAL_ACTUAL_PROFILE_V1'
            or profile['authority_directive']!=107 or profile['deadline']!=previous.common.DEADLINE.isoformat()
            or tuple(r['id'] for r in profile['rows'])!=IDS or profile['max_phase_seconds']!=300
            or profile['layer']!=13 or profile['model']!=previous.MODEL):
        raise ValueError('fixed local diagnosis contract differs')
    for name,sha in profile['source_pins'].items():
        if manual.file_sha(manual.owned_path(name))!=sha:
            raise ValueError('local diagnosis source/input changed: '+name)
    old=previous.verify()
    if manual.file_sha(previous.BASE/'profile.json')!=profile['previous_profile_sha256']:
        raise ValueError('original calibrated profile differs')
    capture=previous.common.read_json(previous.BASE/'capture/report.json')
    if (manual.file_sha(previous.BASE/'capture/report.json')!=profile['previous_capture_sha256']
            or capture['packet_sha256']!=profile['previous_packet_sha256']):
        raise ValueError('original capture differs')
    rows,offsets=first_rows(capture)
    if rows!=profile['rows'] or offsets!=[tuple(v) for v in profile['offsets']]:
        raise ValueError('fixed row content or target offsets changed')
    return profile,old


def logits_for(active,row):
    from torch.nn.attention import sdpa_kernel,SDPBackend
    ids,positions,targets=previous.token_contract(active['tokenizer'],row['question'],row['expected'])
    with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
        logits=active['model'](torch.tensor([ids],device='cuda',dtype=torch.long))
        result=logits[0,positions].detach().cpu()
    if not bool(torch.isfinite(result).all()):
        raise ValueError('nonfinite actual logits')
    return result,positions,targets


def measure(logits,targets,fixed_others):
    gold=torch.tensor(targets,dtype=torch.long)
    top=logits.topk(2,dim=-1).indices
    actual_other=torch.where(top[:,0]==gold,top[:,1],top[:,0])
    at=torch.arange(len(gold))
    return dict(gold_argmax=int((logits.argmax(-1)==gold).sum()),targets=len(gold),
        tokens=[dict(target=int(gold[i]),fixed_competitor=int(fixed_others[i]),
            actual_competitor=int(actual_other[i]),argmax=int(logits[i].argmax()),
            fixed_margin=float(logits[i,gold[i]]-logits[i,fixed_others[i]]),
            actual_margin=float(logits[i,gold[i]]-logits[i,actual_other[i]])) for i in range(len(gold))])


def finish_checks(report, actions):
    good=independent_final_checks(report,actions)
    report.update(status='TECHNICAL_COMPLETE' if good else 'FINAL_VERIFICATION_ERROR',actual_exit=0 if good else 9)
    return good


def verify_original_checkpoint(original):
    spec=manual.resolve_model(previous.MODEL)
    if manual.file_sha(manual.owned_path(spec.checkpoint))!=original['checkpoint_sha256']:
        raise ValueError('original checkpoint file changed')


def execute():
    profile,old=verify()
    if datetime.now(timezone.utc).timestamp()+420>=previous.common.DEADLINE.timestamp():
        raise TimeoutError('diagnosis plus cleanup does not fit authority window')
    directory=BASE/'gpu_v2'
    if directory.exists():
        raise FileExistsError('actual diagnosis already started')
    packet,capture=previous.load_packet(torch)
    budget=previous.common.Budget(profile);budget.check()
    directory.mkdir(exist_ok=False)
    records=[];memory=None;original=None;core_after=None
    with manual.selected_runtime(manual.resolve_model(previous.MODEL)) as active:
        torch.set_num_threads(4)
        torch.cuda.set_per_process_memory_fraction(min(1.,profile['allocator_cap_bytes']/torch.cuda.get_device_properties(0).total_memory))
        torch.cuda.reset_peak_memory_stats()
        original=previous.origin(active)
        if original!=capture['origin']:
            raise ValueError('current original model differs from captured model')
        module=dict(surgery.down_modules(active['model']))[profile['layer']]
        selected,selection=local.bounded_delta(packet['factors'],module._wq.detach(),.0025)
        old_search=previous.common.read_json(previous.BASE/'search/report.json')
        if surgery.tensor_sha(selected)!=old_search['selected']['requested_delta_sha256']:
            raise ValueError('selected historical GPU correction changed')
        raw=packet['factors']['left'].to(module._wq)@packet['factors']['right'].to(module._wq)
        for row,(begin,end) in zip(profile['rows'],profile['offsets']):
            budget.check()
            baseline,positions,targets=logits_for(active,row)
            gold=torch.tensor(targets,dtype=torch.long);top=baseline.topk(2,dim=-1).indices
            others=torch.where(top[:,0]==gold,top[:,1],top[:,0])
            measured=measure(baseline,targets,others)
            recorded=packet['margins'][begin:end]
            current=torch.tensor([v['fixed_margin'] for v in measured['tokens']])
            if not torch.equal(current,recorded):
                raise ValueError('same original calibration margin is not bit-identical')
            item=dict(id=row['id'],question=row['question'],gold=row['expected'],targets=targets,
                variants={'original':measured},original_margin_exact=True)
            for name,delta in (('selected_cap_0.0025',selected),('rank16_unbounded',raw)):
                budget.check()
                with surgery.edit_weights(active['model'],active['route'],[(profile['layer'],delta)],'effective') as receipt:
                    actual,_,actual_targets=logits_for(active,row)
                if actual_targets!=targets:
                    raise ValueError('teacher-forced target sequence changed')
                item['variants'][name]=measure(actual,targets,others)
                item.setdefault('edit_receipts',{})[name]=receipt
            with patch_activation(module,positions,packet['values'][begin:end]):
                oracle,_,oracle_targets=logits_for(active,row)
            if oracle_targets!=targets:
                raise ValueError('oracle changed target sequence')
            item['variants']['input_specific_oracle']=measure(oracle,targets,others)
            after,_,_=logits_for(active,row)
            if not torch.equal(baseline,after):
                raise ValueError('original logits were not fully restored')
            item['variants']['original_after']=measure(after,targets,others)
            records.append(item)
            print('[LOCAL_ACTUAL]',row['id'],json.dumps({n:r['gold_argmax'] for n,r in item['variants'].items()}),flush=True)
        core_after=manual.state_fingerprint(active['model'])
        if core_after!=original['core_sha256'] or any(p.grad is not None for p in active['model'].parameters()):
            raise ValueError('local diagnosis changed registered model or gradients')
        memory=dict(allocated_peak_bytes=torch.cuda.max_memory_allocated(),reserved_peak_bytes=torch.cuda.max_memory_reserved())
        module=selected=raw=delta=receipt=None
    report=dict(schema='P108_CALIBRATION_LOCAL_ACTUAL_V2',
        profile_sha256=manual.file_sha(PROFILE),origin=original,records=records,vram=memory,
        repeated_gold_target_exposures=sum(len(r['targets']) for r in records),new_gold_target_positions=0,
        new_test_selection=False,quality_claim=False,optimizer_updates=0,checkpoint_writes=0,
        original_core_after=core_after,
        nvml_scope='STRICT_IDLE_POINT_QUERY_NOT_CONTINUOUS_OOM_GUARANTEE',
        old_test_verdict='GATE_NEGATIVE_UNCHANGED',wall_seconds=time.monotonic()-budget.start)
    good=finish_checks(report,[('owned_cuda_cleanup',lambda:close_owned_cuda(torch,report)),
        ('frozen_sources_and_inputs',verify),('original_checkpoint',lambda:verify_original_checkpoint(original))])
    report.update(original_checkpoint_unchanged=not any(e['stage']=='original_checkpoint' for e in report['final_verification_errors']),
        old_inputs_unchanged=not any(e['stage']=='frozen_sources_and_inputs' for e in report['final_verification_errors']),
        wall_seconds=time.monotonic()-budget.start)
    previous.common.write_json(directory/'report.json',report)
    print('[FINAL]',json.dumps({k:report[k] for k in ('status','actual_exit','wall_seconds','vram','repeated_gold_target_exposures','final_cuda_cleanup')}),flush=True)
    if not good:
        raise RuntimeError('final verification failed; partial actual report preserved')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('prepare','check','execute'))
    phase=parser.parse_args().phase
    if phase=='prepare':prepare()
    elif phase=='check':
        p,_=verify();print(json.dumps(dict(status='METADATA_ONLY',profile_sha256=manual.file_sha(PROFILE),model_loads=0,ids=[r['id'] for r in p['rows']])))
    else:execute()


if __name__=='__main__':
    main()
