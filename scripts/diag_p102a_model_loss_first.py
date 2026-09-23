#!/usr/bin/env python3
"""P102A Stage0bW tiny-model S1 loss-first/update gate; user runs model, Codex does not."""
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
        print("[CHECK_ONLY] P102A tiny-model loss/gradient/update gate; model NOT_RUN")
        return 0

    import torch
    import torch.nn.functional as F
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.p102a_contract import factorized_ce_loss_first

    torch.manual_seed(102)
    cfg = TMTConfig(vocab_size=256, dim=128, ffn_dim=256, n_q_heads=4,
                    n_kv_heads=2, emb_rank=64, n_prelude=1, n_middle=2,
                    n_coda=1, mlp_group=1, cla_group=2, tie_mlp=False,
                    max_seq_len=32)
    reference = TiedMLPTransformer(cfg)
    candidate = TiedMLPTransformer(cfg)
    candidate.load_state_dict(reference.state_dict(), strict=True)
    reference.train()
    candidate.train()
    raw = torch.randint(0, cfg.vocab_size, (2, 9),
                        generator=torch.Generator().manual_seed(17))
    x, y = raw[:, :-1], raw[:, 1:]
    logits = reference(x)
    full_loss = F.cross_entropy(logits.float().reshape(-1, cfg.vocab_size),
                                y.reshape(-1))
    hidden = candidate(x, return_hidden=True)
    fast_loss = factorized_ce_loss_first(
        hidden.reshape(-1, cfg.dim).float(), candidate._emb_up_w(),
        candidate._emb_w(), y.reshape(-1), 4) / y.numel()
    loss_delta = float((full_loss - fast_loss).abs())
    if loss_delta > 1e-5:
        print(f"[GATE FAIL] S1 loss delta={loss_delta:.8g}")
        return 1
    full_loss.backward()
    fast_loss.backward()
    ref_params = dict(reference.named_parameters())
    test_params = dict(candidate.named_parameters())
    if set(ref_params) != set(test_params):
        raise RuntimeError("model parameter names differ")
    max_grad = 0.0
    for name in ref_params:
        a, b = ref_params[name].grad, test_params[name].grad
        if (a is None) != (b is None):
            raise RuntimeError(f"gradient presence differs: {name}")
        if a is not None:
            max_grad = max(max_grad, float((a - b).abs().amax()))
    if max_grad > 1e-5:
        print(f"[GATE FAIL] S1 gradient max_abs={max_grad:.8g}")
        return 1
    torch.optim.SGD(reference.parameters(), lr=1e-3).step()
    torch.optim.SGD(candidate.parameters(), lr=1e-3).step()
    max_update = max(float((ref_params[k] - test_params[k]).abs().amax())
                     for k in ref_params)
    if max_update > 1e-5:
        print(f"[GATE FAIL] S1 update max_abs={max_update:.8g}")
        return 1
    print(f"[PASS] P102A tiny model loss={loss_delta:.8g} grad={max_grad:.8g} update={max_update:.8g}")
    print("[LIMIT] CPU FP32 tiny model; full trainer, CUDA BF16, peak and wall NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
