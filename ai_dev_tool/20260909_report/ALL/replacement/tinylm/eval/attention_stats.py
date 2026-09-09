"""A10: causal self-attention의 sink/window mass와 같은 query 집합의 null."""
from __future__ import annotations


def causal_null(seq, sink, window, query_start=0):
    if seq < 1 or sink < 0 or window < 0 or not 0 <= query_start < seq:
        raise ValueError("잘못된 attention 집계 범위")
    sums = [0.0, 0.0, 0.0]
    for q in range(query_start, seq):
        visible = q + 1
        s, w = min(sink, visible), min(window, visible)
        union = min(visible, s + w)
        for i, size in enumerate((s, w, union)):
            sums[i] += size / visible
    n = seq - query_start
    return dict(zip(("sink", "window", "union"), (x / n for x in sums)))


def attention_mass(probs, sink, window, query_start=0):
    import torch
    if probs.ndim != 4 or probs.shape[-2] != probs.shape[-1]:
        raise ValueError("full causal prefill (B,H,T,T) 확률 필요")
    seq = probs.shape[-1]
    null = causal_null(seq, sink, window, query_start)
    q = torch.arange(query_start, seq, device=probs.device)[:, None]
    k = torch.arange(seq, device=probs.device)[None, :]
    valid = k <= q
    smask = (k < sink) & valid
    wmask = (k > q - window) & valid
    p = probs[:, :, query_start:, :]
    if not bool(torch.isfinite(p).all()):
        raise ValueError("nonfinite attention")
    row_sums = p.sum(-1)
    if not bool(torch.allclose(row_sums, torch.ones_like(row_sums), atol=1e-4, rtol=1e-4)):
        raise ValueError("attention 확률 합이 1이 아님")
    if float((p * ~valid).abs().max()) > 1e-6:
        raise ValueError("미래 key에 attention이 존재")
    observed = {name: float((p * mask).sum(-1).mean())
                for name, mask in (("sink", smask), ("window", wmask), ("union", smask | wmask))}
    return {"query_start": query_start, "queries_per_head": seq - query_start,
            "head_query_count": p.shape[0] * p.shape[1] * (seq - query_start),
            "observed": observed, "uniform_causal_null": null,
            "excess_over_null": {k: observed[k] - null[k] for k in observed},
            "discarded_mass": 1.0 - observed["union"]}
