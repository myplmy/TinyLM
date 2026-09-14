# TinyLM Stage2 A04 v42 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v42.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `74AC8E34692641FCCE8D8312D14535907D36C815543E54BEF7C845113535B192`
- 수정 후 SHA-256: `20D926EA11EDBEB5A6D323FB6718F1B2EDC7FFF1AF9FAD0042862F2ED4F9EB0F`
- 클린룸 공조·오염·공정수·가스·장비·복구 개념군의 150행을 직접 읽고 `primary`와 `text`만 locator 단위로 재서술했다. 행 순서와 `relations`는 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술 내용

- 기계적 `촉발·억제 조건` 문형과 붙여 쓴 합성어를, 실제 클린룸 운영에서 이해할 수 있는 원인·판단·조치 문장으로 바꿨다.
- 예를 들어 차압 이탈, 출입복·자재 반입, 필터·국소 배기, 공정수·가스, 웨이퍼 이송, 수율 재검, 재가동·사건 기록을 각각 다른 상황으로 설명했다.
- 전역 치환, 템플릿 복사, 숫자 접미사, 대시 qualifier는 사용하지 않았다.

## v42 파일 단위 결과

| 항목 | 결과 |
|---|---:|
| records | 150 |
| JSONL parse·빈 primary/text | 0 |
| primary literal 누락 | 0 |
| exact primary 중복 / exact text 중복 | 0 / 0 |
| relations 개수·내부중복·통제어휘 오류 | 0 / 0 / 0 |
| 자연성 warning | 0행 / 0건 |
| 직접 수정 대상 / 사용자 검토 대기 | 0 / 0 |
| `primary+은/는` 시작 | 11 / 150 (7.33%) — 파일 기준 범위 내 |
| tokens+EOS / 평균 / 최소 / 최대 | 6,020 / 40.13 / 33 / 50 |
| 현재 A04 파일 평균 허용범위 | 38.37–46.58 — 통과 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 44 |
| classification | 43 |
| boundary | 52 |
| contrast | 6 |
| comparison | 6 |
| function | 65 |
| role | 8 |
| process | 150 |
| state | 150 |
| attribute | 76 |
| other | 0 |

`other`가 없으므로 v42의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.661403268`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작: 3,162 / 10,350 = `30.5507%`, `REVIEW_DIVERSITY`.
- HARD 다양성 재서술 대상은 23파일이다: v43–v57, v59–v64, v68–v69.
- ChatGPT 검토 대기 27건 중 위 HARD 대상이 23건이며, 사용자 검토 대기는 0건이다.
- 이 문형 gate는 구조 PASS와 별개다. 따라서 v42 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v42_PostDirectReview_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV42DirectReview_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_Independent_Structure_AfterV42Final_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_Independent_Similarity_AfterV42Final_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_AfterV42Final_r1_2026-09-14.json`

다음 직접 작업 대상은 v43이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
