"""Record the actual first commit, pause the broad WIP, and prepare final notes."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert re.fullmatch('[0-9a-f]{40}',commit)
manifest_path = AUDIT/'BOUNDED_LOCAL_COMMIT_ALLOWLIST_V1.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
assert commit != manifest['expected_head']
assert subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT) == b''
paths = [row['path'] for row in manifest['rows']] + [str(manifest_path.relative_to(ROOT))]
entries = subprocess.check_output(['git','ls-tree','-rz','--full-tree',commit,'--',*paths],cwd=ROOT)
objects = {value.split(bytes([9]),1)[1].decode('utf-8'):value.split(bytes([9]),1)[0].split()[2].decode('ascii')
           for value in entries.split(bytes([0])) if value}
working = subprocess.check_output(['git','hash-object','--no-filters','--stdin-paths'],cwd=ROOT,
    input=(chr(10).join(paths)+chr(10)).encode('utf-8')).decode('ascii').splitlines()
assert set(objects) == set(paths) and all(objects[name] == value for name,value in zip(paths,working))
ledger = ROOT/'handoff/WIP_20261027_작업원장.md'
assert '01a17740-f435-7243-874c-2b5d58181c4c' in ledger.read_text(encoding='utf-8')
common = [sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--file',str(ledger)]
artifact = 'handoff/audit/hold_resolution_20261027_goalc/CURRENT_SCOPE_SAVE_REPORT_20261101_V1.md; handoff/audit/hold_resolution_20261027_goalc/LOCAL_COMMIT_RECEIPT_V1.json'
updates = [
    ['--wait','1','--note','사용자 한정 마감에 따라 전체 goal은 paused다. 579와27과237 저장행을 snapshot46/plan23으로 모두 회수했고843 본문 감사의 파일 오류는0이나 코드/스타일/호출/수치 등 의미 진단은 남아 있다. 공식 부분 캐시 H160219와 초안 P77639고유/P122534위치는 유지하며 최종 캐시와 전량 재계측은 미완이다.',
     '--artifact',artifact,'--resume','사용자의 전체 작업 재개 지시 뒤 snapshot46/plan23/본문감사2와 선택9/선택10 미리보기의 source/body/review SHA 충돌을 중재한다. 잔여 의미 진단을 닫고 최종 별도 캐시와 독립검산 및 전량 재계측과 정본 연쇄를 진행한다. 추가300M/GPU/모델/학습은 미허가다.'],
    ['--done','2','--note','상대 공개13:52 종료 공지와 index 비움을 재확인했다. 이후 우리 명시 소유 경로만 로컬 커밋하고 모든 Git 바이트를 대조했으며 타 세션 전용 자료/원장/프로세스/공유 flag를 변경하지 않았다. 중단/잠금 요청0이다.','--artifact','tmp/COORD_HOLD_01a17740.md'],
    ['--done','3','--note','중단했던47062와119838 후속을 최종v4로 마치고 정확 전체 diff/EOF를 대조했다. snapshot46/plan23/843본문감사2와 CPU495회귀 및 생산66해시 불변을 확인했다. 소유 명시 목록을 한국어 로컬 커밋 '+commit[:8]+'로 실제 저장했고 커밋의 전체 파일 바이트가 작업 파일과 일치한다. 대량 원문/캐시와 과거 실패는 로컬에 보존하고 전체 goal은 paused로 둔다.','--artifact',artifact]
]
for args in updates:
    result = subprocess.run(common+args,cwd=ROOT,capture_output=True,text=True)
    print(result.stdout,result.stderr)
    if result.returncode:
        raise SystemExit(result.returncode)
capsule = subprocess.run(common+['--capsule-check'],cwd=ROOT,capture_output=True,text=True)
assert capsule.returncode == 0,(capsule.stdout,capsule.stderr)
log = AUDIT/'bounded_post_commit_wip_check_v1.log'
with log.open('xb') as stream:
    test = subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/test_wip.py')],cwd=ROOT,
                          stdout=stream,stderr=subprocess.STDOUT)
assert test.returncode == 0
receipt_path = AUDIT/'LOCAL_COMMIT_RECEIPT_V1.json'
receipt = dict(status='ACTUAL_LOCAL_COMMIT_AND_SCOPED_WIP_CLOSURE',primary_commit=commit,
    verified_commit_paths=len(paths),all_primary_commit_bytes_match=True,
    allowlist=dict(path=str(manifest_path.relative_to(ROOT)),sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper()),
    current_goal_status='paused',WIP_item1='WAIT_USER_RESUME',WIP_item2='DONE',WIP_item3='DONE',
    final_cache_created=False,training_authorized=False,push_runs=0,PR_changes=0,
    post_wip_capsule_check=capsule.stdout.strip(),post_wip_test_exit=test.returncode,
    post_wip_log=dict(path=str(log.relative_to(ROOT)),sha256=hashlib.sha256(log.read_bytes()).hexdigest().upper()),
    observed_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat())
with receipt_path.open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
post_paths = [str(path.relative_to(ROOT)) for path in [ledger,receipt_path,log]]
with Path('/tmp/tinylm_hold_01a17740_checkpoint_20261101_post.paths').open('xb') as stream:
    stream.write(bytes([0]).join(name.encode('utf-8') for name in post_paths)+bytes([0]))
with Path('/tmp/tinylm_hold_01a17740_checkpoint_20261101_post.message').open('x',encoding='utf-8') as stream:
    stream.write(chr(10).join(['문서: 한정 마감 커밋 결과와 작업원장을 기록한다','',
        '- 실제 로컬 커밋 '+commit[:8]+'의 전체 저장 경로와 Git 바이트 일치를 확인한다.',
        '- 두 보조작업과 현재 범위 저장을 완료하고 전체 HOLD 해소 목표는 사용자 재개 대기로 둔다.',
        '- 원장 캡슐과 회귀를 확인하고 최종 캐시·추가 학습 미완 상태를 보존한다.','']))
print(json.dumps(dict(primary_commit=commit,verified_paths=len(paths),post_paths=post_paths,
    capsule_check=capsule.stdout.strip()),ensure_ascii=False))
