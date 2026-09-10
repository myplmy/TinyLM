# -*- coding: utf-8 -*-
"""★Muon 옵티마이저 — [`P005`](../../test_plan/P005_muP전이-Muon옵티마이저.md) 구현.

## 무엇인가

**행렬 파라미터의 업데이트를 직교화(orthogonalize)** 한 뒤 적용한다. 모멘텀 버퍼 `B` 를
Newton-Schulz 반복으로 `≈ U Vᵀ`(특이값을 전부 1 로) 만들어 **스펙트럴 노름을 균일화**한다.

- 근거: Muon(Jordan, 2024) · Essential AI **arXiv:2505.02222** — *대배치에서 데이터 효율 유지*.
- ⚠️★**이점이 대배치에 집중**된다(P005 배경). 우리 유효배치는 **131K** 로 작아
  **이득이 제한적일 수 있다** — 그것을 재는 것이 이 계획이다.

## 🚫이 구현이 하지 않는 것

- **벡터 파라미터를 건드리지 않는다.** 임베딩·norm·bias·스칼라는 **AdamW 가 맡는다**
  (P005 §B 의 `M1` 조건 그대로). 라우팅은 `trainer.py` 가 한다.
- **muP 는 별개다.** 이 파일은 P005 의 **B 축만** 구현한다. A 축(muP 전이)은 미구현.
- ⚠️★**삼진 STE 와의 상호작용은 미검증**이다(P005 선결·리스크).
  우리는 full-precision `self.weight` 를 STE 로 최적화하는데, Muon 이 직교화하는 것은
  **그 gradient** 다. **fp16 팔(M2)과 함께 돌려야 분리된다.**

## 구현 메모

Newton-Schulz 5차 반복(계수는 Jordan 의 공개 구현과 같은 관용값):

    X ← aX + b(XXᵀ)X + c(XXᵀ)²X,   a=3.4445, b=-4.7750, c=2.0315

`bfloat16` 으로 돌린다(원 구현과 같다 — 정확한 직교화가 목적이 아니라 **스펙트럼을 고르게**
만드는 것이 목적이라 저정밀로 충분하고 빠르다).
"""
from __future__ import annotations

import torch


@torch.no_grad()
def _newton_schulz(G: torch.Tensor, steps: int = 5, eps: float = 1e-7) -> torch.Tensor:
    """`G` 의 특이값을 대략 1 로 만든다(직교화 근사). 🚫정확한 SVD 가 아니다."""
    a, b, c = 3.4445, -4.7750, 2.0315
    X = G.bfloat16()
    if X.size(0) > X.size(1):                 # 항상 wide 로 돌린 뒤 되돌린다
        X = X.T
        transposed = True
    else:
        transposed = False
    X = X / (X.norm() + eps)                  # 스펙트럴 노름 ≤ 1 로 정규화
    for _ in range(steps):
        A = X @ X.T
        B = b * A + c * (A @ A)
        X = a * X + B @ X
    if transposed:
        X = X.T
    return X.to(G.dtype)


#: ★★P005b b-1(2026-09-10) — **업데이트 스케일 규약 둘.**
#:
#: 직교화(Newton-Schulz)는 **크기 정보를 지운다.** 그래서 되돌려 줘야 하는데,
#: 참조 구현이 **두 갈래**다(`ai_dev_tool/09` V1 검증):
#:
#:   jordan : max(1, out/in) ** 0.5            <- Jordan 원 구현. **우리가 써 온 것**
#:   rms    : 0.2 * sqrt(max(out, in))         <- "AdamW 업데이트 RMS 에 맞춘다"
#:                                                (arXiv:2505.02222 각주 2 · Kimi K2 Algorithm 1)
#:
#: 🚫**둘은 배수로 서로를 못 메운다** — 형상마다 비가 다르다. dim 768·ffn 2048·kv_dim 192 에서
#: 배율 차가 gate/up 5.54 · **down 9.05** · attention 5.54 로 **형상 간 1.63배 어긋난다.**
#: ★그래서 `--muon-lr-mult 15`(균일 배수)로는 RMS-match 를 흉내낼 수 없다.
SCALE_MODES = ("jordan", "rms")


def update_scale(out_dim: int, in_dim: int, mode: str = "jordan") -> float:
    """★스케일 규약을 **한 곳에서만** 정의한다(함정 18).

    🚫`step()` 안에 인라인으로 두면 진단 도구가 **사본**을 만들게 되고, 사본은 어긋난다.
    """
    if mode == "jordan":
        return max(1.0, out_dim / in_dim) ** 0.5
    if mode == "rms":
        return 0.2 * (max(out_dim, in_dim) ** 0.5)
    raise ValueError(f"모르는 muon_scale: {mode!r} (가능: {'|'.join(SCALE_MODES)})")


class Muon(torch.optim.Optimizer):
    """행렬 파라미터 전용. ⚠️**2차원 파라미터만 넣는다** — 라우팅은 호출자 몫이다."""

    def __init__(self, params, lr=2e-2, momentum=0.95, nesterov=True,
                 ns_steps=5, weight_decay=0.0, scale_mode="jordan"):
        if scale_mode not in SCALE_MODES:
            raise ValueError(f"모르는 muon_scale: {scale_mode!r} (가능: {'|'.join(SCALE_MODES)})")
        super().__init__(list(params), dict(lr=lr, momentum=momentum, nesterov=nesterov,
                                            ns_steps=ns_steps, weight_decay=weight_decay,
                                            scale_mode=scale_mode))
        self.scale_mode = scale_mode
        for g in self.param_groups:
            for p in g["params"]:
                if p.ndim != 2:
                    raise ValueError(
                        f"★Muon 은 2차원 파라미터만 받는다 (받은 것: {tuple(p.shape)}). "
                        f"임베딩·norm·bias 는 AdamW 로 보낸다 — P005 §B 의 M1 조건이다.")

    def scale_table(self):
        """형상별 스케일 표 — **돌리기 전에 인쇄한다**(P005b b-1).

        반환: `[(shape, n_params, jordan, rms, rms/jordan), ...]` 를 형상 유일하게.
        ★두 규약을 **함께** 인쇄하는 것이 요점이다 — 하나만 보면 배수 손잡이(`--muon-lr-mult`)가
        무엇을 메우려 했는지 알 수 없다.
        """
        seen, rows = {}, []
        for g in self.param_groups:
            for p in g["params"]:
                key = tuple(p.shape)
                seen[key] = seen.get(key, 0) + 1
        for key, cnt in sorted(seen.items(), key=lambda kv: -kv[1]):
            out_dim, in_dim = key
            j = update_scale(out_dim, in_dim, "jordan")
            r = update_scale(out_dim, in_dim, "rms")
            rows.append((key, cnt, j, r, r / j))
        return rows

    @torch.no_grad()
    def step(self, closure=None):
        loss = closure() if closure is not None else None
        for g in self.param_groups:
            mom, ns, wd = g["momentum"], g["ns_steps"], g["weight_decay"]
            for p in g["params"]:
                if p.grad is None:
                    continue
                st = self.state[p]
                if "buf" not in st:
                    st["buf"] = torch.zeros_like(p.grad)
                buf = st["buf"]
                buf.mul_(mom).add_(p.grad)
                upd = p.grad.add(buf, alpha=mom) if g["nesterov"] else buf
                upd = _newton_schulz(upd, steps=ns)
                # ★업데이트 크기를 형상에 맞춘다 — 직교화하면 스케일 정보가 사라진다.
                #   규약 정본은 `update_scale` 하나다(P005b b-1, 2026-09-10).
                scale = update_scale(p.size(0), p.size(1), g.get("scale_mode", "jordan"))
                if wd:
                    p.mul_(1 - g["lr"] * wd)
                p.add_(upd, alpha=-g["lr"] * scale)
        return loss


def split_params(model):
    """★모델 파라미터를 **(행렬, 그 외)** 로 가른다.

    반환: `(matrix_params, other_params)` — 행렬은 Muon, 나머지는 AdamW.
    🚫**임베딩은 2차원이지만 행렬이 아니다** — 룩업 테이블이라 직교화가 의미를 갖지 않는다.
    """
    mats, others, seen = [], [], set()
    emb_ids = set()
    for m in model.modules():
        if isinstance(m, torch.nn.Embedding):
            emb_ids.add(id(m.weight))
    for p in model.parameters():
        if not p.requires_grad or id(p) in seen:
            continue
        seen.add(id(p))
        (mats if (p.ndim == 2 and id(p) not in emb_ids) else others).append(p)
    return mats, others
