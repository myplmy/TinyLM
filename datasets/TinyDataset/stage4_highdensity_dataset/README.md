# Stage 4 고밀도 데이터셋 생성 준비

- 상태: `ACTUAL_3M_FILE_COUNT_APPROVED_DESIGN_ONLY_CORPUS_AUTHORIZATION_PENDING`
- 교육 역할: 문맥·담화·지시·대화
- 실측 승인 총량: 440 files × 150 = 66,000 records, projected 2,990,900 tokens
- split: train 396 files / validation 44 files = 정확히 90:10
- pilot 완료: 4 files / 600 records; 추가 생성 대기 436 files
- 현행 primary 대비 증보 190, contingency 25 이후 최소 신규 family 165
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
| 1 | 1 | 담화 지시·참조 / `discourse_reference` | 20% | 45/5 | `discourse_reference_packet` | `S4-DRH` / `S4-DRV` |
| 2 | 2 | 생략·공동지시 / `ellipsis_coreference` | 20% | 45/5 | `ellipsis_coreference_packet` | `S4-ECH` / `S4-ECV` |
| 3 | 3 | 대화 상태 / `dialogue_state` | 16% | 36/4 | `dialogue_state_packet` | `S4-DSH` / `S4-DSV` |
| 4 | 4 | 질문–응답 적합성 / `question_answer` | 16% | 36/4 | `question_answer_packet` | `S4-QAH` / `S4-QAV` |
| 5 | 5 | 화행·대화 행위 / `speech_act_pragmatics` | 16% | 36/4 | `speech_act_pragmatics_packet` | `S4-SPH` / `S4-SPV` |
| 6 | 6 | 함축·맥락 의존 / `implicature_context` | 12% | 27/3 | `implicature_context_packet` | `S4-ICH` / `S4-ICV` |

## 실측 3M 승인 배분과 증보

| 영역 / slug | 기존 T/V | 승인 T/V | 증보 T/V | 계획 version T/V | pilot T/V | 생성 대기 T/V |
|---|---:|---:|---:|---|---:|---:|
| A01 `discourse_reference` | 45/5 | 79/9 | +34/+4 | v46~v79 / v06~v09 | 1/1 | 78/8 |
| A02 `ellipsis_coreference` | 45/5 | 79/9 | +34/+4 | v46~v79 / v06~v09 | 0/0 | 79/9 |
| A03 `dialogue_state` | 36/4 | 64/7 | +28/+3 | v37~v64 / v05~v07 | 1/0 | 63/7 |
| A04 `question_answer` | 36/4 | 63/7 | +27/+3 | v37~v63 / v05~v07 | 0/0 | 63/7 |
| A05 `speech_act_pragmatics` | 36/4 | 63/7 | +27/+3 | v37~v63 / v05~v07 | 0/0 | 63/7 |
| A06 `implicature_context` | 27/3 | 48/5 | +21/+2 | v28~v48 / v04~v05 | 1/0 | 47/5 |

## relation·생성 경계

Stage1의 13개 `relations` 통제 어휘를 유지하되, 고차 능력은 6개 `<slug>_packet` `type`으로 평가한다. `relations`는 text에 직접 근거가 있는 2~5개 기초 관계이며 relation focus는 whitelist·필수 교집합·분포 목표가 아니다. 새 relation 이름, 강제 균등화, 고차 능력을 대신하는 `other`를 금지한다.

총량·배분만 승인됐고 추가 corpus 권한은 아직 없다. 다음 승인 뒤 contingency 배치와 신규 family 165개 이상을 중앙 원장·manifest에 먼저 등록·감사하고, pilot 다음 미생성 version 또는 v01부터 직접 작성한다. 현행 pilot 4 files는 보존한다.
