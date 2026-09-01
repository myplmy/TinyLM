# Stage1 (1) Identity 관계 통제 어휘 전환 감사

- 감사일: 2026-09-01
- 상태: **PASS**
- 수정 범위: `train/stage1_(1)identity_high_density_train_v01.json` ~ `v41.json`
- 비수정 범위: Identity validation 전체, Stage1 (2)~(10) 전체, 저밀도 `stage1_dataset`
- 산출물:
  - [`../relation_mapping_identity_v1.json`](../relation_mapping_identity_v1.json)
  - [`../tools/build_identity_relation_control.py`](../tools/build_identity_relation_control.py)
  - [`machine/TinyLM_Stage1_Identity_Relation_Control_Audit_2026-09-01.json`](machine/TinyLM_Stage1_Identity_Relation_Control_Audit_2026-09-01.json)

## 1. 작업 결과

41개 train 파일의 6,100개 레코드에 `relations_controlled`를 추가했다. 기존 `relations`를 포함한 모든 기존 필드의 키 순서, 배열 순서, 값은 유지했다. `relations_controlled`는 원본 `relations`와 같은 길이의 위치 보존 1:1 투영이며, 원본 관계 이름 하나는 정확히 하나의 통제 어휘로만 간다.

원본 JSON 서식은 새 필드 추가 과정에서 정규화되었으므로 파일 자체 SHA-256은 달라졌다. 대신 새 필드를 제거한 기존 필드 투영의 canonical SHA-256을 작업 전·후 및 별도 보호 기준선과 대조했다. 41개 모두 일치했고 기존 필드의 키 순서 대조도 불일치 0개였다.

## 2. 원본 관계 어휘 실측과 처리 범위

| 항목 | 실측 |
|---|---:|
| 전체 relation type | 1,916 |
| 전체 relation token | 17,001 |
| 기존 13종 밖 type | 1,904 |
| 기존 13종 밖 token | 9,054 |
| OOV 상위 120종 token | 5,320 |
| OOV 상위 120종의 OOV token 점유율 | 58.7586% |
| 2회 이상 OOV type | 857 |
| 2회 이상 OOV token | 8,007 |
| 2회 이상 OOV의 OOV token 점유율 | 88.4361% |
| 상위 120종 이후 남은 2회 이상 OOV type | 737 |
| 1회 출현 type 및 token | 1,047 / 1,047 |
| singleton의 OOV token 점유율 | 11.5639% |

상위 120종을 우선 문맥 표본으로 검토한 뒤 나머지 737개 반복형을 같은 기준으로 처리했다. 1회 출현 1,047종은 사용자 규칙에 따라 모두 `other`로 보냈고 전체 목록은 매핑 파일의 `singleton_relations_forced_to_other`에 보존했다.

판단이 갈리거나 보수적 판단이 필요한 146개 이름에는 매핑 파일의 `notes`에 한 줄 근거를 남겼다. 독립 의미 감사에서 1차 50종, 상위 120종 이후 나머지 반복형 737종 전수 대조와 R2 보수 판단을 포함한 2차 68종을 보정해 누적 118종의 의미 매핑을 재확정했다. 2차 68종의 구성은 명백한 `other` 보정 14종, 구체 라벨 간 보정 13종, `other`에서 구체 라벨로의 보정 30종, 의미 혼재나 직접 대응 부재로 R2를 적용한 보수적 `other` 보정 11종이다. `--reapply`로 `relations_controlled`만 안전하게 재투영했으며 원본 필드 투영은 다시 보호 기준선과 일치했다. 주요 판단은 다음과 같다.

- `category`는 명시적 개체→종류 논항 관계가 아니라 범주화 표지이므로 `classification`이다.
- `subtype`, `subtype_of`, `supertype`, `hierarchy`는 종류→더 큰 종류의 관계이므로 `subclass_of`다.
- `function_or_role` 150건은 작물·원료·도구의 용도 서술이 중심이므로 `function`이다.
- `state_vs_event`, `process_vs_result`, `attribute_vs_entity`는 서로 다른 개념 유형을 가르는 용례라 `boundary`다.
- `spatial_general`, `time_context`, `spatial`, `temporal`은 공간·시간의 속성, 관계, 맥락, 과정이 혼재하여 한 라벨로 강제하지 않고 `other`다.
- `necessary_condition`, `sufficient_condition`, `conditional_relation`은 현재 상태가 아닌 논리 관계이며 직접 대응 어휘가 없어 `other`다.
- `condition`, `event_relation`, `structure`, `communication`, `evaluation`은 각 이름 아래 서로 다른 의미 유형이 섞여 있어 `other`다.
- `difference`, `scale_boundary`는 실제 표본이 수치·규모의 같은 축 비교라 `comparison`이다.
- `aggregation`, `payment`, `change_value`, `energy_state`, `validity`는 과정이 아니라 계산값·금액·측정 성질이 중심이라 `attribute`다.
- `phenomenon`, `natural_phenomenon`은 대상을 현상이라는 상위 유형에 두는 표지라 `classification`이다.
- 수학·집합의 `operation`, `logical_operation`, `set_operation`, `multiplication`은 시간 과정으로 고정할 수 없어 `other`다.
- `contains_information`, `contains_content`, `has_members`, `part_of_context`, `part_of_relation`, `allocation`, `cause_effect`, `definition`, `derived_concept`, `derived_from`, `effect_pattern`은 논항 구조가 혼재하거나 13종에 직접 대응하지 않아 R2에 따라 `other`다.

## 3. 통제 어휘 분포와 Attribute train 비교

Identity 분모는 17,001 relation token, Attribute train 분모는 실제 v01~v31의 15,071 relation token이다.

| relation | Identity 횟수 | Identity 비율 | Attribute 횟수 | Attribute 비율 | 차이(pp) |
|---|---:|---:|---:|---:|---:|
| attribute | 1,208 | 7.11% | 4,650 | 30.85% | -23.75 |
| boundary | 3,240 | 19.06% | 3,217 | 21.35% | -2.29 |
| comparison | 253 | 1.49% | 2,647 | 17.56% | -16.08 |
| process | 1,123 | 6.61% | 1,476 | 9.79% | -3.19 |
| other | 3,084 | 18.14% | 921 | 6.11% | +12.03 |
| is_a | 3,210 | 18.88% | 685 | 4.55% | +14.34 |
| state | 376 | 2.21% | 492 | 3.26% | -1.05 |
| contrast | 430 | 2.53% | 280 | 1.86% | +0.67 |
| function | 763 | 4.49% | 220 | 1.46% | +3.03 |
| classification | 1,581 | 9.30% | 190 | 1.26% | +8.04 |
| part_of | 580 | 3.41% | 168 | 1.11% | +2.30 |
| role | 243 | 1.43% | 94 | 0.62% | +0.81 |
| subclass_of | 910 | 5.35% | 31 | 0.21% | +5.15 |

Identity에서 절대 빈도가 가장 큰 항목은 `boundary` 3,240회지만, Attribute와의 상대 비교에서 가장 과대하게 나타난 항목은 `is_a`(+14.34%p)다. 이는 Identity 교육영역의 대상→종류 소속 서술이 많은 설계와 일치한다. `other`도 +12.03%p지만 18.14%로 사용자 상한 40%를 충분히 밑돌며, 공간·시간·논리·표현 관계와 혼합 의미를 거짓 라벨로 강제하지 않은 결과다.

## 4. `other`의 자주 나온 개념 유형 5가지

반복형 원본 관계를 의미군으로 묶어 보면 다음 유형이 자주 나타났다. 아래 수치는 대표 relation type의 합계이며 singleton 1,047종은 별도다.

1. 공간·시간의 일반 맥락과 관계: `spatial_general`, `time_context`, `spatial`, `temporal`, `scope`, `space`, `spatial_context`, `spatial_concept`, `temporal_concept`, `temporal_condition`, `temporal_relation`, `sequence`, `spatial_relation`, `spatial_containment` 대표 반복형 448회.
2. 표현·지시·식별: `representation`, `identifier`, `reference`, `symbolic_expression`, `representation_system`, `aboutness`, `represents`, `copy_relation` 대표 반복형 376회.
3. 논리·형식 연산·규범·계획·제약: `operation`, `constraint`, `condition`, `logical_relation`, `modality`, `epistemic`, `uncertainty`, `goal`, `rule`, `plan`, `norm`, `social_norm`, `standard`, `planning`, `negation`, `criterion`, `equivalence`, `many_to_one`, `many_to_many` 대표 반복형 200회.
4. 일반·사회 관계 및 의존: `relation`, `relationship`, `social_relation`, `dependency`, `event_relation`, `legal_relation`, `process_relation`, `relational_concept`, `conditional_relation`, `source_relation`, `contract_relation`, `reciprocity`, `system_relation`, `semantic_relation` 대표 반복형 198회.
5. 문맥·정보·소통: `context`, `context_dependence`, `communication`, `information`, `contains_information`, `context_variation`, `contextual_status`, `contextual_scope`, `definition_scope`, `content`, `abstract_content`, `media_content` 대표 반복형 144회.

## 5. 검증 게이트

| 게이트 | 결과 |
|---|---|
| 파일 수 41 | PASS |
| 레코드 수 6,100 유지 | PASS |
| ID `S1-IDH-001`~`S1-IDH-6100`, 6,100개 유일 | PASS |
| 매핑 엔트리 1,916, 원본 type 누락 0 | PASS |
| `relations_controlled`가 13종 밖 값을 포함 | 0건, PASS |
| 원본/통제 배열 길이 불일치 | 0건, PASS |
| 저장된 배열과 매핑의 위치별 값 불일치 | 0건, PASS |
| 기존 필드 canonical 투영 변경 파일 | 0/41, PASS |
| 외부 보호 기준선 SHA 불일치 | 0/41, PASS |
| 기존 필드 키·배열 순서 불일치 | 0/41, PASS |
| `other` 비율 40% 이하 | 18.1401%, PASS |
| Identity validation 수정 | 0개 |
| 다른 train 교육영역 수정 | 0개 |
| 기타 보호 데이터셋 SHA-256 불일치 | 0/245, PASS |

다대일 매핑과 위치 보존 길이 조건을 동시에 지키므로 한 레코드 안에서 같은 통제 라벨이 반복될 수 있다. 실제로 1,103개 레코드에서 중복 통제 라벨이 생겼고, 집합 기준 초과 토큰은 1,148개다. 이는 새 corpus의 R4 위반을 허용한 것이 아니라, legacy 원본 배열을 되돌릴 수 있게 위치별 1:1로 보존하기 위한 의도된 예외다.

파일별 SHA-256은 machine audit의 `file_hashes`에 모두 기록했다. `sha256_before`는 최초 보호 기준선, `sha256_pre_reapply`는 독립 의미 리뷰 전 1차 투영본, `sha256_after`는 최종 재투영본이다. 기존 필드 투영 SHA-256 전·후 41쌍도 함께 기록했다. 재검증 명령은 다음과 같다.

```powershell
python stage1_highdensity_dataset/tools/build_identity_relation_control.py --verify
```

최종 재검증 결과는 `PASS`, 보호 기준선 불일치 0, 기존 필드 순서 불일치 0, 실패 항목 0이었다.
