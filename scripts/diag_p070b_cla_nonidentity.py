#!/usr/bin/env python3
"""Separate seed0 CPU coverage; the prior identity-shuffle record is immutable."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from datetime import datetime,timezone
import json
import time
import unittest
from unittest.mock import patch
TAG='p070b_cla_route_nonidentity_v2_s1337'
OUTPUT=ROOT/'test_result/evidence'/TAG
PRIOR=ROOT/'test_result/evidence/p070b_cla_route_contract_v1_s1337/report.json'


def run():
    import torch
    from scripts import test_p070b_cla_nonidentity as tests
    from scripts import diag_p101a_sft_mtp as io
    if datetime.now(timezone.utc)>=datetime(2026,10,16,8,0,tzinfo=timezone.utc):raise TimeoutError('current authority expired')
    if OUTPUT.exists():raise FileExistsError('old nonidentity evidence preserved')
    prior=json.loads(PRIOR.read_text())
    if prior['status']!='CPU_TOY_CONTRACT_PASS':raise ValueError('prior CPU contract required')
    for path,identity in prior['code_sha256'].items():
        if io.data.digest(ROOT/path)!=identity:raise ValueError('prior frozen implementation changed')
    started=time.perf_counter()
    with patch.object(torch.nn.Module,'cuda',side_effect=AssertionError('CPU only')),patch.object(torch.Tensor,'cuda',side_effect=AssertionError('CPU only')):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    report=dict(schema='P070B_CLA_NONIDENTITY_CPU_V2',tag=TAG,
        status='NONIDENTITY_CPU_TOY_PASS' if result.wasSuccessful() else 'IMPLEMENTATION_FAIL',tests=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),observations=tests.OBSERVATIONS,
        prior_report=str(PRIOR.relative_to(ROOT)),prior_report_sha256=io.data.digest(PRIOR),prior_code_unchanged=True,
        code_sha256={p:io.data.digest(ROOT/p) for p in ('scripts/test_p070b_cla_nonidentity.py','scripts/diag_p070b_cla_nonidentity.py')},
        atol=tests.prior.ATOL,rtol=tests.prior.RTOL,cuda_initialized=torch.cuda.is_initialized(),
        real_checkpoints_loaded=0,optimizer_updates=0,new_checkpoints=0,actual_language_quality='NOT_RUN',
        dynamic_route_training='NOT_RUN',learned_router='NOT_IMPLEMENTED',whole_sec=time.perf_counter()-started,
        scope='nonidentity frozen toy route cache/gradient/causality; not learned random-order architecture quality')
    if report['cuda_initialized']:raise ValueError('CPU-only contract initialized CUDA')
    io.write(OUTPUT/'report.json',report);print('[CLA_NONIDENTITY_CPU] '+json.dumps(report),flush=True)
    return 0 if result.wasSuccessful() else 9


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit CPU execution required')
    try:return run()
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[CLA_NONIDENTITY_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
