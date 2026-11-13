"""Research-only GSQ coordinates and Lion; no product-default changes.

Coordinate scaling borrows GSQ's confidence/logit separation, not its full PTQ
recipe. Lion follows google/automl/lion/lion_pytorch.py (Apache-2.0), whose
copyright is 2023 Google Research. The compact implementation below supports
only dense, finite gradients and the explicit no-decay diagnostic contract.
"""
from contextlib import contextmanager
import math
from unittest.mock import patch

import torch

from scripts import p106b_gsq_objective as core


def adam_coordinate_bound(updates, lr, betas=(.9, .95)):
    """Conservative real-arithmetic bound; zero initial moments and wd=0.

    Cauchy-Schwarz on bias-corrected first/second moments gives each step
    <= lr/sqrt((1-beta2)*(1-beta1**2/beta2)). Epsilon can only reduce it.
    This is not a formal floating-point proof or a training-quality estimate.
    """
    beta1, beta2 = betas
    if (type(updates) is not int or updates < 0 or not math.isfinite(lr) or lr < 0
            or not 0 <= beta1 < 1 or not beta1**2 < beta2 < 1):
        raise ValueError('bounded fresh-state Adam contract required')
    return updates * lr / math.sqrt((1-beta2)*(1-beta1**2/beta2))


class ScaledGSQBank(core.GSQBank):
    def __init__(self, master, group, cfg, *, logit_strength=4.6, gain=200.):
        if not math.isfinite(gain) or gain <= 0:
            raise ValueError('positive finite confidence gain required')
        super().__init__(master, group, cfg, logit_strength=logit_strength)
        self.gain = float(gain)
        with torch.no_grad():
            self.mask_logit.div_(self.gain)
            self.sign_logit.div_(self.gain)

    def _binary(self, logits):
        return super()._binary(logits*self.gain)

    def bound(self):
        with torch.no_grad():
            for parameter in self.parameters():
                if not bool(torch.isfinite(parameter).all()):
                    raise FloatingPointError('nonfinite coordinate parameter')
            self.mask_logit.clamp_(-12/self.gain, 12/self.gain)
            self.sign_logit.clamp_(-12/self.gain, 12/self.gain)
            self.scale.clamp_min_(1e-8)


def scaled_bridge(model, *, gain=200., strength=4.6):
    # Only construction is patched; instantiated banks own their implementation.
    # No model default, forward, global sampler or source file is replaced.
    def factory(master, group, cfg, *, logit_strength):
        return ScaledGSQBank(master, group, cfg,
                             logit_strength=logit_strength, gain=gain)
    with patch.object(core, 'GSQBank', factory):
        return core.ObjectiveBridge(model, 'gsq', logit_strength=strength)


class CoordinateLion(torch.optim.Optimizer):
    """Lion sign update with one momentum; optional closure, zero decay only."""
    def __init__(self, parameters, lr=1e-4, betas=(.9, .95)):
        if (not math.isfinite(lr) or lr <= 0
                or len(betas) != 2 or any(not 0 <= value < 1 for value in betas)):
            raise ValueError('finite positive learning rate and valid betas required')
        super().__init__(parameters, dict(lr=lr, betas=betas))

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()
        # Validate all groups before changing any parameter or momentum. Batch
        # finite flags per device to avoid one host synchronization per tensor.
        finite_by_device = {}
        for group in self.param_groups:
            for parameter in group['params']:
                gradient = parameter.grad
                if gradient is None:
                    continue
                if gradient.is_sparse:
                    raise ValueError('dense gradients required')
                finite_by_device.setdefault(gradient.device, []).append(torch.isfinite(gradient).all())
        if any(not bool(torch.stack(flags).all()) for flags in finite_by_device.values()):
            raise FloatingPointError('finite gradients required before any Lion update')
        for group in self.param_groups:
            beta1, beta2 = group['betas']
            for parameter in group['params']:
                gradient = parameter.grad
                if gradient is None:
                    continue
                if gradient.is_sparse:
                    raise ValueError('dense gradients required')
                state = self.state[parameter]
                if not state:
                    state['momentum'] = torch.zeros_like(parameter)
                momentum = state['momentum']
                direction = momentum.mul(beta1).add(gradient, alpha=1-beta1)
                parameter.add_(direction.sign(), alpha=-group['lr'])
                momentum.mul_(beta2).add_(gradient, alpha=1-beta2)
        return loss


def optimizer_pair(bridge, arm):
    if arm not in ('adamw', 'lion'):
        raise ValueError('explicit coordinate optimizer required')
    logits = [p for bank in bridge.banks.values()
              for p in (bank.mask_logit, bank.sign_logit)]
    ids = {id(p) for p in logits}
    others = [p for p in bridge.parameters_for_optimizer() if id(p) not in ids]
    if not logits or not others or len(logits) != len(ids):
        raise ValueError('unique logit and scale/norm groups required')
    common = dict(lr=1e-5, betas=(.9, .95), eps=1e-8,
                  weight_decay=0., foreach=False)
    scale_norm = torch.optim.AdamW(others, **common)
    categorical = (CoordinateLion(logits, lr=1e-4, betas=(.9, .95)) if arm == 'lion'
                   else torch.optim.AdamW(logits, **dict(common, lr=1e-4)))
    return categorical, scale_norm
