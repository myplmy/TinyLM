# TinyLM Stage2~10 실측 3M 승인 작업 체크포인트 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS_WITH_GENERATION_STARTED**
- 의미: 승인된 relation gate 수정, family 증보, 중앙 원장·manifest revision을 완료했다. 자동 semantic-composition 경로는 차단했고, 정본 Guide §10 직접 작성 경로로 첫 신규 train 파일을 생성·감사했다.
- 기계 부속: `machine/TinyLM_Stage2_10_Actual3M_Authorized_Checkpoint_Audit_2026-09-02.json`

## 1. 실행 결과 요약

| Gate | 결과 | 실측 근거 |
|---|---|---|
| G1 Stage5~7 `relation_focus` 강제 제거 | PASS | builder 3개·공유 auditor 1개 수정, 12 pilot files/1,800 records 오류 0, corpus/source SHA 24/24 일치 |
| G2 family 완전 예약 | PASS | 4,370 files, train/val 3,933/437, primary/contingency/new 2,250/225/1,895 |
| G3 중앙 원장·manifest revision | PASS | 중앙 schema 2.0 SHA `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`; 9 manifests exact projection; 23개 검사 오류 0 |
| G4 train 3,933 files | IN PROGRESS | 기존 27 files와 직접 작성 신규 1 file 존재. 신규 train 1/3,906 완료, 3,905 files 남음 |
| G5 validation 437 files | SEQUENCED WAIT | 기존 9 files만 존재. train relation-set 확정 뒤 신규 428 files 생성 |
| G6 655,500 records 통합 감사 | PARTIAL PASS | 현행 37 files·5,550 records 부분 감사 PASS, 4,333 files 미생성 |

현재 Stage2~10 실파일은 corpus JSON 37개와 canonical source 37개다. 신규 corpus·source는 각각 1개이며, 남은 범위는 4,333 files·649,950 records다.

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

직접 작성 경로의 첫 missing reservation은 다음과 같이 생성·감사했다.

- reservation: `S2-A01-T-002`
- file: `stage2_(11)causal_structure_high_density_train_v02.json`
- IDs: `S2-CSH-00151 ~ S2-CSH-00300`
- family: `스마트 온실 관수·환경제어 — 공통 원인과 거짓 상관 통제`

150행의 primary concept·text·relations를 직접 작성하고 source-first packager로 corpus를 만들었다. file-level `--require-complete` 감사 결과 missing 0, 구조·projection 오류 0, exact/normalized 중복 0, 5-word n-gram 반복 0, fuzzy 고유사 pair 0, token 평균 45.206667(+EOS)로 PASS했다. 상세는 `TinyLM_Stage2_CausalStructure_Train_v02_Direct_Authoring_Audit_2026-09-02.md`에 보존했다.

다음 예약은 `S2-A01-T-003`, `stage2_(11)causal_structure_high_density_train_v03.json`, ID `S2-CSH-00301 ~ S2-CSH-00450`, 의미축 `원인 방향·피드백·역인과 판정`이다.

## 6. 현행 corpus 부분 감사

read-only 현행 auditor는 기존 pilot과 신규 v02를 합친 37 source/corpus pairs·5,550 records를 검사해 다음을 확인했다.

- structural verdict PASS
- 9개 Stage tokenizer gate PASS
- exact primary/text/normalized text/primary+relation-set 중복 0
- train/validation exact leakage 0
- hard grammar 0
- cross-record 5-word n-gram 반복 0/101,451 assignments
- generator manual-review debt 0
- coverage는 예약된 corpus/source pairs 4,333개가 아직 생성되지 않았으므로 `PARTIAL_ALLOWED`

조사 휴리스틱 warning 165개는 기존 155개와 신규 v02 10개다. 신규 10개는 `효과와`, `차이가`, `역인과를` 같은 정상 단어 내부 부분문자열 false positive임을 전수 확인했다. 자동 오류로 세지 않고 비차단 검토 후보로 남겼다.

기존 integrated pilot auditor를 2026-09-01 보호 baseline으로 그대로 재실행하면 `protected_file_changed` 1종으로 FAIL한다. 상세 22개 경로는 이번에 승인된 Guide·Design·curriculum·README·중앙 원장·manifest revision이므로 corpus 회귀가 아니다. 현재 authorized revision은 family/manifest 감사와 새 read-only corpus auditor를 함께 사용해 검증했다.

## 7. 보호 범위

- Stage1 train/validation corpus 변경 0
- 저밀도 `stage1_dataset` 변경 0
- held-out/evaluation 변경 0
- legacy `stage2_(2)attribute_high_density_*` 변경 0
- 기존 Stage2~10 pilot corpus/source 변경 0

## 8. 정본·작업원장·checkpoint 동기화

- Guide SHA-256: `5a68e3fcc55edd1a4d47ad3c9a4a904120d9164fd6ed0055f7803efb4b4a8246`
- Design SHA-256: `8cdb17397fdf41d637e1871f79b8fa5be2e88346d4bbe61b496936f20f64c5bb`
- 작업원장 SHA-256: `a12a2361d80f8a959dec4a4422f1c6b33f0210880c9ed281bf12db3183f33e1f`
- resume checkpoint SHA-256: `422cdaa61b3aaf5998f357c018d890873c49015c0723d04db99685dcd2a72bcf`
- 현행 기계 부속 SHA-256: `601348affcb3aae1506540b2791f4d76bd348d329a98967c2459e6642e0a4a65`

Design의 준비 당시 `승인 대기`·primary-only 원장 문맥은 역사적 기준선으로 구분하고, 현행 schema 2.0·4,370 reservations·37 artifact pairs·4,333 pairs 잔여·다음 예약을 §40.7에 동기화했다. 작업원장도 같은 수치와 재개점을 갖는다.

checkpoint는 completed entry별 `source_authoring_method`를 권위 필드로 사용한다. `S2-A01-T-002`는 `direct_model_authoring`, review debt 0이며, 상단 generator 필드는 packager에 포함된 격리 초안 기능을 식별할 뿐 해당 source의 저자 방식을 주장하지 않는다.

## 9. 결론과 재개 조건

G1~G3는 완료됐고 G4는 직접 작성 방식으로 착수했다. G5~G6 전체는 완료되지 않았다. 다음 실행은 `S2-A01-T-003`부터 같은 source-first 직접 작성·파일 단위 감사 순서로 재개한다.

자동 semantic-composition generator는 계속 canonical write 차단 상태다. 향후 그 경로를 사용하려면 Guide §10에 대한 별도 명시적 예외가 필요하며, 현재 승인으로 간주하지 않는다.

직접 작성 재개도 Stage1·저밀도·held-out·기존 pilot 보호 범위를 넓히지 않는다.
