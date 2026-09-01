# TinyLM Stage 2 고밀도 pilot corpus 최종 감사

- 감사일: 2026-09-01 KST
- 판정: **PASS**
- 범위: train 3파일 450레코드 + validation 1파일 150레코드, 총 600레코드
- 정본: `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`, `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`, Stage 2 `PREPARATION_MANIFEST.json`
- 기계 판독 보고서: `audit_reports/machine/TinyLM_Stage2_Pilot_Audit_2026-09-01.json`

## 1. 확정 파일과 예약 준수

| reservation | split | 파일 | ID 범위 | concept family | SHA-256 |
|---|---:|---|---|---|---|
| S2-A01-T-001 | train | `stage2_(11)causal_structure_high_density_train_v01.json` | S2-CSH-00001 ~ S2-CSH-00150 | 스마트 온실 — 직접 원인·매개 경로·배경 조건 분리 | `e6a2468f73c8481e93a75051b87c13fb343848a4838d7a0c47d6e3e185001089` |
| S2-A03-T-001 | train | `stage2_(13)temporal_order_high_density_train_v01.json` | S2-TOH-00001 ~ S2-TOH-00150 | 스마트 온실 — 사건 선후·동시성·부분 겹침 판정 | `620d9e2fe3a77912a1baab7c9a2da3c881e353fc0eb60d6879345d44c14d88a7` |
| S2-A06-T-001 | train | `stage2_(16)relational_composition_high_density_train_v01.json` | S2-RCH-00001 ~ S2-RCH-00150 | 스마트 온실 — 다중 홉 관계 연결과 방향 보존 | `af2e487fa954e0f7e9c45fc87b0ca21614b8bc1331b264e9ef5e6c4593b7b1c7` |
| S2-A01-V-001 | val | `stage2_(11)causal_structure_high_density_val_v01.json` | S2-CSV-00001 ~ S2-CSV-00150 | 문화재 수장고 — 직접 원인·매개 경로·배경 조건 분리 | `e1290fd6d468711849a5a858d6d1f9d5e61a4efc59a0b937e22c788284af8d1b` |

각 JSON에는 정확히 대응하는 `.source.psv` 하나만 남겼다. 반려된 `_source.jsonl` 4개와 의미 문장을 조합하던 `_author_stage2_direct_psv.py`는 제거했다. 현재 builder는 정본 원고를 읽어 ID와 상위 metadata를 붙이는 포장만 수행하며 concept·relations·text를 만들거나 바꾸지 않는다.

## 2. 구조 및 직접 작성 게이트

| packet | 레코드 | concept 문두 | 2문장 이상 | relation-set lag6 | 내부 5어절 반복 |
|---|---:|---:|---:|---:|---:|
| S2-CSH | 150 | 11 | 150 | 56 | 0 |
| S2-TOH | 150 | 0 | 150 | 70 | 0 |
| S2-RCH | 150 | 0 | 150 | 54 | 0 |
| S2-CSV | 150 | 1 | 150 | 41 | 0 |

모든 packet이 concept 문두 90 이하, 2문장 이상 45 이상, 6행 간격 relation-set 일치 72 이하를 만족한다. ID·text·primary concept exact duplicate는 각각 0건이며, primary concept literal 누락도 0건이다. 모든 source를 사람이 행별로 읽고 인공 합성어, 조사, 이중 주제, 중복 관형, 문장 호응을 교정했다.

## 3. relations 통제 어휘 분포

| relation | 횟수 | relation | 횟수 |
|---|---:|---|---:|
| `is_a` | 0 | `subclass_of` | 0 |
| `part_of` | 40 | `classification` | 3 |
| `boundary` | 285 | `contrast` | 0 |
| `comparison` | 60 | `function` | 7 |
| `role` | 122 | `process` | 514 |
| `state` | 534 | `attribute` | 210 |
| `other` | 72 |  |  |

13개 통제 어휘 밖 값은 0건이다. 모든 레코드의 relations는 2~5개이고, 레코드 내부 중복은 0건이다. Stage 2 pilot의 중심이 사건 경로·상태·인과 조건이므로 `process`, `state`, `boundary`, `attribute`가 큰 것은 설계와 일치한다.

`other` 72건을 원고의 `other_type` 의미로 사람이 묶은 상위 5개 유형은 다음과 같다.

| 순위 | 유형 | 횟수 | 포함 사례 |
|---:|---|---:|---|
| 1 | 기록·로그·동기·관측 결측/상충 | 35 | 시계 동기 결측, 중간 상태 결측, 운전 이력 결측 |
| 2 | 측정 한계·척도·임계·기기 오차 | 14 | 측정 상·하한, 센서 척도 변경, 계수기 오차 |
| 3 | 경로·출처·주체·적용 범위 식별 불명 | 10 | 합류 출처 불명, 처리 경로 불명, 권한 규칙 결측 |
| 4 | 표본·시험·조건 범위·관측 기간 부족 | 7 | 희귀 단일 사례, 시험 범위 부족, 우측 검열 |
| 5 | 동시 개입·교란·복수 경로의 기여도 불명 | 6 | 동시 개입, 동시 교란 요인, 복수 경로 중첩 |

위 다섯 범주는 72건 전체를 중복 없이 수동 집계한 것이다.

## 4. validation 분리와 누출 검사

- `unseen_relation: true`: 18/150 = **12.0%**
- `unseen_relation: false`: 132/150 = 88.0%
- true 레코드가 train에서 관측된 정렬 relation-set을 사용한 오류: 0건
- false 레코드가 train 미관측 정렬 relation-set을 사용한 오류: 0건
- true의 고유 relation-set: 10종
- train–val exact text: 0건
- train–val exact primary concept: 0건
- train–val primary concept + relation-set 조합: 0건
- train–val 5어절 연속 중복: 0건
- Stage 1 고밀도와의 5어절 연속 중복: 0건

Validation은 train의 행 번호에 대응시키지 않고 문화재 수장고라는 별도 concept family에서 독립 작성했다.

## 5. 보일러플레이트·유사도·한국어 품질

- 전체 600레코드의 반복 5어절 유형: 0
- 반복 4어절 문두 유형: 0
- exact text / exact primary concept 중복: 0 / 0
- character 3~5-gram TF-IDF cosine 최댓값: **0.390683** (`< 0.72`)
- 자동 조사·형태 오류 flag: 0
- 사람이 600행을 층화 없이 전수 읽어 조사, 붙여쓰기, 합성어, 중복 수식, 인과 방향, 반례 경계를 확인했다.

가장 높은 유사쌍은 스마트 온실 train의 `전원 전환 준비 완료 매개`와 문화재 수장고 val의 `전원 전환 준비 완료 경로`다. 문장 표면 cosine은 0.390683이고, 대상·근거·판정 조건은 서로 달라 임계값을 충분히 밑돈다.

## 6. 형식·보호 파일·분량

- JSON 파싱·top-level metadata·record key·ID 연속성·range: PASS
- source/package projection 일치: PASS
- UTF-8 한국어가 `\u` escape로 저장된 파일: 0
- 보호 baseline: 371개 확인, SHA-256 불일치 0, 누락 0
- 전체 text 문자 수: 48,653
- 정규식 기준 word unit: 13,187
- 실제 benchmark tokenizer 토큰 수는 이번 pilot 감사에서 측정하지 않았으며, 해당 값으로 환산한 토큰 수를 주장하지 않는다.

## 7. 최종 판정

Stage 2 pilot 4파일은 예약·ID·JSON·통제 relations·validation 12% 일반화 slice·누출 방지·반복 억제·유사도·한국어 전수 검토·보호 SHA 게이트를 모두 통과했다. 현재 파일을 Stage 2 pilot 정본으로 확정할 수 있다.
