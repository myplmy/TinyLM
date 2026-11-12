"""Apply only explicit before/after cells via wip.py; no direct ledger writes."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--plan',required=True)
args=parser.parse_args()
path=Path(args.plan).resolve()
assert path.parent==AUDIT and not path.is_symlink()
plan=json.loads(path.read_bytes())
assert plan['wip']=='handoff/WIP_20261027_작업원장.md'
assert plan['session_id']=='01a17740-f435-7243-874c-2b5d58181c4c'
assert {(row['item'],row['field']) for row in plan['updates']}=={
    ('1','작업 내용'),('1','산출물'),('1','이어받을 지점'),('7','작업 내용')}
assert len(plan['updates'])==4
for row in plan['updates']:
    subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override',
        '--file',str(ROOT/plan['wip']),'--item',row['item'],'--field',row['field'],
        '--expect-before',row['before'],'--set-after',row['after'],
        '--reason','진행을 유지하며 의미 있는 정제 묶음의 검증·잔여량과 재개 지점만 갱신한다.',
        '--approval-ref','현재 사용자 전체 잔여 HOLD 정제 계속 및 효율 개선 지시'],
        check=True,stdout=subprocess.DEVNULL)
print(json.dumps(dict(status='FOUR_EXACT_CELLS_APPLIED_VIA_OFFICIAL_API_INDEPENDENT_CHECK_PENDING',
    plan=str(path.relative_to(ROOT)),state_changes=0)))
