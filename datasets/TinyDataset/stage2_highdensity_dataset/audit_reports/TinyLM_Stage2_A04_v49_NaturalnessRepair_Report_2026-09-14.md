# TinyLM Stage2 A04 v49 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v49.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `4D3E2B05BBEBC309B5B431C5BF998CD48A8E46F4FC23C6B9A6512F40CF78E21E`
- 수정 후 SHA-256: `F2E8DFF512769EB2913C6EC41AE8D607D9AD16AB47B2F9277A7ABDEFB5FF88F2`
- 데이터센터의 전원 전환·냉수 및 공조·UPS·비상 발전기·배전반·변압기·서버 랙·보안·정비·비상 냉각 상태 전이 150행을 한 행씩 읽고, 각 locator의 `primary`와 `text`만 직접 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술과 행별 교정

- 붙여쓴 내부 표제어와 기록 중심 설명을 `예비 전원 전환 대기`, `냉수 순환 펌프 기동`, `UPS 배터리 저전압 보호`, `비상 발전기 출력 안정`, `안전 재기동 조건 확인`처럼 실제 운영에서 이해할 수 있는 짧은 명사구로 바꿨다.
- 각 text에는 관찰 대상, 판단 조건, 담당자의 조치, 다음 확인 또는 결과가 드러나도록 직접 썼다. 시각·번호·순서만 남기는 불투명한 서술은 제거했다.
- 수정 전 `primary+은/는` 시작은 136/150(90.67%)으로 diversity HOLD였다. 각 행을 다른 문형으로 재서술해 최종 0/150(0.00%)으로 낮췄다.
- 1차 재서술 뒤 평균 token이 37.00으로 하한 37.4625에 못 미쳐, 조사 후보 2건(`…복구이다`)과 `작업을 다시 열 속도` 비문을 직접 교정하고 조건·조치를 보강했다. 최종 평균은 38.41이다.
- 전역 치환, 템플릿 대량 치환, suffix 번호 부여, source 전체 재직렬화는 사용하지 않았다.

## v49 파일 단위 결과

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
| tokens+EOS / 평균 / 최소 / 최대 | 5,762 / 38.41 / 31 / 51 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 16 |
| classification | 43 |
| boundary | 52 |
| contrast | 0 |
| comparison | 37 |
| function | 69 |
| role | 30 |
| process | 150 |
| state | 150 |
| attribute | 53 |
| other | 0 |

`other`가 없으므로 v49의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.657673486`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.
- source 감사의 5어절 반복 표시는 A04 전체에서 419유형·918 할당으로 남는다. 이는 n-gram 빈도 신호이며, 독립 TF-IDF/Jaccard 임계치 초과와 별개의 advisory 수치다. v49 개별 재서술의 유사도 gate는 모두 통과했다.

### 토큰 평균 해석

- v49 평균은 `38.41`로 공용 source 감사기의 파일 평균 하한 `37.4625`를 통과했다.
- A04 전역 token 평균은 `42.76`이다. 공용 감사기는 기존 v32 평균 `46.58`을 고정 상한 `45.7875` 밖으로 세어 `files_passing=68/69`로 표시한다. v32와 공용 감사기 범위 정의는 이번 v49 허용 범위 밖이므로 수정하지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작: 2,293 / 10,350 = `22.15%`, 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 16파일(v50–v57, v59–v64, v68–v69)에 남아 있다. v31은 67/150(45.00%)의 `REVIEW_DIVERSITY`다. ChatGPT 검토 대기 19건 중 HARD 대상은 16건이며, 사용자 검토 대기는 0건이다.
- 이 문형 gate는 구조 `PASS`와 별개다. 따라서 v49 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v49_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v49_PostDirectReview_2026-09-14.json` — 1차 재서술 결과
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v49_FinalDirectReview_2026-09-14.json` — token·조사 교정 뒤 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_v49_FinalDirectReview_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_Final_v49_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_Final_v49_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_Global_Post_v49_2026-09-14.json`

다음 직접 작업 대상은 v50이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
