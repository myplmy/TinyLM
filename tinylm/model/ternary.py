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


from .ternary_kernel import ternary_kernel_linear  # noqa: E402  (커스텀 커널 진입점, 기본 off)


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

    def _w(self):
        """(옵션) g128 그룹별 mean-centering 후 latent weight 반환."""
        w = self.weight
        if getattr(self.cfg, "center_weights", False):
            O, I = w.shape; g = self.cfg.micro_group
            wg = w.reshape(O, I // g, g)
            w = (wg - wg.mean(dim=2, keepdim=True)).reshape(O, I)
        return w

    def refresh_quant(self, anneal):
        # torch.compile 안전: Python 분기 없이 항상 STE 항을 더한다(anneal은 스칼라 텐서).
        w = self._w()
        wq = ternary(w, self.cfg)
        self._wq = wq + (1.0 - anneal) * (w - wq).detach()

    def clear_quant(self):
        self._wq = None

    def forward(self, x, mode_p=None):
        if getattr(self.cfg, "use_ternary_kernel", False):   # 분리된 커스텀 커널 경로(기본 off)
            y = ternary_kernel_linear(x, self._w(), self.cfg)
        else:
            wq = self._wq if self._wq is not None else ternary(self._w(), self.cfg)
            y = F.linear(x, wq)
        if self.use_mode and mode_p is not None:
            h = F.linear(x, self.mode_a) * (mode_p @ self.mode_gain)
            y = y + F.linear(h, self.mode_b)
        return y


def ternary_g(w, group, cfg):
    """명시적 group 으로 삼진화(LoRA용). group 은 w 의 마지막 차원을 나눠야 한다."""
    return _TernarySTE.apply(w, group, cfg.twn_thr_ratio, cfg.ste_clip)


class LoRA(nn.Module):
    """공유 MLP projection 위에 얹는 '층별' 저랭크 보정(RRT식).
    U 를 0으로 초기화해 시작 시 no-op → 안전. bits=2면 D·U 도 삼진(거의 공짜)."""

    def __init__(self, cfg, in_f, out_f, r):
        super().__init__()
        self.cfg, self.in_f, self.r = cfg, in_f, r
        self.D = nn.Parameter(torch.randn(r, in_f) / math.sqrt(in_f))
        self.U = nn.Parameter(torch.zeros(out_f, r))
        self.bits = cfg.mlp_lora_bits

    def forward(self, x):
        D, U = self.D, self.U
        if self.bits == 2:
            gD = self.cfg.micro_group if self.in_f % self.cfg.micro_group == 0 else self.in_f
            D = ternary_g(D, gD, self.cfg)
            U = ternary_g(U, self.r, self.cfg)      # r개를 한 그룹으로(출력 행별 스케일)
        return F.linear(F.linear(x, D), U)
