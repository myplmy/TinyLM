"""Reuse complete-source framing for every remaining rare field/definition guard."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
instructions={
 'expanded_train:51521':'금석문자경이라는 실제 명칭과 코드/글리프 관계는 유지하고 그 이름 뒤의 빈()껍데기만 원형sidecar보류한다. 새코드번호·별칭·유니코드사실은 만들지않는다.',
 'expanded_train:1018113':'관계대수 연산의 실제 Select/Project/Union/Set Difference/Cartesian Product/Rename 이름과 정의된 p/R/K·closure 설명·실제 SQL예제는 보존한다. 비어있는 연산기호()와 집합식은 원형보류하고 껍데기만 제거한다. Formally defined as 뒤에 실제 정의식이 없으면 그예고만HOLD하며뒤의SQL예제를 누락수학식의정의라고 새로연결하지않는다. SQL코드/문법은정정하거나실행하지않는다.',
 'expanded_train:704845':'HyperJoy V2의실제모델명·번호·2003년7월출시·선곡가능성·PV·파라오케파라다이스라는실제채워진명칭과그기능·BB환경서비스조건·수상/후속모델정보는보존한다. 여러《》빈이름에직접기대는알수없는모드/기능대상을추측하지않고원형보류한다. 스튜디오녹음된미지의곡을새녹음기능이라고재해석하지않는다. 독립적으로식별되는실제이름과조건은문장으로완결한다.',
 'expanded_train:8925':'Object.GetHashCode()/Object.ToString()은실제로명명된메서드표기이며빈수식아니다. 실제API이름·오버로드·인수·서명과설명을그대로보존한다. 빈설명행에가까운다른메서드설명을임의로붙이지않는다. 코드실행/새서명생성금지. 현재후보의독립성이확인되면ACCEPT.',
 'expanded_train:55808':'말미0551/070890두숫자줄은원문에목록명·카탈로그명·번호역할과의연결이없어특정식별자를복원못한다. 숫자들을원형sidecarHOLD하고그두말미줄만제거한다. 천체실제명칭·분류·본문관측수치·출처는보존하며알려진카탈로그명이나숫자레이블을외부지식으로붙이지않는다.',
 'expanded_train:1411355':'defined as뒤에실제정의문이바로다음줄로이어지는hard wrap이다. 명목/실효보호정의의국내가격/세계가격·부가가치기준과조건을보존하고단순줄끝탐지를누락식으로오인해지우지않는다. 식·경제수치를새로계산하지않고현재본문보존가능하면ACCEPT.',
 'expanded_train:467565':'원문의클레바노프-위튼모형이라는실제명칭과이에대응하는4차원장론의초장표를직접대조한다. 모형명을앵커로보존하고명시된U(N)×U(N)게이지초장/손지기초장,맛깔SU(2)L/R표현1/1·2/1·1/2,딸림표현을관계가분명한짧은문장으로보존할수있다. 전량빈기호열과(N,)/(,N)의누락게이지성분은원형HOLD,없던기호·켤레표현·성분을채우지않는다. D3개수·초대칭범위는계속HOLD한다. 특히만약[공란]이라는84줄전제가없어졌으므로그전제에기대는FI모듈라이/변형단정도같이HOLD하고N값을추측하지않는다. 실제6차원코니폴드/5차원다양체/두SU(2)·U(1)대칭및역사는보존한다.',
 'expanded_train:4980':'첫메타데이터의1661년날짜는재위/즉위식이다. 실제출생일필드1654년5월4일과1654년출생분류는일치한다. 첫날짜정규식이재위일을출생으로오인한것을생년충돌이라고보류하지않고실제필드역할·날짜·본문귀속을그대로보존한다. 나이를계산하거나다른날짜를정정하지않는다.',
 'expanded_train:8132':'USER예제의(defun bar ()...)에서()는실제Lisp함수의빈인수목록이다. 빈별칭/빠진정의기호로삭제하지않고예제·정의·프롬프트·인용코드를그대로보존한다. 실행/새코드생성/없는명령명복원금지. 이미보류된미완목록이나식은본문에복원하지않고현재후보독립성을검토한다.',
 'expanded_train:129617':'ISearchProtocol()/IPropertyStore()/IFilter()는같은문장의실제명명된인터페이스표기다. 각각의()를빠진공식이라고삭제하지않는다. 등록API설명의첫여는괄호가닫히지않은것만문맥전체에서확인하여마지막인터페이스설명뒤에닫는괄호하나를맞출수있다. 실제인터페이스명·등록관계·설명·Windows버전별반복문맥은보존하고코드실행/새이름/새매개변수추측금지.',
 'expanded_train:276550':'싱가로프동력기술이라는실제명칭과채워진STK는보존하고(, STK)안의빈선행필드와고아쉼표만제거한다. 영문회사명·발음·군용차량수치/사양을외부지식으로교정하거나추가하지않는다. 기존연도·관계·조건은그대로다.',
 'expanded_train:106369':'소비자들의서로다른두채워진인용문사이따옴표를빈이름으로오인한탐지다. 두의견·인용주체와기업의별도답변을그대로보존하고인용문을지우거나합치지않는다. 새사실검증/최신기업인사변경은하지않고현재후보독립성이맞으면ACCEPT.',
}
source=(AUDIT/'prepare_post_body_guard_counter_v1.py').read_text(encoding='utf-8')


def once(old,new):
    global source
    assert source.count(old)==1,old
    source=source.replace(old,new,1)


once("GROUP='post_body_guard_counter_v1'","GROUP='semantic_field_counter_v1'")
once("selected=[row for row in audit['records'] if row.get('post_policy_would_edit') or row.get('introduced_numeric_occurrences')]",
     "selected=[row for row in audit['records'] if row['id'] in "+repr(set(instructions))+"]")
once("len(selected)==14 and len({row['id'] for row in selected})==14,'all14 current guard cases must be visible'",
     "len(selected)==12 and len({row['id'] for row in selected})==12,'all12 remaining semantic guard sources must be visible'")
once("native_rows={row['id']:row for row in native['rows']}",
     "native_rows={row['id']:row for group in ['root_join_conflict_counter_v1','repeat_local_context_counter_v1','nominal_local_alias_counter_v1'] for row in inv.cache.read(BASE/group/'manifest.json')['rows']}")
start=source.index('instructions={')
end=source.index('\n}\n\n\ndef save',start)+2
source=source[:start]+'instructions='+repr(instructions)+source[end:]
once("machine=proposed.get('candidate',proposed['text'])","machine=body")
once("cost=len(original)+len(body)+len(machine)","cost=len(original)+len(body)")
once("('machine_proposal_not_authority',item['machine']),('full_current_to_machine_diff',delta or '기계 제안은 현재 본문과 같다'),",
     "('current_body_preserved_as_comparison',item['machine']),")
once('# 후속 본문 보존·숫자 경계 판독','# 잔여 실제 필드·정의 경계의 독립 판독')
once('원문·현재후보·기계제안·전체diff·root지시','원문·현재후보·비교본문·root지시')
once('기계삭제제안은 정답이 아니다.47767의 실제var()함수와299540의 채워진 음악 설명은 삭제하지 않는다.',
     '빈기호와실제API/코드표기·인용·hard wrap을구분한다.실제채워진정보를누락식으로오인해지우지않는다.')
once('이14건은478전량검산에서드러난후속전부이며전체goal작업량상한이아니다.',
     '이12건은478전량검산의나머지드문필드/정의신호전부이며전체goal작업량상한이아니다.')
source=source.replace('ALL14_POST_BODY_TRANSFORMS_AND_NUMERIC_FLAGS_REQUIRE_INDEPENDENT_REVIEW',
                      'ALL12_REMAINING_SEMANTIC_FIELD_FLAGS_REQUIRE_INDEPENDENT_REVIEW')
once('sources=14,assignments=','sources=12,assignments=')
once('[audit_path,snapshot_path,draft_path,Path(__file__)]',
     "[audit_path,snapshot_path,draft_path,AUDIT/'prepare_post_body_guard_counter_v1.py',Path(__file__)]")
exec(compile(source,str(Path(__file__)),'exec'))
