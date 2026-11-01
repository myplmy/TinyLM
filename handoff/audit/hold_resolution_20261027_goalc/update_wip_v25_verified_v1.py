"""Persist actual full25 exit/verification and still unfinished579 reviews."""
from pathlib import Path
import datetime
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
assert '01a17740-f435-7243-874c-2b5d58181c4c' in ledger.read_text(encoding='utf-8')
proof = json.loads((AUDIT / 'DRAFT_V25_EXECUTION_RECEIPT_V2.json').read_text(encoding='utf-8'))
assert proof['original_process_exit_code'] == 0 and proof['occurrence_counts']['PENDING'] == 122585
updates = [
 ('1', '작업 내용', '진행: 공식 부분cache는 H160219이고 전체 해소가 아니다. 전량v25는3511.196초/실제0이며 압축 직전 write_stdin46878 반환2fcca8/0을 현재 자기세션의 정확 호출/응답34641·34644로 회수했다(회수99555/ed0d4b0). 독립검증1은 실제1로 상태값 resolution 투영 오류를 남겼고 원문 메타데이터가 바뀐 사실로 해석하지 않는다. 새검증2 실제61681/0cc3120·17.005초는 고유297539/위치460695/inputIDs462874291의 전 행 ID·SHA·구간·분할·중복횟수·상태와 이유 및63코드 불변을 검산했다. 초안은 K49460/E288647/X3/P122585위치, 고유K31275/E188596/X3/P77665이며 root/cache채택0이다. v21 P123212에서627위치 감소한 초안 수치와 공식 부분H160219를 구분한다. 부분cache 실제채택3421 재검토 근거는 보존하고 모든2154912위치를25와 새 대조하는 exec49824가 진행중이다. 선택9의3116원문은 그대로 미채택이며 snapshot39 실제a4758f/0과 plan16 실제9418b1/0에 새579배정 전부를 포함했다. 해당시점114저장/465미저장·새기계반려0이고 미저장은 명시 NEEDS_ROOT로 옛 본문 우회를 금지한다. 다섯 Luna는 각32TASK 전부를 계속 처리 중이다. 7986 비LF최종줄/PaperWorks·8121 공식CDC 저자표기·30153 빈 통계 범례·107977 수식 독립정의·607511 OOB 절차 등의 경계를 중재했고 기존 실패·중간본은 보존한다. 잔여P 전량 후보 유형분석은 기존v20 분석기를25로 재사용해 준비했으며 아직 미실행이다. 전체 해소·최종zeroHcache·재계측·정본연쇄·최종인계·한국어localcommit은 미완이다.'),
 ('1', '이어받을 지점', 'exec49824의 실제종료를 write_stdin으로 관찰하고 compare_verified_v21_v25_and_actual_cache_v1.log와 complete.json을 확인한다. 그 뒤 profile_unreviewed_v25_candidates_v1.py를 CPU1로 실행해 모든77665P 후보를 유형 분석하되 restricted/개별보류는 metadata-only, 기존3116배정은 새 대표 추출에서 제외한다.579원문 다섯역할의 남은 TASK를 계속 회수하며 이전 EOF오판/잘못된 경로 주장/중간본은 실제 증거와 구분해 보존한다. 최신collector/plan은 모든 미저장 ID를 NEEDS_ROOT로 남겨 이전선택을 자동 승격하지 않는다. 새 saved 본문과 선택9 충돌은 source/body/review의 전 해시를 고정해 root가 정확 중재한다. 최종 자동채택에서 개별판독 source를 전부 제외하고 정확 선택본문만 연결한다. 원문 P를 일괄 X로 바꾸지 않는다. 전체 잔여의 실제 복구/수정/근거 있는 제외, 별도 최종cache와독립검증/재계측/정본/인계/한국어commit을 계속한다. 추가300M은 미허가다.'),
 ('2', '작업 내용', '상대 공개13:52 메모에서 소유GPU/정리/커밋 종료 및index비움을 확인했다. 타세션 전용파일·원장·프로세스를 열거나 변경하지 않았다. 우리 전량25는 종료했고 CPU1의 독립검증17초가 실제0이다. 현재 실제 부분ledger와25의 대조 CPU1이며 다음 후보 유형분석도 순차CPU1로 진행한다. 자기 tmp에 현재상태와 새579판독을 기록한다. 우리GPU/모델/학습/설치·외부쓰기·Git/index·공유정본변경0,중단·잠금요청0이다.')
]
for item, field, after in updates:
    rows = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **' + item + '** |')]
    assert len(rows) == 1
    before = rows[0].split('|')[{'작업 내용': 4, '이어받을 지점': 6}[field]].strip()
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/wip.py'), '--override', '--file', str(ledger),
        '--item', item, '--field', field, '--expect-before', before, '--set-after', after,
        '--reason', '전량25실제종료와독립검증및579미저장명시상태회수',
        '--approval-ref', '현재잔여460695전량정제goal및첨부목표CPU코드시험문서허가'],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, 'CAS complete')
timestamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
entry = chr(10) * 2 + '## ' + timestamp + ' — 전량25 실제 종료·독립검산과 CPU1 후속 대조' + chr(10) * 2
entry += '전량25 CPU1은3511.196초/실제0으로 종료했습니다. 독립검산2도17.005초/실제0이며297539SHA/460695위치와원구간·상태/이유·63코드불변을 전행 검산했습니다. 첫검산의 resolution 투영 오류/실패로그도 보존합니다. 새초안P122585는캐시채택이 아니며 공식부분cacheH160219는 그대로입니다.' + chr(10)
entry += '현재 자기 부분ledger2154912위치와25를 대조하는 CPU1이고, 종료후 기존분석기를 재사용한 잔여후보 유형분석을 순차CPU1로 수행합니다. 새579 전량Luna5판독은 계속 미완이며 원문실종·실제코드/임상/모델검증으로 과장하지 않습니다.' + chr(10)
entry += '귀13:52 공개의GPU/커밋종료/index비움을 확인했습니다. 귀전용경로·프로세스·원장에 관여하지 않으며 우리GPU/모델/학습·Git/index·공유정본 변경0입니다. 중단·잠금 요청0,추가300M미허가를 유지합니다.' + chr(10)
with (ROOT / 'tmp/COORD_HOLD_01a17740.md').open('a', encoding='utf-8') as stream:
    stream.write(entry)
print('own public coordination appended')
