최신 `trainer.py`를 실제 코드 기준으로 보면, **현재 14~15GB VRAM과 긴 학습시간의 원인을 단순히 "100M 모델이 커서"라고 볼 수 없고, KD 경로 + 삼진 양자화 재계산 + 평가/체크포인트 I/O가 겹친 구조**로 보는 것이 가장 타당합니다.

특히 이번 코드 검토에서 이전 분석보다 더 중요한 문제 하나를 발견했습니다.

> **gradient accumulation 내부의 각 micro-batch마다 학생 모델의 삼진 양자화를 다시 계산하고 있습니다.**

이것은 현재 `trainer.py`와 `transformer.py`의 결합으로 인해 생기는 상당히 큰 잠재적 병목입니다. 아래에서 우선순위대로 설명하겠습니다.

---

# 1. 가장 먼저 결론

현재 코드에서 제가 보는 병목 우선순위는 다음과 같습니다.

| 우선순위  | 원인                                                           |  속도 영향 |   VRAM 영향 | 판단                      |
| ----- | ------------------------------------------------------------ | -----: | --------: | ----------------------- |
| **1** | **gradient accumulation마다 student ternary quantization 재계산** |   매우 큼 |        중간 | **가장 중요한 코드 개선 후보**     |
| **2** | **dense teacher full forward + full-vocab KD**               |   매우 큼 |         큼 | **KD의 핵심 병목**           |
| **3** | **KD의 `[B,T,V]` logits + softmax/log-softmax temporary**     |      큼 |      매우 큼 | **14~15GB 설명에 유력**      |
| **4** | `eval` 때마다 model+optimizer 전체 checkpoint 저장                  | 중~매우 큼 | 일시적 증가 가능 | **wall-clock 오염 가능성 큼** |
| **5** | `eval`/checkpoint 시간이 `ms/step` 측정값에 포함                      |  측정 왜곡 |         - | **현재 속도 비교를 오염**        |
| **6** | EMA parameter clone/eval                                     |     중간 |        중간 | EMA 사용 시만               |
| **7** | batch pinning/H2D                                            |  낮음~중간 |        낮음 | 현재 설정에서는 주병목 아님         |
| **8** | optimizer fused 여부                                           |  낮음~중간 |        낮음 | 이미 상당 부분 처리됨            |

그리고 중요한 반전이 하나 있습니다.

### 현재 teacher autograd graph가 남아서 메모리가 폭증하는 문제는 아닙니다.

코드에 이미:

```python
with torch.no_grad():
    tlog = teacher(x)
```

가 들어가 있습니다.

따라서 이전에 일반적인 KD 구현에서 흔히 발생하는 "teacher activation graph를 잘못 저장하고 있다"는 문제는 **현재 코드에는 해당하지 않습니다.**

---

# 2. 가장 중요한 문제: 학생의 ternary quantization이 accumulation마다 다시 계산됨

이 부분을 매우 중요하게 보셔야 합니다.

`trainer.py`의 구조는:

```python
for s in range(start, steps):

    ...

    for _ in range(accum):
        x, y = tr()

        logits = model(x)

        ...
        loss.backward()

    opt.step()
    ...
    model.clear_quant()
```

입니다.

현재 기본 `accum=16`이라면 **optimizer update 하나당 16개의 micro-batch를 처리합니다.**

그런데 `transformer.py`의 `forward()`를 보면:

```python
if not self._quant_frozen:
    self.refresh_quant()
```

가 **매 forward마다 실행됩니다.**

그리고 `refresh_quant()`는 모든 `TLinear`에 대해:

```python
w = self._w()
wq = ternary(w, self.cfg)
self._wq = ...
```

를 수행합니다.

즉 개념적으로:

```text
optimizer step
│
├─ micro 1 → ternarize 전체 model
├─ micro 2 → ternarize 전체 model
├─ micro 3 → ternarize 전체 model
├─ ...
├─ micro 16 → ternarize 전체 model
│
└─ optimizer update
```

입니다.

그런데 **micro 1~16 사이에는 model parameter가 전혀 바뀌지 않습니다.**

즉 같은 optimizer step 안에서는:

[
W^{(1)}=W^{(2)}=\cdots=W^{(16)}
]

이므로 양자화 결과의 forward 값도 동일합니다.

---

# 3. 이것은 특히 TinyLM에서 비싼 이유

현재 `_TernarySTE.forward()`는 단순히 `sign()` 하나 하는 연산이 아닙니다.

각 weight matrix에 대해:

```python
wg = w.reshape(...)
aw = wg.abs()

mask = ...
cnt = ...
alpha = ...
return sign(wg) * mask * alpha
```

식으로 group별 threshold/mask/alpha 계산을 합니다.

즉:

```text
weight
 ↓
reshape
 ↓
abs
 ↓
group mean
 ↓
threshold
 ↓
mask
 ↓
alpha
 ↓
ternary weight
```

가 됩니다.

그리고 이것을 **accum=16이면 같은 optimizer update에서 16번** 수행합니다.

특히 100M급 모델에서 GEMM 자체가 작아질수록 이런 부가 연산의 비율이 커질 수 있습니다.

---

# 4. 그런데 단순히 `_wq`를 16번 재사용하면 안 됨

여기에는 중요한 기술적 함정이 있습니다.

현재 `_wq`는 단순한 detached tensor가 아닙니다.

```python
self._wq = wq + (1.0 - anneal) * (w - wq).detach()
```

이런 식으로 **STE의 autograd graph가 연결되어 있습니다.**

따라서 같은 `_wq`를 16번의 backward에서 그냥 재사용하면:

> backward graph를 여러 번 사용하게 되어 `retain_graph=True` 문제가 발생합니다.

그리고 `retain_graph=True`로 해결하면 **activation/autograd graph 메모리가 누적될 수 있어 오히려 VRAM을 망가뜨립니다.**

따라서 올바른 해결법은:

### "quantized weight와 backward graph를 분리"

하는 것입니다.

---

# 5. 제가 권장하는 개선 구조

현재:

```text
각 micro-batch
    ↓
ternary(weight)
    ↓
STE graph 생성
    ↓
forward
    ↓
backward
```

를

```text
optimizer step 시작
    ↓
quantization statistics 계산 1회
    ↓
qweight / mask / alpha / STE factor 저장
    ↓
micro 1
    ↓
fresh lightweight STE wrapper
    ↓
backward

micro 2
    ↓
fresh lightweight STE wrapper
    ↓
backward

...
micro 16

    ↓
optimizer.step()
    ↓
cache 폐기
```

형태로 바꾸는 것입니다.

즉 **"무거운 ternarization은 1회", "micro-batch별 autograd 연결은 새로 생성"**합니다.

---

# 6. 이 최적화는 현재 teacher의 `freeze_quant()` 아이디어와 같은 방향

흥미롭게도 현재 코드에는 이미 teacher에 대한 해결책이 들어 있습니다.

`trainer.py`는 옵션:

```python
--kd-teacher-infer
```

를 켜면:

```python
teacher.freeze_quant()
teacher.drop_latent()
```

를 수행하도록 되어 있습니다.

즉 teacher는

```text
매 forward마다 quantize
```

하지 않고

```text
한 번 quantize
→ frozen quantized weight 재사용
```

하도록 되어 있습니다.

**그런데 학생은 parameter가 계속 업데이트되기 때문에 같은 방식의 완전한 freeze는 불가능합니다.**

따라서 학생에는

> **"optimizer step 단위 quantization cache + micro-batch 단위 fresh STE"**

가 필요합니다.

이것이 제가 이번 코드 검토에서 가장 추천하는 구조적 수정입니다.

---

# 7. 두 번째 핵심 문제: teacher가 실제로 매 KD step full forward를 수행함

현재 online KD:

```python
with torch.no_grad():
    tlog = teacher(x)
```

입니다.

이 자체는 메모리 안전성 측면에서는 올바르지만 계산적으로는:

```text
student forward
+
teacher forward
+
student backward
```

입니다.

teacher가 약 100~150M급이면 **teacher forward 하나가 student forward와 비슷하거나 더 비쌀 수 있습니다.**

즉 KD step에서는 사실상:

```text
학생 학습 1회
+
추가 모델 1회
```

입니다.

---

# 8. 그런데 현재 `kd_every=4`는 이 문제를 상당히 잘 해결하고 있음

현재 구현에서는:

```python
kd_every = 4
```

이면 teacher forward는 4 step 중 한 번만 수행됩니다.

즉:

[
T_{\text{teacher,avg}}
\approx
\frac14T_{\text{teacher}}
]

입니다.

이것은 이미 매우 좋은 최적화입니다.

따라서 제가 현재 상태에서 **가장 먼저 `kd_every`를 8로 더 늘리지는 않겠습니다.**

기존 실험에서도 k4가 품질/시간 측면에서 좋은 결과를 보였기 때문에, 현재는 **k4를 유지하고 teacher 자체를 최적화**하는 쪽이 더 좋습니다.

---

# 9. 세 번째 핵심 문제: full-vocabulary KD가 상당히 무겁다

현재:

```python
tlog = teacher(x)
```

뒤에:

```python
F.log_softmax(logits / T, -1)
F.softmax(tlog / T, -1)
F.kl_div(...)
```

를 계산합니다.

현재:

[
B=8
]

[
T=1024
]

[
V=32768
]

라고 하면 logits 하나가:

[
8\times1024\times32768
======================

268,435,456
]

원소입니다.

BF16이라면:

[
268,435,456\times2
\approx537MB
]

즉 **teacher logits 하나만 약 512 MiB**입니다.

학생 logits도 동일합니다.

따라서 이미:

```text
teacher logits ≈ 0.54GB
student logits ≈ 0.54GB
```

입니다.

그 뒤 KD에서 softmax/log-softmax 결과와 temporary buffer들이 만들어질 수 있습니다.

그래서 KD 구간에서:

```text
Teacher
+
student
+
student activation
+
teacher logits
+
student logits
+
softmax temporary
+
optimizer state
+
CUDA workspace
```

가 겹치면 **14~15GB가 전혀 이상하지 않습니다.**

---

# 10. 따라서 현재 VRAM 14~15GB의 가장 합리적인 설명

현재 코드 기준으로는:

```text
100M teacher weight
```

이 10GB를 먹는 것이 아닙니다.

오히려:

```text
학생 activation
+
teacher forward temporary
+
teacher logits
+
student logits
+
KD softmax/log-softmax
+
optimizer state
+
CUDA allocator/workspace
```

의 합입니다.

그리고 `trainer.py`가 이미 실제 peak을 기록하도록 되어 있습니다:

```python
torch.cuda.max_memory_allocated()
torch.cuda.max_memory_reserved()
```

를 결과 JSON에 저장합니다.

따라서 `nvidia-smi`에서 15GB라고 보는 것보다 이 JSON의

```text
vram_alloc_gb
vram_reserved_gb
```

를 먼저 확인해야 합니다. 코드 주석 자체도 `nvidia-smi ≈ reserved + CUDA context`라고 설명합니다.

---

# 11. 네 번째 문제: evaluation이 training time을 오염시키고 있음

이것도 중요합니다.

`_do_eval()`를 보면 평가 후 매번:

```python
blob = {
    "model": model.state_dict(),
    "opt": opt.state_dict(),
    ...
}
torch.save(blob, ck)
```

를 수행합니다.

그리고 best이면 다시:

```python
torch.save(blob, ck_best)
```

합니다.

즉 eval 한 번마다:

```text
GPU → checkpoint serialization
+
optimizer state serialization
+
disk I/O
```

가 발생합니다.

---

# 12. 이것은 특히 큰 이유가 있음

optimizer state는 학생 모델보다 훨씬 클 수 있습니다.

현재 TinyLM도 AdamW 상태를 가지고 있기 때문에 checkpoint는 단순히 100M weight 파일이 아닙니다.

따라서 학습 중간마다:

```text
model
+
grad/optimizer state
```

를 저장하는 동기식 I/O가 발생합니다.

`eval_every`가 예를 들어 100 step 같은 작은 값이면, 총 학습시간에서 상당한 비율을 차지할 수 있습니다.

---

# 13. 더 심각한 것은 `ms/step` 측정까지 오염됨

현재:

```python
t0 = time.time()
```

가 training 시작 전에 잡혀 있고,

출력:

```python
el = time.time() - t0
el/(s-start+1)*1000
```

입니다.

그런데 이 `el` 안에는:

```text
training forward/backward
+
eval
+
torch.save
+
best checkpoint
+
snapshot
```

이 모두 포함됩니다.

즉 `2500 ms/step`이라고 로그에 보여도 실제 GPU training step은 그보다 훨씬 짧을 수 있습니다.

### 이건 반드시 고치는 것을 추천합니다.

둘을 분리하십시오.

```text
compute_ms/step
wall_ms/step
eval_sec
checkpoint_sec
data_sec
```

를 별도로 기록해야 합니다.

---

# 14. 추천하는 timing 구조

각 outer step에:

```text
data
teacher
student_forward
backward
optimizer
```

를 각각 CUDA event로 측정합니다.

그리고 별도로:

```text
eval_time
checkpoint_time
```

을 CPU wall-clock으로 측정합니다.

최종적으로:

[
T_{\text{wall}}
===============

T_{\text{train}}
+
T_{\text{eval}}
+
T_{\text{checkpoint}}
+
T_{\text{startup}}
]

로 분해합니다.

이렇게 해야 "90분이 왜 90분인가"를 정확히 알 수 있습니다.

---

# 15. 다섯 번째: 현재 평가 시 EMA도 추가 비용

EMA를 켜면 `_do_eval()`에서:

```python
backup = [p.detach().clone() for p in params]
```

를 수행하고 EMA weight를 swap한 뒤 다시 복구합니다.

이 경우:

```text
full parameter clone
+
EMA evaluate
+
restore
```

가 들어갑니다.

100M급에서는 아주 거대한 비용은 아니지만, eval이 빈번하면 누적됩니다.

**EMA validation은 every eval이 아니라 훨씬 드물게 해도 됩니다.**

---

# 16. 여섯 번째: DataLoader가 병목일 가능성은 현재 코드에서는 낮음

`Loader`는:

```python
np.memmap
→ NumPy advanced indexing
→ torch.from_numpy
→ pin_memory()
→ CUDA non_blocking=True
```

를 사용합니다.

따라서 데이터가 매번 전체 파일을 읽는 구조는 아닙니다.

또 batch 자체도

[
8\times1025
]

토큰뿐이라 데이터 크기가 작습니다.

따라서 **14~15GB VRAM이나 90분 학습시간의 주요 원인을 data loading으로 보는 것은 현재 코드만 보면 우선순위가 낮습니다.**

다만 `pin_memory()`를 매 batch마다 호출하는 것은 CPU 측에서 불필요한 allocation/pinning을 발생시키므로 이후 미세최적화 대상으로는 남겨둘 수 있습니다.

---

# 17. `torch.compile`은 이미 있지만 teacher compile의 효과는 별도 검증 필요

현재 teacher도:

```python
if compile_:
    teacher = torch.compile(teacher)
```

합니다.

좋은 방향입니다.

하지만 KD에서는 teacher가 `kd_every=4`라면 teacher graph를 자주 호출하지 않습니다.

따라서 compile startup cost까지 고려하면:

```text
teacher compile
vs
teacher infer optimization
```

을 따로 측정해야 합니다.

특히 `kd_teacher_infer=True`와 함께 쓰는 것이 우선입니다.

---

# 18. 현재 코드에서 이미 구현되어 있는 "최우선 즉시 적용" 옵션

## `--kd-teacher-infer`

이건 먼저 켜볼 가치가 매우 높습니다.

현재 코드 주석에 명시적으로:

```text
freeze_quant()
drop_latent()
```

를 수행한다고 되어 있습니다.

즉:

### 기존

```text
teacher forward
 ↓
refresh_quant()
 ↓
ternary reconstruction
 ↓
forward
```

### 개선

```text
초기 1회
 ↓
freeze_quant

이후
 ↓
cached quantized teacher
 ↓
forward
```

입니다.

게다가 `drop_latent()`로 teacher의 죽은 latent storage도 제거합니다.

코드 주석에서는 dense teacher 기준 약 **472.5MB** 규모의 latent 상주를 제거할 수 있다고 기록되어 있습니다.

따라서:

**VRAM ↓ + teacher compute ↓**

를 동시에 기대할 수 있습니다.

---

# 19. 더 큰 효과를 원하면 offline KD cache

`trainer.py`에는 이미:

```python
if kd_cache:
    KdCacheReader(...)
```

가 구현되어 있습니다.

그리고:

```text
teacher forward 없음
```

이라고 명시되어 있습니다.

이것은 학습 속도에는 상당히 강력합니다.

### 온라인 KD

```text
매 KD step
   ↓
teacher forward
   ↓
teacher logits
   ↓
student forward
   ↓
KD
```

### offline KD

```text
사전에 teacher 한번 실행
       ↓
top-k cache
       ↓
학생 training
```

이 됩니다.

즉 **3~6시간의 반복 실험을 여러 번 할 경우 특히 유리합니다.**

---

# 20. 다만 cache는 full logits를 저장하면 안 됨

현재 `kd_topk=16` 구조가 있는 이유가 바로 이것입니다.

전체 vocabulary:

[
32768
]

개를 저장하는 대신

```text
top 16 values
+
top 16 indices
```

만 저장합니다.

이렇게 하면 GPU VRAM 문제가 아니라 **디스크/CPU cache storage 문제**로 이동합니다.

학습 반복 횟수가 많다면 이 trade-off는 충분히 가치가 있습니다.

---

# 21. 더 나아가면 "top-k online KD"가 다음 단계

현재 online KD는 full teacher logits를 가지고 있습니다.

이것을:

```text
teacher full logits
 ↓
top-k
 ↓
student 해당 위치만 gather
 ↓
approx KD
```

로 바꾸면 GPU 메모리를 크게 낮출 수 있습니다.

다만 이 경우 기존 full-KL과는 **완전히 동일한 objective가 아니므로 연구 실험에서는 별도의 조건**으로 취급해야 합니다.

반면 이미 `kd_cache`를 사용하는 실험은 현재 프로젝트에서도 비교적 깨끗한 실험이 됩니다.

---

# 22. 제가 현재 코드라면 이렇게 수정하겠습니다

## 1단계 — 코드 변경 없이 즉시 실험

현재 baseline을:

```text
student
+
dense teacher
+
KD k4
+
kd-teacher-infer
+
compile
+
no checkpoint
```

으로 측정합니다.

특히:

```text
VRAM allocated
VRAM reserved
tokens/s
student ms
teacher ms
```

를 기록합니다.

---

## 2단계 — eval/checkpoint 분리

현재:

```text
eval
 └─ checkpoint save
```

를:

```text
eval every N
 └─ metric only

checkpoint every M
 └─ model + optimizer
```

로 분리합니다.

예를 들어:

```text
eval_every = 100
save_every = 500
```

같은 방식입니다.

Best model 저장도 모든 eval마다 저장하지 말고 **best 갱신 시에만** 저장합니다.

---

# 23. 3단계 — 가장 중요한 코드 수정

### student quantization cache

현재:

```python
for micro in range(accum):
    logits = model(x)
```

각 호출마다

```text
refresh_quant()
```

됩니다.

이것을:

```text
optimizer step 시작
     ↓
prepare_quant_for_step()

micro 1
     ↓
forward

micro 2
     ↓
forward

...

micro 16

optimizer.step()

clear_quant()
```

로 바꾸되 **autograd graph는 매 micro마다 새로 만들어야 합니다.**

즉 제가 구현한다면 `TernarySTE`를 두 단계로 분리합니다.

### Step-level

```text
quantize(weight)
 ↓
qweight
STE backward factor/mask
```

### Micro-step-level

```text
cached qweight + cached gradient factor
 ↓
fresh autograd Function
```

이 구조가 가장 적합합니다.

---

# 24. 4단계 — KD loss 최적화

현재:

```python
F.log_softmax(student_logits / T)
F.softmax(teacher_logits / T)
F.kl_div(...)
```

는 `[8192,32768]` 규모입니다.

즉 약 **268M elements**입니다.

따라서 이 부분은:

### 단기

`kd_cache top-k`

### 중기

`top-k online KD`

### 장기

`fused distillation kernel`

순으로 가는 것이 좋습니다.

---

# 25. 5단계 — sequence/batch 변경은 마지막에

이번 코드 검토 결과를 기준으로 저는 **현재 `mb=8, seq=1024`를 먼저 바꾸지 않겠습니다.**

이미 프로젝트 실험에서:

[
M=mb\times seq
]

가 약 8192 부근에서 knee를 보였다는 실측이 있습니다.

따라서 외부에서 말하는

> "seq 2048 + batch 32~64"

를 적용하는 것은 현재 프로젝트의 데이터보다 우선순위가 낮습니다.

---

# 26. 예상 효과를 현실적으로 잡으면

정확한 수치는 실측 전에는 확정할 수 없지만, 구조상 기대치는 다음 정도입니다.

| 수정                           |                                         예상 효과 |
| ---------------------------- | --------------------------------------------: |
| `kd_teacher_infer`           | **teacher compute 감소 + ~0.5GB 수준 VRAM 감소 가능** |
| `eval/checkpoint 분리          |  **wall-clock 5~20%+ 가능**(eval 빈도에 따라 크게 달라짐) |
| student quantization caching |                        **상당히 유망, 잠재적으로 10%+** |
| kd top-k/offline cache       |                            **KD가 지배적이면 매우 큼** |
| fused KD                     |                                 높음, 구현 난이도 높음 |
| loader 미세최적화                 |                                         보통 낮음 |
| batch/seq 재조정                |                                    현재 증거상 후순위 |

특히 **student quantization 재계산은 현재 코드 구조상 숨겨진 비용이라 실제 profiler에서 반드시 확인해야 합니다.**

---

# 27. 지금 가장 추천하는 실험 matrix

현재 코드에서 최소한 다음 4개를 비교하면 원인이 상당히 분리됩니다.

### A — 학생 단독

```text
KD OFF
checkpoint OFF
compile ON
```

### B — KD

```text
KD k4
teacher infer OFF
```

### C — teacher 최적화

```text
KD k4
teacher infer ON
```

### D — offline KD

```text
kd_cache ON
```

여기에 각각:

```text
eval/checkpoint 최소화
```

를 적용합니다.

그러면:

[
T_A
]

를 학생 자체의 학습시간,

[
T_B-T_A
]

를 online teacher overhead,

[
T_C-T_B
]

를 teacher quantization overhead,

[
T_D-T_C
]

를 반복 teacher forward 제거 효과로 해석할 수 있습니다.

이것은 논문용 실험으로도 상당히 깨끗합니다.

---

# 28. 특히 VRAM 측정은 이렇게 해석해야 함

현재 `trainer.py`가 이미:

```text
vram_alloc_gb
vram_reserved_gb
```

를 저장합니다.

따라서 예를 들어:

```text
alloc    = 11.2 GB
reserved = 14.7 GB
nvidia-smi = 15.3 GB
```

이면 **실제로 모델 tensor가 15GB인 것이 아닙니다.**

반대로:

```text
alloc    = 14.5 GB
reserved = 14.9 GB
```

이면 실제 activation/logit/temporary가 정말 많은 것입니다.

이 둘은 최적화 방법이 완전히 다릅니다.

---

# 29. 최종 판단

이번 `trainer.py` 검토를 통해 현재 TinyLM의 학습속도/메모리 문제를 가장 정확히 표현하면 다음과 같습니다.

### 가장 가능성이 높은 구조

```text
                    ┌───────────────┐
                    │ Dense Teacher │
                    └───────┬───────┘
                            │
                     full logits
                            │
                            ▼
Input ──────────────────────────────────┐
                                        │
                    ┌───────────────┐   │
                    │ Student       │   │
                    │ Ternary model │   │
                    └───────┬───────┘   │
                            │           │
                     full logits        │
                            └─────┬─────┘
                                  ▼
                       full-vocab KD / KL
```

여기에 Student 쪽에는:

```text
16 accumulation
   ↓
16× ternary refresh
```

가 추가됩니다.

그리고 학습 루프 바깥쪽으로는:

```text
eval
 ↓
model.state_dict()
opt.state_dict()
 ↓
torch.save()
```

가 들어갑니다.

즉 현재의 문제는 **하나의 병목이라기보다 3개의 서로 다른 병목이 겹쳐 있는 구조**입니다.

---

# 30. 제가 권하는 수정 우선순위

**최우선**

1. `--kd-teacher-infer`를 기본 실험 조건으로 검증
2. eval과 checkpoint 저장 주기 분리
3. `compute_ms/step`과 `wall_ms/step` 분리
4. student ternary quantization의 **micro-batch 간 재계산 제거**

**2순위**

5. offline top-k KD cache
6. full-vocab KD softmax/kl 최적화
7. EMA evaluation 빈도 축소

**3순위**

8. loader pinned-memory 미세최적화
9. fused KD kernel
10. batch/sequence 재조정

---

## 특히 한 가지는 바로 수정할 가치가 있습니다

현재 코드의 이 조합:

```python
for _ in range(accum):
    logits = model(x)
```

와

```python
if not self._quant_frozen:
    self.refresh_quant()
```

의 결합은 **현재 TinyLM의 구조상 불필요하게 비싼 계산을 반복하고 있을 가능성이 매우 높습니다.**

`accum=16`이라면 optimizer가 한 번 업데이트되기 전 **동일한 weight에 대해 ternarization을 최대 16번 수행**하고 있는 셈입니다. 이 부분은 현재까지 검토한 방법들 중에서도 **실제로 코드 수준에서 직접 제거할 수 있고, KD를 유지하면서도 학습 시간을 줄일 수 있다는 점에서 가장 먼저 벤치마크할 가치가 있는 후보**입니다.

반면 현재 teacher 쪽은 이미 `no_grad()`가 적용되어 있으므로 **teacher autograd graph 문제를 수정하는 데 시간을 쓰면 안 됩니다.**


현재 코드 구조를 기준으로 하면 **`_wq` 자체를 accumulation 전체에서 재사용하는 방식은 안전하지 않습니다.** `_wq`에는 `_TernarySTE`의 autograd graph가 연결되어 있기 때문입니다. 이를 그대로 16번 backward에서 재사용하면 graph 재사용 문제가 발생하고, `retain_graph=True`로 우회하면 오히려 VRAM이 폭증할 수 있습니다.

따라서 권장 설계는 다음입니다.

> **optimizer step마다 ternary weight의 forward quantization 결과와 STE에 필요한 group scale만 1회 계산하고, 각 micro-batch에서는 이 캐시를 이용해 새로운 autograd Function graph만 생성한다.**

현재 `trainer.py`가 `accum` 횟수만큼 forward/backward한 뒤 `opt.step()`하고 `model.clear_quant()`하는 구조이므로 이 방식이 정확히 들어맞습니다.

그리고 이 변경은 **기존 동작을 기본값으로 유지하는 실험 옵션**으로 구현하는 것을 권장합니다. 이 변경은 현재 삼진 모델/ablation 경로의 속도 최적화로 분리하는 것이 맞습니다.

---

# 1. 현재 문제가 정확히 무엇인가

현재 `trainer.py`:

```python
for _ in range(accum):
    x, y = tr()

    with torch.autocast(...):
        logits = model(x)
```

이고, `TLinear.forward()`가 호출되면 `transformer.py`의 `refresh_quant()`를 통해 모든 `TLinear`의 양자화가 갱신됩니다.

현재 `TLinear.refresh_quant()`은:

```python
w = self._w()
wq = ternary(w, self.cfg)
self._wq = wq + (1.0 - anneal) * (w - wq).detach()
```

입니다.

그리고 `_TernarySTE`는 forward에서:

```python
aw
alpha
```

를 저장하고 backward에서 이를 이용해:

```python
win = 1.0 / (
    1.0 + (aw / (clip * alpha)).pow(4)
)
```

를 계산합니다.

따라서 현재 `accum=16`이면 한 optimizer update에서 사실상:

```text
weight W
 │
 ├─ ternary #1 → backward
 ├─ ternary #2 → backward
 ├─ ternary #3 → backward
 ...
 └─ ternary #16 → backward
 │
 ▼
optimizer.step()
```

입니다.

하지만 16개 micro-batch 동안 **W는 변하지 않습니다.**

---

# 2. 목표 구조

바꿀 구조는 이것입니다.

```text
                 optimizer step
                       │
                       ▼
             ┌──────────────────┐
             │ ternary 계산 1회 │
             │                  │
             │ q = ternary(W)   │
             │ α = group scale  │
             └────────┬─────────┘
                      │
             cached q, α
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
   micro #1       micro #2       micro #16
       │              │              │
 fresh STE       fresh STE       fresh STE
 graph           graph           graph
       │              │              │
 backward        backward        backward
       └──────────────┼──────────────┘
                      ▼
                optimizer.step()
                      │
                      ▼
                  cache clear
```

핵심은:

### 캐시하는 것

* ternary weight `q`
* group별 `alpha`

### 캐시하지 않는 것

* autograd graph
* micro-batch별 activation
* `_TernarySTE` context

입니다.

---

# 3. 왜 `q + alpha`만 캐시하는가?

현재 `_TernarySTE.backward()`가 필요한 것은:

```text
aw
alpha
```

입니다.

그런데 `aw` 전체를 cache하면 weight 크기의 tensor가 하나 더 생깁니다.

반면 `alpha`는:

[
[O,I]
]

weight에 대해 group 크기가 128이라면:

[
[O,I/128]
]

밖에 안 됩니다.

따라서:

```text
q      ≈ weight 크기
alpha  ≈ weight / 128
```

입니다.

`aw`는 cache하지 않고 **각 micro-batch의 backward에서 현재 weight로부터 다시 계산**합니다.

중요한 점은 현재도 backward에서 `aw` 기반 계산이 필요하므로, 이 방식은 완전히 새로운 종류의 큰 연산을 추가하는 것이 아닙니다.

---

# 4. `ternary.py` 수정안

기존 `_TernarySTE`는 **그대로 둡니다.**

그 아래에 새로운 cached STE를 추가하는 것이 안전합니다.

```python
class _CachedTernarySTE(torch.autograd.Function):
    """
    Optimizer-step quantization cache용 STE.

    q와 alpha는 optimizer step 시작 시 1회 계산한다.
    각 micro-batch에서는 이 Function을 새로 호출하므로
    autograd graph는 micro-batch마다 독립적으로 생성된다.
    """

    @staticmethod
    def forward(ctx, w, q, alpha, group, ste_clip, anneal, arena):
        ctx.save_for_backward(w, alpha)
        ctx.group = group
        ctx.ste_clip = ste_clip
        ctx.arena = arena

        # 기존 refresh_quant()와 동일한 forward semantics
        out = q + (1.0 - anneal) * (w - q).detach()

        if arena is not None:
            out = out + arena * w

        return out

    @staticmethod
    def backward(ctx, g):
        w, alpha = ctx.saved_tensors

        O, I = w.shape
        G = I // ctx.group

        aw = w.reshape(O, G, ctx.group).abs()

        win = 1.0 / (
            1.0
            + (
                aw
                / (ctx.ste_clip * alpha).clamp_min(1e-8)
            ).pow(4)
        )

        grad_w = (
            g.reshape(O, G, ctx.group) * win
        ).reshape(O, I)

        if ctx.arena is not None:
            grad_w = grad_w + ctx.arena * g

        return grad_w, None, None, None, None, None, None
```

이 Function의 핵심은:

```python
q
```

를 backward graph에 연결하지 않는 것입니다.

즉:

```text
cached q
    │
    └── forward 값만 제공

current w
    │
    └── fresh autograd graph
             │
             └── backward
```

가 됩니다.

---

# 5. 다음으로 `TLinear`에 cache를 추가

`__init__()`에:

```python
self._step_q = None
self._step_alpha = None
self._step_anneal = None
self._step_arena = None
self._step_cache_enabled = False
```

를 추가합니다.

---

# 6. quantization statistics를 한 번만 계산하는 함수

`TLinear`에 다음 함수를 추가합니다.

```python
@torch.no_grad()
def prepare_step_quant(self, anneal, arena=None):
    """
    한 optimizer step에서 한 번만 호출한다.

    q:
        ternary forward weight

    alpha:
        STE backward에 필요한 group scale
    """

    w = self._w()

    O, I = w.shape
    G = I // self.cfg.micro_group
    g = self.cfg.micro_group

    wg = w.reshape(O, G, g)
    aw = wg.abs()

    if getattr(self.cfg, "sparse34", False):
        b = aw.reshape(O, G, g // 4, 4)

        keep = torch.ones_like(b)
        keep.scatter_(
            3,
            b.argmin(dim=3, keepdim=True),
            0.0,
        )

        mask = keep.reshape(O, G, g)

    else:
        mask = (
            aw >=
            self.cfg.twn_thr_ratio
            * aw.mean(dim=2, keepdim=True)
        ).to(w.dtype)

    cnt = mask.sum(dim=2, keepdim=True).clamp_min(1.0)

    alpha = (
        (aw * mask).sum(dim=2, keepdim=True)
        / cnt
    )

    q = (
        torch.sign(wg)
        * mask
        * alpha
    ).reshape(O, I)

    self._step_q = q.detach()
    self._step_alpha = alpha.detach()

    self._step_anneal = anneal.detach()

    if arena is not None:
        self._step_arena = arena.detach()
    else:
        self._step_arena = None

    self._step_cache_enabled = True
```

이 함수는 기존 `_TernarySTE.forward()`의 계산을 그대로 옮긴 것입니다.

즉 sparse34도 기존과 동일합니다. 기존 구현 역시 4개 단위에서 최소 magnitude weight 하나를 0으로 만드는 방식입니다.

---

# 7. 중요한 점: `prepare_step_quant()`은 `no_grad()`여야 함

반드시:

```python
@torch.no_grad()
```

여야 합니다.

그렇지 않으면:

```text
step cache
 ↓
autograd graph
 ↓
cache에 graph가 붙음
```

이라는 문제가 다시 생깁니다.

우리가 제거하려는 문제가 그대로 재발합니다.

---

# 8. `TLinear.forward()` 수정

현재 학습 경로는 대략:

```python
if self._i8 is not None:
    ...
else:
    wq = self._wq if self._wq is not None else ternary(...)
y = F.linear(x, wq)
```

구조입니다.

여기에 **step cache를 가장 먼저 검사**하게 합니다.

```python
def forward(self, x, mode_p=None):

    if self._step_cache_enabled:

        w = self._w()

        wq = _CachedTernarySTE.apply(
            w,
            self._step_q,
            self._step_alpha,
            self.cfg.micro_group,
            self.cfg.ste_clip,
            self._step_anneal,
            self._step_arena,
        )

    elif getattr(self.cfg, "use_ternary_kernel", False):

        if self._latent_shape is not None:
            raise RuntimeError(
                "latent 해제 상태에서는 커스텀 커널 경로를 쓸 수 없다"
            )

        y = ternary_kernel_linear(
            x, self._w(), self.cfg, self._anneal_t
        )

        if self.use_mode and mode_p is not None:
            y = y + F.linear(
                x,
                self.mode_a
            ) @ (mode_p @ self.mode_gain).T

        return y

    elif self._i8 is not None:

        wq = self._wq_from_i8()

    else:

        wq = (
            self._wq
            if self._wq is not None
            else ternary(self._w(), self.cfg)
        )

    y = F.linear(x, wq)

    if self.use_mode and mode_p is not None:
        y = y + F.linear(
            x,
            self.mode_a
        ) @ (mode_p @ self.mode_gain).T

    return y
```

다만 실제 파일의 `mode` 처리 부분은 현재 구현을 그대로 유지하고, **위 코드에서 step-cache branch만 기존 `wq` 선택 로직 앞에 삽입하는 방식**을 권합니다.

---

# 9. Transformer에 step-cache API 추가

`TiedMLPTransformer`에는 이미:

```python
self._tlinear_cache = list(self._tlinears())
```

가 있습니다. 이 부분은 매우 유용합니다. 매번 module tree를 순회하지 않아도 됩니다.

따라서:

```python
def prepare_quant_step(self):
    """
    현재 optimizer step의 quantization 상태를
    모든 TLinear에 한 번만 준비한다.
    """

    if self._quant_frozen:
        raise RuntimeError(
            "prepare_quant_step()는 frozen inference 상태에서 사용할 수 없습니다."
        )

    ar = (
        self._arena
        if (
            self._arena is not None
            and self._arena_v > 0.0
        )
        else None
    )

    for m in self._tlinear_cache:
        m.prepare_step_quant(
            self._anneal,
            ar,
        )
```

를 추가합니다.

그리고:

```python
def clear_quant(self):
    self._quant_frozen = False

    for m in self._tlinear_cache:
        m.clear_quant()
        m._step_q = None
        m._step_alpha = None
        m._step_anneal = None
        m._step_arena = None
        m._step_cache_enabled = False
```

로 변경합니다.

다만 `_step_*`를 직접 접근하는 것보다 `TLinear.clear_step_quant()`을 만드는 편이 낫습니다.

---

# 10. 따라서 `TLinear`에 이것도 추가

```python
def clear_step_quant(self):
    self._step_q = None
    self._step_alpha = None
    self._step_anneal = None
    self._step_arena = None
    self._step_cache_enabled = False
```

그리고 transformer:

```python
def clear_quant(self):
    self._quant_frozen = False

    for m in self._tlinear_cache:
        m.clear_quant()
        m.clear_step_quant()
```

입니다.

이렇게 하면 기존 `clear_quant()` semantics도 보존됩니다.

현재 `trainer.py`가 optimizer update 후 `model.clear_quant()`을 호출하고 있기 때문에 이 지점이 정확한 cache lifetime 경계가 됩니다.

---

# 11. 가장 중요한 수정: `forward()`에서 자동 `refresh_quant()`을 끄는 방법

현재 transformer의 forward에는 사실상:

```python
if not self._quant_frozen:
    self.refresh_quant()
```

이라는 구조가 있습니다. 기존 inference freeze 기능도 이 구조를 전제로 합니다.

따라서 step cache를 사용하면:

```python
if self._step_quant_cache:
    # 이미 trainer가 prepare_quant_step() 수행
    pass
elif not self._quant_frozen:
    self.refresh_quant()
```

로 만들어야 합니다.

Transformer `__init__()`:

```python
self._step_quant_cache = False
```

추가.

API:

```python
def enable_step_quant_cache(self, on=True):
    self._step_quant_cache = bool(on)
```

그리고 forward:

```python
if not self._quant_frozen and not self._step_quant_cache:
    self.refresh_quant()
```

입니다.

---

# 12. Trainer에서는 딱 한 줄이 핵심

현재:

```python
model.train()
tot, tot_ce = 0.0, 0.0

for _ in range(accum):
```

이전에:

```python
model.train()

if quant_step_cache:
    model.prepare_quant_step()

tot, tot_ce = 0.0, 0.0

for _ in range(accum):
```

를 넣습니다.

즉:

```python
model.set_anneal(anneal)

...

model.train()

if quant_step_cache:
    model.prepare_quant_step()

tot, tot_ce = 0.0, 0.0

for _ in range(accum):
    x, y = tr()

    with torch.autocast(...):
        logits = model(x)

        ...
    
    loss.backward()

...

opt.step()
opt.zero_grad(set_to_none=True)

model.clear_quant()
```

입니다.

---

# 13. 그런데 `prepare_quant_step()`을 어디서 호출해야 하는가?

**반드시 `for _ in range(accum)` 바깥입니다.**

잘못된 구현:

```python
for _ in range(accum):
    model.prepare_quant_step()
    logits = model(x)
```

이러면 아무것도 해결하지 못합니다.

정확한 위치:

```text
set_anneal
   ↓
set_arena
   ↓
prepare_quant_step()       ← 1회
   ↓
micro 1
micro 2
...
micro 16
   ↓
gradient clip
   ↓
optimizer.step()
   ↓
clear_quant()
```

입니다.

---

# 14. `anneal`과 `arena`의 일관성도 보장됨

현재 trainer는 outer step마다:

```python
model.set_anneal(anneal)
```

을 수행합니다.

그리고 Arenas를 사용할 경우:

```python
model.set_arena(...)
```

도 outer step에서 한 번 실행됩니다.

따라서:

```python
prepare_quant_step()
```

에서 현재 값을 snapshot하면 됩니다.

16개 micro-batch 동안 anneal이나 arena가 변경되지 않기 때문에 정확합니다.

---

# 15. backward의 수치적 의미

기존:

```text
micro forward
  ↓
ternary(W)
  ↓
aw, alpha 저장
  ↓
backward
  ↓
win(aw, alpha)
```

새 방식:

```text
optimizer step 시작
  ↓
q(W), alpha(W) 계산
  ↓
cache

micro forward
  ↓
cached q
  ↓
fresh STE graph

micro backward
  ↓
aw = |W|
  ↓
win(aw, cached alpha)
```

입니다.

**forward의 q는 동일하고, backward의 STE gradient도 동일하게 계산됩니다.**

따라서 이 변경은:

* parameter 수 변화 없음
* architecture 변화 없음
* ternary threshold 변화 없음
* sparse34 규칙 변화 없음
* anneal schedule 변화 없음
* optimizer 변화 없음

입니다.

---

# 16. 단, 완전히 "bit-identical"이라고 가정하면 안 됨

여기서는 중요한 연구적 절차가 있습니다.

기존:

```python
ternary(W)
```

는 각 micro-batch forward에서 다시 계산됩니다.

새 방식은:

```python
prepare_quant_step()
```

에서 한 번 계산한 결과를 재사용합니다.

수학적으로 W가 변하지 않는 한 동일하지만, AMP/autocast와 custom Function의 dtype 경계까지 포함하면 **반드시 numerical equivalence test를 해야 합니다.**

따라서 기본값은:

```text
--quant-step-cache OFF
```

로 유지하는 것을 권합니다.

---

# 17. 반드시 추가할 parity test

새 테스트 파일:

```text
tests/test_quant_step_cache.py
```

예:

```python
def test_step_quant_cache_forward_equivalence():
    torch.manual_seed(1337)

    model_a = build_model()
    model_b = copy.deepcopy(model_a)

    model_a.set_anneal(0.7)
    model_b.set_anneal(0.7)

    x = torch.randint(
        0,
        model_a.cfg.vocab_size,
        (2, 128),
        device="cuda",
    )

    # 기존
    with torch.autocast("cuda", dtype=torch.bfloat16):
        y_a = model_a(x)

    # cache
    model_b.prepare_quant_step()

    with torch.autocast("cuda", dtype=torch.bfloat16):
        y_b = model_b(x)

    torch.testing.assert_close(
        y_a,
        y_b,
        rtol=0,
        atol=0,
    )
```

단, **현재 기존 구현과 새 구현의 dtype/autocast 경로를 먼저 맞춘 뒤** exact equality를 요구해야 합니다.

---

# 18. backward parity도 반드시 검사

forward만 같으면 부족합니다.

```python
loss_a = y_a.float().square().mean()
loss_b = y_b.float().square().mean()

loss_a.backward()
loss_b.backward()
```

후:

```python
for pa, pb in zip(
    model_a.parameters(),
    model_b.parameters(),
):
    torch.testing.assert_close(
        pa.grad,
        pb.grad,
        rtol=0,
        atol=0,
    )
```

를 검사합니다.

특히 `_TernarySTE.backward()`의:

```python
win =
1 / (
    1 + (aw / (clip * alpha))^4
)
```

부분이 완전히 동일해야 합니다.

---

# 19. 더 중요한 실제 parity: 16 accumulation

최종적으로는 단일 forward가 아니라 **실제 학습 step**을 비교해야 합니다.

### A

```text
old implementation
accum=16
optimizer.step()
```

### B

```text
step-cache implementation
accum=16
optimizer.step()
```

동일한:

```text
seed
input sequence
initial weights
anneal
LR
```

에서:

```python
max_abs_weight_diff
max_abs_grad_diff
loss_diff
```

를 확인합니다.

이 테스트가 통과해야 실제 실험에 사용하십시오.

---

# 20. VRAM 측면에서 이 설계가 현재 방식보다 좋은 이유

현재 `_TernarySTE`는 각 micro-batch마다:

```text
aw
alpha
```

를 backward까지 유지합니다.

즉 여러 TLinear에 대해 각 micro forward의 autograd context가 존재합니다.

새 방식은:

```text
step cache:
q
alpha

micro:
fresh graph
```

입니다.

`q`는 한 번만 존재하고, `aw`는 각 backward 직전에 계산되므로 **micro-batch별 `aw` 저장을 제거할 수 있습니다.**

따라서:

```text
persistent:
q ≈ 1 × weight

temporary:
aw ≈ 현재 backward에 필요한 것
```

가 됩니다.

특히 KD까지 같이 사용하면 activation/logits 때문에 VRAM이 이미 높은 상황이므로 **quantization cache가 VRAM을 추가로 폭증시키지 않도록 `aw`를 캐시하지 않는 것이 중요합니다.**

---

# 21. 속도 측면에서는 무엇을 제거하는가?

기존 micro-step마다:

```text
abs
mean
threshold
mask
sum
alpha
sign
multiply
reshape
```

를 수행합니다.

새 방식:

### optimizer step당 1회

```text
abs
mean
threshold
mask
sum
alpha
sign
multiply
```

### micro-batch마다

```text
F.linear(x, cached_q)
```

그리고 backward에서:

```text
abs(W)
pow(4)
divide
multiply
```

정도입니다.

따라서 특히 `accum=16`에서는 **forward-side ternarization overhead가 최대 16배 → 1배**로 줄어드는 구조입니다.

---

# 22. 다만 이 부분은 반드시 profiler로 검증

예를 들어 기존:

```text
16 × ternary forward
```

가 16%의 전체 training time을 차지했다면 상당한 개선입니다.

반면 RTX 4070 Ti SUPER에서 GEMM이 압도적으로 지배적이라면:

```text
ternary = 3%
```

밖에 안 될 수도 있습니다.

그러므로 최종 논문/실험에서는:

```text
baseline
step-cache
```

에 대해 최소한:

```text
tokens/sec
ms/optimizer-step
ms/forward
ms/backward
peak allocated VRAM
peak reserved VRAM
```

을 비교하는 것이 좋습니다.

---

# 23. CLI도 feature flag로 추가

`train()` signature:

```python
...
kd_teacher_infer=False,
quant_step_cache=False,
```

추가.

그리고 CLI:

```text
--quant-step-cache
```

를 추가합니다.

기본값:

```python
False
```

로 합니다.

이렇게 해야 기존 실험 결과를 재현할 수 있습니다.

---

# 24. 결과 JSON에도 기록

현재 trainer가 결과 JSON을 기록하고 있으므로:

```python
result["quant_step_cache"] = bool(quant_step_cache)
```

를 넣으십시오.

그리고 가능하면:

```python
result["quant_refresh_count"] = ...
```

도 넣는 것이 좋습니다.

예:

```text
baseline:
quant_refresh_count = 36624

step-cache:
quant_refresh_count = 2289
```

처럼 나타낼 수 있습니다.

`steps=2289`, `accum=16`이면 기존 구현은 이론적으로:

[
2289\times16=36,624
]

micro-forward입니다.

새 방식에서는:

[
2289
]

번만 무거운 quantization을 수행합니다.

---

# 25. 한 가지 더 개선하면 좋음: refresh 횟수 카운터

`TiedMLPTransformer`:

```python
self._quant_refresh_count = 0
```

그리고:

```python
def refresh_quant(self):
    self._quant_refresh_count += 1
    ...
```

`prepare_quant_step()`:

```python
def prepare_quant_step(self):
    self._quant_refresh_count += 1
    ...
```

종료 시:

```python
result["quant_refresh_count"] = model._quant_refresh_count
```

이렇게 하면 실제로 최적화가 적용되었는지 로그로 바로 확인할 수 있습니다.

---

# 26. 구현 후 기대되는 호출 구조

최종적으로 trainer가:

```python
for s in range(start, steps):

    model.set_anneal(anneal)

    if arenas:
        model.set_arena(...)

    model.train()

    if quant_step_cache:
        model.prepare_quant_step()

    for _ in range(accum):

        x, y = tr()

        with torch.autocast(
            device,
            dtype=torch.bfloat16,
            enabled=(device == "cuda"),
        ):
            logits = model(x)

            ...

        loss.backward()

    clip_grad_norm_(...)
    opt.step()
    opt.zero_grad(set_to_none=True)

    model.clear_quant()
```

가 됩니다.

이것이 제가 권하는 **최종 lifecycle**입니다.

---

# 27. 절대 하면 안 되는 구현

### ① `_wq`를 그대로 16회 backward에서 재사용

```python
model.refresh_quant()

for _ in range(16):
    logits = model(x)
    loss.backward()
```

**금지.**

`_wq`에 기존 STE graph가 붙어 있기 때문입니다.

---

### ② `retain_graph=True`

```python
loss.backward(retain_graph=True)
```

**금지.**

메모리 절약을 목적으로 도입하는 cache가 오히려 accumulation 전체의 graph를 붙잡게 됩니다.

---

### ③ `q`뿐 아니라 `aw`를 persistent cache로 저장

```text
q
+
aw
+
alpha
```

**비추천.**

100M급이면 `q`와 `aw` 각각 수백 MB가 될 수 있습니다.

현재 16GB GPU에서 KD까지 같이 돌리는 상황에서는 불필요한 persistent VRAM 증가입니다.

---

# 28. 제가 권하는 최종 설계

정리하면:

```text
                  optimizer step
                       │
                       ▼
              prepare_quant_step()
                       │
              ┌────────┴────────┐
              │                 │
          cached q          cached α
              │                 │
              └────────┬────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       micro 1      micro 2      micro 16
          │            │            │
    CachedSTE      CachedSTE    CachedSTE
      graph          graph        graph
          │            │            │
       backward     backward     backward
          └────────────┼────────────┘
                       ▼
                  optimizer.step
                       │
                       ▼
                  clear cache
```

이 구조가 **안전성·속도·VRAM의 균형이 가장 좋습니다.**

특히 현재 TinyLM에서는 `accum=16`이므로 **무거운 ternarization 계산을 36,624회에서 2,289회로 줄이는 것이 핵심**입니다.

그리고 이 수정은 기존 ternary 알고리즘 자체를 바꾸는 것이 아니라 **"같은 optimizer step 안에서는 weight가 변하지 않는다"는 사실을 이용한 계산 중복 제거**입니다. 따라서 논문에서도 `quantization algorithm`이 아니라 **training-time quantization overhead reduction / optimizer-step quantization caching**이라는 구현 최적화로 명확히 분리할 수 있습니다.
