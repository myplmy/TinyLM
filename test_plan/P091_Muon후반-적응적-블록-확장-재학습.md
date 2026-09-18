# P091 — Muon 후반 적응적 블록 재학습과 foldable latent expansion

> **승인 2026-09-13.** 정본 제안서: [`20260913_Muon-후반-적응적-블록-확장-재학습-제안서-approved.md`](../proposal/done/20260913_Muon-후반-적응적-블록-확장-재학습-제안서-approved.md)  
> 사용자의 P091 승인으로 검토 원문의 미승인 번호 선점을 정식 계획번호로 해소한다.  
> **2026-09-18 흡수 승인:** 레이어 상태 기반 제안의 권장 B안을 별도 P번호 없이 이 계획에
> 흡수했다. 정본 제안서:
> [`20260918_레이어-상태기반-학습연산-재배분-타당성-검토-제안서-approved-on-going.md`](../proposal/20260918_레이어-상태기반-학습연산-재배분-타당성-검토-제안서-approved-on-going.md).
> **현재 상태:** Stage0a 독립 계약 진단 ✅PASS([결과 080](../test_result/080_20260913_P091-Stage0a-계약은-통과했고-실제-배선은-남았다.md)).
> R1의 optimizer update 분해 primitive와 AdamW/Muon CPU fixture는 `STATIC_ONLY` PASS다.
> 논리 occurrence·CLA owner를 포함한 R0 전체 mapping, controller·optimizer-state 격리·실제
> TLinear/trainer 배선, 모델 로딩·GPU 실행은 `NOT_RUN`.

## 1. 왜 — 후반 계산을 모든 parameter에 균등 배분해야 하는지 미측정이다

P005는 Muon의 초·중반 이득을, P087은 추가 token exposure의 후반 가치를 보였다.
그러나 후반에서 모든 블록을 같이 갱신하는 것이 최적인지, 짧은 probe로 효율적인
unique MLP parameter block을 골라 국소 재학습할 수 있는지는 미결이다. 또한 학습 때만
low-rank latent capacity를 붙였다가 (W\leftarrow W+sBA)로 접어 배포 형상을 유지하는 축도 안 잴다.

## 2. 질문

| # | 질문 | 왜 중요한가 |
|---|---|---|
| Q1 | 2/4/8-step probe 순위가 32~128-step 실제 개선 순위를 예측하는가 | selector 자체의 최저가 게이트 |
| Q2 | global→local, round-robin→adaptive, adaptive→expansion의 각 효과는 얼마인가 | 네 변수를 한 팔에 섞지 않는다 |
| Q3 | local optimizer state가 VRAM을 실제 ≥15% 줄이는가 | activation 지배일 수 있다 |
| Q4 | (Q(W+sBA)) 학습 후 fold가 로짓·형상·배포 상주를 보존하는가 | (Q(W)+BA)는 다른 모델이므로 금지 |
| Q5 | gate-zero sensitivity `S`와 realized normalized update `U`가 short-probe gain을 예측하는가 | 작은 update를 redundancy로 오인하지 않는 selector gate |
| Q6 | tied MLP·CLA K/V owner·mixed Muon/AdamW를 물리 tensor 중복 없이 매핑할 수 있는가 | 논리 layer와 unique parameter의 혼동 방지 |

## 3. ★예측 — 정직하게

- short probe ranking은 noisy해 Stage1에서 축이 종료될 가능성이 크다. 그 결과도 후반 sensitivity 탐색 비용의 실측이다.
- local round-robin이 VRAM을 줄여도 adaptive가 품질/초 이득을 더하지 못할 수 있다.
- r128 expansion이 개선을 더하지 못하면 expansion은 기각하고 adaptive/local 결과만 남긴다.
- `S/U` 순위가 window·panel에서는 안정적이어도 realized gain과 상관하지 않을 수 있다. 이 경우
  상태표는 설명용 진단으로만 남기고 자동 selector·동적 LR·skip은 열지 않는다.

## 4. 단계 설계

| 단계 | 무엇 | 계속 조건 | GPU-h |
|---|---|---|---:|
| **Stage0a ✅** | unique module identity 후보, default-off identity, `W+sBA` fold identity | ✅ `unique_candidates=2`, `fold_max_abs=0`([080](../test_result/080_20260913_P091-Stage0a-계약은-통과했고-실제-배선은-남았다.md)) | 0 |
| **Stage0b** | 실제 TLinear 연결, VRAM/timing smoke | NaN/skip 0, off 경로 동일 | 0.1 |
| **Stage1** | p=2/4/8 probe vs 32~128-step realized gain | median Spearman ρ≥0.5, 3 window 중 2개 top-2 포함 | 0.2~0.5 |
| **Stage2** | 100M A~E 5팔 | D>C 또는 E>D가 현 ruler 초과/명시 Pareto | 3~4 |
| **Stage3** | rank 128→256, p/n 보정 | r128 유효·미포화일 때만 | 1~2 |
| **Stage4a** | 300M e1-equivalent winner vs global | 승자 유지 | 3.5~4 |
| **Stage4b** | 같은 계보를 4,578 step/e2-equivalent까지 | Stage4a에서 축 생존 | +3.5~4 |
| **Stage5** | 다른 seed 재현 | 두 seed 방향 일치 | 7~8 |

Stage2의 원인분리 팔은 고정한다.

| 팔 | optimizer | 범위 | 선택 | expansion |
|---|---|---|---|---|
| A | Muon | global | 없음 | off |
| B | AdamW | global | 없음 | off |
| C | AdamW | local | round-robin | off |
| D | AdamW | local | adaptive | off |
| E | AdamW | local | adaptive | r128 |

`B-A`, `C-B`, `D-C`, `E-D`만 각 변수의 순효과로 읽는다. 후보는 physical layer가
아니라 `id(module)`로 중복제거한 unique MLP parameter block이다. Stage0a 독립 primitive는
trainer에 아직 연결하지 않아 기존 기본 경로를 바꾸지 않는다.

### 4.1 레이어 상태 제안 B안 흡수 — R0~R3

새 실험번호를 만들지 않고 P091 selector 질문에 다음 계약을 포함한다.

| 흡수 단계 | 무엇 | 다음 단계 조건 | 상태·비용 |
|---|---|---|---|
| **R0 schema** | logical occurrence, unique MLP/attention tensor, CLA K/V owner, optimizer group을 분리하고 `S/U` 필드 고정 | shared tensor 중복 0, K/V 공급과 잔차 기여 구분 | `DESIGNED`, GPU 0 |
| **R1a audit primitive** | 기존 `OptimizerAudit`에 total/WD/optimizer-only update와 normalized ratio를 opt-in으로 추가 | AdamW·Muon 분리, parameter 중복 차단 | 구현·CPU fixture `STATIC_ONLY` PASS |
| **R1b integration** | 실제 TinyLM mapping·audit on/off 오염·timing을 모델 경로에서 대조 | 기본 off 동일, Muon post-NS delta 포착, overhead 별도 | 모델·GPU `NOT_RUN` |
| **R2 진단** | selector 전용 패널에서 CLA-safe gate-zero `S`와 여러 window의 `U` 측정 | window·panel rank 안정, mapping 오류 0 | 모델·GPU `NOT_RUN` |
| **R3 예측력** | 기존 Stage1의 32~128-step realized gain과 `S/U` ranking 대조 | median Spearman `rho≥0.5`, 3 window 중 2개 top-2 | 기존 Stage1에 흡수 |

`S`는 잔차 기여 ablation이며 CLA K/V 공급 중단으로 부르지 않는다. `U`는 raw gradient가 아니라
weight decay를 분리한 실제 optimizer update를 parameter norm으로 정규화한다. 첫 개입은 후보
group LR 하나만 바꾸며, blockwise LR과 structured execution skip을 같은 결과로 합치지 않는다.

R3가 실패하면 동적 selector·controller·skip은 종료한다. R3가 통과해도 blockwise LR(B)과
fixed structured layer dropout(C)은 각각 별도 후속 계획·승인으로 분리한다.

## 5. 판정 기준

- Stage0 fold: 확장 출력과 fold 후 출력 허용오차 0(동일 dtype/연산 경로 진단).
- Stage1: ρ≥0.5와 top-2 조건을 모두 넘지 못하면 adaptive selector 종료.
- R0/R1: 논리 occurrence와 unique tensor의 중복 집계 0, audit off 동일, on/off timing 오염 별도 보고.
- R2/R3: selector panel과 final panel 분리; 여러 window의 순위 안정성과 realized gain 예측력을
  모두 넘지 못하면 상태 기반 자동화를 종료.
- 품질형: 현 계열 2σ ruler보다 적어도 1배 이상 개선, wall-clock 악화 ≤10%.
- 효율형: 품질은 ruler 안 동급이며 wall-clock ≥15% 감소 또는 peak reserved VRAM ≥15% 감소.
- 최종 채택: Stage5의 두 seed에서 방향 일치. 단일 seed로 기본 학습법을 바꾸지 않는다.

## 6. 비용

| 경로 | 누적 GPU-h |
|---|---:|
| Stage1에서 종료 | 0.3~0.6 |
| Stage2까지 | 3.3~4.6 |
| Stage5까지 최대 | **18.3~22.6** |

## 7. 실행 진입점

- 역사 완료(Windows): `run_P091_Stage0a_late_refine_contract-done.bat` — CPU 계약 진단 PASS([결과 080](../test_result/080_20260913_P091-Stage0a-계약은-통과했고-실제-배선은-남았다.md)).
- WSL 사용자 queue 콘솔 PASS: `run_P091_R1_optimizer_audit_contract.sh` — R1a synthetic CPU
  fixture만 실행했다. 당시 launcher가 `runlog.py`를 우회해 `test_result/` 원본은 미보존이므로
  실제 모델 mapping·selector 증거로 확대하지 않는다.
- 미작성: R1b~R3와 Stage0b~Stage5. 다음은 R0 mapping 문서 대조와 실제
  TLinear/controller·optimizer-state 격리 범위를 별도로 고정하고, 구현 뒤 사용자 스모크를 통과한
  경우에만 Stage1을 연다.

사용자의 2026-09-18 후속 지시는 **기능 gate 구현과 WSL `.sh` 준비**까지 승인했다. 이는 R1a
primitive에만 적용하며 모델 로딩, smoke, GPU, 장기 학습과 B/C 후속 개입의 자동 승인은 아니다.

## 8. 한계

- 현 primitive의 fold identity는 ternary quantizer/quant-cache/TLinear에 연결된 것이 아니다.
- `2 epoch-equivalent`는 300M pool의 복원추출 4,578 step이지 각 토큰을 정확히 두 번 보는 순차 epoch가 아니다.
- controller set은 training pool에서 분리하고 validation을 selector에 쓰지 않는다.
- Stage1은 selector 진단이지 최종 품질 실험이 아니다.
- 같은 seed·token order만으로 paired branch라고 부르지 않는다. model/optimizer/scheduler/RNG,
  data cursor, accumulation boundary, AMP와 compile signature까지 복원해야 한다.

### 정적 preflight(2026-09-18)

| 점검 | 결과 |
|---|---|
| 유사 실험 조회 | 같은 `S/U→realized gain` 예측 실험 없음; D안은 P091과 중복이라 여기 흡수 |
| 소유권 | P091이 selector·local refine을 소유; blockwise LR/skip은 R3 뒤 별도 계획 |
| 태그·진입점 | R1a CPU 계약용 `.sh`만 준비; 학습 tag·본런 `.sh` 없음 |
| 보호 경계 | 데이터·모델·GPU·smoke 접근 없음 |

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 9. 실행 이력 / 갱신

- 2026-09-13: P091 승인·번호 정식화. unique-candidate/default-off/fold primitive와 Stage0a 배치 작성. 동적 결과 `NOT_RUN`.
- 2026-09-13: Stage0a CPU 계약 진단 PASS([결과 080](../test_result/080_20260913_P091-Stage0a-계약은-통과했고-실제-배선은-남았다.md)). 예측한 primitive 계약은 성립했지만 selector·VRAM·품질 예측은 아직 대조하지 못했다. Stage0b 실제 배선이 다음 게이트다.
- 2026-09-18: 레이어 상태 기반 제안 권장 B안을 별도 번호 없이 흡수했다. R0 schema와 R1~R3
  gate를 계획에 추가했다.
- 2026-09-18: R1a optimizer audit v2와 AdamW/Muon synthetic CPU fixture PASS. 전체 모델 mapping,
  audit off 동일성·timing, selector 예측력은 계속 `NOT_RUN`이다.
- 2026-09-18: WSL queue에서도 R1a 콘솔 PASS를 관찰했다. 원본 로그 미보존 결함을 교정했지만
  교정 후 재실행 전에는 durable-log E2E를 주장하지 않는다. 다음 단계는 그대로 R0 mapping과
  R1b 실제 모델 audit이다.
