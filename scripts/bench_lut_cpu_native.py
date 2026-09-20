#!/usr/bin/env python3
"""P014D synthetic single-core benchmark: dense vs Python LUT vs native LUT."""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _time_ms(fn, warmup, iters):
    for _ in range(warmup):
        fn()
    values = []
    for _ in range(iters):
        started = time.perf_counter()
        fn()
        values.append((time.perf_counter() - started) * 1e3)
    return statistics.median(values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--iters", type=int, default=10)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--verbose-build", action="store_true")
    args = parser.parse_args()

    import torch
    import torch.nn.functional as F
    from tinylm.model.lut import TRITS_PER_BYTE, lut_linear, weight_codes
    from tinylm.model.lut_cpu import lut_linear_native_cpu

    torch.set_num_threads(args.threads)
    print(f"torch={torch.__version__} threads={torch.get_num_threads()} dtype=float32")
    print("M\tK\tN\tdense_ms\tpython_lut_ms\tnative_lut_ms\tnative_vs_dense\tnative_vs_python")
    for m, k, n in ((1, 768, 2048), (1, 2048, 768), (1, 768, 768)):
        torch.manual_seed(14000 + k + n)
        x = torch.randn(m, k, dtype=torch.float32)
        ternary = torch.randint(-1, 2, (n, k), dtype=torch.int8)
        codes, i_pad = weight_codes(ternary, TRITS_PER_BYTE)
        alpha = torch.rand(n, 1, dtype=torch.float32) + 0.25
        dense_weight = ternary.float() * alpha
        native = lambda: lut_linear_native_cpu(
            x, codes, i_pad, alpha, verbose_build=args.verbose_build
        )
        python_lut = lambda: lut_linear(
            x, codes, TRITS_PER_BYTE, i_pad, alpha=alpha, out_chunk=256
        )
        dense = lambda: F.linear(x, dense_weight)
        expected = dense()
        native_output = native()
        python_output = python_lut()
        # LUT and dense GEMM reduce K in a different order.  Preserve a tight
        # native-vs-reference check and a scale-appropriate dense comparison.
        torch.testing.assert_close(native_output, python_output, rtol=1e-4, atol=5e-5)
        torch.testing.assert_close(native_output, expected, rtol=2e-4, atol=5e-5)
        dense_ms = _time_ms(dense, args.warmup, args.iters)
        python_ms = _time_ms(python_lut, args.warmup, args.iters)
        native_ms = _time_ms(native, args.warmup, args.iters)
        print(f"{m}\t{k}\t{n}\t{dense_ms:.6f}\t{python_ms:.6f}\t{native_ms:.6f}\t"
              f"{dense_ms / native_ms:.3f}x\t{python_ms / native_ms:.3f}x")
    print("[LIMIT] synthetic v0 is a correctness/native-overhead baseline, not the model tok/s gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
