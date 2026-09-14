# TinyLM Stage2 A04 v56 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v56.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `3F0FA2221A2397074303EE254BFBF348009C978217DE5ECDA3856370BCFE8DCE`
- 수정 후 SHA-256: `9AEBF7749A29BD17C328908E54B9FA0B993B5A1DD8A234D22F30DD505864D8CE`
- 해양 부표의 관측·수온·파고·풍속·조류·위치·통신·전원·수질·계류·경보·회수·분석·보고를 다룬 150행을 한 행씩 직접 읽고 `primary`와 `text`를 재서술했다.
- 행 순서와 `relations` 배열은 보존했다. A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 직접 재서술과 후속 의미 교정

- 붙여 쓴 표제어를 `해양 부표 관측 대기`, `해양 부표 위치 이탈 경보`, `해양 부표 파고 자료 누락 보류`, `해양 부표 회수선 접근`, `해양 부표 보고서 승인`처럼 실제 관측·운영 업무를 가리키는 명사구로 바꿨다.
- 각 text에는 무엇을 관찰하는지, 어떤 조건에서 경보·보류·복구가 일어나는지, 담당자가 무엇을 조절하거나 판단하는지가 드러나게 했다. 기존의 “보존하고 변경한다”식 기록 중심 문장은 해양 관측자가 이해할 수 있는 조치와 결과 설명으로 교체했다.
- 수정 전 `primary+은/는` 시작은 133/150(88.67%)으로 `HOLD_REWRITE_DIVERSITY`였다. 전 행을 직접 읽고 문형을 나누어 최종 0/150(0.00%)으로 낮췄다.
- 1차 전수 재감사에서 기존 A04 v44와의 exact primary 중복 1건, v56 내부 exact primary 중복 2건을 발견했다. `계류 장력 저하`, `탁도 상승 대응`, `수질 지표 안정`을 해당 행의 실제 조건이 드러나는 고유 primary로 개별 보정한 뒤 구조 감사를 다시 실행했다.
- 전역 치환, 템플릿 대량 치환, suffix 번호 부여, source 전체 재직렬화는 사용하지 않았다.

## v56 파일 단위 결과

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
| tokens+EOS / 평균 / 최소 / 최대 | 5,870 / 39.13 / 30 / 53 |

v56 평균 39.13은 공용 source 감사기의 파일 평균 허용 범위 37.4625–45.7875 안이다.

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 13 |
| classification | 49 |
| boundary | 46 |
| contrast | 0 |
| comparison | 34 |
| function | 61 |
| role | 41 |
| process | 150 |
| state | 150 |
| attribute | 56 |
| other | 0 |

`other`가 없으므로 v56의 `other_type` 상위 유형은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.656148356`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 source 감사: 69파일 / 10,350행 / 441,712 tokens+EOS / 평균 42.68. 반복 5어절은 547유형·1,184할당, 반복 4어절 도입부는 68유형이다. 이는 유사도 임계치 초과와 별도인 빈도 신호다.
- `files_passing=68/69`는 이번 v56이 아니라 기존 v32 평균 46.58이 상한 45.7875 밖인 결과다. v32와 공용 감사기 범위 정의는 이번 v56 수정 범위 밖이므로 바꾸지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작은 1,439/10,350=`13.90%`로 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 9파일(v57, v59–v64, v68–v69)에 남아 있다. v31은 67/150(44.67%)의 `REVIEW_DIVERSITY`다.
- reviewer-assist의 ChatGPT 검토 대기는 12건이며, 위 9개 HARD diversity 대상, v31 REVIEW, relations 묶음 기반 유사도 advisory 2건으로 구성된다. 사용자 검토 대기는 0건이다.
- 따라서 v56 파일은 구조·자연성·유사도 gate를 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v56_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v56_FinalDirectReview_2026-09-14.json` — 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_v56_FinalDirectReview_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_Final_v56_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_Final_v56_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_Global_Post_v56_2026-09-14.json`

다음 직접 작업 대상은 v57이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
