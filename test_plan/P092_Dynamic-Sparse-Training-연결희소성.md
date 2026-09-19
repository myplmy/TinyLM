# P092 — Dynamic Sparse Training으로 연결 희소성을 학습한다

> **승인 2026-09-13.** 정본 제안서: [`20260913_Dynamic-Sparse-Training-연결희소성-학습-제안서-approved.md`](../proposal/done/20260913_Dynamic-Sparse-Training-연결희소성-학습-제안서-approved.md)  
> P016/P025/P025B의 고정 N:M이 아니라, 자유 connectivity budget을 유지하며 prune/regrow하는 알고리즘 축이다.  
> **현재 상태(2026-09-14):** Stage0c CUDA 계약은 finite loss·inactive gradient·birth/death
> 보존을 모두 통과했다([결과 083 §6](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)).
> actual `TLinear` mask와 trainer-agnostic controller의 Stage1aT 계약도 사용자 로그에서 PASS했다
> ([083 §8](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md#8-stage1at-actual-tlinear-microtrainer2026-09-19)).
> full Transformer/trainer 30M과 실제 학습·속도·메모리·품질은 여전히 `NOT_RUN`이다.

## 1. 왜 — 삼진 0과 연결 부재를 구분해야 한다

TinyLM TWN은 활성 연결에서도 quantizer가 0을 만든다. 그러나 `Q(W)=0`은 연결 슬롯이
존재하는 수치 상태이고, `M=0`은 topology에서 연결이 없는 구조 상태다. 기존
3:4/2:4는 사람이 패턴을 고정했지만, 이 계획은 전역 active budget만 고정하고 학습 중
어떤 연결을 살릴지 바꾸는 가치를 재다.

## 2. 질문

| # | 질문 | 왜 중요한가 |
|---|---|---|
| Q1 | 50%와 75% structural sparsity에서 static ERK보다 RigL/SET가 좋은가 | sparsity 자체와 rewiring 효과 분리 |
| Q2 | 살아 있는 연결의 ternary zero와 실제 effective sparsity는 얼마인가 | 연결 75% 제거를 75% 속도로 오독하지 않음 |
| Q3 | 죽은 연결의 재생·반복 주기가 품질에 필요한가 | monotonic pruning 후속 가능성 |
| Q4 | topology update 직후 loss/optimizer spike와 암묵적 비용은 얼마인가 | theoretical FLOP과 실제 비용 분리 |

## 3. ★예측 — 정직하게

- 50% connectivity는 살아날 수 있지만 75%는 ternary zero와 겹쳐 품질이 급락할 가능성이 크다.
- RigL이 static보다 좋아도 dense mask GEMM은 연산을 skip하지 않으므로 속도 이득은 0으로 기록한다.
- inactive gradient score와 optimizer cold-start를 잘못 처리하면 topology update마다 loss spike가 반복될 수 있다.

## 4. 단계 설계

`H300`은 Stage0에서 동일 장비로 재는 현행 m100 300M baseline 1회의 GPU 시간이다.

| 단계 | 무엇 | 계속 조건 | 비용 |
|---|---|---|---:|
| **Stage0a** | `S_mask`·`Z_ternary`·`S_effective`, birth/death 계약 | dense에서 `S_mask=0`, 계약 회귀 PASS | 0.01 H300 |
| **Stage0b ⚠️ 무효** | mask/ternary forward-backward 최초 시도 | `tinylm` import 전에 종료; 과학적 결과 `NOT_RUN`([083](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)) | 진입 시간만 |
| **Stage0c ✅ 완료** | CUDA mask/ternary forward-backward, inactive gradient proxy, active conservation | finite·inactive grad 12.144601·births=deaths=16로 통과([083 §6](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)) | 진입 시간만 |
| **Stage1aT ✅ 완료** | actual TLinear static50/DST50 microtrainer 계약 | active 8192/16384·transition 4, mask/inactive/active-only/birth=death/state reset PASS | [083 §8](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md#8-stage1at-actual-tlinear-microtrainer2026-09-19) |
| **Stage1a ⏸ 구현 게이트** | full Transformer/trainer 30M static50 vs DST50 | Stage1aT 로그 PASS, CLI/default-off·smoke 뒤 | 0.20 H300 |
| **Stage1b** | 30M DST75 | 50% 대비 catastrophic divergence 없음 | 0.10 H300 |
| **Stage2a** | 100M dense/static50/DST50/DST75 | best sparse dense gap ≤0.07 | 1~2 H300 |
| **Stage2b** | optimizer cold-start/loss spike | 반복 spike 회복·state 계약 정상 | Stage2a 포함 |
| **Stage3a** | best density 300M, 1 seed | 현 TinyLM 채택선 안 | 1 H300 |
| **Stage3b** | runner-up/재현 seed | 효과가 seed noise보다 큼 | 2~4 H300 |
| **Stage4** | storage/kernel 후속 판정 | 알고리즘적 생존 후만 새 제안 | GPU 0 |

Stage0a/c의 공통 정본은 `tinylm/train/sparsity_contract.py`와
`tinylm/model/sparse_connectivity.py`다. 전자는 torch 없이 세 sparsity를 분리하고, 후자는
mask forward와 inactive regrowth score를 위한 dense-gradient STE primitive를 제공한다. 아직 TLinear에
연결하지 않았다.

## 5. 판정 기준

| 조기 중단 | 결론 |
|---|---|
| 30M 후 dense gap >+0.15 | 해당 sparse branch 종료 |
| topology update마다 회복되지 않는 spike | state/ramp 수정 전 본런 금지 |
| 같은 sparsity의 DST가 static보다 지속 열세 | dynamic rewiring 기각 |
| 계측·topology overhead가 과대 | update 주기 재설계 전 중단 |
| 차이가 ternary-zero 변화만으로 설명 | structural topology 효과 미검출 |

최종 품질은 실행 시점 `scripts/_rulers.py`의 조건별 ruler로 판정한다. 시작부터
90~95% sparsity를 주축으로 삼지 않으며, 12.5% density는 75% 분기가 살아난 후에만 연다.

## 6. 비용

| 경로 | 누적 |
|---|---:|
| 최초 권장 경로 | 약 4~5 H300 |
| 최악 상한 | **≤7.65 H300** |

Stage0에서 `H300`을 실측하기 전에 절대 GPU-h를 확정값으로 바꾸지 않는다.

## 7. 실행 → `run_P092_*.bat`

- 무효 완료: `run_P092_Stage0b_dynamic_sparse_contract-done.bat` — import 실패로 과학적 게이트 `NOT_RUN`([결과 083](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)).
- 실행 완료: `run_P092_Stage0c_dynamic_sparse_contract-done.bat` — CUDA 계약 PASS가 인쇄값까지 2/2 재현됐다([결과 083 §6~§7](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)).
- Stage0a 순수 계약 회귀는 Codex 정적 검사 5/5 PASS.
- 완료: `run_P092_Stage1aT_tlinear_dst_contract-done.sh` — actual TLinear/controller 계약 PASS.
- 미작성: full trainer Stage1a~Stage3b. Stage1aT 뒤 CLI/default-off와 smoke를 연결한다.

## 8. 한계

- 현 mask primitive은 dense tensor/GEMM이므로 FLOP·wall-clock·storage 절감을 주장하지 않는다.
- Stage0c의 작은 행렬은 TLinear/ternary/optimizer 통합을 증명하지 않는다.
- P025B의 exact 2:4·native kernel·sparse-master는 이 계획에서 실험하지 않는다.
- 알고리즘적 sparsity 성공을 하드웨어 가속 성공으로 승격하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-13: 제안서 승인, 비어 있던 다음 정수 번호 P092 배정. 공통 계측·mask primitive·Stage0b 배치 작성. 실행 `NOT_RUN`.
- 2026-09-13: Stage0b는 `ModuleNotFoundError: tinylm`으로 첫 mask 연산 전에 종료([결과 083](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)). 저장소 루트 bootstrap을 추가했고 정적 검사만 PASS했다. 방법론 예측은 대조되지 않았으며 Stage0c 재실행이 필요하다.
- 2026-09-14: Stage0c는 CUDA에서 loss 6.695264, inactive gradient 합 12.144601,
  mask/effective sparsity 0.5, births=deaths=16으로 계약을 통과했다. dense tensor+mask이므로
  sparse kernel·가속·메모리·품질은 주장하지 않고 TLinear·trainer 통합 게이트로 이동한다
  ([결과 083 §6](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)).

- 2026-09-15: 같은 Stage0c 진단이 loss 6.695264, inactive gradient 12.144601,
  births=deaths=16까지 동일하게 두 번째 PASS. 작은 합성 계약 재현일 뿐 trainer·품질 게이트를
  추가로 연 것은 아니다([결과 083 §7](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)).
- 2026-09-19: `TLinear`에 default-off connectivity mask 진입점과 trainer-agnostic
  `ConnectivityController`를 구현했다. Stage1aT는 inactive dense-gradient score를 보존한 뒤 실제
  optimizer update는 active slot에만 적용하고, rewire에서 birth=death와 바뀐 slot optimizer-state
  reset을 검사한다. full Transformer 30M·속도·메모리·품질은 `NOT_RUN`이다.
- 2026-09-19: 사용자 Stage1aT 로그가 20 step·4 transition에서 계약을 통과했다. 작은 fixture의
  dynamic final loss가 static보다 0.012 높은 것은 품질 판정이 아니며 full trainer는 `NOT_RUN`이다.
