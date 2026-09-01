# Stage 6 고밀도 데이터셋 생성 준비

- 상태: `PREPARED_NO_CORPUS_GENERATED`
- 교육 역할: 지식 통합·장문맥·복합 문제
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
| 1 | 1 | 장문맥 유지 / `long_context` | 20% | 45/5 | `long_context_packet` | `S6-LCH` / `S6-LCV` |
| 2 | 2 | 다단계 추론 / `multihop_inference` | 20% | 45/5 | `multihop_inference_packet` | `S6-MHH` / `S6-MHV` |
| 3 | 3 | 복합 제약 만족 / `constraint_satisfaction` | 16% | 36/4 | `constraint_satisfaction_packet` | `S6-CSH` / `S6-CSV` |
| 4 | 4 | 다중 목표·절충 / `multiobjective_tradeoff` | 16% | 36/4 | `multiobjective_tradeoff_packet` | `S6-MTH` / `S6-MTV` |
| 5 | 5 | 다중 출처 통합 / `multisource_integration` | 16% | 36/4 | `multisource_integration_packet` | `S6-MIH` / `S6-MIV` |
| 6 | 6 | 불확실성 관리 / `uncertainty_management` | 12% | 27/3 | `uncertainty_management_packet` | `S6-UMH` / `S6-UMV` |

## 생성 착수 gate

1. 별도 사용자 요청 뒤 A01·A03·A06 train v01과 A01 val v01, 총 600 records를 직접 작성한다.
2. 실제 학습 tokenizer로 평균 token/record를 측정한다.
3. 3M 목표·150-record 단위·90:10을 함께 만족하도록 파일 수 보정안을 승인받는다.
4. train을 실측한 뒤 validation의 12% unseen relation-set을 확정한다.
5. Guide의 JSON·ID·13개 relation·중복·5어절·유사도·조사·leakage·SHA 감사를 통과한다.

현재 `train/`과 `val/`에는 corpus JSON이 없어야 한다. concept-family 예약은 corpus text template가 아니며, text는 record별로 직접 작성해야 한다.
