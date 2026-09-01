# Stage 2~10 tokenizer pilot 통합 감사 — 2026-09-02

- 판정: **PASS**
- 범위: 각 Stage의 A01·A03·A06 train v01과 A01 validation v01
- 실생성: 36 files / 5,400 records (train 4,050, validation 1,350)
- 중요: 이 산출물은 설계서의 tokenizer gate용 pilot이며 Stage별 전체 약 3M-token corpus 완료가 아니다.
- 저밀도와 held-out/evaluation 데이터는 생성·문장 source·유사도 기준에서 제외했다.

## Stage별 생성·토큰 실측

현재 TinyLM CLI 기본 `--data ko-en`에 대응하는 `tok-ko-en-32768.json`을 기준으로 하며, 학습 경로가 문서마다 붙이는 EOS 1개를 포함했다.

| Stage | files | train/val records | val unseen | text chars | mean tokens/record(+EOS) | 3M 단순 환산 files |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 4 | 450/150 | 18/150 (12.00%) | 48,717 | 41.625 | 480.480 |
| 3 | 4 | 450/150 | 18/150 (12.00%) | 51,779 | 42.883 | 466.382 |
| 4 | 4 | 450/150 | 18/150 (12.00%) | 55,233 | 45.317 | 441.339 |
| 5 | 4 | 450/150 | 18/150 (12.00%) | 40,389 | 33.183 | 602.712 |
| 6 | 4 | 450/150 | 18/150 (12.00%) | 59,009 | 48.552 | 411.932 |
| 7 | 4 | 450/150 | 18/150 (12.00%) | 53,634 | 42.600 | 469.484 |
| 8 | 4 | 450/150 | 18/150 (12.00%) | 49,011 | 39.617 | 504.838 |
| 9 | 4 | 450/150 | 18/150 (12.00%) | 48,988 | 39.548 | 505.710 |
| 10 | 4 | 450/150 | 18/150 (12.00%) | 49,942 | 41.060 | 487.092 |

단순 환산 files는 `3,000,000 / 평균(+EOS) / 150`이며, 교육영역 비율·90:10·정수 파일 제약을 적용하기 전 값이다. 이 수치로 중앙 예약 원장을 자동 변경하지 않는다.

## Metadata 정본 대응

- 중앙 예약 row·area exact 대응: 36/36 files 검사, 전체 exact field 일치 `True`
- `purpose`/`design_note`의 예약 semantic-axis literal: 36/36
- 보조 literal 근거(domain / area learning goal / error axis): 24/24/12 files
- exact 대상은 filename·dataset_name(중앙 area name 또는 slug의 정식 표기)·version·split·range·concept_family·record type이다. purpose/design_note는 concept_family exact 일치와 semantic-axis literal을 기계 근거로 삼고, Stage별 승인 builder의 문체 차이는 사람 의미 감사와 함께 판정한다.

## Validation 분리

- `unseen_relation: true`: 162/1350 = 12.00%
- `false` relation-set train 미관측: 0
- `true` relation-set train 관측: 0
- validation 개별 relation label의 해당 Stage train 미관측: 0
- true/false 고유 relation-set: 101 / 120
- true 위치 최대 연속 길이: 3 (허용 최대 3)
- 30행 단위 5개 구간의 true 최소 배치 수: 2 (구간별 최소 2)

## Relations 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 3 |
| `subclass_of` | 7 |
| `part_of` | 502 |
| `classification` | 1,620 |
| `boundary` | 3,453 |
| `contrast` | 460 |
| `comparison` | 1,142 |
| `function` | 1,187 |
| `role` | 1,062 |
| `process` | 2,291 |
| `state` | 3,508 |
| `attribute` | 1,600 |
| `other` | 784 |

`other`로 분류된 record의 자주 나온 의미 유형 5가지는 다음과 같다.
중앙 원장의 `relation_focus`는 영역 수준 편집 초점이며 record별 필수 교집합이나 허용 목록으로 강제하지 않는다.

1. 일정 불확실성: 3 records; 대표 concept `복구 예정 시각 불확실` (`S6-LCH-00094`)
2. 관측 결측: 3 records; 대표 concept `기상 센서의 관측 공백` (`S6-CSH-00070`)
3. 시간정보 결측: 3 records; 대표 concept `현장 사진의 촬영 시각 미상` (`S6-UMH-00130`)
4. 관측 공백: 3 records; 대표 concept `생태 조사 야간 종 검출 공백` (`S8-EQH-00036`)
5. 희귀 단일 사례: 2 records; 대표 concept `한 회차 압력 급락 예외` (`S2-CSH-00150`)

### Stage별 relations 분포

| relation | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `is_a` | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| `subclass_of` | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 2 | 0 |
| `part_of` | 40 | 54 | 0 | 0 | 0 | 0 | 160 | 140 | 108 |
| `classification` | 3 | 30 | 289 | 369 | 160 | 149 | 275 | 216 | 129 |
| `boundary` | 285 | 198 | 351 | 512 | 463 | 258 | 468 | 401 | 517 |
| `contrast` | 0 | 7 | 47 | 75 | 0 | 0 | 153 | 114 | 64 |
| `comparison` | 60 | 45 | 14 | 166 | 146 | 0 | 296 | 204 | 211 |
| `function` | 7 | 280 | 24 | 103 | 0 | 249 | 90 | 193 | 241 |
| `role` | 122 | 36 | 194 | 0 | 125 | 252 | 48 | 90 | 195 |
| `process` | 514 | 397 | 126 | 131 | 0 | 212 | 243 | 344 | 324 |
| `state` | 534 | 509 | 552 | 102 | 506 | 245 | 260 | 386 | 414 |
| `attribute` | 210 | 166 | 96 | 248 | 175 | 0 | 304 | 256 | 145 |
| `other` | 72 | 57 | 89 | 104 | 105 | 112 | 104 | 72 | 69 |

### Stage별 `other` 상위 의미 유형 5가지

- Stage 2: 희귀 단일 사례 2회 — `한 회차 압력 급락 예외` (`S2-CSH-00150`); 기록 결측 1회 — `간헐 통신의 인과 불명` (`S2-CSH-00146`); 동시 개입 1회 — `복수 처치의 기여 미정` (`S2-CSH-00147`); 측정 척도 변경 1회 — `센서 교체 전후 척도 불일치` (`S2-CSH-00148`); 관측되지 않은 조작 1회 — `미기록 수동 조작 가능성` (`S2-CSH-00149`)
- Stage 3: 재제작 정보 보존 1회 — `완성 치수 기록의 재제작 목표` (`S3-GAH-00126`); 재료 이력 보존 1회 — `재료 배치 기록의 색상 재현` (`S3-GAH-00127`); 사용자 치수 미확정 1회 — `현재 사용자 치수 정보의 불확실성` (`S3-GAH-00147`); 설치 조건 미확정 1회 — `설치 벽체 재질의 미확인` (`S3-GAH-00148`); 현장 조건 확인 1회 — `벽체 조사와 고정 방식 결정` (`S3-PDH-00005`)
- Stage 4: 시간이 다른 자기 지시 2회 — `그 아이가 뜻하는 어린 시절의 나` (`S4-DRH-00004`); 대화 참여자 밖 집단 1회 — `그쪽이 가리키는 배우자 가족` (`S4-DRH-00010`); 기간 단위 참조 1회 — `그 시기가 가리키는 육아휴직 기간` (`S4-DRH-00013`); 회상 공간 참조 1회 — `그곳의 선행 장소인 외할머니 집` (`S4-DRH-00018`); 현장 공간 지시 1회 — `저쪽이 뜻하는 대기실 쪽` (`S4-DRH-00020`)
- Stage 5: 관찰 기간 제한 2회 — `관찰 창 절단수명` (`S5-INH-00068`); 출처 불명 2회 — `혼합 원료 추적불능` (`S5-INH-00082`); 구간 검열 2회 — `구간 검열 파손시점` (`S5-INH-00136`); 추론 구조 2회 — `손상 원인과 관측 지표` (`S5-STH-00023`); 미관측 변수 1회 — `미측정 두께 효과` (`S5-INH-00005`)
- Stage 6: 일정 불확실성 3회 — `복구 예정 시각 불확실` (`S6-LCH-00094`); 관측 결측 3회 — `기상 센서의 관측 공백` (`S6-CSH-00070`); 시간정보 결측 3회 — `현장 사진의 촬영 시각 미상` (`S6-UMH-00130`); 일정 미확정 2회 — `구호 물자 도착 시각 미정` (`S6-LCH-00138`); 수요 결측 2회 — `연료 수요 자료 공백` (`S6-CSH-00100`)
- Stage 7: 미해결 질문 2회 — `답변 대기 중인 글꼴 질문` (`S7-MDH-00007`); 맥락과 지시 구분 1회 — `명령이 아닌 참고 배경` (`S7-IIH-00005`); 결정 미지정 1회 — `강조색 선택 보류` (`S7-IIH-00011`); 예시와 결과 구분 1회 — `예시문 산출 제외 범위` (`S7-IIH-00017`); 요구 미정 1회 — `표지 로고 미지정` (`S7-IIH-00023`)
- Stage 8: 대안 원인 2회 — `하천 오염 상류 대조 적합성` (`S8-EQH-00008`); 관측 공백 2회 — `생태 조사 야간 종 검출 공백` (`S8-EQH-00036`); 복합 원인 2회 — `공룡 멸종 단일 원인 과잉 단순화` (`S8-ACH-00027`); 전이 전제 1회 — `배터리 수명 가속 시험 대응성` (`S8-EQH-00013`); 기록 단절 1회 — `기후 추세 관측소 이전 단절점` (`S8-EQH-00027`)
- Stage 9: 행정 허가 범위 2회 — `보호구역 허가 활동 구분` (`S9-RSV-00086`); 조작적 정의 1회 — `위성 관측 변수 정의 질문` (`S9-RSH-00005`); 진단 계층 1회 — `재현성 실패 원인 계층화` (`S9-RSH-00011`); 응답 경로 1회 — `설문 응답 편향 원인 질문` (`S9-RSH-00021`); 부재 추론 1회 — `화석 분포 표본 공백 질문` (`S9-RSH-00027`)
- Stage 10: 규범 갱신 절차 2회 — `법정 홍수위 과학 갱신` (`S10-EIH-00057`); 제도 적용 경계 1회 — `침수지도 보험구역 차이` (`S10-EIH-00004`); 재산권 조정 1회 — `연안 토지권 후퇴 조치` (`S10-EIH-00019`); 토지이용 규제 1회 — `침수 구역의 용도 지역 전환` (`S10-EIH-00020`); 비등록 거주 증거 1회 — `비공식 정착지 적응 기준` (`S10-EIH-00022`)

## 중복·유사도·한국어 품질

- exact/스키마/ID/relation/source 등 전체 감사 오류: 0
- 활성 text author/rewrite/diversify 도구: 0
- pilot 내부 반복 5어절 표본 수: 0
- Stage1 고밀도 교차 반복 5어절 표본 수: 0
- 반복 4어절 문장 도입부 표본 수: 0
- primary concept 직결 조사 후보: 0
- 문자 3~5-gram TF-IDF 내부 최대 cosine: 0.340176
- Stage1 고밀도 교차 최대 cosine: 0.220597
- 검토선 0.72 이상 내부/교차 상위 pair: 0/0

광역 조사 탐지는 형태소 분석기가 아닌 표면 휴리스틱이므로, 기계 후보는 원문 문맥에서 실제 오류와 오탐을 구분한 뒤에만 수정한다.

### 구조 다양성 gate

| 파일 | 개념명 문두 | 2문장 이상 | 3문장 이상 | 4문장 이상 | relation lag-6 반복 |
|---|---:|---:|---:|---:|---:|
| `stage2_(11)causal_structure_high_density_train_v01.json` | 11/150 | 150/150 | 0/150 | 0/150 | 56/144 |
| `stage2_(13)temporal_order_high_density_train_v01.json` | 0/150 | 150/150 | 3/150 | 0/150 | 70/144 |
| `stage2_(16)relational_composition_high_density_train_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 54/144 |
| `stage2_(11)causal_structure_high_density_val_v01.json` | 1/150 | 150/150 | 0/150 | 0/150 | 41/144 |
| `stage3_(1)goal_action_high_density_train_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 16/144 |
| `stage3_(3)planning_decomposition_high_density_train_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 12/144 |
| `stage3_(6)execution_recovery_high_density_train_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 29/144 |
| `stage3_(1)goal_action_high_density_val_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 10/144 |
| `stage4_(1)discourse_reference_high_density_train_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 29/144 |
| `stage4_(3)dialogue_state_high_density_train_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 24/144 |
| `stage4_(6)implicature_context_high_density_train_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 22/144 |
| `stage4_(1)discourse_reference_high_density_val_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 29/144 |
| `stage5_(1)induction_high_density_train_v01.json` | 5/150 | 145/150 | 0/150 | 0/150 | 29/144 |
| `stage5_(3)counterexample_generalization_high_density_train_v01.json` | 7/150 | 150/150 | 0/150 | 0/150 | 1/144 |
| `stage5_(6)structural_transfer_high_density_train_v01.json` | 0/150 | 121/150 | 0/150 | 0/150 | 0/144 |
| `stage5_(1)induction_high_density_val_v01.json` | 5/150 | 122/150 | 0/150 | 0/150 | 24/144 |
| `stage6_(1)long_context_high_density_train_v01.json` | 0/150 | 150/150 | 150/150 | 30/150 | 26/144 |
| `stage6_(3)constraint_satisfaction_high_density_train_v01.json` | 0/150 | 150/150 | 2/150 | 0/150 | 61/144 |
| `stage6_(6)uncertainty_management_high_density_train_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 66/144 |
| `stage6_(1)long_context_high_density_val_v01.json` | 0/150 | 150/150 | 150/150 | 42/150 | 67/144 |
| `stage7_(1)instruction_intent_high_density_train_v01.json` | 68/150 | 77/150 | 0/150 | 0/150 | 58/144 |
| `stage7_(3)multiturn_dialogue_high_density_train_v01.json` | 0/150 | 150/150 | 150/150 | 57/150 | 72/144 |
| `stage7_(6)practical_task_high_density_train_v01.json` | 81/150 | 70/150 | 0/150 | 0/150 | 59/144 |
| `stage7_(1)instruction_intent_high_density_val_v01.json` | 0/150 | 150/150 | 5/150 | 0/150 | 25/144 |
| `stage8_(1)evidence_quality_high_density_train_v01.json` | 68/150 | 83/150 | 0/150 | 0/150 | 1/144 |
| `stage8_(3)argument_critique_high_density_train_v01.json` | 0/150 | 150/150 | 1/150 | 0/150 | 2/144 |
| `stage8_(6)calibration_abstention_high_density_train_v01.json` | 57/150 | 92/150 | 0/150 | 0/150 | 2/144 |
| `stage8_(1)evidence_quality_high_density_val_v01.json` | 87/150 | 72/150 | 0/150 | 0/150 | 1/144 |
| `stage9_(1)research_synthesis_high_density_train_v01.json` | 0/150 | 150/150 | 0/150 | 0/150 | 3/144 |
| `stage9_(3)workflow_state_high_density_train_v01.json` | 0/150 | 148/150 | 1/150 | 0/150 | 2/144 |
| `stage9_(6)provenance_audit_high_density_train_v01.json` | 0/150 | 150/150 | 1/150 | 1/150 | 1/144 |
| `stage9_(1)research_synthesis_high_density_val_v01.json` | 34/150 | 149/150 | 0/150 | 0/150 | 8/144 |
| `stage10_(1)expert_integration_high_density_train_v01.json` | 60/150 | 149/150 | 0/150 | 0/150 | 0/144 |
| `stage10_(3)long_horizon_high_density_train_v01.json` | 48/150 | 140/150 | 0/150 | 0/150 | 10/144 |
| `stage10_(6)metacognitive_control_high_density_train_v01.json` | 6/150 | 150/150 | 0/150 | 0/150 | 0/144 |
| `stage10_(1)expert_integration_high_density_val_v01.json` | 70/150 | 150/150 | 0/150 | 0/150 | 11/144 |

공통 gate는 파일별 개념명 문두 90 이하, 2문장 이상 45개 이상, lag-6 동일 relation-set 72 이하이다. Stage6 long-context와 Stage7 multiturn 파일은 150개 모두 3문장 이상이고 그중 최소 30개는 4문장 이상이어야 한다. 이 수치는 템플릿·round-robin을 드러내는 하한선이며, 별도의 사람 의미 감사와 함께 판정한다.

## 독립 의미 감사

작성자와 다른 검토자가 고정 층화 표본, validation true 전수, 희소 relation, 유사도 상위쌍과 모든 교정 ID를 재판독했다. 세 구간 모두 최종 PASS이고 미해결 지적은 0건이며, 독립 감사자는 corpus/source/JSON을 수정하지 않았다.

- Stage2~4: `TinyLM_Stage2_4_Pilot_Independent_Semantic_Audit_2026-09-02.md`
- Stage5~7: `TinyLM_Stage5_7_Pilot_Independent_Semantic_Audit_2026-09-02.md`
- Stage8~10: `TinyLM_Stage8_10_Pilot_Independent_Semantic_Audit_2026-09-02.md`

## Tokenizer 민감도

| tokenizer | pilot tokens(+EOS) | mean/record(+EOS) |
|---|---:|---:|
| `tok-ko-en-32768.json` | 224,631 | 41.598333 |
| `tok-ko-edu-en-32768.json` | 210,399 | 38.962778 |
| `tok-ko-32768.json` | 205,018 | 37.966296 |

독립 tokenizer 대조는 Python 3.11.4·`tokenizers 0.22.2`로 5,400 records를 전수 비교했다. 세 tokenizer 모두 pure ByteLevel-BPE counter와 record mismatch 0·최대 차이 0이며, EOS는 학습 경로와 같이 record마다 1개를 더했다.

참고로 수정 금지인 Stage1 고밀도 train+validation 38,200 records는 같은 기본 tokenizer와 EOS 기준 1,479,956 tokens, 평균 38.742304 tokens/record다. 따라서 과거의 약 3M 표기는 실제 tokenizer token이 아니라 문자 proxy였음을 구분해야 한다.

## 보호 무결성

- 기준선 일치: 371/371
- 변경/누락: 0/0
- 보호 범위: 저밀도 31파일, Stage1 고밀도 train/val 255파일, 기존 Stage2~10 scaffold 81파일, 중앙 통제 문서 4파일.
- 설계서에 pilot 완료 기록을 추가하는 후속 문서 갱신은 위 사전 비교가 끝난 뒤 별도 의도 변경으로 기록한다.

## 다음 gate

1. Stage별 실측 평균과 6개 교육영역 비율·90:10·150-record 제약을 반영한 배분 후보 계산은 완료했다.
2. 사용자가 실제 tokenizer 기준 Stage별 약 3M안과 Stage1 실측 규모 근접안 중 목표를 확정한다.
3. 실제 3M안을 선택할 때 기존 250 primary family 및 25 contingency를 넘는 새 family 범위를 승인·예약한다.
4. 승인된 원장 revision의 기계 감사를 통과한 뒤 pilot 다음 예약 version부터 전체 corpus 생성을 재개한다.

## 기계 근거

- `machine/TinyLM_Stage2_10_Pilot_Integrated_Audit_2026-09-02.json`
- `machine/TinyLM_Stage2_10_Pilot_Protected_Baseline_2026-09-01.json`
- `machine/TinyLM_Stage2_10_Pilot_3M_Allocation_Options_2026-09-02.json`
- `machine/TinyLM_Stage2_10_Pilot_Semantic_Review_Packet_2026-09-02.json`
- `archive/Stage2_Stage10_Rejected_Pilot_Draft_Record_2026-09-01.md`
