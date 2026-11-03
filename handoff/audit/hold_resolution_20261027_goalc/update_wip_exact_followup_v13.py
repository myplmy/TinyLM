"""Reuse CAS ledger updates for the new saved checkpoint and actual page snapshot."""
from pathlib import Path

source = Path(__file__).with_name('update_wip_exact_followup_v12.py')
code = source.read_text(encoding='utf-8')
replacements = {
    'literal snapshot9는1793중1296저장/497미저장,1232본문후보/64중재이며 채택이나전량판독 완료수가 아니다.':
    'literal snapshot10은1793중1476저장/317미저장,1399본문후보/77중재이며 연결오류0이다. 저장행을채택이나전량내용판독 완료수로바꾸지않는다.',
    '다른유형50162 native준비 실제0(2117초)/전량일치 및98페이지읽기준비3단계실제0을회수했다.':
    '다른유형50162 native준비 실제0(2117초)/전량일치 및98페이지읽기준비3단계실제0을회수했다. 해당새396944파일모두20MB미만/최대3621781바이트를검산했다. field page001 snapshot1은512중78저장/434미저장/연결오류0이며채택이아니다.',
    '한국어저장42ca61d0의2143명시경로/부모/blob/index0검증후생긴작업은미커밋이다.':
    '한국어저장9d536a9e의3239명시경로/48211965바이트·부모/전체blob/공유index0을실제검증하고Git창을닫았다. 그뒤새중재/작업은미커밋이다.',
    '총괄은DDI/Angular/PEP/ROUND/random/인용부호/SDL이름의원문·발행처근거를제공하고Luna만새본문을작성한다.':
    '총괄은DDI/Angular/PEP/ROUND/random/인용부호/SDL/ConfigHosts10표제/공식R예제/구판Perl/Excel4식의원문·발행처근거를제공하고Luna만새본문을작성한다. 한글옛미결17의동일원문/후보사본34개와새working17개를검산했다. 1046282기검토1포함으로발생한사본준비v1의사전assert실패는보존하고v2실제0으로정정했다.',
    '전량native준비실제0과미완의미검토및오삭제정정범위를구분':
    '전량읽기준비와현재리뷰/명시커밋9d536a9e및미완의미검토를구분',
    "names = ['ALL_NONRESTRICTED_NATIVE_PREPARATION_STATUS_V1.json',":
    "names = ['EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V5.json', 'EXACT_PAGE_REVIEW_FIELD_001_V1.json', 'REMAINING_OTHER_TYPES_READER_PREPARATION_VERIFIED_V1.json', 'HANGUL_LITERAL_REOPEN_EXACT_COPIES_V1.json', 'ALL_NONRESTRICTED_NATIVE_PREPARATION_STATUS_V1.json',",
}
for before, after in replacements.items():
    assert code.count(before) == 1
    code = code.replace(before, after)
exec(compile(code, str(source), 'exec'), {'__file__': __file__, '__name__': __name__})
