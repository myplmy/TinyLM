# 제안 — TinyLM의 anneal을 세 계약으로 분해하고 계측 뒤 개선한다

> **작성일**: 2026-09-15
>
> **승인일**: 2026-09-15
>
> **상태**: ✅권장 C안 승인 — A0~A2 구현·CPU fixture 완료, A3 사용자 GPU 실행은 `NOT_RUN`, A4 이후 미승인
>
> **분류**: 학습방법 / 양자화 / 학습률 스케줄

---

## 1. 배경 — 왜 지금 이 제안을 하나

TinyLM에서 “anneal”은 하나의 기법이 아니라 최소 세 가지다.

| 이름 | 현 코드 | 하는 일 | 기본 활성 |
|---|---|---|---|
| WSD LR cooldown | `trainer.py::_lr_factor` | 마지막 `decay_frac` 동안 LR을 peak의 0.1까지 cosine 감쇠 | `--sched wsd`를 명시한 표준 배치에서 활성 |
| ternary quantization anneal | `refresh_quant()`과 `anneal_start/end/shape` | forward weight를 FP와 ternary 사이에서 전이 | 항상 활성; 코드 기본 end 0.60 |
| 보조경로 제거 | `arena_end`, `lora_decay` | Arenas latent 또는 LoRA 완화 출력을 0으로 제거 | 해당 기능을 켰을 때만 활성 |

현행 선형 ternary 전이는

```text
W_forward = Wq + (1 - a(t)) * stopgrad(W - Wq)
```

이고, `a(t)`는 기본적으로 warmup 종료 뒤 5% 지점부터 선형 증가해 `anneal_end`에서 1이 된다.
WSD는 plateau 뒤 마지막 20%에서 `0.1 + 0.9*cosine`으로 감쇠한다. 두 스케줄은 동시에
움직이지만 독립 변수다.

현재 가장 큰 문제는 **코드 기본·공식 기준표와 실제 운용 명령이 다르다는 것**이다.

- `tinylm/train/trainer.py`와 registry 기본: `anneal_end=0.60`.
- [`EXPERIMENT_BASELINES.md`](../../docs/EXPERIMENT_BASELINES.md) 상단: P026/P035 결과에 따라 0.60 유지.
- 현재 루트의 실험 배치 10개: 모두 명시적 `--anneal-end 0.80`.
- P005/P005b/P088 등 최근 결과 재현 명령도 0.80이며, WSD 감쇠 시작 0.80과 정렬한다.

즉 **0.80이 성능으로 승격됐다는 단일 판정 없이 운영 표준이 된 상태**다. P026은 같은
2289-step 조건에서 0.80과 0.60의 차이를 1.07σ 이내로 판정했고, P035의 linear/step 2×2도
최대 0.0128로 검출하지 못했다. step은 `grad_max`가 linear보다 컸다
([결과 015](../../test_result/015_20260731102500_P026-cooldownQAT-스케줄정렬.md),
[결과 022](../../test_result/022_20260801100000_P035-어닐형태-효과없음-P026과함께종결.md)).

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

LR cooldown·quantization 전이·보조경로 제거를 독립 계약으로 계측해, 결과가 없는 정렬
관습 대신 **양자화 거리·코드 진동·품질·안정성으로 선택되는 anneal 정책**을 만든다.

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| anneal 용어·정본 표 | LR/quant/aux 스케줄의 소유 코드, 기본값, 명시값, 적용 범위 |
| 비학습 정적 검사 | 경계값 0/시작/끝/1에서 계수·로그·registry 일치 검사 |
| 양자화 동역학 계측 | 층별 normalized quantization distance, ternary code flip rate, occupancy, grad/update 지표 |
| 단계별 판정표 | 현재 0.80 유지, 0.60 복귀, adaptive/freeze 후보의 품질·안정성·비용 |
| 문서 정합 | 승인된 최종값만 CLI/config/기준표/계획 템플릿에 한 번에 반영 |

이 성과물은 “새 스케줄이 더 좋다”는 선결 결론을 만들지 않는다. 우선 지금의 0.60/0.80
이중 표준을 드러내고, 추가 복잡성이 실제 loss 또는 안정성을 사는 경우에만 기본값을 바꾼다.

## 4. 비용

| 항목 | 양 |
|---|---:|
| GPU | 단계 A0~A2는 0; A3 사용자 계측 trajectory ⚙0.3~0.8 GPU-h, 후보 대조는 별도 승인 시 ⚙2.5~5 GPU-h |
| AI 작업 | ⚙5~9 h — 계측·fixture·문서 정합 |
| ★사용자가 직접 해야 하는 일 | 현재 변경 뒤 스모크, 이어서 A3의 두 계측 trajectory와 계측-off 오염 대조 실행 |
| 디스크 | 계측 JSON ⚙10~100 MiB 외에 현재 trainer가 A3 세 run의 final/best를 저장하므로 최악 약 5.6 GiB(기존 d12 dense 체크포인트 크기 기준); 삭제는 별도 사용자 판단 |

## 5. 원리·근거

**우리 실측**

| 근거 | 값 | 출처 |
|---|---|---|
| WSD 자체 | full-cycle cosine 대비 `−0.0755 nats`, 6.3σ, 시간 비용 0 | [결과 015](../../test_result/015_20260731102500_P026-cooldownQAT-스케줄정렬.md) |
| quant end 0.60↔0.80 | 같은 2289 steps에서 최대 1.07σ, 채택 근거 미달 | 결과 015 |
| linear↔step | 2×2 모두 최대 0.0128 안; 효과 부호도 전이점에 따라 뒤집힘 | [결과 022](../../test_result/022_20260801100000_P035-어닐형태-효과없음-P026과함께종결.md) |
| step 안정성 | step `grad_max` 1.775/2.666, linear 1.036/1.253 | 결과 022 |
| WSD 세부 recipe | 20%·floor 0.1·cosine의 정확한 3요소 결합 원문은 없음 | [WSD 원문 감사](../../docs/20260912_WSD-decay0.2-floor0.1-cosine-근거조사.md) |
| 운영 불일치 | 코드·기준표 0.60, 현재 루트 배치 10/10은 0.80 | 2026-09-15 정적 실사 |

**외부 근거**

- [Compute-Optimal Quantization-Aware Training](https://arxiv.org/abs/2509.22935)은 FP 단계와
  QAT 단계의 최적 비율이 총 compute·모델 크기·bit width에 따라 달라지고, cooldown과 QAT를
  결합할 수 있다고 보고한다. 다만 이 논문은 TinyLM의 연속 FP↔ternary blend 공식을 직접
  검증한 것이 아니므로 0.80의 출처로 사용할 수 없다.
- Nagel et al., [Overcoming Oscillations in Quantization-Aware Training](https://proceedings.mlr.press/v162/nagel22a.html)은
  저비트 QAT에서 weight가 grid point 사이를 진동할 수 있음을 보이고 oscillation dampening과
  iterative freezing을 제안한다. TinyLM에는 현재 code flip/신뢰도 계측이 없어 이 기전을
  확인하거나 배제할 수 없다.
- Liu et al., [Oscillation-free Quantization for Low-bit Vision Transformers](https://proceedings.mlr.press/v202/liu23w.html)은
  confidence-guided annealing으로 신뢰도가 높은 weight부터 고정한다. Vision Transformer의
  2-bit 결과이므로 ternary LLM 기본값으로 바로 이식하지 않고 후보 원리로만 쓴다.
- Leconte et al., [ASkewSGD](https://proceedings.mlr.press/v206/leconte23a.html)은 quantized
  optimization을 annealed interval-constrained problem으로 다룬다. 현 STE blend와 목적은
  가깝지만 optimizer가 달라 독립 구현 후보이지 현재 스케줄의 직접 근거는 아니다.
- [FQ-Conv](https://arxiv.org/abs/1912.09356)는 bit/layer를 점진적으로 양자화하는 접근이
  수렴을 도울 수 있음을 보이지만 CNN·activation quantization 문맥이다.

## 6. 방법

### 6.1 먼저 계약을 분리한다

| 계약 | 독립변수 | 지금 확정 가능한 것 | 아직 모르는 것 |
|---|---|---|---|
| LR | `decay_frac`, floor, shape | WSD가 기존 cosine보다 좋음 | 0.2·0.1·cosine 각각의 최적성 |
| Quant | start, end, shape/adaptive rule | linear가 step보다 안정적이고 0.60/0.80 loss 차이는 미검출 | 코드 진동·grid 접근 동역학과 compute별 최적 전이 |
| Aux | `arena_end`, `lora_decay` | 끝에서 정확히 0이어야 배포 대가 0 | 각 보조기법에 맞는 최적 제거 시점 |

### 6.2 단계별 게이트

| 단계 | 무엇 | 비용 | ★다음으로 가는 조건 |
|---|---|---:|---|
| A0 정본 감사 | 모든 default·배치·계획·결과의 0.60/0.80 소유권을 표로 만든다 | GPU 0 | 변경 이유 없는 묵시값 0건 |
| A1 수학·직렬화 fixture | LR/quant/aux 경계계수, step/linear 의미, JSON 저장값을 검사한다 | GPU 0 | 경계·재개·로그가 정본과 일치 |
| A2 계측 구현 | 층별 `||W-Wq||/||W||`, code flip%, `{-1,0,+1}` 점유, grid margin, grad/update norm을 저빈도로 기록 | GPU 0 구현 | 계측 off가 비트 동일, on 오버헤드 사전 상한 이내 |
| A3 짧은 matched trajectory | 같은 부모·초기화·seed·data order에서 **처음부터** 시작한 0.60/0.80 두 짧은 trajectory로 동역학 차이만 확인 | ⚙0.3~0.8 GPU-h | 진동·거리 차이가 재현되며 계측 자체 오염 없음 |
| A4 최소 후보 대조 | **기존 P026/P035 반복이 아니라**, 현 승자 한 조건에서 current-linear와 confidence-freeze 또는 compute-aware phase 후보 1개만 비교 | ⚙2.5~5 GPU-h | loss가 현 계열 자를 넘고, grad/flip 악화 없음 |
| A5 승격 | 이긴 경우에만 CLI/config/registry/기준표/계획 템플릿 동시 갱신 | GPU 0 | 한 문서·코드가 같은 기본값을 말함 |

### 6.3 승인 뒤 구현 상태

| 단계 | 상태 | 구현·증거 |
|---|---|---|
| A0 | ✅문서 감사 | 코드 기본 0.60, 최근 명시 0.80, WSD와 quant/aux의 소유권을 이 문서에 분리 기록 |
| A1 | ✅`STATIC_ONLY` | `tinylm/train/anneal_schedule.py`에 LR·quant·aux 식을 분리하고 종전 LR 전 구간 정확 일치 CPU fixture 작성 |
| A2 | ✅구현·CPU fixture(`STATIC_ONLY`) | `--anneal-audit*` opt-in JSONL/계약: 유니크 TLinear 표본의 quant 거리·code flip·점유·경계여유·grad/update RMS. off면 계측 인스턴스와 계측 모듈을 import하지 않는 것은 정적으로 확인했지만, 실제 학습의 on/off 동일성과 오버헤드는 사용자 스모크·A3 전 `NOT_RUN` |
| A3 | `E2E_NOT_RUN` | 실제 모델·체크포인트·GPU trajectory와 계측 on/off 오염 검증은 사용자 실행 |
| A4~A5 | ⏳미승인 | A3 결과가 새 후보의 필요성을 보일 때만 별도 승인 |

처음 제안한 “같은 checkpoint를 재생”이라는 표현은 **동일한 후반 checkpoint에서 서로 다른
초반 anneal 이력을 복원할 수 없으므로 부정확했다**. A3는 같은 초기 상태에서 시작하는 두 fresh
trajectory로 정정한다. 고정 샘플 forward만으로는 optimizer update 뒤 code flip을 측정할 수 없다.

### 6.4 A3 사용자 실행 절차(배치 미작성)

1. `Z:\TinyLM`의 `collatz_torch` 활성 터미널에서 현재 변경 뒤 `run_smoke_check.bat`를 실행해
   실패 팔 0·exit-0 오류표지 0·계측 계약 오류 0을 확인한다.
2. 아래 첫 두 명령은 **같은 부모·seed·pool·250 steps**를 쓰고 `--anneal-end`와 출력 tag/path만
   바꾼다. 셋째는 0.80 팔에서 audit만 끈 오염 대조다. 기존 파일이 있으면 덮어쓰지 말고 새
   시각 경로를 쓴다.

```bat
set PYTHONIOENCODING=utf-8
python scripts\runlog.py --name anneal_a3_end060 -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.2 --seed 1337 --eval-every 250 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 250 --tokens 300M --pool-tokens 600M --exact-cache --tag anneal_a3_end060 --anneal-audit runs\audit\anneal_a3_end060.jsonl --anneal-audit-every 10 --anneal-audit-max-modules 8
python scripts\runlog.py --name anneal_a3_end080 -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 250 --tokens 300M --pool-tokens 600M --exact-cache --tag anneal_a3_end080 --anneal-audit runs\audit\anneal_a3_end080.jsonl --anneal-audit-every 10 --anneal-audit-max-modules 8
python scripts\runlog.py --name anneal_a3_off080 -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 250 --tokens 300M --pool-tokens 600M --exact-cache --tag anneal_a3_off080
```

3. 세 run 모두 exit 0·NaN/skip 0이어야 한다. 첫 두 run의 JSONL·`.contract.json`과 세 run의
   runlog를 회신한다.
4. `anneal_a3_end080`과 `anneal_a3_off080`만 audit on/off 오염 대조로 쓴다. 계측 on의
   `ms/step`은 방법의 속도로 인용하지 않는다.
5. A3는 동역학 진단이지 0.60/0.80 품질 재대결이 아니다. 250-step final loss로 기본값을 바꾸지 않는다.
6. 현 trainer는 세 run 모두 final/best 체크포인트를 저장한다. 실행 전 여유 공간 약 5.6 GiB를
   확보하고, 종료 뒤에도 `checkpoints.tsv` 재감사와 별도 사용자 삭제 승인 전에는 임의 삭제하지 않는다.

### 6.5 판정 규칙

1. 0.80은 최근 결과를 서로 비교하기 위한 **조건 고정값**으로는 유지하되, 우월한 기본값이라고
   부르지 않는다.
2. 새 방법은 final loss 하나만 보지 않는다. code flip, quantization distance, grad spike,
   wall time, 추가 상태·저장 비용을 함께 본다.
3. WSD knob와 quant anneal knob를 같은 팔에서 동시에 바꾸지 않는다.
4. compute-optimal QAT의 phase ratio는 모델/bit/compute 조건의 함수다. 300M에서 고른 고정
   fraction을 1.2B에 그대로 일반화하지 않는다.
5. adaptive/freeze가 이기지 않으면 복잡성을 채택하지 않고 현 linear를 유지한다.

## 7. 거절하면 못 하는 것

기존 0.80 명시 실험끼리의 비교와 현재 학습은 계속할 수 있다. 다만 코드 기본 0.60과 운용값
0.80의 불일치가 남고, anneal 효과를 loss 하나로만 보므로 grid 진동·전이 안정성의 원인을
알 수 없다. 새 adaptive 방법의 이득도 주장할 수 없다.

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| 세 anneal을 혼동 | LR·quant·LoRA 값을 한 “anneal 효과”로 합산 | 필드 namespace와 결과 조건서명 분리 |
| 묵시적 표준 변경 | 코드 default와 배치 명시값이 다름 | A0와 한 번의 동시 정합 패치 |
| 계측이 학습을 바꿈 | tensor copy/sync로 ms/step·메모리 증가 | 낮은 주기, detach·비동기 집계, off 비트동일 fixture |
| flip 지표 오판 | scale 변화만으로 code가 바뀌거나 layer 크기가 가중됨 | layer별/가중 평균 둘 다 기록, scale·occupancy 함께 보고 |
| 문헌 과잉 이식 | CNN/ViT의 freezing을 ternary LLM에 즉시 적용 | A3 동역학 확인 뒤 후보 하나만 A4로 개방 |
| 기존 무효 실험 반복 | P026/P035와 같은 0.60/0.80·linear/step을 다시 실행 | A4는 새 진단이 답을 바꿀 후보만 허용 |
| 장기 run 일반화 | 300M 승자를 1.2B에 자동 승격 | compute·tokens/parameter-byte를 조건축으로 기록 |

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | 실제 운용 0.80을 즉시 코드 기본으로 승격하고 문서를 맞춘다 | 단일값이 빠르게 생김 | P026/P035가 우월성을 보이지 않았으므로 관습을 사실로 승격 |
| **B** | 결과 015 판정대로 모든 새 명령을 0.60으로 되돌린다 | 코드·기준표와 일치, 단순 | 최근 결과 연속성이 끊기고 0.80 운용 전환의 원인을 설명하지 못함 |
| **C** | **계측 우선**: 새 실험값은 당분간 0.80로 명시 고정하고 A0~A3 후 후보 하나만 검증 | 기존 비교를 보존하면서 원인과 새 방법을 분리 | 구현·계측 비용이 들고 즉시 새 기본값을 주지 않음 |
| **D** | anneal 축을 영구 닫고 현 상태를 유지 | 비용 0 | 이중 표준과 미계측 진동 위험이 남음 |

### ★권장안과 근거

**C안**을 권장한다. 내부 결과는 WSD 자체는 강하게 지지하지만 ternary end 0.80이나 step
전이를 지지하지 않는다. 반면 최근 결과 대부분이 0.80로 이어져 단순 복귀도 새 교락을 만든다.
따라서 먼저 동역학을 보이는 계측을 만들고, 기존 결과를 반복하지 않는 후보 하나만 통과시키는
것이 가장 적은 GPU 시간으로 기본값과 방법론을 동시에 바로잡는 길이다.

### 승인 기록

- 2026-09-15: 사용자가 C안을 승인했다.
- 승인 범위는 A0~A3이다. A0~A2는 구현·CPU fixture까지 `STATIC_ONLY`, A3는 사용자 실행 전
  `E2E_NOT_RUN`이다. adaptive/freeze 후보(A4), 기본값 변경(A5), 실험 배치 작성은 승인되지 않았다.
