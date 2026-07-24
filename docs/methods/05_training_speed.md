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
| **gradient checkpointing** | 🧪 | v4~ (`--no-ckpt`로 끔) | 활성 재계산으로 VRAM↓ → 큰 배치 가능 | 재계산 비용(느려질 수도) | 16GB 여유 시 `--no-ckpt`가 소폭 빠름 |
| **micro_bs / 유효배치 조정** | 🧪 | — | 큰 matmul로 SM 활용↑ | VRAM↑, 유효배치 바꾸면 LR 재탐색 | mb16은 스필 주의(2번 아래 주의) |
| **데이터 비동기 프리페치** | 💡 | — | 데이터 로딩과 연산 겹침 | 복잡도↑ | 연산 바운드라 이득 미미 → 보류 |
| **Sequence packing (패딩 제거)** | ✅ | v4~ | 문서를 이어붙인 스트림에서 연속 크롭 → 패딩 0, 밀도 100% | — | 이미 적용(Loader). 제안의 "15~30% 이득"은 이미 반영됨 |
| **Muon 옵티마이저** | 💡 | — | Linear 가중치에 스펙트럴(Newton-Schulz) 업데이트 → 같은 loss까지 step↓ | **대배치에서 이득 집중**(소배치·단일GPU엔 제한적), ternary STE와 상호작용 미검증, 구현·튜닝 비용 | muP와 결합 시 HP 전이. 1.7B·대배치 확장 때 유력. 근거 arXiv:2505.02222 |
| **MTP(학습 aux head)** | 💡 | — | 미래 2~4토큰 동시 예측 aux loss → 수렴·표현력↑ | 헤드·loss 추가 연산, 소형 모델 이득 불확실 | factorized 헤드와 결합 가능. 학습용은 DeepSeek-V3식. FastMTP는 추론용(별건) |
| **커스텀 삼진 커널(분리 모듈)** | 🧪→⚠️GPU | v6 (`--ternary-kernel[-triton]`) | int8 codes+그룹alpha 패킹, STE backward 보존. 레퍼런스=기존 경로와 등가, Triton=속도 시도 | **GPU에선 cuBLAS 대비 10×+ 느림**(소박한 커널·recompile 폭주). +compile 시 quant_anneal 값가드로 재컴파일 한도 초과 | **GPU 학습 가속 아님 → 목적은 CPU LUT 배포**. P014② 검증 완료(정확성 통과). 커널 벤치는 `--compile` 없이 |
| **Skip-Forward / Dynamic KD** | ✅ | v6 (`--kd-every K [--kd-dynamic]`) | 교사 forward를 K스텝마다 1회 → 교사 연산 1/K. dynamic은 초반 촘촘·후반 성김 | 건너뛴 스텝 KD 신호 0 → K 크면 격차 재확대(임계점 P017에서 측정) | 온라인 KD 병목(교사 full forward)의 유일한 직접 절감책. `kd_fwd_steps` 로그 |
| **압축 교사 distill** | ✅ | v6 (`--kd-teacher-tag`) | 교사를 dense(132.5M) 대신 압축 tied(≈72.9M)로 → 교사 forward ~0.55× | 교사 상한=압축 교사 품질, 순환성(교사 1회 학습 비용은 지불) | `load_dense`가 cfg로 범용 복원. P018 |
| **hidden(E=256) 정확 오프라인 KD** | 💡 | — | 교사 pre-head hidden h_E(256차)만 캐시 → logits=h_E@emb^T 로 **정확 복원**(top-k 손실 없음). 교사 body forward 제거 | 300M×256 fp16=154GB(int8 77GB, int4 38GB) 디스크. 복원 시 V×E matmul | P015 top-k 실패의 대안. E=256은 head 랭크(정확성 하한). 축소=양자화/PQ/랭크절단 |
| **Fused Cross-Entropy 커널** | 💡 | — | 큰 vocab 로짓 materialize 없이 linear+CE 융합 → 메모리·오버헤드↓ | Windows 호환 불확실 | torch.compile이 일부 융합. vocab 32k라 이득 소폭 |

## VRAM/스필 주의 (Windows, RTX 4070 Ti Super 16GB)

- VRAM을 ~15GB까지 채우면 **WDDM 공유메모리 스필**로 PCIe 왕복 → 7배 느려짐.
  목표는 "채우기"가 아니라 **스필 절벽(≈13~14GB) 아래에서 throughput 최대화**.
- `expandable_segments`는 Windows 미지원(경고만) → posix에서만 설정(v6).
- NVIDIA 제어판 "시스템 메모리 폴백 안 함"으로 두면 스필 대신 OOM(한계 파악 용이).
