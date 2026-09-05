# TinyLM Stage2~10 실측 3M 승인 작업 체크포인트 감사

- 감사 시작일: 2026-09-02 KST
- 마지막 checkpoint: 2026-09-03 KST
- 판정: **AUTHORIZED_BASELINE_PASS / GENERATION_PAUSED / A01_QUALITY_INCOMPLETE**
- 의미: 승인된 relation gate 수정, family 증보, 중앙 원장·manifest revision은 PASS다. 직접 작성 신규 train 38파일도 확정했다. Stage2 A01 source-only v40~v87은 완결하고 1차 구조 보정을 마쳤지만, 영역 품질 보정 도중 사용자 요청으로 중단했으므로 A01이나 전체 생성을 PASS로 확정하지 않는다.
- 기계 부속: `machine/TinyLM_Stage2_10_Actual3M_Authorized_Checkpoint_Audit_2026-09-02.json`

## 1. 실행 결과 요약

| Gate | 결과 | 실측 근거 |
|---|---|---|
| G1 Stage5~7 `relation_focus` 강제 제거 | PASS | builder 3개·공유 auditor 1개 수정, 12 pilot files/1,800 records 오류 0, corpus/source SHA 24/24 일치 |
| G2 family 완전 예약 | PASS | 4,370 files, train/val 3,933/437, primary/contingency/new 2,250/225/1,895 |
| G3 중앙 원장·manifest revision | PASS | 중앙 schema 2.0 SHA `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`; 9 manifests exact projection; 23개 검사 오류 0 |
| G4 train 3,933 files | PAUSED | 기존 27 files와 직접 작성 신규 38 files 완료. `S2-A01-T-040~087` source 48개·7,200행은 1차 구조 보정 뒤 품질 보정 중단 상태이며 미포장 |
| G5 validation 437 files | SEQUENCED WAIT | 기존 9 files만 존재. train relation-set 확정 뒤 신규 428 files 생성 |
| G6 655,500 records 통합 감사 | PARTIAL PASS + SOURCE BATCH INCOMPLETE | 확정된 74 files·11,100 records 부분 감사 PASS. 미포장 A01 source에는 5-word 반복 보정이 남았고 4,296 files 미완료 |

현재 완료 실파일은 corpus JSON 74개와 대응 canonical source 74개다. 신규 완료 corpus·source는 각각 38개이며, 남은 범위는 4,296 files·644,400 records다. 별도의 v40~v87 canonical source 48개·7,200행은 corpus·checkpoint가 없어 완료 수치에 포함하지 않는다.

## 2. G1 relation-focus 재감사

`relation_focus`를 `relations` whitelist로 해석하던 네 실행 조건을 제거했다. 13개 통제어휘, record당 2~5개, 내부 중복 금지, `other_type`, source projection gate는 유지했다.

재실행 결과 Stage5·6·7 builder의 `--check-only`가 각각 4/4 files를 통과했다. 합산 relation 배정은 4,967회이며 상세 13개 분포는 `TinyLM_Stage5_7_Relation_Focus_Gate_Reaudit_2026-09-02.md`에 보존했다.

## 3. G2 family 예약과 의미 독립성

중앙 예약은 4,370행이며 총 655,500개 concrete ID를 덮는다. exact·정규화 family, filename, ID range, concrete ID 중복은 모두 0이다. 같은 Stage의 train/validation domain 겹침도 0이다.

독립 의미감사 판정은 `PASS_WITH_TAXONOMY_POLICY_NOTE`다. Stage2~6 신규 1,025행은 중앙 축과 의미상 정렬된 세분 axis이고, contingency 225행은 승인된 alias다. 이를 exact canonical 문자열로 맹목 치환하면 오히려 중복 excess 52개가 생기므로 원문 `semantic_axis`를 보존했다.

## 4. G3 manifest revision

| Stage | reservations | manifest SHA-256 |
|---:|---:|---|
| 2 | 480 | `1802fd79354a9ff3cd36872a7f2c32a89ae1803e94aae9ce40edea7cbe4b0c0e` |
| 3 | 470 | `8626bae131e66df24611f22c2777d66c49892b933a96a61ee74a549fe6c39df4` |
| 4 | 440 | `d32feb1cb378d4e4a1dff08cf560d70619901c6428c6c533c03772834eed8f48` |
| 5 | 600 | `1c8049c8e65f05b6fe169a791b4d871b1a69cba4c34b066b1c070d302be829f2` |
| 6 | 410 | `95a8811ab7623e70c50e551173d136ed4ebaf0563b0e28cddb85bd84b57a8714` |
| 7 | 470 | `564b0b4dcc7b5d3a38215825b944d76628abc1b575ca6fbeb577a20b4e7e2296` |
| 8 | 500 | `0b296d37d0c8e0957a3dc535466c5f244a53e199848e90ca10c1a6c89a9d8ac8` |
| 9 | 510 | `772cc1596f32271c7ee377e08459f475002082bb28080f205011aeba5c8146e2` |
| 10 | 490 | `68d610b6153f703edb79d2e3cfa64324edd4453e254091093d893f51f842c495` |

`integrate_stage2_10_actual3m_family_manifests.py --verify-current` 재실행 결과는 PASS, writes 0, watched files 16개 해시 불변이었다.

## 5. 생성 엔진 사전감사와 차단

자동 semantic-composition 초안은 다음 구조 gate까지는 통과했다.

- 9-Stage 1,350-row dry-run: 전 Stage tokenizer 목표 ±10% PASS
- known grammar 0, 파일별 primary 150/150 unique
- provenance template fingerprint 132~146종/Stage, 단일 최대 share 2%
- Stage2 전체 virtual expansion 480 files/72,000 rows: 평균 41.495514 tokens, 목표 41.625, 구조 PASS

그러나 이 결과는 corpus 품질 승인과 다르다. 초안 1,350행은 모두 `manual_semantic_review=false`이며, Stage2 virtual 신규 행 71,400개도 직접 작성 debt다. 문자열·template 조합이 의미 내용을 대신 만들기 때문에 Guide §10의 “record별 직접 작성”을 충족하지 않는다.

격리 임시공간에서 canonical `--write`를 재현한 결과 exit 1, `CANONICAL_WRITE_BLOCKED_DIRECT_AUTHORING_FAIL`, 생성 파일 0이었다. 따라서 구조 PASS가 canonical publish로 오인되지 않는다. 전체 4,370-file virtual run은 시간 경계에서 중단했으며 PASS로 보고하지 않는다.

직접 작성 경로의 첫 서른두 missing reservations를 순차 생성·감사했다.

- reservation: `S2-A01-T-002`
- file: `stage2_(11)causal_structure_high_density_train_v02.json`
- IDs: `S2-CSH-00151 ~ S2-CSH-00300`
- family: `스마트 온실 관수·환경제어 — 공통 원인과 거짓 상관 통제`

150행의 primary concept·text·relations를 직접 작성하고 source-first packager로 corpus를 만들었다. file-level `--require-complete` 감사 결과 missing 0, 구조·projection 오류 0, exact/normalized 중복 0, 5-word n-gram 반복 0, fuzzy 고유사 pair 0, token 평균 45.206667(+EOS)로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v02_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

두 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-003`
- file: `stage2_(11)causal_structure_high_density_train_v03.json`
- IDs: `S2-CSH-00301 ~ S2-CSH-00450`
- family: `스마트 온실 관수·환경제어 — 원인 방향·피드백·역인과 판정`

v03 150행도 source-first로 작성·포장했다. file-level 감사에서 구조·projection·통제 relation 오류, exact/normalized 중복, 5-word n-gram 반복, 내부·기존 Stage2 교차 fuzzy 고유사 pair가 모두 0이었다. tokenizer 평균은 44.006667(+EOS), hard grammar 0, review debt 0으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v03_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

세 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-004`
- file: `stage2_(11)causal_structure_high_density_train_v04.json`
- IDs: `S2-CSH-00451 ~ S2-CSH-00600`
- family: `스마트 온실 관수·환경제어 — 개입 전후 결과와 자연 변동 구분`

v04 150행도 source-first로 작성·포장했다. file-level 감사에서 구조·projection·통제 relation 오류, exact/normalized 중복, 5-word n-gram 반복, 내부·기존 Stage2 900건 교차 fuzzy 고유사 pair가 모두 0이었다. tokenizer 평균은 38.853333(+EOS), hard grammar 0, review debt 0으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v04_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

네 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-005`
- file: `stage2_(11)causal_structure_high_density_train_v05.json`
- IDs: `S2-CSH-00601 ~ S2-CSH-00750`
- family: `스마트 온실 관수·환경제어 — 다중 원인의 충분성·기여 범위`

v05 150행도 source-first로 작성·포장했다. file-level 감사에서 구조·projection·통제 relation 오류, exact/normalized 중복, 최종 5-word n-gram 반복, 내부·기존 Stage2 1,050건 교차 fuzzy 고유사 pair가 모두 0이었다. tokenizer 평균은 41.966667(+EOS), hard grammar 0, review debt 0으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v05_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

다섯 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-006`
- file: `stage2_(11)causal_structure_high_density_train_v06.json`
- IDs: `S2-CSH-00751 ~ S2-CSH-00900`
- family: `도시 상수도 정수·배수 운영 — 직접 원인·매개 경로·배경 조건 분리`

v06 150행도 source-first로 작성·포장했다. file-level 감사에서 구조·projection·통제 relation 오류, exact/normalized 중복, 5-word n-gram 반복, 내부·기존 Stage2 1,200건 교차 fuzzy 고유사 pair가 모두 0이었다. tokenizer 평균은 42.706667(+EOS), hard grammar 0, review debt 0으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v06_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

여섯 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-007`
- file: `stage2_(11)causal_structure_high_density_train_v07.json`
- IDs: `S2-CSH-00901 ~ S2-CSH-01050`
- family: `도시 상수도 정수·배수 운영 — 공통 원인과 거짓 상관 통제`

v07 150행도 source-first로 작성·포장했다. file-level 감사에서 구조·projection·통제 relation 오류, exact/normalized 중복, 5-word n-gram 반복, 내부·기존 Stage2 1,350건 교차 fuzzy 고유사 pair가 모두 0이었다. tokenizer 평균은 43.240000(+EOS), hard grammar 0, review debt 0으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v07_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

일곱 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-008`
- file: `stage2_(11)causal_structure_high_density_train_v08.json`
- IDs: `S2-CSH-01051 ~ S2-CSH-01200`
- family: `도시 상수도 정수·배수 운영 — 원인 방향·피드백·역인과 판정`

v08 150행도 source-first로 작성·포장했다. file-level 감사에서 구조·projection·통제 relation 오류, exact/normalized 중복, 5-word n-gram 반복, 내부·기존 Stage2 1,350건 교차 fuzzy 고유사 pair가 모두 0이었다. tokenizer 평균은 45.240000(+EOS), hard grammar 0, review debt 0으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v08_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

여덟 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-009`
- file: `stage2_(11)causal_structure_high_density_train_v09.json`
- IDs: `S2-CSH-01201 ~ S2-CSH-01350`
- family: `도시 상수도 정수·배수 운영 — 개입 전후 결과와 자연 변동 구분`

v09 150행도 source-first로 작성·포장했다. file-level 감사에서 구조·projection·통제 relation 오류, exact/normalized 중복, 5-word n-gram 반복, 내부·기존 Stage2 1,500건 교차 fuzzy 고유사 pair가 모두 0이었다. tokenizer 평균은 38.633333(+EOS), hard grammar 0, review debt 0으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v09_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

아홉 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-010`
- file: `stage2_(11)causal_structure_high_density_train_v10.json`
- IDs: `S2-CSH-01351 ~ S2-CSH-01500`
- family: `도시 상수도 정수·배수 운영 — 다중 원인의 충분성·기여 범위`

PC 중단 뒤 보존된 133행에 누락 17행을 직접 작성해 150행을 완성하고 source-first로 포장했다. file-level 감사에서 구조·projection·통제 relation 오류, exact/normalized 중복, 5-word n-gram 반복, 내부·기존 Stage2 train 1,650건 교차 fuzzy 고유사 pair가 모두 0이었다. tokenizer 평균은 42.106667(+EOS), hard grammar 0, review debt 0으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v10_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

열 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-011`
- file: `stage2_(11)causal_structure_high_density_train_v11.json`
- IDs: `S2-CSH-01501 ~ S2-CSH-01650`
- family: `클라우드 서비스 부하·장애 대응 — 직접 원인·매개 경로·배경 조건 분리`

v11 150행도 source-first로 직접 작성·포장했다. file-level 감사에서 구조·projection·통제 relation 오류, exact/normalized 중복, 5-word n-gram 반복, 내부·기존 Stage2 train 1,800건 교차 fuzzy 고유사 pair가 모두 0이었다. tokenizer 평균은 45.386667(+EOS), hard grammar 0, review debt 0으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v11_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

열한 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-012`
- file: `stage2_(11)causal_structure_high_density_train_v12.json`
- IDs: `S2-CSH-01651 ~ S2-CSH-01800`
- family: `클라우드 서비스 부하·장애 대응 — 공통 원인과 거짓 상관 통제`

v12 150행도 source-first로 직접 작성·포장했다. 첫 token gate의 평균 46.046667은 상한을 넘어 차단했고, 긴 문장을 직접 압축해 최종 45.320000으로 PASS했다. 최초 누적 5-word n-gram 반복 1종도 직접 수정해 최종 0건이며, 구조·projection·통제 relation·exact/normalized 중복·내부 및 기존 Stage2 train 1,950건 교차 fuzzy 오류와 review debt는 모두 0이다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v12_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

열두 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-013`
- file: `stage2_(11)causal_structure_high_density_train_v13.json`
- IDs: `S2-CSH-01801 ~ S2-CSH-01950`
- family: `클라우드 서비스 부하·장애 대응 — 원인 방향·피드백·역인과 판정`

v13 150행도 source-first로 직접 작성·포장했다. file-level 감사에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 2,100건 교차 fuzzy 고유사 pair가 모두 0이었다. 최초 누적 5-word n-gram 반복 1종은 v13의 해당 문장을 직접 다시 써 최종 0건으로 만들었다. tokenizer 평균은 44.913333(+EOS), hard grammar 0, review debt 0으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v13_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

열세 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-014`
- file: `stage2_(11)causal_structure_high_density_train_v14.json`
- IDs: `S2-CSH-01951 ~ S2-CSH-02100`
- family: `클라우드 서비스 부하·장애 대응 — 개입 전후 결과와 자연 변동 구분`

v14 150행도 source-first로 직접 작성·포장했다. 구조·projection·통제 relation 오류, exact/normalized 중복, 누적 5-word n-gram 반복, 내부 및 기존 Stage2 train 2,250건 교차 fuzzy 고유사 pair와 review debt가 모두 0이었다. tokenizer 평균은 44.800000(+EOS), hard grammar 0으로 PASS했다. 조사 warning 18개는 모두 정상 단어 `효과와` 내부의 부분문자열 false positive임을 확인했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v14_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

열네 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-015`
- file: `stage2_(11)causal_structure_high_density_train_v15.json`
- IDs: `S2-CSH-02101 ~ S2-CSH-02250`
- family: `클라우드 서비스 부하·장애 대응 — 다중 원인의 충분성·기여 범위`

v15 150행도 source-first로 직접 작성·포장했다. 첫 tokenizer 평균 47.553333(+EOS)은 상한을 넘어 차단했고 영문·숫자 말미 primary 6건의 조사 연결도 직접 교정했다. 긴 상위 문장을 직접 압축한 최종 평균은 45.220000이며, 구조·projection·통제 relation 오류, exact/normalized 중복, 누적 5-word n-gram 반복, 내부 및 기존 Stage2 train 2,400건 교차 fuzzy 고유사 pair, hard grammar와 review debt는 모두 0이다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v15_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

열다섯 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-016`
- file: `stage2_(11)causal_structure_high_density_train_v16.json`
- IDs: `S2-CSH-02251 ~ S2-CSH-02400`
- family: `철도 운행 간격·환승 조정 — 직접 원인·매개 경로·배경 조건 분리`

v16 150행도 source-first로 직접 작성·포장했다. 최초 파일 내부 5-word 반복 1종과 누적 감사에서 v11과 겹친 열거 표현의 파생 5-word 반복 4종을 v16에서 직접 재서술해 최종 0건으로 만들었다. 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 2,550건 교차 fuzzy 고유사 pair, hard grammar와 review debt는 모두 0이고 tokenizer 평균은 40.033333(+EOS)으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v16_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

열여섯 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-017`
- file: `stage2_(11)causal_structure_high_density_train_v17.json`
- IDs: `S2-CSH-02401 ~ S2-CSH-02550`
- family: `철도 운행 간격·환승 조정 — 공통 원인과 거짓 상관 통제`

v17 150행도 source-first로 직접 작성·포장했다. 최초 파일 내부 5-word 반복 1종과 v12 교차 5-word 반복 1종을 v17 문장에서 직접 재서술해 최종 0건으로 만들었다. 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 2,700건 교차 fuzzy 고유사 pair, hard grammar와 review debt는 모두 0이고 tokenizer 평균은 45.733333(+EOS)으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v17_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

열일곱 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-018`
- file: `stage2_(11)causal_structure_high_density_train_v18.json`
- IDs: `S2-CSH-02551 ~ S2-CSH-02700`
- family: `철도 운행 간격·환승 조정 — 원인 방향·피드백·역인과 판정`

v18 150행도 source-first로 직접 작성·포장했다. source gate에서 v13과 동일한 primary 1건을 직접 교체했고, 최초 tokenizer 평균 46.880000(+EOS)이 상한을 넘어 긴 문장 28건을 직접 압축했다. 최종 평균은 45.520000이며 구조·projection·통제 relation 오류, exact/normalized 중복, 누적 5-word n-gram 반복, 내부 및 기존 Stage2 train 2,850건 교차 fuzzy 고유사 pair, hard grammar와 review debt는 모두 0이다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v18_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

열여덟 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-019`
- file: `stage2_(11)causal_structure_high_density_train_v19.json`
- IDs: `S2-CSH-02701 ~ S2-CSH-02850`
- family: `철도 운행 간격·환승 조정 — 개입 전후 결과와 자연 변동 구분`

v19 150행도 source-first로 직접 작성·포장했다. 초기 source 계약에서 primary literal 누락 71건과 v09와 동일한 primary 1건을 발견해 각 문장을 직접 수정했다. 최종 tokenizer 평균은 38.600000(+EOS)이며 구조·projection·통제 relation 오류, exact/normalized 중복, 누적 5-word n-gram 반복, 내부 및 기존 Stage2 train 3,000건 교차 fuzzy 고유사 pair, hard grammar와 review debt는 모두 0이다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v19_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

열아홉 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-020`
- file: `stage2_(11)causal_structure_high_density_train_v20.json`
- IDs: `S2-CSH-02851 ~ S2-CSH-03000`
- family: `철도 운행 간격·환승 조정 — 다중 원인의 충분성·기여 범위`

v20은 직접 작성한 의미 후보 171행을 source gate 전에 검토해 중복 성격의 후행 감사 후보 21행을 제외하고 150행으로 확정했다. 포장 후 발견한 파일 내부 5-word 반복 1종도 해당 문장을 직접 재서술해 0건으로 만들었다. 최종 tokenizer 평균은 40.640000(+EOS)이며 구조·projection·통제 relation 오류, exact/normalized 중복, 누적 5-word n-gram 반복, 내부 및 기존 Stage2 train 3,150건 교차 fuzzy 고유사 pair, hard grammar와 review debt는 모두 0이다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v20_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

스무 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-021`
- file: `stage2_(11)causal_structure_high_density_train_v21.json`
- IDs: `S2-CSH-03001 ~ S2-CSH-03150`
- family: `하천 저수지 수위·방류 관리 — 직접 원인·매개 경로·배경 조건 분리`

v21은 직접 작성한 의미 후보 162행을 source gate 전에 검토해 후행 보충 후보 12행을 제외하고 150행으로 확정했다. 포장 후 같은 매개 경로 표현에서 나온 파일 내부 5-word 반복 2종도 primary와 문장을 직접 재서술해 0건으로 만들었다. 최종 tokenizer 평균은 43.000000(+EOS)이며 구조·projection·통제 relation 오류, exact/normalized 중복, 누적 5-word n-gram 반복, 내부 및 기존 Stage2 train 3,300건 교차 fuzzy 고유사 pair, hard grammar와 review debt는 모두 0이다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v21_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

스물한 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-022`
- file: `stage2_(11)causal_structure_high_density_train_v22.json`
- IDs: `S2-CSH-03151 ~ S2-CSH-03300`
- family: `하천 저수지 수위·방류 관리 — 공통 원인과 거짓 상관 통제`

v22 150행은 source-first로 직접 작성·포장했다. 최초 source gate와 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 3,450건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 43.380000(+EOS)으로 PASS했고 사후 수정은 없었다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v22_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

스물두 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-023`
- file: `stage2_(11)causal_structure_high_density_train_v23.json`
- IDs: `S2-CSH-03301 ~ S2-CSH-03450`
- family: `하천 저수지 수위·방류 관리 — 원인 방향·피드백·역인과 판정`

v23 150행은 source-first로 직접 작성·포장했다. 최초 source gate와 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 3,600건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 44.500000(+EOS)으로 PASS했고 사후 수정은 없었다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v23_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

스물세 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-024`
- file: `stage2_(11)causal_structure_high_density_train_v24.json`
- IDs: `S2-CSH-03451 ~ S2-CSH-03600`
- family: `하천 저수지 수위·방류 관리 — 개입 전후 결과와 자연 변동 구분`

v24 150행은 source-first로 직접 작성·포장했다. 최초 source gate와 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 3,750건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 42.906667(+EOS)으로 PASS했고 사후 수정은 없었다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v24_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

스물네 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-025`
- file: `stage2_(11)causal_structure_high_density_train_v25.json`
- IDs: `S2-CSH-03601 ~ S2-CSH-03750`
- family: `하천 저수지 수위·방류 관리 — 다중 원인의 충분성·기여 범위`

v25는 최초 직접 작성 원고 148행을 source gate가 차단한 뒤 빠진 의미축 2개를 직접 보충해 150행으로 확정했다. package 후 발견된 내부 5-word n-gram 1종은 공분산 배분 문장 하나를 직접 다시 써 제거했다. 최종 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 3,900건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 44.340000(+EOS)으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v25_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

스물다섯 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-026`
- file: `stage2_(11)causal_structure_high_density_train_v26.json`
- IDs: `S2-CSH-03751 ~ S2-CSH-03900`
- family: `식품 냉장 유통·품질 유지 — 직접 원인·매개 경로·배경 조건 분리`

v26은 156개 직접 작성 후보에서 중심성이 낮거나 중복 성격인 6개를 제외하고 primary literal 1건과 어색한 primary 1건을 직접 수정해 150행으로 확정했다. 최종 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 4,050건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 44.480000(+EOS)으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v26_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

스물여섯 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-027`
- file: `stage2_(11)causal_structure_high_density_train_v27.json`
- IDs: `S2-CSH-03901 ~ S2-CSH-04050`
- family: `식품 냉장 유통·품질 유지 — 공통 원인과 거짓 상관 통제`

v27은 최초 tokenizer 평균 46.906667(+EOS)의 상한 초과를 두 차례 직접 압축해 해결했다. package 뒤 v07과 공유한 5-word n-gram 1종도 로거시계 record를 직접 재서술해 제거했다. 최종 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 4,200건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 45.500000(+EOS)으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v27_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

스물일곱 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-028`
- file: `stage2_(11)causal_structure_high_density_train_v28.json`
- IDs: `S2-CSH-04051 ~ S2-CSH-04200`
- family: `식품 냉장 유통·품질 유지 — 원인 방향·피드백·역인과 판정`

v28은 최초 148행을 source gate가 차단한 뒤 이력효과·예측제어 2행을 직접 보충했다. 완성 원고의 tokenizer 평균 46.973333(+EOS) 상한 초과도 두 차례 직접 압축해 45.486667로 낮췄다. 최종 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 4,350건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v28_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

스물여덟 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-029`
- file: `stage2_(11)causal_structure_high_density_train_v29.json`
- IDs: `S2-CSH-04201 ~ S2-CSH-04350`
- family: `식품 냉장 유통·품질 유지 — 개입 전후 결과와 자연 변동 구분`

v29은 최초 148행을 source gate가 차단한 뒤 자연 기준선 재설정·실제 가동시점 2행을 직접 보충했다. 150행은 평균 41.720000(+EOS)으로 첫 source gate를 통과했다. package 뒤 v12와 공유한 위약검사 5-word n-gram 2종을 직접 재서술해 제거했으며 최종 평균은 41.706667이다. 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 4,500건 교차 fuzzy 고유사 pair, 누적 반복, hard grammar와 review debt는 모두 0이다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v29_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

스물아홉 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-030`
- file: `stage2_(11)causal_structure_high_density_train_v30.json`
- IDs: `S2-CSH-04351 ~ S2-CSH-04500`
- family: `식품 냉장 유통·품질 유지 — 다중 원인의 충분성·기여 범위`

v30은 최초 148행을 source gate가 차단한 뒤 구성원인 제거와 모든 충분경로 폐쇄 2행을 직접 보충했다. 완성 150행은 평균 40.800000(+EOS)으로 첫 source gate를 통과했고 package 후 수정 없이 누적 반복 0을 유지했다. 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 4,650건 교차 fuzzy 고유사 pair, hard grammar와 review debt도 모두 0이다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v30_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

서른 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-031`
- file: `stage2_(11)causal_structure_high_density_train_v31.json`
- IDs: `S2-CSH-04501 ~ S2-CSH-04650`
- family: `온라인 학습 진도·피드백 운영 — 직접 원인·매개 경로·배경 조건 분리`

v31은 최초 147행을 source gate가 차단한 뒤 분리된 직접 원인, 매개 경로와 배경 조건을 다루는 3행을 직접 보충했다. 완성 150행은 평균 38.340000(+EOS)으로 첫 source gate를 통과했고 package 후 수정 없이 누적 반복 0을 유지했다. 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 4,800건 교차 fuzzy 고유사 pair, hard grammar와 review debt도 모두 0이다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v31_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

서른한 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-032`
- file: `stage2_(11)causal_structure_high_density_train_v32.json`
- IDs: `S2-CSH-04651 ~ S2-CSH-04800`
- family: `온라인 학습 진도·피드백 운영 — 공통 원인과 거짓 상관 통제`

v32는 직접 작성한 150행의 최초 tokenizer 평균 49.173333(+EOS)이 상한을 넘어 source gate가 차단했다. 공통원인·선택편향·측정편향·충돌경로의 판정 근거와 relations를 유지하며 긴 후행 설명을 두 차례 직접 압축해 최종 평균을 45.700000으로 낮췄다. 포장 전 source-only 감사와 최종 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 4,950건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v32_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

서른두 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-033`
- file: `stage2_(11)causal_structure_high_density_train_v33.json`
- IDs: `S2-CSH-04801 ~ S2-CSH-04950`
- family: `온라인 학습 진도·피드백 운영 — 원인 방향·피드백·역인과 판정`

v33은 첫 source gate가 73번째 record의 primary literal 누락 1건을 차단해 본문을 직접 고쳤다. 완성 150행은 평균 39.073333(+EOS)으로 source gate를 통과했다. 포장 전 source-only와 최종 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 5,100건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v33_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

서른세 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-034`
- file: `stage2_(11)causal_structure_high_density_train_v34.json`
- IDs: `S2-CSH-04951 ~ S2-CSH-05100`
- family: `온라인 학습 진도·피드백 운영 — 개입 전후 결과와 자연 변동 구분`

v34 150행은 source-first로 직접 작성·포장했다. 최초 source gate와 포장 전·후 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 5,250건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 41.953333(+EOS)으로 PASS했고 사후 수정은 없었다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v34_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

서른네 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-035`
- file: `stage2_(11)causal_structure_high_density_train_v35.json`
- IDs: `S2-CSH-05101 ~ S2-CSH-05250`
- family: `온라인 학습 진도·피드백 운영 — 다중 원인의 충분성·기여 범위`

v35는 포장 전 source-only 누적 감사가 v20과 공유한 5-word n-gram 1종을 차단해 해당 대체경로 문장을 직접 재서술했다. 최종 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 5,400건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 43.986667(+EOS)으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v35_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

서른다섯 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-036`
- file: `stage2_(11)causal_structure_high_density_train_v36.json`
- IDs: `S2-CSH-05251 ~ S2-CSH-05400`
- family: `생태 복원지 종·서식지 관찰 — 직접 원인·매개 경로·배경 조건 분리`

v36 150행은 source-first로 직접 작성·포장했다. 최초 source gate와 포장 전·후 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 5,550건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 44.840000(+EOS)으로 PASS했고 사후 수정은 없었다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v36_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

서른여섯 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-037`
- file: `stage2_(11)causal_structure_high_density_train_v37.json`
- IDs: `S2-CSH-05401 ~ S2-CSH-05550`
- family: `생태 복원지 종·서식지 관찰 — 공통 원인과 거짓 상관 통제`

v37은 source-only 누적 감사가 잡은 파일 내부 5-word 반복 1종과 기존 v07·v34 교차 반복 2종을 해당 세 문장에서 직접 재서술했다. 최종 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 5,700건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 45.306667(+EOS)으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v37_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

서른일곱 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-038`
- file: `stage2_(11)causal_structure_high_density_train_v38.json`
- IDs: `S2-CSH-05551 ~ S2-CSH-05700`
- family: `생태 복원지 종·서식지 관찰 — 원인 방향·피드백·역인과 판정`

v38은 최초 tokenizer 평균 51.013333(+EOS)을 두 차례 직접 압축해 허용범위로 낮췄다. 포장 전 source-only 누적 감사가 파일 내부와 기존 v07 교차 5-word 반복을 각 1종 검출해 해당 문장을 직접 재서술했다. 최종 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 5,850건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 45.733333(+EOS)으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v38_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

서른여덟 번째 직접 작성 파일은 다음과 같다.

- reservation: `S2-A01-T-039`
- file: `stage2_(11)causal_structure_high_density_train_v39.json`
- IDs: `S2-CSH-05701 ~ S2-CSH-05850`
- family: `생태 복원지 종·서식지 관찰 — 개입 전후 결과와 자연 변동 구분`

v39은 사용자 일시중단 전 직접 작성된 98행을 해시로 대조해 보존하고, 재개 승인 뒤 99~150번째 52행을 직접 보충했다. 최초 완성 source와 포장 후 file/full audit에서 구조·projection·통제 relation 오류, exact/normalized 중복, 내부 및 기존 Stage2 train 6,000건 교차 fuzzy 고유사 pair, 5-word n-gram 반복, hard grammar와 review debt가 모두 0이었다. tokenizer 평균은 43.653333(+EOS)으로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v39_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

2026-09-02 추가 지침에 따라 이후 감사 cadence를 바꿨다. 각 Stage의 한 교육영역 source 전체를 먼저 직접 작성하고, 영역 종료 뒤 파일별·누적 token, 중복, n-gram, fuzzy, 조사와 relation 분포를 일괄 감사·수정한 다음 corpus를 포장한다. v40~v50 source는 각 150행·primary/text 고유 150/150·source 최소 계약 오류 0으로 작성됐으나 미포장 진행물이다. source SHA-256은 v40~v45가 `e0f3edfeebf9f7d19027fa301368ff47ab206a20f8b521cb860fbb6871843639`, `508a1f0b96389ca59a1a24e54559c0a7862fa0f7d075ff8fadb8180f5a8ba62b`, `066119ab81894323fbca8f82ef8f2325edc425bba93b2f282f7037e16fb8e437`, `1ce55695d452e2da7e3f45ad3c1b00469f1b7094e41861268170fe8a782df0ba`, `45eb19c7246aa63dd73e4d71320fdd83af500a185709d5047469b2d01b887932`, `0d9e23c53900488f73f3fc4c3142fa739c98145715b4d4728d4428b54fd9b9d5`, v46~v48이 `43fc6f60257b8d8fce30cc427a2a0458a18a0b71d65c5404b55b8c2add7d0eb5`, `3836f96d5cf05fd7b3308d2f080dc161a9f1d4102eb3e93dbca066e1615b7566`, `7e14ff53c3b3d407be961402a580afac6e1b3be880acd6038f967af85cd065a8`, v49~v50이 `fe82fa73241e8d79a4c21365db31b1f7e49f5655a18154cb3fda284042733fcf`, `f70afd38433fa6a4f5997b91b59429e799faccecfec68cfad47e8354a73ed1b2`다. 전환 직전 확인된 v40 token 평균 46.893333(+EOS) 초과는 Stage2 A01 batch 수정 목록에 남겼다.

사용자 일시중단 시점의 v51 source 50행을 그대로 보존하고 51~150번째 100행을 직접 보충했다. 완성 150행의 parse 오류, primary/text 중복, 통제 밖 relation, relation cardinality·내부 중복, primary literal 누락은 모두 0이며 SHA-256은 `11adf713d54a596d352f4487cd23b710adfc2d1faad37719e1311bef5be703c6`이다. corpus 포장·checkpoint 등록·영역 batch 품질 판정은 A01 source 전체 완성 뒤 수행한다.

이어 v52~v54 source 3개·450행을 직접 작성했다. 각 파일은 parse·150행·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류 0이다. source SHA-256은 v52 `7958d7d2492c8aab60fddad530d2313689e76929562584d7134ba53454b59897`, v53 `47e11138d8c69c5d4a41b5644cf1704b828eb5043b0c31ae2b34b6d410356dc2`, v54 `c632fdcc21407e949e6ebfdccae13540363e6cc16b0fc97178ab37c10c48053f`다. v54는 최초 149행에서 누락 한 행을 직접 보충했다. 세 파일 모두 미포장 source-only 진행물이다.

이어 v55~v57 source 3개·450행을 직접 작성했다. 각 파일은 parse·150행·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류 0이다. source SHA-256은 v55 `c42f30c7be0a8b4b2173d955b65a253e77a9e64bee01b1cec3f6bdbdfdf7d01f`, v56 `ca259750951b5b200172825c31196556b8b103af1537ffd4772a2a199de08eea`, v57 `6dae0baccb7ebecd49b00c5402257dd96c99c2e0f997be79877f48613c92ccfa`다. 세 파일 모두 미포장 source-only 진행물이다.

이어 v58~v60 source 3개·450행을 직접 작성했다. v58은 재개 시 실제 파일이 50행임을 우선 확인해 해당 50행을 보존하고 서로 겹치지 않는 100행을 보충했다. v60은 첫 최소 검사에서 primary literal 누락 2건을 검출해 해당 문장만 직접 수정했다. 최종 세 파일은 parse·150행·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v58 `077b32e1099624d45a6a73a817b8988e05eaa1e81c976c114bea91f60a36d724`, v59 `d987020fc02e9498f651aa2ccf56aa70fa5690fcf8e91ff38763078c86804d92`, v60 `7d3e66a371a8a24a2c197dde23da81d4a8c0c92cdeb9c74772a1a1de1e97b509`다. 세 파일 모두 미포장 source-only 진행물이며 batch 전면 감사는 A01 source 완성 뒤 수행한다.

이어 v61~v63 source 3개·450행을 직접 작성했다. v61은 최초 149행에 1행, v63은 148행에 2행을 직접 보충했고, v62는 최초 151행에서 의미 축 주변부 1행을 제거해 정확히 150행으로 맞췄다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v61 `cc8dc796e77144514ec1709fea3404057593aa8572681f42b7e35a8a219b5f2c`, v62 `d06564e79c83f86462b28cf54eb5983e18eac33f6dbdf4ae0bc928969f229990`, v63 `74475c90f2ce75bc136c4db65102d92ce014b7da2883335fb736f12a03e2e555`다. 세 파일 모두 미포장 source-only 진행물이다.

이어 v64~v66 source 3개·450행을 직접 작성했다. v64는 명백한 중복어 오탈자 1건을 수정하고 최초 149행에 1행을 보충했으며, v65는 최초 148행에 2행을 보충했다. v66은 최초 검사에서 바로 150행 계약을 통과했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v64 `bcf6c8833a07d38c8103280526e1f8f6e2ae4ea63e08ea698ff1b9d5b9a93afe`, v65 `9f8ccbeb0b56fcb5f0673a3f796e22946e0317ec212ad217ff8035f939e0e90d`, v66 `89926e81e0f33375ae0b2192af6006e368dcbf164def6afb979aa5ead8aa1967`이다. 세 파일 모두 미포장 source-only 진행물이다.

이어 v67~v69 source 3개·450행을 직접 작성했다. v67은 중단 당시 실제 파일의 50행을 보존하고 100행을 보충했으며, v69는 최초 149행에 대안경로 판정 1행을 보충했다. v68은 최초 완성 검사에서 바로 150행 계약을 통과했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v67 `4eb624f380d3d3e4feeff3c67872598b1c17d3128eeacf7b4e4ee8a2e4e6e56f`, v68 `f8b1783be1ccf840591dab52aa63de4bbe72e58d9a5c8d4432eb32b88e2f6b7d`, v69 `2cce640aa476ee5ea1d608233c318788f33c7a5c42707e13cdcbab07d0bb2f47`이다. 세 파일 모두 미포장 source-only 진행물이며 영역 batch 감사는 v87 source 완성 뒤 수행한다.

이어 v70~v72 source 3개·450행을 직접 작성했다. v70은 최초 완성 검사에서 바로 150행 계약을 통과했고, v71은 최초 149행에 1행, v72는 최초 148행에 2행을 직접 보충했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v70 `9fd8494a3ba227333945cb0d545cc1c43312d60715640272ff167c6a5f28187e`, v71 `e9aa344d0edb59c1e456ee5dfd0691d4c084889832e53fb1b10ce6e617181450`, v72 `7325958532f38f54c61337ca6fd9830ce060c09af83e0db69f6e675319462696`이다. 세 파일 모두 미포장 source-only 진행물이며 영역 batch 감사는 v87 source 완성 뒤 수행한다.

이어 v73~v75 source 3개·450행을 직접 작성했다. v73은 최초 148행에 2행, v74는 최초 149행에 1행을 직접 보충했고 v75는 최초 완성 검사에서 바로 150행 계약을 통과했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v73 `c7b3264c16b16d0efb1cfae9b83551c4aec053bd8afc4c801d11d8131ff42a1f`, v74 `ef742bb8e569c0187984c04ee617384cdd09fbe2952714b0a4a5f7ed381c49a5`, v75 `3f4c2eae9d68011fe07b1103b74cf117f9589ab2d40500ef1507feafb131a9ce`이다. 세 파일 모두 미포장 source-only 진행물이며 영역 batch 감사는 v87 source 완성 뒤 수행한다.

이어 v76~v78 source 3개·450행을 직접 작성했다. v76은 중단 당시 실제 50행을 보존하고 100행을 보충했으며, 최초 최소 검사에서 중단 전 27번째 primary literal 불일치 1건을 검출해 의미를 보존한 문장으로 직접 수정했다. v77은 최초 149행에 1행, v78은 최초 99행 뒤 51행을 직접 보충했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v76 `0a4927c565a67edecd1ad0f1e280b37141511c2cfebdacbcf89a77997ec4d36a`, v77 `d5927ee4b4b8c3ef69cd121d56c6a1486f13b09ac0b581efa138f2d625e63e8d`, v78 `cccbf34f5a034a73c4c4f19e179f56ba3156883597d8d0c1964ecff0eb900962`이다. 세 파일 모두 미포장 source-only 진행물이며 영역 batch 감사는 v87 source 완성 뒤 수행한다.

이어 v79~v81 source 3개·450행을 직접 작성했다. v79는 101행까지 작성한 뒤 남은 49행으로 정확히 닫았고, v80은 50→99→150행, v81은 50→100→150행 순으로 완결했다. v81 작성 중 발견한 명백한 `않고 않고` 중복어 1건은 즉시 직접 수정했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v79 `2672a224ee01b1e7ba759dcb206036db4d963e7be246bc23255587c9db6d2d05`, v80 `6cd52003657a33fd1415b0d54f10bb11bfade917255aba016ce38b98f214e9da`, v81 `bbc61d5b5a34473032680bee7971e09fe9614d807885fdc28a05a6725d444be2`이다. 세 파일 모두 미포장 source-only 진행물이며 영역 batch 감사는 v87 source 완성 뒤 수행한다.

이어 v82~v84 source 3개·450행을 직접 작성했다. v82는 50→99→147→150행, v83은 50→100→150행, v84는 50→100→150행 순으로 완결했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v82 `8e6170463576998a3aba27f4da7df8c4f92c1427bd99b35ad967ff183600e08d`, v83 `f77d0e6381bfb56d0ecb9a049b0cab3736b63601f2065e3b747af889b0440330`, v84 `1b61a8711760e34dabe9ea1223bd591ca8fe8b38b1799e8f21d0e27a17b46d70`이다. 세 파일 모두 미포장 source-only 진행물이며 영역 batch 감사는 v87 source 완성 뒤 수행한다.

이어 v85~v87 source 3개·450행을 직접 작성해 Stage2 A01 source를 완성했다. v85는 최초 173행 초안에서 의미축에 충분한 선행 150행만 남겨 정확히 닫았고, v86은 50→100→150행, v87은 50→99→150행으로 완결했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v85 `6d7e9a2e2903951d947f437855f9f12bd1cefd077028e2a747b2b3b368a944be`, v86 `db211804ab8306046d33989a367e94ce508a3ed3752a006f5e6e82859247929f`, v87 `0ea5ceff7cd606088df70aeb7777509f4feb28dbde6005d8245f9720b67d3352`이다. 48개 source 모두 미포장 상태이며 다음 단계는 v40~v87 영역 batch 감사다.

### 5.40 사용자 중단 시점의 A01 batch 감사 checkpoint

2026-09-03 A01 영역 batch 감사를 실제로 시작했다. 최초 결과에서 `other` relation을 가진 276행에 필수 `other_type`이 없었고, primary 계열 중복 후행 14행과 hard 조사 불일치 1행이 있었다. 각 `other_type`은 의미를 읽고 직접 분류했고, 중복 후행 14행은 primary/text를 직접 재서술했으며, `지표이면`은 `지표라면`으로 바로잡았다.

보정 후 `stage2_10_corpus_audit.py --stage 2 --area 1 --split train --check-only --json` 재실행 결과는 다음과 같다.

- source 87/87 존재, corpus 39/87 존재, v40~v87 corpus 48개 미생성
- 13,050 records, source/corpus artifact error 0
- exact primary/text/normalized text/primary+relation-set duplicate 0
- hard grammar/primary particle finding 0
- Stage2 tokenizer 평균 44.582299(+EOS), 허용 37.4625~45.7875, Stage-level PASS
- cross-record 5-word 반복 666종, 초과 record assignment 737건, 최대 record frequency 7
- 조사 휴리스틱 warning 979건; 자동 false positive가 다수이나 전수 사람 검토 미완료

따라서 auditor의 구조 verdict가 PASS여도 교육영역 최종 품질 판정은 **INCOMPLETE/PAUSED**다. 남은 필수 작업은 5-word 반복 직접 재서술(현재 greedy 후보 293행), 파일별 token gate 재검사와 v40 초과 보정, fuzzy similarity, 조사 warning 사람 검토, 전면 재감사다. 이들이 끝나기 전에는 48개 corpus를 포장하거나 checkpoint 완료 수치를 올리지 않는다.

중단 시점 v40~v87 source-only relations 분포는 `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/4/1,010/1,956/6,039/830/2,449/1,496/749/4,707/1,836/1,996/276`이다. `other_type` 5개 유형은 `식별·인과해석 한계 136`, `미측정 교란·대안경로 59`, `선택·조건화 편향 34`, `불확실성·적용범위 30`, `측정·기록 한계 17`이다. 감사 수정 전 각 progress 문단의 v51~v87 SHA는 작성 직후 역사값이며, 현행 v40~v87 source-set digest는 `195e93127931c040a30109e1a82b8d374da024b21d34252868204cf02f5f89a5`다.

## 6. 현행 corpus 부분 감사

read-only 현행 auditor는 기존 pilot과 신규 v02~v39를 합친 74 source/corpus pairs·11,100 records를 검사해 다음을 확인했다.

- structural verdict PASS
- 9개 Stage tokenizer gate PASS
- exact primary/text/normalized text/primary+relation-set 중복 0
- train/validation exact leakage 0
- hard grammar 0
- cross-record 5-word n-gram 반복 0/199,076 assignments
- generator manual-review debt 0
- coverage는 예약된 corpus/source pairs 4,296개가 아직 생성되지 않았으므로 `PARTIAL_ALLOWED`

조사 휴리스틱 warning 595개는 기존 155개, 신규 v02~v38 412개, 신규 v39 28개다. v39 경고까지 전수 읽었으며 `효과와`, `먹이가`, `차이가`, `증가는`, primary 안의 `...과 ...` 연결 같은 정상 단어 내부 또는 어절 경계 false positive다. 자동 오류로 세지 않고 비차단 검토 후보로 남겼다.

기존 integrated pilot auditor를 2026-09-01 보호 baseline으로 그대로 재실행하면 `protected_file_changed` 1종으로 FAIL한다. 상세 22개 경로는 이번에 승인된 Guide·Design·curriculum·README·중앙 원장·manifest revision이므로 corpus 회귀가 아니다. 현재 authorized revision은 family/manifest 감사와 새 read-only corpus auditor를 함께 사용해 검증했다.

## 7. 보호 범위

- Stage1 train/validation corpus 변경 0
- 저밀도 `stage1_dataset` 변경 0
- held-out/evaluation 변경 0
- legacy `stage2_(2)attribute_high_density_*` 변경 0
- 기존 Stage2~10 pilot corpus/source 변경 0

## 8. 정본·작업원장·checkpoint 동기화

- Guide SHA-256: `1ba975c73be97503827a0d6620c291bf14b28af9ee85529014b42fc852320c04`
- Design SHA-256: `f0794fa0afe682c1d652e60d881e82e8edef2e6b9d850cb0a5b39e3d7aa80d9d`
- 작업원장 SHA-256: `0a58d63e9a5993526ac81f283e2369b7d09fed95276331f54ae9f0c42e0bc5fc`
- resume checkpoint SHA-256: `ee72e500260c6a0a40b1a8018816980c31c2040474f2bc356739c0bd00e7ff1d`
- 기계 부속은 2026-09-03 중단 checkpoint를 추가한 뒤 JSON parse PASS를 확인했다. 자기 참조 문제를 피하기 위해 이 본문에는 해당 mutable 파일의 current SHA를 고정하지 않는다.
- v38 직접 작성 감사 SHA-256: `e7cb6b7fd384d1bd43e576ac6005a6a48fe3aed26bb1c7db8e4adb0612dc8510`
- v39 직접 작성 source SHA-256: `27d8e23d5e4cd82b66d5907bd223ba7c43f4e605cfa10fc6bb99f7ae6b57e52f`
- v39 corpus SHA-256: `949994562255517567f4475500241075e138db70ac4fb7f6933c1344d5d137e6`
- v39 직접 작성 감사 SHA-256: `837a4beb9c2365ebc2460f7077a9b0d9e52c962ad25672f344c836dd34b4b416`

Design의 준비 당시 `승인 대기`·primary-only 원장 문맥은 역사적 기준선으로 구분하고, 현행 schema 2.0·4,370 reservations·74 완료 artifact pairs·4,296 pairs 잔여, source-only v40~v87 및 A01 품질 보정 중단 재개점을 §40.7에 동기화했다. 작업원장도 같은 수치와 재개점을 갖는다.

checkpoint는 completed entry별 `source_authoring_method`를 권위 필드로 사용한다. `S2-A01-T-002~039`는 모두 `direct_model_authoring`, review debt 0이며, 상단 generator 필드는 packager에 포함된 격리 초안 기능을 식별할 뿐 해당 source의 저자 방식을 주장하지 않는다. v40~v87은 아직 checkpoint entry가 없다.

## 9. 결론과 재개 조건

G1~G3는 완료됐고 G4는 직접 작성 방식으로 v39까지 확정한 뒤 Stage2 A01 source-only v40~v87을 완결했다. A01 batch 감사는 구조 보정 뒤 품질 보정 중에 사용자 요청으로 일시중단됐으며 G5~G6 전체도 완료되지 않았다. 다음 실행은 남은 5-word 직접 재서술부터 이어 파일별 token·fuzzy·조사 검토와 전면 재감사를 수행하는 것이다. 모든 gate가 통과한 뒤에만 48개 corpus를 일괄 포장한다.

자동 semantic-composition generator는 계속 canonical write 차단 상태다. 향후 그 경로를 사용하려면 Guide §10에 대한 별도 명시적 예외가 필요하며, 현재 승인으로 간주하지 않는다.

직접 작성 재개도 Stage1·저밀도·held-out·기존 pilot 보호 범위를 넓히지 않는다.

## 10. 2026-09-05 Stage2 A01 train 영역 완료 갱신

사용자 재개 승인과 교육영역 일괄 감사 지침에 따라 중단 checkpoint의 잔여 gate를 순서대로 완료했다. 반복 5어절 666종·초과 assignment 737건은 293행 직접 재서술로 0이 됐고, 파일 평균 초과 29개 source는 의미·primary·relations를 보존해 압축했다. 초기 word-set Jaccard `0.60` 이상 1쌍도 v84 문항을 다시 설계해 제거했다.

최종 `--require-complete` 결과는 source/corpus 87/87, missing 0, artifact·exact/normalized/primary+relation-set·5-word·통제 relation·hard 조사·manual review debt 오류 0이다. token은 13,050 records·574,531 tokens(+EOS)·평균 44.025364이며 파일 평균 87/87이 37.4625~45.7875 안에 있다. 문자 3~5-gram TF-IDF cosine `0.72` 이상 0쌍(최고 0.618116915), word-set Jaccard `0.60` 이상 0쌍(최고 0.545454562)이다. 조사 warning 964건은 정상 어휘 내부 오탐으로 사람 검토했고 실제 오류는 0건이다.

packager는 기존 v01~v39 corpus를 보존하고 v40~v87 corpus 48개를 새로 만들었다. v40~v87 source/corpus set digest는 `a157bb8ae3d08dbb3e4b205441cfb72ad9eaa2af192e5806ec124e8da925b372`, `f8eaff664a566f5fe764d2e6aee802ae288491f2de227a673861c525caf5e793`이며 checkpoint SHA-256은 `ed2ceaf2824d3aea9676bb2144dd480c7be3c7a0a0b0fe4b063dcaa2017429b6`이다. 상세 정본은 `../../stage2_highdensity_dataset/audit_reports/TinyLM_Stage2_A01_CausalStructure_Train_Consolidated_Audit_2026-09-05.md`와 machine JSON이다.

현행 완료는 122 source/corpus pairs·18,300 records, 잔여 4,248 files다. 다음 작성점은 기존 A01 validation v01 pilot을 보존한 `S2-A01-V-002~009` 8 files·1,200 records다. validation source 전체 완성 뒤 token·중복·5어절·fuzzy·조사·train leakage·unseen relation-set 12%를 일괄 감사한다.

추가 Stage2 부분 재감사에서 validation v01 true set과 신규 train v85의 정렬 relation-set 충돌 1건을 찾았다. 보존 validation은 수정하지 않고 train `S2-CSH-12712`의 relations만 실제 비교 의미에 맞춰 보정했으며, 재감사에서 definite leakage 0·true 18건 `PARTIAL_INCONCLUSIVE`를 확인했다. A01 validation v02~v09는 v01의 train 미관측 true set 10종만 재사용하고 이 10종을 이후 Stage2 train 전역 금지 목록으로 유지한다.

validation 포장기는 해당 Stage train source 완전성을 선행조건으로 삼으므로 재개 순서는 `S2-A02-T-001`부터 A02~A06 train 영역을 먼저 완성하는 것으로 확정했다. A01 validation v02~v09의 family·ID·true set 예약은 변경하지 않고 Stage2 train 완결 뒤 실행한다.
