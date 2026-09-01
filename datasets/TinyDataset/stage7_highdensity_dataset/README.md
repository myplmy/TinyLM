# Stage 7 고밀도 데이터셋 생성 준비

- 상태: `ACTUAL_3M_FILE_COUNT_APPROVED_DESIGN_ONLY_CORPUS_AUTHORIZATION_PENDING`
- 교육 역할: 지시 수행·대화·실전 사용
- 실측 승인 총량: 470 files × 150 = 70,500 records, projected 3,003,300 tokens
- split: train 423 files / validation 47 files = 정확히 90:10
- pilot 완료: 4 files / 600 records; 추가 생성 대기 466 files
- 현행 primary 대비 증보 220, contingency 25 이후 최소 신규 family 195
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
| 1 | 1 | 지시·의도 해석 / `instruction_intent` | 20% | 45/5 | `instruction_intent_packet` | `S7-IIH` / `S7-IIV` |
| 2 | 2 | 출력 형식 준수 / `output_format` | 20% | 45/5 | `output_format_packet` | `S7-OFH` / `S7-OFV` |
| 3 | 3 | 다턴 대화 수행 / `multiturn_dialogue` | 16% | 36/4 | `multiturn_dialogue_packet` | `S7-MDH` / `S7-MDV` |
| 4 | 4 | 도구·프로토콜 / `tool_protocol` | 16% | 36/4 | `tool_protocol_packet` | `S7-TPH` / `S7-TPV` |
| 5 | 5 | 안전·불확실성 처리 / `safety_uncertainty` | 16% | 36/4 | `safety_uncertainty_packet` | `S7-SUH` / `S7-SUV` |
| 6 | 6 | 실전 task 완결 / `practical_task` | 12% | 27/3 | `practical_task_packet` | `S7-PTH` / `S7-PTV` |

## 실측 3M 승인 배분과 증보

| 영역 / slug | 기존 T/V | 승인 T/V | 증보 T/V | 계획 version T/V | pilot T/V | 생성 대기 T/V |
|---|---:|---:|---:|---|---:|---:|
| A01 `instruction_intent` | 45/5 | 84/9 | +39/+4 | v46~v84 / v06~v09 | 1/1 | 83/8 |
| A02 `output_format` | 45/5 | 84/9 | +39/+4 | v46~v84 / v06~v09 | 0/0 | 84/9 |
| A03 `multiturn_dialogue` | 36/4 | 68/8 | +32/+4 | v37~v68 / v05~v08 | 1/0 | 67/8 |
| A04 `tool_protocol` | 36/4 | 68/8 | +32/+4 | v37~v68 / v05~v08 | 0/0 | 68/8 |
| A05 `safety_uncertainty` | 36/4 | 68/7 | +32/+3 | v37~v68 / v05~v07 | 0/0 | 68/7 |
| A06 `practical_task` | 27/3 | 51/6 | +24/+3 | v28~v51 / v04~v06 | 1/0 | 50/6 |

## relation·생성 경계

Stage1의 13개 `relations` 통제 어휘를 유지하되, 고차 능력은 6개 `<slug>_packet` `type`으로 평가한다. `relations`는 text에 직접 근거가 있는 2~5개 기초 관계이며 relation focus는 whitelist·필수 교집합·분포 목표가 아니다. 새 relation 이름, 강제 균등화, 고차 능력을 대신하는 `other`를 금지한다.

총량·배분만 승인됐고 추가 corpus 권한은 아직 없다. 다음 승인 뒤 contingency 배치와 신규 family 195개 이상을 중앙 원장·manifest에 먼저 등록·감사하고, pilot 다음 미생성 version 또는 v01부터 직접 작성한다. 현행 pilot 4 files는 보존한다.
