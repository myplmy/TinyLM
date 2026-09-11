# 제안 — Dynamic Sparse Training으로 연결 희소성을 처음부터 학습한다

> **작성** 2026-09-12 · **상태** ⏳판단 대기 · **분류** 실험계획  
> 양식: `proposal/README.md` §3.  
> 🚫 **이 문서는 제안서다. 승인 전에는 구현·학습·배치 파일 생성을 시작하지 않는다.**
>
> **제안 핵심:** 기존 P016의 3:4, P025의 2:4처럼 블록 내부에서 정해진 수의 weight를 강제로 0으로 만드는 것이 아니라, ​**전체 가능한 연결 중 제한된 수만 처음부터 존재하게 하고 학습 중 연결 위치를 prune/regrow하는 Dynamic Sparse Training(DST)**을 TinyLM의 ternary pretraining에 적용한다.
>
> **중복 제외 확인:** 저장소에서 이미 실험·검토한 Sherry 3:4, 2:4 semi-structured sparsity, Sparse-BitNet, GSQ/MaskLLM 계열은 본 제안의 신규 선행연구 근거와 실험축에서 제외한다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

TinyLM에는 이미 두 종류의 sparsity 축이 있다.

1. **P016 — 3:4 희소 삼진**
   - 4개 weight마다 하나를 0으로 강제하는 3:4 규칙.
   - 저장 밀도 1.25 bpw를 목적으로 했다.
   - 실제 TinyLM TWN은 원래도 약 **43–46%의 ternary zero**를 발생시키며, 3:4의 핵심 문제는 단순히 zero 수가 아니라 블록 제약 때문에 TWN이 살렸을 큰 weight를 추가로 제거한다는 것이 확인됐다.
   - 최종 재평가에서는 dense 대비 품질 대가가 약 `+0.04203`이고, 절약한 상주 MiB당 품질비가 기존 깊이 확장선보다 불리하여 해당 메모리 축은 종결됐다.

2. **P025 — 2:4 semi-structured sparsity**
   - 4개 weight 중 2개를 0으로 하는 NVIDIA 희소 Tensor Core 친화 구조.
   - 목표가 **GPU sparse GEMM 학습가속**이며, 50%의 구조적 sparsity를 고정된 N:M 패턴으로 강제한다.
   - 따라서 “어떤 뉴런/feature 사이의 연결을 유지할 것인가”를 자유롭게 학습하는 실험은 아니다.

즉 현재 TinyLM이 답하지 않은 질문은 다음이다.

> **동일한 layer width와 latent model capacity를 유지한 상태에서, 처음부터 전체 연결 중 일부만 활성화하고 학습 과정에서 연결 자체를 제거·재생성하면, 고정 N:M보다 높은 sparsity에서 품질을 유지할 수 있는가?**

이것은 P016/P025와 실험 변수가 다르다.

- P016/P025: **패턴을 사람이 고정**
- 본 제안: **연결 예산만 고정하고 topology를 학습**

또한 TinyLM의 ternary weight는 이미 상당한 수가 수치적으로 `0`이지만 이것과 **구조적으로 존재하지 않는 연결**은 구분해야 한다.

앞으로 다음 세 지표를 별도로 기록한다.

\[
S_{\rm mask}
=
1-\frac{\#M=1}{\#W}
\]

- `S_mask`: 구조적 연결 sparsity. mask에 의해 아예 비활성인 weight.

\[
Z_{\rm ternary}
=
\frac{\#(Q(W)=0 \land M=1)}
{\#(M=1)}
\]

- `Z_ternary`: 살아 있는 연결 중 ternary quantizer가 0으로 만든 비율.

그리고 실제 forward 기준

\[
S_{\rm effective}
=
1-\frac{\#(M\cdot Q(W)\ne0)}{\#W}
\]

를 별도로 측정한다.

예를 들어 `S_mask=50%`이고 활성 연결 내부의 ternary-zero 비율이 기존과 같은 46%라고 **가정**하면 nonzero는

\[
0.5\times0.54=0.27
\]

이므로 effective sparsity는 약 73%가 된다.

그러나 두 sparsity가 독립이라는 보장은 없으므로 이 값은 **예측치일 뿐이며 실제 실험에서 직접 측정한다.**

---

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

**TinyLM의 ternary Transformer를 dense latent topology가 아닌 sparse connectivity 상태에서 처음부터 pretrain하면서, 고정 연결과 dynamic rewiring 중 어느 방식이 주어진 structural density에서 가장 낮은 validation loss를 얻는지 확인하고, sparsity–품질–학습비용–메모리 Pareto frontier를 측정한다.**

주 독립변수:

1. structural mask density
   - 100%
   - 50%
   - 25%
   - 게이트 통과 시 12.5%

2. topology
   - dense
   - static random/ERK
   - dynamic sparse

3. regrowth rule
   - random regrowth
   - gradient-based regrowth(RigL 계열)

4. topology update interval
   - 초기 기본값 100 step
   - 필요 시 200/400 step

본 제안의 **1차 목적은 sparse kernel 가속이 아니다.**

먼저 알고리즘적으로

> “TinyLM이 연결의 50–75%를 실제로 제거한 채 dense와 경쟁할 수 있는가?”

를 판단한다.

실제 wall-clock 가속은 그 결과가 통과한 뒤 별도 kernel/structured-sparsity 단계로 넘긴다.

---

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| DST 신규 실험계획 | 승인 후 `test_plan/Pxxx_...md` |
| structural sparsity 구현 | `TLinear`/해당 linear 경로에 binary connectivity mask |
| static sparse baseline | uniform 및 ERK density allocation |
| dynamic sparse baseline | magnitude prune + gradient regrow |
| sparsity telemetry | layer별 density, ternary zero, effective zero |
| topology telemetry | prune/regrow 수, turnover, edge lifetime |
| resurrection telemetry | 죽은 연결 재생성 횟수와 반복 분포 |
| optimizer telemetry | topology update 직후 loss/update-norm spike |
| 품질 곡선 | val loss vs structural/effective sparsity |
| 계산 곡선 | theoretical active MAC/FLOP 및 실제 wall-clock 별도 표시 |
| 메모리 회계 | dense mask 구현 / 실제 sparse representation을 분리 |
| 최종 판정 | 채택 / 조건부 / 종결 |

특히 결과문서에서는 다음을 반드시 분리한다.

### A. 수학적 연결 절감

\[
\#W_{\rm active}
\]

### B. 실제 저장공간 절감

index/mask metadata까지 포함한 byte 수.

### C. 실제 연산 절감

실제 kernel이 zero 연산을 skip한 경우만 인정.

Python mask를 곱했을 뿐 dense GEMM을 수행했다면:

\[
\boxed{\text{FLOP 절감 = 0}}
\]

으로 기록한다.

즉 **“90% sparse”라는 숫자를 곧바로 “10× 빠름” 또는 “10× 작음”으로 해석하지 않는다.**

---

## 4. 비용

현재 저장소 검색에서 최신 m100 300M-token 기준의 신뢰할 수 있는 단일 `GPU-h/run` 정본 수치를 회수하지 못했다. 따라서 임의의 GPU-h를 만들어내지 않고 **baseline-run equivalent**를 1차 비용 단위로 사용하며, 승인 후 Stage 0에서 동일 장비의 GPU-h를 실측하여 절대값으로 변환한다.

`H300` = 현행 m100 300M-token baseline 1회의 실제 GPU 시간이라고 정의한다.

| 항목 | 양 |
|---|---:|
| Stage 0 계측/스모크 | ⚙ **≤0.05 H300** |
| Stage 1 30M-token screening | ⚙ **0.3–0.6 H300** |
| Stage 2 100M-token screening | ⚙ **1.0–2.0 H300** |
| Stage 3 300M-token 본실험 | ⚙ **3.0–5.0 H300** |
| 최악 총 GPU | ⚙ **≤7.65 H300** |
| 최초 권장 경로 예상 | ⚙ **약 4.0–5.0 H300** |
| AI 구현·분석 | ⚙ **6–10 engineer-h** |
| 사용자 직접 작업 | **승인 1회 + 장시간 학습 실행 여부 판단** |
| 추가 checkpoint 디스크 | ⚙ **2–6 GB**, 기존 보존정책에 따라 삭제 가능 |
| 신규 dataset | **0 B** |
| 신규 tokenizer | **없음** |

예를 들어 Stage 0에서 `H300=4 GPU-h`로 측정된다면 권장 경로는 대략

\[
16\sim20\ {\rm GPU\!-\!h}
\]

이고 최악 상한은 약

\[
30.6\ {\rm GPU\!-\!h}
\]

가 된다.

**Stage 0에서 반드시 H300을 다시 기록한 뒤 이후 비용표를 절대 GPU-h로 고친다.**

---

## 5. 원리·근거

### 5.1 우리 실측

| 근거 | 값/상태 | 출처 |
|---|---|---|
| TinyLM TWN의 자연 zero | 약 **43–46%** | P016 재검토 |
| P016 3:4 | 품질 대가 존재; 최종 메모리 Pareto에서 종결 | P016 / 결과 008 |
| P016 sparse packing | 3:4 자체 저장 포맷까지 구현·검증 경험 있음 | P016 |
| P025 | 2:4 sparse Tensor Core 축이 별도로 존재 | P025 |
| 미해결 영역 | 자유로운 connectivity topology를 pretrain부터 학습한 실험 없음 | repo 검색 결과 |

따라서 본 제안에서는 기존 결과를 다시 확인하기 위해 3:4 또는 2:4를 재학습하지 않는다.

---

### 5.2 신규 외부 근거

아래 논문은 이번 제안 작성 과정에서 실제 조회했으며, TinyLM 저장소 코드/문서 검색에서 제목·arXiv ID·핵심 키워드가 확인되지 않은 것만 신규 근거로 사용한다.

#### [R1] Mocanu et al., 2018 — Sparse Evolutionary Training

**Scalable training of artificial neural networks with adaptive sparse connectivity inspired by network science**

- Nature Communications 9, 2383 (2018)
- DOI: `10.1038/s41467-018-04316-3`
- 링크: [Nature / DOI 페이지](https://doi.org/10.1038/s41467-018-04316-3?utm_source=chatgpt.com)

SET은 처음부터 Erdős–Rényi sparse topology로 시작하고, 학습 중 작은 magnitude 연결을 제거한 뒤 동일한 수의 연결을 무작위로 추가하여 **총 연결 수를 일정하게 유지**한다. MLP 실험에서는 dense 연결의 약 1% 수준만 사용하는 사례에서도 경쟁력 있는 결과를 보고했다.

**TinyLM에 가져올 부분:**  
`magnitude death + random birth`를 가장 단순한 dynamic-topology baseline으로 사용한다.

---

#### [R2] Dettmers & Zettlemoyer, 2019 — Sparse Networks from Scratch / Sparse Momentum

**Sparse Networks from Scratch: Faster Training without Losing Performance**

- arXiv:1907.04840
- 링크: [arXiv 논문 페이지](https://arxiv.org/abs/1907.04840?utm_source=chatgpt.com)

학습 전체에서 sparse weight budget을 유지하면서 momentum 정보를 이용해 layer간 density와 신규 연결을 배치하는 방식을 제시했다. 저자들은 MNIST, CIFAR-10, ImageNet에서 dense 수준에 근접하는 sparse training과 최대 5.61× training speedup을 보고한다. 다만 이 speedup은 해당 구현·hardware 조건의 결과이지 TinyLM에서 재현된다고 가정하지 않는다.

**TinyLM에 가져올 부분:**  
단순 uniform density만 보지 않고 **layer별 sparsity allocation이 중요하다는 점**을 실험 설계에 반영한다.

---

#### [R3] Evci et al., 2020 — RigL

**Rigging the Lottery: Making All Tickets Winners**

- ICML 2020, PMLR 119
- 링크: [PMLR 논문 페이지](https://proceedings.mlr.press/v119/evci20a.html?utm_source=chatgpt.com)

RigL은 고정된 sparse parameter budget을 유지하면서 작은 magnitude의 현재 연결을 제거하고, 현재 0인 위치 가운데 **gradient magnitude가 큰 연결을 다시 활성화**한다. 따라서 weight 값뿐 아니라 connectivity 자체를 학습한다. ResNet, MobileNet, WikiText-103 RNN 등에서 sparse-to-sparse training의 경쟁력을 보였다.

**TinyLM의 주 기준 알고리즘으로 채택한다.**

이유는 SET의 random birth보다 다음 질문에 직접 답하기 때문이다.

> “현재 연결되지 않은 A→B가 실제 loss를 줄일 가능성이 큰가?”

gradient를 candidate score로 사용할 수 있다.

---

#### [R4] Hu et al., 2025 — Mixed Sparsity Training

**Mixed Sparsity Training: Achieving 4× FLOP Reduction for Transformer Pretraining**

- Transactions on Machine Learning Research, 2025
- OpenReview ID: `XosdLS7KVE`
- 링크: [OpenReview 논문 PDF](https://openreview.net/pdf?id=XosdLS7KVE&utm_source=chatgpt.com)

Transformer pretraining에서 dynamic sparse training에 warm-up, ultra-sparsification, restoration 단계를 결합하고 GPT-2 실험에서 약 4×의 이론적/실험상 FLOP 감소와 성능 보존을 보고했다. 특히 static 80% sparsity와 RigL 80%를 비교 대상으로 사용한다.

**TinyLM에 가져올 부분:**  
처음부터 최종 extreme sparsity를 강요하는 실험만 하지 않고,

\[
\text{dense/low-sparse warm-up}
\rightarrow
\text{target sparsity}
\]

schedule을 후속 옵션으로 둔다.

다만 본 제안 1차 실험에서는 변수 폭증을 피하기 위해 **constant sparse budget부터 검증한다.**

---

#### [R5] Xiao et al., 2026 — SMET

**Memory-Efficient LLM Training with Dynamic Sparsity: From Stability to Practical Scaling**

- ICML 2026
- arXiv:2606.00888
- DOI: `10.48550/arXiv.2606.00888`
- 링크: [arXiv/Hugging Face paper page](https://huggingface.co/papers/2606.00888?utm_source=chatgpt.com)

2026년 LLM용 DST 연구에서는 topology update 직후 발생하는 **loss spike**를 중요 문제로 보고한다. 새로 regrow된 parameter에는 Adam 계열 optimizer의 누적 상태가 없기 때문에 cold-start update가 지나치게 커질 수 있으며, SMET은 optimizer warm-up 및 density-aware LR scaling으로 이를 완화한다. 또한 active parameter에만 gradient/optimizer state를 보관하는 memory-efficient training을 제안한다.

**TinyLM에 가장 직접적으로 중요한 신규 근거다.**

TinyLM이 AdamW 계열 optimizer를 사용하는 실험에서는 “연결을 다시 살리는 것”이 단순 mask 조작이 아니라 **optimizer-state 문제**까지 만든다.

따라서 본 실험에서는 반드시 다음을 계측한다.

- topology update 전 loss
- update 직후 loss
- 1/2/4/8/16 step 후 loss
- 신규 regrown weight의 update norm
- 기존 active weight의 update norm
- Adam 1st/2nd moment 초기화 방식

---

#### [R6] Wu et al., 2026 — data-constrained sparse LLM scaling

**When Data Is Scarce: Scaling Sparse Language Models with Repeated Training**

- ICML 2026
- arXiv:2606.01155
- 링크: [arXiv 논문 페이지](https://arxiv.org/abs/2606.01155?utm_source=chatgpt.com)

최대 1.92B 모델, 최대 93.75% sparsity 및 반복 학습 조건을 조사하여 제한된 unique-data 상황에서 sparse training과 data repetition의 상호작용을 분석했다. 저자들은 loss 관점의 최적 sparsity가 대략 **중간 수준(~50%)​**이고, compute 관점 최적값은 더 높아질 수 있다고 보고한다.

TinyLM은 제한된 데이터 pool 및 반복 노출 실험축도 가지고 있으므로 향후 두 축을 결합할 근거가 있다.

그러나 **이번 실험에서는 반복 epoch 축을 섞지 않는다.**

먼저 1-epoch/현행 데이터 조건에서 sparsity만 독립적으로 식별한다.

---

### 5.3 본 제안에서 의도적으로 제외한 기존 연구

다음은 TinyLM 저장소에서 이미 연구 또는 리뷰한 항목이므로 신규 참고문헌으로 계산하지 않으며 재검증하지 않는다.

- Sherry / 3:4 ternary sparsification
- P016 3:4 sparse ternary
- P025 2:4 semi-structured GPU sparsity
- *Accelerating Transformer Pre-training with 2:4 Sparsity*
- Sparse-BitNet
- GSQ
- MaskLLM 관련 learned N:M mask
- Arenas residual-synapse 계열

즉 본 제안의 novelty는 **N:M mask를 더 잘 고르는 것**이 아니라

\[
\boxed{
\text{free connectivity under a fixed sparse budget}
}
\]

이다.

---

## 6. 방법

### 6.1 실험 대상

첫 실험은 가장 해석하기 쉬운 조건을 사용한다.

- 현재 TinyLM m100 계열 baseline
- tokenizer/data split 고정
- train token budget 고정
- seed 고정
- LR/schedule 고정
- KD/tied variants는 **첫 실험에서 제외**
- ternary linear 대상
- embedding / norm / scalar parameter는 sparse mask 대상에서 제외

이유:

DST + ternary + tying + KD를 처음부터 함께 넣으면 실패했을 때 원인을 분리할 수 없다.

먼저

\[
\text{Ternary baseline}
\quad\text{vs}\quad
\text{Ternary + connectivity sparsity}
\]

만 비교한다.

---

### 6.2 mask 정의

각 대상 weight matrix \(W_l\)마다

\[
M_l\in\{0,1\}^{\mathrm{shape}(W_l)}
\]

를 둔다.

forward는 개념적으로

\[
W_l^{\rm eff}
=
M_l\odot Q(W_l)
\]

이다.

여기서:

- \(W_l\): latent/master weight
- \(Q\): 기존 TinyLM ternary quantizer
- \(M_l\): structural connectivity mask

**중요:** `Q(W)=0`과 `M=0`은 의미가 다르다.

- `Q(W)=0`: 연결 슬롯은 존재하지만 현재 quantized weight 값이 0.
- `M=0`: 연결 자체가 topology에서 비활성.

두 상태를 로그에서도 절대로 합치지 않는다.

---

### 6.3 초기 density 배분

첫 screening에서 두 방식을 비교한다.

#### Uniform

모든 대상 matrix에서 같은 density \(d\).

\[
d_l=d
\]

#### ERK

Erdős–Rényi-Kernel 계열 배분으로 작은 layer/특정 shape에 상대적으로 높은 density를 허용한다.

전역 active parameter budget은 동일하게 맞춘다.

첫 목표:

\[
S_{\rm mask}=50\%
\]

통과하면:

\[
75\%
\]

마지막 탐색:

\[
87.5\%
\]

이다.

초기부터 90–95%를 주축으로 삼지 않는다.

2026 LLM 결과도 loss-optimal region이 중간 sparsity에 위치할 가능성을 보여주며, TinyLM은 이미 ternary 내부 zero까지 존재하기 때문이다.

---

### 6.4 Static sparse baseline

반드시 넣는다.

초기 mask를 뽑은 뒤 끝까지 고정한다.

\[
M_t=M_0
\]

이 baseline이 없으면 DST가 잘 나온 경우에도

> sparsity 자체가 괜찮았던 것인지  
> dynamic rewiring이 도움이 된 것인지

구별할 수 없다.

---

### 6.5 Dynamic rewiring

기본 RigL형:

#### death

현재 active weight 중

\[
|W_{ij}|
\]

가 작은 연결 일부를 제거.

#### birth

현재 inactive 위치 중

\[
\left|
\frac{\partial L}{\partial W_{ij}}
\right|
\]

가 큰 위치를 활성화.

항상

\[
\#M=1=\text{constant}
\]

를 유지한다.

초기 권장:

- topology update: 매 **100 step**
- 최초 prune fraction: **0.3**
- cosine decay하여 후반에는 topology를 안정화
- 마지막 **20% training steps에서는 topology freeze**

정확한 값은 실험계획 승인 후 스모크에서 조정한다.

---

### 6.6 “죽었다 살아나는 연결”을 반드시 추적한다

이번 실험은 val loss만 보는 실험으로 끝내지 않는다.

각 weight 위치에 대해 최소한 다음 통계를 기록한다.

- `birth_count`
- `death_count`
- `resurrection_count`
- `active_lifetime_steps`
- `inactive_lifetime_steps`
- 마지막 topology update 시점

그리고 다음 분포를 결과로 남긴다.

\[
P(N_{\rm resurrection}=0,1,2,3,\ldots)
\]

또한:

- 한 번 죽은 뒤 다시 살아난 비율
- 2회 이상 반복된 비율
- 최대 resurrection 횟수
- layer별 turnover
- 전체 active mask 중 update 때 바뀌는 비율

을 측정한다.

이를 통해 후속 실험에서

> “한번 제거한 연결을 영구 제거해도 되는가?”

를 실제 데이터로 판단할 수 있다.

---

### 6.7 topology-update 비용도 직접 잰다

DST의 theoretical sparse FLOP만 보고 가속으로 판정하지 않는다.

다음을 별도 기록한다.

\[
T_{\rm normal-step}
\]

\[
T_{\rm topology-update}
\]

그리고 전체 amortized cost:

\[
T_{\rm avg}
=
\frac{
N_{\rm normal}T_{\rm normal}
+
N_{\rm update}T_{\rm update}
}{
N_{\rm steps}
}
\]

를 사용한다.

현재 구현이 dense tensor + binary mask라면 실제 GEMM은 dense이므로 속도 향상으로 계산하지 않는다.

그 대신 이 단계에서 얻는 것은 **알고리즘적 feasibility**다.

---

### 6.8 단계별 게이트

| 단계 | 무엇 | 비용 | 다음으로 가는 조건 |
|---|---|---:|---|
| **0A** | 기존 sparsity 정의·계측 코드만 설계 | ⚙0.01 H300 | dense에서 `S_mask=0` 정확히 확인 |
| **0B** | mask/ternary forward-backward 스모크 | ⚙0.04 H300 | NaN 없음, active-count 오차 0 |
| **1A** | 30M: static 50% vs DST 50% | ⚙0.20 H300 | DST가 static보다 명확히 우세하거나 dense gap ≤0.05 |
| **1B** | 30M: DST 75% | ⚙0.10 H300 | 50% 대비 catastrophic divergence 없음 |
| **2A** | 100M: dense / static50 / DST50 / DST75 | ⚙1–2 H300 | best sparse가 dense gap ≤0.07 |
| **2B** | optimizer cold-start 진단 | 위에 포함 | topology update 후 반복 loss spike가 관리 가능 |
| **3A** | best density 300M 1 seed | ⚙1 H300 | 기존 TinyLM 채택선 안 |
| **3B** | best + runner-up/재현 seed | ⚙2–4 H300 | 효과가 seed noise보다 큼 |
| **4** | sparse storage/kernel 제안 여부 판정 | GPU 0 | 알고리즘적으로 살아남은 경우만 별도 제안 |

### 조기 중단

다음 중 하나면 해당 branch를 즉시 중단한다.

1. 30M 이후 val-loss gap `>+0.15`
2. topology update마다 반복적인 대형 loss spike가 회복되지 않음
3. 동일 sparsity static보다 DST가 지속적으로 나쁨
4. topology overhead가 지나치게 커서 연구 목적 대비 가치가 없음
5. 결과가 ternary-zero 변화만으로 설명되고 structural topology 효과가 없음

---

### 6.9 최소 실험 매트릭스

| 태그 | structural sparsity | topology | regrowth |
|---|---:|---|---|
| `base` | 0% | dense | 없음 |
| `s50_static` | 50% | static ERK | 없음 |
| `s50_set` | 50% | dynamic | random |
| `s50_rigl` | 50% | dynamic | gradient |
| `s75_rigl` | 75% | dynamic | gradient |

30M screening에서 SET가 RigL보다 명백히 떨어지면 이후 SET를 제거한다.

본실험은 최종적으로

- dense
- best static
- best DST

3개 정도로 줄인다.

---

### 6.10 핵심 판정 지표

#### 품질

\[
\Delta L
=
L_{\rm sparse}-L_{\rm dense}
\]

#### 구조 sparsity

\[
S_{\rm mask}
\]

#### effective sparsity

\[
S_{\rm effective}
\]

#### topology churn

\[
C_t
=
\frac{\#(M_t\ne M_{t-\Delta})}{\#W}
\]

#### resurrection rate

\[
R
=
\frac{
\#\{\text{한 번 죽고 다시 활성화된 edge}\}
}{
\#\{\text{한 번 이상 죽은 edge}\}
}
\]

#### sparse efficiency

저장·실제 kernel이 아직 없으면 quality per **active connection**만 표시하고 메모리/속도 이득이라고 부르지 않는다.

---

## 7. 거절하면 못 하는 것

기존 TinyLM 연구는 계속할 수 있다.

즉 이 제안을 거절한다고 해서 현재 프로젝트가 막히지는 않는다.

다만 다음 질문은 열린 채로 남는다.

1. TinyLM이 N:M이 아닌 **자유 topology sparsity**를 견딜 수 있는가?
2. 처음부터 50–75%의 연결만 학습해도 되는가?
3. 제거된 연결 중 실제로 몇 %가 다시 필요해지는가?
4. 한 번 죽은 weight를 영구 폐기해도 되는가?
5. sparse master weight/optimizer state까지 줄일 근거가 있는가?
6. TinyLM의 43–46% ternary zero가 구조적 redundancy와 같은 위치에서 발생하는가?
7. 같은 저장/active-parameter budget에서 작은 dense model보다 큰 sparse model이 좋은가?

따라서 **즉시 필요한 실험은 아니지만**, 향후 master-weight memory 및 sparse-training 연구를 진행하려면 선행 측정으로 가치가 있다.

---

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| ternary zero와 structural zero 혼동 | sparsity 수치가 과장됨 | 세 sparsity 지표를 별도 기록 |
| dense mask 구현을 실제 sparse 연산으로 오인 | FLOP/속도 절감 허위 보고 | profiler 실측 전 speedup=0 처리 |
| RigL gradient search가 비쌈 | update step 시간 폭증 | update interval 및 amortized cost 기록 |
| 새 edge Adam state cold-start | update 직후 loss spike | SMET식 warm-up/state 정책 후속 gate |
| 너무 높은 초기 sparsity | 초반 학습 자체 실패 | 50% → 75% → 87.5% 순차 진행 |
| sparse mask가 특정 layer를 고사시킴 | 일부 layer fan-in/out 붕괴 | ERK + 최소 density floor |
| random seed 의존 | 특정 topology만 우연히 성공 | 본실험에서 복수 seed |
| mask 메모리가 weight 절약보다 큼 | 저장량 증가 | 이 단계에서는 저장이득 주장 금지 |
| inactive latent W를 dense 보관 | master-memory 절감 없음 | 알고리즘 검증과 memory implementation 분리 |
| inactive gradient 후보 계산 | 실제 training compute 절약 없음 | 성공 후 sparse-gradient 구현 별도 제안 |
| topology가 계속 요동 | 최종 subnet 불안정 | update-rate decay + 후반 freeze |
| ternary STE와 mask STE 교락 | 어느 기법의 효과인지 불명확 | mask는 binary topology로 분리하고 기준선 고정 |
| 기존 P016/P025와 중복 | 실험 자원 낭비 | N:M 실험은 본 proposal에서 제외 |
| **계측 위험** | effective sparsity와 structural sparsity가 로그에서 섞임 | unit test로 hand-countable matrix 검증 |

### 특히 하지 말아야 할 것

초기 제안에서 다음을 한꺼번에 넣지 않는다.

- DST
- KD
- g8/g16 tying
- 3:4
- 2:4
- master-weight INT4
- optimizer 변경
- 반복 epoch

이렇게 하면 결과의 원인 식별이 불가능해진다.

---

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A — 권장** | **50→75% DST/RigL connectivity 실험** | P016/P025와 비중복, from-scratch sparse feasibility 직접 측정 | 당장 wall-clock 가속은 없음 |
| **B** | static sparse만 시험 | 구현 간단, topology 비용 없음 | sparsity 실패가 topology 선택 문제인지 알 수 없음 |
| **C** | 2:4/P025 재개 | 실제 GPU 가속 가능성 | 이미 존재하는 연구축, 신규 질문 아님 |
| **D** | 90%+ extreme sparsity부터 시작 | 성공 시 큰 이득 | ternary natural zero까지 있어 실패 원인 해석 어려움 |
| **E** | post-training pruning만 시행 | 저렴함 | pretraining부터 sparse할 수 있는지 답하지 못함 |
| **F** | 아무것도 안 한다 | 비용 0 | connectivity sparsity 축은 계속 미검증 |

### ★권장안과 근거

**A — 50%에서 시작하는 RigL형 Dynamic Sparse Training을 권장한다.**

이유는 네 가지다.

1. **기존 TinyLM 연구와 겹치지 않는다.**  
   기존 sparse 연구는 3:4와 2:4라는 N:M 규칙이 핵심이었다. 이번에는 구조적 연결 budget만 고정하고 어떤 연결을 사용할지를 학습한다.

2. **실패해도 정보가 남는다.**  
   static sparse와 dynamic sparse를 동시에 두면:
   - sparsity 자체의 손실
   - topology 선택의 손실
   을 분리할 수 있다.

3. **TinyLM에 특히 맞는 후속 질문으로 연결된다.**  
   TinyLM은 ternary quantization 때문에 이미 약 절반의 값이 zero가 된다. 구조적으로도 그 연결을 제거할 수 있다면 향후:
   - sparse master weight
   - sparse optimizer state
   - sparse gradient
   - 실제 sparse kernel
   로 확장할 근거가 생긴다.

4. **2026년 LLM 연구가 바로 필요한 위험을 알려준다.**  
   SMET 결과 때문에 topology change와 Adam state의 상호작용을 처음부터 계측할 수 있으며, 데이터가 제한된 경우에는 2026 sparse scaling 연구와 TinyLM 반복노출 축을 나중에 연결할 수도 있다.

### 최종 채택 기준

300M-token 본실험에서 다음을 모두 만족하면 **연구축 채택**:

\[
\Delta L\le +0.07
\]

그리고 structural sparsity:

\[
S_{\rm mask}\ge 50\%
\]

그리고 static sparse보다 DST가 유의미하게 우세하거나, 동일 품질에서 더 높은 sparsity를 허용할 것.

추가로:

- topology update instability가 제어 가능
- sparse budget 정의가 재현 가능
- effective sparsity와 ternary zero가 분리 계측됨

이어야 한다.

**실제 메모리 또는 속도 채택은 별도 판정이다.**

알고리즘 실험에서 성공하더라도 sparse representation/kernel이 실제로 이득을 만들지 못하면:

\[
\boxed{\text{품질 연구 성공} \ne \text{배포 최적화 성공}}
\]

으로 기록한다.

---

## 참고문헌 — 이번 저장소에서 기존 검토 흔적이 확인되지 않은 신규 근거만

1. Mocanu, D. C. et al. **Scalable training of artificial neural networks with adaptive sparse connectivity inspired by network science.** *Nature Communications* 9, 2383 (2018). DOI `10.1038/s41467-018-04316-3`. [DOI / Nature](https://doi.org/10.1038/s41467-018-04316-3?utm_source=chatgpt.com)

2. Dettmers, T. & Zettlemoyer, L. **Sparse Networks from Scratch: Faster Training without Losing Performance.** arXiv:1907.04840 (2019). [arXiv](https://arxiv.org/abs/1907.04840?utm_source=chatgpt.com)

3. Evci, U., Gale, T., Menick, J., Castro, P. S. & Elsen, E. **Rigging the Lottery: Making All Tickets Winners.** ICML 2020, PMLR 119, 2943–2952. [PMLR](https://proceedings.mlr.press/v119/evci20a.html?utm_source=chatgpt.com)

4. Hu, P., Li, S., Wang, X. & Huang, L. **Mixed Sparsity Training: Achieving 4× FLOP Reduction for Transformer Pretraining.** *Transactions on Machine Learning Research* (2025), OpenReview `XosdLS7KVE`. [OpenReview](https://openreview.net/forum?id=XosdLS7KVE&utm_source=chatgpt.com)

5. Xiao, Q. et al. **Memory-Efficient LLM Training with Dynamic Sparsity: From Stability to Practical Scaling.** ICML 2026, arXiv:2606.00888. DOI `10.48550/arXiv.2606.00888`. [paper page](https://huggingface.co/papers/2606.00888?utm_source=chatgpt.com)

6. Wu, B. et al. **When Data Is Scarce: Scaling Sparse Language Models with Repeated Training.** ICML 2026, arXiv:2606.01155. [arXiv](https://arxiv.org/abs/2606.01155?utm_source=chatgpt.com)

---

## 승인 후 첫 작업

승인되면 바로 학습부터 시작하지 않는다.

1. 이 제안을 `proposal/20260912_Dynamic-Sparse-Training으로-연결희소성을-학습한다-approved.md`로 판정 이력화.
2. 다음 미사용 `Pxxx` 번호를 확인.
3. `test_plan/Pxxx_...md`에 정식 실험계획 작성.
4. structural / ternary / effective sparsity의 hand-count unit test 작성.
5. 30M-token screening을 통과한 뒤에만 100M/300M 학습을 허용.

**현재 상태: ⏳ 사용자 판단 대기.**