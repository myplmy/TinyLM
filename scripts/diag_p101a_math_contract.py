#!/usr/bin/env python3
"""P101A CPU tensor gate for E-rank migration and MTP alignment; no model load."""
from __future__ import annotations

import math
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
    from tinylm.train.p101a_contract import (expand_factorized, migrate_p101a_state,
                                             mtp_targets_from_xy)

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


    # A state migration must preserve every old key, reject unrelated gaps and
    # leave the global RNG and original checkpoint tensors unchanged.
    old_state = {"emb.weight": w.clone(), "emb_up.weight": up.clone(),
                 "other.weight": torch.randn(4, 4)}
    target_state = {"emb.weight": torch.zeros(128, 24),
                    "emb_up.weight": torch.zeros(32, 24),
                    "other.weight": torch.zeros(4, 4),
                    "layers.0.attn_mod.qk_gain_logit":
                        torch.full((4,), math.log(1.0 / 6.0))}
    rng_before = torch.random.get_rng_state().clone()
    migrated = migrate_p101a_state(old_state, target_state, seed=71)
    migrated_again = migrate_p101a_state(old_state, target_state, seed=71)
    if not torch.equal(rng_before, torch.random.get_rng_state()):
        raise RuntimeError("rank expansion consumed global RNG state")
    if set(migrated) != set(target_state) or any(
            migrated[k].shape != target_state[k].shape for k in target_state):
        raise RuntimeError("migration did not produce strict target state")
    if not torch.equal(migrated["emb.weight"], migrated_again["emb.weight"]):
        raise RuntimeError("migration seed is not deterministic")
    if not torch.equal(old_state["emb.weight"], w):
        raise RuntimeError("source checkpoint state was mutated")
    effective = migrated["emb.weight"] @ migrated["emb_up.weight"].T
    if float((effective - old_map).abs().amax()) > 1e-6:
        raise RuntimeError("state migration changed effective input/head map")
    gain = migrated["layers.0.attn_mod.qk_gain_logit"]
    if not torch.allclose(0.5 + 3.5 * torch.sigmoid(gain), torch.ones_like(gain),
                          rtol=0, atol=1e-6):
        raise RuntimeError("migrated QK gain does not start at tau=1")
    for bad_target in (
            dict(target_state, unrelated=torch.zeros(1)),
            dict(target_state, **{"emb.weight": torch.zeros(128, 8)}),
            dict(target_state, **{"layers.0.attn_mod.qk_gain_logit": torch.zeros(4)}),
    ):
        try:
            migrate_p101a_state(old_state, bad_target)
        except ValueError:
            pass
        else:
            raise RuntimeError("invalid migration target was silently accepted")

    raw = torch.tensor([[11, 12, 2, 13, 14, 15]], dtype=torch.long)
    x, y = raw[:, :-1], raw[:, 1:]
    target2, valid2 = mtp_targets_from_xy(x, y, 2, eos_id=2)
    if target2.tolist() != [[2, 13, 14, 15]] or valid2.tolist() != [[True, False, False, True]]:
        raise RuntimeError(f"horizon2 alignment/mask wrong: {target2} {valid2}")
    target4, valid4 = mtp_targets_from_xy(x, y, 4, eos_id=2)
    if target4.tolist() != [[14, 15]] or bool(valid4.any()):
        raise RuntimeError("horizon4 crossed the EOS boundary")
    print(f"[PASS] P101A E expansion/state migration max_abs={max_abs:.8g}; exact keys, local RNG, QK tau=1, MTP EOS/crop")
    print("[LIMIT] assistant message mask, model integration, GPU and quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
