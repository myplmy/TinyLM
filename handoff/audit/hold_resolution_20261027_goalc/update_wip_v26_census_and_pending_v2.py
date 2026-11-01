"""Persist closed CPU receipts and unresolved individual-review work by WIP CAS."""
from pathlib import Path
import datetime
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
assert '01a17740-f435-7243-874c-2b5d58181c4c' in ledger.read_text(encoding='utf-8')
proof = json.loads((AUDIT / 'DRAFT_V25_EXECUTION_RECEIPT_V2.json').read_text(encoding='utf-8'))
assert proof['original_process_exit_code'] == 0
assert proof['occurrence_counts']['PENDING'] == 122585
for namespace in ['verified_v21_v25_actual_cache_comparison_v2',
                  'remaining_unreviewed_candidate_profile_v25_v1',
                  'ordinal_metadata_candidate_census_v26_v1']:
    assert (BASE / namespace / 'complete.json').is_file()
counter = json.loads((BASE / 'ordinal_metadata_counter_v26_v1/manifest.json').read_text(encoding='utf-8'))
assert len(counter['rows']) == 27 and sum(row['occurrences'] for row in counter['rows']) == 53
updates = [
 ('1', '작업 내용', '진행: 검증된 공식 부분cache H160219는 그대로이며 최종 해소가 아니다. 전량25 실제2fcca8/0·3511.196초와 독립검증2 실제0cc312/0·17.005초는297539고유SHA/460695위치/462874291원inputIDs 및63코드 불변을 전행 닫았다. 초안K49460/E288647/X3/P122585위치와 P77665고유는 cache채택0이다. 실제부분ledger2154912위치 대조1은 빈진단매치의 빈코퍼스 종료 오류로 실제bebc75/1을 보존했고, 대조2는 실제b7fc2a/0·29.252초다. 기존1145290본문은 보존했고 신규채택196115 중192694는25의같은본문,3421(train3413/val8)은 P2521과다른종결본문900으로 전량 재검토 대상이다. 옛3421와동일ID이며 새범위추가0,기존acceptedbody와잔여P의exactSHA일치0이다. 잔여profile25 실제29a59e/0·46.286초로77665고유/122585위치를 모두 유형화했다. 새후보는 원문이나 채택이 아니다. 선택9의3116원문은 미채택이며 main579개별판독 중snapshot40 실제6ff9eb/0 시점286저장/293미저장·새기계반려0,plan17 실제6bc409/0은 모든누락을명시보류했다. 이후네역할116쌍은판독종료보고,controls는TASK028까지저장하고029이후진행중이며 미결중재를회수한다. task별읽기색인160개는2937뷰를같은SHA로연결한다. 신규26은 typed축구분류의1./2./3.을보존하는좁은정책이며361기존회귀포함371시험 실제d6d64c/0이다. 앞선시험실패/중간본은보존했다. 전량잔여census26 실제b5e04c/0·5.872초는27고유/53위치에만증거를찾았고 exact원문27쌍재생성 실제1f68af/0·2.352초로25진단을모두재현했다.26후보24EDIT/2KEEP/1PENDING은Luna개별판독중이며cache채택0,전량26미실행이다. 구조역할6건은완료보고했고나머지21건을같은다섯역할로회수한다. 최종zeroHcache·전량재계측·정본연쇄·최종인계·한국어localcommit은미완이다.'),
 ('1', '이어받을 지점', '최우선으로미결원문경계를중재하고공식원천확인날짜와명시U+코드포인트복구근거를작은감사문서로핀한다. historical528506/317922와682490충돌,latin9건및1239923/170442,hangul827336/291381등,controls17218/424015/535065/169961등은새본문과정정표로회수한다. 네종료역할과controls의남은TASK를계속하고ordinal27개도전체회수한다. collector41와plan18은main579및신규27전부를추적하고미저장/미결을명시NEEDS_ROOT로남긴다. 최신원문/본문/리뷰SHA를총괄중재한뒤선택10을만들되옛선택9우회채택은금지한다.25의동결된결과와전체P검산및27exact원문을이용한26증분적용과전량재실행을3안으로영향검토한뒤정확히같은판정/이유/원문구간을독립검산할수있는방식으로진행한다. 나머지P전량의실제복구/수정/근거있는제외를계속하고단순P→X나동일반복전부삭제로닫지않는다. 최종별도cache는기존baseline보존과3421재검토·개별선택·코드/Unicode/EOS/문서경계/분할/누설검사를연결해실제로생성·독립검증·재계측한뒤필요정본/최종인계/한국어localcommit을닫는다. 추가300M및GPU/모델/학습은미허가다.'),
 ('2', '작업 내용', '상대공개13:52메모의소유GPU/정리/커밋종료와index비움을다시확인했다. 이후새공개요청은없다. 타세션전용파일/원장/프로세스를열거나변경하지않는다. 우리전량25와독립검산/대조2/profile25/census26/exact27재생성/371시험은모두실제종료했으며현재장시간CPU실행0,다섯Luna의지정원문판독과총괄중재를진행한다. 자기tmp에닫힌실행과남은판독을갱신한다. 우리GPU/모델/학습/설치/외부쓰기/Git/index/공유정본변경0이며중단/잠금요청0,추가300M미허가를유지한다.')
]
for item, field, after in updates:
    rows = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **' + item + '** |')]
    assert len(rows) == 1
    before = rows[0].split('|')[{'작업 내용': 4, '이어받을 지점': 6}[field]].strip()
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/wip.py'), '--override', '--file', str(ledger),
        '--item', item, '--field', field, '--expect-before', before, '--set-after', after,
        '--reason', '실제대조2프로파일25와26전량census및27원문복구증거와개별미결회수',
        '--approval-ref', '현재잔여460695전량정제goal및첨부목표CPU코드시험문서허가'],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, 'CAS complete')
stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
entry = chr(10) * 2 + '## ' + stamp + ' — 전량25 대조와 유형분석 종료, 좁은26 원문27건 판독' + chr(10) * 2
entry += '전량25 독립검산 뒤 실제 부분ledger2154912위치 대조2(29.252초)와 잔여77665고유 유형분석(46.286초)은 실제0으로 닫았습니다. 대조1의 빈결과 처리 오류는 실패로그를 보존하고 정정했습니다. 공식부분H160219와 미채택초안P122585를 계속 구분합니다.' + chr(10)
entry += '순차CPU1의 좁은 축구분류 경계census(5.872초)는 전체P에서27고유/53위치만 찾았습니다. 원문27쌍 재생성(2.352초)은 이전진단과 같았고371회귀도 실제0입니다. 새후보는채택하지 않았고 기존579원문과 함께 같은Luna다섯역할이 개별판독합니다. 현재장시간CPU/GPU0이며 다음수집·검산도순차CPU1입니다.' + chr(10)
entry += '귀13:52 소유커밋/index비움 안내를 확인했고 귀전용경로/원장/프로세스에 관여하지 않습니다. 우리Git/index/공유정본변경0,중단/잠금요청0이며 최종캐시와정본/로컬커밋은아직미완입니다. 추가300M미허가를유지합니다.' + chr(10)
with (ROOT / 'tmp/COORD_HOLD_01a17740.md').open('a', encoding='utf-8') as stream:
    stream.write(entry)
print('own public coordination appended')
