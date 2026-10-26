# HOLD 복구 원문 작업 위임 명세

현재 사용자 goal은 HOLD 검토·복구와 어려운 사례의 총괄 판정을 요청했다. 총괄은 `/root`, 현재 원장은 `handoff/WIP_20261026b_작업원장.md`다. 이전 다섯 `gpt-6-luna` max 역할을 재사용하며 동시에 최대5개다. 이전 위임의 입력·출력 허가를 이번 자료로 자동 확대하지 않는다.

## 공통 입출력과 경계

기준 경로는 `data_cache/p106b_hold_recovery_v1_20261026_goalc/`다. 위임은 각 `assignments/<role>_initial.md`가 실제 생성된 뒤에만 시작한다. 읽기 허용은 이 명세, 해당 assignment와 거기에 명시된 정확 `packets_initial_v2/<source>_<ordinal>.txt`뿐이다. 총괄용 JSON·기존cache/scan·다른 역할·memory·다른세션·보호TinyDataset·원규약/코드/스킬은 추가로 열지 않는다. 전체 트리/인접 행/접두사 glob 검색도 하지 않는다.

| 기존 역할 | 이번 역할 | 읽기 범위 | 새 쓰기 범위 |
|---|---|---|---|
| context_hangul | 배정된 혼합 유형의 문맥/정제 | 정확 자기 assignment와 그 원문 | `agents/context_hangul/initial/review.md`, 해당 ID `.txt`, 필요한 해당ID `_hold.md` |
| context_latin | 배정된 혼합 유형의 문맥/정제 | 정확 자기 assignment와 그 원문 | `agents/context_latin/initial/review.md`, 해당 ID `.txt`, 필요한 해당ID `_hold.md` |
| historical_review | 배정된 혼합 유형의 문맥/정제 | 정확 자기 assignment와 그 원문 | `agents/historical_review/initial/review.md`, 해당 ID `.txt`, 필요한 해당ID `_hold.md` |
| legacy_review | 배정된 혼합 유형의 문맥/정제 | 정확 자기 assignment와 그 원문 | `agents/legacy_review/initial/review.md`, 해당 ID `.txt`, 필요한 해당ID `_hold.md` |
| context_controls | 배정된 혼합 유형의 문맥/정제/누락 대조 | 정확 자기 assignment와 그 원문 | `agents/context_controls/initial/review.md`, 해당 ID `.txt`, 필요한 해당ID `_hold.md` |

쓰기 허가는 새 txt/md에만 적용한다. 코딩·분석/전처리/시험 스크립트 실행·해시 계산·토큰 계수·모델/GPU·Git·환경/규약·설치/다운로드·원본 편집/삭제·외부검색은0이다. 일반 텍스트 읽기/새 txt/md 저장만 허용한다. 파일명은 지정ID의 `source_ordinal.txt` 형식을 사용한다. 후속 독립 대조는 별도의 정확 assignment로만 허가한다. 총괄이 실제 저장물과 근거를 검토하기 전에는 채택 완료가 아니다.

## 실제 판독·정제 원칙

1. 배정 원문을 시작부터 끝까지 읽는다. 도구 출력 잘림은 미판독이며, 추가 구간을 읽은 뒤 판독 범위를 정확히 쓴다. 읽기 한도를 전체 작업량 한도로 바꾸지 않는다.
2. 참고문헌·목록·분류·인용·정상 반복은 유효한 내용을 가진다. 존재만으로HOLD하지 않는다. 외부 사실 검증을 하지 않았다는 이유만으로 모두HOLD하지 않는다. 사실 미검증과 원문 의미 보존은 구분한다.
3. 제목이 없어도 첫 문장에서 주체/주제를 식별하고 본문이 독립적으로 이해되면 원문 보존이 가능하다. 새 제목·이름·수치·소실 수식·경기 결과·날짜·원어를 생성하지 않는다.
4. 전체를 보존할 수 없으면 완결되고 독립적으로 이해되는 본문만 보존하는 EDIT를 검토할 수 있다. 빠진 관계·표·연결 잃은 조각은 구체적인 별도 `_hold.md`에 남기고, 원문 손실을 숨기지 않는다. 본문에 ‘검수’, ‘보관’, ‘생략’, ‘정제’ 등의 설명을 넣지 않는다.
5. 코드·인용 주체·학술/공식 용어·숫자/단위·날짜·부정·조건·불확실성을 보존한다. 유효 어휘를 동의어로 바꾸거나 내용을 요약해 줄이지 않는다. 정규식처럼 제목/각주/링크/꺾쇠를 모두 지우지 않는다.
6. 추출 중복이 명확한 해당 구간만 좁게 정리한다. 반복이라는 이유만으로 전역 삭제하지 않는다. 코드 울타리와 실제 코드 바이트는 그대로 보존한다.
7. 판단이 어렵거나 원문의 두 주장이 충돌하면 정확한 문자열/위치·가능한 해석·부족 근거를 적어 총괄에게 보낸다. 총괄이 최종 판단하며 사용자에게 바로 승인을 요구하지 않는다.

## 출력 형식

고정 표는 `| ID | 판정 | 새 txt | 근거 | 전체 판독 |` 다섯 열이다. 판정은KEEP/EDIT/HOLD만 사용한다. 근거에 세로줄 문자를 쓰지 않는다. KEEP은 원문 그대로 보존 가능, EDIT는 실제 새txt를 저장, HOLD는 새 학습 본문을 쓰지 않는다. 각 근거는 무엇을 보존/제거/보류했는지 구체적으로 적는다. EDIT는 본문/수치/조건 보존과 실제 변경 범위를 설명한다. 마지막에 실제 읽기/쓰기 목록, 미수행과 범위 이탈/도구 오류 여부를 적는다.

총괄도 판단할 수 없는 대표 사례만 원문·수정문·질문을 갖춘 review_request로 이관한다. 현재 위임은 OS 격리 증거가 아니며 범위 이탈은 숨기거나 삭제하지 않고 즉시 보고한다.

최초 패킷 준비는 tokenizers 없는 시스템 Python에 연결돼 원문 저장 전1로 끝났다. 빈 `packets_initial/`은 보존했고, 기존 tlm_torch 환경과 새 `packets_initial_v2/`를 사용한다. 그 사이 HOLD 전량집계는 독립적으로 실제0을 완료했으므로 초기 판독은 전량유형에서 목적 선택한다. 이 실패를 데이터/모델 실패로 해석하지 않는다.

## 실제 수정본 독립 대조 — counter_initial

초기 실제 EDIT53개를 작성자와 다른 역할에 순환 배정한다. 추가 읽기 허용은 정확 `assignments/<role>_counter_initial.md`, 그 표에 있는 정확 원문/새txt와 표시된 개별 `_hold.md`뿐이다. 다른 역할의 전체 review나 JSON·코드는 열지 않는다. 추가 새 쓰기는 자기 `agents/<role>/counter_initial.md` 한 파일뿐이며 본문 수정0이다.

각 쌍의 원문/수정문 전체를 읽고 정보/숫자/단위/조건/부정/인용/불확실성·참고자료/목록 관계·코드 바이트와 독립 문맥을 대조한다. 부분복구는 유지 본문에 소실 구간의 지시어/예시/수식 전제가 남는지 확인한다. 표제/광고/탐색 정리 외의 누락과 새 사실은 PASS하지 않는다. 판정은PASS/REVISE/HOLD이며 정확 차이/근거·전체 판독 범위·어려운 총괄 질문을 고정 표에 기록한다. 사유 보관문은 학습 본문과 구분한다. 보조가 표본 몇 개를 대조한 것을 전량 사실 검증으로 보고하지 않는다. 실제 범위/오류/미수행은 원 공통 경계와 같다.
# repair_v2 및 counter_reread

기존 initial/counter_initial 저장물은 보존한다. 총괄이 명시한 정확ID의 기존 원문·수정문·sidecar와 자기 새 assignment만 다시 읽는다. repair_v2는 자기 역할 `agents/<role>/repair_v2/`에 새 txt·개별 `_hold.md`·review.md만 작성한다. counter_reread는 자기 역할 counter_reread.md만 새로 작성하고 본문을 바꾸지 않는다. 부정의견을 PASS로 바꾸라는 요청이 아니며 기존 지적이 실제 저장물과 맞는지 다시 확인한다. 코드/시험/계수/해시/스크립트/모델/GPU/Git/웹/memory/보호·목록외읽기0을 유지한다.

repair_v3는 총괄이 정확ID별로 명시한 새namespace/3파일만 쓴다. keep_controls는 자기 정확assignment의 원문만 읽고 자기keep_controls.md 하나만 쓴다. proposal_controls_v1은 자기 정확assignment의 실제원문/제안txt 쌍만 읽고 자기proposal_controls_v1.md 하나만 쓴다. 제안전량817494처리와표본153은최종캐시채택·전량사실검증이아니다. 기존금지와부정기록보존을계승한다.

recovery_context_v2는 각 역할의 정확assignment에 적힌 자기 판독 원문과 해당 자기review만 읽고 자기 `agents/<role>/recovery_context_v2/`의 새txt·개별hold.md·review.md만 쓴다. 기존325패킷은 총괄이 실제원형3파일SHA/토크나이저SHA/각원토큰구간SHA/디코딩바이트를 모두 검증했다(`review_source_proof_v1.json`, 실제325/325). 보조는 SHA/코드 검사를 맡지 않고 문맥 판단/새본문 작성만 한다. 개별 상속HOLD 해제는 이 검증과 새 원문 판독·총괄 채택·독립 대조를 모두 거쳐야 한다. 코드/스크립트/계수/해시/모델/GPU/Git/웹/JSON/memory/목록밖읽기0, 기존부정/초안 불변을 계승한다.

context_repair_v3 및 root_extra_v1은 총괄이 정확ID별로 승인한 원문/이전본문/sidecar/해당검토행만 읽고 자기역할의 새namespace txt/hold.md/review.md만 쓴다. 보존·복원 근거가 실제 저장물과 맞지 않으면 복원을 강제하지 않고 총괄에 보고한다. 사실/누락수식/이름/제목 생성0·기존부정/초안 불변·나머지금지를 계승한다. 705988의 v4는 별도지정이며 조건 문단의 과잉보류를 바로잡는 새버전이다.

validation_v3는 제안v3의새186고유본문/실제제안쌍을정확assignment로배정한다. 각역할은자기`validation_v3/review.md`와명시적새txt/hold.md만쓴다. 알고리즘제안의독립대조와과잉HOLD의문맥복구를분리기록한다. 원형685패킷동일성은총괄의`review_source_proof_all_v3.json`이소유하며보조의해시/코드검증을뜻하지않는다. 모든기존금지·원문/부정기록보존·실제코드/Unicode/숫자/조건/인용보존을계승한다.

versions_wave4는 저장된 최신26사례(EDIT25/KEEP1)의 작성자외 대조다. `assignments/context_controls_counter_versions_wave4.md`의10사례와 `assignments/historical_review_counter_versions_wave4.md`의16사례만 추가 읽기를 허용하고, 각 역할 `agents/<role>/counter_versions_wave4.md` 새 검토표 하나만 쓴다. 같은 이름의 기존 파일을 덮지 않는다. 본문 수정·스크립트·해시·계수·시험·모델·GPU·Git·웹·JSON·memory·목록외 읽기 금지를 유지한다. 총괄이 동결한 실제 저장물 SHA는 `versions_wave4_candidates.json`에 연결하지만 보조는 그 JSON을 읽지 않는다.

validation_v4는 총괄이 직접 메시지로 지정한 정확 ID와 자기 원문/초안에 한정한 좁은 새 버전이다. 기존 v3 파일/부정기록은 보존한다. context_hangul의 v3 오배치 원본은 삭제하지 않고 지정된 base/agents 경로에 새 복사하며, 경로 이탈을 기록한다. 복사할 파일 개수 확인은 통상 텍스트 입출력에 해당하며 corpus/token 통계를 보조에게 위임한 것이 아니다. context_latin이 v3 검토표 말미에 잘못 붙인 990089 발췌는 해당 블록만 제거하여 복원했다고 보고했다. 이런 작업 오류를 숨기거나 corpus 변질로 확대 해석하지 않고 최종 감사에서 구분한다.

initial_alias_v1은 `assignments/context_hangul_initial_alias_v1.md`의 초기 KEEP5개에 남은 빈 선택 별칭만 좁게 수정한다. 읽기는 그 명세/정확원문5개, 쓰기는 정확base/agents/context_hangul/initial_alias_v1/의 지정5본문+review.md만이다. 나머지 금지와 원형 보존은 동일하다. legacy_review도 validation_v3/v4를 루트 agents 아래 잘못 저장한 사실이 발견돼, 해당 자작물만 base/agents로 no-clobber 복사하고 이탈을 기록하도록 지시했다. 원 오배치 파일은 보존한다.

validation_v3_saved는 최종 저장버전을 가진186행 전부의 판독을 회수한 뒤, 직접 수동판정152건(EDIT111/KEEP39/HOLD2)을 작성자외 순환 대조한다. 각 역할의 `assignments/<role>_counter_validation_v3_saved.md`만 추가 입력이며, 해당 표의 정확원문/실제본문/있는sidecar/작성review해당행만 읽는다. 쓰기는 정확base/agents/<role>/counter_validation_v3_saved.md 새 파일 하나뿐이다. 역할별 latin26/legacy31/controls33/hangul31/historical31이며, 학습본문은 수정하지 않는다. 나머지 금지는 동일하다. validation_v4가 실제 최종본문을 제공하는 ID는 과거 v3 검토표의 누락·오지시 파일을 채택하지 않고 최신버전에 연결한다. 756966은 위험한 실제 작업정보와 깨진 문서 경계 때문에1–540행 판독 뒤 HOLD를 유지했으며 전량 의미판독으로 부풀리지 않는다.

388100의 context_repair_v5는 정확 원문/자기 v3본문·sidecar·해당review행에 한정하고, 소실된 density식 앞 고아 표제와 Let V 설정 두 행만 새sidecar로 옮긴다. 다른본문은 동일해야 한다. legacy_review가 작성하고 총괄이 바이트차이·원문 연결을 검증하며, 기존 부정의견과 초안은 보존한다.

후속 개별 중재는 총괄이 메시지로 정확 입력/namespace/ID/변경을 고정했다. latin context_repair_v4는853946/8449/719385/1189970, hangul validation_v5는413195/237434/508614/466507/693383, legacy context_repair_v5는388100/275683, legacy validation_v5는145886/939/186007/150417이다. 모두 기존 초안은 보존하며 실제 의미손실/빈필드 잔여만 수정한다. 서브에이전트에게 새 코드/해시/통계/시험을 위임하지 않는다.

historical validation_v5는 `assignments/historical_review_validation_v5.md`의 정확19사례만 입력으로 하고, 그 명세의 절대base/agents/historical_review/validation_v5/에 지정txt/필요sidecar/review만 쓴다. 일반 text I/O 외의 실행·분석 금지는 유지한다. 완결 코드의 실제 문자·인수·순서를 바꾸지 않는 수동 줄바꿈과 소실값을 생성하는 코드 재구성을 구분한다. 843457의 한줄 C#은 명시 주석/명령경계의 줄바꿈만 허용하며 총괄이 비공백 문자열의 동일성을 대조한다.

후속validation_v5 latin5개는1271176/29997/912185/169812/375187의 실제예고/UI/빈표제잔여와 유효번역 한행 복원이며, controls6개는376171/216767/1016896/495464/609649/292983의 빈별칭/구두점/실제출생연도충돌/누락문단·메타데이터를 처리한다. controls root_extra_v2의250733만 원문 인용블록을복원하고 손상된 참조문자열을 외부사실로정정하지 않는다. 모든 입출력은 총괄 메시지의 정확 기존명세/원문/자기초안과 새절대base namespace로 제한한다.

versions_final_wave5는 Latin기술복원4건과초기빈별칭5건의 최신저장물을 `assignments/legacy_review_counter_versions_final_wave5.md`에 고정했다. legacy_review의 새 counter_versions_final_wave5.md 하나만 출력하며 실제 원문/본문/있는sidecar/작성review해당행을 대조한다. 코드/스크립트/계수/해시/시험/모델/GPU/Git/웹/JSON/memory/목록외0,본문수정0이다. 이 추가9건은685고유원문 밖의 새 표본이 아니라 기존 사례의 수정버전 재검토다.

decorative_markers_v1은 최종직렬화 예비검사에서 실제코드와 장식물결표를 혼동한5사례를 `assignments/context_hangul_decorative_markers_v1.md`로 고정한다. 정확원문/현재본문/review해당행만 읽고 정확base/agents/context_hangul/decorative_markers_v1/의5본문+review만 쓴다. 물결표와 그 분리공백/빈행만 정리하며 의미문자 전체를 보존한다. 원문SHA별 코드가드예외는 총괄만 만들고 기존v3생산코드/규칙 pin은 수정하지 않는다.

final_repairs는새실저장26사례의재대조다. Latin은 `assignments/context_latin_counter_final_repairs.md`의Historical19건, Legacy는 `assignments/legacy_review_counter_final_repairs.md`의Controls7건만읽고자기counter_final_repairs.md 하나만쓴다. 실제원문/저장물/있는sidecar/해당review행만허용하며코드·해시·통계·시험·모델·Git·외부접근·본문수정0이다. 기존지적의오독도검토결과에서제외하지않는다.

위 final_repairs의 최초 메타데이터수집은 아직 위임하기 전에 형식 불일치를 발견했다. Historical19행이 숫자ID를 써 기본파서가 건너뛰었고 Controls6행은 author수정결과를PASS로적었다. 최초7행 후보/assignment는 NOT_APPROVED로보존한다. 정확namespace/source를고정해숫자ID를해석하고실제새본문이있는author-PASS를EDIT로분리한 final_repairs_v2에서19+7=26을단언한뒤실제위임한다. 추가입력은각역할 `assignments/<role>_counter_final_repairs_v2.md`, 새출력은자기counter_final_repairs_v2.md 하나로정정한다. 잘못된 최초assignment로보조작업/캐시채택0이다.

cache_v3 생성후 잔존위키신호의 실제 문맥을 확인해 783522의 불균형한 하와이 링크와 1415117의 [[deacon]을 발견했다. 이는정상scp중첩괄호/위키문법교육/원문인용예외와다르다. 두역할의 `assignments/<role>_postbuild_residual_v1.md`로정확원문/현재본문/있는sidecar/review행을지정하고, 자기 정확base/agents/<role>/postbuild_residual_v1/의본문/필요sidecar/review만새저장한다. 기존동결본문/cache_v3는수정하지않고새수동판정명세와cache_v4로회수한다. 코드/규칙7파일과전량v3제안은그대로재사용하며새의미판정은작성자외대조/총괄문자검산후채택한다.

새채택226,047본문 전체에서 빈절/위키/HTML/주석의 희소잔여를 전수 추린40사례도 회수했다.37개HTML신호는 주로 실제작품명/언어학전사/코드/이메일각괄호이며, 그중950001의단독p태그/1170731의ref래퍼/1389144의닫는ref와384984의빈별칭/각주는추가실제형식잔여다. `context_controls_postbuild_residual_extra4_v1.md`에정확입력과4ID/출력범위를추가했다.1415117을포함한기존5개postbuild본문외의수정금지와코드/해시/통계/시험/외부금지를유지한다. 의미있는주석내용은삭제하지않고부모괄호로보존한다.

420수동긍정본문의두번째좁은서식점검에서384984/783522외995468의빈외부표제를찾았다. 같은문서의1984/1982생년충돌은실제원문으로확인했다. 생년가드의전체출력은이한건이아닌다섯신호이며,생년만있는앞범위와뒤의완전사망일을혼동할수있어총괄이추가구분한다. `legacy_review_postbuild_residual_v1.md`로정확원문/해당review행만위임해995468의두연도를선택하지않는부분보류/유효직업·출연목록보존과빈표제제거를지시했다. 하와이의참고자료→참고문헌은실제서지가이어지는부모/자식표제이므로탐지기의제거제안을자동채택하지않고구조예외로남긴다.

생년신호5개를실제문장으로대조해995468/1008442/validation44의3개는진짜충돌,912185/998546의2개는연도만있는출생과완전한사망일을가드가혼동한오탐으로판정했다. controls의 `context_controls_postbuild_birth2_v1.md`에두실제충돌만추가위임했다. 사망일과자녀날짜/독살추정한정은유지하며정정할생년을생성하지않는다. 원규칙의보수적신호를전량거짓/오류로승격하지않고개별예외를기록한다.

postbuild_v1의새9실저장물은 `assignments/context_latin_counter_postbuild_v1.md`로작성자외재대조한다. Latin은정확원문/실제본문/있는sidecar/작성review해당행만읽고base/agents/context_latin/counter_postbuild_v1.md 하나만쓴다. 생년이상반된문서는해당필드만보류하고사망일/이름/조건/서지까지삭제하지않는지확인한다. 원형과이전캐시/판독기록은보존하며본문수정·코드·계수·해시·시험·외부접근0이다.

후행독립9행의REVISE3개를실제파일로중재했다. validation44의1425년출생분류잔존은실제여서controls의새postbuild_residual_v2에서한행만더분리했다. 995468은고정SHA가변하지않았고1982년분류가실제로없어누락/잔존주장은오독이다. 하와이의이민역사두문장도initial/post_v1에서이미한번씩존재했고SHA불변이라중복삽입하지않았다. Historical의새v2는같은본문과기존sidecar연결을보존한다. `context_latin_counter_postbuild_readback_v2.md`로이3개최신본문을따로재독하고새counter_postbuild_readback_v2.md만쓰도록허용한다. 과거부정표는덮지않는다.13문자/조건검사의v2음성한건은빈행차이이며그순수산문사례의공백동치만구분한v3증거를새로보존한다.

cache_v4 생성중 총괄이1080124의 원문/수정문 전문을 재대조해 교육용 위키 구문과 별개인 네 누락 예고를 확인했다. Historical에 정확 proposals_v1/review_packets/expanded_train_1080124_original.txt 및 자기 recovery_context_v2/expanded_train_1080124.txt만 입력으로 지정하고, 자기 postbuild_residual_v3/의 새 txt/hold.md/review.md만 쓰도록 허용했다. 명시 일반 문법/독일 주소를 보존하며 없는 Jedi 예제·Spanish 주소·or 대안·this page 안내만 별도 보류한다. 없는 예제/주소를 생성하거나 원형/기존본문/코드를 바꾸지 않는다. 실제 저장물의 다른 작성자 대조·총괄 정확구절 차이 검산 뒤 새로운 root_adoptions_v3와 cache_v5로 회수한다. 진행중v4는 지우거나 중단본을 덮지 않고 중간 버전으로 보존한다.

Historical의첫v3는sidecar만쓰고본문은그대로복사해실제조치가없음을총괄diff로확인했다. 오해버전은보존하고원문/같은v3본문/sidecar만입력으로한새postbuild_residual_v4에서실제네구절을빼도록다시배정했다. 실제diff는네구절외내용변경이없다. Controls에게원문·기존context_v2·새v4본문·sidecar/review만입력으로counter_interwiki_postbuild_v1.md를쓰게했다. 대조자는본문PASS이나작성자review범위를대조자자신의v2/v4배정과혼동해REVISE했다. 작성자는실제로v3입력을읽었고v3가이전본문과같음을총괄이확인했으므로기존REVISE는보존하고역할별배정차이를설명한새counter_interwiki_postbuild_v2.md만추가허용했다. 읽지않은v2를작성자가읽었다고기록을고치지않는다.
