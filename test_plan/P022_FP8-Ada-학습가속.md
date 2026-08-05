> ## 0단계 게이트 결과: ✅ **통과** (2026-07-30, [결과 010](../test_result/010_20260730130000_P022-FP8-0단계게이트-통과.md))

> **★차단 해제 2026-08-06 — 배치 `run_P022_stage1_fp8.bat`(가드: `--fp8` 미구현이면 정지)**
> 단계1 은 "σ 실측·REVIEW1 후" 로 보류돼 있었다. **둘 다 충족됐다** —
> σ=0.012(결과 012), REVIEW1 은 결과 024 로 **mC 확정 권고**까지 갔다.
> ⚠️ **기대값을 미리 낮춘다**: 결과 010 이 GEMM 은 스텝의 **50%뿐**이라고 이미 쟀다 →
> end-to-end **−15% 내외**(상한 −23%). **"1.63~2.08×" 를 그대로 인용하면 안 된다.**
> 대조군은 결과 024 의 `mC_wsd`(final 3.6442) — **같은 조건에 정밀도만 다르다.**
>
> 순수 GEMM **1.63~2.08×**(gate/up 1.63 · down 2.00 · attn q/o 1.86 · mb12 2.08 · large ref 1.89).
> 판정선 1.30× 를 5개 형상 전부 통과. Ada FP8:FP16 = 2:1 비율과 일치해 측정 신뢰 확보.
> 환경 문제 없음(torch 2.10.0 / CUDA 13.0 / sm_89 / `_scaled_mm` 존재) → **`torchao` 불필요**.
>
> **★그러나 end-to-end 기대는 -15% 내외다(상한 -23%)**: GEMM 이 스텝 시간의 **약 50%** 뿐이고
> (97.5 TFLOP/step ÷ 80 TFLOPS = 1.22s vs 실측 스텝 2.467s), activation 캐스팅·amax 오버헤드가
> 절감의 30~40% 를 잠식한다(delayed scaling + compile 융합으로 완화 가능하나 추가 구현).
>
> **1단계 선결조건 2건**(둘 다 없으면 결론을 못 낸다):
> 1. **σ(재현 노이즈) 실측** — FP8 의 품질 영향이 노이즈보다 큰지 판정할 수단
> 2. **REVIEW1 로 정본 아키텍처 확정** — 아키텍처 탐색과 activation 양자화를 동시에 하면 교락
>
> 1단계 범위는 결과 010 §4 참조(MLP 3 GEMM 한정, `torch._scaled_mm` 직접, 커스텀 autograd,
> delayed scaling, 250스텝 ms/step 로 -10% 게이트).

# P022 — FP8 텐서코어 학습 가속 (Ada, torchao) [도전적]

근거: torchao float8 training(Ada/Blackwell 텐서코어, torch.compile 결합) — 공개 벤치에서
소비자 40-series에 **~1.4× 처리량** 보고. LLMQ 등도 Ada FP8 동적스케일 학습 유효성 제시.

## 왜 (int8×int8과 다른 점)
- 삼진 커널은 GPU 학습 가속이 아님(§custom_ternary_kernel: weight-only는 dense와 동일 FLOPs).
- **int8×int8**은 activation 저비트 필요하나 소형모델·양자화오버헤드·동적범위손실로 학습엔 비권장
  (별도 int8 GEMM 보고 참조).
- **FP8(E4M3)** 은 int8과 달리 **지수부로 동적범위 보존** → activation 분포에 강건. Ada 텐서코어가
  FP8 GEMM을 bf16 대비 ~2× 처리(하드웨어). torchao가 per-tensor/rowwise 동적스케일 + compile
  융합을 제공해 **삼진 dequant 후 GEMM을 FP8로** 돌릴 여지가 실재.

## 핵심 가설
우리 forward 주연산 = `x(활성) @ wq(삼진 dequant, bf16)`. 이를 **x·wq 를 FP8로 캐스팅해 GEMM**
하면(누산 fp32) Ada에서 bf16 cuBLAS 대비 처리량↑. 삼진 weight 값은 alpha·{-1,0,1} 로 FP8 표현
오차가 작고(정수배), STE backward는 latent(bf16) weight로 유지 → **학습 안정성 보존** 기대.

## 리스크 / 반론 (선검증 필수)
- **소형 GEMM**: d=768·ffn=2048 는 작아 cuBLAS도 "not enough SMs". FP8 이득은 큰 M·N·K에
  집중 → 우리 스케일에서 실이득 불확실. **먼저 마이크로벤치로 확인**(아래 0단계).
- **양자화 오버헤드**: 매 matmul FP8 캐스팅/스케일 계산이 elementwise 비용. compile 융합으로
  상쇄되는지 실측.
- **STE·삼진 상호작용 미검증**: activation을 FP8로 낮추면 KD/어닐과의 결합 손실 가능.
- **Windows/torchao 호환**: torchao float8이 Windows+RTX40에서 빌드·동작하는지 선확인.
  CUDA 12.4+ 권장. 동작 안 하면 계획 보류.

## 단계
0. **마이크로벤치(코드 최소)**: `torch._scaled_mm`(FP8) vs `F.linear`(bf16) 를 우리 실제 shape
   (M=bs·seq, K=768/2048, N=768/2048)로 순수 GEMM 비교. **이득 없으면 여기서 중단**(소형모델
   결론 확정, int8 보고와 동일 귀결일 수 있음).
1. torchao 설치·Windows 동작 확인(`Float8Linear` 또는 `_scaled_mm` 경로).
2. `TLinear.forward` 에 `--fp8` 실험 분기: 완전삼진(anneal≥1) 구간에서만 FP8 GEMM, 어닐 중엔
   기존 bf16. STE backward 불변.
3. dense·tied 200~300 step ms/step + val 무손실 확인(FP8가 품질 훼손 없이 속도만).

## 판정
- 0단계 마이크로벤치에서 FP8가 bf16 대비 **유의미(>1.2×)** 여야 진행. 아니면 **소형모델에선
  FP8도 무의미** 결론 기록하고 종료(정직한 음성 결과도 가치).
- 진행 시: 같은 품질에서 step 시간 20%+↓ 목표. dense 2500→<2000 이 현실적 상한.

## 우선순위
도전적·불확실성 큼. **P021(무료 레버) 먼저** 소진 후, 여력 있을 때 0단계 마이크로벤치로 타당성
게이트. 성공 시 dense·KD 양쪽에 곱해지는 유일한 "진짜 GPU 학습 가속" 후보.
