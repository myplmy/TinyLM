# Stage 5 tokenizer-gate pilot corpus 감사보고서

- 감사일: 2026-09-01 KST
- 판정: **PASS**
- 범위: train 450 + validation 150 = 600 records
- 실제 tokenizer 측정: 미실행. 이 보고서는 문자 수와 정규식 분리 단위만 보고한다.

## 파일

| 예약 ID | 파일 | ID 범위 | records | concept family | SHA-256 |
|---|---|---|---:|---|---|
| S5-A01-T-001 | `stage5_(1)induction_high_density_train_v01.json` | S5-INH-00001 ~ S5-INH-00150 | 150 | S5-A01-T001: 신소재 내구성 시험 — 관찰 표본에서 제한적 규칙 도출 | `b2225c1bdfdb6c0a7f4eb78f3d86b82dc74aabaab8296187cfe90d58b3ed48fc` |
| S5-A01-V-001 | `stage5_(1)induction_high_density_val_v01.json` | S5-INV-00001 ~ S5-INV-00150 | 150 | S5-A01-V001: 산호초 회복 조사 — 관찰 표본에서 제한적 규칙 도출 | `330f73a7b74723c02314ca338826637be9834fa46183772d79b2f7988c31d0b3` |
| S5-A03-T-001 | `stage5_(3)counterexample_generalization_high_density_train_v01.json` | S5-CGH-00001 ~ S5-CGH-00150 | 150 | S5-A03-T001: 신소재 내구성 시험 — 진짜 반례와 범위 밖 사례 구분 | `7625529f41f252517af94855b7196ba5d6534b0264f83f913146916fa1c7e66f` |
| S5-A06-T-001 | `stage5_(6)structural_transfer_high_density_train_v01.json` | S5-STH-00001 ~ S5-STH-00150 | 150 | S5-A06-T001: 신소재 내구성 시험 — 규칙 구조의 불변 요소 추출 | `e1bdb12802018c84181febe13100de088360033f21e6992a3c31ba1e7f1da853` |

## 구조·분리 감사

- JSON/UTF-8/metadata/schema/ID 오류: 0개 오류목록 중 구조 관련 항목은 machine report 참조
- ID/concept/text 중복: {'id': 0, 'primary_concept': 0, 'text': 0}
- 내부 반복 5어절: 0
- 반복 4어절 도입부: 0
- Stage1 고밀도 교차 5어절: 0
- train-val exact text / primary / primary+relation-set: {'exact_text': 0, 'primary_concept': 0, 'primary_plus_relation_set': 0}
- validation true/false: 18/132 (12.00%)
- true train 관측 set: 0; false train 미관측 set: 0
- true 고유 relation-set: 9; 미관측 개별 label: []
- char 3~5gram TF-IDF cosine 최대: 0.301044 (gate < 0.72)
- train-val char 3~5gram TF-IDF cosine 최대: 0.226005 (gate < 0.72)
- 조사 자동 플래그 / 문법 패턴 플래그: 0 / 0; 원고 600행 사람 검토

### 파일별 문두·문장·주기·suffix

| 파일 | concept 문두 시작 | 문장수 분포 | 2문장 이상 | 3문장 이상 | lag-6 relation 동일 | 끝 2글자 상위 5 |
|---|---:|---|---:|---:|---:|---|
| `stage5_(1)induction_high_density_train_v01.json` | 5 | {'1': 5, '2': 145} | 145 | 0 | 29 | [{'suffix': '효과', 'count': 9}, {'suffix': '구간', 'count': 6}, {'suffix': '표본', 'count': 5}, {'suffix': '편향', 'count': 4}, {'suffix': '경계', 'count': 3}] |
| `stage5_(1)induction_high_density_val_v01.json` | 5 | {'1': 28, '2': 122} | 122 | 0 | 24 | [{'suffix': '구역', 'count': 7}, {'suffix': '표본', 'count': 6}, {'suffix': '경계', 'count': 5}, {'suffix': '대비', 'count': 5}, {'suffix': '응쌍', 'count': 4}] |
| `stage5_(3)counterexample_generalization_high_density_train_v01.json` | 7 | {'2': 150} | 150 | 0 | 1 | [{'suffix': '사례', 'count': 20}, {'suffix': '상태', 'count': 12}, {'suffix': '역전', 'count': 5}, {'suffix': '시편', 'count': 4}, {'suffix': '표본', 'count': 3}] |
| `stage5_(6)structural_transfer_high_density_train_v01.json` | 0 | {'1': 29, '2': 121} | 121 | 0 | 0 | [{'suffix': '대응', 'count': 15}, {'suffix': '순서', 'count': 7}, {'suffix': '한계', 'count': 6}, {'suffix': '범위', 'count': 6}, {'suffix': '구분', 'count': 6}] |

### train-val 상위 유사쌍 직접 검토

| cosine | train/val ID 1 | train/val ID 2 | 판정 |
|---:|---|---|---|
| 0.226005 | `S5-INH-00033` | `S5-INV-00030` | 독립 직접 문장으로 검토 완료 |
| 0.190163 | `S5-INH-00045` | `S5-INV-00135` | 독립 직접 문장으로 검토 완료 |
| 0.181607 | `S5-INH-00080` | `S5-INV-00077` | 독립 직접 문장으로 검토 완료 |
| 0.168354 | `S5-INV-00055` | `S5-CGH-00124` | 독립 직접 문장으로 검토 완료 |
| 0.153196 | `S5-INH-00059` | `S5-INV-00079` | 독립 직접 문장으로 검토 완료 |

## Relations 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 0 |
| `classification` | 369 |
| `boundary` | 512 |
| `contrast` | 75 |
| `comparison` | 166 |
| `function` | 103 |
| `role` | 0 |
| `process` | 131 |
| `state` | 102 |
| `attribute` | 248 |
| `other` | 104 |

### `other` 상위 개념 유형

| 유형 | 횟수 |
|---|---:|
| 관찰 기간 제한 | 2 |
| 출처 불명 | 2 |
| 구간 검열 | 2 |
| 추론 구조 | 2 |
| 미관측 변수 | 1 |

## 분량·무결성

- text 문자 수: 40,389
- `[0-9A-Za-z가-힣]+` 분리 단위: 10,500
- 보호 SHA: 369/369 일치, 불일치 0
- 보호 범위: Stage1 저밀도 31, Stage1 고밀도 train/val 255, Stage2~10 기존 scaffold 81, 중앙 예약 원장 2개
- 오류 목록: 없음

기계 판정과 상위 유사쌍은 `audit_reports/machine/TinyLM_Stage5_Pilot_Corpus_Audit_2026-09-01.json`에 보존했다.
