# TinyLM m100: 상주 메모리 고정 상태에서 모델 지능을 높이는 방법론 검토 문서

- **목적**: TinyLM m100에서 **상주 모델 메모리(resident weight memory)를 증가시키지 않으면서** 모델 품질/지능을 높일 수 있는 방법을 사전 검토한다.
- **범위**: 데이터 품질 개선은 제외한다. 단, 기존 KD 및 학습 목적함수 개선은 포함한다.
- **기준일**: 2026-08-13
- **기준 모델**: TinyLM `m100` 계열의 현재 구현/설정
- **핵심 원칙**: `resident memory`와 `effective computation depth`를 분리하여 본다. 즉, 같은 weight를 더 많이 재사용하거나, 아주 작은 layer-specific parameter만 추가하여 계산 경로를 풍부하게 만드는 방법을 우선한다.

---

## 1. 현재 TinyLM m100 기준선

현재 TinyLM m100의 주요 설정은 다음과 같다.

| 항목 | 현재 기준 |
|---|---:|
| hidden dimension | 768 |
| FFN dimension | 2048 |
| Q heads / KV heads | 12 / 3 |
| embedding rank | 256 |
| depth | 2 prelude + 16 middle + 2 coda = 20 |
| MLP sharing | middle에서 group sharing (`mlp_group`) |
| KV sharing | CLA (`cla_group`) |
| weight representation | ternary 계열 |
| sparse option | 3:4 sparse ternary |
| layer-specific modulation | gate / scale-shift / optional LoRA / FiLM |
| inference depth control | `infer_repeat` 지원 |
| 주요 목표 | 작은 resident memory + CPU 친화성 |

현재 코드상 middle MLP는 공유 가능한 구조이며, 각 Layer에는 attention, normalization, residual gate 및 MLP-specific LoRA/FiLM을 추가할 수 있도록 되어 있다. 또한 inference-time middle 반복을 위한 `infer_repeat`, `repeat_where`, `repeat_kv_reuse`가 이미 설정에 존재한다.

**따라서 가장 자연스러운 연구 방향은 새로운 모델을 처음부터 설계하는 것이 아니라, 현재의 MLP sharing을 attention/block sharing → recurrent depth → adaptive depth → cross-layer expert sharing으로 확장하는 것이다.**

---

# 2. 평가 기준

### 2.1 상주 메모리

여기서 상주 메모리는 배포 시 계속 보유해야 하는 모델 weight 및 필수 parameter를 의미한다.

- **증가 없음**: 기존과 사실상 동일
- **감소 가능**: 동일 품질을 유지하면서 더 작은 weight budget으로 구성 가능
- **증가 가능성**: 추가 router/adapter/expert를 넣을 때 발생할 수 있음

주의: inference에서 일시적인 activation/KV-cache 증가와 resident weight 증가를 구분한다.

### 2.2 모델 품질

실험 전에는 정확한 증감을 단정할 수 없다. 아래 평가는 선행연구 근거와 TinyLM 구조적 적합성에 따른 **사전 기대치**이다.

- `+++`: 성능 개선을 기대할 강한 근거
- `++`: 개선 가능성이 높으나 조건 의존
- `+`: 제한적/불확실
- `0`: 품질 자체보다 효율 개선이 주효과
- `-`: 품질 저하 위험

### 2.3 계산량

기존 m100을 1.0×로 놓은 상대적 평가다.

### 2.4 CPU 적합성

CPU inference/training에서 다음을 중요하게 평가한다.

1. 반복 GEMM이 단순한가
2. branch / gather / scatter가 많은가
3. dynamic routing이 필요한가
4. custom kernel 의존성이 있는가
5. 메모리 대역폭이 병목인가

---

# 3. 후보 방법론 종합 비교표

| 우선순위 | 방법론 | 상주 메모리 | 예상 품질 변화 | 계산량 | 구현 난이도 | 기존 아키텍처 변경 | CPU 적합성 | 기존 TinyLM 적합성 | 사전 판단 |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **Full block sharing + recurrent depth** | **동일~감소** | **+++** | ↑↑ | 중 | 중 | **높음** | **매우 높음** | 최우선 |
| **2** | **Shared block + layer-specific low-rank modulation** | **+소량 또는 동일** | **++~+++** | ↑ | 중 | 낮음~중 | **높음** | **매우 높음** | 최우선 |
| **3** | **Depth-aware / intermediate KD** | 동일 | **++** | 학습만 ↑ | 중 | 낮음 | 높음 | **매우 높음** | 최우선 보조축 |
| **4** | **Adaptive recurrent depth / dynamic depth** | 동일 | **++~+++** | 평균 가변 | 중~상 | 중 | 중 | 높음 | 2단계 |
| **5** | **Cross-layer shared MLP expert pool (Hyper Experts 계열)** | **동일 목표 설계 가능** | **+++** | ↑~↑↑ | 상 | **상** | 중~낮음 | 높음 | 연구성 최고 |
| **6** | **Attention sharing** | **감소 가능** | **++** | 동일~↑ | 중 | 중 | **높음** | 높음 | 적극 검토 |
| **7** | **Depth 재배분: embedding/head 압축 → depth 확대** | **동일** | **++** | ↑ | 중 | 상 | 높음 | 중~높음 | 후속 |
| **8** | **Mixture-of-Depths식 token-level conditional compute** | 동일 | **++** | 평균 ↓~동일 | 상 | 상 | **낮음~중** | 중 | 후속 |
| **9** | **MLA/latent KV compression** | weight는 동일 | **0~+** | attention compute 변화 | 상 | 상 | 중 | 중 | 별도 목적 |
| **10** | **일반 MoE** | **대체로 증가** | +++ | 선택적 | 상 | 상 | 낮음 | 낮음 | 이번 목표와 불일치 |
| **11** | **단순 width 증가** | **증가** | +++ | ↑ | 낮음 | 낮음 | 높음 | 낮음 | 제외 |
| **12** | **단순 layer 추가를 위한 독립 weight 증가** | **증가** | ++~+++ | ↑ | 낮음 | 중 | 높음 | 낮음 | 제외 |

---

# 4. 방법론별 상세 검토

## 4.1 Full Block Sharing + Recurrent Depth

### 개념

현재처럼 층마다 서로 다른 block을 보유하는 대신, 소수의 block을 여러 depth에서 반복 사용한다.

일반 Transformer:

```text
H1 = F1(H0)
H2 = F2(H1)
H3 = F3(H2)
...
```

제안:

```text
H1 = Fθ(H0)
H2 = Fθ(H1)
H3 = Fθ(H2)
...
```

또는 몇 개의 block을 순환시킨다.

```text
B1 → B2 → B3 → B4 → B1 → B2 → B3 → B4 → ...
```

### 상주 메모리

**동일 또는 감소 가능.**

특히 현재 20층에서 attention까지 공유하면 유니크 block 수가 줄어든다.

저장해야 할 weight 수는:

```text
현재: N개의 layer-specific block
제안: K개의 unique block, K << N
```

이다.

남는 memory budget을 사용해서 작은 adapter나 더 많은 effective depth를 확보할 수 있다.

### 품질

**가장 유망한 후보 중 하나.**

MobileLLM은 sub-billion 모델에서 deep-and-thin 구조와 block-wise weight sharing이 유효함을 보고했고, 125M/350M에서 layer sharing이 추가적인 정확도 개선을 보였다.

Universal Transformer 역시 Transformer transformation을 recurrent하게 반복하여 parameter count와 computational depth를 분리하는 방향의 대표적 선행연구다.

다만 단순히 동일 block을 반복하는 것만으로 항상 품질이 증가한다고 단정해서는 안 된다. 반복 가능한 표현이 되도록 학습하는 것이 중요하다.

### 계산량

`effective depth`를 20→24→28→32로 늘리면 대략 그 비율만큼 transformer block 계산이 증가한다.

예:

```text
20 → 24 : 약 +20%
20 → 28 : 약 +40%
20 → 32 : 약 +60%
```

실제 wall-clock 증가는 attention implementation, cache reuse, CPU kernel에 따라 달라진다.

### 구현 난이도

**중간.**

현재 TinyLM은 MLP sharing과 `infer_repeat`가 이미 존재하므로 개념적 변경량이 크지 않다.

### 기존 아키텍처 변경

**중간.**

가장 중요한 변화는:

- attention sharing 여부
- KV owner/schedule
- repeated layer의 positional/state handling
- recurrent depth training

이다.

### CPU 적합성

**높음.**

동일한 GEMM을 반복하는 것은 dynamic routing보다 CPU에 유리하다.

단, 계산량 자체는 증가하므로 latency는 증가할 수 있다.

### TinyLM 적합성

**최상.**

현재 `infer_repeat`가 이미 존재하는 것이 특히 유리하다.

### 결론

**가장 먼저 실험할 방법.**

---

# 5. Shared Block + Layer-specific Low-Rank Modulation

## 핵심 아이디어

공유 block은 같게 유지하되, 각 depth에 아주 작은 보정만 둔다.

예:

```text
Shared Block
      +
Layer-specific LoRA
      +
Layer-specific FiLM
      +
Layer gate
```

수식:

```text
F_l(x) = F_θ(x) + A_l B_l x
```

여기에서 `θ`가 대부분의 parameter이고 `A_l B_l`만 작게 둔다.

현재 TinyLM에는 이미 MLP LoRA와 FiLM, residual gate 및 scale/shift parameter가 존재한다.

### 상주 메모리

**소량 증가할 수 있으나 설계에 따라 사실상 동일하게 유지 가능.**

rank 4/8 정도의 low-rank adapter는 full layer보다 훨씬 작다.

또는 기존에 제거한 layer-specific weight budget을 adapter에 재사용하면 **총 resident memory를 고정**할 수 있다.

### 품질

**++~+++**

완전 shared layer의 표현력 부족을 완화한다.

중요한 점은:

> shared block이 "무엇을 계산할지"를 담당하고  
> adapter가 "현재 depth에서 어떻게 변형할지"를 담당하게 만드는 것

이다.

### 계산량

LoRA가 추가되는 만큼 소폭 증가.

하지만 full layer를 다시 추가하는 것보다는 훨씬 작다.

### 구현 난이도

**중간 이하.**

현재 코드 구조와 매우 잘 맞는다.

### CPU 적합성

**높음.**

small-rank matrix multiplication은 CPU에서 처리하기 어렵지 않으며 dynamic routing보다 예측 가능한 계산 graph를 유지한다.

### 결론

**Full sharing의 1차 보완책으로 거의 반드시 시험할 가치가 있다.**

---

# 6. Depth-aware / Intermediate Knowledge Distillation

## 핵심 아이디어

기존 KD:

```text
teacher logits → student logits
```

보다 한 단계 더 나아가 teacher의 intermediate representation을 student depth에 매핑한다.

예:

```text
Teacher layer 4  ──→ Student iteration 4
Teacher layer 8  ──→ Student iteration 8
Teacher layer 12 ──→ Student iteration 12
Teacher layer 16 ──→ Student iteration 16
Teacher layer 20 ──→ Student iteration 20
```

### 왜 TinyLM에 적합한가

shared recurrent block은 동일한 parameter를 반복 사용하므로, 초기 학습에서 "깊이별 기능 분화"를 배우기 어렵다.

Intermediate KD는 이 문제에 직접적인 supervision을 제공한다.

TinyBERT는 Transformer distillation을 intermediate representation까지 포함하는 방식으로 작은 모델에 teacher knowledge를 효과적으로 전달했다.

### 상주 메모리

**증가 없음.**

Teacher는 training-time memory 문제이지 deployment resident memory 문제가 아니다.

### 품질

**++**

특히 recurrent/shared 모델에 유리할 가능성이 높다.

### 계산량

학습 시 teacher forward 및 hidden-state loss 때문에 증가.

Inference 비용에는 영향 없음.

### 구현 난이도

**중간.**

현재 KD 구조에 intermediate hook을 추가하면 된다.

### CPU 적합성

**높음.**

배포 모델 구조에는 추가 routing이 없다.

### 결론

**구조 변경과 동시에 적용할 1순위 학습 방법.**

---

# 7. Adaptive Recurrent Depth / Dynamic Depth

## 핵심 아이디어

모든 token이 같은 횟수로 block을 통과하지 않도록 한다.

```text
easy token
    → 1× block

normal token
    → 2× block

hard token
    → 3~4× block
```

Mixture-of-Depths는 Transformer가 token마다 서로 다른 양의 FLOPs를 사용할 수 있음을 보여주었다.

2026년 PoLar 연구는 더 일반적으로 layer를 skip하거나 loop하여 입력별 execution program을 만드는 방향까지 확장했다.

### 상주 메모리

**증가 없음** 또는 아주 작은 router만 추가.

### 품질

**++~+++**

hard token에 더 많은 계산을 할 수 있기 때문이다.

### 계산량

평균 계산량은 줄일 수도 있고 늘릴 수도 있다.

예:

```text 50% tokens → 1×
30% tokens → 2×
20% tokens → 3×
```

평균은 1.7×이다.

### 구현 난이도

**중~상.**

CPU에서 dynamic routing을 어떻게 구현할지가 핵심이다.

### CPU 적합성

**중간 또는 낮음.**

이유:

- token gather/scatter
- branch
- variable-shape execution
- 작은 batch에서 kernel 효율 저하

등 때문이다.

### TinyLM 적합성

높지만 1차 실험으로는 추천하지 않는다.

### 결론

**고정 recurrent depth가 검증된 뒤 2단계로 진행.**

---

# 8. Cross-layer Shared Expert Pool / Hyper Experts

## 핵심 아이디어

일반 MoE:

```text
Layer 1 → Expert A/B/C
Layer 2 → Expert D/E/F
Layer 3 → Expert G/H/I
```

대신:

```text
Global Expert Pool
A B C D
↑ ↑ ↑ ↑
모든 layer가 공유
```

한다.

Hyper Experts는 모든 MLP를 cross-layer shared pool로 묶어 입력 token별 계산 경로를 layer 사이에서도 재구성할 수 있도록 한다.

### 상주 메모리

**잘 설계하면 동일하게 유지 가능.**

예를 들어 현재 16개 middle MLP의 total weight budget을 4~8개 shared expert로 재배치한다.

### 품질

**+++**

Hyper Experts는 dense baseline보다 낮은 training loss와 높은 evaluation metric을 보고했다.

특히 같은 expert를 한 forward에서 여러 번 사용할 수 있어 parameter utilization을 높인다.

### 계산량

router와 expert activation에 따라 증가하거나 감소한다.

### 구현 난이도

**상.**

TinyLM의 현재 `mlp_group`을 한 단계 더 일반화해야 한다.

필요한 요소:

- cross-layer router
- expert scheduling
- expert reuse
- load balancing
- ternary expert kernel compatibility

### CPU 적합성

**중~낮음.**

routing/gather/scatter 때문에 CPU 효율이 나빠질 가능성이 크다.

### 연구 가치

**매우 높음.**

특히 TinyLM의 "fixed resident memory" 연구 주제와 Hyper Experts의 cross-layer parameter reallocation이 직접 연결된다.

### 결론

**실용적인 1차 모델보다는 논문의 2세대/novel architecture 후보.**

---

# 9. Attention Sharing

현재 TinyLM은 middle MLP를 공유하지만 attention은 layer별로 독립적이다.

이는 상당한 parameter reuse 여지를 남긴다.

### 제안

```text
Attention A
Attention B
Attention C
Attention D

→ 16 middle layers에서 재사용
```

그리고 layer-specific LoRA/FiLM으로 층별 차이를 보완한다.

### 상주 메모리

**상당히 감소 가능.**

현재 독립 attention projection을 여러 층에서 저장하는 부분을 shared set으로 바꾸기 때문이다.

### 품질

**++**

MLP보다 attention sharing이 품질을 더 크게 손상시킬 수도 있으므로 단계적 실험이 필요하다.

### 계산량

동일한 block을 반복하면 계산량은 동일한 depth 기준에서는 거의 동일하다.

### CPU

**높음.**

고정된 GEMM sequence를 반복할 수 있다.

### 결론

**Full-block sharing 전에 Attention-only sharing ablation을 반드시 권장.**

---

# 10. Embedding/LM Head 압축 → 절약한 memory를 depth로 재배분

현재 TinyLM의 factorized embedding은 이미 embedding parameter를 줄이고 있다.

추가적인 embedding rank 축소:

```text
E = 256 → 192 → 128
```

로 resident memory를 줄이고 그 memory budget을:

- shared adapter
- recurrent block
- attention parameter
- expert pool

등에 재투자할 수 있다.

### 장점

모델의 전체 resident memory를 증가시키지 않는다.

### 단점

embedding/LM head는 어휘 표현의 병목이 될 수 있다.

특히 factorized tied embedding의 특성 때문에 단순 quantization과는 다른 trade-off가 발생한다.

### 결론

**주 실험보다는 budget reallocation ablation으로 권장.**

---

# 11. Mixture-of-Depths식 token-level compute

Mixture-of-Depths는 layer마다 top-k token만 full attention/MLP computation에 참여시키는 방법이다.

### 장점

- resident weight 증가 없음
- 동일한 weight로 선택적 computation
- 평균 FLOPs 감소 가능

### 단점

CPU에서는 token routing이 GPU보다 불리할 수 있다.

또 100M CPU 모델에서는 memory bandwidth와 GEMM efficiency가 중요한데, token sparsity가 오히려 kernel utilization을 떨어뜨릴 수 있다.

### 결론

**품질/효율 연구로는 유망하지만 CPU-primary TinyLM에서는 후순위.**

---

# 12. MLA / Latent KV Compression

MLA 계열은 KV cache를 latent space로 압축하여 autoregressive inference 메모리와 bandwidth를 줄인다.

### 중요한 구분

이 방법은 기본적으로:

```text
resident weight
```

보다

```text
KV cache
```

를 줄이는 방법이다.

따라서 이번 연구의 1차 목표인 "같은 resident model memory에서 더 높은 intelligence"와는 직접적 연결성이 약하다.

### 결론

**장기 context / decode memory 연구에는 가치가 있으나 1차 방법으로는 비추천.**

---

# 13. 일반 MoE를 이번 연구의 핵심 방법으로 사용하지 않는 이유

MoE는 parameter capacity를 크게 증가시키면서 token당 활성 parameter를 제한할 수 있다.

그러나:

```text
total resident parameter
```

가 커진다.

사용자의 목표는 resident memory 고정이므로 일반 MoE는 정의상 불리하다.

Hyper Experts처럼 **existing parameter budget을 재배열하는 cross-layer expert sharing**은 예외다.

---

# 14. 가장 중요한 설계 원칙

## 원칙 1 — "Parameter count"와 "computational capacity"를 분리한다

이번 연구에서 가장 중요한 가설이다.

```text
Parameter capacity = 고정
        +
Depth = 증가
        +
Parameter reuse = 증가
```

하면 동일한 model memory에서 더 많은 computation을 수행할 수 있다.

---

## 원칙 2 — 완전 sharing만 하지 않는다

다음 구조가 가장 합리적이다.

```text
Shared large block
        +
Tiny layer-specific modulation
```

완전 sharing보다 표현력이 높고, layer-specific full parameter보다 memory가 작다.

---

## 원칙 3 — training에서도 반복 깊이를 경험시킨다

단순 inference repetition은 training distribution과 mismatch가 생길 수 있다.

따라서:

```text
Training:
16 / 20 / 24 / 28 iterations를 혼합

Inference:
16 / 20 / 24 / 28 선택
```

같은 elastic-depth training을 권장한다.

---

# 15. 권장 실험 로드맵

## Phase 1 — 위험이 가장 낮은 실험

### P1-A
현재 m100 baseline

### P1-B
MLP sharing 증가

```text
g4 → g8 → g16
```

### P1-C
Attention sharing

```text
attn_group = 1 / 2 / 4
```

### P1-D
Full-block sharing

### P1-E
Full-block sharing + rank-4/8 layer adapter

이 단계에서는 **resident memory를 정확히 동일하게 맞춘 후** 비교한다.

---

## Phase 2 — effective depth 실험

같은 parameter budget에서:

```text
20 effective layers
24
28
32
```

을 비교한다.

권장 핵심 지표:

- validation loss
- perplexity
- task benchmark
- tokens/s
- ms/token
- peak RSS
- resident weight bytes
- total MACs
- activation memory

---

## Phase 3 — Depth-aware KD

teacher의 intermediate representation을:

```text
Teacher depth
↓
Student recurrent iteration
```

으로 대응시킨다.

baseline KD와 반드시 비교한다.

---

## Phase 4 — Adaptive depth

```text
fixed 20
fixed 24
fixed 28
adaptive
```

를 비교한다.

adaptive 모델은 평균 FLOPs도 기록해야 한다.

---

## Phase 5 — Cross-layer Expert

최종적으로:

```text
MLP group sharing
        ↓
Cross-layer Expert Pool
```

을 시험한다.

이 단계가 논문에서 가장 독창적인 아키텍처 기여 후보가 될 가능성이 높다.

---

# 16. 권장 우선순위 최종판

| 순위 | 방법 | 이유 |
|---:|---|---|
| **1** | **Full-block sharing + recurrent depth** | resident memory 증가 없이 effective depth를 늘릴 수 있고, MobileLLM/Universal Transformer의 직접적인 근거가 있음 |
| **2** | **Shared block + tiny LoRA/FiLM** | 현재 TinyLM 코드와 거의 직접적으로 연결되고 full sharing의 표현력 손실을 보완 |
| **3** | **Intermediate / depth-aware KD** | 구조를 바꾸지 않으면서 shared recurrent representation을 teacher의 depth에 맞게 학습시키는 강력한 보조 수단 |
| **4** | **Attention sharing** | 현재 구조에서 남아 있는 layer-specific parameter 중 큰 부분을 줄일 수 있음 |
| **5** | **Adaptive recurrent depth** | 동일 weight로 hard token에 계산을 더 배정할 수 있으나 CPU routing 비용 때문에 후순위 |
| **6** | **Cross-layer shared expert pool** | 가장 높은 연구 잠재력. Hyper Experts와 직접 연결되지만 구현 위험이 높음 |
| **7** | **Embedding/head budget reallocation** | memory budget을 재배분할 수 있으나 embedding 품질 손실 가능성을 별도 검증해야 함 |
| **8** | **Mixture-of-Depths** | 이론적으로 매력적이나 CPU implementation에 불리할 가능성 |
| **9** | **MLA** | KV cache 최적화가 주목적이라 현재 연구 질문과 직접적인 일치도가 낮음 |
| **제외** | 일반 MoE / width 증가 | resident memory 고정 조건과 충돌 |

---

# 17. 가장 추천하는 TinyLM 연구 구조

최종적으로는 다음 계열을 가장 추천한다.

```text
                Token Embedding
                       │
                       ▼
                  Prelude
                       │
                       ▼
          ┌────────────────────────┐
          │ Shared Transformer    │
          │                        │
          │ Shared Attention      │
          │ Shared SwiGLU MLP     │
          └────────────────────────┘
                       │
               recurrent × N
                       │
          + layer-specific tiny
            LoRA / FiLM / gate
                       │
                       ▼
              Adaptive Depth
                (optional)
                       │
                       ▼
                    Coda
                       │
                       ▼
                   LM Head
```

핵심적인 실험 가설은 다음이다.

> **H1:** 동일한 resident memory budget에서 layer sharing을 증가시키고 effective depth를 증가시키면 모델 품질이 향상될 수 있다.
>
> **H2:** complete sharing으로 인해 발생하는 layer specialization 손실은 소규모 LoRA/FiLM으로 상당 부분 복구할 수 있다.
>
> **H3:** intermediate KD를 사용하면 shared recurrent block이 depth별 representation hierarchy를 학습하기 쉬워진다.
>
> **H4:** adaptive depth를 사용하면 동일한 parameter budget에서 입력 난이도에 따라 계산량을 재배분하여 quality/compute Pareto frontier를 개선할 수 있다.
>
> **H5:** cross-layer expert sharing은 고정 resident memory에서 parameter utilization을 높이는 더 강력한 일반화가 될 수 있다.

---

# 18. CPU 중심 연구에서는 특히 주의할 점

이번 연구의 목표가 CPU 적합성을 포함한다면 다음 순서를 권장한다.

### CPU-friendly

1. weight sharing
2. recurrent block repetition
3. low-rank adapter
4. fixed-depth elastic inference
5. intermediate KD

### CPU-risky

6. adaptive token routing
7. dynamic expert routing
8. token-level sparsity
9. complex gather/scatter

즉 **1세대 TinyLM에서는 고정된 계산 graph를 유지하는 방법을 우선**한다.

그 이유는 CPU에서는 이론적인 FLOPs 감소가 실제 latency 감소로 이어지지 않을 수 있기 때문이다.

---

# 19. 선행연구 및 참고문헌

## [R1] MobileLLM

Zechun Liu et al., "MobileLLM: Optimizing Sub-billion Parameter Language Models for On-Device Use Cases," 2024.

핵심 관련성:

- sub-billion LLM
- deep-and-thin architecture
- GQA
- embedding sharing
- immediate block-wise weight sharing
- 125M / 350M 실험

**논문:**  
https://arxiv.org/abs/2402.14905

---

## [R2] Universal Transformer

Mostafa Dehghani et al., "Universal Transformers," ICLR 2019.

핵심 관련성:

- recurrent Transformer block
- parameter sharing
- computational depth와 parameter count의 분리
- adaptive computation

**논문:**  
https://arxiv.org/abs/1807.03819

---

## [R3] ALBERT

Zhenzhong Lan et al., "ALBERT: A Lite BERT for Self-supervised Learning of Language Representations," ICLR 2020.

핵심 관련성:

- cross-layer parameter sharing
- factorized embedding parameterization
- 작은 parameter budget에서 성능 유지

**논문:**  
https://arxiv.org/abs/1909.11942

---

## [R4] Mixture-of-Depths

David Raposo et al., "Mixture-of-Depths: Dynamically allocating compute in transformer-based language models," 2024.

핵심 관련성:

- token-level dynamic compute
- fixed global compute budget
- dynamic depth allocation

**논문:**  
https://arxiv.org/abs/2404.02258

---

## [R5] LayerDrop

Angela Fan, Edouard Grave, Armand Joulin, "Reducing Transformer Depth on Demand with Structured Dropout," ICLR 2020.

핵심 관련성:

- depth elasticity
- structured layer dropout
- inference-time subnetworks

**논문:**  
https://arxiv.org/abs/1909.11556

---

## [R6] TinyBERT

Xiaoqi Jiao et al., "TinyBERT: Distilling BERT for Natural Language Understanding," EMNLP 2020.

핵심 관련성:

- intermediate Transformer distillation
- small model KD
- teacher representation transfer

**논문:**  
https://arxiv.org/abs/1909.10351

---

## [R7] BitNet b1.58

Shuming Ma et al., "The Era of 1-bit LLMs: All Large Language Models are in 1.58 Bits," 2024.

핵심 관련성:

- ternary weights `{−1, 0, +1}`
- low-bit LLM
- parameter memory와 compute 효율

**논문:**  
https://arxiv.org/abs/2402.17764

---

## [R8] Hyper Experts

Ilya Deriy, Edoardo Cetin, "Hyper Experts: Language Models With Inference-Time Layer Reallocation," ICLR 2026 TTU Workshop.

핵심 관련성:

- cross-layer shared expert pool
- inference-time layer reallocation
- parameter utilization
- expert reuse across layers

**OpenReview:**  
https://openreview.net/forum?id=cGD7Nzuihz

**PDF:**  
https://openreview.net/pdf?id=cGD7Nzuihz

---

## [R9] Skip a Layer or Loop It? / PoLar

Ziyue Li, Yang Li, Tianyi Zhou, "Skip a Layer or Loop It? Learning Program-of-Layers in LLMs," 2026.

핵심 관련성:

- dynamic program-of-layers
- layer skipping
- layer looping
- input-dependent inference computation
- test-time compute allocation

**논문:**  
https://arxiv.org/abs/2606.06574

---

## [R10] Compact Language Models via Pruning and Knowledge Distillation

Saurav Muralidharan et al., "Compact Language Models via Pruning and Knowledge Distillation," 2024.

핵심 관련성:

- depth/width/attention/MLP pruning
- KD 기반 재학습
- compact LM 설계

**논문:**  
https://arxiv.org/abs/2407.14679

---

## [R11] SmolLM

Loubna Ben Allal et al., "SmolLM: blazingly fast and remarkably powerful," 2024.

핵심 관련성:

- 135M / 360M small LM
- MobileLLM 스타일 deep-and-thin architecture
- GQA
- embedding tying

**Model/연구 소개:**  
https://huggingface.co/blog/smollm

---

## [R12] SmolLM2

Hugging Face, "SmolLM2" model family, 2025.

핵심 관련성:

- 135M compact model
- on-device deployment
- small-model training and evaluation
- architecture informed by MobileLLM 계열

**Model card:**  
https://huggingface.co/HuggingFaceTB/SmolLM2-135M

---

# 20. 참고문헌에서 TinyLM 논문에 가장 직접적으로 연결할 문헌

논문 Related Work에 우선적으로 넣을 것을 고르면:

1. **MobileLLM** — sub-billion + deep/thin + layer sharing
2. **Universal Transformer** — recurrent parameter sharing
3. **ALBERT** — cross-layer parameter sharing
4. **TinyBERT** — intermediate KD
5. **Mixture-of-Depths** — dynamic computation
6. **Hyper Experts** — cross-layer expert sharing
7. **BitNet b1.58** — ternary representation

이다.

특히 TinyLM의 차별점은 단순한 layer sharing이 아니라,

```text
ternary weight
+
micro-group representation
+
MLP sharing
+
CLA/GQA
+
low-rank layer specialization
+
recurrent depth
+
CPU-oriented deployment
```

을 **고정 resident-memory budget이라는 동일한 제약 아래 통합**한다는 점으로 정리하는 것이 좋다.

---

# 21. 최종 의사결정

## 즉시 실험 권장

**A. Full-block sharing**

→ 가장 우선

**B. Full-block sharing + rank-4/8 LoRA 또는 FiLM**

→ A의 성능 손실 보정

**C. Effective depth 20/24/28/32 sweep**

→ "same memory, more computation" 가설 검증

**D. A/B/C + intermediate KD**

→ 작은 모델에서 representation hierarchy 복원

---

## 두 번째 단계

**E. Attention sharing**

→ 추가 resident memory 절감

**F. Adaptive recurrent depth**

→ quality/compute Pareto 개선

---

## 세 번째 단계 — 연구 novelty가 가장 높은 후보

**G. Cross-layer shared expert pool / Hyper Expert 스타일**

→ TinyLM의 `mlp_group`을 global expert pool로 일반화

→ 동일 resident parameter budget에서 parameter utilization을 최대화한다는 연구 질문으로 확장 가능

---

# 22. 한 문장으로 정리

**TinyLM m100에서 상주 메모리를 늘리지 않고 지능을 높이는 가장 현실적인 경로는 `full-block sharing → recurrent depth → tiny layer-specific modulation → depth-aware KD`이고, 그 다음 단계의 가장 흥미로운 연구 방향은 `cross-layer shared expert pool`이다.**

특히 현재 코드에는 MLP sharing, LoRA/FiLM, residual gate, `infer_repeat`가 이미 존재하므로 **대규모 코드 재작성 없이 단계적으로 검증할 수 있다는 점**이 이 접근의 가장 큰 장점이다.
