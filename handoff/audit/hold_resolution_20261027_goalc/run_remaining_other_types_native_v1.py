"""Record the real CPU subprocess status, preserving failed/new outputs."""
from datetime import datetime,timezone
from pathlib import Path
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

stem='REMAINING_OTHER_TYPES_NATIVE_PROCESS_'
started_path=AUDIT/(stem+'STARTED_V1.json')
exit_path=AUDIT/(stem+'EXIT_V1.json')
log_path=AUDIT/'remaining_other_types_native_v1_execution_v1.log'
program=AUDIT/'verify_remaining_other_types_native_v1.py'
assert not started_path.exists() and not exit_path.exists() and not log_path.exists()
assert not (inv.BASE/'remaining_other_types_native_proofs_v1').exists()
argv=[sys.executable,'-I','-B',str(program)]
inv.write_json(started_path,dict(status='ACTUAL_CPU_PROCESS_ABOUT_TO_START_NOT_COMPLETION',
    utc=datetime.now(timezone.utc).isoformat(),argv=argv,expected_unique_sources=50162,
    program_sha256=inv.file_sha(program),goal_complete=False,training_authorized=False))
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
begin=time.monotonic()
with log_path.open('xb') as stream:
    result=subprocess.run(argv,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
receipt=dict(status='ACTUAL_OTHER_TYPE_NATIVE_EXIT_NOT_CONTENT_ADMISSION',
    process_exit_code=result.returncode,seconds=time.monotonic()-begin,argv=argv,
    observation_method='ACTUAL_SUBPROCESS_WAIT_RETURN_CODE',
    log=dict(path=str(log_path.relative_to(ROOT)),sha256=inv.file_sha(log_path)),
    goal_complete=False,training_authorized=False)
proof_path=inv.BASE/'remaining_other_types_native_proofs_v1/complete.json'
if proof_path.exists():receipt['output']=dict(path=str(proof_path.relative_to(ROOT)),sha256=inv.file_sha(proof_path))
inv.write_json(exit_path,receipt)
print(receipt['status'],'exit',result.returncode,'seconds',receipt['seconds'])
raise SystemExit(result.returncode)
