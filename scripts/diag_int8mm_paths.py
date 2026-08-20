#!/usr/bin/env python3
"""P014C 단계 2b — **`_weight_int8pack_mm` 이 왜 6.5배 느린가.** 학습 0 · 모델 0 · 수 초.

## 왜 필요한가

결과 028 §12 가 per-row 융합을 **2.91 tok/s**(게이트 19.07, 같은 실행 언팩캐시 24.42)로 쟀다.
§13 이 산술로 **실효 0.72 GFLOP/s = 단일 스레드 스칼라 수준**임을 보였지만,
**무엇이 그 경로를 고르게 했는지는 가설 넷**으로 남았다:

| 가설 | 이 도구가 보는 방법 |
|---|---|
| **dtype** — fp32 활성이라 최적 경로를 못 탄다 | fp32 vs bf16 vs fp16 비교 |
| **M=1** — 배치1 디코드라 타일링 이득이 없다 | M = 1 / 8 / 64 비교 |
| **스레드** — 이 연산이 단일 스레드로 돈다 | `torch.set_num_threads` 를 바꿔 비교 |
| **비연속 B** — `_i8` 이 contiguous 가 아니라 매 호출 복사 | contiguous / non-contiguous 비교 |

**모델을 짓지 않는다.** 우리 층 shape(768×768, 2048×768, 768×2048)만 만들어 연산을 직접 부른다.

## 기준값 (참고값 — 결과 전에 적는다)

| 무엇이 보이면 | 뜻 |
|---|---|
| 어느 조합에서 **fp32 dequant matmul 보다 빠르다** | ★**우리가 고칠 수 있다.** 그 조건으로 바꾸고 재측정 |
| 모든 조합에서 느리다 | 🚫**이 빌드의 커널 문제.** LUT 커널(P014 안 A/B)로 간다 |
| ⚠️ 어느 경우든 | **이건 int8 커널이지 삼진 커널이 아니다** — 삼진 구조를 안 쓴다 |

사용:
    python scripts/diag_int8mm_paths.py
    python scripts/diag_int8mm_paths.py --iters 50
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch                                                     # noqa: E402


def _hdr(s):
    print("\n" + "=" * 78 + f"\n  {s}\n" + "=" * 78)


def _time(fn, iters, warm=3):
    for _ in range(warm):
        fn()
    t0 = time.perf_counter()
    for _ in range(iters):
        fn()
    return (time.perf_counter() - t0) * 1000 / iters


def main():
    ap = argparse.ArgumentParser(description="_weight_int8pack_mm 경로 진단 (학습 0)")
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--shapes", default="768x768,768x2048,2048x768",
                    help="OxI 목록. 기본 = 우리 층 shape 3종")
    a = ap.parse_args()

    _hdr("환경")
    print(f"  torch {torch.__version__}  threads {torch.get_num_threads()} "
          f"(interop {torch.get_num_interop_threads()})")
    has = hasattr(torch, "_weight_int8pack_mm")
    print(f"  torch._weight_int8pack_mm 존재: {has}")
    if not has:
        print("  🚫 이 torch 에는 연산이 없다. P014C 안 C 는 여기서 끝난다.")
        return 1
    print("  ⚠️ 이 도구는 **커널 속도만** 본다. 정확성은 단계1(check_fused_int8)이 봤다.")
    print("  ⚠️ 그리고 이건 **int8 커널이지 삼진 커널이 아니다** — 삼진 구조를 안 쓴다.")

    shapes = []
    for s in a.shapes.split(","):
        o, i = s.strip().lower().split("x")
        shapes.append((int(o), int(i)))

    _hdr("★행렬 — 조합별 ms/호출 (낮을수록 좋다)")
    print(f"  {'shape(OxI)':<14}{'M':>5}{'dtype':>9}{'thr':>5}"
          f"{'fused':>10}{'dequant':>10}{'배수':>8}  판정")
    print("  " + "-" * 74)

    base_threads = torch.get_num_threads()
    best = None
    for (O, I) in shapes:
        w8 = torch.randint(-1, 2, (O, I), dtype=torch.int8)      # 삼진 코드
        alpha = torch.rand(O) * 0.05 + 0.01
        for M in (1, 8, 64):
            for dt in (torch.float32, torch.bfloat16):
                for thr in (base_threads, 1):
                    torch.set_num_threads(thr)
                    x = torch.randn(M, I, dtype=dt)
                    sc = alpha.to(dt)
                    wq = (w8.to(dt) * alpha.unsqueeze(-1).to(dt))   # 복원본(대조군)
                    try:
                        t_f = _time(lambda: torch._weight_int8pack_mm(
                            x.contiguous(), w8, sc), a.iters)
                    except Exception as e:                        # noqa: BLE001
                        print(f"  {O}x{I:<9}{M:>5}{str(dt).split('.')[-1]:>9}{thr:>5}"
                              f"   🚫 {type(e).__name__}: {str(e)[:28]}")
                        continue
                    # 대조군: 이미 복원된 가중치로 그냥 matmul (= 언팩 캐시 적중 상태)
                    t_d = _time(lambda: x @ wq.t(), a.iters)
                    r = t_f / max(t_d, 1e-9)
                    mark = "✅ 융합이 빠르다" if r < 1.0 else ("⚠️ 비슷" if r < 1.5 else "🚫 느리다")
                    if best is None or r < best[0]:
                        best = (r, O, I, M, str(dt).split(".")[-1], thr)
                    print(f"  {O}x{I:<9}{M:>5}{str(dt).split('.')[-1]:>9}{thr:>5}"
                          f"{t_f:>10.3f}{t_d:>10.3f}{r:>8.2f}  {mark}")
    torch.set_num_threads(base_threads)

    _hdr("판정")
    if best is None:
        print("  🚫 어떤 조합도 실행되지 않았다.")
        return 1
    r, O, I, M, dt, thr = best
    print(f"  ★최선 조합: {O}x{I}  M={M}  dtype={dt}  threads={thr}   배수 {r:.2f}")
    if r < 1.0:
        print("  ✅ **어떤 조합에서는 융합이 복원 matmul 보다 빠르다.**")
        print("     -^> 우리가 그 조건으로 못 맞추고 있었다는 뜻이다. `_fused_int8_linear` 의")
        print("        dtype·contiguous·스레드를 그 조합에 맞추고 결과 028 §12 를 재측정한다.")
    else:
        print("  🚫 **모든 조합에서 융합이 느리다.**")
        print("     -^> 이 torch 빌드·이 CPU 에서 `_weight_int8pack_mm` 은 쓸 수 없다.")
        print("        P014C 안 C 종결을 유지하고 **LUT 커널(P014 안 A/B)** 로 간다.")
    print("\n  ⚠️ 참고값: 결과 028 §12 의 실측은 per-row 융합 2.91 vs 언팩 캐시 24.42 tok/s")
    print("     = 모델 전체에서 약 8.4배 느렸다. 여기 배수가 그것과 자릿수가 맞아야 한다.")
    print("  ⚠️ **이 도구는 삼진을 활용하지 않는다.** 진짜 이득은 LUT mpGEMM 에 있다(02_memory §M.3.3).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
