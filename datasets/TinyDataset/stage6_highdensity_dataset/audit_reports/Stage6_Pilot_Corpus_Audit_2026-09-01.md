# Stage 6 tokenizer-gate pilot corpus 감사보고서

- 감사일: 2026-09-01 KST
- 판정: **PASS**
- 범위: train 450 + validation 150 = 600 records
- 실제 tokenizer 측정: 미실행. 이 보고서는 문자 수와 정규식 분리 단위만 보고한다.

## 파일

| 예약 ID | 파일 | ID 범위 | records | concept family | SHA-256 |
|---|---|---|---:|---|---|
| S6-A01-T-001 | `stage6_(1)long_context_high_density_train_v01.json` | S6-LCH-00001 ~ S6-LCH-00150 | 150 | S6-A01-T001: 광역 재난 자원 배치 — 장거리 객체·사건 참조 유지 | `72a7b0a3e79d0044166e48700ef5ebc1463ae2e996a7d5062757d2560b43e68b` |
| S6-A01-V-001 | `stage6_(1)long_context_high_density_val_v01.json` | S6-LCV-00001 ~ S6-LCV-00150 | 150 | S6-A01-V001: 극지 탐사대 운영기록 — 장거리 객체·사건 참조 유지 | `54ef44059631419b401de6b2103df15b872b927ca09206dab97990b2241d5336` |
| S6-A03-T-001 | `stage6_(3)constraint_satisfaction_high_density_train_v01.json` | S6-CSH-00001 ~ S6-CSH-00150 | 150 | S6-A03-T001: 광역 재난 자원 배치 — 강제·선호·조건부 제약 분류 | `2f20a95c6bd4c984cddbc06ea0da5801d34947330018bde6b6b7ed168075c7af` |
| S6-A06-T-001 | `stage6_(6)uncertainty_management_high_density_train_v01.json` | S6-UMH-00001 ~ S6-UMH-00150 | 150 | S6-A06-T001: 광역 재난 자원 배치 — 불확실성 원천과 전파 경로 구분 | `2aa6b3ed6efd33f91bd091a7c1b6f892e5344d5c7c34aa53df8f62b0f6bb7b2f` |

## 구조·분리 감사

- JSON/UTF-8/metadata/schema/ID 오류: 0개 오류목록 중 구조 관련 항목은 machine report 참조
- ID/concept/text 중복: {'id': 0, 'primary_concept': 0, 'text': 0}
- 내부 반복 5어절: 0
- 반복 4어절 도입부: 0
- Stage1 고밀도 교차 5어절: 0
- train-val exact text / primary / primary+relation-set: {'exact_text': 0, 'primary_concept': 0, 'primary_plus_relation_set': 0}
- validation true/false: 18/132 (12.00%)
- true train 관측 set: 0; false train 미관측 set: 0
- true 고유 relation-set: 5; 미관측 개별 label: []
- char 3~5gram TF-IDF cosine 최대: 0.355563 (gate < 0.72)
- train-val char 3~5gram TF-IDF cosine 최대: 0.136250 (gate < 0.72)
- 조사 자동 플래그 / 문법 패턴 플래그: 0 / 0; 원고 600행 사람 검토

### 파일별 문두·문장·주기·suffix

| 파일 | concept 문두 시작 | 문장수 분포 | 2문장 이상 | 3문장 이상 | lag-6 relation 동일 | 끝 2글자 상위 5 |
|---|---:|---|---:|---:|---:|---|
| `stage6_(1)long_context_high_density_train_v01.json` | 0 | {'3': 120, '4': 30} | 150 | 150 | 26 | [{'suffix': '공백', 'count': 8}, {'suffix': '등급', 'count': 7}, {'suffix': '구역', 'count': 6}, {'suffix': '단계', 'count': 5}, {'suffix': '상태', 'count': 3}] |
| `stage6_(1)long_context_high_density_val_v01.json` | 0 | {'3': 108, '4': 42} | 150 | 150 | 67 | [{'suffix': '공백', 'count': 25}, {'suffix': '등급', 'count': 13}, {'suffix': '단계', 'count': 11}, {'suffix': '임역', 'count': 5}, {'suffix': '역할', 'count': 4}] |
| `stage6_(3)constraint_satisfaction_high_density_train_v01.json` | 0 | {'2': 150} | 150 | 0 | 61 | [{'suffix': '조건', 'count': 20}, {'suffix': '선호', 'count': 18}, {'suffix': '충돌', 'count': 17}, {'suffix': '하한', 'count': 13}, {'suffix': '범위', 'count': 7}] |
| `stage6_(6)uncertainty_management_high_density_train_v01.json` | 0 | {'2': 150} | 150 | 0 | 66 | [{'suffix': '경계', 'count': 29}, {'suffix': '미상', 'count': 15}, {'suffix': '정폭', 'count': 14}, {'suffix': '차선', 'count': 12}, {'suffix': '범위', 'count': 9}] |

### train-val 상위 유사쌍 직접 검토

| cosine | train/val ID 1 | train/val ID 2 | 판정 |
|---:|---|---|---|
| 0.136250 | `S6-LCH-00094` | `S6-LCV-00058` | 독립 직접 문장으로 검토 완료 |
| 0.116417 | `S6-LCH-00039` | `S6-LCV-00139` | 독립 직접 문장으로 검토 완료 |
| 0.111856 | `S6-LCH-00084` | `S6-LCV-00138` | 독립 직접 문장으로 검토 완료 |
| 0.110710 | `S6-LCH-00004` | `S6-LCV-00005` | 독립 직접 문장으로 검토 완료 |
| 0.109023 | `S6-LCH-00099` | `S6-LCV-00041` | 독립 직접 문장으로 검토 완료 |

## Relations 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 0 |
| `classification` | 160 |
| `boundary` | 463 |
| `contrast` | 0 |
| `comparison` | 146 |
| `function` | 0 |
| `role` | 125 |
| `process` | 0 |
| `state` | 506 |
| `attribute` | 175 |
| `other` | 105 |

### `other` 상위 개념 유형

| 유형 | 횟수 |
|---|---:|
| 일정 불확실성 | 3 |
| 관측 결측 | 3 |
| 시간정보 결측 | 3 |
| 일정 미확정 | 2 |
| 수요 결측 | 2 |

## 분량·무결성

- text 문자 수: 59,009
- `[0-9A-Za-z가-힣]+` 분리 단위: 15,072
- 보호 SHA: 369/369 일치, 불일치 0
- 보호 범위: Stage1 저밀도 31, Stage1 고밀도 train/val 255, Stage2~10 기존 scaffold 81, 중앙 예약 원장 2개
- 오류 목록: 없음

기계 판정과 상위 유사쌍은 `audit_reports/machine/TinyLM_Stage6_Pilot_Corpus_Audit_2026-09-01.json`에 보존했다.
