# TinyLM Stage2 A06 relational_composition 재감사·수정 보고서 (2026-09-11)

## 1. 판정 요약

| 축 | 최종 판정 | 근거 |
|---|---|---|
| 하드 구조 | **PASS_WITH_LEGACY_WARNING** | 52파일·7,800건, 하드 오류 0건. v01의 기존 `other_type` 본문 불일치 25건은 보존 규칙에 따라 경고로만 남김 |
| 의미·자연성 | **HOLD** | 고유사도 Jaccard 기준은 해소했으나, 템플릿 skeleton/core와 문자 TF-IDF 반복이 여전히 큼 |
| registry 정합성 | **PASS** | A06 전용 registry 7,800행, parse 오류 0, source locator/primary 불일치 0 |
| package·split leakage | **NOT_RUN_SOURCE_ONLY** | 이번 범위는 A06 train source와 A06 registry뿐이며 package/validation은 읽기·수정하지 않음 |

구조 PASS는 한국어 자연성 PASS를 뜻하지 않는다. 자연성 HOLD를 해소하기 전에는 corpus 확정·패키징 대상으로 승격하지 않는다.

## 2. 범위와 보호 경계

- 대상: `stage2_highdensity_dataset/sources/train/stage2_(16)relational_composition_high_density_train_v01~v52.source.psv`
- 형식: 기존 **legacy PSV**(헤더 `concept|relations|other_type|text`), BOM·공백행·제어문자 없음. 같은 version의 `.source.jsonl`은 없음.
- 레코드: 버전당 150건, 52버전, 총 7,800건.
- v01 source와 기존 v01 package는 수정하지 않았다. v02~v52에서만 행 단위 수정이 발생했다.
- 저밀도·held-out·benchmark·다른 A 영역·공용 `train/`·공용 `val/`·manifest·checkpoint·중앙 원장·공용 reviewer-assist 코드는 사용·수정하지 않았다.
- 상세 기계 결과: [`TinyLM_Stage2_A06_RelationalComposition_Reaudit_PostRepairFinal_2026-09-11.json`](../machine/a06/TinyLM_Stage2_A06_RelationalComposition_Reaudit_PostRepairFinal_2026-09-11.json)

## 3. SHA-256과 수정량

| 대상 | 수정 전 | 수정 후 | 비고 |
|---|---|---|---|
| A06 source-set(파일명·파일 SHA 정렬 결합) | `32DDA8E2AC224CF05D9F99932D24D7A7A22FCE6755F32ED675D3717A45B7FF72` | `87BEB2DBE900E522212E713D0798C0E12E28FC3135618D9B2F9E16A4FD150663` | 파일 52개 모두 존재, 최종 43개 파일에 변경 |
| A06 registry | `3D9CAEC68B9CE92D4C2E6EDF20DEDD1A311FE2F1304E1C9DD80A998404EC936F` | `15A9429AB0F5A6C383E487A443705F834EC68C1C384C8834B31556D55ED98C29` | locator 324건의 primary를 source와 동기화 |
| v01 source | `9607FA0F55D2A5000676C870DCE131B22E7B8FE9ACF61D1A6500AC61B774F610` | 동일 | 보존 |

- source 행 변경: 총 **324건**. 조사·직접 인접중복 294건(기계 후보 293 + v04 1건), 고유사도 의미 재서술 28건, 문맥상 `배관로→배관으로` 2건을 포함한다(중복 없는 324 locator).
- 28건의 고유사도 행은 모두 동일 core에 `— 연결 확인/독립 확인` 표식만 달랐던 후행 행이다. 각 행을 별도 의미로 재서술하고, ID·행 순서·relations는 유지했다.

## 4. 하드 구조 gate

| 검사 | 건수 |
|---|---:|
| missing/unexpected/duplicate format | 0 / 0 / 0 |
| UTF-8·BOM·공백행·제어문자 | 0 |
| columns·empty concept/text·primary literal 누락 | 0 |
| concept/text exact·normalized duplicate | 0 |
| numeric suffix | 0 |
| relations 통제어휘 위반 | 0 |
| relations 2~5개·내부 중복 위반 | 0 |
| `other_type` 규칙 위반 | 0 |
| `other_type` 본문 literal 불일치 | **25 (v01 legacy warning)** |
| row_count·reservation 불일치 | 0 / 0 |
| registry parse·locator/primary 불일치 | 0 / 0 |

train source에는 `unseen_relation` 필드를 넣지 않았다.

## 5. relations 분포 (13개 고정 어휘)

| relation | count |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 1,540 |
| `classification` | 1,153 |
| `boundary` | 3,059 |
| `contrast` | 850 |
| `comparison` | 1,730 |
| `function` | 930 |
| `role` | 2,522 |
| `process` | 4,185 |
| `state` | 4,335 |
| `attribute` | 1,711 |
| `other` | 1,799 |

`other` 상위 유형은 `후속 검증 누락` 213건, `다음 단계 입력 결측` 212건, `식별 기록 상충` 212건, `출처 연결 불명` 212건, `센서 채널 불일치` 211건이다. 관계 cue 누락 수치는 의미 후보를 찾는 advisory이며 자동 FAIL로 세지 않았다(최종 후보: part_of 1,080, process 833, state 1,719, role 1,739, function 444, boundary 2,060, comparison 1,191, classification 883, attribute 1,278, contrast 348, other 0).

## 6. 반복·유사도·조사 감사

| 항목 | 수정 전 | 수정 후 |
|---|---:|---:|
| text 문자 / word-unit / 평균 word-unit | 827,186 / 214,554 / 27.5069 | 827,647 / 214,579 / 27.5101 |
| 반복 5-gram 그룹 / 발생 | 29,691 / 163,552 | 29,572 / 162,821 |
| 반복 4-gram 도입부 그룹 / 발생 | 1,555 / 7,650 | 1,548 / 7,615 |
| boilerplate skeleton distinct / 반복 그룹 / 반복 행 | 563 / 272 / 7,509 | 591 / 272 / 7,481 |
| core distinct / 반복 그룹 / 반복 행 / 최대 그룹 | 3,990 / 2,670 / 6,480 / 3 | 4,018 / 2,659 / 6,441 / 3 |
| 동일 relation-set word Jaccard ≥.95 / 최대 | 28 / 0.969697 | **0 / 0.942857** |
| 동일 relation-set char 3~5-gram TF-IDF ≥.95 / ≥.97 / 최대 | 264 / 52 / 0.974011 | 232 / 29 / 0.973682 |

동일 relation-set pair 전수 비교는 1,046,052쌍이다. Jaccard ≥.95 28쌍은 이번 행별 재서술로 0쌍이 되었지만, TF-IDF ≥.95 232쌍은 공통 문장 골격·표식의 잔여 반복으로 남아 자연성 HOLD로 분류했다. 이전 보고서의 TF-IDF 최대값 `0.974396`과 이번 사전 스냅샷 `0.974011`은 감사기 구현이 달라 생긴 기준 차이이므로, 전후 비교는 동일한 A06 재감사기 값으로 판단했다.

반복 5-gram 최상위는 `항목은 확인된 관계만 확정하게 한다` 1,769회이다. 반복 4-gram 도입부는 `관측 범위가 제한된 보고서에서`, `기본 경로가 열려 있어도`, `두 담당자의 표가 다를 때` 등이 각각 약 210회다. 이는 17개 표식이 450건씩 배치된 생성 템플릿이 주요 원인이다.

### 조사·primary 점검

- text가 primary+은/는으로 시작: **27/7,800 (0.346%)**, `은` 10·`는` 17. 30% review, 45% HOLD 기준보다 낮다.
- dash가 있는 primary: **7,622/7,800 (97.7179%)**. 28개 행은 의미 재서술로 dash를 제거했지만, 나머지는 표식 결합이므로 별도 자연성 검토가 필요하다.
- raw 인접 동일어(정규식 기준): **0건**. 감사기의 구두점 제거 후보 149건은 `... 경로 — 경로 보존`, `... 연결 — 연결 확인`처럼 대시 양쪽 표식이 같은 경우가 대부분이어서 구조 오류가 아닌 advisory로 남겼다.
- `(으)로` 후보: 수정 전 고신뢰 후보 235행(470 occurrence) 중 233행을 교정하고, v43 `배관로` 2행도 문맥상 `배관으로`로 교정하여 최종 후보 **0행**.

## 7. 자연성 경고와 처리 구분

### 직접 수정 완료

1. `apply_patch` 행 단위 조사 교정·인접중복 제거 294건.
2. Jaccard ≥.95의 marker-only 쌍 28건을 개별 의미로 직접 재서술.
3. v43 `배관로` 2건을 문맥상 조사 오류로 직접 교정.
4. primary가 바뀐 locator에 대해 A06 전용 registry 324건을 동기화.

### 사용자 검토 보류(HOLD)

- 문자 3~5-gram TF-IDF ≥.95 **232쌍**(최대 0.973682): 문장 골격은 비슷하지만 각 행의 관계 의미를 자동으로 단정할 수 없어 전역 치환하지 않음.
- dash primary **7,622행**, skeleton 반복 **272그룹·7,481행**, core 반복 **2,659그룹·6,441행**: 템플릿 제거는 행별 의미 재작성 작업으로 별도 승인·분할 수행해야 함.
- relation cue 후보는 의미 판정 전용 목록으로 보류. `other_type` v01 legacy 25건은 v01 보존 규칙으로 수정하지 않음.

따라서 직접 수정 수와 사용자 검토 보류 수는 같은 단위가 아니다(직접 수정은 locator 행, 유사도는 pair, skeleton/core는 그룹·행). 경고를 자동 FAIL 또는 일괄 자동수정으로 해석하지 않는다.

## 8. 원인과 후속 제안

이번 A06의 높은 유사도 원인은 관계 의미 자체보다 (a) 17개 표식의 균등 반복, (b) `항목은 확인된 관계만 확정하게 한다`와 같은 공통 후행절, (c) 동일 core를 표식만 바꿔 재사용한 배치 설계다. 28개 Jaccard 쌍은 이 원인을 직접 확인하여 제거했으나, 나머지 TF-IDF·skeleton은 대량 자동 재서술을 하지 않았다.

후속 작업은 표식별 150건 단위로 새 상황·새 동사·새 증거를 사람 또는 reviewer-assist가 행별 확인하고, 동일 relation-set 내부에서 TF-IDF 상위 pair를 우선 검토하는 방식이 적절하다. 구조 gate가 다시 PASS하더라도 자연성 HOLD는 별도 해소·재감사 후에만 승격한다. legacy PSV를 JSONL로 바꾸는 작업은 전체 재직렬화가 되므로 별도 승인과 변환 검증을 거쳐야 한다.
