# Stage 2 고밀도 데이터셋 생성 준비

- 상태: `ACTUAL_3M_GENERATION_IN_PROGRESS_A01_A02_TRAIN_COMPLETE`
- 교육 역할: 복합 관계·의존·인과·조건 구조
- 실측 승인 총량: 480 files × 150 = 72,000 records, projected 2,997,000 tokens
- split: train 432 files / validation 48 files = 정확히 90:10
- 현행 완료: 176 files / 26,400 records(A01 train 87, A02 train 86, A03 train pilot 1, A06 train pilot 1, A01 validation pilot 1)
- 현행 잔여: 304 files / 45,600 records(train 257, validation 47)
- 현행 primary 대비 증보 230, contingency 25 이후 최소 신규 family 205
- validation 일반화 slice: 파일당 18/150 = 12%
- 현행 contingency: 25 family, area·split·ID·version·filename 미부여
- 중앙 예약 원장 SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

## 정본

- [범용 생성 지침](../stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md)
- [설계·확정 원장](../stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Design_Spec.md)
- [Stage 2~10 concept-family 중앙 원장](../stage1_highdensity_dataset/TinyLM_Stage2_Stage10_Concept_Family_Reservation.json)
- 이 폴더의 `PREPARATION_MANIFEST.json`은 중앙 원장에서 해당 Stage만 추출한 실행 준비 snapshot이다.

## 현행 primary 교육영역 snapshot

| 교육# | 파일 slot | 영역 | 비율 | train/val files | packet | ID H/V |
|---:|---:|---|---:|---:|---|---|
| 1 | 11 | 원인 구조 / `causal_structure` | 20% | 45/5 | `causal_structure_packet` | `S2-CSH` / `S2-CSV` |
| 2 | 12 | 조건·의존 구조 / `conditional_dependency` | 20% | 45/5 | `conditional_dependency_packet` | `S2-CDH` / `S2-CDV` |
| 3 | 13 | 시간 순서·간격 / `temporal_order` | 16% | 36/4 | `temporal_order_packet` | `S2-TOH` / `S2-TOV` |
| 4 | 14 | 상태 전이·동역학 / `state_transition` | 16% | 36/4 | `state_transition_packet` | `S2-STH` / `S2-STV` |
| 5 | 15 | 가능성·양상 / `modality_possibility` | 16% | 36/4 | `modality_possibility_packet` | `S2-MPH` / `S2-MPV` |
| 6 | 16 | 다중 관계 조합 / `relational_composition` | 12% | 27/3 | `relational_composition_packet` | `S2-RCH` / `S2-RCV` |

## 실측 3M 승인 배분과 증보

| 영역 / slug | 기존 T/V | 승인 T/V | 증보 T/V | 계획 version T/V | 현재 완료 T/V | 현재 잔여 T/V |
|---|---:|---:|---:|---|---:|---:|
| A01 `causal_structure` | 45/5 | 87/9 | +42/+4 | v46~v87 / v06~v09 | 87/1 | 0/8 |
| A02 `conditional_dependency` | 45/5 | 86/9 | +41/+4 | v46~v86 / v06~v09 | 86/0 | 0/9 |
| A03 `temporal_order` | 36/4 | 69/8 | +33/+4 | v37~v69 / v05~v08 | 1/0 | 68/8 |
| A04 `state_transition` | 36/4 | 69/8 | +33/+4 | v37~v69 / v05~v08 | 0/0 | 69/8 |
| A05 `modality_possibility` | 36/4 | 69/8 | +33/+4 | v37~v69 / v05~v08 | 0/0 | 69/8 |
| A06 `relational_composition` | 27/3 | 52/6 | +25/+3 | v28~v52 / v04~v06 | 1/0 | 51/6 |

## relation·생성 경계

Stage1의 13개 `relations` 통제 어휘를 유지하되, 고차 능력은 6개 `<slug>_packet` `type`으로 평가한다. `relations`는 text에 직접 근거가 있는 2~5개 기초 관계이며 relation focus는 whitelist·필수 교집합·분포 목표가 아니다. 새 relation 이름, 강제 균등화, 고차 능력을 대신하는 `other`를 금지한다.

총량·배분·family 예약과 실제 corpus 생성은 승인됐다. A01·A02 train은 영역별 직접 작성→일괄 감사·직접 교정→포장을 완료했으며 다음은 기존 A03 v01 pilot을 보존한 `S2-A03-T-002`다. `PREPARATION_MANIFEST.json`은 예약 snapshot이므로 완료율은 checkpoint·중앙 작업원장·영역 통합 감사보고서를 우선한다.

## Stage2 legacy 보호

`stage2_(2)attribute_high_density_*`는 기존 완료·수정 금지 pattern이며 새 3M mixture에서 제외한다. 새 Stage2 영역은 파일 slot `(11)`~`(16)`을 사용한다.
