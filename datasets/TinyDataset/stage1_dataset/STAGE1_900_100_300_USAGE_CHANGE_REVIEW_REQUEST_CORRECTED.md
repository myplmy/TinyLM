# 900 / 100 / 300 데이터셋 활용방안 변경 제안 검토 요청서

## 1. 검토 목적

현재 `datasets/TinyDataset/stage1_dataset/`에는 다음 데이터가 있다.

```text
stage1_dataset/
├── train/
├── val/
├── held-out_v1_archive/
└── held-out_v2/
```

현재 Stage 1 prototype은 총 1,000개이며 다음과 같이 구성되어 있다.

```text
Stage 1 prototype 1,000
├── train 900
└── val 100
```

별도로 `held-out_v2/`에 300개 benchmark가 존재한다.

현재 1,000개 prototype 전체는 약 28.5K token 수준이다. 이를 300M-token standard pretraining corpus의 일부로 그대로 포함시키면 비중이 약 0.0095%에 불과하므로, 일반적인 대규모 pretraining에서 의미 있는 별도 데이터 구성 효과를 검증하기에는 지나치게 작다.

따라서 **현재 900/100/300 데이터의 폴더 구조는 변경하지 않고, 실험에서의 활용 목적만 변경하는 방안**을 검토 요청한다.

---

# 2. 변경 대상의 정확한 의미

이번 제안에서 변경하는 것은 파일명이나 폴더명이 아니다.

현재 존재하는:

```text
train/900
val/100
held-out_v2/300
```

을 그대로 사용하되, **각 데이터가 어떤 실험에서 어떤 역할을 담당하는지를 변경·명확화**한다.

특히 `train/900`은 300M-token standard pretraining에 섞어 넣는 학습 데이터로 사용하지 않는다.

`train/900`은 이미 300M-token standard pretraining을 마친 100M 모델에 **별도로 추가 학습하는 Stage 1 prototype training set**으로 사용한다.

---

# 3. 현재 제안하는 실험의 정확한 정의

본 문서에서 검토하는 실험은 **두 모델의 비교 실험**이다.

## Model A — pretrained baseline

```text
100M 모델
→ 기존 300M-token standard pretraining 완료
→ Stage 1 추가 학습 없음
```

Model A는 Stage 1 데이터에 추가로 노출하지 않는다.

## Model B — Stage 1 additional-training model

```text
Model A와 동일한 100M pretrained checkpoint
→ train/의 Stage 1 900개로 별도 추가 학습
→ val/의 100개로 validation 및 checkpoint selection
```

Model B만 Stage 1 900개를 추가 학습한다.

## 최종 비교

```text
Model A ─┐
         ├─→ 동일한 held-out_v2 300개 평가
Model B ─┘
```

즉 본 실험의 핵심 질문은 다음 하나다.

> **이미 300M-token standard pretraining을 마친 동일한 100M 모델에 Stage 1의 900개를 별도로 추가 학습했을 때, 추가 학습을 하지 않은 동일한 pretrained baseline과 비교하여 held-out_v2 semantic benchmark에 측정 가능한 차이가 발생하는가?**

이 문서에서 말하는 `Stage 1 추가 학습`은 900개를 300M-token pretraining에 혼입하는 것을 의미하지 않는다.

---

# 4. Train 900의 역할

`train/`의 900개는 **일반 300M-token standard pretraining corpus에 혼입하지 않는다.**

다음과 같이 별도의 추가 학습 단계에서 사용한다.

```text
기존 300M-token pretrained checkpoint
                ↓
          Stage 1 추가 학습
                ↓
        train/ 900 examples
```

목적은 다음을 확인하는 것이다.

> **소규모 Stage 1 semantic curriculum을 이미 pretrained된 100M 모델에 추가 학습했을 때, 그 curriculum의 학습 신호가 모델에 주입되는지 확인한다.**

여기서의 결과는 다음을 의미하지 않는다.

- 100M 모델의 전체 일반 지능이 향상되었다.
- 300M-token standard pretraining 자체가 개선되었다.
- 자연어 전반의 성능이 향상되었다.
- 900개가 실제 대규모 pretraining에 충분한 데이터라는 것이 증명되었다.

따라서 `train/900` 실험의 해석 범위는 **Stage 1 prototype의 추가 학습 가능성과 semantic signal 주입 여부**로 제한한다.

---

# 5. Validation 100의 역할

`val/`의 100개는 Stage 1 추가 학습 과정에서 사용한다.

```text
train/ 900
→ gradient update

val/ 100
→ validation loss 관찰
→ checkpoint selection
```

Validation record 자체는 gradient update에 사용하지 않는다.

Validation의 결과는 Stage 1 추가 학습 과정의 의사결정에 사용해도 된다. 예를 들어 다음을 결정할 수 있다.

- 어느 checkpoint를 최종 Model B로 선택할지
- 사전에 정의한 학습 종료 기준을 만족하는지
- 필요할 경우 제한된 범위의 추가 학습 설정을 비교할지

단, 이 과정에서 `held-out_v2`의 결과를 사용해서는 안 된다.

---

# 6. Held-out v2 300의 현재 구현 및 역할

`held-out_v2/`의 300개는 **이미 구현된 최종 semantic benchmark**이며, 본 제안에서는 그 schema를 다시 변경하는 것을 제안하지 않는다.

현재 구현된 benchmark는 다음과 같은 특성을 가진다.

- 300개 benchmark item
- 4-choice candidate 구조
- `correct_index`
- `required_concepts`
- canonical `required_relations`
- canonical `forbidden_relations`
- difficulty 정보
- 외부 LLM judge를 사용하지 않는 평가 구조
- candidate별 likelihood를 비교하는 forced-choice 방식

본 실험에서는 동일한 `held-out_v2` 300개를 Model A와 Model B 모두에 적용한다.

```text
Model A ─┐
         ├─→ held-out_v2 300
Model B ─┘
```

`held-out_v2`는 다음 목적으로만 사용한다.

> **Stage 1 900개 추가 학습 전후의 모델 차이를 동일한 semantic benchmark에서 비교한다.**

`held-out_v2`는 train, validation, checkpoint selection, hyperparameter tuning에 사용하지 않는다.

---

# 7. Held-out v2 평가 방식

현재 구현된 benchmark는 자유생성 답변의 EM/F1을 주된 방식으로 사용하지 않는다.

각 item의 prompt와 4개 후보에 대해 후보별 conditional likelihood를 비교한다.

기본 점수는 다음과 같은 length-normalized conditional log-likelihood를 사용한다.

\[
S(y|x)=\frac{1}{|y|}\sum_t \log P(y_t|x,y_{<t})
\]

가장 높은 후보를 모델의 선택으로 간주한다.

또한 정답과 가장 높은 오답 사이의 margin을 기록한다.

\[
Margin_i=S(correct)-\max(S(wrong))
\]

Model A와 Model B의 비교는 동일한 item에서 수행한다.

\[
\Delta Margin_i=Margin_{B,i}-Margin_{A,i}
\]

이를 이용해 paired margin improvement를 계산한다.

---

# 8. 현재 실험에서 보고할 지표

최소 다음 지표를 보고한다.

### 8.1 Forced-choice accuracy

300개 benchmark에서 정답 후보를 선택한 비율.

### 8.2 Mean margin

정답 후보와 가장 높은 오답 후보의 평균 점수 차이.

### 8.3 Paired margin improvement

동일한 benchmark item에서 Model B와 Model A의 margin 차이.

### 8.4 Benchmark 영역별 성능

held-out_v2의 기존 task 구분에 따라 적절한 하위 지표를 보고한다.

- concept/generalization 계열
- relation/composition 계열
- boundary/counterexample 계열

필요한 경우 confidence interval도 함께 보고한다.

---

# 9. 900/100/300의 최종 역할

현재 제안에 따른 역할은 다음과 같다.

| 데이터 | 수량 | 실험상 역할 |
|---|---:|---|
| `train/` | 900 | 기존 300M-token pretrained 100M 모델에 Stage 1을 별도로 추가 학습하는 prototype training set |
| `val/` | 100 | Stage 1 추가 학습 과정의 validation 및 checkpoint selection |
| `held-out_v2/` | 300 | Model A와 Model B를 동일 조건에서 비교하는 최종 semantic benchmark |
| `held-out_v1_archive/` | - | 보존용이며 본 실험에서는 사용하지 않음 |

**폴더 구조 자체는 변경하지 않는다.**

---

# 10. 본 실험에서 사용하는 모델과 사용하지 않는 모델

본 문서에서 필수 비교 대상은 다음 두 모델이다.

```text
Model A
= 기존 300M-token standard pretraining을 완료한 100M 모델
= Stage 1 추가 학습 없음

Model B
= Model A와 동일한 checkpoint에서 시작
= train/의 900개 Stage 1 추가 학습
= val/의 100개로 checkpoint 선택
```

다음 조건은 본 실험의 비교 대상이 아니다.

```text
랜덤 초기화 모델
```

랜덤 초기화 모델을 추가하면 별도의 질문이 생기므로 본 prototype 실험의 필수 조건으로 넣지 않는다.

또한 다음 실험도 본 문서의 현재 검토 대상이 아니다.

```text
300M-token pretraining 과정에 Stage 1 900개를 혼입하는 실험
```

현재 제안에서는 900개를 기존 300M-token training에 섞지 않고, 300M-token pretraining이 끝난 후 Model A에 별도로 추가 학습한다.

---

# 11. 현재 실험에서 주장할 수 있는 결론의 범위

예를 들어 다음과 같은 결과가 나왔다고 가정한다.

```text
Model A: 50%
Model B: 56%
```

이 경우 다음 정도의 결론을 검토할 수 있다.

> **300M-token standard pretraining을 완료한 100M 모델에 Stage 1 900개를 별도로 추가 학습한 조건에서, 추가 학습하지 않은 동일 pretrained baseline보다 held-out_v2 semantic benchmark 성능이 높았다.**

그러나 다음과 같이 확대 해석해서는 안 된다.

> Stage 1이 300M-token pretraining 자체를 개선했다.

또는:

> Stage 1이 모델의 일반 지능을 향상시켰다.

또는:

> Stage 1 900개면 실제 대규모 pretraining에서도 충분하다.

현재 실험은 이러한 대규모 효능을 검증하는 실험이 아니다.

---

# 12. 실험 독립성 규칙

`held-out_v2` 결과는 최종 비교를 위해서만 사용한다.

다음 행동을 `held-out_v2` 결과를 보고 수행하면 해당 평가를 더 이상 완전한 blind final test로 취급해서는 안 된다.

- train 데이터 수정
- Stage 1 curriculum 수정
- 학습 횟수 또는 budget 변경
- hyperparameter 변경
- checkpoint selection 기준 변경
- 모델 구조 변경

따라서 benchmark 결과를 처음 확인한 뒤 모델이나 학습 조건을 수정해야 한다면 새로운 blind benchmark가 필요하다.

---

# 13. 검토 요청

다음 사항을 비판적으로 검토해 주기 바란다.

1. **기존 300M-token standard pretraining을 완료한 100M checkpoint를 Model A로 두고, 동일 checkpoint에 Stage 1 train 900만 별도 추가 학습한 Model B를 비교하는 설계가 타당한가?**
2. **현재 28.5K token 수준의 Stage 1 prototype을 이러한 소규모 추가 학습 feasibility experiment에 사용하는 것이 타당한가?**
3. **val 100을 Stage 1 추가 학습의 checkpoint selection에 사용하는 것이 적절한가?**
4. **이미 구현된 held-out_v2 300의 forced-choice likelihood 및 paired-margin 평가 방식이 이 비교 목적에 적절한가?**
5. **현재 900/100/300 규모에서 얻을 수 있는 결론의 범위가 적절하게 제한되어 있는가?**
6. **본 실험에서 추가로 필요한 control, leakage 검사 또는 statistical analysis가 있는가?**

본 문서는 구현 승인을 의미하지 않는다. 위 실험 정의의 **논리적 타당성, 비교 대상의 적절성, 데이터 역할의 명확성, validation/benchmark 독립성, 통계적 해석 가능성**을 비판적으로 검토해 주기 바란다.
