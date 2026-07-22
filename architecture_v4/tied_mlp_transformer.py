"""
TiedMLPTransformer (v4)
=======================
측정으로 확정된 설계.

무엇을 바꿨나 (v3 대비)
  1. depth-delta 폐기.  rank_spectrum_v3 측정 결과 excess/비용 효율이 전 항목
     1.0 미만(최고 q_proj r=16의 0.96). '같은 메모리로 레이어를 하나 더 두는 것'
     에 항상 진다. 특히 파라미터의 75%인 MLP는 0.26~0.51로 명백한 손해.
  2. 어텐션을 층별 독립으로.  타이드 레이어를 구별시키는 건 라우터가 아니라
     어텐션이다. 대신 파라미터 풀이 작은 쪽이라 유지 비용이 싸다.
  3. MLP만 g층 단위로 타잉.  파라미터의 75%를 차지하면서 레이어 간 차이가
     full-rank 잡음이라 delta로도 못 잡고, 기능적으로도 묶어서 싼 부분.
  4. prelude / coda 분리.  첫·마지막 층을 공유 풀에 넣으면 그 손해를 중간층의
     어떤 자유도로도 회복 못 한다. 2+2 독립이 단일 최대 이득.
  5. CLA: K/V 텐서를 인접 cla_group 층이 공유.  가중치 타잉과 무관한 별도 축.
     Q/O는 층별 독립이라 층별 차별화는 유지된다.
  6. Factorized embedding: V×E + E×d.  임베딩이 더는 메모리 바닥이 아니게 된다.
     lm_head 연산도 함께 싸진다.

무엇을 유지했나
  - g128 삼진 양자화 (llama.cpp Q2_0_g128 / T-MAC 호환 레이아웃)
  - TWN 임계 + L2 최적 alpha, weight 기반 AMP-안전 STE
  - 삼진화 호이스팅, gradient checkpointing
  - 공유 파라미터 LR 1/sqrt(g), weight decay 미보정
  - 삼진 어닐링 (배포 시점 = 학습 종료 시점)
  - 모드 제어 (단, 기본은 adaLN만. mode-delta는 옵션)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint


# ---------------------------------------------------------------------------

@dataclass
class TMTConfig:
    # --- shape ---
    vocab_size: int = 32768
    dim: int = 768
    ffn_dim: int = 2048
    n_q_heads: int = 12
    n_kv_heads: int = 3               # GQA
    emb_rank: int = 256               # factorized embedding 병목. 0이면 비활성

    # --- depth / tying ---
    n_prelude: int = 2                # 완전 독립
    n_middle: int = 16                # 어텐션 독립 + MLP 타잉
    n_coda: int = 2                   # 완전 독립
    mlp_group: int = 4                # 중간층 MLP를 몇 층씩 묶을지
    cla_group: int = 2                # K/V를 몇 층이 공유할지 (1이면 비활성)

    # --- mode control ---
    n_modes: int = 1                  # 1이면 모드 제어 비활성
    mode_rank: int = 0                # 0이면 adaLN만으로 모드 제어

    # --- ternary ---
    micro_group: int = 128
    twn_thr_ratio: float = 0.7
    ste_clip: float = 2.5
    quant_anneal: float = 1.0
    quantize_embedding: bool = True

    # --- misc ---
    max_seq_len: int = 2048
    rope_theta: float = 10000.0
    norm_eps: float = 1e-5
    grad_checkpoint: bool = False
    tie_mlp: bool = True              # False면 dense 기준선

    def __post_init__(self):
        assert self.dim % self.n_q_heads == 0
        assert self.n_q_heads % self.n_kv_heads == 0
        assert self.dim % self.micro_group == 0 and self.ffn_dim % self.micro_group == 0
        assert self.n_middle % self.mlp_group == 0

    @property
    def head_dim(self): return self.dim // self.n_q_heads
    @property
    def kv_dim(self): return self.n_kv_heads * self.head_dim
    @property
    def n_layers(self): return self.n_prelude + self.n_middle + self.n_coda
    @property
    def n_mlp_groups(self): return self.n_middle // self.mlp_group if self.tie_mlp else self.n_middle


# ---------------------------------------------------------------------------
# Ternary (v3에서 검증된 구현 그대로)
# ---------------------------------------------------------------------------

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
        # 윈도가 weight의 함수 -> grad에 선형 -> GradScaler / 배치크기 불변
        win = 1.0 / (1.0 + (aw / (clip * alpha).clamp_min(1e-8)).pow(4))
        return (g.reshape(O, G, group) * win).reshape(O, I), None, None, None


def ternary(w, cfg): return _TernarySTE.apply(w, cfg.micro_group, cfg.twn_thr_ratio, cfg.ste_clip)


class TLinear(nn.Module):
    """g128 삼진 선형층. depth-delta 없음. 모드 delta는 선택."""

    def __init__(self, cfg: TMTConfig, in_f, out_f, out_scale=1.0, mode_delta=False):
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

    def refresh_quant(self, anneal=1.0):
        wq = ternary(self.weight, self.cfg)
        if anneal < 1.0:
            wq = wq + (1.0 - anneal) * (self.weight - wq).detach()
        self._wq = wq

    def clear_quant(self): self._wq = None

    def forward(self, x, mode_p=None):
        wq = self._wq if self._wq is not None else ternary(self.weight, self.cfg)
        y = F.linear(x, wq)
        if self.use_mode and mode_p is not None:
            h = F.linear(x, self.mode_a) * (mode_p @ self.mode_gain)
            y = y + F.linear(h, self.mode_b)
        return y


# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------

class Attention(nn.Module):
    """Q/O는 항상 층별 독립. K/V는 cla_group의 첫 층만 소유하고 나머지는 재사용."""

    def __init__(self, cfg: TMTConfig, owns_kv: bool):
        super().__init__()
        self.cfg, self.owns_kv = cfg, owns_kv
        o_scale = 1.0 / math.sqrt(2 * cfg.n_layers)
        self.q_proj = TLinear(cfg, cfg.dim, cfg.dim, mode_delta=True)
        self.o_proj = TLinear(cfg, cfg.dim, cfg.dim, out_scale=o_scale, mode_delta=True)
        if owns_kv:
            self.k_proj = TLinear(cfg, cfg.dim, cfg.kv_dim)
            self.v_proj = TLinear(cfg, cfg.dim, cfg.kv_dim)

    def compute_kv(self, x, cos, sin):
        B, T, _ = x.shape
        c = self.cfg
        k = self.k_proj(x).view(B, T, c.n_kv_heads, c.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, c.n_kv_heads, c.head_dim).transpose(1, 2)
        return apply_rope(k, cos, sin), v

    def forward(self, x, kv, cos, sin, mode_p):
        B, T, _ = x.shape
        c = self.cfg
        q = self.q_proj(x, mode_p).view(B, T, c.n_q_heads, c.head_dim).transpose(1, 2)
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

    def __init__(self, cfg: TMTConfig):
        super().__init__()
        o_scale = 1.0 / math.sqrt(2 * cfg.n_layers)
        self.gate_proj = TLinear(cfg, cfg.dim, cfg.ffn_dim, mode_delta=True)
        self.up_proj = TLinear(cfg, cfg.dim, cfg.ffn_dim, mode_delta=True)
        self.down_proj = TLinear(cfg, cfg.ffn_dim, cfg.dim, out_scale=o_scale, mode_delta=True)

    def forward(self, x, mode_p):
        return self.down_proj(F.silu(self.gate_proj(x, mode_p)) * self.up_proj(x, mode_p), mode_p)


class Layer(nn.Module):
    """어텐션·정규화·게이트는 층 소유. MLP는 참조(공유 가능)."""

    def __init__(self, cfg: TMTConfig, owns_kv: bool, mlp: MLP):
        super().__init__()
        self.ln1, self.ln2 = RMSNorm(cfg.dim, cfg.norm_eps), RMSNorm(cfg.dim, cfg.norm_eps)
        self.attn = Attention(cfg, owns_kv)
        self.mlp = [mlp]                       # 모듈 등록 회피: 파라미터 중복 계수 방지
        # 층별 adaLN (논문 관례: norm gain은 항상 층별)
        self.a_scale = nn.Parameter(torch.zeros(cfg.dim))
        self.a_shift = nn.Parameter(torch.zeros(cfg.dim))
        self.m_scale = nn.Parameter(torch.zeros(cfg.dim))
        self.m_shift = nn.Parameter(torch.zeros(cfg.dim))
        # 모드 조건화 adaLN: 모드별 스케일 보정. mode_rank=0이어도 이것만으로 모드가 작동한다.
        self.use_mode_ln = cfg.n_modes > 1
        if self.use_mode_ln:
            self.mode_scale = nn.Parameter(torch.zeros(cfg.n_modes, 2, cfg.dim))
        g0 = 1.0 / math.sqrt(cfg.n_layers)     # 0이면 블록이 초기에 그라디언트를 못 받음
        self.gates = nn.Parameter(torch.tensor([g0, g0]))

    def forward(self, x, kv, cos, sin, mode_p):
        ms = None
        if self.use_mode_ln and mode_p is not None:
            # [B,T,M] @ [M, 2*dim] -> [B,T,2,dim]
            ms = (mode_p @ self.mode_scale.flatten(1)).view(*mode_p.shape[:2], 2, -1)
        a = (1 + self.a_scale) if ms is None else (1 + self.a_scale + ms[..., 0, :])
        m = (1 + self.m_scale) if ms is None else (1 + self.m_scale + ms[..., 1, :])
        x = x + self.gates[0] * self.attn(self.ln1(x) * a + self.a_shift, kv, cos, sin, mode_p)
        x = x + self.gates[1] * self.mlp[0](self.ln2(x) * m + self.m_shift, mode_p)
        return x


# ---------------------------------------------------------------------------

class TiedMLPTransformer(nn.Module):
    def __init__(self, cfg: TMTConfig):
        super().__init__()
        self.cfg = cfg
        E = cfg.emb_rank if cfg.emb_rank else cfg.dim

        # factorized embedding: vocab -> E -> dim,  head는 전치 공유
        self.emb = nn.Embedding(cfg.vocab_size, E)
        nn.init.normal_(self.emb.weight, std=0.02)
        self.emb_up = nn.Linear(E, cfg.dim, bias=False) if cfg.emb_rank else None
        if cfg.emb_rank:
            nn.init.normal_(self.emb_up.weight, std=0.02)

        # MLP 인스턴스 생성: prelude/coda는 층마다, middle은 그룹마다
        self.pre_mlps = nn.ModuleList([MLP(cfg) for _ in range(cfg.n_prelude)])
        self.mid_mlps = nn.ModuleList([MLP(cfg) for _ in range(cfg.n_mlp_groups)])
        self.coda_mlps = nn.ModuleList([MLP(cfg) for _ in range(cfg.n_coda)])

        layers, self.owner = [], []            # owner[i] = i층의 K/V를 소유한 층 인덱스
        for i in range(cfg.n_layers):
            owns = (i % cfg.cla_group == 0)
            self.owner.append(i - (i % cfg.cla_group))
            if i < cfg.n_prelude:
                mlp = self.pre_mlps[i]
            elif i < cfg.n_prelude + cfg.n_middle:
                j = i - cfg.n_prelude
                mlp = self.mid_mlps[j // cfg.mlp_group if cfg.tie_mlp else j]
            else:
                mlp = self.coda_mlps[i - cfg.n_prelude - cfg.n_middle]
            layers.append(Layer(cfg, owns, mlp))
        self.layers = nn.ModuleList(layers)

        self.norm_f = RMSNorm(cfg.dim, cfg.norm_eps)
        self.norm_f_scale = nn.Parameter(torch.ones(cfg.dim))

        if cfg.n_modes > 1:
            self.router = nn.Linear(cfg.dim, cfg.n_modes, bias=False)
            nn.init.normal_(self.router.weight, std=0.02)
            self.router_bias = nn.Parameter(torch.zeros(cfg.n_layers, cfg.n_modes))

        cos, sin = build_rope(cfg.head_dim, cfg.max_seq_len, cfg.rope_theta)
        self.register_buffer("rope_cos", cos, persistent=False)
        self.register_buffer("rope_sin", sin, persistent=False)

    # ---------- quantization ----------
    def _tlinears(self):
        for m in self.modules():
            if isinstance(m, TLinear):
                yield m

    def refresh_quant(self):
        for m in self._tlinears():
            m.refresh_quant(self.cfg.quant_anneal)

    def clear_quant(self):
        for m in self._tlinears():
            m.clear_quant()

    # ---------- forward ----------
    def forward(self, tokens, mode_override=None, return_aux=False):
        cfg = self.cfg
        B, T = tokens.shape
        assert T <= cfg.max_seq_len
        x = self.emb(tokens)
        if self.emb_up is not None:
            x = self.emb_up(x)
        cos, sin = self.rope_cos[:T], self.rope_sin[:T]
        self.refresh_quant()

        kv_bank, mode_hist = {}, []
        for i, layer in enumerate(self.layers):
            mode_p = None
            if cfg.n_modes > 1:
                if mode_override is not None:
                    mp = mode_override[i] if mode_override.dim() == 2 else mode_override
                    mode_p = mp.to(x.dtype).view(1, 1, -1).expand(B, T, -1)
                else:
                    mode_p = F.softmax(self.router(x) + self.router_bias[i], dim=-1)
                mode_hist.append(mode_p)

            if i == self.owner[i]:                     # CLA: 그룹 첫 층만 K/V 계산
                kv_bank[i] = layer.attn.compute_kv(x, cos, sin)
            kv = kv_bank[self.owner[i]]

            if cfg.grad_checkpoint and self.training:
                x = checkpoint(lambda inp, L=layer, k=kv, mp=mode_p:
                               L(inp, k, cos, sin, mp), x, use_reentrant=False)
            else:
                x = layer(x, kv, cos, sin, mode_p)

        x = self.norm_f(x) * self.norm_f_scale
        w = self.emb.weight if self.emb_up is None else None
        if self.emb_up is not None:                    # dim -> E -> vocab (전치 공유)
            logits = F.linear(F.linear(x, self.emb_up.weight.t()), self.emb.weight)
        else:
            logits = F.linear(x, w)

        if not return_aux:
            return logits
        aux = {"router_loss": self._balance(mode_hist),
               "mode_usage": (torch.stack([p.mean(dim=(0, 1)) for p in mode_hist]).detach()
                              if mode_hist else None)}
        return logits, aux

    def _balance(self, hist):
        if not hist:
            return torch.zeros((), device=self.emb.weight.device)
        loss = 0.0
        for p in hist:
            f = p.mean(dim=(0, 1))
            loss = loss + self.cfg.n_modes * (f * f).sum()
        return loss / len(hist)

    # ---------- optimizer ----------
    def param_groups(self, lr, weight_decay=0.1):
        """타이드 MLP는 mlp_group회 사용되어 그라디언트가 그만큼 누적된다.
        LR을 1/sqrt(g)로 나눈다. weight decay는 보정하지 않는다(미보정이 더 나았음)."""
        tied = {id(p) for m in self.mid_mlps for p in m.parameters()} if self.cfg.tie_mlp else set()
        gt, dense, nodecay = [], [], []
        for n, p in self.named_parameters():
            if not p.requires_grad:
                continue
            if p.dim() < 2 or any(k in n for k in ("scale", "shift", "gates", "gain", "bias")):
                nodecay.append(p)
            elif id(p) in tied:
                gt.append(p)
            else:
                dense.append(p)
        g = self.cfg.mlp_group if self.cfg.tie_mlp else 1
        return [{"params": gt, "lr": lr / math.sqrt(g), "weight_decay": weight_decay},
                {"params": dense, "lr": lr, "weight_decay": weight_decay},
                {"params": nodecay, "lr": lr, "weight_decay": 0.0}]

    # ---------- accounting ----------
    def report(self, bpw=1.95, l3_mb=32.0):
        cfg = self.cfg
        MB = lambda n, b: n * b / 8 / 1024 ** 2
        tern = sum(m.weight.numel() for m in self._tlinears())
        mode = sum(p.numel() for m in self._tlinears() if m.use_mode
                   for p in (m.mode_a, m.mode_b, m.mode_gain))
        emb = self.emb.weight.numel() + (self.emb_up.weight.numel() if self.emb_up is not None else 0)
        other = sum(p.numel() for p in self.parameters()) - tern - mode - emb
        total = tern + mode + emb + other
        e_bits = bpw if cfg.quantize_embedding else 16
        mem = MB(tern, bpw) + MB(mode, 16) + MB(emb, e_bits) + MB(other, 16)

        per_l = (cfg.dim*cfg.dim*2 + cfg.kv_dim*cfg.dim*2) + 3*cfg.dim*cfg.ffn_dim
        flops = 2 * cfg.n_layers * per_l / 1e9
        n_kv = sum(1 for i in range(cfg.n_layers) if i == self.owner[i])
        kv_kb = n_kv * 2 * cfg.kv_dim * 2 / 1024
        mlp_mb = MB(3*cfg.dim*cfg.ffn_dim, bpw)

        L = []; A = L.append
        A("=" * 72)
        A(f"d={cfg.dim} ffn={cfg.ffn_dim} layers={cfg.n_prelude}+{cfg.n_middle}+{cfg.n_coda}"
          f"  MLP g={cfg.mlp_group if cfg.tie_mlp else 1}  CLA={cfg.cla_group}"
          f"  vocab={cfg.vocab_size} E={cfg.emb_rank or cfg.dim}")
        A("=" * 72)
        A(f"  {'삼진 가중치':<24}{tern/1e6:>9.1f}M{MB(tern,bpw):>10.1f} MB")
        if mode: A(f"  {'모드 delta (fp16)':<24}{mode/1e6:>9.1f}M{MB(mode,16):>10.1f} MB")
        A(f"  {'임베딩(factorized)':<24}{emb/1e6:>9.1f}M{MB(emb,e_bits):>10.1f} MB")
        A(f"  {'기타(norm/gate/router)':<24}{other/1e6:>9.1f}M{MB(other,16):>10.1f} MB")
        A(f"  {'-'*52}")
        A(f"  {'합계':<24}{total/1e6:>9.1f}M{mem:>10.1f} MB")
        A("")
        A(f"  L3({l3_mb:.0f}MB) 상주       : {'가능' if mem < l3_mb*0.7 else '불가'}"
          f"   (여유 {l3_mb-mem:.1f} MB — KV·활성용)")
        A(f"  타이드 MLP 1그룹      : {mlp_mb:.1f} MB  ({cfg.mlp_group}회 연속 재사용)")
        A(f"  토큰당 FLOPs          : {flops:.3f} GFLOP")
        A(f"  KV 캐시               : {kv_kb:.1f} KB/token  ({n_kv}/{cfg.n_layers} 층만 소유)")
        A(f"    1024 ctx {kv_kb*1024/1024:.1f} MB   2048 ctx {kv_kb*2048/1024:.1f} MB")
        A("=" * 72)
        return "\n".join(L)


def dense_baseline(cfg: TMTConfig) -> TMTConfig:
    """동일 shape·동일 토큰 예산으로 학습할 기준선. 타잉과 CLA만 끈다."""
    import dataclasses
    return dataclasses.replace(cfg, tie_mlp=False, cla_group=1)


if __name__ == "__main__":
    cfg = TMTConfig()
    m = TiedMLPTransformer(cfg)
    print("[검증용 100M급 모델 — 타이드]")
    print(m.report())
    b = TiedMLPTransformer(dense_baseline(cfg))
    print("\n[동일 shape dense 기준선]")
    print(b.report())
    pt = sum(p.numel() for p in m.parameters())
    pb = sum(p.numel() for p in b.parameters())
    print(f"\n파라미터 감축: {pb/1e6:.1f}M -> {pt/1e6:.1f}M  ({pb/pt:.2f}배)")
