"""Persist exact current receipts while keeping the whole cleaning goal active."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

receipt = inv.cache.read(AUDIT / 'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V15.json')
for row in receipt['rows']:
    assert row['process_exit_code'] == 0
    assert inv.file_sha(ROOT / row['snapshot']['path']) == row['snapshot']['sha256']
preview = inv.cache.read(AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW3.json')
assert preview['source_ids'] == 8080 and preview['cache_admitted'] == 0
guard_path = AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V7.json'
guard_state = 'ROOT11 preview3의실제전체guard재검사중이다.'
if guard_path.exists():
    guard = inv.cache.read(guard_path)
    assert guard['input_pins'][str((AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW3.json').relative_to(ROOT))] == inv.file_sha(AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW3.json')
    guard_state = 'ROOT11 preview3 guard의실제계수=' + json.dumps(guard['counts'], separators=(',', ':')) + '이며의미완료/캐시채택은아니다.'
work = (
    '전체goal active·1번RUN이다. 현재공식cache_reviewed_partial_v2는실생성0/독립소비자0의기존증거이며 '
    '원래H460695중K31985/E191835/X121349/H115526위치, 미반영잔여73668고유이다. '
    '채택1369110문서·정확중복0·trainval본문교집합0·기준1145290본문보존은이공식v2범위이고출처UNKNOWN/근접·URL누설미확인을유지한다. '
    '스냅샷15의반복732교차독립판독은전량저장/결합오류0이며과거4개반려이력은보존한다. '
    '출생2743은2666저장/77미저장,2630본문과36개개별검토HOLD이고현재기계결합오류0이다. '
    'literal1793은310저장/1483미저장,300본문과10개질문상태이다. 그중1046282는root전문중재HOLD로승인했다. '
    '기존ROOT10수량26의전량재판독은25본문·1255247선택철회HOLD이며나이/기간/공통날짜/서지복구를포함한다. '
    'glossary574329의182표제복구/기존34보존/UI23줄·고립pipe1문자분리와기타비빈원문줄변경0의전체증명은보존한다. '
    'ROOT11 preview3는8080고유의K1080/E6914/X48/H38,16059692바이트이고새캐시채택0이다. '
    'H38은기존무명36+HLT미리보기1+이전잘못채택1의정확개별검토이며미판독개명이아니다. '
    '기존4381외반복732/출생2666/literal301선택을연결했고별도현재배정미선택1569건은그대로기록했다. '
    'preview1압축중일부original경로누락을v2로보정했고,v2의이전스냅샷에는TASK085의Luna손상본문3개가있었다. '
    'guardv6의실제7961검사에서UTF8실패738526/739125/741129세개를확인해채택하지않았고,다른7872본문코드/Unicode통과·memo0·기존정확style14쌍일치를확인했다. '
    'Luna의새v2복구를수집한snapshot15/preview3로다시검사한다. ' + guard_state +
    ' 새HOLD구분helper11시험과동일입력판독helper11시험은각실제0이다. '
    'cachev3보호runtime초기화도실제0/91경로pin/검토비채택38이지만새build·독립consumer는NOT_RUN이다. '
    '동일바이트1675건은원문전문실제판독을유지하고후보중복3999패킷만증명연결하며118비동일쌍은양쪽전문을읽는다. '
    '새v2계획360개/증명은완료했고set직렬화실패v1은보존한다. '
    '과거숫자89표시중51국소원자증명+38표시15고유/19쌍개별중재를연결했으며새preview전체의수치/순서종결은아니다. '
    '실제코드의주석·들여쓰기·문자열행이소실된예제는비공백토큰동일만으로재작성하지않고손상의존단위를원형HOLD한다. '
    '실제서지·강의개요·조건부관찰은보존하고잘못된수용/전사/리뷰근거를새버전으로고친다. '
    'Ryti688560은실제SKS출판PDF의생몰일과대통령실선거표의연도만정정했고,1300527의소실기호는같은출판3.6절과저자PDF로대조해Luna복구중이다. '
    'controls과거unscopedrg실제접근범위미확인은유지하고,반복경로오류는정확reader명령17TASK목록으로줄인다. '
    '모든실패/옛초안/불선택본문은보존하고상세는FAILURES_V8에연결한다. '
    '최신로컬커밋26b4923d080a952652444637235e9f5b2c3633b6은1248명시경로10641330바이트의당시저장이다. '
    '그이후현재코드·판독·WIP는새커밋전이며current-own-clean이라고주장하지않는다. '
    'ROOT11최종승인/새캐시/나머지유형전량/최종계측/정본연쇄/최종핸드오프는미완이고추가300M금지·학습사용자소유를유지한다.')
resume = (
    '출생controls는정확reader TASK097이후110까지완수하고그뒤본인literal357건을이미준비된고정reader/identityV2로전량진행한다. '
    '다른네역할은자기literal TASK072끝까지계속하고정확히답하지못한문장/코드경계만질문한다. '
    '총괄은guardV7에서UTF8복구3건을확인하고필요시새스냅샷/preview버전으로재검사,기존style14정확쌍과신규숫자·원형순서표시를검토한다. '
    'ROOT11의실제선택범위와현재배정미선택/전체잔여를구별해최종선택을닫고새roster에서HOLD38검토완료와미처리를분리한다. '
    'guarded_reviewed_cache_v3의새roster/cache를실생성하고독립consumer와전체계측을수행한다. '
    '실행중캐시를완료로말하지말고모든실제종료코드/실패를보존한다. '
    '잔여73668고유의다른유형도전체추적·문맥판독·정제를계속하고A–E전체충족때만goal완료한다. '
    '중간저장·부분검증은goal정지/일시중지사유가아니다. 새아티팩트20MB미만·원본/이전캐시/보호TinyDataset/타세션전용자료보호·GPU/모델/학습/push/PR금지유지.')
names = ['EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V15.json', 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW3.json',
    'EXACT_SELECTION_RUNTIME_GUARDS_V6.json', 'ROOT_REVIEWED_TERMINAL_HOLD37_V1.json',
    'EXACT_NUMERIC_CONTEXT_CLEARANCES_V1.json', 'REVIEWED_HOLD_PARTITION_TEST_RESULT_V1.json',
    'CACHE_V3_RUNTIME_INITIALIZATION_V1.json', 'IDENTICAL_LITERAL_INPUT_READING_PROOFS_V2.json',
    'IDENTICAL_INPUT_READING_TEST_RESULT_V1.json', 'CONTROLS_EXACT_REMAINING_COMMAND_PLANS_V1.json',
    'RESUME_PREPARATION_FAILURES_V8.md']
if guard_path.exists(): names.append(guard_path.name)
links = '; ' + '; '.join(str((AUDIT / name).relative_to(ROOT)) for name in names)
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
for field, value in {'작업 내용':work, '산출물':links, '이어받을 지점':resume}.items():
    lines = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(lines) == 1
    before = lines[0].split('|')[{'작업 내용':4, '산출물':5, '이어받을 지점':6}[field]].strip()
    after = before + value if field == '산출물' else value
    proc = subprocess.run([sys.executable,'-I','-B',str(ROOT / 'scripts/wip.py'), '--override',
        '--file',str(ledger),'--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','실제스냅샷15·UTF8반려3개·ROOT11새preview와계속정제상태를연결',
        '--approval-ref','사용자 전체 잔여 HOLD 정제 지시 및 objective의 CPU·문서·로컬저장 허가'],
        cwd=ROOT,text=True,capture_output=True)
    if proc.returncode:
        print(proc.stdout,proc.stderr)
        raise SystemExit(proc.returncode)
    print(field, 'CAS 완료')
