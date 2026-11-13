"""Strict deterministic repeat of the immutable ACTD mechanics, zero updates."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
from types import FunctionType,SimpleNamespace
import unittest
from scripts import diag_p106b_actd_consumer as old

ROOT=old.d.ROOT;TAG='p106b_actd_determinism_v1_20261113';BASE=ROOT/'test_result/evidence'/TAG
SOURCES=('scripts/diag_p106b_actd_determinism.py','scripts/test_p106b_actd_determinism.py')


def compare_gradients(torch,reference,observed):
    result=old.compare_gradients(torch,reference,observed);details=[]
    for name,a in reference.items():
        b=observed[name];outside=int((~torch.isclose(a,b,atol=result['atol'],rtol=result['rtol'])).sum())
        if outside:details.append(dict(parameter=name,outside_tolerance=outside,maximum_absolute_difference=float((a-b).abs().max())))
    result['outside_parameters']=sorted(details,key=lambda r:(-r['outside_tolerance'],r['parameter']))
    result['repeat_exact']=all(torch.equal(reference[n],observed[n])for n in reference)
    return result


def build_runner(destination=BASE):
    proxy=SimpleNamespace(**{k:v for k,v in vars(old.d).items()if not k.startswith('__')})
    proxy.BASE=Path(destination);proxy.TAG=TAG
    return FunctionType(old.run.__code__,dict(old.run.__globals__,d=proxy,compare_gradients=compare_gradients),
        old.run.__name__,old.run.__defaults__)


def prepare():
    old.d.guard(__import__('time').perf_counter(),1800)
    if BASE.exists():raise FileExistsError('fresh deterministic namespace required')
    p,*_=old.read_cache();source=old.d.BASE/'student/report.json';r=json.loads(source.read_text())
    witness=json.loads((old.d.BASE/'ROOT_STUDENT_EXIT_v1.json').read_text())
    if (r['status']!='ACTD_ACTUAL_HEAD_GRADIENT_COST_COMPLETE' or r['returncode']!=0
            or witness['actual_tool_exit']!=0 or witness['report_sha256']!=old.d.inventory.digest(source)
            or r['final_cuda_cleanup']['allocated_bytes'] or r['final_cuda_cleanup']['reserved_bytes']):
        raise ValueError('original complete measurement and preserved repeat-gradient negative required')
    repeats=[b['repeat_gradient_comparison']for b in r['blocks']if 'repeat_gradient_comparison'in b]
    if len(repeats)!=2 or not all(x['outside_tolerance']>0 for x in repeats):raise ValueError('both original repeat negatives required')
    from scripts.test_p106b_actd_determinism import DeterminismContracts
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(DeterminismContracts)
    test_result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not test_result.wasSuccessful() or test_result.testsRun!=3:raise RuntimeError('determinism CPU3 not complete')
    refs=[old.d.BASE/'profile.json',old.d.BASE/'teacher/report.json',source,old.d.BASE/'ROOT_STUDENT_EXIT_v1.json']
    refs.extend(ROOT/s for s in SOURCES)
    BASE.mkdir()
    old.d.write_new(BASE/'profile.json',dict(tag=TAG,authority_directive=115,deadline=old.d.DEADLINE.isoformat(),
        sources={str(x.relative_to(ROOT)):old.d.inventory.digest(x)for x in refs},
        old_function_code_reused=True,old_read_cache_reused=True,original_profile_sha256=old.d.inventory.digest(old.d.BASE/'profile.json'),
        primary_changed_variable='PROCESS_DETERMINISTIC_ALGORITHMS_TRUE_WARN_ONLY_FALSE_CUBLAS_4096_8',
        teacher_calls=0,optimizer_updates=0,checkpoint_writes=0,cpu_contracts=3,baseline_repeat_comparisons=repeats,
        original_ce_denominator=772,original_actd_denominator=607,quality_claim=False))
    print('[ACTD_DETERMINISM_PREPARED] '+TAG,flush=True)


def verify():
    old.d.verify();p=json.loads((BASE/'profile.json').read_text())
    if p['authority_directive']!=115 or p['deadline']!=old.d.DEADLINE.isoformat():raise ValueError('authority changed')
    for name,sha in p['sources'].items():
        if old.d.inventory.digest(ROOT/name)!=sha:raise ValueError('sealed deterministic input changed: '+name)
    return p


def run():
    verify()
    if os.environ.get('CUBLAS_WORKSPACE_CONFIG')!=':4096:8':raise ValueError('fresh process cuBLAS deterministic workspace required')
    import torch
    if torch.cuda.is_initialized():raise RuntimeError('set deterministic policy before first CUDA initialization')
    torch.use_deterministic_algorithms(True,warn_only=False)
    torch.backends.cudnn.deterministic=True
    if not torch.are_deterministic_algorithms_enabled() or torch.is_deterministic_algorithms_warn_only_enabled():
        raise RuntimeError('strict deterministic dispatch not enabled')
    try:build_runner()()
    finally:
        report_path=BASE/'student/report.json'
        if report_path.exists():
            r=json.loads(report_path.read_text());repeats=[b['repeat_gradient_comparison']for b in r['blocks']if 'repeat_gradient_comparison'in b]
            old.d.write_new(BASE/'determinism_recount.json',dict(source_report_sha256=old.d.inventory.digest(report_path),
                deterministic_algorithms=True,warn_only=False,cublas_workspace_config=os.environ['CUBLAS_WORKSPACE_CONFIG'],
                completed_repeat_pairs=len(repeats),all_repeat_exact=len(repeats)==2 and all(x['repeat_exact']for x in repeats),
                all_repeat_within_original_tolerance=len(repeats)==2 and all(x['outside_tolerance']==0 for x in repeats),
                quality_claim=False,training=False,optimizer_updates=0,checkpoint_writes=0))
        verify()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','actual']);args=parser.parse_args()
    (prepare if args.phase=='prepare'else run)()


if __name__=='__main__':main()
