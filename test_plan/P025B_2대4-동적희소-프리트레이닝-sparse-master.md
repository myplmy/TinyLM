# P025B — 2:4 동적 희소 프리트레이닝과 sparse-master

> **승인 2026-09-13.** 정본 제안서: [`20260913_TinyLM-2대4-동적희소-프리트레이닝-sparse-master-제안서-approved.md`](../proposal/done/20260913_TinyLM-2대4-동적희소-프리트레이닝-sparse-master-제안서-approved.md)  
> P025의 고정 2:4 개념을 대체하지 않고, native kernel·topology·dense/sparse master를 분리하는 후속 계획이다.  
> **현재 상태:** 공통 계측 계약과 Stage0a backend 진단만 구현. GPU·품질은 `NOT_RUN`.

## 1. 왜 — 0을 넣는 것과 실제 희소 학습은 다르다

기존 `--sparse34`는 3:4 삼진 품질·패킹 축이며 native GPU 2:4 학습 커널이 아니다.
2:4에서도 dense tensor에 mask만 곱하면 연산·optimizer state가 줄지 않는다. 따라서
native 속도, dense-master 품질, inactive state를 제거한 sparse-master, topology churn을 순서대로 재야 한다.

## 2. 질문

| # | 질문 | 왜 중요한가 |
|---|---|---|
| Q1 | 현 Ada/PyTorch에서 768↔2048·2048→768이 native 2:4 forward·input-grad를 실행하는가 | 속도 축의 0단계 선결 |
| Q2 | dense-master 2:4에서 엄격 2-of-4와 STE가 안정적인가 | topology 축을 열기 전 기준선 |
| Q3 | sparse-master가 dense inactive weight·Adam state 없이 품질·VRAM을 유지하는가 | 실제 메모리 절감의 핵심 |
| Q4 | churn annealing/adaptive freeze가 재생 이득은 유지하고 후반 비용을 줄이는가 | 동적 topology의 가치 분리 |

## 3. ★예측 — 정직하게

- 순수 sparse GEMM은 빠를 수 있지만 소형 TLinear 전체에서 end-to-end 1.10×를 넘지 못할 수 있다.
- 50% 구조 제약은 기존 3:4보다 공격적이므로 품질 대가가 큰 것이 더 가능성 있다.
- sparse-master가 dense-master와 동급이면 큰 메모리 가치가 있지만, hidden dense temporary/state가 남으면 그 주장을 철회한다.

## 4. 단계 설계

| 단계 | 무엇 | 계속 조건 | GPU-h |
|---|---|---|---:|
| **Stage0a** | 실제 MLP 형상 native 2:4 forward·input-grad·A/B 속도 | sparse 호출 성공 + 두 MLP 형상 최소 1.25× | 0.1 |
| **Stage0b** | dense vs 2:4 whole primitive forward/backward | 전체 적용 1.10× 가능성 또는 메모리 트랙 재승인 | 0.2 |
| **Stage1a** | dense-master 2:4, 250 step | NaN 0, invariant 100%, 비정상 발산 없음 | 0.25 |
| **Stage1b** | flip/death/birth/resurrection 계측 | active count·birth/death 보존 | 0.25 |
| **Stage1c** | sparse-master 250 step | hidden dense state 없음, invariant 100% | 0.3 |
| **Stage2** | 100M D/S1/S2/S3 4팔 | 최소 한 sparse-master가 후속 가치 | 2.5 |
| **Stage3a** | 300M control/dense-master/sparse-master | paired/full-val 확보 | 6.0 |
| **Stage3b** | churn cosine/adaptive freeze | Stage3a에서 sparse-master 비탈락 | 2~4 |
| **Stage4** | seed/재생성 | 분해능 근처일 때만 | 3~5 |

Stage0a의 `scripts/diag_sparse24_backend.py`는 magnitude top-2 mask의 블록별 active count,
`torch.sparse.to_sparse_semi_structured`, forward 일치, input-gradient 유한성, 동일 세션
median을 검사한다. weight-gradient·whole-step은 Stage0b 이후 소유로 남긴다.

## 5. 판정 기준

| 축 | 성공 후보 기준 |
|---|---|
| 속도 | end-to-end step ≥1.10×; Stage0a 순수 MLP 게이트는 ≥1.25× |
| 메모리 | peak training VRAM ≥10% 절감 또는 optimizer+parameter state ≥25% 절감 |
| 품질 | 현 계열 `scripts/_rulers.py` 판정선 안; 고정 σ 복사 금지 |
| topology | 모든 4-block에 정확히 2 active, dynamic update의 births=deaths |
| 재현 | 필요 Stage4에서 seed/재생성 방향 유지 |

Stage0a가 속도 게이트를 못 넘으면 학습가속 분기는 종료한다. sparse-master
메모리만 계속할지는 자동 진행하지 않고 새 판정을 받는다.

## 6. 비용

| 경로 | 누적 GPU-h |
|---|---:|
| Stage0a에서 종료 | 0.1 |
| Stage2까지 | 3.6 |
| 전 게이트 통과 최대 | **12.6~18.6** |

## 7. 실행 → `run_P025B_*.bat`

- 작성: `run_P025B_Stage0a_sparse24_backend.bat` — GPU 진단, 약 0.1h.
- 미작성: Stage0b~Stage4. 직전 게이트 로그를 결과로 회수한 후에만 연다.

## 8. 한계

- Stage0a는 sparse weight-gradient, optimizer, TLinear/STE 통합을 증명하지 않는다.
- exact 2:4 mask와 `SparseSemiStructuredTensor` 타입 확인만으로 전체 학습 가속을 주장하지 않는다.
- P092의 자유 unstructured connectivity·ERK·25/12.5% density는 이 계획에 넣지 않는다.
- 공통 계측 계약을 공유하지만 두 계획의 판정을 합치지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-13: 제안서 승인, P025B 배정. 공통 계측 계약·exact-N:M primitive·Stage0a backend 배치 작성. 실행 `NOT_RUN`.
