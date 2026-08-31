# 2026-08-31 — **`(1)identity` 통제 어휘 소급 매핑 · LLM 작업 요청 프롬프트**

> 사용자 지시(2026-08-31 지시 3-a). 🚫**AI 는 이 데이터셋 폴더에 아무것도 쓰지 않았다** —
> 읽기만 하고 아래 수치를 실측했다. **실제 매핑은 데이터셋 담당 LLM 이 수행한다.**
>
> ⚠️★**왜 사람/LLM 이 필요한가**: 자동 규칙만으로는 안 된다. 1,904개 어휘 밖 관계 중
> **1,047종이 단 1회만** 나오고, 이름만으로 13개 중 어디에 얹을지 결정할 수 없는 것이 많다.
> 🚫**전부 `other` 로 몰면 정보가 사라지고**, 억지로 얹으면 **다른 코퍼스와 뜻이 갈린다**.

---

## 0. 먼저 — **얼마나 해야 하는가**(실측)

| | |
|---|---:|
| `(1)identity` train 레코드 | **6,100** |
| 관계 토큰 총량 | **17,001** |
| ✅통제 어휘 13개 안 | **7,947 = 46.7%** |
| 🚫어휘 밖 | **9,054 = 53.3%** |
| 어휘 밖 관계 **종류** | **1,904종** |

★★**노력 대비 회수가 급격히 꺾인다** — 전부 매핑할 필요가 없다:

| 매핑할 종류 수 | 어휘 밖 토큰 중 덮는 비율 | 전체 토큰 중 |
|---:|---:|---:|
| 상위 **25종** | 36.9% | 19.7% |
| 상위 **50종** | 46.1% | 24.6% |
| ★상위 **100종** | ★**56.2%** | 29.9% |
| 상위 200종 | 66.5% | 35.4% |
| 상위 500종 | 80.3% | 42.7% |

⚠️**1회만 나오는 1,047종은 종류의 55.0% 인데 토큰으로는 11.6%** 다.
→ ★**권장: 상위 100~200종만 손으로 매핑하고, 나머지는 규칙으로 `other`.**
그러면 **전체 관계 토큰의 76~82% 가 통제 어휘 안**이 된다.

---

## 1. ★통제 어휘 — **13개. 새 이름을 만들지 않는다**

`(2)attribute`(4,650 레코드)와 `(3)function`(4,050)이 **이미 정확히 지키고 있는** 목록이다.
🚫**여기에 항목을 추가하면 코퍼스마다 어휘가 갈린다.**

| 관계 | attribute 코퍼스 빈도 | 뜻(그 코퍼스에서 쓰이는 대로) |
|---|---:|---|
| `attribute` | 4,650 | X 는 대상의 속성이다 |
| `boundary` | 3,217 | X 와 Y 는 같은 종류가 아니다 / 경계를 긋는다 |
| `comparison` | 2,647 | 둘을 견준다 |
| `process` | 1,476 | 진행·절차·변화 |
| ★`other` | 921 | ★**위 어디에도 안 맞는 것.** 있어야 하는 칸이다 |
| `is_a` | 685 | X 는 Y 의 일종이다 |
| `state` | 492 | 상태 |
| `contrast` | 280 | 대비(같은 축 위의 반대) |
| `function` | 220 | 기능·용도 |
| `classification` | 190 | 분류 행위·분류 체계 |
| `part_of` | 168 | 부분-전체 |
| `role` | 94 | 역할 |
| `subclass_of` | 31 | 하위 분류 |

---

## 2. ★★작업 요청 프롬프트 (LLM 에게 그대로 준다)

```
당신은 TinyLM 프로젝트의 stage1 고밀도 데이터셋 관계 어휘를 정리합니다.

[배경]
stage1_(1)identity_high_density_train_v*.json 의 각 레코드에는 "relations" 배열이
있습니다. 이 코퍼스만 관계 이름을 자유롭게 만들어 써서 1,916종이 되었습니다.
같은 프로젝트의 (2)attribute 와 (3)function 코퍼스는 아래 13개만 씁니다.

  attribute, boundary, comparison, process, other, is_a, state,
  contrast, function, classification, part_of, role, subclass_of

목표는 identity 코퍼스의 관계 이름을 이 13개로 접는 매핑표를 만드는 것입니다.

[반드시 지킬 것]
1. 13개 밖의 새 이름을 만들지 마십시오. 목록을 늘리면 코퍼스마다 어휘가 갈립니다.
2. 하나의 원본 이름은 13개 중 정확히 하나로 갑니다. 다대일은 되고 일대다는 안 됩니다.
3. 확신이 서지 않으면 other 로 보내십시오. 억지로 얹는 것보다 낫습니다.
   other 는 (2)attribute 에서도 921회 쓰이는 정식 항목입니다.
4. 원본 필드를 지우지 마십시오. relations 는 그대로 두고
   relations_controlled 를 새 필드로 추가하십시오. 되돌릴 수 있어야 합니다.
5. 판단이 갈리는 이름은 매핑표에 이유를 한 줄 적어 주십시오.
   나중에 사람이 그 줄만 다시 봅니다.

[판단 기준 - 이름이 아니라 뜻으로]
- 이름이 X_boundary 로 끝난다고 자동으로 boundary 가 아닙니다.
  그 관계가 실제로 하는 일이 "둘은 같은 종류가 아니다" 이면 boundary 입니다.
- 상하위 관계는 is_a 와 subclass_of 를 구분하십시오.
  개체가 종류에 속하면 is_a, 종류가 더 큰 종류에 속하면 subclass_of 입니다.
- 시간·공간·수량을 가리키는 이름(temporal_*, spatial_*, measurement 등)은
  13개에 대응이 없습니다. 그 관계가 "대상의 성질" 을 말하면 attribute,
  "일이 진행되는 방식" 을 말하면 process, 아니면 other 입니다.
- 이름에 vs 나 not 이 들어간 것은 대개 boundary 또는 contrast 입니다.
  같은 축 위의 반대이면 contrast, 다른 종류라는 선긋기이면 boundary 입니다.

[작업 범위]
- 아래 표의 상위 120종을 먼저 매핑하십시오. 이것만으로 어휘 밖 토큰의 약 60%
  가 덮입니다.
- 그 다음 2회 이상 나오는 나머지(총 857종)를 하십시오. 88.4% 까지 올라갑니다.
- 1회만 나오는 1,047종은 규칙으로 other 에 넣고 목록만 남기십시오.
  종류로는 55% 지만 토큰으로는 11.6% 뿐입니다.

[산출물]
1. relation_mapping_identity_v1.json
     { "원본이름": "통제어휘이름", ... }
   판단이 갈린 항목은 별도 "notes" 객체에 이유를 담아 주십시오.
2. 각 레코드에 relations_controlled 를 추가한 데이터 파일.
   relations 는 그대로 둡니다.
3. 매핑 후 13개 각각의 빈도표. attribute 코퍼스의 분포와 나란히 놓고,
   어느 항목이 지나치게 커졌는지 한 줄로 적어 주십시오.

[검증 - 스스로 확인하고 보고할 것]
- relations_controlled 에 13개 밖의 값이 하나라도 있으면 실패입니다.
- 레코드 수가 6,100 에서 변하면 실패입니다.
- relations 와 relations_controlled 의 길이가 레코드마다 같아야 합니다.
- other 비율이 40% 를 넘으면 매핑이 너무 소극적입니다. 다시 보십시오.
```

---

## 3. ★매핑 대상 — **어휘 밖 상위 120종**(빈도 포함, 실측)

| | | | |
|---|---|---|---|
| `representation` 305 | `concept_boundary` 303 | `category` 247 | `measurement` 235 |
| `classification_boundary` 185 | `subtype` 153 | `temporal_boundary` 153 | `function_or_role` 150 |
| `spatial_general` 150 | `time_context` 150 | `variation` 143 | `state_change` 126 |
| `abstract_concept` 125 | `part_whole` 104 | `subtype_of` 96 | `hierarchy` 91 |
| `classification_basis` 84 | `system` 83 | `function_relation` 78 | `event` 75 |
| `contains` 71 | `derived_value` 69 | `supercategory` 59 | `derived_quantity` 58 |
| `action` 48 | `ratio` 44 | `relation` 43 | `measurement_concept` 43 |
| `identifier` 41 | `relationship` 41 | `document` 39 | `category_basis` 39 |
| `supertype` 38 | `state_vs_event` 38 | `result_distinction` 35 | `context` 34 |
| `spatial` 33 | `outcome` 32 | `habitat` 31 | `category_boundary` 30 |
| `attribute_not_entity` 30 | `entity_boundary` 29 | `composition` 28 | `cognitive_process` 28 |
| `process_vs_result` 28 | `speech_act` 27 | `operation` 26 | `social_relation` 26 |
| `material` 25 | `institution` 25 | `constraint` 25 | `context_dependence` 24 |
| `formation` 24 | `service` 24 | `temporal_attribute` 24 | `mental_state` 24 |
| `property` 23 | `scope` 23 | `definition_basis` 23 | `collection` 23 |
| `phenomenon` 22 | `has_parts` 22 | `result_of` 22 | `social_process` 22 |
| `material_of` 21 | `communication` 20 | `abstract_category` 20 | `polysemy` 20 |
| `category_scope` 20 | `temporal` 20 | `broad_class` 20 | `rate` 20 |
| `financial_measure` 19 | `multi_component` 19 | `information` 18 | `attribute_vs_entity` 18 |
| `emotion` 18 | `abstract_property` 18 | `structure` 17 | `condition` 17 |
| `member_of` 17 | `interaction` 16 | `transformation` 16 | `metadata` 16 |
| `population_group` 16 | `representation_boundary` 15 | `mental_attitude` 15 | `attitude_vs_action` 15 |
| `dependency` 15 | `distinction` 14 | `event_relation` 14 | `material_property` 14 |
| `identity` 13 | `goal` 13 | `evaluation` 13 | `subtypes` 13 |
| `range` 13 | `genre` 13 | `social_action` 13 | `unit_of` 13 |
| `classification_context` 12 | `spatial_context` 12 | `reference` 12 | `ambiguity` 12 |
| `abstract_structure` 12 | `logical_relation` 12 | `financial_ratio` 12 | `modality` 12 |
| `epistemic` 12 | `uncertainty` 11 | `mechanism` 11 | `activity` 11 |
| `device` 11 | `equipment` 11 | `has_part` 11 | `example` 11 |
| `group` 11 | `social_state` 11 | `legal_process` 11 | `cultural_form` 11 |

---

## 4. ⚠️참고 — **명백해 보이지만 판단이 필요한 것들**

🚫**아래를 "정답" 으로 주지 않는다.** 매핑은 데이터셋 담당이 정한다. 다만 **왜 자동 규칙이
안 되는지**를 보이는 예로 남긴다.

| 원본 | 자동 규칙이라면 | ⚠️그런데 |
|---|---|---|
| `subtype_of` · `supertype` · `supercategory` · `hierarchy` | 전부 `subclass_of` | ★**방향이 반대인 것이 섞여 있다.** `supertype` 은 위를, `subtype_of` 는 아래를 가리킨다. 13개에는 방향이 없다 |
| `concept_boundary` · `category_boundary` · `entity_boundary` | 전부 `boundary` | ✅**이건 아마 맞다** — 세 개 합쳐 362회로 단일 최대 이득 |
| `measurement` · `ratio` · `rate` · `derived_value` | `attribute`? | 🚫**"측정한다" 는 과정이고 "측정값" 은 속성**이다. 원문을 봐야 갈린다 |
| `representation` 305 | `other`? | ⚠️**단일 최대 항목**이다. `other` 로 보내면 305회가 통째로 사라진다 |
| `time_context` · `spatial_context` · `temporal_*` | `other` | 🚫13개에 시공간 칸이 없다. **`other` 가 정직한 답일 수 있다** |
| `identity` 13 | `is_a`? | 🚫*"X 는 Y 다"* 와 *"X 는 Y 의 일종이다"* 는 다르다 |

---

## 5. 🚫이 문서가 **하지 않은 것**

| | |
|---|---|
| 🚫매핑표를 만들지 않았다 | 자동 규칙만으로는 안 되고, 위 §4 가 그 이유다 |
| 🚫데이터 파일을 건드리지 않았다 | **읽기만 했다.** `(3)function` 은 작업 중이라 읽기도 최소한만 |
| 🚫통제 어휘를 늘리지 않았다 | 13개는 두 코퍼스가 이미 지키는 정본이다 |
| ⏸적용 후 재학습 | ★**소급 매핑은 `text` 필드를 안 바꾼다** → 학습 스트림 불변 → **재학습 불필요**. 바뀌는 것은 슬라이스 평가뿐이다 |
