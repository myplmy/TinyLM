#!/usr/bin/env python3
"""P101A CPU tensor gate for E-rank migration and MTP alignment; no model load."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    if args.check_only:
        print("[CHECK_ONLY] P101A rank/MTP tensor contract; model/GPU NOT_RUN")
        return 0
    import torch
    from tinylm.train.p101a_contract import expand_factorized, mtp_targets_from_xy

    torch.manual_seed(101)
    w = torch.randn(128, 16)
    up = torch.randn(32, 16)
    wider_w, wider_up = expand_factorized(w, up, 8)
    old_map = w @ up.T
    new_map = wider_w @ wider_up.T
    max_abs = float((old_map - new_map).abs().amax())
    if max_abs > 1e-6 or wider_w.shape != (128, 24) or wider_up.shape != (32, 24):
        raise RuntimeError(f"rank expansion changed the real function: {max_abs}")
    up_leaf = wider_up.detach().requires_grad_()
    new_leaf = (wider_w.detach() @ up_leaf.T).square().mean()
    new_leaf.backward()
    if not float(up_leaf.grad[:, -8:].abs().sum()) > 0:
        raise RuntimeError("new U columns received no first-update gradient")

    raw = torch.tensor([[11, 12, 2, 13, 14, 15]], dtype=torch.long)
    x, y = raw[:, :-1], raw[:, 1:]
    target2, valid2 = mtp_targets_from_xy(x, y, 2, eos_id=2)
    if target2.tolist() != [[2, 13, 14, 15]] or valid2.tolist() != [[True, False, False, True]]:
        raise RuntimeError(f"horizon2 alignment/mask wrong: {target2} {valid2}")
    target4, valid4 = mtp_targets_from_xy(x, y, 4, eos_id=2)
    if target4.tolist() != [[14, 15]] or bool(valid4.any()):
        raise RuntimeError("horizon4 crossed the EOS boundary")
    print(f"[PASS] P101A E expansion max_abs={max_abs:.8g}; MTP horizon2/4 EOS/crop alignment")
    print("[LIMIT] assistant message mask, model integration, GPU and quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
