"""Exact P108 local-commit inventory; never enumerate other-session work."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

from handoff.audit.nov01_afternoon.prepare_owned_commit_v3 import git, names

BASE = Path('handoff/audit/nov04_weight_space')
EXACT = (
    'ai_dev_tool/Codex/08_AI-미보고-내역-자백원장.md',
    'docs/EXPERIMENT_BASELINES.md', 'docs/METHODS.md',
    'docs/methods/03_knowledge_quality.md', 'experiments.tsv',
    'handoff/COMPASS.md', 'handoff/WIP_20261022_작업원장.md',
    'test_plan/실험계획목록.md', 'test_result/실험목록.md',
    'test_plan/P108_직접가중치-방향수리와-학습개입.md',
    'test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md',
)


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def main():
    manifest = BASE/'COMMIT_SCOPE_v1.json'
    if manifest.exists() or names(git('diff', '--cached', '--name-only', '-z')):
        raise ValueError('fresh manifest and empty shared index required')
    candidates = {Path(name) for name in EXACT}
    candidates.update(Path('scripts').glob('*p108*.py'))
    candidates.update(Path('.').glob('run_P108_*-cancel.sh'))
    candidates.update(Path('docs/research').glob('20261104_P108_*.md'))
    candidates.update(Path('test_result').glob('108_log_20261104_P108_*.txt'))
    for folder in (BASE, *(Path('test_result/evidence')/tag for tag in
        ('p108w_v1_20261104', 'p108w_v2_20261104',
         'p108w_v3_20261104', 'p108j_v1_20261104'))):
        candidates.update(p for p in folder.rglob('*') if p.is_file())
    records = []
    for p in sorted(candidates):
        name = p.as_posix()
        if (p.is_symlink() or any(x.is_symlink() for x in p.parents)
                or name.startswith(('datasets/', 'data_cache/', 'runs/', 'HF/', '.agents/', '.codex/', 'agents/'))
                or p.suffix in ('.pt', '.bin', '.lock') or 'hold_resolution_' in name):
            raise ValueError('excluded or linked commit candidate: '+name)
        data = p.read_bytes()
        if len(data) >= 20_000_000:
            raise ValueError('20MB per-file commit limit')
        data.decode('utf-8')
        if p.suffix == '.py':
            ast.parse(data.decode('utf-8'), filename=name)
        if p.suffix == '.json':
            json.loads(data)
        before = subprocess.run(['git', 'show', 'HEAD:'+name], capture_output=True)
        if before.returncode == 0 and before.stdout == data:
            continue
        records.append(dict(path=name, bytes=len(data), sha256=sha(data)))
    if len([r for r in records if r['path'].startswith('test_result/108_log_')]) != 17:
        raise ValueError('all 17 owned raw logs must be preserved')
    paths = sorted([r['path'] for r in records]+[str(manifest)])
    subprocess.run(['git', 'diff', '--check', '--', *paths], check=True, capture_output=True)
    value = dict(schema='P108_OWNED_LOCAL_COMMIT_SCOPE_V1', authority_directive=107,
        parent=git('rev-parse', 'HEAD').decode().strip(),
        branch=git('branch', '--show-current').decode().strip(),
        paths=paths, bindings=records, bytes=sum(r['bytes'] for r in records),
        raw_logs=17, maximum_bytes=max(r['bytes'] for r in records),
        foreign_work_excluded=True, checkpoint_or_runtime_staging=False,
        protected_dataset_access=False, push=False)
    with manifest.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps(dict(paths=len(paths), bytes=value['bytes'], max_bytes=value['maximum_bytes'],
                          parent=value['parent'], manifest_sha256=sha(manifest.read_bytes()))))


if __name__ == '__main__':
    main()
