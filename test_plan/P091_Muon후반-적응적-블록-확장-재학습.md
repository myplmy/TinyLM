# P091 — Muon 후반 적응적 블록 재학습과 foldable latent expansion

> **승인 2026-09-13.** 정본 제안서: [`20260913_Muon-후반-적응적-블록-확장-재학습-제안서-approved.md`](../proposal/done/20260913_Muon-후반-적응적-블록-확장-재학습-제안서-approved.md)  
> 사용자의 P091 승인으로 검토 원문의 미승인 번호 선점을 정식 계획번호로 해소한다.  
> **현재 상태:** Stage0a 독립 계약 진단 ✅PASS([결과 080](../test_result/080_20260913_P091-Stage0a-계약은-통과했고-실제-배선은-남았다.md)). controller·optimizer-state 격리·실제 TLinear/trainer 배선과 GPU 실행은 `NOT_RUN`.

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

## 3. ★예측 — 정직하게

- short probe ranking은 noisy해 Stage1에서 축이 종료될 가능성이 크다. 그 결과도 후반 sensitivity 탐색 비용의 실측이다.
- local round-robin이 VRAM을 줄여도 adaptive가 품질/초 이득을 더하지 못할 수 있다.
- r128 expansion이 개선을 더하지 못하면 expansion은 기각하고 adaptive/local 결과만 남긴다.

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

## 5. 판정 기준

- Stage0 fold: 확장 출력과 fold 후 출력 허용오차 0(동일 dtype/연산 경로 진단).
- Stage1: ρ≥0.5와 top-2 조건을 모두 넘지 못하면 adaptive selector 종료.
- 품질형: 현 계열 2σ ruler보다 적어도 1배 이상 개선, wall-clock 악화 ≤10%.
- 효율형: 품질은 ruler 안 동급이며 wall-clock ≥15% 감소 또는 peak reserved VRAM ≥15% 감소.
- 최종 채택: Stage5의 두 seed에서 방향 일치. 단일 seed로 기본 학습법을 바꾸지 않는다.

## 6. 비용

| 경로 | 누적 GPU-h |
|---|---:|
| Stage1에서 종료 | 0.3~0.6 |
| Stage2까지 | 3.3~4.6 |
| Stage5까지 최대 | **18.3~22.6** |

## 7. 실행 → `run_P091_*.bat`

- 완료: `run_P091_Stage0a_late_refine_contract-done.bat` — CPU 계약 진단 PASS([결과 080](../test_result/080_20260913_P091-Stage0a-계약은-통과했고-실제-배선은-남았다.md)).
- 미작성: Stage0b~Stage5. 다음은 실제 TLinear/controller·optimizer-state 격리를 별도 패치하고, 사용자 스모크 후 Stage1만 연다.

## 8. 한계

- 현 primitive의 fold identity는 ternary quantizer/quant-cache/TLinear에 연결된 것이 아니다.
- `2 epoch-equivalent`는 300M pool의 복원추출 4,578 step이지 각 토큰을 정확히 두 번 보는 순차 epoch가 아니다.
- controller set은 training pool에서 분리하고 validation을 selector에 쓰지 않는다.
- Stage1은 selector 진단이지 최종 품질 실험이 아니다.

## 9. 실행 이력 / 갱신

- 2026-09-13: P091 승인·번호 정식화. unique-candidate/default-off/fold primitive와 Stage0a 배치 작성. 동적 결과 `NOT_RUN`.
- 2026-09-13: Stage0a CPU 계약 진단 PASS([결과 080](../test_result/080_20260913_P091-Stage0a-계약은-통과했고-실제-배선은-남았다.md)). 예측한 primitive 계약은 성립했지만 selector·VRAM·품질 예측은 아직 대조하지 못했다. Stage0b 실제 배선이 다음 게이트다.
