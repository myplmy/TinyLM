# P082 — **Qwen·Gemma 교사로 TinyLM의 지능을 실제로 향상시킬 수 있는가**

> ★★**2026-09-03 사용자 결정 두 가지**
>
> **① 안 B 승인** — `C0`(compute control)를 **screen 규모로 재정의**한다(§실행 순서).
> 종전 `C0` 는 *"승자 KD 와 같은 총 GPU-hour"* 라 **full core 뒤**에 있었다 —
> ★**full core 를 정당화할 게이트가 자기가 지켜야 할 문 뒤에 있었다.**
> 개정 후 비용 **약 2~3 GPU-h**, 제안 범위 합계가 **191~280 → 약 52 GPU-h** 로 준다.
>
> **② P083 을 P082 보다 먼저 본다.**
>
> | | GPU |
> |---|---|
> | **P083**(구동기·플랫폼) | ★**거의 0** — Stage 0~5 는 engineer-day 이고 GPU 는 선택적 |
> | **P082**(KD) | **191~280 GPU-h**(안 B 적용 시 약 52) |
>
> **GPU 가 병목인 상황에서 이 차이가 결정적**이고, P083 은 *"40 MiB 에 정말 들어가는가"*
> 라는 **1순위 목표**를 직접 연다. 🚫**P082 를 기각하는 것이 아니다 — 순서 문제다.**


- **상태**: 🔜**계획**. 문서 작성만 완료. **코드 구현·데이터 생성·학습·평가·테스트는 미착수**
- **제안**: 사용자 지시 2026-09-01
- **교사 축**: `Qwen3-0.6B-Base`, `gemma-3-270m`(logit KD) + 조건부 instruct variant(sequence KD)
- **선행**: [P067](P067_외부-토크나이저와-외부-교사.md) ·
  [P075](P075_토크나이저-어휘예산과-한국어-분절.md) ·
  [결과 053](../test_result/053_20260822_P067-단계0a-두-최신-소형모델은-KV를-버리고-있다.md) ·
  [결과 038](../test_result/038_20260808_P050-부모초기화가-전부다-KD는-0이다.md) ·
  [P069 결과 056](../test_result/056_20260823_P069-벤치13종-hellaswag와-piqa만-살아있다.md) ·
  [P080](P080_저밀도-데이터셋을-벤치마크로-쓸-수-있는가.md)
- **조사 정본**: [모델 품질·지능 향상 조사 결과](../docs/20260901_모델-품질-지능-향상-조사결과.md)

---

## 0. ★이 계획의 범위 — **P067을 다시 돌리는 계획이 아니다**

P067이 증명한 것은 다음뿐이다.

| 항목 | P067이 답한 것 | 남은 구멍 |
|---|---|---|
| Qwen 외부 KD 배관 | ✅ 2,289-step full run 가능 | 1 seed·한 KD 설정·영문 bpb만 있음 |
| Qwen 교사 효과 | `Q256T−QT0 = −0.0077 bpb` | 분해능 0.008 미만, downstream 지능 미측정 |
| Gemma 270M 배관 | 250-step forward/backward·VRAM 확인 | 🚫 `grad_max`: 무KD GT0 36.9, KD 118.8/488.8로 모두 기존 `>10` gate 실패; KD 원인 미분리, full 품질 미실행 |
| Gemma 대조군 | `GT0probe`만 있음 | 🚫 full-budget `GT0` 없음 |
| 평가 | 외부 tokenizer common-bpb 가능 | 🚫 HellaSwag·PIQA·ARC-e·한국어·TinyDataset 불가 |
| 증류 목표 | FKL `α=.5,T=2,k4` | on-policy·JSD/skew·sequence/rationale 없음 |

★★**P082의 본 질문은 “loss가 조금 낮아지는가”가 아니다.**
**동일 tokenizer·동일 학생·동일 데이터의 무교사 대조군보다 실제 능력 과제가 좋아지는가**를 묻는다.

두 트랙을 분리한다.

| 트랙 | 목적 | 학생 tokenizer | 교사 사용 |
|---|---|---|---|
| **A. 인과 진단** | logit KD 자체가 작동하는지 | 교사와 동일(Qwen/Gemma 각각) | white-box logits |
| **B. 배포 후보** | native 모델 지능·Pareto 개선 | **native 32k 유지** | 검증된 sequence/rationale, 조건부 cross-token KD |

🚫트랙 A가 이겨도 큰 vocab 학생을 자동 채택하지 않는다. 트랙 B가 이겨야 native 부모초기화·메모리 목표와 양립하는 배포안이 된다.

---

## 1. ★질문

| # | 질문 |
|---|---|
| ★★**Q1** | Qwen3-0.6B와 Gemma 3 270M이 **우리의 동일 prompt·동일 채점기·동일 과제**에서 학생보다 실제로 우수한가 |
| ★★**Q2** | 같은 tokenizer의 무KD 팔보다 기존 FKL이 HellaSwag·PIQA·ARC-e·TinyDataset 능력을 높이는가 |
| ★**Q3** | Qwen의 −0.0077 bpb가 3 seed에서 재현되는가, 아니면 seed 잡음인가 |
| ★★**Q4** | `T/α/every`와 FKL/RKL/JSD/skew-KL 중 TinyLM 용량에 맞는 신호가 있는가 |
| ★**Q5** | 학생이 만든 오류 prefix에 교사가 답하는 mixed on-policy 방식이 teacher-forced KD보다 나은가 |
| ★★**Q6** | 짧고 검증 가능한 sequence/rationale 증류가 generic logit KD보다 실제 지능을 더 올리는가 |
| ★**Q7** | Qwen 0.6B와 Gemma 270M 중 더 큰/작은 교사가 아니라 **과제 전문성과 학생 학습가능성**이 결과를 설명하는가 |
| ★★**Q8** | native tokenizer·부모초기화를 보존한 트랙 B가 큰-vocab 트랙 A보다 품질/메모리 Pareto에서 나은가 |

---

## 2. ★고정된 사실과 가설을 분리한다

### 2.1 이미 측정된 사실

- 내부 dense KD는 300M 조건에서 두 seed 모두 약 **+0.021 loss 악화**, 제거 시 reserved **12.47→5.07 GiB**였다.
- 같은 내부 KD는 100M 예산에서는 **−0.110** 이겼다. KD 효과는 학습예산에 의존한다.
- Qwen은 `Q256T 1.3363` vs `QT0 1.3440`으로 **−0.0077 common-bpb**였다.
- Qwen의 같은-cache final CE는 `3.4796 vs 3.4762`로 KD가 **+0.0034** 나빴다.
- Gemma 270M KD probe는 reserved **14.77GB**, full 예상 **8.8h**, `grad_max=118.8`, skip 0이었다. narrow KD는 488.8, 무KD `GT0probe`도 36.9(warmup peak 88.7), skip 0이었다. backward/VRAM은 통과했지만 모두 기존 `grad_max>10` gate를 실패했으며, 원인이 KD인지 Gemma-vocab 학생/학습 설정 공통인지 분리되지 않았다. 품질 결과가 아니다.
- 현재 외부-tokenizer 모델은 `eval_bench_suite.py`, `eval_korean_bench.py`, `generate.py`로 정확히 평가할 수 없다.
- TinyDataset held-out v2.4 파일과 tokenizer shortcut gate는 있으나 MANIFEST 정본은 아직 v2.3이고 모델 forced-choice evaluator는 없다. P082에서 먼저 승격·hash·평가기를 확정해야 한다.

### 2.2 아직 가설인 것

| 가설 | 반증 방법 |
|---|---|
| H1. 좋은 교사면 KD가 산다 | teacher advantage를 먼저 재고 matched no-KD보다 3-seed downstream 개선 확인 |
| H2. 기존 `T=2, α=.5, k4`가 너무 약하거나 부적합하다 | divergence·T·α·every를 분리 비교하고 gradient 비율 측정 |
| H3. Gemma 270M이 Qwen 600M보다 학생 용량에 맞다 | 각 tokenizer 내 KD 효과를 표준화해 비교. 교사 크기만으로 설명하지 않음 |
| H4. generic FKL보다 on-policy가 낫다 | 같은 teacher/data/compute에서 off-policy와 mixed on-policy 비교 |
| H5. sequence/rationale가 지능에 더 직접적이다 | native no-SFT/SFT/answer-only/rationale 팔 비교 |
| H6. 큰 vocab이 KD 이득을 상쇄한다 | 트랙 A와 native-tokenizer 트랙 B의 품질·파라미터·runtime Pareto 비교 |

---

## 3. ★★“지능 향상” 판정 규칙 — **결과 전에 고정**

### 3.1 지표 계층

| 등급 | 지표 | 역할 |
|---|---|---|
| ★★**1차** | HellaSwag·PIQA·ARC-e 정확도, 검증된 TinyDataset held-out forced-choice | 지식·상식·추론/관계 능력 |
| ★**2차** | 비중복 영문·한국어 common-bpb, tokenizer-family 내부 val CE | 일반 언어모델 품질·회귀 감시 |
| **진단** | teacher/student entropy·margin·agreement, 정답 CE, calibration, 길이/반복/EOS | 왜 올랐거나 무너졌는지 설명 |
| **행동** | 조건부 IFEval·짧은 생성형 정답률 | sequence/SFT 트랙에서만 1차 보조 |
| **비용** | params, packed/runtime MB, reserved/allocated VRAM, wall time, tok/s | Pareto 판정 |

🚫**common-bpb만 좋아진 팔을 “지능 향상”으로 채택하지 않는다.**

### 3.2 evaluator gate

다음이 모두 통과하기 전에는 학습 팔을 열지 않는다.

1. native tokenizer 경로가 기존 점수를 허용 오차 안에서 재현한다.
2. Qwen/Gemma checkpoint가 자기 tokenizer로 encode→score→decode되고 tokenizer ID/hash가 로그에 남는다.
3. 의도적으로 token-id 두 개를 바꾼 tokenizer fixture가 **즉시 실패**한다.
4. 동일 원문·동일 prompt·동일 candidate 순서를 모든 모델에 보장한다.
5. 무작위 모델과 trivial 선택기(최단/최장/position)가 사전 기준선 범위에 든다.
6. TinyDataset은 v2.4 승격 여부를 먼저 결정한다. 승격 시 정본 경로·hash를 명시하고, 미승격 시 v2.3을 명시하며 train/val/held-out 교집합 0을 확인한다.
7. `common_bpb.py`가 실제 사용하는 `train-v2.0`을 학습 corpus와 다시 overlap audit한다. P075의 `dev-v2.0` 12%를 대체 증거로 쓰지 않는다.

### 3.3 teacher-advantage gate

각 과제·문항에서 교사와 직접 대조 학생의 정답 log-likelihood/정확도를 같은 채점기로 잰다.

| 관측 | 행동 |
|---|---|
| 교사가 학생보다 1차 과제 **2개 이상**에서 `≥+2%p`이고 item-paired 95% CI 하한 `>0` | 해당 task-tagged sequence/KD를 다음 단계로 진행 |
| 평균은 좋지만 특정 과제에서 열세 | 그 과제 token/sequence에는 KD weight 0 또는 별도 slice |
| 교사 우위가 1차 과제 어디에도 없음 | 🚫그 교사로 “지능 KD” 중단. 압축률 KD만 별도 표기 |
| 교사 confidence가 높지만 오답 | 🚫confidence gating만으로 통과시키지 않고 정답/검증기 gate 사용 |

generic raw-text logit KD의 token gate는 task 정답률을 억지로 매핑하지 않는다. 별도 비중복 raw held-out에서
`δ_bpb=max(0.008, 2×문서-paired bootstrap SE)`를 먼저 고정하고, 교사 문서-paired `Δbpb≤−δ_bpb`이면서 95% CI 상한 `<0`인 language/domain slice에만 선택적 가중을 허용한다. `S1`은 기존법 재현을 위해 의도적으로 ungated로 둔다.

위 수치와 §7의 안정성·생성 gate는 **Stage 0 protocol**에 먼저 기록한다. evaluator calibration만으로 1회 수정할 수 있고, 어떤 학습 팔의 결과를 본 뒤에는 바꾸지 않는다.

### 3.4 최종 성공 기준

직접 대조는 **같은 tokenizer·형상·raw sample IDs·budget·seed**의 무KD 팔이다.

1. **3 seed** 평균에서 1차 과제 중 적어도 2개가 양의 방향이고, 과제별 효과의 macro 평균에 대한 paired bootstrap 95% CI 하한이 0보다 크다.
2. 어느 1차 과제도 평균 **−2%p보다 크게 회귀하지 않는다.** 정확한 신뢰구간과 함께 보고한다.
3. common-bpb가 직접 대조군보다 `Δbpb≤−δ_bpb`이면 일반 품질의 실무 개선으로 별도 인정한다. 초기 `δ_bpb`는 0.008과 문서-paired bootstrap SE의 2배 중 큰 값이며, 새 corpus/tokenizer family에서 다시 고정한다. 이 조건만으로 지능 성공은 아니다.
4. TinyDataset 300문항은 검정력이 작으므로 McNemar exact와 CI를 함께 쓰고, 단일 정확도 차는 탐색 결과로 표시한다.
5. compute가 다른 팔은 **동일 token budget 표**와 **동일 wall/GPU-hour budget 표**를 둘 다 제시한다.
6. 큰-vocab 트랙은 native 대조보다 품질이 좋아도 runtime/상주 Pareto에서 지면 연구 신호로만 보존하고 배포안으로 채택하지 않는다.
7. **final checkpoint**를 1차 판정 대상으로 고정한다. val-best나 task별 best checkpoint는 탐색 표에만 따로 내며 지표마다 유리한 checkpoint를 골라 성공 판정하지 않는다.

⚠️표본 수가 작아 CI가 0을 포함하면 **실패가 아니라 미확정**이다. 추가 표본/seed 없이 서열을 강제하지 않는다.

---

## 4. ★실험 팔 — **교사 효과와 tokenizer 효과를 섞지 않는다**

### 4.1 트랙 A: same-tokenizer logit KD

#### Qwen family

| 태그(계획명) | tokenizer | 교사 | 목적함수 | seed | 역할 |
|---|---|---|---|---|---|
| `P82_Q_N0` | Qwen | 없음 | CE | 1337/2024/4242 | 직접 대조. 기존 `QT0` 1337은 provenance 통과 시 재사용 |
| `P82_Q_B` | Qwen | Qwen3-0.6B-Base | 기존 FKL `.5/T2/k4` | 〃 | P067 재현. 기존 `Q256T` 1337 조건부 재사용 |
| `P82_Q_M` | Qwen | 〃 | 단계2 최선 pretraining KD | 〃 | 개선안 본시험 |
| ★**`P82_Q_C0`** | Qwen | 없음 | ★**CE를 그 family screen 승자와 같은 GPU-hour까지 연장 (screen 규모)** | 1337 | ★**full core 진입 게이트**(안 B, 2026-09-03 승인) |

#### Gemma family

| 태그(계획명) | tokenizer | 교사 | 목적함수 | seed | 역할 |
|---|---|---|---|---|---|
| ★`P82_G_N0` | Gemma | 없음 | CE | 1337/2024/4242 | ★필수 full-budget 대조. 기존에는 probe만 있음 |
| `P82_G_B` | Gemma | Gemma 3 270M | 기존 FKL `.5/T2/k4` | 〃 | 기존법의 교사 효과 |
| `P82_G_M` | Gemma | 〃 | Qwen에서 선별한 modern KD | 〃 | 교사/가족 간 재현성 |
| ★**`P82_G_C0`** | Gemma | 없음 | ★**CE를 그 family screen 승자와 같은 GPU-hour까지 연장 (screen 규모)** | 1337 | ★**full core 진입 게이트**(안 B, 2026-09-03 승인) |

★★Qwen과 Gemma의 **raw CE를 서로 비교하지 않는다.** 각각 `Q_B−Q_N0`, `G_B−G_N0`를 계산한 뒤 효과량과 downstream 변화만 비교한다.

### 4.2 Qwen 100M pretraining-KD 저비용 후보 매트릭스

full factorial을 돌리지 않는다. 현재 generic pretraining 조건과 직접 유사한 [ACL 2025 설계공간 연구](https://aclanthology.org/2025.acl-long.181/)의 축을 먼저 닫고, Qwen 100M budget에서 아래 순서로 **명백히 해로운 팔만 제거**한다. 최종 판정은 300M full에서 한다.

| 후보 | divergence/target | T | α | `kd_every` | 직접 비교·바꾸는 축 | 목적 |
|---|---|---:|---:|---:|---|---|
| `S0` | 없음 | — | 0 | — | — | 같은-budget 무KD |
| `S1` | FKL | 2 | .5 | 4 | `S0`: 기존 KD 전체 | P067 기준 |
| `S2` | FKL | 1 | .5 | 4 | `S1`: **T만** | 더 sharp한 교사 분포 |
| `S3` | FKL | 1 | .25 | 4 | `S2`: **α만** | KD 비중 완화 |
| `S4` | teacher top-1 NLL | — | .25 | 4 | `S3`: **target/loss만** | full 분포 대신 교사 argmax target |
| `S5` | FKL | 1 | .25 | 2 | `S3`: **빈도만** | divergence 비교용 k2 정합 대조 |
| `S6` | FKL | 1 | early `.5→0` | 2 | `S5`: **α schedule만** | 초기 KD 후 CE-anchor decay |
| `S7` | JSD(0.5) | 1 | .25 | 2 | `S5`: **divergence만** | 양방향 분포 차이의 대칭적 절충 |
| `S8` | skew-KL-only ablation | 1 | .25 | 2 | `S5`: **divergence만** | adaptive replay 없는 loss 단독 진단 |
| `S9` | advantage-gated JSD | 1 | .25 | 2 | `S7`: **token mask만** | held-out NLL/margin 기준으로 교사가 나은 token에 집중 |
| `S10` | FKL | 1 | .9 | 4 | `S2`: **α만** | ACL 2025 high-α 결과의 bounded 반대가설 |
| `S11` | FKL | .5 | .9 | 4 | `S10`: **T만** | ACL 2025 low-T 결과의 규모 외삽 검사 |
| `S12` | FKL | 1 | WSD `.9@max-LR→0` | 4 | `S10`: **α schedule만** | high KD during max-LR 뒤 CE anchor |
| `S13` | FKL | 1 | WSD `.9@max-LR→0` | 4 | `S12`: **LR schedule만** | paper-inspired WSD-α + WSD-LR 결합의 추가 몫 |

- RKL은 toy/fixed-logit 수치 진단일 뿐이다. 별도 승인된 counted training arm이 되기 전에는 결과 수와 예산에 포함하지 않는다.
- `S8`은 DistiLLM 재현이 아니다. DistiLLM은 skew-KL과 student-generated output의 adaptive off-policy replay를 함께 쓴다.
- mixed on-policy/GKD는 이 raw-document screen에서 제외한다. prompt→response 경계와 일정 품질의 SFT 학생을 갖춘 §7 후속 단계에서 `λ=0.25`, 통과 시 `0.5`를 비교한다. generic raw crop에 별도 적용한다면 GKD 재현이 아닌 신규 pretraining 외삽으로 명명한다.
- ACL 2025 pretraining-KD의 high-α/WSD·`T=0.5` 결과는 1.9B급/100B-token 조건이다. 반대로 저장소 내부 300M α sweep은 α가 클수록 악화했다. 따라서 `S10~S13`은 **안전 gate가 있는 반대가설 screen**이지 기본값 채택이 아니다.
- 100M 결과는 “300M에서 성공”의 증거가 아니다. `grad`, 붕괴, 큰 회귀를 거르는 screen이다.
- 상위 팔 선택은 1차 과제 방향, common-bpb, gradient 충돌, 비용을 함께 본다. val CE 하나로 고르지 않는다.

### 4.3 트랙 B: native-tokenizer sequence/rationale KD

트랙 A와 별도 체크포인트·데이터·판정표를 쓴다.

| 태그(계획명) | 초기화 | 추가 데이터/예산 | 학생 loss | 목적 |
|---|---|---|---|---|
| `P82_N_BASE` | native 부모 또는 §4.3.1 결정 | 추가 학습 없음 | — | 시작 checkpoint 고정 |
| `P82_N_CE_TOK` | 〃 | 같은 추가 학생 token/step의 raw CE | 기존 CE | 추가 학습량 대조 |
| `P82_N_CE_GPU` | 〃 | 생성·검증까지 포함한 동일 GPU-hour의 raw CE | 기존 CE | 총 compute 대조 |
| `P82_N_REF` | 〃 | 같은 source의 gold/reference 또는 비교사 검증 답 | assistant-only CE | task SFT 자체 효과 대조 |
| `P82_N_QA_Q` | 〃 | Qwen의 검증된 **answer only** | assistant-only CE | Qwen sequence 신호의 추가 몫 |
| `P82_N_R_Q` | 〃 | 같은 accepted intersection의 Qwen 짧은 answer+rationale | multi-task CE | rationale의 추가 몫 |
| `P82_N_QA_G` | 〃 | Gemma의 검증된 answer only | assistant-only CE | Gemma sequence 신호의 추가 몫 |
| `P82_N_R_G` | 〃 | 같은 accepted intersection의 Gemma 짧은 answer+rationale | multi-task CE | rationale의 추가 몫 |
| `P82_N_MIX` | 〃 | Qwen/Gemma n-best 중 verifier 최선 | CE + 조건부 ranking | 두 교사 상보성 |

교사 효과는 `N_QA_*−N_REF`, rationale 추가효과는 `N_R_*−N_QA_*`, 추가 task 학습의 전체효과는 `N_REF−N_BASE`, 계산 대비효과는 `N_*−N_CE_GPU`로 분리한다. Qwen/Gemma 직접 비교는 **같은 source IDs, 두 교사가 모두 통과한 accepted intersection, 같은 assistant loss token 또는 총 compute**에서만 한다. `N_MIX`도 단일교사보다 더 많은 후보 생성 compute를 썼다면 그 비용을 포함한다.

#### 4.3.1 native tokenizer와 P075 선결 결정

현재 native tokenizer는 PAD/BOS/EOS만 확정돼 있고, [`chat/serialize.py`](../tinylm/chat/serialize.py)의 reserved role-token 전제와 `train_thinking=False` 경로는 P075 완료 전 사용할 수 없다. Stage 0에서 다음 중 하나를 선택·고정한다.

1. **현 tokenizer pilot**: 기존 token들로 분절되는 평문 경계 문자열만 사용한다. 새 token ID가 없어 native 부모초기화를 그대로 보존할 수 있다.
2. **P075 새 tokenizer**: reserved role/thinking token을 정식 도입한다. embedding/head shape와 token ID가 바뀌므로 기존 부모초기화가 자동 호환된다고 주장하지 않는다. 명시적 row mapping/graft를 검증하거나 새 tokenizer용 부모를 먼저 학습한다.

두 분기를 한 결과표에 섞지 않는다. 어느 분기든 교사 출력 생성은 **각 교사의 공식 Hugging Face chat template**를 사용하고, Qwen answer-only는 no-thinking, rationale는 thinking 정책을 고정한다. Gemma의 허용 role/template도 공식 snapshot에 맞춘 뒤 검증된 답 텍스트만 native student serializer로 canonicalize한다.

필요 교사:

- logit KD는 현재 보유한 Base/PT snapshot을 사용한다.
- 지시형 답/rationale 생성은 **해당 instruct snapshot**이 필요하다. 없으면 Base/PT가 출력 형식을 안정적으로 따른다고 가정하지 않는다.
- Qwen/Gemma 정확한 모델 ID·revision·license 수락 상태·tokenizer hash를 데이터 manifest에 고정한다. Qwen의 Apache-2.0과 Gemma 사용약관·notice/attribution·synthetic-output/derivative-data 배포 조건은 별도 체크리스트로 승인한다.

trace mixture 시작점은 **짧고 단순 80~95%, 긴/강한 5~20%**다. 이것은 ACL 2025 small-model learnability 결과를 100M급에 보수적으로 적용한 가설이며, 길이 ablation으로 검정한다.

### 4.4 조건부 트랙 C: native-tokenizer cross-token KD

트랙 B가 양의 신호를 보인 뒤에만 연다.

1. **ALM** chunk likelihood matching prototype: 구현 단순성/비용 우선 후보이지 성능 순위가 아니다.
2. **DSKD** 또는 BLD 중 하나: DSKD는 120M 학생 근거가 더 직접적이나 projector·attention 비용을 먼저 잰다.
3. CDM/DWA-KD는 2가 이기고 token/sequence alignment 오차가 남을 때
4. ULD는 `O(V log V)` 정렬이어도 full-vocab 분포와 같은 token 위치/min-length 정렬 오차가 있어 마지막 후보

🚫이 단계 때문에 트랙 A/B를 지연시키지 않는다. 트랙 C의 구현·실험 수와 비용은 P082 기본 예산에 포함하지 않으며, 별도 승인 전에는 열지 않는다.

---

## 5. ★★필요한 코드 구현

이 절은 **구현 명세**다. 현재 구현됐다는 뜻이 아니며, 이 계획서 작성은 구현 승인이 아니다.

### 5.1 평가·tokenizer 정합성 — **최우선**

| 위치 | 필요한 변경 | 완료 gate |
|---|---|---|
| 신규 공통 tokenizer resolver 또는 `tinylm/data` | native/HF tokenizer를 checkpoint metadata에서 단일 해석 | 같은 checkpoint를 모든 평가기가 같은 tokenizer로 선택 |
| `scripts/eval_bench_suite.py` | `--tokenizer-hf`/checkpoint 자동 해석, teacher HF scoring, per-item JSON | native 점수 재현 + Q/G 모델 정상 채점 |
| `scripts/eval_korean_bench.py` | 동일 외부 tokenizer 지원 | 한국어 task가 Q/G checkpoint에서 동작 |
| `tinylm/infer/generate.py`·CLI | 외부 tokenizer와 special IDs 전달 | encode/decode round trip, EOS 일치 |
| 신규/확장 `eval_forced_choice.py` | Stage 0에서 확정한 TinyDataset 정본의 PMI/length-normalized forced choice | trivial selector·random model gate 통과 |
| `scripts/common_bpb.py` | 여러 원문 split, per-document 출력, tokenizer metadata 자동 검증 | 영문/한국어 공통 원문과 CI 출력 |
| overlap audit | 실제 SQuAD `train-v2.0` + 새 공통 원문을 raw training docs와 검사 | 13-gram 기준 사전 threshold 통과 |

### 5.2 checkpoint·실험 provenance

모든 신규 체크포인트 자체에 다음 metadata를 **필수**로 넣고, 사람이 읽는 sidecar manifest는 checkpoint SHA-256과 서로 binding한다. schema version과 migration rule을 둬 sidecar만 바꿔 과거 artifact를 새 provenance로 가장할 수 없게 한다.

- student tokenizer model ID/path/revision, `tokenizer.json` SHA-256
- vocab size, BOS/EOS/PAD/UNK와 모든 추가 special-token ID
- teacher model ID/path/revision, config·weight index·tokenizer hash
- raw document manifest/hash, token cache hash, train/eval 원문 hash
- loss 종류와 모든 파라미터(T, α, every, on-policy λ, skew/JSD 계수)
- seed, step, micro/accum/seq, token budget, raw bytes/documents exposed
- 코드 revision 식별자와 결과 schema version

로드 시 vocab size만 맞는 **permuted tokenizer**도 거부해야 한다. 경고 후 계속하지 않고 fail-fast한다.

현 checkpoint는 tokenizer hash/revision을 내장하지 않고, legacy 로그에는 내부 `kd_teacher`와 실제 외부 `kd_teacher_hf`가 함께 남을 수 있다. 따라서 기존 `QT0/Q256T`는 새 평가로 점수를 다시 낼 수 있어도, 필수 hash를 복원·검증하지 못하면 **legacy/unverified training artifact**로 표시하며 P082 인과 확증의 seed 1337로 재사용하지 않는다.

#### 5.2.1 cache identity hard gate

현재 cache 재사용 경로는 이름/token 수 중심이고 tokenizer/filter/raw-manifest hash를 충분히 강제하지 않아 `exact=False`에서 다른 cache가 먼저 잡힐 수 있다. P082의 모든 팔은 다음 중 **둘 다** 충족해야 한다.

1. 실행 인자는 `--exact-cache`를 강제하고, 실험 시작 전 resolved cache 경로·hash를 manifest와 대조한다.
2. cache lookup/reader를 수정해 dataset source, filter, tokenizer ID/revision/hash, vocab/special IDs, raw document manifest/order, token count/dtype/seq, seed/crop 규약이 하나라도 다르면 hard fail한다.

Gemma 팔은 기존 probe에서 관찰된 `gemma-3-1b-pt` tokenizer snapshot과 270M teacher의 우연한 byte 동일성에 의존하지 않는다. **정확한 tokenizer model ID·revision·파일 SHA-256을 한 정본으로 고정**하고 teacher tokenizer와 학생 cache tokenizer의 모든 byte와 id↔token/special-ID mapping이 같아야 한다.

### 5.3 KD loss와 진단

| 구현 | 요구사항 |
|---|---|
| `--kd-divergence {fkl,rkl,jsd,skew}` | fp32 chunk 계산, 각 loss의 명시된 수식과 일치, reduction·T² 규약 명시 |
| `--kd-alpha-schedule {constant,linear,wsd}` | LR schedule과 독립 제어, step별 α·누적 유효 KD 질량 기록; WSD-LR 결합은 별도 flag/arm |
| token weight/mask | teacher advantage, entropy, margin, 정답 검증 mask 지원 |
| gradient 진단 | CE와 KD 각각의 norm·cosine·유효 가중비를 고정 주기로 측정 |
| teacher 진단 | CE/bpb, entropy, top-k mass, student agreement, 언어/도메인 slice |
| `kd_every` 회계 | 실제 teacher forward 수·적용 token 수·평균 유효 KD 계수 출력 |
| 안정성 | NaN/Inf, grad spike, collapse, early EOS, 반복률 gate |

현재 [`kd_cache.py`](../tinylm/train/kd_cache.py)는 이 실험의 정본으로 쓰지 않는다.

- 외부 HF teacher cache를 만들지 못한다.
- reader가 `micro_bs`·`seq`만 경고하고 data/steps/accum/temp/seed/teacher/tokenizer hash를 강제하지 않는다.
- top-k retained mass를 tail bucket/재정규화 없이 사용해 truncated KL이 편향된다.

offline KD가 필요하면 모든 provenance를 hard fail로 검사한다. naive top-k는 편향되므로 **tail/other bucket 보존을 검증한 objective** 또는 [Sparse Logit Sampling](https://aclanthology.org/2025.acl-long.885/)의 unbiased importance-sampling 후보를 구현한 뒤 온라인 full-KL과 gradient 기대값/근사오차를 먼저 잰다.

### 5.4 mixed on-policy — prompt-output/SFT gate 뒤 조건부

필요 구성:

1. source prompt `x`, gold/verified response `y`, rollout 구간을 명시한 학생 생성기와 `λ` 비율의 teacher-forced/student-generated batch mixer
2. 학생 prefix에 대한 teacher logits 또는 sequence feedback
3. prompt/response boundary와 attention/loss mask
4. 길이 정규화, EOS·반복·빈 문자열 방지
5. rollout replay buffer를 쓸 경우 snapshot/hash/생성 설정 저장
6. `λ=0`이 기존 off-policy 결과를 재현하고 `λ=1`이 실제 학생 token을 쓰는 단위 테스트

generic raw pretraining에 적용할 때는 crop 앞부분을 prompt, 뒷부분을 continuation으로 삼는 위치 규칙·rollout 길이·원래 continuation CE anchor를 사전 고정한다. 이 외삽은 **GKD/MiniLLM 재현으로 명명하지 않는다.** 단순 fixed-corpus RKL도 toy/fixed-logit 진단일 뿐 counted training arm이 아니다.

### 5.5 sequence/rationale·preference 경로

| 위치 | 필요한 것 |
|---|---|
| 신규 `tinylm/data/sft_loader.py` 계열 | record boundary 유지, prompt label `-100`, assistant-only tokens만 loss |
| `chat/serialize.py` 연결 | 교사는 공식 HF chat template, 학생은 §4.3.1에서 고른 serializer를 적용하고 최종 text를 native tokenizer로 재인코딩. `train_thinking=False`와 role mask를 구현·검증 |
| `trainer.py` | masked CE의 정확한 `sum/count`; `ce_chunk`와 `ignore_index=-100` 호환 |
| 데이터 생성/검증 도구 | n-best, exact/rule verifier, language·length·repetition·dedup filter |
| TinyDataset adapter | `paraphrases`, `near_negatives`, `violated_relation`, `why_wrong`를 pair/listwise schema로 변환 |
| preference loss | answer-only CE가 먼저 이긴 뒤 DPO/ORPO 또는 margin/ranking 중 하나를 분리 도입 |

승격 여부와 무관하게 held-out v2.4와 기존 공개 benchmark의 prompt/answer는 teacher 데이터 생성 입력에 절대 넣지 않는다.

### 5.6 최소 검증 항목

구현 후 full 학습 전에 다음을 통과해야 한다.

- FKL 기존 함수와 신규 FKL의 toy/full chunk 결과 일치
- `α=0`이 동일 seed 무KD와 bit/허용오차 수준 재현
- `kd_every={1,2,4}` 실제 forward count 정확
- tokenizer hash 일치/불일치 positive·negative fixture
- external tokenizer native-eval parity regression
- masked SFT에서 prompt gradient 0, assistant token count 정확
- on-policy `λ=0/1` 경계 조건
- 생성 데이터 train/eval ID 교집합 0, n-gram leakage gate
- checkpoint resume 시 loss/data/teacher/tokenizer manifest 불일치 hard fail
- `exact=False`가 다른 tokenizer/filter cache를 재사용하려 할 때 hard fail하고 `--exact-cache`가 동일 hash만 선택
- legacy checkpoint 내장 metadata 부재와 sidecar 불일치를 거부하는 schema migration fixture

---

## 6. ★데이터 설계

### 6.1 logit KD 데이터

- 같은 tokenizer family 안에서는 **동일 token cache·동일 crop RNG·동일 seed**를 사용한다.
- Qwen과 Gemma 교차 비교에는 같은 raw document ID/order를 고정하고 **token 수와 raw bytes/documents를 모두 기록**한다.
- 한국어/영어, 웹/교육/개념관계 slice를 기록해 교사 이득이 어느 domain에서 생기는지 본다.
- `S1` 재현 팔 외에는 teacher advantage가 없는 문서·token에 무조건 KD를 걸지 않는다. generic raw token 가중은 held-out NLL/margin만 쓰고, 정답/과제 가중은 task-tagged sequence 데이터에만 쓴다.

### 6.2 sequence/rationale 데이터

| 층 | 내용 | 비율 시작점 | 검증 |
|---|---|---:|---|
| A | 짧은 direct answer/한두 문장 설명 | 60~75% | exact/rule/참조 답 |
| B | 짧은 다단계 설명 | 20~30% | 단계별 constraint·최종답 |
| C | 긴/강한 reasoning | 5~20% | 길이·정답·중복·형식 모두 통과 |

- Qwen과 Gemma에 **같은 source prompt ID**를 주고 n-best를 만든다.
- verifier가 둘 다 정답이면 더 짧고 명료한 응답, 한쪽만 정답이면 정답 응답, 둘 다 오답이면 폐기한다.
- teacher identity가 노출되지 않게 최종 포맷을 canonicalize하되 의미·정답은 바꾸지 않는다.
- 교사간 비교는 둘 다 verifier를 통과한 **accepted intersection**에서 하고, Q/G의 source 수·assistant loss token·n-best/생성 설정을 맞춘다. 단일교사 전체 accepted set 결과는 별도 보조표로만 낸다.
- `N_REF`는 같은 source prompt의 gold/reference 또는 교사와 독립적인 verifier-confirmed 답을 쓰며 `N_QA_*`와 같은 accepted IDs·assistant token budget을 맞춘다.
- train/val/held-out, P069 benchmark, common-bpb 원문과 exact/n-gram overlap을 차단한다.
- `stage1_train_900_v2`의 paraphrase는 같은 개념의 표현 변화, near-negative는 오개념 판별 신호로만 쓴다. held-out v2.4 후보는 생성·선별에 사용하지 않는다.

### 6.3 예산 공정성

두 표를 모두 만든다.

1. **동일 학습 token budget**: 기존 100M screen, 300M full 규약
2. **동일 compute budget**: teacher forward/생성/rollout/verifier를 포함한 GPU-hour 또는 wall time. `N_CE_GPU`는 같은 총 시간을 추가 raw CE에 사용한다.
3. **동일 accepted sequence budget**: Q/G/reference에 같은 source 교집합과 assistant loss token 수를 적용한다.

sequence SFT는 token 수가 훨씬 적을 수 있으므로 “300M pretraining과 동급”이라고 부르지 않는다. 추가 단계의 한계효과로 보고한다.

---

## 7. ★★절차와 단계별 중단 게이트

### 단계0 — protocol·평가·provenance 구현 (학습 0)

1. §5.1 tokenizer-aware evaluator, §5.2 checkpoint-embedded manifest, exact-cache hard gate를 구현한다.
2. native 기존 점수 재현, tokenizer mismatch/cache mismatch negative test, TinyDataset trivial baseline을 확인한다.
3. TinyDataset v2.4를 사용할지 검토해 MANIFEST 정본·SHA-256을 확정하고 forced-choice evaluator를 만든다. 미승격이면 v2.3을 정본으로 명시한다.
4. 실제 SQuAD train split과 새 공통 영문·한국어 원문 overlap을 감사한다.
5. §4.3.1의 현 tokenizer plain-boundary pilot과 P075 새 tokenizer 중 하나를 고정한다.
6. Qwen/Gemma revision·tokenizer hash·공식 chat template·license/notice 체크리스트를 고정한다.
7. §3.3과 아래 수치 gate를 protocol에 preregister한다.
8. legacy `run_P067_stage2_gemma270m_full.bat`(★삭제됨 — 재현 명령은 [결과 053 부록](../test_result/053_20260822_P067-단계0a-두-최신-소형모델은-KV를-버리고-있다.md)에 있다)와 현재 queue/registry entry는 `P82_G_N0`와 안정성 gate가 생길 때까지 **실행 금지·운영상 격리**한다. 사용자 요청 범위 밖이므로 이번 문서 작업에서는 batch/registry를 수정하지 않는다.

**STOP**: evaluator parity·checkpoint/cache/tokenizer identity·leakage·license 중 하나라도 실패하거나 legacy Gemma full이 여전히 자동 실행 가능 상태면 이후 학습 금지.

### 단계1 — 교사 자체와 기존 artifact 재판정 (학습 0)

1. Qwen3-0.6B-Base와 Gemma 3 270M을 동일 1차 과제로 평가한다.
2. generic raw held-out에서는 task accuracy가 아니라 문서-paired NLL/bpb·entropy·target margin으로 teacher advantage를 잰다.
3. 기존 `QT0/Q256T`를 새 evaluator로 재평가하되, 내장 provenance를 복원하지 못하면 training artifact 재사용은 금지한다.
4. common-bpb를 비중복 영문·한국어 원문으로 다시 잰다.
5. sequence 교사는 각 공식 template로 소규모 생성 품질 pilot을 하고, 이 단계에서는 학습 데이터를 대량 생성하지 않는다.

**STOP**: teacher advantage가 없는 교사는 해당 task/slice KD에서 제외한다. 기존 Qwen −0.0077이 새 비중복 원문에서 방향까지 뒤집히면 P067 신호는 corpus-specific으로 판정한다.

### 단계2 — Qwen 100M pretraining-KD screen

1. artifact tag는 `P82_Q_SCR100_S0`…`S13`으로 full tag와 분리한다. §4.2의 직접 비교쌍을 따라 실행하되 S1은 ungated 재현, S2~S13은 표의 대조군에서 한 축씩만 바꾼다.
2. 250-step run은 OOM/NaN/gradient/배관 gate로만 사용한다.
3. screen 전체 상한은 **20 GPU-hour**로 먼저 승인받는다. Wave A는 `S0/S1/S2/S3/S5/S10`으로 low/high α와 T·빈도 정합 대조를 먼저 닫는다. Wave B `S4/S6~S9/S11~S13`은 앞선 팔에 양의 신호와 직접 대조군이 있고 남은 cap 안에 들 때만 연다. cap을 넘으면 임의로 팔을 추가하지 않고 별도 승인한다.
4. 100M 결과에서 명백히 해로운 팔을 제거하고, 기준 S1과 최선 1개만 full 후보로 올린다.

**즉시 STOP**: non-finite, skip `>0`, tokenizer/cache mismatch, post-warmup `grad_max>10`. **3회 연속 STOP/조정**: `KD_grad_norm/CE_grad_norm∉[0.1,10]` 또는 cosine `≤−0.5`. 조정 후 같은 gate를 다시 통과하지 못하면 해당 팔을 종료한다.

### 단계3 — native answer-only sequence pilot

1. `N_BASE/N_CE_TOK/N_CE_GPU/N_REF`를 먼저 확보한다.
2. 동일 source와 accepted intersection에서 `N_QA_Q/N_QA_G`를 비교한다.
3. teacher 생성+verifier 비용까지 포함해 token-matched와 compute-matched 표를 모두 낸다.
4. answer-only가 reference와 compute 대조보다 추가 이득을 보인 교사만 rationale 후보로 올린다.

**데이터 STOP**: exact/rule verifier 통과율 `<70%`, 목표 언어 판정 `<95%`, 빈 응답·비정상 early-EOS `>2%`, 반복 4-gram 응답 `>5%`, accepted-set 중복 `>5%`, train/eval overlap `>0`. 이 값은 작은 blind pilot에서 evaluator 오류만으로 1회 수정한 뒤 동결하며, 기준 미달 때 데이터 수를 억지로 채우지 않는다.

### 단계4 — Gemma 100M matched screen

1. `P82_G_SCR100_N0` seed 1337을 **먼저** 실행해 exact tokenizer/cache와 수치 안정성을 확인한다.
2. 그 다음에만 `P82_G_SCR100_B`를 실행한다. `G_SCR100_B−G_SCR100_N0`만 100M Gemma KD 효과로 보고한다.
3. Qwen 최선 방법은 `G_SCR100_B`가 안정적으로 통과했을 때 `P82_G_SCR100_M` 한 팔로만 복제한다. teacher entropy 차이가 크면 사전 명시한 한 개 보정 팔만 허용한다.
4. `grad_max`가 무KD 36.9, KD 118.8/488.8이었던 기존 probe 때문에 matched 원인 분석·안정화 없이 300M/full로 승격하지 않는다.

**STOP**: `G_SCR100_N0` 없이 `G_SCR100_B` 실행 금지, legacy `G270Tfull` 실행 금지, probe val로 full 품질 예측 금지. 단계2와 같은 수치 gate를 적용한다.

### 단계5 — 300M final-checkpoint·3 seed 확증

1. ★**2026-09-03 개정 (안 B 승인)** — `C0` 를 **full core 뒤가 아니라 screen 단계에서** 돌린다. 종전 정의는 *"승자 KD 와 같은 총 GPU-hour"* 라 **승자가 정해진 뒤에만** 실행 가능했고, 그래서 **full core(약 139 GPU-h)를 정당화해야 할 게이트가 그 뒤에** 있었다. ★**개정**: Stage 2 screen 승자의 GPU-hour 에 맞춰 `C0` 를 **약 2~3 GPU-h** 로 돌리고, 🚫**`C0` 가 screen 규모에서 KD 를 이기면 full core 를 열지 않는다.** 그다음에야 matched `N0/B/M` 중 통과 팔을 seed 1337 full 로 실행한다.
2. seed 1337 승격 조건은 `(a)` 1차 과제 하나 이상 `≥+2%p`, equal-task macro `>0`, 어느 과제도 `<−2%p`가 아니거나, `(b)` `Δbpb≤−δ_bpb`이고 어느 1차 과제도 `<−2%p`가 아닌 경우다. 이는 추가 seed를 살 가치가 있는 screen일 뿐 최종 성공 기준이 아니다.
3. 승격한 팔만 seed 2024/4242를 추가하고, 최종 checkpoint로 §3.4를 판정한다. seed 1337이 승격 기준에 못 미치면 자동 추가 실행하지 않는다. `C0` 추가 seed는 KD가 N0를 이기지만 C0와의 차가 미확정일 때만 연다.
4. Qwen과 Gemma는 각각 `Q_*−Q_N0`, `G_*−G_N0`로만 인과효과를 계산한다. 두 family의 절대 CE와 teacher 크기만으로 capacity gap을 주장하지 않는다.

기존 `QT0/Q256T` seed 1337은 **checkpoint-embedded/bound manifest와 코드 의미가 모두 동일할 때만** 재사용한다. 그렇지 않으면 평가 참고자료일 뿐 새 seed의 대체물이 아니다.

### 단계6 — rationale·조건부 on-policy

1. answer-only가 통과한 교사에만 같은 accepted intersection의 short rationale을 추가한다.
2. Q/G 둘 다 `N_REF/N_CE_GPU`를 이길 때만 `N_MIX`, 그 뒤에만 preference/ranking을 연다.
3. prompt-output SFT 학생이 충분한 생성 품질을 보일 때만 `λ=0.25→0.5` mixed on-policy를 별도 counted arm으로 연다.
4. rationale와 on-policy는 각각 answer-only와 같은 token/compute 대조를 두고 효과를 분리한다.

**STOP**: 단계3 데이터 gate 또는 단계2 수치 gate를 위반하면 해당 팔을 종료한다. fixed-corpus RKL/skew-KL만으로 MiniLLM/GKD/DistiLLM 성공을 주장하지 않는다.

### 단계7 — 조건부 cross-tokenizer

sequence KD가 이겼지만 teacher logit/hidden 정보를 더 활용할 근거가 있을 때만 ALM과 DSKD의 **구현비용 대 120M 규모근거**를 먼저 비교해 prototype 하나를 고른다. prototype이 sequence KD와 compute 대조를 못 이기면 CDM/DWA/BLD/ULD를 열지 않는다.

### 단계8 — 보고

결과 문서에는 반드시 다음 표를 함께 낸다.

- 교사 자체 점수와 teacher advantage
- tokenizer family별 직접 대조 효과
- final-checkpoint 3-seed 평균·표준편차·seed-paired 효과, item/cluster CI와 원시 per-item 결과 경로
- common-bpb/val/downstream을 분리한 표
- params·packed/runtime·VRAM·wall/GPU-hour와 teacher 생성·verifier를 포함한 누적 compute
- checkpoint/tokenizer/cache/data binding hash와 legacy/unverified 여부
- 구현됨/미구현/실행됨/미실행됨 구분
- 실패·중단 팔과 중단 gate

---

## 8. 평가 상세

### 8.1 1차 과제

| 과제 | 현재 native 근거 | P082 사용법 |
|---|---|---|
| HellaSwag | 30.0→33.7 등 우연 초과·모델 차 관측 | full 또는 가능한 최대 표본, normalized score, per-item 저장 |
| PIQA | 51.7→53.7 등 작은 차 | full 표본과 bootstrap 필요 |
| ARC-e | 37.0→37.7, 우연 초과 | prompt/shot 고정, 후보 순서 고정 |
| TinyDataset held-out v2.4 **후보** | 파일·tokenizer shortcut gate는 있으나 MANIFEST 정본은 v2.3, 모델 평가 없음 | v2.4 승격/hash 확정 후 PMI/length-normalized forced choice, McNemar exact; 미승격이면 v2.3 명시 |

MMLU·ARC-c·BoolQ·BFCL은 현재 바닥/기준선 미달이라 1차 서열용으로 쓰지 않는다. sequence/SFT가 큰 도약을 보일 때 회귀·emergence 진단으로만 다시 본다.

### 8.2 언어모델 품질

- 같은 tokenizer family 내부: 동일 cache CE와 paired crop loss
- tokenizer 교차: 동일 raw text의 bpb만 사용
- 영문과 한국어 common text를 별도 보고하고 macro 평균으로 뭉개지 않는다.
- teacher/student 각자의 bytes/token, token count, 문서별 bpb 분포를 기록한다.

### 8.3 통계

- 모델 seed: 1337/2024/4242
- 과제별 점수는 표본 수로 가중하지 않고 **equal-task macro**를 1차 종합치로 사용
- 같은 문항의 item-paired bootstrap 10,000회 또는 exact McNemar와, source/document cluster bootstrap을 구분
- seed별 matched 차이를 먼저 계산해 seed-paired 평균·분산과 부호 일관성을 보고; 필요 시 seed×item hierarchical bootstrap을 보조로 사용
- item-level CI와 3-seed sign consistency는 서로 다른 불확실성으로 분리하고 어느 하나로 다른 하나를 대체하지 않음
- 다수 과제의 p-value는 Holm 보정, 효과량과 CI를 우선
- 사전 기준에 못 미친 결과는 “미확정/기각”을 분리
- 0.008 bpb는 Qwen 조건의 측정 σ가 아니라 기존 실무 규칙이다. 새 corpus/family에서 `δ_bpb`를 재고정
- final checkpoint가 1차이며 val-best/task-best는 탐색 결과로만 보고

---

## 9. ★예상 결과

| # | 예상 | 신뢰 | 빗나가면 |
|---|---|---|---|
| **E1** | 기존 Qwen FKL의 common-bpb 이득은 3 seed 평균에서도 **작거나 경계**다 | 중간 | 명확히 크면 외부 교사 KD를 다시 주력 축으로 승격 |
| ★**E2** | T=1·낮은 α 또는 JSD/skew가 `.5/T2/k4`보다 안정적이다 | 중간 | 기존 설정이 최선이면 원인은 hyperparameter가 아님 |
| ★**E3** | mixed on-policy가 generic FKL보다 downstream에서 낫지만 비용이 크다 | 낮음~중간 | 이기지 못하면 TinyLM 용량/데이터가 rollout KD를 못 받는 것 |
| **E4** | Gemma 270M이 Qwen 600M보다 항상 좋지는 않다 | 중간 | 명확히 좋아도 teacher-family 전체효과 신호일 뿐 size-only capacity-gap 검증이나 Qwen의 teacher assistant 증거가 아님 |
| ★★**E5** | 짧고 검증된 sequence KD가 raw logit KD보다 1차 과제를 더 직접적으로 올린다 | 중간 | `N_REF/N_CE_GPU`도 함께 이기지 못하면 teacher 신호가 아니라 task SFT/추가 compute 효과였던 것 |
| ★**E6** | 긴 rationale 비중이 높으면 100M급 학생은 악화하거나 형식만 모사한다 | 중간 | 긴 trace가 이기면 현재 CoT 보류 판단 재검토 |
| ★★**E7** | native tokenizer+부모초기화 트랙이 배포 Pareto에서 큰-vocab 트랙을 이긴다 | 높음 | 큰 vocab KD가 품질 차로 비용을 상쇄하면 별도 배포 후보 |

예상은 판정 기준이 아니다. 특히 **Gemma full 품질은 현재 무자료**이므로 방향을 확정적으로 예측하지 않는다.

---

## 10. ⚠️실험 시 주의사항

1. 🚫Gemma 250-step probe val을 품질로 인용하지 않는다.
2. 🚫Qwen/Gemma/native 모델의 raw CE를 교차 비교하지 않는다.
3. 🚫`GT0full` 없는 `G270Tfull`을 KD 효과로 해석하지 않는다.
4. 🚫한 seed, 한 task, common-bpb 하나로 “지능 향상”을 주장하지 않는다.
5. tokenizer vocab size만 같다고 동일 tokenizer로 간주하지 않는다.
6. `kd_every=4`의 명목 α=.5를 매 step 50% KD로 오독하지 않는다. 적용 스텝·token·gradient를 기록한다.
7. Base/PT logit KD와 instruct sequence KD를 한 이름 “Qwen KD”로 합치지 않는다.
8. teacher confidence는 정답 보장이 아니다. confidence-only gating에는 verifier/teacher-advantage 조건을 더한다.
9. 학생 rollout에서 짧은 반복·early EOS로 objective를 속이는지 반드시 검사한다.
10. current offline top-k cache를 그대로 외부 teacher 실험에 쓰지 않는다.
11. teacher 생성 데이터에 held-out·benchmark·common-text 원문을 섞지 않는다.
12. 동일 token budget과 동일 raw byte/document exposure가 다를 수 있음을 기록한다.
13. Qwen/Gemma license와 모델 revision을 확인하고 결과 재현에 필요한 snapshot을 고정한다.
14. 구현 smoke 통과와 full 실험 승인은 별도다. 배치를 만들었다고 실행 승인으로 해석하지 않는다.
15. 🚫legacy P067 Gemma full batch는 `G_N0`·수치 안정성 gate 전 실행하지 않는다. 이번 문서 작업에서 batch/registry는 수정하지 않았다.
16. 🚫`--exact-cache`와 metadata hard fail 없이 어떤 P082 학습도 시작하지 않는다.
17. 🚫off-the-shelf Gemma를 Qwen의 teacher assistant라고 부르지 않는다. Q/G 비교는 크기 외 조건이 달라 capacity-gap 검증이 아니다.
18. P075 새 tokenizer를 택하면 embedding/head shape가 바뀐다. row mapping/graft 또는 새 부모 없이 기존 native 부모초기화를 보존했다고 말하지 않는다.
19. Qwen/Gemma 공식 template로 생성하고 student serializer로 재인코딩한다. teacher serializer와 student serializer를 같은 것으로 가정하지 않는다.

---

## 11. 비용·선결

실측/외삽을 구분한다.

| 항목 | 비용 | 성격 | 선결 |
|---|---:|---|---|
| evaluator·manifest 구현 | ⚙**약 1~2일** | 추정 | 없음 |
| KD divergence·진단 | ⚙**약 1일** | 추정 | evaluator |
| mixed on-policy | ⚙**2~4일 + rollout 비용** | 추정 | 기본 KD 재현 |
| SFT/sequence 데이터 경로 | ⚙**2~3일 + 생성/검증** | 기존 검토 기반 추정 | evaluator·template |
| Qwen 무KD full 1회 | **336.8분** | P067 실측 | tokenizer cache |
| Qwen 기존 KD full 1회 | **470.3분** | P067 실측 | 약 10.62GB reserved |
| Gemma KD full 1회 | ⚙**약 8.8시간** | 250-step 외삽 | 약 14.77GB reserved |
| 3-seed 확증 | 위 비용의 약 3배 | 산술 | seed1337 gate 통과 |

### 11.1 누적 비용 envelope와 승인 상한

| 범위 | 낮음 | 예상 | 높음/중단 전 | 해석 |
|---|---:|---:|---:|---|
| Stage 2 Qwen 100M screen | 약 **14.9 GPU-h** | 15~20 GPU-h | **20 GPU-h cap** | full 실측의 1/3 선형환산으로 Wave A 6팔≈14.94h; Wave B는 신호·잔여 cap 조건부 |
| Stage 3~4 native/Gemma screen | 10 GPU-h | 20~40 GPU-h | **40 GPU-h cap** | 생성·검증 포함; 구현 후 재산정 |
| Track A token-matched full core | 약 **139 GPU-h** | 139~160 GPU-h | — | Qwen 3팔×3seed 약 64h + Gemma 계획 placeholder 약 75h; Gemma N0 실측 전 확정치 아님 |
| ★**Track A compute control (안 B)** | ★**약 2~3 GPU-h** | 2~4 GPU-h | — | ★**2026-09-03 개정** — screen 규모로 재정의. 종전 17 GPU-h 는 full core 종속이었다. 🚫**여기서 KD 가 지면 full core 를 열지 않는다** |
| rationale/on-policy | 10 GPU-h | 20~40 GPU-h | **40 GPU-h cap** | answer-only 통과 때만 |
| P082 기본범위 합계 | 약 **191 GPU-h** | **211~280 GPU-h** | **280 GPU-h hard cap** | Track C 제외. 어느 단계든 별도 실행 승인 필요 |
| 모든 선택축을 무제한 확장 | — | — | `>350 GPU-h` 가능 | 🚫P082 기본범위가 아니며 새 계획/승인 필요 |

Qwen full core 산술은 실측 5.61h(no-KD), 7.84h(KD)를 사용했다. Gemma 약 75h는 두 KD 팔의 8.8h 외삽과 아직 미측정인 N0를 포함한 **계획용 placeholder**다. Stage 4에서 실제 N0/KD 시간을 잰 뒤 arm 수·seed 수·cap을 다시 고정한다. 기존 Qwen artifact가 strict provenance를 못 만족하면 재학습 비용이 필요하다.

⚠️위 cap은 실행 승인이 아니라 비용 중단선이다. teacher 생성·verifier·평가·재시도도 누적 GPU-hour에 포함하고, 280 GPU-hour를 넘기기 전 새 계획과 별도 승인을 받는다.

---

## 12. 필요한 추가 자산

- 정확한 revision으로 고정된 Qwen3-0.6B-Base·Gemma 3 270M snapshot
- sequence KD용 Qwen/Gemma instruct snapshot 또는 안정적인 정답 생성 계약
- Qwen Apache-2.0 notice와 Gemma 사용약관 수락·attribution·synthetic-output/derivative-data 배포 체크리스트
- P075 결정서: 현 tokenizer plain-boundary pilot 또는 새 reserved-token tokenizer + row mapping/graft/새 부모
- 비중복 영문·한국어 common-text corpus와 고정 manifest
- TinyDataset held-out v2.4 승격 결정·정본/hash(미승격 시 v2.3 명시) 및 모델 forced-choice evaluator
- teacher-generated 데이터용 정답 verifier와 dedup/leakage audit
- 3 seed × per-item 결과를 모으는 통계 report 도구
- 충분한 저장공간: 외부 tokenizer cache, 생성 데이터, per-item 결과. full-vocab offline logits 저장은 금지

---

## 13. 최종 의사결정 표

| 결과 | 결론 | 다음 행동 |
|---|---|---|
| Q/G 모두 matched no-KD를 못 이김 | generic logit KD 축 기각 | 부모초기화·데이터·깊이·sequence SFT로 이동 |
| bpb만 개선, 1차 과제 무효 | 압축률 KD 신호 | “지능 향상” 주장 금지, 목적함수/데이터 변경 |
| 한 교사만 1차 과제 개선 | teacher expertise/capacity 조건부 | 이긴 교사·과제에 집중, 다른 교사 확대 중단 |
| modern KD가 FKL을 이김 | 목적함수/분포 mismatch가 원인 | 3-seed와 Gemma 재현 후 표준 후보 |
| sequence KD만 이김 | raw logits보다 task signal이 중요 | native-tokenizer SFT/선호학습 우선 |
| native sequence가 큰-vocab KD와 동급 | 배포 Pareto에서 native 채택 | ALM은 추가 이득 필요 |
| 둘 다 명확히 이김 | 서로 다른 teacher family에서 신호 재현 | cross-token을 조건부 확장. teacher assistant는 큰 교사에서 증류한 중간모델을 만드는 별도 계획에서만 검토 |

---

## 14. 선행연구

- [MiniLLM: Knowledge Distillation of Large Language Models — ICLR 2024](https://openreview.net/forum?id=5h0qf7IBZZ) · [arXiv v6의 개정 제목/본문](https://arxiv.org/abs/2306.08543) · [DOI](https://doi.org/10.48550/arXiv.2306.08543)
- [On-Policy Distillation of Language Models / GKD](https://arxiv.org/abs/2306.13649) · [DOI](https://doi.org/10.48550/arXiv.2306.13649)
- [DistiLLM](https://arxiv.org/abs/2402.03898) · [DOI](https://doi.org/10.48550/arXiv.2402.03898)
- [Pre-training Distillation for Large Language Models: A Design Space Exploration](https://aclanthology.org/2025.acl-long.181/) · [DOI](https://doi.org/10.18653/v1/2025.acl-long.181)
- [Sparse Logit Sampling](https://aclanthology.org/2025.acl-long.885/) · [DOI](https://doi.org/10.18653/v1/2025.acl-long.885)
- [Sequence-Level Knowledge Distillation](https://aclanthology.org/D16-1139/) · [DOI](https://doi.org/10.18653/v1/D16-1139)
- [Teaching Tiny Minds: Exploring Methods to Enhance Knowledge Distillation for Small Language Models](https://aclanthology.org/2024.conll-babylm.27/) — 44M/58M, CoNLL-BabyLM 2024 공식 페이지
- [Towards the Law of Capacity Gap in Distilling Language Models](https://aclanthology.org/2025.acl-long.1097/) · [DOI](https://doi.org/10.18653/v1/2025.acl-long.1097)
- [Improved Knowledge Distillation via Teacher Assistant — AAAI 2020](https://ojs.aaai.org/index.php/AAAI/article/view/5963) · [DOI](https://doi.org/10.1609/aaai.v34i04.5963)
- [On the Generalization vs Fidelity Paradox in KD](https://aclanthology.org/2025.findings-acl.923/) · [DOI](https://doi.org/10.18653/v1/2025.findings-acl.923)
- [Small Models Struggle to Learn from Strong Reasoners](https://aclanthology.org/2025.findings-acl.1301/) · [DOI](https://doi.org/10.18653/v1/2025.findings-acl.1301)
- [Investigating Mysteries of CoT-Augmented Distillation](https://aclanthology.org/2024.emnlp-main.349/) · [DOI](https://doi.org/10.18653/v1/2024.emnlp-main.349)
- [Dual-Space Knowledge Distillation](https://aclanthology.org/2024.emnlp-main.1010/) · [DOI](https://doi.org/10.18653/v1/2024.emnlp-main.1010)
- [Approximate Likelihood Matching](https://papers.neurips.cc/paper_files/paper/2025/hash/720f9f5dc751eb56952ae4fee2398f73-Abstract-Conference.html) · [DOI](https://doi.org/10.52202/085713-2653)
- [DWA-KD](https://aclanthology.org/2026.findings-eacl.181/) · [DOI](https://doi.org/10.18653/v1/2026.findings-eacl.181)
- [Byte-Level Distillation](https://aclanthology.org/2026.customnlp4u-1.9/) · [DOI](https://doi.org/10.18653/v1/2026.customnlp4u-1.9)
- [Qwen3-0.6B-Base 공식 모델 카드](https://huggingface.co/Qwen/Qwen3-0.6B-Base)
- [Gemma 3 270M 공식 모델 카드·사용조건](https://huggingface.co/google/gemma-3-270m)

---

## 15. 착수 경계

이 문서는 계획만 고정한다. **단계0의 코드 구현, batch/registry 격리 수정, 데이터 생성, smoke/test, teacher 평가, 학습 배치 작성·실행은 모두 아직 수행하지 않았다.**
착수 시에도 `단계0 → 단계1 → 단계2…` 순서와 STOP gate를 지키며, 각 GPU-hour cap과 비싼 full run은 별도 승인 뒤 수행한다.
