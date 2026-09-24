#!/usr/bin/env python3
"""P103A Stage0cW physical FFN tile tiny-model gate; model path is user-run only."""
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
        print("[CHECK_ONLY] P103A X2 model full-tile and one-tile physical-width gate; model NOT_RUN")
        return 0

    import torch
    import torch.nn.functional as F
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.p103a_contract import ffn_tiles

    torch.set_num_threads(1)
    torch.manual_seed(103)
    cfg = TMTConfig(vocab_size=256, dim=128, ffn_dim=256, n_q_heads=4,
                    n_kv_heads=2, emb_rank=64, n_prelude=1, n_middle=2,
                    n_coda=1, mlp_group=1, cla_group=2, tie_mlp=False,
                    max_seq_len=32, x2_tile_size=64)
    reference = TiedMLPTransformer(cfg)
    all_tiles = TiedMLPTransformer(replace(cfg, x2_active_tiles=(0, 1, 2, 3)))
    all_tiles.load_state_dict(reference.state_dict(), strict=True)
    reference.train()
    all_tiles.train()
    raw = torch.randint(0, cfg.vocab_size, (2, 9),
                        generator=torch.Generator().manual_seed(19))
    x, y = raw[:, :-1], raw[:, 1:]
    base = F.cross_entropy(reference(x).float().reshape(-1, cfg.vocab_size), y.reshape(-1))
    tiled = F.cross_entropy(all_tiles(x).float().reshape(-1, cfg.vocab_size), y.reshape(-1))
    loss_delta = float((base.detach() - tiled.detach()).abs())
    base.backward()
    tiled.backward()
    rp, tp = dict(reference.named_parameters()), dict(all_tiles.named_parameters())
    if set(rp) != set(tp):
        raise RuntimeError("X2 parameter names differ")
    grad_delta = 0.0
    for name in rp:
        a, b = rp[name].grad, tp[name].grad
        if (a is None) != (b is None):
            raise RuntimeError(f"X2 gradient presence differs: {name}")
        if a is not None:
            grad_delta = max(grad_delta, float((a - b).abs().amax()))
    torch.optim.SGD(reference.parameters(), lr=1e-3).step()
    torch.optim.SGD(all_tiles.parameters(), lr=1e-3).step()
    update_delta = max(float((rp[name].detach() - tp[name].detach()).abs().amax()) for name in rp)
    one_tile = TiedMLPTransformer(replace(cfg, x2_active_tiles=(0,)))
    one_tile.load_state_dict(reference.state_dict(), strict=True)
    one_tile.train()
    one_tile(x)
    mlp = one_tile.pre_mlps[0]
    probe = torch.randn(2, 3, cfg.dim, generator=torch.Generator().manual_seed(23))
    measured = mlp(probe, None)
    expected = ffn_tiles(probe, mlp.gate_proj._wq, mlp.up_proj._wq,
                         mlp.down_proj._wq, (0,), tile_size=64)
    subset_delta = float((measured.detach() - expected.detach()).abs().amax())
    widths = [m._x2_last_width for m in (list(one_tile.pre_mlps)
              + list(one_tile.mid_mlps) + list(one_tile.coda_mlps))]
    print(f"[X2] full_loss={loss_delta:.8g} full_grad={grad_delta:.8g} full_update={update_delta:.8g} one_tile={subset_delta:.8g} widths={widths}")
    if (max(loss_delta, grad_delta, update_delta, subset_delta) > args.max_abs
            or widths != [64] * len(widths)):
        print("[GATE FAIL] X2 tile function, gradient, update or physical width differs")
        return 1
    print("[PASS] P103A X2 full-tile model function/gradient/update and one-tile physical width")
    print("[LIMIT] optimizer state remains full-width; GPU wall/memory/quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
