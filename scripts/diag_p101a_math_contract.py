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
    import torch.nn.functional as F
    from tinylm.train.p101a_contract import (expand_factorized, migrate_p101a_state,
                                             mtp_targets_from_xy, mtp_loss_components,
                                             mtp_weighted_mean, mtp_aux_coefficients)

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
    mtp_target = dict(target_state, mtp_up2=torch.zeros(32, 24),
                      mtp_up4=torch.zeros(32, 24))
    mtp_state = migrate_p101a_state(old_state, mtp_target, seed=71)
    if set(mtp_state) != set(mtp_target):
        raise RuntimeError("MTP migration did not produce strict key set")
    for key in ("mtp_up2", "mtp_up4"):
        if (not torch.equal(mtp_state[key], mtp_state["emb_up.weight"])
                or mtp_state[key].data_ptr() == mtp_state["emb_up.weight"].data_ptr()):
            raise RuntimeError("MTP auxiliary U did not receive an independent main-U copy")
    for bad_target in (
            dict(target_state, unrelated=torch.zeros(1)),
            dict(target_state, **{"emb.weight": torch.zeros(128, 8)}),
            dict(target_state, **{"layers.0.attn_mod.qk_gain_logit": torch.zeros(4)}),
            dict(target_state, mtp_up2=torch.zeros(32, 24)),
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
    # Full-logit reference vs loss-first MTP core: same hidden, independent
    # horizon heads, shared embedding, EOS mask and one update denominator.
    raw2 = torch.tensor([[11, 12, 2, 13, 14, 15],
                         [21, 22, 23, 24, 25, 26]], dtype=torch.long)
    xx, yy = raw2[:, :-1], raw2[:, 1:]
    hidden = torch.randn(2, 5, 6, requires_grad=True)
    main_up = torch.randn(6, 4, requires_grad=True)
    aux2_up = torch.randn(6, 4, requires_grad=True)
    aux4_up = torch.randn(6, 4, requires_grad=True)
    vocab = torch.randn(32, 4, requires_grad=True)
    params = (hidden, main_up, aux2_up, aux4_up, vocab)
    pieces = mtp_loss_components(hidden, main_up, aux2_up, aux4_up,
                                 vocab, xx, yy, eos_id=2, chunk=3)
    lambda2, lambda4 = mtp_aux_coefficients(50, 101)
    if (lambda2, lambda4) != (0.20, 0.10):
        raise RuntimeError("MTP hold coefficients differ")
    if mtp_aux_coefficients(0, 101) != (0.0, 0.0) or mtp_aux_coefficients(100, 101) != (0.0, 0.0):
        raise RuntimeError("MTP schedule endpoints must be zero")
    loss = mtp_weighted_mean([pieces], lambda2, lambda4)
    ref = F.cross_entropy((hidden @ main_up @ vocab.T).reshape(-1, 32),
                          yy.reshape(-1), reduction="mean")
    for k, projection, coefficient in ((2, aux2_up, lambda2),
                                       (4, aux4_up, lambda4)):
        target, valid = mtp_targets_from_xy(xx, yy, k, eos_id=2)
        masked = target.masked_fill(~valid, -100)
        logits = (hidden[:, :target.shape[1]] @ projection @ vocab.T).reshape(-1, 32)
        ref = ref + coefficient * F.cross_entropy(
            logits, masked.reshape(-1), ignore_index=-100, reduction="sum") / valid.sum()
    grad_ref = torch.autograd.grad(ref, params, retain_graph=True)
    grad_loss = torch.autograd.grad(loss, params)
    if not torch.allclose(loss, ref, atol=1e-5, rtol=1e-5):
        raise RuntimeError("MTP loss-first scalar differs from full-logit reference")
    if not all(torch.allclose(a, b, atol=1e-5, rtol=1e-5)
               for a, b in zip(grad_ref, grad_loss)):
        raise RuntimeError("MTP hidden/main/aux/shared-vocab gradients differ")
    if not all(float(g.abs().sum()) > 0 for g in grad_loss):
        raise RuntimeError("MTP head or shared embedding received zero gradient")
    print(f"[PASS] P101A E expansion/state migration max_abs={max_abs:.8g}; QK tau=1; MTP EOS/loss-first/all gradients")
    print("[LIMIT] assistant message mask, full trainer/model integration, GPU and quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
