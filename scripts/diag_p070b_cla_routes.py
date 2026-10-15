#!/usr/bin/env python3
"""CPU toy contracts for CLA-atomic routes, no real checkpoint or learning."""
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
TAG='p070b_cla_route_contract_v1_s1337'
OUTPUT=ROOT/'test_result/evidence'/TAG


def run():
    import torch
    from scripts import test_p070b_cla_routes as tests
    from scripts import diag_p101a_sft_mtp as io
    if datetime.now(timezone.utc)>=datetime(2026,10,16,8,0,tzinfo=timezone.utc):raise TimeoutError('current authority expired')
    if OUTPUT.exists():raise FileExistsError('old route evidence preserved')
    started=time.perf_counter()
    with patch.object(torch.nn.Module,'cuda',side_effect=AssertionError('CPU-only route contract')),patch.object(torch.Tensor,'cuda',side_effect=AssertionError('CPU-only route contract')):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    report=dict(schema='P070B_CLA_ATOMIC_ROUTE_CONTRACT_V1',tag=TAG,
        status='CPU_TOY_CONTRACT_PASS' if result.wasSuccessful() else 'IMPLEMENTATION_FAIL',
        tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),observations=tests.OBSERVATIONS,
        tolerances=dict(atol=tests.ATOL,rtol=tests.RTOL),actual_shape=dict(layers=10,dim=32,ffn=64,cla_group=2,tie_mlp=True),
        code_sha256={p:io.data.digest(ROOT/p) for p in ('scripts/p070b_cla_routes.py','scripts/test_p070b_cla_routes.py','scripts/diag_p070b_cla_routes.py','tinylm/config.py','tinylm/model/transformer.py')},
        cuda_initialized=torch.cuda.is_initialized(),optimizer_updates=0,real_checkpoints_loaded=0,new_checkpoints=0,
        actual_language_quality='NOT_RUN',dynamic_training='NOT_RUN',learned_router='NOT_IMPLEMENTED',
        serialized_real_checkpoint_loader='NOT_IMPLEMENTED',models_modified=0,whole_sec=time.perf_counter()-started,
        scope='tiny CPU functionality, not real architecture quality, stochastic route training or deployment')
    if report['cuda_initialized']:raise ValueError('CPU contract initialized CUDA')
    io.write(OUTPUT/'report.json',report)
    print('[CLA_ROUTE_CONTRACT] '+json.dumps(report),flush=True)
    return 0 if result.wasSuccessful() else 9


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit CPU execute required')
    try:return run()
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[CLA_ROUTE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
