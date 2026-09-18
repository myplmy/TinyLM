# 제안 — 레이어 상태 진단은 채택하되 학습률 재가중·연산 생략·재활성화를 분리한다

> **작성** 2026-09-18 · **상태** 🔄권장 B안 승인·P091 흡수 진행 중 · **분류** 실험계획 전 타당성 검토 / 학습 최적화
> 양식: [`proposal/README.md`](README.md) §3. **아홉 절을 비우지 않는다.**
>
> **검토 대상**: `ai_dev_tool/temp_20260917_레이어-상태기반-학습연산-재배분-제안서(검토용).md`
> **독립 보존 범위**: 이 문서는 검토 대상의 문제의식·수식·A~D안·수치 가정·비용·근거·제외안을
> 다시 적고 판정을 붙인다. 원본 temp 문서가 나중에 삭제돼도 이 문서만으로 제안과 검토 결과를
> 복원할 수 있다. 이번 작업에서는 원본을 수정하거나 삭제하지 않는다.
>
> **승인 기록(2026-09-18):** 사용자가 권장 B안을 승인했다. 중복 P번호를 만들지 않고
> [P091 §4.1](../test_plan/P091_Muon후반-적응적-블록-확장-재학습.md)에 R0~R3 계약을
> 흡수했다. R1 구현·CPU fixture, 사용자 smoke, R2/R3 모델·GPU 진단과 B/C 후속 축은 남아 있어
> `-approved-on-going` 상태다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

검토 대상은 “모든 레이어에 매 step 같은 학습 계산을 쓰는 대신, 현재 상태에 따라 계산을
재배분하자”는 문제를 제기했다. 핵심 진단은 다음 두 축이다.

### 1.1 원안의 두 진단량

1. **정규화된 업데이트 활동도 `U_l`**

   ```text
   U_l = EMA(||ΔW_l,grad|| / (η_t ||W_l|| + ε))
   ```

   원안은 가능한 경우 weight decay 성분을 빼고 gradient-driven update만 보며, 값이 작으면
   “현재 거의 학습하지 않는 층” 후보로 해석한다.

2. **우회 민감도 `S_l`**

   ```text
   S_l = CE(block l bypass) - CE(normal)
   ```

   고정된 진단 패널에서 한 논리 레이어의 기여를 우회했을 때 CE가 얼마나 나빠지는지 측정한다.
   값이 크면 현재 함수에서 중요한 층, 작으면 우회 영향이 작은 층으로 해석한다.

원안은 `S/U` 사분면을 다음처럼 읽는다.

| 상태 | 원안 해석 | 원안 행동 후보 |
|---|---|---|
| `S↑, U↑` | 중요하고 활발히 학습 | 유지 |
| `S↑, U↓` | 중요하지만 정체 | 학습률 확대 또는 “재활성화” |
| `S↓, U↑` | 현재 중요도는 낮지만 학습 중 | 관찰·보수적 유지 |
| `S↓, U↓` | 중요도·활동 모두 낮음 | skip/freeze 후보. 단 즉시 제거하지 않음 |

이 문제의식은 타당하다. TinyLM에도 이미 업데이트 계측기와 레이어 잔차 gate가 있고,
후반 국소 재학습을 다루는 승인 계획 P091이 있다. 반면 현재 모델은 논리 레이어와 물리 파라미터가
1:1이 아니며, CLA K/V 소유관계와 MLP 공유가 있다. 따라서 원안의 “20개 독립 block” 전제와
임의 block bypass는 그대로 적용할 수 없다.

### 1.2 원안이 제시한 A~D안과 실행 순서

| 안 | 원안 내용 | 원안이 기대한 효과 |
|---|---|---|
| A | 현행 dense 학습 기준선 | 품질·시간·메모리 기준 |
| B | blockwise learning rate | sharpness 또는 상태에 맞춘 층별 학습률로 수렴 가속 |
| C | `S/U` 기반 선택적 layer skip | 낮은 중요도 층의 forward/backward를 생략해 실제 연산 절감 |
| D | `S↑, U↓` 후보에 짧은 “dormant resuscitation”을 적용하고 keep/skip 재판정 | 정체한 중요 층을 되살리거나 실제 불필요 후보를 가름 |

원안은 최대 세 개의 full trajectory를 `A → B → D` 순으로 두고 C를 fallback 또는 후속안으로
남겼다. D는 같은 checkpoint·token order·seed에서 microbranch를 만들고, 후보층 LR `×2`,
다른 층 LR `×0.5~1`, 약 `50~100 step` 뒤 held-out CE가 불확실성보다 좋아지고 spike가 없으면
유지하자는 설계다. C는 낮은 `U` 하위 `20~25%`와 낮은 `S`를 후보로 삼아 skip 비율을
`10% → 20%`로 올리며, 최종적으로 wall-clock `5~10%` 개선을 목표로 한다.

원안은 과거 P002의 20-block·300M 조건에서 dense 약 `97.5분`, tied 약 `90분`, loss
`3.7797`을 출발점으로 들고 “아직 덜 학습된 조건에서 레이어별 계산 배분이 이득일 수 있다”고
보았다. 그러나 이 수치는 현재 Muon·CLA·평가 조건의 기준선이 아니라 역사적 관측이므로,
현재 실험의 시간·노이즈·품질 gate로 재사용할 수 없다.

### 1.3 이번 검토의 결론

**원안은 `분할·흡수 후 조건부 채택`이 타당하다.** `S/U` 진단과 “dormant가 곧 redundant는
아니다”라는 원칙은 살린다. 그러나 B와 D는 forward/backward FLOPs를 줄이지 않으므로
“연산 절감”이 아니라 **업데이트 압력 재배분**으로 이름을 바꾼다. 실제 연산 절감은 C만 주장할
수 있고, 그것도 정적 skip 패턴이 backend에서 실제로 생략되는지 측정한 뒤에만 가능하다.

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

논리 레이어의 함수적 민감도와 물리 파라미터의 실제 업데이트 활동도를 분리 계측하고, 그 신호가
후속 개입의 **실현 이득을 예측하는지** 먼저 검증한 뒤, 검증된 신호만 기존 P091 또는 별도
단일변수 실험으로 넘긴다.

이번 문서의 독립변수는 아직 학습 기법이 아니다. 첫 질문은 `S/U` selector의 예측력이고,
그 다음에만 아래 셋 중 하나를 독립적으로 연다.

- 물리 파라미터별 학습률 재가중
- 고정 패턴 structured layer dropout/skip
- P091 안의 후보 block 국소 재학습

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| 진단 계약 | 논리 occurrence의 `S`와 unique physical parameter의 `U`를 분리한 schema |
| CLA-safe 민감도 정의 | K/V 공급은 보존하고 해당 레이어의 잔차 기여만 0으로 만드는 진단 |
| 업데이트 계측 확장안 | 기존 `OptimizerAudit`를 재사용해 realized update, WD 성분, LR-normalized 지표를 분리 |
| selector 검증안 | 짧은 진단 순위와 실제 국소 재학습 이득의 Spearman/top-k 대조 |
| 중복 정리 | D안은 P091에 흡수하고, B·C는 서로 다른 후속 실험으로 분리 |
| 중단선 | selector가 이득을 예측하지 못하면 동적 controller·skip·resuscitation을 만들지 않음 |

승인만으로 코드·계획서·배치·GPU 실행은 생기지 않는다. 실험번호도 선점하지 않는다.
P091 갱신이나 새 실험계획은 사용자가 후속 범위를 승인할 때 `exp-plan`과 `exp-preflight`로
별도 작성한다.

## 4. 비용

### 4.1 원안이 제시한 비용·목표

| 항목 | 원안 값 | 이번 판정 |
|---|---:|---|
| full trajectory | 최대 3개(A, B, D) | selector 검증 전에 과다; 그대로 채택 불가 |
| D microbranch | 후보 1~2개, 50~100 step | 개념은 저비용이나 현재 batch/token 기준으로 재계산 필요 |
| C skip | 10%에서 20%로 확대 | 정적 패턴·compile 실측 없이 동적 확대 금지 |
| 목표 | wall-clock 5~10% 개선 | 사전 기대치일 뿐 성공 기준으로 고정할 근거 없음 |
| 진단 | 약 20개 layer 우회 평가, 전체의 `<0.5%` 기대 | 현재 eval 분모·CLA schedule로 재측정 전 주장 불가 |

### 4.2 수정안의 비용 상한

| 단계 | GPU | AI 작업 | 사용자 직접 작업 | 디스크 |
|---|---:|---:|---|---:|
| R0 계약·offline mapping | `0 GPU-h` | ⚙2~4h | 설계 승인 1회 | ⚙1 MiB 미만 |
| R1 계측 오염 fixture | `0 GPU-h` CPU fixture + 향후 사용자 짧은 smoke | ⚙2~4h | 코드 승인 뒤 smoke | ⚙수 MiB |
| R2 고정 checkpoint 진단 | 후속 계획에서 재산정; 지금은 `NOT_RUN` | ⚙1~2h | GPU/model 진단 실행 | 평가 산출물 크기만큼 |
| R3 P091 selector 대조 | P091 Stage1의 기존 `0.2~0.5 GPU-h` 범위 안에 흡수 가능성 | ⚙2~4h | P091 후속 승인·실행 | audit 로그 |
| R4 B 또는 C 한 축 | R0~R3 PASS 뒤 별도 산정 | 별도 계획 | 별도 승인 | 별도 산정 |

현재 단계의 승인 비용은 문서 판단뿐이다. GPU 비용은 0이다. 원안의 3개 full trajectory는
R0~R3가 통과하기 전에는 열지 않는다.

## 5. 원리·근거

### 5.1 우리 코드·결과와의 대조

| 근거 | 관측 | 설계에 주는 제약 |
|---|---|---|
| [`transformer.py`](../tinylm/model/transformer.py) | 논리 `layers`가 prelude/middle/coda, tied MLP, shared attention, CLA K/V owner를 조합 | 논리 layer와 physical parameter를 1:1로 취급 금지 |
| [`modules.py`](../tinylm/model/modules.py) | attention·MLP 잔차가 각각 learned gate를 거쳐 더해짐 | gate-zero로 잔차 기여만 끊는 진단 가능; 실제 연산은 계속되므로 speed 증거 아님 |
| [`EXPERIMENT_BASELINES.md`](../docs/EXPERIMENT_BASELINES.md) B.15 | 기존 U2도 gate-zero라 K/V 공급은 보존된다고 정정 | `S`는 “잔차 기여 민감도”로 이름 붙여야 함 |
| [`optimizer_audit.py`](../tinylm/train/optimizer_audit.py) | 최대 8개 matrix의 gradient RMS, WD 포함 update RMS, weight RMS, update/weight를 이미 기록 | 새 계측기를 병렬로 만들지 말고 기존 감사기를 확장 |
| [`trainer.py`](../tinylm/train/trainer.py) | matrix는 Muon, 나머지는 AdamW인 혼합 경로와 서로 다른 LR/WD를 사용 | AdamW용 Blockwise LR 결과를 그대로 이식 금지 |
| [`P091`](../test_plan/P091_Muon후반-적응적-블록-확장-재학습.md) | short probe 순위가 32~128-step realized gain을 예측하는지 이미 정식 질문으로 보유 | D안의 selector·국소 재학습은 P091에 흡수 |
| [`P035B 결과 084`](../test_result/084_20260915_P035B-감사오염은-없고-후반궤적차도-지속되지-않았다.md) | 계측 오염 G1은 통과했으나 짧은 동역학 차의 지속성 G2는 불성립 | 짧은 신호만으로 adaptive/freeze를 열지 않음 |
| 실행 레지스트리 조회 | 유사 Muon·재귀 런은 있으나 `S/U → realized gain` 대조는 없음 | 질문은 중복 아님; 기존 런은 기준선·계보로 사용 |

`OptimizerAudit`의 현재 update는 **실현된 parameter delta와 weight decay를 포함**한다.
Muon에서는 raw gradient가 Newton–Schulz 변환 뒤의 실제 update가 아니므로, `U`를 하나의 수식으로
고정하면 오해가 생긴다. 최소한 다음을 나눠야 한다.

1. `U_realized = EMA(||W_after - W_before|| / (||W_before|| + ε))`
2. optimizer가 제공할 수 있을 때 `U_grad_component`
3. `U_decay_component`
4. LR·schedule 차이를 제거한 비교용 `U_normalized`

어느 지표도 “중요도”를 직접 뜻하지 않는다. 중요도는 별도 개입 `S`와 realized gain으로 대조한다.

### 5.2 외부 근거와 적용 한계

- [The Sharpness Disparity Principle in Transformers](https://proceedings.mlr.press/v267/wang25dl.html)은
  transformer block 사이 sharpness 차이가 일찍 생겨 유지된다고 보고하고, GPT-2/LLaMA
  0.12B~1.1B의 **AdamW**에 Blockwise LR을 적용해 더 낮은 종단 loss와 거의 2배 수렴 가속을
  보고했다. B안의 직접 근거지만 TinyLM의 Muon+AdamW 혼합 경로에는 전이 검증이 필요하다.
- [SlimFit](https://aclanthology.org/2024.naacl-long.345/)은 training dynamics로 기여가 낮은
  layer를 동적으로 freeze해 BERT·ViT **fine-tuning** 메모리를 줄였다. “상태 기반 동결”의
  가능성은 지지하지만 scratch LLM pretraining의 품질·속도 보증은 아니다.
- [Are All Layers Created Equal?](https://www.jmlr.org/beta/papers/v23/20-069.html)은 학습 뒤
  re-initialization/re-randomization에 대한 층별 robust/critical 차이를 보였다. norm이나 이동량만으로
  중요도를 판단하기 어렵다는 근거지만, 온라인 selector나 현재 레이어 skip을 직접 검증하지 않는다.
- [Loss of plasticity in deep continual learning](https://www.nature.com/articles/s41586-024-07711-7)은
  continual-learning 조건에서 low-utility **unit**을 소량 재초기화하는 continual backprop을
  제안했다. D안의 “dormant를 되살린다”는 영감은 주지만, stationary LLM pretraining의 논리
  block 전체에 LR을 올리는 근거로 곧바로 쓸 수 없다.
- [Don't Drop Dropout](https://arxiv.org/abs/2609.05275)은 271M~8.2B, 2,400회가 넘는
  Cerebras 실험에서 layer distribution·시간 schedule·optimizer를 함께 조정한 layer dropout이
  같은 step에서 최대 25% training FLOPs를 절감할 수 있다고 보고한다. C안과 가장 직접적이지만,
  하드웨어·모델 규모·static schedule이 TinyLM의 dynamic `S/U` controller와 다르다.

### 5.3 네 범주 판정

#### A. 그대로 타당한 부분

| 내용 | 판정 이유 |
|---|---|
| weight movement 하나가 아니라 intervention-based sensitivity를 함께 본다 | 활동도와 함수적 기여는 다른 축이다 |
| tied/shared 구조에서는 논리 occurrence와 physical parameter를 분리한다 | TinyLM 실제 구조와 일치한다 |
| `U↓`만으로 freeze·prune하지 않는다 | 작은 update는 수렴·LR·스케줄·공유·optimizer의 결과일 수 있다 |
| 후보를 1~2개로 제한하고 paired branch·rollback을 둔다 | 원인분리와 손상 제한에 유리하다 |
| 품질뿐 아니라 wall-clock·FLOPs·메모리를 함께 기록한다 | 계산 재배분 주장의 필수 증거다 |
| reset, `-W`, `1-W` 같은 큰 개입을 첫 단계에서 제외한다 | 현재 질문보다 위험하고 독립변수를 늘린다 |

#### B. 개선하면 사용 가능한 부분

| 원안 | 개선안 |
|---|---|
| `U_l` 한 식 | realized update·WD·LR-normalized 지표를 분리하고 기존 `OptimizerAudit` 확장 |
| block bypass CE | CLA owner KV 계산은 유지한 gate-zero 잔차 기여 ablation으로 정확히 명명 |
| 같은 seed·token order | checkpoint, AdamW/Muon state, scheduler progress, RNG, data cursor/sampler, AMP 상태까지 복원 |
| P002 시간·loss 기준 | 현재 Muon recipe·동일 pool/tokenizer/tokens/parent/eval ruler로 다시 고정 |
| 하위 20~25% 등 고정 threshold | baseline window 간 rank 안정성·불확실성에서 threshold를 도출 |
| 동적 skip | fixed mask/static schedule이 실제 FLOPs·wall-clock을 줄이는지 먼저 측정 |
| D에서 후보 `×2`, 나머지 `×0.5~1` | 첫 paired arm은 후보만 변경하고 나머지는 그대로 둬 독립변수 1개 유지 |
| held-out CE 한 패널 | selector panel과 최종 판정 panel을 분리해 leakage 방지 |

#### C. 개념만 차용할 부분

| 개념 | 차용 범위 |
|---|---|
| `S/U` 4상태 controller | 먼저 offline label/diagnostic vocabulary로만 사용; 자동 제어는 selector PASS 뒤 |
| dormant resuscitation | P091의 local/adaptive 후보 선택과 realized gain 대조에 흡수 |
| 상태 전이·히스테리시스 | 여러 window의 rank 안정성이 확인된 뒤 controller 설계 입력으로만 보존 |
| 상태 기반 layer dropout | 고정 structured dropout 기준선이 산 뒤에만 `S/U` 정보 추가 효과를 검토 |
| “낮은 S·U면 redundancy” | redundancy 결론이 아니라 추가 causal ablation 후보를 고르는 휴리스틱으로만 사용 |

#### D. 현재 형태로 사용 불가한 부분

| 내용 | 사용 불가 이유 |
|---|---|
| B·D를 “학습 연산 절감”으로 합산 | LR 변경은 기본 forward/backward FLOPs를 줄이지 않는다 |
| CLA·shared module에서 임의 논리 block 전체 bypass | downstream K/V 소비와 shared parameter 효과를 동시에 바꿔 개입 의미가 불명확하다 |
| P002의 90~97.5분·loss 3.7797을 현재 gate로 사용 | optimizer·구조·pool·평가 계보가 현재 기준선과 다르다 |
| `20~25%`, `×2`, `×0.5~1`, `50~100 step`, `10→20%`, `5~10%`를 사전 고정 | TinyLM 현재 noise·ruler·batch·compile 근거가 없다 |
| 같은 seed와 token order만으로 paired control 완료 주장 | optimizer/scheduler/RNG/data cursor 상태가 다르면 다른 branch다 |
| selector 검증 전 A/B/D 세 full trajectory | 가장 싼 반증을 건너뛰고 GPU 비용과 해석 축을 늘린다 |
| `S↓, U↓`와 D 실패만으로 “불필요 층” 확정 | 개입 범위·평가 패널·학습 horizon 의존이며 인과적 redundancy 증거가 아니다 |
| SlimFit·continual learning·post-training reset 결과를 scratch pretraining 보증으로 사용 | task·scale·optimizer·개입 단위가 다르다 |

## 6. 방법

### 6.1 수정된 단계

| 단계 | 무엇 | 비용 | ★다음으로 가는 조건 |
|---|---|---:|---|
| **R0 계약** | 논리 layer occurrence, unique MLP/attention parameter, CLA K/V owner, optimizer group을 매핑하고 `S/U` schema 고정 | `0 GPU-h` | 한 물리 tensor가 여러 occurrence에 쓰여도 중복 집계 0; K/V 공급/잔차 기여 구분 |
| **R1 계측** | 기존 `OptimizerAudit`에 realized/WD/normalized update를 opt-in으로 추가하고 on/off 오염 fixture | CPU + 사용자 smoke | 기본 off bit-identical, audit overhead와 선택 편향 명시, Muon 실제 delta 포착 |
| **R2 진단** | 고정 checkpoint와 selector 전용 패널에서 CLA-safe gate-zero `S` 및 여러 window의 `U` 측정 | 후속 계획에서 산정 | rank가 window·패널에 대해 안정적이고 tied/shared mapping 오류 0 |
| **R3 예측력** | P091 Stage1 안에서 `S/U` ranking과 32~128-step realized gain을 대조 | P091 기존 범위 | median Spearman `ρ≥0.5` 및 top-2 재현이라는 P091 gate 충족 |
| **R4 단일 축** | B(Blockwise LR) 또는 C(fixed structured layer dropout) 하나만 별도 계획 | 별도 산정 | R3 PASS, 현재 baseline/태그/토큰/평가 preflight PASS, 변수 1개 |
| **R5 재현** | 유효한 축만 full horizon·다른 seed에서 재현 | 별도 산정 | 현재 ruler 초과 또는 명시한 quality/efficiency Pareto, 두 seed 방향 일치 |

R3가 실패하면 `S/U`는 설명용 진단으로만 남기고 동적 selector·controller·skip은 종료한다.
R4에서 Blockwise LR을 택하면 compute-saving을 주장하지 않는다. structured layer dropout을 택하면
명목 skip률이 아니라 profiler FLOPs·wall-clock·compile graph 수로 실제 생략을 확인한다.

### 6.2 paired branch의 최소 복원 계약

동일 branch 주장을 하려면 다음이 모두 같아야 한다.

- 같은 model checkpoint와 tensor hash
- AdamW와 Muon 양쪽 optimizer state
- LR scheduler의 step/progress와 각 param-group LR
- Python·NumPy·torch CPU/CUDA RNG state
- data iterator/cursor/sampler state와 실제 token order
- AMP/GradScaler, gradient accumulation 경계, compile/config signature
- selector panel과 최종 evaluation panel의 분리

첫 개입은 **후보 parameter group의 LR만 변경**하고 나머지는 유지한다. “전체 update budget을
보존한다”는 재배분 팔은 후보-only 효과가 확인된 뒤 별도 독립변수로 둔다.

### 6.3 실행 전 금지선

- 승인 결과는 별도 P번호가 아니라 P091 계획에 흡수한다. BAT/SH·trainer flag는 직전 gate와
  별도 구현 승인 전 만들지 않는다.
- 사용자 승인 전 GPU·모델·smoke를 Codex가 실행하지 않는다.
- `datasets/TinyDataset/**`를 selector panel 후보로 열거나 검사하지 않는다.
- 현재 P091과 같은 질문의 독립 plan을 중복 생성하지 않는다.

## 7. 거절하면 못 하는 것

기존 dense/Muon 실험과 P091은 그대로 진행할 수 있다. 이 제안을 거절해도 현재 기본 학습법을
잃지 않는다. 다만 레이어별 “정체”와 “함수적 민감도”를 분리해 설명하거나, 그 신호가 국소
재학습·skip의 이득을 예측하는지 검증하는 경로는 열리지 않는다. 따라서 우선순위는 P091의
이미 승인된 선결보다 높지 않다.

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| 논리/물리 중복 집계 | tied MLP가 여러 층의 별도 `U`처럼 보임 | `id(parameter/module)` 기반 unique physical table과 occurrence table 분리 |
| CLA 개입 오해 | K/V 공급은 살아 있는데 “층 전체 제거”로 보고 | gate-zero를 잔차 기여 ablation으로 명명하고 owner KV 여부 기록 |
| audit가 timing을 오염 | CPU copy·동기화로 ms/step 증가 | audit on/off 대조, step timing과 copy timing 분리, 표본 수 제한 |
| Muon update 오측정 | raw gradient를 실제 update로 간주 | pre/post parameter delta 또는 optimizer 내부 post-NS update 기록 |
| held-out leakage | `S`를 고른 패널로 최종 성능도 판정 | selector/final panel 분리 및 고정 |
| branch 재생 불일치 | 같은 seed인데 loss가 갈라짐 | §6.2 전체 상태 복원과 signature 대조 |
| dynamic control graph churn | skip마다 compile graph 재생성·속도 악화 | fixed mask/static schedule 선행, graph 수와 warmup 제외 wall-clock 기록 |
| proxy 과적합 | `S/U` 순위는 안정적이나 realized gain 예측 실패 | R3를 필수 gate로 두고 실패 시 자동화 종료 |
| 기존 P091 중복 | 같은 selector를 다른 이름으로 재실험 | D안을 P091에 흡수하고 계획 정본 하나만 유지 |
| 품질과 계산의 혼동 | LR 개선을 FLOPs 절감으로 보고 | optimizer 재가중과 execution sparsity 결과표를 분리 |

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | 원안을 A→B→D full trajectory로 거의 그대로 실행 | 가장 빨리 큰 결과를 얻을 가능성 | 현재 구조·Muon·P091 중복·paired confound 때문에 원인 해석이 약함 |
| **B** | **권장:** `S/U` 진단을 정교화하고 D는 P091에 흡수, B와 C는 selector PASS 뒤 서로 독립된 후속 축으로 분리 | 가장 싼 단계에서 반증 가능, 기존 계획과 중복 0, 계산절감 주장도 정확 | 초기에는 “새 기법”보다 계측·계약 작업이 많음 |
| **C** | 원안을 전부 기각하고 dense/Muon/P091만 유지 | 추가 코드·GPU 0, 운영 단순 | 레이어별 기여와 업데이트 불균형의 설명 가능성을 포기 |

### ★권장안과 근거

**B안을 권장한다.** 원안의 가장 강한 부분은 특정 LR 배수나 skip률이 아니라, “활동도와
민감도는 다르며 작은 update가 redundancy를 뜻하지 않는다”는 진단 구조다. TinyLM에는 이를
검증할 수 있는 gate, 기존 업데이트 감사기, P091 selector 질문이 이미 있다. 반대로 원안의
수치 threshold와 세 full trajectory는 현재 기준선·구조에서 검증되지 않았다. 그러므로 먼저
`S/U → realized gain` 예측력을 증명하고, 그 뒤에도 **학습률 재가중**과 **실제 execution
sparsity**를 한 결과로 합치지 않는 것이 가장 적은 비용으로 가장 해석 가능한 경로다.

승인 선택지는 다음처럼 좁힌다.

- **B1 승인**: R0 계약과 P091 흡수 설계만 작성한다. 코드·GPU 0.
- **B2 후속 승인**: B1 문서 대조 뒤 R1 계측 구현과 CPU fixture만 연다.
- **B3 후속 승인**: 사용자 smoke와 R1 PASS 뒤 R2/R3 GPU 진단 계획을 작성한다.

2026-09-18 사용자는 권장 B안을 **게이트 계획으로 승인**했다. 이에 B1/R0 계약은 P091에
흡수했고 B2·B3의 구현·smoke·GPU는 계획에 적힌 선결을 통과한 뒤 별도 실행 범위로 남긴다.
