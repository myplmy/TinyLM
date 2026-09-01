# Stage 7 고밀도 데이터셋 생성 준비

- 상태: `PREPARED_NO_CORPUS_GENERATED`
- 교육 역할: 지시 수행·대화·실전 사용
- 설계 목표: 약 3M token(실제 tokenizer pilot 전 잠정)
- primary: 250 files × 150 = 37,500 records
- split: train 225 files / validation 25 files = 정확히 90:10
- validation 일반화 slice 계획: 파일당 18/150 = 12%
- contingency: 25 family, ID·version·filename 미부여·비활성
- 중앙 예약 원장 SHA-256: `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99`

## 정본

- [범용 생성 지침](../stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md)
- [설계·확정 원장](../stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Design_Spec.md)
- [Stage 2~10 concept-family 중앙 원장](../stage1_highdensity_dataset/TinyLM_Stage2_Stage10_Concept_Family_Reservation.json)
- 이 폴더의 `PREPARATION_MANIFEST.json`은 중앙 원장에서 해당 Stage만 추출한 실행 준비 snapshot이다.

## 세부 교육영역

| 교육# | 파일 slot | 영역 | 비율 | train/val files | packet | ID H/V |
|---:|---:|---|---:|---:|---|---|
| 1 | 1 | 지시·의도 해석 / `instruction_intent` | 20% | 45/5 | `instruction_intent_packet` | `S7-IIH` / `S7-IIV` |
| 2 | 2 | 출력 형식 준수 / `output_format` | 20% | 45/5 | `output_format_packet` | `S7-OFH` / `S7-OFV` |
| 3 | 3 | 다턴 대화 수행 / `multiturn_dialogue` | 16% | 36/4 | `multiturn_dialogue_packet` | `S7-MDH` / `S7-MDV` |
| 4 | 4 | 도구·프로토콜 / `tool_protocol` | 16% | 36/4 | `tool_protocol_packet` | `S7-TPH` / `S7-TPV` |
| 5 | 5 | 안전·불확실성 처리 / `safety_uncertainty` | 16% | 36/4 | `safety_uncertainty_packet` | `S7-SUH` / `S7-SUV` |
| 6 | 6 | 실전 task 완결 / `practical_task` | 12% | 27/3 | `practical_task_packet` | `S7-PTH` / `S7-PTV` |

## 생성 착수 gate

1. 별도 사용자 요청 뒤 A01·A03·A06 train v01과 A01 val v01, 총 600 records를 직접 작성한다.
2. 실제 학습 tokenizer로 평균 token/record를 측정한다.
3. 3M 목표·150-record 단위·90:10을 함께 만족하도록 파일 수 보정안을 승인받는다.
4. train을 실측한 뒤 validation의 12% unseen relation-set을 확정한다.
5. Guide의 JSON·ID·13개 relation·중복·5어절·유사도·조사·leakage·SHA 감사를 통과한다.

현재 `train/`과 `val/`에는 corpus JSON이 없어야 한다. concept-family 예약은 corpus text template가 아니며, text는 record별로 직접 작성해야 한다.
