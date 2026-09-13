#!/usr/bin/env python3
"""P022C Stage0a: strict CUDA FP8 scaled-matmul feasibility gate."""
from __future__ import annotations

import argparse


def main() -> int:
    ap = argparse.ArgumentParser(description="P022C strict FP8 backend gate")
    ap.add_argument("--m", type=int, default=8192)
    args = ap.parse_args()

    import torch

    if not torch.cuda.is_available():
        print("[GATE FAIL] CUDA is unavailable; FP8 backend was not tested.")
        return 2
    if not hasattr(torch, "float8_e4m3fn") or not hasattr(torch, "_scaled_mm"):
        print("[GATE FAIL] this torch build has no float8_e4m3fn/_scaled_mm.")
        return 2

    device = "cuda"
    cap = torch.cuda.get_device_capability()
    print(f"GPU={torch.cuda.get_device_name()} sm_{cap[0]}{cap[1]} torch={torch.__version__}")
    tested = 0
    for k, n in ((768, 2048), (2048, 768), (768, 768)):
        x = torch.randn(args.m, k, device=device, dtype=torch.bfloat16)
        w = torch.randn(n, k, device=device, dtype=torch.bfloat16)
        sx = (448.0 / x.abs().amax().clamp_min(1e-8)).float()
        sw = (448.0 / w.abs().amax().clamp_min(1e-8)).float()
        xq = (x * sx).to(torch.float8_e4m3fn)
        wq = (w * sw).to(torch.float8_e4m3fn).t()
        try:
            out = torch._scaled_mm(
                xq,
                wq,
                scale_a=(1.0 / sx).reshape(1),
                scale_b=(1.0 / sw).reshape(1),
                out_dtype=torch.bfloat16,
            )
            torch.cuda.synchronize()
        except Exception as exc:
            print(f"[GATE FAIL] M={args.m} K={k} N={n}: {type(exc).__name__}: {exc}")
            return 3
        if out.shape != (args.m, n) or out.dtype != torch.bfloat16 or not torch.isfinite(out).all():
            print(f"[GATE FAIL] invalid output for K={k} N={n}: {out.shape} {out.dtype}")
            return 3
        tested += 1
        print(f"PASS M={args.m} K={k} N={n} out={tuple(out.shape)} dtype={out.dtype}")

    print(f"[GATE PASS] torch._scaled_mm executed on CUDA for {tested} TinyLM shapes.")
    print("NOTE: cast/scaling overhead, backward, whole-step speed, and quality remain NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
