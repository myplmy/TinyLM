# TinyLM Stage 8 pilot corpus 최종 감사 보고서

- 감사일: 2026-09-01 (KST)
- 결과: **PASS**
- 범위: 예약된 train 3파일 + validation 1파일, 총 600 records
- 정본: 고밀도 Guide·Design, 중앙 예약 ledger, Stage 8 `PREPARATION_MANIFEST.json`
- 제외: 저밀도·held-out은 source나 품질 비교에 사용하지 않음

## 1. 확정 파일

| 파일 | ID 범위 | records | concept family | SHA-256 |
|---|---:|---:|---|---|
| stage8_(1)evidence_quality_high_density_train_v01.json | S8-EQH-00001 ~ S8-EQH-00150 | 150 | S8-A01-T001: 과학 실험 보고서 — 주장과 직접·간접 근거 연결 | `5f6f31fe9819ca62f3252980c9dca86711a201de346f07e73f7f021af615097f` |
| stage8_(3)argument_critique_high_density_train_v01.json | S8-ACH-00001 ~ S8-ACH-00150 | 150 | S8-A03-T001: 과학 실험 보고서 — 주장·전제·근거 구조 복원 | `333903bd0b6e2e17ee179c30c5dfc45c57bc732d28c1326f0729b9c23c655f11` |
| stage8_(6)calibration_abstention_high_density_train_v01.json | S8-CAH-00001 ~ S8-CAH-00150 | 150 | S8-A06-T001: 과학 실험 보고서 — 증거 강도와 확신 수준 정렬 | `7e6ccc64b6e82fb9416e629ca40384c53355cce246c8529cc1ec11218b17a8ce` |
| stage8_(1)evidence_quality_high_density_val_v01.json | S8-EQV-00001 ~ S8-EQV-00150 | 150 | S8-A01-V001: 박물관 소장 이력 보고 — 주장과 직접·간접 근거 연결 | `e0709681e8a555cfae447e17b909442281fe5dd7d13390c12c368978d52ed1b9` |

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
| stage8_(1)evidence_quality_high_density_train_v01.json | 68 | 83 | 1 | 74 | 1 |
| stage8_(1)evidence_quality_high_density_val_v01.json | 87 | 72 | 1 | 75 | 1 |
| stage8_(3)argument_critique_high_density_train_v01.json | 0 | 150 | 2 | 67 | 1 |
| stage8_(6)calibration_abstention_high_density_train_v01.json | 57 | 92 | 2 | 64 | 1 |

구조 gate는 파일별 concept 문두 `<=90`, 2문장 이상 `>=45`, relation-set lag6 `<=72`이며 모두 충족한다. validation 대응 행 cosine의 최대값은 `0.039415`, 평균은 `0.003205`로 행별 골격 치환 징후가 없다.

## 3. 문자 3~5-gram TF-IDF cosine

검토 경계는 `0.72`이며, 경계 이상 쌍은 모든 비교에서 **0건**이다.

| 비교 | 최대 cosine | 상위 pair |
|---|---:|---|
| 내부 | 0.198742 | `S8-EQH-00013` / `S8-CAH-00018` |
| train-val | 0.146771 | `S8-CAH-00039` / `S8-EQV-00107` |
| Stage1 고밀도 교차 | 0.193942 | `S8-CAH-00121` / `S1-ATH-0878` |
| Stage8-10 동료 교차 | 0.305367 | `S8-EQH-00027` / `S9-RSH-00087` |

상위 20쌍은 문장을 직접 대조했으며, 서로 다른 객체·판정축을 구체적으로 설명하는 정상적인 인접 쌍이었다.

## 4. 한국어 품질 감사

- primary concept literal 누락: **0건**. 개념명과 본문 리터럴의 띄어쓰기를 source 600행에서 대조했다.
- 광범위 조사 후보: **49건**; 전수 문맥 검토 결과 활용형 어미·복합명사 말음 오탐이며 실제 조사 오류 **0건**
- 비정상 무공백 장문, 제어문자, 깨진 Unicode, 문장 호응 오류: **0건**
- 템플릿/보일러플레이트: 반복 5어절과 도입부가 모두 0이고, 각 행이 구체적 자료·제약·판정 범위를 가진 독립 완결문임을 확인

## 5. relations 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 3 |
| `subclass_of` | 5 |
| `part_of` | 160 |
| `classification` | 275 |
| `boundary` | 468 |
| `contrast` | 153 |
| `comparison` | 296 |
| `function` | 90 |
| `role` | 48 |
| `process` | 243 |
| `state` | 260 |
| `attribute` | 304 |
| `other` | 104 |

### `other` 상위 개념 유형 5개

| 순위 | 유형 | 횟수 |
|---:|---|---:|
| 1 | 대안 원인 | 2 |
| 2 | 관측 공백 | 2 |
| 3 | 복합 원인 | 2 |
| 4 | 전이 전제 | 1 |
| 5 | 기록 단절 | 1 |

모든 record는 13개 통제어휘 중 2~5개를 가지며 record 내부 relation 중복은 0이다. `other`는 source의 `other_type`과 전부 대응한다.

## 6. 분량·보호 감사

- text: 49,011자, 최소 56, 최대 155, 평균 81.685자
- 단어 단위: 13,275개, 최소 15, 최대 43, 평균 22.125개
- 보호 baseline: 371파일 재해시, mismatch **0건**
- 중앙 ledger SHA-256: `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99`

기계 판독 상세는 `audit_reports/machine/TinyLM_Stage8_Pilot_Audit_2026-09-01.json`에 보존했다.
