"""Capture the actual CPU build exit separately from cache verification."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
out=BASE/'cache_reviewed_partial_v3'
receipt=AUDIT/'CACHE_REVIEWED_PARTIAL_V3_PROCESS_EXIT_V1.json'
started_path=AUDIT/'CACHE_REVIEWED_PARTIAL_V3_PROCESS_STARTED_V1.json'
log=AUDIT/'cache_reviewed_partial_v3_build_v1.log'
assert not out.exists() and not receipt.exists() and not started_path.exists() and not log.exists()
command=[sys.executable,'-I','-B',str(AUDIT/'guarded_reviewed_cache_v4.py'),'build',
    '--roster',str(BASE/'roster_reviewed_partial_v3/complete.json'),
    '--adoptions',str(BASE/'reviewed_partial_adoptions_v3.json'),
    '--selection',str(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json'),
    '--output-name','cache_reviewed_partial_v3','--proposal-name','guarded_partial_proposals_v3']
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
         MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
started=dict(status='ACTUAL_CPU_PARTIAL_CACHE_BUILD_STARTED_NOT_VERIFIED',argv=command,
    utc=datetime.now(timezone.utc).isoformat(),goal_complete=False,training_authorized=False)
with started_path.open('x',encoding='utf-8') as stream:
    json.dump(started,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
begin=time.monotonic()
with log.open('xb') as stream:
    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    for line in process.stdout:
        stream.write(line)
        stream.flush()
        print(line.decode('utf-8',errors='replace').rstrip(),flush=True)
    code=process.wait()
value=dict(status='ACTUAL_BUILD_EXIT_ZERO_REQUIRES_INDEPENDENT_VERIFY' if code==0 else 'ACTUAL_CACHE_BUILD_FAILED_PRESERVE_PARTIAL_OUTPUT',
    process_exit_code=code,observation_method='ACTUAL_SUBPROCESS_WAIT_RETURN_CODE',argv=command,
    seconds=time.monotonic()-begin,log=dict(path=str(log.relative_to(ROOT)),
        sha256=hashlib.sha256(log.read_bytes()).hexdigest().upper()),
    new_output_exists=out.exists(),independent_consumer_run=False,goal_complete=False,training_authorized=False)
if (out/'built.json').exists():
    value['built_receipt']=dict(path=str((out/'built.json').relative_to(ROOT)),
        sha256=hashlib.sha256((out/'built.json').read_bytes()).hexdigest().upper())
with receipt.open('x',encoding='utf-8') as stream:
    json.dump(value,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps({key:value[key] for key in ['status','process_exit_code','seconds','new_output_exists']}),flush=True)
raise SystemExit(code)
