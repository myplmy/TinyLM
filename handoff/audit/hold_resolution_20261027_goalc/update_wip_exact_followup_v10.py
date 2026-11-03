"""Record actual cache3 validation and all residual queues without closing the goal."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

metrics_path=AUDIT/'REVIEWED_PARTIAL_V3_VERIFIED_METRICS_V1.json'
metrics=inv.cache.read(metrics_path)
assert metrics['remaining_hold']==110173 and metrics['unprocessed_unique']==70192
assert metrics['accepted_total']['documents']==1372548
for name in ['CACHE_REVIEWED_PARTIAL_V3_PROCESS_EXIT_V1.json','CACHE_REVIEWED_PARTIAL_V3_VERIFY_EXIT_V1.json',
             'REMAINING_FIELD_TITLE_NATIVE_PROCESS_EXIT_V1.json']:
    assert inv.cache.read(AUDIT/name)['process_exit_code']==0
snapshot=inv.cache.read(inv.BASE/'remaining_literal_full_counter_v1_snapshots/v7/complete.json')
assert snapshot['errors']==[]
work=(
    '전체 정제 goal active,1번 RUN이다. cache_reviewed_partial_v3의 실제 CPU 생성0/별도 독립consumer0과 전체계측을 확인했다. '
    '원래H460695위치 중K32187/E195071/X123264/H110173이며 개별 검토H38/미처리110135위치(70192고유)를 분리한다. '
    'v2보다H5353위치 감소,채택1372548문서/EOS포함1066879306IDs/본문1065506758IDs다. '
    '기준1145290본문 보존·채택 전량 재생성·문서경계/EOS/직렬화·파일20MB미만·정확본문중복0·trainval정확본문교집합0은 실제 검증 범위다. '
    '중간v2후보 전체 불변은 아니며 오채택 철회/수량복구를 기록했다. 출처UNKNOWN/근접·이동구간·URL누설 미확인은 유지한다. '
    '원래H 제외123264는 정확중복123177/개별문맥84/원형경계3위치이며 불량 확정과 중복을 섞지 않는다. '
    '동일 채택목록의 empty/adjacent-heading신호154218→52,wiki-opener590→82이나 정상 코드/인용도 포함하는 탐지신호다. '
    '출생2743 전량 저장·ROOT11선택7857·코드/Unicode/memo실패0은 중간 근거이며 출생 별도2차 전문판독은 미완이다. '
    'literal snapshot7은1793중920행 저장/873미저장,873본문후보와47중재이며 채택이 아니다. 잘못된 TASK와ID의 리뷰5행은 근거에서 제외하고 정정 중이다. '
    '미처리70192고유는 현재 literal1792+미배정68399+보호metadata1로 전량 census했다. '
    '다음 필드/제목18237고유/29659위치/36페이지는 native복원과 동결후보 재생성 전량 일치0이며 실제 문맥 판독은 별도다. '
    '보호7부모/동일SHA11위치는 metadata/승인safeview만 사용했고 부모본문decode0이다. '
    '최근 한국어 로컬 저장a1bc5a4c 이후 작업은 새 저장 전이다. 전체 정제·독립의미검토·정본연쇄·최종핸드오프는 미완이며 추가300M/GPU/모델/학습/push/PR금지다.')
resume=(
    '다섯 Luna는 자기 literal TASK072까지 전량 판독을 계속하고 총괄 중재를 정확 새리뷰로 연결한다. '
    '필드/제목18237의 36페이지 전량을 기존 전문 판독 준비기로 packet화하고 controls고정reader와 동일입력 전문재구성 계획을 준비한다. '
    '현재 배정을 마친 역할부터 다음 정확 페이지를 순차 배정하며 작은 페이지를 전체 작업량 한도로 삼지 않는다. '
    'root는 남은 좁은 문맥 중재·ID/TASK/본문/sidecar/pin·오삭제/숫자/주체·독립2차 검토를 수행한다. '
    '모든 남은 유형을 별도 출처연결과 실제 판독으로 계속 처리하고 미판독을 종결HOLD로 이름만 바꾸지 않는다. '
    '새 선택이 확정되면 새 캐시를 생성/별도독립검증/전체계측하며 기존 검증 캐시는 보존한다. '
    '한국어 명시 소유 로컬 커밋을 저장하되 중간 캐시·저장·압축은 goal정지/일시중지 사유가 아니다. A–E가 모두 충족할 때만 완료한다.')
names=['REVIEWED_PARTIAL_V3_VERIFIED_METRICS_V1.json','HOLD_STATUS_AND_EXCLUSION_RATIONALE_20261103_V2.md',
       'CACHE_REVIEWED_PARTIAL_V3_PROCESS_EXIT_V1.json','CACHE_REVIEWED_PARTIAL_V3_VERIFY_EXIT_V1.json',
       'REMAINING_FIELD_TITLE_NATIVE_PROCESS_EXIT_V1.json','REMAINING_FIELD_TITLE_READERS_SCOPE_V1.md']
links='; '+'; '.join(str((AUDIT/name).relative_to(ROOT)) for name in names)
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
for field,value in {'작업 내용':work,'산출물':links,'이어받을 지점':resume}.items():
    rows=[line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(rows)==1
    before=rows[0].split('|')[{'작업 내용':4,'산출물':5,'이어받을 지점':6}[field]].strip()
    after=before+value if field=='산출물' else value
    result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override',
        '--file',str(ledger),'--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','cache3 실제 생성/독립소비자0과 전량 미처리 census·필드준비를 구분해 기록',
        '--approval-ref','사용자 전체 잔여HOLD 지시 및 objective CPU/파생캐시/문서/한국어로컬저장 허가'],
        cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout,result.stderr)
        raise SystemExit(result.returncode)
    print(field,'CAS 완료')
