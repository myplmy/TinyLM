# 제안 — FP8 compute와 shadow precision을 분리하고 format·scaling·write-back을 단계적으로 연다

> **작성** 2026-09-11 · **상태** ⏳판단 대기 · **분류** 실험계획  
> 양식: `proposal/README.md` §3. 아홉 절을 비우지 않는다.  
> **제안 파일명** `proposal/20260911_FP8-compute와-shadow-precision을-분리해-연다.md`
>
> 🚫 승인 전에는 코드 구현, batch 생성, `test_plan/` 번호 할당을 하지 않는다.
>
> 현재 확인상 실험 번호는 **P089까지 사용 중**이다. 다음 번호를 이 제안서에서 예약하지 않는다.  
> 승인 시 `실험계획목록.md`와 `experiments.tsv`를 다시 확인한 뒤 번호를 배정한다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

현재 TinyLM의 ternary 학습에는 서로 다른 정밀도 축이 최소 세 개 존재한다.

| 축 | 현재 상태 | 의미 |
|---|---|---|
| latent/shadow weight | `TLinear.weight` 연속 `nn.Parameter` | optimizer가 실제로 갱신하는 잠재 weight |
| ternary forward weight `_wq` | `--wq-dtype`으로 저장 dtype 변경 가능 | ternary 변환 후 `F.linear`에 들어가는 weight |
| optimizer state | `--opt-dtype`으로 FP32/BF16 선택 가능 | AdamW moment 저장 정밀도 |

현재 `tinylm/model/ternary.py`의 `TLinear.weight`에는 **shadow precision 자체를 FP8 lattice로 제한하는 축이 없다.**

또한 현재 `--wq-dtype`은 shadow precision이 아니다.

현재 코드에서 `ternary()`는 고정밀 latent weight를 받아 계산되고, 이후 생성된 `_wq`의 **저장 dtype만** `bf16/fp16`으로 낮춘다. 코드 주석도 `_wq` 저장 dtype만 바뀌고 ternary 계산 자체는 FP32라고 명시한다.

따라서 다음은 서로 다른 질문이다.

\[
\text{A. FP8 GEMM을 사용해 실제 학습 compute를 빠르게 할 수 있는가?}
\]

\[
\text{B. optimizer가 누적하는 latent/shadow weight 자체를 FP8 grid에 제한해도 학습되는가?}
\]

이 둘을 한 번에 변경하면 품질 변화가

- FP8 GEMM의 activation/weight/gradient quantization 때문인지,
- shadow/master weight의 낮은 누적 정밀도 때문인지,
- E4M3/E5M2 차이 때문인지,
- scaling policy 때문인지,
- rounding/write-back 때문인지

구분되지 않는다.

따라서 본 제안은 **compute precision과 shadow precision을 직교 축으로 분리한다.**

### 1.1 본 실험에서 사용할 내부 기준선

저장소 전체의 “표준모델”과 혼동하지 않도록, 여기서는 **본 실험의 tied 기준선**이라고 부른다.

본 실험 기준 후보:

- preset 계열: `m100R1c`
- 부모초기화: `--init-from`
- KD 없음
- `--no-ckpt`
- AdamW
- 기존 FP32 latent/shadow
- 기존 `wq_dtype`
- 기존 optimizer-state dtype

관련 현재 실측:

| 항목 | 값 |
|---|---:|
| `mC_initonly_nc` full-val | **3.6762** |
| `mC_initonly_nc` 학습속도 | **2.485 s/step** |
| tied 무KD·부모초기화·`--no-ckpt` σ | **0.0005** |
| 해당 계열 현재 2σ | **0.0010** |

따라서 이 proposal에서 `2σ=0.0010`을 사용할 때는 **이 tied 계열 안에서만** 사용한다.

다른 architecture/optimizer/초기화 계열로 옮겨가며 같은 자를 자동 재사용하지 않는다.

### 1.2 현재 `_wq` 축과 shadow 축은 다르다

현재 `--wq-dtype bf16/fp16`은 `_wq` 저장과 autocast 비용을 줄이는 축이다.

그것은 다음을 뜻하지 않는다.

\[
TLinear.weight \in FP8
\]

또는

\[
optimizer\ update\ accumulation \in FP8
\]

즉 기존 P068류 `_wq` 실험과 본 proposal의 shadow/master precision 실험은 중복이 아니다.

### 1.3 외부 연구가 추가로 요구하는 변수

초기 제안에서는 shadow를 사실상

\[
\text{E4M3 vs E5M2}
\]

문제로 보았다.

그러나 선행연구를 반영하면 FP8 shadow quantizer는 최소 다음 네 항으로 정의해야 한다.

\[
Q(W;F,G,S,R)
\]

여기서

- \(F\): format — E4M3 / E5M2
- \(G\): scale granularity — tensor / row / group
- \(S\): scale policy — current amax / delayed/fixed / 기타
- \(R\): write-back rounding — RNE/RTN / stochastic rounding 등

이다.

따라서 **E4M3/E5M2만 바꾸고 scaling이나 rounding을 암묵적으로 두지 않는다.**

---

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

**현재 TinyLM의 다른 학습조건을 고정한 채, FP8 compute와 low-precision shadow accumulation을 분리해서 각각 실제 속도 이득과 품질 한계를 측정하고, shadow에서는 format보다 먼저 scaling·update visibility·write-back이 병목인지 판정한다.**

구체적으로 다음 다섯 질문에 순서대로 답한다.

1. Ada FP8 GEMM이 현재 TinyLM/TLinear에서 실제 hardware FP8 경로를 타며 기존 BF16/FP16 compute보다 빠른가?
2. Ada에서 가능한 per-tensor FP8 scaling 조건에서는 `E4M3 fwd + E5M2 bwd`와 `E4M3 all-way` 중 어느 쪽이 적합한가?
3. compute precision을 고정한 뒤 latent/shadow weight를 FP8 lattice에 직접 write-back하면 학습이 유지되는가?
4. shadow 실패의 주원인이 dynamic range인지, mantissa resolution인지, invisible update인지, rounding bias인지 구분할 수 있는가?
5. static FP8 shadow가 가능할 경우 학습 중 shadow precision schedule

\[
H\rightarrow L,\quad L\rightarrow H,\quad H\rightarrow L\rightarrow H
\]

가 static low precision보다 유리한가?

정의:

\[
H=\text{기존 FP32 latent/shadow}
\]

\[
L=\text{S1에서 실제로 검증된 low-precision shadow policy 전체}
\]

여기서 \(L\)은 단순히 “E4M3”이라는 dtype 이름이 아니다.

예:

\[
L=
(\text{E4M3},\ \text{row-scale},\ \text{current scale},\ \text{RNE})
\]

또는 필요하면

\[
L=
(\text{E4M3},\ \text{row-scale},\ \text{current scale},\ \text{SR})
\]

처럼 **완전한 quantization/write-back policy**로 정의한다.

---

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| FP8 hardware 경로 판정 | profiler에서 실제 FP8 GEMM kernel 사용 여부 |
| Ada FP8 scaling 가격표 | Current vs Delayed scaling의 ms/step 및 overhead |
| FP8 compute 가격표 | BF16 기준 대비 ms/step, tokens/s, peak VRAM |
| FP8 compute 품질 가격표 | HYBRID vs E4M3-all의 paired full-val |
| shadow precision 가격표 | FP32 / FP16 sentinel / E4M3 / 조건부 E5M2 |
| update-visibility 진단 | exact frozen-update fraction, ULP margin, update distortion |
| ternary-specific 진단 | ternary transition precision/recall/F1, state disagreement |
| rounding 진단 | RNE 직접 write-back 실패 시 SR rescue 여부 |
| shadow schedule 가격표 | static L / H→L / L→H / H→L→H |
| 최종 판정 | 기존 경로 유지 / FP8 compute 채택 / FP8 shadow 연구 지속 여부 |
| 후속 구현 근거 | 실제 packed/masterless FP8 또는 error-feedback optimizer를 만들 가치가 있는지 판정 |

승인 시에만 다음을 수행한다.

- `test_plan/`에 다음 사용 가능 번호로 정식 계획서 생성
- 필요한 FP8 backend/wrapper 구현
- `trainer.py` 연결
- shadow observer/fake-quant write-back 구현
- CLI/config 신규 flag 연결
- run JSON에 신규 축 기록
- `scripts/flag_whitelist.tsv` 갱신
- smoke 경로 추가
- 정적 게이트 전수 실행
- 실행 직전에만 batch 생성
- `experiments.tsv` 등록
- 실행 후 `results/` 결과문서 작성

🚫 proposal 승인만으로 기존 기본값을 바꾸지 않는다.

모든 신규 기능은

\[
\text{default off}=\text{기존 동작 유지}
\]

를 원칙으로 한다.

---

## 4. 비용

기준:

\[
mC\_initonly\_nc \approx 2.485\ {\rm s/step}
\]

이다.

100M:

\[
763\times2.485/3600\approx0.53\ {\rm GPU-h/arm}
\]

300M:

\[
2289\times2.485/3600\approx1.58\ {\rm GPU-h/arm}
\]

FP8에서는 실제 step time이 달라질 수 있으므로 아래는 전부 ⚙추정이다.

| 단계 | GPU 비용 |
|---|---:|
| C0 — backend/profiler feasibility | ⚙0.1 h |
| C1 — Current/Delayed FP8 speed probe | ⚙0.7~0.8 h |
| C2 — 100M FP8 compute format screen | ⚙1.1~1.6 h |
| C3 — 300M compute 최종 확인 | ⚙3.0~3.2 h |
| S0 — FP32 reference shadow observer | ⚙0.2 h |
| S1a — FP16/E4M3 static shadow screen | ⚙1.1~1.6 h |
| S1b — E5M2 또는 SR rescue | ⚙0~1.1 h, 조건부 |
| S2 — H/L schedule screen | ⚙2.1~2.7 h |
| S3 — schedule 승자 300M 확인 | ⚙1.6~3.2 h |
| 실제 packed/masterless FP8/ECO류 | 별도 승인 전 미산정 |

조건부 누적:

- C0 실패: **⚙0.1 h 종료**
- compute speed 판정까지: **⚙0.8~0.9 h**
- compute 100M screen까지: **⚙1.9~2.5 h**
- compute 300M 확인까지: **⚙4.9~5.7 h**
- static shadow screen까지: **⚙6.2~7.5 h**
- rounding rescue까지 필요하면: **⚙6.7~8.6 h**
- schedule screen까지: **⚙8.8~11.3 h**
- 최종 300M shadow 확인까지: **⚙10.4~14.5 h**

모든 단계가 자동으로 열리는 것은 아니다.

앞 단계 gate가 실패하면 즉시 종료한다.

| 기타 비용 | 양 |
|---|---:|
| AI/코드 작업 | ⚙3~6 engineer-h 상당 |
| 사용자가 직접 해야 하는 일 | batch 실행·초기 실패 확인 약 ⚙15~30 min hands-on |
| 임시 디스크 | ⚙최대 5 GB, checkpoint 정책에 따라 변동 |

현재 실험 큐를 선점하지 않는다.

승인 후 큐와 실험 번호를 다시 확인한다.

---

## 5. 원리·근거

### 5.1 우리 실측

| 근거 | 값 | 출처 |
|---|---:|---|
| tied control | `mC_initonly_nc` full-val **3.6762** | `docs/EXPERIMENT_BASELINES.md` B.7.1 |
| tied control speed | **2485 ms/step** | 동 |
| tied 무KD ruler | **2σ=0.0010** | B.9.1 |
| `_wq` dtype 의미 | 저장 dtype만 변경, `ternary()` 계산은 FP32 | `tinylm/model/ternary.py` |
| 현재 실험 번호 | P089 사용 중 | `experiments.tsv` |

### 5.2 외부 근거 — 조회 범위와 이 제안에 쓰는 부분

| ID | 연구/문서 | 조회 범위 | 이 proposal에 쓰는 근거 |
|---|---|---|---|
| R1 | Micikevicius et al., **FP8 Formats for Deep Learning**, arXiv:2209.05433 | arXiv abstract | E4M3/E5M2 표준 FP8 조합, 대규모 LM까지 FP8 training |
| R2 | Sun et al., **Hybrid 8-bit Floating Point Training and Inference**, NeurIPS 2019 | NeurIPS abstract | forward/backward가 동일 precision 요구를 갖지 않음 |
| R3 | Noune et al., **8-bit Numerical Formats for Deep Neural Networks**, arXiv:2206.02915 | abstract/indexed text | exponent/mantissa bit 및 exponent bias가 실제 training 결과에 영향을 줌 |
| R4 | Kuzmin et al., **FP8 Quantization: The Power of the Exponent**, arXiv:2208.09225 | arXiv abstract | 최적 exponent allocation이 outlier와 분포에 의존, scale/exponent bits 학습 가능 |
| R5 | Mishra et al., **Recipes for Pre-training LLMs with MXFP8**, arXiv:2506.08027 | arXiv HTML §§3.2–3.3 | weights/activations에서 E4M3가 E5M2보다 우수, fine scaling에서는 gradient도 E4M3 가능 |
| R6 | Peng et al., **FP8-LM: Training FP8 Large Language Models**, arXiv:2310.18313 | arXiv HTML §§2.2, 3.3 | FP8 master weight는 열화, FP16+scaling master가 FP32와 가까움 |
| R7 | Nikdan et al., **ECO: Quantized Training without Full-Precision Master Weights**, arXiv:2601.22101 | arXiv HTML | naive direct FP8 write-back 실패 가능, error compensation/SR가 핵심 |
| R8 | Shang, **Reference Traces for Auditing Invisible Weight Updates and Guiding Exact-Budget Protection**, arXiv:2607.09800v3 | arXiv HTML | exact invisible-update event와 aggregate proxy를 구분, SR write-back 효과 |
| R9 | Zhao et al., **Direct Quantized Training of Language Models with Stochastic Rounding**, PMLR 304 | abstract | high-precision shadow 없이 저정밀 weight 직접 학습 가능성, SR 활용 |
| R10 | NVIDIA Transformer Engine 2.18.0 | 공식 문서 | Ada SM89+ Current Scaling, HYBRID/E4M3, scaling overhead와 device 지원 범위 |

### 5.3 FP8 compute와 FP8 shadow는 반드시 분리한다

FP8 Tensor Core 가속은 본질적으로

\[
A_{\rm FP8}W_{\rm FP8}
\]

형태의 GEMM이 실제 FP8 hardware kernel로 실행될 때 생긴다.

반면 shadow weight를 FP8 grid에 저장하는 것만으로 forward/backward GEMM이 자동으로 FP8이 되는 것은 아니다.

반대로 FP8 GEMM을 사용해도 master/shadow weight는 FP32일 수 있다.

Transformer Engine도 이 둘을 분리한다.

따라서:

\[
\boxed{\text{FP8 compute}}
\]

와

\[
\boxed{\text{low-precision shadow accumulation}}
\]

은 독립 실험으로 유지한다.

### 5.4 Ada에서 MXFP8 결과를 그대로 구현하지 않는다

R5의 MXFP8 결과는 중요하지만 hardware 조건을 구분해야 한다.

MXFP8은 32-element fine-grained scaling을 사용한다.

그 조건에서는 E4M3의 dynamic range만으로 충분해져, 추가 exponent bit보다 추가 mantissa bit가 유리해진다.

실제로 R5에서는 weights와 activations에서 E5M2가 E4M3보다 더 나쁜 perplexity를 만들었고, 8B에서는 gradients도 E4M3가 E5M2보다 유리했다.

그러나 현재 RTX 4070 Ti SUPER는 Ada다.

Transformer Engine 2.18 기준:

- FP8 Current Scaling: **Ada SM89+**
- Delayed/per-tensor FP8: Ada에서 사용 가능
- FP8 block scaling: **Hopper SM90+**
- native MXFP8: **Blackwell SM100+**

따라서:

\[
\boxed{\text{MXFP8 결과 = format 가설의 근거}}
\]

이지

\[
\boxed{\text{현재 GPU에서 그대로 사용할 backend}}
\]

는 아니다.

이 때문에 compute Track에서는 Ada의 coarse per-tensor scaling에서 먼저 공식 HYBRID를 기준으로 둔다.

### 5.5 Compute format의 1차 가설

Ada의 per-tensor scaling에서는 우선:

\[
C_{\rm hybrid}
=
E4M3_{\rm fwd}+E5M2_{\rm bwd}
\]

를 기준 FP8 recipe로 둔다.

E5M2는 mantissa precision을 하나 희생하는 대신 넓은 range를 갖는다.

per-tensor scaling처럼 한 tensor 전체가 같은 scale을 공유하면 gradient outlier 때문에 E5M2의 range가 실제로 필요할 수 있다.

반면:

\[
C_{\rm e4}
=
E4M3_{\rm fwd}+E4M3_{\rm bwd}
\]

도 직접 비교한다.

단, R5의 결과만 보고 C_e4가 당연히 이긴다고 가정하지 않는다.

R5의 결과에는 **fine-grained scaling**이라는 중요한 조건이 있기 때문이다.

### 5.6 Shadow에서는 format보다 scaling과 mantissa resolution이 중요할 수 있다

shadow weight는 큰 값을 표현하는 용도만 갖지 않는다.

optimizer가 매 step 내는 작은 update

\[
W_t\rightarrow W_t+\Delta W_t
\]

를 누적해야 한다.

따라서 shadow는

- range
- relative ULP
- mantissa resolution
- scale granularity
- rounding

에 동시에 민감하다.

R6 FP8-LM에서는 master weight가 precision-sensitive했고:

- FP32 master: 안정
- FP16 + tensor scaling: FP32에 가까움
- BF16: FP16-scaled보다 조금 나쁨
- FP8 master: 성능 열화

가 관찰됐다.

따라서 본 proposal은 처음부터

\[
E4M3_{\rm shadow}>E5M2_{\rm shadow}
\]

를 결과로 가정하지 않는다.

대신 다음 hypothesis를 둔다.

**H1**

shadow 내부 dynamic range가 scaling으로 충분히 커버된다면,

\[
E4M3>E5M2
\]

일 가능성이 높다.

**H2**

row/group 안의 dynamic range나 outlier가 심해 E4M3에서 underflow/saturation이 많다면 E5M2가 일부 구간에서 유리할 수 있다.

**H3**

두 형식 모두 RNE direct write-back에서 update visibility가 부족하면 format 선택보다 rounding/master accumulation 문제가 더 크다.

### 5.7 custom exponent bias와 scale을 중복 독립변수로 세지 않는다

R3/R4는 exponent bias 및 representable range 조절이 중요함을 보여준다.

하지만 arbitrary scale factor를 허용하는 FP8 quantizer에서는 exponent bias shift와 tensor scaling이 상당 부분 같은 역할을 한다.

즉

\[
x\rightarrow Q_{E4M3}(x/s)\cdot s
\]

에서 \(s\)를 자유롭게 조절할 수 있다면, 별도의 “custom BF8 exponent bias”를 처음부터 또 하나의 독립축으로 넣는 것은 중복될 수 있다.

따라서 1차 실험에서는 custom hardware-incompatible BF8 dtype을 만들지 않는다.

먼저:

- E4M3/E5M2
- scale granularity
- scale policy

로 관측한다.

그 결과 기존 E4M3/E5M2 어느 쪽도 적절한 range-resolution 절충을 만들지 못한다는 근거가 생겼을 때만 custom shifted format을 별도 proposal로 연다.

### 5.8 shadow의 primary diagnostic은 ordinary reconstruction error가 아니다

ternary 모델에서 최종 forward state는

\[
T(W)
\]

로 결정된다.

따라서 단순

\[
\|Q(W)-W\|
\]

만 보는 것은 부족하다.

FP8 error가 커도 ternary state가 그대로면 영향이 작을 수 있고, 반대로 작은 FP8 error가 threshold 근처에서 ternary state를 바꿀 수 있다.

따라서 shadow 진단은 다음 순서로 둔다.

#### A. exact invisible-update fraction

저장된 low-precision code를 \(q_t\), optimizer proposal을 \(\Delta W_t\)라 하면:

\[
D_f=
P\left[
Q_f(q_t+\Delta W_t)=q_t
\right]
\]

를 센다.

이는 단순히 gradient가 작은지가 아니라 **실제 write-back 뒤 code가 움직였는지**를 센다.

#### B. ULP visibility margin

각 coordinate에 대해

\[
R_i=
\frac{|\Delta W_i|}
{\frac12{\rm ULP}(q_i)+\epsilon}
\]

를 계산한다.

- \(R_i<1\): RNE에서 update가 사라질 위험
- \(R_i\gg1\): grid를 넘을 만큼 충분한 update

분포를 layer/time별로 기록한다.

#### C. quantized update distortion

\[
\Delta Q_t
=
Q(W_t+\Delta W_t)-Q(W_t)
\]

에 대해

\[
E_{\rm upd}
=
\frac{\|\Delta Q_t-\Delta W_t\|_F}
{\|\Delta W_t\|_F+\epsilon}
\]

를 기록한다.

#### D. update direction cosine

\[
C_{\rm upd}
=
\frac{
\langle\Delta Q_t,\Delta W_t\rangle
}{
\|\Delta Q_t\|\,\|\Delta W_t\|+\epsilon
}
\]

를 기록한다.

기존의 단순 norm preservation ratio는 quantization jump가 커지면 1보다 커져도 “좋아진 것”처럼 보일 수 있으므로 primary 지표로 쓰지 않는다.

#### E. ternary state disagreement

\[
P[T(Q(W_t))\neq T(W_t)]
\]

를 센다.

#### F. ternary transition precision / recall / F1

고정밀 shadow에서 step \(t\rightarrow t+1\) 사이 일어난 ternary transition을 reference로 한다.

FP8 shadow transition에 대해 TP/FP/FN을 정의해:

- recall
- precision
- F1

을 모두 기록한다.

🚫 recall만 쓰지 않는다.

불필요한 transition을 많이 만들면 recall만 높아질 수 있기 때문이다.

#### G. range diagnostics

- saturation rate
- zero/underflow rate
- subnormal rate
- scale
- amax
- per-row 또는 per-group dynamic-range ratio

를 함께 기록한다.

### 5.9 stochastic rounding은 처음부터 기본값으로 섞지 않는다

R7/R8/R9는 stochastic rounding이 direct low-precision accumulation에서 중요할 수 있음을 보여준다.

그러나 처음부터 SR을 켜면:

> “FP8 grid 자체가 충분한가?”

와

> “SR이 부족한 update accumulation을 구조적으로 보완했는가?”

를 분리하기 어렵다.

따라서 순서는:

1. deterministic RNE/RTN direct write-back
2. failure signature 확인
3. invisible-update가 주원인이면 SR rescue

로 둔다.

SR까지 실패하면 error-feedback/ECO류는 새 optimizer 동작이므로 별도 단계로 분리한다.

### 5.10 H/L schedule 가설

학습 후기로 갈수록 learning-rate decay와 함께 optimizer proposal이 작아지는 경향이 있다.

따라서 deterministic low-precision accumulation에서는 후기일수록

\[
|\Delta W|<\frac12{\rm ULP}(W)
\]

구간이 늘 수 있다.

이에 따른 사전 가설은:

- **H→L**: 가장 위험. 후기 fine update를 low precision으로 보내기 때문
- **L→H**: 후기 수렴을 보호하므로 합리적
- **H→L→H**: 초기 trajectory와 후기 fine convergence를 모두 보호하므로 가장 보수적

이다.

따라서 현재 사전 예상은

\[
H\rightarrow L\rightarrow H
\]

또는

\[
L\rightarrow H
\]

가 H→L보다 유리할 가능성이 높다고 둔다.

단, 이는 판정이 아니라 hypothesis다.

---

## 6. 방법

# Track C — FP8 compute

Track C에서는 shadow precision을 기존 FP32로 고정한다.

optimizer도 AdamW로 고정한다.

현재 Muon 축은 별도 연구 중이므로 함께 변경하지 않는다.

FP8 정책이 정해진 뒤 Muon transfer는 별도 비교한다.

---

### C0 — FP8 backend feasibility

| 항목 | 내용 |
|---|---|
| 긴 학습 | 없음 |
| 모델 | 현재 TinyLM/TLinear |
| 비교 | 기존 BF16/autocast |
| 목적 | 실제 FP8 Tensor Core 경로가 가능한지 |
| 비용 | ⚙0.1 h |

현재 TLinear는 자기 parameter를 그대로 `Linear`에 넘기는 구조가 아니다.

latent weight에서 매 forward ternary `_wq`를 만들어 `F.linear`에 공급한다.

따라서 단순히 `te.Linear`로 교체하면 모델 의미가 바뀔 수 있다.

C0에서 확인:

1. `TLinear.weight` ownership 유지
2. ternary mapping 유지
3. STE backward 유지
4. `_wq` 의미 유지
5. 기존 `torch.compile` 조건 유지
6. 실제 FP8 GEMM kernel 실행
7. finite forward/backward
8. gradient 누락 없음
9. default-off 기존 경로 변화 없음
10. FP8 operand shape 제약 충족

현재 주요 768/2048 차원은 16의 배수여서 Transformer Engine FP8 Linear shape 요구와 기본적으로 정합하지만, 실제 ternary functional path에서 이를 별도 확인한다.

#### C0 gate

다음 중 하나라도 실패하면 compute Track 종료 또는 proposal 수정:

- 실제 FP8 GEMM kernel 미검출
- TLinear 의미를 바꿔야만 FP8 사용 가능
- STE가 달라짐
- graph break/quantization overhead가 심각
- NaN/Inf
- default-off regression

🚫 단순 `torch.float8_*` cast 성공을 hardware FP8 성공으로 쓰지 않는다.

---

### C1 — FP8 scaling recipe speed probe

Ada에서 실제 사용할 수 있는 per-tensor recipe부터 비교한다.

한 세션:

| Arm | compute | shadow |
|---|---|---|
| C-A | 기존 기준 | FP32 |
| C-B | FP8 HYBRID + Current Scaling | FP32 |
| C-C | FP8 HYBRID + Delayed Scaling | FP32 |
| C-A' | 기존 기준 재측정 | FP32 |

이 단계에서 E4M3/E5M2 format 효과와 scaling-policy 효과를 동시에 섞지 않는다.

Current Scaling은 매 quantization마다 amax를 구하므로 tensor read overhead가 크다.

TinyLM처럼 비교적 작은 모델에서는 이 overhead가 Tensor Core 이득을 상쇄할 가능성이 있으므로 Delayed Scaling도 같이 가격을 잰다.

고정:

- same preset
- same batch
- same seq
- same compile
- same shadow
- same `wq_dtype`
- same `opt_dtype`
- AdamW
- no KD
- same seed/data

측정:

- warmup 제외 median ms/step
- p10/p90
- tokens/s
- peak allocated/reserved VRAM
- compile time 별도
- FP8 GEMM kernel 호출 수/비율
- FP8 cast/amax kernel 시간
- graph break count

#### C1 gate

FP8 최선 arm이:

\[
\ge10\%
\]

속도 개선이면 C2 진행.

5~10%이면 다음 중 하나가 추가로 있어야 진행:

- VRAM 감소
- microbatch 증가 가능
- cast traffic 감소

<5%이고 메모리 이득도 없으면 compute Track 종료.

A와 A' 차이가 크면 session drift로 판정하고 재측정한다.

---

### C2 — 100M compute format screen

C1에서 고른 scaling recipe를 고정한다.

비교:

| Arm | FP8 format |
|---|---|
| C2-A | 기존 compute |
| C2-H | E4M3 fwd / E5M2 bwd |
| C2-E | E4M3 fwd / E4M3 bwd |

\[
763\ {\rm steps}\approx100M\ tokens
\]

목적:

- final equivalence 증명 아님
- coarse per-tensor Ada 조건에서 E4M3-all이 실제로 가능한지 판정
- R5 MXFP8 결과가 TinyLM/Ada coarse scaling으로 transfer되는지 확인

Gate:

- NaN/Inf 없음
- 비정상 loss spike 없음
- control 대비 full/paired 열화 +0.01 이내

둘 다 통과하면 품질이 더 좋은 arm을 우선한다.

차이가 noise 수준이면 더 빠른 arm을 고른다.

---

### C3 — 300M compute-only 최종 확인

두 arm:

| Arm | compute | shadow |
|---|---|---|
| C-FP | 기존 | FP32 |
| C-F8 | C1/C2 승자 | FP32 |

고정:

- 300M tokens
- seed 1337
- same pool/data order
- same initialization
- no KD
- AdamW
- same `wq_dtype`
- same optimizer-state dtype
- same checkpoint condition

본 tied 계열의 current ruler:

\[
2\sigma=0.0010
\]

따라서:

\[
\Delta{\rm full\mbox{-}val}\le+0.0010
\]

이면

> 현재 tied 기준선의 측정 분해능에서 regression을 검출하지 못함

으로 쓴다.

🚫 “완전히 동일” 또는 수학적 lossless라고 쓰지 않는다.

\[
\Delta>+0.0010
\]

이면 speed-quality tradeoff로 별도 기록한다.

---

# Track S — low-precision shadow

Track C와 독립적이다.

S Track compute는 하나로 고정:

- C가 성공했으면 검증된 FP8 compute
- C가 실패했으면 기존 compute

즉 compute 실패가 shadow 질문을 막지 않는다.

---

### S0 — observer-only reference diagnostic

실제 학습은 FP32 shadow로 그대로 수행한다.

optimizer가 제안한 update를 관측하여 가상 quantizer를 replay한다.

초기 observer 대상:

1. FP16 + scaling sentinel
2. E4M3
3. E5M2

FP8의 1차 공통 scaling policy는 동일하게 둔다.

권장 1차 정의:

- granularity: **row-wise**
- scale: current amax
- rounding: RNE
- scale metadata: FP32 simulation

이유:

- E4M3/E5M2 format만 공정하게 비교 가능
- R7 ECO의 row-wise FP8 baseline과 가까움
- tensor 하나 전체보다 outlier 영향을 줄임
- software observer 단계이므로 hardware 지원 여부와 분리 가능

필요하면 micro-group scaling은 sensitivity diagnostic으로만 추가한다.

측정:

- exact frozen-update fraction
- ULP visibility margin 분포
- update distortion
- update cosine
- saturation
- underflow/zero
- ternary state disagreement
- ternary-transition precision/recall/F1
- layer별/시점별 값
- scale와 within-group dynamic range

#### S0의 중요한 해석 규칙

`dead_update`가 높다고 그 layer가 “중요하다”고 쓰지 않는다.

update visibility와 downstream importance는 다른 질문이다.

S0는 **수치 failure mode를 분류하는 observer**다.

---

### S0 → S1 format gate

E4M3와 E5M2 비교:

#### E5M2를 S1 실제 학습 arm으로 열 조건

다음 중 하나를 만족해야 한다.

1. E4M3에서 의미 있는 underflow/zero가 있고 E5M2가 이를 명확히 줄임
2. E5M2가 ternary-transition F1을 지속적으로 개선
3. E5M2가 update distortion을 의미 있게 낮춤

단순히 E5M2의 theoretical range가 넓다는 이유로 arm을 만들지 않는다.

#### adaptive E4M3/E5M2 controller

1차 proposal에서는 기본적으로 **열지 않는다.**

다음 조건을 모두 만족할 때만 별도 subbranch를 고려한다.

- layer/time별 승자가 안정적으로 갈림
- 그 차이가 scaling artifact가 아님
- E5M2가 최소 10% 이상의 구간에서 지속적으로 우세
- ternary F1 또는 update distortion을 상대 20% 이상 개선
- format switching 자체가 추가 quantization error를 만들지 않음

즉 기존 안보다 adaptive-format 구현 우선순위를 낮춘다.

---

### S1a — static shadow causal screen

첫 구현은 packed FP8 storage가 아니라 fake quantization이다.

physical tensor는 기존 dtype에 두되 optimizer step 직후:

\[
W^{*}_{t+1}=W_t+\Delta W_t
\]

\[
W_{t+1}
\leftarrow
DQ(Q(W^{*}_{t+1}))
\]

를 수행한다.

이 단계에서는:

🚫 VRAM 절감 주장 금지  
🚫 속도 향상 주장 금지

목적은 오직:

> low-precision grid에 직접 누적해도 optimization trajectory가 유지되는가?

이다.

1차 arm:

| Arm | shadow |
|---|---|
| S-A | FP32 |
| S-16 | FP16 + 동일 계열 scaling |
| S-E4 | E4M3 + row-scale + RNE |

S0에서 E5M2 gate가 열린 경우:

| Arm | shadow |
|---|---|
| S-E5 | E5M2 + same scale policy + RNE |

FP16 sentinel의 목적은 매우 중요하다.

FP8가 실패했을 때:

- “FP32만 가능하다”
- “8bit가 너무 거칠 뿐 16bit는 가능하다”

를 구분할 수 있다.

#### S1a 100M gate

- NaN/Inf 없음
- loss plateau/freeze 없음
- control 대비 +0.01 이내
- exact frozen fraction이 시간에 따라 폭증하지 않음

S-E4가 통과하면 S2로 진행 가능.

---

### S1b — stochastic-rounding rescue

다음 failure signature가 있을 때만 연다.

- RNE E4M3가 품질 gate 실패
- 동시에 exact frozen-update fraction 증가
- ULP visibility가 failure와 시간적으로 정합
- saturation/underflow가 주원인은 아님

그 경우 같은 E4M3/scale에서 **rounding만 SR로 변경**한다.

| Arm | 변경 |
|---|---|
| S-E4-RNE | 기존 실패 arm |
| S-E4-SR | rounding만 stochastic |

SR이 회복시키면:

> E4M3 format 자체 실패

가 아니라

> deterministic direct write-back failure

로 판정한다.

SR까지 실패하면 S2를 자동으로 열지 않는다.

ECO/error-feedback는 optimizer semantics를 변경하므로 이 proposal의 static-shadow 원인분리 단계에서는 넣지 않는다.

S3 이후 별도 proposal 후보로 남긴다.

---

### S2 — H/L schedule screen

S1에서 실제 low-precision shadow \(L\)이 100M gate를 통과했을 때만 연다.

\[
H=FP32
\]

\[
L=\text{S1 승자의 완전한 format+scale+rounding policy}
\]

100M 비교:

| Arm | schedule |
|---|---|
| S-H | H all-way |
| S-L | L all-way |
| S-HL | H → L |
| S-LH | L → H |
| S-HLH | H → L → H |

기본 전환점:

- 초기 H 보호: first 10%
- 후기 H 복귀: last 20%
- 후기 20%는 현재 `decay_frac=0.2`와 정렬

따라서:

\[
H\rightarrow L:
0\!-\!10\%\ H,\quad10\!-\!100\%\ L
\]

\[
L\rightarrow H:
0\!-\!80\%\ L,\quad80\!-\!100\%\ H
\]

\[
H\rightarrow L\rightarrow H:
0\!-\!10\%\ H,\quad10\!-\!80\%\ L,\quad80\!-\!100\%\ H
\]

단:

S0 reference trace에서 ULP visibility가 이 경계와 명백하게 모순되면 **학습 실행 전에** 계획서를 수정한다.

실행 후 가장 잘 나온 지점에 맞춰 switch point를 소급 조정하지 않는다.

### S2에서는 runtime precision controller를 만들지 않는다

S0 observer 값을 보고 매 step 자동으로 H/L을 전환하지 않는다.

이유:

- update visibility ≠ parameter importance
- controller 자체가 새 독립변수
- controller threshold를 outcome에 맞출 위험
- format/precision thrashing 가능

먼저 고정 schedule의 causal 가격표를 만든다.

---

### S3 — shadow 최종 300M 확인

S2 승자 하나와 FP32 shadow control만 비교한다.

성공 조건:

\[
\Delta{\rm full\mbox{-}val}\le+0.0010
\]

이면:

> 현재 tied 무KD 기준선의 측정 분해능 안에서 품질 열화를 검출하지 못했다.

라고 판정한다.

이 조건을 통과해야 다음 단계의 실제 storage 연구를 연다.

---

### S4 — 실제 storage/masterless optimizer는 별도 proposal

fake quantization 성공은

\[
\text{low-precision grid에서 optimization 가능}
\]

을 뜻한다.

그러나

\[
\text{실제 1-byte persistent shadow storage}
\]

와 동일한 것은 아니다.

실제 storage에서는:

- scale metadata
- dequant/update/requant
- rounding hardware support
- optimizer state interaction
- error feedback
- ECO류 momentum correction
- stochastic rounding
- fused update kernel

이 새 독립변수가 된다.

특히 R7에서는 naive FP8 master 제거가 여러 크기의 Transformer에서 실패했고 error-feedback가 이를 크게 회복했다.

따라서 실제 masterless optimizer는 S3 성공 뒤 별도 proposal에서 비교한다.

후속 후보:

\[
\text{plain FP8+SR}
\]

vs

\[
\text{FP8+error feedback/ECO}
\]

vs

\[
\text{selective high-precision master}
\]

등이다.

---

### 구현 전 공통 preflight

승인 뒤 구현 시 다음을 모두 검사한다.

1. 신규 flag 기본값 off
2. default-off 기존 step0 값/로그 동일
3. CLI → config → trainer/model 실제 연결
4. 신규 값 JSON 기록
5. `flag_whitelist.tsv` 반영
6. smoke arm 존재
7. static checks 전수 통과
8. batch와 test_plan 일치
9. control arm 선행
10. seed/data/token budget 동일
11. `wq_dtype` 고정
12. `opt_dtype` 고정
13. Muon 혼입 없음
14. shadow format과 compute format 별도 필드 기록
15. scale granularity 기록
16. scale policy 기록
17. rounding policy 기록
18. observer와 실제 write-back 구분 기록

---

## 7. 거절하면 못 하는 것

거절해도 현재 TinyLM 연구가 막히지는 않는다.

기존 FP32 latent + 기존 BF16/FP16 compute 경로를 계속 사용하면 된다.

따라서 **프로젝트 진행의 필수 선결은 아니다.**

다만 다음을 알 수 없게 된다.

1. Ada FP8 Tensor Core가 TinyLM의 실제 wall-clock을 줄이는가
2. 현재 FP32 latent/shadow가 정말 필요한가
3. FP8 shadow 실패 시 range와 mantissa 중 어느 쪽이 원인인가
4. direct low-precision write-back에서 invisible update가 실제 TinyLM에도 발생하는가
5. 후기 FP32 복귀가 precision schedule로 의미 있는가
6. 실제 masterless FP8 optimizer를 만들 가치가 있는가

따라서 이 proposal의 핵심 가치는 배포 모델 크기를 직접 줄이는 데 있지 않고:

\[
\boxed{\text{학습 compute와 persistent training state를 어디까지 낮출 수 있는지 경계를 측정}}
\]

하는 데 있다.

현재 프로젝트 우선순위가 학습속도/학습메모리보다 배포 품질과 CPU inference에 훨씬 높다면 이 proposal은 미뤄도 된다.

---

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| float8 cast만 하고 실제 FP8 GEMM을 안 탐 | 속도 그대로인데 FP8 성공으로 오판 | C0 profiler evidence 필수 |
| `te.Linear` 교체가 TLinear 의미 변경 | ternary/STE가 달라짐 | parameter ownership·mapping·gradient 확인 |
| Current Scaling overhead가 FP8 이득을 상쇄 | amax/cast kernel 시간이 큼 | C1에서 Delayed와 직접 비교 |
| MXFP8 논문을 Ada backend 근거로 오용 | 존재하지 않는 hardware path를 전제 | format hypothesis와 backend support 분리 |
| compile 조건이 달라짐 | compile 효과를 FP8 효과로 오판 | A/B/C/A' 동일 session |
| historical speed와 비교 | 온도/driver drift | 같은 session 재측정 |
| `wq_dtype`와 shadow precision 혼동 | 원인 오귀속 | 별도 field·flag |
| optimizer state 동시 변경 | shadow 효과와 교락 | `opt_dtype` 고정 |
| Muon 동시 변경 | optimizer와 precision 교락 | AdamW 먼저 |
| FP8 shadow에서 scale 정의가 암묵적 | 실험 재현 불가 | format+granularity+scale+rounding 전부 기록 |
| E4M3/E5M2 scale policy가 다름 | format 비교가 무효 | 동일 scaling policy 강제 |
| 매 step scale 재계산 자체가 code 이동을 만듦 | dead-update 지표 왜곡 | quantizer state를 명시하고 exact code event 기록 |
| reconstruction error만 사용 | ternary 동작과 무관한 지표가 승자 결정 | ternary transition F1 포함 |
| transition recall만 사용 | false transition 남발이 좋아 보임 | precision/recall/F1 전부 |
| RNE FP8에서 작은 update 소실 | loss finite인데 학습 정지 | ULP/exact freeze observer |
| SR을 처음부터 켬 | format failure와 rounding rescue 구분 불가 | RNE → 조건부 SR 순서 |
| SR 자체 variance 증가 | loss noise 증가 | matched RNE/SR |
| E5M2의 넓은 range를 무조건 장점으로 해석 | mantissa 한 비트 감소를 무시 | underflow와 update visibility 둘 다 계측 |
| adaptive format 과설계 | overhead·thrashing | 기본 branch에서 제외, 강한 S0 근거 필요 |
| H→L 후기 freeze | WSD 후반 fine update 소실 | L→H/H→L→H 직접 비교 |
| early L trajectory 훼손 | 후기 H로 회복 안 됨 | H→L→H 포함 |
| fake quant를 VRAM 절감으로 해석 | 실제 storage 그대로 | S1~S3에서 메모리 절감 주장 금지 |
| 실제 packed FP8 결과가 다름 | fake quant 성공 후 storage 실패 | S4 별도 proposal |
| ECO/error feedback를 너무 일찍 섞음 | FP8 lattice 질문과 optimizer 변경 혼재 | S4로 분리 |
| current 2σ ruler를 다른 계열에 오용 | 잘못된 동급 판정 | 0.0010은 tied 조건에만 사용 |

### 금지할 해석

- E4M3/E5M2 둘 다 8 bit이므로 format adaptive를 **압축률 개선**이라고 쓰지 않는다.
- FP8 shadow 성공을 FP8 GEMM 성공이라고 쓰지 않는다.
- FP8 GEMM 성공을 masterless training 성공이라고 쓰지 않는다.
- fake quantization을 실제 VRAM 절감이라고 쓰지 않는다.
- MXFP8 pretraining 성공을 Ada MXFP8 hardware 지원이라고 쓰지 않는다.
- 100M screen을 최종 동등성 증명이라고 쓰지 않는다.
- `Δ≤0.0010`을 “완전히 동일”이라고 쓰지 않는다.
- dead-update fraction이 높은 layer를 곧바로 “중요한 layer”라고 쓰지 않는다.
- E5M2가 dynamic range가 크다는 이유만으로 shadow에 더 적합하다고 쓰지 않는다.
- E4M3가 MXFP8에서 우세했다는 이유만으로 Ada per-tensor FP8에서도 반드시 우세하다고 쓰지 않는다.

---

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | ★ Compute → observer → static shadow → rounding rescue → schedule을 조건부 순차 검증 | 원인 분리 가장 좋음, 최신 문헌의 핵심 변수까지 계측 | 전 gate 통과 시 ⚙10~14.5 GPU-h |
| B | FP8 compute C0~C3만 | 즉시 wall-clock 가치 확인, 구현 상대적으로 단순 | shadow/master precision 질문은 남음 |
| C | shadow S0~S1만, compute 기존 유지 | low-precision latent 가설을 직접 검증 | FP8 hardware speed 축 미확인 |
| D | FP16 shadow sentinel까지만 | FP32 master가 정말 필요한지 싸게 확인 | FP8 경계는 모름 |
| E | 바로 ECO/SR masterless 구현 | 성공하면 큰 메모리 이득 가능 | format/scaling/rounding 원인이 섞이고 구현비 큼 |
| F | 아무것도 안 한다 | 비용 0, 기존 안정 경로 유지 | 학습속도와 shadow precision 한계 미확인 |

### ★권장안과 근거

**A를 권장한다.**

단, “승인 즉시 전 단계를 실행한다”는 뜻이 아니다.

핵심은:

\[
\boxed{\text{값싼 진단}\rightarrow\text{명시적 gate}\rightarrow\text{필요한 고비용 학습만}}
\]

이다.

구체적으로:

1. C0에서 실제 FP8 kernel이 없으면 **⚙0.1 GPU-h에서 compute 종료**
2. C1에서 speed/VRAM 이득이 없으면 **compute quality run 생략**
3. C2에서 Ada coarse scaling의 format 승자를 결정
4. S0에서 **E4M3/E5M2가 아니라 실제 failure mechanism을 먼저 분류**
5. E5M2가 range 문제를 실제로 해결할 때만 S-E5를 실행
6. adaptive E4M3/E5M2 controller는 기본 구현하지 않음
7. RNE FP8가 invisible-update signature와 함께 실패할 때만 SR rescue
8. static L이 통과해야 H/L schedule을 실행
9. S3까지 통과해야 실제 packed/masterless optimizer를 새 proposal로 연다
10. ECO/error feedback는 direct-grid 질문과 분리해서 후속으로 다룬다

이 순서는 저장소의

> 값싼 진단 → 명시적 gate → 필요한 경우에만 비싼 학습

규약에 맞는다.

또한 최신 FP8 문헌이 보여주는 세 가지 사실:

\[
\text{compute precision}\neq\text{master precision}
\]

\[
\text{FP8 format}\neq\text{scaling policy}
\]

\[
\text{FP8 grid}\neq\text{write-back policy}
\]

를 실험 구조에서 직접 분리한다.

따라서 결과가 성공이든 실패든 **무엇 때문에 그런 결과가 나왔는지 남는 실험**이 된다.

---

**상태:** ⏳판단 대기

승인 전 구현·batch 작성 없음.

승인 시 현재 `실험계획목록.md` 및 `experiments.tsv`를 다시 조회한 뒤 다음 사용 가능 `test_plan/` 번호를 배정한다.