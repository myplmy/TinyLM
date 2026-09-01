# TinyLM Stage 9 pilot corpus 최종 감사 보고서

- 감사일: 2026-09-01 (KST)
- 결과: **PASS**
- 범위: 예약된 train 3파일 + validation 1파일, 총 600 records
- 정본: 고밀도 Guide·Design, 중앙 예약 ledger, Stage 9 `PREPARATION_MANIFEST.json`
- 제외: 저밀도·held-out은 source나 품질 비교에 사용하지 않음

## 1. 확정 파일

| 파일 | ID 범위 | records | concept family | SHA-256 |
|---|---:|---:|---|---|
| stage9_(1)research_synthesis_high_density_train_v01.json | S9-RSH-00001 ~ S9-RSH-00150 | 150 | S9-A01-T001: 학술 조사 프로젝트 — 연구 질문과 하위 질문 분해 | `a863c7c6f55788f7c54c3c7b8d1b31df1bde862fef534eab28b2e3d7f2681f90` |
| stage9_(3)workflow_state_high_density_train_v01.json | S9-WSH-00001 ~ S9-WSH-00150 | 150 | S9-A03-T001: 학술 조사 프로젝트 — 작업 상태와 증거 기반 완료 판정 | `5ebdb9f908aafbde8d51d0f8c42178a463828e6882b82c0436fb142b0f9758ff` |
| stage9_(6)provenance_audit_high_density_train_v01.json | S9-PAH-00001 ~ S9-PAH-00150 | 150 | S9-A06-T001: 학술 조사 프로젝트 — 원본·파생물·변환 계보 기록 | `a996f6c0675c4d8ed0ebb93e2ba6e0371cc4959334597593272a1cd00a935f01` |
| stage9_(1)research_synthesis_high_density_val_v01.json | S9-RSV-00001 ~ S9-RSV-00150 | 150 | S9-A01-V001: 남극 보급 운영 — 연구 질문과 하위 질문 분해 | `d99cf120fe8ef12aae92561cf9da606637197f2370273f4be66d814d159b2b31` |

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
| stage9_(1)research_synthesis_high_density_train_v01.json | 0 | 150 | 3 | 82 | 2 |
| stage9_(1)research_synthesis_high_density_val_v01.json | 34 | 149 | 8 | 32 | 1 |
| stage9_(3)workflow_state_high_density_train_v01.json | 0 | 148 | 2 | 65 | 1 |
| stage9_(6)provenance_audit_high_density_train_v01.json | 0 | 150 | 1 | 90 | 1 |

구조 gate는 파일별 concept 문두 `<=90`, 2문장 이상 `>=45`, relation-set lag6 `<=72`이며 모두 충족한다. validation 대응 행 cosine의 최대값은 `0.035161`, 평균은 `0.006300`로 행별 골격 치환 징후가 없다.

## 3. 문자 3~5-gram TF-IDF cosine

검토 경계는 `0.72`이며, 경계 이상 쌍은 모든 비교에서 **0건**이다.

| 비교 | 최대 cosine | 상위 pair |
|---|---:|---|
| 내부 | 0.170729 | `S9-RSV-00039` / `S9-RSV-00091` |
| train-val | 0.119528 | `S9-RSH-00059` / `S9-RSV-00037` |
| Stage1 고밀도 교차 | 0.186864 | `S9-RSH-00147` / `S1-TUH-0823` |
| Stage8-10 동료 교차 | 0.305367 | `S9-RSH-00087` / `S8-EQH-00027` |

상위 20쌍은 문장을 직접 대조했으며, 서로 다른 객체·판정축을 구체적으로 설명하는 정상적인 인접 쌍이었다.

## 4. 한국어 품질 감사

- primary concept literal 누락: **0건**. 개념명과 본문 리터럴의 띄어쓰기를 source 600행에서 대조했다.
- 광범위 조사 후보: **51건**; 전수 문맥 검토 결과 활용형 어미·복합명사 말음 오탐이며 실제 조사 오류 **0건**
- 비정상 무공백 장문, 제어문자, 깨진 Unicode, 문장 호응 오류: **0건**
- 템플릿/보일러플레이트: 반복 5어절과 도입부가 모두 0이고, 각 행이 구체적 자료·제약·판정 범위를 가진 독립 완결문임을 확인

## 5. relations 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 2 |
| `part_of` | 140 |
| `classification` | 216 |
| `boundary` | 401 |
| `contrast` | 114 |
| `comparison` | 204 |
| `function` | 193 |
| `role` | 90 |
| `process` | 344 |
| `state` | 386 |
| `attribute` | 256 |
| `other` | 72 |

### `other` 상위 개념 유형 5개

| 순위 | 유형 | 횟수 |
|---:|---|---:|
| 1 | 행정 허가 범위 | 2 |
| 2 | 조작적 정의 | 1 |
| 3 | 진단 계층 | 1 |
| 4 | 응답 경로 | 1 |
| 5 | 부재 추론 | 1 |

모든 record는 13개 통제어휘 중 2~5개를 가지며 record 내부 relation 중복은 0이다. `other`는 source의 `other_type`과 전부 대응한다.

## 6. 분량·보호 감사

- text: 48,988자, 최소 63, 최대 132, 평균 81.647자
- 단어 단위: 13,031개, 최소 15, 최대 36, 평균 21.718개
- 보호 baseline: 371파일 재해시, mismatch **0건**
- 중앙 ledger SHA-256: `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99`

기계 판독 상세는 `audit_reports/machine/TinyLM_Stage9_Pilot_Audit_2026-09-01.json`에 보존했다.
