"""Observe a real CPU-only full birth-type regeneration and preserve its exit."""
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
log=AUDIT/'remaining_birth_native_v1_execution_v1.log'
start=AUDIT/'REMAINING_BIRTH_NATIVE_STARTED_V1.json'
finish=AUDIT/'REMAINING_BIRTH_NATIVE_EXIT_V1.json'
assert not any(path.exists() for path in [log,start,finish])
assert not (BASE/'remaining_birth_native_proofs_v1').exists()
command=[sys.executable,'-I','-B',str(AUDIT/'verify_remaining_birth_native_v1.py')]
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
         MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
with start.open('x',encoding='utf-8') as stream:
    json.dump(dict(status='ACTUAL_CPU_FULL_BIRTH_TYPE_NATIVE_REGENERATION_STARTED',
        utc=datetime.now(timezone.utc).isoformat(),argv=command,goal_complete=False),stream,ensure_ascii=False,indent=2)
begin=time.monotonic()
with log.open('xb') as stream:
    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    for line in process.stdout:
        stream.write(line)
        stream.flush()
        print(line.decode('utf-8',errors='replace').rstrip(),flush=True)
    code=process.wait()
report=BASE/'remaining_birth_native_proofs_v1/complete.json'
value=dict(process_exit_code=code,observation_method='ACTUAL_SUBPROCESS_WAIT_RETURN_CODE',
    seconds=time.monotonic()-begin,argv=command,goal_complete=False,training_authorized=False)
if report.exists():
    proof=json.loads(report.read_text(encoding='utf-8'))
    value.update(completed_artifact=dict(path=str(report.relative_to(ROOT)),
        sha256=hashlib.sha256(report.read_bytes()).hexdigest().upper()),counts=proof['counts'])
value['log']=dict(path=str(log.relative_to(ROOT)),sha256=hashlib.sha256(log.read_bytes()).hexdigest().upper())
with finish.open('x',encoding='utf-8') as stream:
    json.dump(value,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps(value,ensure_ascii=False),flush=True)
raise SystemExit(code)
