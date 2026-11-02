"""Run the full independent consumer once, after the observed build exit zero."""
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
out=BASE/'cache_reviewed_partial_v2'
build=json.loads((AUDIT/'CACHE_REVIEWED_PARTIAL_V2_PROCESS_EXIT_V1.json').read_text(encoding='utf-8'))
assert build['process_exit_code']==0 and build['observation_method']=='ACTUAL_SUBPROCESS_WAIT_RETURN_CODE'
assert build['built_receipt']['sha256']==hashlib.sha256((out/'built.json').read_bytes()).hexdigest().upper()
log=AUDIT/'cache_reviewed_partial_v2_verify_v1.log'
receipt=AUDIT/'CACHE_REVIEWED_PARTIAL_V2_VERIFY_EXIT_V1.json'
started_path=AUDIT/'CACHE_REVIEWED_PARTIAL_V2_VERIFY_STARTED_V1.json'
assert not log.exists() and not receipt.exists() and not started_path.exists()
assert not any((out/name).exists() for name in
               ['verified.json','recovery_verified.json','partial_resolution_verified.json','restricted_metadata_verified.json'])
command=[sys.executable,'-I','-B',str(AUDIT/'guarded_reviewed_cache_v2.py'),'verify',
    '--roster',str(BASE/'roster_reviewed_partial_v2/complete.json'),
    '--selection',str(AUDIT/'ROOT_AUTHORED_SELECTIONS_V10.json'),'--output-name','cache_reviewed_partial_v2']
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
         MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
with started_path.open('x',encoding='utf-8') as stream:
    json.dump(dict(status='ACTUAL_FULL_INDEPENDENT_CONSUMER_STARTED_NOT_VERIFIED',argv=command,
        utc=datetime.now(timezone.utc).isoformat(),goal_complete=False,training_authorized=False),
        stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
begin=time.monotonic()
with log.open('xb') as stream:
    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    for line in process.stdout:
        stream.write(line)
        stream.flush()
        print(line.decode('utf-8',errors='replace').rstrip(),flush=True)
    code=process.wait()
proofs={}
for name in ['verified.json','recovery_verified.json','partial_resolution_verified.json','restricted_metadata_verified.json']:
    path=out/name
    if path.exists():
        proofs[name]=dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper())
value=dict(status='ACTUAL_FULL_CONSUMER_EXIT_ZERO_PARTIAL_GOAL_INCOMPLETE' if code==0 else
    'ACTUAL_CONSUMER_FAILED_PRESERVE_EVIDENCE_NO_OVERWRITE',process_exit_code=code,
    observation_method='ACTUAL_SUBPROCESS_WAIT_RETURN_CODE',seconds=time.monotonic()-begin,
    argv=command,proofs=proofs,log=dict(path=str(log.relative_to(ROOT)),
    sha256=hashlib.sha256(log.read_bytes()).hexdigest().upper()),goal_complete=False,training_authorized=False)
with receipt.open('x',encoding='utf-8') as stream:
    json.dump(value,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=value['status'],process_exit_code=code,proofs=list(proofs),seconds=value['seconds'])),flush=True)
raise SystemExit(code)
