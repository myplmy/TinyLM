# 900 / 100 / 300 데이터셋 활용방안 변경 제안 검토 요청서

## 1. 검토 목적

현재 Stage 1 데이터는 다음과 같이 구성되어 있다.

```text
Stage 1 prototype 1,000
├── train 900
└── validation 100

별도 held-out 300
└── benchmark / semantic probe
```

당초에는 900개를 실제 학습 데이터, 100개를 validation, 300개를 최종 held-out benchmark로 사용하는 구조를 제안하였다.

그러나 현재 확인된 실제 데이터 규모와 100M 파라미터급 모델의 300M-token 표준 학습 조건을 고려하면, 900개의 텍스트를 일반적인 대규모 pretraining corpus의 train subset으로 사용하는 것은 데이터 규모 측면에서 적절하지 않다.

이에 따라 기존 900/100/300의 역할을 변경하는 방안을 검토 요청한다.

---

# 2. 현재 구조의 핵심 문제

현재 1,000개 전체는 약 28.5K token 수준으로 확인된다.

300M-token 학습 기준:

\[
\frac{28.5K}{300M}\approx0.0095\%
\]

따라서 900 train을 그대로 일반 pretraining에 포함하더라도 전체 학습량에서 차지하는 비중은 극히 작다.

반대로 이를 반복적으로 학습시키면 전체 corpus에서 차지하는 실제 정보량에 비해 동일 문장과 동일 semantic pattern이 지나치게 많이 노출될 수 있다.

따라서 현재 1,000개의 역할을 다음과 같이 재정의하는 것이 타당하다.

> **1,000개 = 대규모 pretraining corpus 자체가 아니라 Stage 1 semantic curriculum prototype / specification / 집중학습 실험용 seed**

---

# 3. 변경 제안

기존:

```text
1,000 Stage 1
├── train 900
└── val 100

held-out 300
└── free-generation benchmark
```

를 다음과 같이 변경하는 것을 제안한다.

```text
Stage 1 prototype
├── train 900
│   └── Stage 1 집중학습 실험용
│
└── val 100
    └── Stage 1 학습 과정의 선택/모니터링용

held-out 300
└── Stage 1 최종 semantic probe
    └── 학습에 전혀 사용하지 않음
```

핵심은 **900/100을 폐기하지 않고, "일반 300M pretraining 데이터"가 아닌 별도의 Stage 1 집중학습 단계에 사용하는 것**이다.

---

# 4. Train 900의 새로운 역할

Train 900은 다음 조건에서 의미가 있다.

## 4.1 사용하는 목적

```text
Base 100M model
        ↓
Stage 1 concentrated training
        ↓
Train 900
```

즉,

> "Stage 1에서 설계한 개념 구조가 실제로 모델 가중치에 학습될 수 있는가?"

를 확인하는 용도다.

## 4.2 해석 범위

Train 900을 집중학습하여 성능이 올라갔다고 하더라도 다음을 의미하지 않는다.

- 모델의 일반 지능이 증가했다.
- 대규모 pretraining이 개선되었다.
- 실제 자연어 전반의 능력이 향상되었다.

그 대신 다음을 의미한다.

> **작은 100M급 모델이 제한된 개념 curriculum을 직접 학습하고, 별도 held-out 문제에 일반화할 수 있는가?**

이 질문에 답하는 것이다.

---

# 5. Validation 100의 새로운 역할

Validation 100은 그대로 유지한다.

다만 validation은 다음 용도만 가진다.

- Stage 1 집중학습 중 loss 관찰
- checkpoint selection
- 학습 종료 시점 결정
- 필요시 제한적인 hyperparameter 비교

Validation은 gradient update에 직접 사용하지 않는다.

```text
Train 900
→ gradient update

Val 100
→ loss / validation evaluation
→ checkpoint selection
```

따라서 validation은 **학습 과정에 영향을 주는 데이터**이며, 그 때문에 held-out과 분리한다.

---

# 6. Held-out 300의 새로운 역할

Held-out 300은 가장 중요한 변경 대상이다.

현재 자유생성 benchmark는 base LM의 특성상 실제 semantic capability보다 generation format 실패를 측정할 위험이 있다.

따라서 held-out 300을 **semantic probe**로 재설계하는 것을 제안한다.

## 6.1 기본 형식

각 문제를:

```text
prompt
candidate A
candidate B
candidate C
candidate D
correct candidate
```

형태로 구성한다.

예:

```text
수달은 어떤 범주의 동물인가?

A. 포유류
B. 어류
C. 파충류
D. 조류
```

모델은 자유롭게 답변할 필요 없이 각 후보의 conditional likelihood를 계산한다.

---

# 7. Held-out semantic probe의 채점

외부 LLM judge는 사용하지 않는다.

모델의 답변 생성 결과를 의미적으로 해석하는 대신:

\[
S(y|x)
=
\frac{1}{|y|}
\sum_t
\log P(y_t|x,y_{<t})
\]

와 같은 **length-normalized conditional log-likelihood**를 계산한다.

가장 높은 점수의 후보를 모델의 선택으로 간주한다.

최초 구현에서는 PMI normalization보다 이 방식을 우선하는 것을 제안한다.

---

# 8. Paired 평가

Baseline과 Stage 1 모델은 반드시 **동일한 300개 item**을 평가한다.

각 item에 대해:

\[
Margin_i =
S(correct)-\max S(wrong)
\]

을 계산한다.

Baseline과 Stage 1 사이의 차이는:

\[
\Delta_i =
Margin_{Stage1,i}-Margin_{Baseline,i}
\]

로 계산한다.

이것을 이용해 평균 margin improvement와 confidence interval을 보고한다.

이 방법은 단순 accuracy보다 작은 효과를 포착하기 유리하다.

---

# 9. 900/100/300의 최종 역할

권장 역할은 다음과 같다.

| 데이터 | 수량 | 역할 |
|---|---:|---|
| Train | 900 | Stage 1 집중학습 |
| Validation | 100 | checkpoint / 학습 과정 모니터링 |
| Held-out | 300 | 최종 semantic probe |
| **합계** | **1,300** | |

중요한 점은 **1,300개가 하나의 학습 corpus라는 뜻이 아니다.**

```text
900 + 100 = Stage 1 prototype
300       = independent benchmark
```

이다.

---

# 10. 300M-token 표준 학습과의 관계

향후 300M-token 본 실험에서는 현재 1,000개를 그대로 넣지 않는다.

대신 향후 약 3M-token Stage 1 corpus가 만들어졌을 경우:

```text
Baseline:
300M baseline

Stage1:
297M baseline
+ 3M Stage1
= 300M
```

형태로 비교한다.

즉 현재 900/100은 **3M expansion을 만들기 전의 prototype feasibility 단계**다.

---

# 11. 실험 계층을 명확히 분리할 것

두 종류의 실험을 혼동하지 않는다.

## Experiment A — Stage 1 feasibility

```text
100M base model
→ Train 900 집중학습
→ Val 100
→ Held-out 300
```

목적:

> Stage 1 semantic curriculum이 학습 가능하고 일반화 가능한가?

## Experiment B — Large-scale mixture experiment

```text
300M total tokens

Baseline:
300M baseline

Stage1:
297M baseline + 3M Stage1
```

목적:

> 실제 large-scale pretraining mixture의 약 1%를 Stage 1 semantic corpus로 교체했을 때 효과가 있는가?

A와 B는 서로 다른 질문이다.

---

# 12. Held-out 300도 함께 수정해야 한다

기존 held-out 300은 자유생성 평가를 전제로 한 다음 구조를 가진다.

```text
id
split
 task
prompt
answer
key_relations
difficulty
```

이를 **contrastive semantic probe용 benchmark**로 변경할 것을 제안한다.

## 12.1 변경된 기본 schema

각 item은 최소 다음 정보를 갖는다.

```json
{
  "id": "E-001",
  "task_type": "identity",
  "prompt": "수달은 어떤 범주의 동물인가?",
  "candidates": [
    "포유류",
    "어류",
    "파충류",
    "조류"
  ],
  "correct_index": 0,
  "required_concepts": [
    "수달",
    "포유류"
  ],
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
      "object": "어류"
    }
  ],
  "difficulty": 1
}
```

## 12.2 `key_relations`의 역할 변경

기존 `key_relations`는 semantic relation과 reasoning constraint가 섞여 있으므로 benchmark 채점용 단일 relation field로 사용하지 않는다.

다음처럼 분리한다.

```text
required_concepts
required_relations
forbidden_relations
reasoning_constraints
```

예를 들어 `attribute_not_category`, `unknown_not_false`, `same_function_not_identity` 같은 항목은 실제 대상 간 relation이라기보다 **평가 제약조건 또는 오류 유형**으로 취급한다.

## 12.3 후보(distractor) 설계 원칙

정답 이외의 3개 후보는 단순히 무관한 단어를 넣지 않는다.

좋은 distractor는 정답과 같은 semantic neighborhood에 있어야 한다.

예:

```text
수달은 어떤 범주의 동물인가?

A. 포유류      ← 정답
B. 어류
C. 파충류
D. 조류
```

다음과 같은 distractor는 변별력이 낮다.

```text
A. 포유류
B. 냉장고
C. 삼각형
D. 주전자
```

## 12.4 `forbidden_relations`

개념 경계·반례 문제에서는 정답 관계뿐 아니라 명백히 잘못된 관계도 기록한다.

예:

```json
{
  "required_relations": [
    {
      "type": "inside",
      "subject": "사과",
      "object": "상자"
    }
  ],
  "forbidden_relations": [
    {
      "type": "part_of",
      "subject": "사과",
      "object": "상자"
    }
  ]
}
```

이를 통해 `inside → part_of`와 같은 관계 혼동을 별도로 측정할 수 있다.

## 12.5 최종 평가 방식

Held-out 300에서는 free-generation EM/F1을 기본 지표로 사용하지 않는다.

대신:

```text
prompt
   ↓
4 candidate likelihoods
   ↓
length-normalized conditional log-likelihood
   ↓
argmax candidate
   ↓
accuracy
   +
correct-vs-best-wrong margin
```

을 기본으로 한다.

## 12.6 Paired benchmark

Baseline과 Stage 1 모델에 정확히 동일한 prompt/candidate set을 사용한다.

각 item마다:

\[
M_i = S(correct)-\max(S(wrong))
\]

를 구한다.

그리고:

\[
\Delta M_i = M_{Stage1,i}-M_{Baseline,i}
\]

를 계산한다.

최종 결과에는 최소한:

- forced-choice accuracy
- mean margin
- paired mean margin improvement
- confidence interval
- concept generalization accuracy
- relation composition accuracy
- boundary accuracy

를 보고한다.

## 12.7 Benchmark freeze 규칙

Held-out 300은 최종 모델과 학습 규칙이 확정될 때까지 결과를 보지 않는다.

Held-out 결과를 보고:

- learning rate 변경
- checkpoint 변경
- corpus 변경
- curriculum 변경
- architecture 변경
- tokenizer 변경

등을 수행하면 해당 benchmark는 더 이상 완전한 최종 test로 취급하지 않는다.

따라서 benchmark schema와 distractor는 모델 비교 전에 freeze하고, scorer version도 고정한다.

---

# 13. Held-out benchmark와의 관계

현재 300 held-out은 다음 용도로 사용한다.

```text
final checkpoint
        ↓
held-out 300
        ↓
semantic probe
```

이 benchmark는 3M corpus의 생성/확장 과정에서 절대로 사용하면 안 된다.

특히 benchmark의 정답·distractor를 보고 3M corpus를 수정하면 contamination이 발생한다.

---

# 14. Benchmark는 contrastive probe로 변경하는 것을 권장

현재 free-generation 방식 대신:

```text
prompt
A
B
C
D
```

를 제공하고 각 candidate의 conditional likelihood를 비교한다.

예:

```text
수달은 어떤 범주의 동물인가?

A. 포유류
B. 어류
C. 파충류
D. 조류
```

모델이 실제 문장을 생성할 필요가 없다.

---

# 15. Accuracy보다 paired margin이 중요하다

Baseline과 Stage 1을 동일 item에서 비교한다.

\[
\Delta_i = Margin_{Stage1,i}-Margin_{Baseline,i}
\]

을 사용한다.

그리고 평균뿐 아니라 item-level distribution과 confidence interval을 함께 보고한다.

---

# 16. 내가 권하는 최종 구조

현재 prototype 단계에서는 다음 구조를 기준으로 실험을 진행한다.

```text
Stage 1 prototype
├── train 900
│   └── concentrated curriculum training
│
└── val 100
    └── checkpoint selection

Independent held-out
└── 300
    └── contrastive semantic probe
```

그리고 효과가 확인된 경우에만 별도의 3M-token Stage 1 corpus를 구축하여 300M-token 고정 예산 실험으로 확장한다.

```text
A: 300M baseline
B: 297M baseline + 3M Stage1
C: 297M baseline + 3M random/control
```

---

# 17. 최종 검토 요청

다음 변경에 대한 검토를 요청한다.

| 항목 | 기존 | 변경안 |
|---|---|---|
| Train 900 | 일반 학습 데이터 | **Stage 1 집중학습용 prototype** |
| Val 100 | validation | **유지** |
| Held-out 300 | 자유생성 benchmark | **contrastive semantic probe** |
| Scoring | 자유생성 + 문자열/의미 채점 | **candidate likelihood + paired margin** |
| 1,000개 역할 | 대규모 학습 corpus | **Stage 1 semantic seed/prototype** |
| 향후 실제 혼입 | 현재 1,000개 | **약 3M-token expansion** |
| 300M 실험 | 해당 없음 | **297M baseline + 3M Stage1** |
| 외부 LLM judge | 고려 가능 | **사용하지 않음** |

## 18. 요청하는 검토 범위

특히 다음 사항을 비판적으로 검토해 주기 바란다.

1. **900 train / 100 validation을 Stage 1 집중학습 prototype으로 사용하는 것이 타당한가?**
2. **held-out 300을 자유생성 대신 contrastive likelihood probe로 바꾸는 것이 현재 100M base LM에 적절한가?**
3. **`required_concepts / required_relations / forbidden_relations / reasoning_constraints`로 schema를 분리하는 것이 적절한가?**
4. **4-choice distractor 설계가 실제 semantic discrimination을 제공할 수 있는가?**
5. **paired margin을 주요 지표 중 하나로 사용하는 것이 적절한가?**
6. **이 구조에서 별도의 deterministic scorer가 실제로 필요한가, 아니면 forced-choice likelihood만으로 충분한가?**
7. **3M-token expansion으로 넘어가기 전에 반드시 수행해야 할 feasibility experiment가 추가로 있는가?**

본 문서는 구현 승인을 의미하지 않는다. 위 사항에 대한 **타당성·수학적 적절성·실험적 독립성·구현 복잡성·기존 평가 도구와의 중복 여부를 비판적으로 검토한 후**, 필요하면 수정된 대안을 제안해 주기를 요청한다.
