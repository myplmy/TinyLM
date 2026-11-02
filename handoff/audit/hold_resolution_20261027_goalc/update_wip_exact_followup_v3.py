"""Record actual snapshot8 and pending corrections without pausing the goal."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

receipt=inv.cache.read(AUDIT/'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V8.json')
assert len(receipt['rows'])==3 and all(r['process_exit_code']==0 for r in receipt['rows'])
snapshots={}
for row in receipt['rows']:
    pin=row['snapshot'];assert inv.file_sha(ROOT/pin['path'])==pin['sha256']
    snapshots[row['cohort']]=inv.cache.read(ROOT/pin['path'])
birth=snapshots['remaining_birth_full_counter_v1']
repeat=snapshots['repeat_named_full_independent_v1']
totals=lambda data: (sum(r['saved'] for r in data['coverage'].values()),sum(r['awaiting_review'] for r in data['coverage'].values()))
bs,ba=totals(birth);rs,ra=totals(repeat)
terminal=inv.cache.read(AUDIT/'ROOT_REVIEWED_TERMINAL_HOLD19_V1.json')
assert terminal['unique_sources']==19 and not terminal['new_roster_joined']
work=(f'전체 goal active·1번 진행이다. 공식 검증 부분캐시v2는 실생성0/독립소비자0이며 원래H460695중 K31985/E191835/X121349/H115526위치·잔여73668고유다. 채택1369110문서 전량재생성·정확중복0·trainval본문교집합0·기준1145290본문보존·보호7/동일SHA11 metadata전용 검산 근거를 유지한다. '
      f'후속 반복732의 첫판독은 전량결합했고 다른역할 독립판독은 snapshot8 기준 {rs}저장/{ra}미저장, NEEDS_ROOT{len(repeat["needs_root"])}이다. 실제 본문연결 반려{len(repeat["errors"])}는 역사TASK017–020의 출력열 제목 오류이며 새리뷰 정정 중이다. '
      f'생년2743건은 snapshot8 기준 {bs}저장/{ba}미저장·미결{len(birth["needs_root"])}이다. 이 중 무명19건은 Luna/총괄 전문판독으로 개별검토완료HOLD19위치를 별도승인했으나 공식roster미연결이다. 달력2건은 공개문헌 맥락과 원문을 대조해 양쪽날짜 보존의 새review049_v11로 연결했다. '
      '수치가드8/역사리뷰별칭게이트5 회귀시험은 실제통과했다. snapshot6의 실제2087본문 진단은 code/Unicode/style/no_memo모두통과·순서표시187/수치표시32로 의미검토전이며 자동면제하지 않는다. 102091 독립나이10 복구, Calc/U/표축/의도된퀴즈빈칸/본문귀속의 오삭제 교정을 계속한다. '
      '생년snapshot7은 중첩리뷰파일명으로실제실패했고원형/로그를보존한 정확별칭등록후snapshot8의3프로세스는0이다. 열제목20행거절/완료보고와실제저장불일치/복사오타/경로오기를숨기지않는다. 과거노트바이트보존과잘못된경로본문반환자기보고의독립미확인은유지한다. '
      '최신저장HEAD bbf07a3864a99bf31b8f24d58d359dcb7fb4ba6b 이후의이번변경은아직새로커밋하지않았다. ROOT11/새캐시/전량최종계측/정본종결은미완이며중간저장을목표완료·일시중지·학습승인으로처리하지않는다.')
resume=('반복732의독립리뷰미저장과기존중재미결을모두회수하고출력열20행/실제본문/수치·의미가드를재검산해ROOT11로연결한다. root는574329긴glossary의headword결손전문판독을계속한다. birth는현재진행TASK와정확명령목록을따라controls22/hangul현재65이후/latin현재26이후/historical28/legacy44에서110까지이어간다. 102091나이10복구와422570월일충돌·431356빈구분자를새리뷰로해결한다. 그뒤잔여73668고유의다른유형도계속처리하고검토완료HOLD와미판독을구분한다. 소유명시경로한국어로컬중간저장을하되전체goal active와추가300M/모델/GPU/보호TinyDataset/타세션전용자료/push/PR금지를유지한다.')
links='; '+ '; '.join('handoff/audit/hold_resolution_20261027_goalc/'+name for name in (
    'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V8.json','EXACT_COHORT_BODY_DIAGNOSTICS_V3.json',
    'ROOT_REVIEWED_TERMINAL_HOLD19_V1.json','BIRTH_TERMINAL19_CALENDAR2_SCOPE_V1.json',
    'NUMERIC_ATOM_TEST_RESULT_V1.json','EXACT_REVIEW_RANK_ALIAS_TEST_RESULT_V1.json',
    'EXACT_COHORT_LEGACY_REVIEW_RANK_ALIASES_V1.json','NEW_IO_INCIDENT_CURRENT_METADATA_V1.json',
    'BIRTH_EXACT_CAT_COMMANDS_V1.json','RESUME_PREPARATION_FAILURES_V6.md'))
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
for field,value in {'작업 내용':work,'산출물':links,'이어받을 지점':resume}.items():
    rows=[line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(rows)==1
    before=rows[0].split('|')[{'작업 내용':4,'산출물':5,'이어받을 지점':6}[field]].strip()
    after=before+value if field=='산출물' else value
    result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override','--file',str(ledger),
        '--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','실제수집8과수치가드·달력/무명판독·실패복구·미결20행의진행상태연결',
        '--approval-ref','사용자전체정제완료까지지시와첨부goal의CPU/관련문서허가'],cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout,result.stderr);raise SystemExit(result.returncode)
    print(field,'CAS 완료')
