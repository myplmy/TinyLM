# TinyLM Stage 10 pilot corpus 최종 감사 보고서

- 감사일: 2026-09-01 (KST)
- 결과: **PASS**
- 범위: 예약된 train 3파일 + validation 1파일, 총 600 records
- 정본: 고밀도 Guide·Design, 중앙 예약 ledger, Stage 10 `PREPARATION_MANIFEST.json`
- 제외: 저밀도·held-out은 source나 품질 비교에 사용하지 않음

## 1. 확정 파일

| 파일 | ID 범위 | records | concept family | SHA-256 |
|---|---:|---:|---|---|
| stage10_(1)expert_integration_high_density_train_v01.json | S10-EIH-00001 ~ S10-EIH-00150 | 150 | S10-A01-T001: 연안 기후적응 전략 — 도메인별 개념·단위·증거 기준 정렬 | `268c1f3f4164403039ad675a6b9fe4f4edc5a0cbcab65db1680c42bb1023ca9c` |
| stage10_(3)long_horizon_high_density_train_v01.json | S10-LHH-00001 ~ S10-LHH-00150 | 150 | S10-A03-T001: 연안 기후적응 전략 — 장기 목표·중간 성과·종료 기준 계층화 | `305c247ac34ded578886f4268ed7864e02ab888d474b7661e370717254fe4351` |
| stage10_(6)metacognitive_control_high_density_train_v01.json | S10-MCH-00001 ~ S10-MCH-00150 | 150 | S10-A06-T001: 연안 기후적응 전략 — 지식 공백·가정·취약 단계 식별 | `6e0e4c0da1e780a50d7b5ce3fbbf355e9b9a858c6680d152729c3015259b141d` |
| stage10_(1)expert_integration_high_density_val_v01.json | S10-EIV-00001 ~ S10-EIV-00150 | 150 | S10-A01-V001: 문화재 반환 협상 — 도메인별 개념·단위·증거 기준 정렬 | `ff33bb90d3acf2d96d8001d7a94d1b623a1428f64b4fbada1f5c1d39fc615e3e` |

source 원고는 파일당 150행의 고정 JSONL이며 builder는 ID·metadata 포장만 수행한다. 출력 600 records와 source 600행은 text·primary concept·relations가 전부 일치한다.

## 2. 구조·중복·누출 감사

- JSON/UTF-8/schema/metadata/ID/range/source 대응 오류: **0**
- exact ID/primary concept/text/primary+relation-set 중복: **0 / 0 / 0 / 0**
- 내부 반복 5어절 / 반복 4어절 도입부 / 인접 단어 중복: **0 / 0 / 0**
- train-val exact primary/text/primary+relation-set: **0 / 0 / 0**
- Stage1 고밀도 exact primary/text/primary+relation-set 및 공통 5어절: **0 / 0 / 0 / 0**
- Stage8-10 동료 pilot exact primary/text 및 공통 5어절: **0 / 0 / 0**
- validation `unseen_relation=true`: **18/150 = 12.0%**. true relation-set은 train 미관측, false relation-set은 train 관측, 개별 relation label은 모두 train 관측이다.

| 파일 | concept literal 문두 | 2문장 이상 | relation-set lag6 | 고유 relation-set | 동일 4어절 suffix 최대 |
|---|---:|---:|---:|---:|---:|
| stage10_(1)expert_integration_high_density_train_v01.json | 60 | 149 | 0 | 77 | 1 |
| stage10_(1)expert_integration_high_density_val_v01.json | 70 | 150 | 11 | 31 | 1 |
| stage10_(3)long_horizon_high_density_train_v01.json | 48 | 140 | 10 | 53 | 1 |
| stage10_(6)metacognitive_control_high_density_train_v01.json | 6 | 150 | 0 | 60 | 1 |

구조 gate는 파일별 concept 문두 `<=90`, 2문장 이상 `>=45`, relation-set lag6 `<=72`이며 모두 충족한다. validation 대응 행 cosine의 최대값은 `0.035033`, 평균은 `0.004544`로 행별 골격 치환 징후가 없다.

## 3. 문자 3~5-gram TF-IDF cosine

검토 경계는 `0.72`이며, 경계 이상 쌍은 모든 비교에서 **0건**이다.

| 비교 | 최대 cosine | 상위 pair |
|---|---:|---|
| 내부 | 0.134372 | `S10-EIV-00014` / `S10-EIV-00024` |
| train-val | 0.092804 | `S10-EIH-00067` / `S10-EIV-00001` |
| Stage1 고밀도 교차 | 0.230981 | `S10-LHH-00021` / `S1-IDH-4647` |
| Stage8-10 동료 교차 | 0.181780 | `S10-MCH-00116` / `S9-RSH-00113` |

상위 20쌍은 문장을 직접 대조했으며, 서로 다른 객체·판정축을 구체적으로 설명하는 정상적인 인접 쌍이었다.

## 4. 한국어 품질 감사

- primary concept literal 누락: **0건**. 개념명과 본문 리터럴의 띄어쓰기를 source 600행에서 대조했다.
- 광범위 조사 후보: **68건**; 전수 문맥 검토 결과 활용형 어미·복합명사 말음 오탐이며 실제 조사 오류 **0건**
- 비정상 무공백 장문, 제어문자, 깨진 Unicode, 문장 호응 오류: **0건**
- 템플릿/보일러플레이트: 반복 5어절과 도입부가 모두 0이고, 각 행이 구체적 자료·제약·판정 범위를 가진 독립 완결문임을 확인

## 5. relations 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 108 |
| `classification` | 129 |
| `boundary` | 517 |
| `contrast` | 64 |
| `comparison` | 211 |
| `function` | 241 |
| `role` | 195 |
| `process` | 324 |
| `state` | 414 |
| `attribute` | 145 |
| `other` | 69 |

### `other` 상위 개념 유형 5개

| 순위 | 유형 | 횟수 |
|---:|---|---:|
| 1 | 규범 갱신 절차 | 2 |
| 2 | 제도 적용 경계 | 1 |
| 3 | 재산권 조정 | 1 |
| 4 | 토지이용 규제 | 1 |
| 5 | 비등록 거주 증거 | 1 |

모든 record는 13개 통제어휘 중 2~5개를 가지며 record 내부 relation 중복은 0이다. `other`는 source의 `other_type`과 전부 대응한다.

## 6. 분량·보호 감사

- text: 49,942자, 최소 51, 최대 148, 평균 83.237자
- 단어 단위: 12,847개, 최소 11, 최대 37, 평균 21.412개
- 보호 baseline: 371파일 재해시, mismatch **0건**
- 중앙 ledger SHA-256: `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99`

기계 판독 상세는 `audit_reports/machine/TinyLM_Stage10_Pilot_Audit_2026-09-01.json`에 보존했다.
