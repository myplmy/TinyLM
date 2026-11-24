"""Independent FP32 implementation of the pinned NorMuon author arithmetic.

Reference: zichongli5/NorMuon@99f2ac72ee61a0e09514856a6dbaad2ecbdecab6,
normuon.py blob1b87c80b2dea0a4bb21102703e30fdadde4754e1.
https://github.com/zichongli5/NorMuon/blob/99f2ac72ee61a0e09514856a6dbaad2ecbdecab6/normuon.py

The four interfaces preserve EMA/Nesterov gradient mutation, FP32 post-NS
normalization, source 4D axes, None momentum tails and optional auxiliary Adam.
Adaptations: FP32 contiguous masters only, strict fixed topology/checkpoints,
collective prevalidation and sequential owner broadcast instead of all_gather.
This is neither an unchanged upstream library nor its FSDP2 implementation.
Late arithmetic errors can partially update weights/state; restore a good
checkpoint on every rank. No whole-step transactional rollback is promised.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from numbers import Real

import torch
import torch.distributed as dist

from .adamuon_author import _orthogonal

SCHEMA = "TINYLM_NORMUON_AUTHOR_FP32_BROADCAST_V1"
SOURCE = "99f2ac72ee61a0e09514856a6dbaad2ecbdecab6:1b87c80b2dea0a4bb21102703e30fdadde4754e1"


def _number(value, name, upper=None, positive=False):
    if (isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)
            or value < 0 or (positive and value == 0) or (upper is not None and value >= upper)):
        raise ValueError("NorMuon author invalid " + name)


def _settings(group):
    if type(group.get("use_muon")) is not bool:
        raise ValueError("NorMuon author explicit use_muon required")
    for key in ("lr", "weight_decay"):
        _number(group[key], key)
    if group["use_muon"]:
        for key in ("momentum", "beta2"):
            _number(group[key], key, upper=1)
        keys = {"params", "use_muon", "lr", "weight_decay", "momentum", "beta2"}
    else:
        betas = group["betas"]
        if not isinstance(betas, (tuple, list)) or len(betas) != 2:
            raise ValueError("NorMuon author two Adam betas required")
        for beta in betas:
            _number(beta, "Adam beta", upper=1)
        _number(group["eps"], "Adam eps", positive=True)
        if not 0 < float(torch.tensor(group["eps"], dtype=torch.float32)) < float("inf"):
            raise ValueError("NorMuon author eps must remain finite positive FP32")
        keys = {"params", "use_muon", "lr", "weight_decay", "betas", "eps"}
    if set(group) != keys:
        raise ValueError("NorMuon author unexpected or missing group fields")


def _parameter(p, matrix):
    if (not isinstance(p, torch.nn.Parameter) or p.dtype != torch.float32
            or p.layout != torch.strided or not p.numel() or not p.is_contiguous()
            or (matrix and p.ndim not in (2, 4))):
        raise ValueError("NorMuon author requires dense contiguous FP32 masters; matrix groups 2D/4D")


def _state(p, value, matrix, *, same_device=True):
    if not value:
        return
    required = {"momentum_buffer", "second_momentum_buffer"} if matrix else {"exp_avg", "exp_avg_sq", "step"}
    if set(value) != required:
        raise ValueError("NorMuon author exact state fields required")
    if matrix:
        fields = (("momentum_buffer", p.shape), ("second_momentum_buffer", p[..., :1].shape))
    else:
        fields = (("exp_avg", p.shape), ("exp_avg_sq", p.shape))
        if type(value["step"]) is not int or value["step"] < 1:
            raise ValueError("NorMuon author positive integer Adam step required")
    for key, shape in fields:
        tensor = value[key]
        if (not isinstance(tensor, torch.Tensor) or tensor.shape != shape
                or tensor.dtype != torch.float32 or tensor.layout != torch.strided
                or (same_device and tensor.device != p.device)
                or not bool(torch.isfinite(tensor).all())):
            raise ValueError("NorMuon author state shape/dtype/device/finite differs: " + key)
        if key in ("second_momentum_buffer", "exp_avg_sq") and bool((tensor < 0).any()):
            raise ValueError("NorMuon author variance cannot be negative")


def _matrix_direction(grad, moment, variance, beta, beta2):
    # The caller's gradient is deliberately changed, just as in the reference.
    moment.lerp_(grad, 1 - beta)
    direction = grad.lerp_(moment, beta)
    shape = direction.shape
    matrix = direction.reshape(shape[0], -1) if direction.ndim == 4 else direction
    update = _orthogonal(matrix, 5).to(grad.dtype).reshape(shape)
    before = update.norm(dim=(-2, -1), keepdim=True)
    row_mean = (update * update).mean(dim=-1, keepdim=True)
    variance.lerp_(row_mean, 1 - beta2)
    update.mul_(1 / variance.sqrt().add_(1e-10))
    after = update.norm(dim=(-2, -1), keepdim=True)
    update.mul_(before / after.add_(1e-10))
    update.mul_(max(1, grad.size(-2) / grad.size(-1)) ** .5)
    return update


def _adam_direction(grad, value, betas, eps):
    value["step"] += 1
    first, second = value["exp_avg"], value["exp_avg_sq"]
    first.lerp_(grad, 1 - betas[0])
    second.lerp_(grad.square(), 1 - betas[1])
    step = value["step"]
    return (first / (1 - betas[0] ** step)) / ((second / (1 - betas[1] ** step)).sqrt() + eps)


class _AuthorBase(torch.optim.Optimizer):
    def __init__(self, groups, *, variant, distributed, rank, world_size):
        if type(rank) is not int or type(world_size) is not int or not 0 <= rank < world_size:
            raise ValueError("NorMuon author valid explicit rank/world_size required")
        if not distributed and (rank != 0 or world_size != 1):
            raise ValueError("NorMuon author single device requires rank0/world1")
        if distributed and (not dist.is_initialized() or dist.get_rank() != rank
                or dist.get_world_size() != world_size):
            raise ValueError("NorMuon author matching initialized default process group required")
        self.variant, self.distributed = variant, distributed
        self.rank, self.world_size = rank, world_size
        prepared, seen = [], set()
        for original in groups:
            group = dict(original)
            if type(group.get("use_muon")) is not bool:
                raise ValueError("NorMuon author explicit use_muon group routing required")
            source = group["params"]
            if isinstance(source, (set, torch.Tensor)):
                raise ValueError("NorMuon author ordered nonempty parameter groups required")
            params = list(source)
            if not params:
                raise ValueError("NorMuon author empty groups are unsupported")
            for p in params:
                _parameter(p, group["use_muon"])
                if id(p) in seen:
                    raise ValueError("NorMuon author duplicate physical parameter")
                seen.add(id(p))
            if distributed and group["use_muon"]:
                params.sort(key=lambda p: tuple(p.shape), reverse=True)
            group["params"] = params
            defaults = (dict(lr=.02, momentum=.95, beta2=.95, weight_decay=0.) if group["use_muon"]
                else dict(lr=3e-4, betas=(.9, .95), eps=1e-10, weight_decay=0.))
            for key, value in defaults.items():
                group.setdefault(key, value)
            _settings(group)
            prepared.append(group)
        if not prepared or len({p.device for group in prepared for p in group["params"]}) != 1:
            raise ValueError("NorMuon author one nonempty device per rank required")
        self._building = True
        super().__init__(prepared, {})
        self._building = False
        self._completed_steps = 0
        self.topology_sha256 = self._topology()
        self._collective(None, topology=True)

    def add_param_group(self, group):
        if not getattr(self, "_building", False):
            raise ValueError("NorMuon author topology is fixed")
        super().add_param_group(group)

    def _topology(self):
        topology = [(group["use_muon"], [(list(p.shape), str(p.dtype)) for p in group["params"]])
            for group in self.param_groups]
        return hashlib.sha256(json.dumps(topology, separators=(",", ":")).encode()).hexdigest().upper()

    def _collective(self, error, *, topology=False):
        if not self.distributed:
            if error:
                raise ValueError(error)
            return
        signature = (self.variant, self.topology_sha256) if topology else None
        gathered = [None] * self.world_size
        dist.all_gather_object(gathered, (error, signature))
        failures = [entry[0] for entry in gathered if entry[0]]
        if failures:
            raise ValueError("NorMuon author collective preflight: " + "; ".join(failures))
        if topology and len({entry[1] for entry in gathered}) != 1:
            raise ValueError("NorMuon author rank topology/variant differs")

    def validate_before_step(self):
        try:
            if self._topology() != self.topology_sha256:
                raise ValueError("NorMuon author topology changed")
            for group in self.param_groups:
                _settings(group)
                for p in group["params"]:
                    _parameter(p, group["use_muon"])
                    _state(p, self.state.get(p, {}), group["use_muon"])
                    if not bool(torch.isfinite(p).all()):
                        raise ValueError("NorMuon author nonfinite master")
                    grad = p.grad
                    if grad is not None and (grad.shape != p.shape or grad.dtype != p.dtype
                            or grad.device != p.device or grad.layout != torch.strided
                            or not bool(torch.isfinite(grad).all())):
                        raise ValueError("NorMuon author gradient shape/dtype/device/finite differs")
            error = None
        except (ValueError, KeyError) as exc:
            error = str(exc)
        self._collective(error)

    def _local_step(self, p, group):
        present = p.grad is not None
        if not present:
            p.grad = torch.zeros_like(p)
        value = self.state[p]
        if group["use_muon"]:
            if not value:
                value.update(momentum_buffer=torch.zeros_like(p), second_momentum_buffer=torch.zeros_like(p[..., :1]))
            update = _matrix_direction(p.grad, value["momentum_buffer"], value["second_momentum_buffer"],
                group["momentum"], group["beta2"])
        else:
            if not value:
                value.update(exp_avg=torch.zeros_like(p), exp_avg_sq=torch.zeros_like(p), step=0)
            update = _adam_direction(p.grad, value, group["betas"], group["eps"])
        if not bool(torch.isfinite(update).all()):
            raise ArithmeticError("NorMuon author nonfinite computed update")
        if present and group["weight_decay"]:
            p.mul_(1 - group["lr"] * group["weight_decay"])
        p.add_(update.reshape_as(p), alpha=-group["lr"])
        if not bool(torch.isfinite(p).all()):
            raise ArithmeticError("NorMuon author nonfinite updated master")
        _state(p, value, group["use_muon"])

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()
        self.validate_before_step()
        for group in self.param_groups:
            for index, p in enumerate(group["params"]):
                sharded = self.distributed and group["use_muon"]
                owner = index % self.world_size if sharded else self.rank
                try:
                    if owner == self.rank:
                        self._local_step(p, group)
                    error = None
                except (ValueError, RuntimeError, ArithmeticError) as exc:
                    error = str(exc)
                self._collective(error)
                if sharded:
                    dist.broadcast(p.detach(), src=owner)
        self._completed_steps += 1
        return loss

    def _contract(self):
        return dict(schema=SCHEMA, source=SOURCE, variant=self.variant,
            rank=self.rank, world_size=self.world_size, topology_sha256=self.topology_sha256,
            completed_steps=self._completed_steps,
            transport="OWNER_BROADCAST" if self.distributed else "SINGLE_DEVICE")

    def state_dict(self):
        result = super().state_dict()
        result["author_contract"] = self._contract()
        return result

    def _checked_checkpoint(self, state_dict):
        contract = state_dict.get("author_contract", {})
        completed = contract.get("completed_steps")
        expected = dict(self._contract(), completed_steps=completed)
        if contract != expected or type(completed) is not int or completed < 0:
            raise ValueError("NorMuon author resume method/rank/world/topology differs")
        groups, states = state_dict["param_groups"], state_dict["state"]
        if len(groups) != len(self.param_groups) or any(len(a["params"]) != len(b["params"])
                for a, b in zip(groups, self.param_groups)):
            raise ValueError("NorMuon author resume parameter topology differs")
        ids = [key for group in groups for key in group["params"]]
        if len(ids) != len(set(ids)) or any(type(key) is not int or key < 0 for key in ids):
            raise ValueError("NorMuon author unique saved parameter IDs required")
        owned = set()
        for saved, current in zip(groups, self.param_groups):
            _settings(saved)
            if saved["use_muon"] != current["use_muon"]:
                raise ValueError("NorMuon author matrix/auxiliary role changed")
            for index, (key, p) in enumerate(zip(saved["params"], current["params"])):
                if not self.distributed or not saved["use_muon"] or index % self.world_size == self.rank:
                    owned.add(key)
                _state(p, states.get(key, {}), saved["use_muon"], same_device=False)
        if not set(states) <= owned or (completed > 0 and set(states) != owned):
            raise ValueError("NorMuon author orphan/nonowner state")
        payload = {key: value for key, value in state_dict.items() if key != "author_contract"}
        return payload, completed

    def validate_checkpoint(self, state_dict):
        """Read-only matrix payload checks before other checkpoint components load."""
        self._checked_checkpoint(state_dict)

    def load_state_dict(self, state_dict):
        payload, completed = self._checked_checkpoint(state_dict)
        super().load_state_dict(copy.deepcopy(payload))
        self._completed_steps = completed


class SingleDeviceNorMuonAuthor(_AuthorBase):
    def __init__(self, params, lr=.02, weight_decay=0., momentum=.95, beta2=.95):
        super().__init__([dict(params=params, use_muon=True, lr=lr, weight_decay=weight_decay,
            momentum=momentum, beta2=beta2)], variant="MATRIX_SINGLE", distributed=False, rank=0, world_size=1)


class NorMuonAuthor(_AuthorBase):
    def __init__(self, params, lr=.02, weight_decay=0., momentum=.95, beta2=.95, *, rank, world_size):
        super().__init__([dict(params=params, use_muon=True, lr=lr, weight_decay=weight_decay,
            momentum=momentum, beta2=beta2)], variant="MATRIX_SHARDED", distributed=True, rank=rank, world_size=world_size)


class SingleDeviceNorMuonWithAuxAdamAuthor(_AuthorBase):
    def __init__(self, param_groups):
        super().__init__(param_groups, variant="AUX_SINGLE", distributed=False, rank=0, world_size=1)


class NorMuonWithAuxAdamAuthor(_AuthorBase):
    def __init__(self, param_groups, *, rank, world_size):
        super().__init__(param_groups, variant="AUX_SHARDED", distributed=True, rank=rank, world_size=world_size)
