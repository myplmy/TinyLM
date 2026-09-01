# Stage 10 고밀도 데이터셋 생성 준비

- 상태: `ACTUAL_3M_FILE_COUNT_APPROVED_DESIGN_ONLY_CORPUS_AUTHORIZATION_PENDING`
- 교육 역할: 통합 전문 수행·장기 안전 자율성
- 실측 승인 총량: 490 files × 150 = 73,500 records, projected 3,017,910 tokens
- split: train 441 files / validation 49 files = 정확히 90:10
- pilot 완료: 4 files / 600 records; 추가 생성 대기 486 files
- 현행 primary 대비 증보 240, contingency 25 이후 최소 신규 family 215
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
| 1 | 1 | 전문 지식 통합 / `expert_integration` | 20% | 45/5 | `expert_integration_packet` | `S10-EIH` / `S10-EIV` |
| 2 | 2 | 교차 도메인 종합 / `crossdomain_synthesis` | 20% | 45/5 | `crossdomain_synthesis_packet` | `S10-CSH` / `S10-CSV` |
| 3 | 3 | 장기 계획·자율 수행 / `long_horizon` | 16% | 36/4 | `long_horizon_packet` | `S10-LHH` / `S10-LHV` |
| 4 | 4 | 적대적·비정상 조건 강건성 / `adversarial_robustness` | 16% | 36/4 | `adversarial_robustness_packet` | `S10-ARH` / `S10-ARV` |
| 5 | 5 | 안전 자율성 / `safe_autonomy` | 16% | 36/4 | `safe_autonomy_packet` | `S10-SAH` / `S10-SAV` |
| 6 | 6 | 메타인지·자기통제 / `metacognitive_control` | 12% | 27/3 | `metacognitive_control_packet` | `S10-MCH` / `S10-MCV` |

## 실측 3M 승인 배분과 증보

| 영역 / slug | 기존 T/V | 승인 T/V | 증보 T/V | 계획 version T/V | pilot T/V | 생성 대기 T/V |
|---|---:|---:|---:|---|---:|---:|
| A01 `expert_integration` | 45/5 | 88/10 | +43/+5 | v46~v88 / v06~v10 | 1/1 | 87/9 |
| A02 `crossdomain_synthesis` | 45/5 | 88/9 | +43/+4 | v46~v88 / v06~v09 | 0/0 | 88/9 |
| A03 `long_horizon` | 36/4 | 71/8 | +35/+4 | v37~v71 / v05~v08 | 1/0 | 70/8 |
| A04 `adversarial_robustness` | 36/4 | 71/8 | +35/+4 | v37~v71 / v05~v08 | 0/0 | 71/8 |
| A05 `safe_autonomy` | 36/4 | 70/8 | +34/+4 | v37~v70 / v05~v08 | 0/0 | 70/8 |
| A06 `metacognitive_control` | 27/3 | 53/6 | +26/+3 | v28~v53 / v04~v06 | 1/0 | 52/6 |

## relation·생성 경계

Stage1의 13개 `relations` 통제 어휘를 유지하되, 고차 능력은 6개 `<slug>_packet` `type`으로 평가한다. `relations`는 text에 직접 근거가 있는 2~5개 기초 관계이며 relation focus는 whitelist·필수 교집합·분포 목표가 아니다. 새 relation 이름, 강제 균등화, 고차 능력을 대신하는 `other`를 금지한다.

총량·배분만 승인됐고 추가 corpus 권한은 아직 없다. 다음 승인 뒤 contingency 배치와 신규 family 215개 이상을 중앙 원장·manifest에 먼저 등록·감사하고, pilot 다음 미생성 version 또는 v01부터 직접 작성한다. 현행 pilot 4 files는 보존한다.
