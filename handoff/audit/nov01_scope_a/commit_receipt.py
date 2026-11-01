"""Read-only Git/raw-log verification plus owned closing receipts only."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from update_handoff import rows


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def main():
    first = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if first != 'c43ef2eb0428c2e53b21ea466bcd0b18e163bfb9':
        raise ValueError('closing receipt requires the exact A implementation commit')
    plan = json.loads((BASE / 'STAGE_PATHS_v1.json').read_text())
    changed = subprocess.check_output(['git', 'diff-tree', '--no-commit-id', '--no-renames',
                                       '--name-only', '-z', '-r', first])
    committed = {x.decode() for x in changed.split(bytes([0])) if x}
    if committed != set(plan['paths']):
        raise ValueError('first commit scope differs from the reviewed paths')
    if 'scripts/flag_whitelist.tsv' in committed:
        raise ValueError('foreign flag was committed')
    flag = ROOT / 'scripts/flag_whitelist.tsv'
    if sha(flag.read_bytes()) != plan['foreign_flag_sha256']:
        raise ValueError('foreign flag changed during this closure')
    audit = json.loads((BASE / 'OWNED_STATIC_v5.json').read_text())
    for entry in audit['validation_scope']['inputs']:
        if entry['path'].endswith('.py') or entry['path'] == 'scripts/flag_whitelist.tsv':
            if sha((ROOT / entry['path']).read_bytes()) != entry['sha256']:
                raise ValueError('validated source/shared metadata changed')
    closure = json.loads((ROOT / 'handoff/audit/nov01_afternoon/RESULT_CLOSURE_v1.json').read_text())
    logs = closure['input_logs']
    if len(logs) != 50 or any(not x.startswith('test_result/') or not x.endswith('.txt') for x in logs):
        raise ValueError('exact 50 public raw logs required')
    logs = [*logs, 'smoketest_logs/20261031170749_smoke_codex_nov01_adaptive_training_v1_329e4ed.txt']
    raw_rows = []
    for name in logs:
        local = (ROOT / name).read_bytes()
        saved = subprocess.check_output(['git', 'show', first + ':' + name])
        if saved != local:
            raise ValueError('committed raw log differs: ' + name)
        raw_rows.append(dict(path=name, bytes=len(local), sha256=sha(local)))
    board = rows((ROOT / 'handoff/WIP_20261022_작업원장.md').read_text())
    handoff = rows((ROOT / 'handoff/202611011123_HANDOFF.md').read_text())
    if len(board) != 106 or set(board) != set(handoff):
        raise ValueError('directive inventory mismatch')
    for key in board:
        if board[key][1] != handoff[key][1] or board[key][2] not in handoff[key][5]:
            raise ValueError('original directive or status mismatch: ' + key)
    if board['106'][2] != '✅**완료**':
        raise ValueError('A row must be complete')
    for name in ('HANDOFF_STRUCTURE_final.log', 'HANDOFF_TIME_final.log', 'HANDOFF_QUEUE_final.log'):
        text = (BASE / name).read_text()
        if ('errors=0' not in text and '모순 0건' not in text):
            raise ValueError('final handoff check did not pass')
    result = dict(schema='TINYLM_SCOPE_A_COMMIT_RECEIPT_V1', implementation_commit=first,
                  implementation_paths=len(committed), raw_result_logs=50, raw_smoke_logs=1,
                  raw_logs_byte_exact=raw_rows, source_changes_after_validation=0,
                  foreign_flag_preserved=True, directives=106, all_originals_and_statuses_match=True,
                  wip106='DONE', whole_wip_closed=False, current_full_smoke='NOT_RUN',
                  after_15_gpu_model_runs=0, payload_deletions=0, push_pr=0)
    receipt = BASE / 'COMMIT_RECEIPT_v1.json'
    with receipt.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    closing = ['handoff/WIP_20261022_작업원장.md', 'handoff/202611011123_HANDOFF.md']
    closing += ['handoff/audit/nov01_scope_a/' + name for name in (
        'COMMIT_MESSAGE_v2.txt', 'HANDOFF_SYNC_close.json', 'HANDOFF_STRUCTURE_final.log',
        'HANDOFF_TIME_final.log', 'HANDOFF_QUEUE_final.log', 'commit_receipt.py',
        'COMMIT_RECEIPT_v1.json', 'STAGE_PATHS_v2.json')]
    for name in closing:
        if (ROOT / name).is_file() and (ROOT / name).stat().st_size >= 20_000_000:
            raise ValueError('closing result file exceeds 20MB')
    with (BASE / 'STAGE_PATHS_v2.json').open('x', encoding='utf-8') as stream:
        json.dump(dict(base_head=first, paths=closing, scope='owned closing documents only'),
                  stream, ensure_ascii=False, indent=2)
    Path('/tmp/tinylm_nov01_scope_a_close_paths.nul').write_bytes(
        bytes([0]).join(name.encode() for name in closing) + bytes([0]))
    print(json.dumps(dict(implementation_commit=first, raw_logs_exact=len(logs),
                          directives=106, source_changes=0, closing_paths=len(closing))))


if __name__ == '__main__':
    main()
