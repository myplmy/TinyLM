"""Verify the saved CPU tool scope; no cache build or corpus reprocessing."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest().upper()
draft_path = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc/draft_proposals_v26_delta_v1/complete.json'
draft = json.loads(draft_path.read_text(encoding='utf-8'))
pins = draft['lineage']['source_code_sha256']
assert len(pins) == 66
for name, expected in pins.items():
    assert sha(ROOT / name) == expected, name
sources = set(pins)
sources.update(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts').glob('p106b_hold_resolution*.py'))
sources.update(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts').glob('test_p106b_hold_resolution*.py'))
sources.update(str(p.relative_to(ROOT)) for p in AUDIT.glob('*.py'))
syntax = []
for name in sorted(sources):
    path = ROOT / name
    compile(path.read_text(encoding='utf-8'), name, 'exec')
    syntax.append(dict(path=name, sha256=sha(path)))
tests = [
    'scripts/test_p106b_hold_resolution_policy_v26.py',
    'scripts/test_p106b_hold_resolution_refinement_v10_current25.py',
    'scripts/test_p106b_hold_resolution_review_safeguards_v3.py',
    'scripts/test_p106b_hold_resolution_literal_guard_v4.py',
    'scripts/test_p106b_hold_resolution_reviewed_cache_v2.py',
    'scripts/test_p106b_hold_resolution_partial_cache.py',
    'scripts/test_wip.py',
]
env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
    MKL_NUM_THREADS='1', RAYON_NUM_THREADS='1', TOKENIZERS_PARALLELISM='false', PYTHONIOENCODING='utf-8')
records = []
for index, name in enumerate(tests, 1):
    log = AUDIT / ('bounded_checkpoint_check_' + str(index).zfill(2) + '_v1.log')
    started = time.monotonic()
    with log.open('xb') as stream:
        result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / name)], cwd=ROOT, env=env,
            stdout=stream, stderr=subprocess.STDOUT)
    assert log.stat().st_size < 20_000_000, log
    records.append(dict(path=name, sha256=sha(ROOT / name), exit_code=result.returncode,
        seconds=time.monotonic()-started, log=str(log.relative_to(ROOT)), log_sha256=sha(log)))
    print(json.dumps(records[-1], ensure_ascii=False), flush=True)
    if result.returncode:
        break
for name, expected in pins.items():
    assert sha(ROOT / name) == expected, 'verified26 production source changed: ' + name
report = dict(status='BOUNDED_CHECKPOINT_CPU_CHECKS_NOT_CORPUS_COMPLETION',
    observed_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
    verified26_production_pins_unchanged=len(pins), syntax_files=syntax, tests=records,
    all_requested_tests_executed=len(records)==len(tests),
    all_exit_zero=len(records)==len(tests) and all(r['exit_code']==0 for r in records),
    goal_resumed=False, goal_complete=False, cache_admitted=0, training_authorized=False,
    GPU_model_training_runs=0, protected_or_other_session_paths_accessed=False)
target = AUDIT / 'BOUNDED_CHECKPOINT_CHECKS_V1.json'
assert not target.exists()
with target.open('x', encoding='utf-8') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(syntax_files=len(syntax), tests=len(records), all_exit_zero=report['all_exit_zero']),ensure_ascii=False))
raise SystemExit(0 if report['all_exit_zero'] else 1)
