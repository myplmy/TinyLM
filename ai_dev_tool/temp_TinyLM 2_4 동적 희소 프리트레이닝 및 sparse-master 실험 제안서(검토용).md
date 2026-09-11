# 제안 — 2:4 동적 희소 프리트레이닝과 sparse-master 전환

> **작성** 2026-09-12 · **상태** ⏳판단 대기 · **분류** 실험계획  
> 양식: `proposal/README.md` §3. **아홉 절을 비우지 않는다.**  
> 이 문서는 **제안**이며 승인 전에는 구현·배치 작성·학습을 시작하지 않는다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

TinyLM은 이미 TLinear에 **3:4 semi-structured sparsity**를 구현했다.

현재 구현의 핵심은 다음과 같다.

- 각 4-weight 블록에서 \(|w|\)가 가장 작은 1개를 0으로 강제한다.
- 따라서 forward에서 정확히 3/4의 weight를 유지한다.
- ternary 값은 `sign(w) × mask × α` 형태로 생성된다.
- 그러나 latent `self.weight` 자체는 dense `nn.Parameter`이다.
- backward도 inactive position을 포함한 전체 latent tensor에 gradient를 반환한다.
- 따라서 현재 방식은 **sparse executed weight + dense master weight** 구조다.

내부 근거:

- `tinylm/model/ternary.py`: `_TernarySTE`, `sparse34`
- P016 계열: 3:4 ternary sparsity
- `docs/EXPERIMENT_BASELINES.md`: `mA_g4s34_k4`, `mB_g8s34_k4` 등 실측
- `handoff/COMPASS.md`: 기존 3:4 메모리 축은 현재 지배당한 것으로 판정됨
- 현재 저장소의 핵심 목표는 단순 FLOPs 최소화가 아니라 **저메모리 초경량 모델**이므로 training master/optimizer state까지 줄일 수 있는 sparse-to-sparse 방식은 기존 3:4 배포 sparsity와 다른 질문이다.

기존 300M-token 공정 계열에서 다음 결과가 이미 있다.

| 모델 | 구성 | val | packed |
|---|---|---:|---:|
| `p6d` | dense | 3.7045 | 30.9 MB |
| `mA_g4s34_k4` | g4 + 3:4 + KD k4 | 3.7003 | 11.7 MB |
| `mB_g8s34_k4` | g8 + 3:4 + KD k4 | 3.7295 | 10.3 MB |
| `mC_g8_k4` | g8 + no 3:4 | 3.6862 | 14.9 MB |

단, 이 숫자는 과거 KD 조건이 포함된 계열이므로 **현재 무KD 표준조건과 직접 혼합하여 판정하지 않는다.**

외부 연구에서는 두 계열이 분리되어 발전했다.

1. **STE 기반 2:4**
   - dense latent/master weight를 유지한다.
   - 실행 weight만 2:4 sparse projection한다.
   - inactive weight도 gradient를 받아 다시 active가 될 수 있다.
   - NVIDIA Sparse Tensor Core와 결합하면 실제 transformer pretraining wall-clock 가속이 보고됐다.

2. **dynamic sparse-to-sparse**
   - master 자체도 sparse하게 유지한다.
   - 일정 주기마다 일부 active connection을 제거하고 새로운 connection을 생성한다.
   - RigL, Top-KAST에서 일반 sparse training이 검증됐고, 2026년 CHTs24는 이를 **2:4 semi-structured LLM linear layer**까지 확장했다.

현재 TinyLM에는 이 둘을 동일 조건에서 비교한 실험이 없다.

특히 다음 질문들은 미측정이다.

- 2:4에서 inactive weight가 실제로 얼마나 자주 다시 active가 되는가?
- 개별 weight의 resurrection 횟수 분포는 어떤가?
- topology churn은 학습 후반까지 필요한가?
- 일정 시점 이후 topology를 고정해도 품질이 유지되는가?
- dense master 및 optimizer state를 제거하면 실제 VRAM이 얼마나 감소하는가?
- sparsity가 실제 sparse GEMM으로 연결될 때 TinyLM 크기에서도 wall-clock 이득이 있는가?

이 제안은 이 여섯 질문을 하나의 단계적 실험으로 묶는다.

---

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

**TinyLM의 ternary MLP에 2:4 semi-structured dynamic sparsity를 pretraining 시작부터 적용했을 때, dense-master STE 방식과 true sparse-master 방식의 품질·학습속도·VRAM·topology dynamics를 비교하고, topology를 안전하게 조기 동결할 수 있는지를 측정한다.**

주요 독립변수는 다음 네 개다.

| 축 | 값 |
|---|---|
| master representation | dense / true sparse |
| topology | static / dynamic |
| topology refresh | 고정 주기 / 감소 schedule |
| topology freeze | 없음 / adaptive freeze |

1차 연구 질문:

> **dense master를 끝까지 유지하지 않아도 TinyLM의 품질을 유지하면서 training memory와 실제 wall-clock을 줄일 수 있는가?**

2차 연구 질문:

> **학습 초반 topology exploration 후 churn을 0으로 수렴시키는 것이 전체 학습 동안 계속 weight resurrection을 허용하는 것보다 효율적인가?**

---

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| 2:4 topology 계측기 | flip rate, resurrection count, death count, lifetime, last-resurrection-step |
| dense-master 2:4 기준선 | 현재 TLinear STE 구조를 일반화한 대조군 |
| sparse-master 2:4 기준선 | inactive weight와 optimizer state를 상주시킬 필요가 없는 sparse-to-sparse 대조군 |
| topology annealing 결과 | refresh fraction 감소 schedule별 품질/속도 |
| adaptive-freeze 판정 | topology를 어느 시점 이후 고정할 수 있는지 |
| VRAM 회계 | parameter / grad / optimizer state / temporary buffer 분리 |
| wall-clock 회계 | GEMM, mask/topology update, optimizer, 전체 step time 분리 |
| 품질 판정 | full-val + `paired_eval` 기반 Δ 및 조건별 분해능 |
| 최종 실험 결과문서 | dense / 2:4 dense-master / 2:4 sparse-master 간 Pareto 표 |
| 후속 판단 | TinyLM 기본 학습축으로 승격 / 메모리 전용 레버 / 폐기 중 하나 |

성공 시 바뀌는 것은 단순히 “2:4도 된다”가 아니다.

성공 조건을 만족하면 향후 TinyLM 학습에서:

- inactive master weight 제거,
- inactive AdamW state 제거,
- 학습 후반 topology search 제거,
- NVIDIA 2:4-compatible execution

을 동시에 고려할 근거가 생긴다.

---

## 4. 비용

아래는 **승인 후 실제 계획서를 작성할 때 다시 실측으로 보정할 추정치**다.

| 항목 | 양 |
|---|---:|
| GPU — 단계 0 kernel/correctness probe | ⚙0.3 GPU-h |
| GPU — 단계 1 topology instrumentation, 250-step × 3~4팔 | ⚙0.8 GPU-h |
| GPU — 단계 2 100M-token screening | ⚙2.5 GPU-h |
| GPU — 단계 3 300M-token 본런 | ⚙6~10 GPU-h |
| GPU — 반복/시드 확인 여유 | ⚙3~5 GPU-h |
| **최대 총 GPU** | **⚙12.6~18.6 GPU-h** |
| AI 작업 — 구현·정적게이트·분석·결과문서 | ⚙8~14 h |
| ★사용자가 직접 해야 하는 일 | ⚙0.5~1.0 h — 승인, GPU batch 실행/초기 감시, OOM·driver 오류 전달 |
| 디스크 | ⚙10~25 GB, checkpoint 정책에 따라 변동 |

### 비용 제한

전 단계를 자동으로 진행하지 않는다.

**앞 단계가 실패하면 다음 단계 비용을 쓰지 않는다.**

특히 단계 0에서 실제 2:4 kernel이 TinyLM shape에서 속도 이득을 내지 못하면 “학습가속” 본런은 중단한다.

---

## 5. 원리·근거

### 5.1 우리 실측·현재 구현

| 근거 | 값/사실 | 출처 |
|---|---|---|
| 기존 semi-structured sparsity | 3:4 존재 | `tinylm/model/ternary.py`, P016 |
| 3:4 선택법 | 4개 중 최소 \(|w|\) 1개 제거 | `_TernarySTE.forward()` |
| master | dense `nn.Parameter` | `TLinear.weight` |
| inactive gradient | backward에서 dense shape gradient 반환 | `_TernarySTE.backward()` |
| 기존 sparse packed 후보 | `mA_g4s34_k4` 11.7 MB | `docs/EXPERIMENT_BASELINES.md` |
| 속도 계측 주의 | 세션 간 ms/step drift 존재 | `CLAUDE.md` / 결과 037 |
| 현재 정책 | 다른 날 런의 속도 직접 비교 금지 | `CLAUDE.md` |
| 현재 품질 판정 | `paired_eval` 사용 | 저장소 기준표·COMPASS |
| 기존 3:4 위치 | 현재 양자화 메모리 축에서 지배당함 | `handoff/COMPASS.md` |

따라서 이번 실험은 P016의 단순 반복이 아니다.

P016:

> **배포 representation을 3:4로 더 압축할 수 있는가?**

이번 제안:

> **training topology와 master/optimizer state 자체를 sparse하게 유지할 수 있는가?**

질문이 다르다.

### 5.2 제안하는 학습 구조

#### A. Dense-master 2:4 — 기준선

각 4개 latent weight:

\[
w=(w_1,w_2,w_3,w_4)
\]

에서 magnitude 상위 2개만 forward에 사용한다.

\[
m_i =
\begin{cases}
1 & |w_i| \text{가 top-2}\\
0 & \text{otherwise}
\end{cases}
\]

executed ternary weight:

\[
\hat w_i = m_i \cdot \operatorname{sign}(w_i)\cdot\alpha.
\]

latent \(w_i\) 네 개는 모두 유지한다.

따라서 현재 `sparse34`를 2:4로 일반화한 가장 직접적인 대조군이다.

목적은 **“2:4 자체의 품질 대가”와 “sparse-master의 추가 대가”를 분리​**하는 것이다.

#### B. Dynamic sparse-master 2:4

master에서 각 4개 중 2개만 parameter로 유지한다.

예:

```text
step t
[A B 0 0]

refresh

A 제거
C 생성

[0 B C 0]
```

inactive position에는 지속적인 latent weight를 두지 않는다.

topology update 시:

1. 제거 후보: active 중 낮은 importance
2. 생성 후보: CHTs24형 topology score
3. 2:4 법칙을 깨지 않는 범위에서 1:1 교체
4. 새 weight는 명시된 initialization rule 사용
5. 새 weight의 optimizer state도 새로 정의

한다.

이 경우 forward sparsity뿐 아니라 **parameter와 optimizer state까지 sparse**해질 수 있다.

#### C. Churn annealing

초기에는 topology 탐색을 허용하되 교체율을 점차 낮춘다.

예시 초기 후보:

\[
\rho(t)=\rho_0\frac{1+\cos(\pi t/T_f)}{2}
\]

with

\[
\rho_0=0.10.
\]

즉 refresh 시 active weight의:

```text
10% → 7% → 3% → 1% → 0%
```

정도로 topology 교체가 줄어든다.

이 수치는 **사전 확정값이 아니라 screening 후보**이며 test plan에서 고정한다.

#### D. Adaptive freeze

다음이 동시에 만족되면 topology를 영구 고정하는 방식을 실험한다.

예시 gate:

- 최근 3회 refresh의 EMA flip rate < 0.5%
- 최근 resurrection의 대부분이 이미 재방문 위치
- validation 추세가 dense-master 2:4보다 악화되지 않음
- topology age가 최소 warm-up 기간 이상

freeze 이후에는:

- topology search 없음
- resurrection 없음
- inactive state 없음
- sparse optimizer state만 유지

한다.

### 5.3 반드시 기록할 topology 지표

기존 연구가 충분히 보고하지 않은 TinyLM 전용 계측으로 다음을 저장한다.

#### 전체 지표

\[
r_t=\frac{\|m_t\oplus m_{t-1}\|_1}{D}
\]

- `flip_rate`
- `0→1 resurrection rate`
- `1→0 death rate`
- layer별 flip rate
- MLP projection별 flip rate

#### weight-level lifetime 통계

각 weight position에 대해:

- 최초 active step
- 최초 death step
- resurrection 횟수
- death 횟수
- 총 active duration
- longest active streak
- longest inactive streak
- 마지막 resurrection step
- 마지막 topology change step

을 기록한다.

최종적으로:

```text
P(resurrection_count = 0)
P(resurrection_count = 1)
P(resurrection_count = 2~4)
P(resurrection_count >= 5)
max resurrection_count
```

를 낸다.

#### churn의 가치

각 refresh마다 새로 살아난 weight가 이후:

- 다음 refresh까지 생존했는가
- 5회 이상 refresh를 생존했는가
- 다시 바로 제거됐는가

를 측정한다.

이를 통해 **“실제로 유용한 topology exploration인지 단순 oscillation인지”​**를 구분한다.

### 5.4 외부 근거

#### [R1] Zhou et al., 2021 — SR-STE

**Aojun Zhou et al., _Learning N:M Fine-grained Structured Sparse Neural Networks From Scratch_.**

- N:M sparse network를 initialization부터 학습.
- SR-STE 제안.
- Sparse Architecture Divergence로 topology 변화를 계측.
- NVIDIA 2:4의 hardware-oriented training 가능성을 제시.

DOI: `10.48550/arXiv.2102.04010`

이 실험에서는 **dense-master 2:4 기준선**의 직접 선행연구로 사용한다.

#### [R2] Hu et al., ICML 2024

**Yuezhou Hu et al., _Accelerating Transformer Pre-training with 2:4 Sparsity_.**

- Transformer FFN에 2:4 pretraining 적용.
- flip rate를 명시적으로 정의.
- mask oscillation이 optimization을 해치는 것을 분석.
- transposable 2:4 mask 및 sparse kernel 최적화.
- 실제 transformer pretraining wall-clock 가속을 보고.

DOI: `10.48550/arXiv.2404.01847`

TinyLM에서는 **flip-rate 정의와 실제 wall-clock 계측법의 핵심 기준**으로 사용한다.

#### [R3] Hu, Zhu & Chen, NeurIPS 2024 — S-STE

**Yuezhou Hu, Jun Zhu, Jianfei Chen, _S-STE: Continuous Pruning Function for Efficient 2:4 Sparse Pre-training_.**

- hard-thresholding의 discontinuity 문제 분석.
- incorrect descent direction
- descent 크기 예측 실패
- sparse-mask oscillation

을 분리.
- continuous sparse projection으로 이를 완화.

DOI: `10.52202/079017-1063`

TinyLM에서 dense-master 2:4가 불안정할 경우 **hard top-2와 continuous projection을 구분할 근거**다.

#### [R4] Evci et al., ICML 2020 — RigL

**Utku Evci et al., _Rigging the Lottery: Making All Tickets Winners_.**

- 학습 전 과정에서 sparse parameter count 유지.
- 작은 magnitude weight를 제거.
- inactive 후보에 대한 gradient 신호를 이용해 새로운 connection을 생성.
- topology update 빈도를 제한.
- static sparse topology보다 dynamic topology가 유리할 수 있음을 보임.

DOI: `10.48550/arXiv.1911.11134`

이번 제안의 **dynamic prune-and-regrow 구조 및 churn annealing**의 주요 선행근거다.

#### [R5] Jayakumar et al., 2021 — Top-KAST

**Siddhant M. Jayakumar et al., _Top-KAST: Top-K Always Sparse Training_.**

- forward와 backward 모두 constant sparsity를 유지.
- dense parameter/gradient materialization을 피하려는 sparse training.
- language modeling에도 적용.
- topology exploration이 학습 전 기간에 동일한 가치가 있지 않음을 분석할 수 있는 구조를 제공.

DOI: `10.48550/arXiv.2106.03517`

TinyLM의 **sparse-master 및 early topology-freeze 가설**에 직접 관련된다.

#### [R6] Lyu et al., CPAL 2026 — CHTs24

**Jiaqing Lyu et al., _Cannistraci-Hebb Training with N:M Semi-Structured Sparsity for Pre-Training and Re-Training_.**

- 기존 N:M sparse training이 dense weight + STE를 유지한다는 문제를 직접 지적.
- **CHTs24**로 2:4 semi-structured sparsity와 dynamic sparse-to-sparse training을 결합.
- LLM linear layer pretraining에서 SR-STE 대비 경쟁력 있는 결과를 보고.
- inactive dense master를 반드시 유지해야 한다는 전제를 제거.

웹 논문 페이지: PMLR Volume 328, paper `lyu26a`.

이 논문이 이번 제안에서 **true sparse-master 2:4의 가장 직접적인 선행연구**다.

### 5.5 이 연구에서 새로 확인하려는 부분

선행연구와 겹치지 않는 TinyLM의 핵심 질문은 다음이다.

1. **ternary + 2:4**가 dense/full-precision 2:4와 같은 topology dynamics를 보이는가?
2. 한 weight가 실제로 몇 번 resurrection하는가?
3. resurrection 대부분이 초기에 끝나는가?
4. 높은 churn을 유지하는 것이 품질에 실제로 필요한가?
5. topology를 조기 freeze해도 되는가?
6. freeze 후 sparse master와 optimizer state 제거가 TinyLM처럼 작은 모델에서도 실제 wall-clock 이득을 내는가?
7. 기존 3:4 ternary 압축보다 2:4 sparse-training의 장점이 품질 손실을 정당화하는가?

---

## 6. 방법

### 원칙

**값싼 kernel/계측 검증 → 짧은 학습 → 100M screening → 300M 본런** 순서로 진행한다.

단계가 통과되지 않으면 다음 단계로 가지 않는다.

| 단계 | 무엇 | 비용 | ★다음으로 가는 조건 |
|---|---|---:|---|
| **0A** | 현재 GPU에서 TinyLM MLP shape의 2:4 sparse GEMM 지원 여부 확인 | ⚙0.1h | 실제 sparse kernel 실행 성공 |
| **0B** | forward/backward microbenchmark: dense vs 2:4 | ⚙0.2h | MLP kernel ≥1.25× 또는 전체 적용 시 ≥1.10× 가능성이 실측으로 보임 |
| **1A** | dense-master 2:4 correctness + 250-step probe | ⚙0.25h | NaN 없음, 2:4 invariant 100%, dense 대비 loss divergence 비정상 없음 |
| **1B** | topology telemetry 추가 | ⚙0.25h | flip/resurrection/death conservation 검증 |
| **1C** | sparse-master 2:4 250-step probe | ⚙0.3h | optimizer/state accounting 검증, 2:4 invariant 100% |
| **2** | 100M-token 4-arm screening | ⚙2.5h | 최소 한 sparse-master 방식이 dense-master 2:4와 품질 차이가 다음 단계 가치가 있음 |
| **3A** | 300M dense-control + dense-master 2:4 + sparse-master dynamic | ⚙6h | full-val/paired 결과 확보 |
| **3B** | churn-annealed + adaptive-freeze 본런 | ⚙2~4h | 단계 3A에서 sparse-master가 탈락하지 않았을 때만 |
| **4** | seed 또는 재생성 확인 | ⚙3~5h | 결과가 조건별 분해능 근처일 때만 |

### 단계 0 — 속도 가능성부터 닫는다

현재 TinyLM TLinear은 **mask에 0을 넣는 것만으로는 sparse GEMM이 되지 않는다.**

따라서 가장 먼저:

```text
768 × 2048
2048 × 768
및 실제 현행 preset의 MLP shape
```

에서 사용 GPU가 native 2:4 연산을 실제로 수행하는지 확인한다.

측정:

- dense GEMM forward
- 2:4 GEMM forward
- dense backward-input
- sparse backward-input
- backward-weight
- 전체 TLinear forward+backward
- compile 유무

#### 속도 게이트

다른 날 수치를 비교하지 않는다.

같은 프로세스 또는 동일 세션 내에서:

1. warm-up
2. A/B alternating measurement
3. median
4. p10/p90
5. CUDA synchronize

를 사용한다.

**2:4 kernel이 실질적으로 빠르지 않으면 학습가속 목적의 단계 3은 중단한다.**

다만 sparse-master의 VRAM 연구는 별도 가치가 있으므로 메모리 축만 계속할지는 그 시점에 다시 제안한다.

### 단계 1 — correctness와 계측

#### 1A. Dense-master 2:4

기존:

```text
--sparse34
```

를 직접 변경하지 않고, 호환성을 유지한 새 generic N:M 경로를 설계한다.

예:

```text
sparse_nm = None | (3,4) | (2,4)
```

단, 실제 CLI·config 이름은 승인 후 test plan에서 저장소 naming 규칙과 충돌 여부를 검사한 뒤 확정한다.

기존 `sparse34` 결과는 bit-equivalence regression으로 보존한다.

#### 1B. topology logger

매 topology update마다:

```text
layer
projection
step
flip_rate
resurrected
removed
mean_age_active
median_age_active
max_resurrection_count
```

를 기록한다.

모든 2:4 block에서:

\[
\sum m = 2
\]

인지 assert한다.

또한 dynamic 2:4에서는 항상:

\[
N_{0\rightarrow1}=N_{1\rightarrow0}
\]

이어야 한다.

위 conservation이 깨지면 실험을 중단한다.

#### 1C. Sparse-master

CHTs24 방향을 기준으로 한다.

필수 조건:

- inactive value 자체를 persistent trainable parameter로 두지 않는다.
- inactive AdamW \(m,v\) state도 상주시키지 않는다.
- topology refresh 시 새 active parameter의 initialization rule을 로그에 남긴다.
- optimizer state reset/transfer 정책을 명시한다.

### 단계 2 — 100M screening

최소 네 팔:

| 팔 | topology | master | refresh |
|---|---|---|---|
| **D** | dense | dense | 없음 |
| **S1** | dynamic 2:4 | dense | magnitude/STE |
| **S2** | static 2:4 | sparse | 없음 |
| **S3** | dynamic 2:4 | sparse | CHTs24-inspired |

목적:

\[
\text{dynamic topology의 가치}
\]

와

\[
\text{dense master의 가치}
\]

를 분리하는 것이다.

#### 판정

S3가 S2보다 개선되지 않으면:

> topology exploration 자체의 가치가 TinyLM에서는 검출되지 않음

으로 판단하고 churn schedule 실험을 중단한다.

S1 ≫ S3이면:

> inactive latent optimization이 중요한 가능성

으로 판단한다.

S3 ≈ S1이면:

> dense master 없이도 topology search 가능

이라는 핵심 가설이 살아남는다.

### 단계 3 — 300M 본런

100M에서 살아남은 팔만 실행한다.

공통조건은 실행 당시의 **현재 표준조건**을 따른다.

원칙:

- 동일 corpus
- 동일 pool
- 동일 token budget
- 동일 seed
- 동일 schedule
- 동일 optimizer 조건
- 동일 eval
- sparse axis 외 한 번에 하나만 변경

한다.

현재 표준조건과 다르면 반드시 “왜”를 결과문서에 적는다.

### 단계 3B — topology annealing/freeze

동적 sparse-master가 통과한 경우만 진행한다.

비교:

```text
dynamic-full
dynamic-cosine-decay
adaptive-freeze
```

를 둔다.

#### adaptive freeze의 사전등록 후보

예:

```text
EMA flip_rate < 0.5%
AND
3 consecutive topology refreshes
AND
validation slope deterioration 없음
```

이면 topology freeze.

단, threshold는 test plan에서 **본런 결과를 보기 전에 고정**한다.

### 단계 4 — 결과 판정

#### 품질

- `paired_eval`
- full validation
- condition-specific resolution
- exact Δ
- 통계적 유의성과 실무상 동급을 구분

한다.

#### 속도

반드시 같은 세션의 대조군과 비교한다.

보고:

```text
tokens/s
ms/step
forward ms
backward ms
optimizer ms
topology-update amortized ms
```

#### 메모리

최소:

```text
parameter
gradient
optimizer m
optimizer v
topology metadata
temporary dense buffer
CUDA allocated
CUDA reserved
peak allocated
```

로 분해한다.

특히 sparse-master라고 부르면서 hidden dense temporary가 존재하는 경우 이를 숨기지 않는다.

### 최종 성공 기준

아래 세 조건을 모두 만족한 팔만 “학습 레버 후보”로 올린다.

1. **품질**  
   dense 또는 dense-master 2:4 대비 Δ가 현재 프로젝트의 사전 고정 판정선 안.

2. **실제 효율**  
   다음 중 하나 이상:
   - end-to-end step ≥ **1.10×**
   - peak training VRAM ≥ **10% 감소**
   - optimizer+parameter state ≥ **25% 감소**

3. **재현성**  
   seed/재생성 확인에서 방향이 유지.

속도 이득 없이 저장 크기만 감소하면:

> **학습 가속 레버가 아니라 메모리 레버**

로 분류한다.

---

## 7. 거절하면 못 하는 것

이 제안을 거절해도 기존 TinyLM 연구는 계속할 수 있다.

따라서 **핵심 프로젝트 진행이 막히지는 않는다.**

못 하게 되는 것은 다음 질문에 대한 답이다.

- dense latent weight가 실제로 끝까지 필요한가?
- inactive weight resurrection이 TinyLM에서도 중요한가?
- topology exploration은 언제 끝나는가?
- 2:4가 TinyLM pretraining의 실제 GPU 속도를 올릴 수 있는가?
- sparse optimizer state가 training VRAM을 의미 있게 줄이는가?

현재 COMPASS 기준으로 더 직접적인 열린 축들이 이미 있으므로 이 실험이 반드시 최우선이어야 하는 것은 아니다.

다만 기존 `sparse34` 코드가 있고 ternary weight 경로가 이미 분리되어 있기 때문에 **다른 저장소보다 구현 진입점이 명확한 편**이라는 장점이 있다.

---

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| **가장 큰 위험: 0을 넣었지만 실제 sparse kernel이 아님** | FLOPs 계산은 줄었는데 ms/step 동일 | 단계 0에서 native kernel 여부를 먼저 실측 |
| TinyLM 크기가 너무 작아 kernel overhead가 이득을 먹음 | GEMM은 빠르나 end-to-end 무이득 | block + whole-step 둘 다 측정 |
| ternary와 2:4의 이중 제약으로 품질 급락 | S1부터 val 악화 | dense-master 2:4를 먼저 대조군으로 둠 |
| topology churn이 심함 | flip rate가 후반에도 높음 | churn annealing / S-STE 계열 대안 |
| sparse-master가 dense temporary를 내부적으로 생성 | peak VRAM이 줄지 않음 | allocation profiler와 temporary buffer 회계 |
| optimizer가 hidden dense state를 유지 | parameter는 sparse인데 Adam state 동일 | optimizer state byte 직접 합산 |
| 새로 살아난 weight가 optimizer history가 없어 불안정 | refresh 직후 loss spike 반복 | initialization/state-ramp ablation |
| Muon과 dynamic support가 충돌 | update가 inactive 위치에 생김 | 1차는 현행 표준 optimizer 조건을 그대로 쓰되 active-support projection을 별도 검증; 필요 시 후속 제안 |
| compile graph가 topology refresh마다 깨짐 | recompilation / step spike | mask metadata와 weight storage 변경의 graph 영향 profile |
| topology logger 자체가 느림 | instrumented run만 느려짐 | 본런에서는 histogram/counter만 GPU-side 또는 저주기 수집 |
| 다른 날 속도 비교 교락 | 세션간 ±수% 차이 | 반드시 paired same-session benchmark |
| 기존 3:4 결과와 조건이 다름 | 옛 KD 수치와 새 무KD 수치 혼용 | 기존 수치는 배경으로만 사용, 판정은 새 대조군 |
| static 2:4가 우연히 좋은 seed를 얻음 | 한 seed에서만 동급 | 필요할 때 seed/재생성 단계 실행 |
| sparse master 구현 비용이 이득보다 큼 | engineering 비용 증가 | 250-step 단계에서 조기 중단 |
| “50% sparsity = 50% 전체 속도 향상” 오해 | 예상과 실제 차이 | FFN / 전체 step Amdahl 회계 분리 |

### 계측 위험 — 필수 경고

이 실험에서 가장 위험한 오판은:

> **logical sparsity를 hardware sparsity로 착각하는 것**

이다.

다음 세 값을 반드시 따로 적는다.

1. logical zero ratio
2. 실제 저장 byte
3. 실제 kernel wall-clock

셋 중 하나만 줄었다고 나머지도 줄었다고 쓰지 않는다.

---

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | **2:4 dense-master → sparse-master → churn annealing → adaptive freeze의 단계적 실험** | 품질·속도·VRAM·topology 원인을 분리 가능. 실패 지점을 정확히 앎 | 구현량이 가장 큼 |
| **B** | 기존 `sparse34`를 단순 2:4로 바꾸고 dense master 유지 | 가장 빠르게 품질 확인 가능 | master/optimizer memory 질문에 답하지 못함. 선행연구 반복성이 큼 |
| **C** | sparse-master 2:4만 바로 구현 | 연구 질문은 명확 | 실패 시 2:4 자체가 나쁜지 sparse-master가 나쁜지 구분 불가 |
| **D** | 한번 죽은 weight를 영구 제거하는 monotonic pruning | 구현 단순, master가 점차 줄어듦 | 초기 오판 복구 불가. topology exploration 효과를 버림 |
| **E** | unstructured RigL형 sparsity | 높은 sparsity까지 탐색 가능 | TinyLM GPU 실제 가속과 직접 연결하기 어려움 |
| **F** | 3:4 sparse-master만 연구 | 기존 TinyLM 표현과 직접 연결 | 25% sparsity라 training speed ceiling이 작고 현 COMPASS에서 3:4 축의 우선순위가 낮음 |
| **G** | 아무것도 안 한다 | 비용 0 | dense master와 topology dynamics 질문은 열린 채 유지 |

### ★권장안과 근거

**A를 권장한다.**

핵심 이유는 이번 연구에서 가장 중요한 것은 2:4라는 숫자가 아니라 다음 세 효과를 분리하는 것이기 때문이다.

\[
\text{2:4 constraint}
\]

\[
\text{dynamic topology}
\]

\[
\text{dense master 제거}
\]

이를 한 번에 도입하면 품질이 나빠졌을 때 원인을 알 수 없다.

따라서:

```text
dense
  ↓
dense-master dynamic 2:4
  ↓
sparse-master static 2:4
  ↓
sparse-master dynamic 2:4
  ↓
churn annealing
  ↓
adaptive freeze
```

순서가 가장 정보 효율적이다.

특히 단계 0의 sparse-kernel microbenchmark를 **첫 게이트**로 두는 것이 중요하다.

TinyLM의 목적은 논리적 FLOPs를 줄였다고 주장하는 것이 아니라 실제 저사양·저메모리 시스템에서 유효한 설계를 찾는 것이므로, native 2:4 실행이 현재 shape에서 실질적인 시간을 절약하지 못하면 대형 본런으로 넘어갈 이유가 없다.

---

## 참고문헌

1. Zhou, A. et al. **Learning N:M Fine-grained Structured Sparse Neural Networks From Scratch.** 2021.  
   DOI: `10.48550/arXiv.2102.04010`

2. Hu, Y., Zhao, K., Huang, W., Chen, J., Zhu, J. **Accelerating Transformer Pre-training with 2:4 Sparsity.** ICML 2024, PMLR 235:19531–19543.  
   DOI: `10.48550/arXiv.2404.01847`

3. Hu, Y., Zhu, J., Chen, J. **S-STE: Continuous Pruning Function for Efficient 2:4 Sparse Pre-training.** NeurIPS 2024.  
   DOI: `10.52202/079017-1063`

4. Evci, U., Gale, T., Menick, J., Castro, P. S., Elsen, E. **Rigging the Lottery: Making All Tickets Winners.** ICML 2020.  
   DOI: `10.48550/arXiv.1911.11134`

5. Jayakumar, S. M., Pascanu, R., Rae, J. W., Osindero, S., Elsen, E. **Top-KAST: Top-K Always Sparse Training.** 2021.  
   DOI: `10.48550/arXiv.2106.03517`

6. Lyu, J., Wang, R., Bao, K., Zhang, Y., Cannistraci, C. V. **Cannistraci-Hebb Training with N:M Semi-Structured Sparsity for Pre-Training and Re-Training.** Conference on Parsimony and Learning, PMLR 328:192–217, 2026.  
   Web: PMLR Volume 328, paper `lyu26a`.

---

## 승인 후에만 할 일

승인되면 저장소 규약에 따라 이 제안서를 바로 구현하지 않고 먼저:

1. `test_plan/`의 다음 P번호 확인
2. `docs/EXPERIMENT_BASELINES.md`와 중복/조건충돌 검사
3. `exp-preflight` 수행
4. 단계별 사전 판정선을 고정한 test plan 작성
5. 정적 게이트 통과
6. 그 뒤에만 배치와 코드 변경

순으로 진행한다.

승인 전에는 코드·배치·학습 조건을 변경하지 않는다.