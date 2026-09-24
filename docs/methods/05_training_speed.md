# 5. 학습 속도

벽시계 시간 단축. 현재 m100 300M ≈ dense 97.5분 / tied ~90분.
**주의: 이 스텝은 거의 연산 바운드**(이론 하한 ~2.2s vs 실측 ~2.6~3.3s)라 큰 폭 단축은 어렵다.

| 기법 | 상태 | 버전 | 작동원리(개선 기여) | 트레이드오프 | 특기 |
|---|---|---|---|---|---|
| **bf16 autocast** | ✅ | v4~ | 텐서코어 활용, GradScaler 불필요 | — | 주 matmul이 bf16이라 TF32 이득은 제한적 |
| **torch.compile** | ✅ | v5~ | 그래프 컴파일·커널 융합 | 첫 스텝 컴파일 수 분 | "Not enough SMs"로 max_autotune GEMM은 생략 |
| **pin_memory + non_blocking** | ✅ | v4~ | H2D 전송을 연산과 겹침 | — | Loader가 이미 적용 |
| **TF32 + cudnn.benchmark** | 🧪 | v6 | fp32 matmul→TF32, 고정 shape 오토튠 | 소폭(주연산 bf16이라) | `set_float32_matmul_precision('high')` |
| **reduce-overhead (CUDA그래프)** | 🧪 | v6 (`--compile-mode`) | 커널 런치·파이썬 오버헤드를 그래프로 묶음 → 10~25% 가능 | grad accum과 충돌 → 각 forward 전 `cudagraph_mark_step_begin()` 필요(v6에서 처리), VRAM 약간↑ | 연산 바운드라 이득 불확실. 문제 시 `--compile-mode default` |
| **gradient checkpointing off (`--no-ckpt`)** | ✅**측정·채택** | v4~ | 활성 재계산 제거 → forward 1회 | VRAM **13.5GB**(스필벽 바로 아래). **tied+KD+dense교사에는 금지**(15.7GB↑, OOM 위험) | ★결과 007: 정상상태 **2982→2467 ms/step = -17.3%**. **단일 최대 엔지니어링 레버.** dense 런 표준 |
| **micro-batch 크기 `M = mb×seq`** | 🧪**조건부**(폐기 철회) | — | micro-batch 당 토큰 M 이 클수록 GEMM·런치 효율↑ | **M 무릎 ≈ 8,192.** 아래면 손해, 위면 포화. VRAM 도 M 으로 결정 | ★결과 007+P021B: M=4096 **2550** / M=8192 **2327~2468** / M=10240 2443(포화) / M=12288 **OOM**. 표준(mb8×seq1024)은 **이미 M=8192** 라 더 올릴 이유 없음 — 007의 "이득 0"은 맞았으나 이유("연산바운드")는 **틀렸다**. ★**seq 를 줄이면 mb 를 2배로 올려 M 유지 필수**(P013 설계조건) |
| **데이터 비동기 프리페치** | 💡 | — | 데이터 로딩과 연산 겹침 | 복잡도↑ | 연산 바운드라 이득 미미 → 보류 |
| **Sequence packing (패딩 제거)** | ✅ | v4~ | 문서를 이어붙인 스트림에서 연속 크롭 → 패딩 0, 밀도 100% | — | 이미 적용(Loader). 제안의 "15~30% 이득"은 이미 반영됨 |
| ★**Muon 옵티마이저** | ✅**RMS4 사용자 기본 채택**(결과 078 §11~§15; 2026-09-18 결정) | v6 `--optimizer muon --muon-scale {jordan,rms} --muon-lr-mult N` | 행렬 73개(72.7M = 전체의 89.5%)에 Newton-Schulz 5스텝, 나머지 62개는 AdamW | RMS4는 상단·matrix WD·재귀/무재귀 네 형상·seed2024·600M·1.2B 방향 게이트를 통과. 기본 recipe는 `rms ×4, matrix WD 0`, KD off. 코드 기본 구현은 새 사용자 smoke 전 `STATIC_ONLY` | seed2024 +0.0052~+0.0061, 600M +0.0043~+0.0089, 1.2B +0.0045. 단 Stage11/12의 **1.2B-pool val은 한국어 0%**라 한국어 품질 근거가 아니며 신규 1.2B SH는 금지. WD parameter-group 정본은 [20260918 보고서](../20260918_TinyLM-Muon-RMS4-Weight-Decay-방법론-조사와-권고.md) |
| **MTP(학습 aux head)** | 💡 | — | 미래 2~4토큰 동시 예측 aux loss → 수렴·표현력↑ | 헤드·loss 추가 연산, 소형 모델 이득 불확실 | factorized 헤드와 결합 가능. 학습용은 DeepSeek-V3식. FastMTP는 추론용(별건) |
| **커스텀 삼진 커널(분리 모듈)** | 🧪→⚠️GPU | v6 (`--ternary-kernel[-triton]`) | int8 codes+그룹alpha 패킹, STE backward 보존. 레퍼런스=기존 경로와 등가, Triton=속도 시도 | GPU 학습 가속은 **원리상 불가**(dequant 후 dense와 동일 FLOPs). `--compile` 병용 시 dynamo 크래시 → 현재 코드가 SystemExit 차단 | **"10×+ 느림"은 정정됨**(결과 003): torch.compile 재컴파일 아티팩트였고, `--compile` 없이 재측정하니 k_triton 160~250ms/step 로 정상. **커널 자체는 문제 없음.** 다만 GPU 학습 목적은 여전히 무의미 → **실사용처 = CPU LUT/AVX2 배포**(P016 3:4 정합). 벤치는 `--compile` 없이 |
| **Skip-Forward / Dynamic KD** | ✅**역사적 측정·현재 기본 비활성** | v6 (`--kd-every K [--kd-dynamic]`) | 교사 forward를 K스텝마다 1회 → 교사 연산 1/K. dynamic은 초반 촘촘·후반 성김 | KD off에서는 작동하지 않음. 명시적 KD 연구 팔에만 적용 | 결과 005에서는 정적 k4가 full KD보다 빨랐으나, 결과 038과 사용자 결정으로 기준 recipe는 KD off. `kd_every=4`를 전역 기본이라고 부르지 않음 |
| **압축 교사 distill** | ✅**측정** | v6 (`--kd-teacher-tag`) | 교사를 dense(132.5M) 대신 압축 tied(≈63.5M)로 → 교사 forward 대폭↓ | 교사 상한=압축 교사 품질, 순환성(교사 1회 학습 비용은 지불) | ★결과 007: k4+압축교사+no-ckpt 조합으로 **교사 오버헤드 = dense-nockpt 대비 +19%**(2940 vs 2467 ms/step), full-KD 대비 스텝시간 **-32%**. `load_dense`가 cfg로 범용 복원. P018 |
| **hidden(E=256) 정확 오프라인 KD** | 💡 | — | 교사 pre-head hidden h_E(256차)만 캐시 → logits=h_E@emb^T 로 **정확 복원**(top-k 손실 없음). 교사 body forward 제거 | 300M×256 fp16=154GB(int8 77GB, int4 38GB) 디스크. 복원 시 V×E matmul | P015 top-k 실패의 대안. E=256은 head 랭크(정확성 하한). 축소=양자화/PQ/랭크절단 |
| **Fused Cross-Entropy 커널** | 💡 | — | 큰 vocab 로짓 materialize 없이 linear+CE 융합 → 메모리·오버헤드↓ | Windows 호환 불확실 | torch.compile이 일부 융합. vocab 32k라 이득 소폭 |
| **FP8 텐서코어 학습** | 🚪**0단계 통과·1단계 조건부** | — (P022) | Ada FP8(E4M3) GEMM = bf16 대비 구조적 2:1. 삼진 dequant 후 GEMM 을 FP8 로 | ★**GEMM 은 스텝의 50%뿐** → 상한 -23%, 캐스팅 오버헤드 감안 **실제 -15% 내외**. activation 양자화가 삼진 위에 겹침(결과 008 의 초선형 악화 우려). `--compile` 상호작용 미검증. 커스텀 autograd(fwd/dgrad/wgrad 3 GEMM) 공수 큼 | ★결과 010: 실측 **1.63~2.08×**(gate/up 1.63, down 2.00, attn 1.86). Ada 2:1 비율과 일치 → **"소형GEMM 무의미" 가설 기각**. 환경 OK(torch 2.10/CUDA 13/sm_89/`_scaled_mm`). `torchao` 불필요 — `torch._scaled_mm` 직접. **1단계 선결 = σ 실측 + REVIEW1 아키텍처 확정** |
| **int8×int8 텐서코어 GEMM** | ⛔검토후보류 | — | activation까지 int8화한 IMMA GEMM | 소형모델 이득 marginal + 양자화오버헤드 + 동적범위손실 + STE복잡. 학습엔 부적합. Ada는 2×(A100/H100의 2~4× 아님) | 결론: 학습 미도입. CPU 배포는 삼진-weight LUT 경로가 별개 |
| **Sophia 옵티마이저** | ⏸**보류** | — (P023) | 대각 Hessian 곡률로 스텝수↓. 논문 125M–1.5B에서 ~2× | 재현성 데이터·튜닝 의존, 삼진 STE 상호작용 미검증, HP 재탐색 | **P026 통과 후 착수**(2026-07-30 결정). P026 과 같은 자원(steps)을 노려 교락되고, 판정에 노이즈 실측이 선결. arXiv:2305.14342 |
| **점진적 스태킹(model growth)** | 💡 | — (P024) | 얕게→깊이 성장, 연산 재사용 → 같은 품질 총 벽시계↓(RAPTR 33%) | 성장 스케줄 민감, CLA/KV-bank 재배선, 어닐 상호작용 | dense 교사 학습비 절감에 적용. arXiv:2402.05913 |
| **어닐 형태(선형 램프 vs 계단)** | 🚫**실측완료·효과 미검출**(P035, 결과 022) | v6 (`--anneal-shape`·`--anneal-start`) | 계단 어닐로 'FP→별도 QAT' 중복을 인위 생성해 기전 유무를 검정 | 2×2 모두 최대 0.0128 안이고 step의 `grad_max`가 더 커 기본 `linear` 유지 | 같은 0.60/0.80·linear/step 격자는 반복하지 않는다. 새 후보는 동역학 계측이 원인을 보일 때만 연다 |
| **cooldown-QAT 융합 스케줄(정렬)** | ⏸**실측완료·귀속 미확정**(결과 015) | v6 (`--anneal-end`·`--decay-frac`) | LR 감쇠와 QAT(어닐)를 겹쳐 중복 full-precision 업데이트 제거 | **정렬 고유 효과가 검출되지 않았다**(−0.0128 = 1.1σ < 2σ) | ★결과 015: `qb_wsd80 − qb_wsd60 = −0.0128`. 15% 스텝 절감(`qb_wsd80_s85` vs `qb_cos` **+0.0050**)은 성립하나 **wsd 성분과 분리 안 됨** → 빠진 칸 `qb_wsd60_s85`(P026 단계5) 전까지 채택 보류. arXiv:2509.22935 |
| **WSD 스케줄(스텝 절감 레버)** | ✅**측정·연구 recipe 채택** | v6 (`--sched wsd`) | 긴 plateau + 마지막 `decay_frac` 감쇠 | CLI 기본은 아직 cosine이라 명시 플래그 필요 | ★결과 015: 동일 스텝·동일 종료 LR(peak×0.1)에서 cosine 대비 **−0.0755(6.3σ)**. 시간 비용 0(정상상태 ms/step 2502~2520, 스케줄 무관). **dense 에서만 확인** — tied+KD 미검증 |
| **anneal 동역학 계측** | ✅**A0~A2 구현·CPU fixture**, A3 `E2E_NOT_RUN` | `anneal_schedule.py`, `--anneal-audit*` | LR/quant/aux 식을 분리하고 quant 거리·code flip·점유·경계여유·grad/update RMS를 저빈도 JSONL로 기록 | CPU 복사·동기화가 섞여 계측 on 속도는 인용 금지; 기본값·품질은 안 바뀜 | 승인된 [제안서](../../proposal/done/20260915_anneal-스케줄-분해와-계측우선-개선-approved.md). A3는 같은 초기 상태의 fresh 0.60/0.80 trajectory를 사용자가 실행한 뒤 판정 |
| **seq-length warmup(P013)** | 💡→📌**설계조건 확보** | — (P013) | 초반 짧은 seq 로 어텐션 O(seq²) 절감 | **M 유지 필수** — seq 절반이면 mb 2배 | ★P021B: mb16×seq512(M=8192) 가 표준 mb8×seq1024(M=8192) 대비 **-5.7%**. 단 seq·mb 가 동시에 변해 기여도 분리는 안 됨. 이 값을 이득 상한으로 |
| **데이터 풀 다양성(`--pool-tokens`)** | ✅**측정·조건부 채택** | v6 | 학습토큰은 그대로 두고 샘플 풀만 확대 → 반복 노출 감소 | 토큰화 1회 비용·디스크; pool별 언어비·val이 바뀌면 비교 교락 | 결과 006 log-val −0.12에는 시험지 변화가 섞였다. 같은 common text 방향은 양수지만 큰 pool의 영어 편향이 있다. 언어비를 보존한 exact cache에서만 “무료 품질 레버”로 사용 |
| **2:4 준정형 희소(GPU)** | ⚠️**GPU work 후보 / wall 음성** | — (P025B) | 희소 텐서코어로 학습·추론 GEMM 가속 가능성을 pack·M별로 분리 | Stage0cW M8192 fwd+dgrad+dense-wgrad+pack/accum event/graph **1.334~1.386×**, 동기 wall **0.926~0.959×** | TLinear·sparse wgrad·optimizer·전체 step 통합 전 채택 금지([082 §13](../../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#13-stage0cw-whole-primitive2026-09-22--gpu-work는-양성-동기-wall은-음성)) |
| **WSL native SDPA/GQA(P060B)** | ⚠️**품질 동급 / cache 정합 미통과** | — (P060B) | K/V repeat와 `enable_gqa` 백엔드를 동일 조건으로 비교 | Stage3 3-seed 속도 평균 0.9988×·reserved -1.986%; 품질 실무상 동급이지만 방향 불일치 | Stage2 cache decode NRMS 0.004489로 미통과; 기본 off 유지([088 §10](../../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md#31-최신-누적-판정-stage2wstage3w2026-09-22--품질은-실무상-동급-cache-배포-정합은-미통과)) |
| **URL/메타데이터 prepend(데이터)** | 💡 | — (P012 추가) | 문서 앞 출처/메타 prepend로 목표loss 토큰 30~40%↓ | 한국어 셋은 URL 원본 부재 가능(score 대체) | 연산바운드에서 절대 벽시계 줄이는 데이터측 레버. arXiv:2511.21613 |
| **SplitK 융합 dequant+GEMM(추론)** | 📄참고 | — | 스키니(M=1-16) 메모리바운드 W4A16 GEMM을 SplitK atomic으로 가속 | **추론 decode 전용**. 학습은 M=8192 대배치=연산바운드라 무관. cuBLAS 아닌 naive Triton DP 대비 수치 | 우리 학습엔 부적합. GPU decode 시 ternary_kernel 업그레이드 경로. arXiv:2402.00025 |

## accum/steps 착시 주의 (중요)

이 코드에서 **1 step = accum micro-batch 묶음**이라 ms/step은 accum에 ~선형이다. accum을 줄이면
ms/step은 주지만 step당 토큰(=micro_bs×accum×seq)도 줄어 **고정 토큰까지 총 벽시계는 거의 불변**
(연산 바운드). 즉 "accum 조정으로 step 반감"은 총시간 이득이 아니다. 실제 벽시계 레버는:
**(a) `--no-ckpt`**(재계산 제거, 단일 최대, **실측 -17.3%**·VRAM 확인),
**(b) `M = micro_bs×seq` 를 8,192 이상으로 유지**(무릎. 표준은 이미 충족 — 아래 §M 규칙),
**(c) KD 오버헤드 소거**(dyn4+압축교사), **(d) 데이터효율 P012**(목표loss까지 토큰↓), **(e) seq-warmup
P013**, **(f) FP8 P022**(선검증). 조합 벤치 = **P021**. 정직한 상한: 연산바운드·이론하한 ~2.2s이라
dense step <1250 반감은 비현실적 — KD는 ≈dense까지, dense는 no-ckpt로 소폭.

## ★M 규칙 — micro-batch 당 토큰 (결과 007 + P021B, 2026-07-30)

**`M = micro_bs × seq`** 하나가 **속도와 VRAM 을 동시에** 결정한다. micro_bs 단독으로 보지 말 것.

| M | 정상상태 ms/step | VRAM(`--no-ckpt`) | 판정 |
|---|---|---|---|
| 4,096 (mb8×seq512) | 2550 | 13.5GB 미만(추정) | **무릎 아래 — -8.7% 손해** |
| **8,192** (mb8×seq1024 / mb16×seq512) | 2468 / 2327 | **13.5GB** | **무릎 = 표준** |
| 10,240 (mb10×seq1024) | 2443(정규화) | 15.2GB | 포화(+1% 이내), 스필 구간 |
| 12,288 (mb12×seq1024 **또는** mb24×seq512) | — | **OOM** | 한계 초과 |

M=12,288 은 **서로 다른 두 형상(mb12×1024, mb24×512)이 똑같이 OOM** 했고 PyTorch 할당량
(12.65 GiB)까지 같았다 → VRAM 이 M 의 함수임이 교차 확인됐다.

**실무 규칙**: seq 를 절반으로 줄이면 micro_bs 를 2배로 올려 M=8,192 를 유지한다(P013 선결조건).
그러지 않으면 8.7% 를 잃는다.

## VRAM/스필 주의 (Windows, RTX 4070 Ti Super 16GB)

- VRAM을 ~15GB까지 채우면 **WDDM 공유메모리 스필**로 PCIe 왕복 → 7배 느려짐.
  목표는 "채우기"가 아니라 **스필 절벽(≈13~14GB) 아래에서 throughput 최대화**.
- `expandable_segments`는 Windows 미지원(경고만) → posix에서만 설정(v6).
- NVIDIA 제어판 "시스템 메모리 폴백 안 함"으로 두면 스필 대신 OOM(한계 파악 용이).

## WSL2 이전 검토 (작업환경)

- **여는 것**: Triton(FP8/커널/2:4·SplitK) 성숙, bitsandbytes 8-bit 옵티마이저, flash-linear-attention
  (P004 KDA), `expandable_segments`(posix) → 위 여러 레버의 전제조건을 해제. 일부 보고는 WSL2가
  네이티브 Windows보다 빠름.
- **안 여는 것(주의)**: WSL2도 GPU가 **WDDM 경유**라 **스필 절벽(≈13~14GB)은 그대로**(WSL issue #10452:
  VRAM 근접 시 공유메모리 스필로 급감). `/mnt/c` 파일 I/O 느림 → 데이터·HF캐시는 WSL2 ext4 안에 둘 것.
- **결론**: 커널레벨(FP8/2:4/ternary kernel)·8-bit 옵티마이저·KDA를 실제 추진하면 WSL2 권장. 순수
  bf16 cuBLAS 학습만이면 이득 제한적(스필 벽 불변). 근거: triton-windows(≥3.3 Windows 지원 존재하나
  Linux가 성숙), bitsandbytes Windows/ WSL2 모두 CUDA 오류 보고 잔존.

## 리서치 근거·링크 (2026-07 조사)

- 옵티마이저: [Sophia (arXiv:2305.14342)](https://arxiv.org/abs/2305.14342) 2× 주장(125M–1.5B),
  [Muon (arXiv:2505.02222)](https://arxiv.org/html/2505.02222v1) 토큰 15%↓·대배치 편중,
  재현성 유보 [Benchmarking Optimizers (arXiv:2509.01440)](https://arxiv.org/pdf/2509.01440).
- 성장/커리큘럼: [Progressive Subnetworks/RAPTR (arXiv:2402.05913)](https://arxiv.org/abs/2402.05913),
  [Curriculum-Guided Layer Scaling (arXiv:2506.11389)](https://arxiv.org/abs/2506.11389).
- 스케줄/QAT: [Compute-Optimal QAT (arXiv:2509.22935)](https://arxiv.org/abs/2509.22935),
  [Sub-100M QAT schedule×bit (arXiv:2605.25966)](https://arxiv.org/pdf/2605.25966).
- 희소/커널: [2:4 Sparsity Pretraining (arXiv:2404.01847)](https://arxiv.org/html/2404.01847v3),
  [PyTorch 2:4 blog](https://pytorch.org/blog/accelerating-neural-network-training/),
  [Sparse-BitNet (arXiv:2603.05168)](https://arxiv.org/html/2603.05168v1),
  [SplitK W4A16 (arXiv:2402.00025)](https://arxiv.org/abs/2402.00025).
- FP8: [TorchAO (arXiv:2507.16099)](https://arxiv.org/pdf/2507.16099),
  [FP8 mechanics](https://r0m1t.com/fp8forllms.html).
- 데이터: [Metadata/URL prepend (arXiv:2511.21613)](https://arxiv.org/pdf/2511.21613).
- 환경: [triton-windows](https://github.com/woct0rdho/triton-windows),
  [WSL GPU 스필 issue #10452](https://github.com/microsoft/WSL/issues/10452).

---

## ★2026-08-06 갱신 — 차단 해제 2건 · 미실험 목록

### 차단 해제

| 기법 | 종전 상태 | **지금** | 근거 |
|---|---|---|---|
| **FP8(P022 단계1)** | ⏸ "σ 실측·REVIEW1 후" | **★차단 해제** | σ=0.012 실측(결과 012) **완료**, REVIEW1 은 결과 024 로 **mC 확정 권고**까지 갔다. 두 선결 조건이 모두 충족됐다. 0단계 게이트는 이미 통과(결과 010, 순수 GEMM 1.63~2.08×) |
| **Sophia(P023)** | ⏸ "P026 통과 후" | **★차단 해제** | P026 은 결과 015 로 **종결**(정렬 무효), P035 로 **계열 종결**(형태도 무효). 자원 교락 대상이 사라졌다 |

> **FP8 의 기대값을 미리 낮춰 둔다**: 결과 010 이 이미 계산했다 — GEMM 이 스텝의 **50%** 뿐이라
> end-to-end 는 **−15% 내외**(상한 −23%)다. "1.63~2.08×" 를 그대로 인용하면 안 된다.

### P014(커스텀 삼진 커널) — ★새로운 근거가 생겼다

종전 판단은 "Triton 커널이 레퍼런스보다 빠르지 않으면 이득 없음" 이었다.
결과 016 §10.4 가 **다른 각도**를 열었다:

> batch 1 디코드에서 세 모델의 tok/s 가 파라미터 2.26배 차이에도 **5% 이내**다.
> **런치 오버헤드 바운드** 가설이 맞다면, 이득은 GEMM 을 빠르게 하는 데서 오는 것이 아니라
> **커널 개수를 줄이는 융합**에서 온다. 커스텀 커널은 정확히 그걸 할 수 있다
> (dequant + GEMM 을 하나로).

**단 가설 검정이 선결**이다 → `run_P030_stage4_layerscaling.bat`(수분, GPU 0).
**층 수를 바꿔도 tok/s 가 안 변하면** 융합도 소용없다.

### 아직 실험하지 않은 학습속도 기법

| 기법 | 상태 | 왜 아직 안 했나 | 다음 조건 |
|---|---|---|---|
| **FP8 학습(P022 단계1)** | **가능** | 선결이 방금 풀렸다 | **배치 작성 완료** `run_P022_stage1_fp8.bat` |
| **★KD 교사에 `freeze_quant`+`drop_latent`** | 💡**최우선(값싸다)** | — (P042) | 교사는 가중치가 **고정**인데 매 스텝 `refresh_quant()` 를 돌고 fp32 latent 도 들고 있다. 추론용으로 **이미 구현된 함수 두 개**를 학습 루프의 교사에 붙이면 된다 | 없음(교사는 backward 가 없다) | ★결과 014: 재양자화가 CPU 추론 시간의 **약 79%** 였다(디바이스는 다르나 같은 연산). 그리고 교사 latent 해제로 **VRAM 이 남으면 tied+KD 에도 `--no-ckpt` 가 열린다 = 추가 −17.3%**. 구현 소, 기대 큼 |
| **FP8(Ada)** | ⏸**조건부 보류** | — (P022) | 텐서코어 FP8 GEMM | 스케일링 팩터 관리 실패 시 **조용한 발산**. 삼진 STE backward 와의 상호작용 미분석 | ★결과 010: GEMM 1.63~2.08× 이나 GEMM 이 스텝의 50% → end-to-end **−15%**(표준 런 18분). **2026-08-06 판단: 지금은 구현 안 한다** — 메모리 목표와 무관하고 위 두 행이 같은 자릿수를 구현 거의 없이 준다. **트리거 = 20 GPU시간 이상 캠페인(P041 단계2·P033) 확정 시** |
| Sophia(P023) | **가능** | 선결이 방금 풀렸다 | HP 재탐색 비용이 크다 — FP8 다음 |
| 데이터 비동기 프리페치 | 보류 | 연산 바운드라 이득 미미 | 학습이 데이터 바운드가 되면 |
| int8×int8 IMMA GEMM(학습) | ⛔기각 | 소형모델 이득 marginal + 동적범위 손실 | 재검토 안 함 |
| CUDA Graphs(P027) | 미착수 | 런치 오버헤드 제거 — **결과 016 §10.4 가 이걸 다시 띄웠다** | P030 단계4 결과 후. **추론 쪽 이득이 더 클 수 있다** |
| 점진적 스태킹(P024) | 미착수 | 교사 학습 가속용. 교사 재학습 계획이 없다 | P033 스케일업 시 |
| 2:4 희소 GPU 가속(P025) | 미착수 | 희소 텐서코어. 3:4 와 별개 | 3:4 결론(결과 019 §9) 이후 우선순위 낮음 |
| **★압축 교사**(`--kd-teacher-tag`) | 🧪**구현됨·미사용** | v6 (P018, B-2) | dense 교사 대신 tied 교사로 KD | ⚠️**교사가 약해져 품질 영향** | ~교사 forward 비용 **절반** + VRAM 확보. 결과 005 가 압축 교사를 이미 측정한 이력 있음 |
| **★오프라인 KD 캐시** | 🧪**구현됨·미사용** | v6 (`--kd-cache`, P015, B-3) | 교사 top-k 를 미리 캐시 → 교사 forward **0** | ⚠️top-k 16 이라 **정보 손실**, 디스크 큼 | ~학생만 돌아 **−35% 추정** |
| **★교사 forward int8**(신규) | 💡 | — (P042 §7, B-1) | 교사도 `to_int8()`. ★결과 016 §12.3: **GPU int8 언팩은 −12~15% 뿐** | 속도 −1%(교사가 1/4 스텝) | ~VRAM **−350MB** → **`--no-ckpt`(−17.3%) 개방 확률↑**. **VRAM 을 −1% 로 사는 셈** |
| ~~accum 조정으로 스텝 반감~~ | 🚫**이득 0 확정** | — (B-5) | — | — | 🚫★결과 007: ms/step 이 accum 에 **~선형** → **총 벽시계 이득 없다.** 다시 시도하지 않는다 |

## 2026-09-19~23 WSL 후속 게이트 판정

| 계획 | 사용자 보존 결과 | 현재 판정 | 다음 |
|---|---|---|---|
| [P022C](../../test_plan/P022C_FP8-compute-shadow-precision-분리.md) | Wc cached weight `1.368/0.968/1.188×`; NRMS 3.76~3.78%·memory 전 형상 증가 | **cache-only compute 가속 음성** | activation 변환 융합/다른 format의 새 설계 전 통합 금지; shadow는 별도 |
| [P025B](../../test_plan/P025B_2대4-동적희소-프리트레이닝-sparse-master.md) | Stage0cW event/graph `1.334~1.386×`, 동기 wall `0.926~0.959×` | 큰 M GPU work 후보·호출 wall 음성 | 실제 통합이 host overhead를 없애애만 후속; 기본 경로 불변 |
| [P060B](../../test_plan/P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md) | Stage3 3-seed 속도 평균 `0.9988×`, reserved −1.986%; Stage2 cache 정합 미통과 | 품질 실무상 동급이어도 배포 적합성 미증명 | 기본 off 유지; 정합 원인·분해 설계 전 채택 금지 |
| [P091](../../test_plan/P091_Muon후반-적응적-블록-확장-재학습.md) | R2 pipeline PASS; `S rho=-1.0~0.4`, `U rho=1.0` | selector S 불안정; 속도·품질 증거 없음 | S를 기본 selector로 승격 금지 |
| [P014D](../../test_plan/P014D_LUT-배포커널-속도와-패킹.md) | native CPU v1 compiled 정합 PASS, 두 actual checkpoint native/int8 1.314×·1.231× | 1.50× 속도 문턱 미달(exit8 유효 음성) | scalar v1 기본 배포 미채택; SIMD/ABI 별도 설계([069 §11](../../test_result/069_20260902_P014D-디코드-프로파일이-경로이름을-양자화형식으로-넘겨-두-팔-다-죽었다.md)) |
| [P092](../../test_plan/P092_Dynamic-Sparse-Training-연결희소성.md) | 100M sparse mask 포함 held759.64MiB 대 dense678.92MiB; 두 순서 decode tok/s도 sparse가 낮음 | 현재 dense-mask DST의 상주·추론 가속 음성, 학습 품질 +0.07 gate 실패 | kernel/압축 배포 새 설계 전 300M 자동 재개 금지([083 §12](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)) |
| [P102A](../../test_plan/P102A_T1-S1-S2-S3-학습시간-기능계약.md) | T0/T1 같은 100M 두 팔 사용자 실행: eval/save 32.703→7.189s, whole-wall 1836.554→1802.371s(1.01897×) | eval/save 감소 방향은 관측, 나머지 약8.67s는 단일 실행 순서·clock/compile 교란 가능해 T1 기본 채택 불가 | 역순 반복·동일 fixed-crop 품질 및 원 JSON 대조 뒤 판단([093](../../test_result/093_20260925_P102A-기능통과-T1-단일순서-속도관측.md)) |
| [P093](../../test_plan/P093_구조조건부-직접공유와-완화타잉.md) | rank16 output NRMS `0.974`, rank0 대비 개선 약 `0.75%` | 현재 parent approximation 과학적 음성 | 새 parameterization 없이는 모델/GPU 단계로 진행하지 않음 |

forced SDPA의 raw warning은 모든 backend가 실패했다는 뜻이 아니었다. EFFICIENT를 강제한 팔에서
GQA head 수가 달라 해당 kernel이 선택되지 못했고, 같은 로그의 CUDNN·FLASH·default 팔은 실제로
실행됐다. 진단기는 이제 backend별 warning을 해당 행에 붙여 출력한다. 계약 PASS나 isolated
forward 속도를 학습 속도·end-to-end throughput으로 확대하지 않는다.
