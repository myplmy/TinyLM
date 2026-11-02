"""Record actual new source/review results through the normal exact-WIP CAS."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
assert '01a17740-f435-7243-874c-2b5d58181c4c' in ledger.read_text(encoding='utf-8')
updates = [
 ('작업 내용', '전체goal active로 계속한다. 반복21891 전량유형검사후40고유/60위치를native재생성했고Luna전문판독40건을마쳤다. 실제중복3건수정은별도역할독립판독도3수용이며캐시미편입이다. 교차원문215 수집53은210저장/5미저장·새기계반려3건을드러내누락TASK005와잘못놓인출력경로를후속리뷰로보완중이다. 빈필드19123 전량검사는223고유/354위치의좁은후보를찾았고전부native재생성일치·216고유/342위치의다른검사통과를확인해Luna5가전량판독중이다. 화학명산역할오탐·불완전사양·인용누락·조사오류는개별중재중이며기계통과를채택으로세지않는다. WIP31·출력경로8·TASK17·재고5·새별칭12시험은실제통과했다. 공식H160219·v26 P77639고유/122534위치·최종cache미완·추가300M금지를유지한다.'),
 ('산출물', 'handoff/audit/hold_resolution_20261027_goalc/RESUME_FULL_GOAL_20261102_V3.md; handoff/audit/hold_resolution_20261027_goalc/supplemental_candidates_snapshot_v53.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/root_join_conflict_counter_v1/manifest.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/repeat_local_context_counter_v1/manifest.json; handoff/audit/hold_resolution_20261027_goalc/REPEAT_THREE_INDEPENDENT_REVIEW_SCOPE_V1.md; data_cache/p106b_hold_resolution_v1_20261027_goalc/nominal_local_alias_candidates_v1/complete.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/nominal_local_native_proofs_v1/complete.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/nominal_local_alias_counter_v1/manifest.json'),
 ('이어받을 지점', '교차215의누락5행·17347/18945/22347출력열·74282후속을실제저장물로확인하고수집54/계획30후속및ROOT10을조립한다. 반복40의수정3건exactdiff·독립리뷰핀과129617남은literal사유를검산한다. 빈별칭223전량판독을회수하고1077081기계역할오탐·621714추가빈필드·1017885사양·167920누락목록·188351누락시구·한글조사교정을정확경계로검산한다. 모든신규본문의코드/Unicode/의미/숫자/메모/잘림검사를닫은뒤전량v26와개별선택을실제새캐시·독립소비자·재계측에연결하고정본연쇄/한국어로컬커밋을계속한다. 미결을단순HOLD로개명해완료하거나부분묶음마감을전체일시중지로바꾸지않는다.'),
]
for field, after in updates:
    row = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(row) == 1
    before = row[0].split('|')[{'작업 내용':4, '산출물':5, '이어받을 지점':6}[field]].strip()
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT/'scripts/wip.py'), '--override',
        '--file', str(ledger), '--item', '1', '--field', field, '--expect-before', before, '--set-after', after,
        '--reason', '전체goal재개중실제수집53·반복독립판독·전량빈필드검사와native223근거반영',
        '--approval-ref', '사용자전체정제잔여HOLD완료까지재개지시및첨부목표CPU코드시험문서허가'],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(field, 'CAS 완료')
