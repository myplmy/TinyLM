"""Wait for the exact actual build receipt, then run the independent CPU consumer."""
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
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
build_exit=AUDIT/'CACHE_REVIEWED_PARTIAL_V3_PROCESS_EXIT_V1.json'
waiting=AUDIT/'CACHE_REVIEWED_PARTIAL_V3_VERIFY_WAIT_STARTED_V1.json'
started=AUDIT/'CACHE_REVIEWED_PARTIAL_V3_VERIFY_STARTED_V1.json'
exit_path=AUDIT/'CACHE_REVIEWED_PARTIAL_V3_VERIFY_EXIT_V1.json'
log=AUDIT/'cache_reviewed_partial_v3_verify_v1.log'
for path in [waiting,started,exit_path,log]:assert not path.exists()
with waiting.open('x') as f:json.dump(dict(status='WAITING_FOR_ACTUAL_BUILD_EXIT_NOT_CONSUMER_STARTED',
    build_receipt=str(build_exit.relative_to(ROOT)),utc=datetime.now(timezone.utc).isoformat(),
    goal_complete=False,training_authorized=False),f,ensure_ascii=False,indent=2)
begin=time.monotonic()
while not build_exit.exists():
    if time.monotonic()-begin>10800:
        with exit_path.open('x') as f:json.dump(dict(status='CONSUMER_NOT_RUN_BUILD_RECEIPT_TIMEOUT',
            process_exit_code=None,prerequisite_verified=False,goal_complete=False,training_authorized=False),f,indent=2)
        raise SystemExit(2)
    time.sleep(10)
build=json.loads(build_exit.read_text())
if build['process_exit_code']!=0:
    with exit_path.open('x') as f:json.dump(dict(status='CONSUMER_NOT_RUN_BUILD_FAILED',process_exit_code=None,
        prerequisite=dict(path=str(build_exit.relative_to(ROOT)),sha256=digest(build_exit)),
        goal_complete=False,training_authorized=False),f,indent=2)
    raise SystemExit(2)
pin=build['built_receipt'];assert digest(ROOT/pin['path'])==pin['sha256']
command=[sys.executable,'-I','-B',str(AUDIT/'consume_guarded_partial_cache_v3_library_v1.py'),'verify',
    '--roster',str(BASE/'roster_reviewed_partial_v3/complete.json'),
    '--selection',str(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json'),'--output-name','cache_reviewed_partial_v3']
with started.open('x') as f:json.dump(dict(status='ACTUAL_INDEPENDENT_CONSUMER_STARTED_NOT_VERIFIED',
    argv=command,build_receipt=dict(path=str(build_exit.relative_to(ROOT)),sha256=digest(build_exit)),
    utc=datetime.now(timezone.utc).isoformat(),goal_complete=False,training_authorized=False),f,ensure_ascii=False,indent=2)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
begin=time.monotonic()
with log.open('xb') as stream:
    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    for line in process.stdout:
        stream.write(line);stream.flush();print(line.decode('utf-8',errors='replace').rstrip(),flush=True)
    code=process.wait()
proofs={}
for name in ['verified.json','recovery_verified.json','partial_resolution_verified.json',
        'restricted_metadata_verified.json','baseline_preservation_scope.json']:
    path=BASE/'cache_reviewed_partial_v3'/name
    if path.exists():proofs[name]=dict(path=str(path.relative_to(ROOT)),sha256=digest(path))
with exit_path.open('x') as f:json.dump(dict(
    status='ACTUAL_FULL_CONSUMER_EXIT_ZERO_PARTIAL_GOAL_INCOMPLETE' if code==0 else 'ACTUAL_CONSUMER_FAILED_PRESERVE_ALL_OUTPUT',
    process_exit_code=code,observation_method='ACTUAL_SUBPROCESS_WAIT_RETURN_CODE',argv=command,
    seconds=time.monotonic()-begin,proofs=proofs,log=dict(path=str(log.relative_to(ROOT)),sha256=digest(log)),
    goal_complete=False,training_authorized=False),f,ensure_ascii=False,indent=2)
print(json.dumps(dict(process_exit_code=code,seconds=time.monotonic()-begin,proofs=list(proofs))),flush=True)
raise SystemExit(code)
