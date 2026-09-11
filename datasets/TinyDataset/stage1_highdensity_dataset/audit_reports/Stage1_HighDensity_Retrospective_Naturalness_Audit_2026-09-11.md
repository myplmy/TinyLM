# Stage1 High-Density retrospective naturalness 추가 감사 — 2026-09-11

- 범위: 확정·수정 금지 상태인 `stage1_highdensity_dataset/train/*.json` 및 `val/*.json`의 **읽기 전용 전수 집계**.
- 목적: `concepts[0]`가 문장 도입부에 반복되는 정도를 기록하고, Stage1 v2 준비본에서의 향후 검토 범위를 남긴다.
- 비범위: v1 record·ID·relations·text·기존 감사 PASS 판정의 수정, v2 source 생성, 자동 재서술, 품질 최종 판정.
- 판정: `RETROSPECTIVE_SIGNAL_ONLY`. 이 보고서는 완료된 v1의 소급 HOLD 또는 재작성 지시가 아니다.

## 1. 측정 정의

한 record의 `text`가 `concepts[0]`으로 정확히 시작하고, 그 직후 첫 글자가 `은` 또는 `는`인 경우를 `primary+은/는 도입`으로 센다. 공백·인용부호·다른 조사·문맥 선행어가 있으면 세지 않는다. 따라서 이 값은 정의형 문장의 **도입부 집중도**일 뿐, 문법 오류율이나 자연성의 자동 판정값이 아니다.

## 2. 전수 결과

| split | files | records | `은` | `는` | primary+은/는 | 비율 |
|---|---:|---:|---:|---:|---:|---:|
| train | 227 | 34,000 | 14,789 | 11,277 | 26,066 | 76.6647% |
| validation | 28 | 4,200 | 1,583 | 2,001 | 3,584 | 85.3333% |
| 전체 | 255 | 38,200 | 16,372 | 13,278 | 29,650 | 77.6178% |

현행 Stage2 reviewer-assist의 임시 경고선은 30% 초과, 포장 HOLD 신호는 45% 초과다. 그러나 해당 값은 Stage2의 신규 source를 위한 도입부 다양성 신호이며, 문법 오류율이나 Stage1 v1의 소급 합격선으로 설계된 것이 아니다. Stage1 전체가 77.6178%인 사실은 이 임계값을 범용·자동 품질 실패 기준으로 쓰면 안 된다는 근거다.

## 3. 해석과 v1 보호 상태

- 많은 record가 `개념명은/는 …` 형식으로 시작한다는 뜻이며, 각 문장이 부자연스럽거나 교육 내용이 틀렸다는 증거는 아니다.
- 이 전수값은 기존 exact/normalized duplicate, 5어절 반복, 조사, controlled relations, schema 감사와 서로 다른 측정축이다. 기존 구조 감사 PASS를 자연성·용어 출처 PASS로 확대 해석하지 않되, 반대로 이 지표 하나로 기존 PASS를 취소하지도 않는다.
- v1은 확정·수정 금지 상태를 유지한다. 이 보고서 작성 과정에서 JSON·JSONL·source·relations·ID는 변경하지 않았다.

## 4. Stage1 v2에서의 추후 검토 사항

Stage1 v2는 아직 `PREPARATION_ONLY`이며, 이 수치만으로 v2의 수정 목표나 비율 상한을 확정하지 않는다. 사용자가 v2 범위와 재작성 권한을 승인할 때 다음을 별도 검토한다.

1. area·concept family별 층화 표본을 사람이 읽어 `primary+은/는` 형식이 정상적인 교육 설명인지, 반복 template인지 구분한다.
2. v2 source 작성 전 term registry에서 primary의 자연성·정의·출처·내부 시나리오 근거를 검토하고, 자동 합성어·행번호 suffix·기계적 X1/X2 결합을 배제한다.
3. family별 도입부 형식의 계획된 다양성, primary masking 유사도, 반복 5어절, 조사, 출처·split 경계를 함께 평가한다. 단일 비율만으로 자동 재작성하지 않는다.
4. 30%/45% 같은 수치 gate를 v2에 적용할지는 v1·Stage2의 층화 사람 검토 결과와 사용자 승인 뒤에 보정한다. 보정 전에는 review signal로만 사용한다.

상세 준비 경계와 향후 승인 절차는 `../../stage1_highdensity_dataset_v2/TinyLM_Stage1_HighDensity_v2_Design_Spec.md` 및 `../../stage1_highdensity_dataset_v2/work_ledger/Stage1_HighDensity_v2_Work_Ledger.md`에서 유지한다.
