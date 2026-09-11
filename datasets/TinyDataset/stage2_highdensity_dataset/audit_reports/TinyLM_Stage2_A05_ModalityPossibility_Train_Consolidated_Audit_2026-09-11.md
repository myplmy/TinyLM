# TinyLM Stage2 A05 가능성·양상(modality_possibility) train 통합 감사 보고서

- 감사일: 2026-09-11 (KST)
- 대상: `stage2_(15)modality_possibility_high_density_train_v01.source.jsonl`~`v69.source.jsonl`
- 범위: A05 source와 A05 전용 term registry만. validation, 포장본, checkpoint는 대상에서 제외
- 최종 판정: **PASS_SOURCE_ONLY_WITH_REVIEW_SIGNALS**
- 의미: source 구조·통제어휘·중복·결정적 조사 오류·registry 연결은 통과했다. 반복 5어절과 유사도는 공통 템플릿에서 생긴 검토 신호이며, 포장·학습 승인 자체를 의미하지 않는다.

## 1. 산출 범위와 보호 경계

- 예약: 69개 파일 × 파일당 150행 = **10,350 records** (`S2-MPH-00001`~`S2-MPH-10350`)
- 신규 생성: v11~v69, 59개 파일·8,850행
- 기존 source 보완: v01~v10은 보존을 우선하고 A05 감사에서 확인된 명확한 문장 오류만 해당 행에 반영
- A05 registry: `stage2_highdensity_dataset/sources/term_registry/stage2_(15)modality_possibility_train_registry_v01_v69.jsonl`
- registry: 10,350행, source locator coverage **100%**, `term_kind=constructed_scenario`, `review_status=audited_source_only`
- source set SHA-256: `c33b5f265f6be8cee626853fdfed26518655c1a1bf5b16e79f5be1b6f00a82e1`
- registry SHA-256: `6e3f0ddf751a52086b45535c847e91cf33195fa68ac18117205a34465e3644b5`
- `stage2_highdensity_dataset/train/`, `val/`, checkpoint, 중앙 작업원장·manifest, 공용 감사기, 다른 영역 source는 수정하지 않았다.

## 2. 개념군·생성 구성

예약된 concept family/domain과 semantic axis를 그대로 사용했다. v01~v36은 스마트 온실, 도시 상수도, 클라우드, 철도, 하천·저수지, 식품 유통, 온라인 학습, 생태 복원, 배터리 저장장치의 9개 도메인에 4개 축을 순환한다. v37~v69는 지하철·양식장·태양광·콜센터·공항·클린룸·열공급망·부표·수술실·산림·전기버스·발효·데이터센터·항만·축사·터널 등 신규 도메인과 아래 축을 배치했다.

| semantic axis | 파일 수 | 행 수 |
|---|---:|---:|
| 가능성·실제 발생·미발생의 구분 | 9 | 1,350 |
| 확률 수치와 주관 확신의 분리 | 9 | 1,350 |
| 계획·예정·예측의 시간적 지위 | 9 | 1,350 |
| 가정·반사실·조건부 결과 판정 | 9 | 1,350 |
| 불완전 관측의 가능 상태 | 4 | 600 |
| 가능 상태와 실제 관측 상태의 분리 | 6 | 900 |
| 예측 확률과 운영자 확신도의 척도 구분 | 6 | 900 |
| 예정된 조치와 발생한 사건의 시간 지위 | 6 | 900 |
| 반사실 조건에서 결과 범위 제한 | 6 | 900 |
| 정보 부족과 실질적 무작위성의 불확실성 구분 | 5 | 750 |

v11~v69의 `text` 8,850행은 primary를 그대로 포함하면서 domain·semantic axis·관측 근거·판정 경계를 교차하도록 직접 재작성했다. 감사 중 발견한 32개 행은 의미가 유지되도록 개별 재서술했고, 표지어 중복과 조사 부착 오류는 해당 표현만 수정한 뒤 registry를 재생성했다.

## 3. 구조·JSON·중복 감사

| 검사 | 결과 |
|---|---:|
| 파일 수 / 파일당 행 수 | 69 / 69개 파일 모두 150행 |
| JSONL parse·필드 집합 | 0 오류; 각 행은 `primary`, `text`, `relations`만 보유 |
| relations cardinality·내부 중복·통제 밖 값 | 0 위반; 전 행 3개 relation |
| primary literal 누락 | 0 |
| primary에 행번호/숫자 suffix | 0 |
| exact primary/text 중복 | 0 / 0 |
| NFKC·공백 정규화 primary/text 중복 | 0 / 0 |
| registry parse·필수 필드·source locator | 0 오류; coverage 100% |

### 길이·핵심구조

- 독립 source 감사 토큰식(`[A-Za-z0-9가-힣]+`) 기준 총 **206,495 tokens**, 평균 **19.952173913 tokens/record**이다. 이는 모델 tokenizer 수치가 아닌 source 비교용 평균이다.
- primary+`은/는`으로 text가 시작하는 행은 **1,702/10,350 = 16.4444%**이다. 전체는 30% review threshold 아래이며 45% HOLD를 넘지 않는다. 파일별 최대는 v05의 50/150 = **33.3333%**로 diversity review 신호만 남겼다.
- primary core: 1-token 1행, 2-token 151행, 3-token 이상 10,198행, 공백 없음 0행
- 2-token core의 동일 X1·상이 X2: 1 group / 2행; 동일 X2·상이 X1: 12 groups / 91행

## 4. relations 통제어휘 분포

13개 고정 어휘 밖의 값은 없다. 총 relation occurrence는 **31,050회**(record당 3개)이다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 38 |
| `classification` | 924 |
| `boundary` | 4,231 |
| `contrast` | 1,590 |
| `comparison` | 2,924 |
| `function` | 745 |
| `role` | 1,710 |
| `process` | 4,698 |
| `state` | 7,380 |
| `attribute` | 3,477 |
| `other` | 3,333 |

### `other`가 포함된 행의 개념 유형 상위 5가지

| 유형 | 행 수 | 해당 유형 행 수 대비 비율 |
|---|---:|---:|
| 확률·확신 | 896 | 39.8222% (896/2,250) |
| 가정·반사실·조건부 결과 | 705 | 31.3333% (705/2,250) |
| 정보 부족·불완전 관측 | 675 | 50.0000% (675/1,350) |
| 가능성·실제 발생·미발생 | 607 | 26.9778% (607/2,250) |
| 계획·예정·예측 | 450 | 20.0000% (450/2,250) |

## 5. 자연성·다양성 교차 감사

- 결정적 조사·표면 오류: **0건**. 초기에 확인된 `검수 결과 결과`, `시스템 로그 로그`, `계측 자료 자료`, marker의 `가/와` 부착 오류와 A05 legacy의 `기록를/이력를/사진를` 등을 직접 수정하고 재감사했다.
- 반복 5어절: **30종**이 2회 이상. 상위 예시는 `제안해도 승인 전에는 계획 상태로`, `승인 전에는 계획 상태로 남긴다`, `현장 조건이 바뀌면 일정도 달라진다` 등이며 각각 최대 195회다. 모두 서로 다른 primary·관측 근거를 공유하는 template-level signal로 보존하고, 의미 오류로 자동 판정하지 않았다.
- 동일 relation-set masked similarity groups: **44개**
  - raw word-set Jaccard ≥ 0.60: **166,088쌍**, 최고 0.954545455
  - primary masked word-set Jaccard ≥ 0.60: **522,136쌍**, 최고 1.000000000
  - raw char 3~5-gram TF-IDF cosine ≥ 0.72: **18,542쌍**, 최고 0.973745678
  - primary masked char 3~5-gram TF-IDF cosine ≥ 0.72: **34,221쌍**, 최고 1.000000000
  - 후보 pair 검사 818,692쌍, oversized bucket 119개
- 위 수치는 공통 modality 판정 문형·도메인 표지어가 만드는 review signal이다. reviewer-assist는 자동 source 변경을 하지 않으며, 의미가 다른 문장을 일괄 삭제·재작성하지 않았다.

## 6. reviewer-assist 결과와 수정 이력

- 정본 reviewer-assist 최종 report: `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Full_Audit_Final_2026-09-11.json`
- hard source errors: **0**
- direct rewrite targets: **0** (재감사 시 결정적 미해결 항목 없음)
- ChatGPT 우선 검토 queue: **46** (파일별 도입부 집중, X2 공유, 동일 relation-set/유사도 신호)
- user review queue: **0**
- source 변경 요약: v11~v69 text 8,850행의 다양화 재작성, 32개 record의 의미 직접 재서술, 표지어 중복 135건·표지어 조사 부착 오류 676건 및 legacy 조사·띄어쓰기 오류 정정
- 수정 후 primary·relations·행 수·registry locator를 모두 재검증했다. registry는 `audited_source_only`로 표시했으며 포장 승인 상태와 혼동하지 않는다.

## 7. 결론과 다음 경계

A05 train source v01~v69는 구조·통제 relations·primary literal·중복·registry coverage·결정적 조사 오류 gate를 모두 통과했다. 따라서 **A05 source-only 감사는 PASS**다. 반복 5어절과 고유사도 수치는 보고서에 남긴 검토 신호이므로, 향후 실제 corpus packaging 또는 학습 입력으로 승격할 때에는 해당 신호를 별도 정책으로 승인해야 한다. 이번 작업에서는 validation과 package/checkpoint를 생성하거나 수정하지 않았다.

## 8. 제안 커밋 메시지(한국어)

**제목**

`Stage2 A05 가능성·양상 train source와 전용 감사 산출물 확정`

**본문**

`- modality_possibility train source v01~v69, 10,350행과 A05 term registry를 추가한다.`
`- v11~v69 문장을 의미축별로 재작성하고 조사·표지어 중복 등 32개 행의 명확한 오류를 보완한다.`
`- 13개 relations 통제어휘, JSONL 구조, 중복·registry coverage 및 독립 token/유사도 감사를 기록한다.`
`- A05 전용 통합 감사보고서와 machine reviewer/independent 결과를 포함하며 train/val package·checkpoint·중앙 원장은 변경하지 않는다.`

## 9. 기계 부속

- `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Full_Audit_Final_2026-09-11.json`
- `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Independent_Audit_PostRewrite_2026-09-11.json`
- `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Final_2026-09-11.json`
- `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_UserReview_2026-09-11.json`
- `a05_local_work_ledger_2026-09-11.md`

## 10. 2026-09-11 재감사·재수정 결과 (사용자 재지침 이행)

> 이 절의 재감사 판정이 이전 §7의 source-only PASS 표기를 대체한다. 이전 수치는 변경 전 snapshot으로 보존하고, 아래 수치를 현재 source 상태의 정본으로 사용한다.

### 10.1 범위·보호 경계·SHA-256

- 대상은 `stage2_(15)modality_possibility_high_density_train_v01.source.jsonl`~`v69.source.jsonl`뿐이다. **69 files / 10,350 records**(파일당 150 records)는 전후 동일하다.
- 수정 전 source-set SHA-256: 독립 방식 `13ed6bf9cce2929c4a6460c3b5796b150843dcb5a01217b3f8615910c54763f1`; reviewer-assist 방식 `c33b5f265f6be8cee626853fdfed26518655c1a1bf5b16e79f5be1b6f00a82e1`.
- 수정 후 source-set SHA-256: 독립 방식 `392a816ecfb76502a6ca3984e789a4e6a3a1d01545df5789537089890afef1`; reviewer-assist 방식 `564538fe0c1a91e9444bf7b88a5a3c59597defab3fd0836a1c3088f4856d49e4`.
- 독립 digest는 정렬한 `filename|file_sha256\\n`의 SHA-256이고, reviewer digest는 reviewer-assist가 정의한 source-set digest다. 서로 다른 계산법이므로 값 자체를 상호 대체하지 않고 전후 비교에 각각 사용했다. 파일별 해시는 `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_Independent_Reaudit_2026-09-11.json`에 보존했다.
- 직접 text 재서술은 **87 records**(v01 12, v02 35, v04 15, v06 25)이며, `other`가 있는 **3,333 records**에 누락된 `other_type`만 schema 보완했다. `primary`, `relations`, 행 순서, registry locator는 변경하지 않았다. 다른 영역 source, `train/`, `val/`, manifest, checkpoint, 중앙 원장, 공용 감사기는 수정하지 않았다.

### 10.2 hard structure gate

| 검사 | 결과 |
|---|---:|
| 파일/파일당 records | 69 files / 각 150 |
| UTF-8 BOM·공백행·제어문자·JSONL parse | 0 / 0 / 0 / 0 |
| primary/text 비어 있음 | 0 / 0 |
| primary literal 누락 | 0 |
| 통제어휘 밖 relations | 0 |
| relations 개수(2~5) 오류·내부 중복 | 0 / 0 |
| `other_type` 누락·불필요 추가 | 0 / 0 |
| train `unseen_relation` | 0 |
| 허용 key 위반 | 0 |

**구조 gate: PASS (error 0).** `relations`는 13개 통제어휘만 사용했고 모든 행의 relation 수는 3개이다.

### 10.3 relations·other·길이·중복

총 relation occurrence는 **31,050회**다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 38 |
| `classification` | 924 |
| `boundary` | 4,231 |
| `contrast` | 1,590 |
| `comparison` | 2,924 |
| `function` | 745 |
| `role` | 1,710 |
| `process` | 4,698 |
| `state` | 7,380 |
| `attribute` | 3,477 |
| `other` | 3,333 |

`other_type` 상위 5개(3,333행)는 `확률·확신` 1,033, `가정·반사실·조건부 결과` 635, `계획·예정·예측` 606, `정보 부족·불완전 관측` 534, `가능성·실제 발생·미발생` 525이다.

- 독립 source token regex `[A-Za-z0-9가-힣]+`: **206,566 tokens**, 평균 **19.958067633 tokens/record**.
- primary/text exact 및 NFKC 정규화 중복: **0 / 0 / 0 / 0**.
- `primary+은/는` 시작: **1,717/10,350 = 16.5894%**. 전체 30% review, 45% HOLD 임계보다 낮다. 다만 v05의 50/150(33.3333%)은 파일 단위 다양성 review 신호다.
- primary core: 1-token 1행, 2-token 143행, 3-token 이상 10,206행. (2-token 이상에서 공백 없는 primary 0행.) 동일 X1·상이 X2는 1 group/2행(`탱크세척`), 동일 X2·상이 X1은 12 groups/85행이다.

### 10.4 반복·유사도 교차 감사

- 반복 5어절을 **2회 이상**으로 세면 10,889종 / 119,924 assignments가 반복된다. 기존 보고서와 같은 고빈도(건수 **≥150**) 관점에서는 **30종 / 5,850 assignments**이며 상위 count는 195다. 두 수치는 임계가 달라 함께 기록한다.
- reviewer-assist의 동일 relation-set masked similarity는 **44 groups**, 후보 pair 818,692개, oversized bucket 119개다. reviewer 후보 검색 기준은 raw word-Jaccard **166,087쌍**(최고 .954545455), primary-masked word-Jaccard **522,111쌍**(최고 1.0), raw char 3~5-gram TF-IDF **18,541쌍**(최고 .973745678), primary-masked char 3~5-gram TF-IDF **34,146쌍**(최고 1.0)이다.
- 별도 scikit-learn 독립 char 3~5-gram TF-IDF 전수 대조는 **22,043쌍**, 최고 **.968091583**이다. 검색 범위·후보 생성이 다른 두 감사기를 같은 수치로 합산하지 않는다.
- 높은 유사도와 195회 문구 반복은 modality 판정에서 공유하는 관측·예측·실제 분리 문형과 도메인 어휘가 만드는 **검토 신호**다. 유사도만으로 삭제·자동 재작성하지 않았다.

### 10.5 자연성 advisory와 의미 보류

- 정본 reviewer-assist post report는 hard 0, direct target 0, ChatGPT review queue **45 groups**, user queue 0을 반환했다. 현재 경고 규칙 파일이 A05의 의미 패턴을 충분히 표현하지 않아 rule-warning은 0이지만, 이는 자연성 PASS를 뜻하지 않는다.
- 독립 의미 advisory는 다음 **489 unique rows**를 사용자 검토표로 보류했다: `counterfactual_marker` 195, `generic_condition_model` 195, `scope_undefined` 50, `motion_explanation` 49. 이들은 조건·행위·범위·설명 대상이 원문에서 정해지지 않아 임의의 구체 조건을 발명하면 안 되는 군이다.
- 대표적인 `대안 경로를 비교하는 표지다`, `그 경로를 따랐는지`, `움직임을 설명한다`, `범위를 어디까지 예상할지`, `조건을 달리한 모형이` 표현은 표면 조사만 고쳐서는 의미가 생기지 않는다. `audit_reports/machine/a05/TinyLM_Stage2_A05_ModalityPossibility_UserReview_2026-09-11.json`에 locator·primary·text·flag를 남겼다.
- 사용자가 지적한 `열차 출입문 조건부 결과` 행(v16:4)은 **수정하지 않고 보류**했다. 현재 text에는 어떤 출입문 조건인지, 무엇이 대안인지, 어떤 운용 경로·행위자가 비교되는지 명시되어 있지 않다. 따라서 이를 열차 문이 조건부로 열리고 닫히는다는 뜻이나 항공기 출입문 대안으로 추정해 고치는 것은 근거 없는 의미 발명이다. 도메인 의미가 승인되면 그 locator만 새 조건·관측 기준·실제 사건 판정으로 직접 재서술한다.

### 10.6 최종 판정

- **구조: PASS.** JSONL, 150행, 필수 필드, primary literal, 13개 relations, `other_type`, 중복, registry coverage의 재감사 결과는 모두 통과했다.
- **자연성: HOLD.** 489행의 의미 미정/부자연 문구와 높은 문형 재사용은 사용자 의미 검토가 끝나지 않았다. reviewer-assist의 구조 PASS를 자연스러운 한국어 PASS로 승격하지 않는다.
- **전체 source-only 상태: `SOURCE_STRUCTURAL_PASS_NATURALNESS_HOLD_PENDING_SEMANTIC_REVIEW`.** 사용자 검토표의 의미 승인이 있기 전에는 package train/val 승격이나 학습용 확정으로 보지 않는다.
