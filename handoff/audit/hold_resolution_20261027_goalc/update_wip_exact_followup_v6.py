"""Keep the active goal and actual saved results distinct in the exact owned WIP."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

receipt = inv.cache.read(AUDIT / 'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V13.json')
snapshots = {}
assert all(row['process_exit_code'] == 0 for row in receipt['rows'])
for row in receipt['rows']:
    pin = row['snapshot']
    assert inv.file_sha(ROOT / pin['path']) == pin['sha256']
    snapshots[row['cohort']] = inv.cache.read(ROOT / pin['path'])
birth = snapshots['remaining_birth_full_counter_v1']
repeat = snapshots['repeat_named_full_independent_v1']
saved = sum(row['saved'] for row in birth['coverage'].values())
awaiting = sum(row['awaiting_review'] for row in birth['coverage'].values())
literal = inv.cache.read(inv.BASE / 'remaining_literal_native_proofs_v1/complete.json')
assert literal['counts']['fresh_regeneration_and_proof_match'] == 1793
prior = inv.cache.read(AUDIT / 'ROOT10_STATED_QUANTITY_DIAGNOSTICS_V3.json')
assert prior['counts']['flagged_sources'] == 26
work = (
    '전체 goal active·1번 진행이다. 공식 부분캐시v2 실생성0/독립소비자0, 원래H460695중 '
    'K31985/E191835/X121349/H115526위치와 잔여73668고유는 아직 새선택 미반영의 정본이다. '
    '채택1369110문서 전량재생성·정확중복0·trainval본문교집합0·기준1145290본문보존의 기존 증거를 유지한다. '
    '스냅샷13에서 반복732의 교차 독립 판독은 전량 저장/연결·미결0·결합오류0이다. '
    'glossary574329는 Luna의 실제 정제본문에서 발행처와 일치한 표제182복원/기존34보존/탐색UI23줄과 고립구분자1문자 제거를 원문 전체 줄순서로 검산해 다른 비빈줄 변경0을 확인했다. '
    '출생2743은 스냅샷13 기준2532저장/211미저장, 이 중36건은 Luna와총괄 전문 판독 완료HOLD로 별도승인했으나 새roster미연결이다. '
    '525187은 새본문/리뷰의 실제 결합을 검증했고 출생의 현재 기계결합오류0이다. 40개NEEDS_ROOT중36개는 검토완료HOLD이며 나머지4개는이후새리뷰로중재반영중이다. '
    '잘못된TASK043의223800 추가행은 옛반려 이력으로 보존하고 정상043새리뷰와 원래042의 실제배정을 유지한다. '
    '기존ROOT10의4330본문 수량검사에서 표시한26건은 다른Luna의 전문 재판독을 모두 회수했다. 실제나이·기간·서지·공통날짜 손실을 새본문으로 복구했고, '
    '1255247은 무명리드를 지운뒤 분류뿐인 본문을 잘못채택했던 근거를 확인해 선택철회/HOLD승인을 기록했지만 캐시미반영이다. '
    '다음 프로그램문맥1793고유/2597위치는 보호/기존소유와 겹침0, 전량fresh원문decode와 동결재생성 일치를 확인하고 역할별전량판독중이다. '
    '스냅샷13의 이 유형은76저장/1717미저장이며 이후저장은 다음수집대기다. root가 실제전문을읽은1046282는 수식/관계가손상된미리보기 조각의 개별HOLD를 승인했다. '
    '세묶음3456본문 CPU재판독에서Unicode/style/no_memo는 전부통과, 원형순서311/수치56본문쌍/code1표시는 별도문맥중재대상이다. '
    'code1은 원형/본문SHA가정확한1291499의그리스어강세전사한문장을실행코드로잡은경우로 실제fence0/다른inline매치73보존과 원형sidecar를확인해 정확쌍만 승인했다. '
    '새국소수치증명10회귀시험은 실제통과0이다. 수치원자·단위·순서·중복수를 같은변경블록에서대조해51표시를원형에연결했고38표시는15고유/19본문쌍의추가중재로남겼다. '
    '이 검사는 숫자출처의좁은증거이며 대상·사건·사실정정·의미를자동승인하지않는다. 처음짧은fixture의기대표시가없어10시험중1실패한원형은보존했고 새v2fixture/실제종료코드로고쳤다. '
    'controls의루트경로없는rg과거실제접근범위는미확인이다. 지정reader9시험과단일역할레지스트리/2000문자출력만허용해계속하며 OS수준차단이라고주장하지않는다. '
    '추가두reader의실제probe는각0이며 전문판독은아니다. 경로오류·누락본문·잘못된열제목·잘못된sidecar·초안덮기거절과모든실패/이전버전은보존한다. '
    '최신로컬저장은26b4923d080a952652444637235e9f5b2c3633b6의1248명시경로10641330바이트다. 정확멤버십/블롭/부모와당시소유범위clean을검증했고그이후신규판독과현재문서등은아직새커밋전이다. 바이트동일읽기11시험은실제0이며1675동일쌍은전체원문판독을유지한채후보중복3999패킷만증명으로연결하고118다른쌍은양쪽전문을읽는다. v1producer는마지막set JSON직렬화실패로보존,새v2실제0/완료증명과역할별V2계획을사용한다. ROOT11/새캐시/전량최종계측/정본종결은미완이다. '
    '중간저장·부분캐시검증을전체목표완료·일시중지·학습승인으로처리하지않는다.')
resume = (
    '출생의각역할남은TASK를110까지계속하고신규리뷰를다음스냅샷으로회수한다. Legacy는출생110의1415최소마크업보정후 '
    '자기새literal360건전량, Hangul은이미literal356건전량을진행한다. 다른역할도출생을마친뒤준비된자기literal전량으로이어간다. '
    '총괄은525187복구와glossary최종선택/ROOT10수량26결과를다시결합하고、숫자38표시의15고유원문을기존1차근거와실제본문으로중재한다. '
    '무명36·prior1255247선택철회·literal1046282의검토완료HOLD는원문/범위/두판독근거로새roster에연결한다. '
    'ROOT11을20MB미만아티팩트로작성하고기존4381과신규정제/독립검토/정확예외를합쳐새캐시를실생성·검증한다. '
    '그뒤잔여73668고유의다른유형도전량처리하고A–E를충족할때만전체goal완료한다. '
    '소유명시경로한국어로컬중간저장은정제작업을멈추는단계가아니다. GPU/모델/학습/추가300M/보호TinyDataset/타세션전용자료/push/PR금지를유지한다.')
resume = resume.replace('、', ', ')
names = ('EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V13.json', 'EXACT_COHORT_BODY_DIAGNOSTICS_V5.json',
    'BIRTH_SEMANTIC_SPAN_DIAGNOSTICS_V3.json', 'ROOT_REVIEWED_TERMINAL_HOLD36_V1.json',
    'ROOT_PRIOR_BODY_WITHDRAWAL_1255247_V1.json', 'GLOSSARY_574329_RESTORATION_VERIFIED_V1.json',
    'EXACT_PHONETIC_STRESS_CODE_EXCEPTION_1291499_V1.json', 'NUMERIC_LOCAL_ATOM_TEST_RESULT_V2.json',
    'EXACT_COHORT_NUMERIC_LOCAL_PROOFS_V1.json', 'CONTROLS_LITERAL_AND_GLOSSARY_READER_PROBES_V1.json',
    'RESUME_PREPARATION_FAILURES_V7.md', 'EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V2.json', 'IDENTICAL_LITERAL_INPUT_READING_PROOFS_V2.json', 'IDENTICAL_INPUT_READING_TEST_RESULT_V1.json')
links = '; ' + '; '.join(str((AUDIT / name).relative_to(ROOT)) for name in names)
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
for field, value in {'작업 내용': work, '산출물': links, '이어받을 지점': resume}.items():
    lines = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(lines) == 1
    before = lines[0].split('|')[{'작업 내용': 4, '산출물': 5, '이어받을 지점': 6}[field]].strip()
    after = before + value if field == '산출물' else value
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/wip.py'),
        '--override', '--file', str(ledger), '--item', '1', '--field', field,
        '--expect-before', before, '--set-after', after,
        '--reason', '실제 스냅샷13·커밋26b4923d·동일쌍1675와 계속정제를 연결',
        '--approval-ref', '사용자 전체 잔여 HOLD 정제 지시 및 첨부 goal의 CPU·문서·로컬 저장 허가'],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(field, 'CAS 완료')
