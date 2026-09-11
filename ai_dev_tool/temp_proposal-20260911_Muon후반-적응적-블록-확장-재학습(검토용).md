# 제안 — **Muon 후반 적응적 블록 재학습 + foldable latent expansion**

> **작성** 2026-09-11 · **상태** ⏳판단 대기 · **분류** 실험계획  
> 승인 시 신규 실험계획 **P091** 후보.  
> 양식: [`proposal/README.md`](README.md) §3. **아홉 절을 비우지 않는다.**
>
> 🚫**이 문서는 제안서다. 아직 구현·배치·GPU 런을 만들지 않는다.**  
> 승인 후 `test_plan/P091_...md`로 승격하고 구현 게이트(`ai_dev_tool/03`)를 통과한 뒤에만 배치를 만든다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

### 1.1 Muon은 TinyLM에서 이미 실제 이득을 보였다

P005의 최신 실측에서 `--optimizer muon --muon-lr-mult 15`는 본런에서 AdamW보다

- **Δ val = −0.04406**
- 무재귀 `d16`으로 전이해도 **−0.03625**
- `ms/step` 증가는 프로브에서 약 **+0.8%**
- `n_skip = 0`

를 보였다.

즉 **학습 초반·중반의 전역 최적화기로 Muon을 사용하는 축 자체는 이미 열려 있다.**

그러나 현재 Muon은 전 학습 가능 행렬에 대해 gradient와 momentum buffer를 유지하며 계속 전체 모델을 갱신한다.

---

### 1.2 반대로 후반에는 모든 블록에 같은 계산량을 계속 배분할 필요가 있는지는 측정하지 않았다

현재 학습은 기본적으로

\[
\theta_1,\theta_2,\ldots,\theta_k
\]

전체를 매 step 함께 업데이트한다.

하지만 late training에서는 각 parameter block의 한 단위 계산당 기대 개선량

\[
-\frac{\Delta L_i}{\Delta t_i}
\]

가 서로 같다는 보장이 없다.

가령 현재 상태에서

\[
S_2 \gg S_1,S_3,\ldots
\]

라면 남은 계산량을 모든 블록에 균등하게 쓰는 것보다 **블록 2에 일정 기간 집중한 뒤 다시 탐색하는 방식**이 같은 GPU 시간에서 더 효율적일 가능성이 있다.

🚫**TinyLM에서는 아직 이 질문을 직접 측정한 실험이 없다.**

현재 `train_repeat=block`은 특정 블록을 forward graph 안에서 반복 방문시키는 **재귀/깊이 증가**이며,

> 특정 parameter block만 여러 optimizer step 동안 집중해서 갱신한다

는 본 제안과 다른 축이다.

---

### 1.3 P087은 후반 추가 학습 자체가 아직 충분히 가치 있음을 보였다

P087에서 300M pool을 고정한 채 학습량을

- 2,289 steps → 4,578 steps

로 늘렸을 때

\[
3.64328 \rightarrow 3.52781
\]

즉 **−0.11547** 개선됐다.

4 epoch 상당인 9,156 steps에서도 다시 **−0.07438** 개선됐으며 `val-train_ce`도 과적합 문턱 0.3에 도달하지 않았다.

따라서 후반 계산 예산 자체가 이미 소진된 영역이 아니다.

본 제안의 질문은 다음이다.

> **그 추가 계산을 전체 모델에 균등하게 주는 것보다, 현재 가장 잘 먹히는 블록에 적응적으로 집중하면 더 싸게 같은 개선을 얻을 수 있는가?**

---

### 1.4 GPU 메모리 측면의 두 번째 동기가 있다

후반부에 한 번에 하나의 MLP parameter block만 학습시키면 다른 블록은 `requires_grad=False`로 둘 수 있다.

그러면 적어도

- frozen parameter의 parameter gradient
- 해당 parameter에 대한 GPU optimizer state

를 유지할 필요가 없다.

특히 TinyLM의 MLP는 `gate_proj`, `up_proj`, `down_proj` 세 행렬로 구성되므로 `dim=768, ffn=2048`에서 unique MLP 하나의 matrix parameter는 약

\[
3\times768\times2048
\approx4.72\text{M}
\]

이다.

전체 모델 optimizer state 대신 현재 선택된 수백만 parameter에만 optimizer를 두는 late phase가 가능하다.

⚠️**전체 VRAM이 이 비율만큼 줄어든다는 뜻은 아니다.**  
모델 가중치·activation·suffix backward는 남는다. 실제 `reserved` 감소량은 반드시 실측한다.

---

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

**초반·중반은 기존 Muon으로 전역 학습하고, 후반에는 short probe로 현재 loss를 가장 빠르게 줄이는 unique MLP block을 선택하여 일정 step 집중 학습한 뒤 다시 탐색하는 방식이, 전역 학습 지속보다 품질/시간/VRAM Pareto를 개선하는지 검증한다.**

독립변수는 네 개다.

1. **학습 범위**
   - global
   - local round-robin
   - local adaptive

2. **후반 optimizer 전환**
   - Muon 계속
   - AdamW cooldown

3. **임시 weight-space expansion**
   - 없음
   - foldable low-rank latent expansion

4. **탐색/집중 비율**
   - probe steps \(p\)
   - exploit steps \(n\)

★★**이 네 효과를 처음부터 한 팔에 섞지 않는다.**

---

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| ★adaptive block controller | `tinylm/train/refine.py` 후보. candidate 열거·probe·restore·선택·집중학습 |
| ★foldable latent expansion | `TLinear`의 training-only 임시 \(W+\Delta W\) 경로 |
| 블록별 효율 계측 | `ΔCE/token`, `ΔCE/GPU-second`, probe→실제 개선 상관 |
| VRAM 계측 | global vs local의 `allocated/reserved`, optimizer/grad 메모리 |
| wall-clock 계측 | ms/step, tokens/s, 총 GPU-second |
| 품질 판정 | `paired_eval` full-val 비교 |
| controller 신뢰성 판정 | 짧은 probe가 이후 32~128 step 이득 순위를 예측하는가 |
| rank 판정 | expansion rank 0 / 128 / 필요 시 256 |
| 최종 알고리즘 판정 | global Muon 대비 채택 / 조건부 채택 / 기각 |
| 승인 후 계획서 | `test_plan/P091_Muon후반-적응적-블록-확장-재학습.md` |
| 방법론 원장 | 해당 `docs/methods/` 표에 상태·트레이드오프 추가 |

최종적으로 단순히 *"loss가 줄었다"​*가 아니라 다음 함수를 얻는 것이 목표다.

\[
\text{late-training policy}
:
(\theta,t)
\rightarrow
\{\text{어느 블록을 몇 step 학습할지}\}
\]

그리고 이 policy가 유효하다면 향후 폭·깊이·타잉 구조에서도 후반 compute allocation 방법으로 재사용한다.

---

## 4. 비용

아래는 **제안 단계의 추정치**다. Stage0 실측으로 반드시 다시 계산한다.

| 항목 | 양 |
|---|---:|
| 구현·정적 진단 | ⚙ **2~4 engineer-h**, GPU 0 |
| 동적 smoke | ⚙ **0.1 GPU-h** |
| Stage1 controller 유효성 진단 | ⚙ **0.2~0.5 GPU-h** |
| Stage2 100M factorial screening | ⚙ **3~4 GPU-h** |
| Stage3 rank/주기 보정 | ⚙ **1~2 GPU-h**, Stage2 통과 시만 |
| ★Stage4 2-epoch-equivalent 1 seed | ⚙ **7~8 GPU-h**(2팔) |
| ★Stage4 두 번째 seed | ⚙ **추가 7~8 GPU-h**, 1 seed 통과 시만 |
| 디스크 | ⚙ **8~15 GB** 상한 예상. 실제 checkpoint 크기로 Stage0에서 재산정 |
| ★사용자가 직접 해야 하는 일 | `run_smoke_check.bat` 및 승인된 GPU 배치 실행 |

★★**최대 비용을 처음부터 지불하지 않는다.**

대략적인 비용 구조는

\[
0.5h
\rightarrow
4h
\rightarrow
2h
\rightarrow
8h
\rightarrow
8h
\]

의 순차 게이트다.

Stage1 또는 Stage2에서 가설이 닫히면 뒤 GPU 비용은 발생하지 않는다.

---

## 5. 원리·근거

### 5.1 우리 실측

| 근거 | 값 | 출처 |
|---|---:|---|
| Muon ×15 본런 이득 | **−0.04406** | P005 / 결과 076 §10 |
| Muon의 d16 무재귀 전이 | **−0.03625** | P005 / 결과 076 §10 |
| 반복 노출 e1→e2 | **−0.11547** | P087 / 결과 073 |
| 반복 노출 e2→e4 | **−0.07438** | P087 / 결과 073 §8 |
| e4 후 과적합 게이트 | `val-train_ce ≈ +0.0969 < 0.3` | P087 |
| Tied middle MLP | physical layer 여러 개가 unique MLP 하나를 공유 | `transformer.py` / `modules.py` |
| MLP projection | gate / up / down의 세 `TLinear` | `modules.py` |
| quantization | fp32 latent `weight` → ternary projection | `TLinear.refresh_quant()` |

이 실측은

1. **후반에 쓸 계산량 자체는 아직 가치가 있고**
2. **Muon은 초반·전역 학습에 이미 유효하며**
3. **MLP unique parameter group이 명시적으로 나뉘어 있다**

는 세 조건을 제공한다.

---

### 5.2 ★여기서 말하는 "확장"의 정확한 의미

🚫**실제 MLP hidden width를 일시적으로 늘리는 것이 아니다.**

SwiGLU에서 hidden neuron을 추가하면

\[
D_e[
\mathrm{silu}(G_ex)\odot U_ex
]
\]

라는 새로운 비선형 함수를 만들기 때문에 일반적으로 기존 폭의 행렬 하나로 **정확히 fold할 수 없다.**

본 제안이 사용하는 것은 **weight-space expansion**이다.

각 `TLinear`의 latent matrix에 대해

\[
W_{\rm eff}=W+sBA
\]

를 사용한다.

예:

\[
A\in\mathbb{R}^{r\times d_{in}},
\qquad
B\in\mathbb{R}^{d_{out}\times r}.
\]

초기에는

\[
B=0
\]

으로 두어

\[
W_{\rm eff}=W
\]

를 정확히 만족시킨다.

학습 후에는

\[
W\leftarrow W+sBA
\]

하고 \(A,B\)를 버린다.

따라서 최종 추론 모델은 다시 원래 parameter shape다.

★★이 proposal에서 **"가상 확장" = 임시 low-rank weight-space optimization dimension 추가​**라는 뜻으로 고정한다.

---

### 5.3 TinyLM의 ternary 경로에서는 expansion 위치가 중요하다

잘못된 구현:

\[
Q(W)x + BAx
\]

올바른 구현:

\[
Q(W+sBA)x.
\]

둘은 일반적으로 같지 않다.

따라서 expansion은 `TLinear` 출력에 LoRA처럼 더하는 것이 아니라 **latent weight가 centering/ternary projection에 들어가기 전**에 적용해야 한다.

즉 개념적 순서는

```text
weight
  + temporary_delta
       ↓
optional centering
       ↓
ternary()
       ↓
linear
```

이다.

fold 뒤에도 동일한 순서를 거쳐야 한다.

---

### 5.4 기존 ternary-LoRA 축과 다른 이유

P008의 persistent ternary-LoRA는 추론 구조에 남는 layer-specific 보정이며 이미 비용 대비 이득 문제로 종결됐다.

본 제안의 \(A,B\)는

- late training 동안만 존재하고
- 선택된 unique MLP 하나에만 붙으며
- exploit 종료 시 \(W\)에 fold되고
- inference graph와 배포 상주에는 남지 않는다.

따라서 **P008을 다시 여는 제안이 아니다.**

---

### 5.5 외부 근거

**이번 제안서에서는 신규 외부 논문을 근거로 사용하지 않는다.**

Muon 자체의 외부 근거는 이미 P005에서 관리하고 있다.  
본 proposal의 신규 주장인 *adaptive local refinement + foldable ternary-latent expansion*은 우선 TinyLM 내부에서 직접 측정한다.

외부 유사 연구 조사가 필요하면 승인 후 `docs/methods/08_paper_review.md` 규약에 따라 별도 수행한다.

---

## 6. 방법

### 6.1 실험 단위 — 🚫physical layer가 아니라 **unique MLP parameter block**

Tied 모델에서는 여러 physical layer가 같은 `mid_mlps[g]`를 참조한다.

따라서 candidate를 physical layer 번호로 정의하면 같은 parameter를 중복 후보로 세게 된다.

후보 단위는 반드시

```text
pre_mlps[*]
mid_mlps[*]   # unique shared modules
coda_mlps[*]
```

이다.

예를 들어 `2 + 16(g8) + 2`이면 candidate 수는

\[
2+2+2=6
\]

이다.

초기 실험에서는 **attention·embedding·norm은 후보에서 제외**한다.

MLP 행렬만 움직여 원인을 제한한다.

---

### 6.2 controller의 한 cycle

현재 모델 상태를 \(\theta_0\), 후보를 \(i=1,\ldots,k\)라고 한다.

각 후보마다 반드시 같은 \(\theta_0\)에서 시작한다.

```text
θ0
 ├─ candidate 1: p probe steps → score → restore
 ├─ candidate 2: p probe steps → score → restore
 ├─ ...
 └─ candidate k: p probe steps → score → restore
```

🚫다음처럼 하면 안 된다.

```text
candidate 1 학습 결과
      ↓
candidate 2 probe
      ↓
candidate 3 probe
```

순서에 따라 뒤 candidate가 다른 모델에서 평가되기 때문이다.

---

### 6.3 probe와 selector data를 분리한다

validation set은 controller가 절대 보지 않는다.

한 cycle에서 training pool로부터

- **P**: probe-update batches
- **C**: controller-score batches

두 window를 만든다.

모든 후보는 동일한 P와 C를 사용한다.

candidate \(i\)의 score:

\[
S_i =
\frac{
L_C(\theta_0)
-
L_C(\theta_i^{probe})
}{
t_i
}.
\]

즉

\[
\boxed{
S_i = \text{controller CE 감소 / GPU-second}
}
\]

를 primary selector로 한다.

보조로

\[
\Delta CE/\text{token}
\]

도 기록한다.

이렇게 해야 단순히 큰 블록이 더 많이 개선된다는 이유만으로 선택되지 않고 **실제 시간 효율**을 측정할 수 있다.

---

### 6.4 winner exploit

가장 큰 \(S_i\)를 얻은 candidate를 선택한다.

probe에서 수정된 model을 그대로 쓰지 않고 다시 \(\theta_0\)로 돌아간 뒤 winner만

\[
n
\]

step 학습한다.

초기 후보값:

- `probe_steps p = 4`
- `exploit_steps n = 128`

이다.

따라서 g8 표준 tied 구조의 후보가 6개라면 cycle당 탐색 비용은

\[
6\times4=24\text{ steps}
\]

이고 exploit은 128 steps다.

탐색 overhead의 step 기준 상한은 약

\[
24/128 = 18.75\%.
\]

🚫이 18.75%가 너무 비싸면 방법 자체의 목적과 충돌한다.

그래서 Stage1이 `p=2/4/8`, `n=64/128/256` 중 **최소한으로 신뢰 가능한 조합**을 고른다.

---

### 6.5 expansion을 켠 winner

선택된 MLP의

- `gate_proj`
- `up_proj`
- `down_proj`

각각에 임시 \(A,B\)를 붙인다.

`dim=768, ffn=2048`일 때 rank 128이면 임시 parameter 수는 대략

\[
3r(d+f)
=
3(128)(768+2048)
\approx1.08M.
\]

rank 256이면 약

\[
2.16M.
\]

초기 기본 후보는 **r=128**이다.

🚫처음부터 r=512 이상을 쓰지 않는다.  
adaptive allocation의 효과와 expansion의 효과를 분리하기 전에는 큰 expansion의 비용을 정당화할 수 없다.

---

### 6.6 fold gate

exploit 직전에 expansion 상태의 출력 \(z_e\)를 저장한다.

fold:

\[
W\leftarrow W+sBA
\]

후 temporary parameter를 제거하고 quant cache를 clear/rebuild한 뒤 \(z_f\)를 다시 계산한다.

필수 게이트:

\[
\max|z_e-z_f|
\]

가 fp32 진단에서 0 또는 사전 정의된 부동소수 오차 대역 안이어야 한다.

★★**이 gate가 실패하면 Stage1으로 가지 않는다.**

---

### 6.7 optimizer 교락을 분리한다

사용자 가설은

> **초반 Muon → 후반 local refinement**

이다.

그러나 후반에서 AdamW로 바꾸면

- optimizer 변경
- global→local 변경
- adaptive selection
- expansion

네 변화가 한꺼번에 생긴다.

따라서 Stage2는 다음 5팔로 분해한다.

| 팔 | Phase B optimizer | 학습 범위 | 선택 | expansion | 무엇을 분리하나 |
|---|---|---|---|---|---|
| **A** | Muon | global | — | off | 기존 방식 |
| **B** | AdamW | global | — | off | **optimizer switch 효과** |
| **C** | AdamW | local | round-robin | off | **localization 효과** |
| **D** | AdamW | local | adaptive | off | **selection 효과** |
| **E** | AdamW | local | adaptive | r128 | ★**expansion 효과** |

따라서

\[
B-A
\]

= Muon→AdamW 전환,

\[
C-B
\]

= global→local,

\[
D-C
\]

= adaptive selection,

\[
E-D
\]

= temporary expansion

으로 읽는다.

★★이 분해 없이 E와 A만 비교하면 결과가 좋아도 **무엇 때문에 좋아졌는지 알 수 없다.**

---

### 6.8 단계

| 단계 | 무엇 | 비용 | ★다음으로 가는 조건 |
|---|---|---:|---|
| **Stage0a** | 코드 설계·candidate mapping·default-off identity·fold identity | GPU 0, ⚙2~4 engineer-h | 모든 identity gate 통과 |
| **Stage0b** | 신규 경로 smoke + VRAM/timing 1차 | ⚙0.1 GPU-h | NaN/skip 0, 기존 off 경로 동일 |
| ★**Stage1** | short probe가 장기 이득을 예측하는가: `p=2/4/8` vs 32~128-step realized gain | ⚙0.2~0.5h | probe ranking이 재현 가능 |
| ★**Stage2** | **100M(763-step) 5팔 A~E** | ⚙3~4h | D>C 또는 E>D가 자동 ruler를 넘거나 명확한 Pareto |
| **Stage3** | rank 128→256, `p/n` 보정 | ⚙1~2h | r128이 유효하지만 포화하지 않은 경우만 |
| ★**Stage4a** | winner vs global control, 300M pool에서 **e1 상당 2,289 steps** | ⚙3.5~4h | winner가 유지 |
| ★★**Stage4b** | 같은 checkpoint에서 **e2 상당 4,578 steps까지 계속** | 추가 ⚙3.5~4h | e1에서 축이 살아 있을 때만 |
| **Stage5** | 다른 seed 재현 | ⚙7~8h | Stage4b 채택 문턱 통과 때만 |

---

### 6.9 ★"2 epoch"의 정확한 정의

P087에서 이미 확인했듯 현재 loader는 **uniform random sampling with replacement**다.

따라서 엄밀한

> 첫 번째 데이터 전체 순회 → 두 번째 데이터 전체 순회

구조가 아니다.

이 계획에서 `e2`는 P087과 같은 의미로 고정한다.

- pool = **300M**
- steps = **4,578**
- token exposure = **600M**
- 명목상 = **2 epoch-equivalent**

P087 실측에서 이때 pool coverage는 약 **86.47%**였다.

따라서 결과문서에는 🚫*"데이터를 정확히 두 번씩 보았다"​*라고 쓰지 않는다.

---

### 6.10 Stage1 — controller 자체를 먼저 검증한다

가장 중요한 선결은 expansion이 아니다.

> **4-step 개선 순위가 이후 128-step 개선 순위를 실제로 예측하는가?**

가 먼저다.

같은 parent checkpoint에서 후보마다

- 2-step
- 4-step
- 8-step

score를 구한 뒤, 실제 longer local refinement 결과와 비교한다.

측정:

- Spearman rank correlation
- top-1 일치
- top-2 포함률
- score margin
- window를 바꿨을 때 winner 안정성

초기 통과 기준:

- median Spearman \(\rho \ge 0.5\)
- 서로 다른 controller window 3개 중 **2개 이상에서 long-run winner가 probe top-2 안**
- `p=4`가 `p=8`과 사실상 같은 판정을 주면 **p=4 채택**

🚫통과하지 못하면 adaptive selection을 본런에 쓰지 않는다.

그때의 결론은

> "late block sensitivity는 존재하더라도 short probe로 싸게 찾을 수 없다"

이다.

이것도 중요한 결과다.

---

### 6.11 Stage2 사전등록 예측

| # | 예측 | 반증되면 |
|---|---|---|
| **P1** | B는 A보다 반드시 좋지 않을 수 있다. optimizer switch 자체는 불확실 | 이 팔은 단순 교락 제거용이므로 축 전체 기각 아님 |
| **P2** | local round-robin C는 global B보다 VRAM이 확실히 낮다 | 아니면 local refinement의 메모리 목적 실패 |
| **P3** | adaptive D가 round-robin C보다 `ΔCE/GPU-second`가 좋다 | adaptive selection 기각 |
| **P4** | r128 E가 D보다 추가 개선을 준다 | expansion 기각, adaptive만 유지 |
| **P5** | E의 최종 배포 모델은 fold 후 parameter shape·runtime memory가 D와 같다 | 아니면 "training-only expansion" 실패 |
| **P6** | Stage2의 probe+selection overhead는 총 wall-clock의 **25% 미만** | 초과하면 selector를 더 싸게 만들기 전 본런 금지 |

---

### 6.12 판정

품질의 자는 하드코딩하지 않는다.

★★`scripts/_rulers.py`와 `paired_eval`이 해당 계열의 현재 ruler를 선택하게 한다.

Stage2/4의 채택 조건은 다음 둘 중 하나다.

**품질형 승리**

\[
\Delta CE < -1\times\text{2σ ruler}
\]

이면서 wall-clock 악화가 **10% 이하**.

또는

**효율형 승리**

품질이 ruler 안에서 동급이면서

- total training wall-clock **15% 이상 감소**, 또는
- peak reserved VRAM **15% 이상 감소**.

최종 채택(Stage5 이후)은 **두 seed에서 방향이 같아야 한다.**

단일 seed의 효과량만으로 기본 학습법을 바꾸지 않는다.

---

### 6.13 compile은 두 단계로 다룬다

dynamic candidate switching과 temporary parameter attach/detach는 `torch.compile` 재컴파일과 충돌할 가능성이 높다.

따라서 초기 알고리즘 검증(Stage1~2)은

```text
모든 팔 eager
```

로 맞춘다.

그래야 compile 차이가 알고리즘 비교에 섞이지 않는다.

축이 열린 뒤 Stage4에서는 두 수치를 별도로 기록한다.

1. **algorithmic**: 양쪽 eager
2. **practical**: global baseline은 기존 최적 compile 경로, refinement는 실제 지원되는 최적 경로

🚫compile 지원을 나중에 할 것이라는 이유로 실험 자체를 미루지는 않는다.

---

### 6.14 초기 구현 범위 밖

첫 구현에는 다음을 넣지 않는다.

- attention block adaptive training
- embedding adaptive training
- actual hidden-width expansion
- gradient-norm pre-screen
- 여러 블록 동시 선택
- dynamic rank allocation
- `torch.compile`용 dynamic graph 최적화
- no-grad prefix 최적화
- Muon local-state offload 최적화

이것들은 **adaptive MLP refinement 자체가 이긴 뒤**에만 연다.

---

## 7. 거절하면 못 하는 것

TinyLM의 기존 연구는 그대로 진행할 수 있다.

즉 이 제안을 거절해도

- P005 Muon
- P087/P088 token scaling
- P089 width axis
- P090 SFT
- 기존 배포 최적화

에는 직접적인 blocker가 생기지 않는다.

다만 다음 질문은 열린 채로 남는다.

> **late training compute를 모든 parameter에 균등하게 계속 배분하는 것이 실제로 효율적인가?**

그리고 GPU 메모리가 제한된 환경에서

> **전체 optimizer state를 끝까지 GPU에 유지해야 하는가?**

도 답하지 못한다.

따라서 **필수 인프라 제안은 아니고, 학습 compute/VRAM Pareto를 새로 여는 연구 축​**이다.

---

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| ★probe ranking이 noisy | window마다 winner가 바뀜 | Stage1에서 먼저 측정. 불안정하면 축 종료/`p` 증가 |
| ★candidate order contamination | 뒤 candidate만 지속적으로 유리 | 모든 candidate를 동일 \(\theta_0\)에서 시작하고 optimizer state도 restore |
| validation leakage | validation loss를 selector가 직접 최적화 | controller set은 training pool에서만 추출 |
| optimizer switch 교락 | E가 좋아도 AdamW 때문인지 selection 때문인지 모름 | A~E 5팔 factorial |
| tied layer 중복 계산 | physical layer를 candidate로 세어 같은 weight를 여러 번 평가 | unique module identity로 후보 구성 |
| ternary mismatch | \(Q(W)+BA\) 방식으로 구현 | 반드시 \(Q(W+BA)\) |
| fold 불일치 | fold 전후 logits 차이 | Stage0 identity gate 실패 시 런 금지 |
| quant cache stale | fold 후 옛 `_wq` 사용 | `clear_quant()`/재생성 gate |
| compile 재컴파일 | selection마다 compile overhead | Stage1~2 eager |
| probe 비용 과다 | 탐색 시간이 exploit 이득을 먹음 | overhead >25%면 본런 중단 |
| local training이 global representation을 망침 | full-val 개선 없이 controller CE만 개선 | controller와 validation 완전 분리 + paired_eval |
| 한 블록에 계속 몰림 | 동일 candidate만 반복 선택 | 현상 자체를 기록. 강제 균등화는 첫 버전에 넣지 않음 |
| optimizer state reset 효과 | local 팔이 reset 때문에 달라짐 | A~E에 state 정책 명시·동일화 |
| VRAM 예상보다 안 줄음 | activation이 지배적 | Stage0 실측으로 확인. reserved <15%면 메모리 주장은 철회 |
| 속도 비교 세션 드리프트 | 다른 날 ms/step 차이 | 속도 팔은 같은 배치·동일 세션, 동시 실행 금지 |
| 250-step 오판 | 짧은 진단 loss를 최종 품질로 해석 | Stage1은 controller 진단일 뿐. 품질 판정은 763+ steps + paired_eval |
| P087과 "epoch" 의미 혼동 | 정확히 두 바퀴 돌았다고 서술 | `2 epoch-equivalent = 4578 steps`로 고정 |

---

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | ★**adaptive local refinement + 필요 시 r128 expansion** | selection과 expansion을 분리 가능. GPU optimizer state 축소 가능. inference 비용 0 | controller 구현 필요, probe overhead |
| **B** | local round-robin만 사용 | 매우 단순. 탐색비 0 | "현재 가장 잘 먹히는 층"이라는 핵심 가설을 사용하지 못함 |
| **C** | global Muon을 끝까지 계속 | 구현 0. 이미 이득 실측 | 후반 compute allocation·optimizer VRAM은 그대로 |
| **D** | 실제 hidden width를 임시 확장 | optimization capacity가 직관적 | SwiGLU 비선형 때문에 원래 폭으로 정확한 fold가 일반적으로 불가능 |
| **E** | gradient norm으로 한 번에 sensitivity 계산 | probe보다 싸질 가능성 | 전체 gradient memory가 다시 필요하고 `‖g‖`가 실제 loss/sec와 같다는 보장 없음 |
| **F** | 아무것도 안 한다 | 비용 0 | late compute allocation 질문이 열린 채로 남음 |

### ★권장안과 근거

**A를 권장한다. 단, expansion부터 시작하지 않는다.**

순서는 반드시

\[
\boxed{
\text{Muon 전역학습}
\rightarrow
\text{probe가 예측 가능한가?}
\rightarrow
\text{adaptive local만 검증}
\rightarrow
\text{그 뒤에 expansion 추가}
}
\]

로 한다.

핵심 이유는 세 가지다.

1. **가장 싼 실패 원인이 selector다.**  
   short probe가 장기 이득을 예측하지 못하면 expansion을 구현해도 adaptive policy의 근거가 없다.

2. **adaptive allocation과 virtual expansion은 서로 다른 가설이다.**  
   한 번에 켜면 어떤 효과가 이겼는지 알 수 없다.

3. **TinyLM에는 이미 후반 계산량이 유효하다는 실측(P087)과 초반 Muon의 이득(P005)이 있다.**  
   따라서 새로 답해야 할 부분은 *"남은 계산을 어디에 쓸 것인가"​*이지 Muon이나 추가 토큰의 가치를 다시 증명하는 것이 아니다.

---

## 승인 시 다음 작업

승인되면 다음 순서로 진행한다.

1. 이 제안서를 `-approved`로 이관.
2. `test_plan/P091_Muon후반-적응적-블록-확장-재학습.md` 작성.
3. `test_plan/실험계획목록.md`에 P091 등록.
4. `docs/methods/` 해당 원장에 **제안/미검증** 상태 추가.
5. `ai_dev_tool/03_실험착수_절차.md`에 따라 구현 게이트 수행.
6. 새 기능은 **default off + 기존 경로 비트 동일**로 구현.
7. 신규 축을 실제로 켠 smoke arm과 `check_smoke.py EXPECT`를 함께 추가.
8. `check_static_all.py` 통과 후 사용자 `run_smoke_check.bat`.
9. **그 뒤에만** Stage1 배치를 작성.
10. Stage1 통과 전에는 Stage2~Stage5 GPU 배치를 만들지 않는다.

### 승인 선택지

- **승인 A — 전체 계획 승인**: Stage0부터 시작하고 각 gate를 만족할 때 자동으로 다음 단계 설계까지 진행.
- **승인 B — Stage0~1만 승인**: controller predictiveness까지만 확인 후 다시 사용자 판정.
- **기각**: 구현·배치·P091을 만들지 않고 제안서를 `-rejected`로 보존.