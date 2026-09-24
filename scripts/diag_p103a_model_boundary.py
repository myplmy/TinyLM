#!/usr/bin/env python3
"""P103A Stage0dW tiny-model frozen lower/tail exact-window gate; user runs model."""
from __future__ import annotations

import argparse
from dataclasses import replace
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--max-abs", type=float, default=5e-5)
    args = ap.parse_args()
    if args.max_abs <= 0:
        ap.error("--max-abs must be positive")
    if args.check_only:
        print("[CHECK_ONLY] P103A X3 frozen lower/tail same-window model gate; model NOT_RUN")
        return 0

    import torch
    import torch.nn.functional as F
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.p103a_contract import WindowBoundaryTable, fixed_window_starts, gather_fixed_window_xy
    from tinylm.train.p103a_model_boundary import frozen_prefix_boundary, tail_logits_from_boundary

    torch.set_num_threads(1)
    torch.manual_seed(103)
    cfg = TMTConfig(vocab_size=256, dim=128, ffn_dim=256, n_q_heads=4,
                    n_kv_heads=2, emb_rank=64, n_prelude=1, n_middle=2,
                    n_coda=1, mlp_group=1, cla_group=2, tie_mlp=False,
                    max_seq_len=32)
    reference = TiedMLPTransformer(cfg)
    candidate = TiedMLPTransformer(replace(cfg))
    candidate.load_state_dict(reference.state_dict(), strict=True)
    split = 2
    for model in (reference, candidate):
        model.emb.requires_grad_(False)
        model.emb_up.requires_grad_(False)
        for layer in model.layers[:split]:
            layer.requires_grad_(False)
        model.train()
    stream = torch.randint(0, cfg.vocab_size, (17,),
                           generator=torch.Generator().manual_seed(31))
    x, y = gather_fixed_window_xy(stream, fixed_window_starts(stream.numel(), 8), 8)
    ref_logits = reference(x)
    ref_loss = F.cross_entropy(ref_logits.float().reshape(-1, cfg.vocab_size),
                               y.reshape(-1))
    boundary = frozen_prefix_boundary(candidate, x, split)
    parent_sha = "A" * 64
    ids = torch.arange(x.shape[0], dtype=torch.long)
    exact_table = WindowBoundaryTable(x, boundary, parent_sha256=parent_sha,
                                       split_layer=split, quantized=False)
    exact = exact_table.gather(ids, x, parent_sha256=parent_sha, split_layer=split)
    if not torch.equal(exact, boundary):
        raise RuntimeError("X3 exact window boundary changed")
    cached_logits = tail_logits_from_boundary(candidate, exact, split)
    cached_loss = F.cross_entropy(cached_logits.float().reshape(-1, cfg.vocab_size),
                                  y.reshape(-1))
    logit_delta = float((ref_logits - cached_logits).abs().amax())
    loss_delta = float((ref_loss - cached_loss).abs())
    ref_loss.backward()
    cached_loss.backward()
    rp, cp = dict(reference.named_parameters()), dict(candidate.named_parameters())
    if set(rp) != set(cp):
        raise RuntimeError("X3 parameter names differ")
    grad_delta = 0.0
    for name in rp:
        a, b = rp[name].grad, cp[name].grad
        if (a is None) != (b is None):
            raise RuntimeError(f"X3 gradient presence differs: {name}")
        if a is not None:
            grad_delta = max(grad_delta, float((a - b).abs().amax()))
    torch.optim.SGD(reference.parameters(), lr=1e-3).step()
    torch.optim.SGD(candidate.parameters(), lr=1e-3).step()
    update_delta = max(float((rp[name] - cp[name]).abs().amax()) for name in rp)
    quant_table = WindowBoundaryTable(x, boundary, parent_sha256=parent_sha,
                                       split_layer=split, quantized=True)
    approx = quant_table.gather(ids, x, parent_sha256=parent_sha, split_layer=split)
    nrms = float((approx - boundary).square().mean().sqrt()
                 / boundary.square().mean().sqrt().clamp_min(1e-12))
    print(f"[X3] exact logit={logit_delta:.8g} loss={loss_delta:.8g} grad={grad_delta:.8g} update={update_delta:.8g}; INT8 boundary NRMS={nrms:.8g}")
    if max(logit_delta, loss_delta, grad_delta, update_delta) > args.max_abs:
        print("[GATE FAIL] X3 frozen-prefix exact window differs from full model")
        return 1
    print("[PASS] P103A X3 tiny-model exact frozen lower/tail window gate")
    print("[LIMIT] INT8 is report-only; actual M0 12/4, 2M/20M RAM, GPU wall and quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
