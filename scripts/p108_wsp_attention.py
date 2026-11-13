"""Opt-in no-gradient WSP output interventions, restricted to live float R1.

Attention head columns follow the actual Q-head layout of the O projection.
No Q/K/V, cache ownership, product defaults, training or file I/O is changed.
"""
from contextlib import contextmanager
import torch
from scripts import p108_weight_space as common


def outputs(model):
    if list(model.visit_schedule()) != list(range(len(model.layers))):
        raise ValueError('only the trained R1 visit schedule is supported')
    result = {}
    for i, layer in enumerate(model.layers):
        result[f'attention:{i}'] = layer.attn_mod.o_proj
        result[f'mlp:{i}'] = layer.mlp[0].down_proj
    if len({id(m) for m in result.values()}) != len(result):
        raise ValueError('shared output parameters are not supported')
    return result


def head_columns(module, n_heads, head):
    if (type(n_heads) is not int or n_heads < 1 or type(head) is not int
            or not 0 <= head < n_heads or module.weight.shape[1] % n_heads):
        raise ValueError('invalid Q-head column layout')
    width = module.weight.shape[1] // n_heads
    return list(range(head * width, (head + 1) * width))


def head_delta(module, n_heads, head):
    delta = torch.zeros_like(module.weight)
    cols = head_columns(module, n_heads, head)
    delta[:, cols] = -module.weight.detach()[:, cols]
    return delta


@contextmanager
def edit(model, route, edits):
    """Edit registered float masters; refresh and restore exact prior caches."""
    route.assert_active()
    if route.mode != 'float' or model.training or not model._quant_frozen:
        raise ValueError('frozen float evaluation route required')
    modules = outputs(model)
    if not edits or len({key for key, _ in edits}) != len(edits):
        raise ValueError('nonempty unique output edits required')
    prepared = []
    for key, delta in edits:
        if key not in modules:
            raise ValueError('unknown output key')
        module = modules[key]
        if (delta.shape != module.weight.shape or delta.device != module.weight.device
                or delta.dtype != module.weight.dtype or not torch.isfinite(delta).all()
                or module._wq is None):
            raise ValueError('output delta layout/finite/cache mismatch')
        prepared.append((key, module, delta))
    saved, receipts = [], []
    try:
        with torch.no_grad():
            for key, module, delta in prepared:
                original, cache = module.weight.detach().clone(), module._wq
                before = module._wq.detach().clone()
                saved.append((module, original, cache))
                if bool(delta.ne(0).any()):
                    module.weight.add_(delta)
                    module.refresh_quant(1.)
                actual = module._wq.detach() - before
                if bool((actual.ne(0) & ~delta.ne(0)).any()):
                    raise RuntimeError('float edit changed values outside requested support')
                tolerance = 2 * torch.finfo(delta.dtype).eps * max(1., float(before.abs().max()))
                if float((actual - delta).abs().max()) > tolerance:
                    raise RuntimeError('actual float edit differs from requested delta')
                receipts.append(dict(key=key, master_changed=int(module.weight.ne(original).sum()),
                    effective_changed=int(actual.ne(0).sum()), changed_outside_requested=0,
                    delta_norm=float(actual.norm()), requested_delta_norm=float(delta.norm()),
                    before_sha256=common.tensor_sha(original), after_sha256=common.tensor_sha(module.weight)))
        route.assert_active()
        yield receipts
    finally:
        with torch.no_grad():
            for module, original, cache in reversed(saved):
                if common.tensor_sha(module.weight) != common.tensor_sha(original):
                    module.weight.copy_(original)
                module._wq = cache
                route._versions[id(module)] = module.weight._version
                if common.tensor_sha(module.weight) != common.tensor_sha(original) or module._wq is not cache:
                    raise RuntimeError('master/cache rollback failed')
        route.assert_active()


@contextmanager
def capture(model):
    values, handles = {}, []
    for key, module in outputs(model).items():
        def hook(_module, args, result, key=key):
            if key in values:
                raise RuntimeError('unexpected repeated output visit')
            values[key] = dict(input=args[0][0, -8:].detach().float().mean(0).cpu(),
                               output=result[0, -8:].detach().float().mean(0).cpu())
        handles.append(module.register_forward_hook(hook))
    def residual(_module, args):
        if 'residual' in values:
            raise RuntimeError('unexpected repeated final norm visit')
        values['residual'] = args[0][0, -8:].detach().float().mean(0).cpu()
    handles.append(model.norm_f.register_forward_pre_hook(residual))
    try:
        yield values
    finally:
        for handle in handles:
            handle.remove()
