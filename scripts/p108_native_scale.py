"""Opt-in fixed-scale ternary edits, with no loading or product defaults.

``sign`` is a true latent sign flip followed by the original quantizer.
``codes`` changes frozen native trits, including zero transitions; it does not
claim that an arbitrary latent requantization will retain that frozen edit.
"""
from contextlib import contextmanager
import random

import torch

from scripts import p108_weight_space as common


def layout(weight, group):
    if (not isinstance(weight, torch.Tensor) or weight.ndim != 2
            or weight.dtype != torch.float32 or not torch.isfinite(weight).all()
            or type(group) is not int or group <= 0 or weight.shape[1] % group):
        raise ValueError('finite FP32 matrix and exact positive group required')
    view = weight.detach().reshape(weight.shape[0], -1, group)
    scales = view.abs().amax(-1, keepdim=True)
    codes = view.sign().to(torch.int8)
    if not torch.equal(view, codes.to(view.dtype) * scales):
        raise ValueError('input is not an exact fixed-scale ternary matrix')
    return codes, scales


def from_codes(original, codes, group):
    old, scales = layout(original, group)
    if (not isinstance(codes, torch.Tensor) or codes.dtype != torch.int8
            or codes.shape != old.shape or codes.device != old.device
            or not bool(((codes >= -1) & (codes <= 1)).all())):
        raise ValueError('native code shape/device/domain differs')
    if bool(((scales == 0) & codes.ne(0)).any()):
        raise ValueError('a zero-scale group cannot acquire nonzero codes')
    changed = codes.ne(old)
    target = original.detach().clone().reshape_as(old)
    values = (codes.to(original.dtype) * scales).expand_as(target)
    target[changed] = values[changed]
    return target.reshape_as(original)


def project(original, delta, group, *, allow_zero):
    if (type(allow_zero) is not bool or not isinstance(delta, torch.Tensor)
            or delta.shape != original.shape or delta.dtype != original.dtype
            or delta.device != original.device or not torch.isfinite(delta).all()):
        raise ValueError('finite matched delta and explicit zero policy required')
    codes, scales = layout(original, group)
    desired = (original + delta).reshape_as(codes)
    if not torch.isfinite(desired).all():
        raise ValueError('requested target overflows')
    if allow_zero:
        safe = torch.where(scales > 0, scales, torch.ones_like(scales))
        new = torch.round(desired / safe).clamp(-1, 1).to(torch.int8)
        new = torch.where(scales > 0, new, torch.zeros_like(new))
    else:
        # Ties at zero retain the original sign. Original masked zeros stay zero.
        new = torch.where(desired * codes < 0, -codes, codes)
    return from_codes(original, new, group)


def transitions(original, target, group):
    old, scales = layout(original, group)
    new = target.reshape_as(old).sign().to(torch.int8)
    if not torch.equal(from_codes(original, new, group), target):
        raise ValueError('target scale or untouched signed-zero bytes differ')
    return torch.stack([((old == a) & (new == b)).sum(-1)
                        for a in (-1, 0, 1) for b in (-1, 0, 1)], dim=-1)


def random_control(original, target, group, seed):
    if type(seed) is not int:
        raise ValueError('explicit integer control seed required')
    old, _ = layout(original, group)
    # Randomness is CPU-owned and therefore reproducible across devices.
    src = old.cpu().reshape(-1, group)
    dst = target.detach().reshape_as(old).sign().to(torch.int8).cpu().reshape_as(src)
    result = src.clone()
    rng = random.Random(seed)
    changed_groups = torch.nonzero(src.ne(dst).any(-1), as_tuple=False).flatten().tolist()
    for row in changed_groups:
        for before in (-1, 0, 1):
            pool = torch.nonzero(src[row] == before, as_tuple=False).flatten().tolist()
            rng.shuffle(pool)
            offset = 0
            for after in (-1, 0, 1):
                if after == before:
                    continue
                count = int(((src[row] == before) & (dst[row] == after)).sum())
                positions = pool[offset:offset + count]
                if len(positions) != count:
                    raise ValueError('cannot match native transition counts')
                if positions:
                    result[row, positions] = after
                offset += count
    out = from_codes(original, result.reshape_as(old).to(old.device), group)
    if not torch.equal(transitions(original, out, group), transitions(original, target, group)):
        raise RuntimeError('random native transitions are not matched')
    return out


def packet(original, target, group):
    transitions(original, target, group)
    old, scales = layout(original, group)
    new = target.reshape_as(old).sign().to(torch.int8)
    indices = torch.nonzero(new.flatten().ne(old.flatten()), as_tuple=False).flatten()
    return dict(schema='P108_NATIVE_CODE_PACKET_V1', group=group, shape=list(original.shape),
                original_sha256=common.tensor_sha(original), scales_sha256=common.tensor_sha(scales),
                target_sha256=common.tensor_sha(target), indices=indices.cpu().tolist(),
                codes=new.flatten()[indices].cpu().tolist(),
                transition_sha256=common.tensor_sha(transitions(original, target, group)))


def unpack(original, data):
    if (not isinstance(data, dict) or data.get('schema') != 'P108_NATIVE_CODE_PACKET_V1'
            or data.get('shape') != list(original.shape)
            or data.get('original_sha256') != common.tensor_sha(original)):
        raise ValueError('native packet origin/schema/shape differs')
    group = data['group']
    old, scales = layout(original, group)
    if data.get('scales_sha256') != common.tensor_sha(scales):
        raise ValueError('native packet scale binding differs')
    indices, values = data.get('indices'), data.get('codes')
    if (not isinstance(indices, list) or not isinstance(values, list) or len(indices) != len(values)
            or len(set(indices)) != len(indices)
            or any(type(i) is not int or i < 0 or i >= original.numel() for i in indices)
            or any(type(c) is not int or c not in (-1, 0, 1) for c in values)):
        raise ValueError('native packet indices/codes are invalid')
    codes = old.clone()
    if indices:
        codes.flatten()[indices] = torch.tensor(values, dtype=torch.int8, device=codes.device)
    target = from_codes(original, codes, group)
    if (common.tensor_sha(target) != data.get('target_sha256')
            or common.tensor_sha(transitions(original, target, group)) != data.get('transition_sha256')):
        raise ValueError('native packet target or transition binding differs')
    return target


@contextmanager
def apply(model, route, edits, mode):
    """All edits prevalidated; exact prior caches and master bytes restored."""
    if mode not in ('sign', 'codes') or not isinstance(edits, list) or not edits:
        raise ValueError('explicit native realization and nonempty edits required')
    route.assert_active()
    if route.metadata.get('mode') != 'ternary' or model.training or not getattr(model, '_quant_frozen', False):
        raise ValueError('frozen eval ternary route required')
    modules = dict(common.down_modules(model))
    if len({i for i, _ in edits}) != len(edits):
        raise ValueError('duplicate edited layer')
    prepared = []
    for index, data in edits:
        if type(index) is not int or index not in modules:
            raise ValueError('unknown native edited layer')
        module = modules[index]
        if (getattr(module.cfg, 'center_weights', False) or module._wq is None
                or module.weight.dtype != torch.float32):
            raise ValueError('uncentered FP32 master and existing cache required')
        group = getattr(module.cfg, 'micro_group', 128) or module.weight.shape[1]
        if data.get('group') != group:
            raise ValueError('packet group differs from module group')
        target = unpack(module._wq.detach(), data)
        before_codes, _ = layout(module._wq, group)
        after_codes = target.reshape_as(before_codes).sign().to(torch.int8)
        changed = before_codes.ne(after_codes).reshape_as(target)
        if mode == 'sign' and bool((changed & (module._wq == 0)).any()):
            raise ValueError('latent sign mode cannot unmask a zero')
        if mode == 'sign' and not torch.equal(target.abs(), module._wq.abs()):
            raise ValueError('latent sign mode must retain every magnitude')
        prepared.append((index, module, data, target, changed))
    saved, receipts = [], []
    try:
        with torch.no_grad():
            for index, module, data, target, changed in prepared:
                latent, cache = module.weight.detach().clone(), module._wq
                saved.append((module, latent, cache))
                if bool(changed.any()):
                    if mode == 'sign':
                        module.weight[changed] = -module.weight[changed]
                        module.refresh_quant(1.)
                    else:
                        module._wq = target
                if common.tensor_sha(module._wq) != data['target_sha256']:
                    raise RuntimeError('native actual effective values differ from sealed target')
                if mode == 'sign' and not torch.equal(module.weight.abs(), latent.abs()):
                    raise RuntimeError('native sign edit changed master magnitudes')
                actual = module._wq.detach() - cache.detach()
                if bool((actual.ne(0) & ~changed).any()):
                    raise RuntimeError('native edit changed values outside requested support')
                receipts.append(dict(layer=index, mode=mode, changed=int(changed.sum()),
                    latent_changed=int(module.weight.ne(latent).sum()), changed_outside_requested=0,
                    effective_delta_norm=float(actual.norm()), scales_sha256=data['scales_sha256'],
                    before_sha256=data['original_sha256'], after_sha256=data['target_sha256'],
                    storage_scope='LATENT_SIGN_REQUANT' if mode == 'sign' else 'FROZEN_NATIVE_TRITS_NOT_LATENT_REQUANT'))
        route.assert_active()
        yield receipts
    finally:
        with torch.no_grad():
            for module, latent, cache in reversed(saved):
                if not torch.equal(module.weight, latent):
                    module.weight.copy_(latent)
                module._wq = cache
                route._versions[id(module)] = module.weight._version
                if common.tensor_sha(module.weight) != common.tensor_sha(latent) or module._wq is not cache:
                    raise RuntimeError('native exact rollback failed')
        route.assert_active()
