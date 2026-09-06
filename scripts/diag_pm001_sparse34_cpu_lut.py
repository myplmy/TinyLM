#!/usr/bin/env python3
"""PM001 Stage1/2 — 3:4 1.25bpw CPU LUT native contract and microbenchmark.

사용자 실행 전용. 최초 native 호출은 C++ 확장을 빌드한다. 합성 텐서만 쓰며 모델
checkpoint나 학습 데이터는 읽지 않는다. build 시간은 latency 측정에서 제외한다.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _rel(a, b) -> float:
    return float((a.float() - b.float()).abs().max() / b.float().abs().max().clamp_min(1e-12))


def _make_sparse34(torch, out_features: int, in_features: int, group: int, generator):
    blocks = out_features * in_features // 4
    zero_pos = torch.randint(0, 4, (blocks,), generator=generator)
    values = (torch.randint(0, 2, (blocks, 4), generator=generator) * 2 - 1).to(torch.int8)
    values.scatter_(1, zero_pos.unsqueeze(1), 0)
    codes = values.reshape(out_features, in_features).contiguous()
    alpha = (torch.rand(out_features, in_features // group, generator=generator) * 0.04 + 0.01)
    weight = (codes.reshape(out_features, -1, group).float()
              * alpha.unsqueeze(-1)).reshape(out_features, in_features)
    return codes, alpha.contiguous(), weight.contiguous()


def _median_ms(fn, iters: int, repeats: int = 5) -> float:
    for _ in range(3):
        fn()
    samples = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        for _ in range(iters):
            fn()
        samples.append((time.perf_counter() - t0) * 1000.0 / iters)
    return statistics.median(samples)


def _contract(torch, args) -> list[str]:
    from tinylm.model.lut import pack_sparse34_rows, unpack_sparse34_rows
    from tinylm.model.sparse34_cpu import (
        load_sparse34_cpu_extension,
        sparse34_cpu_environment,
        sparse34_lut_linear,
        sparse34_lut_workspace_bytes,
    )

    failures = []
    gen = torch.Generator().manual_seed(args.seed)
    codes, alpha, weight = _make_sparse34(torch, args.out, args.dim, args.group, gen)
    x = torch.randn(args.batch, args.dim, generator=gen)
    packed, n = pack_sparse34_rows(codes)
    restored = unpack_sparse34_rows(packed, n, dtype=torch.int8)
    bad = int((restored != codes).sum())
    expected_row_bytes = ((args.dim // 4) * 5 + 7) // 8
    got_bpw = packed.numel() * 8 / codes.numel()
    print("\n[C1 row packing]")
    print(f"  shape={tuple(packed.shape)} expected_row_bytes={expected_row_bytes} "
          f"mismatch={bad} bpw={got_bpw:.6f}")
    if bad or packed.shape != (args.out, expected_row_bytes) or abs(got_bpw - 1.25) > 1e-12:
        failures.append("C1 row pack/roundtrip/1.25bpw contract failed")

    dense = torch.nn.functional.linear(x, weight)
    reference = sparse34_lut_linear(x, packed, alpha, args.group, backend="reference",
                                    out_chunk=args.out_chunk)
    rel_ref = _rel(reference, dense)
    print("\n[C2 PyTorch 32-state reference]")
    print(f"  relative_error={rel_ref:.3e}")
    if rel_ref >= 3e-5:
        failures.append(f"C2 reference relative error {rel_ref:.3e}")

    print("\n[C3 native build/load]")
    before = sparse34_cpu_environment()
    print(f"  before={before}")
    t0 = time.perf_counter()
    try:
        load_sparse34_cpu_extension(verbose=args.verbose_build)
    except Exception as exc:  # noqa: BLE001 - toolchain 원인을 그대로 로그에 남긴다
        print(f"  FAIL: {type(exc).__name__}: {exc}")
        failures.append("C3 native extension build/load failed")
        return failures
    build_s = time.perf_counter() - t0
    print(f"  loaded in {build_s:.3f}s (excluded from latency) after={sparse34_cpu_environment()}")
    native = sparse34_lut_linear(x, packed, alpha, args.group, backend="native")
    rel_native = _rel(native, dense)
    rel_pair = _rel(native, reference)
    print(f"  native_vs_dense={rel_native:.3e} native_vs_reference={rel_pair:.3e}")
    if rel_native >= 3e-5 or rel_pair >= 3e-5:
        failures.append(
            f"C3 native accuracy failed dense={rel_native:.3e} ref={rel_pair:.3e}")

    print("\n[C4 TLinear integration]")
    from tinylm.config import build_config
    from tinylm.model.ternary import TLinear
    cfg = build_config("tiny", "tied", 128, True)
    cfg.sparse34 = True
    cfg.micro_group = args.group
    lin = TLinear(cfg, args.dim, args.out)
    xi = torch.randn(args.batch, args.dim, generator=gen)
    lin.refresh_quant(torch.tensor(1.0))
    baseline = lin(xi).detach().clone()
    lin.drop_latent()
    lin.to_sparse34_lut(backend="native")
    converted = lin(xi).detach()
    rel_model = _rel(converted, baseline)
    path_ok = (lin._s34_codes is not None and lin._s34_alpha is not None
               and lin._i8 is None and lin._wq is None and lin.latent_dropped())
    print(f"  path_ok={path_ok} relative_error={rel_model:.3e} "
          f"resident_bytes={lin.sparse34_lut_bytes():,}")
    if not path_ok or rel_model >= 3e-5:
        failures.append(f"C4 TLinear integration failed path={path_ok} rel={rel_model:.3e}")

    workspace = sparse34_lut_workspace_bytes(args.batch, args.dim)
    generic_entries = ((args.dim + 4) // 5) * 243
    sparse_entries = (args.dim // 4) * 32
    resident = packed.numel() + alpha.numel() * alpha.element_size()
    effective_bpw = resident * 8 / codes.numel()
    print("\n[C5 structural efficiency ledger]")
    print(f"  activation_LUT_entries generic_g5={generic_entries:,} sparse34={sparse_entries:,} "
          f"ratio={generic_entries/sparse_entries:.3f}x")
    print(f"  native_workspace={workspace:,} bytes for batch_rows={args.batch}")
    print(f"  resident code+fp32_alpha={resident:,} bytes effective_bpw={effective_bpw:.6f}")
    print("  packed code alone=1.25bpw; no (O,I) int8/fp32 reconstructed weight tensor.")
    return failures


def _benchmark(torch, args) -> None:
    from tinylm.model.lut import weight_codes, lut_linear
    from tinylm.model.sparse34_cpu import sparse34_lut_linear

    print("\n" + "=" * 96)
    print("  Stage2 CPU microbenchmark — median ms/call; build time already excluded")
    print("  Performance is an observation, not a pass condition. End-to-end model remains separate.")
    print("=" * 96)
    print(f"  torch_threads={torch.get_num_threads()} iters={args.iters}")
    print(f"  {'shape OxI':<14}{'M':>4}{'dense':>11}{'generic g5':>13}{'s34 native':>13}"
          f"{'native/dense':>14}{'native/g5':>12}")
    print("  " + "-" * 86)
    gen = torch.Generator().manual_seed(args.seed + 1)
    for shape in args.shapes.split(","):
        out_features, in_features = (int(v) for v in shape.lower().split("x"))
        codes, alpha, weight = _make_sparse34(
            torch, out_features, in_features, args.group, gen)
        # 속도 대조는 scale=1로 통일해 generic g5와 native가 같은 weight를 계산하게 한다.
        alpha.fill_(1.0)
        weight = codes.float()
        from tinylm.model.lut import pack_sparse34_rows
        packed, _ = pack_sparse34_rows(codes)
        generic_codes, i_pad = weight_codes(codes, 5)
        generic_alpha = torch.ones(out_features, 1)
        for rows in args.rows:
            x = torch.randn(rows, in_features, generator=gen)
            with torch.no_grad():
                yd = torch.nn.functional.linear(x, weight)
                yg = lut_linear(x, generic_codes, 5, i_pad, alpha=generic_alpha,
                                out_chunk=args.out_chunk)
                yn = sparse34_lut_linear(x, packed, alpha, args.group, backend="native")
                rg, rn = _rel(yg, yd), _rel(yn, yd)
                if rg >= 3e-5 or rn >= 3e-5:
                    raise RuntimeError(
                        f"benchmark shape correctness failed {out_features}x{in_features} M={rows}: "
                        f"generic={rg:.3e}, native={rn:.3e}")
                td = _median_ms(lambda: torch.nn.functional.linear(x, weight), args.iters)
                tg = _median_ms(lambda: lut_linear(
                    x, generic_codes, 5, i_pad, alpha=generic_alpha,
                    out_chunk=args.out_chunk), args.iters)
                tn = _median_ms(lambda: sparse34_lut_linear(
                    x, packed, alpha, args.group, backend="native"), args.iters)
            print(f"  {out_features}x{in_features:<8}{rows:>4}{td:>11.3f}{tg:>13.3f}{tn:>13.3f}"
                  f"{tn/max(td,1e-12):>14.2f}{tn/max(tg,1e-12):>12.2f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="PM001 3:4 CPU LUT contract/benchmark")
    ap.add_argument("--dim", type=int, default=256)
    ap.add_argument("--out", type=int, default=128)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--group", type=int, default=128)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--out-chunk", type=int, default=128)
    ap.add_argument("--verbose-build", action="store_true")
    ap.add_argument("--benchmark", action="store_true")
    ap.add_argument("--shapes", default="768x768,2048x768,768x2048")
    ap.add_argument("--rows", type=int, nargs="+", default=(1, 8))
    ap.add_argument("--iters", type=int, default=10)
    ap.add_argument("--threads", type=int, default=0)
    args = ap.parse_args()

    print("=" * 96)
    print("  PM001 Stage1 — 3:4 native CPU LUT contract (training 0, checkpoint 0)")
    print("=" * 96)
    print("  success criteria (registered before results):")
    print("    C1 row roundtrip mismatch=0 and exactly 1.250000 bpw")
    print("    C2 reference vs dense relative error < 3e-5")
    print("    C3 native builds with no fallback; native vs dense/reference < 3e-5")
    print("    C4 TLinear uses packed path after latent/int8/fp32 quant copies are removed")
    print("  NOTE: contract pass proves correctness/wiring only, not speed.")

    import torch
    if args.threads > 0:
        torch.set_num_threads(args.threads)
    if args.dim % args.group or args.group % 4 or args.out <= 0:
        print(f"  invalid dimensions: out={args.out} dim={args.dim} group={args.group}")
        return 2
    failures = _contract(torch, args)
    print("\n[contract verdict]")
    if failures:
        for failure in failures:
            print(f"  FAIL: {failure}")
        return 1
    print("  PASS: packed native CPU LUT correctness and TLinear wiring hold.")
    if args.benchmark:
        _benchmark(torch, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
