#!/usr/bin/env python3
"""PM001 Stage0 — Windows Triton 환경과 삼진 forward 구현을 분리 진단한다.

사용자 실행 전용. 합성 텐서만 사용하며 학습·체크포인트·데이터셋은 건드리지 않는다.
strict 계약이라 Triton 미설치/컴파일/launch 실패를 reference 성공으로 숨기지 않는다.
"""
from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _rel(a, b) -> float:
    return float((a.float() - b.float()).abs().max() / b.float().abs().max().clamp_min(1e-12))


def main() -> int:
    ap = argparse.ArgumentParser(description="PM001 strict Triton ternary contract")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", choices=("fp32", "bf16"), default="fp32")
    ap.add_argument("--dim", type=int, default=256)
    ap.add_argument("--out", type=int, default=128)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--group", type=int, default=128)
    ap.add_argument("--seed", type=int, default=1337)
    a = ap.parse_args()

    print("=" * 96)
    print("  PM001 Stage0 — ternary Triton strict contract (training 0, checkpoint 0)")
    print("=" * 96)
    print("  success criteria (registered before results):")
    print("    T0 has_triton=True and CUDA available")
    print("    T1 anneal=0.5 reference relative error: fp32 < 1e-5, bf16 < 5e-3")
    print("    T2 anneal=1.0 Triton attempts>=1, successes>=1, fallbacks=0")
    print("    T3 Triton output/x-grad/w-grad relative error < 5e-3")
    print("  NOTE: pass proves current environment + wiring, not speed or training benefit.")

    import torch
    import torch.nn.functional as F
    from types import SimpleNamespace
    from tinylm.model.ternary import ternary
    from tinylm.model.ternary_kernel import (
        reset_ternary_kernel_status,
        ternary_kernel_linear,
        ternary_kernel_status,
    )

    status0 = ternary_kernel_status()
    print("\n[environment]")
    print(f"  platform={platform.platform()}")
    print(f"  python={sys.executable}")
    print(f"  torch={torch.__version__} cuda_build={torch.version.cuda}")
    print(f"  cuda_available={torch.cuda.is_available()} device_arg={a.device}")
    print(f"  has_triton={status0['has_triton']} version={status0['triton_version']}")
    print(f"  triton_module={status0['triton_module_file']}")
    print(f"  distributions: triton={status0['triton_distribution']} "
          f"triton-windows={status0['triton_windows_distribution']}")
    print(f"  triton_import_error={status0['triton_import_error']}")
    if not status0["has_triton"]:
        print("  FAIL T0: Triton import unavailable in this exact Python interpreter.")
        return 2
    if torch.device(a.device).type != "cuda" or not torch.cuda.is_available():
        print("  FAIL T0: strict Triton contract requires an available CUDA device.")
        return 2
    if a.dim % a.group or a.group <= 0 or (a.group & (a.group - 1)):
        print(f"  FAIL input contract: group={a.group} must be a power-of-two divisor of dim={a.dim}")
        return 2

    dtype = torch.float32 if a.dtype == "fp32" else torch.bfloat16
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        print("  FAIL T0: requested bf16 but current CUDA device does not support bf16.")
        return 2
    torch.manual_seed(a.seed)
    torch.cuda.manual_seed_all(a.seed)
    device = torch.device(a.device)
    print(f"  cuda_device={torch.cuda.get_device_name(device)} "
          f"capability={torch.cuda.get_device_capability(device)}")
    x_seed = torch.randn(a.batch, a.dim, device=device, dtype=dtype)
    w_seed = torch.randn(a.out, a.dim, device=device, dtype=torch.float32) * 0.02
    probe = torch.randn(a.batch, a.out, device=device, dtype=torch.float32)
    cfg = SimpleNamespace(
        micro_group=a.group,
        twn_thr_ratio=0.7,
        ste_clip=2.5,
        sparse34=False,
        quant_anneal=1.0,
        ternary_kernel_triton=False,
        ternary_kernel_strict=True,
    )

    def run_standard(anneal: float):
        x = x_seed.detach().clone().requires_grad_(True)
        w = w_seed.detach().clone().requires_grad_(True)
        q = ternary(w, cfg)
        eff = q + (1.0 - anneal) * (w - q).detach()
        y = F.linear(x, eff.to(dtype))
        (y.float() * probe).sum().backward()
        return y.detach(), x.grad.detach(), w.grad.detach()

    def run_kernel(anneal: float, use_triton: bool):
        x = x_seed.detach().clone().requires_grad_(True)
        w = w_seed.detach().clone().requires_grad_(True)
        cfg.ternary_kernel_triton = use_triton
        cfg.ternary_kernel_strict = use_triton
        at = torch.tensor(anneal, device=device, dtype=torch.float32)
        y = ternary_kernel_linear(x, w, cfg, at)
        (y.float() * probe).sum().backward()
        return y.detach(), x.grad.detach(), w.grad.detach()

    failures = []
    standard_half = run_standard(0.5)
    reset_ternary_kernel_status()
    kernel_half = run_kernel(0.5, False)
    half_err = tuple(_rel(got, ref) for got, ref in zip(kernel_half, standard_half))
    half_tol = 1e-5 if dtype == torch.float32 else 5e-3
    print("\n[T1 anneal reference]")
    print(f"  output={half_err[0]:.3e} x_grad={half_err[1]:.3e} w_grad={half_err[2]:.3e}")
    if max(half_err) >= half_tol:
        failures.append(
            f"T1 max relative error {max(half_err):.3e} >= dtype tolerance {half_tol:.1e}")

    standard_full = run_standard(1.0)
    reset_ternary_kernel_status()
    try:
        kernel_full = run_kernel(1.0, True)
        torch.cuda.synchronize(device)
    except Exception as exc:  # noqa: BLE001 - status와 원 예외를 로그에 함께 보존한다
        print("\n[T2 strict Triton]")
        print(f"  FAIL: {type(exc).__name__}: {exc}")
        print(f"  status={ternary_kernel_status()}")
        return 1
    status = ternary_kernel_status()
    full_err = tuple(_rel(got, ref) for got, ref in zip(kernel_full, standard_full))
    print("\n[T2/T3 strict Triton]")
    print(f"  status={status}")
    print(f"  output={full_err[0]:.3e} x_grad={full_err[1]:.3e} w_grad={full_err[2]:.3e}")
    if status["attempts"] < 1 or status["triton_successes"] < 1 or status["fallbacks"] != 0:
        failures.append(f"T2 backend telemetry contract failed: {status}")
    if max(full_err) >= 5e-3:
        failures.append(f"T3 max relative error {max(full_err):.3e}")

    print("\n[verdict]")
    if failures:
        for failure in failures:
            print(f"  FAIL: {failure}")
        return 1
    print("  PASS: this interpreter compiled and executed the Triton forward with no fallback.")
    print("  This is a functionality contract only; it does not prove a speedup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
