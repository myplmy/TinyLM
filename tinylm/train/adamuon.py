"""Opt-in single-device AdaMuon adaptation with FP32 elementwise variance.

Read: arXiv:2507.11005v3 Algorithm1/section3 and author main/adamuon.py.
Author main revision is unverified. This is an independent adaptation, NOT a
bitwise port: FP32 V/normalization, existing TinyLM BF16 NS5, no distributed
buffer. Nesterov defaults to the author code, unlike paper Algorithm1.

Default trainer/Muon/NorMuon are unchanged. Prevalidation is global; arithmetic
failure during step may leave earlier matrices or moments updated. Stop and
restore a valid checkpoint after such a failure; no global rollback is claimed.
"""
from __future__ import annotations

import math
import copy
from numbers import Integral, Real

import torch

from .muon import _newton_schulz, split_params as muon_split_params

SCHEMA = "TINYLM_ADAMUON_SIGN_NS_FP32_V1"
__all__ = ["AdaMuon", "parameter_groups"]


def _finite(value, label):
    if not bool(torch.isfinite(value).all()):
        raise ValueError("AdaMuon nonfinite " + label)


def _number(value, label, *, positive=False, upper=None):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("AdaMuon real scalar required: " + label)
    value = float(value)
    if (not math.isfinite(value) or value < 0 or (positive and value == 0)
            or (upper is not None and value >= upper)):
        raise ValueError("AdaMuon invalid scalar: " + label)
    return value


def _group(group):
    need = {"lr", "momentum", "nesterov", "ns_steps", "weight_decay", "eps", "schema"}
    if not need <= set(group) or group["schema"] != SCHEMA:
        raise ValueError("AdaMuon exact method/state schema required")
    for key in ("lr", "weight_decay"):
        _number(group[key], key)
    _number(group["momentum"], "momentum", upper=1)
    epsilon = _number(group["eps"], "eps", positive=True)
    eps32 = float(torch.tensor(epsilon, dtype=torch.float32))
    if eps32 <= 0 or not math.isfinite(eps32):
        raise ValueError("AdaMuon eps must be positive finite FP32")
    if type(group["nesterov"]) is not bool:
        raise ValueError("AdaMuon nesterov must be bool")
    if isinstance(group["ns_steps"], bool) or not isinstance(group["ns_steps"], Integral) or group["ns_steps"] < 1:
        raise ValueError("AdaMuon positive NS iteration count required")


def _parameter(p):
    if (not isinstance(p, torch.Tensor) or p.ndim != 2 or not p.numel()
            or p.dtype != torch.float32 or p.layout != torch.strided):
        raise ValueError("AdaMuon adaptation requires nonempty dense FP32 master matrices")


def _state(p, state, *, device=True):
    if not state:
        return
    if set(state) != {"momentum_buffer", "v_buffer"}:
        raise ValueError("AdaMuon first and full elementwise second moment required")
    for name, tensor in state.items():
        if (not isinstance(tensor, torch.Tensor) or tensor.shape != p.shape
                or tensor.dtype != torch.float32 or tensor.layout != torch.strided
                or (device and tensor.device != p.device)):
            raise ValueError("AdaMuon state shape/dtype/device differs: " + name)
        _finite(tensor, name)
    if bool((state["v_buffer"] < 0).any()):
        raise ValueError("AdaMuon second moment cannot be negative")


def parameter_groups(model, *, weight_decay, output_parameters=()):
    """Reuse TinyLM matrix routing, explicitly exclude output/embedding params.

    Return matrix list plus AdamW decay/no-decay groups. No optimizer is created.
    Tied embedding/output parameters count once. Caller-declared output weights
    and an explicit get_output_embeddings/lm_head module are excluded from NS.
    """
    _number(weight_decay, "weight_decay")
    matrix, other = muon_split_params(model)
    head_ids = {id(p) for p in output_parameters}
    for head in (getattr(model, "lm_head", None),
                 model.get_output_embeddings() if callable(getattr(model, "get_output_embeddings", None)) else None):
        if isinstance(head, torch.nn.Module):
            head_ids.update(id(p) for p in head.parameters())
    shifted = [p for p in matrix if id(p) in head_ids]
    matrix = [p for p in matrix if id(p) not in head_ids]
    other = other + shifted
    all_ids = [id(p) for p in matrix + other]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("AdaMuon parameter groups overlap")
    expected = {id(p) for p in model.parameters() if p.requires_grad}
    if set(all_ids) != expected:
        raise ValueError("AdaMuon parameter groups are incomplete")
    groups = []
    for kind, condition, decay in (("adamw_decay", lambda p: p.ndim >= 2, weight_decay),
                                    ("adamw_no_decay", lambda p: p.ndim < 2, 0.)):
        params = [p for p in other if condition(p)]
        if params:
            groups.append(dict(params=params, weight_decay=decay, group_kind=kind))
    return matrix, groups


class AdaMuon(torch.optim.Optimizer):
    """FP32 master/moments; existing BF16 NS, fixed final update RMS0.2.

    None gradient skips all state creation/decay. Zero gradient has zero update
    from zero history. Existing nonzero moments continue for a zero gradient.
    """
    def __init__(self, params, lr=.02, momentum=.95, nesterov=True,
                 ns_steps=5, weight_decay=0., eps=1e-8):
        defaults = dict(lr=lr, momentum=momentum, nesterov=nesterov, ns_steps=ns_steps,
            weight_decay=weight_decay, eps=eps, schema=SCHEMA)
        _group(defaults)
        if isinstance(params, set):
            raise ValueError("AdaMuon stable parameter order required")
        super().__init__(params, defaults)

    def add_param_group(self, param_group):
        group = dict(param_group)
        values = group["params"]
        if isinstance(values, set):
            raise ValueError("AdaMuon stable parameter order required")
        values = [values] if isinstance(values, torch.Tensor) else list(values)
        group["params"] = values
        _group(dict(self.defaults, **group))
        seen = {id(p) for old in self.param_groups for p in old["params"]}
        for p in values:
            _parameter(p)
            if id(p) in seen:
                raise ValueError("AdaMuon duplicate physical parameter")
            seen.add(id(p))
        super().add_param_group(group)

    def _preflight(self):
        seen, active = set(), []
        for group in self.param_groups:
            _group(group)
            for p in group["params"]:
                _parameter(p)
                if id(p) in seen:
                    raise ValueError("AdaMuon duplicate physical parameter")
                seen.add(id(p))
                _finite(p, "weight")
                _state(p, self.state.get(p, {}))
                g = p.grad
                if g is None:
                    continue
                if g.shape != p.shape or g.dtype != p.dtype or g.device != p.device or g.layout != torch.strided:
                    raise ValueError("AdaMuon gradient shape/dtype/device/layout differs")
                _finite(g, "gradient")
                active.append((group, p))
        return active

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()
        for group, p in self._preflight():
            state = self.state[p]
            if not state:
                state["momentum_buffer"] = torch.zeros_like(p)
                state["v_buffer"] = torch.zeros_like(p, dtype=torch.float32)
            beta, eps = group["momentum"], group["eps"]
            momentum = state["momentum_buffer"]
            momentum.mul_(beta).add_(p.grad)
            _finite(momentum, "updated momentum")
            direction = p.grad.add(momentum, alpha=beta) if group["nesterov"] else momentum
            _finite(direction, "direction")
            orthogonal = _newton_schulz(direction.sign(), steps=group["ns_steps"]).float()
            _finite(orthogonal, "NS output")
            variance = state["v_buffer"]
            variance.mul_(beta).addcmul_(orthogonal, orthogonal, value=1 - beta)
            _finite(variance, "updated second moment")
            update = orthogonal / (variance.sqrt() + eps)
            _finite(update, "preconditioned update")
            norm = update.norm()
            _finite(norm, "update norm")
            update.mul_(.2 * math.sqrt(p.numel()) / (norm + eps))
            _finite(update, "RMS aligned update")
            amount, decay = group["lr"], 1 - group["lr"] * group["weight_decay"]
            bound = float(p.abs().max()) * abs(decay) + float(update.abs().max()) * abs(amount)
            if not math.isfinite(bound) or bound > torch.finfo(p.dtype).max or not math.isfinite(decay):
                raise RuntimeError("AdaMuon weight overflow risk; stop and restore valid checkpoint")
            if group["weight_decay"]:
                p.mul_(decay)
            p.add_(update, alpha=-amount)
            _finite(p, "updated weight")
        return loss

    def load_state_dict(self, state_dict):
        groups = state_dict["param_groups"]
        if len(groups) != len(self.param_groups) or any(len(a["params"]) != len(b["params"])
                for a, b in zip(groups, self.param_groups)):
            raise ValueError("AdaMuon resume group topology differs")
        ids = [key for group in groups for key in group["params"]]
        if any(type(key) is not int or key < 0 for key in ids) or len(ids) != len(set(ids)):
            raise ValueError("AdaMuon resume parameter IDs must be unique nonnegative integers")
        if not set(state_dict["state"]) <= set(ids):
            raise ValueError("AdaMuon resume has orphan optimizer state")
        for saved, current in zip(groups, self.param_groups):
            _group(saved)
            for key, p in zip(saved["params"], current["params"]):
                _state(p, state_dict["state"].get(key, {}), device=False)
        # PyTorch may retain tensors from the supplied state; prevent future
        # steps from modifying a caller-owned in-memory checkpoint dictionary.
        super().load_state_dict(copy.deepcopy(state_dict))
        self._preflight()
