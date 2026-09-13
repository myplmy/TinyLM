#!/usr/bin/env python3
"""P091 Stage0a: unique-candidate and foldable latent-expansion diagnostic."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="P091 foldable expansion contract")
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    import torch
    import torch.nn.functional as F
    from tinylm.train.late_refine import (
        LateRefineConfig,
        expanded_latent_weight,
        fold_expansion_,
        unique_parameter_blocks,
    )

    device = args.device
    torch.manual_seed(910)
    weight = torch.randn(24, 16, device=device)
    down = torch.randn(24, 4, device=device) * 0.01
    up = torch.randn(4, 16, device=device) * 0.01
    x = torch.randn(7, 16, device=device)
    scale = 0.25

    late_cfg = LateRefineConfig()
    if late_cfg.enabled:
        raise AssertionError("P091 must be default-off")
    if expanded_latent_weight(weight) is not weight:
        raise AssertionError("default-off path did not preserve weight identity")

    shared = object()
    other = object()
    candidates = unique_parameter_blocks([shared, shared, other, shared])
    if candidates != [shared, other]:
        raise AssertionError("tied physical uses were not deduplicated by identity")

    effective = expanded_latent_weight(weight, down, up, scale=scale)
    before = F.linear(x, effective)
    folded = weight.clone()
    fold_expansion_(folded, down, up, scale=scale)
    after = F.linear(x, folded)
    torch.testing.assert_close(before, after, rtol=0, atol=0)

    print(f"PASS device={device} unique_candidates={len(candidates)} fold_max_abs=0")
    print("CONTRACT: quantization must consume Q(W + scale*(down@up)); Q(W)+delta is forbidden.")
    print("NOTE: controller, optimizer-state isolation, and trainer wiring remain NOT_RUN/not implemented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
