# Stage 5 고밀도 데이터셋 생성 준비

- 상태: `ACTUAL_3M_FILE_COUNT_APPROVED_DESIGN_ONLY_CORPUS_AUTHORIZATION_PENDING`
- 교육 역할: 일반화·추론·전이
- 실측 승인 총량: 600 files × 150 = 90,000 records, projected 2,986,500 tokens
- split: train 540 files / validation 60 files = 정확히 90:10
- pilot 완료: 4 files / 600 records; 추가 생성 대기 596 files
- 현행 primary 대비 증보 350, contingency 25 이후 최소 신규 family 325
- validation 일반화 slice: 파일당 18/150 = 12%
- 현행 contingency: 25 family, area·split·ID·version·filename 미부여
- 중앙 예약 원장 SHA-256: `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99`

## 정본

- [범용 생성 지침](../stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md)
- [설계·확정 원장](../stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Design_Spec.md)
- [Stage 2~10 concept-family 중앙 원장](../stage1_highdensity_dataset/TinyLM_Stage2_Stage10_Concept_Family_Reservation.json)
- 이 폴더의 `PREPARATION_MANIFEST.json`은 중앙 원장에서 해당 Stage만 추출한 실행 준비 snapshot이다.

## 현행 primary 교육영역 snapshot

| 교육# | 파일 slot | 영역 | 비율 | train/val files | packet | ID H/V |
|---:|---:|---|---:|---:|---|---|
| 1 | 1 | 귀납 일반화 / `induction` | 20% | 45/5 | `induction_packet` | `S5-INH` / `S5-INV` |
| 2 | 2 | 연역 추론 / `deduction` | 20% | 45/5 | `deduction_packet` | `S5-DEH` / `S5-DEV` |
| 3 | 3 | 반례 기반 일반화 / `counterexample_generalization` | 16% | 36/4 | `counterexample_generalization_packet` | `S5-CGH` / `S5-CGV` |
| 4 | 4 | 새 조합 일반화 / `compositional_novelty` | 16% | 36/4 | `compositional_novelty_packet` | `S5-CNH` / `S5-CNV` |
| 5 | 5 | 유추 전이 / `analogical_transfer` | 16% | 36/4 | `analogical_transfer_packet` | `S5-ATH` / `S5-ATV` |
| 6 | 6 | 도메인 구조 전이 / `structural_transfer` | 12% | 27/3 | `structural_transfer_packet` | `S5-STH` / `S5-STV` |

## 실측 3M 승인 배분과 증보

| 영역 / slug | 기존 T/V | 승인 T/V | 증보 T/V | 계획 version T/V | pilot T/V | 생성 대기 T/V |
|---|---:|---:|---:|---|---:|---:|
| A01 `induction` | 45/5 | 108/12 | +63/+7 | v46~v108 / v06~v12 | 1/1 | 107/11 |
| A02 `deduction` | 45/5 | 108/12 | +63/+7 | v46~v108 / v06~v12 | 0/0 | 108/12 |
| A03 `counterexample_generalization` | 36/4 | 87/10 | +51/+6 | v37~v87 / v05~v10 | 1/0 | 86/10 |
| A04 `compositional_novelty` | 36/4 | 86/10 | +50/+6 | v37~v86 / v05~v10 | 0/0 | 86/10 |
| A05 `analogical_transfer` | 36/4 | 86/9 | +50/+5 | v37~v86 / v05~v09 | 0/0 | 86/9 |
| A06 `structural_transfer` | 27/3 | 65/7 | +38/+4 | v28~v65 / v04~v07 | 1/0 | 64/7 |

## relation·생성 경계

Stage1의 13개 `relations` 통제 어휘를 유지하되, 고차 능력은 6개 `<slug>_packet` `type`으로 평가한다. `relations`는 text에 직접 근거가 있는 2~5개 기초 관계이며 relation focus는 whitelist·필수 교집합·분포 목표가 아니다. 새 relation 이름, 강제 균등화, 고차 능력을 대신하는 `other`를 금지한다.

총량·배분만 승인됐고 추가 corpus 권한은 아직 없다. 다음 승인 뒤 contingency 배치와 신규 family 325개 이상을 중앙 원장·manifest에 먼저 등록·감사하고, pilot 다음 미생성 version 또는 v01부터 직접 작성한다. v100 이상은 자릿수를 확장해 표기하며 현행 pilot 4 files는 보존한다.
