"""Keep the goal running after the real build and independent consumer finish."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
metrics=AUDIT/'REVIEWED_PARTIAL_V2_VERIFIED_METRICS_V1.json'
verified=json.loads(metrics.read_text(encoding='utf-8'))
assert verified['remaining_hold']==115526 and verified['goal_complete'] is False
updates={
 '작업 내용':' 새cache_reviewed_partial_v2는실제생성종료0·독립소비자종료0으로검증됐다. 첫CLI소비자재귀오류종료1/증거0을보존하고별도직접라이브러리진입3시험뒤재실행했다. 공식잔여HOLD는이전160219에서115526위치/73668고유로44693위치감소했고최초460695중74.9235%를처리했다. 원래H의K31985/E191835/X121349/H115526이며채택전량재생성·정확중복0·trainval본문교집합0·보호7/동일SHA11metadata전용검산을마쳤다. 기준1145290본문보존이며이전부분후보전부불변주장은하지않는다. 같은채택목록전후구조·언어proxy는새재계측영수증에기록했고보호부모본문계측한계를명시했다. 후속732판독은이캐시에포함되지않으며전체goal은계속active이다.',
 '산출물':'; handoff/audit/hold_resolution_20261027_goalc/REVIEWED_PARTIAL_V2_VERIFIED_METRICS_V1.json; handoff/audit/hold_resolution_20261027_goalc/HOLD_STATUS_AND_EXCLUSION_RATIONALE_20261103_V1.md; handoff/audit/hold_resolution_20261027_goalc/CACHE_REVIEWED_PARTIAL_V2_VERIFY_EXIT_V1.json; handoff/audit/hold_resolution_20261027_goalc/CACHE_REVIEWED_PARTIAL_V2_VERIFY_EXIT_V2.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/cache_reviewed_partial_v2/partial_resolution_verified.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/repeat_named_roles_counter_v2/ROOT_MEDIATION_V1.md',
 '이어받을 지점':'전체goal은active이다. 공식새부분캐시v2검증0과미결73668고유/115526위치를기준으로반복732고유/1117위치의30TASK씩전량판독·정확본문결합·전체차이·가드·독립의미검토후ROOT11로연결한다. 다른큰미결유형복구도계속한다. 94e59e8d의676경로중간저장뒤새검증/재계측/소비자실패및수정/후속732/WIP를한국어로컬커밋한다. 미처리를HOLD종결로개명하거나부분캐시종료를전체완료/일시중지로바꾸지않는다. 추가300M·GPU/모델·타세션전용자료·보호TinyDataset·push/PR은금지다.'
}
for field,value in updates.items():
    rows=[line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(rows)==1
    before=rows[0].split('|')[{'작업 내용':4,'산출물':5,'이어받을 지점':6}[field]].strip()
    after=value if field=='이어받을 지점' else before+value
    result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override','--file',str(ledger),
        '--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','새부분캐시실생성0·독립검산0·잔여115526및동일채택목록재계측반영',
        '--approval-ref','사용자전체정제잔여HOLD완료까지지시와첨부goal의CPU분석/관련자료허가'],
        cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout,result.stderr)
        raise SystemExit(result.returncode)
    print(field,'CAS 완료')
