"""Keep the actual running partial cache and whole residual goal distinct."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json'
selection=inv.cache.read(selection_path)
roster_path=inv.BASE/'roster_reviewed_partial_v3/complete.json'
roster=inv.cache.read(roster_path)
assert selection['source_ids']==7857 and selection['goal_complete'] is False
assert roster['remaining_hold']==110173 and roster['reviewed_hold']==38 and roster['unprocessed']==110135
assert roster['unique_counts']['HOLD']==70230
start=AUDIT/'CACHE_REVIEWED_PARTIAL_V3_PROCESS_STARTED_V1.json'
assert start.exists()
receipt=AUDIT/'CACHE_REVIEWED_PARTIAL_V3_PROCESS_EXIT_V1.json'
state='새 cache_reviewed_partial_v3의 실제 CPU 생성은 RUN이며 실제 종료 및 독립 consumer는 아직 미확인이다.'
if receipt.exists():
    result=inv.cache.read(receipt)
    state='새 cache_reviewed_partial_v3 생성의 실제 종료코드는 '+str(result['process_exit_code'])+'이며 독립 consumer 검증은 별도 미완이다.'
work=(
    '전체 정제 goal active,1번 RUN이다. 공식 검증 완료 cache_reviewed_partial_v2는 그대로 보존한다. '
    '공식 v2는 생성0/독립consumer0,원래H460695위치 중K31985/E191835/X121349/H115526,미반영73668고유이며 채택1369110문서다. '
    '기준1145290본문 보존·정확본문중복0·trainval본문교집합0은 그 v2 검증 범위이고 출처UNKNOWN/근접·URL누설 미확인은 유지한다. '
    '출생2743 전량 판독 저장은 snapshot17에서2707본문/개별 검토HOLD36,결합 오류0이다. 반복732는 다른 역할의 독립 전문 판독 전량을 연결했다. '
    'ROOT10수량26 재판독 및 오채택1255247철회HOLD를 연결했다. 문자잘림3개/LTER명칭 누락/빈 참고자료/사망월일 주체/출생지 관계/qualified날짜 오삭제를 새 Luna 버전으로 조치했다. '
    'ROOT11은7857고유 K950/E6821/X48/H38,14118277바이트의 중간 캐시 선택이며 전체 의미완료가 아니다. '
    '이번 선택 밖 literal1792와 나머지 유형은 명시 미처리로 유지한다. 원장 selected미종결0은 선택집합 안의 뜻이며 코퍼스HOLD0이 아니다. '
    'guard V10은7771본문 코드/Unicode실패0·memo0·기존 정확style14쌍,문자순서표시585다. 새/변경3448쌍의숫자는63국소원자+32기존정확중재+18개별중재로 연결했다. '
    '수량15문맥과 경북 지명접두 오탐1을 검토했고 출생 전량의 별도2차전문판독은 NOT_COMPLETED다. '
    '새 roster3는297539고유/460695위치/462874291원문ID를 보존한다. 전망H110173위치/70230고유 중 개별검토H38위치·미처리110135위치(70192고유)를 분리했다. '
    '151개 실제 runtime pin 문맥으로 proposal census3를 준비했다. '+state+
    ' literal1793의 지정 전량 판독은 다섯 Luna가 계속한다. 초기001–013재감사·잘못된수용·ID/편집근거혼동·빈/무차이출력·경로실패를 새버전/오류메모로 보존하며 새 본문은 Luna만 작성한다. '
    '정확 동일입력1675의 원문전문은 읽고 후보 중복패킷만 생략하는 프로토콜이다. selected 후보조각을 연속 후보 전문으로 오해하지 않도록 추가 명확화한다. '
    '최근 한국어 로컬 커밋a1bc5a4cb59a0865b20ce028e7da742427b7a0bb의2740명시경로 저장·부모·바이트 검산/index0은 당시 범위다. 그 이후 현재 작업과 생성 캐시는 새 저장 전이며 current-own-clean을 주장하지 않는다. '
    '나머지 전량처리·독립의미검토·새캐시독립검증/전체계측·정본연쇄·최종핸드오프는 미완이다. 추가300M/GPU/모델/학습/push/PR금지 유지.')
resume=(
    '실행 중 cache3의 정확 세션17115와 자체 build log/STARTED/EXIT만 추적한다. 실제 생성0 뒤에만 guarded_reviewed_cache_v4의 제한 consumer로 별도 독립검증을 실행하고 전체계측한다. '
    '실패 시 원형/부분출력/종료코드를 보존하고 덮거나 삭제하지 않는다. '
    '다섯 Luna는 자기 literal TASK072까지 전량 판독을 계속한다. 완료/중재 답을 정확 새리뷰에 연결하고 동일ID의source/body/sidecar를 마감한 뒤 다음ID를 편집해 혼동을 방지한다. '
    '총괄은 임시자료 출력 제한·원문 패킷 경로·identity 후보 중간생략을 명확화하고 SOURCEID/SHA/ordered/full diff 보존을 검산한다. '
    '새 roster의 미처리70192고유 중 이미 배정한literal1792를 제외한 나머지 모든 유형을 전량 metadata census/출처복원/문맥판독으로 계속 추적·처리한다. '
    'ROOT11 선택은 중간 기술캐시 근거이며 남은 문자순서변화/독립의미검토를 완료로 승격하지 않는다. '
    '중간 커밋·부분 캐시·컨텍스트 압축은 goal 정지/일시중지 사유가 아니다. A–E 전체 조건을 충족할 때만 완료한다. '
    '각 새 파일20MB미만,보호 원본/이전캐시/TinyDataset/타세션전용자료 보호와 사용자소유 학습 경계를 유지한다.')
names=['ROOT_AUTHORED_SELECTIONS_V11.json','ROOT11_COMPLETED_COHORT_BODY_CLOSURE_V1.json',
    'ROOT11_COMPLETED_COHORT_CHECK_PROCESS_EXITS_V1.json','ROOT11_NUMERIC_CONTEXT_CLEARANCES_V1.json',
    'ROOT11_QUANTITY_AND_QUALIFIED_DATE_CONTEXTS_V1.json','ROOT_REVIEWED_PARTIAL_ADMISSIONS_V3.json',
    'CACHE_REVIEWED_PARTIAL_V3_PROCESS_STARTED_V1.json','EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V3.json']
links='; '+'; '.join(str((AUDIT/n).relative_to(ROOT)) for n in names)+'; '+str(roster_path.relative_to(ROOT))
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
for field,value in {'작업 내용':work,'산출물':links,'이어받을 지점':resume}.items():
    lines=[line for line in ledger.read_text().splitlines() if line.startswith('| **1** |')]
    assert len(lines)==1
    before=lines[0].split('|')[{'작업 내용':4,'산출물':5,'이어받을 지점':6}[field]].strip()
    after=before+value if field=='산출물' else value
    proc=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override',
        '--file',str(ledger),'--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','ROOT11 선택·전체 roster3 수량과 실제 cache3 생성 RUN을 미완료 그대로 기록',
        '--approval-ref','사용자 전체 잔여 HOLD 정제와 objective CPU·캐시·문서·로컬저장 허가'],
        cwd=ROOT,text=True,capture_output=True)
    if proc.returncode:print(proc.stdout,proc.stderr);raise SystemExit(proc.returncode)
    print(field,'CAS 완료')
