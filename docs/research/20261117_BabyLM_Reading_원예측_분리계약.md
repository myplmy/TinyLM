# BabyLM Reading의 원예측과 공식 통계 점수를 분리한다

## 1. 왜

사용자161/원장53의 기존 미완이다. 현재 공식commit6f825c는 재조회에서도 최신이었다.
Reading1726행/205문장과 AoA504단어/8005문맥·human CSV는 기존82파일 cache에 이미 있었다.
자료가 없다는 이전 포괄 서술은 정정한다. [현재 선결](../../handoff/audit/research_20261118_01a1e647/BABYLM_REMAINING_EVAL_FRONTIER_v1.json)이 원문 SHA·source·의존성을 소유한다.
원 reading/run.py는 statsmodels OLS를 사용하며 statsmodels/patsy는 기존 두 runtime에 없다.
설치는 사용자161 지시대로 유보하지만 GPU의 원예측을 보존하면 후속 승인이 나도 재추론할 필요가 없다.

| 안 | 내용 | 장점 | 단점 | 영향도 | 비용 |
|---|---|---|---|---|---|
| A | 패키지 승인 뒤 전체 수행 | 한 번에 원pipeline 종료 | 현재 가능한 모델 계산도 지연 | 없음 | 현재0·후속GPU 필요 |
| B | 원 word/prev-word 예측 전량 수집, OLS 분리 | 원함수/입력 유지·승인 뒤 CPU 통계만 필요 | 지금 공식R² 점수는NOT_RUN | 새 얇은 helper/원행·실행기 | 중간 |
| C | OLS library를 새로 대체 구현 | 새설치 없이 통계 계산 가능 | 원library 동등성/유지보수·판정 부담 | 추가 통계 backend | 높음·현재 유보 |

B를 선택한다. 실제1726행과 모든 원prev 조건을 처리한다. 부분 score를 공식R²로 쓰지 않는다.

| 파일·경로 | 동작 | 권한 근거 | NOT_RUN·제외 |
|---|---|---|---|
| scripts/p106b_babylm_reading.py·대응test | 신설·CPU계약 | 사용자161의 필요한 구현·기존53 수행 | 기존 실제GPU 동결 source 수정0 |
| 새 Reading diag/런처·전용 evidence | 신설·기존4모델 직렬 수행 | 현재161 CPU/GPU 허가 | 설치/새환경·학습/교사·원CP 변경0 |
| 고정공식 source·기존reading CSV·native/Falcon tokenizer | 읽기 | 기존53/현재161, source Apache2 | eval자료의 TRAIN/SFT/KD 편입0 |
| 계획/결과101·문서연쇄·소유WIP/감사 | 좁은 갱신 | 원장·결과 회수 지시 | root09·타정제·보호·Git/삭제0 |

| 축 | 영향 | 내용 |
|---|---|---|
| 코드 | 있음 | 원 get_p/get_p2/get_logits AST를 그대로 실행하고 model 반환은 지원tuple로 연결한다. |
| 데이터 | 없음 | 원CSV row/order/NA·문맥·word를 유지한다. native word 인코딩/단일piece 재디코딩을 명시 trace한다. |
| 테스트 | 있음 | 합성 full-label CE·단/다중subtoken·원source drift·전량 token길이/원문·이전word/미결측을 검증한다. |
| 정본 | 있음 | 원예측/공식통계NOT_RUN·다른suite 선결을 분리해 기록한다. |
| 부채/순서 | 있음 | 임의 통계 대체 대신 승인 뒤 CPU로 재사용할 원캐시를 만든다. |
| GPU 권한 | 있음 | 현재161·한GPU/한모델. 진행중 BabyLM COMPS·Entity 종료 뒤 수행한다. |
| 소유권 | 없음 | 현재명시 평가파일/모델만 읽고 새 cache만 쓴다. 보호/타정제0. |
| 비교 유효성 | 조건부 | 모델별 학습/tokenizer 차이가 있어 서술 비교다. 원함수의 spacing/단일piece decode 정책을 바꾸지 않는다. |
| 증거 구분 | 있음 | CPU가짜모델 token sweep·실제 word확률·인간 reading OLS는 다른 단계다. |
| 문서 연쇄 | 있음 | 실제 종료/원예측과 통계 선결을 결과101→계획/목록/기준표/방법론/COMPASS에 회수한다. |

## 2. 질문

기존4모델이 모든1726 target 및 존재하는 prev-word의 원확률을 finite하게 계산하는가?
각 원문맥/word의 native ID와 source 함수 분기가 같은가? 추후 원OLS 입력을 완전히 복구할 수 있는가?

## 3. 예측

짧은 문맥과 영어 word가 많아 현재1024 문맥에서 전량을 기대한다. 그러나 underflow·길이
초과·bytepiece 디코딩 불복원·tokenizer API 차이·수치oracle 실패가 가능하다. 점수 방향과
인간 reading 상관/ΔR² 향상은 예측하지 않는다.

## 4. 단계

1. CPU: 고정Apache2 source/기존자료SHA·원함수 AST를 확인한다. 실제model 없는 deterministic
   logits fixture로 단/다중토큰 확률·독립CE·native API를 검증한다.
2. CPU: 두 실제tokenizer로 전체1726행과 원prev 조건의 호출을 순서대로 추적한다. 수동BOS·
   ChatML·문맥 crop·추가제외0, 원 item 결측은 source처럼 문자열 None으로 처리한다.
3. GPU: 기존frozen 모델의 원word 함수와 독립full-label CE를 먼저 대조한다. cost표본은 입력만으로
   고정하며 실제 호출의 native positions로 전량비용을 계산한다.
4. GPU: fit하면 전량 원예측/ID·문맥/target trace를 새write-once shard에 기록한다. 같은고정모델의
   동일한 context/word를 재사용할 수 있지만 scalar/trace만 cache하고 CPU전체/실제반복 canary를 먼저 검증한다.
5. 종료: source/CP/model state/CUDA종료와 원행 순서·수치·cache 출처를 독립 검산한다.
6. 후속: statsmodels/patsy 설치 승인 뒤 원 OLS 코드를 그대로 사용한다. 현재 대체통계0이다.

11월 18일 사용자163의 GPU 허가로 4개 모델의 1,726행 및 이전 단어 1,520행씩을 수집했다. 08:02:53 KST에 순차 실행을 마쳤고 4개 종료 코드 0과 원 CSV, 샤드, CUDA 해제를 검증했다. OLS는 저장된 예측을 사용할 수 있다. [결과101 §635.1](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-reading-original-predictions-prepared)

## 5. 판정

1726행/prev분모·finite 원확률·native trace·원source/모델 불변·해제를 모두 닫으면 해당
frozen 모델의 원예측 수집 완료다. 공식 ET/SPR ΔR²·AIC/회귀 p값은NOT_RUN을 유지한다.
source dtype/word 경계·decode·0확률·길이 초과는 임의제외/확률floor로 숨기지 않고HOLD한다.
독립CE의 원허용차1e-5/1e-4를 유지하며 cache reuse는 실제 반복 scalar가 같을 때만 허용한다.

## 6. 비용

기존 공식 평가 runtime만 사용한다. 한모델30분/내부1800초·외부1860초+kill60초,
네모델 보수 편성2.2시간이며 실측값이 아니다. 자체 allocated8GiB, 원예측64MB/모델,
10MB shard·11월18일16:30 계산 종료/17시 회수다. 전체 word 호출의 실제positions로 forecast를 입장시킨다.

## 7. 실행

helper/CPU/전량token sweep 뒤 전용 diag/런처를 작성·봉인한다. 지금 모델 실행은NOT_RUN이다.
설치·일반코퍼스/모델 취득·새환경0이다. 현재 source5파일 archive는 분석 증거이며 package로 설치/import하지 않았다.

## 8. 한계

원함수의 word spacing과 단일subtoken decode 정의를 보존한다. human reading metric 미실행,
새학습효과/대회적격·AoA나EWoK 완료를 주장하지 않는다. AoA는 같은 모델의 학습시점계열이
필요하고 현재native595 source는 마지막4543step만 저장한다. EWoK 전체자료는 사용자 약관동의가 필요하다.

## 9. 이력

현재 source/data/dependency 분석 완료/실제 원예측NOT_RUN이다. 기존 문항은 재취득하지 않았다.
필요한 package·동의·checkpoint 선결은 사용자161의 최종 보고 질문에 남긴다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 10. 11월 18일 저장 예측의 회귀 재현

네 모델의 예측이 모두 확보됐다. 기존 예측과 공식 CSV는 고정한 채 원 `run.py`의 통계 부분을 CPU에서 실행하기로 했다. 원본의 회귀식, 행별 결측 처리, 상관계수, 보고 집계는 그대로 사용하고, 회귀 계산은 현재 평가 환경에 있는 NumPy와 SciPy로 수행한다. 결과는 원본 `statsmodels` 실행과 별도로 회귀 재현으로 기록한다.

| 경로 | 판단 |
|---|---|
| 원 패키지 사용 | 라이브러리 수준 비교에 필요하다. 현재 환경에 두 패키지가 없어 설치 결정을 기다린다. |
| 공식을 고정하고 저장 예측으로 CPU 재현 | 현재 수행한다. 새 계산 경로는 이 실험의 좁은 감사 도구에 둔다. |
| 모델 재추론 | 원 CSV와 GPU 예측의 일치 및 종결 증거가 확보되어 중복이다. |

공식 원본 blob과 SHA, CSV·예측 SHA, 원행과 이전 단어 결측을 확인한다. 전체 회귀에서 NumPy SVD와 SciPy 피벗 QR의 계수·분산·적합값이 허용차 이내이며 설계 행렬이 완전열계수인지 확인한다. R²·AIC·t·p와 원 집계를 보존한다. 예상은 두 수치 경로가 일치한다는 것이다. 모델별 점수 방향은 정하지 않았다. 예측 입력은 평가 전용이다. 실행기는 모델을 불러오지 않으며 패키지 설치를 요구하지 않는다.

## 11. 11월 20일 저장 예측의 공식 OLS 진입점

저장 예측을 원 통계 코드의 실제 OLS에 전달하는 CPU 진입점을 검증했다. 원식과 표본 지문 176개는 회귀 재현과 일치했다. 기존 평가 환경의 `statsmodels`·`patsy`가 갖춰지면 저장 예측을 그대로 읽어 공식 보고를 발행한다. 실제 점수는 대기다. [결과101 §707](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-reading-official-saved-ols)
