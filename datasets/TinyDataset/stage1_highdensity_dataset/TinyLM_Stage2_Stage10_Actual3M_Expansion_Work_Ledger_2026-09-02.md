# TinyLM Stage2~10 실측 3M 증보 작업원장 — 2026-09-02

- 문서 상태: `FULL_GENERATION_AUTHORIZED_IN_PROGRESS`
- 기준 시각: 2026-09-02 KST
- 목적: 컨텍스트 압축·세션 중단 뒤에도 승인 범위, 수치, 미완료 항목과 재개점을 잃지 않게 하는 단일 작업원장
- corpus 생성 권한: **있으나 현재 일시중단**. 정본 Guide §10 직접 작성 경로로 Stage2 train 신규 38 files를 완료했고 Stage2 A01의 나머지 source도 작성했지만, 2026-09-03 사용자 중단 요청에 따라 새 corpus 생성·포장을 멈췄다. 자동 semantic-composition 초안의 canonical source/train/val 쓰기 gate는 계속 닫혀 있다.
- 재개 상태: 완료 통계는 v39까지의 74쌍·11,100 records다. 교육영역 일괄 작성 전환 뒤 `S2-A01-T-040~087` source 48개·7,200행을 직접 작성해 최소 계약을 통과했으나 corpus·checkpoint가 없어 완료 통계에 넣지 않는다. A01 1차 batch 감사와 일부 직접 보정까지 끝났고, 다음 재개점은 남은 5-word 반복·파일별 token·fuzzy·조사 검토를 끝낸 뒤 전면 재감사하는 단계다.
- 감사 cadence: 2026-09-02 추가 지시에 따라 앞으로 파일별 token 평균·중복·유사도·조사 감사와 수정은 각 Stage의 **교육영역 source 전체가 완성된 뒤 일괄 수행**한다. 작성 중에는 parse·행 수·schema·relations·primary literal/고유성 최소 계약만 확인하며, batch gate 통과 전 corpus 포장과 완료 계상은 하지 않는다.

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

전체 생성 승인은 corpus 범위와 순서를 승인한 것이며, 정본 Guide §10의 `record별 직접 작성`·`자동 의미 생성 금지`를 폐기한 승인은 아니다. 650,100 records를 자동 조합하는 초안 엔진을 독립 점검한 결과 concept 문자열 대량 조합, relation 선배정 뒤 clause 부착, 반복 template, 다수 조사 오류가 확인됐다. 따라서 이 초안은 canonical `sources/`, `train/`, `val/`에 쓰지 않는다. 현 작업은 Guide를 유지하는 직접 작성 장기 경로로 전환했고, `S2-A01-T-002~033`을 record별 직접 작성·감사해 확정했다.

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
| 13 | 남은 4,334파일 corpus 생성 | 일시중단·38 files 완료 | `S2-A01-T-002~039` source/JSON 38쌍·5,700 records 직접 작성 PASS. `S2-A01-T-040~087` source 48개·7,200행 작성·미포장, A01 1차 batch 구조 보정 후 품질 보정 중단; 남은 완료 대상 4,296 files |
| 14 | 전체 통합 감사·문서 확정 | 부분 PASS | 현행 74 source/corpus pairs·11,100 records 감사 PASS. 전체 완료 감사는 4,296 files 생성 뒤 수행 |

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
| 당시 Stage2~10 corpus/source 수 | 36/36, 문서 전용 감사 시점에는 기존 pilot만 존재. 현행은 §9~§11의 73/73을 적용 |
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
- corpus 생성은 전체 train을 Stage2→10 순으로 만든 뒤 train gate를 닫고, 전체 validation을 Stage2→10 순으로 생성한다. 2026-09-02 `S2-A01-T-002`로 시작해 `S2-A01-T-038`까지 직접 작성·감사했다.

후속 전체 작업 승인은 완료됐지만 2026-09-03 사용자 요청으로 실행 목표는 일시중단 상태다. 재개 승인 전에는 새 source·corpus를 생성하지 않는다. 재개 시 §6 진행 기록에서 첫 미완료 항목을 찾고, 실제 source·JSON 수와 최신 감사 결과를 함께 대조한다. 기존 pilot 36개와 보호 대상은 덮어쓰지 않는다.

## 9. 후속 실행 체크포인트

| 체크포인트 | 상태 | 완료 근거 |
|---|---|---|
| G1 relation-focus 도구 수정 | PASS | `TinyLM_Stage5_7_Relation_Focus_Gate_Reaudit_2026-09-02.md` SHA-256 `95400763…f6378d`; 기계 보고서 `251f793b…9ccf` |
| G2 family 4,370개 완전 예약 | PASS | primary/contingency/new `2,250/225/1,895`, exact·정규화 family 및 655,500 concrete ID 중복 0 |
| G3 manifest 9개 동기화 | PASS | 중앙 SHA `21804692…e5aa7`, Stage별 `480/470/440/600/410/470/500/510/490` exact projection |
| G4 train 3,933 files | 진행 중 | 기존 pilot 27 + 직접 작성 신규 38 = 65 완료 files; `S2-A01-T-040~087` source-only 48개는 미계상, 신규 train 38/3,906 완료, 3,868 files 남음 |
| G5 validation 437 files | 순차 대기 | G4 train 전수 relation-set 확정 뒤 생성; 현재 pilot 9 files만 존재 |
| G6 전체 655,500 records | 부분 PASS | 현행 11,100 records 감사 PASS; G4·G5 완료 뒤 전수 통합 감사 |

## 10. 실제 corpus 순차 생성 원장

기존 pilot은 각 Stage train 3 files·validation 1 file로 보존한다. 신규 생성은 먼저 train 전체를 Stage2→Stage10 순서로 완료·감사하고, 그 뒤 validation 전체를 같은 Stage 순서로 생성한다.

| Stage | 최종 train/val | 시작 train/val | 신규 train/val | 신규 합계 | 현재 상태 |
|---:|---:|---:|---:|---:|---|
| 2 | 432 / 48 | 3 / 1 | 429 / 47 | 476 | 신규 train 37 완료, Stage2 잔여 439 |
| 3 | 423 / 47 | 3 / 1 | 420 / 46 | 466 | 생성 전 |
| 4 | 396 / 44 | 3 / 1 | 393 / 43 | 436 | 생성 전 |
| 5 | 540 / 60 | 3 / 1 | 537 / 59 | 596 | 생성 전 |
| 6 | 369 / 41 | 3 / 1 | 366 / 40 | 406 | 생성 전 |
| 7 | 423 / 47 | 3 / 1 | 420 / 46 | 466 | 생성 전 |
| 8 | 450 / 50 | 3 / 1 | 447 / 49 | 496 | 생성 전 |
| 9 | 459 / 51 | 3 / 1 | 456 / 50 | 506 | 생성 전 |
| 10 | 441 / 49 | 3 / 1 | 438 / 48 | 486 | 생성 전 |
| **합계** | **3,933 / 437** | **27 / 9** | **3,906 / 428** | **4,334** | **신규 38 완료, 전체 잔여 4,296** |

재개 시 이 표만 믿지 않고 실제 `train/*.json`, `val/*.json`, `sources/train/*`, `sources/val/*` 수와 마지막 stage checkpoint 감사 파일을 함께 대조한다. 기존 pilot 경로가 존재하면 덮어쓰지 않고 기준 SHA와 일치할 때만 skip한다.

## 11. 자동 생성 차단 감사와 직접 작성 재개점

canonical 쓰기 전에 수행한 독립 dry-run/code review 결과는 다음과 같다.

- 자동 semantic-composition 경로의 canonical corpus/source 신규 쓰기: **0 files**
- 직접 작성 경로의 canonical corpus/source 신규 쓰기: **각 38 files**
- 현재 실파일: 기존 pilot 36쌍 + Stage2 train v02~v39 38쌍 = JSON/source 74/74
- 교육영역 batch 진행물: Stage2 A01 `S2-A01-T-040~087` source 48개·7,200행, corpus/checkpoint 없음; 완료 쌍에는 미포함. source 작성 및 1차 구조 보정은 완료했으나 5-word 반복·파일별 token·fuzzy·조사 검토가 남아 일시중단
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
- 직접 작성 경로의 두 번째 대상 `S2-A01-T-003`, `stage2_(11)causal_structure_high_density_train_v03.json`, ID `S2-CSH-00301~S2-CSH-00450`은 150행 직접 작성·포장·전수 감사 PASS. source SHA `5f9204f…f97b6e`, corpus SHA `27178ea8…a7172f`
- 신규 v03 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/15/35/147/17/72/64/32/126/46/46/0`; cardinality 4개 150 records, 고유 relation-set 45종
- 신규 v03 exact·normalized duplicate 0, 5-word n-gram 반복 0/2,924 assignments, 내부·기존 Stage2 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 44.006667(+EOS) PASS
- 직접 작성 경로의 세 번째 대상 `S2-A01-T-004`, `stage2_(11)causal_structure_high_density_train_v04.json`, ID `S2-CSH-00451~S2-CSH-00600`은 150행 직접 작성·포장·전수 감사 PASS. source SHA `c86c4c0a…e2d2e76`, corpus SHA `c7b98529…5d36d843`
- 신규 v04 relations 587회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/23/39/150/35/117/21/30/71/38/63/0`; cardinality 3개 13 records, 4개 137 records, 고유 relation-set 54종
- 신규 v04 exact·normalized duplicate 0, 5-word n-gram 반복 0/2,599 assignments, 내부·기존 Stage2 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 38.853333(+EOS) PASS
- 직접 작성 경로의 네 번째 대상 `S2-A01-T-005`, `stage2_(11)causal_structure_high_density_train_v05.json`, ID `S2-CSH-00601~S2-CSH-00750`은 150행 직접 작성·포장·전수 감사 PASS. source SHA `a56d13b6…f25285eb`, corpus SHA `2136848c…9ab6add9`
- 신규 v05 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/56/55/150/29/96/34/15/64/47/54/0`; cardinality 4개 150 records, 고유 relation-set 47종
- 신규 v05 exact·normalized duplicate 0, 5-word n-gram 반복 0/2,799 assignments, 내부·기존 Stage2 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 41.966667(+EOS) PASS
- 직접 작성 경로의 다섯 번째 대상 `S2-A01-T-006`, `stage2_(11)causal_structure_high_density_train_v06.json`, ID `S2-CSH-00751~S2-CSH-00900`은 150행 직접 작성·포장·전수 감사 PASS. source SHA `5e33e2b7…381221e`, corpus SHA `24cf8398…e7577fd7`
- 신규 v06 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/49/37/150/22/42/42/30/111/58/59/0`; cardinality 4개 150 records, 고유 relation-set 50종
- 신규 v06 exact·normalized duplicate 0, 5-word n-gram 반복 0/2,752 assignments, 내부·기존 Stage2 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 42.706667(+EOS) PASS
- 직접 작성 경로의 여섯 번째 대상 `S2-A01-T-007`, `stage2_(11)causal_structure_high_density_train_v07.json`, ID `S2-CSH-00901~S2-CSH-01050`은 150행 직접 작성·포장·전수 감사 PASS. source SHA `dbbc550b…9d77243e`, corpus SHA `e582739e…52f52e92`
- 신규 v07 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/53/53/150/32/64/18/54/75/52/49/0`; cardinality 4개 150 records, 고유 relation-set 61종
- 신규 v07 exact·normalized duplicate 0, 5-word n-gram 반복 0/2,685 assignments, 내부·기존 Stage2 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 43.240000(+EOS) PASS
- 직접 작성 경로의 일곱 번째 대상 `S2-A01-T-008`, `stage2_(11)causal_structure_high_density_train_v08.json`, ID `S2-CSH-01051~S2-CSH-01200`은 150행 직접 작성·포장·전수 감사 PASS. source SHA `a74c5888…924d67`, corpus SHA `cbe738bd…06ff97`
- 신규 v08 relations 597회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/16/53/150/25/52/49/50/124/45/33/0`; cardinality 3개 3 records, 4개 147 records, 고유 relation-set 40종
- 신규 v08 exact·normalized duplicate 0, 5-word n-gram 반복 0/2,898 assignments, 내부·기존 Stage2 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 45.240000(+EOS) PASS
- 직접 작성 경로의 여덟 번째 대상 `S2-A01-T-009`, `stage2_(11)causal_structure_high_density_train_v09.json`, ID `S2-CSH-01201~S2-CSH-01350`은 150행 직접 작성·포장·전수 감사 PASS. source SHA `32449203…bdeb6ccc3`, corpus SHA `0588971d…af86152b`
- 신규 v09 relations 596회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/19/79/150/33/112/47/24/34/36/62/0`; cardinality 3개 4 records, 4개 146 records, 고유 relation-set 43종
- 신규 v09 exact·normalized duplicate 0, 5-word n-gram 반복 0/2,407 assignments, 내부·기존 Stage2 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 38.633333(+EOS) PASS
- 직접 작성 경로의 아홉 번째 대상 `S2-A01-T-010`, `stage2_(11)causal_structure_high_density_train_v10.json`, ID `S2-CSH-01351~S2-CSH-01500`은 중단 전 133행을 보존하고 누락 17행을 직접 작성한 뒤 포장·전수 감사 PASS. source SHA `f38ff62c…6a12bed`, corpus SHA `63657393…faec13`
- 신규 v10 relations 596회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/77/90/150/21/73/22/21/42/43/57/0`; cardinality 3개 4 records, 4개 146 records, 고유 relation-set 46종
- 신규 v10 exact·normalized duplicate 0, 5-word n-gram 반복 0/2,603 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 42.106667(+EOS) PASS
- 직접 작성 경로의 열 번째 대상 `S2-A01-T-011`, `stage2_(11)causal_structure_high_density_train_v11.json`, ID `S2-CSH-01501~S2-CSH-01650`은 150행 직접 작성·포장·전수 감사 PASS. source SHA `a94340dd…5fb4e3`, corpus SHA `0a374e29…c9cbb0`
- 신규 v11 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/51/81/150/43/56/19/14/94/59/33/0`; cardinality 4개 150 records, 고유 relation-set 44종
- 신규 v11 exact·normalized duplicate 0, 5-word n-gram 반복 0/3,156 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 45.386667(+EOS) PASS
- 직접 작성 경로의 열한 번째 대상 `S2-A01-T-012`, `stage2_(11)causal_structure_high_density_train_v12.json`, ID `S2-CSH-01651~S2-CSH-01800`은 150행 직접 작성·포장 후 token 상한과 교차 5-word 반복을 직접 수정해 전수 감사 PASS. source SHA `aa367da7…99da5ad`, corpus SHA `2391026c…230e49`
- 신규 v12 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/50/123/150/30/77/7/15/82/20/46/0`; cardinality 4개 150 records, 고유 relation-set 38종
- 신규 v12 final exact·normalized duplicate 0, 5-word n-gram 반복 0/3,244 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 45.320000(+EOS) PASS
- 직접 작성 경로의 열두 번째 대상 `S2-A01-T-013`, `stage2_(11)causal_structure_high_density_train_v13.json`, ID `S2-CSH-01801~S2-CSH-01950`은 150행 직접 작성·포장 후 교차 5-word 반복 1종을 직접 수정해 전수 감사 PASS. source SHA `e3e6f977…df6347`, corpus SHA `7210e0cc…02e180`
- 신규 v13 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/48/90/150/26/59/36/18/124/34/15/0`; cardinality 4개 150 records, 고유 relation-set 32종
- 신규 v13 final exact·normalized duplicate 0, 5-word n-gram 반복 0/3,002 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 44.913333(+EOS) PASS
- 직접 작성 경로의 열세 번째 대상 `S2-A01-T-014`, `stage2_(11)causal_structure_high_density_train_v14.json`, ID `S2-CSH-01951~S2-CSH-02100`은 150행 직접 작성·포장·전수 감사 PASS. source SHA `fda7e4a3…e0722ae`, corpus SHA `dff92faf…c9d31`
- 신규 v14 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/18/62/150/14/131/43/3/71/41/67/0`; cardinality 4개 150 records, 고유 relation-set 36종
- 신규 v14 exact·normalized duplicate 0, 5-word n-gram 반복 0/3,098 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 44.800000(+EOS) PASS
- 직접 작성 경로의 열네 번째 대상 `S2-A01-T-015`, `stage2_(11)causal_structure_high_density_train_v15.json`, ID `S2-CSH-02101~S2-CSH-02250`은 150행 직접 작성 후 영문·숫자 말미 primary 조사 6건과 tokenizer 상한을 직접 수정해 포장·전수 감사 PASS. source SHA `ac7638dd…51577f`, corpus SHA `52e1098c…98a2e`
- 신규 v15 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/48/90/150/15/85/31/5/72/42/62/0`; cardinality 4개 150 records, 고유 relation-set 41종
- 신규 v15 exact·normalized duplicate 0, 5-word n-gram 반복 0/3,008 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 최초 47.553333 차단·최종 45.220000(+EOS) PASS
- 직접 작성 경로의 열다섯 번째 대상 `S2-A01-T-016`, `stage2_(11)causal_structure_high_density_train_v16.json`, ID `S2-CSH-02251~S2-CSH-02400`은 150행 직접 작성·포장 뒤 파일 내부 5-word 반복 1종과 v11 교차 열거 반복 4종을 직접 재서술해 전수 감사 PASS. source SHA `3f3deb0f…ba3076`, corpus SHA `12b42804…28598`
- 신규 v16 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/43/127/150/23/30/43/29/63/61/31/0`; cardinality 4개 150 records, 고유 relation-set 40종
- 신규 v16 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,759·0/141,385 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 40.033333(+EOS) PASS
- 직접 작성 경로의 열여섯 번째 대상 `S2-A01-T-017`, `stage2_(11)causal_structure_high_density_train_v17.json`, ID `S2-CSH-02401~S2-CSH-02550`은 150행 직접 작성·포장 뒤 파일 내부·누적 5-word 반복 각 1종을 직접 수정해 전수 감사 PASS. source SHA `56df9cf1…f91980`, corpus SHA `9080211e…a9aa2c`
- 신규 v17 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/35/84/150/38/73/38/27/50/49/56/0`; cardinality 4개 150 records, 고유 relation-set 56종
- 신규 v17 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/3,261·0/144,646 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 45.733333(+EOS) PASS
- 직접 작성 경로의 열일곱 번째 대상 `S2-A01-T-018`, `stage2_(11)causal_structure_high_density_train_v18.json`, ID `S2-CSH-02551~S2-CSH-02700`은 150행 직접 작성 중 v13 교차 primary 1건과 tokenizer 상한을 직접 수정한 뒤 포장·전수 감사 PASS. source SHA `725da8e8…d6e12e3`, corpus SHA `736e64ec…6c625cb`
- 신규 v18 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/39/70/150/38/62/45/26/100/39/31/0`; cardinality 4개 150 records, 고유 relation-set 54종
- 신규 v18 exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/3,082·0/147,728 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 최초 46.880000 차단·최종 45.520000(+EOS) PASS
- 직접 작성 경로의 열여덟 번째 대상 `S2-A01-T-019`, `stage2_(11)causal_structure_high_density_train_v19.json`, ID `S2-CSH-02701~S2-CSH-02850`은 150행 직접 작성 뒤 primary literal 누락 71건과 v09 교차 primary 1건을 직접 수정해 포장·전수 감사 PASS. source SHA `cc84ef79…9bb08d`, corpus SHA `fdd213f7…3f5f52`
- 신규 v19 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/32/81/150/25/118/42/14/39/40/59/0`; cardinality 4개 150 records, 고유 relation-set 38종
- 신규 v19 exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,486·0/150,214 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 38.600000(+EOS) PASS
- 직접 작성 경로의 열아홉 번째 대상 `S2-A01-T-020`, `stage2_(11)causal_structure_high_density_train_v20.json`, ID `S2-CSH-02851~S2-CSH-03000`은 171행 초안에서 중복 성격 후행 21행을 제외해 150행을 확정하고, 파일 내부 5-word 반복 1종을 직접 재서술한 뒤 포장·전수 감사 PASS. source SHA `b97e0b66…6ed3a30`, corpus SHA `6d8871a3…3aecd6`
- 신규 v20 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 1/0/48/69/150/48/81/33/23/36/42/69/0`; cardinality 4개 150 records, 고유 relation-set 58종
- 신규 v20 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,735·0/152,949 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 40.640000(+EOS) PASS
- 직접 작성 경로의 스무 번째 대상 `S2-A01-T-021`, `stage2_(11)causal_structure_high_density_train_v21.json`, ID `S2-CSH-03001~S2-CSH-03150`은 162행 직접 원고에서 후행 보충 후보 12행을 제외해 150행을 확정하고, 파일 내부 5-word 반복 2종을 직접 재서술한 뒤 포장·전수 감사 PASS. source SHA `9a1bde93…a7ba605`, corpus SHA `23431d01…a95f2bf`
- 신규 v21 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/41/82/150/25/46/41/26/77/56/56/0`; cardinality 4개 150 records, 고유 relation-set 52종
- 신규 v21 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,657·0/155,606 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 43.000000(+EOS) PASS
- 직접 작성 경로의 스물한 번째 대상 `S2-A01-T-022`, `stage2_(11)causal_structure_high_density_train_v22.json`, ID `S2-CSH-03151~S2-CSH-03300`은 150행을 직접 작성해 최초 source gate와 포장·전수 감사를 수정 없이 PASS. source SHA `2b9d504d…6a118`, corpus SHA `8169c71c…9819c`
- 신규 v22 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/25/82/150/34/54/26/44/72/61/52/0`; cardinality 4개 150 records, 고유 relation-set 52종
- 신규 v22 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,624·0/158,230 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 43.380000(+EOS) PASS
- 직접 작성 경로의 스물두 번째 대상 `S2-A01-T-023`, `stage2_(11)causal_structure_high_density_train_v23.json`, ID `S2-CSH-03301~S2-CSH-03450`은 150행을 직접 작성해 최초 source gate와 포장·전수 감사를 수정 없이 PASS. source SHA `a21165fc…919750`, corpus SHA `9b586ddd…d577ee`
- 신규 v23 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/19/50/150/38/63/36/44/102/61/37/0`; cardinality 4개 150 records, 고유 relation-set 46종
- 신규 v23 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,572·0/160,802 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 44.500000(+EOS) PASS
- 직접 작성 경로의 스물세 번째 대상 `S2-A01-T-024`, `stage2_(11)causal_structure_high_density_train_v24.json`, ID `S2-CSH-03451~S2-CSH-03600`은 150행을 직접 작성해 최초 source gate와 포장·전수 감사를 수정 없이 PASS. source SHA `78dc0d16…bf185`, corpus SHA `a6f338dd…90e82`
- 신규 v24 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/21/70/150/19/132/28/33/56/44/47/0`; cardinality 4개 150 records, 고유 relation-set 37종
- 신규 v24 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,304·0/163,106 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 42.906667(+EOS) PASS
- 직접 작성 경로의 스물네 번째 대상 `S2-A01-T-025`, `stage2_(11)causal_structure_high_density_train_v25.json`, ID `S2-CSH-03601~S2-CSH-03750`은 148행 source gate 실패 뒤 누락 의미축 2개를 직접 보충하고 내부 5-word 반복 1종을 직접 수정해 PASS. source SHA `cd8b9664…e15ab`, corpus SHA `0c6beecd…8cdc9`
- 신규 v25 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/56/74/150/20/95/34/27/49/49/46/0`; cardinality 4개 150 records, 고유 relation-set 56종
- 신규 v25 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,289·0/165,395 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 44.340000(+EOS) PASS
- 직접 작성 경로의 스물다섯 번째 대상 `S2-A01-T-026`, `stage2_(11)causal_structure_high_density_train_v26.json`, ID `S2-CSH-03751~S2-CSH-03900`은 156개 직접 후보 중 중심성이 낮거나 중복 성격인 6개를 제외하고 primary literal 1건과 어색한 primary 1건을 직접 수정해 PASS. source SHA `fcf4c91f…3c8b2`, corpus SHA `b117d594…31eaa`
- 신규 v26 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/36/76/150/34/53/41/31/81/43/55/0`; cardinality 4개 150 records, 고유 relation-set 53종
- 신규 v26 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,552·0/167,947 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 44.480000(+EOS) PASS
- 직접 작성 경로의 스물여섯 번째 대상 `S2-A01-T-027`, `stage2_(11)causal_structure_high_density_train_v27.json`, ID `S2-CSH-03901~S2-CSH-04050`은 초기 token 평균 46.906667을 두 차례 직접 압축해 상한 안으로 낮추고 v07 교차 5-word 반복 1종을 직접 수정해 PASS. source SHA `b2ed6637…fabc12`, corpus SHA `d5f90113…d6e7a`
- 신규 v27 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/42/142/150/54/82/21/19/38/24/28/0`; cardinality 4개 150 records, 고유 relation-set 32종
- 신규 v27 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,441·0/170,388 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 45.500000(+EOS) PASS
- 직접 작성 경로의 스물일곱 번째 대상 `S2-A01-T-028`, `stage2_(11)causal_structure_high_density_train_v28.json`, ID `S2-CSH-04051~S2-CSH-04200`은 최초 148행을 의미축 2개로 보충하고 token 평균 46.973333을 두 차례 직접 압축해 PASS. source SHA `161a0502…95fcb`, corpus SHA `42ff611c…e5de`
- 신규 v28 relations 597회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/23/71/150/42/37/46/23/142/37/26/0`; cardinality 3개 3 records, 4개 147 records, 고유 relation-set 34종
- 신규 v28 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,392·0/172,780 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 45.486667(+EOS) PASS
- 직접 작성 경로의 스물여덟 번째 대상 `S2-A01-T-029`, `stage2_(11)causal_structure_high_density_train_v29.json`, ID `S2-CSH-04201~S2-CSH-04350`은 최초 148행을 의미축 2개로 보충하고, package 후 v12 교차 5-word 반복 2종을 직접 재서술해 PASS. source SHA `129694b8…6e335`, corpus SHA `1cf68c12…dc47e`
- 신규 v29 relations 587회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/5/65/150/34/101/27/33/89/43/40/0`; cardinality 3개 13 records, 4개 137 records, 고유 relation-set 45종
- 신규 v29 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,279·0/175,059 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 41.706667(+EOS) PASS
- 직접 작성 경로의 스물아홉 번째 대상 `S2-A01-T-030`, `stage2_(11)causal_structure_high_density_train_v30.json`, ID `S2-CSH-04351~S2-CSH-04500`은 최초 148행을 의미축 2개로 보충한 뒤 source·package·전수 감사를 PASS. source SHA `71fe37bd…1f950`, corpus SHA `08dafd39…a10b7`
- 신규 v30 relations 569회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/31/92/150/51/73/39/15/72/15/31/0`; cardinality 3개 31 records, 4개 119 records, 고유 relation-set 48종
- 신규 v30 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,099·0/177,158 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 40.800000(+EOS) PASS
- 직접 작성 경로의 서른 번째 대상 `S2-A01-T-031`, `stage2_(11)causal_structure_high_density_train_v31.json`, ID `S2-CSH-04501~S2-CSH-04650`은 최초 147행을 의미축 3개로 보충한 뒤 source·package·전수 감사를 PASS. source SHA `d4295506…84df09`, corpus SHA `2157d1de…17b54f`
- 신규 v31 relations 587회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/29/90/150/37/44/61/24/74/52/26/0`; cardinality 3개 13 records, 4개 137 records, 고유 relation-set 54종
- 신규 v31 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/1,882·0/179,040 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 38.340000(+EOS) PASS
- 직접 작성 경로의 서른한 번째 대상 `S2-A01-T-032`, `stage2_(11)causal_structure_high_density_train_v32.json`, ID `S2-CSH-04651~S2-CSH-04800`은 최초 평균 49.173333의 token 상한 초과를 두 차례 직접 압축한 뒤 source·package·전수 감사를 PASS. source SHA `09c65399…d5dc9d4`, corpus SHA `1513b3e1…20de6`
- 신규 v32 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/18/90/150/54/57/40/32/63/58/38/0`; cardinality 4개 150 records, 고유 relation-set 52종
- 신규 v32 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,333·0/181,373 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 45.700000(+EOS) PASS
- 직접 작성 경로의 서른두 번째 대상 `S2-A01-T-033`, `stage2_(11)causal_structure_high_density_train_v33.json`, ID `S2-CSH-04801~S2-CSH-04950`은 최초 primary literal 누락 1건을 직접 고친 뒤 source·package·전수 감사를 PASS. source SHA `f6a963ae…5c800f2`, corpus SHA `52733734…eb7ecd`
- 신규 v33 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/28/94/112/38/51/57/29/132/50/9/0`; cardinality 4개 150 records, 고유 relation-set 43종
- 신규 v33 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,014·0/183,387 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 39.073333(+EOS) PASS
- 직접 작성 경로의 서른세 번째 대상 `S2-A01-T-034`, `stage2_(11)causal_structure_high_density_train_v34.json`, ID `S2-CSH-04951~S2-CSH-05100`은 150행을 직접 작성해 최초 source gate와 포장·전수 감사를 수정 없이 PASS. source SHA `33d384b7…a8acf79`, corpus SHA `20cf2f5f…3dfcec`
- 신규 v34 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/27/80/120/22/88/60/12/94/37/60/0`; cardinality 4개 150 records, 고유 relation-set 56종
- 신규 v34 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,604·0/185,991 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 41.953333(+EOS) PASS
- 직접 작성 경로의 서른네 번째 대상 `S2-A01-T-035`, `stage2_(11)causal_structure_high_density_train_v35.json`, ID `S2-CSH-05101~S2-CSH-05250`은 150행 직접 작성 뒤 v20 교차 5-word 반복 1종을 직접 재서술해 source·package·전수 감사를 PASS. source SHA `7f7e39ec…f8a45d`, corpus SHA `41165afb…a5aeb8`
- 신규 v35 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/63/88/119/42/73/74/15/51/30/45/0`; cardinality 4개 150 records, 고유 relation-set 63종
- 신규 v35 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,630·0/188,621 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 43.986667(+EOS) PASS
- 직접 작성 경로의 서른다섯 번째 대상 `S2-A01-T-036`, `stage2_(11)causal_structure_high_density_train_v36.json`, ID `S2-CSH-05251~S2-CSH-05400`은 150행을 직접 작성해 최초 source gate와 포장·전수 감사를 수정 없이 PASS. source SHA `d14f5296…28497f`, corpus SHA `a4488274…e5a044`
- 신규 v36 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/59/83/131/38/33/56/7/109/33/51/0`; cardinality 4개 150 records, 고유 relation-set 47종
- 신규 v36 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,594·0/191,215 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 44.840000(+EOS) PASS
- 직접 작성 경로의 서른여섯 번째 대상 `S2-A01-T-037`, `stage2_(11)causal_structure_high_density_train_v37.json`, ID `S2-CSH-05401~S2-CSH-05550`은 source-only 누적 감사가 잡은 파일 내부 5-word 반복 1종과 기존 v07·v34 교차 반복 2종을 직접 재서술한 뒤 포장·전수 감사를 PASS. source SHA `be00d8b2…0e7169`, corpus SHA `83f057da…d180d2`
- 신규 v37 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/46/107/145/29/52/45/19/66/23/68/0`; cardinality 4개 150 records, 고유 relation-set 48종
- 신규 v37 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,756·0/193,971 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 45.306667(+EOS) PASS
- 직접 작성 경로의 서른일곱 번째 대상 `S2-A01-T-038`, `stage2_(11)causal_structure_high_density_train_v38.json`, ID `S2-CSH-05551~S2-CSH-05700`은 최초 token 평균 51.013333을 두 차례 직접 압축하고, 파일 내부·v07 교차 5-word 반복 각 1종을 직접 재서술해 전수 감사 PASS. source SHA `b0666c45…1f28b8`, corpus SHA `99ead223…dddf1`
- 신규 v38 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/37/65/86/42/58/63/67/122/26/34/0`; cardinality 4개 150 records, 고유 relation-set 74종
- 신규 v38 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,601·0/196,572 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 45.733333(+EOS) PASS
- 직접 작성 경로의 서른여덟 번째 대상 `S2-A01-T-039`, `stage2_(11)causal_structure_high_density_train_v39.json`, ID `S2-CSH-05701~S2-CSH-05850`은 일시중단 전 98행을 보존하고 재개 승인 뒤 52행을 직접 보충해 source·package·전수 감사를 수정 없이 PASS. source SHA `27d8e23d…57e52f`, corpus SHA `94999456…d137e6`
- 신규 v39 relations 600회: `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/7/54/85/30/127/56/28/129/29/55/0`; cardinality 4개 150 records, 고유 relation-set 44종
- 신규 v39 final exact·normalized duplicate 0, 파일 내부 및 누적 5-word n-gram 반복 0/2,504·0/199,076 assignments, 내부·기존 Stage2 train 교차 character similarity ≥0.80 및 word Jaccard ≥0.60 모두 0 pair, exact tokenizer 평균 43.653333(+EOS) PASS
- 현행 74쌍·11,100 records 통합 감사: artifact·중복·train/validation exact leakage·cross-record 5-word n-gram·hard grammar·manual-review debt 모두 0, 5-word assignments 199,076, Stage2 누적 평균 43.078889(+EOS) PASS
- 현재 자동 초안의 `manual_semantic_review=false`는 구조 PASS와 정본 의미 PASS를 분리하는 필수 표식이며, 한 건이라도 남으면 canonical publish를 차단한다.

도구 preflight 상세는 `tools/stage2_10_tool_preflight_report_2026-09-02.md`(SHA-256 `4d94813218c68c0541d356109be52d39b6e72388cd9aef515060b05152cc43ce`)에 보존했다. 실행 예시는 `tools/README_stage2_10_corpus_engine.md`에 있으며, read-only pilot 감사는 기본 partial mode인 `--check-only --json`을 사용한다. 새 Python 도구는 저장소의 `*.py` ignore 규칙 때문에 commit 대상으로 삼을 때 `git add -f`가 필요하다.

전체 체크포인트 판정은 `audit_reports/TinyLM_Stage2_10_Actual3M_Authorized_Checkpoint_Audit_2026-09-02.md`와 기계 부속 `audit_reports/machine/TinyLM_Stage2_10_Actual3M_Authorized_Checkpoint_Audit_2026-09-02.json`에 보존한다.

일시중단 재개점 `S2-A01-T-039`은 사용자 승인 뒤 99번째 원고부터 52행을 직접 보충해 확정했다. source/corpus/checkpoint가 모두 존재하고 source SHA-256은 `27d8e23d5e4cd82b66d5907bd223ba7c43f4e605cfa10fc6bb99f7ae6b57e52f`, corpus SHA-256은 `949994562255517567f4475500241075e138db70ac4fb7f6933c1344d5d137e6`이다.

교육영역 일괄 작성으로 전환한 뒤 Stage2 A01 `S2-A01-T-040~050` source 11개·1,650행을 직접 작성했다. 열한 source 모두 parse·행 수 150·primary/text 고유 150/150·통제 relations·record당 2~5개·record 내부 관계 중복 금지·primary literal 최소 계약 오류 0이다. source SHA-256은 v40~v45가 `e0f3edfeebf9f7d19027fa301368ff47ab206a20f8b521cb860fbb6871843639`, `508a1f0b96389ca59a1a24e54559c0a7862fa0f7d075ff8fadb8180f5a8ba62b`, `066119ab81894323fbca8f82ef8f2325edc425bba93b2f282f7037e16fb8e437`, `1ce55695d452e2da7e3f45ad3c1b00469f1b7094e41861268170fe8a782df0ba`, `45eb19c7246aa63dd73e4d71320fdd83af500a185709d5047469b2d01b887932`, `0d9e23c53900488f73f3fc4c3142fa739c98145715b4d4728d4428b54fd9b9d5`, v46~v48이 `43fc6f60257b8d8fce30cc427a2a0458a18a0b71d65c5404b55b8c2add7d0eb5`, `3836f96d5cf05fd7b3308d2f080dc161a9f1d4102eb3e93dbca066e1615b7566`, `7e14ff53c3b3d407be961402a580afac6e1b3be880acd6038f967af85cd065a8`, v49~v50이 `fe82fa73241e8d79a4c21365db31b1f7e49f5655a18154cb3fda284042733fcf`, `f70afd38433fa6a4f5997b91b59429e799faccecfec68cfad47e8354a73ed1b2`다. 전환 직전 v40 예비 감사에서 확인한 tokenizer 평균 46.893333(+EOS)의 파일 gate 초과는 개별 수정하지 않고 Stage2 A01 전체 종료 batch 수정 목록에 보존했다.

사용자 일시중단 시점의 `S2-A01-T-051`, `stage2_(11)causal_structure_high_density_train_v51.json`, ID `S2-CSH-07501~S2-CSH-07650`, family `반도체 클린룸 오염·수율 관리 — 매개 단계와 직접 효과의 경로 판정` source 50행을 보존하고 51~150번째 100행을 직접 보충했다. 완성 source는 parse 오류 0, primary/text 고유 150/150, 통제 밖 relation 0, cardinality·내부 중복·primary literal 최소 계약 오류 0이며 SHA-256은 `11adf713d54a596d352f4487cd23b710adfc2d1faad37719e1311bef5be703c6`이다. corpus·checkpoint entry는 없고 영역 batch 감사도 시작하지 않았다.

이어 `S2-A01-T-052~054` source 3개·450행을 직접 작성했다. 각 파일은 parse·150행·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류 0이다. source SHA-256은 v52 `7958d7d2492c8aab60fddad530d2313689e76929562584d7134ba53454b59897`, v53 `47e11138d8c69c5d4a41b5644cf1704b828eb5043b0c31ae2b34b6d410356dc2`, v54 `c632fdcc21407e949e6ebfdccae13540363e6cc16b0fc97178ab37c10c48053f`다. v54는 최초 149행에서 누락 한 행을 직접 보충했다. 다음은 `S2-A01-T-055`, `stage2_(11)causal_structure_high_density_train_v55.json`, ID `S2-CSH-08101~S2-CSH-08250`, family `산림 병해충 예찰·방제 — 개입 변수와 자연 변동의 인과 효과 분리`의 1행부터다.

이어 `S2-A01-T-055~057` source 3개·450행을 직접 작성했다. 각 파일은 parse·150행·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류 0이다. source SHA-256은 v55 `c42f30c7be0a8b4b2173d955b65a253e77a9e64bee01b1cec3f6bdbdfdf7d01f`, v56 `ca259750951b5b200172825c31196556b8b103af1537ffd4772a2a199de08eea`, v57 `6dae0baccb7ebecd49b00c5402257dd96c99c2e0f997be79877f48613c92ccfa`다. 다음은 `S2-A01-T-058`, `stage2_(11)causal_structure_high_density_train_v58.json`, ID `S2-CSH-08551~S2-CSH-08700`, family `데이터센터 냉각·전력 절체 — 시간 역전 가능성을 배제한 원인 방향 확인`의 1행부터다.

이어 `S2-A01-T-058~060` source 3개·450행을 직접 작성했다. v58은 중단 요약과 달리 실파일이 50행임을 재확인한 뒤 기존 50행을 보존하고 100행을 보충했으며, v60은 primary literal 누락 2건을 직접 고쳐 재검사했다. 세 파일은 최종적으로 parse·150행·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v58 `077b32e1099624d45a6a73a817b8988e05eaa1e81c976c114bea91f60a36d724`, v59 `d987020fc02e9498f651aa2ccf56aa70fa5690fcf8e91ff38763078c86804d92`, v60 `7d3e66a371a8a24a2c197dde23da81d4a8c0c92cdeb9c74772a1a1de1e97b509`다. 다음은 `S2-A01-T-061`, `stage2_(11)causal_structure_high_density_train_v61.json`, ID `S2-CSH-09001~S2-CSH-09150`, family `도로 터널 배수·교통 통제 — 매개 단계와 직접 효과의 경로 판정`의 1행부터다.

이어 `S2-A01-T-061~063` source 3개·450행을 직접 작성했다. v61은 최초 149행에서 1행을, v63은 최초 148행에서 2행을 직접 보충했고, v62는 최초 151행에서 의미 축 주변부 1행을 제거해 정확히 150행으로 맞췄다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v61 `cc8dc796e77144514ec1709fea3404057593aa8572681f42b7e35a8a219b5f2c`, v62 `d06564e79c83f86462b28cf54eb5983e18eac33f6dbdf4ae0bc928969f229990`, v63 `74475c90f2ce75bc136c4db65102d92ce014b7da2883335fb736f12a03e2e555`다. 다음은 `S2-A01-T-064`, `stage2_(11)causal_structure_high_density_train_v64.json`, ID `S2-CSH-09451~S2-CSH-09600`, family `도시 열공급망 부하·압력 조정 — 복수 원인의 결합 충분성과 기여 한계`의 1행부터다.

이어 `S2-A01-T-064~066` source 3개·450행을 직접 작성했다. v64의 명백한 중복어 오탈자를 직접 고치고 최초 149행에 1행을 보충했으며, v65의 최초 148행에는 2행을 보충했다. v66은 최초 검사에서 바로 150행 계약을 통과했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v64 `bcf6c8833a07d38c8103280526e1f8f6e2ae4ea63e08ea698ff1b9d5b9a93afe`, v65 `9f8ccbeb0b56fcb5f0673a3f796e22946e0317ec212ad217ff8035f939e0e90d`, v66 `89926e81e0f33375ae0b2192af6006e368dcbf164def6afb979aa5ead8aa1967`이다. 다음은 `S2-A01-T-067`, `stage2_(11)causal_structure_high_density_train_v67.json`, ID `S2-CSH-09901~S2-CSH-10050`, family `산림 병해충 예찰·방제 — 공통 원인 통제 전후 상관 변화 해석`의 1행부터다.

이어 `S2-A01-T-067~069` source 3개·450행을 직접 작성했다. 중단 당시 v67의 실제 50행을 보존하고 100행을 보충했으며, v69의 최초 149행에는 대안경로 판정 1행을 보충했다. v68은 최초 완성 검사에서 바로 150행 계약을 통과했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v67 `4eb624f380d3d3e4feeff3c67872598b1c17d3128eeacf7b4e4ee8a2e4e6e56f`, v68 `f8b1783be1ccf840591dab52aa63de4bbe72e58d9a5c8d4432eb32b88e2f6b7d`, v69 `2cce640aa476ee5ea1d608233c318788f33c7a5c42707e13cdcbab07d0bb2f47`이다. 다음은 `S2-A01-T-070`, `stage2_(11)causal_structure_high_density_train_v70.json`, ID `S2-CSH-10351~S2-CSH-10500`, family `데이터센터 냉각·전력 절체 — 개입 변수와 자연 변동의 인과 효과 분리`의 1행부터다.

이어 `S2-A01-T-070~072` source 3개·450행을 직접 작성했다. v70은 최초 완성 검사에서 150행 계약을 통과했고, v71은 최초 149행에 매개효과의 실무중요성 판정 1행을, v72는 최초 148행에 통제 후 무상관 및 작은 효과의 해석 2행을 직접 보충했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v70 `9fd8494a3ba227333945cb0d545cc1c43312d60715640272ff167c6a5f28187e`, v71 `e9aa344d0edb59c1e456ee5dfd0691d4c084889832e53fb1b10ce6e617181450`, v72 `7325958532f38f54c61337ca6fd9830ce060c09af83e0db69f6e675319462696`이다. 다음은 `S2-A01-T-073`, `stage2_(11)causal_structure_high_density_train_v73.json`, ID `S2-CSH-10801~S2-CSH-10950`, family `도로 터널 배수·교통 통제 — 시간 역전 가능성을 배제한 원인 방향 확인`의 1행부터다.

이어 `S2-A01-T-073~075` source 3개·450행을 직접 작성했다. v73은 최초 148행에 2행, v74는 최초 149행에 1행을 직접 보충했고 v75는 최초 완성 검사에서 바로 150행 계약을 통과했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v73 `c7b3264c16b16d0efb1cfae9b83551c4aec053bd8afc4c801d11d8131ff42a1f`, v74 `ef742bb8e569c0187984c04ee617384cdd09fbe2952714b0a4a5f7ed381c49a5`, v75 `3f4c2eae9d68011fe07b1103b74cf117f9589ab2d40500ef1507feafb131a9ce`이다. 다음은 `S2-A01-T-076`, `stage2_(11)causal_structure_high_density_train_v76.json`, ID `S2-CSH-11251~S2-CSH-11400`, family `도시 열공급망 부하·압력 조정 — 매개 단계와 직접 효과의 경로 판정`의 1행부터다.

이어 `S2-A01-T-076~078` source 3개·450행을 직접 작성했다. v76은 중단 당시 실제 50행을 보존하고 100행을 보충했으며, 최초 최소 검사에서 중단 전 27번째 primary literal 불일치 1건을 검출해 의미를 보존한 문장으로 직접 수정했다. v77은 최초 149행에 1행, v78은 최초 99행 뒤 51행을 직접 보충했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v76 `0a4927c565a67edecd1ad0f1e280b37141511c2cfebdacbcf89a77997ec4d36a`, v77 `d5927ee4b4b8c3ef69cd121d56c6a1486f13b09ac0b581efa138f2d625e63e8d`, v78 `cccbf34f5a034a73c4c4f19e179f56ba3156883597d8d0c1964ecff0eb900962`이다. 다음은 `S2-A01-T-079`, `stage2_(11)causal_structure_high_density_train_v79.json`, ID `S2-CSH-11701~S2-CSH-11850`, family `산림 병해충 예찰·방제 — 복수 원인의 결합 충분성과 기여 한계`의 1행부터다.

이어 `S2-A01-T-079~081` source 3개·450행을 직접 작성했다. v79는 두 번째 묶음까지 101행을 작성해 남은 49행으로 정확히 닫았고, v80은 50→99→150행, v81은 50→100→150행 순으로 완결했다. v81 작성 중 발견한 명백한 `않고 않고` 중복어 1건은 즉시 직접 수정했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v79 `2672a224ee01b1e7ba759dcb206036db4d963e7be246bc23255587c9db6d2d05`, v80 `6cd52003657a33fd1415b0d54f10bb11bfade917255aba016ce38b98f214e9da`, v81 `bbc61d5b5a34473032680bee7971e09fe9614d807885fdc28a05a6725d444be2`이다. 다음은 `S2-A01-T-082`, `stage2_(11)causal_structure_high_density_train_v82.json`, ID `S2-CSH-12151~S2-CSH-12300`, family `데이터센터 냉각·전력 절체 — 공통 원인 통제 전후 상관 변화 해석`의 1행부터다.

이어 `S2-A01-T-082~084` source 3개·450행을 직접 작성했다. v82는 50→99→147→150행, v83은 50→100→150행, v84는 50→100→150행 순으로 완결했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v82 `8e6170463576998a3aba27f4da7df8c4f92c1427bd99b35ad967ff183600e08d`, v83 `f77d0e6381bfb56d0ecb9a049b0cab3736b63601f2065e3b747af889b0440330`, v84 `1b61a8711760e34dabe9ea1223bd591ca8fe8b38b1799e8f21d0e27a17b46d70`이다. 다음은 `S2-A01-T-085`, `stage2_(11)causal_structure_high_density_train_v85.json`, ID `S2-CSH-12601~S2-CSH-12750`, family `도로 터널 배수·교통 통제 — 개입 변수와 자연 변동의 인과 효과 분리`의 1행부터다.

이어 `S2-A01-T-085~087` source 3개·450행을 직접 작성해 Stage2 A01 예약 source를 모두 완성했다. v85는 최초 173행 초안에서 의미축에 충분한 선행 150행만 남겨 정확히 닫았고, v86은 50→100→150행, v87은 50→99→150행으로 완결했다. 최종 세 파일은 parse·행 수·primary/text 150/150 고유·통제 relations·cardinality·내부 relation 중복 금지·primary literal 최소 계약 오류가 모두 0이다. source SHA-256은 v85 `6d7e9a2e2903951d947f437855f9f12bd1cefd077028e2a747b2b3b368a944be`, v86 `db211804ab8306046d33989a367e94ce508a3ed3752a006f5e6e82859247929f`, v87 `0ea5ceff7cd606088df70aeb7777509f4feb28dbde6005d8245f9720b67d3352`이다. 다음 재개점은 v40~v87 source 48개·7,200행의 영역 batch 감사이며, 통과 전에는 corpus·checkpoint를 만들거나 완료 통계를 올리지 않는다.

2026-09-03 A01 영역 batch 감사를 시작했다. 최초 감사에서 `other`를 포함한 276행의 `other_type` 누락, primary 계열 중복 후행 14행, hard 조사 불일치 1행을 찾았다. 276행에는 의미에 맞춰 `other_type`을 직접 부여하고, 중복 후행 14행의 primary/text를 직접 재서술했으며, `지표이면` 1건을 `지표라면`으로 고쳤다. 수정 후 read-only 전수 감사에서 13,050행의 source 구조 오류, exact/normalized/primary+relation-set 중복, hard 조사 오류는 모두 0이고 Stage2 전체 tokenizer 평균 44.582299(+EOS)은 허용범위 PASS다.

다만 이것은 A01 최종 PASS가 아니다. cross-record 5-word 반복 666종·초과 record assignment 737건이 남았고, 이를 해소하기 위한 직접 재서술 대상은 현재 greedy 기준 293행이다. 파일별 token gate 재검사·fuzzy similarity·조사 warning 979건의 사람 검토도 아직 끝나지 않았다. 특히 v40의 예비 평균 46.893333(+EOS) 초과는 계속 수정 대기다. 따라서 v40~v87 corpus 포장과 checkpoint 등록은 수행하지 않았다.

중단 시점 v40~v87 source-only relations 분포는 `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/4/1,010/1,956/6,039/830/2,449/1,496/749/4,707/1,836/1,996/276`이다. `other_type` 상위 5개는 `식별·인과해석 한계 136`, `미측정 교란·대안경로 59`, `선택·조건화 편향 34`, `불확실성·적용범위 30`, `측정·기록 한계 17`이다. 이는 최종 보고값이 아니라 중단 checkpoint 값이다.

감사 보정으로 v51~v87의 작성 직후 SHA 기록은 역사값이 됐다. 재개 시 개별 해시는 최종 재감사 뒤 다시 산출한다. 현재 v40~v87 파일명을 정렬하고 각 파일 SHA-256을 `파일명=해시` UTF-8 행으로 연결해 SHA-256한 source-set digest는 `195e93127931c040a30109e1a82b8d374da024b21d34252868204cf02f5f89a5`다. 사용자 요청에 따라 이 지점에서 작업을 일시중단하며, 재개 순서는 **5-word 직접 재서술 → 파일별 token 보정 → fuzzy·조사 검토 → 전면 재감사 → PASS일 때만 일괄 포장**이다.

semantic-composition 초안의 canonical 승격은 여전히 승인되지 않았다. 이 경로를 쓰려면 Guide §10 예외를 별도로 명시해야 하며, 현재 직접 작성 착수를 예외 승인으로 해석하지 않는다. 기존 pilot·Stage1 보호 corpus·저밀도·held-out 수정 권한도 확대되지 않는다.
