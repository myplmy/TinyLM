"""P101A opt-in mathematical contracts for factorized rank expansion and MTP targets."""
from __future__ import annotations

import torch


def expand_factorized(w: torch.Tensor, up: torch.Tensor, extra_rank: int,
                      *, random_std: float = 0.02) -> tuple[torch.Tensor, torch.Tensor]:
    """Return W[V,E+R], U[D,E+R] with identical real-valued input/head maps."""
    if w.ndim != 2 or up.ndim != 2 or w.shape[1] != up.shape[1]:
        raise ValueError("factorized W and U must share the rank dimension")
    if extra_rank < 1 or random_std <= 0:
        raise ValueError("extra rank and random_std must be positive")
    random_cols = torch.randn(w.shape[0], extra_rank, device=w.device, dtype=w.dtype) * random_std
    zero_cols = torch.zeros(up.shape[0], extra_rank, device=up.device, dtype=up.dtype)
    return torch.cat((w, random_cols), dim=1), torch.cat((up, zero_cols), dim=1)


def mtp_targets_from_xy(x: torch.Tensor, y: torch.Tensor, horizon: int,
                        *, eos_id: int | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """Return horizon-k targets and same-document mask from legacy S+1 crop.

    Position t uses only hidden at t to predict raw[t+k]. The EOS target itself
    is permitted; any EOS strictly between source and target invalidates it.
    This is a pretraining contract, not an assistant-message SFT mask.
    """
    if x.ndim != 2 or y.shape != x.shape or horizon < 1 or horizon > x.shape[1]:
        raise ValueError("x/y must be aligned [B,S] with 1 <= horizon <= S")
    if not torch.equal(x[:, 1:], y[:, :-1]):
        raise ValueError("x/y are not an S+1 next-token crop")
    raw = torch.cat((x[:, :1], y), dim=1)
    width = raw.shape[1] - horizon
    target = raw[:, horizon:]
    valid = torch.ones_like(target, dtype=torch.bool)
    if eos_id is not None:
        eos = (raw == eos_id).to(torch.long)
        before = eos.cumsum(dim=1) - eos
        valid = before[:, :width] == before[:, horizon:]
    return target, valid
