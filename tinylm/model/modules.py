"""RMSNorm, RoPE, Attention(QK-norm), MLP, Layer."""
from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .ternary import TLinear, LoRA

# ---- 어텐션 컴포넌트 레지스트리 (config.attn_kind 로 선택) ----
ATTENTION_KINDS = {}

def register_attention(name):
    def deco(cls):
        ATTENTION_KINDS[name] = cls
        return cls
    return deco

def build_attention(cfg, owns_kv):
    kind = getattr(cfg, "attn_kind", "softmax_cla")
    if kind not in ATTENTION_KINDS:
        raise NotImplementedError(
            f"attn_kind={kind!r} 미구현. 등록됨: {list(ATTENTION_KINDS)}. "
            f"새 어텐션은 @register_attention('name') 로 modules.py 에 추가하세요.\n"
            f"주의: transformer.forward 의 KV-bank(compute_kv/owner) 로직은 softmax_cla 전용이라, "
            f"KDA 등 상태가 다른 종류는 그 오케스트레이션도 함께 일반화해야 합니다(P004).")
    return ATTENTION_KINDS[kind](cfg, owns_kv)


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


@register_attention("softmax_cla")
class Attention(nn.Module):
    """softmax + GQA + CLA + QK-norm. Q/O는 층별 독립, K/V는 cla_group 첫 층만 소유·재사용.
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
        # ── F-1 (2026-08-14) — GQA 복제를 SDPA 에 맡긴다 ─────────────────────────
        #   종전: K/V 를 `repeat_interleave` 로 **물리적으로 n_rep(=4) 배 복제**한다.
        #   즉 (B, 3, T, 64) 를 (B, 12, T, 64) 로 만들어 **활성 메모리를 4배** 쓴다.
        #   `enable_gqa=True` 는 커널이 **복제 없이** 같은 KV 헤드를 여러 Q 헤드에 태운다.
        #   ⚠️ **기본 off = 종전 경로 = 비트 동일.** 커널 경로가 바뀌므로 로짓이 완전히
        #      같다고 가정하지 않는다 — `scripts/diag_gqa_equiv.py` 가 잰다.
        #   ⚠️ **학습 경로(q_len == kv_len)에만 적용한다.** KV 캐시 경로는 `attn_mask` 를
        #      쓰는데 그쪽은 Flash 백엔드가 아니고, 캐시 정확성 게이트(`diag_kvcache.py`)가
        #      이미 확정한 경로라 건드릴 이유가 없다.
        use_gqa = bool(getattr(c, "sdpa_gqa", False)) and n_rep > 1
        q_len, kv_len = q.shape[2], k.shape[2]
        if not (use_gqa and q_len == kv_len):
            if n_rep > 1:
                k = k.repeat_interleave(n_rep, dim=1)
                v = v.repeat_interleave(n_rep, dim=1)
            kv_len = k.shape[2]
        # ★KV 캐시가 있으면 q_len < kv_len 이다. 이때 `is_causal=True` 를 그대로 쓰면
        #   SDPA 가 마스크를 **좌상단 정렬**해서 완전히 틀린 위치를 가린다(조용히 틀린다).
        #   질의는 절대위치 [past_len, past_len+q_len) 에 있으므로 tril(past_len) 이 맞다.
        if q_len == kv_len:                                   # 캐시 없음(=prefill 포함)
            if use_gqa:
                o = F.scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=True)
            else:
                o = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        else:
            past_len = kv_len - q_len
            mask = torch.ones(q_len, kv_len, dtype=torch.bool,
                              device=q.device).tril(past_len)
            o = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        # ── ★★P081 선결 (2026-08-31) — **어텐션 확률을 밖으로 내보낸다** ──────────────
        #   🚫SDPA 는 확률을 안 돌려준다. Flash 백엔드에서는 물질화조차 안 된다.
        #   그래서 어텐션 싱크(StreamingLLM)를 **한 번도 못 봤다**.
        #
        #   ★**훅으로 밖에서 재계산하지 않는다** — 그러면 RoPE·QK-norm·GQA 복제·마스크
        #   규약을 **두 곳에서 정의**하게 되고(함정 18), 그렇게 만든 수치가 실제와
        #   달라도 **조용히 틀린다**. 여기서는 위에서 이미 만든 q·k·mask 를 그대로 쓴다.
        #
        #   ⚠️★**출력 경로에 안 들어간다.** `o` 는 위 SDPA 가 만든 그대로이고
        #   아래 블록은 **읽기만** 한다 → 기본 off 는 물론 **on 이어도 로짓이 비트 동일**하다.
        #   ⚠️메모리 (B, H, q_len, kv_len) x 4B — B=1·1024 면 50 MB, 학습 배치면 400 MB.
        #   → **학습에서는 켤 수 없다**(아래 assert).
        if getattr(c, "return_probs", False):
            assert not self.training, \
                "return_probs 는 진단 전용이다 — 학습에서 켜면 활성 메모리가 배치x헤드로 늘어난다"
            with torch.no_grad():
                # ⚠️`use_gqa` 경로에서는 k 가 **복제되지 않았다**(커널이 대신 한다).
                #   확률을 손으로 만들 때는 헤드 수를 맞춰야 하므로 여기서만 복제한다.
                kp = k.repeat_interleave(n_rep, dim=1) if k.shape[1] != q.shape[1] else k
                att = (q.float() @ kp.float().transpose(-2, -1)) / math.sqrt(c.head_dim)
                if q_len == kv_len:
                    m = torch.ones(q_len, kv_len, dtype=torch.bool, device=q.device).tril()
                else:
                    m = mask                         # 위에서 만든 그 마스크 그대로
                att = att.masked_fill(~m, float("-inf"))
                self.last_probs = att.softmax(-1).detach()
        return self.o_proj(o.transpose(1, 2).contiguous().view(B, T, c.dim), mode_p)


class MLP(nn.Module):
    """중간층에서는 mlp_group개 층이 이 인스턴스 하나를 공유한다."""

    def __init__(self, cfg):
        super().__init__()
        o_scale = 1.0 / math.sqrt(2 * cfg.n_layers)
        self.gate_proj = TLinear(cfg, cfg.dim, cfg.ffn_dim, mode_delta=True)
        self.up_proj = TLinear(cfg, cfg.dim, cfg.ffn_dim, mode_delta=True)
        self.down_proj = TLinear(cfg, cfg.ffn_dim, cfg.dim, out_scale=o_scale, mode_delta=True)

    def forward(self, x, mode_p, lora=None, film=None, lrm=None):
        g = self.gate_proj(x, mode_p)
        u = self.up_proj(x, mode_p)
        # ★P086 — `W̄ = s·W` 를 **출력 쪽에서** 건다. TLinear 는 선형이라 동치이고,
        #   공유 W 를 건드리지 않으므로 **층마다 다른 s** 를 줄 수 있다.
        #   🚫gate 와 up 을 **같은 s 로 묶지 않는다** — silu(s·g)·(s·u) 는 비선형이라
        #   하나로 묶으면 두 축이 교락된다.
        if lrm is not None:
            g = g * lrm[0]
            u = u * lrm[1]
        if lora is not None:                        # 층별 LoRA 보정(gate/up/down)
            g = g + lora[0](x)
            u = u + lora[1](x)
        h = F.silu(g) * u
        if film is not None:                        # 층별 FiLM: 공유 MLP 은닉을 층마다 변조(거의 공짜)
            h = h * (1.0 + film[0]) + film[1]
        d = self.down_proj(h, mode_p)
        if lrm is not None:
            d = d * lrm[2]
        if lora is not None:
            d = d + lora[2](h)
        return d


class Layer(nn.Module):
    """어텐션·정규화·게이트는 층 소유. MLP는 참조(공유 가능)."""

    def __init__(self, cfg, owns_kv: bool, mlp: MLP, mlp_lora: bool = False, mlp_film: bool = False,
                 mlp_lrm: bool = False,
                 attn=None):
        super().__init__()
        self.ln1, self.ln2 = RMSNorm(cfg.dim, cfg.norm_eps), RMSNorm(cfg.dim, cfg.norm_eps)
        # ★P057(2026-08-13) — `attn` 을 주면 **공유 어텐션**을 참조한다(MLP 타잉과 같은 형태).
        #   주지 않으면 층이 자기 것을 만든다 = 종전 = 비트 동일.
        #   ⚠️ MLP 는 `self.mlp = [mlp]` 로 **리스트에 넣어 모듈 등록을 회피**해 파라미터
        #      이중계수를 막았다. 어텐션도 같은 문제가 있으므로 **같은 수법**을 쓴다.
        self._shared_attn = attn is not None
        if attn is None:
            self.attn = build_attention(cfg, owns_kv)
        else:
            self._attn_ref = [attn]        # 모듈 등록 회피(파라미터 중복 계수 방지)
        self.mlp = [mlp]                       # 모듈 등록 회피: 파라미터 중복 계수 방지
        self.has_lora = mlp_lora and cfg.mlp_lora_rank > 0
        if self.has_lora:                      # 공유 MLP를 층별로 특화시키는 저랭크 보정
            r = cfg.mlp_lora_rank
            self.lora_gate = LoRA(cfg, cfg.dim, cfg.ffn_dim, r)
            self.lora_up   = LoRA(cfg, cfg.dim, cfg.ffn_dim, r)
            self.lora_down = LoRA(cfg, cfg.ffn_dim, cfg.dim, r)
        # ★★P086 — 층별 스칼라 승수. **타잉된 중간층에만** 붙인다(공유가 문제의 원인이라서).
        #   1.0 으로 시작하므로 켠 직후의 첫 forward 는 **끈 것과 같다.**
        self.has_lrm = mlp_lrm and getattr(cfg, "mlp_lrm", False)
        if self.has_lrm:
            self.lrm = nn.Parameter(torch.ones(3))   # gate · up · down
        self.has_film = mlp_film and getattr(cfg, "mlp_film", False)
        if self.has_film:                      # 층별 FiLM 파라미터(스케일/시프트, ffn_dim)
            self.film_scale = nn.Parameter(torch.zeros(cfg.ffn_dim))
            self.film_shift = nn.Parameter(torch.zeros(cfg.ffn_dim))
        self.a_scale = nn.Parameter(torch.zeros(cfg.dim))
        self.a_shift = nn.Parameter(torch.zeros(cfg.dim))
        self.m_scale = nn.Parameter(torch.zeros(cfg.dim))
        self.m_shift = nn.Parameter(torch.zeros(cfg.dim))
        self.use_mode_ln = cfg.n_modes > 1
        if self.use_mode_ln:
            self.mode_scale = nn.Parameter(torch.zeros(cfg.n_modes, 2, cfg.dim))
        g0 = 1.0 / math.sqrt(cfg.n_layers)
        self.gates = nn.Parameter(torch.tensor([g0, g0]))

    @property
    def attn_mod(self):
        """★이 층이 실제로 쓰는 어텐션 모듈. 공유(P057)면 참조, 아니면 자기 것.

        ⚠️ **`layer.attn` 을 직접 쓰는 코드가 밖에 있다**(`transformer.forward` 의
        `compute_kv`, `init_utils` 의 이식). 공유일 때 `self.attn` 은 **존재하지 않으므로**
        전부 이 프로퍼티를 거쳐야 한다. 그래서 속성이 아니라 프로퍼티로 만들었다 —
        `AttributeError` 로 즉사시키는 편이 조용히 틀리는 것보다 낫다.
        """
        return self._attn_ref[0] if self._shared_attn else self.attn

    def forward(self, x, kv, cos, sin, mode_p, attn_out=None, want_attn=False):
        """★P049 §17.3(`--reuse-attn-on-dup`) — `attn_out`·`want_attn` 두 인자가 추가됐다.

        ⚠️**기본값이면 종전과 비트 동일**이다(`attn_out=None`·`want_attn=False`).
        `transformer.forward` 가 **재귀 통과에서만** 이 두 인자를 쓴다.

        - `attn_out` 이 주어지면 **어텐션을 계산하지 않고 그 값을 쓴다**(재사용).
          근거는 결과 041 §17: **복제층 어텐션 출력이 cos 0.9882** 였다.
        - `want_attn` 이면 **이번에 계산한 어텐션 출력을 함께 돌려준다**(다음 통과가 쓸 것).

        🚫★**돌려주는 것은 `attn_mod(...)` 의 출력**이지 `gates[0] *` 를 곱한 값이 아니다 —
        게이트는 층 소유라 통과마다 같지만, **곱하기 전 값을 캐시해야 게이트 학습이 산다.**
        """
        ms = None
        if self.use_mode_ln and mode_p is not None:
            ms = (mode_p @ self.mode_scale.flatten(1)).view(*mode_p.shape[:2], 2, -1)
        a = (1 + self.a_scale) if ms is None else (1 + self.a_scale + ms[..., 0, :])
        m = (1 + self.m_scale) if ms is None else (1 + self.m_scale + ms[..., 1, :])
        if attn_out is None:
            attn_out = self.attn_mod(self.ln1(x) * a + self.a_shift, kv, cos, sin, mode_p)
        x = x + self.gates[0] * attn_out
        lora = (self.lora_gate, self.lora_up, self.lora_down) if self.has_lora else None
        film = (self.film_scale, self.film_shift) if self.has_film else None
        lrm = self.lrm if self.has_lrm else None
        x = x + self.gates[1] * self.mlp[0](self.ln2(x) * m + self.m_shift, mode_p, lora, film, lrm)
        return (x, attn_out) if want_attn else x
