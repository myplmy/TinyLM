"""RMSNorm, RoPE, Attention(QK-norm), MLP, Layer."""
from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .ternary import TLinear


class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-5):
        super().__init__(); self.eps = eps
    def forward(self, x):
        return x * torch.rsqrt(x.float().pow(2).mean(-1, keepdim=True) + self.eps).to(x.dtype)


def build_rope(hd, max_len, theta, device=None):
    inv = 1.0 / (theta ** (torch.arange(0, hd, 2, device=device).float() / hd))
    f = torch.outer(torch.arange(max_len, device=device).float(), inv)
    return torch.cos(f), torch.sin(f)


def apply_rope(x, cos, sin):
    x1, x2 = x.float().chunk(2, dim=-1)
    cos, sin = cos[None, None], sin[None, None]
    return torch.cat([x1*cos - x2*sin, x1*sin + x2*cos], dim=-1).to(x.dtype)


class Attention(nn.Module):
    """Q/O는 항상 층별 독립. K/V는 cla_group의 첫 층만 소유하고 나머지는 재사용.
    v5: q·k 내적 전에 파라미터 없는 RMSNorm(QK-norm) 으로 로짓 폭주를 막는다."""

    def __init__(self, cfg, owns_kv: bool):
        super().__init__()
        self.cfg, self.owns_kv = cfg, owns_kv
        o_scale = 1.0 / math.sqrt(2 * cfg.n_layers)
        self.q_proj = TLinear(cfg, cfg.dim, cfg.dim, mode_delta=True)
        self.o_proj = TLinear(cfg, cfg.dim, cfg.dim, out_scale=o_scale, mode_delta=True)
        self.q_norm = RMSNorm(cfg.head_dim, cfg.norm_eps)
        if owns_kv:
            self.k_proj = TLinear(cfg, cfg.dim, cfg.kv_dim)
            self.v_proj = TLinear(cfg, cfg.dim, cfg.kv_dim)
            self.k_norm = RMSNorm(cfg.head_dim, cfg.norm_eps)

    def compute_kv(self, x, cos, sin):
        B, T, _ = x.shape
        c = self.cfg
        k = self.k_proj(x).view(B, T, c.n_kv_heads, c.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, c.n_kv_heads, c.head_dim).transpose(1, 2)
        k = self.k_norm(k)                          # v5: RoPE 전에 정규화
        return apply_rope(k, cos, sin), v

    def forward(self, x, kv, cos, sin, mode_p):
        B, T, _ = x.shape
        c = self.cfg
        q = self.q_proj(x, mode_p).view(B, T, c.n_q_heads, c.head_dim).transpose(1, 2)
        q = self.q_norm(q)                          # v5: RoPE 전에 정규화
        q = apply_rope(q, cos, sin)
        k, v = kv
        n_rep = c.n_q_heads // c.n_kv_heads
        if n_rep > 1:
            k = k.repeat_interleave(n_rep, dim=1)
            v = v.repeat_interleave(n_rep, dim=1)
        o = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return self.o_proj(o.transpose(1, 2).contiguous().view(B, T, c.dim), mode_p)


class MLP(nn.Module):
    """중간층에서는 mlp_group개 층이 이 인스턴스 하나를 공유한다."""

    def __init__(self, cfg):
        super().__init__()
        o_scale = 1.0 / math.sqrt(2 * cfg.n_layers)
        self.gate_proj = TLinear(cfg, cfg.dim, cfg.ffn_dim, mode_delta=True)
        self.up_proj = TLinear(cfg, cfg.dim, cfg.ffn_dim, mode_delta=True)
        self.down_proj = TLinear(cfg, cfg.ffn_dim, cfg.dim, out_scale=o_scale, mode_delta=True)

    def forward(self, x, mode_p):
        return self.down_proj(F.silu(self.gate_proj(x, mode_p)) * self.up_proj(x, mode_p), mode_p)


class Layer(nn.Module):
    """어텐션·정규화·게이트는 층 소유. MLP는 참조(공유 가능)."""

    def __init__(self, cfg, owns_kv: bool, mlp: MLP):
        super().__init__()
        self.ln1, self.ln2 = RMSNorm(cfg.dim, cfg.norm_eps), RMSNorm(cfg.dim, cfg.norm_eps)
        self.attn = Attention(cfg, owns_kv)
        self.mlp = [mlp]                       # 모듈 등록 회피: 파라미터 중복 계수 방지
        self.a_scale = nn.Parameter(torch.zeros(cfg.dim))
        self.a_shift = nn.Parameter(torch.zeros(cfg.dim))
        self.m_scale = nn.Parameter(torch.zeros(cfg.dim))
        self.m_shift = nn.Parameter(torch.zeros(cfg.dim))
        self.use_mode_ln = cfg.n_modes > 1
        if self.use_mode_ln:
            self.mode_scale = nn.Parameter(torch.zeros(cfg.n_modes, 2, cfg.dim))
        g0 = 1.0 / math.sqrt(cfg.n_layers)
        self.gates = nn.Parameter(torch.tensor([g0, g0]))

    def forward(self, x, kv, cos, sin, mode_p):
        ms = None
        if self.use_mode_ln and mode_p is not None:
            ms = (mode_p @ self.mode_scale.flatten(1)).view(*mode_p.shape[:2], 2, -1)
        a = (1 + self.a_scale) if ms is None else (1 + self.a_scale + ms[..., 0, :])
        m = (1 + self.m_scale) if ms is None else (1 + self.m_scale + ms[..., 1, :])
        x = x + self.gates[0] * self.attn(self.ln1(x) * a + self.a_shift, kv, cos, sin, mode_p)
        x = x + self.gates[1] * self.mlp[0](self.ln2(x) * m + self.m_shift, mode_p)
        return x
