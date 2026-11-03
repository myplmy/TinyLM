"""Record actual preparation exits while leaving full semantic work active."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

ready = inv.cache.read(AUDIT / 'ALL_NONRESTRICTED_NATIVE_PREPARATION_STATUS_V1.json')
assert ready['official_unprocessed_nonrestricted_unique_with_native_proof'] == 70191
assert ready['official_unprocessed_restricted_metadata_only_unique'] == 1
for name in ('REMAINING_OTHER_TYPES_NATIVE_PROCESS_EXIT_V1.json', 'OTHER_TYPE_READING_PREPARATION_PROCESS_EXIT_V1.json'):
    assert inv.cache.read(AUDIT / name)['process_exit_code'] == 0
readers = inv.cache.read(AUDIT / 'LITERAL_ROLE_FIXED_READERS_VERIFIED_V2.json')
assert len(readers['roles']) == 4
assert all(row['actual_cli_exit_code'] == 0 and row['actual_other_role_rejected'] for row in readers['roles'])
work = (
    '전체 정제 goal active/1번RUN이다. 공식 cache_reviewed_partial_v3 실제생성0/독립consumer0/전체계측은 완료했지만 전체정제 완료가 아니다. '
    '원래H460695 중K32187/E195071/X123264/H110173이며, 공식H는 개별검토38/미처리110135위치(70192고유)다. '
    '채택1372548문서/EOS포함1066879306IDs/본문1065506758IDs, 기준1145290본문보존·전량재생성·EOS/경계/직렬화·정확중복0/trainval정확교집합0을 확인했다. '
    '원래H 제외123264는정확중복123177/문맥84/원형경계3이다. UNKNOWN출처와근접/이동/URL누설미확인, 추가300M학습금지를 유지한다. '
    'literal snapshot9는1793중1296저장/497미저장,1232본문후보/64중재이며 채택이나전량판독 완료수가 아니다. '
    '한글literal356의첫저장은끝났으나옛중재17보완이남는다. 나머지역할은literal72까지계속한다. '
    '필드18237의native일치/36페이지/91524파일20MB미만 검산과 전체TASK색인을 만들었다. 첫TASK만읽고다음페이지로뛰는오류를발견해한글page001의21TASK전부로교정했다. '
    '다른유형50162 native준비 실제0(2117초)/전량일치 및98페이지읽기준비3단계실제0을회수했다. '
    '현재미처리중읽기준비완료는보호제외70191고유/110134위치이며 보호1고유/1위치는metadata만유지한다. 준비70192에는이미검토한1046282가포함되므로공식미처리70192와같은집합이아니다. '
    'HANGUL역할의필드3724원문16784packet은정확동일byte별칭이고,네역할literal고정reader V2는경계/타역할거부/CLI0을검증했다. 경로실패는미판독으로유지한다. '
    '총괄은DDI/Angular/PEP/ROUND/random/인용부호/SDL이름의원문·발행처근거를제공하고Luna만새본문을작성한다. '
    '미응답질문805860과gmtime실패조건715858의오삭제를발견해새버전복원을지시했고,완결된버그코드·질문·자료귀속은불량으로삭제하지않도록재검토중이다. '
    'ROOT11의7857선택/출생2743저장은중간근거이며585순서문자flag와출생독립2차전문검토는미완이다. '
    '한국어저장42ca61d0의2143명시경로/부모/blob/index0검증후생긴작업은미커밋이다. 전체own-clean을주장하지않는다. '
    '최종정제·새선택/roster/캐시·독립의미검토·정본연쇄·최종핸드오프·한국어로컬저장은계속한다. GPU/모델/학습/원형덮기삭제/보호TinyDataset/타세션자료/push/PR은금지다.')
resume = (
    '다섯Luna의옛중재를새정확review로연결하고literal TASK072전부→field36페이지의각TASK전부→other98페이지전부를순차수행한다. '
    '총괄은누락수식/원문질문/코드단편과실제추출손상/숫자/인용/귀속과오삭제를중재하며원문SHA와새본문/sidecar를검산한다. '
    '585문자순서flag와출생독립2차의미검토를진행하고,현실검토가끝난選択のみ新ROOT/roster/별도캐시와독립consumer/전체계측으로연결한다. '
    '다음한국어중간저장은명시작은코드/문서/감사근거/WIP만저장하고대량본문은SHA색인으로연결한다. '
    '정본/최종핸드오프/로컬커밋까지A–E전부충족해야goal완료다. 중간저장·부분캐시·압축은정지/일시중지사유가아니다.')
resume = resume.replace('選択のみ新', '선택만새')
names = ['ALL_NONRESTRICTED_NATIVE_PREPARATION_STATUS_V1.json',
         'REMAINING_OTHER_TYPES_NATIVE_PROCESS_EXIT_V1.json',
         'OTHER_TYPE_READING_PREPARATION_PROCESS_EXIT_V1.json',
         'COMPLETE_FIELD_PAGE_TASK_INDEX_V1.json',
         'COMPLETE_OTHER_TYPES_PAGE_TASK_INDEX_V1.json',
         'FIELD_CONTEXT_HANGUL_EXACT_PACKET_ALIASES_V1.json',
         'LITERAL_ROLE_FIXED_READERS_VERIFIED_V2.json']
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
for field, value in {'작업 내용': work, '산출물': names, '이어받을 지점': resume}.items():
    lines = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(lines) == 1
    before = lines[0].split('|')[{'작업 내용': 4, '산출물': 5, '이어받을 지점': 6}[field]].strip()
    after = before + '; ' + '; '.join(str((AUDIT / name).relative_to(ROOT)) for name in value) if field == '산출물' else value
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/wip.py'), '--override',
        '--file', str(ledger), '--item', '1', '--field', field, '--expect-before', before,
        '--set-after', after, '--reason', '전량native준비실제0과미완의미검토및오삭제정정범위를구분',
        '--approval-ref', '사용자전체잔여HOLD정제및objective CPU/파생데이터/코드시험/문서/한국어로컬저장허가'],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(field, 'CAS 완료')
