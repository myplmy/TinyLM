# Stage 8 고밀도 데이터셋 생성 준비

- 상태: `ACTUAL_3M_FILE_COUNT_APPROVED_DESIGN_ONLY_CORPUS_AUTHORIZATION_PENDING`
- 교육 역할: 평가·비판·검증·수정
- 실측 승인 총량: 500 files × 150 = 75,000 records, projected 2,971,250 tokens
- split: train 450 files / validation 50 files = 정확히 90:10
- pilot 완료: 4 files / 600 records; 추가 생성 대기 496 files
- 현행 primary 대비 증보 250, contingency 25 이후 최소 신규 family 225
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
| 1 | 1 | 근거 품질 / `evidence_quality` | 20% | 45/5 | `evidence_quality_packet` | `S8-EQH` / `S8-EQV` |
| 2 | 2 | 오류 탐지 / `error_detection` | 20% | 45/5 | `error_detection_packet` | `S8-EDH` / `S8-EDV` |
| 3 | 3 | 논증 비판 / `argument_critique` | 16% | 36/4 | `argument_critique_packet` | `S8-ACH` / `S8-ACV` |
| 4 | 4 | 검증·재현 / `verification_validation` | 16% | 36/4 | `verification_validation_packet` | `S8-VRH` / `S8-VRV` |
| 5 | 5 | 수정·교정 / `revision_correction` | 16% | 36/4 | `revision_correction_packet` | `S8-RCH` / `S8-RCV` |
| 6 | 6 | 확신 보정·유보 / `calibration_abstention` | 12% | 27/3 | `calibration_abstention_packet` | `S8-CAH` / `S8-CAV` |

## 실측 3M 승인 배분과 증보

| 영역 / slug | 기존 T/V | 승인 T/V | 증보 T/V | 계획 version T/V | pilot T/V | 생성 대기 T/V |
|---|---:|---:|---:|---|---:|---:|
| A01 `evidence_quality` | 45/5 | 90/10 | +45/+5 | v46~v90 / v06~v10 | 1/1 | 89/9 |
| A02 `error_detection` | 45/5 | 90/10 | +45/+5 | v46~v90 / v06~v10 | 0/0 | 90/10 |
| A03 `argument_critique` | 36/4 | 72/8 | +36/+4 | v37~v72 / v05~v08 | 1/0 | 71/8 |
| A04 `verification_validation` | 36/4 | 72/8 | +36/+4 | v37~v72 / v05~v08 | 0/0 | 72/8 |
| A05 `revision_correction` | 36/4 | 72/8 | +36/+4 | v37~v72 / v05~v08 | 0/0 | 72/8 |
| A06 `calibration_abstention` | 27/3 | 54/6 | +27/+3 | v28~v54 / v04~v06 | 1/0 | 53/6 |

## relation·생성 경계

Stage1의 13개 `relations` 통제 어휘를 유지하되, 고차 능력은 6개 `<slug>_packet` `type`으로 평가한다. `relations`는 text에 직접 근거가 있는 2~5개 기초 관계이며 relation focus는 whitelist·필수 교집합·분포 목표가 아니다. 새 relation 이름, 강제 균등화, 고차 능력을 대신하는 `other`를 금지한다.

총량·배분만 승인됐고 추가 corpus 권한은 아직 없다. 다음 승인 뒤 contingency 배치와 신규 family 225개 이상을 중앙 원장·manifest에 먼저 등록·감사하고, pilot 다음 미생성 version 또는 v01부터 직접 작성한다. 현행 pilot 4 files는 보존한다.
