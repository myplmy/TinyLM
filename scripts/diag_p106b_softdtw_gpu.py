"""Bounded mathematical/cost GPU experiment; no model or full DWA claim."""
import argparse
import gc
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import statistics
import time
import traceback
import unittest
from scripts import diag_p106b_actd_topk as data

ROOT=data.ROOT;BASE=ROOT/'test_result/evidence/p106b_softdtw_gpu_v1_20261113'
SOURCES=('scripts/p106b_softdtw_triton.py','scripts/test_p106b_softdtw_triton.py','scripts/diag_p106b_softdtw_gpu.py','scripts/p106b_dwa_reference.py')


def prepare():
    data.guard()
    if BASE.exists():raise FileExistsError('fresh GPU DP namespace required')
    from scripts.test_p106b_softdtw_triton import SoftDtwInterfaceContracts
    tests=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(SoftDtwInterfaceContracts))
    if not tests.wasSuccessful()or tests.testsRun!=3:raise RuntimeError('CPU interface3 incomplete')
    BASE.mkdir(parents=True)
    data.write_new(BASE/'profile.json',dict(authority_directive=115,deadline=data.DEADLINE.isoformat(),
        sources={p:data.inventory.digest(ROOT/p)for p in SOURCES},packages={p:importlib.metadata.version(p)for p in ['torch','triton']},
        gamma=.1,atol=1e-9,rtol=1e-8,precision='FP64_LIBDEVICE',
        small_shapes=[[1,1],[1,17],[17,1],[8,12],[16,24],[32,48]],large_shapes=[[256,384],[512,768],[1024,1024]],
        max_cells=1048576,seed=1337,warm_repeats=5,model_loads=0,optimizer_updates=0,checkpoint_writes=0,quality_claim=False))
    print('[SOFTDTW_PREPARED] CPU3 '+str(BASE.relative_to(ROOT)),flush=True)


def verify():
    data.guard();p=data.inventory.q.read_json(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=data.DEADLINE.isoformat():raise ValueError('GPU DP authority changed')
    for name,sha in p['sources'].items():
        if data.inventory.digest(ROOT/name)!=sha:raise ValueError('GPU DP sealed source changed')
    if any(importlib.metadata.version(n)!=v for n,v in p['packages'].items()):raise ValueError('GPU DP package version changed')
    return p


def measured(torch,cost,p,report,start):
    from scripts.p106b_softdtw_triton import soft_dtw
    c=cost.cuda().requires_grad_(True);torch.cuda.synchronize();tick=time.perf_counter();out=soft_dtw(c,gamma=p['gamma']);out.backward();torch.cuda.synchronize()
    row=dict(shape=list(cost.shape),cold_compile_forward_backward_seconds=time.perf_counter()-tick,value=float(out.detach()),gradient=c.grad.detach().cpu().clone(),warm=[])
    torch.cuda.reset_peak_memory_stats()
    for _ in range(p['warm_repeats']):
        data.guard(start,1080);c.grad=None;beg=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
        torch.cuda.synchronize();tick=time.perf_counter();beg.record();out=soft_dtw(c,gamma=p['gamma']);out.backward();end.record();torch.cuda.synchronize()
        row['warm'].append(dict(wall_seconds=time.perf_counter()-tick,cuda_event_span_ms=beg.elapsed_time(end)))
        if not torch.equal(c.grad.detach().cpu(),row['gradient']):raise ValueError('identical GPU DP replay differs')
    row['warm_wall_median_seconds']=statistics.median(x['wall_seconds']for x in row['warm']);row['peak_allocated_bytes']=torch.cuda.max_memory_allocated();row['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
    return row


def work(torch,p,report,start):
    from scripts.p106b_dwa_reference import soft_dtw as reference
    torch.manual_seed(p['seed']);report['small']=[];report['large']=[]
    for shape in p['small_shapes']:
        data.guard(start,1080);c=torch.rand(*shape,dtype=torch.float64)*2;c.requires_grad_(True)
        tick=time.perf_counter();expected=reference(c,gamma=p['gamma']);expected.backward();cpu_seconds=time.perf_counter()-tick
        row=measured(torch,c.detach(),p,report,start);g=row.pop('gradient')
        row.update(reference_forward_backward_seconds=cpu_seconds,loss_abs_difference=abs(row['value']-float(expected.detach())),gradient_max_abs=float((g-c.grad).abs().max()),
            independent_loss_close=math.isclose(row['value'],float(expected.detach()),abs_tol=p['atol'],rel_tol=p['rtol']),
            independent_gradient_close=torch.allclose(g,c.grad,atol=p['atol'],rtol=p['rtol']))
        report['small'].append(row)
        if not row['independent_loss_close']or not row['independent_gradient_close']:raise ValueError('original FP64 CPU reference comparison failed')
        print('[SOFTDTW_SMALL] '+json.dumps(row),flush=True)
    for shape in p['large_shapes']:
        data.guard(start,1080);c=torch.rand(*shape,dtype=torch.float64)*2;row=measured(torch,c,p,report,start);g=row.pop('gradient')
        reverse=measured(torch,c.T.contiguous(),p,report,start);gt=reverse.pop('gradient')
        row.update(transpose_loss_abs_difference=abs(row['value']-reverse['value']),transpose_gradient_max_abs=float((g-gt.T).abs().max()),
            transpose_close=math.isclose(row['value'],reverse['value'],abs_tol=p['atol'],rel_tol=p['rtol'])and torch.allclose(g,gt.T,atol=p['atol'],rtol=p['rtol']),
            gradient_min=float(g.min()),gradient_max=float(g.max()),gradient_sum=float(g.sum()),
            endpoint_gradients=[float(g[0,0]),float(g[-1,-1])],independent_large_cpu_reference='NOT_RUN',reverse_timing=reverse)
        n,m=shape;path_ok=(-p['atol']<=row['gradient_min']and row['gradient_max']<=1+p['rtol']
            and max(n,m)-p['rtol']<=row['gradient_sum']<=n+m-1+p['rtol']
            and all(abs(v-1)<=p['rtol']for v in row['endpoint_gradients']))
        row['path_constraints']=path_ok;report['large'].append(row)
        if not row['transpose_close']or not path_ok:raise ValueError('large DP metamorphic/path constraint failed')
        print('[SOFTDTW_LARGE] '+json.dumps(row),flush=True)


def actual():
    p=verify();start=time.perf_counter()
    if (BASE/'report.json').exists():raise FileExistsError('GPU DP already attempted')
    report=dict(status='RUNNING',returncode=9,profile_sha256=data.inventory.digest(BASE/'profile.json'),model_loads=0,training=False,optimizer_updates=0,checkpoint_writes=0,quality_claim=False,
        isolated_compile_cache=os.environ.get('TRITON_CACHE_DIR'));failure=None
    import torch
    try:
        from scripts.interactive_research_infer import require_idle_gpu
        report['entry_gpu_point']=require_idle_gpu()
        expected=str(ROOT/'data_cache'/BASE.name/'triton')
        if os.environ.get('TRITON_CACHE_DIR')!=expected:raise ValueError('owned isolated Triton cache required')
        torch.set_num_threads(2);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        work(torch,p,report,start);report.update(status='GPU_SOFTDTW_COMPONENT_VERIFIED_NATIVE_DWA_NOT_RUN',returncode=0)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        gc.collect()
        if torch.cuda.is_initialized():
            try:
                from scripts.diag_p107_hybrid_mntp import close_owned_cuda
                close_owned_cuda(torch,report)
            except BaseException as exc:report.update(status='ERROR',returncode=9,cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:verify();report['sources_unchanged']=True
        except BaseException as exc:report.update(status='ERROR',returncode=9,source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        report['seconds']=time.perf_counter()-start;data.write_new(BASE/'report.json',report)
    if failure:raise failure
    print('[SOFTDTW_GPU_FINAL] '+json.dumps({k:report[k]for k in ['status','seconds','returncode']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','actual']);a=parser.parse_args();(prepare if a.phase=='prepare'else actual)()
