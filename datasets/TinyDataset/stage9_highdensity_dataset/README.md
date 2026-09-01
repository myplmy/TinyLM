# Stage 9 고밀도 데이터셋 생성 준비

- 상태: `ACTUAL_3M_FILE_COUNT_APPROVED_DESIGN_ONLY_CORPUS_AUTHORIZATION_PENDING`
- 교육 역할: 연구·도구 오케스트레이션·지속 워크플로
- 실측 승인 총량: 510 files × 150 = 76,500 records, projected 3,025,447 tokens
- split: train 459 files / validation 51 files = 정확히 90:10
- pilot 완료: 4 files / 600 records; 추가 생성 대기 506 files
- 현행 primary 대비 증보 260, contingency 25 이후 최소 신규 family 235
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
| 1 | 1 | 조사·종합 / `research_synthesis` | 20% | 45/5 | `research_synthesis_packet` | `S9-RSH` / `S9-RSV` |
| 2 | 2 | 도구 오케스트레이션 / `tool_orchestration` | 20% | 45/5 | `tool_orchestration_packet` | `S9-TOH` / `S9-TOV` |
| 3 | 3 | 워크플로 상태 지속 / `workflow_state` | 16% | 36/4 | `workflow_state_packet` | `S9-WSH` / `S9-WSV` |
| 4 | 4 | 협업·인계 / `collaboration_handoff` | 16% | 36/4 | `collaboration_handoff_packet` | `S9-CHH` / `S9-CHV` |
| 5 | 5 | 모니터링·적응 / `monitoring_adaptation` | 16% | 36/4 | `monitoring_adaptation_packet` | `S9-MAH` / `S9-MAV` |
| 6 | 6 | 출처·감사 가능성 / `provenance_audit` | 12% | 27/3 | `provenance_audit_packet` | `S9-PAH` / `S9-PAV` |

## 실측 3M 승인 배분과 증보

| 영역 / slug | 기존 T/V | 승인 T/V | 증보 T/V | 계획 version T/V | pilot T/V | 생성 대기 T/V |
|---|---:|---:|---:|---|---:|---:|
| A01 `research_synthesis` | 45/5 | 92/11 | +47/+6 | v46~v92 / v06~v11 | 1/1 | 91/10 |
| A02 `tool_orchestration` | 45/5 | 92/10 | +47/+5 | v46~v92 / v06~v10 | 0/0 | 92/10 |
| A03 `workflow_state` | 36/4 | 74/8 | +38/+4 | v37~v74 / v05~v08 | 1/0 | 73/8 |
| A04 `collaboration_handoff` | 36/4 | 73/8 | +37/+4 | v37~v73 / v05~v08 | 0/0 | 73/8 |
| A05 `monitoring_adaptation` | 36/4 | 73/8 | +37/+4 | v37~v73 / v05~v08 | 0/0 | 73/8 |
| A06 `provenance_audit` | 27/3 | 55/6 | +28/+3 | v28~v55 / v04~v06 | 1/0 | 54/6 |

## relation·생성 경계

Stage1의 13개 `relations` 통제 어휘를 유지하되, 고차 능력은 6개 `<slug>_packet` `type`으로 평가한다. `relations`는 text에 직접 근거가 있는 2~5개 기초 관계이며 relation focus는 whitelist·필수 교집합·분포 목표가 아니다. 새 relation 이름, 강제 균등화, 고차 능력을 대신하는 `other`를 금지한다.

총량·배분만 승인됐고 추가 corpus 권한은 아직 없다. 다음 승인 뒤 contingency 배치와 신규 family 235개 이상을 중앙 원장·manifest에 먼저 등록·감사하고, pilot 다음 미생성 version 또는 v01부터 직접 작성한다. 현행 pilot 4 files는 보존한다.
