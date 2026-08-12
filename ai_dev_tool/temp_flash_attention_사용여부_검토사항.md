# TinyLM FlashAttention 사용 여부 검증 및 학습속도 영향 사전 점검 문서

## 0. 문서 목적

본 문서는 RTX 4070 Ti SUPER 16GB에서 TinyLM 100M급 모델의 학습속도를 개선하기에 앞서, **현재 TinyLM이 실제로 FlashAttention 계열 CUDA kernel을 사용하고 있는지 검증하기 위한 사전 점검 절차**를 정의한다.

본 문서의 목적은 단순히 다음 설정이 존재하는지를 확인하는 것이 아니다.

```python
attn_implementation="flash_attention_2"
```

위 옵션은 Hugging Face Transformer 계열에서는 유효할 수 있지만, TinyLM은 자체적인 `tinylm.model` 및 training stack을 사용하므로 이 옵션의 존재 여부만으로 실제 FlashAttention 사용을 증명할 수 없다.

따라서 다음 세 가지를 분리하여 검증한다.

1. **Attention 구현 경로**: TinyLM이 어떤 API를 호출하는가?
2. **Backend 선택**: PyTorch SDPA가 Flash backend를 선택하는가?
3. **실제 CUDA kernel 실행**: GPU profiler에서 FlashAttention 계열 kernel이 실제 실행되는가?

최종 판단은 3번을 가장 높은 신뢰도로 간주한다.

---

# 1. 먼저 정의해야 할 것: "FlashAttention 사용"의 세 가지 수준

FlashAttention이라는 용어가 여러 의미로 사용되므로 다음과 같이 구분한다.

## Level 0 — FlashAttention 미사용

다음과 같이 attention을 직접 구현하는 경우이다.

```python
scores = q @ k.transpose(-2, -1)
scores = softmax(scores)
out = scores @ v
```

이 경우 attention matrix가 명시적으로 생성될 가능성이 있으며, 일반적인 math kernel을 사용할 수 있다.

판정:

> FlashAttention 사용 안 함.

---

## Level 1 — PyTorch SDPA 사용

TinyLM이 다음과 같은 API를 사용하는 경우:

```python
torch.nn.functional.scaled_dot_product_attention(...)
```

이것만으로 FlashAttention 사용이 확정되는 것은 아니다.

PyTorch SDPA는 입력 조건과 backend에 따라 FlashAttention, memory-efficient attention, math implementation 등을 선택할 수 있다.

따라서:

> SDPA 사용 = FlashAttention 사용

이라고 판단하면 안 된다.

---

## Level 2 — SDPA의 Flash backend 사용

PyTorch가 실제로 Flash Attention backend를 선택한 경우이다.

개념적으로:

```text
TinyLM attention
      ↓
scaled_dot_product_attention()
      ↓
PyTorch SDPA dispatcher
      ↓
FLASH_ATTENTION backend
      ↓
CUDA kernel
```

이 단계에서는 FlashAttention 사용이라고 볼 수 있다.

그러나 최종적인 실험 보고에서는 실제 kernel 실행 여부까지 확인하는 것이 가장 바람직하다.

---

## Level 3 — 실제 FlashAttention CUDA kernel 실행 확인

Profiler 또는 CUDA kernel trace에서 FlashAttention 계열 kernel이 실제 실행되는 것을 확인하는 단계이다.

예:

```text
flash_attn
flash_attention
_fwd
_bwd
scaled_dot_product_attention
```

등의 Flash 계열 kernel이 확인되는 경우이다.

이것이 **가장 강한 증거**다.

---

# 2. 현재 TinyLM에서 가장 먼저 확인할 파일

현재 저장소의 학습 코드는 일반적인 Hugging Face `Trainer` 구조가 아니다.

`tinylm/train/trainer.py`는 자체적으로 다음을 import한다.

```python
from ..model import TiedMLPTransformer
```

그리고 자체 `train()` 함수에서 모델과 학습을 제어한다.

따라서 다음 순서로 코드를 추적한다.

```text
tinylm/train/trainer.py
        ↓
tinylm/model/__init__.py
        ↓
tinylm/model/transformer.py
        ↓
tinylm/model/modules.py
        ↓
Attention implementation
```

특히 다음 문자열을 검색한다.

```text
scaled_dot_product_attention
sdpa
flash_attention
flash_attn
attention
softmax
matmul
bmm
einsum
```

---

# 3. 1단계: Attention 구현 자체 확인

## 확인 대상 A

다음 코드가 존재하는지 검색한다.

```python
F.scaled_dot_product_attention(...)
```

또는

```python
torch.nn.functional.scaled_dot_product_attention(...)
```

### 발견한 경우

다음 단계로 이동한다.

```text
SDPA 사용
   ↓
Flash backend 사용 여부 검증
```

### 발견하지 못한 경우

다음과 같은 직접 구현 여부를 확인한다.

```python
q @ k.transpose(...)
softmax(...)
attn @ v
```

또는

```python
torch.matmul(q, k.transpose(...))
```

이 경우 FlashAttention을 사용하고 있지 않을 가능성이 높다.

---

# 4. 2단계: PyTorch 버전 확인

Flash backend의 지원 여부와 구현은 PyTorch 버전에 따라 달라질 수 있으므로 먼저 환경을 기록한다.

실행:

```bash
python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.get_device_name(0))"
```

반드시 기록할 항목:

```text
PyTorch version:
CUDA version:
GPU:
GPU compute capability:
Python version:
```

RTX 4070 Ti SUPER에서는 Ada Lovelace GPU의 특성을 고려해야 한다.

따라서 H100/Hopper 전용 FlashAttention-3 성능 결과를 그대로 적용해서는 안 된다.

---

# 5. 3단계: SDPA backend 사용 가능 여부 확인

PyTorch는 SDPA backend를 제공하며 FlashAttention backend를 사용할 수 있는 조건을 별도로 검사할 수 있다.

테스트용으로 다음 형태의 독립적인 검증 코드를 작성한다.

```python
import torch
import torch.nn.functional as F

device = "cuda"
dtype = torch.bfloat16

B = 8
H = 12
L = 1024
D = 64

q = torch.randn(B, H, L, D, device=device, dtype=dtype)
k = torch.randn(B, H, L, D, device=device, dtype=dtype)
v = torch.randn(B, H, L, D, device=device, dtype=dtype)

out = F.scaled_dot_product_attention(
    q, k, v,
    is_causal=True,
)

print(out.shape)
```

이 테스트의 목적은 TinyLM 자체를 검증하는 것이 아니다.

먼저 현재 GPU/PyTorch 환경에서 **Flash-capable SDPA 경로 자체가 정상적으로 동작할 수 있는지** 확인한다.

---

# 6. 4단계: Flash backend를 강제로 지정하여 baseline 생성

PyTorch에서는 SDPA backend를 명시적으로 제한하여 테스트할 수 있다.

개념적으로 다음과 같이 비교한다.

```python
from torch.nn.attention import sdpa_kernel, SDPBackend

with sdpa_kernel(backends=[SDPBackend.FLASH_ATTENTION]):
    out = F.scaled_dot_product_attention(
        q, k, v,
        is_causal=True,
    )
```

이 테스트에서 중요한 것은 오류가 발생하지 않는지뿐만 아니라 다음을 기록하는 것이다.

```text
Flash backend 강제 실행 가능 여부
forward 실행시간
peak VRAM
출력 shape
NaN 여부
```

이것은 **TinyLM 전체가 FlashAttention을 사용한다는 증명이 아니라 GPU 환경 자체의 사전 검증**이다.

---

# 7. 5단계: TinyLM 실제 Attention에 적용

이 단계가 가장 중요하다.

TinyLM의 실제 attention forward에서 사용되는 Q/K/V를 확인한다.

예를 들어 실제 코드가 다음과 같다면:

```python
q = ...
k = ...
v = ...

out = F.scaled_dot_product_attention(
    q, k, v,
    is_causal=True,
)
```

Flash backend를 선택할 가능성이 있다.

그러나 다음과 같다면:

```python
scores = torch.matmul(q, k.transpose(-2, -1))
scores = torch.softmax(scores, dim=-1)
out = torch.matmul(scores, v)
```

PyTorch SDPA를 사용하지 않는 것이다.

이 경우 Hugging Face의

```python
attn_implementation="flash_attention_2"
```

를 외부에서 추가해도 TinyLM의 custom attention이 자동으로 FlashAttention으로 바뀌지 않는다.

---

# 8. 6단계: GQA/CLA 때문에 Flash backend가 거부되지 않는지 확인

TinyLM은 일반적인 MHA와 다른 attention 구조를 사용하므로 반드시 다음 조건을 확인한다.

```text
Q heads
K/V heads
head dimension
sequence length
dtype
causal 여부
mask 형태
GQA 설정
CLA 설정
```

특히 GQA에서는 Q의 head 수와 K/V의 head 수가 다를 수 있다.

따라서 다음과 같은 구조라면:

```text
Q : [B, Hq, L, D]
K : [B, Hkv, L, D]
V : [B, Hkv, L, D]
```

SDPA/Flash backend가 해당 형태를 지원하는지 확인해야 한다.

단순히 "FlashAttention 패키지가 설치되어 있다"는 사실은 충분하지 않다.

---

# 9. 7단계: backend warning을 이용한 검증

Flash backend를 강제했는데 조건이 맞지 않는다면 PyTorch가 backend 선택 실패 원인을 알려주는 경우가 있다.

따라서 테스트 단계에서는 다음을 반드시 확인한다.

```text
Flash backend 실행 성공
또는
Flash backend 실행 실패 + 실패 원인
```

실패 원인이 다음과 같은 경우 각각 기록한다.

```text
dtype unsupported
head dimension unsupported
mask unsupported
GQA unsupported
non-contiguous tensor
device unsupported
training/backward unsupported
```

이 결과는 이후 TinyLM attention을 수정할 때 중요한 진단 자료가 된다.

---

# 10. 8단계: 반드시 profiler로 최종 확인

가장 중요한 검증이다.

PyTorch profiler 또는 NVIDIA Nsight Systems/Nsight Compute를 이용하여 실제 CUDA kernel을 확인한다.

최소한 다음 정보를 확보한다.

```text
Forward attention kernel
Backward attention kernel
Kernel execution time
Number of launches
GPU utilization
```

Profiler에서 FlashAttention 계열 kernel이 실제 실행되는지 확인한다.

즉 다음 구조를 증명해야 한다.

```text
TinyLM
 ↓
Attention
 ↓
SDPA
 ↓
Flash backend
 ↓
Flash CUDA kernel
```

이것이 확인되면 FlashAttention 사용을 사실상 확정할 수 있다.

---

# 11. 9단계: "FlashAttention 사용 여부"와 "속도 향상 여부"를 별도로 검증

매우 중요한 원칙이다.

FlashAttention을 사용했다고 해서 반드시 전체 학습속도가 크게 향상되는 것은 아니다.

따라서 두 개의 질문을 분리한다.

### 질문 A

> FlashAttention이 실제 실행되는가?

### 질문 B

> FlashAttention이 TinyLM 전체 training step을 실제로 빠르게 만드는가?

A와 B는 서로 다른 실험이다.

---

# 12. 속도 실험 설계

다음과 같이 최소 3개 configuration을 만든다.

## A — Current baseline

```text
현재 TinyLM attention
```

## B — SDPA

```text
PyTorch SDPA
```

## C — Flash backend

```text
PyTorch SDPA
+
FLASH_ATTENTION backend
```

가능하다면 추가로:

## D — Math backend

```text
SDPA
+
MATH backend
```

를 실행한다.

이렇게 하면 다음을 비교할 수 있다.

```text
Math
vs
SDPA optimized backend
vs
FlashAttention
```

---

# 13. 동일 조건 원칙

A/B/C/D 실험에서 다음은 절대 바꾸지 않는다.

```text
model architecture
parameter count
dataset
training tokens
sequence length
micro batch
gradient accumulation
learning rate
optimizer
precision
seed
compile setting
checkpoint setting
KD setting
```

예를 들어 현재 TinyLM 기준이라면:

```text
seq = 1024
micro_bs = 8
accum = 16
dtype = BF16
```

등을 그대로 유지한다.

FlashAttention 검증 실험에서 sequence length나 batch를 동시에 바꾸면 FlashAttention의 효과를 분리할 수 없다.

---

# 14. warm-up을 반드시 분리

첫 번째 step은 benchmark에 사용하지 않는다.

특히 `torch.compile`이 사용되는 경우 compile overhead가 포함될 수 있기 때문이다.

권장:

```text
warm-up 10~20 steps
↓
benchmark 50~100 steps
```

예:

```text
Step 1~20   : warm-up
Step 21~70  : measurement
```

그리고 평균값과 중앙값을 모두 기록한다.

---

# 15. 측정해야 할 핵심 지표

단순히 `ms/step`만 기록하지 않는다.

다음 지표를 기록한다.

| 지표                  | 목적               |
| ------------------- | ---------------- |
| ms/step             | 직접적인 학습속도        |
| tokens/sec          | 실제 throughput    |
| peak allocated VRAM | 실제 tensor memory |
| peak reserved VRAM  | allocator memory |
| GPU utilization     | GPU 활용도          |
| attention runtime   | attention 개선 효과  |
| forward time        | forward 영향       |
| backward time       | backward 영향      |
| optimizer time      | optimizer 영향     |
| total step time     | 최종 효과            |

특히:

[
\text{tokens/sec}
=================

\frac{\text{micro_bs}\times\text{seq}\times\text{accum}}
{\text{step time}}
]

으로 계산한다.

---

# 16. VRAM은 allocated와 reserved를 구분한다

다음 네 값을 기록한다.

```python
torch.cuda.memory_allocated()
torch.cuda.memory_reserved()
torch.cuda.max_memory_allocated()
torch.cuda.max_memory_reserved()
```

실험 전:

```python
torch.cuda.reset_peak_memory_stats()
```

실험 후:

```python
print("allocated:",
      torch.cuda.memory_allocated() / 1024**3)

print("reserved:",
      torch.cuda.memory_reserved() / 1024**3)

print("peak allocated:",
      torch.cuda.max_memory_allocated() / 1024**3)

print("peak reserved:",
      torch.cuda.max_memory_reserved() / 1024**3)
```

이렇게 해야 다음과 같은 상황을 구별할 수 있다.

```text
allocated = 9 GB
reserved  = 15 GB
```

이 경우 실제 tensor가 15GB를 사용하는 것이 아니다.

따라서 `nvidia-smi`의 15GB만 보고 activation이 15GB라고 판단하면 안 된다.

---

# 17. FlashAttention 검증 성공 기준

다음 조건을 모두 만족하면 "FlashAttention 사용"을 확정한다.

### 필수 조건

* [ ] TinyLM attention이 SDPA 또는 FlashAttention 경로를 호출한다.
* [ ] Flash backend가 현재 GPU/PyTorch 환경에서 활성화된다.
* [ ] Flash backend 강제 실행이 성공한다.
* [ ] TinyLM 실제 training path에서 동일한 backend가 사용된다.
* [ ] profiler에서 Flash 계열 CUDA kernel이 확인된다.
* [ ] backward에서도 적절한 Flash kernel이 실행된다.

특히 마지막 두 항목을 권장한다.

---

# 18. "FlashAttention을 사용하지 않는다"는 판정 기준

다음 중 하나라도 확인되면 FlashAttention 사용을 확정해서는 안 된다.

### 경우 1

```text
직접 matmul + softmax + matmul
```

### 경우 2

```text
SDPA 사용
그러나 math backend 실행
```

### 경우 3

```text
Flash backend 테스트는 성공
그러나 TinyLM 실제 training path에서는 다른 backend 실행
```

### 경우 4

```text
FlashAttention package 설치
그러나 실제 CUDA kernel에는 나타나지 않음
```

특히 **"flash-attn이 pip로 설치되어 있다"는 것은 FlashAttention 사용의 증거가 아니다.**

---

# 19. FlashAttention이 켜져 있어도 속도가 개선되지 않을 수 있는 경우

다음 상황에서는 FlashAttention의 효과가 작을 수 있다.

```text
TinyLM 전체 step
├── GEMM        50%
├── attention   10%
├── MLP         20%
├── norm        10%
└── 기타         10%
```

이 경우 attention을 2배 빠르게 해도 전체 speedup은 제한적이다.

Amdahl's law에 따르면 attention이 전체 시간의 10%라면 attention을 무한히 빠르게 만들어도:

[
S_{\max}=\frac{1}{1-0.10}=1.11
]

즉 전체 학습속도는 최대 약 11%만 개선된다.

따라서 FlashAttention을 검증하는 목적은

> "FlashAttention이면 무조건 빠르다"

가 아니라

> **"현재 TinyLM에서 attention이 실제로 의미 있는 비중을 차지하는가?"**

를 함께 확인하는 것이다.

---

# 20. TinyLM에서 특히 주의해야 할 점

TinyLM은 약 100M parameter의 작은 모델이다.

따라서 7B~70B 모델의 FlashAttention benchmark 결과를 그대로 적용하면 안 된다.

작은 모델에서는 다음 overhead의 상대적 비중이 커질 수 있다.

```text
kernel launch
small GEMM
RMSNorm
RoPE
residual
elementwise operation
optimizer
data loading
```

따라서 FlashAttention 논문에서 큰 speedup이 보고되었다고 해서 TinyLM에서도 동일한 speedup이 보장되지 않는다.

---

# 21. FlashAttention 검증 후 다음 단계

### Case A — FlashAttention이 현재 사용되지 않음 + 효과가 큼

즉시 적용 후보.

```text
Current
  ↓
SDPA
  ↓
Flash backend
```

으로 변경한다.

---

### Case B — FlashAttention이 현재 사용되지 않음 + 효과가 작음

Attention이 전체 step의 병목이 아닌 것이다.

다음으로:

```text
RMSNorm
SwiGLU
residual
LM head
optimizer
GEMM
```

의 profiler 결과를 조사한다.

이 경우 FlashAttention에 계속 시간을 투자하지 않는다.

---

### Case C — 이미 FlashAttention 사용 중

추가적인 FlashAttention 설정 변경은 중단한다.

다음 후보로 넘어간다.

```text
fused RMSNorm
fused SwiGLU
fused residual
fused CE
FP8 GEMM
optimizer fusion
```

---

### Case D — Flash backend를 사용할 수 없음

실패 원인을 분류한다.

```text
dtype
mask
GQA
head dimension
PyTorch version
CUDA
tensor layout
```

그 원인을 먼저 해결한 뒤 다시 benchmark한다.

---

# 22. 절대 먼저 하지 말아야 할 작업

FlashAttention 사용 여부를 확인하기 전에 다음 변경을 동시에 하지 않는다.

```text
× seq 1024 → 2048
× batch 8 → 16/32/64
× optimizer 변경
× gradient checkpoint 변경
× FP8 변경
× model architecture 변경
× KD 변경
```

이렇게 하면 속도 변화의 원인을 판별할 수 없다.

---

# 23. 권장 실험 순서

최종 작업 순서는 다음과 같다.

```text
[1] 현재 TinyLM attention 코드 확인
          ↓
[2] SDPA 사용 여부 확인
          ↓
[3] PyTorch / CUDA / GPU 환경 확인
          ↓
[4] Flash backend 단독 실행 테스트
          ↓
[5] TinyLM 실제 attention에 적용
          ↓
[6] profiler로 실제 CUDA kernel 확인
          ↓
[7] baseline vs Flash benchmark
          ↓
[8] tokens/sec 비교
          ↓
[9] peak allocated/reserved VRAM 비교
          ↓
[10] attention 비중 계산
          ↓
[11] 효과가 충분하면 적용
          ↓
[12] 효과가 작으면 다른 kernel로 이동
```

---

# 24. 최종 판정표

실험 종료 후 다음 표를 채운다.

| 항목                    | Baseline | Flash | 판정 |
| --------------------- | -------: | ----: | -- |
| Attention API         |        ? |     ? |    |
| Backend               |        ? | Flash |    |
| Flash kernel 확인       |        ? |     ? |    |
| Forward attention ms  |        ? |     ? |    |
| Backward attention ms |        ? |     ? |    |
| Total step ms         |        ? |     ? |    |
| Tokens/sec            |        ? |     ? |    |
| Peak allocated GB     |        ? |     ? |    |
| Peak reserved GB      |        ? |     ? |    |
| GPU utilization       |        ? |     ? |    |
| Loss 동일성              |        ? |     ? |    |

최종적으로 다음과 같이 판정한다.

### PASS — 실제 FlashAttention 사용 + 속도 개선

```text
Flash kernel 확인
AND
total step time 감소
```

→ 적용 가치 있음.

### CONDITIONAL — FlashAttention 사용하지만 전체 속도 개선 미미

```text
Flash kernel 확인
BUT
total step improvement < 5%
```

→ attention은 주요 병목이 아님. 다른 kernel 최적화로 이동.

### FAIL — FlashAttention 미사용

```text
Flash kernel 미검출
```

→ backend 또는 attention 구현 문제를 먼저 조사.

### FAIL — FlashAttention 사용 가능하지만 backend 조건 불충족

```text
Flash backend rejected
```

→ rejection reason 확인 후 TinyLM attention 구현 수정 여부 판단.

---

# 25. 현재 TinyLM에서의 권장 의사결정 기준

현재 TinyLM의 목표가 **동일한 학습 token 수에서 wall-clock training time을 줄이는 것**이라는 점을 고려하면 다음 기준을 사용한다.

### 1차 목표

FlashAttention 적용으로

[
T_{\text{step}}
]

이 실제 감소하는가?

### 2차 목표

동일한 조건에서

[
\text{tokens/sec}
]

가 증가하는가?

### 3차 목표

peak VRAM이 감소하여 더 효율적인 batch configuration을 사용할 수 있는가?

단, **VRAM 감소 자체를 성공으로 판정하지 않는다.**

예:

```text
VRAM: 15 GB → 9 GB
속도: 동일
```

이라면 메모리 최적화에는 성공했지만 **학습속도 가속에는 실패**한 것이다.

반대로:

```text
VRAM: 15 GB → 14 GB
속도: 20% 증가
```

라면 이번 연구 목적에는 훨씬 중요한 결과다.

---

# 26. 최종 결론

FlashAttention 검증에서 가장 중요한 원칙은 다음 한 문장으로 요약된다.

> **"FlashAttention 설정이 존재하는가?"가 아니라 "TinyLM의 실제 training path에서 FlashAttention CUDA kernel이 실행되고 있으며, 그 결과 end-to-end training throughput이 증가하는가?"를 검증해야 한다.**

따라서 작업 전에는 **모델 구조나 batch/sequence를 변경하지 말고 현재 baseline을 고정**한다.

그 상태에서:

```text
① Attention 코드 확인
② SDPA 여부 확인
③ Flash backend 가능 여부 확인
④ 실제 TinyLM training path 확인
⑤ CUDA profiler로 kernel 확인
⑥ 동일 조건 benchmark
⑦ tokens/sec 및 ms/step 비교
```

를 수행한다.

이 7단계가 끝난 뒤에야 FlashAttention을 실제 TinyLM 학습에 적용할지 결정한다.

---

## 참고

PyTorch의 `scaled_dot_product_attention`은 여러 backend를 사용할 수 있으므로 SDPA 호출 자체만으로 FlashAttention 사용을 확정할 수 없다. 실제 backend 선택과 실행 조건을 별도로 검증해야 한다.

FlashAttention-2는 attention의 메모리 접근 및 병렬화 방식을 최적화하는 방법이며, attention 자체의 계산 복잡도를 제거하는 방법은 아니다. 따라서 TinyLM 100M급 모델에서의 실제 end-to-end speedup은 별도의 benchmark가 필요하다.

현재 TinyLM의 training code는 자체 `TiedMLPTransformer` 및 custom training loop를 사용하므로, 일반 Hugging Face `AutoModelForCausalLM.from_pretrained(..., attn_implementation="flash_attention_2")` 예제를 그대로 적용하는 방식은 사전 검증 없이 사용해서는 안 된다.
