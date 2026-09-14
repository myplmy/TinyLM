# TinyLM Stage2 A04 v57 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v57.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `3F009F32A2952162903ED7AAD347E1410184656BA6B24D4F5CF437F09B6B0AE3`
- 수정 후 SHA-256: `8F18D5AEA07E7E2912F8F18D858DACC45931EE696787D588B4830538DE9B7AD1`
- 수술실 배정, 환자 확인, 마취, 멸균, 공조, 감염 관리, 회복실 관찰, 퇴원·시설 복구를 다룬 150행을 한 행씩 직접 읽고 `primary`와 `text`를 재서술했다.
- 행 순서와 `relations` 배열은 보존했다. A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 직접 재서술과 후속 의미 교정

- 붙여 쓴 표제어와 기록 중심 문구를 `수술 전 환자 신원 확인`, `수술실 양압 저하 대응`, `수술실 환기 이상 대응`, `회복실 위험 신호 대응`, `수술 후 인계 완료`처럼 실제 의료진이 이해할 수 있는 짧은 명사구로 바꿨다.
- text에는 환자·설비 상태를 무엇으로 확인하는지, 어떤 위험 조건에서 누가 무엇을 판단·조치하는지, 그 결과 수술·이송·운영이 어떻게 달라지는지가 드러나도록 했다.
- 수정 전 `primary+은/는` 시작은 137/150(91.33%)으로 `HOLD_REWRITE_DIVERSITY`였다. 각 행의 문형을 개별로 바꾼 최종 결과는 0/150(0.00%)이다.
- 1차 전수 재감사에서 v45와 `수술 전 환자 확인` primary가 1건 겹치고, 양압·환기 대응 및 정상 복귀 문장 2쌍이 고유사 임계치를 넘은 것을 발견했다. v57:8, 24, 25, 54, 55만 다시 읽어 `수술 전 환자 신원 확인`과 서로 다른 설비 원인·조치가 드러나는 설명으로 개별 보정했다.
- 전역 치환, 템플릿 대량 치환, suffix 번호 부여, source 전체 재직렬화는 사용하지 않았다.

## v57 파일 단위 결과

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
| tokens+EOS / 평균 / 최소 / 최대 | 5,659 / 37.73 / 31 / 55 |

v57 평균 37.73은 공용 source 감사기의 파일 평균 허용 범위 37.4625–45.7875 안이다.

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 9 |
| classification | 33 |
| boundary | 70 |
| contrast | 0 |
| comparison | 36 |
| function | 46 |
| role | 47 |
| process | 150 |
| state | 150 |
| attribute | 59 |
| other | 0 |

`other`가 없으므로 v57의 `other_type` 상위 유형은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.656555507`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 source 감사: 69파일 / 10,350행 / 440,796 tokens+EOS / 평균 42.59. 반복 5어절은 554유형·1,199할당이다. 이는 유사도 임계치 초과와 별도인 빈도 신호다.
- `files_passing=68/69`는 이번 v57이 아니라 기존 v32 평균 46.58이 상한 45.7875 밖인 결과다. v32와 공용 감사기 범위 정의는 이번 v57 수정 범위 밖이므로 바꾸지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작은 1,302/10,350=`12.58%`로 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 8파일(v59–v64, v68–v69)에 남아 있다. v31은 67/150(44.67%)의 `REVIEW_DIVERSITY`다.
- reviewer-assist의 ChatGPT 검토 대기는 11건이며, 위 8개 HARD diversity 대상, v31 REVIEW, relations 묶음 기반 유사도 advisory 2건으로 구성된다. 사용자 검토 대기는 0건이다.
- 따라서 v57 파일은 구조·자연성·유사도 gate를 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v57_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v57_FinalDirectReview_2026-09-14.json` — 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_v57_FinalDirectReview_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_Final_v57_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_Final_v57_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_Global_Post_v57_2026-09-14.json`

다음 직접 작업 대상은 v59이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
