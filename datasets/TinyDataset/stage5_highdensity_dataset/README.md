# Stage 5 고밀도 데이터셋 생성 준비

- 상태: `PREPARED_NO_CORPUS_GENERATED`
- 교육 역할: 일반화·추론·전이
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
| 1 | 1 | 귀납 일반화 / `induction` | 20% | 45/5 | `induction_packet` | `S5-INH` / `S5-INV` |
| 2 | 2 | 연역 추론 / `deduction` | 20% | 45/5 | `deduction_packet` | `S5-DEH` / `S5-DEV` |
| 3 | 3 | 반례 기반 일반화 / `counterexample_generalization` | 16% | 36/4 | `counterexample_generalization_packet` | `S5-CGH` / `S5-CGV` |
| 4 | 4 | 새 조합 일반화 / `compositional_novelty` | 16% | 36/4 | `compositional_novelty_packet` | `S5-CNH` / `S5-CNV` |
| 5 | 5 | 유추 전이 / `analogical_transfer` | 16% | 36/4 | `analogical_transfer_packet` | `S5-ATH` / `S5-ATV` |
| 6 | 6 | 도메인 구조 전이 / `structural_transfer` | 12% | 27/3 | `structural_transfer_packet` | `S5-STH` / `S5-STV` |

## 생성 착수 gate

1. 별도 사용자 요청 뒤 A01·A03·A06 train v01과 A01 val v01, 총 600 records를 직접 작성한다.
2. 실제 학습 tokenizer로 평균 token/record를 측정한다.
3. 3M 목표·150-record 단위·90:10을 함께 만족하도록 파일 수 보정안을 승인받는다.
4. train을 실측한 뒤 validation의 12% unseen relation-set을 확정한다.
5. Guide의 JSON·ID·13개 relation·중복·5어절·유사도·조사·leakage·SHA 감사를 통과한다.

현재 `train/`과 `val/`에는 corpus JSON이 없어야 한다. concept-family 예약은 corpus text template가 아니며, text는 record별로 직접 작성해야 한다.
