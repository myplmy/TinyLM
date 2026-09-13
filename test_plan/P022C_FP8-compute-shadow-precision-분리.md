# P022C — FP8 compute와 shadow precision을 분리해 연다

> **승인 2026-09-13.** 정본 제안서: [`20260913_FP8-compute-shadow-precision-format-scaling-writeback-제안서-approved.md`](../proposal/done/20260913_FP8-compute-shadow-precision-format-scaling-writeback-제안서-approved.md)  
> P022/P022B의 FP8 GEMM·사후 수치 진단을 승계하되, **compute dtype**과 **persistent shadow/write-back precision**을 같은 팔에서 바꾸지 않는다.  
> **현재 상태:** Stage0a(C0) 진단 배치만 작성. GPU·모델·품질은 `NOT_RUN`.

## 1. 왜 — 기존 FP8 결과가 답하지 못한 두 물음

P022는 Ada의 순수 FP8 GEMM 상한을, P022B는 삼진 `_wq`·활성의 E4M3 왕복 오차를 재었다.
그러나 실제 학습에서 FP8 kernel이 end-to-end 이득을 내는지, 그리고 optimizer update를
FP8/FP16 grid에 직접 write-back해도 trajectory가 유지되는지는 미측정이다. 두 축을
섞으면 실패 원인이 kernel/scaling인지 shadow 가수·반올림인지 구분할 수 없다.

## 2. 질문

| # | 질문 | 왜 중요한가 |
|---|---|---|
| Q1 | 현 GPU/PyTorch에서 TinyLM 실제 형상이 CUDA FP8 `_scaled_mm`를 타는가 | 불가하면 compute 트랙을 0.1h에 종료한다 |
| Q2 | current/delayed scaling을 포함해 BF16보다 end-to-end 이득이 있는가 | 순수 GEMM 배수는 학습 속도가 아니다 |
| Q3 | compute를 고정한 채 FP16/E4M3/E5M2 shadow write-back이 어떤 수치 실패를 내는가 | format·scale·rounding을 분리한다 |
| Q4 | H/L 고정 schedule이 low shadow의 품질 대가를 줄이는가 | runtime controller를 선제 구현하지 않는다 |

## 3. ★예측 — 정직하게

- C0의 CUDA 호출은 성공할 가능성이 크지만, 소형 행렬의 cast/amax 비용으로 C1 이득이 10%에 못 미칠 수 있다.
- E4M3 static shadow는 frozen-update를 만들 위험이 크다. FP16 sentinel이 통과하고 E4M3만 실패하면 8-bit 격자 문제로 읽는다.
- C 트랙 실패는 S 트랙 기각이 아니며, fake-quant shadow 성공은 실제 1-byte storage 증명이 아니다.

## 4. 단계 설계 — 싼 것이 다음의 게이트

| 계획 단계 | 제안서 단계 | 무엇 | 계속 조건 | 예상 GPU-h |
|---|---|---|---|---:|
| **Stage0a** | C0 | CUDA FP8 backend·TinyLM 3형상 실제 호출 | `_scaled_mm` 유한 forward 성공 | 0.1 |
| **Stage0b** | C1 | BF16/current/delayed scaling 동일세션 속도 | ≥10%, 또는 5~10%+메모리/배치 이득 | 0.7~0.8 |
| **Stage1a** | C2 | 100M compute format screen | 제어군 대비 paired 열화 +0.01 이내 | 1.1~1.6 |
| **Stage1b** | C3 | 300M compute-only 확인 | 현재 ruler에서 무열화 또는 명시적 Pareto | 3.0~3.2 |
| **Stage2a** | S0 | FP32 shadow observer replay | invisible update·ULP·distortion·ternary F1 정상 저장 | 0.2 |
| **Stage2b** | S1a | FP16/E4M3 static fake-write-back | NaN/동결 없음, +0.01 이내 | 1.1~1.6 |
| **Stage2c** | S1b | E5M2 또는 stochastic-rounding rescue | 사전 failure signature가 있을 때만 | 0~1.1 |
| **Stage3** | S2 | 100M H/L·L/H·H/L/H 고정 schedule | observer와 사전 정합, 승자 확정 | 2.1~2.7 |
| **Stage4** | S3 | 300M shadow 최종 확인 | 현 계열 ruler 안, 2-seed 후속 판정 | 1.6~3.2 |

Stage0a는 `scripts/diag_fp8_backend_gate.py`로 실제 CUDA 호출을 즉시 실패 코드로
반환하고, 기존 `scripts/bench_fp8_gemm.py`로 순수 GEMM 상한을 같은 로그에 남긴다.
Stage0a 통과 전에 Stage0b 이후 코드·배치를 작성하지 않는다.

## 5. 판정 기준

| 결과 | 판정 |
|---|---|
| C0 backend 미지원/비유한 | compute 트랙 즉시 종료; 단순 cast를 하드웨어 FP8로 쓰지 않음 |
| C1 <5% 이득·메모리 이득 없음 | compute 트랙 종료 |
| C2/S1 +0.01 초과 | 해당 format/schedule 중단 |
| 300M 최종 | `scripts/_rulers.py`가 선택한 현 계열 ruler로 판정; 고정 수치를 사전 복사하지 않음 |

## 6. 비용

| 경로 | 누적 GPU-h |
|---|---:|
| C0에서 종료 | 0.1 |
| compute 300M까지 | 4.9~5.7 |
| static shadow까지 | 6.2~7.5 |
| 전 게이트 통과 최대 | **10.4~14.5** |

## 7. 실행 → `run_P022C_*.bat`

- 작성: `run_P022C_Stage0a_fp8_backend.bat` — GPU 진단, 약 0.1h.
- 미작성: Stage0b~Stage4. 직전 게이트 PASS와 사용자 로그 회수 후에만 조건·태그를 확정한다.

## 8. 한계

- `_scaled_mm` 성공은 TLinear/STE·backward·compile 정합을 증명하지 않는다.
- 순수 GEMM 배수는 cast·amax·graph break를 포함한 end-to-end 배수가 아니다.
- fake write-back은 실제 저장공간·optimizer-state 절감을 증명하지 않는다.
- Ada/coarse scaling 결과를 Hopper/MXFP8로 일반화하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-13: 제안서 승인, P022C 배정. Stage0a 엄격 backend 게이트와 배치 작성. 실행은 `NOT_RUN`.
