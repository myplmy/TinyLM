# TinyLM Stage 1 Function train v01 중단 복구·착수·확정 감사 보고서

- 기준일: 2026-08-30
- 작업 루트: `Z:\TinyLM\datasets\TinyDataset`
- 대상 영역: Stage 1 `(3) function` 기능·용도·목적 train
- 설계 목표: 4,050 records, 27 files × 150 records, 약 324K tokens 환산
- 이번 확정 범위: v01 150 records

## 1. 결론

PC 중단 뒤 실제 파일부터 다시 확인해 중복 생성 여부와 누락 범위를 판정했다. 중단 직후 정본 경로에는 `stage1_(3)function_high_density_train_v*.json`이 없었으므로 v01은 기존 파일을 덮어쓴 작업이 아니다. 지침서에 27개 concept family와 ID 범위를 미리 예약했고, v01 `S1-FNH-0001~0150`을 직접 작성한 뒤 JSON·관계·중복·문장 유사도·조사·저밀도 prototype 분리 감사를 통과시켜 확정했다.

현재 누적은 **150 / 4,050 records, 1 / 27 files**이며 잔여는 **3,900 records, 26 files**다. 다음 작성 대상은 예약표의 v02 `식재료 준비·조리·제공 기구의 기능`, ID `S1-FNH-0151~0300`이다.

## 2. 중단 전후 작업 구분

### 2.1 중단 직후 실제로 남아 있던 상태

- 생성 지침서에는 `(3) function` 영역명, 파일명 예, `S1-FNH` ID, train record 기본 형식 일부가 반영되어 있었다.
- 정본 `stage1_highdensity_dataset/train`에는 Function 고밀도 train 파일이 0개였다.
- `stage2_(2)attribute_high_density_*` 이름과 일치하는 실제 파일은 현재 workspace에서 0개였다.
- identity 45개와 attribute 35개, 합계 80개 수정 금지 파일의 SHA-256 기준점을 먼저 저장했다.
- repository 밖 상대 경로의 기존 `test_result` log 5개는 이 작업과 무관한 사용자 산출물로 판정해 수정·정리하지 않았다.

### 2.2 재개 후 완료한 작업

1. 지침서의 수정 금지 규칙에 `stage2_(2)attribute_high_density_*` 패턴을 추가했다. 실제 파일이 현재 보이지 않아도 향후 발견 시 해시를 먼저 저장하고 읽기 전용으로 취급하도록 명시했다.
2. Function train 27개 버전의 concept family, 하위 기능 축, ID 범위를 예약 원장으로 고정했다.
3. v01의 primary concept 150개와 의미 `text` 150개를 literal로 직접 작성했다.
4. `build_function_train.py`는 직접 작성 literal의 ID·metadata·JSON 포장과 제약 검사만 수행하도록 만들었다.
5. `audit_function_corpus.py`로 구조·중복·유사도·조사·relations 분포와 저밀도 `S1-FUNC-*` 120개와의 분리를 감사했다.
6. 1차 포장 뒤 관계 의미를 수동 재감사했다. 전체 도구를 부품처럼 본 `part_of`, 실제 분류 문장이 없는 `classification/is_a/subclass_of`, 다른 관계로 충분히 설명되는 `other`를 보수적으로 제거·재배치했다.
7. 대조가 암시적이었던 `플러시컷톱`, `버니싱툴`, `부품회수집게` 문장은 비교 대상을 명시하도록 직접 보완했다.
8. 정본 루트 기준으로 다시 포장·재감사하고 수정 금지 80개 파일의 전후 SHA-256이 모두 같은지 확인했다.

재검증 도중 포장기의 기준 경로를 한 단계 잘못 전달해 `stage1_highdensity_dataset/stage1_highdensity_dataset/` 중첩 복제본이 일시 생성되었다. 경로와 파일 범위를 확인한 뒤 이번 작업에서 생성된 복제본만 영구 삭제했으며, 정본 파일은 아래 SHA-256으로 남아 있다. 삭제 대상은 정본과 별개인 재생성 가능한 중복 JSON 1개뿐이었다.

## 3. v01 확정 파일

| 항목 | 확정값 |
|---|---|
| 파일 | `train/stage1_(3)function_high_density_train_v01.json` |
| SHA-256 | `02b8974c56b7733b57c94f742c88a4bb170fc55c5ede83f76038e673620cb2e7` |
| concept family | 수동 작업·정비·제작 공구의 기능 |
| 하위 축 | 체결, 파지, 절단, 성형, 표면 마감, 타격, 인출, 천공, 나사 가공 |
| record 수 | 150 |
| ID 범위 | `S1-FNH-0001~S1-FNH-0150` |
| type / split | `function_packet` / `train` |
| primary concept | 150개, exact 중복 0 |
| text 문자 수 | 합계 8,731자, 최소 45자, 중앙값 56.5자, 평균 58.207자, 최대 92자 |
| 문장 수 | 1문장 121건, 2문장 29건 |

`약 324K tokens`는 4,050 records 전체에 대한 설계 환산량이다. v01 및 전체 corpus의 실제 token 수는 최종 tokenizer로 별도 계측하기 전까지 확정 token 수로 표현하지 않는다.

## 4. relations 의미 재감사

모든 record는 `function`을 포함하고 총 2~5개의 통제 관계만 갖는다. 한 record 안의 같은 관계명 반복은 0건이다.

1차 중간 초안은 `part_of 26`, `classification 27`, `is_a 8`, `subclass_of 8`, `other 9`로 과잉 라벨 가능성이 있었다. 의미 재감사 후에는 더 큰 구동계의 실제 부품 2건에만 `part_of`를 남겼고, 명시적 분류 문장이 있는 6건에만 `classification`과 `is_a/subclass_of`를 남겼다. `other` 9건은 모두 구조적 속성으로 기능을 설명할 수 있어 `attribute` 등으로 정정했다.

### 통제 어휘 13개 최종 분포

| relation | 횟수 | 판정 기준 |
|---|---:|---|
| `is_a` | 1 | 명시적 상위 공구 범주 |
| `subclass_of` | 5 | 명시적 하위 유형 문장 |
| `part_of` | 2 | 실제 구동계 부품 |
| `classification` | 6 | 실제 분류 문장과 함께 사용 |
| `boundary` | 17 | 수행하지 않는 용도·적용 한계 |
| `contrast` | 10 | 다른 도구·방식과 명시적 대비 |
| `comparison` | 7 | 접근 폭·크기·힘 등의 명시적 비교 |
| `function` | 150 | 전 record 필수 |
| `role` | 50 | 작업·시스템 안에서 맡는 역할 |
| `process` | 45 | 시간 순서·변화 과정 |
| `state` | 3 | 잠금·해제·정렬 유지 상태 |
| `attribute` | 79 | 형상·재료·구조가 기능에 기여 |
| `other` | 0 | 다른 12개로 설명 불가능한 사례 없음 |

### `other` 상위 개념 유형 5개

`other`로 확정한 record가 0건이므로 상위 개념 유형 5가지는 **해당 없음**이다. 보고 형식을 맞추기 위해 존재하지 않는 유형을 만들거나, 분포를 채우기 위해 정직한 라벨을 왜곡하지 않았다.

## 5. JSON·중복·유사도·문장 품질 감사

| 검사 | 결과 |
|---|---:|
| JSON parse / UTF-8 실패 | 0 |
| schema 오류 | 0 |
| top-level metadata 오류 | 0 |
| ID 불연속·중복 | 0 |
| relations 통제 어휘·개수·중복 오류 | 0 |
| exact primary concept 중복 | 0 |
| exact text 중복 | 0 |
| 반복 5어절 phrase | 0 |
| 반복 4어절 도입부 | 0 |
| Unicode escape 포함 파일 | 0 |
| primary concept 조사 오류 | 0 |
| 내부 문자 3~5-gram TF-IDF 최대 유사도 | 0.187422 |

내부 최고 유사 쌍은 `롱노즈플라이어`와 `미니쇠톱`이며 점수는 0.187422다. 두 문장은 좁은 공간 접근이라는 일부 어휘만 공유하고 대상·작용·결과가 달라 보일러플레이트나 의미 중복으로 판정하지 않았다.

넓은 조사 휴리스틱은 2건을 후보로 냈다.

- `S1-FNH-0057`의 `가까이`: 부사이며 조사 오류가 아니다.
- `S1-FNH-0150`의 `여닫는`: 동사 관형형이며 조사 오류가 아니다.

수동 확인 결과 `은/는`, `이/가` 등 조사의 불량 반복은 발견되지 않았다.

## 6. 저밀도 Function prototype 분리

비교 대상은 다음 120 records다.

- `stage1_dataset/train_v2/stage1_train_900_v2.json`의 `S1-FUNC-*` 108개
- `stage1_dataset/val/stage1_val_metadata_100.json`의 `S1-FUNC-*` 12개

| 검사 | 결과 |
|---|---:|
| exact primary concept 교집합 | 0 |
| exact text 교집합 | 0 |
| 반복 5어절 교집합 | 0 |
| 교차 문자 3~5-gram TF-IDF 최대 유사도 | 0.090128 |

교차 최고 쌍은 고밀도 `파이프렌치`와 prototype `트럭`으로, 낮은 점수의 우연한 기능 어휘 공유다. corpus 재사용이나 leakage 징후로 보지 않는다.

## 7. 27개 예약 concept family와 진행 상태

| 버전 | ID 범위 | concept family | 상태 |
|---|---|---|---|
| v01 | 0001~0150 | 수동 작업·정비·제작 공구 | 확정 |
| v02 | 0151~0300 | 식재료 준비·조리·제공 기구 | reserved, 다음 |
| v03 | 0301~0450 | 식품 보존·포장·위생·품질 관리 장치 | reserved |
| v04 | 0451~0600 | 의복·신발·착용 보호·휴대 구성품 | reserved |
| v05 | 0601~0750 | 청소·세탁·건조·생활 폐기물 처리 도구 | reserved |
| v06 | 0751~0900 | 건물 외피·개구부·실내 마감·공간 조절 구성품 | reserved |
| v07 | 0901~1050 | 급배수·위생·환기·냉난방 실내 설비 | reserved |
| v08 | 1051~1200 | 농림·축산·수산 생산 도구와 설비 | reserved |
| v09 | 1201~1350 | 육상·항공·해상 교통수단과 부품 | reserved |
| v10 | 1351~1500 | 포장·하역·운반·분류·보관 물류 장비 | reserved |
| v11 | 1501~1650 | 제조 성형·절삭·접합·조립 생산 설비 | reserved |
| v12 | 1651~1800 | 품질검사·공정제어·설비진단·유지보수 장치 | reserved |
| v13 | 1801~1950 | 도로·교량·철도·터널·배수 공공 인프라 | reserved |
| v14 | 1951~2100 | 물 공급·하수처리·위생·자원회수 도시 서비스 | reserved |
| v15 | 2101~2250 | 에너지 생산·변환·저장·송배전·보호 장치 | reserved |
| v16 | 2251~2400 | 전자회로·센서·신호처리·구동 부품 | reserved |
| v17 | 2401~2550 | 컴퓨팅 처리·기억·저장·입출력 장치 | reserved |
| v18 | 2551~2700 | 네트워크·소프트웨어·데이터 서비스 | reserved |
| v19 | 2701~2850 | 통신·미디어 기록·편집·전송·표현 도구 | reserved |
| v20 | 2851~3000 | 실험실 채취·분리·반응·계량·교정 장비 | reserved |
| v21 | 3001~3150 | 의료 진단·치료·모니터링·재활·감염관리 기구 | reserved |
| v22 | 3151~3300 | 생물 기관·세포 구조·생태계 구성원 | reserved |
| v23 | 3301~3450 | 환경 감시·오염 정화·자원 순환·생태 복원 시설 | reserved |
| v24 | 3451~3600 | 안전·재난·보안·구조·접근성 보조 장치 | reserved |
| v25 | 3601~3750 | 교육·학습·도서관·문서화 도구 | reserved |
| v26 | 3751~3900 | 상업·금융·거래·고객 서비스 체계 | reserved |
| v27 | 3901~4050 | 공공행정·법률·복지·지역사회·문화 서비스 | reserved |

하위 기능 축과 세부 생성 규칙은 `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`의 20절을 정본으로 삼는다. 새 세션은 마지막 `확정` 다음의 첫 `reserved`만 선택한다.

## 8. 수정 금지 파일 검증

중단 복구 시작 시 저장한 해시와 최종 해시를 비교했다.

| 보호 패턴 | 실제 파일 수 | 변경 | 누락 | 추가 |
|---|---:|---:|---:|---:|
| `stage1_(1)identity_high_density_*` | 45 | 0 | 0 | 0 |
| `stage1_(2)attribute_high_density_*` | 35 | 0 | 0 | 0 |
| `stage2_(2)attribute_high_density_*` | 0 | 0 | 0 | 0 |
| 합계 | 80 | 0 | 0 | 0 |

`stage2_(2)attribute_high_density_*`의 현재 실제 수가 0이어도 사용자 지시에 따라 수정 금지 패턴은 지침서에 유지한다.

## 9. 산출물과 재현 명령

```text
stage1_highdensity_dataset/train/stage1_(3)function_high_density_train_v01.json
stage1_highdensity_dataset/tools/build_function_train.py
stage1_highdensity_dataset/tools/audit_function_corpus.py
stage1_highdensity_dataset/TinyLM_Stage1_Function_Train_v01_Audit_2026-08-30.json
stage1_highdensity_dataset/TinyLM_Stage1_Function_Train_v01_Progress_Audit_2026-08-30.md
stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md
```

repository root에서 다음처럼 실행한다.

```powershell
python stage1_highdensity_dataset\tools\build_function_train.py .
python stage1_highdensity_dataset\tools\audit_function_corpus.py . --output stage1_highdensity_dataset\TinyLM_Stage1_Function_Train_v01_Audit_2026-08-30.json
```

`dataset_root` 인수는 repository root인 `.`이다. 고밀도 하위 폴더를 인수로 넘기지 않는다.
