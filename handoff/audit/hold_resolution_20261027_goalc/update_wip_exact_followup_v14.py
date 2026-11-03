"""Reuse the CAS writer and keep newly found semantic defects visible."""
from pathlib import Path

source=Path(__file__).with_name('update_wip_exact_followup_v13.py')
text=source.read_text(encoding='utf-8')
marker="exec(compile(code, str(source), 'exec'), {'__file__': __file__, '__name__': __name__})"
assert text.count(marker)==1
environment={'__file__':__file__,'__name__':'prepare_current_cas_values'}
exec(compile(text[:text.index(marker)],str(source),'exec'),environment)
code=environment['code']
changes={
 'literal snapshot10은1793중1476저장/317미저장,1399본문후보/77중재이며 연결오류0이다. 저장행을채택이나전량내용판독 완료수로바꾸지않는다.':
 'literal snapshot11은1793중1546저장/247미저장,1492본문후보/54중재이며기계연결오류0이다. 저장/중재행을채택이나전량내용판독완료수로바꾸지않는다. legacy360과한글356의첫전량저장·옛보완연결후둘은field로진행하며다른셋은literal72까지계속한다.',
 'field page001 snapshot1은512중78저장/434미저장/연결오류0이며채택이아니다.':
 'field page001 snapshot2는512중85저장/427미저장/기계연결오류0이며채택이아니다. 잘못된review006의타TASK두행은과거무효증거로보존하고정확4934/4939를새전문판독·새review006으로연결했다. 현재미결0은그512중저장된85행의상태일뿐이다.',
 'ROOT11의7857선택/출생2743저장은중간근거이며585순서문자flag와출생독립2차전문검토는미완이다.':
 'ROOT11 독립의미검토는585flag중9원문/본문/전체diff실제판독,576미판독이다. 기존선택5건의오삭제/귀속/한정오류를찾아3새수정본을재독·정적검산했고출생프로필2건은Luna보완중이다. 수정3건도새ROOT/roster/캐시에아직미반영이며기존캐시3의구조0을의미완료로승격하지않는다. 출생2743의독립2차전량검토도미완이다.',
 '그뒤새중재/작업은미커밋이다.':
 '그뒤snapshot11/field2/개별전문판독HOLD7/독립의미검토9와3수정·2보완/소유작업사본이력대조/모든other후속권한은미커밋이다.',
 '미응답질문805860과gmtime실패조건715858의오삭제를발견해새버전복원을지시했고,완결된버그코드·질문·자료귀속은불량으로삭제하지않도록재검토중이다.':
 '미응답질문805860/gmtime실패조건715858/정상feature목록768125의오삭제를새버전으로복원했고원저자버그/인용·TODO를오류나검수메모로자동삭제하지않는다. controls파생v2두건의수정이력은현재사본을새보존했고원문/후보·선택v3 SHA일치를검산했으나수정전v2바이트는아직미검증이다.',
 '다음한국어중간저장은명시작은코드/문서/감사근거/WIP만저장하고대량본문은SHA색인으로연결한다.':
 '다음한국어중간저장은현재9d536a9e를부모로명시작은코드/문서/감사근거/WIP만저장하고대량본문은SHA색인으로연결한다. 독립검토에서찾은문제·새수정3건·진행중출생2건은새선택/캐시까지추적한다.',
 "names = ['EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V5.json',":
 "names = ['ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V4.json', 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V1.json', 'WORKING_COPY_HISTORY_INCIDENT_RECONCILIATION_V1.json', 'OTHER_TYPES_PHASE_EXACT_AUTHORIZATION_V1.json', 'EXACT_PAGE_REVIEW_FIELD_001_V2.json', 'EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V5.json',",
}
for before,after in changes.items():
    assert code.count(before)==1,before
    code=code.replace(before,after)
exec(compile(code,str(source),'exec'),{'__file__':__file__,'__name__':__name__})
