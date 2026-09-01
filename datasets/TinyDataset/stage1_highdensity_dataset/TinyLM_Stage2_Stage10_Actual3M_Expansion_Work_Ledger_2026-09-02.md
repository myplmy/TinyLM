# TinyLM Stage2~10 실측 3M 증보 작업원장 — 2026-09-02

- 문서 상태: `FULL_GENERATION_AUTHORIZED_IN_PROGRESS_DIRECT_AUTHORING`
- 기준 시각: 2026-09-02 KST
- 목적: 컨텍스트 압축·세션 중단 뒤에도 승인 범위, 수치, 미완료 항목과 재개점을 잃지 않게 하는 단일 작업원장
- corpus 생성 권한: **있음**. 정본 Guide §10 직접 작성 경로는 활성화했고 Stage2 train 신규 1 file을 완료했다. 자동 semantic-composition 초안의 canonical source/train/val 쓰기 gate는 계속 닫혀 있다.

## 1. 사용자 승인과 금지 경계

2026-09-02 사용자는 Stage2~10의 **실제 `tok-ko-en-32768.json` 기준 Stage별 약 3M-token안**을 먼저 승인했다. 최초 문서 전용 단계에서는 다음 순서를 지정했다.

1. Stage별·세부영역별 필요한 concept/topic family 증보량을 검토한다.
2. 설계서와 작업원장만 갱신한다.
3. corpus·canonical source·builder 실행·중앙 family JSON revision·Stage manifest revision은 하지 않는다.
4. 문서 감사 결과를 보고하고 corpus 생성 허가를 다시 요청한다.
5. 사용자가 명시적으로 승인한 뒤에만 실제 생성에 착수한다.

이 원장은 위 권한을 넓히지 않는다. 저밀도, held-out/evaluation, Stage1 수정 금지 corpus와 legacy `stage2_(2)attribute_high_density_*`는 계속 열람·해시 대조 외 수정하지 않는다.

### 1.1 2026-09-02 후속 전체 작업 승인

사용자가 다음 네 단계를 명시적으로 승인했다.

1. Stage5~7의 `relation_focus` whitelist 강제를 수정하고 재감사한다.
2. contingency 225개를 54개 area·split에 배치하고 신규 family 최소 1,895개를 선정한다.
3. 중앙 family 원장과 Stage2~10 manifest를 revision하고 감사한다.
4. 기존 pilot을 보존한 채 남은 4,334 files·650,100 records를 생성하고 통합 감사한다.

실행 순서는 고정한다. **도구 수정 PASS → family/manifest revision PASS → train 생성·감사 → validation 생성·분리 감사 → 전체 통합 감사** 순이며, 앞 단계가 실패하면 다음 단계로 넘어가지 않는다.

후속 작업 시작 commit은 `f4308e6d9f295463f513dabb4e49ceeb33c01996`이고 TinyDataset 작업경로는 clean이었다. 시작 기준은 corpus JSON 36개, canonical source 36개, 중앙 family JSON SHA-256 `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99`다.

### 1.2 canonical authoring gate

전체 생성 승인은 corpus 범위와 순서를 승인한 것이며, 정본 Guide §10의 `record별 직접 작성`·`자동 의미 생성 금지`를 폐기한 승인은 아니다. 650,100 records를 자동 조합하는 초안 엔진을 독립 점검한 결과 concept 문자열 대량 조합, relation 선배정 뒤 clause 부착, 반복 template, 다수 조사 오류가 확인됐다. 따라서 이 초안은 canonical `sources/`, `train/`, `val/`에 쓰지 않는다. 현 작업은 Guide를 유지하는 직접 작성 장기 경로로 전환했고, 첫 `S2-A01-T-002`를 record별 직접 작성·감사해 확정했다.

## 2. 정본과 시작 해시

| 파일 | 작업 시작 SHA-256 | 이번 작업 지위 |
|---|---|---|
| `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md` | `98272f9bcb1bedc3c10467952bb4286a70b89686c4c22cd6ae4accd4f652f26f` | 갱신 허용 |
| `TinyLM_Stage2_Stage10_Curriculum_and_Family_Reservation_Draft.md` | `221eff53b8f8482d34d62e5ba2bad8dc8c593f9db193ce4cdc99dff3516ec8b0` | 갱신 허용 |
| `TinyLM_Stage2_Stage10_Concept_Family_Reservation.json` | `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99` | 작업 시작 snapshot. 후속 승인에 따라 schema 2.0·4,370행으로 revision 완료; 현행 SHA `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7` |
| `TinyLM_Stage2_10_Pilot_3M_Allocation_Options_2026-09-02.json` | `2188111c6d3a36a09c4f90fd8d840e9ef695d016340ef7c3860717be9c013972` | 계산 근거·변경 금지 |
| `stage2_highdensity_dataset/README.md` | `3223319a75517b4b125bc8e4c19c3720936377b55fa990ed07c61e16d3e0e05b` | Stage별 설계서로 갱신 허용 |
| `stage3_highdensity_dataset/README.md` | `94ffe5552e17ea6c00f9dcefb06e516864e26540ad49e5fdaff3163190315c0f` | Stage별 설계서로 갱신 허용 |
| `stage4_highdensity_dataset/README.md` | `e24fdc902173a6057538f67f5d3aa6dfd6b31628430865b5bcba9631b24daa4c` | Stage별 설계서로 갱신 허용 |
| `stage5_highdensity_dataset/README.md` | `843aa105e0be66584a283ee5e0ee9ea0ce7b1484c5abdb12d22f2fd09de829ff` | Stage별 설계서로 갱신 허용 |
| `stage6_highdensity_dataset/README.md` | `10f10eee09b1a3b28d61bf9d442cde7786d716589b237c4bd08b051cba40e7aa` | Stage별 설계서로 갱신 허용 |
| `stage7_highdensity_dataset/README.md` | `2e9bb34d00f5175cb6c328bf184e3c5de782fbc3d5065fa36011c4f90b0187d6` | Stage별 설계서로 갱신 허용 |
| `stage8_highdensity_dataset/README.md` | `24fb0b1be1cdf27108fc3d1b134c46c3f86d9200a83d94fb673087c3d0627672` | Stage별 설계서로 갱신 허용 |
| `stage9_highdensity_dataset/README.md` | `c45a161d00b76e9ae48be4878efa19ab2167653858bc44b116dd8da8b25d0adf` | Stage별 설계서로 갱신 허용 |
| `stage10_highdensity_dataset/README.md` | `6810d03e5d57a80733f4aee671f92986dcd812e1694960096890718159fe857e` | Stage별 설계서로 갱신 허용 |

> 시작 시점의 Stage별 `PREPARATION_MANIFEST.json`은 2026-09-01 준비 snapshot이었다. 후속 전체 작업 승인 뒤 9개 manifest를 중앙 schema 2.0 원장의 exact Stage projection으로 revision했으며, 현행 상태는 §9의 G3와 manifest revision 감사보고서를 따른다.

## 3. 승인된 Stage별 총량

모든 파일은 150 records이며 Stage별 train/validation 파일 수는 정확히 90:10이다. 아래 총량은 기존 pilot 4 files/Stage를 포함한다.

| Stage | 승인 총 files | train/val | records | pilot 평균 token/record(+EOS) | 투영 tokens | primary 250 대비 증보 | contingency 25 이후 신규 family | 승인 직후 pilot 제외 생성 대기 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 480 | 432/48 | 72,000 | 41.625 | 2,997,000 | 230 | 205 | 476 |
| 3 | 470 | 423/47 | 70,500 | 42.883333 | 3,023,275 | 220 | 195 | 466 |
| 4 | 440 | 396/44 | 66,000 | 45.316667 | 2,990,900 | 190 | 165 | 436 |
| 5 | 600 | 540/60 | 90,000 | 33.183333 | 2,986,500 | 350 | 325 | 596 |
| 6 | 410 | 369/41 | 61,500 | 48.551667 | 2,985,928 | 160 | 135 | 406 |
| 7 | 470 | 423/47 | 70,500 | 42.600000 | 3,003,300 | 220 | 195 | 466 |
| 8 | 500 | 450/50 | 75,000 | 39.616667 | 2,971,250 | 250 | 225 | 496 |
| 9 | 510 | 459/51 | 76,500 | 39.548333 | 3,025,447 | 260 | 235 | 506 |
| 10 | 490 | 441/49 | 73,500 | 41.060000 | 3,017,910 | 240 | 215 | 486 |
| **합계** | **4,370** | **3,933/437** | **655,500** | — | **27,001,510** | **2,120** | **1,895** | **4,334** |

`primary 대비 증보`는 승인 총 files에서 시작 primary 250을 뺀 값이다. `contingency 이후 신규 family`는 225개 contingency를 의미 적합성 검토 뒤 area·split에 배치하고도 필요했던 수량이다. 후속 승인 실행에서 contingency 225개와 신규 family 1,895개 모두 area·split·ID·version·filename까지 중앙 schema 2.0 원장에 확정했다.

## 4. 세부영역 증보 계산 규칙

- 20/20/16/16/16/12% 교육 비율, Stage별 승인 총 files, train/validation 90:10과 150-record 정수 단위를 함께 만족하도록 allocation 정본의 largest-remainder 결과를 사용한다.
- 현행 primary 기준은 A01~A06 각각 총 50/50/40/40/40/30 files다.
- `세부영역 증보 T/V = 승인 T/V - 현행 primary T/V`다.
- pilot 완료는 A01 train+val 각 1, A03 train 1, A06 train 1이다. `생성 대기 = 승인 총량 - pilot 완료`다.
- 증보 version 범위는 충돌 방지용 계획에서 출발했으며, 후속 승인 뒤 중앙 schema 2.0 원장의 실제 filename·ID·family 예약으로 활성화했다.
- 54개 세부영역별 확정 수치는 중앙 Design §40.5, curriculum 설계서와 각 Stage README에 동일하게 기록한다.

## 5. Stage1 `relations` 13개 어휘의 Stage2~10 적용 검토

### 5.1 검토 결론

통제 완료된 `relations` 필드와 13개 어휘는 **그대로 유지하는 것이 타당하다. 단, 고차 교육능력의 이름으로 사용하거나 완전한 관계 그래프로 해석해서는 안 된다.** identity legacy의 자유 어휘 원본 `relations` 1,916종은 Stage2~10으로 전파하지 않는다.

- `relations`: 문장 안에 실제로 드러난 기초 의미 관계의 2~5개 비완전 투영
- `type`: Stage별 고차 교육능력. 54개 `<slug>_packet`이 인과·조건·계획·담화·검증 등의 능력 구분을 담당
- `concept_family`: 도메인과 세부 의미축을 담당

따라서 `causal`, `dependency`, `temporal_order`, `evidence` 같은 이름을 `relations`에 추가하지 않는다. 이들은 해당 Stage의 `type`으로 평가한다. 반대로 인과 학습 record라는 이유만으로 `process`, `state`, `boundary`를 억지로 넣지 않는다. `relation_focus`도 허용 목록이나 분포 목표가 아니다.

### 5.2 pilot 근거

- 5,400 records에서 통제 밖 relation 0, record별 2~5개·내부 중복 0
- 전체 relation 배정 17,619회 중 `other` 784회 = 4.4497%
- 13개 label은 전체 pilot에서 모두 관측됐지만 Stage별 0회인 label이 존재한다. 이는 교육영역 의미 차이이며 강제 보충 대상이 아니다.
- validation은 개별 label을 train에서 관측하고, `unseen_relation`은 새 label이 아니라 train 미관측 정렬 relation-set 조합으로 사용해 13개 어휘 폐쇄성과 일반화 평가를 함께 유지했다.

### 5.3 corpus 생성 중 필수 gate

1. 모든 record의 `type`이 예약된 Stage·area packet type과 정확히 일치한다.
2. `relations`는 문장에 직접 근거가 있는 13개 중 2~5개만 사용한다.
3. Stage나 area마다 13개 전부를 채우거나 빈도를 균등화하지 않는다.
4. `other`는 고차 능력 label의 대용품이 아니며 대표 concept과 의미 유형을 계속 보고한다.
5. Stage5·6·7의 `tools/build_pilot.py`와 Stage5의 `tools/audit_pilot.py`에 있던 `relations ⊆ relation_focus` 실행 조건은 제거했다. 13개 통제 어휘·2~5개·record 내부 중복 금지·source projection gate는 유지했으며, 2026-09-02 재감사에서 pilot 12 files/1,800 records 오류 0과 기존 corpus/source SHA 24/24 일치를 확인했다.
6. downstream 평가에서는 13개 relation별 결과와 54개 `type`별 결과를 분리 보고한다.

새 `capability` 필드는 현재 `type`과 중복되므로 추가하지 않는 안을 권고한다. 향후 loader가 `type`을 보존하지 않는 사실이 확인될 때만 별도 schema 변경안을 사용자 승인 대상으로 올린다.

`semantic_axis`는 13개 relations와 달리 폐쇄 통제 어휘가 아니라 family의 세부 교육 초점을 설명하는 문자열이다. 독립 의미 감사에서 Stage2~6 신규 1,025행이 중앙 area 축의 의미 정렬된 세분 표현이고 의미 이탈·중복은 0으로 판정됐다. 따라서 현 생성에서는 세분 축을 보존하고 exact whitelist를 강제하지 않는다. 향후 downstream consumer가 canonical exact 값을 요구할 때는 원문 축을 덮어쓰지 말고 별도 `semantic_axis_canonical` 투영 또는 alias registry를 승인·추가한다.

## 6. 진행 기록

| 순서 | 항목 | 상태 | 근거/재개점 |
|---:|---|---|---|
| 1 | 실측 3M안 사용자 승인 기록 | 완료 | 2026-09-02 사용자 지시 |
| 2 | Stage별 총량·90:10·token 투영 재검산 | 완료 | allocation SHA `2188111c…3972` |
| 3 | 54개 세부영역 증보 T/V·version 범위 산출 | 완료 | Design·curriculum·README 동일 수치 반영 |
| 4 | Stage1 relations 적용 타당성 검토 | 완료 | §5 검토 결론 |
| 5 | 중앙 Design 갱신 | 완료 | §40.3~§40.6, v100+ 표기 규칙 반영 |
| 6 | curriculum 설계서 갱신 | 완료 | 총량·54개 증보표·relation 정책·승인 gate 반영 |
| 7 | Stage2~10 README 9개 갱신 | 완료 | Stage별 총량·6개 영역 증보표·relation 경계 반영 |
| 8 | 문서 전용 무결성 감사 | 완료 | §7 PASS |
| 9 | Stage5~7 relation-focus 도구 수정·재감사 | 완료 | G1 PASS, 사람용·기계용 재감사 보고서 보존 |
| 10 | contingency·신규 family 선정 및 원장/manifest revision | 완료 | G2·G3 PASS, 4,370 reservations와 9 manifests 동기화 |
| 11 | semantic-composition generator preflight r1 | 실패·수정 완료 | corpus/source 쓰기 0; S2-A01-T-050에서 5×5×5=125 조합으로 primary concept 중복 발견 |
| 12 | semantic-composition generator preflight r2~final | 구조 PASS·정본 FAIL | 9-Stage 1,350행은 token·known-grammar·primary uniqueness PASS로 개선됐으나 manual-review debt 1,350이며 Guide §10 직접 작성 판정 FAIL. `--write` hard block과 임시 파일 0을 재현 |
| 13 | 남은 4,334파일 corpus 생성 | 착수·1 file 완료 | `S2-A01-T-002` source/JSON 1쌍·150 records 직접 작성 PASS. 남은 4,333 files; 다음 `S2-A01-T-003` |
| 14 | 전체 통합 감사·문서 확정 | 부분 PASS | 현행 37 source/corpus pairs·5,550 records 감사 PASS. 전체 완료 감사는 4,333 files 생성 뒤 수행 |

## 7. 후속 승인 전 문서 전용 감사 — 역사 snapshot

이 절은 중앙 family·manifest revision을 승인받기 전의 문서 전용 gate 기록이다. 아래의 `불변` 판정은 당시 작업 단계에만 적용되며, 현행 revision 결과는 §8~§11과 별도 family/manifest 감사보고서가 정본이다.

### 7.1 판정

`PASS` — 승인된 문서 11개와 본 작업원장만 갱신했다. 이번 단계에서 corpus·canonical source·builder·중앙 family JSON·Stage manifest를 수정하거나 실행하지 않았다.

| 검사 | 결과 |
|---|---:|
| allocation 정본과 Stage 총량 | 4,370 files, 3,933/437, 655,500 records, 27,001,510 projected tokens — PASS |
| 세부영역 표 | 54/54 areas가 Design·curriculum·해당 README에서 각각 exact match — PASS |
| 허용된 기존 설계 문서 변경 | 11/11 |
| protected baseline 비허용 row | 360/360 SHA-256 불변 |
| 중앙 family JSON | `823881a7…c6c99`, 불변 |
| Stage manifest | 9/9 baseline SHA-256 불변 |
| pilot corpus JSON | 36/36 integrated-audit SHA-256 일치 |
| pilot canonical source | 36/36 integrated-audit SHA-256 일치 |
| 당시 Stage2~10 corpus/source 수 | 36/36, 문서 전용 감사 시점에는 기존 pilot만 존재. 현행은 §9~§11의 37/37을 적용 |
| stale pre-pilot 문구 | curriculum·9 README에서 0 |
| `git diff --check` | PASS |

### 7.2 당시 갱신 문서 최종 SHA-256

| 파일 | 최종 SHA-256 |
|---|---|
| `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md` | `0540c1572bdb729ffbfc9c627e1243f00e87beb4e56ae72667ef8f07ec553eaa` |
| `TinyLM_Stage2_Stage10_Curriculum_and_Family_Reservation_Draft.md` | `39eaa7d8423596dd2e643cb4fdc60d476196bd39353063bc4c8cf49f6be632b8` |
| `stage2_highdensity_dataset/README.md` | `aa2bc75f76f3b0ff8776506dc7e511c3d28e7f7606b7e37ff7a96403b81c7959` |
| `stage3_highdensity_dataset/README.md` | `bc2924167664f2b69927da9ca028dd9e82a1c48a47f018d0c56144e58ce9bb5c` |
| `stage4_highdensity_dataset/README.md` | `9291c22ab4b521bd5aa3f3b58c7f473fa2d82ae7a54012d1bc98c589f4ca126d` |
| `stage5_highdensity_dataset/README.md` | `72e85304a664c88fb3998fcec6262d59733a187b56375c10f4c521491040ffdb` |
| `stage6_highdensity_dataset/README.md` | `452bb2a1d967781114a78b2a264383bf949113ef6a61ce29a2a64024987dc18c` |
| `stage7_highdensity_dataset/README.md` | `2e134a7eaa3c99d04fc01be1eaa5519f5a2de2226bc474957cda9af28662d989` |
| `stage8_highdensity_dataset/README.md` | `84ab8fcb2e3a413b04fbe1987f62decddf6ba27fcdcf5c082da75d66d5cf0b50` |
| `stage9_highdensity_dataset/README.md` | `e1ed087dc256d09d5495069fafacdc8c2390ae45cd7d0a773fc5027e3d6e28a2` |
| `stage10_highdensity_dataset/README.md` | `ff358a5a6bdc9b3e994e6882d92612a9f4933ce1afe0d1652e7bebb12cfc485f` |

## 8. 미확정·다음 재개점

- contingency 225개의 54개 area·train/validation 배치 — 완료
- 신규 family 1,895개의 정확한 이름·도메인·semantic axis — 완료
- 중앙 family ledger와 9개 manifest revision — 완료, 중앙 SHA-256 `21804692…e5aa7`
- 4,370개 family 의미 독립성 별도 감사 — `PASS_WITH_TAXONOMY_POLICY_NOTE`; 세분 axis 보존 정책은 §5에 기록
- corpus 생성은 전체 train을 Stage2→10 순으로 만든 뒤 train gate를 닫고, 전체 validation을 Stage2→10 순으로 생성한다. 2026-09-02 `S2-A01-T-002` 직접 작성 파일로 실제 생성을 시작했다.

후속 전체 작업 승인은 완료됐다. 중단 시 §6 진행 기록에서 첫 미완료 항목을 찾고, 실제 source·JSON 수와 최신 감사 결과를 함께 대조한 뒤 재개한다. 기존 pilot 36개와 보호 대상은 덮어쓰지 않는다.

## 9. 후속 실행 체크포인트

| 체크포인트 | 상태 | 완료 근거 |
|---|---|---|
| G1 relation-focus 도구 수정 | PASS | `TinyLM_Stage5_7_Relation_Focus_Gate_Reaudit_2026-09-02.md` SHA-256 `95400763…f6378d`; 기계 보고서 `251f793b…9ccf` |
| G2 family 4,370개 완전 예약 | PASS | primary/contingency/new `2,250/225/1,895`, exact·정규화 family 및 655,500 concrete ID 중복 0 |
| G3 manifest 9개 동기화 | PASS | 중앙 SHA `21804692…e5aa7`, Stage별 `480/470/440/600/410/470/500/510/490` exact projection |
| G4 train 3,933 files | 진행 중 | 기존 pilot 27 + 직접 작성 신규 1 = 28 files; 신규 train 1/3,906 완료 |
| G5 validation 437 files | 차단 | G4 train 전수 relation-set 확정 전 생성 금지; 현재 pilot 9 files만 존재 |
| G6 전체 655,500 records | 부분 PASS | 현행 5,550 records 감사 PASS; G4·G5 완료 뒤 전수 통합 감사 |

## 10. 실제 corpus 순차 생성 원장

기존 pilot은 각 Stage train 3 files·validation 1 file로 보존한다. 신규 생성은 먼저 train 전체를 Stage2→Stage10 순서로 완료·감사하고, 그 뒤 validation 전체를 같은 Stage 순서로 생성한다.

| Stage | 최종 train/val | 시작 train/val | 신규 train/val | 신규 합계 | 현재 상태 |
|---:|---:|---:|---:|---:|---|
| 2 | 432 / 48 | 3 / 1 | 429 / 47 | 476 | 신규 train 1 완료, Stage2 잔여 475 |
| 3 | 423 / 47 | 3 / 1 | 420 / 46 | 466 | 생성 전 |
| 4 | 396 / 44 | 3 / 1 | 393 / 43 | 436 | 생성 전 |
| 5 | 540 / 60 | 3 / 1 | 537 / 59 | 596 | 생성 전 |
| 6 | 369 / 41 | 3 / 1 | 366 / 40 | 406 | 생성 전 |
| 7 | 423 / 47 | 3 / 1 | 420 / 46 | 466 | 생성 전 |
| 8 | 450 / 50 | 3 / 1 | 447 / 49 | 496 | 생성 전 |
| 9 | 459 / 51 | 3 / 1 | 456 / 50 | 506 | 생성 전 |
| 10 | 441 / 49 | 3 / 1 | 438 / 48 | 486 | 생성 전 |
| **합계** | **3,933 / 437** | **27 / 9** | **3,906 / 428** | **4,334** | **신규 1 완료, 전체 잔여 4,333** |

재개 시 이 표만 믿지 않고 실제 `train/*.json`, `val/*.json`, `sources/train/*`, `sources/val/*` 수와 마지막 stage checkpoint 감사 파일을 함께 대조한다. 기존 pilot 경로가 존재하면 덮어쓰지 않고 기준 SHA와 일치할 때만 skip한다.

## 11. 자동 생성 차단 감사와 직접 작성 재개점

canonical 쓰기 전에 수행한 독립 dry-run/code review 결과는 다음과 같다.

- 자동 semantic-composition 경로의 canonical corpus/source 신규 쓰기: **0 files**
- 직접 작성 경로의 canonical corpus/source 신규 쓰기: **각 1 file**
- 현재 실파일: 기존 pilot 36쌍 + Stage2 train v02 1쌍 = JSON/source 37/37
- 최초 primary 조합 수 오류: 125/150 unique, 사전 gate에서 차단
- 중간 r2 역사 표본: 조사 탐지 520 rows/609 locations, 명백한 인접 반복 51 rows, 여러 Stage token 평균 이탈과 Stage5 4.489M 투영을 확인하고 수정
- 최종 9-Stage 1,350-row 가상 표본: 전 Stage tokenizer 목표 ±10% PASS, known grammar 0, 파일별 primary 150/150 unique, provenance fingerprint 132~146종·최대 share 2%, 구조 PASS
- 그러나 최종 가상 표본 전부가 `manual_semantic_review=false`여서 manual-review debt 1,350, 직접 작성 판정 `FAIL_GENERATED_ROWS_REQUIRE_MANUAL_SEMANTIC_REVIEW`
- Stage2 전체 가상 확장 480 files/72,000 rows는 구조·token·known-grammar gate를 통과했지만 생성 행 71,400개가 모두 같은 직접 작성 debt라 canonical 생성 근거로 사용할 수 없음. 4,370 files 전체 가상 run은 시간 경계에서 중단했으며 PASS로 보고하지 않음
- canonical `--write` 독립 재현은 exit 1, `CANONICAL_WRITE_BLOCKED_DIRECT_AUTHORING_FAIL`, 격리 임시공간 파일 0
- 기존 pilot read-only 감사: 36 source/corpus pairs·5,400 rows, exact duplicate/leakage 0, hard grammar 0, cross-record 5-word n-gram 반복 0/98,453 assignments, manual-review debt 0. 조사 휴리스틱 warning 155개는 `결과와`, `차이가` 같은 부분문자열 false positive를 포함해 자동 오류가 아닌 검토 후보로 분리
- 2026-09-01 보호 baseline을 사용하는 legacy integrated auditor는 승인된 Guide·Design·curriculum·README·중앙 원장·manifest 22경로가 달라져 `protected_file_changed` 1종으로 FAIL한다. corpus 오류가 아니며 현행 authorized revision은 별도 family/manifest audit와 read-only corpus auditor로 검증
- 직접 작성 경로의 첫 대상 `S2-A01-T-002`, `stage2_(11)causal_structure_high_density_train_v02.json`, ID `S2-CSH-00151~S2-CSH-00300`은 150행 직접 작성·포장·전수 감사 PASS. source SHA `6f42ea7f…c22462b`, corpus SHA `fc79cf4a…aa41f0`
- 신규 v02 relations 573회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/1/28/150/16/107/29/9/95/58/80/0`; cardinality 3개 27 records, 4개 123 records
- 신규 v02 duplicate·normalized duplicate 0, 5-word n-gram 반복 0/2,998 assignments, character similarity ≥0.80 0 pair, word Jaccard ≥0.60 0 pair, exact tokenizer 평균 45.206667(+EOS) PASS
- 현재 자동 초안의 `manual_semantic_review=false`는 구조 PASS와 정본 의미 PASS를 분리하는 필수 표식이며, 한 건이라도 남으면 canonical publish를 차단한다.

도구 preflight 상세는 `tools/stage2_10_tool_preflight_report_2026-09-02.md`(SHA-256 `4d94813218c68c0541d356109be52d39b6e72388cd9aef515060b05152cc43ce`)에 보존했다. 실행 예시는 `tools/README_stage2_10_corpus_engine.md`에 있으며, read-only pilot 감사는 기본 partial mode인 `--check-only --json`을 사용한다. 새 Python 도구는 저장소의 `*.py` ignore 규칙 때문에 commit 대상으로 삼을 때 `git add -f`가 필요하다.

전체 체크포인트 판정은 `audit_reports/TinyLM_Stage2_10_Actual3M_Authorized_Checkpoint_Audit_2026-09-02.md`와 기계 부속 `audit_reports/machine/TinyLM_Stage2_10_Actual3M_Authorized_Checkpoint_Audit_2026-09-02.json`에 보존한다.

다음 재개점은 `S2-A01-T-003`, `stage2_(11)causal_structure_high_density_train_v03.json`, ID `S2-CSH-00301~S2-CSH-00450`, family `스마트 온실 관수·환경제어 — 원인 방향·피드백·역인과 판정`이다. v02와 같은 record별 직접 작성 → source check → package → file audit → 전체 partial audit 순서로 진행한다.

semantic-composition 초안의 canonical 승격은 여전히 승인되지 않았다. 이 경로를 쓰려면 Guide §10 예외를 별도로 명시해야 하며, 현재 직접 작성 착수를 예외 승인으로 해석하지 않는다. 기존 pilot·Stage1 보호 corpus·저밀도·held-out 수정 권한도 확대되지 않는다.
