# TinyLM Stage2 A04 v44 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v44.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `BDC89172C69C47EF4E0E69A0AEC92DDBA8CF966468223F3F8E0EFC47CCD8E3E3`
- 수정 후 SHA-256: `1DE27D835F5EBD56A26ACA18A202827D92478AB52A19A69E3E36C5029EB8DE52`
- 해양 부표의 수온·파랑·조류·계류·전원·센서·수질·통신·폭풍·회수 개념군 150행을 한 행씩 읽고, 각 locator의 `primary`와 `text`만 직접 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술 내용

- 기계적으로 반복되던 `primary은/는` 도입과 불투명한 상태 기록 표현을, 관측값·원인·담당자의 판단·조치·결과가 이어지는 해양 관측 현장 문장으로 바꿨다.
- 수온·파랑·수질 경보, 저전력 관측, 계류 장력, 표류 추정, 센서 보정, 통신 복구, 회수와 재배치가 서로 다른 상황을 설명하도록 분리했다.
- 후속 직접 검토에서 의미가 겹친 38·86행은 일반 관제 수신 대기와 수질 경보 수신 대기로 구분해 86행을 재서술했다. 독립 구조 감사에서 찾은 24·66행의 exact primary 중복은 66행을 `해양 부표 저산소 원인 확인`으로 바꾸어 경보 발령과 원인 판단을 분리했다.
- `text` 안의 `primary` literal, 숫자 접미사·대시 qualifier 부재, 통제 relations 보존을 150행 모두 다시 확인했다. 전역 치환·템플릿 복사·전체 재직렬화는 사용하지 않았다.

## v44 파일 단위 결과

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
| tokens+EOS / 평균 / 최소 / 최대 | 5,992 / 39.95 / 32 / 56 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 31 |
| classification | 52 |
| boundary | 51 |
| contrast | 5 |
| comparison | 17 |
| function | 51 |
| role | 11 |
| process | 150 |
| state | 150 |
| attribute | 82 |
| other | 0 |

`other`가 없으므로 v44의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.660536516`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.

### 토큰 평균 해석

- v44 평균은 `39.95`로 현재 A04 관측 파일 평균 범위 `38.37–46.58` 안에 있다.
- 공용 source 감사기의 고정 `files_passing` 계산은 `37.4625–45.7875`을 쓰므로, 기존 v32 평균 `46.58` 하나를 범위 밖으로 세어 68/69로 표시한다. 이는 v44 수정 실패가 아니라 기존 범위 정의 불일치이며, 공용 감사기·v32는 이번 허용범위 밖이어서 수정하지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작: 2,863 / 10,350 = `27.66%`, 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 다만 파일별 `HOLD_REWRITE_DIVERSITY`는 21파일(v45–v57, v59–v64, v68–v69)에 남아 있다. ChatGPT 검토 대기 24건 중 HARD 대상은 21건이며, 사용자 검토 대기는 0건이다.
- 이 문형 gate는 구조 `PASS`와 별개다. 따라서 v44 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v44_PostDirectReview_r1_2026-09-14.json` — 38·86행 고유사 후보를 찾은 중간 산출물
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v44_PostDirectReview_r2_2026-09-14.json` — 고유사 쌍 해소 뒤 파일 단위 결과
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v44_PostDirectReview_r3_2026-09-14.json` — exact primary 중복 해소 뒤 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV44DirectReview_r2_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_AfterV44DirectReview_r2_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_AfterV44DirectReview_r1_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_AfterV44DirectReview_r1_2026-09-14.json`

다음 직접 작업 대상은 v45다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
