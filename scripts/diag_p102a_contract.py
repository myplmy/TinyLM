#!/usr/bin/env python3
"""P102A CPU reference fixture for S1/S2/S3; no model or GPU."""
from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    if args.check_only:
        print("[CHECK_ONLY] P102A S1/S2/S3 tensor reference; trainer/model/GPU NOT_RUN")
        return 0
    import torch
    import torch.nn.functional as F
    from tinylm.train.p102a_contract import (
        factorized_ce_chunks, update_local_vjp, sampled_mtp_loss,
    )

    torch.manual_seed(102)
    h = torch.randn(7, 16, requires_grad=True)
    up = torch.randn(16, 8, requires_grad=True)
    emb = torch.randn(32, 8, requires_grad=True)
    targets = torch.tensor([1, 2, -100, 4, 5, -100, 7])
    full = F.cross_entropy(((h @ up) @ emb.T).float(), targets,
                           ignore_index=-100, reduction="sum")
    chunked = factorized_ce_chunks(h, up, emb, targets, 3)
    if not torch.allclose(full, chunked, rtol=1e-6, atol=1e-6):
        raise RuntimeError("S1 reference loss differs")
    grad_full = torch.autograd.grad(full, (h, up, emb), retain_graph=True)
    grad_chunk = torch.autograd.grad(chunked, (h, up, emb))
    if not all(torch.allclose(a, b, rtol=1e-5, atol=1e-5)
               for a, b in zip(grad_full, grad_chunk)):
        raise RuntimeError("S1 hidden/up/emb gradient differs")

    w = torch.randn(4, 5, requires_grad=True)
    surrogate = w.square()
    g1, g2 = torch.randn_like(w), torch.randn_like(w)
    ref1 = torch.autograd.grad(surrogate, w, g1, retain_graph=True)[0]
    ref2 = torch.autograd.grad(surrogate, w, g2, retain_graph=True)[0]
    joint = update_local_vjp(surrogate, w, g1 + g2)
    if not torch.allclose(ref1 + ref2, joint, rtol=1e-6, atol=1e-6):
        raise RuntimeError("S2 VJP sum contract differs")

    counts = [2, 3, 4, 5]
    sums = [torch.tensor(v, dtype=torch.float64) for v in (2, 6, 12, 20)]
    full_mean = sum(sums) / sum(counts)
    estimates = []
    for pair in combinations(range(4), 2):
        selected = [j in pair for j in range(4)]
        estimates.append(sampled_mtp_loss(sums, counts, selected, probability=0.5))
    expected = torch.stack(estimates).mean()
    if not torch.allclose(full_mean, expected, rtol=1e-12, atol=1e-12):
        raise RuntimeError("S3 sampled MTP estimator is biased in four-micro exhaustive fixture")
    print("[PASS] P102A S1 full/chunk loss+all gradients, S2 VJP, S3 HT expectation")
    print("[LIMIT] fused kernel, real STE cached graph, MTP trainer and GPU wall NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
