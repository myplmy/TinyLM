"""Capture only relevant CPU checks after new collector scope and WIP updates."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
out=AUDIT/'RESUME_JOIN_CPU_CHECKS_V1.json'
assert not out.exists()
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
         MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
commands=[
 ['scripts/test_wip.py'],
 ['scripts/wip.py','--capsule-check','--file','handoff/WIP_20261027_작업원장.md'],
 ['scripts/test_p106b_hold_resolution_author_output_bindings_v1.py'],
 ['scripts/test_p106b_hold_resolution_review_safeguards_v3.py'],
 ['handoff/audit/hold_resolution_20261027_goalc/test_typed_nominal_local_alias_v2.py'],
]
records=[]
for number,args in enumerate(commands,1):
    command=[sys.executable,'-I','-B',*args]
    started=time.monotonic()
    result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True)
    log=AUDIT/f'resume_join_cpu_check_v1_{number:02d}.log'
    with log.open('xb') as stream:
        stream.write(result.stdout)
        stream.write(result.stderr)
    records.append(dict(argv=command,exit_code=result.returncode,seconds=time.monotonic()-started,
        stdout_bytes=len(result.stdout),stderr_bytes=len(result.stderr),
        log=dict(path=str(log.relative_to(ROOT)),sha256=hashlib.sha256(log.read_bytes()).hexdigest().upper())))
    print(args[0],result.returncode,flush=True)
receipt=dict(status='CPU_SCOPE_CHECKS_COMPLETED_NOT_SEMANTIC_OR_CACHE_APPROVAL',records=records,
    all_exit_zero=all(row['exit_code']==0 for row in records),model_loads=0,gpu_calls=0,
    source_bodies_read=False,training_authorized=False,goal_complete=False)
with out.open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2)
    stream.write('\n')
assert receipt['all_exit_zero']
