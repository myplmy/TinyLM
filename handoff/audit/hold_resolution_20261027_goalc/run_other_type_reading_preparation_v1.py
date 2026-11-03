"""Run the complete page/input/index preparation and retain real exit codes."""
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

native=inv.cache.read(AUDIT/'REMAINING_OTHER_TYPES_NATIVE_PROCESS_EXIT_V1.json')
assert native['process_exit_code']==0
proof=inv.cache.read(inv.BASE/'remaining_other_types_native_proofs_v1/complete.json')
assert proof['counts']['fresh_regeneration_and_proof_match']==50162
out=AUDIT/'OTHER_TYPE_READING_PREPARATION_PROCESS_EXIT_V1.json'
start=AUDIT/'OTHER_TYPE_READING_PREPARATION_PROCESS_STARTED_V1.json'
log=AUDIT/'other_type_reading_preparation_v1.log'
assert not out.exists() and not start.exists() and not log.exists()
commands=[
    [sys.executable,'-I','-B',str(AUDIT/'prepare_remaining_other_types_readers_v1.py')],
    [sys.executable,'-I','-B',str(AUDIT/'prepare_remaining_other_types_identity_and_controls_v1.py')],
    [sys.executable,'-I','-B',str(AUDIT/'prepare_complete_phase_task_index_v1.py'),'--phase','other'],
]
inv.write_json(start,dict(status='ACTUAL_OTHER_TYPE_READING_PREPARATION_START_NOT_COMPLETION',
    utc=datetime.now(timezone.utc).isoformat(),commands=commands,goal_complete=False,training_authorized=False))
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
         MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
results=[]
begin=time.monotonic()
with log.open('xb') as stream:
    for argv in commands:
        current=time.monotonic()
        process=subprocess.run(argv,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
        results.append(dict(argv=argv,process_exit_code=process.returncode,seconds=time.monotonic()-current))
        if process.returncode:break
code=next((result['process_exit_code'] for result in results if result['process_exit_code']),0)
inv.write_json(out,dict(status='ACTUAL_OTHER_TYPE_READING_PREPARATION_EXIT_NOT_CONTENT_ADMISSION',
    process_exit_code=code,results=results,not_run=commands[len(results):],seconds=time.monotonic()-begin,
    log=dict(path=str(log.relative_to(ROOT)),sha256=inv.file_sha(log)),
    goal_complete=False,training_authorized=False))
print('other-type reading preparation exit',code,'steps',len(results))
raise SystemExit(code)
