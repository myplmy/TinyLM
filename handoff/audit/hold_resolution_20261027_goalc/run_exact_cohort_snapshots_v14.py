"""Capture actual exits for the next five immutable review snapshots."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1',
    OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', RAYON_NUM_THREADS='1',
    TOKENIZERS_PARALLELISM='false')
rows = []
for cohort, version in [('repeat_named_roles_counter_v2', 'v14'),
    ('remaining_birth_full_counter_v1', 'v14'),
    ('repeat_named_full_independent_v1', 'v14'),
    ('root10_quantity_recheck_v1', 'v4'),
    ('remaining_literal_full_counter_v1', 'v4')]:
    log = AUDIT / (cohort + '_snapshot_' + version + '.log')
    started = time.time()
    command = [sys.executable, '-I', '-B', str(AUDIT / 'collect_exact_cohort_reviews_v5.py'),
        '--cohort', cohort, '--version', version]
    with log.open('xb') as stream:
        result = subprocess.run(command, cwd=ROOT, env=env,
            stdout=stream, stderr=subprocess.STDOUT)
    summary = inv.BASE / (cohort + '_snapshots') / version / 'complete.json'
    row = dict(cohort=cohort, process_exit_code=result.returncode,
        elapsed_seconds=time.time() - started,
        log=dict(path=str(log.relative_to(ROOT)), sha256=inv.file_sha(log)), command=command)
    if summary.exists():
        row['snapshot'] = dict(path=str(summary.relative_to(ROOT)), sha256=inv.file_sha(summary))
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)
with (AUDIT / 'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V14.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(status='ACTUAL_PROCESS_EXITS_NOT_ADMISSION', rows=rows,
        producer_sha256=inv.file_sha(Path(__file__)), goal_complete=False,
        training_authorized=False), stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
raise SystemExit(0 if all(row['process_exit_code'] == 0 for row in rows) else 1)
