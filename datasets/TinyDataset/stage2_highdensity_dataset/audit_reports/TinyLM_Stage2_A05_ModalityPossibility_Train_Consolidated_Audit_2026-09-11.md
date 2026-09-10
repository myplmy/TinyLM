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
- `a05_local_work_ledger_2026-09-11.md`
