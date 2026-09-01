# TinyLM Stage4 고밀도 pilot 감사 보고서

## 결론

- 최종 판정: **PASS**
- 범위: train 3파일 450레코드 + validation 1파일 150레코드, 총 600레코드
- 정본 원고: 각 packet마다 `.source.psv` 1개이며, 반려된 `_source.jsonl`은 제거했다.
- 작성 방식: 상담 면담과 고고학 구술 인터뷰의 primary concept·relations·text를 행별 독립 문장으로 직접 작성했다. build 도구는 의미 내용을 생성하지 않고 ID와 metadata만 포장한다.
- 실제 tokenizer 토큰 수는 아직 측정하지 않았다.

## 파일별 구조 결과

| 예약 ID | 파일 | split | 레코드·ID 범위 | concept 문두 | 2문장 이상 | lag6 동일 relation-set | JSON SHA-256 |
|---|---|---:|---|---:|---:|---:|---|
| S4-A01-T-001 | `stage4_(1)discourse_reference_high_density_train_v01.json` | train | 150, S4-DRH-00001~00150 | 0 | 150 | 29 | `85ffb68c552bce19f2ce978aa42a9c6f188d51f47f84dc993ec3fbf580b5dc5f` |
| S4-A03-T-001 | `stage4_(3)dialogue_state_high_density_train_v01.json` | train | 150, S4-DSH-00001~00150 | 0 | 150 | 24 | `5fbe1c379cb3981002fbbac6ca6b77811df3bc61ef000729bcd7b4d3b70e92fc` |
| S4-A06-T-001 | `stage4_(6)implicature_context_high_density_train_v01.json` | train | 150, S4-ICH-00001~00150 | 0 | 150 | 22 | `23ab5bdb95add2cf952efe82063d4394f736b5c3ad33d4420ee3b26c1f53fcb9` |
| S4-A01-V-001 | `stage4_(1)discourse_reference_high_density_val_v01.json` | val | 150, S4-DRV-00001~00150 | 0 | 150 | 29 | `3d241a67e441b96985bc0dba7039410f254c86e390b97cdf327d0ca16b4cc02d` |

모든 파일은 150레코드이며 ID·primary concept·text duplicate가 없다. relations는 13개 통제 어휘만 사용했고 레코드마다 2~5개, 내부 중복 0이다. 네 파일 모두 concept 문두 90 이하, 2문장 이상 45 이상, lag6 동일 relation-set 72 이하 게이트를 통과했다.

## Validation 분리와 relation-label coverage

- `unseen_relation: true`: 18/150, 12.0%
- `unseen_relation: false`: 132/150, 88.0%
- true 정렬 relation-set: 18종이며 전부 Stage4 train 미관측
- false 정렬 relation-set: 전부 Stage4 train 관측
- validation 사용 개별 label: `attribute`, `boundary`, `classification`, `comparison`, `contrast`, `function`, `other`, `process`, `role`, `state`
- 위 10개 label 모두 Stage4 train에서 1회 이상 의미 있게 출현

train-val exact text, exact primary concept, primary concept+relation-set 중복은 모두 0이다. train-val 공통 5어절과 Stage1 고밀도 보호 corpus 공통 5어절도 각각 0이다.

## 보일러플레이트·유사도·문법

- 내부 반복 5어절 유형: 0
- 반복 4어절 도입부 유형: 0
- character 3~5 gram TF-IDF cosine 최대값: **0.180895** (`< 0.72`)
- 자동 조사·결합·중복구·금지 패턴 flag: 0
- 네 파일 모두 150/150 레코드가 2문장 이상이고 concept 문두 고정 구조는 0이다.

## Relations 분포

| relation | 횟수 | relation | 횟수 |
|---|---:|---|---:|
| is_a | 0 | subclass_of | 0 |
| part_of | 0 | classification | 289 |
| boundary | 351 | contrast | 47 |
| comparison | 14 | function | 24 |
| role | 194 | process | 126 |
| state | 552 | attribute | 96 |
| other | 89 |  |  |

통제 어휘 밖 relation은 0개다. 장거리 참조, 대화 상태, 함축 경계를 다루는 Stage4 pilot 특성상 `state`, `boundary`, `classification`, `role`이 중심이다. 의미가 없는 `is_a`, `subclass_of`, `part_of`는 분포를 채우기 위해 넣지 않았다.

## other 상위 개념 유형 5개

기계 감사의 concept 접미·형태 집계 기준이다.

1. 확인 대기: 2회 — 예: `처방 변경 이유의 의사 확인 대기`
2. 답변 대기: 2회 — 예: `휴직 가능성의 회사 답변 대기`
3. 역할 규범: 2회 — 예: `좋은 딸이어야 해요의 역할 규범`
4. 시절의 나: 1회 — `그 아이가 뜻하는 어린 시절의 나`
5. 배우자 가족: 1회 — `그쪽이 가리키는 배우자 가족`

`other`에는 지시 범위·시간·공간이 외부 맥락에 의존하는 경우, 외부 답변 대기, 암묵 규범, 함축의 의미가 미확정인 경우가 주로 포함됐다.

## 분량과 보호 파일

- text 문자 수: 55,011
- 정규식 word unit: 14,279
- 보호 SHA 기준 파일: `stage1_highdensity_dataset/audit_reports/machine/TinyLM_Stage2_10_Pilot_Protected_Baseline_2026-09-01.json`
- 보호 대상 확인: 371/371
- SHA 불일치: 0
- 누락: 0

기계 판독 보고서는 `audit_reports/machine/TinyLM_Stage4_Pilot_Audit_2026-09-01.json`에 있다.
