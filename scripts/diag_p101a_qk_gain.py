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
    from tinylm.train.p101a_contract import (migrate_p101a_state, mtp_loss_components,
                                             mtp_weighted_mean)

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
        hidden = on(tokens, return_hidden=True)
        reconstructed = on._head_logits(hidden)
    max_abs = float((before - after).abs().amax())
    if not torch.allclose(after, reconstructed, atol=1e-6, rtol=1e-6):
        raise RuntimeError("normalized hidden path does not reconstruct main logits")
    if max_abs > args.max_initial_abs:
        print(f"[GATE NEGATIVE] tau=1 function drift max_abs={max_abs:.8g}")
        return 8
    try:
        on(tokens, return_hidden=True, use_cache=True)
    except ValueError:
        pass
    else:
        raise RuntimeError("hidden path accepted inference cache")
    on.train()
    labels = torch.randint(0, 256, (2, 8), generator=torch.Generator().manual_seed(8))
    loss = F.cross_entropy(on(tokens).reshape(-1, 256), labels.reshape(-1))
    loss.backward()
    grad_sum = sum(float(p.grad.abs().sum()) for p in gains if p.grad is not None)
    if not grad_sum > 0:
        raise RuntimeError("QK gain parameters received no gradient")
    mtp = TiedMLPTransformer(TMTConfig(**base, qk_gain_learnable=True, mtp_aux=True))
    mtp.load_state_dict(migrate_p101a_state(source, mtp.state_dict()), strict=True)
    if (not torch.equal(mtp.mtp_up2, mtp.emb_up.weight)
            or not torch.equal(mtp.mtp_up4, mtp.emb_up.weight)
            or mtp.mtp_up2.data_ptr() == mtp.mtp_up4.data_ptr()):
        raise RuntimeError("MTP auxiliary heads do not start as independent main-U copies")
    mtp.eval()
    with torch.no_grad():
        hidden_mtp = mtp(tokens, return_hidden=True)
        if mtp.mtp_aux_logits(hidden_mtp, 2).shape != before.shape:
            raise RuntimeError("MTP auxiliary logits have the wrong shape")
        deployed = mtp.mtp_deployment_payload()
        plain = TiedMLPTransformer(TMTConfig(**deployed["cfg"]))
        plain.load_state_dict(deployed["model"], strict=True)
        plain.eval()
        if not torch.allclose(mtp(tokens), plain(tokens), atol=1e-6, rtol=1e-6):
            raise RuntimeError("removing MTP heads changed deployment main logits")
    mtp.train()
    xx, yy = tokens[:, :-1], tokens[:, 1:]
    hidden_mtp = mtp(xx, return_hidden=True)
    parts = mtp_loss_components(hidden_mtp, mtp.emb_up.weight,
                                mtp.mtp_up2, mtp.mtp_up4, mtp.emb.weight,
                                xx, yy, eos_id=2, chunk=4)
    mtp_weighted_mean([parts], 0.20, 0.10).backward()
    for name, parameter in (("aux2", mtp.mtp_up2), ("aux4", mtp.mtp_up4),
                            ("shared-vocab", mtp.emb.weight)):
        if parameter.grad is None or not float(parameter.grad.abs().sum()) > 0:
            raise RuntimeError(f"MTP {name} received no gradient")
    print(f"[PASS] P101A tau=1 abs={max_abs:.8g} gain_grad_l1={grad_sum:.8g}; MTP tiny-model aux/export/gradient")
    print("[LIMIT] actual M0 checkpoint and full trainer/GPU/quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
