# TinyLM Stage3 고밀도 pilot 감사 보고서

## 결론

- 최종 판정: **PASS**
- 범위: train 3파일 450레코드 + validation 1파일 150레코드, 총 600레코드
- 정본 원고: 각 JSON과 대응하는 `.source.psv` 1개만 유지
- 작성 방식: primary concept, 의미 기반 relations, 한국어 text를 행별로 직접 작성하고 Python은 ID·metadata 포장 및 감사에만 사용
- 실제 tokenizer 토큰 수: 미측정. 본 감사의 분량 보조치는 한국어 정규식 word unit과 문자 수다.

## 파일별 구조 결과

| 예약 ID | 파일 | split | 레코드·ID 범위 | concept 문두 | 2문장 이상 | lag6 동일 relation-set | JSON SHA-256 |
|---|---|---:|---|---:|---:|---:|---|
| S3-A01-T-001 | `stage3_(1)goal_action_high_density_train_v01.json` | train | 150, S3-GAH-00001~00150 | 0 | 150 | 16 | `24780509d048c304c4b9c35069a928df03ca26e0001d7b79d56e51fc72c3a7f4` |
| S3-A03-T-001 | `stage3_(3)planning_decomposition_high_density_train_v01.json` | train | 150, S3-PDH-00001~00150 | 0 | 150 | 12 | `87a6771ccdf852e8fa859de345596d4849c74540eb38d2487abe59dd33c9fbcb` |
| S3-A06-T-001 | `stage3_(6)execution_recovery_high_density_train_v01.json` | train | 150, S3-ERH-00001~00150 | 0 | 150 | 29 | `7e97651abe2c08d05998f2f69a1f64a1f1c52bd8d03c7e906694587470c4e186` |
| S3-A01-V-001 | `stage3_(1)goal_action_high_density_val_v01.json` | val | 150, S3-GAV-00001~00150 | 0 | 150 | 10 | `d10a30756c7292a9885fd38e39fb7d542aa526483ceac69a2ec13d290e617867` |

모든 파일은 150레코드, ID·primary concept·text exact duplicate 0, relations 길이 2~5 및 레코드 내부 중복 0이다. concept 문두는 허용 상한 90 이하, 2문장 이상은 요구 하한 45 이상, lag6 동일 정렬 relation-set은 허용 상한 72 이하를 만족했다.

## Validation 분리와 누출 검사

- `unseen_relation: true`: 18/150, 12.0%
- `unseen_relation: false`: 132/150, 88.0%
- true의 정렬 relation-set: 18종 모두 Stage3 train 미관측
- false의 정렬 relation-set: 전부 Stage3 train 관측
- validation에 사용된 개별 relation label 11종은 모두 Stage3 train에서 1회 이상 의미 있게 출현
- train-val exact text: 0
- train-val exact primary concept: 0
- train-val 동일 primary concept + relation-set: 0
- train-val 공통 5어절: 0
- Stage1 고밀도 보호 corpus와 공통 5어절: 0

## 보일러플레이트·유사도·문법

- 전체 600레코드 내부 반복 5어절 유형: 0
- 반복 4어절 도입부 유형: 0
- character 3~5 gram TF-IDF cosine 최대값: **0.178807** (`< 0.72`)
- 자동 조사·결합·중복구·금지 패턴 flag: 0
- 문장 구조 층화: 네 파일 모두 150/150이 2문장 이상이며 concept 문두 고정 골격이 없다.

## Relations 분포

| relation | 횟수 | relation | 횟수 |
|---|---:|---|---:|
| is_a | 0 | subclass_of | 0 |
| part_of | 54 | classification | 30 |
| boundary | 198 | contrast | 7 |
| comparison | 45 | function | 280 |
| role | 36 | process | 397 |
| state | 509 | attribute | 166 |
| other | 57 |  |  |

13개 통제 어휘 밖 relation은 0개다. Stage3 pilot의 목표·계획·복구 특성상 `state`, `process`, `function`, `boundary`가 중심이며, 쓰지 않은 `is_a`와 `subclass_of`를 억지로 삽입하지 않았다.

## other 상위 개념 유형 5개

기계 감사의 concept 접미·형태 집계 기준이다.

1. 기록 과제: 2회 — 예: `납품 사진 기록 과제`
2. 재제작 목표: 1회 — `완성 치수 기록의 재제작 목표`
3. 색상 재현: 1회 — `재료 배치 기록의 색상 재현`
4. 정보의 불확실성: 1회 — `현재 사용자 치수 정보의 불확실성`
5. 재질의 미확인: 1회 — `설치 벽체 재질의 미확인`

`other`에는 외부 확인 대기, 기록·증거 보존, 현장 정보 미확정, 복구 종료 근거처럼 나머지 12개 relation으로 거짓 라벨링하기 어려운 의미를 남겼다.

## 분량과 보호 파일

- text 문자 수: 51,781
- 정규식 word unit: 13,837
- 보호 SHA 기준 파일: `stage1_highdensity_dataset/audit_reports/machine/TinyLM_Stage2_10_Pilot_Protected_Baseline_2026-09-01.json`
- 보호 대상 확인: 371/371
- SHA 불일치: 0
- 누락: 0

기계 판독 보고서는 `audit_reports/machine/TinyLM_Stage3_Pilot_Audit_2026-09-01.json`에 있다.
