#!/usr/bin/env python3
"""P092 Stage0b: masked forward/backward and topology-accounting smoke."""
from __future__ import annotations

import argparse
import math


def main() -> int:
    ap = argparse.ArgumentParser(description="P092 dynamic-sparsity primitive diagnostic")
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    import torch
    from tinylm.model.sparse_connectivity import connectivity_weight
    from tinylm.train.sparsity_contract import sparsity_snapshot, topology_transition

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(920)
    weight = torch.randn(16, 16, device=device, requires_grad=True)
    x = torch.randn(8, 16, device=device)
    before = torch.zeros_like(weight, dtype=torch.bool)
    before[:, ::2] = True
    after = before.clone()
    after[:, 0] = False
    after[:, 1] = True

    masked = connectivity_weight(weight, before, dense_regrowth_gradient=True)
    loss = (x @ masked.t()).square().mean()
    loss.backward()
    if not math.isfinite(float(loss)) or not torch.isfinite(weight.grad).all():
        raise AssertionError("non-finite forward/backward")
    inactive_grad = weight.grad[~before].abs().sum().item()
    if inactive_grad <= 0:
        raise AssertionError("inactive connections have no gradient score for regrowth")

    codes = torch.sign(masked.detach()).reshape(-1).tolist()
    snap = sparsity_snapshot(before.reshape(-1).tolist(), codes)
    event = topology_transition(before.reshape(-1).tolist(), after.reshape(-1).tolist())
    if snap.active != weight.numel() // 2:
        raise AssertionError(f"active-count mismatch: {snap.active}")
    if not event.conserves_active_count:
        raise AssertionError(f"birth/death conservation failed: {event}")

    print(f"PASS device={device} loss={float(loss):.6f} inactive_grad_sum={inactive_grad:.6f}")
    print(
        f"mask={snap.mask_sparsity:.3f} ternary_zero={snap.ternary_zero_rate:.3f} "
        f"effective={snap.effective_sparsity:.3f} births={event.births} deaths={event.deaths}"
    )
    print("NOTE: dense tensor plus mask is not a sparse kernel; claimed FLOP speedup remains zero.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
