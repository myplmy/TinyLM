"""Save current evidence without changing the active whole-corpus goal."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

receipt_path = AUDIT / 'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V16.json'
receipt = inv.cache.read(receipt_path)
snapshots = {}
for row in receipt['rows']:
    assert row['process_exit_code'] == 0
    assert inv.file_sha(ROOT / row['snapshot']['path']) == row['snapshot']['sha256']
    snapshots[row['cohort']] = inv.cache.read(ROOT / row['snapshot']['path'])
preview_path = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW4.json'
preview = inv.cache.read(preview_path)
assert preview['source_ids'] == 8297 and preview['cache_admitted'] == 0
guard_path = AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V8.json'
guard = inv.cache.read(guard_path)
assert guard['input_pins'][str(preview_path.relative_to(ROOT))] == inv.file_sha(preview_path)
assert len(snapshots['remaining_birth_full_counter_v1']['errors']) == 0
work = (
    '전체 정제 goal은 active이고 1번은 RUN이다. 공식 cache_reviewed_partial_v2는 실제 생성 종료0 및 독립 consumer 종료0의 기존 검증 범위다. '
    '원래 HOLD460695 위치 중 KEEP31985/EDIT191835/EXCLUDE121349/HOLD115526이며 아직 미반영 잔여73668고유다. '
    '공식 채택1369110문서, 정확 본문 중복0, train/val 본문 교집합0, 기준1145290본문 보존을 확인했으며 출처UNKNOWN과 근접·URL누설 미확인을 유지한다. '
    'snapshot16에서 반복732의 다른 역할 교차 판독 전량을 연결했고 과거 반려4개 이력은 보존한다. '
    '출생2743 전량이 저장됐으며 본문2707개와 개별 검토 HOLD36개다. 현재 결합 오류0이다. '
    'literal1793은450개 리뷰 저장,1343개 미저장이며 본문440개와 중재10개다. 그 중1046282는 총괄 전문 판독 HOLD다. '
    '기존ROOT10 수량26 재판독은25본문과 잘못된 이전 채택1255247의 철회HOLD다. '
    'ROOT11 preview4는8297고유/16405196바이트이며 KEEP1095/EDIT7116/EXCLUDE48/HOLD38이고 새 캐시 채택0이다. '
    '새 선택은 반복732/출생2743/literal441에 연결되며 현재 배정 미선택1352개와 전체 잔여를 구별한다. '
    'guard V8 실제 계수는' + json.dumps(guard['counts'], separators=(',', ':')) + '이다. '
    '1022680/1228201 코드 guard 두 표시와 신규 숫자·순서 표시의 내용 종결은 아직 필요하다. style14는 기존 정확 본문 쌍이며 이전 UTF8 손상3개는 새 버전에서 해소됐다. '
    '1323187의 LTER 이름 누락은 실제27행 이름·좌표 문자열·순서와 대조해 Luna v2로 복구했다. '
    '표 검증11시험, 실제 이전/새 본문 검증, cache adapter4 초기화101pin/검토비채택38 및 정확 쌍4검사 모두 실제0이다. 실제 새 캐시 build/독립 consumer는 NOT_RUN이다. '
    'reviewed HOLD partition11시험과 동일입력 판독11시험도 실제0이며, 동일바이트1675개에서 원문 전문 판독을 유지하고 후보 중복 패킷만 증명으로 연결한다. '
    '숫자89표시 중51개 국소 원자 증명과38개 개별 중재는 이전 정확 쌍에 한정하며 ROOT11 전체 의미 완료가 아니다. '
    'Girard/Ryti/Gregory/CIB의 좁은 사실·기호 정정, Subset 인수명 공식 근거 및 원문 병합·핀 범위 중재를 보존한다. '
    '채워진 제목·서지·함수 설명·강의 목록·원문 수치·조건·불확실성을 보존하며 없는 코드/수식/이름은 만들지 않는다. '
    '실패와 이전 초안은 FAILURES_V9까지 보존한다. 마지막 로컬 커밋26b4923d080a952652444637235e9f5b2c3633b6 이후 현재 작업은 새 저장 전이며 current-own-clean으로 보고하지 않는다. '
    'ROOT11 최종 승인/새 캐시/나머지 유형 전량/최종 계측/정본 연쇄/최종 핸드오프는 미완이다. 추가300M 금지와 학습 사용자 소유를 유지한다.')
resume = (
    '다섯 Luna 역할은 자기 literal1793 지정 TASK 끝까지 원문과 실제 선택 본문을 문맥 판독하고 새 버전으로 저장한다. '
    'Latin은 초반001–013의 잘못된 ACCEPT 재검토도 끝내며 controls는 고정 scoped reader와 자기 unchanged base만 쓴다. '
    '총괄은 runtime guard 두 표시, 현재 수치·순서 변화 및 실제 독립 의미 검토를 닫고 유효 정확 쌍만 최종ROOT11에 채택한다. '
    '새 roster에서 검토완료 HOLD38과 미판독을 별도로 계수하며 guarded_reviewed_cache_v4로 별도 cache를 실제 생성하고 독립 consumer·전체 재계측을 수행한다. '
    '생성 실행 중/정적 검사/선별 판독을 전체 완료로 승격하지 않는다. 나머지73668고유의 아직 배정하지 않은 모든 유형도 순차 전량 처리한다. '
    '작은 근거·코드·원장만 명시 경로와 한국어 제목/본문으로 로컬 중간 저장하고 계속한다. '
    '중간 저장·부분 검증·압축은 goal 정지 또는 일시중지 사유가 아니다. A–E 전체 충족 때만 완료한다. '
    '각 새 파일20MB미만, 보호 원본/이전 캐시/TinyDataset/타 세션 전용자료 보호와 GPU/모델/학습/push/PR 금지를 유지한다.')
names = ['EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V16.json', 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW4.json',
    'EXACT_SELECTION_RUNTIME_GUARDS_V8.json', 'LTER_TABLE_IDENTITY_TEST_RESULT_V1.json',
    'EXACT_LTER_TABLE_BODY_APPROVAL_1323187_V1.json', 'CACHE_V4_RUNTIME_INITIALIZATION_V1.json',
    'EXACT_LTER_RUNTIME_BINDING_CHECKS_V1.json', 'CONTROLS_LITERAL_UNCHANGED_CANDIDATE_BASES_V1.json',
    'RESUME_PREPARATION_FAILURES_V9.md']
links = '; ' + '; '.join(str((AUDIT / n).relative_to(ROOT)) for n in names)
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
for field, value in {'작업 내용':work, '산출물':links, '이어받을 지점':resume}.items():
    lines = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(lines) == 1
    before = lines[0].split('|')[{'작업 내용':4, '산출물':5, '이어받을 지점':6}[field]].strip()
    after = before + value if field == '산출물' else value
    proc = subprocess.run([sys.executable,'-I','-B',str(ROOT / 'scripts/wip.py'),'--override',
        '--file',str(ledger),'--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','출생2743 저장·snapshot16·새 검증과 여전한 전체 미완료를 실제 근거로 갱신',
        '--approval-ref','사용자 전체 잔여 HOLD 정제 지시와 objective CPU·문서·로컬저장 허가'],
        cwd=ROOT,text=True,capture_output=True)
    if proc.returncode:
        print(proc.stdout,proc.stderr)
        raise SystemExit(proc.returncode)
    print(field, 'CAS 완료')
