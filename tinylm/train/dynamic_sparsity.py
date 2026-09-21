"""P092 TLinear connectivity controller; default-off and trainer-agnostic."""
from __future__ import annotations

from dataclasses import dataclass
import math

import torch

from ..model.ternary import TLinear


@dataclass(frozen=True)
class RewireSummary:
    births: int
    deaths: int
    active: int
    total: int


def _initial_mask(weight: torch.Tensor, density: float) -> torch.Tensor:
    if not 0.0 < density <= 1.0:
        raise ValueError("density must be in (0,1]")
    active = max(1, min(weight.shape[1], round(weight.shape[1] * density)))
    indices = weight.detach().abs().topk(active, dim=1, largest=True, sorted=False).indices
    mask = torch.zeros_like(weight, dtype=torch.bool)
    mask.scatter_(1, indices, True)
    return mask


class ConnectivityController:
    def __init__(self, modules, *, density=0.5, dynamic=False, swap_fraction=0.1):
        self.modules = [module for module in modules if isinstance(module, TLinear)]
        if not self.modules:
            raise ValueError("at least one TLinear is required")
        if not 0.0 <= swap_fraction <= 1.0:
            raise ValueError("swap_fraction must be in [0,1]")
        self.dynamic = bool(dynamic)
        self.swap_fraction = float(swap_fraction)
        self.scores = {}
        for module in self.modules:
            module.set_connectivity(
                _initial_mask(module.weight, density),
                dense_regrowth_gradient=self.dynamic,
            )

    def capture_scores_and_mask_gradients(self, *, capture_scores=True):
        """Save inactive scores, then keep optimizer updates on active slots only."""
        for module in self.modules:
            grad = module.weight.grad
            if grad is None:
                raise RuntimeError("connectivity score requested before backward")
            if self.dynamic and capture_scores:
                self.scores[id(module)] = grad.detach().abs().clone()
            grad.mul_(module.connectivity_mask.to(grad.dtype))

    @staticmethod
    def _reset_optimizer_state(optimizers, parameter, changed):
        for optimizer in optimizers:
            state = optimizer.state.get(parameter, {})
            for value in state.values():
                if torch.is_tensor(value) and value.shape == parameter.shape:
                    value.masked_fill_(changed, 0)

    @torch.no_grad()
    def rewire(self, optimizers=()):
        summaries = []
        if not self.dynamic or self.swap_fraction <= 0:
            for module in self.modules:
                mask = module.connectivity_mask
                summaries.append(RewireSummary(0, 0, int(mask.sum()), mask.numel()))
            return summaries
        for module in self.modules:
            mask = module.connectivity_mask.clone()
            score = self.scores.get(id(module))
            if score is None:
                raise RuntimeError("rewire requires captured dense gradients")
            before = mask.clone()
            per_row = mask.sum(dim=1)
            if not bool(torch.all(per_row == per_row[0])):
                raise RuntimeError("P092 row-wise density conservation was violated")
            active = int(per_row[0])
            inactive = mask.shape[1] - active
            swaps = min(active, inactive, max(1, math.ceil(active * self.swap_fraction)))
            prune_score = module.weight.detach().abs().masked_fill(~mask, float("inf"))
            grow_score = score.masked_fill(mask, float("-inf"))
            prune = prune_score.topk(swaps, dim=1, largest=False, sorted=False).indices
            grow = grow_score.topk(swaps, dim=1, largest=True, sorted=False).indices
            mask.scatter_(1, prune, False)
            mask.scatter_(1, grow, True)
            # A newly born edge must not resurrect a stale latent value from
            # its inactive lifetime.  Optimizer state is reset below as well.
            module.weight.scatter_(1, grow, 0.0)
            module.set_connectivity(mask, dense_regrowth_gradient=True)
            changed = before ^ mask
            self._reset_optimizer_state(optimizers, module.weight, changed)
            births = int(((~before) & mask).sum())
            deaths = int((before & (~mask)).sum())
            summaries.append(RewireSummary(births, deaths, int(mask.sum()), mask.numel()))
        return summaries
