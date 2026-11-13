#!/usr/bin/env python3
"""Fresh-process ABBA compiled padding costs; never a quality/adoption gate."""
import argparse
from contextlib import contextmanager
import copy
from datetime import datetime,timezone
import gc
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback
import weakref
from scripts import diag_p101a_padding_gpu as pad
from scripts import p101a_padding_shapes as shapes

ROOT=Path(__file__).resolve().parents[1]
TAG='p101a_padding_compiled_v2_20261113';BASE=ROOT/'test_result/evidence'/TAG
INVENTORY=ROOT/'test_result/evidence/p101a_padding_shapes_v2_20261113/report.json'
CACHE=ROOT/'tmp'/TAG
PLAN='test_plan/P101A_M0-U2-QK-MTP-기능계약.md'
DEADLINE=datetime(2026,11,13,8,tzinfo=timezone.utc)
SOURCES=('scripts/diag_p101a_compiled_padding.py','scripts/test_p101a_compiled_padding.py',
         'scripts/p101a_padding_shapes.py','scripts/diag_p107_hybrid_mntp.py',
         'scripts/diag_p106_full_coload_accum.py')
ARMS={mode+'_q'+str(q):(mode,q) for mode in ('ntp','mtp') for q in (128,64,32)}


def unpack_arm(name):
    if name not in ARMS:raise ValueError('registered explicit compiled cost arm required')
    return ARMS[name]


def guard(start=None,maximum=3600):
    if (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:raise TimeoutError('Nov13 final reserve')
    if start is not None and time.perf_counter()-start>maximum:raise TimeoutError('compiled PAD phase budget')


def phase_name(mtp,quantum):
    if mtp not in ('ntp','mtp') or type(quantum) is not int or quantum not in shapes.POLICIES:
        raise ValueError('explicit NTP/MTP and32/64/128 quantum required')
    return mtp+'_q'+str(quantum)


def ordered_groups(inventory):
    groups=sorted(inventory['selected_groups'],key=lambda x:x['absolute_update'])
    if len(groups)!=7 or len({g['absolute_update'] for g in groups})!=7:raise ValueError('same7 complete groups required')
    return groups


def denominators(groups):
    from tinylm.train import mtp_sft as core
    if len(groups)!=16 or any(len(m)!=8 for m in groups):raise ValueError('whole16x8 required')
    return {h:sum(core.count_record(r)[h] for m in groups for r in m) for h in (1,2,3,4)}


def source_map():
    result=pad.source_manifest();result.update({n:pad.digest(ROOT/n) for n in SOURCES})
    return result


def packages():
    return {n:importlib.metadata.version(n) for n in ('torch','triton','tokenizers')}


def prepare():
    guard()
    if BASE.exists() or CACHE.exists():raise FileExistsError('fresh compile namespace/cache required')
    inv=json.loads(INVENTORY.read_text())
    if inv['status']!='CPU_INVENTORY_COMPLETE_NOT_SPEED_OR_QUALITY' or not inv['known_defective_v3_not_admitted']:
        raise ValueError('closed masked shapes inventory required')
    for name,sha in dict(inv['sources'],**inv['assets']).items():
        if pad.digest(ROOT/name)!=sha:raise ValueError('inventory source/asset changed: '+name)
    if not shutil.which('c++'):raise FileNotFoundError('existing C++ compiler required; no automatic install')
    model_packages=packages()
    if model_packages['torch']!='2.10.0+cu130':raise ValueError('explicit existing PyTorch version required')
    BASE.mkdir();(BASE/'initial_plan.txt').write_bytes((ROOT/PLAN).read_bytes())
    pad.write_new(BASE/'profile.json',dict(schema='P101A_COMPILED_PADDING_V1',tag=TAG,authority_directive=115,
        deadline=DEADLINE.isoformat(),sources=source_map(),assets=inv['assets'],inventory_sha256=pad.digest(INVENTORY),
        selected_groups=ordered_groups(inv),plan_sha256=pad.digest(BASE/'initial_plan.txt'),packages=model_packages,
        policies=tuple(shapes.POLICIES),blocks=['fixed','crop','crop','fixed'],cold_cycles=1,steady_cycles=1,
        minimum_free_mib=8192,minimum_disk_bytes=16*2**30,max_phase_seconds=3600,max_child_seconds=1200,
        compile_mode='default',compile_dynamic='UNSPECIFIED_DEFAULT_NONE',optimizer_ns='UNCHANGED_PRODUCT_BF16',
        quality_claim=False,production_adopted=False,checkpoint_writes=0,known_defective_v3_not_admitted=True,
        resource_scope='7_FULL_GROUPS_REPEATED_NOT_704_MAIN_TRAINING',
        execution_interface='EXISTING_EXP_ARM_GRADE_WITH_EXPLICIT6_VARIANTS',
        concurrent_cpu_policy='ROOT_TEXT_WORK_ONLY_DURING_TIMING_NO_HEAVY_CPU_JOBS'))
    print('[PREPARED] '+TAG,flush=True)


def verify():
    p=json.loads((BASE/'profile.json').read_text())
    if p['authority_directive']!=115 or p['deadline']!=DEADLINE.isoformat() or p['sources']!=source_map():
        raise ValueError('frozen compiled authority/source differs')
    if p['packages']!=packages() or pad.digest(INVENTORY)!=p['inventory_sha256']:
        raise ValueError('existing dependency/inventory changed')
    if pad.digest(BASE/'initial_plan.txt')!=p['plan_sha256']:raise ValueError('frozen plan changed')
    for name,sha in p['assets'].items():
        if pad.digest(ROOT/name)!=sha:raise ValueError('exact old asset changed: '+name)
    return p


def run_child(command,stdout_path,seconds,env):
    """Existing owned-process-group cleanup, preserving complete child stdout."""
    from scripts.diag_p106_full_coload_accum import _kill_group
    process=None;started=time.perf_counter();timed_out=False
    try:
        with Path(stdout_path).open('x',encoding='utf-8') as stream:
            process=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,
                stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            while process.poll() is None:
                if time.perf_counter()-started>seconds:
                    timed_out=True;raise TimeoutError('owned compiled child budget')
                if Path(stdout_path).stat().st_size>18_000_000:raise RuntimeError('owned child log size stop')
                try:process.wait(timeout=.5)
                except subprocess.TimeoutExpired:pass
    finally:
        _kill_group(process)
        if process is not None:process.wait(timeout=10)
    return dict(returncode=process.returncode,seconds=time.perf_counter()-started,timed_out=timed_out)


@contextmanager
def termination_as_exception():
    previous=signal.getsignal(signal.SIGTERM)
    def stop(*_):raise TimeoutError('owned parent termination; child group cleanup required')
    signal.signal(signal.SIGTERM,stop)
    try:yield
    finally:signal.signal(signal.SIGTERM,previous)


def check_block_identity(previous,current):
    if previous is not None and any(previous[k]!=current[k] for k in ('initial_core_sha256','initial_head_sha256')):
        raise ValueError('fresh block initial model/head differs')
    if previous is not None and previous['process_id']==current['process_id']:
        raise ValueError('independent compiler process required')


def counter_snapshot():
    try:
        from torch._dynamo.utils import counters,guard_failures
        return dict(available=True,counters={str(k):{str(n):int(v) for n,v in values.items()} for k,values in counters.items()},
                    guard_failures={str(code):list(map(str,values)) for code,values in guard_failures.items()})
    except (ImportError,AttributeError,TypeError,ValueError) as exc:
        return dict(available=False,reason=repr(exc))


def one_update(torch,base,compiled,opts,core,groups,expected,policy,quantum,mode,cycle,budget_start):
    guard(budget_start,1200)
    actual=denominators(groups)
    if actual!={int(h):v for h,v in expected['denominators'].items()}:raise ValueError('whole horizon masses changed')
    if pad.identity([[pad.record_value(r) for r in m] for m in groups])!=expected['ordered_records_sha256']:
        raise ValueError('original micro/order/real prefix changed')
    weights=core.coefficients(expected['absolute_update'],704) if mode=='mtp' else {}
    active=tuple(h for h,w in weights.items() if w)
    for opt in opts:opt.zero_grad(set_to_none=True)
    torch.cuda.synchronize();tick=time.perf_counter();observed={h:0 for h in (1,)+active};widths=[]
    for micro in groups:
        guard(budget_start,1200)
        width=1024 if policy=='fixed' else shapes.width([len(r.x) for r in micro],quantum);widths.append(width)
        x,y,seg=core.pad_records(micro,base._padding_pad_id,'cuda',fixed_width=width,batch_size=8)
        with torch.autocast('cuda',dtype=torch.bfloat16):
            hidden=compiled(x,return_hidden=True)
            sums,counts=core.components(base,hidden,y,seg,horizons=active)
            loss=core.normalized_loss(sums,actual,weights)
        if not bool(torch.isfinite(loss)):raise FloatingPointError('nonfinite compiled loss')
        loss.backward()
        for h in observed:observed[h]+=counts[h]
        del x,y,seg,hidden,sums,loss
    if any(observed[h]!=actual[h] for h in observed):raise ValueError('observed targets changed')
    grads=[p.grad for p in base.parameters() if p.grad is not None]
    if not grads or not all(bool(torch.isfinite(g).all()) for g in grads):raise FloatingPointError('invalid compiled gradient')
    norm=torch.nn.utils.clip_grad_norm_(base.parameters(),1.,error_if_nonfinite=True)
    for opt in opts:opt.step()
    torch.cuda.synchronize()
    return dict(absolute_update=expected['absolute_update'],cycle=cycle,policy=policy,seconds=time.perf_counter()-tick,
        update_timing_scope='PAD_FORWARD_HEAD_BACKWARD_FINITE_CLIP_STEP_SYNC;GROUP_CHECK_AND_ZERO_OUTSIDE',
        actual_x_tokens=expected['actual_x_tokens'],padded_slots=8*sum(widths),widths=widths,
        denominator=actual,observed_targets=observed,weights=weights,preclip_norm=float(norm),
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())


def child(mode,quantum,block):
    p=verify();name=phase_name(mode,quantum)
    if type(block) is not int or not 0<=block<4:raise ValueError('block0..3 required')
    out=BASE/name/('block_'+str(block));cache=CACHE/name/('block_'+str(block))
    if out.exists() or cache.exists():raise FileExistsError('fresh process block/cache required')
    if os.environ.get('TORCHINDUCTOR_CACHE_DIR')!=str(cache/'inductor') or os.environ.get('TRITON_CACHE_DIR')!=str(cache/'triton'):
        raise ValueError('fresh process compiler cache environment required')
    out.mkdir();cache.mkdir(parents=True);started=time.perf_counter();torch=base=compiled=opts=records=None
    weak_model=None;weak_parameters=[]
    result=dict(schema=p['schema'],status='RUNNING',mode=mode,quantum=quantum,block=block,
        policy=p['blocks'][block],updates=[],source_profile_sha256=pad.digest(BASE/'profile.json'),
        quality_claim=False,checkpoint_writes=0,returncode=9,process_id=os.getpid())
    try:
        from scripts import interactive_research_infer as manual
        point=manual.require_idle_gpu();reply=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
            capture_output=True,text=True,timeout=10,check=True)
        if not reply.stdout.strip().isdigit() or int(reply.stdout.strip())<p['minimum_free_mib']:
            raise MemoryError('compiled PAD requires8192MiB point free')
        if shutil.disk_usage(ROOT).free<p['minimum_disk_bytes']:raise OSError('compiled cache disk reserve')
        result['gpu_point']=dict(point,free_mib=int(reply.stdout.strip()))
        from scripts import diag_p101a_sft_mtp as engine,diag_p101a_clean_bilingual as clean
        from tinylm.train import mtp_sft as core
        tick=time.perf_counter();torch,base,cfg,tok,initial=engine.load_runtime('parent_'+mode)
        if cfg.n_layers!=14 or cfg.cla_group!=2 or cfg.tie_mlp or cfg.train_repeat!=1. or not cfg.grad_checkpoint:
            raise ValueError('same14/CLA2/R1/untied/checkpoint geometry required')
        result['initial_core_sha256']=initial;result['initial_head_sha256']={str(h):pad.identity(getattr(base,'mtp_up'+str(h)).detach().tolist()) for h in (2,3,4)} if mode=='mtp' else {}
        corpus=engine.corpus_report(ROOT/pad.CORPUS);records=clean.encoded(ROOT/pad.CORPUS,corpus,tok)
        selected=[]
        by_epoch={}
        for g in p['selected_groups']:by_epoch.setdefault(g['epoch'],set()).add(g['index'])
        for epoch,wanted in sorted(by_epoch.items()):
            for index,groups in enumerate(engine.batches(records['train'],epoch)):
                if index in wanted:selected.append((epoch*176+index,groups))
        selected.sort(key=lambda x:x[0])
        if [u for u,_ in selected]!=[g['absolute_update'] for g in p['selected_groups']]:raise ValueError('source group order changed')
        result['cpu_load_encode_seconds']=time.perf_counter()-tick
        pad_id=tok.token_to_id('<|pad|>')
        if pad_id is None:pad_id=tok.token_to_id('<pad>')
        if type(pad_id) is not int:raise ValueError('original PAD identity missing')
        base._padding_pad_id=pad_id;base.train();torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        torch.manual_seed(1337);base=base.cuda();torch.cuda.reset_peak_memory_stats()
        weak_model=weakref.ref(base);weak_parameters=[weakref.ref(v) for v in base.parameters()]
        tick=time.perf_counter();compiled=torch.compile(base,mode='default');opts=engine.optimizers(compiled)
        result['compiler_config']=dict(mode='default',dynamic='UNSPECIFIED_DEFAULT_NONE',
            suppress_errors=bool(torch._dynamo.config.suppress_errors),
            inductor_cache=os.environ['TORCHINDUCTOR_CACHE_DIR'],triton_cache=os.environ['TRITON_CACHE_DIR'])
        for group in opts[0].param_groups:group['lr']=5e-5
        for group in opts[1].param_groups:group['lr']=2e-4
        owned=[id(v) for opt in opts for group in opt.param_groups for v in group['params']]
        if len(set(owned))!=len(owned) or set(owned)!={id(v) for v in base.parameters() if v.requires_grad}:
            raise ValueError('unique complete original optimizer ownership required')
        result['compile_wrapper_optimizer_seconds']=time.perf_counter()-tick
        with (out/'updates.jsonl').open('x',encoding='utf-8') as journal:
            for cycle in ('cold','steady'):
                for (_,groups),expected in zip(selected,p['selected_groups']):
                    event=one_update(torch,base,compiled,opts,core,groups,expected,p['blocks'][block],quantum,mode,cycle,started)
                    journal.write(json.dumps(event,allow_nan=False)+chr(10));journal.flush();result['updates'].append(event)
                    print('[PAD_COMPILED_UPDATE] '+json.dumps(dict(block=block,mode=mode,quantum=quantum,cycle=cycle,
                        update=event['absolute_update'],seconds=event['seconds'])),flush=True)
                result['counters_after_'+cycle]=counter_snapshot()
        result['training_peak_allocated_bytes']=torch.cuda.max_memory_allocated();result['training_peak_reserved_bytes']=torch.cuda.max_memory_reserved()
        tick=time.perf_counter();validation=engine.evaluate(base,records['val'],pad_id);torch.cuda.synchronize()
        if any(v['ce'] is not None and not math.isfinite(v['ce']) for v in validation.values()):raise FloatingPointError('nonfinite fixed1024 DEV')
        result['postprocess_fixed1024_seconds']=time.perf_counter()-tick
        result['postprocess_targets']={h:v['targets'] for h,v in validation.items()}
        snapshot=result['counters_after_steady']
        result['compiled_graph_count']=(snapshot.get('counters',{}).get('stats',{}).get('unique_graphs')
                                        if snapshot.get('available') else None)
        result['status']='COMPILED_RESOURCE_BLOCK_COMPLETE_NOT_QUALITY';result['returncode']=0
    except BaseException as exc:
        result.update(status='COMPILED_RESOURCE_ERROR',error=repr(exc),traceback=traceback.format_exc(),returncode=9)
    if torch is not None and torch.cuda.is_initialized():
        result['phase_peak_allocated_bytes']=torch.cuda.max_memory_allocated();result['phase_peak_reserved_bytes']=torch.cuda.max_memory_reserved()
    try:
        if base is not None:base.clear_quant()
    except BaseException as exc:result.update(status='CACHE_CLEAR_ERROR',cleanup_error=repr(exc),returncode=9)
    base=compiled=opts=records=selected=group=None;gc.collect()
    if torch is not None and torch.cuda.is_initialized():
        try:
            torch._dynamo.reset();gc.collect()
            result['owned_model_alive_after_reset']=weak_model is not None and weak_model() is not None
            result['owned_parameters_alive_after_reset']=sum(r() is not None for r in weak_parameters)
            if result['owned_model_alive_after_reset'] or result['owned_parameters_alive_after_reset']:
                raise RuntimeError('owned compiled model/parameter references remain')
            from scripts.diag_p107_hybrid_mntp import close_owned_cuda
            close_owned_cuda(torch,result)
        except BaseException as exc:result.update(status='CUDA_CLEANUP_UNVERIFIED',cleanup_error=repr(exc),returncode=9)
    try:verify();result['sources_assets_unchanged']=True
    except BaseException as exc:result.update(status='FINAL_SOURCE_ERROR',error=repr(exc),returncode=9)
    result['cache_bytes']=sum(f.stat().st_size for f in cache.rglob('*') if f.is_file())
    result['whole_wall_seconds']=time.perf_counter()-started;pad.write_new(out/'report.json',result)
    print('[PAD_COMPILED_BLOCK_FINAL] '+json.dumps(dict(block=block,status=result['status'],seconds=result['whole_wall_seconds'])),flush=True)
    return result['returncode']


def run(mode,quantum):
    guard();p=verify();name=phase_name(mode,quantum);out=BASE/name
    if out.exists():raise FileExistsError('phase already attempted')
    out.mkdir();started=time.perf_counter();result=dict(schema=p['schema'],name=name,status='RUNNING',blocks=[],quality_claim=False,returncode=9)
    previous=None
    try:
      with termination_as_exception():
        for block in range(4):
            guard(started,p['max_phase_seconds'])
            seconds=min(p['max_child_seconds'],p['max_phase_seconds']-(time.perf_counter()-started))
            if seconds<120:raise TimeoutError('not enough child budget; later blocks NOT_RUN')
            cache=CACHE/name/('block_'+str(block));env=dict(os.environ,TORCHINDUCTOR_CACHE_DIR=str(cache/'inductor'),
                TRITON_CACHE_DIR=str(cache/'triton'),CUDA_CACHE_PATH=str(cache/'cuda'),
                OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',TOKENIZERS_PARALLELISM='false')
            cmd=[sys.executable,'-B','-X','utf8','-m','scripts.diag_p101a_compiled_padding','child',
                 '--arm',phase_name(mode,quantum),'--block',str(block)]
            print('[PAD_CHILD_START] '+json.dumps(dict(mode=mode,quantum=quantum,block=block,policy=p['blocks'][block])),flush=True)
            receipt=run_child(cmd,out/('block_'+str(block)+'_stdout.txt'),seconds,env)
            path=out/('block_'+str(block))/'report.json'
            if receipt['returncode']!=0 or not path.is_file():raise RuntimeError('owned compiled child incomplete: '+str(block))
            report=json.loads(path.read_text())
            if report['status']!='COMPILED_RESOURCE_BLOCK_COMPLETE_NOT_QUALITY' or len(report['updates'])!=14:
                raise ValueError('exact14 updates per independent block required')
            check_block_identity(previous,report);previous=report
            result['blocks'].append(dict(block=block,report=str(path.relative_to(ROOT)),sha256=pad.digest(path),process=receipt))
            print('[PAD_CHILD_COMPLETE] '+json.dumps(dict(block=block,seconds=receipt['seconds'])),flush=True)
        result.update(status='COMPILED_ABBA_RESOURCE_COMPLETE_NOT_QUALITY',returncode=0)
    except BaseException as exc:result.update(status='COMPILED_PHASE_ERROR',error=repr(exc),traceback=traceback.format_exc(),returncode=9)
    result['whole_wall_seconds']=time.perf_counter()-started;pad.write_new(out/'report.json',result)
    print('[PAD_COMPILED_PHASE_FINAL] '+json.dumps(dict(name=name,status=result['status'],blocks=len(result['blocks']))),flush=True)
    return result['returncode']


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('prepare','run','child'))
    p.add_argument('--arm',choices=tuple(ARMS),default='ntp_q128');p.add_argument('--block',type=int)
    a=p.parse_args()
    if a.phase=='prepare':prepare();return 0
    mode,quantum=unpack_arm(a.arm)
    if a.phase=='child':return child(mode,quantum,a.block)
    return run(mode,quantum)


if __name__=='__main__':raise SystemExit(main())
