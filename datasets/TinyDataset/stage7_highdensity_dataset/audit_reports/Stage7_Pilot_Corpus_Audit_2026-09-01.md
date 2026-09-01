# Stage 7 tokenizer-gate pilot corpus 감사보고서

- 감사일: 2026-09-01 KST
- 판정: **PASS**
- 범위: train 450 + validation 150 = 600 records
- 실제 tokenizer 측정: 미실행. 이 보고서는 문자 수와 정규식 분리 단위만 보고한다.

## 파일

| 예약 ID | 파일 | ID 범위 | records | concept family | SHA-256 |
|---|---|---|---:|---|---|
| S7-A01-T-001 | `stage7_(1)instruction_intent_high_density_train_v01.json` | S7-IIH-00001 ~ S7-IIH-00150 | 150 | S7-A01-T001: 보고서 형식 변환 — 핵심 목표와 부수 맥락 분리 | `3106665d143c7ca3400885dd4761ca478dafbfc82f30731ee59be6b1cda05699` |
| S7-A01-V-001 | `stage7_(1)instruction_intent_high_density_val_v01.json` | S7-IIV-00001 ~ S7-IIV-00150 | 150 | S7-A01-V001: 유물 보존 점검표 실행 — 핵심 목표와 부수 맥락 분리 | `09a746039d0f0e14ba7059fbf80e6ef167dd7264d25cb6a906460db11d848190` |
| S7-A03-T-001 | `stage7_(3)multiturn_dialogue_high_density_train_v01.json` | S7-MDH-00001 ~ S7-MDH-00150 | 150 | S7-A03-T001: 보고서 형식 변환 — 이전 결정과 최신 수정 통합 | `35e9eddcbe736fcb1e7f043c2614361bf50317bac88bc849b9d9c10de443a7a2` |
| S7-A06-T-001 | `stage7_(6)practical_task_high_density_train_v01.json` | S7-PTH-00001 ~ S7-PTH-00150 | 150 | S7-A06-T001: 보고서 형식 변환 — 요구 분석에서 실행까지 상태 연결 | `c8001c60ee64c688e7639627b8dcacd18e8be6fd13ec3ce62274724c0b9b8918` |

## 구조·분리 감사

- JSON/UTF-8/metadata/schema/ID 오류: 0개 오류목록 중 구조 관련 항목은 machine report 참조
- ID/concept/text 중복: {'id': 0, 'primary_concept': 0, 'text': 0}
- 내부 반복 5어절: 0
- 반복 4어절 도입부: 0
- Stage1 고밀도 교차 5어절: 0
- train-val exact text / primary / primary+relation-set: {'exact_text': 0, 'primary_concept': 0, 'primary_plus_relation_set': 0}
- validation true/false: 18/132 (12.00%)
- true train 관측 set: 0; false train 미관측 set: 0
- true 고유 relation-set: 18; 미관측 개별 label: []
- char 3~5gram TF-IDF cosine 최대: 0.303907 (gate < 0.72)
- train-val char 3~5gram TF-IDF cosine 최대: 0.134552 (gate < 0.72)
- 조사 자동 플래그 / 문법 패턴 플래그: 0 / 0; 원고 600행 사람 검토

### 파일별 문두·문장·주기·suffix

| 파일 | concept 문두 시작 | 문장수 분포 | 2문장 이상 | 3문장 이상 | lag-6 relation 동일 | 끝 2글자 상위 5 |
|---|---:|---|---:|---:|---:|---|
| `stage7_(1)instruction_intent_high_density_train_v01.json` | 68 | {'1': 73, '2': 77} | 77 | 0 | 58 | [{'suffix': '범위', 'count': 30}, {'suffix': '조건', 'count': 24}, {'suffix': '경계', 'count': 20}, {'suffix': '기능', 'count': 20}, {'suffix': '당자', 'count': 13}] |
| `stage7_(1)instruction_intent_high_density_val_v01.json` | 0 | {'2': 145, '3': 5} | 150 | 5 | 25 | [{'suffix': '범위', 'count': 35}, {'suffix': '조건', 'count': 22}, {'suffix': '기능', 'count': 21}, {'suffix': '금지', 'count': 19}, {'suffix': '경계', 'count': 13}] |
| `stage7_(3)multiturn_dialogue_high_density_train_v01.json` | 0 | {'3': 93, '4': 53, '5': 4} | 150 | 150 | 72 | [{'suffix': '경계', 'count': 20}, {'suffix': '흐름', 'count': 18}, {'suffix': '당자', 'count': 13}, {'suffix': '대기', 'count': 9}, {'suffix': '기준', 'count': 9}] |
| `stage7_(6)practical_task_high_density_train_v01.json` | 81 | {'1': 80, '2': 70} | 70 | 0 | 59 | [{'suffix': '기능', 'count': 41}, {'suffix': '절차', 'count': 28}, {'suffix': '당자', 'count': 24}, {'suffix': '보고', 'count': 22}, {'suffix': '완료', 'count': 12}] |

### train-val 상위 유사쌍 직접 검토

| cosine | train/val ID 1 | train/val ID 2 | 판정 |
|---:|---|---|---|
| 0.134552 | `S7-IIH-00047` | `S7-IIV-00122` | 독립 직접 문장으로 검토 완료 |
| 0.132556 | `S7-IIH-00023` | `S7-IIV-00122` | 독립 직접 문장으로 검토 완료 |
| 0.131870 | `S7-IIH-00112` | `S7-IIV-00148` | 독립 직접 문장으로 검토 완료 |
| 0.125594 | `S7-IIH-00117` | `S7-IIV-00129` | 독립 직접 문장으로 검토 완료 |
| 0.125486 | `S7-IIH-00122` | `S7-IIV-00098` | 독립 직접 문장으로 검토 완료 |

## Relations 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 0 |
| `classification` | 149 |
| `boundary` | 258 |
| `contrast` | 0 |
| `comparison` | 0 |
| `function` | 249 |
| `role` | 252 |
| `process` | 212 |
| `state` | 245 |
| `attribute` | 0 |
| `other` | 112 |

### `other` 상위 개념 유형

| 유형 | 횟수 |
|---|---:|
| 미해결 질문 | 2 |
| 맥락과 지시 구분 | 1 |
| 결정 미지정 | 1 |
| 예시와 결과 구분 | 1 |
| 요구 미정 | 1 |

## 분량·무결성

- text 문자 수: 53,634
- `[0-9A-Za-z가-힣]+` 분리 단위: 13,955
- 보호 SHA: 369/369 일치, 불일치 0
- 보호 범위: Stage1 저밀도 31, Stage1 고밀도 train/val 255, Stage2~10 기존 scaffold 81, 중앙 예약 원장 2개
- 오류 목록: 없음

기계 판정과 상위 유사쌍은 `audit_reports/machine/TinyLM_Stage7_Pilot_Corpus_Audit_2026-09-01.json`에 보존했다.
