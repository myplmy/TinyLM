# TinyLM Stage2 A04 v45 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v45.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `F3E6FF038593FE27EBA9F35F62907F70FF85667D7350A8ADF34C69590C9522BB`
- 수정 후 SHA-256: `9BA08B4B5003EC97D29D032D3DAD89441A1EA32FE3910356826FBE9C9D34B92E`
- 수술실 운영·환자 확인·감염관리·공조·수혈·기구 계수·회복실·설비 대응 개념군 150행을 한 행씩 읽고, 각 locator의 `primary`와 `text`만 직접 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술과 후속 교정

- `안정`, `이탈`, `피드백`을 기계적으로 붙인 명사구를 수술실에서 실제로 말하는 수술 전 확인, 멸균 포장 손상, 수혈 정보 불일치, 회복실 퇴실 보류, 예비 장비 전환 같은 개념으로 바꿨다.
- 각 설명에 관찰할 사실, 담당자의 판단·조치, 환자 안전 또는 다음 단계의 결과가 드러나도록 썼다. 같은 `X은/는` 도입에 치우치지 않도록 10행의 문장 시작도 의미에 맞게 바꿨다.
- 첫 파일 단위 검사에서 64행의 primary literal 누락을 발견해 직접 고쳤다. 50/150이던 `primary+은/는` 시작은 40/150(26.67%)으로 낮췄다.
- 첫 token 감사에서 평균 `37.39`가 공용 하한 `37.4625`보다 0.07 낮게 나와, 설명이 짧아 실제 판단 근거가 더 필요한 15행에만 환자 준비·전원 지속 시간·검사 위치·관찰 인력 등 의미 있는 맥락을 보완했다. 최종 평균은 `38.55`다.
- 독립 구조 감사에서 65행 primary가 v69 56행과 겹친 것을 찾고, v45만 `수술실 입실 전 보호복 점검`으로 더 구체화했다. 전역 치환·템플릿 복사·전체 재직렬화는 사용하지 않았다.

## v45 파일 단위 결과

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
| tokens+EOS / 평균 / 최소 / 최대 | 5,782 / 38.55 / 30 / 51 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 13 |
| classification | 19 |
| boundary | 74 |
| contrast | 0 |
| comparison | 30 |
| function | 59 |
| role | 30 |
| process | 150 |
| state | 150 |
| attribute | 75 |
| other | 0 |

`other`가 없으므로 v45의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.661214155`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.

### 토큰 평균 해석

- v45 평균은 `38.55`로 현재 A04 관측 파일 평균 범위 `38.37–46.58` 안에 있다.
- 공용 source 감사기의 고정 `files_passing` 계산은 `37.4625–45.7875`을 쓰므로, 기존 v32 평균 `46.58` 하나를 범위 밖으로 세어 68/69로 표시한다. 이는 v45 수정 실패가 아니라 기존 범위 정의 불일치이며, 공용 감사기·v32는 이번 허용범위 밖이어서 수정하지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작: 2,753 / 10,350 = `26.60%`, 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 다만 파일별 `HOLD_REWRITE_DIVERSITY`는 20파일(v46–v57, v59–v64, v68–v69)에 남아 있다. ChatGPT 검토 대기 23건 중 HARD 대상은 20건이며, 사용자 검토 대기는 0건이다.
- 이 문형 gate는 구조 `PASS`와 별개다. 따라서 v45 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v45_PreDirectReview_2026-09-14.json` — 수정 전 150/150 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v45_PostDirectReview_r1_2026-09-14.json` — literal 누락과 문형 review를 찾은 중간 산출물
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v45_PostDirectReview_r2_2026-09-14.json` — 문형 비율 교정 뒤 파일 단위 결과
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v45_PostDirectReview_r3_2026-09-14.json` — 의미 보완 뒤 파일 단위 결과
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v45_PostDirectReview_r4_2026-09-14.json` — cross-file exact primary 중복 해소 뒤 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV45DirectReview_r1_2026-09-14.json` — 초기 token 하한 미달 확인
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV45DirectReview_r3_2026-09-14.json` — 최종 token gate 결과
- `machine/TinyLM_Stage2_A04_IndependentStructure_AfterV45DirectReview_r2_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_AfterV45DirectReview_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_AfterV45DirectReview_r1_2026-09-14.json`

다음 직접 작업 대상은 v46이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
