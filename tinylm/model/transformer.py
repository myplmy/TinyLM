"""TiedMLPTransformer (v5) — 조립.

v4 대비 변경(학습 발산 대응, 메모리·파라미터·FLOPs 중립):
  A. QK-norm (modules.Attention).  B. torch.compile 안전 어닐(_anneal 버퍼 + set_anneal).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint

from ..config import TMTConfig, dense_baseline  # noqa: F401  (재export)
from .ternary import TLinear, ternary  # noqa: F401
from .modules import RMSNorm, Attention, MLP, Layer, build_rope, apply_rope  # noqa: F401
from .ternary import LoRA  # noqa: F401


class TiedMLPTransformer(nn.Module):
    def __init__(self, cfg: TMTConfig):
        super().__init__()
        self.cfg = cfg
        E = cfg.emb_rank if cfg.emb_rank else cfg.dim

        self.emb = nn.Embedding(cfg.vocab_size, E)
        nn.init.normal_(self.emb.weight, std=0.02)
        self.emb_up = nn.Linear(E, cfg.dim, bias=False) if cfg.emb_rank else None
        if cfg.emb_rank:
            nn.init.normal_(self.emb_up.weight, std=0.02)

        self.pre_mlps = nn.ModuleList([MLP(cfg) for _ in range(cfg.n_prelude)])
        self.mid_mlps = nn.ModuleList([MLP(cfg) for _ in range(cfg.n_mlp_groups)])
        self.coda_mlps = nn.ModuleList([MLP(cfg) for _ in range(cfg.n_coda)])

        layers, self.owner = [], []
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
            is_mid_tied = (cfg.n_prelude <= i < cfg.n_prelude + cfg.n_middle) and cfg.tie_mlp
            layers.append(Layer(cfg, owns, mlp, mlp_lora=is_mid_tied, mlp_film=is_mid_tied))
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

        # v5: 삼진 어닐 계수를 버퍼로 → torch.compile 재컴파일 방지.
        self.register_buffer("_anneal", torch.tensor(float(cfg.quant_anneal)), persistent=False)
        self._tlinear_cache = list(self._tlinears())   # ②: 매 forward 모듈 트리 순회 제거(plain list)

    # ---------- quantization ----------
    def _tlinears(self):
        for m in self.modules():
            if isinstance(m, TLinear):
                yield m

    def set_anneal(self, v: float):
        self._anneal.fill_(float(v))
        self.cfg.quant_anneal = float(v)

    def refresh_quant(self):
        for m in self._tlinear_cache:
            m.refresh_quant(self._anneal)

    def clear_quant(self):
        for m in self._tlinear_cache:
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

            if i == self.owner[i]:
                kv_bank[i] = layer.attn.compute_kv(x, cos, sin)
            kv = kv_bank[self.owner[i]]

            if cfg.grad_checkpoint and self.training:
                x = checkpoint(lambda inp, L=layer, k=kv, mp=mode_p:
                               L(inp, k, cos, sin, mp), x, use_reentrant=False)
            else:
                x = layer(x, kv, cos, sin, mode_p)

        x = self.norm_f(x) * self.norm_f_scale
        if self.emb_up is not None:
            logits = F.linear(F.linear(x, self.emb_up.weight.t()), self.emb.weight)
        else:
            logits = F.linear(x, self.emb.weight)

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
        import math
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
        lora = sum(p.numel() for m in self.modules() if isinstance(m, LoRA) for p in m.parameters())
        other = sum(p.numel() for p in self.parameters()) - tern - mode - emb - lora
        total = tern + mode + emb + other + lora
        e_bits = bpw if cfg.quantize_embedding else 16
        l_bits = cfg.mlp_lora_bits
        mem = MB(tern, bpw) + MB(mode, 16) + MB(emb, e_bits) + MB(other, 16) + MB(lora, l_bits)

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
        if lora: A(f"  {'LoRA(r='+str(cfg.mlp_lora_rank)+', '+str(l_bits)+'bit)':<24}{lora/1e6:>9.1f}M{MB(lora,l_bits):>10.1f} MB")
        A(f"  {'임베딩(factorized)':<24}{emb/1e6:>9.1f}M{MB(emb,e_bits):>10.1f} MB")
        A(f"  {'기타(norm/gate/router)':<24}{other/1e6:>9.1f}M{MB(other,16):>10.1f} MB")
        A(f"  {'-'*52}")
        A(f"  {'합계':<24}{total/1e6:>9.1f}M{mem:>10.1f} MB")
        A("")
        A(f"  L3({l3_mb:.0f}MB) 상주       : {'가능' if mem < l3_mb*0.7 else '불가'}"
          f"   (여유 {l3_mb-mem:.1f} MB — KV·활성용)")
        if cfg.tie_mlp:
            A(f"  타이드 MLP 1그룹      : {mlp_mb:.1f} MB  ({cfg.mlp_group}회 연속 재사용)")
        else:
            A(f"  MLP 블록(층별 독립)    : {mlp_mb:.1f} MB  (dense: 재사용 없음)")
        A(f"  토큰당 FLOPs          : {flops:.3f} GFLOP")
        A(f"  KV 캐시               : {kv_kb:.1f} KB/token  ({n_kv}/{cfg.n_layers} 층만 소유)")
        A(f"    1024 ctx {kv_kb*1024/1024:.1f} MB   2048 ctx {kv_kb*2048/1024:.1f} MB")
        A("=" * 72)
        return "\n".join(L)
