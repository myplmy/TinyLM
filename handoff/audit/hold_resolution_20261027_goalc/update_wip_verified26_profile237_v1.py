"""CAS the live ledger with actual26 verification and still-open source work."""
from pathlib import Path
import datetime
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
assert '01a17740-f435-7243-874c-2b5d58181c4c' in ledger.read_text(encoding='utf-8')
receipt = json.loads((AUDIT / 'DRAFT_V26_DELTA_EXECUTION_RECEIPT_V1.json').read_text(encoding='utf-8'))
assert receipt['unique_sources_checked'] == 297539 and receipt['fresh_native_source_pairs'] == 27
assert receipt['occurrence_counts']['PENDING'] == 122534 and receipt['unique_counts']['PENDING'] == 77639
snapshot = json.loads((AUDIT / 'supplemental_candidates_snapshot_v42.json').read_text(encoding='utf-8'))
assert snapshot['coverage']['root_selected_lexical_counter_v1']['saved'] == 579
assert snapshot['coverage']['ordinal_metadata_counter_v26_v1']['saved'] == 27
updates = [
 ('1', '작업 내용', '진행: 공식검증부분cache H160219는그대로이며최종정제/학습재개완료가아니다. 전량25의실제종료/독립검증과부분ledger대조2/profile25는기존영수증으로닫혔고3421재검토는P2521/다른종결본문900이다. 새26증분은기존25를상속하며원문전량26재실행이라고부르지않는다. producer93613의실제270c13/0·28.232초와별도검증94492의실제c39d64/0·18.834초가닫혔다. 전체297539고유중297512행은옛JSON그대로이고변경27원문을양쪽에서토큰으로다시읽어EOS/UTF8/SHA와26판정/이유/수정/본문을대조했다. 모든460695위치/462874291원inputIDs/중복횟수/분할/구간을보존하며66생산코드는불변이다. 초안은K49463/E288695/X3/P122534위치,고유K31277/E188620/X3/P77639이고cache채택0이다.26만으로26고유/51위치의경계보류를해소했으며상충생년1건은P유지다. snapshot42 실제9f085e/0와plan19 실제7fa6bc/0: main579와ordinal27검토행은전부저장됐으나main978970선언불일치와670434미결리뷰잔류를수정회수해야한다. 새237은snapshot시점117저장/120미저장이고이후저장중이다. plan19는합집합3377원문/5230제안을연결하고미저장을명시보류하여옛본문우회를금지한다. 새237은기존유형238대표중ordinal중복1을제외해전량원문을재생성한것이며실제e59443/0·12.856초로모든25진단을재현했다.952뷰와237TASK색인도실제0으로원문/후보전체를재구성했다. 배정은controls28/hangul53/latin70/historical28/structure58이고같은Luna5만판독한다. 최신root선택9는3116원문으로미채택이며preview10은2917선택/223중재미결이다. 최종cache/재계측/정본연쇄/최종인계/한국어localcommit은미완이다.'),
 ('1', '이어받을 지점', 'snapshot42의두main결함978970(ACCEPT선언과빈각주제거본문불일치),670434(본문v2는있으나최신판정표미저장)를해당Luna의새표로회수한다. 새237의각TASK판독과미결중재를계속하며현재root질문461104접촉형식/audit수학조건,471905음향,577734누락목록/학술서지,681502Strennic대조범위,916339빈예선표제,99120빈수식표제,502163유효라벨값과범위,5473빈도표표제등은정확원문을확인하여독립완결정보를보존하고직접결손부분만hold한다. main/ordinal/237의수정과전량배정누락을새collector/plan에항상명시한다. 선택10의새본문충돌은source/body/review전SHA와총괄근거를핀해중재하고옛선택9를우회채택하지않는다. 코드/Unicode/수치/부정/조건/메모/EOF를독립대조하며실제결손코드가hold로분리된71604와명시문자복구51521은정확구간과근거를별도로연결한다. 모형지식으로수식/연도를생성하지않고전역보호완화도하지않는다. 대표237은전체작업상한이아니며이후전량P의반복/필드/분류등큰유형에좁은근거있는정책을적용하고새전량상태를검산한다. 최종별도cache는baseline보존/3421재검토/개별선택/중복과train-val/EOS/토크나이저/직렬화/문서경계를실제로닫고전량재계측/필요정본/최종인계/한국어localcommit까지계속한다. 추가300M/GPU/모델/학습은미허가다.'),
 ('2', '작업 내용', '상대공개13:52의소유GPU/커밋/인계종료와index비움이최신이며새중단/잠금요청은없다. 타세션전용자료/원장/프로세스는열거나수정하지않는다. 우리26증분28.232초와별도검산18.834초는순차CPU1로실제0종료했고새237원문재생성/952뷰/TASK색인도종료했다. 현재장시간CPU0,동일Luna5의지정237원문판독과총괄수집/중재를계속한다. 우리GPU/모델/학습/설치/외부쓰기/Git/index/공유정본변경0,중단/잠금요청0이다. 추가300M미허가와최종캐시미완을자기공개tmp에도갱신한다.')
]
for item, field, after in updates:
    rows = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **' + item + '** |')]
    assert len(rows) == 1
    before = rows[0].split('|')[{'작업 내용': 4, '이어받을 지점': 6}[field]].strip()
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/wip.py'), '--override', '--file', str(ledger),
        '--item', item, '--field', field, '--expect-before', before, '--set-after', after,
        '--reason', '실제26증분독립검산및57927저장과새237미저장명시상태회수',
        '--approval-ref', '현재잔여460695전량정제goal및첨부목표CPU코드시험문서허가'],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, 'CAS complete')
stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
lines = ['', '', '## ' + stamp + ' — 26 증분 독립 검산 종료와237 원문 판독', '',
    '우리26증분은검증된25를상속하고변경27원문만새로읽은CPU1이며28.232초/실제0종료했습니다. 독립검산18.834초/실제0은나머지297512JSON행불변과변경27의실제토큰/EOS/UTF8/SHA/판정및460695위치전행을확인했습니다. 새초안P122534는캐시채택이아니고공식부분H160219는그대로입니다.',
    '새유형대표237원문/후보재생성12.856초와952순서뷰/237TASK색인도종료했습니다. 기존579/ordinal27행은전부저장됐으나선언2건보완과새237판독은진행중입니다. 현재장시간CPU/GPU0이며다음수집/검산도순차CPU1입니다.',
    '귀13:52소유GPU/커밋종료/index비움을확인했고귀전용자료/원장/프로세스에관여하지않습니다. 우리Git/index/공유정본변경0,중단/잠금요청0입니다. 최종cache/정본/로컬커밋과추가300M실행은아직미완/미허가입니다.', '']
with (ROOT / 'tmp/COORD_HOLD_01a17740.md').open('a', encoding='utf-8') as stream:
    stream.write(chr(10).join(lines))
print('own public coordination appended')
