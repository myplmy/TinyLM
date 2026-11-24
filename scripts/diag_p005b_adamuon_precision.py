"""CPU 2x2 arithmetic trajectories, using no model/data/checkpoint/GPU."""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT)not in sys.path:sys.path.insert(0,str(ROOT))
BASE=ROOT/'test_result/evidence/p005b_adamuon_precision_v1_20261117'
AUDIT=ROOT/'handoff/audit/research_20261117_01a1e647'
SOURCES=('scripts/p005b_adamuon_precision.py','scripts/test_p005b_adamuon_precision.py',
 'scripts/diag_p005b_adamuon_precision.py','tinylm/train/adamuon.py','tinylm/train/muon.py')
PRIMARY='handoff/audit/research_20261117_01a1e647/ADAMUON_PRIMARY_PINNED_v1.json'
CONTRACT='test_result/078_log_20261117_P005b_Stage17Wa_precision_contracts.txt'
SHAPES=((3,7),(7,3),(8,8),(32,64),(64,32))
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,value):
    raw=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(raw)>=20_000_000:raise ValueError('metadata cap20MB')
    with Path(path).open('xb')as stream:stream.write(raw)
def prepare():
    raw=(ROOT/CONTRACT).read_text(encoding='utf-8')
    assert 'Ran 6 tests' in raw and '[runlog] 종료코드 0' in raw
    primary=read(ROOT/PRIMARY)
    assert primary['commit']=='9c1ba5be86ebd7dd7464a0bc43b28daccf40279e'
    assert primary['all_main_and_pinned_blobs_identical'] is True
    profile=dict(user_directive=158,UTC=datetime.now(timezone.utc).isoformat(),
        sources={name:sha(ROOT/name)for name in SOURCES},
        inputs={name:sha(ROOT/name)for name in(PRIMARY,CONTRACT)},primary=primary,
        shapes=SHAPES,nesterov=(False,True),seed=1337,steps=5,beta=.95,lr=.01,
        weight_decay=.1,ns_steps=5,eps=1e-8,synthetic_FP32_weight_and_gradients=True,
        factors=dict(NS=['LOCAL_GRAM_SQUARE_THEN_COEFFICIENT','AUTHOR_COEFFICIENT_THEN_GRAM_PRODUCT'],
                     tail=['FP32_V_AND_NORMALIZATION','BF16_V_AND_NORMALIZATION']),
        maximum_seconds=300,minimum_available_RAM_bytes=1<<30,
        maximum_output_bytes=20_000_000,original_model_loads=0,GPU_calls=0,
        original_optimizer_cost_reexecuted=False,training=False,quality_adoption=False,
        comparison='10_CASES_4_FACTOR_TRAJECTORIES_5_STEPS_PLUS_50_EXISTING_CLASS_CONTROL_STEPS')
    BASE.mkdir(exist_ok=False);write(BASE/'profile.json',profile)
    print('ADAMUON_PRECISION_PROFILE',sha(BASE/'profile.json'),'10cases/4factors/5steps/model0',flush=True)
def actual():
    import torch
    import numpy as np
    import psutil
    from scripts.p005b_adamuon_precision import local_step,NS_ORDERS,TAILS
    from tinylm.train.adamuon import AdaMuon
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    start=time.perf_counter();profile=read(BASE/'profile.json')
    out=BASE/'actual';out.mkdir(exist_ok=False)
    process=psutil.Process()
    report=dict(status='STARTED',returncode=1,profile_sha256=sha(BASE/'profile.json'),
        rows=[],comparisons=[],synthetic_optimizer_step_calls=0,local_arithmetic_step_calls=0,
        model_loads=0,model_forward=0,model_optimizer_updates=0,GPU_calls=0,
        original_checkpoint_or_data_reads=0,quality_adoption=False,RSS_entry=process.memory_info().rss)
    def signature(tensor):
        raw=tensor.detach().contiguous().view(torch.uint8).numpy().tobytes()
        return dict(shape=list(tensor.shape),dtype=str(tensor.dtype),bytes=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest().upper())
    def check():
        if time.perf_counter()-start>profile['maximum_seconds']:raise TimeoutError('wall300s')
        if datetime.now(timezone.utc)>=datetime.fromisoformat('2026-11-17T16:40:00+09:00'):
            raise TimeoutError('current CPU arithmetic cutoff')
        for name,expected in{**profile['sources'],**profile['inputs']}.items():
            if sha(ROOT/name)!=expected:raise ValueError('frozen source/input changed '+name)
        if torch.cuda.is_initialized():raise ValueError('CPU calculation initialized CUDA')
    try:
        check()
        if psutil.virtual_memory().available<profile['minimum_available_RAM_bytes']:raise ValueError('available RAM1GiB')
        rng=torch.Generator(device='cpu').manual_seed(profile['seed'])
        arrays={};rms={f'N{n}T{t}':[]for n in range(2)for t in range(2)}
        for shape in profile['shapes']:
            for nesterov in profile['nesterov']:
                case='x'.join(map(str,shape))+'_nesterov'+str(int(nesterov))
                initial=torch.randn(shape,generator=rng)*.2
                states={f'N{n}T{t}':dict(weight=initial.clone(),momentum=torch.zeros_like(initial),
                    variance=torch.zeros_like(initial,dtype=torch.float32 if t==0 else torch.bfloat16))
                    for n in range(2)for t in range(2)}
                control=torch.nn.Parameter(initial.clone())
                optimizer=AdaMuon([control],lr=profile['lr'],momentum=profile['beta'],nesterov=nesterov,
                    ns_steps=profile['ns_steps'],weight_decay=profile['weight_decay'],eps=profile['eps'])
                for step in range(profile['steps']):
                    check()
                    gradient=torch.randn(shape,generator=rng);gradient_signature=signature(gradient)
                    for n in range(2):
                        for t in range(2):
                            key=f'N{n}T{t}';old=states[key]
                            before={k:signature(v)for k,v in old.items()if k in('weight','momentum','variance')}
                            now=local_step(old['weight'],gradient,old['momentum'],old['variance'],
                                ns_order=NS_ORDERS[n],tail=TAILS[t],beta=profile['beta'],lr=profile['lr'],
                                nesterov=nesterov,weight_decay=profile['weight_decay'],ns_steps=profile['ns_steps'],eps=profile['eps'])
                            assert before=={k:signature(old[k])for k in before}
                            assert signature(gradient)==gradient_signature
                            assert now['state_bytes']==initial.numel()*(8 if t==0 else 6)
                            update_rms=float(now['update'].float().square().mean().sqrt());rms[key].append(update_rms)
                            report['rows'].append(dict(case=case,step=step+1,factor=key,
                                signatures={k:signature(now[k])for k in('weight','momentum','variance','update')},
                                update_RMS=update_rms,state_bytes=now['state_bytes'],input_buffers_unchanged=True))
                            states[key]=now;report['local_arithmetic_step_calls']+=1
                    control.grad=gradient.clone();optimizer.step();report['synthetic_optimizer_step_calls']+=1
                    for key,value in(('weight',control.detach()),('momentum',optimizer.state[control]['momentum_buffer']),
                                     ('variance',optimizer.state[control]['v_buffer'])):
                        assert torch.equal(states['N0T0'][key],value),'current class control '+key
                    assert torch.equal(control.grad,gradient)
                    for axis,pairs in(('NS_ORDER',(('N0T0','N1T0'),('N0T1','N1T1'))),
                                       ('TAIL_PRECISION',(('N0T0','N0T1'),('N1T0','N1T1')))):
                        for a,b in pairs:
                            left,right=states[a]['weight'],states[b]['weight']
                            difference=(left.double()-right.double()).abs()
                            report['comparisons'].append(dict(case=case,step=step+1,axis=axis,arm_a=a,arm_b=b,
                                different_elements=int((left!=right).sum()),max_abs=float(difference.max()),
                                rms_abs=float(difference.square().mean().sqrt()),
                                trajectory='SAME_INITIAL_WEIGHT_AND_GRADIENT_STREAM_FACTOR_FIXED_FROM_STEP1'))
                for key,state in states.items():
                    for name in('weight','momentum','variance','update'):
                        value=state[name].detach().contiguous()
                        arrays[case+'_'+key+'_'+name]=value.view(torch.uint16).numpy().copy() if value.dtype==torch.bfloat16 else value.numpy().copy()
                print('ADAMUON_PRECISION_CASE',case,'control5 EXACT/factors20',flush=True)
                del states,control,optimizer,gradient,old,now,value,initial,left,right,difference
        vector_path=out/'synthetic_final_vectors.npz'
        with vector_path.open('xb')as stream:np.savez_compressed(stream,**arrays)
        assert vector_path.stat().st_size<profile['maximum_output_bytes']
        assert report['synthetic_optimizer_step_calls']==50 and report['local_arithmetic_step_calls']==200
        assert len(report['comparisons'])==200 and len(report['rows'])==200
        report.update(status='CPU_ADAMUON_FACTOR_TRAJECTORIES_COMPLETE',returncode=0,
            current_class_control_steps=50,current_class_control_bit_equal=True,
            all_source_inputs_unchanged=True,all_input_buffers_unchanged=True,
            update_RMS_ranges={k:dict(minimum=min(v),maximum=max(v))for k,v in rms.items()},
            vector=dict(path=str(vector_path.relative_to(ROOT)),bytes=vector_path.stat().st_size,sha256=sha(vector_path)),
            state_B_per_element=dict(FP32_V=8,BF16_V=6),official_distributed_optimizer_executed=False)
        check()
    except BaseException as error:
        report.update(status='CPU_ADAMUON_FACTOR_ERROR',returncode=1,error=dict(type=type(error).__name__,message=str(error)))
    finally:
        gc.collect();report['CUDA_initialized']=torch.cuda.is_initialized()
        report['RSS_exit']=process.memory_info().rss;report['wall_seconds']=time.perf_counter()-start
        write(out/'report.json',report)
    print('ADAMUON_PRECISION_END',report['status'],report['returncode'],report['wall_seconds'],flush=True)
    return report['returncode']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','actual'));args=parser.parse_args()
    if args.action=='prepare':prepare();return 0
    return actual()
if __name__=='__main__':raise SystemExit(main())
