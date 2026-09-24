#!/usr/bin/env python3
"""P103A Stage1aW pinned M0 12/4 frozen-boundary CPU gate; user runs model only."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tinylm.train.p101a_assets import PARENT, EXPECTED, verify_m0_assets


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--max-abs", type=float, default=5e-5)
    args = ap.parse_args()
    if args.max_abs <= 0:
        ap.error("--max-abs must be positive")
    run = verify_m0_assets()
    if args.check_only:
        print("[PASS] P103A M0 parent/tokenizer/cache SHA and metadata; model NOT_RUN")
        return 0

    import torch
    import torch.nn.functional as F
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.init_utils import _strip
    from tinylm.train.p103a_contract import WindowBoundaryTable, fixed_window_starts, gather_fixed_window_xy
    from tinylm.train.p103a_model_boundary import (freeze_lower_dependency, frozen_prefix_boundary, tail_logits_from_boundary)

    torch.set_num_threads(1)
    state = torch.load(PARENT, map_location="cpu", weights_only=True)
    if (not isinstance(state, dict) or not {"model", "cfg", "step"}.issubset(state)
            or state["step"] != run["steps"]):
        raise ValueError("M0 checkpoint schema/step differs")
    cfg = TMTConfig(**state["cfg"])
    split = 12
    if (cfg.n_layers != 16 or cfg.cla_group != 2 or cfg.dim != 768
            or cfg.emb_rank != 256 or cfg.tie_mlp):
        raise ValueError("M0 12/4 geometry/CLA differs")
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(_strip(state["model"]), strict=True)
    del state
    freeze_lower_dependency(model, split)
    model.train()
    stream = torch.randint(0, cfg.vocab_size, (17,),
                           generator=torch.Generator().manual_seed(31))
    x, y = gather_fixed_window_xy(stream, fixed_window_starts(stream.numel(), 8), 8)
    full_logits = model(x)
    full_loss = F.cross_entropy(full_logits.float().reshape(-1, cfg.vocab_size),
                                y.reshape(-1))
    full_loss.backward()
    baseline = {name: p.grad.detach().clone() for name, p in model.named_parameters()
                if p.grad is not None}
    model.zero_grad(set_to_none=True)
    model.clear_quant()
    boundary = frozen_prefix_boundary(model, x, split)
    table = WindowBoundaryTable(x, boundary, parent_sha256=EXPECTED[PARENT],
                                split_layer=split, quantized=False)
    exact = table.gather(torch.arange(x.shape[0]), x,
                         parent_sha256=EXPECTED[PARENT], split_layer=split)
    cached_logits = tail_logits_from_boundary(model, exact, split)
    cached_loss = F.cross_entropy(cached_logits.float().reshape(-1, cfg.vocab_size),
                                  y.reshape(-1))
    logits_delta = float((full_logits.detach() - cached_logits.detach()).abs().amax())
    loss_delta = float((full_loss.detach() - cached_loss.detach()).abs())
    cached_loss.backward()
    grad_delta = 0.0
    for name, parameter in model.named_parameters():
        old, new = baseline.get(name), parameter.grad
        if (old is None) != (new is None):
            raise RuntimeError(f"M0 12/4 gradient presence differs: {name}")
        if old is not None:
            grad_delta = max(grad_delta, float((old - new).abs().amax()))
    lr = 1e-4
    before = {name: p.detach().clone() for name, p in model.named_parameters()
              if p.grad is not None}
    torch.optim.SGD((p for p in model.parameters() if p.requires_grad), lr=lr).step()
    update_delta = max(float((p.detach() - (before[name] - lr * baseline[name])).abs().amax())
                       for name, p in model.named_parameters() if name in before)
    approx_table = WindowBoundaryTable(x, boundary, parent_sha256=EXPECTED[PARENT],
                                       split_layer=split, quantized=True)
    approx = approx_table.gather(torch.arange(x.shape[0]), x,
                                 parent_sha256=EXPECTED[PARENT], split_layer=split)
    nrms = float((approx - boundary).square().mean().sqrt()
                 / boundary.square().mean().sqrt().clamp_min(1e-12))
    print(f"[X3 M0] logits={logits_delta:.8g} loss={loss_delta:.8g} grad={grad_delta:.8g} update={update_delta:.8g}; INT8 boundary NRMS={nrms:.8g}")
    if max(logits_delta, loss_delta, grad_delta, update_delta) > args.max_abs:
        print("[GATE FAIL] actual M0 12/4 exact frozen boundary differs")
        return 1
    print("[PASS] P103A pinned M0 12/4 exact fixed-window CPU function gate")
    print("[LIMIT] random 8-token windows only; 2M/20M cache, INT8 quality, GPU wall/RSS NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
