# P092 — Dynamic Sparse Training으로 연결 희소성을 학습한다

> **승인 2026-09-13.** 정본 제안서: [`20260913_Dynamic-Sparse-Training-연결희소성-학습-제안서-approved.md`](../proposal/done/20260913_Dynamic-Sparse-Training-연결희소성-학습-제안서-approved.md)  
> P016/P025/P025B의 고정 N:M이 아니라, 자유 connectivity budget을 유지하며 prune/regrow하는 알고리즘 축이다.  
> **현재 상태(2026-09-23):** Stage0c·Stage1aT CUDA 계약과 Stage1W 30M/Stage2W 100M
> full-trainer 여덟 팔은 사용자 로그로 완료됐다([083 §9~§10](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)).
> 품질 격차는 감소했지만 기존 Stage3 gate는 실패했다. 구 Stage3W 3시드 SH는 -cancel 이력으로 보존하고,
> 승인된 Stage3Wb 병목 진단만 작성했다. 새 진단의 GPU·추론 상주는 `NOT_RUN`이다.

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
| **Stage1a ✅ 30M 완료·sparse 품질 음성** | full Transformer/trainer 30M dense/static50/DST50 | default-off·compile·mask/state-reset·finite 통과 | 0.20 H300 |
| **Stage1b ✅ 30M 완료·25% density 음성** | 30M DST75(25% density) | 50% 대비 catastrophic divergence 없음 | 0.10 H300 |
| **Stage2a ✅ 완료·문턱 실패** | 100M dense/static50/DST50/DST75 | best dynamic gap +0.19656 > 0.07 | 1~2 H300 |
| **Stage2b ⚠️ 부분** | optimizer cold-start/loss spike | 100M 본런 grad_max≤1.119, update7; 반복 spike 회복의 시간열 추가 분석은 미완 | Stage2a 포함 |
| **Stage3a HOLD** | best density 300M, 1 seed | Stage2 gap gate 음성이라 자동 진행 금지 | 1 H300 |
| **Stage3b HOLD** | runner-up/재현 seed | Stage3a 미개방 | 2~4 H300 |
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
- 완료: `run_P092_Stage1W_full_trainer_30M-done.sh` — 4팔 모두 exit0·skip0, sparse 셋 모두 dense gap>+0.15.
- 완료: `run_P092_Stage2W_full_trainer_100M-done.sh` — 4팔 모두 exit0·skip0, 최선 dynamic50도 dense gap +0.19656.
- **실행 설계 취소, 연구축 유지**: `run_P092_Stage3W_full_trainer_300M_seeds-cancel.sh` — 100M gate 실패로 기존 런처가 exit8이며, 사용자 선택인 Stage3Wb 진단→수정→한 시드와도 다르다.
  3시드 일괄안의 GPU 실행은 0건. Stage3Wb와 조건부 300M 한 시드는 별도 설계로 남는다.

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
- 2026-09-21: full trainer opt-in을 배선했다. 기본 `none`은 mask/controller를 생성하지
  않는다. static/dynamic은 inactive gradient를 optimizer 전에 차단하고, dynamic update는
  행별 top-k를 vectorize해 birth를 0으로 시작하며 AdamW/Muon state를 함께 reset한다.
  30M·100M·300M 태그 충돌은 0건이고 학습 결과는 `NOT_RUN`이다.

### 9.1 full-trainer preflight

**독립변수**: 같은 모델/seed/pool/tokenizer/schedule에서 connectivity mode·density만 변경.
**계산**: 229/763/2289 step = 30.015M/100.008M/300.024M draw. nominal 600M exact cache는
모든 팔에 공통이며 실제 train split 597M 한계를 결과에 남긴다.
**태그**: 전 팔 충돌 0.
**판정**: 30M은 진입, 100M은 Stage3 gate, 300M은 세 seed 품질. dense mask GEMM으로
속도·storage 절감을 주장하지 않는다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 9.2 2026-09-23 30M·100M full-trainer 결과와 stage gate

[결과 083 §9](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)의 여덟 JSON은 모두 exit0·skip0다. 30M dense 5.02031 대비 static50 +0.64031, dynamic50 +0.65813, dynamic25 +0.51875로 **사전 30M 중단선 +0.15를 세 branch 모두 초과**했다. 그 뒤 실행된 100M는 실측으로 보존하되 Stage1 선결을 통과한 것으로 소급 표시하지 않는다. 100M dense 3.96750 대비 dynamic50 +0.19656, dynamic25 +0.33797이고 static50 +0.17953이다. 최선 dynamic50도 **Stage3 gate +0.07 실패**다.

예측 중 “50% connectivity는 살아날 수 있다”는 이 recipe/예산에서 불성립, “75% 급락 가능성”은 관찰과 합치지만 과학적 양성 채택은 아니다. sparse 팔의 속도·상주 이득도 없다. 30M dynamic50 `grad_max=22.09` 경보가 있었고 100M는 1.119라 지속 발산 확정은 피한다. 향후 구조 희소를 재개하려면 난도를 줄인 일정·초기화 또는 별도 하드웨어 회계와 새 문턱을 사전 승인받아야 한다. 기존 Stage3 SH의 존재는 실행 권장이 아니다.

## 9.3 2026-09-23 Stage3Wb — 먼저 병목·상주를 분리, 이후 한 시드 탐색

[결과 083 §10](../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)의 후속 감사에서는 30M→100M dense 격차가 세 희소 팔 모두 감소했다. 그러나 기존 +0.15/+0.07 사전 문턱을 통과한 것은 아니다. 사용자 결정은 기존 Stage3W 3시드 런처를 삭제하지 않고 다음 순서로 재검토하는 것이다.

1. **Stage3Wb 진단(신규 .sh, 사용자 실행)**: 기존 100M 세 checkpoint의 bool mask 포함 텐서 상주, checkpoint byte, CUDA allocated delta, TTFT, decode tok/s를 dense/static50/DST50 순서와 역순으로 계측한다. 역사 학습 ms/step은 별도 표에 보존한다. [진단 런처](../run_P092_Stage3Wb_resident_speed_diagnostic.sh)는 학습 0, 약 0.2h이다.
2. **원인별 수정**: 실제 관측된 로드·상주·kernel 병목에 한정해 최소 수정하고 동일 checkpoint 정합·동일 형상·같은 측정법으로 전후를 비교한다. 현재는 dense mask GEMM이라 FLOP을 건너뛰지 않고, 일반 JSON `runtime_mb`에 mask도 포함되지 않는다. 저장 packed 수치나 synthetic kernel 우세를 모델 배포 개선으로 승격하지 않는다.
3. **300M 한 시드**: 진단과 수정 결과에서 실질적 속도 또는 배포 상주 이득이 확인되고 새 품질/비용 게이트를 사전 등록한 뒤에만 동일조건 dense/DST50 한 시드로 탐색한다. 이 미래 단계는 현재 `NOT_RUN`이며 아직 SH를 만들지 않는다. 원래 Stage3W의 gate 실패를 소급 통과시키지 않는다.

기존 `run_P092_Stage3W_full_trainer_300M_seeds.sh`는 인벤토리와 권장순서에서 **HOLD 상태로 보존**한다. 문턱 실패를 이유로 런처를 단독 제외·삭제하거나, 승인된 진단을 원래 3시드 계획의 대체 실행으로 오인하지 않는다. Stage3Wb의 성공은 병목 원인 판독이며 품질 승격이 아니다.

## 9.4 2026-09-23 옛 Stage3W 3시드 실행 설계 취소

사용자가 이번에 live SH 5건의 우선순위·취소 여부를 판단하도록 지시했다. 옛 `run_P092_Stage3W_full_trainer_300M_seeds.sh`는 100M +0.19656 대 사전 +0.07 게이트에서 exit8로 막히며, 12개 300M 학습 호출을 묶은 형태도 사용자 선택인 **Stage3Wb 진단→관측 병목 수정→동일조건 한 시드**와 맞지 않는다. 그래서 파일 내용과 역사 명령은 [`-cancel` 보존본](../run_P092_Stage3W_full_trainer_300M_seeds-cancel.sh)으로 남기고 실험 큐 활성행만 취소 이력으로 옮겼다. GPU 학습 실행은 0건이며, 이전 §9.3의 HOLD 표현은 그때의 상태 기록이다.

취소 대상은 옛 **3시드 일괄 실행 설계**뿐이다. P092 Stage0~2의 관측값, 연결희소 연구축, [Stage3Wb 진단](../run_P092_Stage3Wb_resident_speed_diagnostic.sh)은 그대로 열린다. Stage3Wb 사용자 로그에서 속도·상주·정합을 판독하고 측정된 원인을 수정·재측정한 뒤, 새 판정선을 사전등록한 300M 한 시드 런처가 필요한지 결정한다. 실패한 옛 게이트를 삭제하거나 통과했다고 소급하지 않는다.
