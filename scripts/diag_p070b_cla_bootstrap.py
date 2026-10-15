#!/usr/bin/env python3
"""New CPU execution version after process-local helper import bootstrap only."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from datetime import datetime,timezone
import hashlib
import json
import subprocess
import time
import unittest
from unittest.mock import patch
TAG='p070b_cla_route_bootstrap_v3_s1337'
OUTPUT=ROOT/'test_result/evidence'/TAG
RECOVERY='eea62c03b1b384ce95c4f1ed666aab4dd3494e16'
BOOTSTRAP=b'from pathlib import Path\nimport sys\nROOT=Path(__file__).resolve().parents[1]\nsys.path.insert(0,str(ROOT))\n'


def run():
    import torch
    from scripts import test_p070b_cla_routes as first
    from scripts import test_p070b_cla_nonidentity as second
    from scripts import diag_p101a_sft_mtp as io
    if datetime.now(timezone.utc)>=datetime(2026,10,16,8,0,tzinfo=timezone.utc):raise TimeoutError('current authority expired')
    if OUTPUT.exists():raise FileExistsError('old bootstrap evidence preserved')
    helper='scripts/p070b_cla_routes.py';old=subprocess.check_output(['git','show',RECOVERY+':'+helper])
    current=(ROOT/helper).read_bytes()
    if current.count(BOOTSTRAP)!=1 or current.replace(BOOTSTRAP,b'',1)!=old:raise ValueError('only process-local bootstrap may differ from frozen helper')
    prior_paths=['test_result/evidence/p070b_cla_route_contract_v1_s1337/report.json','test_result/evidence/p070b_cla_route_nonidentity_v2_s1337/report.json']
    source_reports={}
    for p in prior_paths:
        source_reports[p]=io.data.digest(ROOT/p)
        if (ROOT/p).read_bytes()!=subprocess.check_output(['git','show',RECOVERY+':'+p]):raise ValueError('old reports changed')
    direct=subprocess.run([sys.executable,'-B','-X','utf8',helper],cwd=ROOT,capture_output=True,text=True,timeout=30)
    if direct.returncode:raise ValueError('helper direct execution import failed: '+direct.stderr[-1000:])
    started=time.perf_counter();suite=unittest.TestSuite()
    for module in (first,second):suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    with patch.object(torch.nn.Module,'cuda',side_effect=AssertionError('CPU-only')),patch.object(torch.Tensor,'cuda',side_effect=AssertionError('CPU-only')):
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(schema='P070B_CLA_BOOTSTRAP_CPU_V3',tag=TAG,status='BOOTSTRAP_CPU_PASS' if result.wasSuccessful() else 'IMPLEMENTATION_FAIL',
        unittest_cases=result.testsRun,errors=len(result.errors),failures=len(result.failures),direct_helper_import_returncode=direct.returncode,
        recovery_commit=RECOVERY,original_helper_sha256=hashlib.sha256(old).hexdigest().upper(),
        current_helper_sha256=io.data.digest(ROOT/helper),bootstrap_removed_body_exactly_matches_git=True,
        prior_reports_sha256=source_reports,old_uniform_observations=first.OBSERVATIONS,nonidentity_observations=second.OBSERVATIONS,
        code_sha256={p:io.data.digest(ROOT/p) for p in (helper,'scripts/test_p070b_cla_routes.py','scripts/test_p070b_cla_nonidentity.py','scripts/diag_p070b_cla_bootstrap.py','tinylm/config.py','tinylm/model/transformer.py')},
        cuda_initialized=torch.cuda.is_initialized(),real_checkpoints_loaded=0,optimizer_updates=0,new_checkpoints=0,
        world_quality='NOT_RUN',dynamic_route_training='NOT_RUN',whole_sec=time.perf_counter()-started,
        scope='new CPU numerical execution after helper process path repair; original observations preserved at recovery commit')
    if report['cuda_initialized']:raise ValueError('CPU-only initialized CUDA')
    io.write(OUTPUT/'report.json',report);print('[CLA_BOOTSTRAP_CPU] '+json.dumps(report),flush=True)
    return 0 if result.wasSuccessful() else 9


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit CPU execution required')
    try:return run()
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[CLA_BOOTSTRAP_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
