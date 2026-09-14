# TinyLM Stage2 A04 v43 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v43.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `C8C2D19413CEF5854B6FDC6224C6F70D53D7CBDF71BC7410BA83AF4B18CF952A`
- 수정 후 SHA-256: `BB1E5FDCC6861F2E48B907EC2192FA1DBE2F636A8081C526213602E86F9F56CD`
- 지역난방의 보일러·펌프·배관·밸브·수질·수용가·축열조 개념군 150행을 직접 읽고, 각 locator의 `primary`와 `text`만 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술 내용

- `도시열공급`, `전이`, `계보`, `가역·비가역` 같은 기계적 표지 중심 표현을 지역난방 현장에서 이해할 수 있는 점검·전환·보수·인계·민원 처리 문장으로 바꿨다.
- 각 설명은 원인 또는 관찰, 담당자의 판단·조치, 결과가 드러나도록 썼다. 예를 들어 예비 열원 전환, 누수·수격 보수, 계측 중단, 우회 공급, 수질 처리, 수요 조절을 서로 다른 상황으로 설명했다.
- 구조 계약상 `text` 안의 `primary` literal을 150행 모두 다시 확인했다. 고유사였던 100·150행 쌍은 150행을 `복구 가능 여부 판단`으로 별도 재서술했다.
- 전역 치환, 템플릿 복사, 숫자 접미사, 대시 qualifier는 사용하지 않았다.

## v43 파일 단위 결과

| 항목 | 결과 |
|---|---:|
| records | 150 |
| JSONL parse·빈 primary/text | 0 |
| primary literal 누락 | 0 |
| exact primary 중복 / exact text 중복 | 0 / 0 |
| relations 개수·내부중복·통제어휘 오류 | 0 / 0 / 0 |
| 자연성 warning | 0행 / 0건 |
| 직접 수정 대상 / ChatGPT·사용자 검토 대기 | 0 / 0 / 0 |
| `primary+은/는` 시작 | 1 / 150 (0.67%) — 파일 기준 범위 내 |
| tokens+EOS / 평균 / 최소 / 최대 | 6,071 / 40.47 / 31 / 57 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 41 |
| classification | 41 |
| boundary | 46 |
| contrast | 4 |
| comparison | 18 |
| function | 60 |
| role | 9 |
| process | 150 |
| state | 150 |
| attribute | 81 |
| other | 0 |

`other`가 없으므로 v43의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.660861542`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.
- v43 내부 같은 relations 집합의 Jaccard 후보 1쌍(100·150행)은 직접 재서술 뒤 0건이 됐으며, ChatGPT 및 사용자 검토 대기는 모두 0건이다.

### 토큰 평균 해석

- v43 평균은 `40.47`로 현재 A04 관측 파일 평균 범위 `38.37–46.58` 안에 있다.
- 공용 source 감사기의 고정 `files_passing` 계산은 `37.4625–45.7875`을 쓰므로, 기존 v32 평균 `46.58` 하나를 범위 밖으로 세어 68/69로 표시한다. 이는 v43 수정 실패가 아니라 기존 범위 정의 불일치이며, 공용 감사기·v32는 이번 허용범위 밖이어서 수정하지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작: 3,013 / 10,350 = `29.11%`, 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 다만 파일별 `HOLD_REWRITE_DIVERSITY`는 22파일(v44–v57, v59–v64, v68–v69)에 남아 있다. ChatGPT 검토 대기 25건 중 HARD 대상은 22건이며, 사용자 검토 대기는 0건이다.
- 이 문형 gate는 구조 `PASS`와 별개다. 따라서 v43 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v43_PostDirectReview_r1_2026-09-14.json` — 150행 직접 재서술 뒤 100·150행 고유사 후보를 발견한 중간 산출물
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v43_PostDirectReview_r2_2026-09-14.json` — 150행 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV43DirectReview_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_AfterV43DirectReview_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_AfterV43DirectReview_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_AfterV43DirectReview_r1_2026-09-14.json`

다음 직접 작업 대상은 v44다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
