#!/usr/bin/env python3
"""P102A Stage0cW tiny-model S2 STE update-cache gate; model path is user-run only."""
from __future__ import annotations

import argparse
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
        print("[CHECK_ONLY] P102A S2 tiny-model STE loss/gradient/clip/update; model NOT_RUN")
        return 0

    import torch
    import torch.nn.functional as F
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    torch.set_num_threads(1)
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
    raw = [torch.randint(0, cfg.vocab_size, (2, 9),
                         generator=torch.Generator().manual_seed(seed))
           for seed in (17, 23, 29)]
    data = [(batch[:, :-1], batch[:, 1:]) for batch in raw]
    base_losses = []
    for x, y in data:
        loss = F.cross_entropy(reference(x).float().reshape(-1, cfg.vocab_size),
                               y.reshape(-1)) / len(data)
        base_losses.append(float(loss.detach()))
        loss.backward()

    candidate.begin_quant_update_cache()
    if not candidate._p102a_quant_update:
        raise RuntimeError("S2 cache contains no TLinear STE graphs")
    cached_losses = []
    for x, y in data:
        loss = F.cross_entropy(candidate(x).float().reshape(-1, cfg.vocab_size),
                               y.reshape(-1)) / len(data)
        cached_losses.append(float(loss.detach()))
        loss.backward()
    leaf_grads = sum(leaf.grad is not None for _, _, leaf in candidate._p102a_quant_update)
    if leaf_grads < 1:
        raise RuntimeError("S2 received no detached surrogate gradients")
    candidate.finish_quant_update_cache()
    if candidate._p102a_quant_update is not None:
        raise RuntimeError("S2 cache survived the VJP")

    max_loss = max(abs(a - b) for a, b in zip(base_losses, cached_losses))
    ref_params = dict(reference.named_parameters())
    test_params = dict(candidate.named_parameters())
    if set(ref_params) != set(test_params):
        raise RuntimeError("S2 parameter names differ")
    max_grad = 0.0
    for name in ref_params:
        a, b = ref_params[name].grad, test_params[name].grad
        if (a is None) != (b is None):
            raise RuntimeError(f"S2 gradient presence differs: {name}")
        if a is not None:
            max_grad = max(max_grad, float((a - b).abs().amax()))
    ref_norm = float(torch.nn.utils.clip_grad_norm_(reference.parameters(), 1.0))
    test_norm = float(torch.nn.utils.clip_grad_norm_(candidate.parameters(), 1.0))
    torch.optim.SGD(reference.parameters(), lr=1e-3).step()
    torch.optim.SGD(candidate.parameters(), lr=1e-3).step()
    max_update = max(float((ref_params[name] - test_params[name]).abs().amax())
                     for name in ref_params)
    reference.clear_quant()
    candidate.clear_quant()
    print(f"[S2] loss={max_loss:.8g} grad={max_grad:.8g} clip_norm_delta={abs(ref_norm-test_norm):.8g} update={max_update:.8g} leaf_grads={leaf_grads}")
    if max(max_loss, max_grad, abs(ref_norm - test_norm), max_update) > args.max_abs:
        print("[GATE FAIL] S2 small-model same-update contract differs")
        return 1
    print("[PASS] P102A S2 cached STE VJP equals per-micro reference on CPU tiny model")
    print("[LIMIT] CUDA BF16, peak, whole-step wall and quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
