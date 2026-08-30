# TinyLM Stage 1~Stage 7 데이터셋·Corpus 생성 작업 지침서

- 문서 상태: 현행 정본
- 기준일: 2026-08-30 KST
- 대상 프로젝트: 약 100M 파라미터급 한국어 TinyLM curriculum
- 현재 구현 초점: Stage 1 고밀도 데이터셋
- 대체 대상: `TinyLM_Stage1_Stage7_Master_Continuity_Summary.md`

이 문서는 새 작업 세션이 다른 대화 기록을 읽지 않아도 TinyLM 데이터셋을 같은 규약으로 계속 생성·감사할 수 있도록 만든 단독 작업 지침서다. 과거 handoff나 감사보고서와 내용이 충돌하면 **실제 파일 → 최신 감사 JSON → 이 지침서 → 과거 handoff·요약 문서** 순으로 현재 상태를 판정한다. 확정되지 않은 Stage 2~Stage 7의 세부 수치나 schema를 임의로 만들어서는 안 된다.

---

## 1. 프로젝트 목표와 curriculum 철학

TinyLM은 단순한 문장 암기보다 다음 능력을 순서대로 형성해야 한다.

1. 대상과 개념을 식별한다.
2. 대상의 정체성, 속성, 상태, 기능, 관계를 서로 다른 정보 유형으로 구분한다.
3. 개념 경계와 반례를 통해 과잉 일반화를 억제한다.
4. 부분–전체, 공간, 비교, 시간, 조건 의존 관계를 조합한다.
5. 문맥 안에서 여러 개념과 관계를 동시에 유지한다.
6. 부정과 불확실성, 관찰되지 않음과 존재하지 않음을 구분한다.
7. 이후 단계에서 절차, 추론, 대화, 지시 수행, 실전 문제 해결로 확장한다.

핵심 원칙은 **초기에는 세계를 구성하는 기본 ontology를 분리하고 연결하며, 뒤 단계에서 그 단위를 조합해 추론하고 행동하게 하는 것**이다.

---

## 2. Stage 1~Stage 7의 상위 역할

### Stage 1 — 개념·속성·관계의 기초 ontology

핵심 질문:

- 이것은 무엇인가?
- 이것은 어떤가?
- 무엇과 어떤 관계인가?
- 어떤 조건에서 달라지는가?

교육 범위:

- 대상·정체성·분류
- 속성·정도·변이
- 기능·용도·목적
- 개념 경계·반례
- 부분–전체
- 상태·상태 변화
- 공간 관계
- 비교·대조
- 문맥 통합
- 타입·부정·불확실성

### Stage 2 — 복합 관계·의존·인과·조건 구조

조건부 관계, 원인–결과, 의존성, 가능성, 시간적 선후, 상태 전이, 다중 관계 조합을 다룬다.

### Stage 3 — 절차·행동·계획·문제 해결

목표, 계획, 단계, 제약, 자원, 선택, 우선순위, 실패와 복구를 행동 전후 상태와 연결한다.

### Stage 4 — 문맥·담화·지시·대화

장문 참조, 생략, 대화 상태, 질문–응답, 지시 추적, 화행, 암시와 맥락 의존을 다룬다.

### Stage 5 — 일반화·추론·전이

귀납·연역 구조, 반례 기반 일반화, 새로운 개념 조합, 규칙·구조의 다른 도메인 전이를 다룬다.

### Stage 6 — 지식 통합·장문맥·복합 문제

긴 문맥, 다단계 추론, 복합 제약, 다중 목표, 정보 통합, 불확실성 관리를 다룬다.

### Stage 7 — 지시 수행·대화·실전 사용

명령 이해, 출력 형식 준수, 다턴 대화, 도구·프로토콜 확장, 안전과 불확실성 처리, 실전 task 수행을 다룬다.

> Stage 2~Stage 7은 현재 상위 역할만 확정되어 있다. 각 Stage의 token mixture, 파일 수, ID 체계, train/val 비율은 별도 승인 없이 임의 확정하지 않는다.

---

## 3. Stage 1 확정 3M-token mixture

| 영역 | 비율 | token | 핵심 질문 |
|---|---:|---:|---|
| 대상·정체성·분류 | 18% | 540K | 이것은 무엇인가? |
| 속성·정도·변이 | 14% | 420K | 이것은 어떤가? |
| 기능·용도·목적 | 12% | 360K | 무엇에 사용되는가? |
| 개념 경계·반례 | 14% | 420K | 왜 다른 개념인가? |
| 부분–전체 | 10% | 300K | 무엇이 무엇의 일부인가? |
| 상태·상태 변화 | 10% | 300K | 지금 어떤 상태이며 어떻게 변하는가? |
| 공간 관계 | 7% | 210K | 어디에 있고 어떻게 배치되는가? |
| 비교·대조 | 6% | 180K | 무엇이 같고 다른가? |
| 문맥 통합 | 5% | 150K | 여러 개념이 한 상황에서 어떻게 연결되는가? |
| 타입·부정·불확실성 | 4% | 120K | 정보 타입과 확실성은 무엇인가? |
| **합계** | **100%** | **3,000K** | |

교육 우선순위와 실제 token mixture를 혼동하지 않는다. 교육 우선순위는 정체성 25%, 속성 15%, 기능 12%, 경계 12%, 부분–전체 10%, 상태 8%, 공간 6%, 비교 5%, 문맥 4%, 타입·부정·불확실성 3%라는 설계 관점을 가질 수 있지만, 실제 3M 배분은 위 표를 따른다.

### 3.1 Stage 1 열 개 영역의 교육 목적

| 영역 | 모델이 답해야 할 질문 | 반드시 분리해 가르칠 내용 |
|---|---|---|
| 대상·정체성·분류 | 이것은 무엇인가? | entity, 상위·하위 범주, 유형–인스턴스, 분류 경계, 오분류 방지 |
| 속성·정도·변이 | 이것은 어떤가? | 정적 속성, 정도, 편차, 환경·시간 변화, 민감도, 안정·회복 |
| 기능·용도·목적 | 무엇에 사용되는가? | 도구의 목적, 대상의 기능, 행동의 목적, 수단과 결과 |
| 개념 경계·반례 | 왜 다른 개념인가? | 반례, 인접 개념, 조건부 분류, 필요·충분조건의 직관 |
| 부분–전체 | 무엇이 무엇의 일부인가? | 구성요소, 방향성, 전체 속성을 부분에 잘못 상속하는 오류 |
| 상태·상태 변화 | 지금 어떠하며 어떻게 바뀌는가? | 열림·닫힘, 켜짐·꺼짐, 손상, 상변화, 대상과 상태의 분리 |
| 공간 관계 | 어디에 있고 어떻게 배치되는가? | 안·밖, 위·아래, 근접, 좌·우, 인접, 공간 경계 |
| 비교·대조 | 무엇이 같고 다른가? | 비교 기준, 공통점, 상대적 크기, 명시적 차이 |
| 문맥 통합 | 한 상황에서 어떻게 연결되는가? | 사람, 대상, 위치, 도구, 행동, 상태의 동시 유지 |
| 타입·부정·불확실성 | 정보 타입과 확실성은 무엇인가? | Entity/Attribute/Quantity/Relation/State/Action, 부정, 부재와 비존재, 가능성, 미관측과 비존재 |

### 3.2 정보 타입과 방향성의 핵심 원칙

- 정체성 `고양이는 동물이다`와 속성 `고양이는 민첩하다`를 같은 정보로 취급하지 않는다.
- 속성 `컵은 단단하다`와 공간 관계 `컵은 상자 안에 있다`를 분리한다.
- `사람`, `빨간색`, `세 개`, `책상 위`, `열림`, `달리기`는 각각 Entity, Attribute, Quantity, Relation, State, Action으로 구분한다.
- 대상의 정체성은 시간이 지나도 유지될 수 있지만 현재 상태는 바뀔 수 있다.
- 관계는 방향을 가진다. 바퀴가 자전거의 `part_of`라는 사실과 자전거가 바퀴를 가진다는 역방향 진술은 의미 방향이 다르다.
- `has_part`, `inside`, `contains` 같은 말은 의미 설명에 쓸 수 있어도 새 record의 `relations` 이름으로 만들지 않는다. metadata에는 13개 통제 어휘만 사용하고, `part_of`의 주체·객체 방향은 `text`와 primary concept 기준으로 명확히 한다.

### 3.3 과잉 일반화 억제 원칙

100M급 소형 모델이 다음 오류를 학습하지 않게 한다.

```text
A와 B가 함께 등장한다 → A와 B는 같다
A에서 B가 자주 보인다 → B는 A의 정의다
A가 속성 B를 가진다 → B를 가진 것은 모두 A다
A는 대체로 B다 → A는 언제나 B다
```

가능한 corpus 묶음에는 다음 네 요소를 조합한다.

```text
positive example + counterexample + boundary + condition
```

상관과 동일성, 공존과 정의, 흔한 속성과 필요조건을 구분한다. 조건을 뺀 절대 문장으로 바꾸지 않는다.

### 3.4 Identity 영역의 현행 실제 파일 snapshot

Identity의 설계 배분은 540K 중 train 486K, validation 54K인 90:10이다. 초기 900:100 prototype 분할과 현재 전체 설계를 혼동하지 않으며 held-out은 이 540K에 섞지 않는다.

2026-08-30 실제 고밀도 파일은 다음과 같다.

- train v01~v41: 41개 파일, 6,100 records, `S1-IDH-001`~`S1-IDH-6100`
- validation v01~v04: 4개 파일, 600 records, `S1-IDV-0001`~`S1-IDV-0600`
- train v01만 100개이고 v02~v41은 각 150개다.
- legacy identity 파일은 버전별 top-level metadata와 ID padding이 균일하지 않다. 이를 attribute schema로 일괄 재직렬화하지 않는다.

주요 누적 concept family는 일상 사물, 음식·조리, 의복·개인용품, 자연·생태, 과학 현상, 수학·논리, 사회·제도, 문화·언어·예술, 교육, 공학·인프라, 건강 일반, 상업·물류, 교통·지리·도시, 법률, 행정·공공서비스, 농축수산, 지식·정보·기록, 환경·기후·에너지, 건축·공간, 조직·노동, 디지털 사회, 안전·재난, 가족·인구, 재료·제품·도구, 범용 공간, 시간, 인과·조건·가능성, 집합·계층·상속, 정량, 상태전이, 관찰·증거·검증 ontology를 포함한다. 이 목록은 이력이지 540K 영역이 완전히 소진되었다는 뜻은 아니다.

현재 사용자 경계상 `stage1_(1)identity_high_density_*`는 **수정 금지**다. 이 지침서의 신규 attribute 작업 규약을 이유로 legacy identity 파일을 정리하거나 관계명을 바꾸지 않는다.

### 3.5 평가 원칙

외부 LLM judge는 필수 구성요소로 두지 않는다. 우선 사용할 평가는 teacher-forced token CE, paired CE difference, likelihood 또는 pseudo-log-likelihood, 다지선다 우도 비교, exact match/F1, 구조적 deterministic scorer다. SFT가 없는 base LM의 자유 생성 답변을 단순 문자열 비교하는 방식은 출력 형식 변동이 커서 단독 핵심 지표로 쓰지 않는다.

---

## 4. Split의 역할과 절대 경계

### Train

- gradient update에 사용한다.
- 개념, 속성, 관계, 경계와 조건 변화를 학습한다.
- validation이나 held-out record를 섞지 않는다.

### Validation

- gradient update에 사용하지 않는다.
- train과 같은 causal-LM loss로 validation loss/perplexity를 측정한다.
- checkpoint, epoch, 학습 종료, 사전에 정한 제한적 hyperparameter 선택에 사용할 수 있다.
- validation을 반복해서 본 결정은 허용되지만, 그 때문에 validation은 최종 blind test가 아니다.

### Held-out / Benchmark

- 최종 모델을 확정한 뒤에만 사용한다.
- gradient, checkpoint 선택, hyperparameter 조정, corpus 수정 근거로 사용하지 않는다.
- 결과를 본 뒤 학습 조건을 바꾸면 해당 benchmark는 더 이상 완전한 blind final test가 아니며 새 benchmark가 필요하다.

정확한 순서:

```text
TRAIN
  ↓
VALIDATION
  ↓
checkpoint selection
  ↓
FINAL MODEL FIXED
  ↓
HELD-OUT BENCHMARK
```

모델 입력에는 기본적으로 `text`만 제공한다. `id`, `type`, `concepts`, `relations`, `unseen_relation`은 감사, 균형 점검, 오류 분석, leakage 검사에 쓰는 metadata이며 tokenizer 입력에 자동으로 붙이지 않는다.

---

## 5. Stage 1 고밀도 디렉터리와 파일명 규약

기준 루트:

```text
stage1_highdensity_dataset/
├── train/
├── val/
├── tools/
└── 감사·지침 Markdown/JSON
```

영역 번호:

```text
(1) identity  = 대상·정체성·분류
(2) attribute = 속성·정도·변이
(3) function  = 기능·용도·목적
```

### Train 파일명

```text
stage1_(1)identity_high_density_train_v01.json
stage1_(2)attribute_high_density_train_v01.json
stage1_(3)function_high_density_train_v01.json
```

### Validation 파일명

```text
stage1_(1)identity_high_density_val_v01.json
stage1_(2)attribute_high_density_val_v01.json
stage1_(3)function_high_density_val_v01.json
```

규칙:

- 버전은 `v01`, `v02`처럼 두 자리 0-padding을 쓴다.
- 한 파일은 원칙적으로 정확히 150개 record다.
- 150개를 넘기지 말고 다음 버전 파일로 이동한다.
- 각 새 버전은 직전 파일과 구별되는 새 concept family를 갖는다.
- 영역·split·버전이 파일명과 top-level metadata에서 일치해야 한다.

---

## 6. ID 규약

### Attribute train

```text
S1-ATH-0001 ... S1-ATH-4650
```

### Attribute validation

```text
S1-ATV-0001 ...
```

### Function train

```text
S1-FNH-0001 ... S1-FNH-4050
```

`FNH`는 Function High-density train 전용 접두사다. 기존 prototype의 `S1-FUNC-*`와 충돌시키지 않는다. Function validation을 만들 때는 별도 `S1-FNV-*` 접두사를 사용하고 train ID를 재사용하지 않는다.

현재 확정된 attribute validation 600개는 다음 범위를 쓴다.

| 버전 | ID 범위 | 수량 |
|---|---|---:|
| val v01 | S1-ATV-0001~0150 | 150 |
| val v02 | S1-ATV-0151~0300 | 150 |
| val v03 | S1-ATV-0301~0450 | 150 |
| val v04 | S1-ATV-0451~0600 | 150 |

ID 검사:

- 파일 안에서 오름차순 연속
- 파일 간 중복 0
- train과 val 접두사 분리
- 선언한 `range`와 첫·마지막 실제 ID 일치

---

## 7. Top-level JSON schema

### Train 예시

```json
{
  "dataset_name": "Korean AI Curriculum — Stage 1 Attribute High-Density Train 150 v31",
  "version": "31",
  "purpose": "개념군과 교육 목적",
  "split": "train",
  "record_count": 150,
  "range": "S1-ATH-4501 ~ S1-ATH-4650",
  "design_note": "인접 개념 경계와 구성 원칙",
  "records": []
}
```

### Validation 예시

```json
{
  "dataset_name": "Korean AI Curriculum — Stage 1 Attribute High-Density Validation 150 v01",
  "version": "1",
  "purpose": "새 개념군에서 속성·정도·변이 일반화를 검증하는 validation corpus 150개",
  "split": "val",
  "record_count": 150,
  "range": "S1-ATV-0001 ~ S1-ATV-0150",
  "concept_family": "이 파일의 새 개념군",
  "design_note": "train과 분리한 방식과 의미 경계",
  "generalization_slice": {
    "basis": "controlled relation-set composition unseen in attribute train v01~v31",
    "unseen_records": 18,
    "total_records": 150,
    "ratio": 0.12
  },
  "records": []
}
```

Top-level 필수 검사:

- `record_count == len(records)`
- `split` 정확
- `version`과 파일명 일치
- `range`와 실제 첫·마지막 ID 일치
- `purpose`, `design_note`, validation의 `concept_family`가 실제 내용과 일치

---

## 8. Attribute와 Function record schema

### Train record

```json
{
  "id": "S1-ATH-4501",
  "type": "attribute_packet",
  "split": "train",
  "text": "한국어 속성 문장",
  "concepts": ["핵심개념"],
  "relations": ["attribute", "boundary", "comparison"]
}
```

### Validation record

```json
{
  "id": "S1-ATV-0001",
  "type": "attribute_packet",
  "split": "val",
  "text": "train에 없던 새 개념군의 한국어 속성 문장",
  "concepts": ["핵심개념"],
  "relations": ["attribute", "boundary", "comparison"],
  "unseen_relation": false
}
```

### Function train record

```json
{
  "id": "S1-FNH-0001",
  "type": "function_packet",
  "split": "train",
  "text": "대상이 수행하는 기능, 사용 목적, 작동 조건과 경계를 설명한 한국어 문장",
  "concepts": ["핵심개념"],
  "relations": ["function", "process", "boundary"]
}
```

필드 규칙:

- `type`은 attribute train/val 모두 `attribute_packet`이다.
- Function train/val의 `type`은 `function_packet`이다.
- `split`은 파일과 record에서 모두 동일해야 한다.
- `text`는 비어 있지 않은 실제 UTF-8 한국어다.
- 한국어를 `\uXXXX` escape로 저장하지 않는다.
- `concepts`는 비어 있지 않은 문자열 배열이며 첫 항목이 primary concept다.
- primary concept는 전체 해당 split에서 중복시키지 않는 것을 원칙으로 한다.
- `relations`는 아래 13개 통제 어휘만 사용한다.
- 새 validation record에는 `unseen_relation` boolean이 반드시 존재한다.
- Function train record에는 `unseen_relation`을 붙이지 않는다.

---

## 9. Relations 통제 어휘 — 13개 고정

아래 목록 밖 이름을 만들지 않는다.

| relation | 의미 |
|---|---|
| `is_a` | 이 개념이 속하는 상위 범주 |
| `subclass_of` | 이 개념의 하위 범주 |
| `part_of` | 부분과 전체의 관계 |
| `classification` | 어떤 분류 체계 안에서의 위치 |
| `boundary` | 혼동하기 쉬운 다른 개념과의 경계 |
| `contrast` | 명시적으로 대비되는 다른 개념 |
| `comparison` | 정도나 크기의 비교 |
| `function` | 이 개념이 하는 일 |
| `role` | 사람이나 사물이 맡는 역할 |
| `process` | 시간에 따른 과정이나 변화 |
| `state` | 어떤 시점의 상태 |
| `attribute` | 속성, 성질, 측정값 |
| `other` | 위 12개 중 어디에도 맞지 않는 경우 |

강제 규칙:

1. 목록 밖 이름을 새로 만들지 않는다.
2. `concept_boundary`, `temporal_boundary`, `entity_boundary`는 모두 `boundary`다.
3. `function_or_role`을 쓰지 말고 실제 의미에 따라 `function` 또는 `role` 하나를 고른다.
4. `subtype`은 `subclass_of`다.
5. 애매하면 `other`를 사용한다. `other`가 많다는 사실은 오류가 아니다.
6. 한 record의 relations는 2~5개다.
7. 한 record 안에서 같은 relation 이름을 두 번 쓰지 않는다.
8. relation 이름은 text의 실제 의미와 일치해야 한다. 수량만 맞추기 위해 붙이지 않는다.

과거 문서에 있던 `degree`, `measurement`, `sensitivity`, `variability`, `capability`, `threshold` 등 자유 relation 이름은 현재 금지다. 의미에 따라 `comparison`, `attribute`, `process`, `function`, `boundary`, `other` 등으로 보수적으로 매핑한다.

---

## 10. Attribute corpus의 의미 경계

Attribute는 기본적으로 다음 질문에 답한다.

> 이것은 어떤가?

또는:

> 이 특성이 어느 정도인가?

> 조건이 바뀌면 이 특성이 어떻게 달라지는가?

반드시 구별할 것:

```text
정체성          무엇인가
속성            어떤가
상태            지금 어떤 상태인가
관계            다른 대상과 어떻게 연결되는가
측정값          관측된 수치가 얼마인가
변화율          시간·조건당 얼마나 변하는가
민감도          작은 조건 변화에 얼마나 크게 반응하는가
능력            어떤 기능을 수행할 수 있는가
성향            특정 행동·반응을 보이기 쉬운가
```

예:

```text
내열성           성질
현재 노출온도    조건값
열화속도         시간 변화율
온도민감도       온도 변화에 대한 반응 기울기
복구가능성       회복 성공의 개연성
복구속도         정상 범위로 돌아오는 빠르기
```

상관과 동일성, 공존과 정의, 속성과 필요조건을 혼동하지 않는다. 가능한 경우 positive 사례, 조건, 경계 또는 반례를 자연스럽게 포함한다.

---

## 11. `text` 작성 규약

### 11.1 의미 문장은 모델이 직접 개별 작성

금지:

- Python loop와 문장 template로 의미 문구 생성
- concept 이름이나 접미사만 바꾼 대량 문장
- 동일한 2~3문장 골격의 반복
- 기존 train 문장을 단어 몇 개만 바꾸어 val에 재사용
- 유사도 검사를 피하려고 무의미한 단어를 삽입

허용되는 자동화:

- ID 부여
- JSON 포장과 UTF-8 직렬화
- record 수와 range 계산
- relation 분포 집계
- 중복·n-gram·유사도·조사 검사
- train/val leakage 검사

즉, 자동화는 **형식과 검증**에만 사용하고 `text`의 의미 내용은 concept별로 직접 작성한다.

### 11.2 사전식 정의만 반복하지 않음

비권장:

> X란 Y를 의미한다.

권장 방향:

- 실제 대상과 상황에서 속성이 드러나는 사례
- 같은 대상이라도 조건에 따라 정도가 달라지는 경우
- 현재 수준과 변화율의 차이
- 인접 concept와의 경계
- 측정값과 성질 자체의 차이

정의가 필요하면 쓸 수 있으나 corpus 전체가 같은 정의문 형식이 되어서는 안 된다.

### 11.3 문장 구조 다양화

- concept 이름을 항상 첫 단어로 놓지 않는다.
- 사례→해석, 비교→경계, 조건→결과, 관찰→판정 등 담화 순서를 섞는다.
- 1~3문장을 자연스럽게 사용한다. 문장 수를 기계적으로 맞추지 않는다.
- 같은 연결어와 종결문을 반복하지 않는다.
- 대상 도메인을 재료, 생물, 신호, 환경, 조직, 구조, 행동 등으로 적절히 다양화한다.

### 11.4 한국어 품질

- 은/는, 이/가, 을/를, 과/와, 으로/로를 받침에 맞게 쓴다.
- concept 뒤의 조사를 특히 확인한다.
- `정도은`, `민감도은` 같은 오류는 0건이어야 한다.
- 뜻이 모호한 과도한 명사 결합을 피한다.
- 번역투나 어색한 피동 표현을 반복하지 않는다.

---

## 12. 150개 단위 concept-family 설계

한 파일을 만들기 전에 다음을 확정한다.

1. 이 버전의 상위 concept family는 무엇인가?
2. 직전 및 전체 과거 버전과 어떤 점에서 새로운가?
3. 150개 primary concept가 서로 실제로 다른 질문을 갖는가?
4. 정적 수준, 변화, 변동, 민감, 안정, 회복, 경계가 균형 있게 포함되는가?
5. 특정 접미사 3종만 반복하여 150개를 채우지 않았는가?

한 concept family 안에서도 하위 축을 5~10개 정도로 나누고 실제 현상·측정·경계를 달리한다. 새 버전이 이전 버전의 동의어 목록이 되지 않게 한다.

---

## 13. 현재 Attribute train 정본 상태

설계 기준:

```text
속성·정도·변이 전체 420K
train 고밀도 목표 약 378K = 4,650 packet
validation 목표 약 42K = 600 packet
```

packet 수는 설계 환산 기준이며 실제 tokenizer token 수와 동일하다고 단정하지 않는다. 최종 보고에서는 packet 기준과 실제 tokenizer 측정 여부를 분리해 적는다.

### Train v01~v31

| 버전 | ID 범위 | 주요 concept family | 수량 |
|---|---|---|---:|
| v01 | 0001~0150 | 물리·감각 속성, 크기·형상·기초 통계·활성 | 150 |
| v02 | 0151~0300 | 능력·성능·행동·효율·책임·복원 | 150 |
| v03 | 0301~0450 | 생존·성장·생태 적응·번식·이동·반응 | 150 |
| v04 | 0451~0600 | 신뢰·추론·계획·자기조절·사회 행동 | 150 |
| v05 | 0601~0750 | 언어 명료성·모호성·정중성·응집성·정보밀도 | 150 |
| v06 | 0751~0900 | 물질 속성의 환경 의존·변화율·민감도·회복률 | 150 |
| v07 | 0901~1050 | 공간·시간·환경 변화에 따른 성능과 적응폭 | 150 |
| v08 | 1051~1200 | 열화·손상·고장·복구·잔여수명 | 150 |
| v09 | 1201~1350 | 측정·평가 정확성·신뢰도·타당도·오차 | 150 |
| v10 | 1351~1500 | 자원·용량·부하·효율·한계·최적화 | 150 |
| v11 | 1501~1650 | 확률·분포·변동·극값·위험·신뢰 구간 | 150 |
| v12 | 1651~1800 | 변화 방향·속도·가속·주기·수렴·안정화 | 150 |
| v13 | 1801~1950 | 정보·데이터·신호 품질·손실·잡음·지연 | 150 |
| v14 | 1951~2100 | 상호작용·상관·결합·간섭·호환·경쟁 | 150 |
| v15 | 2101~2250 | 결정·선택·우선순위·목표·제약·전략 | 150 |
| v16 | 2251~2400 | 구조·복잡성·연결성·계층성·밀도·규모 | 150 |
| v17 | 2401~2550 | 규칙·패턴·질서·순서·불변성·일탈 | 150 |
| v18 | 2551~2700 | 역치·임계 전이·포화·응답 크기·시간 응답 | 150 |
| v19 | 2701~2850 | 관측·검출·식별·구별·추정·추적 | 150 |
| v20 | 2851~3000 | 제어·피드백·조절·목표추종·구동 보정 | 150 |
| v21 | 3001~3150 | 강건성·복원탄력성·결함허용·운영연속성 | 150 |
| v22 | 3151~3300 | 학습·적응·일반화·전이·유지·망각 | 150 |
| v23 | 3301~3450 | 접근성·사용성·가독성·인지부담·표출성 | 150 |
| v24 | 3451~3600 | 모듈성·결합·응집·상호운용·대체·재구성 | 150 |
| v25 | 3601~3750 | 가역·비가역·경로의존·이력·잔류·복귀 | 150 |
| v26 | 3751~3900 | 평형·균형·항상성·보존·유입유출 수지 | 150 |
| v27 | 3901~4050 | 투과·확산·전달·운반·흐름·차단·여과 | 150 |
| v28 | 4051~4200 | 동기화·협응·정렬·위상·타이밍·합의 | 150 |
| v29 | 4201~4350 | 운전 규모·병렬 처리·분산 운영·부하 분배 | 150 |
| v30 | 4351~4500 | 공정성·대표성·편향·포용성·형평성 | 150 |
| v31 | 4501~4650 | 설명·해석·투명성·감사·근거 문서화 | 150 |
| **합계** | **0001~4650** | **31개 파일** | **4,650** |

### 최신 train 감사 기준

전체 v01~v31 감사에서 다음 값이 확정되었다.

- JSON·UTF-8 실패 0
- ID 불연속·중복 0
- 메타데이터 오류 0
- record schema 오류 0
- exact text 중복 0
- primary concept 중복 0
- 반복 5어절 0
- 반복 4어절 도입부 0
- 조사 후보 0
- relations 규칙 오류 0
- 전체 최고 문자 3~5-gram TF-IDF cosine 0.499366

정본 감사 파일:

```text
TinyLM_Stage1_Attribute_Train_v01_v31_Full_Audit_2026-08-30.json
TinyLM_Stage1_Attribute_Train_v18_v31_Final_Audit_2026-08-30.md
```

---

## 14. Attribute validation 600개 분리 규칙

현재 목표:

```text
약 42K tokens 설계 대응
600 records
4 files × 150 records
train 4,650개의 약 12.90% record 수
```

### V1. 주 validation 관계

원칙적으로 train에서 이미 학습한 relation을 사용한다. 현재 attribute train v01~v31에는 통제 어휘 13개가 모두 한 번 이상 등장한다. `unseen_relation: false`인 record는 train에서 실제 관측된 **relations 집합 조합**을 사용한다.

### V2. 일반화 slice 10~15%

전체 validation의 10~15%는 `unseen_relation: true`로 표시한다.

현재 train에는 13개 relation 이름이 모두 이미 있으므로, 통제 어휘 밖의 새 relation 이름을 만들면서 V2를 만족시키는 것은 불가능하다. 따라서 현재 attribute validation에서는 다음처럼 정의한다.

> `unseen_relation: true` = 각 relation 이름은 train에서 보았지만, 그 record의 정규화된 relations 집합 조합은 train v01~v31에 한 번도 없었던 compositional unseen 관계.

예를 들어 `attribute + classification + process + state`가 train에 하나도 없었다면 이 조합을 가진 val record는 true다. relation 순서만 바꾼 것은 새 조합으로 보지 않는다.

확정 결과:

```text
unseen_relation true  = 72 / 600 = 12.00%
unseen_relation false = 528 / 600 = 88.00%
파일별 true           = 18 / 150 = 12.00%
```

이 해석은 13개 통제 어휘 규칙과 V2를 동시에 지키기 위한 현행 규약이다. 향후 train 어휘 상태가 달라지면 생성 전에 다시 실측하고 문서화한다.

### V3. 실제 비율 보고

작업 후 다음을 반드시 보고한다.

- 전체 true/false 개수와 비율
- 파일별 true/false 개수와 비율
- true record의 고유 unseen relation-set 조합 수
- false record의 relation-set이 모두 train에서 관측되었는지
- true record의 relation-set이 모두 train에서 미관측이었는지

### Train과 validation의 분리

새 val은 다음을 모두 피한다.

- train과 정확히 같은 `text`
- train 문장의 단순 바꿔쓰기
- train primary concept 재사용
- 같은 primary concept와 같은 relation-set의 객체–관계 조합
- train의 5어절 이상 문구 복제
- held-out 문장이나 정답 구조 복사

현재 작업에서는 새 concept family를 사용해 primary concept를 train과 완전히 분리한다. 객체–관계 조합은 `(primary concept, 정렬된 relations 집합)`으로 감사한다.

---

## 15. Validation concept-family 선정 원칙

Validation은 train의 같은 문장을 다시 묻는 데이터가 아니다. train에서 배운 속성·정도·변이의 종류를 **새로운 concept family와 대상**에 적용하는 능력을 본다.

선정 기준:

1. train v01~v31의 주요 family와 직접 중복하지 않는다.
2. 새 분야에서도 수준, 변화, 변동, 민감, 안정, 경계가 나타나야 한다.
3. 한 파일 안에서 너무 넓게 흩어지지 않는다.
4. 서로 다른 네 파일은 concept family가 겹치지 않는다.
5. primary concept 문자열은 train과 val 전체에서 중복 0을 목표로 한다.
6. train보다 더 어려운 대상에 적용할 수 있으나 held-out만큼 공격적인 완전 미지 task로 만들지는 않는다.

현재 600개 확정 family:

| val 버전 | 새 개념군 | 핵심 일반화 축 |
|---|---|---|
| v01 | 토양·지질·지형·수문 반응 특성 | 물성, 공간 편차, 침식, 수분 이동, 지형 안정 |
| v02 | 식품·조리·발효·저장 품질 특성 | 관능 속성, 공정 변화, 숙성, 보존, 복원·열화 |
| v03 | 건축·실내환경·도시 미기후 특성 | 열·빛·음향·공기질·동선·공간 쾌적성 |
| v04 | 해양·연안·수생환경 특성 | 염분·탁도·파랑·퇴적·혼합·서식환경 변동 |

### 현재 validation v01~v04 정본 감사

2026-08-30 최종 재감사 기준:

- 4개 파일, 각 150개, 합계 600개
- ID `S1-ATV-0001`~`S1-ATV-0600` 연속
- JSON·UTF-8·metadata·schema·relation 규칙 오류 0
- `unseen_relation: true` 72개, false 528개, 실제 비율 12.00%
- 파일별 true 18/150 = 12.00%
- true 고유 미관측 relation-set 12종, false 고유 train 관측 relation-set 22종
- train–val exact text, primary concept, 객체–관계 조합 교집합 모두 0
- validation 내부 및 train–val 공통 반복 5어절 0
- 반복 4어절 도입부 0, primary concept 직후 조사 오류 0
- validation 내부 최고 문자 3~5-gram TF-IDF cosine 0.383657
- train–val 최고 cosine 0.311535

현재 relations 전체 분포는 `is_a` 3, `subclass_of` 4, `part_of` 49, `classification` 71, `boundary` 300, `contrast` 44, `comparison` 278, `function` 90, `role` 27, `process` 207, `state` 138, `attribute` 600, `other` 52다. `other` 52개는 조건·입력 의존/영향/선택성 22, 공간·시간 집중/분포/편향 12, 구조 저항/상태 분류/형태적 기타 7, 복합 감각/물질 이동·혼합/수용 6, 잠재성/불확실성/위험 추정 5개로 편집 분류했다.

정본 산출물:

```text
val/stage1_(2)attribute_high_density_val_v01.json
val/stage1_(2)attribute_high_density_val_v02.json
val/stage1_(2)attribute_high_density_val_v03.json
val/stage1_(2)attribute_high_density_val_v04.json
TinyLM_Stage1_Attribute_Validation_v01_v04_Audit_2026-08-30.json
TinyLM_Stage1_Attribute_Validation_v01_v04_Final_Report_2026-08-30.md
```

---

## 16. Validation과 held-out의 차이

Validation에서 새 concept와 일부 unseen relation composition을 사용하는 것은 허용되지만 다음 차이를 유지한다.

| 항목 | Validation | Held-out |
|---|---|---|
| 사용 시점 | 학습 중 | 최종 모델 확정 후 |
| checkpoint 선택 | 가능 | 금지 |
| 반복 확인 | 가능 | 최소화 |
| gradient update | 금지 | 금지 |
| unseen 강도 | 제한적 | 더 엄격한 blind 일반화 |
| 결과를 보고 corpus 수정 | 가능하지만 val 적응으로 기록 | 하면 새 blind benchmark 필요 |

Validation과 held-out을 같은 폴더나 loader로 합치지 않는다.

Held-out의 대표 축은 `unseen concept`, `novel relation`, `boundary / counterexample`다. 단, `unseen`은 고정된 이름표가 아니라 당시 train 정본과의 교집합으로 판정한다. train corpus가 바뀌면 held-out의 unseen concept·relation 상태를 전부 다시 감사해야 한다.

---

## 17. 자동 감사 필수 항목

### 구조·직렬화

- JSON parse 성공
- UTF-8 decode 성공
- 한글 `\uXXXX` escape 0
- 파일명, version, split 일치
- 각 파일 record 150
- 전체 목표 record 수 일치
- ID 형식·연속·범위·중복 검사
- type과 split 검사
- 빈 text/concepts/relations 0

### Relations

- 13개 통제 어휘 밖 이름 0
- record당 2~5개
- record 안 relation 중복 0
- 13개 각각의 전체·파일별 분포
- `other` record의 반복 개념 유형 상위 5개

### Text와 concept 품질

- exact text 중복 0
- primary concept 중복 0
- 서로 다른 record의 동일 5어절 구절 0 목표
- 동일 4어절 도입부 0 목표
- 일반 조사·concept 직후 조사 후보 0 목표
- 문자 3~5-gram TF-IDF cosine 상위 pair 수동 검토
- 권장 최고 유사도 0.55 미만, 0.45 이상 쌍은 의미상 독립 여부 확인
- 문장 수와 문자 길이 분포
- 보일러플레이트 cluster 수동 분석

### Train–validation leakage

- ID 교집합 0
- exact text 교집합 0
- primary concept 교집합 0
- `(primary concept, relation-set)` 교집합 0
- train-val 공통 5어절 구절 확인
- 필요하면 상위 cross-split similarity pair 수동 검토

### Validation unseen slice

- `unseen_relation` 필드 누락 0
- boolean 외 값 0
- true 비율 10~15%
- false relation-set은 train seen
- true relation-set은 train unseen
- relation 순서를 무시한 set 기준으로 판정

유사도 도구는 자동 수정기가 아니다. 검출 record는 의미를 유지한 채 모델이 다시 직접 작성한다.

---

## 18. 생성 후 보고 형식

최종 보고에는 최소 다음 내용을 포함한다.

### 18.1 파일·누적 표

| 버전 | 파일명 | ID 범위 | 개념군 | 수량 | 누적 |
|---|---|---|---|---:|---:|

### 18.2 구조 감사

```text
file count
record count
JSON/UTF-8 failures
metadata/schema errors
ID gaps/duplicates
empty text
exact text duplicates
primary concept duplicates
5-word repeated phrases
4-word repeated openings
particle candidates
maximum similarity
```

### 18.3 Relations 분포

13개 이름을 0회인 항목도 빼지 말고 모두 보고한다.

```text
is_a
subclass_of
part_of
classification
boundary
contrast
comparison
function
role
process
state
attribute
other
```

`other`가 있는 경우 자주 나온 concept 유형 5개와 횟수, 예시를 보고한다. 분류 규칙과 이질적 remainder도 밝힌다.

### 18.4 Validation 전용 보고

```text
unseen_relation true / false count
actual unseen ratio
file-by-file ratio
unique unseen relation-set count
train-val exact text overlap
train-val primary concept overlap
train-val object-relation overlap
cross-split repeated phrase / similarity result
```

### 18.5 무결성

- 수정 금지 파일의 시작·종료 SHA-256 비교
- 사용자가 요청한 범위 밖 파일을 건드리지 않았는지
- 별도 프로세스가 만든 unrelated 변경은 보존했는지

---

## 19. 작업 순서

1. 사용자 지시와 이 지침서를 읽는다.
2. 실제 train/val 파일 목록과 Git 상태를 확인한다.
3. 수정 금지 파일의 SHA-256 기준을 저장한다.
4. 기존 concept·text·relation-set을 모두 인덱싱한다.
5. 새 concept family와 ID 범위, relation 분리를 먼저 설계한다.
6. primary concept와 `text`를 모델이 개별 작성한다.
7. 자동화로 JSON 구조만 포장한다.
8. 같은 감사기를 전체 split과 cross-split에 실행한다.
9. 검출된 문장은 직접 보정하고 감사를 반복한다.
10. 감사 JSON과 Markdown 보고서를 만든다.
11. 수정 금지 파일 SHA-256을 다시 비교한다.
12. 누적 표, relations 13개 분포, `other` 유형, unseen 비율을 사용자에게 보고한다.

현재 attribute validation v01~v04를 repository root에서 재포장·재감사하는 명령은 다음과 같다.

```powershell
python stage1_highdensity_dataset\tools\build_attribute_validation.py stage1_highdensity_dataset
python stage1_highdensity_dataset\tools\audit_attribute_validation.py stage1_highdensity_dataset --output stage1_highdensity_dataset\TinyLM_Stage1_Attribute_Validation_v01_v04_Audit_2026-08-30.json --similarity-limit 60
```

첫 명령은 source 안의 직접 작성 literal을 JSON으로 포장한다. 두 번째 명령은 읽기 전용 감사다. 미래 버전을 만들 때 기존 600개 literal을 template로 복제하지 말고 새 concept family와 문장을 직접 추가한 뒤 감사 범위를 확장한다.

---

## 20. Stage 1 Function train 324K 생성 규약과 27개 예약 concept family

### 20.1 목표와 의미 경계

```text
영역: Stage 1 (3) 기능·용도·목적
train 설계량: 약 324K tokens
packet 목표: 4,050 records
파일 목표: 27 files × 150 records
파일명: stage1_(3)function_high_density_train_v00.json 형식
ID: S1-FNH-0001 ~ S1-FNH-4050
```

packet 수는 설계 환산 기준이며 실제 tokenizer token 수와 동일하다고 단정하지 않는다. Function corpus는 다음 질문을 중심으로 한다.

```text
무엇을 하는가?
무엇에 사용하는가?
어떤 결과를 만들기 위해 존재하는가?
어떤 조건에서는 그 기능을 수행하지 못하거나 다른 도구와 역할이 갈리는가?
```

모든 record는 `function` relation을 반드시 포함하고 통제 어휘에서 1~4개를 더 골라 총 2~5개로 만든다. `use_for`, `used_to`, `purpose`, `enables`, `protect`, `transport`, `contain` 같은 자유 relation 이름을 만들지 않는다.

- `function`: 대상이 수행하는 작용이나 설계 목적
- `role`: 특정 작업·시스템·상황에서 맡는 몫
- `process`: 기능이 시간 순서나 변화 과정으로 구현됨
- `part_of`: 부품 기능이 더 큰 장치·절차의 일부임
- `boundary`: 비슷한 도구와의 용도 경계 또는 수행하지 않는 일
- `comparison`·`contrast`: 대안 도구와 성능·용도 차이를 실제로 서술함
- `state`: 작동·대기·잠금·해제처럼 현재 상태가 기능을 바꿈
- `attribute`: 재료·형상·구조 특성이 기능 수행에 직접 기여함
- `classification`, `is_a`, `subclass_of`: 실제 분류 문장이 있을 때만 사용함
- `other`: 나머지 12개로 정직하게 표현할 수 없는 관계만 보수적으로 표시함

단순히 `X는 Y에 사용된다`만 4,050번 반복하지 않는다. 대상, 입력, 작용, 결과, 조건, 경계 가운데 필요한 요소를 자연스럽게 조합하고, 기능과 우연한 사용 사례를 구분한다. 자동화는 ID·JSON 포장·감사에만 사용하며 의미 `text`와 primary concept는 record별로 직접 작성한다.

기존 `stage1_dataset`의 저밀도 `S1-FUNC-*` prototype은 참고·중복 검사 대상으로만 사용한다. exact text는 재사용하지 않고, 가능한 경우 primary concept도 더 구체적인 대상이나 부품으로 이동한다. 고밀도 Function split 안에서는 primary concept 중복 0을 유지한다.

### 20.2 27개 concept family 예약표

아래 표는 context 압축이나 새 세션에서도 버전 주제가 재선정되지 않게 하는 확정 원장이다. v01~v27은 모두 생성·감사를 마쳤으므로 임의로 family를 바꾸거나 다시 생성하지 않는다. 변경 권한이 새로 주어지더라도 기존 전체 concept·text와 보호 파일 해시를 먼저 감사하고 이유와 대체 범위를 이 표에 기록한다.

| 버전 | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 수동 작업·정비·제작 공구의 기능 | 체결, 파지, 절단, 성형, 표면 마감, 타격, 인출, 천공, 나사 가공 | 확정 (2026-08-30) |
| v02 | 0151~0300 | 식재료 준비·조리·제공 기구의 기능 | 세척, 계량, 분할, 혼합, 성형, 가열, 뒤집기, 따르기, 제공 | 확정 (2026-08-30) |
| v03 | 0301~0450 | 식품 보존·포장·위생·품질 관리 장치의 기능 | 냉장·냉동, 건조, 밀봉, 살균, 표시, 산소·수분 차단, 검사 | 확정 (2026-08-30) |
| v04 | 0451~0600 | 의복·신발·착용 보호·휴대 구성품의 기능 | 체온 조절, 충격·날씨 보호, 여밈, 지지, 수납, 착용 조절 | 확정 (2026-08-30) |
| v05 | 0601~0750 | 청소·세탁·건조·생활 폐기물 처리 도구의 기능 | 포집, 분리, 세정, 탈수, 건조, 탈취, 압축, 배출 | 확정 (2026-08-30) |
| v06 | 0751~0900 | 건물 외피·개구부·실내 마감·공간 조절 구성품의 기능 | 지지, 차폐, 채광, 출입, 단열, 방수, 흡음, 공간 분할 | 확정 (2026-08-30) |
| v07 | 0901~1050 | 급배수·위생·환기·냉난방 실내 설비의 기능 | 공급, 배출, 여과, 열교환, 압력 조절, 공기 순환, 위생 유지 | 확정 (2026-08-30) |
| v08 | 1051~1200 | 농림·축산·수산 생산 도구와 설비의 기능 | 토양 준비, 파종, 관개, 급이, 보호, 수확, 양식, 어획 | 확정 (2026-08-30) |
| v09 | 1201~1350 | 육상·항공·해상 교통수단과 부품의 기능 | 추진, 조향, 제동, 현가, 부양, 항법, 계류, 탑승자 보호 | 확정 (2026-08-30) |
| v10 | 1351~1500 | 포장·하역·운반·분류·보관 물류 장비의 기능 | 적재, 결속, 완충, 이송, 승강, 분류, 추적, 재고 보존 | 확정 (2026-08-30) |
| v11 | 1501~1650 | 제조 성형·절삭·접합·조립 생산 설비의 기능 | 주조, 압연, 절삭, 연삭, 용접, 체결, 정렬, 자동 조립 | 확정 (2026-08-30) |
| v12 | 1651~1800 | 품질검사·공정제어·설비진단·유지보수 장치의 기능 | 검출, 비교, 피드백, 보정, 윤활, 진단, 교체, 안전 정지 | 확정 (2026-08-30) |
| v13 | 1801~1950 | 도로·교량·철도·터널·배수 공공 인프라의 기능 | 하중 전달, 통행 유도, 선형 유지, 배수, 환기, 충돌 방호 | 확정 (2026-08-30) |
| v14 | 1951~2100 | 물 공급·하수처리·위생·자원회수 도시 서비스의 기능 | 취수, 정수, 저장, 압송, 침전, 소독, 슬러지 처리, 회수 | 확정 (2026-08-30) |
| v15 | 2101~2250 | 에너지 생산·변환·저장·송배전·보호 장치의 기능 | 발전, 변압, 정류, 축전, 열저장, 개폐, 차단, 계통 보호 | 확정 (2026-08-30) |
| v16 | 2251~2400 | 전자회로·센서·신호처리·구동 부품의 기능 | 감지, 변환, 증폭, 필터링, 발진, 스위칭, 구동, 피드백 | 확정 (2026-08-30) |
| v17 | 2401~2550 | 컴퓨팅 처리·기억·저장·입출력 장치의 기능 | 연산, 명령 제어, 캐시, 영구 저장, 입력, 표시, 주변장치 연결 | 확정 (2026-08-30) |
| v18 | 2551~2700 | 네트워크·소프트웨어·데이터 서비스의 기능 | 주소 지정, 라우팅, 인증, 직렬화, 검색, 동기화, 백업, 복구 | 확정 (2026-08-30) |
| v19 | 2701~2850 | 통신·미디어 기록·편집·전송·표현 도구의 기능 | 촬영, 녹음, 부호화, 편집, 송수신, 재생, 자막, 배포 | 확정 (2026-08-30) |
| v20 | 2851~3000 | 실험실 채취·분리·반응·계량·교정 장비의 기능 | 시료 채취, 여과, 원심분리, 배양, 적정, 검출, 표준화 | 확정 (2026-08-30) |
| v21 | 3001~3150 | 의료 진단·치료·모니터링·재활·감염관리 기구의 기능 | 관찰, 검사, 투약, 절개, 봉합, 생체신호 감시, 재활 보조, 멸균 | 확정 (2026-08-30) |
| v22 | 3151~3300 | 생물 기관·세포 구조·생태계 구성원의 기능 | 흡수, 수송, 호흡, 방어, 감각, 번식, 분해, 서식처 제공 | 확정 (2026-08-30) |
| v23 | 3301~3450 | 환경 감시·오염 정화·자원 순환·생태 복원 시설의 기능 | 대기·수질 감시, 집진, 흡착, 중화, 재활용, 서식처 복원 | 확정 (2026-08-30) |
| v24 | 3451~3600 | 안전·재난·보안·구조·접근성 보조 장치의 기능 | 경보, 차단, 대피, 소화, 구조, 신원 확인, 침입 방지, 감각·이동 보조 | 확정 (2026-08-30) |
| v25 | 3601~3750 | 교육·학습·도서관·문서화 도구의 기능 | 설명, 연습, 평가, 색인, 인용, 기록, 버전 관리, 지식 검색 | 확정 (2026-08-30) |
| v26 | 3751~3900 | 상업·금융·거래·고객 서비스 체계의 기능 | 가격 제시, 주문, 결제, 정산, 신용 평가, 환불, 상담, 분쟁 접수 | 확정 (2026-08-30) |
| v27 | 3901~4050 | 공공행정·법률·복지·지역사회·문화 서비스의 기능 | 신청, 심사, 허가, 권리 보호, 돌봄 연계, 공공 안내, 보존, 참여 지원 | 확정 (2026-08-30) |

### 20.3 v01~v27 확정 누적과 감사 기준점

2026-08-30 생성·재개·최종 재감사에서 다음 정본을 확정했다.

```text
파일: train/stage1_(3)function_high_density_train_v01.json ~ v27.json
record: 4,050
ID: S1-FNH-0001 ~ S1-FNH-4050
현재 누적: 4,050 / 4,050 records, 27 / 27 files
잔여: 0 records, 0 files
상태: Function train v01~v27 완료·수정 금지
```

v02~v27의 3,900개와 기존 v01의 150개는 primary concept와 `text`를 record별 직접 작성했다. 자동화는 literal의 ID·metadata·JSON 포장과 읽기 전용 감사에만 사용했다. 전체 감사 결과 JSON·UTF-8·schema·metadata·ID·relations 오류, exact ID/concept/text 중복, 반복 5어절, 반복 도입부, 실제 조사 오류는 모두 0이다. 문자 3~5-gram TF-IDF 기준 내부 최대 유사도는 `0.357568`, 저밀도 `S1-FUNC-*` 120개와의 교차 최대 유사도는 `0.211338`이다. prototype과 exact primary concept·exact text·반복 5어절 교집합도 모두 0이다.

`text` 합계는 253,352자이고 `[0-9A-Za-z가-힣]+` 기준 공백·문장부호 분리 단위는 61,667개다. 약 324K tokens는 4,050-record 설계 환산량이며, 실제 학습 tokenizer가 정해지기 전에는 모델 token 수로 표현하지 않는다.

| relation | v01~v27 횟수 | relation | v01~v27 횟수 |
|---|---:|---|---:|
| `is_a` | 2 | `subclass_of` | 42 |
| `part_of` | 340 | `classification` | 187 |
| `boundary` | 526 | `contrast` | 10 |
| `comparison` | 224 | `function` | 4,050 |
| `role` | 1,036 | `process` | 1,144 |
| `state` | 779 | `attribute` | 488 |
| `other` | 0 |  |  |

`other`는 0건이므로 자주 나온 개념 유형 5가지는 해당 없음이다. 12개 명명 관계로 정직하게 설명되는 사례에 `other`를 억지로 붙이지 않았으며, 어느 관계에도 맞지 않는 향후 사례가 생기면 0을 유지하려고 왜곡하지 않는다.

정본 감사 파일은 `TinyLM_Stage1_Function_Train_v01_v27_Full_Audit_2026-08-30.json`이고 최종 보고서는 `TinyLM_Stage1_Function_Train_v02_v27_Final_Audit_2026-08-30.md`다. 재현 명령은 repository root에서 실행한다. 인수로 `stage1_highdensity_dataset` 자체를 넘기면 경로가 한 번 더 중첩되므로 반드시 `.`을 사용한다.

```powershell
$env:PYTHONIOENCODING='utf-8'
python stage1_highdensity_dataset\tools\build_function_train_v02_v27.py .
python stage1_highdensity_dataset\tools\audit_function_corpus.py . --similarity-limit 500 --output stage1_highdensity_dataset\TinyLM_Stage1_Function_Train_v01_v27_Full_Audit_2026-08-30.json
```

### 20.4 누적·상태 갱신 규칙

한 파일이 생성·감사를 통과하면 해당 행의 상태를 `확정`으로 바꾸고 다음을 함께 기록한다.

- 실제 파일명과 SHA-256
- 150개 record와 ID 범위
- concept family와 하위 축
- 전체 누적과 4,050개 중 잔여 수
- relations 13개 전체·버전별 분포
- `other`의 자주 나온 개념 유형 5개
- exact text·primary concept·5어절·도입부·유사도·조사 감사 결과
- 저밀도 `S1-FUNC-*` prototype과의 exact text·primary concept 교집합
- 수정 금지 파일의 전후 해시 일치 여부

현재 Function 예약표에는 `reserved`가 남아 있지 않다. 새 세션은 Function v02부터 다시 시작하지 않으며, 다음 영역은 사용자의 명시적 지시와 별도 concept-family 원장을 받은 뒤에만 착수한다.

---

## 21. 수정 금지와 안전 규칙

- 사용자가 수정 금지한 영역은 열람·해시 계산 외에 쓰지 않는다.
- 현재 attribute 작업에서 `stage1_(1)identity_high_density_*` 파일은 수정하지 않는다.
- `stage1_(2)attribute_high_density_*` train·validation 확정 파일은 수정하지 않는다.
- 사용자 지시에 따라 `stage2_(2)attribute_high_density_*`와 일치하는 모든 확정 파일도 수정하지 않는다. 현재 경로에서 발견되지 않더라도 이름 패턴 자체를 보호 규칙으로 유지하고, 다른 위치가 연결되면 먼저 해시를 저장한 뒤 읽기 전용으로 취급한다.
- `stage1_(3)function_high_density_train_v01.json`~`v27.json`은 2026-08-30 최종 감사 통과 정본이므로 후속 corpus 작업에서 수정하지 않는다.
- held-out benchmark는 corpus source로 사용하지 않는다.
- dirty worktree의 사용자 변경과 외부 프로세스 산출물을 임의 정리하지 않는다.
- 임시 감사 파일은 최종 산출물과 구분하고 완료 후 제거한다.
- 전체 폴더를 재직렬화하거나 일괄 이동하지 않는다.

---

## 22. 현재 감사·연속성 산출물

현행 참고 파일:

```text
TinyLM_Stage1_Attribute_Train_v18_v31_Final_Audit_2026-08-30.md
TinyLM_Stage1_Attribute_Train_v01_v31_Full_Audit_2026-08-30.json
TinyLM_Stage1_Attribute_Train_v01_v17_Legacy_Audit_Before_Fix_2026-08-30.json
TinyLM_Stage1_Attribute_Train_v01_v17_Legacy_Audit_After_Fix_2026-08-30.json
TinyLM_Stage1_Attribute_Train_v18_v31_Audit_2026-08-30.json
TinyLM_Stage1_Attribute_Validation_v01_v04_Audit_2026-08-30.json
TinyLM_Stage1_Attribute_Validation_v01_v04_Final_Report_2026-08-30.md
train/stage1_(3)function_high_density_train_v01.json
train/stage1_(3)function_high_density_train_v02.json ... v27.json
tools/build_function_train.py
tools/build_function_train_v02_v27.py
tools/function_sources/v02.tsv ... v27.tsv
tools/audit_function_corpus.py
TinyLM_Stage1_Function_Train_v01_Audit_2026-08-30.json
TinyLM_Stage1_Function_Train_v01_Progress_Audit_2026-08-30.md
TinyLM_Stage1_Function_Train_v01_v27_Full_Audit_2026-08-30.json
TinyLM_Stage1_Function_Train_v02_v27_Final_Audit_2026-08-30.md
```

과거 `TinyLM_Stage1_Attribute_Train_Codex_Handoff_2026-08-30.md`의 v18 재작성 전 상태와 `TinyLM_Stage1_Stage7_Master_Continuity_Summary.md`의 v17 누적 수치는 역사적 handoff다. 현재 정본 상태는 실제 train v01~v31과 최신 감사 결과다.

---

## 23. 새 세션용 핵심 재개 지시

> 실제 파일을 먼저 감사하고, 한 파일 150개·새 concept family·13개 통제 relations·직접 작성 text·split 독립 규칙을 지킨다. 자동화는 포장과 검증에만 사용한다. 생성 후 JSON/ID/concept/text/n-gram/유사도/조사/relations 분포를 전수 검사하고, validation이면 train과의 exact text·primary concept·객체–관계 조합 및 10~15% `unseen_relation` 비율까지 보고한다. Identity, Attribute train·validation, Function train v01~v27은 모두 확정·수정 금지다. Function 4,050 records는 완료되었으므로 다시 생성하지 말고, 다음 corpus 영역은 사용자의 명시적 범위와 새 concept-family 원장을 확인한 뒤 착수한다.
