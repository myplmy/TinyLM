"""One-off closing through standard Git commands and explicit pathspec only."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
OWN = [
    'ai_dev_tool/Codex/08_AI-미보고-내역-자백원장.md',
    'handoff/202611011123_HANDOFF.md',
    'handoff/audit/nov01_scope_a/COMMIT_MESSAGE_v3.txt',
    'handoff/audit/nov01_scope_a/INDEX_RACE_v1.json',
    'handoff/audit/nov01_scope_a/INDEX_RACE_v2.json',
    'handoff/audit/nov01_scope_a/commit_race_record_REJECTED.py.txt',
    'handoff/audit/nov01_scope_a/test_commit_race_record_REJECTED.py.txt',
    'handoff/audit/nov01_scope_a/GIT_TRANSACTION_CPU_v1.log',
    'handoff/audit/nov01_scope_a/standard_git_close.py',
    'handoff/audit/nov01_scope_a/test_standard_git_close.py',
    'handoff/audit/nov01_scope_a/GIT_STANDARD_CPU_v1.log',
]


def git(*args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    env.pop('GIT_INDEX_FILE', None)
    return subprocess.run(['git', *args], cwd=ROOT, env=env, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def prepare():
    text = (BASE / 'GIT_STANDARD_CPU_v1.log').read_text()
    if 'Ran 5 tests' not in text or not text.rstrip().endswith('OK'):
        raise ValueError('standard Git CPU fixtures must pass first')
    if git('diff', '--cached', '--name-only', '-z'):
        raise ValueError('shared index is not empty; preserve staged work')
    record = dict(schema='TINYLM_STANDARD_OWNED_COMMIT_V1',
                  base_head=git('rev-parse', 'HEAD').decode().strip(), paths=OWN,
                  rejected_manual_index_execution=False,
                  automatic_review_rejection=dict(
                      action='manual primary index.lock and temporary index replacement commit',
                      reason='공유 Git index와 index.lock을 직접 조작하고 임시 index를 primary로 교체하므로 다른 세션 staged 작업 덮어쓰기·index 손상 위험이 높고 사용자가 해당 교체 방식까지 명시 승인하지 않았다.'),
                  safer_alternative='standard git add and git commit --only with exact pathspec',
                  cpu_tests=5, public_peer_window_closed=True, gpu_model_runs=0)
    with (BASE / 'INDEX_RACE_v2.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    print('STANDARD_PREPARE exact_paths=' + str(len(OWN)))


def commit():
    record = json.loads((BASE / 'INDEX_RACE_v2.json').read_text())
    if git('diff', '--cached', '--name-only', '-z'):
        raise ValueError('nonempty shared index preserved; no staging/commit')
    if git('rev-parse', 'HEAD').decode().strip() != record['base_head']:
        raise ValueError('HEAD changed before staging')
    source = {}
    for name in OWN:
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size >= 20_000_000:
            raise ValueError('invalid explicit payload')
        source[name] = path.read_bytes()
    git('add', '--', *OWN)
    if git('rev-parse', 'HEAD').decode().strip() != record['base_head']:
        raise ValueError('HEAD changed after staging; stop before commit')
    raw = git('diff', '--cached', '--name-only', '--no-renames', '-z', '--', *OWN)
    names = {part.decode() for part in raw.split(bytes([0])) if part}
    if names != set(OWN):
        raise ValueError('owned staged paths differ; stop before commit')
    for name in OWN:
        if git('show', ':' + name) != source[name] or (ROOT / name).read_bytes() != source[name]:
            raise ValueError('owned bytes changed; stop before commit')
    git('diff', '--cached', '--check', '--', *OWN)
    if git('rev-parse', 'HEAD').decode().strip() != record['base_head']:
        raise ValueError('HEAD changed before commit')
    # Git itself selects only these paths. Other staged paths cannot enter this
    # commit and Git preserves their staged state. No manual index replacement.
    git('commit', '--quiet', '--only', '-F', str(BASE / 'COMMIT_MESSAGE_v3.txt'), '--', *OWN)
    head = git('rev-parse', 'HEAD').decode().strip()
    raw = git('diff-tree', '--no-commit-id', '--no-renames', '--name-only', '-z', '-r', head)
    saved = {part.decode() for part in raw.split(bytes([0])) if part}
    if saved != set(OWN):
        raise ValueError('unexpected committed scope; preserve and report')
    print(json.dumps(dict(commit=head, exact_owned_paths=len(OWN),
                          manual_index_replacement=False, foreign_committed=0)))


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['commit']:
        commit()
    else:
        raise SystemExit('one explicit prepare/commit operation required')
