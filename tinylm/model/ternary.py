"""g128 삼진 양자화 (v3에서 검증된 구현). AMP-안전 STE."""
from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class _TernarySTE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, w, group, thr_ratio, ste_clip, sparse34=False):
        O, I = w.shape
        G = I // group
        wg = w.reshape(O, G, group)
        aw = wg.abs()
        if sparse34:
            # (P016) 3:4 희소: group 을 4-블록으로 쪼개 각 블록에서 |w|최소 1개를 0강제.
            #   → 정확히 3/4 유지(C(4,3)·2^3=32=2^5 → 1.25bpw 무낭비 패킹). TWN threshold 미적용
            #   (nonzero 개수를 4당 3으로 고정해야 5비트 코드공간과 정합).
            b = aw.reshape(O, G, group // 4, 4)
            keep = torch.ones_like(b)
            keep.scatter_(3, b.argmin(dim=3, keepdim=True), 0.0)   # 최소 |w| 위치만 0
            mask = keep.reshape(O, G, group)
        else:
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
        return (g.reshape(O, G, group) * win).reshape(O, I), None, None, None, None


def ternary(w, cfg):
    return _TernarySTE.apply(w, cfg.micro_group, cfg.twn_thr_ratio, cfg.ste_clip,
                             getattr(cfg, "sparse34", False))


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
        self._anneal_t = None            # refresh_quant가 채우는 어닐 스칼라 텐서(커널 경로 재컴파일 방지용)
        self._latent_shape = None        # drop_latent() 후에도 파라미터 수를 알기 위한 기록

    # ---------- P034 단계2: 추론 시 latent 해제 ----------
    def latent_dropped(self):
        return self._latent_shape is not None

    def weight_numel(self):
        """★`weight.numel()` 대신 이걸 쓴다. latent 를 해제해도 **파라미터 수 회계가 유지**된다.

        해제 후 `weight` 는 빈 텐서가 되므로 `mem_breakdown()` 이 삼진 파라미터를 0 으로 세고
        저장 MB 가 갑자기 0 이 된다 — 그러면 P034 단계2 의 효과를 잴 수가 없다.
        """
        if self._latent_shape is not None:
            n = 1
            for d in self._latent_shape:
                n *= d
            return n
        return self.weight.numel()

    def drop_latent(self):
        """freeze 후 fp32 latent `weight` 의 저장공간을 해제한다(추론 전용, 되돌릴 수 없다).

        ★근거(결과 016): 상주 = 유니크삼진 × 4B × **2벌**(latent + dequant 사본) + 나머지.
          추론에는 backward 가 없으므로 latent 는 **죽은 무게**다. 이 한 줄이 상주의 절반을
          없앤다 — 커스텀 커널 없이 오늘 가능한 **가장 큰 단일 레버**다(P034 §단계2).

        ★`_wq` 를 detach 하는 이유: `refresh_quant()` 는 autograd Function 을 타므로 `_wq` 가
          grad_fn 으로 `weight` 를 **붙잡고 있다**. detach 하지 않으면 저장공간을 비워도
          그래프가 참조를 유지해 실제 해제가 일어나지 않는다.
        """
        if self._wq is None:
            raise RuntimeError("drop_latent() 전에 freeze_quant() 가 필요하다 "
                               "(_wq 가 없으면 forward 가 latent 를 다시 읽는다).")
        if self._latent_shape is None:
            self._latent_shape = tuple(self.weight.shape)
        self._wq = self._wq.detach()
        # 파라미터 객체는 유지하고 저장공간만 비운다(state_dict 키 구조를 깨지 않기 위해).
        self.weight.data = self.weight.data.new_empty(0)
        self.weight.requires_grad_(False)

    def _w(self):
        """(옵션) g128 그룹별 mean-centering 후 latent weight 반환."""
        w = self.weight
        if getattr(self.cfg, "center_weights", False):
            O, I = w.shape; g = self.cfg.micro_group
            wg = w.reshape(O, I // g, g)
            w = (wg - wg.mean(dim=2, keepdim=True)).reshape(O, I)
        return w

    def refresh_quant(self, anneal, arena=None):
        # torch.compile 안전: Python 분기 없이 항상 STE 항을 더한다(anneal은 스칼라 텐서).
        self._anneal_t = anneal          # 커널 경로가 float(cfg.quant_anneal) 대신 이 텐서를 쓰게 함
        w = self._w()
        wq = ternary(w, self.cfg)
        self._wq = wq + (1.0 - anneal) * (w - wq).detach()
        # ★P036 Arenas — `Y = X·Tα + λ_t·X·W` (논문 식 7). **detach 하지 않는다**:
        #   존재 이유가 정확히 `∂L/∂X` 에 latent W 를 넣는 것이다(식 8). 위의 어닐 항은
        #   `.detach()` 라 그 경로가 없다 — 두 항은 **다른 일을 한다**(결과 016 §8.6).
        #   arena 가 None 이면 기존 경로 그대로 = 비트 동일.
        if arena is not None:
            self._wq = self._wq + arena * w

    def clear_quant(self):
        self._wq = None

    def forward(self, x, mode_p=None):
        if getattr(self.cfg, "use_ternary_kernel", False):   # 분리된 커스텀 커널 경로(기본 off)
            if self._latent_shape is not None:
                raise RuntimeError("latent 해제 상태에서는 커스텀 커널 경로를 쓸 수 없다 "
                                   "(커널이 latent weight 를 직접 읽는다).")
            y = ternary_kernel_linear(x, self._w(), self.cfg, self._anneal_t)
        else:
            wq = self._wq if self._wq is not None else ternary(self._w(), self.cfg)
            y = F.linear(x, wq)
        if self.use_mode and mode_p is not None:
            h = F.linear(x, self.mode_a) * (mode_p @ self.mode_gain)
            y = y + F.linear(h, self.mode_b)
        return y


def ternary_g(w, group, cfg):
    """명시적 group 으로 삼진화(LoRA용). group 은 w 의 마지막 차원을 나눠야 한다.
    LoRA 보정은 3:4 대상 아님 → sparse34=False 고정(backward 인자 수 정합 위해 명시)."""
    return _TernarySTE.apply(w, group, cfg.twn_thr_ratio, cfg.ste_clip, False)


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
