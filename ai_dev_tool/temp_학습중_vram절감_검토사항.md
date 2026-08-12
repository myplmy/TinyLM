---

# TinyLM 학습 VRAM 과다사용 및 학습속도 최적화 사전 검토·작업 지시서

## 0. 문서 목적

본 문서는 약 100M parameter급 TinyLM을 RTX 4070 Ti SUPER 16GB VRAM에서 학습할 때 발생하는 다음 문제를 분석하고, 코드 수정 전에 작업용 AI가 변경의 타당성을 검토할 수 있도록 하기 위한 것이다.

### 현재 문제

* 100M급 student 모델 학습에서 VRAM 사용량이 약 **14~15GB**
* KD teacher를 사용하는 경우 VRAM peak가 더 증가
* 하나의 실험에 약 **3~6시간**, 일부 실험에서는 약 90분 수준의 학습시간이 발생
* 동일한 학습 token budget에서 가능한 한 많은 실험을 수행해야 하므로 **wall-clock training time 단축이 중요**
* 그러나 단순히 VRAM을 줄이기 위해 checkpointing 등을 활성화하여 학습속도를 희생하는 것은 현재 연구 목적에 부합하지 않음

따라서 본 문서에서는:

> **① 실제 VRAM resident 원인, ② 순간적인 VRAM peak 원인, ③ 계산시간 증가 원인, ④ 학습 품질 변화 가능성**

을 분리해서 분석한다.

---

# 1. 현재 최우선 판단

현재 코드 분석 결과, VRAM 문제를 하나의 원인으로 간주해서는 안 된다.

현재 구조에서는 대략 다음과 같이 VRAM이 구성될 가능성이 있다.

```text
GPU VRAM
│
├─ Student parameters
│
├─ Student gradients
│
├─ Optimizer states
│
├─ Student activations
│      └─ no-checkpoint이므로 상대적으로 큼
│
├─ Teacher parameters
│
├─ Teacher forward activations
│
├─ Student logits
│
├─ Teacher logits
│
├─ KD temporary tensors
│
├─ Ternary autograd saved tensors
│      ├─ x
│      ├─ aw
│      ├─ alpha
│      └─ eff
│
└─ CUDA / GEMM / Triton temporary workspace
```

따라서 단순히:

> "100M 모델인데 왜 15GB를 쓰느냐?"

라는 접근은 부정확하다.

특히 **KD + no-checkpoint + custom ternary autograd**가 동시에 사용되는 경우에는 100M parameter라는 모델 크기만으로 VRAM 사용량을 판단하면 안 된다.

---

# 2. 문제를 4개로 분리한다

이번 작업에서는 다음 네 가지를 반드시 별도로 평가한다.

| 문제                               | 주요 대상               |          우선순위 |
| -------------------------------- | ------------------- | ------------: |
| A. KD full logits VRAM           | `trainer.py`        |         별도 실험 |
| B. Ternary autograd saved tensor | `ternary_kernel.py` | **최우선 코드 검토** |
| C. no-checkpoint activation      | `trainer.py`        |        **유지** |
| D. initialization SVD            | `init_utils.py`     |            낮음 |

그리고 별도로:

| 추가 방법                | 검토                      |
| -------------------- | ----------------------- |
| Teacher CPU resident | 속도/VRAM trade-off 분석    |
| Saved tensor 최소화     | 속도/VRAM/품질 trade-off 분석 |
| BF16 AdamW           | 현재는 주범 아님               |
| Loader               | VRAM 주범 아님              |
| Evaluate             | 주범 아님                   |
| Prepare              | training VRAM과 무관       |

---

# 3. A. KD full logits는 별도 실험으로 분리

## 3.1 현재 문제

KD를 사용하는 경우 student와 teacher 모두:

[
L\times V
]

형태의 logits를 생성할 가능성이 있다.

여기서:

* (B): batch
* (T): sequence length
* (V): vocabulary size

이면 logits 크기는:

[
B\times T\times V
]

이다.

예를 들어:

[
B=8,\quad T=1024,\quad V=32768
]

이면:

[
8\times1024\times32768
======================

268,435,456
]

elements이다.

BF16 기준:

[
268,435,456\times2
\approx536.9MB
]

이다.

따라서 student logits 하나만 약 **537MB**이다.

teacher logits까지 동시에 존재하면 단순 logits만:

[
\approx1.07GB
]

이다.

여기에 softmax, log-softmax, KD loss 계산 과정의 temporary tensor가 추가될 수 있다.

---

# 4. KD full logits를 즉시 제거해서는 안 되는 이유

현재 TinyLM 연구에서는 KD가 모델 성능에 영향을 미치는 중요한 실험 요소다.

따라서:

```text
full logits KD
```

를:

```text
top-k KD
```

또는:

```text
CPU teacher
```

등으로 바로 바꾸면,

**VRAM 개선과 동시에 학습 목표 자체가 변경될 가능성**이 있다.

특히 top-k KD는 teacher distribution의 tail을 제거하기 때문에:

[
D_{KL}(p_T || p_S)
]

자체가 달라진다.

따라서 이는 단순한 implementation optimization이 아니라 **training objective 변경 가능성이 있는 실험**이다.

---

# 5. KD full logits 별도 실험계획

다음 3개를 최소한 비교한다.

### KD-A — 현재 baseline

```text
teacher GPU
full teacher logits
full student logits
current KD
```

### KD-B — teacher logits inference 최적화

가능하면 teacher는:

```text
torch.no_grad()
```

상태에서 수행하되 full logits KD는 유지.

### KD-C — reduced-logit KD

예:

```text
top-k teacher distribution
```

또는 기타 memory-efficient KD.

단, KD-C는 **별도의 학습방법(ablation)**으로 취급한다.

---

# 6. KD 실험에서 반드시 측정할 것

각 실험에서:

```text
peak allocated VRAM
peak reserved VRAM
tokens/sec
step time
training loss
validation loss
final validation perplexity/loss
```

를 측정한다.

특히:

[
\Delta PPL
]

또는 validation loss 차이가 통계적으로/실험적으로 허용 가능한지를 봐야 한다.

### 결론 기준

예를 들어:

```text
full KD:
14.8 GB
100 tok/s
val 3.70

reduced KD:
10.5 GB
130 tok/s
val 3.71
```

이라면 reduced KD를 실험 가속 방법으로 고려할 수 있다.

반대로:

```text
10.5 GB
130 tok/s
val 3.82
```

라면 단순히 VRAM이 줄었다는 이유로 채택해서는 안 된다.

---

# 7. B. `custom ternary autograd`가 현재 가장 중요한 코드 검토 대상

현재 `ternary_kernel.py`의 custom autograd 구조에서 핵심적인 부분은:

```python
ctx.save_for_backward(x, aw, alpha, eff)
```

이다.

이 부분은 단순히 "tensor를 저장하므로 메모리를 먹는다"라고 판단하면 안 된다.

**각 tensor가 backward에서 왜 필요한지를 먼저 분석해야 한다.**

---

# 8. `save_for_backward()`의 각 tensor 역할

현재 저장되는 것으로 분석되는 tensor:

```text
x
aw
alpha
eff
```

### `x`

linear backward에서:

[
\frac{\partial L}{\partial W}
=============================

X^T G
]

또는 이에 대응하는 matrix multiplication을 계산하려면 input activation이 필요하다.

따라서 `x`는 상당히 정당한 저장 대상이다.

---

### `aw`

대략:

[
a_w=|W|
]

이며 STE backward의 window/weighting 계산에 사용된다.

예:

[
w_{in}
======

\frac{1}
{1+
\left(
\frac{|W|}
{c\alpha}
\right)^4
}
]

따라서 현재 구현에서는 `aw`가 필요하다.

하지만 중요한 점:

> `aw`는 `W.abs()`로부터 다시 계산할 수 있다.

즉 **저장 대신 backward에서 recompute 가능한 tensor**다.

---

### `alpha`

group-wise scale이다.

대략:

[
\alpha_g
========

\frac{\sum |W_i|M_i}
{\sum M_i}
]

형태다.

`alpha`는 weight보다 훨씬 작다.

group size가 128이라면 대략:

[
\frac{1}{128}
]

크기다.

따라서 `alpha`는 저장해도 VRAM 부담이 상대적으로 작다.

---

### `eff`

가장 주의해야 한다.

현재 effective weight:

[
W_{\mathrm{eff}}
================

W_q+(1-a)(W-W_q)
]

같은 형태를 사용한다.

즉 `eff`는 사실상 **full weight-size tensor**다.

따라서:

```text
weight
+
aw
+
eff
```

가 동시에 존재하면 상당한 중복 저장이 발생한다.

---

# 9. 왜 이것이 VRAM 측면에서 치명적일 수 있는가

100M 모델의 parameter 자체는 크지 않지만, 중요한 것은:

> **parameter tensor 하나를 저장하는 것과 parameter-size tensor를 autograd activation으로 여러 layer에 저장하는 것은 별개의 문제다.**

예를 들어 전체 ternary weight가 수백 MB라고 하자.

각 layer가:

```text
W
aw
eff
```

를 저장한다면:

```text
W
+ W-sized aw
+ W-sized eff
```

가 된다.

그리고 여기에:

```text
x
activation
teacher
student logits
```

가 추가된다.

따라서 모델 parameter가 100M이라는 사실만으로 VRAM이 작아야 한다는 결론은 성립하지 않는다.

---

# 10. 특히 `eff` 저장은 재검토 가치가 높다

backward에서 `gx`를 계산하려면:

[
G_x=G_yW_{\mathrm{eff}}
]

가 필요하다.

현재는 이 때문에 `eff`를 저장하는 것으로 보인다.

그러나:

[
W_{\mathrm{eff}}
]

는 backward 시점에 다시 계산할 수 있다.

즉:

```text
현재
forward
 ├─ calculate eff
 └─ save eff
       ↓
backward
 └─ use eff
```

를:

```text
개선
forward
 └─ save compact representation

backward
 ├─ reconstruct eff
 └─ use eff
```

로 변경할 수 있다.

---

# 11. `aw`도 동일한 원리

현재:

```text
forward
 └─ aw = abs(W)
       ↓
     save aw
```

이지만:

```text
backward
 └─ aw = abs(W)
```

로 재계산할 수 있다.

따라서:

```text
saved tensor:
x
alpha
```

중심의 구조를 검토할 수 있다.

단, **이 변경이 정확한지 확인하기 위해 기존 backward와 gradient parity test가 반드시 필요하다.**

---

# 12. 중요한 원칙: "저장 tensor 최소화"가 무조건 좋은 것은 아님

여기서 속도 trade-off가 발생한다.

### 현재

```text
forward
  ↓
aw 계산
eff 계산
  ↓
저장
  ↓
backward
  ↓
재사용
```

### 최소 저장

```text
forward
  ↓
필요 정보만 저장
  ↓
backward
  ↓
aw 재계산
eff 재계산
```

따라서:

[
VRAM \downarrow
]

대신:

[
FLOPs \uparrow
]

한다.

---

# 13. 현재 TinyLM에서는 이 trade-off를 어떻게 판단할 것인가

사용자의 연구 목표는 **학습시간 단축**이므로 무조건 memory-saving 방향으로 가면 안 된다.

현재 RTX 4070 Ti SUPER에서:

```text
VRAM 14~15GB
```

이지만 OOM이 발생하지 않고 있고,

```text
no-checkpoint
```

가 상당한 속도 향상을 제공한다면,

**VRAM을 최대한 낮추는 것이 목표가 아니다.**

목표는:

[
\boxed{
\text{최소 충분 VRAM으로 최대 tokens/sec}
}
]

이다.

따라서 `aw`, `eff` recompute가:

```text
VRAM 2GB 감소
+
training time 5% 증가
```

라면 반드시 채택할 이유가 없다.

반면:

```text
VRAM 2GB 감소
+
training time 1% 증가
```

라면 채택 가치가 높다.

---

# 14. 저장 tensor 최소화의 품질 영향

여기서 매우 중요한 부분:

**정확하게 같은 수식을 다시 계산한다면 학습 품질에는 원칙적으로 영향을 주지 않는다.**

즉:

```text
저장된 aw
```

와:

```text
backward에서 다시 계산한 abs(W)
```

가 수치적으로 동일하다면 optimizer가 받는 gradient도 동일하다.

따라서:

[
\text{quality impact}\approx0
]

가 목표다.

다만 다음이 달라지면 문제가 된다.

* dtype
* autocast 여부
* 연산 순서
* rounding
* sparse34 mask 계산
* anneal
* alpha 계산

따라서 반드시 gradient parity를 검사해야 한다.

---

# 15. 저장 tensor 최소화의 검증 기준

최소한 다음을 비교한다.

```text
baseline kernel
vs
recompute kernel
```

동일 seed/weight/input에 대해:

### Forward

[
\max |Y_1-Y_2|
]

### Gradient

[
\max |\nabla W_1-\nabla W_2|
]

### optimizer update

[
\max |W'_1-W'_2|
]

를 측정한다.

그리고 실제 `accum=16` optimizer step까지 비교해야 한다.

---

# 16. C. no-checkpoint는 유지한다

이 부분은 다른 최적화 방향과 명확히 구분해야 한다.

gradient checkpointing은:

[
VRAM\downarrow
]

시키는 대신:

[
forward\ recomputation\uparrow
]

시킨다.

현재 TinyLM에서는 이미 no-checkpoint가 상당한 학습속도 개선을 가져오는 것으로 확인된 상태이므로:

> **VRAM이 남아 있는 한 no-checkpoint를 기본 설정으로 유지한다.**

---

# 17. checkpoint를 켜야 하는 조건

checkpointing은 다음 경우에만 fallback으로 사용한다.

### 조건 A

```text
peak VRAM > 16GB
```

로 OOM이 발생한다.

### 조건 B

KD 실험에서 full logits 때문에 VRAM이 부족하다.

### 조건 C

더 큰 batch/sequence length를 위해 checkpoint가 필요하다.

그 외에는:

```text
no-checkpoint
```

를 우선한다.

---

# 18. 따라서 VRAM 목표치를 8GB로 잡으면 안 된다

앞서 제시된:

> "VRAM을 8~10GB로 낮추자"

라는 목표는 **현재 TinyLM 연구 목적에는 적절하지 않다.**

더 좋은 목표는:

[
\boxed{Peak\ VRAM < 15.5GB}
]

정도로 안정적인 headroom을 확보하면서,

[
\boxed{tokens/sec\ 최대화}
]

하는 것이다.

예를 들어:

```text
9 GB / 80 tok/s
```

보다

```text
14 GB / 110 tok/s
```

가 현재 연구에는 더 유리하다.

---

# 19. D. initialization SVD는 우선순위를 낮춘다

`init_utils.py`의 SVD:

```text
teacher embedding
 ↓
effective embedding matrix
 ↓
torch.linalg.svd
```

는 초기화 시점의 VRAM peak를 증가시킬 수 있다.

하지만 중요한 질문은:

> **학습 중에도 그 메모리가 상주하는가?**

이다.

현재 구조에서는 SVD 이후 teacher가 제거되고:

```python
del teacher
torch.cuda.empty_cache()
```

되는 경로라면, **학습 중 resident VRAM에는 직접적인 영향을 주지 않는다.**

---

# 20. 따라서 initialization SVD 변경의 우선순위

### 현재 문제가

```text
training OOM
```

이라면:

**SVD는 우선순위 낮음.**

### 문제가

```text
teacher/student initialization에서 OOM
```

이라면:

**SVD 최적화 필요.**

### 문제가

```text
초기화 시간이 너무 오래 걸림
```

이라면:

별도 최적화 대상.

즉 현재 3~6시간 training time 문제를 해결하기 위한 핵심 작업으로 SVD를 건드릴 필요는 없다.

---

# 21. Teacher를 CPU에 유지하는 방안

이것은 상당히 중요한 별도 문제다.

현재:

```text
Teacher
 ↓
GPU resident
```

라면 teacher parameter가 VRAM을 계속 차지한다.

CPU resident로 바꾸면:

```text
GPU
Student

CPU
Teacher
```

가 된다.

이론적으로 teacher parameter VRAM을 거의 제거할 수 있다.

---

# 22. 하지만 teacher CPU resident는 학습속도에 매우 불리할 가능성이 높음

문제는 teacher forward다.

현재:

```text
CPU teacher
 ↓
CPU computation
```

만 하는 것은 GPU보다 매우 느리다.

또 teacher weight를 layer별로 GPU로 가져오는 방식이라면:

```text
CPU
 ↓ PCIe
GPU
 ↓
forward
 ↓
CPU
```

가 반복된다.

RTX 4070 Ti SUPER에서 GPU compute는 매우 빠른데 PCIe 전송은 상대적으로 느리기 때문에:

[
T_{\mathrm{teacher}}
====================

T_{\mathrm{transfer}}
+
T_{\mathrm{compute}}
]

가 되어 teacher GPU resident보다 크게 느려질 가능성이 높다.

---

# 23. 특히 KD에서는 teacher를 매 accumulation마다 실행한다

현재 구조가 `accum=16`이고 teacher를 `kd_every=4`로 실행한다면 개념적으로:

```text
micro 1 teacher
micro 2
micro 3
micro 4 teacher
...
```

처럼 teacher forward가 반복된다.

따라서 teacher를 CPU로 옮기면:

[
16/4=4
]

회/optimizer step 정도의 teacher inference 비용이 발생한다.

그때마다 CPU↔GPU transfer가 발생한다면 wall-clock 손실이 상당할 수 있다.

---

# 24. Teacher CPU resident가 적합한 경우

다음 조건이면 고려할 가치가 있다.

```text
VRAM OOM
+
teacher GPU resident 때문에 OOM
+
checkpoint를 켜고 싶지 않음
```

즉 **속도를 희생해서 VRAM을 확보해야 하는 emergency fallback**이다.

반면:

```text
14.5GB
+
학습 정상
```

이라면 teacher CPU offload는 권장하지 않는다.

---

# 25. 더 좋은 teacher CPU 방식

teacher 전체를 CPU에 두고 매번 GPU로 복사하는 것보다:

### 방법 A

Teacher의 필요한 부분만 GPU에 올리는 layer streaming

### 방법 B

Teacher를 작은 precision으로 GPU resident

### 방법 C

Teacher inference를 별도 preprocessing 단계에서 수행

이 더 합리적일 수 있다.

특히 C는:

```text
teacher
 ↓
offline inference
 ↓
teacher logits/cache
 ↓
student training
```

구조다.

하지만 이것 역시 **저장공간과 I/O가 증가하고 KD 실험 자체의 조건이 달라지므로 별도 실험**이다.

---

# 26. Teacher CPU resident의 품질 영향

teacher의 계산 자체가 동일한 precision과 동일한 weight라면:

[
\text{quality impact}\approx0
]

이다.

하지만 다음이 변경되면 품질이 달라질 수 있다.

* teacher quantization
* BF16 → FP32
* logits truncation
* top-k
* teacher temperature 계산 방식
* numerical softmax

따라서:

> **CPU에 위치시키는 것 자체는 품질 문제가 아니지만, CPU offload 과정에서 precision/objective를 변경하면 별개의 문제다.**

---

# 27. Teacher CPU resident의 권장 판단

현재 연구에서는:

### 기본 실험

```text
teacher GPU resident
```

유지.

### 별도 VRAM ablation

```text
teacher CPU resident
```

측정.

측정:

```text
VRAM
tokens/sec
teacher latency
total step time
validation loss
```

입니다.

---

# 28. `adamw_bf16.py`에 대한 최종 판단

현재 AdamW 구현은:

```text
BF16 moment
+
FP32 temporary calculation
```

구조입니다.

이는 속도에는 약간 불리할 수 있지만 **14~15GB VRAM 문제의 핵심 원인으로 보지 않는다.**

따라서:

> **현재 단계에서는 수정하지 않는다.**

특히 optimizer를 바꾸면 P018 실험의 optimizer confound가 발생할 수 있으므로, 다른 최적화가 끝난 뒤 마지막에 검토하는 것이 좋다.

---

# 29. `loader.py`에 대한 최종 판단

현재 batch가:

```text
8 × 1025
```

수준이므로 GPU input tensor는 수십 KB 정도다.

따라서:

> **VRAM 14~15GB의 원인이 아니다.**

pin_memory를 매번 호출하는 구조는 속도 최적화 대상이 될 수 있지만 현재 우선순위가 낮다.

---

# 30. `evaluate.py`에 대한 최종 판단

현재:

```text
@torch.no_grad()
+
freeze_quant()
```

구조는 적절하다.

다만 vocabulary가 32K이고 sequence가 1024라면 validation의 full logits는 순간적으로 큰 tensor가 된다.

따라서 평가 peak VRAM을 줄이는 것이 목적이라면:

```text
fused CE
```

등을 검토할 수 있다.

그러나 **training VRAM 문제와 분리한다.**

---

# 31. `prepare.py`에 대한 최종 판단

GPU training VRAM과 직접 관계 없다.

현재 작업에서 수정할 필요가 없다.

---

# 32. 전체 변경 우선순위

최종적으로 다음 순서를 권장한다.

## Phase 0 — 현재 baseline 계측

수정 전:

```text
peak allocated VRAM
peak reserved VRAM
tokens/sec
step time
forward time
backward time
teacher time
quantization time
```

측정.

---

## Phase 1 — `ternary_kernel.py` autograd 검증

현재:

```python
ctx.save_for_backward(x, aw, alpha, eff)
```

의 각각의 필요성을 분석.

우선:

```text
eff → recompute 가능성 검토
aw  → recompute 가능성 검토
x   → 유지 가능성 높음
alpha → 유지
```

검토.

---

## Phase 2 — saved tensor 최소화 실험

비교:

```text
T0:
x + aw + alpha + eff

T1:
x + alpha + eff

T2:
x + alpha + compact quantization representation
```

각각:

```text
VRAM
tokens/sec
gradient parity
loss
validation
```

측정.

---

# 33. Phase 3 — Step-level quantization cache

앞서 설계한:

```text
prepare_quant_step()
```

도입.

기존:

[
N_{\mathrm{micro}}
]

번 quantization을:

[
N_{\mathrm{optimizer}}
]

번으로 감소.

`accum=16`이라면 이론적으로 약:

[
16\times
]

중복 계산 제거 기회가 있다.

단, 실제 wall-clock speedup은 profiling으로 확인한다.

---

# 34. Phase 4 — KD full logits 별도 실험

반드시 별도 branch:

```text
KD-full
KD-memory-efficient
```

비교.

이 단계에서만:

```text
top-k
streaming
fused KD
```

등을 검토한다.

**P018-R1 기본 모델 구조의 변경으로 섞지 않는다.**

---

# 35. Phase 5 — Teacher CPU 실험

다음 조건에서만:

```text
VRAM이 여전히 16GB 한계에 접근
```

하면 실시.

비교:

```text
Teacher GPU
vs
Teacher CPU
```

그리고 반드시:

[
\text{tokens/sec}
]

를 비교한다.

VRAM이 3GB 감소했지만 학습시간이 50% 증가한다면 채택하지 않는다.

---

# 36. Phase 6 — Initialization SVD

마지막에 판단.

현재 training VRAM 문제가 해결된 후에도:

```text
initialization OOM
```

또는:

```text
initialization time excessive
```

가 있으면 CPU SVD 등을 적용한다.

그렇지 않으면 건드리지 않는다.

---

# 37. 변경에 따른 품질 영향 분류

이것은 작업용 AI가 반드시 구분해야 한다.

| 변경                   |       VRAM |      속도 |                    품질 영향 |
| -------------------- | ---------: | ------: | -----------------------: |
| `aw` recompute       |          ↓ |     ↓/≈ |                 원칙적으로 없음 |
| `eff` recompute      |         ↓↓ |    ↓ 가능 |                 원칙적으로 없음 |
| step quant cache     |        ↓/≈ |    ↑ 가능 |                 원칙적으로 없음 |
| no-checkpoint        |          ↑ |  **↑↑** |                       없음 |
| teacher CPU          |         ↓↓ |   **↓** |                 원칙적으로 없음 |
| teacher quantization |         ↓↓ |    ↑ 가능 |              **있을 수 있음** |
| top-k KD             |         ↓↓ |    ↑ 가능 |              **있을 수 있음** |
| fused KD             |          ↓ |    ↑ 가능 |              구현이 동일하면 없음 |
| CPU SVD              | 학습 중 변화 없음 | 초기화 ↓/↑ |                       없음 |
| BF16 AdamW 변경        |          ↓ |      변동 | optimizer dynamics 검증 필요 |

여기서 가장 중요한 것은:

> **메모리를 줄이는 방법과 학습 objective를 바꾸는 방법을 절대로 같은 범주로 취급하지 않는다.**

---

# 38. 작업용 AI가 코드 수정 전에 반드시 확인해야 할 것

다음 조건을 만족하지 않으면 코드를 수정하지 않는다.

### `ternary_kernel.py`

* [ ] `aw`가 backward에서 반드시 저장되어야 하는가?
* [ ] `aw = abs(W)` 재계산이 numerical equivalent인가?
* [ ] `eff`가 저장되지 않아도 되는가?
* [ ] `eff` 재구성 시 anneal semantics가 동일한가?
* [ ] sparse34 mask가 동일한가?
* [ ] `alpha` 계산이 동일한가?
* [ ] `ctx.save_for_backward()`에서 제거되는 tensor가 다른 autograd path에 필요한 것은 아닌가?
* [ ] backward gradient parity가 통과하는가?

---

# 39. Step quantization cache 확인사항

* [ ] optimizer step당 정확히 1회 quantization되는가?
* [ ] accumulation 중 weight가 변경되지 않는다는 가정을 만족하는가?
* [ ] `anneal`이 accumulation 중 변하지 않는가?
* [ ] arena 값이 accumulation 중 변하지 않는가?
* [ ] cached tensor에 autograd graph가 붙지 않는가?
* [ ] micro-batch마다 새로운 autograd graph가 생성되는가?
* [ ] `retain_graph=True`가 필요하지 않은가?
* [ ] `optimizer.step()` 후 cache가 삭제되는가?
* [ ] baseline과 gradient parity가 맞는가?

---

# 40. Teacher CPU 확인사항

* [ ] teacher parameter transfer가 optimizer step마다 발생하지 않는가?
* [ ] layer마다 CPU→GPU transfer가 발생하는가?
* [ ] teacher forward latency가 얼마나 증가하는가?
* [ ] PCIe transfer가 GPU compute를 idle 상태로 만드는가?
* [ ] teacher output precision이 기존과 동일한가?
* [ ] validation loss가 유지되는가?

---

# 41. 반드시 추가해야 할 profiling

현재 문제를 추측만으로 해결하면 안 된다.

`trainer.py`에 다음 계측을 넣는 것이 좋다.

```text
quantization_ms
student_forward_ms
teacher_forward_ms
kd_loss_ms
backward_ms
optimizer_ms
data_ms
```

그리고:

```text
torch.cuda.max_memory_allocated()
torch.cuda.max_memory_reserved()
```

를 optimizer step 단위로 기록한다.

그러면 예를 들어:

```text
Data             2%
Quantization     8%
Student forward  20%
Teacher forward  18%
KD               7%
Backward         43%
Optimizer         2%
```

처럼 실제 병목을 확인할 수 있다.

---

# 42. 최종 권장 아키텍처

현재 목적에서는 다음 상태를 목표로 한다.

```text
                    TinyLM Training
                           │
             ┌─────────────┴─────────────┐
             │                           │
         Student                       Teacher
             │                           │
      no-checkpoint                 GPU resident
             │                           │
       Fast training               no_grad()
             │                           │
             └──────────┬────────────────┘
                        │
                       KD
                        │
               full logits baseline
                        │
                separate ablation
                        │
          ┌─────────────┴─────────────┐
          │                           │
   Quantization                  Autograd
   step cache                    saved tensor
          │                           │
       q + α                    minimize saved
          │                           │
     1× / optimizer             recompute aw/eff
          │                           │
          └─────────────┬─────────────┘
                        │
                  optimizer step
```

---

# 43. 최종 결론

현재 TinyLM의 VRAM 문제에 대해 **무조건 "VRAM을 8~10GB로 줄이는 것"을 목표로 삼는 것은 잘못된 방향**이다.

현재 연구 목적은:

[
\boxed{\text{동일 token budget에서 최대한 많은 실험을 수행}}
]

이므로 최적화 목표는:

[
\boxed{
\text{VRAM을 충분히 안정적으로 확보하면서 tokens/sec를 최대화}
}
]

여야 한다.

따라서 현재의 우선순위는 다음과 같이 확정하는 것을 권장한다.

### 최우선

**① `ternary_kernel.py`의 `save_for_backward(x, aw, alpha, eff)` 검증 및 최소화**

→ VRAM을 줄이되 **gradient semantics를 유지하는 것이 핵심**

### 최우선

**② optimizer-step quantization cache**

→ `accum=16`에서 반복적인 quantization 제거

### 유지

**③ no-checkpoint**

→ VRAM을 더 쓰더라도 **학습속도 개선 효과 때문에 유지**

### 별도 실험

**④ KD full logits**

→ VRAM뿐 아니라 KD objective/품질에 영향을 줄 가능성이 있으므로 기본 구현과 분리하여 실험

### 조건부

**⑤ Teacher CPU resident**

→ VRAM은 크게 줄일 수 있지만 PCIe/CPU inference 때문에 **학습속도를 크게 떨어뜨릴 위험이 있으므로 emergency/fallback 실험**

### 후순위

**⑥ initialization SVD**

→ 초기화 peak만 감소하고 training resident VRAM에는 영향을 주지 않는다면 현재 학습속도 문제 해결에는 우선순위가 낮음

### 당장은 유지

**⑦ `adamw_bf16.py`, `loader.py`, `prepare.py`**

→ 현재 14~15GB VRAM의 핵심 원인으로 볼 근거가 부족하며, 먼저 더 큰 병목을 제거한 후 profiling 결과에 따라 수정

---

## 작업용 AI에 전달할 핵심 지시

> **코드 수정 시 VRAM 최소화 자체를 목표로 하지 말 것.**
> 현재 TinyLM의 목적은 RTX 4070 Ti SUPER 16GB에서 가능한 한 높은 training throughput을 확보하는 것이다.
>
> 특히 `no-checkpoint`는 VRAM을 많이 사용하더라도 유지한다.
> `teacher CPU offload`도 VRAM만 보고 적용하지 말고 PCIe transfer와 teacher latency를 포함한 wall-clock cost를 측정한다.
>
> `ternary_kernel.py`의 `ctx.save_for_backward(x, aw, alpha, eff)`는 가장 먼저 분석한다. `aw`와 `eff`가 정말 persistent activation으로 저장되어야 하는지 backward 수식을 기준으로 검증하고, recompute로 대체할 경우 기존 `_TernaryKernelLinear.backward()`와 **forward/gradient/optimizer-step numerical parity**를 검증한다.
>
> KD full logits는 현재 KD objective를 변경할 수 있으므로 기존 코드에서 임의로 제거하거나 top-k로 변경하지 않는다. **full-logit KD를 baseline으로 보존하고 memory-efficient KD를 별도 ablation으로 수행하여 VRAM, tokens/sec, loss, validation quality를 비교한다.**
>
> initialization SVD는 학습 중 resident VRAM과 직접 관련이 없다면 현재 학습 최적화 작업에서 후순위로 둔다.
>
> 모든 최적화는 최종적으로 **peak VRAM뿐 아니라 `tokens/sec`, optimizer-step time, validation loss`를 함께 측정하여 채택 여부를 결정한다.**
