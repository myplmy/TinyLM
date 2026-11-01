"""Prepare an explicit owned-file list; this tool never changes Git state."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
assert subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT) == b''
scopes = ['scripts/p106b_hold_resolution*.py','scripts/test_p106b_hold_resolution*.py',
    'handoff/audit/hold_resolution_20261027_goalc','handoff/WIP_20261027_작업원장.md']
raw = subprocess.check_output(['git','status','--porcelain=v1','-z','--untracked-files=all','--',*scopes],cwd=ROOT)
changed = [v.decode('utf-8')[3:] for v in raw.split(bytes([0])) if v]
logs = {'collect_supplemental_candidates_v46.log','materialize_reviewed_selection_plan_v23.log',
    'audit_fresh_author_bodies_v2.log','materialize_bounded_checkpoint_evidence_v1.log',
    'start_bounded_checkpoint_20261101_v1.log','run_bounded_checkpoint_checks_v1.log'}
selected, local_only = [], Counter()
for name in sorted(changed):
    path = ROOT / name
    assert path.is_file() and not path.is_symlink(), name
    if name.startswith('scripts/') or name == 'handoff/WIP_20261027_작업원장.md':
        keep = True
    elif path.parent == AUDIT:
        keep = (path.suffix in {'.py','.md'} or
                (path.suffix == '.json' and path.stat().st_size <= 200000) or
                (path.suffix == '.log' and (path.name in logs or path.name.startswith('bounded_checkpoint_check_'))))
    else:
        keep = False
    if not keep:
        local_only['large_top_json_or_generated_log' if path.parent == AUDIT else 'archived_review_or_diagnostic'] += 1
        continue
    assert not any(name.startswith(prefix) for prefix in ['data_cache/','datasets/','HF/','runs/','smoketest_logs/','.env'])
    payload = path.read_bytes()
    assert len(payload) < 20_000_000
    if path.suffix == '.py':
        compile(payload.decode('utf-8'), name, 'exec')
    selected.append(dict(path=name, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest().upper()))
assert selected and sum(row['bytes'] for row in selected) < 40_000_000
value = dict(status='EXPLICIT_OWNED_LOCAL_COMMIT_ALLOWLIST',
    expected_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
    rows=selected, files=len(selected), bytes=sum(row['bytes'] for row in selected),
    groups=dict(Counter('scripts' if row['path'].startswith('scripts/') else Path(row['path']).suffix for row in selected)),
    local_only_untracked_preserved=dict(local_only), protected_or_other_session_paths_included=False,
    original_data_or_large_cache_staged=False, goal_complete=False, training_authorized=False)
manifest = AUDIT / 'BOUNDED_LOCAL_COMMIT_ALLOWLIST_V1.json'
with manifest.open('x',encoding='utf-8') as stream:
    json.dump(value,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
paths = [row['path'] for row in selected] + [str(manifest.relative_to(ROOT))]
assert all(chr(10) not in name and chr(0) not in name for name in paths)
pathspec = Path('/tmp/tinylm_hold_01a17740_checkpoint_20261101_v1.paths')
with pathspec.open('xb') as stream:
    stream.write(bytes([0]).join(name.encode('utf-8') for name in paths) + bytes([0]))
message = Path('/tmp/tinylm_hold_01a17740_checkpoint_20261101_v1.message')
with message.open('x',encoding='utf-8') as stream:
    stream.write(chr(10).join(['데이터: 잔여 HOLD 복구 도구와 판독 결과의 중단점 저장','',
        '- 원문 SHA·EOS·UTF-8 보존을 확인한 v26 증분과 누적 정제·검토 도구를 저장한다.',
        '- 579·27·237건 판독을 연결하고 중단했던 47062·119838의 후속 정정을 마무리한다.',
        '- CPU 회귀 495개와 현재 생산 코드 66개 불변, 843개 본문 대조 근거를 기록한다.',
        '- 원문 탐색 한계와 잔여 의미 진단을 보존하며 공식 부분 캐시의 HOLD 160219는 유지한다.',
        '- 최종 캐시·전량 재계측은 미완이며 목표 일시정지와 추가 300M 학습 미승인을 유지한다.','']))
print(json.dumps(dict(files=len(paths),bytes=value['bytes'],groups=value['groups'],
    local_only_preserved=value['local_only_untracked_preserved'],pathspec=str(pathspec),message=str(message)),ensure_ascii=False))
