# 900 / 100 / 300 데이터셋 활용방안 변경 제안 검토 요청서

## 1. 검토 목적

현재 `datasets/TinyDataset/stage1_dataset/`에는 다음 데이터가 존재한다.

```text
stage1_dataset/
├── train/
├── val/
├── held-out_v1_archive/
└── held-out_v2/
```

현재 Stage 1 prototype의 본체는 총 1,000개이며, 다음과 같이 나뉘어 있다.

```text
Stage 1 prototype 1,000
├── train 900
└── val 100
```

별도로 `held-out_v2/`에 300개 benchmark가 존재한다.

본 문서에서 검토를 요청하는 것은 **폴더명이나 파일 구조를 변경하는 것이 아니라, 이 데이터들의 실험상 활용 방법을 변경하는 것**이다.

특히 현재 1,000개 prototype의 규모가 약 28.5K token 수준이므로, 이를 300M-token 규모의 일반적인 pretraining corpus에 포함시키는 데이터로 보는 것은 적절하지 않다.

따라서 현재 1,000개는 **대규모 pretraining 데이터가 아니라 Stage 1의 소규모 집중학습 prototype**으로 활용하는 방안을 검토 요청한다.

---

# 2. 현재 1,000개 prototype을 일반 pretraining 데이터로 사용하는 문제

현재 1,000개 전체는 약 28.5K token 수준이다.

300M-token standard training과 비교하면:

\[
\frac{28.5K}{300M}\approx0.0095\%
\]

이다.

따라서 `train/`의 900개를 300M-token standard pretraining에 단순히 포함시키는 방식은 전체 학습량에서 차지하는 비중이 너무 작다.

반대로 동일한 900개를 반복적으로 많이 노출시키면 전체 정보량에 비해 특정 문장과 semantic pattern이 지나치게 반복될 수 있으며, prototype 자체에 대한 memorization 또는 overfitting 가능성이 커진다.

따라서 현재 1,000개를 다음과 같이 정의하는 것이 적절한지 검토를 요청한다.

> **현재 1,000개 = Stage 1 semantic curriculum prototype이며, 300M-token standard pretraining corpus의 일부로 사용하는 데이터가 아니다.**

---

# 3. 제안하는 현재 실험의 정확한 정의

## 3.1 폴더 구조는 변경하지 않는다

현재 디렉터리 구조를 그대로 사용한다.

```text
stage1_dataset/
├── train/
├── val/
├── held-out_v1_archive/
└── held-out_v2/
```

이 문서에서 제안하는 변경은 **파일 이동·이름 변경이 아니라 실험상 역할의 변경**이다.

## 3.2 현재 prototype 실험에서 비교할 모델

현재 실험에서 비교할 모델은 정확히 두 개다.

### Model A — pretrained baseline

```text
기존 100M 모델
→ 기존 300M-token standard pretraining 완료
→ Stage 1 추가학습 없음
```

### Model B — Stage 1 adapted model

```text
Model A와 동일한 100M pretrained checkpoint
→ train/의 Stage 1 900개 추가학습
→ val/의 100개로 validation 및 checkpoint 선택
```

그리고 **Model A와 Model B를 동일한 `held-out_v2/` 300개로 비교**한다.

즉 현재 실험의 핵심 질문은 다음 하나다.

> **이미 300M-token standard pretraining을 마친 동일한 100M 모델에 Stage 1의 900개를 추가로 집중학습했을 때, 추가학습을 하지 않은 동일한 pretrained baseline과 비교하여 held-out_v2 semantic benchmark에서 측정 가능한 차이가 발생하는가?**

이것이 본 문서에서 제안하는 900/100/300 활용 변경의 핵심이다.

---

# 4. Train 900의 역할

`train/`의 900개는 **300M-token standard pretraining에 혼입하는 데이터가 아니다.**

다음과 같은 별도의 Stage 1 집중학습 단계에서 사용한다.

```text
Model A
   ↓
Stage 1 train 900
   ↓
Model B
```

목적은 다음을 확인하는 것이다.

> **소규모로 설계된 Stage 1 semantic curriculum을 이미 pretrained된 100M 모델에 집중적으로 학습시켰을 때, 그 학습 신호가 모델에 주입되는가?**

이 결과는 다음을 의미하지 않는다.

- 모델의 전체 일반 지능이 향상되었다.
- 300M-token standard pretraining 자체가 개선되었다.
- 자연어 전반의 능력이 향상되었다.

즉 **현재 실험은 Stage 1 prototype의 학습 가능성과 semantic adaptation 가능성을 확인하는 실험**이다.

---

# 5. Validation 100의 역할

`val/`의 100개는 `train/`의 900개에 대한 별도의 validation 데이터로 사용한다.

Validation은 다음 목적으로만 사용한다.

- Stage 1 추가학습 중 validation loss 관찰
- checkpoint selection
- 필요시 사전에 정한 범위 내에서 학습 종료 시점 결정
- 필요시 제한적인 hyperparameter 비교

Validation record 자체는 gradient update에 사용하지 않는다.

즉:

```text
train 900
→ gradient update

val 100
→ validation evaluation
→ checkpoint selection
```

Validation의 결과는 학습 과정의 의사결정에 사용되므로, 최종 benchmark인 `held-out_v2`와 구분한다.

---

# 6. Held-out v2 300의 현재 구현 및 역할

`held-out_v2/`의 300개는 **본 실험에서 사용할 최종 semantic benchmark**다.

이 부분은 새로 구현할 항목이 아니다. **이미 benchmark v2 형식으로 구현되어 있는 현재 상태를 그대로 사용한다.**

현재 구현된 주요 특징은 다음과 같다.

- 300개 benchmark
- `candidates`를 이용한 4-choice contrastive evaluation
- `correct_index`
- `required_concepts`
- canonicalized `required_relations`
- canonicalized `forbidden_relations`
- 난이도 정보
- 외부 LLM judge를 사용하지 않는 평가 구조
- candidate별 likelihood를 비교하는 forced-choice 방식

따라서 본 문서에서는 held-out v2 자체를 다시 설계하거나 재작성하는 것을 제안하지 않는다.

최종 평가에서는 동일한 benchmark item을 Model A와 Model B에 적용한다.

```text
Model A ─┐
         ├→ held-out_v2 300
Model B ─┘
```

---

# 7. 현재 실험에서의 benchmark 측정 방식

현재 held-out v2의 목적은 자유생성 능력을 평가하는 것이 아니라, **동일한 prompt와 후보 집합에서 모델이 어느 후보를 더 선호하는지**를 측정하는 것이다.

후보 `y`에 대한 기본 점수는 다음과 같은 length-normalized conditional log-likelihood를 사용한다.

\[
S(y|x)=\frac{1}{|y|}\sum_t \log P(y_t|x,y_{<t})
\]

각 item에서 가장 높은 후보를 모델의 선택으로 간주한다.

또한 정답 후보와 가장 높은 오답 후보의 차이를 다음과 같이 기록한다.

\[
Margin_i = S(correct)-\max S(wrong)
\]

Model A와 Model B의 차이는:

\[
\Delta Margin_i = Margin_{B,i}-Margin_{A,i}
\]

로 계산한다.

---

# 8. 현재 실험에서 보고할 결과

최소 다음 결과를 보고하는 것을 제안한다.

### 8.1 Forced-choice accuracy

동일한 300개 문항에서 정답 후보를 선택한 비율.

### 8.2 Mean margin

정답 후보와 가장 높은 오답 후보 사이의 평균 score 차이.

### 8.3 Paired margin improvement

동일한 benchmark item에서 Model B와 Model A의 margin 차이.

### 8.4 Benchmark 영역별 결과

held-out v2의 구성에 따라 최소 다음을 분리한다.

- concept/generalization 성격의 항목
- relation/composition 성격의 항목
- boundary/counterexample 성격의 항목

필요하면 confidence interval도 함께 보고한다.

---

# 9. 현재 실험에서 900/100/300이 의미하는 것

최종적으로 데이터의 역할은 다음과 같다.

| 데이터 | 수량 | 현재 제안하는 역할 |
|---|---:|---|
| `train/` | 900 | pretrained Model A에 Stage 1을 집중 추가학습하는 prototype training set |
| `val/` | 100 | Stage 1 추가학습의 validation 및 checkpoint selection |
| `held-out_v2/` | 300 | Model A와 Model B를 비교하는 최종 semantic benchmark |
| `held-out_v1_archive/` | - | 보존용. 본 실험에서는 사용하지 않음 |

중요한 점은:

```text
900 + 100
= Stage 1 prototype의 학습/validation 데이터

300
= 독립적인 최종 benchmark
```

이며, **1,300개 전체를 하나의 학습 corpus로 사용하는 것이 아니다.**

---

# 10. 현재 실험의 해석 범위

이 실험에서 다음 결과가 나왔다고 가정한다.

```text
Model A: held-out_v2 = 52.0%
Model B: held-out_v2 = 57.0%
```

이 결과는 다음 정도의 결론을 지지할 수 있다.

> **300M-token pretrained 100M 모델에 Stage 1 900개를 집중적으로 추가학습한 조건에서, 추가학습하지 않은 동일 pretrained baseline보다 held-out semantic benchmark 성능이 높았다.**

그러나 이것만으로 다음과 같은 결론을 내려서는 안 된다.

> Stage 1이 300M-token pretraining 자체의 품질을 향상시켰다.

또는:

> Stage 1이 모델의 일반 지능을 향상시켰다.

현재 900개 prototype은 이런 대규모 효능을 검증하기 위한 규모가 아니다.

---

# 11. 현재 제안과 향후 대규모 실험의 구분

본 문서의 현재 검토 대상은 **900/100/300 prototype 실험**이다.

향후 Stage 1 corpus를 충분히 확장하게 되면 별도의 large-scale pretraining 실험을 설계할 수 있다. 그 실험은 현재 900개 실험과는 다른 질문을 다룬다.

따라서 현재 문서에서는 향후 대규모 corpus의 구체적인 규모나 mixture 구성은 **현재 900/100/300 실험의 일부로 취급하지 않는다.**

---

# 12. 권장 실험 흐름

현재 prototype에 대해서는 다음 순서가 가장 명확하다.

```text
기존 300M-token pretrained 100M checkpoint
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
     Model A           Model B
   추가학습 없음      Stage 1 train 900
                         │
                       val 100
                         │
                    checkpoint 선택
        │                 │
        └────────┬────────┘
                 ▼
          held-out_v2 300
                 │
                 ▼
       paired semantic comparison
```

이 실험으로 확인하려는 것은 단 하나다.

> **Stage 1의 900개를 pretrained 100M 모델에 집중적으로 추가학습하는 것만으로, 추가학습하지 않은 동일 pretrained baseline과 비교해 held-out semantic benchmark에 측정 가능한 변화가 발생하는가?**

---

# 13. 검토 요청

다음 사항을 비판적으로 검토해 주기 바란다.

1. **기존 300M-token pretrained 100M checkpoint를 출발점으로 하고, Model A는 추가학습하지 않으며 Model B만 Stage 1 train 900을 추가학습하는 비교 설계가 실험 목적에 적절한가?**
2. **900개를 일반 pretraining corpus에 혼입하지 않고 별도의 집중학습 prototype으로 사용하는 것이 타당한가?**
3. **val 100을 checkpoint selection에 사용하는 것이 적절한가? 별도의 validation 방법이 필요한가?**
4. **이미 구현된 held-out v2의 forced-choice likelihood/paired-margin benchmark 방식이 이 prototype 실험의 목적에 적절한가?**
5. **현재 900/100/300 규모에서 이 실험으로 주장할 수 있는 결론과 주장할 수 없는 결론의 범위가 적절한가?**
6. **현재 실험 설계에서 추가로 필요한 control 또는 leakage 검사가 있는가?**

본 문서는 구현 승인을 의미하지 않는다. 위 실험 정의의 **논리적 타당성, 비교 대상의 적절성, 데이터 역할의 명확성, validation/benchmark 독립성, 통계적 해석 가능성**을 비판적으로 검토해 주기 바란다.
