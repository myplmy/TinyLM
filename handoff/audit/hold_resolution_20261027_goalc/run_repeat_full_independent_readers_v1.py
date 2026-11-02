"""Export and check all role-separated independent readers; retain real exit."""
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

log=AUDIT/'repeat_full_independent_readers_v1.log'
started=time.time()
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
with log.open('xb') as stream:
    result=subprocess.run([sys.executable,'-I','-B',str(AUDIT/'prepare_repeat_full_independent_readers_v1.py')],
        cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
receipt=dict(process_exit_code=result.returncode,elapsed_seconds=time.time()-started,
    log=dict(path=str(log.relative_to(ROOT)),sha256=inv.file_sha(log)),
    producer_sha256=inv.file_sha(Path(__file__)),goal_complete=False,training_authorized=False)
if result.returncode==0:
    path=inv.BASE/'repeat_named_full_independent_v1/manifest.json'
    manifest=inv.cache.read(path)
    assert len(manifest['rows'])==732
    assert all(r['role']!=r['previous_editor_role'] for r in manifest['rows'])
    receipt.update(manifest=dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path)),
        sources=732,same_editor_reviewer=0,assignments={role:len(ids) for role,ids in manifest['assignments'].items()},
        packet_parts=sum(len(r['reading_parts']) for r in manifest['rows']))
with (AUDIT/'REPEAT_FULL_INDEPENDENT_READERS_EXIT_V1.json').open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
print(json.dumps(receipt,ensure_ascii=False))
raise SystemExit(result.returncode)
