#!/usr/bin/env python3
"""P014D native LUT source contract and optional compiled correctness test."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile", action="store_true",
                        help="build the local C++ extension and run tensor correctness")
    parser.add_argument("--verbose-build", action="store_true")
    args = parser.parse_args()

    import torch
    from tinylm.config import TMTConfig
    from tinylm.model.lut import TRITS_PER_BYTE, lut_linear, weight_codes
    from tinylm.model.lut_cpu import extension_name, lut_linear_native_cpu, source_path
    from tinylm.model.ternary import TLinear

    source = source_path()
    text = source.read_text(encoding="utf-8")
    assert source.is_file() and "lut_linear_cpu" in text and "kPatterns = 243" in text
    assert "pattern_carries" in text and "gil_scoped_release" in text
    assert extension_name().startswith("tinylm_lut_cpu_")
    assert TMTConfig().lut_backend == "reference"
    try:
        TMTConfig(lut_backend="silent-fallback")
    except AssertionError:
        pass
    else:
        raise AssertionError("unknown LUT backend must fail closed")
    if not args.compile:
        print("[PASS] P014D native LUT source/default contract; compile NOT_RUN")
        return 0

    torch.manual_seed(14014)
    for shape in ((1, 13, 9), (2, 3, 16, 7)):
        *leading, input_dim, output_dim = shape
        x = torch.randn(*leading, input_dim, dtype=torch.float32)
        ternary = torch.randint(-1, 2, (output_dim, input_dim), dtype=torch.int8)
        codes, i_pad = weight_codes(ternary, TRITS_PER_BYTE)
        alpha = torch.rand(output_dim, 1, dtype=torch.float32) + 0.25
        reference = lut_linear(x, codes, TRITS_PER_BYTE, i_pad, alpha=alpha)
        actual = lut_linear_native_cpu(
            x, codes, i_pad, alpha, verbose_build=args.verbose_build
        )
        torch.testing.assert_close(actual, reference, rtol=1e-6, atol=1e-6)
    cfg = TMTConfig(micro_group=0)
    layer = TLinear(cfg, 13, 9)
    layer.refresh_quant(torch.tensor(1.0))
    layer.drop_latent()
    layer.to_lut()
    x = torch.randn(2, 13)
    layer.cfg.lut_backend = "reference"
    reference = layer(x)
    layer.cfg.lut_backend = "native_cpu"
    actual = layer(x)
    torch.testing.assert_close(actual, reference, rtol=1e-5, atol=2e-5)
    print("[PASS] P014D native CPU LUT compiled correctness: 2-D/3-D and TLinear dispatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
