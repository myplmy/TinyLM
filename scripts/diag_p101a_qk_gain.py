#!/usr/bin/env python3
"""P101A opt-in QK-gain model contract; user-run CPU/model gate only."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--max-initial-abs", type=float, default=1e-5)
    args = ap.parse_args()
    if args.check_only:
        print("[CHECK_ONLY] P101A QK gain default-off, tau=1 migration, gradient and optimizer group; model NOT_RUN")
        return 0
    import torch
    import torch.nn.functional as F
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.p101a_contract import migrate_p101a_state

    torch.manual_seed(101)
    base = dict(vocab_size=256, dim=128, ffn_dim=256, n_q_heads=4,
                n_kv_heads=2, emb_rank=64, n_prelude=1, n_middle=2,
                n_coda=1, mlp_group=1, cla_group=2, tie_mlp=False,
                max_seq_len=32)
    off = TiedMLPTransformer(TMTConfig(**base, qk_gain_learnable=False))
    on = TiedMLPTransformer(TMTConfig(**base, qk_gain_learnable=True))
    expected = [name for name, _ in on.named_parameters() if name.endswith(".qk_gain_logit")]
    if len(expected) != 4:
        raise RuntimeError(f"unexpected QK gain count: {len(expected)}")
    source = off.state_dict()
    migrated = migrate_p101a_state(source, on.state_dict())
    if sorted(set(migrated) - set(source)) != sorted(expected):
        raise RuntimeError("migration added keys outside the expected QK gains")
    on.load_state_dict(migrated, strict=True)
    gains = [p for name, p in on.named_parameters() if name in expected]
    tau = torch.cat([0.5 + 3.5 * torch.sigmoid(p) for p in gains])
    if not torch.allclose(tau, torch.ones_like(tau), atol=1e-6, rtol=0):
        raise RuntimeError("tau initial value is not one")
    groups = on.param_groups(1e-3)
    tail = groups[-1]
    if len(groups) != 5 or tail["lr"] != 1e-4 or tail["weight_decay"] != 0:
        raise RuntimeError("QK gain optimizer policy differs")
    if {id(p) for p in tail["params"]} != {id(p) for p in gains}:
        raise RuntimeError("QK gain optimizer group is incomplete")
    off.eval()
    on.eval()
    tokens = torch.randint(0, 256, (2, 8), generator=torch.Generator().manual_seed(7))
    with torch.no_grad():
        before = off(tokens)
        after = on(tokens)
    max_abs = float((before - after).abs().amax())
    if max_abs > args.max_initial_abs:
        print(f"[GATE NEGATIVE] tau=1 function drift max_abs={max_abs:.8g}")
        return 8
    on.train()
    labels = torch.randint(0, 256, (2, 8), generator=torch.Generator().manual_seed(8))
    loss = F.cross_entropy(on(tokens).reshape(-1, 256), labels.reshape(-1))
    loss.backward()
    grad_sum = sum(float(p.grad.abs().sum()) for p in gains if p.grad is not None)
    if not grad_sum > 0:
        raise RuntimeError("QK gain parameters received no gradient")
    print(f"[PASS] P101A tau=1 abs={max_abs:.8g} per-layer-head={tau.numel()} gain_grad_l1={grad_sum:.8g}")
    print("[LIMIT] tiny CPU model only; actual M0 checkpoint migration, GPU and quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
