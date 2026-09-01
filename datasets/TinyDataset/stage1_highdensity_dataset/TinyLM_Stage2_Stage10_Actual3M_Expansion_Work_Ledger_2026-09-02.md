# TinyLM Stage2~10 실측 3M 증보 작업원장 — 2026-09-02

- 문서 상태: `DESIGN_UPDATE_COMPLETE_CORPUS_AUTHORIZATION_PENDING`
- 기준 시각: 2026-09-02 KST
- 목적: 컨텍스트 압축·세션 중단 뒤에도 승인 범위, 수치, 미완료 항목과 재개점을 잃지 않게 하는 단일 작업원장
- corpus 생성 권한: **없음**. 이번 작업은 설계 Markdown과 본 작업원장만 갱신한다.

## 1. 사용자 승인과 금지 경계

2026-09-02 사용자는 Stage2~10의 **실제 `tok-ko-en-32768.json` 기준 Stage별 약 3M-token안**을 승인했다. 동시에 다음 순서를 지정했다.

1. Stage별·세부영역별 필요한 concept/topic family 증보량을 검토한다.
2. 설계서와 작업원장만 갱신한다.
3. corpus·canonical source·builder 실행·중앙 family JSON revision·Stage manifest revision은 하지 않는다.
4. 문서 감사 결과를 보고하고 corpus 생성 허가를 다시 요청한다.
5. 사용자가 명시적으로 승인한 뒤에만 실제 생성에 착수한다.

이 원장은 위 권한을 넓히지 않는다. 저밀도, held-out/evaluation, Stage1 수정 금지 corpus와 legacy `stage2_(2)attribute_high_density_*`는 계속 열람·해시 대조 외 수정하지 않는다.

## 2. 정본과 시작 해시

| 파일 | 작업 시작 SHA-256 | 이번 작업 지위 |
|---|---|---|
| `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md` | `98272f9bcb1bedc3c10467952bb4286a70b89686c4c22cd6ae4accd4f652f26f` | 갱신 허용 |
| `TinyLM_Stage2_Stage10_Curriculum_and_Family_Reservation_Draft.md` | `221eff53b8f8482d34d62e5ba2bad8dc8c593f9db193ce4cdc99dff3516ec8b0` | 갱신 허용 |
| `TinyLM_Stage2_Stage10_Concept_Family_Reservation.json` | `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99` | 변경 금지; 현행 250+25/Stage snapshot |
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

> 주의: Stage별 `PREPARATION_MANIFEST.json`은 2026-09-01 준비 snapshot이다. 이번에는 갱신하지 않으며 `PREPARED_NO_CORPUS_GENERATED`를 현행 상태로 해석하지 않는다.

## 3. 승인된 Stage별 총량

모든 파일은 150 records이며 Stage별 train/validation 파일 수는 정확히 90:10이다. 아래 총량은 기존 pilot 4 files/Stage를 포함한다.

| Stage | 승인 총 files | train/val | records | pilot 평균 token/record(+EOS) | 투영 tokens | primary 250 대비 증보 | contingency 25 이후 신규 family | pilot 제외 생성 대기 |
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

`primary 대비 증보`는 승인 총 files에서 현행 primary 250을 뺀 값이다. `contingency 이후 신규 family`는 Stage별 비활성 contingency 25개를 모두 적합하게 재검토·활성화할 수 있다고 가정한 최소 신규 선정량이다. contingency에는 아직 area·split·ID·version·filename이 없으므로 25개를 자동 배분하지 않는다.

## 4. 세부영역 증보 계산 규칙

- 20/20/16/16/16/12% 교육 비율, Stage별 승인 총 files, train/validation 90:10과 150-record 정수 단위를 함께 만족하도록 allocation 정본의 largest-remainder 결과를 사용한다.
- 현행 primary 기준은 A01~A06 각각 총 50/50/40/40/40/30 files다.
- `세부영역 증보 T/V = 승인 T/V - 현행 primary T/V`다.
- pilot 완료는 A01 train+val 각 1, A03 train 1, A06 train 1이다. `생성 대기 = 승인 총량 - pilot 완료`다.
- 증보 version 범위는 충돌 방지용 **계획 범위**다. 사용자 corpus 생성 승인과 중앙 원장 revision 전에는 실제 filename·ID·family 이름으로 활성화하지 않는다.
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

### 5.3 corpus 승인 전 필수 gate

1. 모든 record의 `type`이 예약된 Stage·area packet type과 정확히 일치한다.
2. `relations`는 문장에 직접 근거가 있는 13개 중 2~5개만 사용한다.
3. Stage나 area마다 13개 전부를 채우거나 빈도를 균등화하지 않는다.
4. `other`는 고차 능력 label의 대용품이 아니며 대표 concept과 의미 유형을 계속 보고한다.
5. 실파일 확인 결과 Stage5·6·7의 `tools/build_pilot.py`와 Stage5의 `tools/audit_pilot.py`가 `relations ⊆ relation_focus`를 강제한다. 전체 생성 전에 이를 13개 통제 어휘·2~5개·text 의미 일치 검사로 교체·재감사한다. 이번 문서 작업에서는 builder를 수정하거나 실행하지 않는다.
6. downstream 평가에서는 13개 relation별 결과와 54개 `type`별 결과를 분리 보고한다.

새 `capability` 필드는 현재 `type`과 중복되므로 추가하지 않는 안을 권고한다. 향후 loader가 `type`을 보존하지 않는 사실이 확인될 때만 별도 schema 변경안을 사용자 승인 대상으로 올린다.

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
| 9 | corpus 생성 | **승인 대기** | 사용자 재승인 전 금지 |

## 7. 문서 전용 최종 감사

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
| 현행 Stage2~10 corpus/source 수 | 36/36, 기존 pilot만 존재 |
| stale pre-pilot 문구 | curriculum·9 README에서 0 |
| `git diff --check` | PASS |

### 7.2 갱신 문서 최종 SHA-256

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

- 비활성 contingency 225개의 54개 area·train/validation 배치
- 신규 family 1,895개의 정확한 이름·도메인·semantic axis
- 중앙 family ledger와 9개 manifest의 revision schema 및 새 SHA
- 승인된 version 계획 범위에 실제 family·filename·ID range를 결합하는 순서
- corpus 생성 시작 Stage와 동시/순차 진행 단위

문서 감사 PASS 후 위 항목은 **설계상 필요하지만 아직 활성화되지 않은 예약 작업**으로 남긴다. 사용자에게 corpus 생성 허가를 요청하되, 승인 전에는 어떤 corpus나 source도 만들지 않는다.
