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
| **micro_bs / 유효배치 조정** | 🚫**폐기** | — | 큰 matmul로 SM 활용↑(기대) | — | ★결과 007: mb12/accum11 **OOM**(16.8~17GB), mb10/accum13(15.2GB)은 **토큰당 -0.9%(노이즈)**. **SM 이용률 이미 포화 = 연산바운드 확증.** VRAM만 낭비 |
| **데이터 비동기 프리페치** | 💡 | — | 데이터 로딩과 연산 겹침 | 복잡도↑ | 연산 바운드라 이득 미미 → 보류 |
| **Sequence packing (패딩 제거)** | ✅ | v4~ | 문서를 이어붙인 스트림에서 연속 크롭 → 패딩 0, 밀도 100% | — | 이미 적용(Loader). 제안의 "15~30% 이득"은 이미 반영됨 |
| **Muon 옵티마이저** | 💡 | — | Linear 가중치에 스펙트럴(Newton-Schulz) 업데이트 → 같은 loss까지 step↓ | **대배치에서 이득 집중**(소배치·단일GPU엔 제한적), ternary STE와 상호작용 미검증, 구현·튜닝 비용 | muP와 결합 시 HP 전이. 1.7B·대배치 확장 때 유력. 근거 arXiv:2505.02222 |
| **MTP(학습 aux head)** | 💡 | — | 미래 2~4토큰 동시 예측 aux loss → 수렴·표현력↑ | 헤드·loss 추가 연산, 소형 모델 이득 불확실 | factorized 헤드와 결합 가능. 학습용은 DeepSeek-V3식. FastMTP는 추론용(별건) |
| **커스텀 삼진 커널(분리 모듈)** | 🧪→⚠️GPU | v6 (`--ternary-kernel[-triton]`) | int8 codes+그룹alpha 패킹, STE backward 보존. 레퍼런스=기존 경로와 등가, Triton=속도 시도 | GPU 학습 가속은 **원리상 불가**(dequant 후 dense와 동일 FLOPs). `--compile` 병용 시 dynamo 크래시 → 현재 코드가 SystemExit 차단 | **"10×+ 느림"은 정정됨**(결과 003): torch.compile 재컴파일 아티팩트였고, `--compile` 없이 재측정하니 k_triton 160~250ms/step 로 정상. **커널 자체는 문제 없음.** 다만 GPU 학습 목적은 여전히 무의미 → **실사용처 = CPU LUT/AVX2 배포**(P016 3:4 정합). 벤치는 `--compile` 없이 |
| **Skip-Forward / Dynamic KD** | ✅**측정·기본값** | v6 (`--kd-every K [--kd-dynamic]`) | 교사 forward를 K스텝마다 1회 → 교사 연산 1/K. dynamic은 초반 촘촘·후반 성김 | 건너뛴 스텝 KD 신호 0 → K 크면 격차 재확대 | ★결과 005: **정적 k4 가 품질·시간 모두 최적**(3.7875 / 141.0분, full KD 대비 **-0.042·-15%**). **dynamic 우선권장 철회**(150M 혼입판의 dyn4 우세는 역전됨). **KD 기본값 = `--kd-every 4`** |
| **압축 교사 distill** | ✅**측정** | v6 (`--kd-teacher-tag`) | 교사를 dense(132.5M) 대신 압축 tied(≈63.5M)로 → 교사 forward 대폭↓ | 교사 상한=압축 교사 품질, 순환성(교사 1회 학습 비용은 지불) | ★결과 007: k4+압축교사+no-ckpt 조합으로 **교사 오버헤드 = dense-nockpt 대비 +19%**(2940 vs 2467 ms/step), full-KD 대비 스텝시간 **-32%**. `load_dense`가 cfg로 범용 복원. P018 |
| **hidden(E=256) 정확 오프라인 KD** | 💡 | — | 교사 pre-head hidden h_E(256차)만 캐시 → logits=h_E@emb^T 로 **정확 복원**(top-k 손실 없음). 교사 body forward 제거 | 300M×256 fp16=154GB(int8 77GB, int4 38GB) 디스크. 복원 시 V×E matmul | P015 top-k 실패의 대안. E=256은 head 랭크(정확성 하한). 축소=양자화/PQ/랭크절단 |
| **Fused Cross-Entropy 커널** | 💡 | — | 큰 vocab 로짓 materialize 없이 linear+CE 융합 → 메모리·오버헤드↓ | Windows 호환 불확실 | torch.compile이 일부 융합. vocab 32k라 이득 소폭 |
| **FP8 텐서코어 학습** | 🚪**0단계 통과·1단계 조건부** | — (P022) | Ada FP8(E4M3) GEMM = bf16 대비 구조적 2:1. 삼진 dequant 후 GEMM 을 FP8 로 | ★**GEMM 은 스텝의 50%뿐** → 상한 -23%, 캐스팅 오버헤드 감안 **실제 -15% 내외**. activation 양자화가 삼진 위에 겹침(결과 008 의 초선형 악화 우려). `--compile` 상호작용 미검증. 커스텀 autograd(fwd/dgrad/wgrad 3 GEMM) 공수 큼 | ★결과 010: 실측 **1.63~2.08×**(gate/up 1.63, down 2.00, attn 1.86). Ada 2:1 비율과 일치 → **"소형GEMM 무의미" 가설 기각**. 환경 OK(torch 2.10/CUDA 13/sm_89/`_scaled_mm`). `torchao` 불필요 — `torch._scaled_mm` 직접. **1단계 선결 = σ 실측 + REVIEW1 아키텍처 확정** |
| **int8×int8 텐서코어 GEMM** | ⛔검토후보류 | — | activation까지 int8화한 IMMA GEMM | 소형모델 이득 marginal + 양자화오버헤드 + 동적범위손실 + STE복잡. 학습엔 부적합. Ada는 2×(A100/H100의 2~4× 아님) | 결론: 학습 미도입. CPU 배포는 삼진-weight LUT 경로가 별개 |
| **Sophia 옵티마이저** | ⏸**보류** | — (P023) | 대각 Hessian 곡률로 스텝수↓. 논문 125M–1.5B에서 ~2× | 재현성 데이터·튜닝 의존, 삼진 STE 상호작용 미검증, HP 재탐색 | **P026 통과 후 착수**(2026-07-30 결정). P026 과 같은 자원(steps)을 노려 교락되고, 판정에 노이즈 실측이 선결. arXiv:2305.14342 |
| **점진적 스태킹(model growth)** | 💡 | — (P024) | 얕게→깊이 성장, 연산 재사용 → 같은 품질 총 벽시계↓(RAPTR 33%) | 성장 스케줄 민감, CLA/KV-bank 재배선, 어닐 상호작용 | dense 교사 학습비 절감에 적용. arXiv:2402.05913 |
| **cooldown-QAT 융합 스케줄** | 🧪**구현완료·실측대기** | v6 (`--anneal-end`·`--decay-frac`) | LR 감쇠와 QAT(어닐)를 겹쳐 중복 full-precision 업데이트 제거 | 스케줄 정렬만 → 저비용·저위험. **기본값 0.60/0.2 = 종전 동작 무변** | 종전 어닐 종료 0.60 vs WSD 감쇠시작 0.81 = **487스텝 어긋남**. `--sched wsd --anneal-end 0.80` 이 정렬(잔차 29스텝=1.3%, warmup 오프셋). 배치 `run100m_P026.bat`. arXiv:2509.22935 |
| **데이터 풀 다양성(`--pool-tokens`)** | ✅**측정·채택** | v6 | 학습토큰은 그대로 두고 샘플 풀만 확대 → 반복 노출 감소 | 토큰화 1회 비용·디스크 | ★결과 006: 같은 300M 학습에서 풀 300M→600M 만으로 dense **3.8241→3.7045(-0.12)**. **학습시간 증가 0 의 무료 품질 레버.** 신규 기준선은 풀 ≥ 2× 학습토큰 필수. 포화점 미측정 |
| **2:4 준정형 희소(GPU)** | 💡→🧪게이트 | — (P025) | 희소 텐서코어로 학습 GEMM 최대 2×(Ada 지원). 메모리+속도 동시 | 50% 강제-0 품질리스크(3:4보다 공격적), 소형GEMM 이득 불확실, cuSPARSELt/Windows 제약 | 마이크로벤치 게이트. 삼진 정합(Sparse-BitNet arXiv:2603.05168) |
| **URL/메타데이터 prepend(데이터)** | 💡 | — (P012 추가) | 문서 앞 출처/메타 prepend로 목표loss 토큰 30~40%↓ | 한국어 셋은 URL 원본 부재 가능(score 대체) | 연산바운드에서 절대 벽시계 줄이는 데이터측 레버. arXiv:2511.21613 |
| **SplitK 융합 dequant+GEMM(추론)** | 📄참고 | — | 스키니(M=1-16) 메모리바운드 W4A16 GEMM을 SplitK atomic으로 가속 | **추론 decode 전용**. 학습은 M=8192 대배치=연산바운드라 무관. cuBLAS 아닌 naive Triton DP 대비 수치 | 우리 학습엔 부적합. GPU decode 시 ternary_kernel 업그레이드 경로. arXiv:2402.00025 |

## accum/steps 착시 주의 (중요)

이 코드에서 **1 step = accum micro-batch 묶음**이라 ms/step은 accum에 ~선형이다. accum을 줄이면
ms/step은 주지만 step당 토큰(=micro_bs×accum×seq)도 줄어 **고정 토큰까지 총 벽시계는 거의 불변**
(연산 바운드). 즉 "accum 조정으로 step 반감"은 총시간 이득이 아니다. 실제 벽시계 레버는:
**(a) `--no-ckpt`**(재계산 제거, 단일 최대, 15~30%↓·VRAM 확인), **(b) micro_bs↑**(SM 활용),
**(c) KD 오버헤드 소거**(dyn4+압축교사), **(d) 데이터효율 P012**(목표loss까지 토큰↓), **(e) seq-warmup
P013**, **(f) FP8 P022**(선검증). 조합 벤치 = **P021**. 정직한 상한: 연산바운드·이론하한 ~2.2s이라
dense step <1250 반감은 비현실적 — KD는 ≈dense까지, dense는 no-ckpt로 소폭.

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
