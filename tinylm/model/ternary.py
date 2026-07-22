"""g128 삼진 양자화 (v3에서 검증된 구현). AMP-안전 STE."""
from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class _TernarySTE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, w, group, thr_ratio, ste_clip):
        O, I = w.shape
        G = I // group
        wg = w.reshape(O, G, group)
        aw = wg.abs()
        mask = (aw >= thr_ratio * aw.mean(dim=2, keepdim=True)).to(w.dtype)
        cnt = mask.sum(dim=2, keepdim=True).clamp_min(1.0)
        alpha = (aw * mask).sum(dim=2, keepdim=True) / cnt
        ctx.save_for_backward(aw, alpha)
        ctx.meta = (O, I, G, group, ste_clip)
        return (torch.sign(wg) * mask * alpha).reshape(O, I)

    @staticmethod
    def backward(ctx, g):
        aw, alpha = ctx.saved_tensors
        O, I, G, group, clip = ctx.meta
        win = 1.0 / (1.0 + (aw / (clip * alpha).clamp_min(1e-8)).pow(4))
        return (g.reshape(O, G, group) * win).reshape(O, I), None, None, None


def ternary(w, cfg):
    return _TernarySTE.apply(w, cfg.micro_group, cfg.twn_thr_ratio, cfg.ste_clip)


class TLinear(nn.Module):
    """g128 삼진 선형층. depth-delta 없음. 모드 delta는 선택."""

    def __init__(self, cfg, in_f, out_f, out_scale=1.0, mode_delta=False):
        super().__init__()
        assert in_f % cfg.micro_group == 0, f"{in_f} % {cfg.micro_group} != 0"
        self.cfg, self.in_f, self.out_f = cfg, in_f, out_f
        self.weight = nn.Parameter(torch.randn(out_f, in_f) * (out_scale / math.sqrt(in_f)))
        self.use_mode = mode_delta and cfg.n_modes > 1 and cfg.mode_rank > 0
        if self.use_mode:
            r = cfg.mode_rank
            self.mode_a = nn.Parameter(torch.randn(r, in_f) / math.sqrt(in_f))
            self.mode_b = nn.Parameter(torch.zeros(out_f, r))
            self.mode_gain = nn.Parameter(torch.ones(cfg.n_modes, r) + 0.02*torch.randn(cfg.n_modes, r))
        self._wq = None

    def refresh_quant(self, anneal):
        # torch.compile 안전: Python 분기 없이 항상 STE 항을 더한다(anneal은 스칼라 텐서).
        # anneal==1.0이면 계수가 0이 되어 순수 삼진.
        wq = ternary(self.weight, self.cfg)
        self._wq = wq + (1.0 - anneal) * (self.weight - wq).detach()

    def clear_quant(self):
        self._wq = None

    def forward(self, x, mode_p=None):
        wq = self._wq if self._wq is not None else ternary(self.weight, self.cfg)
        y = F.linear(x, wq)
        if self.use_mode and mode_p is not None:
            h = F.linear(x, self.mode_a) * (mode_p @ self.mode_gain)
            y = y + F.linear(h, self.mode_b)
        return y
