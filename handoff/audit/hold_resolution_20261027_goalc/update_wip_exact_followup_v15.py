"""Update the owned ongoing row through the normal compare-and-set WIP API."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import wip


def main():
    ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
    payload = ledger.read_text(encoding='utf-8')
    assert '01a17740-f435-7243-874c-2b5d58181c4c' in payload[:5000]
    table = wip.parse_table(payload)
    rows = {ident: cells for _, ident, cells in table.rows}
    assert rows['1'][2] == '🔄진행'
    assert all('완료' in rows[ident][2] for ident in ('2', '3', '4', '5'))
    names = [
        'RESUME_PROGRESS_AND_SPEED_20261103_V1.md',
        'REVIEWED_PARTIAL_V3_VERIFIED_METRICS_V1.json',
        'HOLD_STATUS_AND_EXCLUSION_RATIONALE_20261103_V2.md',
        'OUTPUT_HEADING_80_BINDINGS_VERIFIED_V2.json',
        'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V5.json',
        'LITERAL_SAVED_ROW_PROGRESS_OBSERVATION_V1.json',
        'WORKING_COPY_HISTORY_INCIDENT_RECONCILIATION_V1.json',
        'EXACT_PAGE_REVIEW_FIELD_001_V4.json',
        'EXACT_PAGE_REVIEW_FIELD_002_V4.json',
        'EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V6.json',
    ]
    for name in names:
        assert (AUDIT / name).is_file(), name
    note = (
        '사용자 재개 지시 아래1번RUN으로 전체 정제를 계속한다. 관리goal은08:02UTC조회에서blocked였고 원인은미확인이나 실제 승인대기/외부막힘은없다. '
        '공식cache3의 실제생성/독립consumer/전체계측은완료했지만 전량내용복구 완료는아니다. 원래H460695중350522처리/H110173이며 잔류는개별검토38/미처리110135위치·70192고유다. '
        'literal snapshot14는1793중1716저장/77미저장,1668본문후보/48중재·연결오류0이다. 네역할1차저장전량과별도로옛중재를새review에연결한다. '
        'field page001v4는146/512저장, page002v4는한글102/512저장으로해당역할전량이며페이지전체완료는아니다. '
        'field18237/36페이지와other50162/98페이지는native/reader준비만완료했다. 현재공식미처리의보호제외70191고유/110134위치는읽기준비됐고보호1건은metadata만유지한다. '
        '출력열표기오인식80행은리뷰바이트그대로본문SHA연결을회복했고7회귀0이다. '
        '독립의미검토는585flag중9건판독/576미판독,오류5건모두새수정본문재독·특정보존검산을마쳤으나새선택/캐시에는미반영이다. 출생2743의독립2차전량검토도미완이다. '
        '신규저장증가율은비슷한5시간구간186→155행/시간이며재수정은증가량밖이다. 총괄의중복판독/반복질의/경로대기를진행로그·정확별칭·115명령으로줄였다. '
        '최근한국어커밋767f408e는555명시경로/5215959바이트검산이며이후작업은미커밋이다. 전체own-clean을주장하지않는다. '
        'controls옛working v2두건의수정전바이트는미검증이고현재사본/원문/선택v3검산근거는보존한다. '
        'GPU/모델/학습/추가300M/원형덮기삭제/보호TinyDataset/타세션전용자료/push/PR은금지다.'
    )
    resume = (
        'controls literal TASK072전부와다섯역할의옛중재정확review연결을마친다. 역할별field36페이지의각TASK전부와other98페이지전부를순차수행한다. '
        '총괄은동일규칙의반복재승인을없애고새로운실제근거충돌만중재하며원문SHA/새본문/sidecar·코드/숫자/귀속/한정을검산한다. '
        '585flag의나머지576건과출생독립2차의미검토를계속하고검토가끝난선택만새ROOT/roster/캐시·독립consumer·전량계측으로연결한다. '
        '기존5오류수정과현재미커밋소유변경을추적해명시작은코드/문서/감사근거/WIP를한국어로컬커밋하고대량본문은SHA색인으로연결한다. '
        '정본연쇄/최종핸드오프/로컬저장까지A–E전부충족해야완료다. 중간저장·부분캐시·압축은정지/일시중지사유가아니다.'
    )
    values = {'작업 내용': note,
              '산출물': '; '.join(str((AUDIT / name).relative_to(ROOT)) for name in names),
              '이어받을 지점': resume}
    indices = {'작업 내용': 3, '산출물': 4, '이어받을 지점': 5}
    for field, after in values.items():
        wip.override_field(ledger, '1', field, rows['1'][indices[field]], after,
                           '재개 후 실제 수집/의미검토/속도 근거와 관리goal표시 불일치를 현재 진행행에 반영',
                           '현재 사용자 중단 작업 재개 및 전체 잔여 HOLD 완료까지 수행 지시', False)
    result = {'status': 'THREE_NORMAL_WIP_API_CAS_UPDATES_COMPLETED',
              'ledger': str(ledger.relative_to(ROOT)),
              'ledger_sha256': hashlib.sha256(ledger.read_bytes()).hexdigest().upper(),
              'state': 'RUN', 'closed_items_reopened': 0, 'goal_marked_complete': False}
    out = AUDIT / 'WIP_EXACT_FOLLOWUP_V15_APPLIED.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
