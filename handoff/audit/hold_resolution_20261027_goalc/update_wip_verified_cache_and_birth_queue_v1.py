"""Put current verified facts first so the compact capsule cannot retain stale state."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
native=json.loads((AUDIT/'REMAINING_BIRTH_NATIVE_EXIT_V1.json').read_text(encoding='utf-8'))
reader=json.loads((AUDIT/'REMAINING_BIRTH_READERS_EXIT_V1.json').read_text(encoding='utf-8'))
assert native['process_exit_code']==reader['process_exit_code']==0
assert native['counts']['fresh_regeneration_and_proof_match']==reader['sources']==2743
updates={
 '작업 내용':'전체goal active·1번진행이다. 공식새부분캐시v2는실생성0·독립소비자0으로검증됐고원래H460695중K31985/E191835/X121349/H115526위치다. 잔여는73668고유이며이전H160219보다44693위치감소했다. 채택1369110문서전량재생성·정확중복0·trainval본문교집합0·기준1145290본문보존·보호7/동일SHA11metadata전용검산을마쳤다. 첫CLI소비자재귀실패1은보존하고별도라이브러리진입3시험뒤재검증했다. ROOT10의4381선택/수집60·계획37·4333본문code/Unicode가드0반려·독립49의10추가수정을연결했다. 후속반복732고유/1117위치는다섯Luna각30TASK전량판독중이며그원문native732일치와부분회수61의270저장/462대기/9출력반려를기록했다. 표명명값오보류·수식직접의존·완결단락오삭제를중재V3로추가수정중이다. 다음출생충돌전량2743고유/4273위치는현재732와중복0이고native2743재생성일치·reader종료0으로547/549/549/549/549개배정을준비했다. 이두후속묶음은아직새캐시에미편입이며입력검증을내용완료로세지않는다. 94e59e8d의676경로는중간저장이다.',
 '산출물':'; handoff/audit/hold_resolution_20261027_goalc/REMAINING_BIRTH_FULL_SOURCE_SCOPE_V1.md; handoff/audit/hold_resolution_20261027_goalc/REMAINING_BIRTH_NATIVE_EXIT_V1.json; handoff/audit/hold_resolution_20261027_goalc/REMAINING_BIRTH_READERS_EXIT_V1.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/manifest.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/repeat_named_roles_counter_v2/ROOT_MEDIATION_V3.md; handoff/audit/hold_resolution_20261027_goalc/RESUME_PREPARATION_FAILURES_V4.md',
 '이어받을 지점':(
 '반복732 전량의미판독과 V3 명명지역/거리 오보류 복구, 정확 출력/TASK 결합, 전체 차이와 가드 및 독립 재검토를 회수해 ROOT11로 연결한다. '
 '각 역할은 현재30TASK를 마친 뒤 출생충돌2743 전체의 자기 START/TASK로 이어간다. 다른 미결 유형과115526위치 내용복구도 계속한다. '
 '새 검증/재계측/소비자 실패와 수정/후속 판독/WIP를 명시 경로와 한국어 로컬 커밋으로 저장한다. '
 '미처리를HOLD종결로개명하거나부분캐시/묶음종료를전체완료·일시중지로바꾸지않는다. 추가300M·모델/GPU·보호TinyDataset·타세션전용자료·push/PR은금지다.')
}
for field,value in updates.items():
    rows=[line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(rows)==1
    before=rows[0].split('|')[{'작업 내용':4,'산출물':5,'이어받을 지점':6}[field]].strip()
    after=before+value if field=='산출물' else value
    result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override','--file',str(ledger),
        '--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','공식검증115526를현재상태선두에두고후속732/2743전량판독및실패근거연결',
        '--approval-ref','사용자전체정제잔여HOLD완료까지지시와첨부goal의CPU/관련문서허가'],
        cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout,result.stderr)
        raise SystemExit(result.returncode)
    print(field,'CAS 완료')
