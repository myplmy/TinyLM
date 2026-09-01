# Stage 6 고밀도 데이터셋 생성 준비

- 상태: `ACTUAL_3M_FILE_COUNT_APPROVED_DESIGN_ONLY_CORPUS_AUTHORIZATION_PENDING`
- 교육 역할: 지식 통합·장문맥·복합 문제
- 실측 승인 총량: 410 files × 150 = 61,500 records, projected 2,985,928 tokens
- split: train 369 files / validation 41 files = 정확히 90:10
- pilot 완료: 4 files / 600 records; 추가 생성 대기 406 files
- 현행 primary 대비 증보 160, contingency 25 이후 최소 신규 family 135
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
| 1 | 1 | 장문맥 유지 / `long_context` | 20% | 45/5 | `long_context_packet` | `S6-LCH` / `S6-LCV` |
| 2 | 2 | 다단계 추론 / `multihop_inference` | 20% | 45/5 | `multihop_inference_packet` | `S6-MHH` / `S6-MHV` |
| 3 | 3 | 복합 제약 만족 / `constraint_satisfaction` | 16% | 36/4 | `constraint_satisfaction_packet` | `S6-CSH` / `S6-CSV` |
| 4 | 4 | 다중 목표·절충 / `multiobjective_tradeoff` | 16% | 36/4 | `multiobjective_tradeoff_packet` | `S6-MTH` / `S6-MTV` |
| 5 | 5 | 다중 출처 통합 / `multisource_integration` | 16% | 36/4 | `multisource_integration_packet` | `S6-MIH` / `S6-MIV` |
| 6 | 6 | 불확실성 관리 / `uncertainty_management` | 12% | 27/3 | `uncertainty_management_packet` | `S6-UMH` / `S6-UMV` |

## 실측 3M 승인 배분과 증보

| 영역 / slug | 기존 T/V | 승인 T/V | 증보 T/V | 계획 version T/V | pilot T/V | 생성 대기 T/V |
|---|---:|---:|---:|---|---:|---:|
| A01 `long_context` | 45/5 | 74/8 | +29/+3 | v46~v74 / v06~v08 | 1/1 | 73/7 |
| A02 `multihop_inference` | 45/5 | 74/8 | +29/+3 | v46~v74 / v06~v08 | 0/0 | 74/8 |
| A03 `constraint_satisfaction` | 36/4 | 59/7 | +23/+3 | v37~v59 / v05~v07 | 1/0 | 58/7 |
| A04 `multiobjective_tradeoff` | 36/4 | 59/7 | +23/+3 | v37~v59 / v05~v07 | 0/0 | 59/7 |
| A05 `multisource_integration` | 36/4 | 59/6 | +23/+2 | v37~v59 / v05~v06 | 0/0 | 59/6 |
| A06 `uncertainty_management` | 27/3 | 44/5 | +17/+2 | v28~v44 / v04~v05 | 1/0 | 43/5 |

## relation·생성 경계

Stage1의 13개 `relations` 통제 어휘를 유지하되, 고차 능력은 6개 `<slug>_packet` `type`으로 평가한다. `relations`는 text에 직접 근거가 있는 2~5개 기초 관계이며 relation focus는 whitelist·필수 교집합·분포 목표가 아니다. 새 relation 이름, 강제 균등화, 고차 능력을 대신하는 `other`를 금지한다.

총량·배분만 승인됐고 추가 corpus 권한은 아직 없다. 다음 승인 뒤 contingency 배치와 신규 family 135개 이상을 중앙 원장·manifest에 먼저 등록·감사하고, pilot 다음 미생성 version 또는 v01부터 직접 작성한다. 현행 pilot 4 files는 보존한다.
