"""Record bounded original-source search and actual saved-body diagnostics."""
from pathlib import Path
import datetime
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
assert '01a17740-f435-7243-874c-2b5d58181c4c' in ledger.read_text(encoding='utf-8')
snapshot = json.loads((AUDIT / 'supplemental_candidates_snapshot_v43.json').read_text(encoding='utf-8'))
audit = json.loads((AUDIT / 'fresh_author_body_literals_v1.json').read_text(encoding='utf-8'))
assert snapshot['coverage']['profile_strata_source_counter_v25_v1']['saved'] == 229
assert audit['counts']['bodies'] == 824 and not audit['errors']
assert (AUDIT / 'LOCAL_SOURCE_DISCOVERY_REPORT_V1.md').is_file()
updates = [
 ('1', '작업 내용', '진행: 공식 검증 부분 캐시의 HOLD 160219는 그대로이며 최종 정제나 학습 재개가 완료된 상태가 아니다. 검산된 26 증분의 초안은 고유 P77639, 위치 P122534이고 캐시 채택은 0이다. snapshot43 실제 1f7888/0, plan20 실제 7b295c/0으로 main579와 ordinal27 저장은 전부 회수했다. main978970와670434의 이전 선언 결함도 닫혔다. 새237은 수집 시점229저장/8미저장이며 이후 마지막 Latin 판독과 중재 후속 저장이 계속된다. 1239776의 표 구분자/본문 경로, 234748의 비허용 판정어, 중재 뒤에도 NEEDS_ROOT로 남은 표들은 해당 작성자에게 새 표로 회수 중이다. 새 본문 감사8074는 실제 f1e6cf/0, 5.249초로824 본문/원문 SHA를 확인했고 파일 오류0이다. 함수괄호 손실1, 코드나 문자 경고4, 스타일2, 새 숫자5, 편집메모0 등은 진단이며 자동 통과가 아니다. 사용자 원문 폴더 탐색 지시로 HF의 위키백과/FineWeb 원천4곳을 링크 경계 안에서 확인했으나 각5개 메타파일뿐이고 원문 본문을 찾지 못했다. 허용 native 캐시와 준비 코드의 streaming/토큰 배열 저장 경로도 대조했다. 탐색 범위와 한계를 별도 보고서에 기록했으며 저장소 전체에 원본이 없다고 단정하지 않는다. 선택9/선택10미리보기는 여전히 캐시 미채택이며 최종 별도 캐시, 전량 재계측, 정본 연쇄, 최종 인계, 한국어 로컬 커밋은 미완이다.'),
 ('1', '이어받을 지점', '동일 Luna 다섯 역할의237 검토와 후속 판정표를 실제 수집해 미저장/기계거절/NEEDS_ROOT가 남지 않도록 처리한다. 최신 본문의 원문/본문/판독표 SHA를 연결하고 코드/Unicode/수치/부정/조건/출처/EOF 경고를 실제 구간으로 중재한다. 71604 손상 코드 보류,1254536 API 식별자 손실과 호출 보류,51521 명시 코드포인트 복구는 전역 보호 완화 없이 정확 구간과 근거를 핀한다. 자료에 없는 수식이나 연도를 만들지 않는다. 원문 폴더 탐색에서는 보호 TinyDataset과 타 세션 전용 자료 및 평가 사례를 열지 않았고 다운로드도 하지 않았다. 남은 큰 유형의 반복/필드/분류에 좁은 근거 정책을 적용하고 전체 P 보존 계수를 대조한다. 최종 캐시는 baseline 보존,3421 재검토,개별 선택,중복과 train-val,EOS/토크나이저/직렬화/문서경계를 실제로 닫는다. 대표237은 작업 상한이 아니다. 추가300M/GPU/모델/학습은 미허가다.'),
 ('2', '작업 내용', '상대 공개13:52의 소유 GPU/커밋 종료와 index 비움이 최신 확인 상태이며 새 잠금/중단 요청은 없다. 타 세션 전용 자료/원장/프로세스는 열거나 수정하지 않았다. 우리 수집/본문 감사는 순차 CPU1로 종료했고 현재 장시간 CPU/GPU는0이다. 후속은 동일 Luna 다섯 역할의 지정 원문 판독과 총괄 중재다. 원문 탐색은 작업 폴더의 허용 경로 메타데이터와 준비 코드 읽기만 했으며 외부 다운로드0이다. 우리 Git/index/공유 정본 변경0, 중단/잠금 요청0이고 최종 캐시와 로컬 커밋은 아직 미완이다.')
]
for item, field, after in updates:
    rows = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **' + item + '** |')]
    assert len(rows) == 1
    before = rows[0].split('|')[{'작업 내용':4, '이어받을 지점':6}[field]].strip()
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/wip.py'), '--override', '--file', str(ledger),
        '--item', item, '--field', field, '--expect-before', before, '--set-after', after,
        '--reason', '사용자 원문 폴더 탐색 지시와 실제 저장본문 감사 및 판독표 미결 회수 기록',
        '--approval-ref', '현재 잔여460695 전량 정제 goal과 첨부 CPU 코드 시험 문서 허가'],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, 'CAS complete')
stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
lines = ['', '', '## ' + stamp + ' — 원문 위치 탐색과 저장 본문 감사', '',
    '사용자 원문 위치 탐색 지시로 위키백과/FineWeb HF 원천4곳과 허용 native 경로/준비 코드를 확인했습니다. 해당4곳은 총20개 메타파일뿐이며 추출 전 본문은 찾지 못했습니다. 보호 데이터/귀 전용 자료/평가 사례는 열지 않았습니다.',
    '수집43/계획20은 실제0으로 종료했습니다. 최신 저장 본문824개를 CPU1로5.249초 실제0 대조했고 파일 오류0이나 호출/코드/문자/수치 진단은 개별 중재 중입니다. 마지막237 판독과 표 회수를 계속하며 캐시 채택0/공식 부분H160219 유지입니다.',
    '현재 장시간CPU/GPU0이며 다음 작업도 순차CPU1입니다. 우리 Git/index/공유 정본 변경0, 중단/잠금 요청0입니다. 추가300M은 미허가이고 최종 캐시/로컬커밋은 미완입니다.', '']
with (ROOT / 'tmp/COORD_HOLD_01a17740.md').open('a', encoding='utf-8') as stream:
    stream.write(chr(10).join(lines))
print('own public coordination appended')
