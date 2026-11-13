"""Native MLP/LoRA function calibration primitives; no files/model loading.

GSQ-style diagnostic: binary Gumbel mask/sign logits and positive group scales.
This is not a vendored official whole-model GSQ pipeline or an RCO solver.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
import torch.nn as nn
import torch.nn.functional as F
from tinylm.model.modules import MLP
from tinylm.model.ternary import LoRA, ternary, ternary_g

PROJECTIONS = ("gate_proj", "up_proj", "down_proj")
VERSION = "P093B_NATIVE_FUNCTION_CAL_V1"


def native_weight(linear):
    if getattr(linear, "use_mode", False) or getattr(linear, "connectivity_mask", None) is not None:
        raise ValueError("mode/connectivity needs a separate calibration contract")
    if linear.weight.dtype != torch.float32:
        raise ValueError("preregistered FP32 master required")
    cached = getattr(linear, "_wq", None)
    return (cached if cached is not None else ternary(linear.weight, linear.cfg)).detach().clone()


def shared_native(mlps, cfg):
    if len(mlps) != 4 or len({id(m) for m in mlps}) != 4:
        raise ValueError("four distinct untied MLP owners required")
    if cfg.n_modes != 1 or getattr(cfg, "x2_active_tiles", ()):
        raise ValueError("mode/X2 paths are outside this gate")
    result = MLP(copy.deepcopy(cfg)).to(mlps[0].gate_proj.weight.device)
    with torch.no_grad():
        for name in PROJECTIONS:
            layer = getattr(result, name)
            layer.weight.copy_(torch.stack([getattr(m, name).weight.detach() for m in mlps]).mean(0))
            layer.weight.requires_grad_(False)
            layer._wq = ternary(layer.weight, layer.cfg).detach()
    return result.eval()


def weighted_factors(error, inputs, rank, *, ridge=1e-3):
    """Minimize an activation-weighted linear initialization, then fit SwiGLU."""
    if (error.ndim != 2 or inputs.ndim != 2 or inputs.shape[1] != error.shape[1]
            or not 1 <= rank <= min(error.shape) or inputs.shape[0] < 2):
        raise ValueError("invalid weighted-SVD geometry")
    with torch.no_grad():
        cov = inputs.t() @ inputs / inputs.shape[0]
        eps = cov.diag().mean().clamp_min(1e-8) * ridge
        cov = cov + eps * torch.eye(cov.shape[0], device=cov.device, dtype=cov.dtype)
        lower = torch.linalg.cholesky(cov)
        weighted = error @ lower
        q = min(rank + 8, min(weighted.shape))
        u, s, v = torch.svd_lowrank(weighted, q=q, niter=3)
        root = s[:rank].clamp_min(0).sqrt()
        up = u[:, :rank] * root
        right = root[:, None] * v[:, :rank].t()
        down = torch.linalg.solve_triangular(lower.t(), right.t(), upper=True).t()
    if not torch.isfinite(up).all() or not torch.isfinite(down).all():
        raise ValueError("nonfinite weighted-SVD initialization")
    return up.contiguous(), down.contiguous()


def residual_adapters(originals, shared, inputs, rank, cfg):
    local = copy.deepcopy(cfg)
    # The historical 16 label means unquantized forward. Parameters remain FP32.
    local.mlp_lora_bits = 16
    adapters = []
    for mlp, x in zip(originals, inputs):
        with torch.no_grad():
            hidden = F.silu(mlp.gate_proj(x, None)) * mlp.up_proj(x, None)
        layer = []
        for name in PROJECTIONS:
            original = getattr(mlp, name)
            reference = native_weight(original)
            base = native_weight(getattr(shared, name))
            activation = hidden if name == "down_proj" else x
            up, down = weighted_factors(reference - base, activation, rank)
            adapter = LoRA(local, reference.shape[1], reference.shape[0], rank).to(x.device)
            with torch.no_grad():
                adapter.U.copy_(up); adapter.D.copy_(down)
            layer.append(adapter)
        adapters.append(tuple(layer))
    return adapters


class GSQProjection(nn.Module):
    def __init__(self, weight, group, cfg):
        super().__init__()
        if weight.ndim != 2 or group < 1 or weight.shape[1] % group:
            raise ValueError("group must divide projection input")
        self.cfg, self.group = cfg, group
        self.in_f, self.out_f = weight.shape[1], weight.shape[0]
        w = weight.detach().float().reshape(self.out_f, -1, group)
        nonzero = w != 0
        alpha = (w.abs() * nonzero).sum(-1, keepdim=True) / nonzero.sum(-1, keepdim=True).clamp_min(1)
        self.mask_logit = nn.Parameter(torch.where(nonzero, 4.6, -4.6).expand_as(w).clone())
        self.sign_logit = nn.Parameter(torch.where(w >= 0, 4.6, -4.6).expand_as(w).clone())
        self.log_scale = nn.Parameter(alpha.clamp_min(1e-8).log())
        self.temperature = 1.0

    def _binary(self, logits):
        if not self.training:
            return (logits >= 0).to(logits.dtype)
        two = torch.stack((-logits / 2, logits / 2), dim=-1)
        return F.gumbel_softmax(two, tau=self.temperature, hard=True, dim=-1)[..., 1]

    def matrix(self):
        mask, sign = self._binary(self.mask_logit), 2 * self._binary(self.sign_logit) - 1
        return (mask * sign * self.log_scale.exp()).reshape(self.out_f, self.in_f)

    def forward(self, x, mode_p=None):
        if mode_p is not None:
            raise ValueError("mode router is outside this gate")
        return F.linear(x, self.matrix())

    def bound(self):
        with torch.no_grad():
            self.mask_logit.clamp_(-12, 12); self.sign_logit.clamp_(-12, 12)
            self.log_scale.clamp_(-24, 8)

    def code_scale(self):
        if self.training:
            raise ValueError("export requires deterministic hard eval")
        code = ((self.mask_logit >= 0).to(torch.int8)
                * (2 * (self.sign_logit >= 0).to(torch.int8) - 1))
        return code.detach(), self.log_scale.exp().detach()


def gsq_shared(shared, cfg):
    result = MLP(copy.deepcopy(cfg)).to(shared.gate_proj.weight.device)
    for name in PROJECTIONS:
        weight = native_weight(getattr(shared, name))
        group = int(cfg.micro_group) or weight.shape[1]
        setattr(result, name, GSQProjection(weight, group, cfg))
    return result.eval()


class GSQAdapter(nn.Module):
    def __init__(self, adapter):
        super().__init__()
        self.cfg, self.r = adapter.cfg, adapter.r
        if self.cfg.micro_group <= 0:
            raise ValueError("native LoRA currently needs a positive D group")
        group_d = self.cfg.micro_group if adapter.in_f % self.cfg.micro_group == 0 else adapter.in_f
        d = ternary_g(adapter.D.detach(), group_d, self.cfg)
        u = ternary_g(adapter.U.detach(), adapter.r, self.cfg)
        self.down = GSQProjection(d, group_d, self.cfg)
        self.up = GSQProjection(u, adapter.r, self.cfg)
        self.register_buffer("_scale", adapter._scale.detach().clone())

    def forward(self, x):
        return self.up(self.down(x)) * self._scale

    def native_export(self):
        if self.training:
            raise ValueError("hard eval required for native round-trip")
        cfg = copy.deepcopy(self.cfg); cfg.mlp_lora_bits = 2
        result = LoRA(cfg, self.down.in_f, self.up.out_f, self.r).to(self.down.log_scale.device)
        with torch.no_grad():
            result.D.copy_(self.down.matrix()); result.U.copy_(self.up.matrix())
            result._scale.copy_(self._scale)
        return result.eval()


def parameters_unique(modules):
    seen, result = set(), []
    for module in modules:
        for parameter in module.parameters():
            if parameter.requires_grad and id(parameter) not in seen:
                seen.add(id(parameter)); result.append(parameter)
    return result


def local_predictions(shared, inputs, adapters=None):
    return [shared(x, None, None if adapters is None else adapters[i], None, None)
            for i, x in enumerate(inputs)]


def normalized_loss(predictions, targets):
    signal = sum(y.square().sum() for y in targets)
    if not torch.isfinite(signal) or signal <= 0:
        raise ValueError("reference signal empty/nonfinite")
    error = sum((p-y).square().sum() for p, y in zip(predictions, targets))
    if not torch.isfinite(error):
        raise ValueError("candidate function error is nonfinite")
    return error / signal


def measure(shared, inputs, targets, adapters=None):
    shared.eval()
    for layer in adapters or []:
        for adapter in layer: adapter.eval()
    with torch.no_grad():
        predictions = local_predictions(shared, inputs, adapters)
        return {"nrms": float(normalized_loss(predictions, targets).sqrt()),
                "layer_nrms": [float(((p-y).square().sum()/y.square().sum().clamp_min(1e-30)).sqrt())
                               for p, y in zip(predictions, targets)]}


def fit(shared, inputs, targets, *, adapters=None, steps=250, strategy="adam", deadline=None):
    modules = [shared] if adapters is None else [a for layer in adapters for a in layer]
    params = parameters_unique(modules)
    if not params or steps < 1:
        raise ValueError("nonempty gradient ownership and positive steps required")
    optimizer = torch.optim.AdamW(params, lr=1e-3, weight_decay=0) if strategy == "adam" else None
    moments = {id(p): torch.zeros_like(p) for p in params} if strategy == "lion" else {}
    if strategy not in ("adam", "lion"):
        raise ValueError("unknown calibration optimizer")
    projections = [m for module in modules for m in module.modules() if isinstance(m, GSQProjection)]
    grad_max, history = 0.0, []
    begin = time.perf_counter()
    for step in range(steps):
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError("calibration wall budget exceeded")
        for module in modules: module.train()
        for projection in projections: projection.temperature = 1.0 - .9 * step / max(1, steps-1)
        for p in params: p.grad = None
        loss = normalized_loss(local_predictions(shared, inputs, adapters), targets)
        if not torch.isfinite(loss): raise ValueError("nonfinite calibration loss")
        loss.backward()
        grads = [p.grad for p in params if p.grad is not None]
        if not grads or not all(torch.isfinite(g).all() for g in grads):
            raise ValueError("empty/nonfinite calibration gradients")
        grad_max = max(grad_max, max(float(g.abs().max()) for g in grads))
        if optimizer is not None:
            torch.nn.utils.clip_grad_norm_(params, 1.0); optimizer.step()
        else:
            with torch.no_grad():
                scale_ids = {id(p.log_scale) for p in projections}
                for p in params:
                    if p.grad is None: continue
                    m = moments[id(p)]
                    update = m.mul(.9).add(p.grad, alpha=.1).sign()
                    p.add_(update, alpha=-(.001 if id(p) in scale_ids else .025))
                    m.mul_(.99).add_(p.grad, alpha=.01)
                for projection in projections: projection.bound()
        if step in (0, steps-1): history.append({"step": step+1, "loss": float(loss.detach())})
    for module in modules: module.eval()
    return {"steps": steps, "strategy": strategy, "grad_max": grad_max,
            "wall_sec": time.perf_counter()-begin, "history": history,
            "trainable_parameters": sum(p.numel() for p in params)}


@contextmanager
def patched_group(model, layer_ids, shared, adapters=None):
    """Only in-memory references/LoRA slots; restore even when a forward fails."""
    missing = object(); saved = []
    try:
        for i, index in enumerate(layer_ids):
            layer = model.layers[index]
            values = {n: getattr(layer, n, missing) for n in ("lora_gate", "lora_up", "lora_down")}
            saved.append((layer, layer.mlp[0], layer.has_lora, values))
            layer.mlp[0] = shared; layer.has_lora = adapters is not None
            if adapters is not None:
                for name, adapter in zip(values, adapters[i]): setattr(layer, name, adapter)
        yield
    finally:
        for layer, original, has_lora, values in saved:
            layer.mlp[0] = original; layer.has_lora = has_lora
            for name, value in values.items():
                if value is missing:
                    if hasattr(layer, name): delattr(layer, name)
                else: setattr(layer, name, value)
