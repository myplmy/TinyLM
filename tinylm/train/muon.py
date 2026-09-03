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


class Muon(torch.optim.Optimizer):
    """행렬 파라미터 전용. ⚠️**2차원 파라미터만 넣는다** — 라우팅은 호출자 몫이다."""

    def __init__(self, params, lr=2e-2, momentum=0.95, nesterov=True,
                 ns_steps=5, weight_decay=0.0):
        super().__init__(list(params), dict(lr=lr, momentum=momentum, nesterov=nesterov,
                                            ns_steps=ns_steps, weight_decay=weight_decay))
        for g in self.param_groups:
            for p in g["params"]:
                if p.ndim != 2:
                    raise ValueError(
                        f"★Muon 은 2차원 파라미터만 받는다 (받은 것: {tuple(p.shape)}). "
                        f"임베딩·norm·bias 는 AdamW 로 보낸다 — P005 §B 의 M1 조건이다.")

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
                # ★업데이트 크기를 형상에 맞춘다 — 직교화하면 스케일 정보가 사라지므로
                #   `√(fan_out/fan_in)` 로 되돌린다(원 구현과 같은 관용).
                scale = max(1.0, p.size(0) / p.size(1)) ** 0.5
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
