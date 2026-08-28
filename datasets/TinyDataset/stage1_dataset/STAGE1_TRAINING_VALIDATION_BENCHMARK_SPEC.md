# Stage 1 학습·Validation·Benchmark 데이터 파이프라인 제안서

## 0. 문서 목적

이 문서는 Claude가 Stage 1의 100M 파라미터급 한국어 모델 실험 코드를 구현할 때 사용할 수 있도록, 다음 항목을 하나의 일관된 실험 규격으로 정의한다.

1. Stage 1 학습 데이터의 로딩 및 split 처리
2. validation 데이터의 로딩·평가 방법과 checkpoint selection 규칙
3. 별도의 `held-out benchmark` 로딩 및 최종 평가 방법
4. 외부 LLM judge를 사용하지 않는 deterministic scorer의 설계
5. 2점 체계와 관계 단위 채점
6. 데이터 누수(leakage)와 validation/test contamination 방지
7. 재현 가능한 실험 로그 및 결과 보고 형식

핵심 원칙은 다음과 같다.

> **Train은 가중치 업데이트에 사용하고, Validation은 학습 과정의 의사결정에 사용하며, Held-out benchmark는 최종 성능 보고에만 사용한다.**

Validation과 Held-out은 둘 다 gradient update에는 사용하지 않지만, validation은 checkpoint·hyperparameter·학습 종료 여부를 결정하는 데 사용되므로 최종 성능을 검증하는 held-out과 분리해야 한다.

---

# 1. 현재 Stage 1 데이터 구성

## 1.1 원본 Stage 1 prototype

현재 Stage 1 prototype은 총 1,000개다.

| 유형 | 수량 | 비율 |
|---|---:|---:|
| 대상·정체성·기본 분류 | 250 | 25% |
| 속성 | 150 | 15% |
| 기능·용도 | 120 | 12% |
| 개념 경계·반례 | 120 | 12% |
| 부분–전체 | 100 | 10% |
| 상태·상태 대비 | 80 | 8% |
| 공간 관계 | 60 | 6% |
| 비교·대조 | 50 | 5% |
| 문맥 속 개념 | 40 | 4% |
| 개념 타입 구분·부정 | 30 | 3% |
| **합계** | **1,000** | **100%** |

이 1,000개는 **학습 prototype 전체**이며, validation을 포함한 원본 풀(pool)이다.

## 1.2 실제 split

실제 모델 학습에는 다음처럼 분리한다.

```text
Stage 1 prototype = 1,000
├── train = 900
└── val   = 100

separate benchmark
└── held-out = 300
```

따라서 최종 실험 데이터는 총 1,300개를 갖지만, **1,000개와 300개는 성격이 다르다.**

- 900 train + 100 val: 기존 Stage 1 prototype에서 분할
- 300 held-out: Stage 1 prototype과 별도로 제작한 benchmark

Held-out은 1,000개에 다시 합치면 안 된다.

---

# 2. 권장 디렉터리 구조

```text
stage1_dataset/
├── MANIFEST.json
│
├── train/
│   ├── stage1_train_900.json
│   ├── stage1_train_text_900.jsonl
│   └── stage1_train_metadata_900.json
│
├── val/
│   ├── stage1_val_100.json
│   ├── stage1_val_text_100.jsonl
│   └── stage1_val_metadata_100.json
│
└── held-out/
    ├── stage1_heldout_test_300.json
    ├── stage1_heldout_eval_300.jsonl
    └── stage1_heldout_metadata_300.json
```

## 2.1 실제 모델 입력

모델 학습·validation 입력에는 기본적으로 `text`만 사용한다.

예:

```json
{"text":"사과는 과일의 한 종류다. 나무에서 자라며 먹을 수 있는 과육을 가진다."}
```

`id`, `type`, `concepts`, `relations`는 모델에게 그대로 보여주는 텍스트가 아니라 다음 용도로 유지한다.

- dataset audit
- 균형 확인
- stratified sampling
- error analysis
- benchmark scoring
- leakage 검사

특히 **Train metadata의 `relations`를 모델 입력으로 직접 노출하지 않는 것을 기본값으로 한다.**

---

# 3. 데이터 로더 설계

## 3.1 Loader API의 목표

구현은 특정 프레임워크에 종속되지 않도록 다음과 같은 논리적 API를 갖는 것을 권장한다.

```text
Stage1DatasetLoader
 ├── load_train()
 ├── load_val()
 ├── load_benchmark()
 ├── validate_manifest()
 └── audit_split_integrity()
```

각 loader는 최소한 다음 필드를 제공한다.

```text
record_id
text
split
```

metadata를 동시에 사용해야 하는 분석 모드에서는 다음도 제공한다.

```text
record_id
text
type
group
concepts
relations
```

## 3.2 Train loader

Train loader는 다음 파일만 읽어야 한다.

```text
train/stage1_train_text_900.jsonl
```

권장 반환 형태:

```python
{
    "text": "..."
}
```

학습 시에는 `id`, `concepts`, `relations`를 tokenizer 입력에 넣지 않는다.

## 3.3 Validation loader

Validation loader는 다음 파일만 읽는다.

```text
val/stage1_val_text_100.jsonl
```

Validation도 기본적으로 모델에게 `text`만 제공한다.

중요:

- validation target은 학습 gradient에 포함하지 않는다.
- `model.eval()` 상태에서 평가한다.
- gradient computation을 끈다.
- validation loss를 계산할 경우 train loss와 동일한 token-level objective를 사용한다.

## 3.4 Held-out benchmark loader

Held-out benchmark는 일반 training dataset과 다른 구조를 가진다.

```text
held-out/stage1_heldout_eval_300.jsonl
```

최소 항목:

```text
id
split
 task
prompt
answer
key_relations
```

Benchmark는 일반 LM training batch loader로 돌리지 않고 **evaluation harness**에서 별도로 처리한다.

권장 인터페이스:

```text
BenchmarkRunner
 ├── generate_answer(prompt)
 ├── normalize_answer(output)
 ├── extract_entities(output)
 ├── detect_relations(output)
 ├── score_record(record)
 └── aggregate_scores(results)
```

---

# 4. Train/Validation split 규칙


## 4.1 Stratified split

Validation 100개는 Stage 1의 유형 분포를 가능한 한 유지해야 한다.

권장 비율:

```text
identity                  25
attribute                 15
function                  12
boundary                  12
part_whole                10
state                      8
spatial                    6
comparison                 5
context                    4
type_distinction_negative  3
--------------------------------
                         100
```

이렇게 해야 validation score가 특정 한 개념 유형의 성능만 반영하지 않는다.

---

# 5. Validation 방법

## 5.1 Validation에서 별도의 특별한 평가가 필요한가?

**Validation은 원칙적으로 별도의 복잡한 채점기를 사용할 필요가 없다.**

Training과 동일한 causal-LM objective로 validation loss/perplexity를 측정하는 것이 기본이다.

```text
train batch
→ forward
→ loss
→ backward
→ update

validation batch
→ forward
→ loss only
→ no backward
→ no update
```

다만 Stage 1처럼 데이터가 매우 작고 의미적 일반화를 목표로 하는 실험에서는 **validation loss 하나만 보는 것은 부족하다.**

따라서 다음 두 층으로 평가한다.

### A. Standard validation

- validation loss
- token-level cross entropy
- perplexity

### B. Lightweight semantic validation

100개 validation record에 대해 가능한 경우 metadata 기반의 간단한 관계 검사를 수행한다.

예:

```text
is_a
not_is_a
part_of
inside
above
below
same_category
state
```

다만 validation semantic score를 checkpoint 선택에 사용한다면 이것 역시 validation contamination의 일부가 된다. 이것은 정상적인 사용이며, 그 때문에 held-out benchmark가 별도로 필요하다.

## 5.2 Checkpoint selection

권장 기본 기준:

```text
primary criterion = validation loss 최소
```

semantic score까지 checkpoint selection에 사용하려면 사전에 규칙을 고정한다.

권장 예:

```text
primary: val_loss
secondary: semantic_val_score
```

또는

```text
selection_score = normalized_val_loss + weighted_semantic_penalty
```

단, 이런 복합 점수는 실험 조건을 바꾸기 쉽게 만들기 때문에 **첫 실험에서는 단순하게 validation loss를 primary로 하는 것이 더 좋다.**

---

# 6. Held-out benchmark의 역할

Held-out은 다음 질문에 답하기 위한 것이다.

> "900 train + 100 validation으로 학습과 선택을 마친 최종 모델이, 학습 중 한 번도 보지 않은 개념과 관계를 일반화할 수 있는가?"

Held-out은 다음 행동에 절대 사용하지 않는다.

- checkpoint selection
- learning rate 선택
- batch size 선택
- epoch 선택
- curriculum 재설계
- 데이터 추가/삭제 결정
- tokenizer 선택
- 모델 구조 선택
- prompt tuning
- scorer tuning

한 번이라도 이를 보고 모델/학습 방법을 수정했다면 해당 benchmark는 더 이상 완전한 최종 test가 아니며, 그 이후에는 validation-like 역할을 한 것으로 취급해야 한다.

---

# 7. Held-out benchmark 구성

현재 300개 benchmark는 다음 세 영역으로 나뉜다.

| 영역 | 수량 | 목적 |
|---|---:|---|
| unseen concept | 150 | 학습셋에 직접 등장하지 않은 개념에 대한 일반화 |
| novel relation | 90 | 기존 개념을 새로운 관계 조합으로 연결 |
| boundary | 60 | 과잉 일반화, 잘못된 동일시, 필요/충분조건 오류 검출 |
| **합계** | **300** | |

이 세 영역의 점수를 반드시 별도로 보고한다.

---

# 8. Benchmark 평가 방식

## 8.1 가장 중요한 원칙

**문장 문자열 일치(exact match)를 사용하지 않는다.**

예:

정답:

```text
수달은 포유류다.
```

모델:

```text
수달은 포유류에 속하는 동물입니다.
```

이는 의미적으로 정답이다.

따라서 평가용 정답을 문장 하나가 아니라 **핵심 개념과 관계**로 구조화한다.

---

# 9. 외부 LLM judge 없이 채점하는 방법

외부 LLM judge를 사용하지 않는 것을 기본 실험 규격으로 한다.

## 9.1 2점 체계

각 benchmark item에 대해:

### 2점: 완전 정답

필수 개념과 필수 관계를 모두 만족한다.

예:

```text
Q: 수달은 어떤 종류의 동물인가?
A: 수달은 포유류다.
```

→ 2점

### 1점: 부분 정답

핵심 방향은 맞지만 요구한 specificity 또는 일부 관계가 부족하다.

예:

```text
A: 수달은 동물이다.
```

→ 포괄적으로는 맞지만 benchmark의 핵심 목표인 `수달 → 포유류`를 완전히 충족하지 못하므로 1점.

### 0점: 오답

핵심 관계가 잘못되었다.

```text
A: 수달은 물고기다.
```

→ 0점

---

# 10. 관계 단위 채점

한 문항에 관계가 여러 개라면 문장 전체를 한 번에 맞다/틀리다로 처리하지 않는다.

예:

```json
{
  "required_relations": [
    "inside",
    "not_touching"
  ]
}
```

모델 출력:

```text
작은 상자는 큰 상자 안에 있지만 서로 닿지 않는다.
```

→ 2점

출력:

```text
작은 상자는 큰 상자 안에 있다.
```

→ 1점

출력:

```text
작은 상자는 큰 상자의 일부다.
```

→ 0점

따라서 benchmark item은 가능하면 다음 구조를 가지게 한다.

```json
{
  "required_concepts": [],
  "required_relations": [],
  "forbidden_relations": [],
  "partial_credit_conditions": []
}
```

---

# 11. Deterministic scorer 설계

## 11.1 전체 파이프라인

```text
model output
    ↓
Unicode normalization
    ↓
whitespace / punctuation normalization
    ↓
canonical phrase normalization
    ↓
concept/entity extraction
    ↓
relation extraction
    ↓
forbidden relation check
    ↓
required relation matching
    ↓
0 / 1 / 2 scoring
    ↓
aggregate metrics
```

## 11.2 표현 정규화

다음은 같은 뜻으로 정규화할 수 있다.

```text
포유류다
포유류이다
포유류입니다
포유류에 속한다
포유류에 해당한다
```

→ canonical relation:

```text
is_a(subject, 포유류)
```

단순 형태소 정규화만으로 완벽한 의미 판정이 되지는 않으므로, **관계별 canonical pattern table**을 관리한다.

---

# 12. 권장 canonical relation table

## 12.1 `is_a`

대표 패턴:

```text
X는 Y다
X는 Y이다
X는 Y에 속한다
X는 Y의 한 종류다
X는 Y에 해당한다
```

## 12.2 `not_is_a`

```text
X는 Y가 아니다
X는 Y가 아니다
X는 Y로 분류되지 않는다
X는 Y에 속하지 않는다
```

## 12.3 `part_of`

```text
X는 Y의 일부다
X는 Y를 이루는 부분이다
X는 Y의 구성요소다
```

## 12.4 `inside`

```text
X는 Y 안에 있다
X는 Y 내부에 있다
X는 Y 속에 있다
```

주의:

```text
inside != part_of
```

예:

```text
사과가 상자 안에 있다
```

→ `inside(사과, 상자)`

이지,

→ `part_of(사과, 상자)`

가 아니다.

## 12.5 `above / below`

```text
X는 Y 위에 있다
X는 Y보다 아래에 있다
```

## 12.6 `same_category`

```text
X와 Y는 모두 Z다
X와 Y는 같은 범주에 속한다
```

단, 이것은 `X == Y`가 아니다.

## 12.7 상태 관계

```text
X가 열려 있다
X가 닫혀 있다
X가 켜져 있다
X가 꺼져 있다
X가 젖어 있다
```

→ `state(X, ...)`

상태를 개념/정체성과 혼동해서는 안 된다.

---

# 13. Forbidden relation을 반드시 둔다

Stage 1 benchmark에서 가장 중요한 것은 과잉 일반화 감지이므로 정답 관계뿐 아니라 **금지 관계**도 기록하는 것을 권장한다.

예:

```json
{
  "required_relations": ["inside"],
  "forbidden_relations": ["part_of"]
}
```

모델이:

```text
사과는 상자의 일부다.
```

라고 답하면 `part_of`가 검출되어 오답 처리할 수 있다.

이는 외부 judge 없이도 deterministic하게 구현 가능하다.

---

# 14. Benchmark별 scoring schema 권장

각 평가 항목을 내부적으로 다음처럼 확장하는 것을 권장한다.

```json
{
  "id": "E-001",
  "task": "identity",
  "prompt": "수달은 어떤 종류의 동물인가?",
  "gold_answer": "수달은 포유류다.",
  "required_concepts": ["수달", "포유류"],
  "required_relations": [
    {
      "type": "is_a",
      "subject": "수달",
      "object": "포유류"
    }
  ],
  "forbidden_relations": [
    {
      "type": "is_a",
      "subject": "수달",
      "object": "물고기"
    }
  ],
  "difficulty": 1
}
```

이렇게 해야 자동 scorer가 안정적으로 작동한다.

---

# 15. 2점 채점의 정확한 알고리즘

권장 기본 규칙:

```text
if forbidden_relation_detected:
    score = 0
elif all(required_relations_match):
    score = 2
elif some(required_relations_match):
    score = 1
else:
    score = 0
```

단일 관계 문제는 더 간단하다.

```text
required relation 정확 → 2
상위 범주만 맞거나 불완전 → 1
관계 방향/타입이 틀림 → 0
```

---

# 16. 자유생성 평가의 한계와 해결책

완전히 자유로운 한국어 답변을 deterministic scorer 하나로 100% 의미 판정하는 것은 어렵다.

따라서 Stage 1에서는 benchmark prompt를 가능한 한 **짧고 구조적으로** 만든다.

좋은 예:

```text
수달은 어떤 종류의 동물인가?
```

좋은 예:

```text
공은 상자 안에 있고 상자는 방 안에 있다. 공은 방 안에 있는가?
```

좋지 않은 예:

```text
이 상황을 종합적으로 설명하고 수달에 대한 모든 관련 정보를 자유롭게 기술하라.
```

후자는 deterministic scoring이 어려워진다.

---

# 17. 권장 benchmark task 유형

## A. Identity

```text
새 개체 → 상위 범주
```

예:

```text
카피바라는 어떤 범주의 동물인가?
```

## B. Boundary

```text
속성 → 잘못된 범주화를 막는 문제
```

예:

```text
투명한 물체는 모두 유리인가?
```

## C. Relation composition

```text
A inside B
B inside C
→ A inside C
```

## D. Relation distinction

```text
inside != part_of
near != touching
state != identity
```

## E. Negation

```text
고래는 물고기가 아니다.
```

## F. Uncertainty

```text
정보가 부족한 경우 확정하지 않는가?
```

---

# 18. 최종 benchmark metrics

최소 다음 지표를 모두 기록한다.

## 18.1 Overall 2-point score

```text
score = sum(item_score) / (2 * number_of_items)
```

0~1 범위로 표시한다.

예:

```text
210 items × 2 points
45 items × 1 point
45 items × 0 point
```

이면:

```text
(210×2 + 45) / 600 = 0.775
```

→ **77.5%**

## 18.2 Concept Accuracy

새로운 개념의 정체성·분류를 얼마나 정확하게 판단하는가.

## 18.3 Relation Accuracy

관계를 얼마나 정확히 적용하는가.

## 18.4 Boundary Accuracy

잘못된 일반화와 개념 경계 문제를 얼마나 정확하게 처리하는가.

## 18.5 Overgeneralization Error Rate

다음과 같은 오류를 별도로 집계한다.

```text
속성 → 범주
기능 → 정체성
내부 → 부분
상태 → 정체성
유사 → 동일
동시발생 → 인과
```

## 18.6 Relation Confusion Rate

예:

```text
inside → part_of
near → touching
attribute → identity
state → identity
```

## 18.7 Unsupported Assertion Rate

질문이나 제공된 정보에서 뒷받침되지 않는 새로운 주장 비율.

특히 100M 모델의 hallucination-like behavior를 추적하는 데 유용하다.

---

# 19. Benchmark 결과를 한 숫자로만 평가하지 말 것

다음과 같은 결과를 가정한다.

```text
Concept Accuracy        90%
Relation Accuracy       86%
Boundary Accuracy       48%
```

이 경우 전체 점수가 높더라도 Stage 1이 바람직하게 학습되었다고 판단해서는 안 된다.

Boundary Accuracy가 낮으면 **shortcut / overgeneralization** 가능성이 크다.

반대로:

```text
Concept Accuracy        81%
Relation Accuracy       78%
Boundary Accuracy       77%
```

라면 절대 점수는 조금 낮더라도 개념 표현이 더 건강하게 형성되었을 가능성이 있다.

따라서 Stage 1에서는 특히:

```text
Boundary Accuracy
Overgeneralization Error Rate
```

을 중요한 지표로 취급한다.

---

# 20. Benchmark를 보기 전/후의 규칙

## benchmark 이전

자유롭게 수정 가능:

- architecture
- learning rate
- batch size
- epoch
- scheduler
- curriculum composition
- tokenizer
- train/val split
- validation scorer

## benchmark를 처음 확인한 후

가능하면 해당 benchmark 결과를 기반으로 모델이나 학습 규칙을 다시 수정하지 않는다.

실험상 수정이 꼭 필요했다면:

```text
benchmark-v1
```

을 더 이상 최종 test라고 부르지 않고,

```text
validation-like evaluation
```

으로 승격/강등시킨 뒤 새로운 blind benchmark를 만든다.

---

# 21. Leakage 검사

## 21.1 파일 수준

Train loader가 `val/` 또는 `held-out/` 경로를 읽지 않는지 확인한다.

## 21.2 ID 수준

```text
train_ids ∩ val_ids = ∅
data_ids ∩ heldout_ids = ∅
after training:
train_ids ∩ heldout_ids = ∅
val_ids ∩ heldout_ids = ∅
after training
```

## 21.3 텍스트 수준

정확한 text equality를 검사한다.

## 21.4 개념 수준

Held-out의 `unseen_concept` subset에 등장하는 핵심 개념이 train에서 직접 학습되었는지 확인한다.

단, 실제로 완전한 concept-disjoint를 보장하기 어렵기 때문에 benchmark annotation에서 다음을 구분한다.

```text
new entity
new relation
new composition
new boundary case
```

이는 benchmark의 성격을 투명하게 만드는 데 중요하다.

---

# 22. Validation과 Held-out을 절대로 합치지 않는 이유

Validation은 최종 모델을 선택하는 데 영향을 준다.

예:

```text
checkpoint A → val 72%
checkpoint B → val 76%
checkpoint C → val 79%
```

C를 선택했다면 validation에 이미 적응한 것이다.

반면 held-out은:

```text
최종 checkpoint 결정
        ↓
held-out 300 평가
```

순서여야 한다.

따라서:

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

가 정확한 실험 구조다.

---

# 23. Training loop 권장 구조

의사코드:

```text
load train_loader
load val_loader
initialize model

for epoch in epochs:
    model.train()

    for batch in train_loader:
        loss = forward(batch)
        backward(loss)
        optimizer.step()
        optimizer.zero_grad()

    model.eval()
    val_loss = evaluate_language_model(val_loader)
    val_semantic = evaluate_optional_semantic_validation(val_loader)

    save_checkpoint_if_best(val_loss, val_semantic)

# Do NOT touch held-out during the loop.

final_model = load_best_checkpoint()
benchmark_results = run_heldout_benchmark(final_model)
```

첫 실험에서는 `val_loss`를 primary checkpoint criterion으로 하는 것을 권장한다.

---

# 24. Batch 구성 권장

Stage 1은 900개밖에 없으므로 매 epoch마다 모든 예제를 보는 것이 가능하다.

권장:

```text
shuffle(train) = True
shuffle(val) = False
shuffle(held-out) = False
```

Benchmark prompt 순서는 고정해 재현성을 높인다.

가능하면 seed를 고정한다.

```text
python random seed
numpy seed
framework seed
DataLoader worker seed
```

GPU 연산의 완전 결정성은 사용하는 backend에 따라 보장되지 않을 수 있으므로, **동일 seed + 동일 software version + 동일 hardware 조건에서 재현**하는 것으로 실험 규격을 정의한다.

---

# 25. Stage 1에서 추가로 권장하는 두 종류의 validation loss

Train/validation이 sequence LM objective라면 다음 두 값을 동시에 기록하는 것이 좋다.

```text
raw validation loss
length-normalized validation loss
```

단, 모든 sequence 길이가 동일하다면 사실상 같은 의미가 된다.

현재 데이터가 동일한 길이로 packing되지 않을 경우 token count 기준으로 평균을 내야 한다.

잘못된 방식:

```text
mean(batch_loss)
```

권장:

```text
sum(token_loss) / sum(valid_tokens)
```

이렇게 해야 마지막 batch 크기나 padding 비율에 따른 왜곡이 줄어든다.

---

# 26. Padding / masking 규칙

Causal LM에서 pad token이 존재한다면 loss mask에서 제외한다.

```text
attention_mask = 1 for real token
attention_mask = 0 for padding
```

loss 역시:

```text
ignore_index = pad_token_id
```

등으로 처리한다.

Train과 Validation에 동일한 tokenizer와 동일한 masking 규칙을 적용한다.

---

# 27. Benchmark 생성 방식

Benchmark는 teacher forcing loss로만 평가하지 않는 것을 권장한다.

Benchmark의 목적은 실제 응답 능력을 보는 것이므로:

```text
prompt
  ↓
model.generate()
  ↓
generated answer
  ↓
deterministic scorer
```

를 사용한다.

즉 benchmark는 **generation evaluation**이다.

별도의 perplexity benchmark가 필요하다면 보조 지표로 기록하되, Stage 1 semantic capability의 대표 점수로 사용하지 않는다.

---

# 28. Generation 설정

모델 비교 시 generation 설정을 고정해야 한다.

권장:

```text
temperature = 0
sampling = False
do_sample = False
```

또는 deterministic greedy decoding을 사용한다.

`temperature`, `top_p`, `top_k` 등을 checkpoint마다 다르게 적용하면 benchmark 비교가 무효가 된다.

max_new_tokens도 고정한다.

예:

```text
max_new_tokens = 64
```

다만 실제 구현 시 평균 정답 길이를 고려해 충분한 길이를 사용한다.

---

# 29. Scorer 구현 시 절대로 하면 안 되는 것

다음은 금지한다.

1. benchmark prompt를 scorer 개발 데이터로 계속 수정하면서 사용
2. 사람이 benchmark 결과를 보고 pattern dictionary를 무한히 수정한 뒤 동일 benchmark를 다시 채점
3. 모델별로 scorer 규칙을 다르게 적용
4. 특정 checkpoint만 사람이 유리하게 해석
5. exact-match만으로 자연어 의미를 판정
6. forbidden relation을 무시

Scorer를 크게 변경했다면 scorer 버전을 올린다.

예:

```text
scorer_version = 1.0
scorer_version = 1.1
```

---

# 30. Scorer 개발 순서

권장 개발 절차:

### Phase A

10~20개의 수작업 sanity cases를 만든다.

```text
정답
부분정답
오답
관계 반전
금지 관계
```

### Phase B

scorer가 인간이 만든 expected score와 일치하는지 확인한다.

### Phase C

300개 benchmark 전체를 한 번 실행한다.

### Phase D

이후에는 scorer를 freeze한다.

### Phase E

모델 checkpoint간 비교에 같은 scorer를 적용한다.

---

# 31. Validation semantic scorer와 benchmark scorer를 구분할 것

둘을 같은 코드로 만들 수는 있지만 개념적으로는 분리하는 것이 좋다.

```text
validation_semantic_scorer
    └── checkpoint selection에 사용 가능

heldout_benchmark_scorer
    └── final reporting only
```

benchmark scorer에 사용된 기준은 실험이 끝난 뒤까지 고정한다.

---

# 32. 결과 보고 양식

최소 다음 표를 기록한다.

| Model | Val Loss | Val Semantic | Held-out 2pt | Concept | Relation | Boundary |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | ... | ... | ... | ... | ... | ... |
| Stage 1 | ... | ... | ... | ... | ... | ... |

추가로:

```text
Overgeneralization Error Rate
Relation Confusion Rate
Unsupported Assertion Rate
```

을 기록한다.

---

# 33. Baseline 비교가 반드시 필요하다

Stage 1이 효과가 있는지 확인하려면 최소 두 모델을 비교한다.

```text
Baseline
```

동일한 모델 구조와 학습 예산이지만 Stage 1 curriculum을 학습하지 않은 조건.

```text
Stage1
```

Stage 1 train 900을 학습한 조건.

가능하면 다음도 추가한다.

```text
Baseline + random 900 examples
Stage1 900 curated examples
```

이 비교는 **데이터 수 증가의 효과와 데이터 구성의 효과를 분리**하는 데 특히 중요하다.

---

# 34. 추가 ablation 권장

Stage 1의 효과를 실제로 증명하려면 다음 ablation이 유용하다.

```text
A. No Stage 1
B. Random 900
C. Stage 1 900
D. Stage 1 900 + extra training
```

핵심은 B와 C다.

```text
Random 900 vs Curated Stage 1 900
```

에서 held-out benchmark 성능이 차이 난다면 **단순 데이터량 증가가 아니라 curriculum 구성 자체의 효과**를 주장할 수 있다.

---

# 35. Stage 1의 성공 판정 예시

좋은 결과의 한 예:

```text
Baseline
Concept       52%
Relation      47%
Boundary      31%
Overall       43%

Stage 1
Concept       76%
Relation      72%
Boundary      70%
Overall       73%
```

이 경우 특히 Boundary 개선이 크므로 의미 있는 개념 학습 신호로 해석할 수 있다.

반대로:

```text
Baseline
Overall 43%

Stage 1
Overall 70%
Boundary 35%
```

이라면 높은 전체 점수에도 불구하고 shortcut learning을 의심해야 한다.

---

# 36. Held-out 300개를 한 번에 한 숫자로만 보고하지 말 것

최종 보고는 최소 다음 형태가 좋다.

```text
Held-out overall: 73.2%

Unseen Concept:    78.7%
Novel Relation:    71.1%
Boundary:          68.3%

Overgeneralization Error: 17.4%
Relation Confusion:        11.8%
Unsupported Assertion:      6.2%
```

이렇게 하면 모델이:

- 개념을 못 배운 것인지
- 관계를 못 조합하는 것인지
- 반례에서 무너지는 것인지

구분할 수 있다.

---

# 37. 최종 구현 체크리스트

Claude는 구현 완료 전에 다음을 모두 검사해야 한다.

## Dataset

- [ ] train = 900
- [ ] val = 100
- [ ] held-out = 300
- [ ] train/val ID overlap = 0
- [ ] train/held-out ID overlap = 0
- [ ] val/held-out ID overlap = 0
- [ ] 실제 학습 파일에 validation record가 없음
- [ ] actual training input은 text-only

## Train

- [ ] train shuffle enabled
- [ ] validation shuffle disabled
- [ ] padding loss masked
- [ ] token-weighted loss
- [ ] optimizer update가 train에서만 발생

## Validation

- [ ] `eval()` mode
- [ ] no_grad/inference mode
- [ ] validation loss 계산
- [ ] checkpoint selection 기준 고정
- [ ] validation 결과가 held-out으로 넘어가지 않음

## Held-out

- [ ] training loop에서 절대 호출하지 않음
- [ ] checkpoint selection에서 사용하지 않음
- [ ] generation deterministic
- [ ] scorer version 고정
- [ ] final model 확정 이후 실행

## Scorer

- [ ] exact-match가 아니라 semantic relation 기반
- [ ] 2점/1점/0점 구현
- [ ] required relation 지원
- [ ] forbidden relation 지원
- [ ] partial credit 지원
- [ ] scorer unit test 존재
- [ ] scorer version 기록

---

# 38. 권장 최종 실행 구조

```text
                ┌───────────────────────┐
                │ Stage 1 prototype     │
                │ 1,000 records         │
                └──────────┬────────────┘
                           │
                  stratified split
                           │
             ┌─────────────┴─────────────┐
             │                           │
        TRAIN 900                    VAL 100
             │                           │
       gradient update              loss / semantic
             │                           │
             └─────────────┬─────────────┘
                           │
                     checkpoint
                       selection
                           │
                     FINAL MODEL
                           │
                           ▼
               ┌───────────────────────┐
               │ Held-out Benchmark    │
               │       300             │
               └──────────┬────────────┘
                          │
                     generation
                          │
                deterministic scorer
                          │
                          ▼
        ┌──────────────────────────────────┐
        │ Overall / Concept / Relation    │
        │ Boundary / Overgeneralization   │
        │ Relation Confusion / Unsupported│
        └──────────────────────────────────┘
```

---

# 39. 최종 권고

이 실험의 목적은 단순히 1,000개 문장을 외우게 하는 것이 아니다.

목표는 다음과 같은 **개념적 일반화**다.

```text
대상
 ↓
속성
 ↓
기능
 ↓
부분/전체
 ↓
상태
 ↓
공간 관계
 ↓
비교
 ↓
문맥
 ↓
경계/부정
```

따라서 학습 성능을 볼 때도 단순 validation loss뿐 아니라 **held-out에서 새로운 개념과 새로운 관계를 얼마나 안정적으로 결합하는지**를 봐야 한다.

특히 Stage 1 초기 실험에서는 다음 세 가지를 최우선으로 한다.

1. **Train/Val/Held-out의 완전한 역할 분리**
2. **외부 LLM judge 없이 재현 가능한 deterministic benchmark**
3. **Boundary와 Relation Confusion을 별도 지표로 추적**

이 세 가지가 지켜져야 Stage 1 curriculum이 실제로 100M급 모델의 개념 일반화 능력을 향상시켰는지 신뢰성 있게 판단할 수 있다.
