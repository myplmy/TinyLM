# TinyLM Stage2 A04 v46 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v46.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `5DC92928233AD47F1091D57DA139DD5540AED86084DE7C3A48B8480071775A50`
- 수정 후 SHA-256: `E4EBD4529AFC5D266A713C1ECBECFA96A8F5B437661B10A73E4E202479650567`
- 산림 예찰·병해충 조사·방제·산불 대응·복구 개념군의 150행을 한 행씩 읽고, 각 locator의 `primary`와 `text`만 직접 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술과 후속 교정

- 번호·대시·절단 어근·임의 합성어가 없는 실제 산림 관리 명사구로 primary를 다시 썼다. 예찰, 유인 트랩, 병반, 고사목, 약제, 산불 대피로처럼 현장에서 구별 가능한 대상을 사용했다.
- text에는 관찰할 사실, 작업 중단 또는 판단 조건, 담당자의 조치, 다음 확인·복구 결과가 읽히도록 넣었다. 기록 시각이나 변경 순서만 나열하는 불투명한 문장은 쓰지 않았다.
- 수정 전 `primary+은/는` 시작이 150/150으로 diversity HOLD였으므로, 뜻에 맞게 관찰·조건·행동으로 시작하는 문장을 섞어 40/150(26.67%)으로 낮췄다.
- 첫 파일 평균이 36.15로 하한보다 낮아, 짧지만 실제 판단 근거가 필요한 30행에 사진·위치·재측정·안전·대조군·재개 조건을 개별적으로 보완했다. 이후 4행의 `조사이며`식 설명도 사람이 읽기 자연스러운 `조사라고 하며` 또는 `확인하는 일`로 직접 다듬었다.
- 전역 치환·템플릿 복사·suffix 번호 부여·source 전체 재직렬화는 사용하지 않았다.

## v46 파일 단위 결과

| 항목 | 결과 |
|---|---:|
| records | 150 |
| JSONL parse·BOM·빈 primary/text | 0 / 0 / 0 |
| primary literal 누락 | 0 |
| exact primary 중복 / exact text 중복 | 0 / 0 |
| relations 개수·내부중복·통제어휘 오류 | 0 / 0 / 0 |
| 자연성 warning | 0행 / 0건 |
| 직접 수정 대상 / ChatGPT·사용자 검토 대기 | 0 / 0 / 0 |
| `primary+은/는` 시작 | 40 / 150 (26.67%) — 파일 기준 범위 내 |
| tokens+EOS / 평균 / 최소 / 최대 | 5,772 / 38.48 / 26 / 57 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 4 |
| classification | 27 |
| boundary | 74 |
| contrast | 0 |
| comparison | 36 |
| function | 70 |
| role | 14 |
| process | 150 |
| state | 150 |
| attribute | 75 |
| other | 0 |

`other`가 없으므로 v46의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.660074446`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.

### 토큰 평균 해석

- v46 평균은 `38.48`로 공용 source 감사기의 파일 평균 하한 `37.4625`를 통과했고, 현재 A04 관측 파일 평균 범위 `38.37–46.58` 안에 있다.
- 공용 source 감사기의 고정 `files_passing` 계산은 `37.4625–45.7875`을 쓰므로, 기존 v32 평균 `46.58` 하나를 범위 밖으로 세어 68/69로 표시한다. 이는 v46 수정 실패가 아니라 기존 범위 정의 불일치이며, 공용 감사기·v32는 이번 허용범위 밖이어서 수정하지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작: 2,643 / 10,350 = `25.54%`, 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 19파일(v47–v57, v59–v64, v68–v69)에 남아 있다. ChatGPT 검토 대기 22건 중 HARD 대상은 19건이며, 사용자 검토 대기는 0건이다.
- 이 문형 gate는 구조 `PASS`와 별개다. 따라서 v46 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v46_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v46_PostDirectReview_r1_2026-09-14.json` — 전면 직접 재서술 뒤 파일 단위 결과
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v46_PostDirectReview_r2_2026-09-14.json` — token 보완 뒤 파일 단위 결과
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v46_PostDirectReview_r3_2026-09-14.json` — 조사 후보 4행을 직접 다듬은 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV46DirectReview_r1_2026-09-14.json` — 초기 token 하한 미달 확인
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV46DirectReview_r3_2026-09-14.json` — 최종 token gate 결과
- `machine/TinyLM_Stage2_A04_StructureIndependent_AfterV46DirectReview_r3_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_SimilarityIndependent_AfterV46DirectReview_r3_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_AfterV46DirectReview_r4_2026-09-14.json`

다음 직접 작업 대상은 v47이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
