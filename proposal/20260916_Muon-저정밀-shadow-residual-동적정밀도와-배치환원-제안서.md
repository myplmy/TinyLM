# 제안 — Muon 저정밀 shadow에 explicit residual을 붙이고 WSD 구간별 정밀도를 바꾼다

> **작성** 2026-09-16 · **상태** ⏳판단 대기 · **분류** 실험계획  
> 양식: `proposal/README.md` §3. 아홉 절을 비우지 않는다.  
> **선결:** P022C shadow/write-back 트랙의 failure signature 또는 low-shadow 생존 조건 확인.  
> **범위:** Muon-owned matrix의 latent/shadow 저장 정밀도만 다룬다. Muon momentum 저정밀화, FP8 compute, global-batch 확대는 본 제안의 독립변수가 아니다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

TinyLM의 `TLinear.weight`는 현재 연속형 `nn.Parameter`이며, ternary forward weight와 별개인 **latent/shadow weight**다. 현재 ternary forward는 이 weight에서 `_wq`를 만들어 사용한다. 즉 배포용 ternary weight가 낮은 정밀도라고 해서 학습 중 latent 자체의 상주 메모리가 저정밀인 것은 아니다.

[P068](../test_plan/P068_학습-fp32를-어디까지-내릴-수-있나.md)은 현재 master/shadow와 gradient가 FP32이고 GEMM·activation은 이미 BF16임을 코드 실사로 확인했으며, 특히 WSD 감쇠 후반에는 작은 update가 저정밀 weight grid에서 사라질 가능성을 문제로 제기했다.

[P022C](../test_plan/P022C_FP8-compute-shadow-precision-분리.md)는 이를 이어서 `H=기존 FP32 shadow`, `L=검증된 low-precision write-back policy`로 정의하고 `static L`, `H→L`, `L→H`, `H→L→H`를 단계적으로 비교한다. 동시에 **fake write-back 성공은 실제 VRAM 절감 증거가 아니며, 실제 packed/masterless implementation과 error feedback은 후속 proposal로 분리**하도록 명시했다.

현재 optimizer는 일반 AdamW가 아니라 **행렬=Muon, 나머지=AdamW** 구조다. Muon-owned matrix에서는 gradient를 momentum에 누적한 뒤 Newton–Schulz orthogonalization과 형상별 scaling을 거쳐 update를 적용한다. 따라서 ECO처럼 quantization error를 곧바로 momentum에 넣는 것은 Muon의 비선형 update 변환과 섞인다. 반면 **post-Muon weight update 결과를 `저정밀 shadow + explicit residual`로 표현하는 방식은 Muon update 계산 자체를 바꾸지 않고 분리할 수 있다.**

외부에서도 master weight 제거 가능성은 확인되어 있다.

- Nikdan et al., **ECO: Quantized Training without Full-Precision Master Weights**, arXiv:2601.22101  
  https://arxiv.org/abs/2601.22101
- Zhao et al., **Direct Quantized Training of Language Models with Stochastic Rounding**, PMLR 304  
  https://proceedings.mlr.press/v304/zhao26b.html

ECO는 quantized parameter에 직접 update한 뒤 quantization error를 optimizer momentum으로 되돌리는 방법을 제안하지만, Muon의 Newton–Schulz update를 대상으로 한 방법은 아니다.

Direct Quantized Training은 high-precision shadow 없이 quantized persistent weight를 직접 학습하며 stochastic rounding을 사용한다. 이 역시 explicit temporal residual과는 다른 보상 방법이다.

따라서 이 제안은 **ECO를 Muon momentum에 그대로 이식하는 것이 아니라**, 다음의 분리된 표현을 먼저 검증한다.

`virtual shadow W = dequant(Q) + dequant(R)`

여기서:

- `Q`: 저정밀 persistent shadow
- `R`: quantization residual

이다.

---

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

**P022C에서 검증된 low-precision shadow policy `L`을 고정한 상태에서 explicit residual의 존재·정밀도·WSD 구간별 precision schedule만 독립적으로 바꾸어, Muon+ternary 학습 품질을 보존하면서 실제 persistent training memory를 줄일 수 있는지 확인하고, 확보한 VRAM을 global batch를 바꾸지 않은 physical microbatch 증가로 환원할 수 있는지 측정한다.**

핵심 독립변수는 세 단계로 분리한다.

1. residual 없음 → residual 있음
2. residual BF16 → residual 8-bit
3. residual 정밀도 고정 → WSD 진행에 따른 `R8→R16`

다음 항목은 모든 핵심 팔에서 고정한다.

- Muon momentum dtype
- Muon scale/LR recipe
- ternary anneal
- FP8 compute 설정
- global effective batch

---

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| residual 효용 가격표 | `L only / L+R16 / L+R8`의 paired validation CE |
| residual 정밀도 가격표 | R8와 R16의 reconstruction error·품질·저장 bytes |
| WSD precision schedule 가격표 | static R8 vs `R8→R16 @ WSD decay` |
| Muon-specific observer | post-Muon update RMS, reconstruction RMS, `ρ` |
| ternary-specific observer | reconstructed latent 사용 시 ternary state disagreement/F1 |
| 실제 storage 판정 | fake-write-back이 아닌 persistent FP32 shadow 제거 여부 |
| 메모리 가격표 | peak allocated/reserved와 실제 persistent bytes |
| batch 환원 가격표 | 동일 131K effective batch에서 최대 microbatch와 tokens/s |
| 후속 판정 | 고정 schedule 채택 / adaptive controller 후속 / 축 종료 |

가장 중요한 최종 산출물은 단순히 “FP8/INT8로 학습 가능하다”가 아니다.

다음 연결을 직접 측정한다.

**실제 persistent memory 절감 → physical microbatch 확대 → 동일 global batch에서 tokens/s 증가**

현재 TinyLM의 300M 표준 학습은 다음과 같다.

`seq=1024`

`micro_bs=8`

`accum=16`

따라서 한 optimizer update당 유효 토큰은:

`8 × 16 × 1024 = 131072`

이다.

본 제안에서는 Stage4까지 이 값을 바꾸지 않는다.

---

## 4. 비용

절대 GPU-hour는 현 Muon recipe의 실제 300M runtime이 확정될 때까지 고정하지 않고 다음처럼 정의한다.

`H300 = 동일 장비에서 현행 Muon+WSD 300M baseline 1회`

| 항목 | 양 |
|---|---:|
| Stage0 observer·계약·memory upper bound | ⚙0.05~0.10 H300 |
| Stage1 static residual 100M 2개 신규 팔 | ⚙0.67 H300 |
| Stage2 residual schedule 100M 1개 신규 팔 | ⚙0.33 H300 |
| Stage3 실제 packed/storage winner 100M | ⚙0.33 H300 |
| Stage4 microbatch/timing sweep | ⚙0.05~0.15 H300 |
| Stage5 300M winner + direct baseline | ⚙2.0 H300 |
| Stage6 다른 seed 확인, 채택 후보일 때만 | ⚙2.0 H300 |
| **최대 조건부 GPU 비용** | **⚙5.5 H300 이하** |
| AI/코드 작업 | ⚙4~8 engineer-h |
| 사용자가 직접 해야 하는 일 | ⚙30~60 min hands-on |
| 임시 checkpoint/log | ⚙5 GB 이하 |

Stage0에서 `H300`과 실제 candidate parameter 수를 기록한 뒤 절대 GPU-hour로 환산한다.

현재 승인 연구 큐의 GPU hard cap에 자동으로 포함시키지 않는다.

**proposal 승인 ≠ GPU 예산 자동 편성**으로 둔다.

---

## 5. 원리·근거

### 5.1 우리 코드/실측에서 이미 확인된 것

| 근거 | 확인된 내용 | 출처 |
|---|---|---|
| latent/shadow | `TLinear.weight`는 연속 `nn.Parameter` | `tinylm/model/ternary.py` |
| ternary forward | latent에서 ternary `_wq` 생성 | `tinylm/model/ternary.py` |
| Muon state | matrix마다 momentum buffer를 유지 | Muon optimizer 구현 |
| Muon update | momentum 이후 Newton–Schulz와 scaling 수행 | Muon optimizer 구현 |
| WSD | optimizer update에 WSD LR schedule 적용 | trainer |
| precision 선행축 | P022C가 shadow format/scaling/write-back/H-L schedule을 소유 | P022C |
| 후속 분리 | ECO/error-feedback와 실제 masterless storage는 별도 proposal 대상으로 남김 | P022C 승인 제안서 |
| 저정밀 위험 | WSD 후반 작은 update와 shadow precision 문제를 P068이 이미 제기 | P068 |
| batch 기준 | 300M 표준 effective batch 131K = `8×16×1024` | 실험계획목록 |

### 5.2 핵심 수치 모델

Muon이 한 optimizer step에서 계산한 최종 적용 예정 update를 다음처럼 둔다.

`ΔW_t`

그때 고정밀로 계산한 가상 weight는:

`W*_t = W_(t-1) - ΔW_t`

이다.

저장 단계는 다음처럼 정의한다.

`Q_t = Quantize_L(W*_t)`

`r_t = W*_t - Dequantize(Q_t)`

`R_t = Quantize_R(r_t)`

`W̃_t = Dequantize(Q_t) + Dequantize(R_t)`

여기서 실제 storage representation과 원래 가상 weight 사이의 오차는:

`ε_t = W*_t - W̃_t`

이다.

observer의 핵심 지표는:

`ρ_t = RMS(ε_t) / max(RMS(ΔW_t), tiny)`

로 둔다.

### 5.3 왜 gradient가 아니라 post-Muon update와 비교하나

Muon에서는 다음 변환이 일어난다.

`gradient`

→ `momentum`

→ `Nesterov`

→ `Newton–Schulz orthogonalization`

→ `shape scaling`

→ `learning-rate scaling`

→ `actual parameter update`

따라서 raw gradient 크기와 quantization residual을 직접 비교하면 실제 적용되는 parameter update에 대한 distortion을 정확히 나타내지 않는다.

본 실험에서는 반드시 **최종 post-Muon update `ΔW` 기준**으로 계측한다.

### 5.4 ternary-specific 계측

TinyLM은 latent weight가 조금 달라져도 ternary threshold 경계에서 forward state가 불연속적으로 달라질 수 있다.

따라서 단순 RMS reconstruction error 외에 다음을 기록한다.

- ternary code disagreement rate
- `0 → ±1` transition disagreement
- `±1 → 0` transition disagreement
- sign disagreement
- group alpha relative error
- ternary precision
- ternary recall
- ternary F1

비교 대상은 동일 step의:

`Ternary(W*_t)`

와

`Ternary(W̃_t)`

이다.

### 5.5 외부 근거

#### R1 — ECO

Nikdan et al., **ECO: Quantized Training without Full-Precision Master Weights**

arXiv:2601.22101

https://arxiv.org/abs/2601.22101

ECO는 full-precision master weight를 제거하고 low-precision persistent weight에 직접 update를 적용한 뒤 quantization error를 optimizer state로 보상한다.

본 proposal에 쓰는 근거는:

- low-precision persistent weight 직접 학습 가능성
- naive direct write-back의 update loss 문제
- error compensation의 필요성

이다.

단, ECO의 optimizer momentum error injection을 Muon에 그대로 적용할 수 있다고 가정하지 않는다.

#### R2 — Direct Quantized Training

Zhao et al., **Direct Quantized Training of Language Models with Stochastic Rounding**

PMLR 304

https://proceedings.mlr.press/v304/zhao26b.html

본 proposal에 쓰는 근거는:

- full-precision latent/master 없이 직접 quantized weight를 학습할 수 있음
- stochastic rounding이 작은 update 소실을 완화할 수 있음
- ternary persistent weight 학습도 검증 대상에 포함됨

이다.

그러나 stochastic rounding은 본 proposal의 explicit residual과 동일한 메커니즘이 아니다.

---

## 6. 방법

### Stage0 — 선결·계약·이론 상한부터 잰다

P022C가 아직 low-shadow S0~S3를 완료하지 않았으므로 본 proposal은 즉시 full implementation으로 가지 않는다.

### Stage0a — P022C trigger 확인

다음 두 조건 중 하나 이상이 충족되어야 residual 트랙을 연다.

1. low shadow direct write-back/SR가 invisible-update 또는 write-back error signature와 함께 실패
2. low shadow 품질은 생존했지만 persistent FP32 shadow 제거가 다음 메모리 병목으로 남음

둘 다 아니면 본 proposal은 `NOT_RUN`으로 유지한다.

---

### Stage0b — memory upper-bound audit

현 baseline의 Muon-owned matrix parameter 수를:

`N_M`

으로 측정한다.

다음 실제 bytes를 계산한다.

- FP32 shadow
- L8 shadow + scale metadata
- L8 shadow + R8 + metadata
- L8 shadow + R16 + metadata

예를 들어 metadata를 무시한 이상적 하한은:

`FP32 shadow = 4 × N_M bytes`

`L8 = 1 × N_M bytes`

`L8 + R8 = 2 × N_M bytes`

`L8 + R16 = 3 × N_M bytes`

이다.

그러나 실제 판정에는 반드시:

- scale tensor
- padding
- temporary dequant buffer
- optimizer scratch
- allocator fragmentation

까지 포함한다.

동시에 현재 microbatch에서 다음을 실측한다.

`peak_alloc(micro=m)`

`peak_alloc(micro=m_next)`

따라서 다음 microbatch 단계로 올라가기 위해 필요한 추가 메모리는:

`ΔVRAM_micro = peak_alloc(m_next) - peak_alloc(m)`

이다.

#### throughput branch gate

다음 조건을 만족해야 Stage4의 microbatch 환원 분기를 연다.

`예상 회수 bytes ≥ 1.2 × ΔVRAM_micro`

통과하지 못하면:

- 알고리즘 품질 연구는 계속 가능
- memory-saving 결과는 기록 가능
- **microbatch 증가를 통한 throughput 향상 주장은 종료**

한다.

---

### Stage0c — observer only

기존 FP32 weight는 그대로 유지한다.

실제 optimizer trajectory를 변경하지 않고, 각 optimizer step에서 후보 representation을 simulation한다.

대상:

- `L only`
- `L + R8`
- `L + R16`

측정:

- `RMS(ΔW)`
- `RMS(ε)`
- `ρ`
- residual max
- residual p99
- residual saturation rate
- exact frozen-update fraction
- ternary state disagreement
- ternary F1

구간은 최소:

- WSD stable 구간
- WSD decay 초반
- WSD decay 후반

으로 나눈다.

이 단계에서는 FP32 shadow가 여전히 존재하므로:

**VRAM 절감이라고 기록하지 않는다.**

---

### Stage1 — residual 자체의 순효과

P022C에서 정한 low-shadow policy `L`을 고정한다.

100M screen:

| 팔 | shadow | residual | 기준과의 유일한 차이 |
|---|---|---|---|
| A | `L` | 없음 | P022C low-shadow control |
| B | `L` | BF16 | explicit residual 추가 |
| C | `L` | 8-bit | residual만 BF16→8-bit |

#### Stage1 판정

A가 P022C에서 동일 signature로 이미 실행되어 있다면 재사용한다.

동일 signature의 조건:

- optimizer
- Muon scale
- learning rate
- WSD
- seed
- dataset
- token budget
- quantizer format
- scale granularity
- rounding
- ternary configuration

이 모두 동일해야 한다.

하나라도 다르면 direct control을 다시 실행한다.

100M gate:

- NaN 없음
- skip 증가 없음
- control 대비 paired full-val 열화 `≤ +0.01`

추가 판정:

- `B ≈ A`이면 explicit residual 이득 없음 → residual 축 종료
- `B < A`이면 residual 효과 확인 → C로 진행
- `C-B > +0.01`이면 R8 종료, R16만 생존
- `C≈B`이면 R8를 기본 후보로 유지

---

### Stage2 — WSD 진행에 따른 residual precision

Stage1에서 R8가 생존한 경우에만 연다.

master/shadow policy는 P022C 승자를 그대로 사용한다.

residual만 바꾼다.

| 팔 | WSD stable | WSD decay |
|---|---|---|
| S0 | R8 | R8 |
| S1 | R8 | R16 |

핵심 schedule:

`(L,R8) → (L,R16)`

이다.

전환점은 사후 최적화하지 않는다.

첫 실험의 transition point는:

**WSD decay 시작 시점**

으로 고정한다.

예를 들어 `decay_frac=0.2`라면:

`progress = 0.8`

지점이다.

#### P022C master schedule과의 결합

P022C 승자가 `H→L`이면:

`H → (L,R8) → (L,R16)`

으로 둔다.

P022C 승자가 `H→L→H`이면:

`H → (L,R8/R16) → H`

로 둔다.

즉 본 proposal에서 master/shadow schedule을 다시 탐색하지 않는다.

### Stage2에서는 하지 않는 것

- 60/70/80/90% transition sweep
- layer-wise precision controller
- `rho` adaptive controller
- gradient precision 변경
- Muon momentum precision 변경

이들은 첫 fixed schedule이 유효한 뒤 후속 proposal에서 다룬다.

---

### Stage3 — 실제 persistent storage를 연다

Stage0~2까지는 numerical semantics 검증이다.

Stage3부터만 **실제 memory saving**을 주장할 수 있다.

#### PASS 조건

persistent FP32 `TLinear.weight`가 실제로 없어야 한다.

다음 구조는 PASS가 아니다.

`FP32 weight + fake FP8 Q + residual`

왜냐하면 메모리를 줄이지 않고 오히려 늘리기 때문이다.

목표 상태는 개념적으로:

`persistent Q`

`persistent R`

`Muon optimizer state`

만 저장하고, 필요한 순간에:

`W̃ = dequant(Q) + dequant(R)`

를 재구성하는 것이다.

#### 구현 규칙

- default-off = 기존 코드 경로와 동일
- Muon momentum FP32 유지
- gradient dtype 현행 유지
- ternary quantizer 규칙 변경 금지
- Muon scale 변경 금지
- WSD 변경 금지
- state dict에 Q/R 저장
- precision phase 저장
- resume 시 residual 누락을 조용히 허용하지 않음
- incompatible checkpoint는 hard error
- packed representation과 fake representation을 로그에서 구분

#### 체크포인트 계약

checkpoint에는 최소 다음 metadata를 저장한다.

- shadow format
- residual format
- scale granularity
- scale values/state
- current precision phase
- WSD progress 또는 global step
- quantization policy version

resume 시 해당 정보가 일치하지 않으면:

`RuntimeError`

또는 동등한 명시적 실패를 발생시킨다.

---

### Stage4 — 절약한 VRAM을 physical microbatch로 환원

global effective batch는 고정한다.

현재:

`8 × 16 × 1024 = 131072`

후보:

`16 × 8 × 1024 = 131072`

`32 × 4 × 1024 = 131072`

`64 × 2 × 1024 = 131072`

`128 × 1 × 1024 = 131072`

가능한 범위에서 순차 검사한다.

따라서 변하지 않는 것은:

- tokens/update
- optimizer step 수
- WSD horizon
- ternary anneal horizon
- Muon update 횟수
- global token exposure

이다.

#### Stage4 측정

- `ms_step_median`
- `ms_step_p10`
- `ms_step_p90`
- tokens/s
- `torch.cuda.max_memory_allocated`
- `torch.cuda.max_memory_reserved`
- maximum feasible physical microbatch
- OOM 여부
- compile/recompile 횟수

#### efficiency gate

다음 중 하나 이상을 만족해야 실용 후보로 남긴다.

1. 실제 peak allocated 감소가 예상 persistent 절감량의 80% 이상
2. physical microbatch가 최소 한 단계 증가하고 tokens/s가 baseline보다 `≥5%` 증가

둘 다 아니면:

**알고리즘적으로는 성공했어도 practical training optimization으로 채택하지 않는다.**

5% 미만 speed 차이는 timing noise 가능성이 있으므로 speed 채택 근거로 쓰지 않는다.

---

### Stage5 — 300M direct paired 확인

Stage1~4 승자 하나만 300M으로 승격한다.

비교:

`current Muon baseline`

vs

`Q+R winner`

같은 조건에서 direct paired 실행한다.

측정:

- final full-val CE
- best full-val CE
- train CE
- CE-vs-token curve
- stable 구간 `ρ`
- decay 구간 `ρ`
- residual saturation
- ternary disagreement
- ternary F1
- peak allocated
- peak reserved
- maximum microbatch
- tokens/s
- total wall-clock
- wall-clock to same CE

품질 판정은 실행 시점의:

`scripts/_rulers.py`

가 선택한 **동일 Muon 계열 ruler**를 사용한다.

과거 AdamW/tied 계열의 `2σ` 값을 복사해서 쓰지 않는다.

---

### Stage6 — 채택 후보일 때만 다른 seed

Stage5에서 다음 두 조건을 모두 통과한 경우에만 연다.

1. 품질이 current ruler 안에서 동급 또는 우세
2. 실제 memory/throughput 이득이 efficiency gate 통과

다른 seed에서:

`baseline vs winner`

한 쌍을 추가한다.

최종 채택 조건:

- 두 seed에서 품질 방향 일치
- 두 seed에서 memory saving 유지
- throughput 방향 일치
- catastrophic residual growth 없음

단일 seed만으로 기본 training recipe를 변경하지 않는다.

---

## 7. 거절하면 못 하는 것

P022C 자체는 이 proposal 없이 계속 수행할 수 있다.

거절해도 다음은 가능하다.

- FP8 compute 실험
- static low-shadow 실험
- E4M3/E5M2 비교
- stochastic rounding 실험
- 기존 H/L precision schedule

따라서 이 proposal을 거절한다고 기존 precision 연구가 막히지는 않는다.

다만 다음 질문에는 답하지 못한다.

1. Muon에서 explicit residual이 low-shadow write-back loss를 실제로 보상하는가
2. residual precision을 WSD 진행에 따라 바꾸는 것이 static precision보다 효율적인가
3. low-shadow 성공이 실제 persistent VRAM 절감으로 이어지는가
4. 그 VRAM 절감이 physical microbatch 증가와 tokens/s 개선으로 이어지는가

즉 P022C 이후의 **실제 masterless training viability**는 미확인으로 남는다.

---

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| P022C와 중복 | 같은 static low-shadow를 다시 측정 | P022C `L`과 control 승계 |
| fake quant를 memory saving으로 오독 | FP32 `weight`와 Q/R이 동시에 존재 | Stage2까지 메모리 절감 주장 금지 |
| Q+R 절감량이 너무 작음 | activation VRAM에 묻힘 | Stage0 byte upper-bound gate |
| scale metadata가 예상보다 큼 | 실제 bytes가 이론값 초과 | tensor별 실물 byte accounting |
| temporary dequant buffer가 절감 상쇄 | peak VRAM 감소 없음 | Stage3 peak allocated 직접 측정 |
| Muon momentum과 residual 의미 혼동 | optimizer trajectory가 달라짐 | momentum injection 금지 |
| Newton–Schulz 전 residual 삽입 | 다른 optimizer가 되어버림 | post-Muon update 뒤에서만 적용 |
| R8 residual도 작은 update를 잃음 | `rho`, saturation 증가 | R16 sentinel |
| WSD 후기만 보고 사후 transition 튜닝 | schedule overfit | 첫 transition은 decay start 고정 |
| precision과 batch를 동시에 변경 | 품질 원인 불명 | Stage4 전까지 micro/accum 고정 |
| global batch가 바뀜 | optimization dynamics 교락 | `micro×accum×seq=131072` assert |
| gradient dtype이 함께 낮아짐 | shadow 효과와 gradient 효과 혼재 | gradient dtype 현행 유지 |
| Muon momentum까지 양자화됨 | residual 효과와 optimizer-state 효과 혼재 | momentum FP32 고정 |
| resume 때 residual 초기화 | trajectory discontinuity | state 누락 시 hard error |
| ternary threshold 경계 증폭 | 작은 latent 오차가 code 변경 | ternary disagreement/F1 측정 |
| 속도 결과가 allocator noise | 2~3% 차이가 세션 drift와 유사 | same-session direct pair |
| compile graph 변화 | 첫 step만 느려짐/빨라짐 | warmup 제외 후 median 사용 |
| adaptive controller를 너무 빨리 구현 | threshold·thrashing 새 교락 | fixed schedule 성공 뒤 별도 proposal |

### 금지할 해석

다음 표현은 Stage3 이전에 사용하지 않는다.

- “VRAM을 절감했다”
- “master weight를 제거했다”
- “8-bit training memory가 실현됐다”

Stage0~2는 fake/simulated numerical experiment일 수 있기 때문이다.

또한 다음을 같은 결과로 취급하지 않는다.

`low CE degradation`

과

`actual storage reduction`

과

`throughput improvement`

이 세 가지는 각각 독립적으로 측정한다.

---

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | **P022C 뒤에 explicit Q+R → residual precision → WSD schedule → real storage → microbatch 순으로 연다** | 원인분리가 가장 강하고 최종적으로 실제 VRAM/tok/s까지 측정 가능 | actual storage 구현 난이도 높음 |
| B | ECO처럼 quantization error를 Muon momentum에 직접 흡수 | 별도 residual buffer를 줄일 가능성 | Newton–Schulz 비선형성 때문에 ECO와 동일하다고 볼 수 없음 |
| C | P022C stochastic rounding만 사용 | 추가 residual state 불필요 | SR만으로 충분한지 미확인, deterministic reconstruction error 분석 어려움 |
| D | FP32→BF16 shadow만 사용 | 구현 간단 | 8-bit memory 한계 미확인, 후기 update resolution 문제 가능 |
| E | 처음부터 adaptive `rho` controller | layer/time별 precision 최적화 가능 | threshold·thrashing·runtime overhead까지 새 독립변수 증가 |
| F | direct persistent ternary + residual | 이론상 shadow storage 최소 | residual이 사실상 hidden continuous master가 될 위험, ternary grid 지나치게 거침 |
| G | 아무것도 안 한다 | 비용 0 | FP32 shadow 유지, memory→batch 이득 미확인 |

### ★권장안과 근거

**A를 권장한다. 단, 즉시 구현하지 않고 P022C shadow gate 뒤의 조건부 후속으로 둔다.**

이유는 세 가지다.

첫째, P022C가 이미:

- static shadow
- format
- scaling
- rounding
- H/L schedule

을 담당한다.

P022C를 건너뛰고 residual까지 동시에 넣으면:

`format 효과`

`rounding 효과`

`residual 효과`

를 분리할 수 없다.

둘째, Muon에서는 ECO식 momentum compensation보다 **post-Muon explicit residual**이 optimizer semantics를 덜 변경한다.

Muon은 단순 SGD/Adam update가 아니라 momentum 이후 Newton–Schulz를 거치므로, error를 momentum 앞이나 안쪽에 주입하면 update 방향 자체가 달라질 수 있다.

셋째, 연구의 최종 목적은 저정밀 표현 자체가 아니라 **실제 학습비용 절감**이다.

따라서 최종 채택선은:

`낮은 CE 열화`

만으로 두지 않는다.

반드시:

`실제 FP32 persistent shadow 제거`

→ `VRAM 감소`

→ `physical microbatch 증가 가능 여부`

→ `동일 global batch에서 tokens/s 개선`

까지 측정한다.

---

## 승인 후에만 할 일

본 proposal이 승인된 뒤에만 다음을 수행한다.

1. 현재 사용 가능한 실험번호 확인
2. `test_plan/` 정식 계획서 생성
3. `test_plan/README.md` 색인 추가
4. observer 구현
5. Q/R storage abstraction 구현
6. 신규 CLI/config flag 등록
7. run JSON metadata 추가
8. `scripts/flag_whitelist.tsv` 갱신
9. checkpoint/resume contract 구현
10. default-off regression test
11. Stage0 batch 작성
12. Stage0 통과 후에만 Stage1 batch 작성

승인 전에:

- P번호 선점
- 실제 training implementation
- batch 생성
- experiments.tsv 등록
- 기본값 변경

을 하지 않는다.

## 비판 검토 부록 — Muon·저정밀 문헌과 구현 계약 보완

### A. 추가 선행연구

원문의 ECO와 Direct Quantized Training은 full-precision master를 없애는 직접 근거로 적절하다.
하지만 Muon 자체의 optimizer-state 저정밀화 연구가 빠져 있어 “momentum은 고정한다”는 선택을
외부 대안과 비교하기에 부족했다. 다음 원문을 함께 본다.

- ECO: https://arxiv.org/abs/2601.22101
- Direct Quantized Training: https://proceedings.mlr.press/v304/zhao26b.html
- MuonQ: https://arxiv.org/abs/2605.11396
- Effective Quantization of Muon Optimizer States: https://arxiv.org/abs/2509.23106
- Floating Point Quantization of LLM Training: https://arxiv.org/abs/2510.21314

MuonQ는 Muon state의 방향 보존형 저비트 표현과 최대 7.3배 state-memory 감축을, 별도 Muon
state 연구는 blockwise 8-bit로 최대 62% state-footprint 감축을 보고한다. 이는 본 제안의
shadow-weight residual과 같은 방법은 아니지만, 전체 학습 메모리에서 shadow만 줄이는 안의
기회비용을 평가하는 필수 대조다.

### B. 구현 전에 닫아야 할 결함

1. **숨은 master 금지**: `Q+R`의 유효 정밀도가 16~24bit라면 단순 분할 master가 될 수 있다.
   residual entropy·dynamic range·유효 bit·zero rate를 보고하고, full-size 고정밀 persistent
   tensor, optimizer reference, storage alias가 없음을 hard assertion으로 검사한다.
2. **update 의미 단일화**: `W=dequant(Q)+dequant(R)`에서 post-Muon update를 적용한 뒤 Q를
   requantize하고 그 오차를 R로 보내는 순서, Q/R scale refresh 주기, residual clipping,
   stochastic rounding을 한 식으로 고정한다. Q와 R을 따로 update해 이중 양자화하지 않는다.
3. **P022C 출구조건**: static L이 실제 packed/masterless 상태로 품질·메모리 문턱을 이미
   만족하면 residual 복잡성을 열지 않는다. P022C가 fake write-back에 머물면 본안의 storage
   단계도 열지 않는다.
4. **정밀도 스케줄의 관측 선결**: WSD decay 경계만으로 R8→R16을 정당화할 수 없다. update/ULP,
   residual RMS와 post-Muon update RMS의 비 `rho`, ternary disagreement가 실제로 decay에서
   바뀌는지 observer가 먼저 보여야 한다.
5. **최악 phase 메모리**: 후반 R16이 peak라면 앞 단계의 R8 절감으로 microbatch를 늘렸다가
   decay에서 OOM이 날 수 있다. global batch는 최악 phase에서도 고정 가능해야 하며, phase별
   재할당·microbatch 변경은 독립변수로 금지한다.
6. **전체 메모리 분해**: FP32 Muon state, gradient, activation, temporary dequant가 shadow
   절감보다 클 수 있다. Stage0은 persistent/temporary/peak를 분리하고 Muon-state quantization
   대안과 같은 표에서 비교해야 한다.
7. **비열등 문턱**: 원문의 `B≈A`와 `≤+0.01`은 단일 점 기준으로 너무 넓다. 현재
   `scripts/_rulers.py`의 조건별 자와 paired CI를 사용하고 최소효과·비열등 margin을 사전등록한다.
8. **resume 계약**: Q/R, scale, precision phase, WSD progress가 checkpoint round-trip 뒤
   동일해야 한다. load 직후 고정밀 W를 영구 materialize하지 않는지도 검사한다.

### C. 수정된 게이트

| 게이트 | 필수 관측 | 중단선 |
|---|---|---|
| R0 P022C 선결 | 실제 packed/masterless static L과 failure signature | fake-only면 저장 실험 중단 |
| R1 observer | update/ULP·rho·disagreement의 WSD 구간별 분포 | decay 변화가 없으면 동적 R8→R16 보류 |
| R2 storage proof | hidden master 0, physical peak/RSS 실측 | logical byte만 줄면 중단 |
| R3 static residual | paired 품질·skip·resume·메모리 | 현 ruler 밖 또는 peak 절감 없음이면 중단 |
| R4 dynamic precision | 최악 phase에서도 batch 고정, R8→R16 이득 | OOM/phase batch 변경이면 무효 |
| R5 throughput | 동일 global batch와 더 큰 physical microbatch를 분리 비교 | batch·kernel 교락 시 재설계 |
| R6 scale/seed | 300M 뒤 최소 2 seed | 방향 미재현이면 기본값 후보 탈락 |

### D. 최종 판단

**조건부 승격 타당(A+)**이다. 가장 먼저 열 것은 Q/R 구현이 아니라 P022C 결과를 입력으로 한
observer와 전체 학습 메모리 분해다. shadow residual과 Muon-state quantization을 경쟁 대안으로
비교하고, 실제 packed/masterless 증거가 있는 경로만 다음 단계로 보낸다. 이 부록은 구현 승인이나
P번호 선점이 아니며, 사용자 승인 전 계획서·코드·배치·기본값을 만들지 않는다.
을 하지 않는다.