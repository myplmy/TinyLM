"""Apply fixed-scale research packets once per eager native down-weight owner."""

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass

import torch

from scripts import p108_native_scale as native
from scripts.p108_weight_space import tensor_sha
from tinylm.model.ternary import TLinear, ternary
from tinylm.model.transformer import TiedMLPTransformer


_ACTIVE = "_p108_shared_down_edit_active"


@dataclass(frozen=True)
class DownOwner:
    module: TLinear
    layers: tuple[int, ...]
    visits: tuple[int, ...]


def physical_down_owners(model):
    if type(model) is not TiedMLPTransformer or not model.cfg.tie_mlp:
        raise ValueError("original tied TinyLM expected")
    logical = {}
    for index, layer in enumerate(model.layers):
        down = layer.mlp[0].down_proj
        if type(down) is not TLinear:
            raise ValueError("original TLinear down required")
        logical.setdefault(down, []).append(index)
    schedule = model.visit_schedule()
    if any(type(index) is not int or not 0 <= index < len(model.layers) for index in schedule):
        raise ValueError("invalid physical owner visit schedule")
    return {layers[0]: DownOwner(down, tuple(layers), tuple(i for i, index in enumerate(schedule) if index in layers))
            for down, layers in logical.items()}


def check_frozen_model(model, owners):
    cfg = model.cfg
    if (model.training or not model._quant_frozen or float(model._anneal) != 1 or cfg.quant_anneal != 1
            or model._int8_store or model._lut_store or model._unpack_cache or model._p102a_quant_update is not None
            or model._arena is not None or model._arena_v != 0 or cfg.center_weights or cfg.sparse34
            or cfg.use_ternary_kernel or cfg.wq_dtype != "fp32" or cfg.n_modes != 1):
        raise ValueError("frozen eager FP32 ternary evaluation required")
    buffers = {owner.module.weight.untyped_storage().data_ptr() for owner in owners.values()}
    if len(buffers) != len(owners):
        raise ValueError("distinct TLinear wrappers cannot alias a master storage")


def packet_target(model, owner, packet, realization):
    module = owner.module
    if (not owner.visits or module.use_mode or module.connectivity_mask is not None
            or module._latent_shape is not None or module._i8 is not None or module._lut_codes is not None
            or module._wq is None or module._wq.dtype != torch.float32 or module.weight.dtype != torch.float32
            or getattr(module.forward, "__func__", None) is not TLinear.forward
            or getattr(module.refresh_quant, "__func__", None) is not TLinear.refresh_quant):
        raise ValueError("visited eager native cache with an ordinary FP32 master required")
    expected = ternary(module.weight, model.cfg)
    expected = expected + (1.0 - model._anneal) * (module.weight - expected).detach()
    if tensor_sha(module._wq) != tensor_sha(expected):
        raise ValueError("frozen down cache differs from the current native master")
    group = model.cfg.micro_group or module.in_f
    if packet.get("group") != group:
        raise ValueError("packet group differs from the physical down module")
    target = native.unpack(module._wq, packet)
    changed = target.ne(module._wq)
    if realization == "sign" and not torch.equal(target.abs(), module._wq.abs()):
        raise ValueError("native latent sign can only flip existing nonzero trits")
    return target, changed


@contextmanager
def apply_shared_down_packets(model, packets, *, realization):
    """Edit each physical down module once; make every actual visit see the edit."""
    if realization not in ("sign", "codes") or not isinstance(packets, Mapping) or not packets:
        raise ValueError("explicit realization and a nonempty mapping of owner packets required")
    owners = physical_down_owners(model)
    check_frozen_model(model, owners)
    marker = object()
    if model.__dict__.setdefault(_ACTIVE, marker) is not marker:
        raise RuntimeError("a shared down edit already owns this model")
    saved = []
    try:
        receipts = []
        with torch.no_grad():
            prepared = []
            for index, packet in packets.items():
                if type(index) is not int or index not in owners:
                    raise ValueError("use the first logical layer of a physical down owner")
                owner = owners[index]
                target, changed = packet_target(model, owner, packet, realization)
                prepared.append((index, owner, packet, target, changed))

            for index, owner, packet, target, changed in prepared:
                module = owner.module
                master, cache, anneal = module.weight.detach().clone(), module._wq, module._anneal_t
                saved.append((module, master, cache, anneal))
                if bool(changed.any()):
                    if realization == "sign":
                        module.weight[changed] = -module.weight[changed]
                        module.refresh_quant(model._anneal)
                    else:
                        module._wq = target
                if tensor_sha(module._wq) != packet["target_sha256"]:
                    raise RuntimeError("native compute matrix differs from the sealed target")
                delta = module._wq - cache
                if bool((delta.ne(0) & ~changed).any()):
                    raise RuntimeError("change outside the physical packet support")
                receipts.append(dict(owner_layer=index, logical_layers=owner.layers, visit_ordinals=owner.visits,
                    changed_trits=int(changed.sum()), changed_master=int(module.weight.ne(master).sum()),
                    effective_delta_norm=float(delta.norm()), before_sha256=packet["original_sha256"],
                    after_sha256=packet["target_sha256"]))
        yield receipts
    finally:
        try:
            with torch.no_grad():
                for module, master, cache, anneal in reversed(saved):
                    if tensor_sha(module.weight) != tensor_sha(master):
                        module.weight.copy_(master)
                    module._wq = cache
                    module._anneal_t = anneal
        finally:
            del model.__dict__[_ACTIVE]
