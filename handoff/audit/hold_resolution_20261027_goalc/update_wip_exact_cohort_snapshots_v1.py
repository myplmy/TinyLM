"""Record verified cache and actual follow-up collection, keeping item one RUN."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
exits=inv.cache.read(AUDIT/'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V1.json')
assert len(exits['rows'])==2 and all(r['process_exit_code']==0 for r in exits['rows'])
for row in exits['rows']:
    assert inv.file_sha(ROOT/row['snapshot']['path'])==row['snapshot']['sha256']
body=inv.cache.read(AUDIT/'EXACT_COHORT_BODY_DIAGNOSTICS_V1.json')
assert body['counts']['bodies_fully_read_back_by_cpu']==1268
updates={
 '작업 내용':'전체goal active·1번진행이다. 공식새부분캐시v2는실생성0·독립소비자0이고원래H460695중K31985/E191835/X121349/H115526위치다. 잔여73668고유·채택1369110문서전량재생성·정확중복0·trainval본문교집합0·기준1145290본문보존·보호7/동일SHA11metadata전용검산을마쳤다. 첫CLI소비자재귀실패1은보존하고별도진입3시험후재검증했다. 후속반복732/1117위치와출생2743/4273위치는중복0이며원문native전량일치다. 별도전량수집v1둘다실제종료0:반복722저장/10미저장·본문703/미결8/기계반려11,출생575저장/2168미저장·본문565/미결10이다. 후속본문1268전량CPU검사code/Unicode/style/no_memo통과,순서삭제107표시·미상주장8/소유자3발생·무명도입8건은추가검토중이다. TASK총3475원문/5339패킷참조순서예외0이다. 정확역할재개허용서·명의소실철회·사망필드충돌·139도표제근거·수식독립내용오삭제방지를중재했다. 832056잘못된경로내용반환자기보고는독립미확인으로보존하고정확60조각으로재판독했다. Latin기존노트v2해시변경/원바이트보존미확인은한계로기록했다. 후속묶음은ROOT11/캐시미편입이며위수치는의미완료가아니다. 94e59e8d676경로는이전중간저장이다.',
 '산출물':'; handoff/audit/hold_resolution_20261027_goalc/EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V1.json; handoff/audit/hold_resolution_20261027_goalc/EXACT_COHORT_BODY_DIAGNOSTICS_V1.json; handoff/audit/hold_resolution_20261027_goalc/EXACT_TASK_PACKET_CONTRACT_V1.json; handoff/audit/hold_resolution_20261027_goalc/EXACT_ROLE_RECHECK_SCOPE_RECEIPT_V2.json; handoff/audit/hold_resolution_20261027_goalc/ADDITIONAL_MARKER_RECHECK_SCOPE_V1.json; handoff/audit/hold_resolution_20261027_goalc/RESUME_PREPARATION_FAILURES_V5.md; data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/ROOT_MEDIATION_V3.md',
 '이어받을 지점':'반복732의미저장10·미결/기계반려·신규주체소실3건및출생무명도입8건등정정본을회수하고새스냅샷/전량차이·가드로확인한다. 반복최종본문전량의역할교차독립검토를준비하고ROOT11로연결한다. 출생2743의남은TASK와다른115526위치의유형별내용복구도계속한다. 검증캐시/실패정정/판독회수/코드시험/WIP를명시경로와한국어로컬커밋으로중간저장하되전체완료·일시중지로바꾸지않는다. 추가300M·모델/GPU·보호TinyDataset·타세션전용자료·push/PR금지.'}
for field,value in updates.items():
    rows=[line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(rows)==1
    before=rows[0].split('|')[{'작업 내용':4,'산출물':5,'이어받을 지점':6}[field]].strip()
    after=before+value if field=='산출물' else value
    result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override','--file',str(ledger),
        '--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','공식검증115526와별도실제수집/1268본문진단/정확재개/실패정정을현재상태에연결',
        '--approval-ref','사용자전체정제잔여HOLD완료까지지시와첨부goal의CPU/관련문서허가'],
        cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout,result.stderr)
        raise SystemExit(result.returncode)
    print(field,'CAS 완료')
