# TinyLM Stage2 A04 v55 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v55.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `2325C32D33DF66A362E7AEC98FFDC466BA05950F13EEB3623A135471D073F0B0`
- 수정 후 SHA-256: `9CEE27DB6760FC4B1517A937A69658C11448FDF334FB38A3599C1006DF47FA29`
- 도시 지역난방의 보일러·순환 펌프·배관·열교환기·축열조·수요처·경보·복구·비상 대응을 다룬 150행을 한 행씩 직접 읽고 `primary`와 `text`를 재서술했다.
- 행 순서와 `relations` 배열은 보존했다. A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 직접 재서술과 후속 의미 교정

- 기존의 형식적 상태 표기를 `지역난방 보일러 기동`, `지역난방 배관 누수 대응`, `지역난방 재개 전 공급 조건 확인`, `지역난방 공급 부족 재발 대응`처럼 관찰 대상과 업무 뜻이 드러나는 짧은 명사구로 고쳤다.
- 각 text에는 무엇을 살피는지, 어떤 조건에서 보류·전환·복구하는지, 누가 무엇을 조절하는지가 드러나게 했다. 기록 시각이나 변경 순서만 나열해 상태 설명을 대신하던 문구는 실제 판단·조치 문장으로 바꿨다.
- 수정 전 `primary+은/는` 시작은 96/150(64.00%)으로 `HOLD_REWRITE_DIVERSITY`였다. 전 행을 문형별로 직접 재서술해 최종 0/150(0.00%)으로 낮췄다.
- 전수 재독 후 `열원을 증원`, `밸브 순서별 확인 담당`, `재상승값`, `미복구 수요처`, `재발한 비상 상황`처럼 일상 한국어 문장으로 읽기 어색하거나 의미가 흐린 locator를 개별 보정했다. `전환 신호`를 `압력 신호`로 잘못 적은 한 행도 원래 primary의 의미와 맞게 고쳤다.
- 파일 안에서 의미가 지나치게 겹치던 `공급 단계 완료 확인`과 `공급 단계 상태 확인`은 서로 다른 판단 결과가 드러나게 분리해 독립 TF-IDF 상위쌍에서도 제거했다.
- 전역 치환, 템플릿 대량 치환, suffix 번호 부여, source 전체 재직렬화는 사용하지 않았다.

## v55 파일 단위 결과

| 항목 | 결과 |
|---|---:|
| records | 150 |
| JSONL parse·BOM·빈 primary/text | 0 / 0 / 0 |
| primary literal 누락 | 0 |
| exact primary 중복 / exact text 중복 | 0 / 0 |
| relations 개수·내부중복·통제어휘 오류 | 0 / 0 / 0 |
| 자연성 warning | 0행 / 0건 |
| 직접 수정 대상 / ChatGPT·사용자 검토 대기 | 0 / 0 / 0 |
| `primary+은/는` 시작 | 0 / 150 (0.00%) — 파일 기준 범위 내 |
| tokens+EOS / 평균 / 최소 / 최대 | 6,460 / 43.07 / 35 / 55 |

v55 평균 43.07은 공용 source 감사기의 파일 평균 허용 범위 37.4625–45.7875 안이다.

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 14 |
| classification | 45 |
| boundary | 48 |
| contrast | 0 |
| comparison | 35 |
| function | 62 |
| role | 41 |
| process | 150 |
| state | 150 |
| attribute | 55 |
| other | 0 |

`other`가 없으므로 v55의 `other_type` 상위 유형은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.656072088`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 source 감사: 69파일 / 10,350행 / 442,088 tokens+EOS / 평균 42.71. 반복 5어절은 530유형·1,146할당, 반복 4어절 도입부는 67유형이다. 이는 유사도 임계치 초과와 별도인 빈도 신호다.
- `files_passing=68/69`는 이번 v55가 아니라 기존 v32 평균 46.58이 상한 45.7875 밖인 결과다. v32와 공용 감사기 범위 정의는 이번 v55 수정 범위 밖이므로 바꾸지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작은 1,572/10,350=`15.19%`로 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 10파일(v56–v57, v59–v64, v68–v69)에 남아 있다. v31은 67/150(44.67%)의 `REVIEW_DIVERSITY`다.
- reviewer-assist의 ChatGPT 검토 대기는 13건이며, 위 10개 HARD diversity 대상, v31 REVIEW, relations 묶음 기반 유사도 advisory 2건으로 구성된다. 사용자 검토 대기는 0건이다.
- 따라서 v55 파일은 구조·자연성·유사도 gate를 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v55_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v55_FinalDirectReview_2026-09-14.json` — 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_v55_FinalDirectReview_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_Final_v55_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_Final_v55_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_Global_Post_v55_2026-09-14.json`

다음 직접 작업 대상은 v56이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
