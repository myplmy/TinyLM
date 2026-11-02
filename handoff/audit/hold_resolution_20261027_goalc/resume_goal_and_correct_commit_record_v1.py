"""Resume the exact WIP and correct the earlier whole-commit scope claim."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
old_path = AUDIT/'LOCAL_COMMIT_RECEIPT_V1.json'
old = json.loads(old_path.read_text(encoding='utf-8'))
allow_path = ROOT/old['allowlist']['path']
allow = json.loads(allow_path.read_text(encoding='utf-8'))
expected = {r['path'] for r in allow['rows']} | {str(allow_path.relative_to(ROOT))}
actual = {r.decode('utf-8') for r in subprocess.check_output(['git','diff-tree','--no-commit-id',
    '--name-only','-z','-r',old['primary_commit']],cwd=ROOT).split(bytes([0])) if r}
assert len(expected) == 671 and expected <= actual and len(actual) == 681
correction = dict(status='CORRECTED_WHOLE_COMMIT_MEMBERSHIP_NOT_HISTORY_REWRITE',
    previous_receipt=dict(path=str(old_path.relative_to(ROOT)),sha256=hashlib.sha256(old_path.read_bytes()).hexdigest().upper()),
    primary_commit=old['primary_commit'],intended_owned_paths=671,actual_total_changed_paths=681,
    intended_paths_all_present=True,additional_paths_from_concurrent_staging=10,
    additional_file_contents_read=False,additional_path_names_printed=False,
    previous_owned_subset_byte_verification_is_not_whole_commit_membership_verification=True,
    previous_commits_or_other_files_modified=False,goal_status_at_current_resume='active',
    public_coordination_source='tmp/COORD_EXPERIMENT_01a0b33b.md',
    observed_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat())
with (AUDIT/'LOCAL_COMMIT_RECEIPT_V2.json').open('x',encoding='utf-8') as stream:
    json.dump(correction,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
ledger = ROOT/'handoff/WIP_20261027_작업원장.md'
assert '01a17740-f435-7243-874c-2b5d58181c4c' in ledger.read_text(encoding='utf-8')
result = subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--file',str(ledger),
    '--start','1','--note','사용자 goal 활성화에 따라 전체 잔여 HOLD 처리를 재개한다. 이전 턴은 두 후속 v4/843본문 대조/495회귀/로컬 저장의 실제 진전이었다. 저장 판독 snapshot46와 plan23 및 본문감사2를 기준으로 보존 경고8건과 알고리즘 경계1건의 원문 전체를 다시 판독하고 정확 선택을 연결한다. 이전 첫 커밋은 소유671개를 모두 포함하나 실제 전체681개였고 동시 staging된 상대 마감10개가 포함됐음을 별도 영수증V2로 정정했다. 커밋과 원형은 보존한다.',
    '--resume','새 resume_guard_counter_20261102_v1의 정확9원문/최신본문 쌍을 만들고 Luna 두 원문 역할에만 판독·새TXT/MD를 위임한다. 66생산코드 동결과 source/EOS/UTF8/SHA를 검증하고 코드/문자/스타일/호출의 정확 보류·보존 경계를 중재한다. 이후 큰 유형의 전량 복구와 최종 캐시/독립검산/재계측/정본 연쇄를 계속한다. 추가300M/GPU/모델/학습은 미허가다.'],
    cwd=ROOT,capture_output=True,text=True)
print(result.stdout,result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
with (ROOT/'tmp/COORD_HOLD_01a17740.md').open('a',encoding='utf-8') as stream:
    stream.write(chr(10).join(['','','## '+stamp+' — 전체 HOLD 목표 재개와 저장 범위 정정','',
        '사용자가 전체 HOLD 목표를 다시 active로 설정했습니다. 귀19:13 정정 저장/현재 실행·Git사용창 종료 공지를 확인했습니다. 지난 우리 첫 ed2는 준비671경로 전부를 포함하지만 실제 전체681경로였고 귀 마감10경로가 함께 포함됐음을 Git 경로 집합으로 확인해 LOCAL_COMMIT_RECEIPT_V2에 정정했습니다. 추가 경로명이나 본문은 출력/열람하지 않았고 기존 커밋·귀 파일을 되돌리거나 변경하지 않습니다.',
        '현재 index0이며 우리 다음 단계는 기존843판독 중 보존경고8+알고리즘경계1의 정확 원문과 최신본문 재대조, 그 뒤 큰 유형의 전량 복구입니다. CPU1/동일 Luna 원문역할 최대5, GPU/모델/학습/설치/대량다운로드0, 추가300M미허가입니다. 귀 전용 자료/원장/프로세스 접근·중단/잠금 요청0이며 현재 Git쓰기 예정은 없습니다.','']))
print('WIP item1 active; previous commit scope corrected without changing history.')
