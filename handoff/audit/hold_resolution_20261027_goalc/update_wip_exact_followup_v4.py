"""Keep the active goal and actual saved results distinct in the exact owned WIP."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

receipt = inv.cache.read(AUDIT / 'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V10.json')
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
    '전체 goal active·1번 진행이다. 공식 검증 부분캐시 v2는 실생성0/독립소비자0이며 원래 H460695 중 '
    'K31985/E191835/X121349/H115526 위치·잔여73668고유다. 채택1369110문서 전량 재생성, 정확 중복0, '
    'trainval본문 교집합0, 기준1145290본문 보존의 기존 증거를 유지한다. '
    f'후속 반복732는 첫 판독 전량과 독립 판독732 저장을 회수했고 독립 미결은 긴 glossary574329 한 건이며 '
    f'스냅샷10의 독립 리뷰 결합 오류는 {len(repeat["errors"])}이다. 출생2743은 스냅샷10 기준 '
    f'{saved}저장/{awaiting}미저장, NEEDS_ROOT{len(birth["needs_root"])}·결합오류{len(birth["errors"])}이다. '
    '저장은 판정 완료나 캐시 채택이 아니다. 무명19건의 개별 전문 검토 완료 HOLD와 후속 미결을 따로 추적한다. '
    '출생 수량 진단 v2는1594 선택 본문 중9건 표시이며, 기존 나이 손실17건 재검토의 실제 복구와 정당한 보류를 '
    '새 리뷰에 연결 중이다. 기존 ROOT10에도 보호ID/SHA를 먼저 제외하고4330본문을 검사해26건 보수적 표시를 얻었고 '
    '다음 Luna 지정 전문 재판독을 준비했다. 표시는 오류 확정이 아니다. 3057본문의 최신 구조 진단에서 '
    'code1/수치47/순서276건이 표시되어 원문 문맥 검토 전이며 자동 면제하지 않는다. '
    '다음 프로그램 문맥 유형1793고유/2597위치는 기존 소유·보호 대상과 겹치지 않았고, 전량 새 native decode와 '
    '동결 재생성이1793건 일치했다. 기존 다섯 역할별 새 전량 판독 입력을 준비했으며 의미 채택은0이다. '
    'glossary는 발행처와 기존 정의의 공백 정규화 전문 일치로 표제181개 복원 후보를 마련했으나 실제 정제문 검토 전이다. '
    'controls의 저장소 루트 경로 없는 rg 자기보고는 실제 접근 범위 미확인이다. 경로 고정 reader와 역할별 레지스트리, '
    '2000문자 출력 및9회귀 시험을 추가했고 원문 접근을 해당 reader로 제한했다. 빈 출력으로 접근0을 주장하지 않는다. '
    '기존 리뷰 덮어쓰기·오타·경로오류·프로세스 실패는 보존한다. ROOT10 확장 진단의 두 schema 실패와 '
    '쓰기 훅 거절도 숨기지 않으며 새 버전 진단이 성공했다. '
    '최신 로컬 저장은623c2587809e5147b0cc36d3249fbe69d8ecc401, 명시1261경로/7376058바이트이며 '
    '이후 변경은 미커밋이다. ROOT11·새 캐시·전량 최종 계측·정본 종결은 미완이다. '
    '중간 저장·부분 캐시 검증을 전체 목표 완료·일시중지·학습 승인으로 처리하지 않는다.')
resume = (
    '현재 출생 유형의 남은 자기 TASK를110까지 계속하고 새 리뷰를 스냅샷11 이후로 회수한다. '
    'Hangul은 출생549건과 지정 중재 종료 뒤 ROOT10 수량 진단26건의 원문/선택본문/전체diff를 독립 재판독한다. '
    '다른 역할은 기존 출생 배정을 마친 뒤 프로그램 문맥1793건의 자기 새 START/TASK 전량으로 이어간다. '
    'controls 새 유형은 별도 고정 reader를 먼저 만든다. 총괄은 glossary574329의 발행처 표제 근거와 미일치 정의를 '
    '검토해 Luna 실제 정제에 연결하고 code1/수치47/순서276 표시를 중재한다. 무명 추가 원문은 실제 전문 재판독한 '
    '것만 개별 검토 완료 HOLD에 연결한다. 모든 신규 선택·독립 검토·정확 예외를 ROOT11과 새 roster/캐시로 연결한다. '
    '그 뒤 나머지 미결 유형도 계속하여 전량A–E를 충족한다. 소유 명시 경로의 한국어 로컬 중간 저장은 전체 goal을 '
    '멈추는 단계가 아니다. GPU/모델/학습/추가300M/보호TinyDataset/타세션전용자료/push/PR 금지를 유지한다.')
names = ('EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V1.json', 'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V10.json',
    'EXACT_COHORT_BODY_DIAGNOSTICS_V4.json', 'BIRTH_SEMANTIC_SPAN_DIAGNOSTICS_V2.json',
    'ROOT10_STATED_QUANTITY_DIAGNOSTICS_V3.json', 'SCOPED_PACKET_READER_TEST_RESULT_V2.json',
    'REMAINING_LITERAL_FULL_SOURCE_SCOPE_V1.md', 'GLOSSARY_574329_PRIMARY_DEFINITION_ALIGNMENT_V1.json')
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
        '--reason', '실제 스냅샷10과 새 유형1793 검증·수량 재판독·저장623c·읽기 사고 경계를 연결',
        '--approval-ref', '사용자 전체 잔여 HOLD 정제 지시 및 첨부 goal의 CPU·문서·로컬 저장 허가'],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(field, 'CAS 완료')
