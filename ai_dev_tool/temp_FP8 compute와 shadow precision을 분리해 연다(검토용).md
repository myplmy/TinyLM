# 제안 — FP8 compute와 shadow precision을 분리해 연다

> **작성** 2026-09-11  
> **상태** ⏳판단 대기  
> **분류** 실험계획  
> **제안 파일명** `proposal/20260911_FP8-compute와-shadow-precision을-분리해-연다.md`
>
> 이 문서는 `proposal/README.md` 및 `proposal/_TEMPLATE.md` 규약을 따른다.  
> 🚫 승인 전에는 코드 구현, 배치 생성, `test_plan/` 번호 할당을 하지 않는다.
>
> 현재 확인상 실험 번호는 P089까지 사용 중이지만, **다음 번호를 여기서 예약하지 않는다.** 승인 시 `실험계획목록.md`와 `experiments.tsv`를 다시 확인한 뒤 번호를 배정한다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

현재 TinyLM의 ternary 학습에는 서로 다른 정밀도 축 세 개가 존재한다.

| 축 | 현재 상태 | 의미 |
|---|---|---|
| **latent/shadow weight** | `TLinear.weight` 연속 `nn.Parameter` | optimizer가 실제로 갱신하는 잠재 weight |
| **ternary forward weight `_wq`** | `--wq-dtype`으로 저장 dtype 변경 가능 | ternary 변환 후 `F.linear`에 들어가는 weight |
| **optimizer state** | `--opt-dtype`으로 FP32/BF16 선택 가능 | AdamW의 moment 저장 정밀도 |

현재 `tinylm/model/ternary.py`의 `TLinear.weight`에는 shadow precision 자체를 FP8로 제한하는 축이 없다.

또한 현재 `--wq-dtype`은 **shadow weight precision이 아니다.**

`ternary()` 계산은 기존 고정밀 latent weight에서 수행하고, 생성된 `_wq`의 저장 dtype만 BF16/FP16으로 낮춘다. 따라서 다음 두 문제는 별개다.

\[
\text{A. FP8 GEMM을 이용해 학습 계산을 빠르게 할 수 있는가?}
\]

\[
\text{B. 연속적인 shadow weight 자체를 FP8 lattice로 제한해도 학습되는가?}
\]

이를 한 실험에서 동시에 변경하면 성능 변화가

- FP8 GEMM의 수치 오차 때문인지,
- shadow precision 때문인지,
- E4M3/E5M2 선택 때문인지

구분할 수 없다.

따라서 **compute precision과 shadow precision을 직교 축으로 분리하여 순차적으로 연다.**

### 현재 내부 근거

- 표준 무KD 조건은 `m100R1c + --init-from`, KD 없음.
- 20층 무KD에서는 `--no-ckpt` 사용이 현재 규약이다.
- `mC_initonly_nc`의 실측 full-val은 **3.6762**, 학습속도는 약 **2.485 s/step**.
- 최신 타잉 계열 품질 자는
  \[
  2\sigma = 0.0010
  \]
  이다.
- `--opt-dtype bf16`은 표준조건이 아니므로 이 실험에서는 기본적으로 사용하지 않는다.
- `wq_dtype`, `opt_dtype`, optimizer까지 동시에 변경하지 않는다.

출처: `docs/EXPERIMENT_BASELINES.md` B.6, B.7, B.9.1.

### 외부 근거

NVIDIA Transformer Engine 2.18.0 공식 문서에서:

- FP8 Current Scaling은 **Ada SM89 이상**을 지원한다.
- 기본 FP8 HYBRID는
  - forward: **E4M3**
  - backward: **E5M2**
- E4M3는 E5M2보다 정밀도가 높고,
- E5M2는 더 넓은 dynamic range를 가진다.
- Current Scaling에서는 tensor마다 FP32 scale 하나를 사용한다.
- E4M3/E4M3도 지원된다.

따라서 현재 RTX 4070 Ti SUPER 환경에서는 FP4보다 **FP8을 먼저 여는 것이 하드웨어 가속 가능성과 구현 현실성 면에서 우선순위가 높다.**

---

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

다음 네 질문에 순서대로 답한다.

1. **FP8 GEMM 자체가 현재 TinyLM에서 실제 Tensor Core 경로를 타며 BF16/FP16보다 빠른가?**
2. 그때 `E4M3 forward + E5M2 backward`와 `E4M3 forward + E4M3 backward` 중 어떤 구성이 품질/속도상 적합한가?
3. compute precision을 고정한 뒤, **ternary latent/shadow weight 자체를 FP8로 제한해도 품질을 유지할 수 있는가?**
4. shadow FP8이 가능하다면
   \[
   H\rightarrow L,\quad L\rightarrow H,\quad H\rightarrow L\rightarrow H
   \]
   와 L 구간의
   \[
   E4M3\leftrightarrow E5M2
   \]
   적응 선택이 정적 E4M3보다 유리한가?

여기서 shadow schedule의 정의는 다음과 같다.

\[
H=\text{현재 FP32 shadow}
\]

\[
L=\text{검증된 FP8 shadow policy}
\]

**FP8 compute와 H/L shadow schedule은 같은 변수가 아니다.**

---

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| FP8 하드웨어 경로 판정 | profiler에서 실제 FP8 GEMM 사용 여부 |
| 학습 가속 가격표 | BF16 대비 ms/step, tokens/s, peak VRAM |
| FP8 compute 품질 가격표 | E4M3/E5M2 및 E4M3/E4M3의 paired full-val |
| shadow precision 진단 | layer별 dead-update, update preservation, ternary transition 보존율 |
| E4M3/E5M2 선택 근거 | 어떤 layer/시점에서 어느 형식이 실제로 유리한지 |
| shadow schedule 가격표 | static L / H→L / L→H / H→L→H |
| 최종 판정 | 기존 경로 유지 / FP8 compute 채택 / FP8 shadow까지 채택 |
| 이후 구현 근거 | 실제 FP8 shadow storage 또는 fused optimizer를 만들 가치가 있는지 판정 |

### 승인 시 생성/수정될 대상

승인 시에만 다음을 수행한다.

- `test_plan/`에 다음 사용 가능 번호로 정식 계획서 생성
- 필요한 FP8 backend 또는 wrapper 구현
- `trainer.py` 연결
- shadow observer/projection 코드 구현
- CLI/config 신규 플래그 연결
- 실행 JSON에 신규 축 기록
- `scripts/flag_whitelist.tsv` 갱신
- smoke 경로 추가
- 정적 게이트 전수 실행
- 실행 시점에만 batch 파일 생성
- `experiments.tsv` 등록
- 실행 후 `results/` 결과문서 생성

🚫 `proposal` 승인만으로 기존 기본값을 바꾸지 않는다.

신규 기능은 모두 **default off = 기존 동작 bit-identical**을 원칙으로 한다.

---

## 4. 비용

현재 `mC_initonly_nc ≈ 2.485 s/step`을 단순 기준으로 한 추정이다. FP8 구현 및 환경에 따라 달라질 수 있으므로 모두 ⚙ 추정값이다.

| 단계 | GPU 비용 |
|---|---:|
| C0 — backend/profiler smoke | ⚙0.1 h |
| C1 — 250-step 속도 A/B/C/A' | ⚙0.7 h |
| C2 — 100M compute 품질 screen | ⚙1.1 h |
| C3 — 300M compute 최종 검증 | ⚙3.2 h |
| S0 — 250-step shadow observer | ⚙0.2 h |
| S1 — 100M shadow causal screen | ⚙1.1~1.6 h |
| S2 — schedule 4종 100M screen | ⚙2.1 h |
| S3 — schedule 승자 300M 확인 | ⚙1.6~3.2 h |
| 실제 packed/masterless FP8 | **별도 승인 전 미산정** |

### 조건부 총비용

- C0에서 실패: **⚙0.1 h 종료**
- compute 속도 screen까지: **⚙0.8 h**
- compute 최종검증까지: **⚙5.1 h**
- shadow static screen까지: **⚙6.4~6.9 h**
- schedule screen까지: **⚙8.5~9.0 h**
- schedule full confirmation 포함: **⚙10~12 h**

모든 단계가 자동으로 열리는 것이 아니다. **앞 단계가 게이트를 통과할 때만 다음 비용을 쓴다.**

| 기타 비용 | 양 |
|---|---:|
| AI/코드 작업 | ⚙2~4 engineer-h 상당 |
| 사용자가 직접 해야 하는 일 | 승인 후 batch 실행·실패 확인 약 ⚙10~20 min hands-on + GPU 실행 |
| 임시 디스크 | ⚙최대 5 GB 수준, checkpoint 정책에 따라 변동 |

현재 실험 큐를 선점하지 않는다. 승인 후 큐 상태를 다시 보고 실행순서를 정한다.

---

## 5. 원리·근거

### 5.1 FP8 compute와 FP8 shadow는 분리해야 한다

FP8 Tensor Core 가속은

\[
A_{\rm FP8}W_{\rm FP8}
\]

GEMM이 실제 저정밀 hardware kernel로 실행될 때 생긴다.

반면 shadow weight를 FP8로 저장하는 것만으로는 forward/backward GEMM이 자동으로 FP8이 되지 않는다.

따라서

\[
\boxed{\text{FP8 compute}}
\]

와

\[
\boxed{\text{FP8 shadow}}
\]

를 별도의 실험으로 측정한다.

---

### 5.2 compute에서는 E4M3/E5M2 HYBRID를 1순위로 한다

공식 FP8 recipe의 기본은

\[
\text{forward}=E4M3
\]

\[
\text{backward}=E5M2
\]

이다.

forward weight/activation은 상대적으로 precision 요구가 높고, backward gradient는 더 넓은 range가 필요할 수 있기 때문이다.

다만 TinyLM의 분포가 일반 dense Transformer와 같다는 보장은 없으므로 다음을 직접 비교한다.

\[
C_1=E4M3_{\rm fwd}+E5M2_{\rm bwd}
\]

\[
C_2=E4M3_{\rm fwd}+E4M3_{\rm bwd}
\]

E5M2 forward는 첫 실험군에 넣지 않는다. 정밀도를 일부러 더 낮출 근거가 없다.

---

### 5.3 shadow에서는 E4M3를 우선 가설로 둔다

shadow weight의 역할은 단순히 큰 값을 표현하는 것이 아니다.

optimizer의 작은 업데이트

\[
W_t\rightarrow W_t+\Delta W_t
\]

를 누적하여 최종적으로 ternary threshold를 넘게 만드는 연속 상태다.

따라서 shadow에는 dynamic range보다 **작은 update를 보존하는 precision**이 중요할 가능성이 높다.

초기 가설은:

\[
\boxed{E4M3_{\rm shadow} > E5M2_{\rm shadow}}
\]

이다.

다만 이를 선험적으로 확정하지 않는다.

---

### 5.4 L 구간 E4M3/E5M2 adaptive는 observer 결과가 있을 때만 연다

E4M3와 E5M2는 둘 다 8 bit다.

따라서

\[
E4M3\leftrightarrow E5M2
\]

선택은 **메모리를 추가로 줄이지 않는다.**

장점이 있다면 오직:

- saturation 감소
- dead-update 감소
- ternary transition 보존 개선

이다.

그래서 controller부터 구현하지 않고 먼저 FP32 shadow를 유지한 상태에서 두 FP8 형식을 **가상으로 관측**한다.

optimizer가 의도한 다음 weight를

\[
W^*_{t+1}=W_t+\Delta W_t
\]

라고 하고 format \(f\)에 대해 다음을 측정한다.

#### ① dead-update rate

\[
D_f=
P\left[
Q_f(W^*_{t+1})=Q_f(W_t)
\right]
\]

#### ② update preservation

\[
U_f=
\frac{
\|Q_f(W^*_{t+1})-Q_f(W_t)\|_F
}{
\|W^*_{t+1}-W_t\|_F+\epsilon
}
\]

#### ③ ternary transition recall

현재 ternary mapping을 \(T(W)\)라 하면, 고정밀 shadow에서 발생했어야 할

\[
T(W_t)\rightarrow T(W^*_{t+1})
\]

변화를 FP8 shadow도 얼마나 재현하는지 측정한다.

이 값은 일반적인 weight reconstruction error보다 TinyLM에 더 직접적인 지표다.

#### ④ saturation / underflow

E4M3의 좁은 range가 실제 layer에서 문제를 일으키는지도 같이 센다.

---

### 5.5 H/L schedule의 가설

후기 학습으로 갈수록 일반적으로 실제 update의 크기가 작아진다.

따라서 단순 직관상:

- `H→L`: 후기 작은 update가 FP8 lattice에 막힐 위험
- `L→H`: 후기 수렴은 보호하지만 초기 trajectory가 FP8 noise 영향을 받음
- `H→L→H`: 초기 trajectory와 후기 미세 수렴을 모두 보호

라는 차이가 예상된다.

초기 예상 순위는

\[
H\rightarrow L\rightarrow H
\]

가 가장 안전하지만, **이는 가설이지 판정이 아니다.**

실험으로 확인한다.

---

## 6. 방법

# Track C — FP8 compute

Shadow precision은 전부 기존 FP32로 고정한다.

optimizer는 첫 실험에서는 **AdamW**로 고정한다.

현재 Muon 축이 별도로 진행 중이므로 FP8과 동시에 바꾸면 원인 분리가 깨진다. FP8 정책이 확정된 뒤에만 Muon transfer를 별도 실험한다.

---

### C0 — FP8 backend feasibility

| 항목 | 내용 |
|---|---|
| 학습 | 긴 학습 없음 |
| 모델 | 현재 표준 TinyLM/TLinear |
| 확인 | 실제 FP8 GEMM kernel 사용 여부 |
| 비교 | 기존 BF16/autocast 경로 |
| GPU | ⚙0.1 h |

TinyLM `TLinear`은 자기 parameter를 직접 쓰는 일반 `Linear`가 아니라, latent weight에서 매 forward 생성되는 ternary `_wq`를 `F.linear`에 공급한다.

따라서 단순히 `te.Linear`로 교체해 버리면 **모델 의미가 바뀔 수 있다.**

C0에서 반드시 확인한다.

1. 기존 `TLinear.weight` ownership 유지
2. 기존 ternary mapping 유지
3. STE gradient 유지
4. `torch.compile` 조건 동일
5. 실제 FP8 kernel 실행
6. finite forward/backward
7. gradient 누락 없음

### C0 게이트

다음 중 하나라도 실패하면 **compute Track 종료 후 재설계**한다.

- profiler에 실제 FP8 GEMM이 확인되지 않음
- 기존 TLinear 의미를 바꿔야만 FP8을 쓸 수 있음
- graph break로 FP8 이득을 상쇄
- NaN/Inf 발생
- 기존 default-off 경로와 bit-identical 조건 실패

🚫 단순 `float8` cast 성공을 **FP8 가속 성공으로 쓰지 않는다.**

---

### C1 — 250-step matched speed probe

한 세션 안에서 다음 순서로 실행한다.

| Arm | compute | shadow |
|---|---|---|
| C-A | 기존 기준 | FP32 |
| C-B | E4M3 fwd / E5M2 bwd | FP32 |
| C-C | E4M3 fwd / E4M3 bwd | FP32 |
| C-A' | 기존 기준 재측정 | FP32 |

나머지는 모두 동일:

- 같은 preset
- 같은 batch
- 같은 sequence
- 같은 compile 조건
- 같은 `wq_dtype`
- 같은 `opt_dtype`
- AdamW
- no KD
- 같은 seed/data

측정값:

- warmup 제외 median ms/step
- p10/p90 step time
- tokens/s
- peak allocated/reserved VRAM
- compile time 별도
- FP8 kernel 호출 비율

### C1 판정

**속도 개선**

\[
\ge10\%
\]

이면 다음 단계 진입.

**5~10%**

이면 조건부. VRAM 감소 또는 microbatch 확대 가능성이 있어야 계속한다.

**<5%이고 메모리 이득도 없음**

이면 compute Track을 닫는다.

A와 A' 차이가 크면 그 세션의 속도 판정을 무효로 하고 재측정한다.

---

### C2 — 100M quality screen

C1 승자 하나와 기존 control만 비교한다.

\[
763\ {\rm steps}\approx100M\ tokens
\]

목적은 최종 동등성 판정이 아니라 **큰 품질 붕괴를 값싸게 자르는 것**이다.

Gate:

- 발산/NaN 없음
- loss curve 비정상 진동 없음
- full/paired validation 열화가 **+0.01 이내**

`+0.01`은 lossless 자가 아니라 **300M을 태울 가치가 있는지 보는 coarse engineering gate**다.

---

### C3 — 300M compute-only 최종 판정

두 팔:

| Arm | compute | shadow |
|---|---|---|
| C-FP | 기존 | FP32 |
| C-F8 | C1/C2 승자 | FP32 |

조건:

- 300M tokens
- same seed = 1337
- same pool/data order
- same initialization
- no KD
- AdamW
- same `wq_dtype`
- same optimizer state dtype
- same checkpoint condition

현재 타잉 계열 자:

\[
2\sigma=0.0010
\]

따라서

\[
\Delta {\rm full\mbox{-}val}\le+0.0010
\]

이면 현재 측정 분해능에서 **detectable regression 없음**으로 적는다.

\[
\Delta>+0.0010
\]

이면 “lossless” 또는 “동등”이라고 쓰지 않는다.

속도가 빨라도 **품질-속도 tradeoff**로 별도 보고한다.

---

# Track S — FP8 shadow precision

Compute Track과 독립적으로 수행한다.

S Track에서는 compute precision을 한 값으로 고정한다.

- C Track이 성공했다면 검증된 compute mode
- C Track이 실패했다면 기존 compute mode

즉 compute 실패가 shadow 연구를 막지는 않는다.

---

### S0 — observer-only shadow diagnostic

실제 학습 weight는 **FP32 그대로 유지**한다.

optimizer update마다 E4M3/E5M2 shadow를 가상 계산만 한다.

측정:

- `dead_update_e4m3`
- `dead_update_e5m2`
- `update_preservation_e4m3`
- `update_preservation_e5m2`
- saturation/underflow
- ternary transition count
- ternary transition recall
- layer별 승자
- 학습 단계별 승자

비용:

\[
250\ {\rm steps}\approx0.2h
\]

### adaptive E4M3/E5M2 개방 조건

다음 경우에는 **adaptive를 만들지 않는다.**

- layer-step 관측의 ≥90%에서 E4M3가 동급 이상
- E4M3 saturation이 사실상 문제없음
- E5M2가 ternary transition 보존을 의미 있게 개선하지 못함

반대로 다음 두 조건을 동시에 만족하면 adaptive branch를 연다.

1. E5M2가 **≥10%의 layer-step 구간**에서 실제 승자이고
2. 해당 구간에서 dead-update 또는 ternary-transition 오류가 E4M3 대비 **상대 20% 이상 개선**

이 문턱은 controller complexity를 정당화하기 위한 사전 게이트다.

---

### S1 — static FP8 shadow causal screen

첫 구현은 실제 packed FP8 저장이 아니라 **fake quantization**이다.

즉 physical tensor는 기존 dtype을 유지하고 optimizer step 직후

\[
W_{t+1}
\leftarrow
DQ\!\left(Q_{\rm FP8}(W^*_{t+1})\right)
\]

를 수행한다.

이 단계에서는:

🚫 VRAM 절감을 주장하지 않는다.  
🚫 속도 향상을 주장하지 않는다.

목적은 오직

> “shadow가 FP8 lattice에만 존재해도 학습되는가?”

를 확인하는 것이다.

Arm:

| Arm | shadow |
|---|---|
| S-A | FP32 |
| S-B | E4M3 |
| S-C | adaptive E4M3/E5M2 — **S0 gate가 열린 경우에만** |

100M screen 후 승자만 300M으로 올린다.

---

### S2 — H/L schedule screen

S1에서 static FP8 shadow가 최소한 학습 가능한 것으로 확인된 경우에만 연다.

H와 L:

\[
H=FP32
\]

\[
L=S1에서 검증된 FP8\ policy
\]

100M에서 다음을 비교한다.

| Arm | schedule |
|---|---|
| S-H | FP32 all-way control |
| S-L | FP8 all-way |
| S-HL | H → L |
| S-LH | L → H |
| S-HLH | H → L → H |

전환점은 우선 다음처럼 고정한다.

- 초기 H 보호구간: 첫 **10%**
- 후기 H 복귀: 마지막 **20%**
- 마지막 20%는 현재 `decay_frac=0.2`와 정렬

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

단, 250-step observer에서 실제 update/noise 곡선이 이 경계와 명백히 어긋나면 **실험 전에 계획서를 수정하고 이유를 기록한다.** 실행 뒤 경계를 소급 조정하지 않는다.

---

### S2에서 adaptive L이 열린 경우

매 block마다 매 step 포맷을 바꾸지 않는다.

첫 구현은 **layer 단위**로 제한한다.

권장 controller:

- 판단 통계: 100-step EMA
- 최소 dwell: 200 steps
- 전환 조건: 상대 개선 ≥20%
- hysteresis 적용
- 동일 포맷 유지가 기본

목적은

\[
E4M3\leftrightarrow E5M2
\]

thrashing을 막는 것이다.

그리고 두 형식 모두 8 bit이므로 adaptive policy에 **메모리 이득을 귀속하지 않는다.**

---

### S3 — shadow 최종 300M 확인

S2 승자 한 개만 현재 FP32 shadow control과 비교한다.

기본 성공 조건:

\[
\Delta {\rm full\mbox{-}val}\le+0.0010
\]

이면 현재 타잉 계열의 측정 분해능 안에서 품질 열화를 검출하지 못한 것으로 판정한다.

이를 통과해야 다음 단계인 **실제 FP8 shadow storage/masterless optimizer**를 별도 제안할 가치가 생긴다.

---

### S4 — 실제 storage 절감은 별도 제안으로 분리

fake quantization 성공은

\[
\text{FP8 lattice에서 학습 가능}
\]

을 의미할 뿐,

\[
\text{실제 1-byte shadow storage로 동일하게 학습 가능}
\]

을 자동으로 의미하지 않는다.

실제 storage에서는 optimizer update를 위해

- dequantize
- update
- requantize
- error feedback
- stochastic rounding
- masterless optimizer

등의 설계가 새 독립변수가 된다.

따라서 S3 성공 후 **새 proposal로 분리**한다.

---

### 구현 전 공통 preflight

승인 뒤 구현할 때 다음을 모두 검사한다.

1. 신규 flag 기본값 off
2. default-off 기존 step0 값/로그 bit-identical
3. CLI → config → trainer/model까지 실제 연결
4. 신규 값 JSON에 기록
5. `flag_whitelist.tsv` 반영
6. smoke arm 존재
7. static checks 전수 통과
8. batch와 test_plan 일치
9. control arm 먼저 존재
10. seed/data/token budget 동일
11. `wq_dtype` 고정
12. `opt_dtype` 고정
13. Muon 혼입 없음

---

## 7. 거절하면 못 하는 것

거절해도 현재 TinyLM 연구 자체가 막히지는 않는다.

기존 BF16/FP32 학습 경로를 그대로 사용하면 된다.

다만 다음 세 가지를 알 수 없게 된다.

1. 현재 Ada GPU의 FP8 Tensor Core가 TinyLM 학습에서 실제 wall-clock 이득을 주는지
2. ternary model의 FP32 latent shadow가 실제로 필요한지, 아니면 FP8이면 충분한지
3. 학습 정밀도를 시간에 따라 조절하는 것이 최종 TinyLM의 학습비용을 줄일 수 있는지

따라서 이 제안의 가치는 **배포 모델 크기를 직접 줄이는 것**보다는

\[
\boxed{\text{같은 모델을 더 싸고 빠르게 학습할 수 있는가}}
\]

를 여는 데 있다.

현재 프로젝트 우선순위가 배포 상주메모리와 품질보다 학습속도를 낮게 두고 있다면 이 제안은 미뤄도 된다.

---

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| float8 cast만 하고 실제 FP8 kernel을 안 탐 | 속도 그대로인데 “FP8 학습”이라 오판 | profiler evidence를 C0 필수 gate |
| `te.Linear` 교체가 TLinear 의미를 바꿈 | ternary/STE가 달라짐 | parameter ownership과 ternary mapping 유지 확인 |
| compile 조건이 달라짐 | FP8 이득처럼 보이는 compile 교락 | control도 동일 compile 조건 |
| historical speed와 비교 | 환경/온도/드라이버 차이를 속도로 오판 | 같은 세션 A/B/C/A' |
| `wq_dtype`와 shadow precision 혼동 | 원인을 잘못 귀속 | 두 flag를 별도 기록·고정 |
| optimizer state까지 같이 변경 | FP8 shadow 효과와 교락 | `opt_dtype` 고정 |
| Muon까지 동시 사용 | optimizer 개선과 FP8 효과 교락 | AdamW 먼저 |
| fake quant를 VRAM 절감으로 해석 | 실제 storage는 그대로 | S1에서 메모리/속도 주장 금지 |
| E4M3/E5M2 adaptive 과설계 | controller overhead > 수치 이득 | S0 observer gate |
| format thrashing | 재양자화 noise 증가 | EMA+hysteresis+minimum dwell |
| ordinary qerror만 보고 선택 | ternary threshold 동작과 상관없을 수 있음 | ternary-transition metric을 primary diagnostic으로 |
| late FP8가 작은 update 삭제 | WSD 후기 성능 악화 | L→H / H→L→H 직접 비교 |
| early FP8가 trajectory 훼손 | 후기 H로도 회복 안 됨 | H→L→H 포함 |
| FP8 compute는 빠르지만 품질 저하 | speed만 보고 채택 | 300M paired full-val gate |
| 기존 ruler 오용 | 0.0034로 잘못 “동급” 판정 | 타잉 current ruler 0.0010 사용 |
| 실제 packed FP8에서 결과가 달라짐 | fake quant 성공 후 storage 구현 실패 | masterless/storage는 별도 proposal |

### 특히 금지할 해석

- `E4M3/E5M2 둘 다 8 bit`이므로 adaptive 선택을 **압축률 개선**이라고 쓰지 않는다.
- FP8 shadow 성공을 **FP8 GEMM 가속 성공**이라고 쓰지 않는다.
- FP8 GEMM 성공을 **FP8 master-weight 학습 성공**이라고 쓰지 않는다.
- 100M screen을 최종 품질 동등성 증명으로 쓰지 않는다.
- `Δ≤0.0010`은 “완전히 동일”이 아니라 **현재 자에서 차이를 검출하지 못했다**고 쓴다.

---

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | ★Compute → observer → shadow → schedule을 조건부로 순차 검증 | 원인 분리, 비용 조기 중단, FP8 가속과 shadow 연구를 모두 얻음 | 전체 gate 통과 시 GPU 약 10h 이상 |
| **B** | FP8 compute C0~C3만 수행 | 가장 직접적인 속도 이득 검증, 구현 단순 | shadow precision 가설은 남음 |
| **C** | shadow observer/S1만 수행, GEMM은 기존 유지 | low-precision latent 가설만 값싸게 검증 | 현재 GPU의 FP8 hardware 가속을 활용하지 못함 |
| **D** | 아무것도 안 한다 | 비용 0, 기존 안정 경로 유지 | 학습속도/저정밀 shadow 축 미확인 |

### ★권장안과 근거

**A를 권장한다.**

단, “모든 단계를 승인 즉시 실행한다”는 의미가 아니다.

핵심은

\[
\boxed{\text{값싼 gate가 실패하면 즉시 종료}}
\]

하는 conditional design이다.

특히:

1. C0에서 실제 FP8 kernel이 안 잡히면 **0.1 GPU-h 수준에서 compute 실험 종료**
2. C1에서 속도 이득이 없으면 **compute 품질 실험 종료**
3. S0에서 E4M3가 사실상 전부 이기면 **adaptive E4M3/E5M2 구현 자체를 생략**
4. S1에서 FP8 shadow가 깨지면 **H/L schedule을 돌리지 않음**
5. S3까지 통과한 뒤에야 **실제 packed FP8/masterless 구현을 새 proposal로 연다**

이 순서는 현재 저장소의

> 값싼 진단 → 명시적 gate → 필요한 경우에만 고비용 학습

규약과 가장 잘 맞는다.

또한 compute precision과 shadow precision을 처음부터 묶지 않으므로, 결과가 좋든 나쁘든 **무엇이 원인이었는지 남는 실험**이 된다.

---

**상태: ⏳판단 대기**

승인 전 구현·배치 작성 없음.  
승인 시 현재 실험 번호 레지스트리를 다시 조회한 뒤 `test_plan/` 번호를 배정한다.