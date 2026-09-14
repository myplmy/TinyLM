# TinyLM Stage2 A04 v48 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v48.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `3764FCD8CBF90C8693BAD6D38D4D9EFF9C0ED7F83A11D789DCA87D01FE244D20`
- 수정 후 SHA-256: `821EF85460767B1A9B2BEEFDED190D639E9FBA2A85A132E84905496B05439984`
- 발효 생산의 배양·멸균·세정·품질·포장·냉장·회수 개념군 150행을 한 행씩 읽고, 각 locator의 `primary`와 `text`만 직접 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술과 후속 교정

- 기계적인 `발효공정 X 안정/이탈` 표기를 발효조 온도 확인, 배양액 산소 부족, 무균 연결 불량, 세정제 잔류, 제품 회수 범위 확인 같은 실제 제조·품질 관리 개념으로 바꿨다.
- 각 text에는 관찰 대상, 위험 또는 판단 조건, 현장 조치와 다음 확인이 드러나게 썼다. 배치번호·시각 보존이나 순서 변경만 나열하는 문장은 제거했다.
- 수정 전 `primary+은/는` 시작은 150/150으로 diversity HOLD였다. 뜻을 바꾸지 않고 관찰 대상·작업자·절차로 시작하는 문장을 32행에 개별적으로 적용해 42/150(28.00%)으로 낮췄다.
- 문형 조정 뒤에도 token 평균은 `37.94`로 공용 하한 `37.4625`를 넘었다. 전역 치환·템플릿 복사·suffix 번호 부여·source 전체 재직렬화는 사용하지 않았다.

## v48 파일 단위 결과

| 항목 | 결과 |
|---|---:|
| records | 150 |
| JSONL parse·BOM·빈 primary/text | 0 / 0 / 0 |
| primary literal 누락 | 0 |
| exact primary 중복 / exact text 중복 | 0 / 0 |
| relations 개수·내부중복·통제어휘 오류 | 0 / 0 / 0 |
| 자연성 warning | 0행 / 0건 |
| 직접 수정 대상 / ChatGPT·사용자 검토 대기 | 0 / 0 / 0 |
| `primary+은/는` 시작 | 42 / 150 (28.00%) — 파일 기준 범위 내 |
| tokens+EOS / 평균 / 최소 / 최대 | 5,691 / 37.94 / 29 / 46 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 0 |
| classification | 31 |
| boundary | 75 |
| contrast | 0 |
| comparison | 35 |
| function | 75 |
| role | 9 |
| process | 150 |
| state | 150 |
| attribute | 75 |
| other | 0 |

`other`가 없으므로 v48의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.657654143`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.

### 토큰 평균 해석

- v48 평균은 `37.94`로 공용 source 감사기의 파일 평균 하한 `37.4625`를 통과했고, 현재 A04 관측 파일 평균 범위 `37.94–46.58` 안에 있다.
- 공용 source 감사기의 고정 `files_passing` 계산은 `37.4625–45.7875`을 쓰므로, 기존 v32 평균 `46.58` 하나를 범위 밖으로 세어 68/69로 표시한다. 이는 v48 수정 실패가 아니라 기존 범위 정의 불일치이며, 공용 감사기·v32는 이번 허용범위 밖이어서 수정하지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작: 2,429 / 10,350 = `23.47%`, 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 17파일(v49–v57, v59–v64, v68–v69)에 남아 있다. ChatGPT 검토 대기 20건 중 HARD 대상은 17건이며, 사용자 검토 대기는 0건이다.
- 이 문형 gate는 구조 `PASS`와 별개다. 따라서 v48 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v48_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v48_PostDirectReview_r1_2026-09-14.json` — 전면 직접 재서술 뒤 파일 단위 결과
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v48_PostDirectReview_r2_2026-09-14.json` — 문형 비율 교정 뒤 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV48DirectReview_r1_2026-09-14.json` — 전면 직접 재서술 뒤 token 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV48DirectReview_r2_2026-09-14.json` — 최종 token gate 결과
- `machine/TinyLM_Stage2_A04_StructureIndependent_AfterV48DirectReview_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_SimilarityIndependent_AfterV48DirectReview_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_AfterV48DirectReview_r1_2026-09-14.json`

다음 직접 작업 대상은 v49이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
