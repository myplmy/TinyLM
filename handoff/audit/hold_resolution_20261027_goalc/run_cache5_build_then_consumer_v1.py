"""Start the consumer immediately after a real successful CPU build exit."""
from pathlib import Path
from datetime import datetime,timezone
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
out=AUDIT/'CACHE5_BUILD_AND_CONSUMER_CHAIN_V1.json'
assert not out.exists()
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
rows=[]
for phase,script in [('build','run_guarded_partial_cache_v5.py'),('consumer','run_guarded_partial_cache_v5_consumer_v1.py')]:
    log=AUDIT/('cache5_'+phase+'_runner_stdout_v1.log');assert not log.exists()
    print(json.dumps(dict(phase=phase,status='ACTUAL_SUBPROCESS_START',utc=datetime.now(timezone.utc).isoformat())),flush=True)
    with log.open('xb') as stream:
        result=subprocess.run([sys.executable,'-I','-B',str(AUDIT/script)],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    rows.append(dict(phase=phase,process_exit_code=result.returncode,runner_log=str(log.relative_to(ROOT))))
    print(json.dumps(rows[-1]),flush=True)
    if result.returncode:break
value=dict(status='ACTUAL_BUILD_AND_CONSUMER_EXIT_ZERO' if len(rows)==2 and all(r['process_exit_code']==0 for r in rows)
    else 'FAILED_PHASE_PRESERVED_NO_OVERWRITE',phases=rows,
    consumer_start_requires_actual_build_exit_zero=True,CPU_threads=1,CUDA_visible_devices='',
    goal_complete=False,training_authorized=False)
with out.open('x',encoding='utf-8') as stream:
    json.dump(value,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
raise SystemExit(0 if value['status']=='ACTUAL_BUILD_AND_CONSUMER_EXIT_ZERO' else 1)
