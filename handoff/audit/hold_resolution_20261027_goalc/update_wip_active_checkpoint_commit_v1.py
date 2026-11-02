"""Record the verified intermediate commit without closing or pausing the goal."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
receipt='handoff/audit/hold_resolution_20261027_goalc/RESUME_ACTIVE_SCOPE_LOCAL_COMMIT_V1.json'
record=json.loads((ROOT/receipt).read_text(encoding='utf-8'))
assert record['whole_changed_path_set_exact'] and record['all_committed_bytes_match']
assert record['actual_changed_paths']==676 and record['remaining_shared_index_count']==0
for field in ['작업 내용','산출물']:
    rows=[line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(rows)==1
    before=rows[0].split('|')[{'작업 내용':4,'산출물':5}[field]].strip()
    after=before+(' 명시676경로약3.8MB를한국어로컬커밋'+record['commit'][:8]+
        '로저장했고전체실제경로·바이트일치와index0을확인했다. 전체goal진행과CPU캐시생성은계속한다.'
        if field=='작업 내용' else '; '+receipt)
    result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override','--file',str(ledger),
        '--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','실제676경로한국어중간커밋검산결과반영및전체목표진행유지',
        '--approval-ref','사용자전체HOLD정제계속지시와첨부goal의명시로컬커밋허가'],
        cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout,result.stderr)
        raise SystemExit(result.returncode)
    print(field,'CAS 완료')
