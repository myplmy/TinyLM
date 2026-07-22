"""배포 상태(완전 삼진)에서의 val loss/ppl."""
from __future__ import annotations

import math

import torch
import torch.nn.functional as F


@torch.no_grad()
def evaluate(model, loader, iters, device, bytes_per_token=None):
    was = model.cfg.quant_anneal
    model.set_anneal(1.0)                      # 완전 삼진 = 배포 상태 (compile 안전)
    model.eval(); model.refresh_quant()
    tot = 0.0
    for _ in range(iters):
        x, y = loader()
        with torch.autocast(device, dtype=torch.bfloat16, enabled=(device == "cuda")):
            logits = model(x)
        tot += F.cross_entropy(logits.reshape(-1, logits.size(-1)),
                               y.reshape(-1)).float().item()
    model.clear_quant(); model.train(); model.set_anneal(was)
    loss = tot / iters
    out = {"val_loss": loss, "ppl": math.exp(min(loss, 20))}
    if bytes_per_token:
        out["bpb"] = loss / math.log(2) / bytes_per_token
    return out
