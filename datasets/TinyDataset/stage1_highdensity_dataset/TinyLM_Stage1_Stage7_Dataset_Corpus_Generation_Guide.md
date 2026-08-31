# TinyLM Stage 1~Stage 7 고밀도 데이터셋·Corpus 생성 작업지침서

- 문서 역할: 재사용 가능한 생성·분리·감사·보고 규칙의 정본
- 기준일: 2026-08-31 KST
- 짝 문서: `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`

이 문서는 특정 버전의 생성 이력이나 감사 수치를 보관하지 않는다. token 배분, 현재 완료 파일, ID 범위, 예약 concept family, relations 실측 분포, 감사 결과와 수정 금지 목록은 짝 문서인 데이터셋 설계서에서 관리한다. 새 corpus 작업자는 **작업지침서와 설계서를 모두 완독**한 뒤 실제 파일을 감사하고 시작한다.

## 1. 정본 우선순위와 허용 source

상태가 충돌할 때 우선순위는 다음과 같다.

1. 실제 고밀도 파일
2. 해당 고밀도 파일의 최신 감사 JSON
3. `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`
4. 이 작업지침서
5. 과거 handoff·요약 문서

생성 의미·schema·family의 정본은 고밀도 작업지침서와 고밀도 설계서다.

- 다른 밀도의 데이터셋을 예시, 문장 source, schema 근거, concept 후보, 중복·유사도 비교 기준으로 사용하지 않는다.
- 다른 밀도의 데이터셋에 임의의 기준 지위를 부여하지 않는다.
- held-out/benchmark는 생성 source나 corpus 교정 근거로 열람하지 않는다.
- 과거 handoff는 현재 상태 발견에만 보조적으로 쓰고 실제 파일과 최신 설계서를 덮어쓰지 않는다.
- 새 Stage·영역의 수치, ID, schema, split 비율은 설계서나 사용자 승인 없이 임의 확정하지 않는다.

## 2. 시작 전 필수 감사

작업을 시작할 때 다음 순서를 지킨다.

1. 작업지침서와 설계서를 완독한다.
2. 대상 영역·split의 실제 파일 목록, record 수, 마지막 ID와 마지막 확정 version을 조사한다.
3. 예약 concept-family 원장을 확인하고 이미 쓴 family를 다시 선택하지 않는다.
4. 설계서의 수정 금지 pattern을 실제 경로에 해석한다.
5. 보호 파일의 경로와 SHA-256 기준선을 저장한다.
6. `git status --short`로 기존 사용자 변경과 외부 산출물을 기록한다.
7. 대상 영역의 기존 고밀도 파일에서 schema·relation-set·ID 관례를 실측한다.
8. source 원고, builder, audit 출력의 위치를 확정한다.

중단 재개 시 파일명만 보고 추정하지 않는다. 실제 source 행 수, 생성 JSON, 감사 결과를 함께 대조해 마지막 완료 지점을 결정한다.

## 3. 정보 유형과 과잉 일반화 억제

고밀도 corpus는 다음 정보 유형을 섞어 동일한 것으로 가르치지 않는다.

- 정체성: `고양이는 동물이다`
- 속성: `고양이는 민첩하다`
- 상태: `문이 열려 있다`
- 기능: `필터는 입자를 거른다`
- 관계: `바퀴는 자전거의 일부다`
- 공간: `컵은 상자 안에 있다`
- 행동: `사람이 문을 연다`
- 수량: `상자에 공이 세 개 있다`

다음 과잉 일반화는 명시적으로 억제한다.

```text
A와 B가 함께 등장한다 → A와 B는 같다
A에서 B가 흔하다 → B는 A의 정의다
A가 속성 B를 가진다 → B를 가진 것은 모두 A다
A는 대체로 B다 → A는 언제나 B다
```

가능한 경우 positive example, counterexample, boundary, condition을 자연스럽게 조합한다. 흔한 특징과 필요조건, 상관과 인과, 공존과 동일성, 상태와 정체성을 구분한다.

## 4. Split의 역할과 절대 경계

### Train

- gradient update에 사용한다.
- validation·held-out record를 섞지 않는다.
- 확정 뒤 validation 결과를 보고 train 문장을 고치면 split 오염 여부를 별도로 기록한다.

### Validation

- gradient update에 사용하지 않는다.
- train과 같은 causal-LM loss/perplexity, paired likelihood 또는 구조 scorer에 사용한다.
- checkpoint·epoch·학습 종료·사전 지정 hyperparameter 선택에 쓸 수 있다.
- 반복해서 본 validation은 최종 blind test가 아니다.

### Held-out / Benchmark

- final model과 평가 절차를 고정한 뒤에만 사용한다.
- gradient, checkpoint 선택, hyperparameter 조정, corpus 수정 근거로 사용하지 않는다.
- 결과를 보고 조건을 바꾸면 새 blind benchmark가 필요하다.

```text
TRAIN → VALIDATION → CHECKPOINT SELECTION → FINAL MODEL FIXED → HELD-OUT
```

기본 학습 입력에는 `text`만 제공한다. `id`, `type`, `concepts`, `relations`, `unseen_relation`은 감사·균형·오류 분석 metadata이며 명시적 실험 설계 없이 tokenizer 입력에 붙이지 않는다.

## 5. 디렉터리와 파일명 규약

기준 구조:

```text
stage1_highdensity_dataset/
├── train/
├── val/
├── tools/
├── tools/<area>_sources/
├── TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md
└── TinyLM_Stage1_Stage7_Dataset_Design_Spec.md
```

영역 slug:

```text
(1) identity  = 대상·정체성·분류
(2) attribute = 속성·정도·변이
(3) function  = 기능·용도·목적
(4) boundary  = 개념 경계·반례
```

파일명 pattern:

```text
stage1_(N)<slug>_high_density_train_vNN.json
stage1_(N)<slug>_high_density_val_vNN.json
```

강제 규칙:

- version은 `v01`, `v02`처럼 두 자리 0-padding을 쓴다.
- 한 파일은 설계서에 다른 값이 명시되지 않는 한 정확히 150 records다.
- 150개를 넘기지 않고 다음 version으로 이동한다.
- 각 version은 예약표의 한 concept family만 담당한다.
- filename, top-level `version`, `split`, 영역 slug가 일치해야 한다.
- 새 영역 slug나 prefix는 설계서에 먼저 등록한 뒤 사용한다.

## 6. ID 규약

- train과 validation은 서로 다른 prefix를 쓴다.
- 영역마다 설계서에 등록된 prefix만 사용한다.
- 한 split의 ID는 파일 안·파일 사이에서 전역 오름차순 연속이어야 한다.
- ID를 재사용하거나 padding 폭을 중간에 바꾸지 않는다.
- top-level `range`는 실제 첫·마지막 ID와 일치해야 한다.
- legacy 정본의 ID 형식이 다르더라도 신규 영역 규약을 이유로 일괄 수정하지 않는다.

검사 항목:

```text
format valid
global sequence valid
duplicate ID = 0
declared range = actual range
train prefix != validation prefix
```

## 7. Top-level JSON schema

### Train

```json
{
  "dataset_name": "Korean AI Curriculum — Stage 1 <Area> High-Density Train 150 v01",
  "version": "1",
  "purpose": "해당 concept family의 학습 목적",
  "split": "train",
  "record_count": 150,
  "range": "S1-XXX-0001 ~ S1-XXX-0150",
  "concept_family": "설계서에 예약된 concept family",
  "design_note": "포함 축과 경계",
  "records": []
}
```

### Validation

```json
{
  "dataset_name": "Korean AI Curriculum — Stage 1 <Area> High-Density Validation 150 v01",
  "version": "1",
  "purpose": "새 concept family에서 일반화를 검증하는 목적",
  "split": "val",
  "record_count": 150,
  "range": "S1-XXV-0001 ~ S1-XXV-0150",
  "concept_family": "train과 분리된 concept family",
  "design_note": "일반화 축과 분리 기준",
  "generalization_slice": {
    "basis": "unseen_relation 판정 근거",
    "unseen_records": 18,
    "total_records": 150,
    "ratio": 0.12
  },
  "records": []
}
```

필수 검사:

- UTF-8 JSON parse 성공
- 한글을 `\uXXXX` escape로 직렬화하지 않음
- `record_count`와 실제 배열 길이 일치
- filename/version/split/range 일치
- `purpose`, `concept_family`, `design_note`와 실제 원고 일치
- validation slice 수치와 실제 boolean 집계 일치

## 8. Record schema

### Train record

```json
{
  "id": "S1-XXX-0001",
  "type": "<area>_packet",
  "split": "train",
  "text": "직접 작성한 한국어 의미 문장",
  "concepts": ["primary concept"],
  "relations": ["필수 relation", "보조 relation"]
}
```

### Validation record

```json
{
  "id": "S1-XXV-0001",
  "type": "<area>_packet",
  "split": "val",
  "text": "train과 분리된 새 문장",
  "concepts": ["primary concept"],
  "relations": ["필수 relation", "보조 relation"],
  "unseen_relation": false
}
```

공통 규칙:

- record key set은 해당 split schema와 정확히 일치한다.
- `type`은 영역에 등록된 `<area>_packet`이다.
- `split`은 top-level과 같다.
- `text`는 비어 있지 않은 실제 UTF-8 한국어다.
- `concepts`는 비어 있지 않은 문자열 배열이다.
- `concepts[0]`은 primary concept이며 해당 split에서 중복 0을 목표로 한다.
- primary concept는 문장에 명시적으로 나타나야 한다.
- 보조 concept를 쓰는 영역은 문장에 실제로 나타난 값만 넣고 record 내부 중복을 금지한다.
- train에는 `unseen_relation`을 붙이지 않는다.
- 새 validation에는 boolean `unseen_relation`을 반드시 붙인다.

영역별 필수 relation:

| 영역 | type | 모든 record의 필수 relation |
|---|---|---|
| Attribute | `attribute_packet` | `attribute` |
| Function | `function_packet` | `function` |
| Boundary | `boundary_packet` | `boundary` |

Identity legacy schema는 실제 정본을 따르며 다른 영역 schema로 일괄 변환하지 않는다.

## 9. Relations 통제 어휘 — 13개 고정

아래 이름 밖의 relation을 만들지 않는다.

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
2. `concept_boundary`, `temporal_boundary`, `entity_boundary`는 `boundary`다.
3. `function_or_role` 대신 실제 의미에 따라 `function` 또는 `role`을 고른다.
4. `subtype`은 `subclass_of`다.
5. 애매하면 `other`를 사용한다. `other`가 많다는 사실은 오류가 아니다.
6. 한 record의 relations는 2~5개다.
7. record 안에서 같은 relation을 두 번 쓰지 않는다.
8. 수량을 맞추려고 text에 없는 relation을 붙이지 않는다.
9. relation 순서만 바꾼 것은 새 relation-set이 아니다.

과거에 쓰인 `degree`, `measurement`, `capability`, `threshold`, `anti_overgeneralization`, `attribute_vs_category`, `necessary_condition` 같은 자유 이름은 신규 고밀도 metadata에서 금지한다. 실제 의미에 따라 통제 어휘로 보수적으로 표현한다.

## 10. 의미 문장 직접 작성 원칙

primary concept와 `text`의 의미 내용은 모델이 record별로 직접 작성한다.

허용 자동화:

- ID 부여
- top-level metadata·JSON 포장
- source 열 수·행 수 검증
- relation 통제·중복 검사
- exact duplicate·n-gram·유사도 계산
- 조사 후보 추출
- 통계·SHA-256·보고 표 생성

금지 자동화:

- concept 이름 목록을 문자열 조합으로 대량 합성
- 같은 문장 template에 명사만 교체
- sequential replace로 한국어 문장을 변형
- 공통 suffix를 붙여 수백 개 primary concept를 기계 생성
- relation을 round-robin으로 배정하고 의미 검토를 생략
- validation을 train 문장 paraphrase로 만드는 작업

자동화는 문장을 **포장하고 검사**할 수 있지만 의미를 대신 만들 수 없다.

## 11. `text` 작성 규약

### 11.1 의미 밀도

가능한 문장에는 다음 중 둘 이상을 자연스럽게 포함한다.

- 대상 또는 기준
- 관찰되는 속성·기능·상태
- 판정 기준
- 변화 과정 또는 조건
- 비교 대상이나 경계
- 실제 반례
- 결과 또는 해석상의 주의점

사전식 `X는 Y다`만 반복하지 않는다. 분류, 관찰, 조건, 결과, 반례를 필요에 맞게 조합한다.

### 11.2 다양화

- 모든 문장을 primary concept+`은/는`으로 시작하지 않는다.
- 첫 문장과 둘째 문장의 역할을 바꾼다.
- 원인→결과, 반례→기준, 관찰→판정, 조건→예외 등 논리 흐름을 섞는다.
- 세미콜론·쉼표·연결어를 자연스럽게 사용하되 동일 골격을 반복하지 않는다.
- 서로 다른 concept가 같은 종결부를 공유하지 않게 한다.

### 11.3 한국어 품질

- `은/는`, `이/가`, `을/를`, `과/와`, `(으)로`를 받침에 맞춘다.
- concept를 먼저 확정한 뒤 문장에 맞춰 조사와 어순을 직접 쓴다.
- 한자어·외래어를 불필요하게 붙인 인공 합성어를 피한다.
- 불완전한 병렬, 중복 목적어, 끊긴 수식어, 번역투를 피한다.
- 규범적·법적·의학적 문장은 범위를 과장하지 않는다.

## 12. 150개 concept-family 설계

새 영역은 생성 전에 전체 version의 family를 설계서에 예약한다.

예약표 필수 열:

```text
version | ID range | concept family | 포함 축 | 상태
```

선정 규칙:

1. 한 family는 정확히 한 파일을 담당한다.
2. 서로 다른 version의 family는 의미 중심이 겹치지 않는다.
3. 한 family 안의 150개는 공통 교육 목표를 가지되 primary concept는 중복하지 않는다.
4. 지나치게 넓은 family는 하위 축을 명시한다.
5. 예약 뒤 context 압축이나 새 세션에서도 이름을 바꾸거나 재선정하지 않는다.
6. 실제 파일과 전수 감사가 끝난 뒤에만 상태를 `확정`으로 바꾼다.
7. 중단 시 마지막 확정 version 다음부터 재개한다.

## 13. Validation 분리 규칙

### V1. 주 validation 관계

`unseen_relation: false` record는 원칙적으로 train에서 학습한 relation 이름을 사용한다. 더 엄격한 영역 규약이 설계서에 있으면 train에서 관측된 정렬 relation-set까지 사용한다.

### V2. 일반화 slice 10~15%

전체 validation의 10~15%는 `unseen_relation: true`다.

생성 전에 train을 실측하고 다음 중 어느 해석인지 설계서에 기록한다.

- train에 없던 **통제 relation 이름**을 포함한 record
- 통제 이름은 모두 보았지만 train에 없던 **정렬 relation-set 조합**을 사용한 compositional unseen record

통제 어휘 밖 이름을 만들어 V2를 맞추지 않는다. true/false 판정은 relation 순서를 정렬한 집합으로 계산한다.

### V3. 비율·분리 보고

반드시 보고한다.

- 전체 true/false 수와 비율
- 파일별 true/false 수와 비율
- true 고유 relation-set 수
- false set이 모두 train 관측인지
- true set이 모두 train 미관측인지
- train 미관측 개별 label을 썼다면 label별 횟수

Validation은 다음을 피한다.

- train exact `text`
- train 문장의 단순 바꿔쓰기
- train primary concept 재사용
- 동일 primary concept+relation-set 조합
- train의 5어절 이상 문구 복제
- held-out 문장·정답 구조 복사

## 14. Validation과 held-out의 차이

| 구분 | Validation | Held-out |
|---|---|---|
| 목적 | 학습 중 일반화 확인 | 최종 blind 평가 |
| checkpoint 선택 | 가능 | 금지 |
| corpus 수정 근거 | 제한적으로 가능하나 오염 기록 | 금지 |
| 노출 | 개발 중 반복 가능 | final 전 비공개 |
| 재사용 | 개발 비교 | 결과를 본 뒤 조건 변경 시 폐기 |

## 15. 자동 감사 필수 항목

### 구조·직렬화

- 파일별 JSON parse
- UTF-8 decode
- `\uXXXX` escape 여부
- top-level key·metadata·version·split·range
- records 배열과 `record_count`
- record key set·type·split
- 전역 ID 형식·연속·중복

### Relations

- 13개 통제 어휘 밖 값 0
- record당 2~5개
- record 내부 중복 0
- 영역 필수 relation 100%
- text 의미와 label 일치
- 전체·version별 13개 분포
- `other` 상위 개념 유형 5개

### Text와 concept

- exact ID·primary concept·text 중복 0
- 빈 text·concept 0
- primary concept literal 누락 0
- 비정상 길이·제어문자·깨진 escape 0
- 반복 5어절과 반복 4어절 도입부
- 문자 3~5-gram TF-IDF cosine 상위 pair
- primary concept 직후 조사 검사
- 문장 전체 조사 후보 추출 후 사람이 오탐/실제 오류 판정
- 높은 유사도 pair 직접 검토

### Split leakage

- train–val exact text
- train–val exact primary concept
- train–val `(primary concept, sorted relation-set)`
- train–val 공통 5어절
- train–val 최대·상위 유사도

### Validation unseen

- boolean 필드 타입
- true 비율 10~15%
- 선언과 실제 train 미관측 여부 일치
- 파일별/전체 집계

감사 script는 read-only가 원칙이다. 오류를 찾으면 source 원고를 `apply_patch`로 직접 고치고 builder와 전체 감사를 다시 실행한다.

## 16. 생성 후 보고 형식

### 16.1 파일·누적 표

| version | 파일 | ID 범위 | records | concept family | 상태 | SHA-256 |
|---|---|---|---:|---|---|---|

전체 목표, 현재 누적, 잔여 records/files를 함께 적는다.

### 16.2 구조 감사

다음 수치를 0/비0으로 명시한다.

```text
JSON/UTF-8 errors
metadata/schema errors
ID sequence/duplicate errors
concept/text duplicates
relation rule errors
repeated n-grams/openings
particle errors
similarity maxima
split leakage
```

### 16.3 Relations 분포

13개를 0인 relation까지 모두 보고한다.

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

`other`가 0이면 상위 5유형은 해당 없음이라고 적는다. 1개 이상이면 편집 검토로 자주 나온 개념 유형 5개와 횟수·대표 concept를 보고한다. 편집 유형명을 새 relation으로 넣지 않는다.

### 16.4 분량

- 설계 token 환산량
- 실제 records
- 전체 `text` 문자 수
- `[0-9A-Za-z가-힣]+` 기준 분리 단위
- 실제 tokenizer를 측정했는지 여부

설계 token과 tokenizer 실측을 같은 수치로 표현하지 않는다.

### 16.5 무결성

- 보호 파일 시작/종료 SHA-256 일치 수
- 변경·누락 파일 수
- 작업 전 존재한 unrelated 변경 보존 여부
- `git diff --check` 결과

## 17. 표준 작업 순서

1. 작업지침서·설계서·실제 파일을 읽는다.
2. 보호 SHA-256과 초기 git status를 저장한다.
3. 예약 family와 ID 범위를 확인한다.
4. 한 version의 primary concept·relations·text를 직접 작성한다.
5. source 행 수·열·relation을 검사한다.
6. builder로 정확히 150 records를 포장한다.
7. JSON·ID·schema·relations를 검사한다.
8. concept/text duplicate, 5어절, 도입부, 유사도, 조사를 검사한다.
9. 사람이 모든 플래그와 의미 문장을 검토한다.
10. source를 직접 수정하고 전체를 재빌드·재감사한다.
11. 파일 상태와 누적을 설계서에 갱신한다.
12. 다음 예약 family로 이동한다.
13. 전체 완료 뒤 통합 감사·최종 보고서를 작성한다.
14. 보호 SHA-256과 초기 git status를 다시 비교한다.

## 18. 수정 금지와 안전

- 설계서에 수정 금지로 등록된 파일은 읽기·해시 계산 외에 쓰지 않는다.
- dirty worktree의 사용자 변경과 외부 process 산출물을 임의 정리하지 않는다.
- 전체 폴더를 재직렬화하거나 일괄 이동하지 않는다.
- 대상 version 밖 파일을 builder가 덮어쓰지 않게 출력 path를 제한한다.
- 기존 source와 겹치는 파일을 수정해야 하면 먼저 실제 diff와 권한 범위를 확인한다.
- 임시 감사 산출물은 정본과 구분한다.
- destructive 명령, broad delete, reset을 사용하지 않는다.

## 19. 새 세션 재개 지시

> 고밀도 작업지침서와 데이터셋 설계서를 먼저 읽고 실제 고밀도 파일을 감사한다. 다른 밀도의 데이터셋과 held-out은 참고·source·비교 기준으로 사용하지 않는다. 설계서의 마지막 확정 version과 다음 예약 family를 확인하고, 한 파일 150개·직접 작성 text·13개 통제 relations·split 격리 규칙을 지킨다. 자동화는 포장과 감사에만 사용한다. 생성 후 JSON/ID/concept/text/n-gram/유사도/조사/relations·other 분포와 보호 SHA-256을 보고하고, 설계 원장의 상태를 갱신한다.
