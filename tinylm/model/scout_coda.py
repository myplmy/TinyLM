"""P095 S0bT opt-in Scout bridge at the first Transformer coda layer.

The backbone is unchanged. This experimental single-sequence adapter uses an
ephemeral pre-hook, so it is not a compiled trainer or deployment integration.
"""
from __future__ import annotations

import torch
from torch import nn

from .scout_memory import CausalScoutMemory, ScoutMemoryBridge, ScoutMemoryState


class ScoutCodaAdapter(nn.Module):
    """Route one causal sequence through the real backbone with explicit LTM state."""

    def __init__(self, backbone: nn.Module, memory: CausalScoutMemory):
        super().__init__()
        cfg = backbone.cfg
        if cfg.n_coda < 1 or cfg.grad_checkpoint:
            raise ValueError("S0bT requires a coda and non-checkpointed model")
        self.backbone = backbone
        self.bridge = ScoutMemoryBridge(cfg.dim, memory)
        self.coda_index = cfg.n_prelude + cfg.n_middle
        self._active = False

    def forward(self, tokens: torch.Tensor, state: ScoutMemoryState,
                write_mask: torch.Tensor) -> tuple[torch.Tensor, ScoutMemoryState]:
        if self._active:
            raise RuntimeError("ScoutCodaAdapter does not allow nested/concurrent forward")
        if tokens.ndim != 2 or tokens.shape[0] != 1 or write_mask.shape != (tokens.shape[1],):
            raise ValueError("S0bT takes one sequence and a [T] explicit write mask")
        if tokens.device != state.keys.device or tokens.device != write_mask.device:
            raise ValueError("tokens, memory and write mask must share a device")
        if self.backbone.cfg.n_coda < 1:
            raise ValueError("coda disappeared")
        captured: list[ScoutMemoryState] = []

        def before_coda(_layer: nn.Module, inputs: tuple):
            if captured:
                raise RuntimeError("coda hook fired more than once in one forward")
            hidden = inputs[0]
            if hidden.ndim != 3 or hidden.shape[:2] != tokens.shape:
                raise ValueError("coda hidden shape differs from input sequence")
            fused, updated = self.bridge(hidden[0], state, write_mask)
            captured.append(updated)
            return (fused.unsqueeze(0), *inputs[1:])

        self._active = True
        handle = self.backbone.layers[self.coda_index].register_forward_pre_hook(before_coda)
        try:
            logits = self.backbone(tokens)
        finally:
            handle.remove()
            self._active = False
        if len(captured) != 1:
            raise RuntimeError("first coda layer was never reached")
        return logits, captured[0]
