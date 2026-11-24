"""Sample one of each repeated pair of weight-gradient contributions in G4 R2."""

from collections import Counter
from contextlib import contextmanager
from unittest.mock import patch

import torch

from tinylm.model.ternary import TLinear


class DoubleWeightVJP(torch.autograd.Function):
    @staticmethod
    def forward(ctx, weight):
        return weight.view_as(weight)

    @staticmethod
    def backward(ctx, gradient):
        return gradient * 2


class RepeatedWeightSampling:
    """Preserve all forward states and all input gradients, sample only dW paths."""

    def __init__(self, model):
        if (model.cfg.grad_checkpoint or model.cfg.train_repeat != 2 or model.cfg.n_modes != 1
                or model._arena is not None or model.cfg.repeat_kv_reuse or model.cfg.reuse_attn_on_dup):
            raise ValueError("this diagnostic samples only an unstaged G4 R2 backward")
        self.calls = Counter()
        self.counts = Counter()
        self.phase = None

    def inventory(self, model, inputs):
        original = TLinear.forward

        def count(module, x, *args, **kwargs):
            self.counts[module] += 1
            return original(module, x, *args, **kwargs)

        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16), patch.object(TLinear, "forward", count):
            model(inputs, return_hidden=True)
        if not self.counts or any(n != 1 and n % 2 for n in self.counts.values()):
            raise ValueError("the repeated weight routes must partition into equal halves")

    @contextmanager
    def microbatch(self, selected_half):
        if selected_half not in (0, 1) or self.phase is not None or not self.counts:
            raise ValueError("each microbatch needs its own complementary sampling phase")
        self.phase = selected_half
        self.calls.clear()
        original = TLinear.forward

        def gradient_path(module, x, *args, **kwargs):
            count = self.counts[module]
            index = self.calls[module]
            self.calls[module] += 1
            if not count or index >= count:
                raise ValueError("the live visit counts differ from the fixed R2 inventory")
            if count == 1:
                return original(module, x, *args, **kwargs)
            weight = module._wq
            if weight is None or not weight.requires_grad:
                raise ValueError("gradient sampling needs a live STE weight")
            keep = (index >= count//2) == bool(self.phase)
            module._wq = DoubleWeightVJP.apply(weight) if keep else weight.detach()
            try:
                return original(module, x, *args, **kwargs)
            finally:
                module._wq = weight

        try:
            with patch.object(TLinear, "forward", gradient_path):
                yield
            if self.calls != self.counts:
                raise ValueError("the whole backward did not preserve the inventory")
        finally:
            self.phase = None
