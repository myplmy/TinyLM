"""Keep the full goal running while recording actual reviewed-cache preparation."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
assert '01a17740-f435-7243-874c-2b5d58181c4c' in ledger.read_text(encoding='utf-8')
updates=[
 ('작업 내용','전체goal active·1번진행을유지한다. 교차215·반복40·빈별칭223 전량과후속26·독립49를수집60/계획37에연결했다. 신규미저장0·기계반려0이며과거26오류와실패57/59를보존했다. 독립49는10건추가수정이고ROOT10은4381원문선택 K748/E3585/X48이다. 실제캐시가드전량4333본문은code/Unicode반려0·memo0,스타일14는정확쌍독립예외다. 원문프로그램5블록비공백토큰·AST를다시검산했고실행0이다. 보호7/동일SHA11위치는실제scan에서도본문미디코딩검산을마쳤다. 전량297539고유/460695위치로스터를실제생성해미결73668고유/115526위치를명시했고130개입력을동결했다. 새부분캐시v2실생성을CPU로착수했다. 투영14·보호adapter17·정확쌍10반례시험은통과했다. 공식이전캐시H160219는독립소비자검증전까지유지하며추가300M금지다.'),
 ('산출물','handoff/audit/hold_resolution_20261027_goalc/ROOT_AUTHORED_SELECTIONS_V10.json; handoff/audit/hold_resolution_20261027_goalc/EXACT_SELECTION_RUNTIME_GUARDS_V3.json; handoff/audit/hold_resolution_20261027_goalc/ROOT_RUNTIME_PAIR_APPROVALS_V1.json; handoff/audit/hold_resolution_20261027_goalc/ACTUAL_GUARDED_SOURCE_ROWS_V1.json; handoff/audit/hold_resolution_20261027_goalc/ROOT_REVIEWED_PARTIAL_ADMISSIONS_V2.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/roster_reviewed_partial_v2/complete.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/guarded_partial_proposals_v2/complete.json; handoff/audit/hold_resolution_20261027_goalc/CACHE_REVIEWED_PARTIAL_V2_PROCESS_STARTED_V1.json'),
 ('이어받을 지점','새cache_reviewed_partial_v2실제생성종료코드와built를회수하고독립소비자·보호metadata검산을수행한다. 생성완료를검증완료로승격하지않는다. 검증뒤전량문서/ID/언어/구조/중복/제외/보류를이전같은분모와재계측하고공식수량을갱신한다. 미결73668고유/115526위치는아직UNRESOLVED_NOT_ADMITTED이며큰유형문맥증명·원문복구를계속한다. 현재근거·실패·미선택과코드를명시allowlist·한국어로컬커밋으로중간저장하고정본연쇄와최종인계는전체완료근거로이어간다. 부분묶음종료·저장을전체완료/일시중지로바꾸지않는다.'),
]
for field,after in updates:
    rows=[line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(rows)==1
    before=rows[0].split('|')[{'작업 내용':4,'산출물':5,'이어받을 지점':6}[field]].strip()
    result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override','--file',str(ledger),
        '--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','실제ROOT10·독립49·전량로스터및새캐시CPU생성착수근거반영',
        '--approval-ref','사용자전체정제잔여HOLD완료까지지시와첨부goal의CPU코드시험문서관련로컬저장허가'],
        cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout,result.stderr)
        raise SystemExit(result.returncode)
    print(field,'CAS 완료')
