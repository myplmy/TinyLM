"""Independent row-major scalar DP loss readback; no GPU rerun or model."""
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import time
from scripts import diag_p106b_actd_topk as data

ROOT=data.ROOT
SOURCE=ROOT/'test_result/evidence/p106b_softdtw_gpu_v2_20261113'
BASE=ROOT/'test_result/evidence/p106b_softdtw_large_cpu_v1_20261113'


def scalar_row_dp(cost,gamma):
    n,m=cost.shape
    previous=[float('inf')]*(m+1);previous[0]=0.
    for row in cost.tolist():
        current=[float('inf')]*(m+1)
        for j,value in enumerate(row,1):
            a,b,c=previous[j],current[j-1],previous[j-1];low=min(a,b,c)
            current[j]=value+low-gamma*math.log(math.exp((low-a)/gamma)+math.exp((low-b)/gamma)+math.exp((low-c)/gamma))
        previous=current
    return previous[m]


def main():
    data.guard()
    if BASE.exists():raise FileExistsError('fresh independent readback namespace required')
    original=json.loads((SOURCE/'report.json').read_text());profile=json.loads((SOURCE/'profile.json').read_text())
    witness=json.loads((SOURCE/'ROOT_ACTUAL_EXIT_v2.json').read_text())
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
    if (witness['actual_tool_exit']!=0 or witness['report_sha256']!=sha(SOURCE/'report.json')
            or witness['profile_sha256']!=sha(SOURCE/'profile.json')or original['returncode']!=0
            or importlib.metadata.version('torch')!=profile['packages']['torch']):
        raise ValueError('closed original GPU report, profile and same Torch required')
    sources={str(p.relative_to(ROOT)):sha(p)for p in [Path(__file__).resolve(),SOURCE/'profile.json',
        SOURCE/'report.json',SOURCE/'ROOT_ACTUAL_EXIT_v2.json',ROOT/'scripts/p106b_dwa_reference.py']}
    BASE.mkdir(parents=True)
    data.write_new(BASE/'profile.json',dict(authority_directive=115,sources=sources,original_seed=profile['seed'],
        original_atol=profile['atol'],original_rtol=profile['rtol'],small_shapes=profile['small_shapes'],large_shapes=profile['large_shapes'],
        new_random_inputs=0,gpu_reexecutions=0,large_gradient_comparison='NOT_RUN',model_loads=0,quality_claim=False))
    start=time.perf_counter();report=dict(status='RUNNING',returncode=9,small=[],large=[],gpu_calls=0,
        model_loads=0,optimizer_updates=0,checkpoint_writes=0,large_gradient_comparison='NOT_RUN',quality_claim=False);failure=None
    try:
        import torch
        from scripts.p106b_dwa_reference import soft_dtw
        torch.set_num_threads(2);torch.manual_seed(profile['seed'])
        if torch.cuda.is_initialized():raise ValueError('CPU-only readback required')
        for group in ['small','large']:
            if len(profile[group+'_shapes'])!=len(original[group]):raise ValueError('shape count changed')
            for shape,saved in zip(profile[group+'_shapes'],original[group]):
                data.guard(start,120)
                if shape!=saved['shape']:raise ValueError('original RNG draw order changed')
                cost=torch.rand(*shape,dtype=torch.float64)*2
                tick=time.perf_counter();value=scalar_row_dp(cost,profile['gamma']);seconds=time.perf_counter()-tick
                row=dict(shape=shape,cpu_row_major_loss=value,original_gpu_loss=saved['value'],
                    loss_abs_difference=abs(value-saved['value']),cpu_reference_seconds=seconds,
                    original_tolerance_close=math.isclose(value,saved['value'],abs_tol=profile['atol'],rel_tol=profile['rtol']))
                if group=='small':
                    ref=float(soft_dtw(cost,gamma=profile['gamma']));row['torch_scalar_reference_difference']=abs(value-ref)
                    if not math.isclose(value,ref,abs_tol=profile['atol'],rel_tol=profile['rtol']):
                        raise ValueError('independent row DP differs from original small CPU reference')
                report[group].append(row)
                if not row['original_tolerance_close']:raise ValueError('original GPU loss differs under original tolerance')
        if any(sha(ROOT/name)!=digest for name,digest in sources.items()):raise ValueError('source drift')
        if torch.cuda.is_initialized():raise ValueError('unexpected CUDA initialized')
        report.update(status='INDEPENDENT_LARGE_FORWARD_LOSS_VERIFIED_GRADIENT_NOT_RUN',returncode=0,
            sources_unchanged=True,cuda_initialized=False)
    except BaseException as exc:
        report.update(status='ERROR',error=repr(exc));failure=exc
    finally:
        report['seconds']=time.perf_counter()-start;data.write_new(BASE/'report.json',report)
    if failure:raise failure
    print('[SOFTDTW_LARGE_CPU] '+json.dumps(dict(status=report['status'],seconds=report['seconds'],
        large=report['large'],large_gradient_comparison='NOT_RUN',gpu_calls=0)),flush=True)


if __name__=='__main__':main()
