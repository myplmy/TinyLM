"""A bounded CPU mathematical counterexample search, not model or DWA quality."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

from scripts import diag_p106b_actd_topk as data

ROOT=data.ROOT
BASE=ROOT/'test_result/evidence/p106b_dwa_band_symmetry_v1_20261113'
SOURCES=('scripts/diag_p106b_dwa_band_symmetry.py','scripts/p106b_dwa_reference.py')


def main():
    data.guard()
    if BASE.exists():raise FileExistsError('fresh symmetry diagnostic namespace required')
    profile=dict(authority_directive=115,seeds=[13,137,1337,10007],student_length=8,teacher_length=12,
        features=6,gamma=.1,alpha=.7,base=5.,entropy_scale=2.,penalty=1.,atol=1e-10,
        attention_score_scale=10.,self_band_policy='UNBANDED_EXPLICIT_VARIANT',
        sources={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest().upper()for name in SOURCES},
        torch_version=importlib.metadata.version('torch'),model_loads=0,gpu_calls=0,optimizer_updates=0,
        checkpoint_writes=0,quality_claim=False)
    data.write_new(BASE/'profile.json',profile)
    start=time.perf_counter()
    import torch
    from torch.nn import functional as F
    from scripts.p106b_dwa_reference import soft_dtw,adaptive_band_cost
    torch.set_num_threads(2)
    if torch.cuda.is_initialized():raise ValueError('CPU-only diagnostic requires uninitialized CUDA')
    rows=[]
    for seed in profile['seeds']:
        data.guard(start,60);torch.manual_seed(seed)
        x=torch.randn(8,6,dtype=torch.float64,requires_grad=True)
        y=torch.randn(12,6,dtype=torch.float64,requires_grad=True)
        scores=torch.randn(8,12,dtype=torch.float64)*profile['attention_score_scale']
        a=scores.softmax(-1);reverse=scores.T.softmax(-1)
        xn=F.normalize(x,dim=-1);yn=F.normalize(y,dim=-1)
        cost=1-xn@yn.T;sx=soft_dtw(1-xn@xn.T,gamma=.1);sy=soft_dtw(1-yn@yn.T,gamma=.1)
        bias=.5*(sx+sy)
        free=soft_dtw(cost,gamma=.1)-bias;free_reverse=soft_dtw(cost.T,gamma=.1)-bias
        kwargs={key:profile[key]for key in ('alpha','base','entropy_scale','penalty')}
        ab=adaptive_band_cost(cost,a,**kwargs);ba=adaptive_band_cost(cost.T,reverse,**kwargs)
        band=soft_dtw(ab,gamma=.1)-bias;band_reverse=soft_dtw(ba,gamma=.1)-bias
        gx,gy=torch.autograd.grad(band,(x,y))
        self_distance=soft_dtw(1-xn@xn.T,gamma=.1)-sx
        row=dict(seed=seed,unbanded=float(free.detach()),unbanded_reverse=float(free_reverse.detach()),
            unbanded_swap_abs=float((free-free_reverse).detach().abs()),self_distance_abs=float(self_distance.detach().abs()),
            banded=float(band.detach()),banded_reverse=float(band_reverse.detach()),
            banded_swap_abs=float((band-band_reverse).detach().abs()),
            band_penalty_transpose_max_abs=float(((ab-cost)-(ba-cost.T).T).detach().abs().max()),
            finite_gradients=bool(torch.isfinite(gx).all()and torch.isfinite(gy).all()),
            student_gradient_norm=float(gx.norm()),teacher_feature_gradient_norm=float(gy.norm()))
        if row['unbanded_swap_abs']>profile['atol']or row['self_distance_abs']>profile['atol']or not row['finite_gradients']:
            raise ValueError('original unbanded/finite reference invariant failed')
        rows.append(row)
    if torch.cuda.is_initialized():raise ValueError('unexpected CUDA initialization')
    if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest().upper()!=sha for name,sha in profile['sources'].items()):
        raise ValueError('sealed source changed')
    observed=any(row['banded_swap_abs']>profile['atol']for row in rows)
    report=dict(status='DIRECTIONAL_BAND_COUNTEREXAMPLE_OBSERVED'if observed else'NO_COUNTEREXAMPLE_IN_FIXED_FIXTURES',
        returncode=0,rows=rows,seconds=time.perf_counter()-start,sources_unchanged=True,cuda_initialized=False,
        model_loads=0,optimizer_updates=0,checkpoint_writes=0,quality_claim=False,
        interpretation='Only the explicit unbanded-self/directional-cross variant is tested. Full DWA, native CMA and teacher/student quality are not evaluated.')
    data.write_new(BASE/'report.json',report)
    print('[DWA_BAND_CPU] '+json.dumps(dict(status=report['status'],seconds=report['seconds'],
        max_unbanded_swap_abs=max(row['unbanded_swap_abs']for row in rows),
        banded_swap_abs=[row['banded_swap_abs']for row in rows],model_loads=0,gpu_calls=0)),flush=True)


if __name__=='__main__':main()
