# Stage 8 고밀도 데이터셋 생성 준비

- 상태: `PREPARED_NO_CORPUS_GENERATED`
- 교육 역할: 평가·비판·검증·수정
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
| 1 | 1 | 근거 품질 / `evidence_quality` | 20% | 45/5 | `evidence_quality_packet` | `S8-EQH` / `S8-EQV` |
| 2 | 2 | 오류 탐지 / `error_detection` | 20% | 45/5 | `error_detection_packet` | `S8-EDH` / `S8-EDV` |
| 3 | 3 | 논증 비판 / `argument_critique` | 16% | 36/4 | `argument_critique_packet` | `S8-ACH` / `S8-ACV` |
| 4 | 4 | 검증·재현 / `verification_validation` | 16% | 36/4 | `verification_validation_packet` | `S8-VRH` / `S8-VRV` |
| 5 | 5 | 수정·교정 / `revision_correction` | 16% | 36/4 | `revision_correction_packet` | `S8-RCH` / `S8-RCV` |
| 6 | 6 | 확신 보정·유보 / `calibration_abstention` | 12% | 27/3 | `calibration_abstention_packet` | `S8-CAH` / `S8-CAV` |

## 생성 착수 gate

1. 별도 사용자 요청 뒤 A01·A03·A06 train v01과 A01 val v01, 총 600 records를 직접 작성한다.
2. 실제 학습 tokenizer로 평균 token/record를 측정한다.
3. 3M 목표·150-record 단위·90:10을 함께 만족하도록 파일 수 보정안을 승인받는다.
4. train을 실측한 뒤 validation의 12% unseen relation-set을 확정한다.
5. Guide의 JSON·ID·13개 relation·중복·5어절·유사도·조사·leakage·SHA 감사를 통과한다.

현재 `train/`과 `val/`에는 corpus JSON이 없어야 한다. concept-family 예약은 corpus text template가 아니며, text는 record별로 직접 작성해야 한다.
