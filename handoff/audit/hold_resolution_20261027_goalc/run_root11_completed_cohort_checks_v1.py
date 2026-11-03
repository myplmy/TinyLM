"""Run independent CPU diagnostics, then the source-specific numerical closure."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
selection=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json'
tasks=[('numeric','audit_root11_numeric_context_v2.py','ROOT11_NUMERIC_CONTEXT_DIAGNOSTICS_V2.json',[]),
    ('quantities','audit_root11_stated_quantities_v2.py','ROOT11_STATED_QUANTITY_DIAGNOSTICS_V2.json',[]),
    ('qualified_dates','audit_root11_qualified_dates_v2.py','ROOT11_QUALIFIED_DATE_DIAGNOSTICS_V2.json',[]),
    ('runtime_guards','audit_exact_selection_runtime_guards_v7.py','EXACT_SELECTION_RUNTIME_GUARDS_V10.json',
        ['--selection',str(selection),'--output',str(AUDIT/'EXACT_SELECTION_RUNTIME_GUARDS_V10.json')])]
jobs=[]
for name,script,artifact,args in tasks:
    log=AUDIT/('ROOT11_COMPLETED_COHORT_'+name.upper()+'_V1.log')
    stream=log.open('xb')
    command=[sys.executable,'-I','-B',str(AUDIT/script),*args]
    started=time.monotonic()
    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    jobs.append((name,artifact,log,stream,command,started,process))
rows=[]
for name,artifact,log,stream,command,started,process in jobs:
    code=process.wait();stream.close()
    row=dict(name=name,command=command,process_exit_code=code,seconds=time.monotonic()-started,
        log=dict(path=str(log.relative_to(ROOT)),sha256=inv.file_sha(log)))
    path=AUDIT/artifact
    if path.exists():row['artifact']=dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path))
    rows.append(row);print(json.dumps(row),flush=True)
if all(row['process_exit_code']==0 for row in rows):
    log=AUDIT/'ROOT11_COMPLETED_COHORT_NUMERIC_CLEARANCES_V1.log'
    command=[sys.executable,'-I','-B',str(AUDIT/'record_root11_numeric_clearances_v1.py'),
        '--diagnostic',str(AUDIT/'ROOT11_NUMERIC_CONTEXT_DIAGNOSTICS_V2.json'),
        '--output',str(AUDIT/'ROOT11_NUMERIC_CONTEXT_CLEARANCES_V1.json')]
    started=time.monotonic()
    with log.open('xb') as stream:
        process=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    row=dict(name='numeric_clearances',command=command,process_exit_code=process.returncode,
        seconds=time.monotonic()-started,log=dict(path=str(log.relative_to(ROOT)),sha256=inv.file_sha(log)))
    path=AUDIT/'ROOT11_NUMERIC_CONTEXT_CLEARANCES_V1.json'
    if path.exists():row['artifact']=dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path))
    rows.append(row);print(json.dumps(row),flush=True)
inv.write_json(AUDIT/'ROOT11_COMPLETED_COHORT_CHECK_PROCESS_EXITS_V1.json',
    dict(status='ACTUAL_CPU_PROCESS_EXITS_NOT_WHOLE_CORPUS_COMPLETION',rows=rows,
        selection=dict(path=str(selection.relative_to(ROOT)),sha256=inv.file_sha(selection)),
        producer_sha256=inv.file_sha(Path(__file__)),goal_complete=False,training_authorized=False))
raise SystemExit(0 if len(rows)==5 and all(r['process_exit_code']==0 for r in rows) else 1)
