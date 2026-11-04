"""Seal exact closed P108 logs, artifacts and source readback without models."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from scripts.p106b_shards import verify

BASE = Path('handoff/audit/nov04_weight_space')
RESULT = Path('test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md')
STAGES = (
    'Stage0W_weight_space_contract', 'Stage0bW_weight_space_contract',
    'Stage0cW_weight_space_byte_contract', 'Stage0dW_weight_space_byte_contract',
    'Stage0eW_fixed_support_contract', 'Stage1W_weight_direction_capture',
    'Stage1bW_weight_direction_byte_capture', 'Stage2bW_weight_direction_search',
    'Stage3cW_fixed_support_confirm', 'Stage4aW_float_contract',
    'Stage4bW_float_direction_capture', 'Stage4cW_float_unique_search',
    'Stage4dW_float_direction_confirm', 'Stage5aW_local_solver_contract',
    'Stage5bW_local_gradient_capture', 'Stage5cW_local_weight_dev',
    'Stage5dW_local_weight_confirm',
)
TAGS = ('p108w_v1_20261104', 'p108w_v2_20261104',
        'p108w_v3_20261104', 'p108j_v1_20261104')


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def write_new(path, data):
    raw = (json.dumps(data, ensure_ascii=False, indent=2)+chr(10)).encode('utf-8')
    if len(raw) >= 4_000_000:
        raise ValueError('small immutable audit required')
    with path.open('xb') as stream:
        stream.write(raw)


def main():
    output = BASE/'PRIMARY_SEAL_v1.json'
    if output.exists():
        raise FileExistsError(output)
    logs = ['test_result/108_log_20261104_P108_'+stage+'.txt' for stage in STAGES]
    actual = {str(p) for p in Path('test_result').glob('108_log_20261104_P108_*.txt')}
    if actual != set(logs):
        raise ValueError('closed raw-log set differs from explicit phase list')
    headings = RESULT.read_text(encoding='utf-8').splitlines()
    mappings = []
    for stage, log in zip(STAGES, logs):
        if stage.startswith('Stage0'):
            prefix = '### 1.1 '
        elif stage.startswith('Stage1'):
            prefix = '### 1.2 '
        elif stage.startswith('Stage2'):
            prefix = '### 1.3 '
        elif stage.startswith('Stage3'):
            prefix = '### 1.4 '
        elif stage.startswith('Stage4'):
            prefix = '## 6. '
        elif stage.startswith('Stage5d'):
            prefix = '## 10. '
        else:
            prefix = '## 8. '
        found = [h for h in headings if h.startswith(prefix)]
        if len(found) != 1:
            raise ValueError('exact result section missing')
        mappings.append(dict(log=log, result=str(RESULT), section=found[0], status='RECORDED'))
    closure = BASE/'P108_RESULT_CLOSURE_v1.json'
    write_new(closure, dict(schema='TINYLM_RESULT_CLOSURE_V1',
        session_id='01a0b33b-d14e-7c40-ada8-229a1f97eabd',
        wip='handoff/WIP_20261022_작업원장.md', input_logs=logs, mappings=mappings,
        raw_sha256={name: sha(Path(name).read_bytes()) for name in logs}))
    run = subprocess.run([sys.executable, '-B', '-X', 'utf8',
        'scripts/check_result_closure.py', '--manifest', str(closure)],
        capture_output=True, text=True, check=True)
    artifact_rows, shard_manifests, phase_reports = [], [], []
    for tag in TAGS:
        directory = Path('test_result/evidence')/tag
        for p in sorted(directory.rglob('*')):
            if not p.is_file():
                continue
            raw = p.read_bytes()
            if len(raw) >= 20_000_000 or p.is_symlink():
                raise ValueError('oversize or linked owned evidence')
            if p.suffix == '.json':
                data = json.loads(raw)
                if p.name == 'answers_shards_manifest.json':
                    verify(p.parent, data)
                    shard_manifests.append(str(p))
                if p.name == 'report.json' and 'wall_seconds' in data:
                    phase_reports.append(dict(path=str(p), status=data.get('status'),
                                              wall_seconds=data['wall_seconds']))
            elif p.suffix == '.jsonl':
                for line in raw.decode('utf-8').splitlines():
                    json.loads(line)
            artifact_rows.append(dict(path=str(p), sha256=sha(raw), bytes=len(raw)))
    sources = []
    for p in sorted(Path('scripts').glob('*p108*.py')):
        raw = p.read_bytes()
        ast.parse(raw.decode('utf-8'), filename=str(p))
        sources.append(dict(path=str(p), sha256=sha(raw)))
    old = json.loads((BASE/'SOURCE_ARCHIVE_v2.json').read_text(encoding='utf-8'))
    for profile in old['profiles']:
        if sha(Path(profile['path']).read_bytes()) != profile['sha256']:
            raise ValueError('sealed execution profile changed')
        for row in profile['sources']:
            if sha((BASE/row['blob']).read_bytes()) != row['sha256']:
                raise ValueError('archived executed source changed')
    readback = Path('scripts/p108_readback.py')
    data = readback.read_bytes()
    blob = BASE/'source_blobs'/(sha(data)+'.txt')
    if not blob.exists():
        with blob.open('xb') as stream:
            stream.write(data)
    write_new(BASE/'SOURCE_ARCHIVE_v3.json', dict(schema='P108_READBACK_SOURCE_V3',
        sealed_execution_archive='handoff/audit/nov04_weight_space/SOURCE_ARCHIVE_v2.json',
        source=str(readback), sha256=sha(data), blob=str(blob.relative_to(BASE)),
        scope='POST_EXECUTION_READBACK_ONLY_NOT_GPU_EXECUTION_SOURCE'))
    write_new(output, dict(schema='P108_PRIMARY_CLOSED_EVIDENCE_V1',
        closure=str(closure), closure_actual_exit=run.returncode,
        closure_stdout=run.stdout, explicit_raw_logs=len(logs),
        artifacts=artifact_rows, shard_manifests_verified=shard_manifests,
        parsed_python=sources, phase_reports=phase_reports,
        summed_phase_wall_seconds=sum(row['wall_seconds'] for row in phase_reports),
        summed_phase_scope='INCLUDES_REPEATED_NOOP_DIAGNOSTIC_NOT_EXCLUSIVE_GPU_BUSY_TIME',
        maximum_owned_artifact_bytes=max(row['bytes'] for row in artifact_rows),
        original_model_actions=0, other_session_actions=0,
        scientific_verdict='GATE_NEGATIVE', official_benchmark_runs=0,
        full_smoke='NOT_RUN_YET', scoped_static='OWNED_STATIC_v5_6_PASS_0_ERROR_71_NOT_RUN'))
    print(json.dumps(dict(raw_logs=len(logs), artifacts=len(artifact_rows),
        shard_sets=len(shard_manifests), python=len(sources), closure_exit=0,
        phase_wall_seconds=sum(row['wall_seconds'] for row in phase_reports),
        max_artifact_bytes=max(row['bytes'] for row in artifact_rows))))


if __name__ == '__main__':
    main()
