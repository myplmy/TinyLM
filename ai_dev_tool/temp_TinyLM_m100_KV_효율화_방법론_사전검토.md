# TinyLM m100 KV-Cache 효율화 방법론 사전검토 문서

> 작업 전 검토용. 대상 모델은 TinyLM `m100`이며, 현재 구조와 연구 목표를 기준으로 KV-cache 효율화 방법론을 비교·우선순위화한다.

## 1. 문서 목적

본 문서는 TinyLM m100에 MLA 계열 및 기타 KV-cache 효율화 기법을 도입하기 전에 다음을 체계적으로 판단하기 위한 사전 검토 자료다.

- 어떤 방법이 실제 KV-cache를 얼마나 줄이는가?
- 품질 손실 가능성은 어느 정도인가?
- 계산량과 latency에는 어떤 영향을 주는가?
- 현재 TinyLM 코드/구조를 얼마나 수정해야 하는가?
- CPU 추론이라는 TinyLM의 목표와 양립하는가?
- 기존 GQA + CLA + weight tying + ternary 구조와 자연스럽게 결합되는가?
- 어떤 방법을 어떤 순서로 실험하는 것이 가장 효율적인가?

**중요:** 문헌에서 보고된 수치와 m100의 현재 구조로부터 계산한 이론값은 구분한다. 문헌 수치는 해당 논문의 실험 설정에 국한되며, m100에서 동일한 결과가 재현된다는 의미가 아니다.

---

# 2. 기준 모델: TinyLM m100

현재 코드의 m100 설정은 다음과 같다.

| 항목 | m100 설정 |
|---|---:|
| Hidden dimension `d` | 768 |
| Q heads | 12 |
| KV heads | 3 |
| Head dimension | 64 |
| FFN dimension | 2048 |
| Prelude / Middle / Coda | 2 / 16 / 2 |
| 총 layer | 20 |
| MLP group | 4 (기본 m100) |
| CLA group | 2 |
| Embedding rank | 256 |
| Vocab | 32,768 |
| RoPE | 적용 |
| Weight | ternary 계열 |

현재 `modules.py`의 attention은 **softmax + GQA + CLA + QK-norm** 구조다. Q/O projection은 각 layer가 소유하고, K/V는 CLA group의 첫 layer가 소유하여 다음 layer에서 재사용한다. fileciteturn4file0

현재 config에서도 `n_q_heads=12`, `n_kv_heads=3`, `cla_group=2`로 정의되어 있다. fileciteturn0file0

## 2.1 현재 KV-cache 크기의 기준값

head dimension은

`768 / 12 = 64`

이고, 한 CLA owner가 보유하는 K/V는

`3 KV heads × 64 = 192`

차원씩이다.

따라서 K+V는

`192 + 192 = 384 scalar / token / owner`

이다.

CLA group=2이므로 20개 layer 중 실질적인 KV owner는 10개다.

따라서 전체는

`384 × 10 = 3,840 scalar / token`

이다.

### 이론적 cache 크기

| Cache format | token당 | 1K context | 4K context | 8K context |
|---|---:|---:|---:|---:|
| FP32 | 15.0 KiB | 15 MiB | 60 MiB | 120 MiB |
| FP16 | 7.5 KiB | 7.5 MiB | 30 MiB | 60 MiB |
| INT8 | 3.75 KiB | 3.75 MiB | 15 MiB | 30 MiB |
| INT4 | 1.875 KiB | 1.875 MiB | 7.5 MiB | 15 MiB |

이는 **현재 KV 자체만 계산한 이론값**이며 allocator overhead, cache metadata, temporary tensor, activation 등을 포함한 실제 RSS와는 다르다.

---

# 3. 가장 중요한 전제: m100은 이미 KV를 상당히 줄인 상태다

일반적인 MHA를 사용하면

- K: `12 × 64 = 768`
- V: `12 × 64 = 768`
- 합계: `1,536 scalar / layer / token`

20 layer이면

`1,536 × 20 = 30,720 scalar / token`

이다.

현재 m100은 GQA + CLA를 사용하여

`30,720 / 3,840 = 8×`

수준으로 구조적인 KV 표현량을 줄인 상태다.

따라서 DeepSeek-V2 MLA가 MHA 대비 보고한 대규모 cache 감소율을 m100에 그대로 적용해서는 안 된다. m100에서 MLA는 **이미 압축된 GQA+CLA cache를 다시 압축하는 2차 압축 기법**으로 봐야 한다.

---

# 4. 방법론 종합 비교표

평가 기준:

- **KV 감소:** 현재 m100의 GQA+CLA 기준 추가 감소 가능성
- **품질:** 해당 방법이 일반적으로 유발하는 손실 가능성
- **계산량:** 기존 m100 attention 대비 상대적 변화
- **구현 난이도:** 코드 수정 및 검증 부담
- **아키텍처 변경:** 학습 모델 구조를 바꿔야 하는 정도
- **CPU 적합성:** CPU inference 관점
- **m100 적합성:** 현재 구조와의 결합 용이성

| 방법론 | KV 감소 | 품질 변화 | 계산량 | 구현 난이도 | 기존 아키텍처 변경 | CPU 적합성 | m100 적합성 | 권장도 |
|---|---|---|---|---|---|---|---|---|
| **FP16 KV** | 2× 저장량 | 거의 없음 | 거의 동일 | 매우 낮음 | 없음 | **매우 높음** | **매우 높음** | **P0** |
| **INT8 KV** | 4× 저장량 | 일반적으로 작음 | 소폭 증가 가능 | 낮음~중간 | 없음 | **높음** | **매우 높음** | **P0** |
| **INT4 KV** | 8× 저장량 | 데이터/양자화 방식 의존 | dequant overhead | 중간 | 없음 | 높음 | 높음 | **P1** |
| **GTA-like** | 약 1.5–3× 잠재적 추가 축소 | 소폭~중간 가능 | attention 감소 가능 | 중간~높음 | **부분 변경** | **높음** | **매우 높음** | **P2** |
| **MLA-lite r=128** | 약 1.4–1.7× (설계 의존) | 소폭 손실 가능 | projection/latent 계산 추가 | 높음 | **부분 변경** | 보통 | **높음** | **P3** |
| **MLA-lite r=96** | 이론상 약 2× | r=128보다 위험 | projection 추가 | 높음 | 부분 변경 | 보통 | 높음 | **P4** |
| **TransMLA-style conversion** | 큰 폭 가능 | healing 후 회복 가능 | 변환 후 MLA와 동일 | 높음 | **변경** | 보통 | 중~높음 | **P5** |
| **CARE-style rank allocation** | 큰 폭 가능 | uniform SVD보다 유리한 가능성 | rank 불균등 관리 | 매우 높음 | 변경 | 보통 | 높음 | **P6** |
| **SVDq 계열** | 큰 폭 가능 | mixed precision 설계 의존 | projection/quantization 추가 | 높음 | 부분 변경 | 보통 | 중간 | **P7** |
| **TurboQuant 계열** | 매우 큼 | 논문상 우수 | 저비트 연산/커널 의존 | 매우 높음 | cache path 변경 | **미검증/주의** | 중간 | **P8** |
| **Kimi Linear / Delta 계열** | 매우 큼 / 상태 기반 | 구조 전환 위험 | attention에 따라 감소 가능 | 매우 높음 | **대폭 변경** | 높을 가능성 | 낮음(현 단계) | **P9** |

---

# 5. 방법론별 세부 검토

## 5.1 FP16 KV-cache

### 핵심
KV를 FP32에서 FP16으로 저장한다.

### m100 기대값
현재 이론값 기준:

`15 KiB/token → 7.5 KiB/token`

즉 **저장량 2× 감소**.

### 장점
- 모델 attention 구조를 전혀 바꾸지 않는다.
- 현재 GQA+CLA와 완전히 호환된다.
- 품질 손실 가능성이 매우 낮다.
- 별도의 low-rank factorization이 필요 없다.
- CPU에서 FP16 지원 여부만 확인하면 된다.

### 단점
- CPU가 FP16 연산을 native하게 잘 처리하지 못하는 환경에서는 실제 throughput 이득이 작을 수 있다.
- KV memory bandwidth 감소가 곧 latency 감소를 보장하지 않는다.

### 판단
**반드시 baseline으로 먼저 측정해야 한다.**

---

## 5.2 INT8 KV-cache

### 핵심
K/V를 INT8로 저장하고 attention 계산 전에 dequantize하거나 INT8-aware kernel을 사용한다.

### 이론값
FP32 대비:

`4× cache reduction`

현재 m100 기준:

`15 KiB/token → 3.75 KiB/token`

### 선행연구
KIVI는 KV-cache의 K와 V가 서로 다른 통계 특성을 보인다는 점을 이용해 K/V에 서로 다른 양자화 축을 사용하며, 2-bit KV quantization으로 상당한 memory 절감 및 throughput 개선을 보고했다.

### 장점
- attention 구조를 유지한다.
- GQA+CLA와 결합하기 쉽다.
- MLA보다 코드 변경량이 훨씬 작다.
- cache가 길어질수록 효과가 커진다.

### 단점
- per-token/per-channel scale 관리가 필요하다.
- CPU에서 dequant 비용이 실제 memory bandwidth 절감 효과를 잠식할 수 있다.
- 8-bit가 정말 빠른지는 target CPU에서 실측해야 한다.

### 판단
**m100에서 MLA보다 먼저 해야 하는 실험.**

---

## 5.3 INT4 KV-cache

### 이론값
FP32 대비:

`8× cache reduction`

현재 m100 기준:

`15 KiB/token → 1.875 KiB/token`

### 장점
KV-cache가 매우 작아진다.

### 단점
INT8보다 quantization error가 커지고 kernel 구현의 영향이 크다.

### 판단
INT8이 성공한 뒤 확장하는 것이 좋다. 처음부터 INT4를 구현하면 attention 품질 손실과 kernel overhead가 동시에 섞여 원인 분석이 어려워진다.

---

# 6. MLA 계열

## 6.1 정통 MLA의 기본 개념

MLA는 K/V 자체를 모두 cache하지 않고 작은 latent representation을 cache한다.

개념적으로:

`h_t → c_t^{KV}`

를 만들고 `c_t^{KV}`를 저장한다.

필요한 경우 이를 이용해 K/V를 복원하거나 attention 계산에 직접 활용한다.

DeepSeek-V2의 MLA는 원래 MHA의 KV-cache 부담을 크게 줄이는 것을 목표로 설계되었다.

그러나 m100에서는 이미 GQA+CLA가 있기 때문에 동일한 절대 감소율을 기대할 수 없다.

---

# 7. MLA-lite를 m100에 적용하는 이유

m100의 현재 K/V projection은 다음과 같다.

- K: `768 × 192`
- V: `768 × 192`
- 총: `294,912 parameters`

단순화한 MLA latent 구조에서 rank를 `r`이라고 하면:

- down projection: `768 × r`
- K up projection: `r × 768`
- V up projection: `r × 768`

총 parameter는

`2,304 × r`

이다.

## 7.1 r=128

`2,304 × 128 = 294,912`

즉 **기존 K/V projection과 parameter 수가 동일**하다.

따라서 r=128은 m100에서 매우 좋은 first candidate다.

---

# 8. MLA-lite의 KV-cache 계산

MLA에는 RoPE를 별도 경로로 두는 설계가 필요할 수 있다. 이를 단순화하여 rope 차원을 `d_rope=8/head`라고 가정한다.

그러면 cache 크기를:

`latent_rank + Q_heads × d_rope`

로 근사할 수 있다.

## r=128

`128 + 12×8 = 224`

현재 GQA+CLA의 384와 비교하면:

`224 / 384 = 58.3%`

즉 약 **41.7% 추가 감소**.

## r=96

`96 + 12×8 = 192`

따라서:

`192 / 384 = 50%`

즉 **50% 추가 감소**.

이 값들은 **m100의 구체적 설계에서 계산한 이론값**이며 실제 구현에서는 cache representation, positional component, alignment, metadata를 포함해 재계산해야 한다.

---

# 9. MLA-lite의 평가

| 항목 | r=128 | r=96 |
|---|---|---|
| 추가 KV 감소 | 약 41.7% | 약 50% |
| K/V parameter | 기존과 동일 | 약 25% 감소 |
| 품질 위험 | 낮음~중간 | 중간 이상 |
| projection 계산 | 증가 | 증가 |
| CPU | 보통 | 보통 |
| 구현 난이도 | 높음 | 높음 |
| 기존 GQA+CLA와 결합 | 좋음 | 좋음 |
| 첫 실험 후보 | **강력 추천** | 2차 후보 |

### 결론
**MLA 자체를 연구하려면 r=128을 첫 설정으로 잡는 것이 가장 합리적이다.**

---

# 10. GTA-like

## 개념

GTA(Grouped-head latent Attention)는 attention-head sharing과 latent value representation을 동시에 활용하는 계열이다.

핵심은 MLA처럼 전체 K/V를 무조건 latent로 만드는 것보다:

- attention map의 redundancy
- value representation redundancy

를 동시에 제거하는 것이다.

## 왜 m100에 적합한가

m100은 이미:

`12 Q heads / 3 KV heads`

를 사용한다.

따라서 GTA-like 구조는 기존 GQA 설계에서 한 단계 확장하기 좋다.

예시:

- Q = 12
- K head = 1
- latent V = 128
- CLA = 2 유지

이 경우 기존 384 scalar/owner에 비해 훨씬 작은 cache를 만들 수 있다.

### 중요
GTA의 논문 결과에는 160M, 500M, 1B급 실험이 포함되어 있어 TinyLM 규모와 매우 가까운 연구 근거라는 장점이 있다.

다만 해당 연구는 현재 문헌 상태에서 withdrawn 이력이 있으므로, 확립된 SOTA로 단정하지 않고 **검증할 가치가 높은 연구 가설**로 취급해야 한다.

### 판단
**m100에서 MLA와 직접 경쟁시킬 가치가 매우 높다.**

---

# 11. TransMLA-style conversion

## 목적
이미 학습된 GQA 모델을 MLA 구조로 변환한다.

즉:

`trained GQA checkpoint → MLA initialization → healing/KD`

이다.

### 장점
- 기존 학습된 m100 checkpoint를 활용할 수 있다.
- 처음부터 MLA를 재학습하는 비용을 줄일 수 있다.
- GQA에서 MLA로 이동하는 실제 transformation 문제를 연구할 수 있다.

### 단점
- m100의 핵심 실험 목표가 from-scratch architecture comparison이라면 직접적인 우선순위는 낮다.
- conversion quality가 별도의 실험 변수로 추가된다.

### 판단
P018의 주력 구조 실험보다는 **P018 후속 conversion 연구**에 적합하다.

---

# 12. CARE-style activation-aware rank allocation

CARE는 단순 uniform SVD보다 activation covariance와 layer별 rank allocation을 고려하는 방식이다.

m100에서 특히 흥미로운 이유는 layer 구조가 균일하지 않기 때문이다.

- prelude
- middle
- coda
- CLA owner/non-owner
- tied MLP

등으로 층별 역할이 다르다.

따라서:

`r=128 for every layer`

보다

`r_l = layer-specific`

을 탐색하는 것이 자연스럽다.

예:

`96, 128, 160, ...`

### 장점
- 동일한 전체 KV budget에서 성능을 최적화할 여지가 있다.
- TinyLM의 구조적 layer heterogeneity와 잘 맞는다.

### 단점
- 구현과 실험 설계가 복잡하다.
- rank allocation이 추가적인 hyperparameter가 된다.

### 판단
MLA-lite가 성공한 뒤 **2단계 고도화 방법**으로 적합하다.

---

# 13. SVDq 계열

SVD로 KV 표현을 저랭크화한 뒤 mixed precision quantization을 추가하는 방식이다.

잠재적으로:

`low-rank + low-bit`

라는 두 압축축을 동시에 사용할 수 있다.

### 장점
- 구조적 압축과 수치적 압축을 동시에 이용한다.
- 매우 작은 cache를 목표로 할 수 있다.

### 단점
- 구현 복잡도가 높다.
- 실제 CPU latency가 좋아지는지 별도 검증이 필요하다.

### 판단
논문 최종 단계의 aggressive compression 후보로 적합하다.

---

# 14. TurboQuant 계열

TurboQuant는 초저비트 KV-cache 압축과 효율적인 attention computation을 목표로 하는 최신 연구다.

논문/공식 발표에서는 3-bit 수준의 KV quantization에서 큰 cache 절감과 일부 GPU에서의 attention speedup을 보고한다.

### 주의점
이 결과는 특정 GPU/kernel 환경의 성능이므로 **CPU에서 동일한 효과가 난다고 가정해서는 안 된다.**

TinyLM의 CPU 목표에서는:

- 실제 CPU vector ISA
- int4/int3 unpack cost
- dequant bandwidth
- cache locality

를 따로 측정해야 한다.

### 판단
**최우선 연구 대상은 아니다.** INT8/INT4 baseline 이후에 검토한다.

---

# 15. Kimi Linear / Delta 계열

이 계열은 KV-cache를 줄이는 수준을 넘어 attention을 recurrent/linear state 기반으로 바꾸는 접근이다.

이론적으로 context length에 따라 증가하는 full KV-cache 대신 고정 크기 state를 사용할 수 있다.

### 장점
- 초장문 context에서 매우 강하다.
- 메모리 성장률 자체를 바꿀 수 있다.

### 단점
- 현재 m100의 attention 구조를 크게 바꾼다.
- softmax attention과의 품질 비교가 복잡하다.
- P018의 현재 GQA+CLA 연구와 분리된 아키텍처 연구가 된다.

### 판단
**장기 연구용. 현재 P018/m100의 직접 후속으로는 부적합.**

---

# 16. CPU 적합성 관점의 핵심 판단

TinyLM은 GPU 전용 모델이 아니라 CPU 친화성을 중요한 목표로 한다. 따라서 논문의 FLOPs 감소만 보고 방법을 선택하면 안 된다.

CPU에서는 다음 경향을 예상할 수 있다.

### 유리

- cache 저장량 감소
- memory bandwidth 감소
- 간단한 int8 arithmetic
- 기존 GEMM/SIMD 경로 재사용

### 불리

- 복잡한 latent reconstruction
- 작은 matrix multiplication 증가
- bit unpacking
- 많은 scale/metadata 처리
- GPU용 fused kernel 의존성

따라서 **MLA가 이론상 cache를 더 줄이더라도 INT8 KV가 실제 CPU latency에서는 더 빠를 가능성**이 있다.

이것은 반드시 실측해야 한다.

---

# 17. 기존 TinyLM 구조와의 적합성

현재 TinyLM은 다음 구조적 특징을 가진다.

```text
Embedding
   ↓
20-layer Transformer
   ├─ Q: layer별 독립
   ├─ K/V: GQA
   ├─ K/V: CLA로 2-layer 공유
   ├─ MLP: middle layer tying
   ├─ Ternary weights
   └─ RoPE + QK-Norm
```

따라서 변경 위험을 기준으로 보면:

### 가장 자연스러운 방법

`KV precision 변경`

### 그 다음

`GTA-like`

### 그 다음

`MLA-lite`

### 그 다음

`TransMLA / CARE / SVDq`

### 가장 큰 변경

`Kimi Linear / Delta-type architecture`

---

# 18. 구현 영향 분석

현재 `modules.py`에는 attention registry가 존재하며 새로운 attention 종류를 등록할 수 있다. fileciteturn4file0

예상 구현량은 다음과 같다.

| 방법 | `modules.py` | `transformer.py` | `config.py` | kernel 추가 가능성 |
|---|---|---|---|---|
| FP16 KV | 소 | 매우 소 | 소 | 낮음 |
| INT8 KV | 중 | 중 | 소 | 중간 |
| INT4 KV | 중 | 중 | 소 | 높음 |
| GTA-like | 중~대 | 중 | 중 | 중간~높음 |
| MLA-lite | 대 | 대 | 중 | 높음 |
| TransMLA | 대 | 대 | 중 | 높음 |
| CARE | 대 | 대 | 대 | 높음 |
| SVDq | 대 | 대 | 대 | 높음 |
| Linear/Delta | 매우 대 | 매우 대 | 대 | 높음 |

특히 현재 attention registry 자체는 MLA를 추가할 수 있는 기반이 있으나, `transformer.forward()`의 KV-bank/owner orchestration은 현재 `softmax_cla`를 전제로 한다. 따라서 MLA/KDA 등 상태 구조가 다른 attention을 넣으려면 orchestration도 일반화해야 한다. fileciteturn4file0

---

# 19. 권장 우선순위

## P0 — 반드시 먼저 수행

### A. FP16 KV

목적: 구조 변경 없이 실제 cache/runtime baseline 확보.

### B. INT8 KV

목적: m100에서 가장 낮은 위험으로 cache를 4× 줄일 수 있는지 확인.

**P0의 이유:**

1. 현재 architecture를 거의 그대로 보존한다.
2. 품질 변화와 계산량을 분리해서 측정하기 쉽다.
3. MLA보다 구현 비용이 훨씬 낮다.
4. CPU 연구라는 TinyLM의 핵심 목표와 직접 연결된다.

---

# 20. P1 — 저비트 KV

### C. INT4 KV

INT8이 성공했을 때 수행한다.

조건:

- validation loss 허용 범위 내
- CPU latency 개선 또는 최소한 성능 유지
- 실제 RSS 감소 확인

---

# 21. P2 — GTA-like

### D. GTA-lite + CLA

추천 설정 예:

- Q = 12
- reduced K heads
- latent V rank = 128
- CLA = 2

**선택 이유:**

1. m100의 GQA 구조를 자연스럽게 확장한다.
2. MLA보다 구조 변경이 상대적으로 작다.
3. 소형 모델 규모의 선행연구가 있다.
4. attention computation 감소까지 기대할 수 있다.
5. CPU에 상대적으로 유리할 가능성이 있다.

---

# 22. P3 — MLA-lite

### E. MLA-lite r=128

권장 첫 구성:

- `r = 128`
- `d_rope = 8/head`
- `CLA = 2` 유지
- existing RoPE 유지
- QK-norm 유지

**선택 이유:**

- 현재 K/V projection parameter와 동일
- 현재 cache 대비 이론상 약 41.7% 추가 감소 가능
- r=96보다 품질 위험이 낮음
- MLA 자체를 연구하기에 구조적으로 명확함

---

# 23. P4 — MLA-lite r=96

r=128이 품질을 유지한다는 것이 확인된 후 수행한다.

목표:

- 약 50% 추가 KV reduction
- parameter까지 감소

**주의:** r 감소가 실제 품질에 미치는 영향을 정량화해야 한다.

---

# 24. P5 — TransMLA

기존 m100 checkpoint를 사용한다.

목표:

> `GQA+CLA checkpoint → MLA conversion`

이 연구는 구조 자체보다 **지식 보존과 conversion efficiency**를 평가한다.

---

# 25. P6 — CARE-style rank allocation

MLA-lite가 성공했다는 전제에서 수행한다.

목표:

> 동일한 KV budget에서 uniform rank보다 좋은 성능이 가능한가?

m100의 prelude/middle/coda와 CLA owner/non-owner 차이를 활용한다.

---

# 26. P7~P8 — 공격적 hybrid compression

다음 조합을 장기적으로 검토한다.

```text
MLA-lite / GTA
      +
INT8 / INT4 KV
```

또는

```text
Low-rank KV
      +
Mixed precision KV
```

이 단계에서 SVDq/TurboQuant 계열을 비교한다.

---

# 27. P9 — 구조 전환형 attention

Kimi Linear / Delta / recurrent state 계열은 현재 P018의 연장선보다는 별도의 architecture branch로 관리한다.

---

# 28. 권장 연구 트리

```text
m100 GQA + CLA
        │
        ├── P0: FP16 KV
        │       └── INT8 KV
        │             └── INT4 KV
        │
        ├── P2: GTA-like + CLA
        │
        └── P3: MLA-lite + CLA
                 │
                 ├── r=128
                 │      └── r=96
                 │
                 ├── CARE rank allocation
                 │
                 └── INT8/INT4 KV hybrid

별도 branch:
GQA checkpoint → TransMLA

장기 branch:
Kimi Linear / Delta-type
```

---

# 29. 반드시 통일해야 하는 평가 지표

서로 다른 방법을 비교할 때 단순 validation loss만 비교하면 안 된다.

## 품질

- validation loss
- perplexity
- downstream benchmark
- long-context benchmark

## 메모리

- theoretical KV bytes/token
- 실제 KV allocated bytes
- peak RSS
- model persistent memory
- temporary attention memory

## 속도

- prefill tok/s
- decode tok/s
- latency/token
- 1K / 4K / 8K context별 latency

## 계산

- attention FLOPs
- projection FLOPs
- dequant FLOPs
- latent reconstruction FLOPs

## CPU

- 단일 thread
- multi-thread
- SIMD 사용 여부
- memory bandwidth
- cache miss

---

# 30. 실험 설계에서 반드시 피해야 할 혼입

방법론을 비교할 때 다음을 동시에 바꾸면 원인을 판단할 수 없다.

### 잘못된 예

`MLA + INT4 + MLP g8 + 다른 LR + 다른 token budget`

### 권장

먼저:

`m100 baseline → MLA only`

그 다음:

`same MLA → MLA + INT8 KV`

그 다음:

`same KV method → different rank`

즉 한 번에 하나의 축만 바꾸는 것이 기본이다.

---

# 31. 품질 비교에서 권장하는 기준

m100의 기존 실험에서 validation loss 차이가 1σ 안팎일 수 있다는 점을 고려하면 단일 run의 작은 차이를 구조적 우위로 단정하면 안 된다.

권장:

- 동일 seed
- 동일 token budget
- 동일 dataset/pool
- 동일 training schedule
- 필요 시 2~3 seed
- 평균과 표준편차 보고

특히 MLA/GTA의 경우 초기 학습 수렴 속도가 달라질 수 있으므로 최종 validation loss만 보는 것보다 training curve를 함께 비교한다.

---

# 32. 작업 시작 전 최종 의사결정

## 1차 권장

**INT8 KV + 기존 GQA + CLA**

가장 먼저 구현한다.

## 2차 권장

**GTA-like + CLA**

현재 architecture를 크게 깨지 않으면서 구조적으로 더 큰 KV 절감을 검증한다.

## 3차 권장

**MLA-lite r=128 + CLA**

TinyLM에서 MLA의 실제 가치를 검증한다.

## 4차 권장

**MLA-lite r=96**

압축률을 더 높인다.

## 5차 권장

**CARE-style layer-wise rank allocation**

동일 KV budget 최적화를 시도한다.

## 별도 실험

**TransMLA-style checkpoint conversion**

기존 checkpoint 재활용 가능성을 검증한다.

## 후순위

**SVDq / TurboQuant / Kimi Linear 계열**

보다 공격적인 압축 및 구조 전환 연구에 사용한다.

---

# 33. 최종 권고

현재 TinyLM m100의 목적이 **초소형 모델 + 저메모리 + CPU 친화성 + 구조적 파라미터 절감**이라면, 단순히 “가장 KV를 많이 줄이는 방법”을 선택해서는 안 된다.

가장 중요한 것은 다음 Pareto frontier다.

```text
Quality
  ↑
  │             GQA+CLA baseline
  │              ●
  │        INT8 ●
  │
  │                 GTA-like ●
  │
  │                    MLA-lite ●
  │
  │                         INT4 / hybrid
  │                              ●
  └────────────────────────────────────→
                Memory reduction
```

따라서 현재 기준의 최종 권장 순서는:

**P0: FP16/INT8 KV → P1: INT4 KV → P2: GTA-like → P3: MLA-lite r=128 → P4: MLA-lite r=96 → P5: TransMLA → P6: CARE → P7~P8: SVDq/TurboQuant hybrid → P9: Linear/Delta 계열**

이다.

특히 **MLA를 반드시 구현해야 한다면 `m100 + GQA(12/3) + CLA(2) + MLA-lite(r=128)`를 첫 실험으로 삼는 것이 가장 합리적**이다. 반면 **실용적인 CPU 메모리 절감을 하나만 먼저 얻고 싶다면 INT8 KV-cache가 우선**이다.

---

# 34. 주요 참고문헌 및 자료

1. DeepSeek-AI, “DeepSeek-V2: A Strong Mixture-of-Experts Language Model,” 2024. MLA 원논문.
   - https://arxiv.org/abs/2405.04434

2. “Latent Multi-Head Attention for Small Language Models,” 2025.
   - https://arxiv.org/abs/2506.09342

3. “TransMLA: ... GQA to MLA conversion,” 2025.
   - https://arxiv.org/abs/2502.07864

4. “CARE: Covariance-Aware and Rank-Enhanced Decomposition for Enabling Multi-Head Latent Attention,” ICLR 2026.
   - https://arxiv.org/abs/2603.17946

5. “GTA: Grouped-head latent Attention,” 2025/2026.
   - https://arxiv.org/abs/2506.17286
   - OpenReview: https://openreview.net/forum?id=zS9Fwi8Ta9

6. Zirui Liu et al., “KIVI: A Tuning-Free Asymmetric 2-bit Quantization for KV Cache,” 2024.
   - https://arxiv.org/abs/2402.02750

7. “SVDq: ... KV Cache Compression,” 2025.
   - https://arxiv.org/abs/2502.15304

8. Google Research, “TurboQuant,” 2026.
   - https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/

9. “Kimi Linear: An Expressive, Efficient Attention Architecture,” 2025.
   - https://arxiv.org/abs/2510.26692

---

# 35. 작업 전 체크리스트

- [ ] m100 baseline의 실제 KV-cache dtype 및 peak RSS 측정
- [ ] FP16 KV baseline 측정
- [ ] INT8 KV 구현 및 품질 게이트 측정
- [ ] INT4 KV 구현 여부 결정
- [ ] GTA-like tensor shape 설계
- [ ] MLA-lite r=128 tensor shape 설계
- [ ] RoPE residual dimension 결정
- [ ] MLA cache의 실제 byte accounting 작성
- [ ] `transformer.py` KV-bank abstraction 분리
- [ ] attention 구현과 KV-cache representation을 분리
- [ ] 동일 token budget / seed / schedule로 비교
- [ ] 1K/4K/8K context에서 decode benchmark 수행
- [ ] CPU single-thread / multi-thread 모두 측정
- [ ] validation loss 외 downstream/long-context 품질 확인
- [ ] 실제 memory와 theoretical memory를 별도로 보고

---

## 한 줄 결론

**m100에서는 MLA를 첫 번째 KV 최적화 수단으로 선택하기보다 INT8 KV를 실용 baseline으로 확보하고, 그 다음 GTA-like와 MLA-lite(r=128)를 동일한 GQA+CLA 기반에서 비교하는 것이 가장 연구·구현·CPU 실용성 측면에서 균형이 좋다.**
