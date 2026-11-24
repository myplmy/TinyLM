# BabyLM COMPS·Entity 기존 자료의 전량 평가 계약

사용자158의11월17일17시승인과원장53을적용한다. 원BLiMP완료자료는재사용하고반복하지않는다. 공식현재commit은기존로컬`6f825c291e2c4c78ad33b1935fd64d45f52642dc`와같다. 자료revision은`8d52da9424a9ff30b9e8266c4f751aba9c504233`이다. 기준표와기존native595-f/native595-q/new595-broad-f/Falcon90M의strict경로를재사용한다.

| 안 | 내용 | 장점 | 한계·영향 | 수행비용 |
|---|---|---|---|---|
| A | 기존공식함수의변경없는AST와strict native adapter | 전체문항·원suffix mask·원점수·동점RNG를유지 | 원생성자대신기존loader와추적wrapper를사용함을공개 | 중간,선택 |
| B | COMPS·Entity scorer독립재구현 | 구조단순화가능 | 원offset/once-shift/UID·예측문자열의새불일치위험 | 중간 |
| C | 최신full harness/새패키지·평가자료도입 | 남은suite확대가능 | 현재다운로드/새환경승인경계에걸리므로질문유보 | 높음,보류 |

## 착수 전 영향과 권한

| 경로 | 동작 | 권한 | 제외 |
|---|---|---|---|
| scripts/p106b_babylm_semantics.py 및새driver/test | 새decode/getitem관찰·입력추적·원rank대조·현재예산 | 사용자158 필요구현/실험 | 기존실행소스수정없음 |
| 기존7평가파일·토크나이저·명시4모델 | 읽기/현재승인내단일GPU직렬평가 | 사용자158,평가전용 | 학습/추가300M/보호데이터없음 |
| 새evidence namespace/원로그/registry/현재원장 | 신설및실제상태기록 | 사용자158 | 기존원로그·캐시불변 |
| 결과101·P106B·목록·기준표·METHODS·COMPASS | 범위에맞는연쇄갱신 | 사용자158 | 루트09/Git/다른정제없음 |

코드영향은새두과제의입력관찰과현재worker에있다. 원scorer·모델·학습자료형식은바꾸지않는다. 기존BlimpAudit는후보2개/예측문자열형식이고정되어그대로재사용할수없다. 새helper6계약은공식decode·nothing 제외·overlap mask·변경없는getitem·후보2/5·정확동점RNG·잘못된예측문자열거절을검사했다. driver2계약은원순서비용표본과전파일/실제padding위치외삽을검사한다. 데이터마이그레이션없음,기술부채는별도wrapper/source pin과최종원문검산비용이다. 비교는같은7파일/원정답/모델native tokenizer이고학습풀차이에대한학습효과실험은아니다. 메모리/시간은실행관측이며품질이나절감률로대체하지않는다. 설치·다운로드·새환경0이다.

## 1. 왜

원장53의BabyLM공식평가중이미취득한COMPS4/Entity3의실제점수가없다. 현재공식source와같은로컬함수·자료로전량분모를닫을수있다. 기존BLiMP점수를의미·개체추적점수로대신하지않는다.

## 2. 질문

| 질문 | 이유 |
|---|---|
| Q1, 원decoder/phrase mask/정확동점/UID집계가native2/5후보에서유지되는가 | 원형점수계약입장 |
| Q2, 기존4고정모델의전량COMPS·Entity정확도는어떤가 | 추가학습없는기준선확보 |
| Q3, 전량계산이현재시간/자원에서가능한가 | 부분결과를전량으로승격하지않기 |

## 3. 예측

원형6계약과기존strict full-logits경로가있어수치입장을기대한다. 작은TinyLM과한정된학습량때문에무작위기대COMPS50/Entity20보다낮거나유사할수있다. native595-f/q차이는양자화경로비교이고new595-broad-f는훈련이력도다르므로단일학습요인의인과효과로해석하지않는다. 97,808행으로시간초과가날수있으며그경우전체남은문항은NOT_RUN이다.

## 4. 단계 설계

### 단계 0 — 입력과CPU계약

6helper+2driver계약,공식4소스SHA/변경없는AST,기존license/manifest와7파일SHA,현재source/CP선결을검사한다. COMPS91,028/Entity raw9,483에서공식소문자nothing 포함옵션2,703개만제외해6,780행/전체97,808행을고정한다. native공통토크나이저1회/Falcon1회로전행의native ID·offset·비어있지않은원phrase target/1024문맥을검사한다. 자르기·추가BOS·새행제외없음. 모델0/GPU0/예상10분이내다.

### 단계 1 — 실제모델oracle와비용

기존4모델을한번씩직렬로연다. FP32/TF32off/eager·SDPA math/noKV/noautocast,실제native tokenizer 기본동작을쓴다. 기존synthetic batch/single/역순/full-label oracle와실제COMPS/Entity의입력만으로선택한최장문항각후보의원phrase-sum 대full-label CE를대조한다. 원ATOL1e-5/RTOL1e-4를바꾸지않는다. 파일별32균등위치+각UID첫행+첫최장문항을출력전고정하고원순서로비용측정한다. 비용표본점수는정식품질이아니다.

### 단계 2 — 전량 평가

각파일실측시간×전량/표본의실제padding input위치비×1.5를합하고120초를더한다. 남은1800초/현재16:40모델계산창에들어온모델만전량실행한다. Entity→COMPS,각파일원순서/최대8batch,task별seed1337초기화후파일간유지. 원compute_causal_results/rank_and_evaluate/process_results를그대로부르고temperature1/원suffix sum을쓴다. COMPS UID4와Entity UID18의공식macro를과제별구분한다. 전행raw/native ID/mask/우도/선택/원파일행/UID/입력cluster를10MB이하shard와SHA로저장한다.

### 단계 3 — 종료·독립재집계

원본source/입력/strict모델상태불변과소유모델/CUDA allocated/reserved0을검사한다. 원파일SHA·전량분모/저장shard/우도최대·정답·UID macro를모델없이재집계한다. COMPS cluster는파일공통property,Entity는파일+sample_id로출력전고정한다. 통계추가시동일문항paired·과제UID macro/cluster를보존하고표본독립성·훈련seed분산을구별한다. 원문항분모미완은HOLD/부분이다.

## 5. 판정 기준

| 결과 | 판정 |
|---|---|
| source/전량native검사/oracle실패 | full NOT_RUN/실제실패보존 |
| 실측전량예산초과 | HOLD8,줄여실행하지않음 |
| 97,808전량·UID22·원점수/입력추적·불변/종료/독립검산 | 해당고정모델의두과제기준선완료 |
| 일부파일·일부문항만완료 | 부분관측,두과제전체완료주장불가 |

새학습품질판정자가없는고정모델평가다. good-first/label0의항상첫후보100%는정답순서누출이며유효모델기준선이아니다. uniform 기대는50/20이다. 전체BabyLM suite/대회학습제약준수나일반한국어대화성능은판정하지않는다.

## 6. 비용

CPU준비최대10분,모델별실제최대1800초+소유종료60초/4개직렬,개별8GiB allocator cap·전체event512MB/모델·각10MB shard다. 16:40전에새hardcap이들어오지않으면시작하지않고17시인계한다. 기존runtime내프로세스별cache만쓰고새설치/다운로드는없다.

## 7. 실행

`run_P106B_Stage8sem0Wc_existing_semantics.sh`를별도작성한다. 실행Python은이미있는`data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python`이고torch2.10.0+cu130/transformers5.14.1/lm_eval0.4.14.dev0/tokenizers0.22.2다. 이전기한의execute/controller는호출하거나기한재바인딩하지않는다. 현재worker가사용자158/시간·STOP·예산을소유한다.

## 8. 한계

평가전용7파일은훈련편입불가다. 공식whole CLI대신고정된변경없는AST함수와기존native wrapper를사용한다. 모델별토크나이저는고유경로이고raw likelihood를모델사이에직접비교하지않는다. 읽기/AoA나fine-tuning등남은suite자료·코드는별도선결이다. 전량실행시간은단일GPU의해당시점관측이며속도인과비교가아니다.

## 9. 이력

2026-11-17 12:42 helper6 PASS,12:56 driver2 PASS. 새full평가는아직NOT_RUN이다. 원장53/158과현재intake/source를연결한다. 결과후이절/원P106B/결과101·목록·방법론·기준표·COMPASS를갱신한다.

preflight: 학습steps/micro/accum/seq와pool비율은학습0이므로적용없음이다. 새tag registry충돌없음,완료BLiMP반복없음,독립변수는고정모델과평가과제이며훈련이력차이는공개한다. 출력전전량/원tol/실측예산/보존·종료기준을정했다. 모델수치와실행비용은아직미확인이다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.


### 첫 준비 실패와 현재 입장

12:58의첫CPU준비는과거adapter receipt의`interactive_research_infer.py` SHA가현재와달라실제1로중단됐다. 모델/GPU0·새namespace미생성이고실패소스/원로그를별도로보존했다. 차이는그한파일이며과거receipt자체SHA/성공상태는유지된다. 현재worker는이차이를명시저장하고현재소스봉인·현재adapter21계약/driver2(합23PASS)·매모델의새실제synthetic/phrase-full-label 수치oracle를현재입장선결로쓴다. 기존실행소스나과거receipt를고치지않고새worker만준비전에갱신했다. [실패영수증](../../handoff/audit/research_20261117_01a1e647/BABYLM_PREPARE_HISTORICAL_STALE_v1.json).


### 현재 상태 — 입력 완료, 실제 모델 미실행

현재prepare는13:00:40KST 실제0으로97808전행을native/Falcon 두토크나이저에서검사했다. native최대246/Falcon261토큰·추가제외/절단0이다. source/profile와registry696을봉인했지만GPU명령은자동승인검토두차례거절/프로세스미생성이다. 실제수치oracle·비용·네모델전량점수는NOT_RUN이며위§3의품질예측은미판정이다. 현재명시재승인은사용자지시에따라17시최종질문으로유보하고우회하지않는다. [결과101§621](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-babylm-semantic-prepared). 단계0완료/단계1~3실제모델경로NOT_RUN이다.
