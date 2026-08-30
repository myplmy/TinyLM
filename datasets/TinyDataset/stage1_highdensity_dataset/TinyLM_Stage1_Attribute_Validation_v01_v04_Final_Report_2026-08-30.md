# TinyLM Stage 1 Attribute Validation v01~v04 생성·최종 감사 보고서

- 기준일: 2026-08-30 KST
- 대상 split: `stage1_(2)attribute` validation
- 생성 범위: v01~v04, 4개 파일, 600 records
- ID 범위: `S1-ATV-0001`~`S1-ATV-0600`
- 판정: **PASS**

## 1. 생성 결과

| 버전 | 파일 | ID 범위 | 새 concept family | records | 누적 | unseen |
|---|---|---|---|---:|---:|---:|
| v01 | `stage1_(2)attribute_high_density_val_v01.json` | 0001~0150 | 토양·지질·지형·수문 반응 특성 | 150 | 150 | 18 |
| v02 | `stage1_(2)attribute_high_density_val_v02.json` | 0151~0300 | 식품·조리·발효·저장 품질 특성 | 150 | 300 | 18 |
| v03 | `stage1_(2)attribute_high_density_val_v03.json` | 0301~0450 | 건축·실내환경·도시 미기후 특성 | 150 | 450 | 18 |
| v04 | `stage1_(2)attribute_high_density_val_v04.json` | 0451~0600 | 해양·연안·수생환경 반응 특성 | 150 | 600 | 18 |

네 파일 모두 `stage1_highdensity_dataset/val/`에 있다. 각 `text`는 concept별로 직접 작성했으며 자동화는 ID 부여, JSON 포장, train 인덱싱과 감사에만 사용했다.

사용자가 지정한 약 42K 설계 분량은 600-record 기준으로 충족했다. 현재 workspace에는 실제 학습 tokenizer가 없으므로 모델 token 수로 확정하지 않았으며, 참고 실측은 본문 31,288자와 공백·문장부호 기준 어휘 단위 7,533개다. 향후 실제 학습 tokenizer가 정해지면 같은 네 파일의 `text`만 입력해 별도로 계수해야 한다.

## 2. Validation 분리 규칙 결과

Attribute train v01~v31에는 통제 relation 이름 13개가 이미 모두 존재한다. 따라서 통제 어휘를 깨지 않으면서 V2를 구현하기 위해 `unseen_relation: true`를 **개별 relation 이름이 아니라 정렬된 relation-set 조합이 train에서 미관측인 경우**로 판정했다. relation 순서만 다른 것은 같은 조합이다.

| 구분 | records | 비율 |
|---|---:|---:|
| `unseen_relation: true` | 72 | 12.00% |
| `unseen_relation: false` | 528 | 88.00% |
| 합계 | 600 | 100.00% |

- 파일별 true: 18/150 = 12.00%
- true에 사용한 고유 미관측 relation-set: 12종
- false에 사용한 고유 train 관측 relation-set: 22종
- true의 relation-set이 train에 없다는 검사: 전부 PASS
- false의 relation-set이 train에 있다는 검사: 전부 PASS
- true와 false를 포함한 모든 개별 relation 이름이 train에 있다는 검사: 전부 PASS

## 3. Relations 값 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 3 |
| `subclass_of` | 4 |
| `part_of` | 49 |
| `classification` | 71 |
| `boundary` | 300 |
| `contrast` | 44 |
| `comparison` | 278 |
| `function` | 90 |
| `role` | 27 |
| `process` | 207 |
| `state` | 138 |
| `attribute` | 600 |
| `other` | 52 |

모든 record는 relation 2~5개, record 안 중복 0개, 통제 어휘 밖 이름 0개다. 13개 통제 어휘가 validation 전체에서 모두 실제 사용되었다.

## 4. `other` 개념 유형 상위 5개

`other`가 붙은 52개를 primary concept의 핵심 질문에 따라 상호 배타적으로 다시 분류했다. `other`는 오류 표지가 아니라 나머지 12개 relation만으로 정직하게 설명하기 어려운 보조 관계다.

| 순위 | 반복 개념 유형 | 횟수 | 예시 |
|---:|---|---:|---|
| 1 | 조건·입력 의존, 영향, 선택성 | 22 | 수문모형초기조건의존성, 혼합순서의존성, 규조류규산의존성 |
| 2 | 공간·시간 집중, 분포, 편향 | 12 | 표면유출집중도, 센서결측공간집중성, 플랑크톤수직집중성 |
| 3 | 구조 저항, 상태 분류, 형태적 기타 | 7 | 토양뿌리관입저항성, 저장등급기능상태, 서식공간조각화도 |
| 4 | 복합 감각, 물질 이동·혼합, 수용 | 6 | 향미복합도, 포장재향이행도, 공동공간소음수용도 |
| 5 | 잠재성, 불확실성, 위험 추정 | 5 | 낙석발생잠재력, 설비효율추정불확실성, 연안재해예측불확실성 |
| **합계** |  | **52** | |

## 5. 구조·중복·유사도·한국어 감사

| 감사 항목 | 결과 |
|---|---:|
| JSON parse / UTF-8 실패 | 0 |
| 한글 `\uXXXX` escape 파일 | 0 |
| 파일 metadata 오류 | 0 |
| record schema 오류 | 0 |
| ID 불연속·중복 | 0 |
| exact text 중복 | 0 |
| primary concept 중복 | 0 |
| validation 내부 반복 5어절 | 0 |
| validation 내부 반복 4어절 도입부 | 0 |
| primary concept 직후 조사 오류 | 0 |
| 일반 조사 휴리스틱 후보 | 9개 검토, 실제 오류 0 |
| relation 규칙 오류 | 0 |
| `unseen_relation` 판정 오류 | 0 |
| 내부 최고 문자 3~5-gram TF-IDF cosine | 0.383657 |

본문 길이는 최소 36자, 중앙값 50자, 평균 52.147자, 최대 93자다. 1문장 record 523개, 2문장 record 77개다. 형태소 분석을 하지 않는 일반 조사 휴리스틱이 `되찾는`, `머금는`, `가라앉는`, `붙잡는` 등의 동사 어절에서 9개 후보를 냈으나 문맥 수동 검토 결과 모두 정상 표현이었다. 따라서 조사 오류로 확정한 record는 0개다.

초기 감사에서는 반복 5어절 14건, 반복 도입부 1건, 내부 최고 유사도 0.605588을 검출했다. 해당 record를 의미를 유지한 새 문장으로 직접 재작성하고, 미관측 relation 조합의 각 라벨이 실제 문장 의미에 성립하는지도 함께 보강했다. 최종 재감사에서는 반복 5어절과 반복 도입부가 모두 0건이고 최고 유사도는 0.383657로 낮아졌다. 최고 쌍은 서로 다른 해양 관계 개념인 `하구교환역할대비상태`와 `기질역할대비상태`이며, 공통 relation 조합 때문에 어휘가 일부 비슷하지만 객체와 측정 질문은 독립적이다.

## 6. Train–validation leakage 감사

| 분리 항목 | 결과 |
|---|---:|
| train–val exact primary concept overlap | 0 |
| train–val exact text overlap | 0 |
| `(primary concept, sorted relation-set)` overlap | 0 |
| train–val 공통 5어절 구절 | 0 |
| cross-split 최고 문자 3~5-gram TF-IDF cosine | 0.311535 |

Cross-split 최고 쌍은 val의 `해수전기전도온도의존성`과 train의 `전도도변동성`이다. 둘은 해수의 온도 조건 의존성과 일반 전도도 변동을 각각 다뤄 문장·객체·관계 조합이 동일하지 않다.

## 7. 수정 금지 파일 무결성

작업 시작과 종료의 SHA-256을 비교했다.

- `stage1_highdensity_dataset/train/`의 72개 기존 JSON: 전부 동일
- 그중 attribute train v01~v31: 전부 동일
- 그중 identity train v01~v41: 전부 동일
- 기존 identity validation v01~v04: 전부 동일

즉, `stage1_(1)identity_high_density_*` 계열과 기존 attribute train은 수정하지 않았다.

## 8. 재현·감사 산출물

- 직접 작성 source와 JSON packager: `tools/build_attribute_validation.py`
- validation·cross-split 감사기: `tools/audit_attribute_validation.py`
- 기계 판독 감사 결과: `TinyLM_Stage1_Attribute_Validation_v01_v04_Audit_2026-08-30.json`
- corpus 생성 정본 지침: `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`

`TinyLM_Stage1_Stage7_Master_Continuity_Summary.md`는 이번 작업에서 삭제하지 않았다. 새 지침서가 이를 대체할 수 있도록 현행 train/validation 상태와 규약을 반영했다.
