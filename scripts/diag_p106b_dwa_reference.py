"""CPU math/reference cost only; no native model or full DWA-KD integration."""
import gc
import hashlib
import json
from pathlib import Path
import resource
import time
import unittest
from scripts import diag_p106b_actd_topk as data

ROOT=data.ROOT;BASE=ROOT/'test_result/evidence/p106b_dwa_reference_v1_20261113'


def main():
    data.guard();start=time.perf_counter()
    if BASE.exists():raise FileExistsError('fresh DWA ingredient namespace required')
    paths=[ROOT/'scripts'/name for name in ['p106b_dwa_reference.py','test_p106b_dwa_reference.py','diag_p106b_dwa_reference.py']]
    pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest().upper()for p in paths};BASE.mkdir(parents=True)
    data.write_new(BASE/'profile.json',dict(authority_directive=115,deadline=data.DEADLINE.isoformat(),sources=pins,
        source_paper='https://arxiv.org/html/2602.21669v1',token_weight_gradient_policy='EXPLICIT_DETACHED_VARIANT',
        normalized_dtw_scope='UNBANDED_REFERENCE_ONLY',band_attention_gradient='FROZEN_INDICATOR_POLICY',
        native_integration=False,full_dwa_implemented=False,max_cells_per_cost=4096,model_loads=0,gpu_calls=0,quality_claim=False))
    from scripts.test_p106b_dwa_reference import DwaIngredientContracts
    test=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(DwaIngredientContracts))
    if not test.wasSuccessful()or test.testsRun!=8:raise RuntimeError('DWA ingredient CPU8 incomplete')
    import torch
    from scripts.p106b_dwa_reference import unbanded_divergence
    torch.set_num_threads(1);torch.manual_seed(1337);rows=[]
    for n,m in [(8,12),(16,24),(32,48)]:
        x=torch.randn(n,16,dtype=torch.float64,requires_grad=True);y=torch.randn(m,16,dtype=torch.float64)
        tick=time.perf_counter();loss=unbanded_divergence(x,y,gamma=.1);forward=time.perf_counter()-tick;tick=time.perf_counter();loss.backward();backward=time.perf_counter()-tick
        if not bool(torch.isfinite(x.grad).all())or y.grad is not None:raise ValueError('finite student-only reference gradient required')
        rows.append(dict(student_length=n,teacher_length=m,cross_cells=n*m,self_cells=n*n+m*m,loss=float(loss.detach()),forward_seconds=forward,backward_seconds=backward,
            student_gradient_norm=float(x.grad.norm()),teacher_gradient=None));del x,y,loss;gc.collect()
    if torch.cuda.is_initialized():raise ValueError('CPU ingredients initialized CUDA')
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest().upper()!=sha for p,sha in pins.items()):raise ValueError('source changed during reference test')
    report=dict(status='DWA_INGREDIENT_CPU_REFERENCE_VERIFIED_FULL_METHOD_NOT_RUN',returncode=0,cpu_tests=8,reference_costs=rows,
        cuda_initialized=False,model_loads=0,gpu_calls=0,optimizer_updates=0,checkpoint_writes=0,quality_claim=False,
        native_integration=False,full_dwa_implemented=False,source_unchanged=True,seconds=time.perf_counter()-start,
        peak_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    data.write_new(BASE/'report.json',report);print('[DWA_REFERENCE_CPU] '+json.dumps(report),flush=True)


if __name__=='__main__':main()
