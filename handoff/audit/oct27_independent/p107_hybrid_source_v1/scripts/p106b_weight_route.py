"""Instance-local TLinear routes for the bounded P106B native control.

No assets, checkpoints or models are opened/created here. Float means latent
FP32 weights with identity weight/input gradients; the caller keeps matched
BF16 AMP training and FP32-MATH evaluation. Anneal0 is not this float route:
the original refresh still backpropagates through the STE window at anneal0.

Only the supplied model's TLinear bound methods are temporarily replaced. The
class and product defaults remain untouched. Missing refresh is an error in
both routes, so TLinear.forward cannot silently fall back to ternary weights.
The caller must keep compiled callables inside the context's lifetime.

New checkpoints need ``quantization_route`` metadata and the strict loader
below. A generic external loader that ignores this metadata cannot be changed
by this module; the driver must call generic_loader_guard before that path.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
import sys
from types import MethodType

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
from tinylm.model.ternary import TLinear

SCHEMA = 'P106B_WEIGHT_ROUTE_V1'
MODES = ('ternary', 'float')
_MARKER = '_p106b_weight_route'
_MISSING = object()
_CACHE_FIELDS = ('_wq', '_anneal_t')
_FALSE_FLAGS = ('center_weights', 'sparse34', 'use_ternary_kernel',
                'ternary_kernel_triton', 'fused_int8', 'arenas', 'mlp_film',
                'mlp_lrm', 'mtp_aux', 'qk_gain_learnable', 'repeat_embed_reinject',
                'repeat_kv_reuse', 'reuse_attn_on_dup', 'return_probs')
_FIXED_FLAGS = dict(n_modes=1, mode_rank=0, mlp_lora_rank=0, train_repeat=1.,
                    infer_repeat=1., attn_group=1, attn_kind='softmax_cla',
                    connectivity_mode='none', connectivity_density=1.,
                    wq_dtype='fp32', kv_dtype='fp32')


def _mode(mode):
    if type(mode) is not str or mode not in MODES:
        raise ValueError('explicit ternary or float weight route required')
    return mode


def route_metadata(mode):
    """Canonical computation contract, separate from cfg and recipe metadata."""
    mode = _mode(mode)
    return dict(schema=SCHEMA, mode=mode, scope='TLINEAR_WEIGHTS_ONLY',
                master_dtype='fp32',
                compute_policy='CALLER_MATCHED_BF16_AMP_TRAIN_FP32_MATH_EVAL',
                forward='LATENT_IDENTITY_VIEW' if mode == 'float' else 'ORIGINAL_ANNEALED_TERNARY',
                backward='IDENTITY' if mode == 'float' else 'ORIGINAL_STE_WINDOW',
                dedicated_loader_required=True)


def validate_route_metadata(metadata, expected_mode=None):
    if not isinstance(metadata, Mapping):
        raise ValueError('explicit quantization_route checkpoint metadata required')
    mode = _mode(metadata.get('mode'))
    expected = route_metadata(mode)
    if (dict(metadata) != expected
            or any(type(metadata[key]) is not type(value) for key, value in expected.items())):
        raise ValueError('weight route metadata is missing, changed or unsupported')
    if expected_mode is not None and mode != _mode(expected_mode):
        raise ValueError('checkpoint route differs from explicitly requested mode')
    return mode


def generic_loader_guard(payload):
    """Reject float checkpoints before a generic set_anneal1/freeze loader."""
    if not isinstance(payload, Mapping):
        raise ValueError('checkpoint mapping required')
    mode = validate_route_metadata(payload.get('quantization_route'))
    if mode == 'float':
        raise RuntimeError('float checkpoint requires weight_route plus load_routed_state; generic loader forbidden')
    return mode


def _check_cfg(cfg):
    if cfg is None:
        raise ValueError('explicit existing model cfg required')
    if any(bool(getattr(cfg, name, False)) for name in _FALSE_FLAGS):
        raise ValueError('unsupported centering, sparse, kernel, auxiliary or repeat route')
    for name, expected in _FIXED_FLAGS.items():
        if getattr(cfg, name, expected) != expected:
            raise ValueError('unsupported weight-route cfg: ' + name)
    if getattr(cfg, 'x2_active_tiles', ()):
        raise ValueError('physical tile selection is unsupported')
    if getattr(cfg, 'tie_mlp', False):
        raise ValueError('this experiment route requires the dense untied recipe')


def _check_linear(module):
    _check_cfg(module.cfg)
    if (type(module) is not TLinear or module.use_mode
            or not isinstance(module.weight, torch.nn.Parameter)
            or module.weight.ndim != 2 or module.weight.shape != (module.out_f, module.in_f)
            or module.weight.dtype != torch.float32 or not module.weight.requires_grad):
        raise ValueError('ordinary live FP32-master TLinear required')
    if any(getattr(module, name, None) is not None for name in
           ('_latent_shape', '_i8', '_alpha', '_lut_codes', '_lut_alpha',
            '_i8_cache', '_i8_cache_gen', '_unpack_gen', 'connectivity_mask')):
        raise ValueError('packed, latent-drop, unpack or connectivity state is unsupported')
    if module._connectivity_dense_grad or '_wq' in module._parameters:
        raise ValueError('connectivity gradients or Parameter quant cache are unsupported')


def _linears(model):
    if not isinstance(model, torch.nn.Module) or hasattr(model, '_orig_mod'):
        raise ValueError('uncompiled original module required before route installation')
    _check_cfg(getattr(model, 'cfg', None))
    modules = tuple(m for m in model.modules() if isinstance(m, TLinear))
    if not modules or tuple(getattr(model, '_tlinear_cache', ())) != modules:
        raise ValueError('complete unique TLinear cache in module traversal order required')
    if any(m.cfg is not model.cfg for m in modules):
        raise ValueError('all TLinear modules must belong to the same cfg instance')
    if (getattr(model, '_p102a_quant_update', None) is not None
            or getattr(model, '_int8_store', False) or getattr(model, '_lut_store', False)
            or getattr(model, '_unpack_cache', False)
            or getattr(model, '_emb_fmt', None) is not None
            or getattr(model, '_arena', None) is not None
            or getattr(model, '_arena_v', 0.) != 0.):
        raise ValueError('unsupported model deployment, arena or update-cache state')
    for name in ('refresh_quant', 'clear_quant', 'freeze_quant'):
        if not callable(getattr(model, name, None)):
            raise ValueError('model needs the existing quant lifecycle methods')
    for module in modules:
        _check_linear(module)
        if (getattr(module.refresh_quant, '__func__', None) is not TLinear.refresh_quant
                or getattr(module.forward, '__func__', None) is not TLinear.forward):
            raise ValueError('pre-existing TLinear method override is unsupported')
    return modules


@dataclass
class WeightRoute:
    mode: str
    model: object = field(repr=False)
    linears: tuple = field(repr=False)
    active: bool = False
    cache_invalidated: bool = False
    cache_restored: bool = False
    _versions: dict = field(default_factory=dict, repr=False)

    @property
    def metadata(self):
        return route_metadata(self.mode)

    def assert_active(self):
        return assert_route_active(self.model, self.mode)


def assert_route_active(model, expected_mode=None):
    route = getattr(model, _MARKER, None)
    if not isinstance(route, WeightRoute) or not route.active or route.model is not model:
        raise RuntimeError('explicit live weight_route context required')
    if expected_mode is not None and route.mode != _mode(expected_mode):
        raise RuntimeError('active weight route differs from requested checkpoint mode')
    if any(getattr(m, _MARKER, None) is not route for m in route.linears):
        raise RuntimeError('TLinear route ownership changed')
    return route


def _float_refresh(module, anneal, arena=None):
    route = getattr(module, _MARKER, None)
    if not isinstance(route, WeightRoute) or not route.active or route.mode != 'float':
        raise RuntimeError('float refresh outside its owning route')
    _check_linear(module)
    if arena is not None:
        raise ValueError('arena arguments are unsupported in the float control')
    module._anneal_t = anneal
    # A Parameter assigned directly to _wq would register a new state_dict key.
    # view_as creates a non-Parameter Tensor with an exact identity gradient.
    module._wq = module._w().view_as(module.weight)
    # Frozen evaluation needs version checks. Avoid per-update Python version
    # guards/dictionary writes in compiled training, which refreshes every call.
    if not route.model.training:
        route._versions[id(module)] = module.weight._version


def _ternary_refresh(module, anneal, arena=None):
    route = getattr(module, _MARKER, None)
    if not isinstance(route, WeightRoute) or not route.active or route.mode != 'ternary':
        raise RuntimeError('ternary refresh outside its owning route')
    _check_linear(module)
    if arena is not None:
        raise ValueError('arena arguments are unsupported in the ternary control')
    TLinear.refresh_quant(module, anneal, arena)
    if not route.model.training:
        route._versions[id(module)] = module.weight._version


def _guarded_forward(module, x, mode_p=None):
    route = getattr(module, _MARKER, None)
    if not isinstance(route, WeightRoute) or not route.active:
        raise RuntimeError('TLinear called outside its owning route')
    _check_linear(module)
    if (mode_p is not None or getattr(route.model, '_p102a_quant_update', None) is not None
            or getattr(route.model, '_emb_fmt', None) is not None
            or getattr(route.model, '_int8_store', False) or getattr(route.model, '_lut_store', False)
            or getattr(route.model, '_unpack_cache', False)):
        raise ValueError('mode and quant-update-cache paths are unsupported')
    if module._wq is None:
        raise RuntimeError('refresh_quant missing; implicit ternary fallback is forbidden')
    if getattr(route.model, '_quant_frozen', False):
        if route.model.training:
            raise RuntimeError('frozen inference cache cannot be used for training')
        if route._versions.get(id(module)) != module.weight._version:
            raise RuntimeError('frozen weight cache is stale after a weight update')
    return TLinear.forward(module, x, mode_p)


def _restore_attribute(owner, name, value):
    if value is _MISSING:
        if name in owner.__dict__:
            delattr(owner, name)
    else:
        setattr(owner, name, value)


@contextmanager
def weight_route(model, mode):
    """Temporarily install one route on this model's instances only.

    Same-model or shared-TLinear nesting is refused; separate models may have
    independent nested contexts. Methods, anneal, training flags and unchanged
    caches are restored on success and exceptions. If a parameter version
    changes (optimizer/load), old caches are stale and are invalidated instead.
    Weight updates themselves are intentionally retained.
    """
    mode = _mode(mode)
    if getattr(model, _MARKER, None) is not None:
        raise RuntimeError('nested route on the same model is unsupported')
    modules = _linears(model)
    if any(getattr(m, _MARKER, None) is not None for m in modules):
        raise RuntimeError('a TLinear instance is already owned by another route')
    route = WeightRoute(mode, model, modules)
    states = [(module, {name: module.__dict__.get(name, _MISSING)
                        for name in ('refresh_quant', 'forward', _MARKER, *_CACHE_FIELDS)})
              for module in modules]
    model_marker = model.__dict__.get(_MARKER, _MISSING)
    versions = tuple((p, p._version) for p in model.parameters())
    parameter_ids = tuple(id(p) for p in model.parameters())
    state_keys = tuple(model.state_dict())
    training_modes = tuple((m, m.training) for m in model.modules())
    frozen = getattr(model, '_quant_frozen', False)
    anneal = getattr(model, '_anneal', None)
    anneal_value = anneal.detach().clone() if isinstance(anneal, torch.Tensor) else None
    cfg_anneal = getattr(model.cfg, 'quant_anneal', _MISSING)
    cfg_flags = {name: getattr(model.cfg, name, _MISSING)
                 for name in (*_FALSE_FLAGS, *_FIXED_FLAGS, 'x2_active_tiles', 'tie_mlp')}
    try:
        setattr(model, _MARKER, route)
        for module in modules:
            setattr(module, _MARKER, route)
            module.refresh_quant = MethodType(_float_refresh if mode == 'float' else _ternary_refresh, module)
            module.forward = MethodType(_guarded_forward, module)
            module._wq = None
            module._anneal_t = None
        model._quant_frozen = False
        route.active = True
        yield route
    finally:
        route.active = False
        changed = any(p._version != version for p, version in versions)
        identity_changed = (tuple(id(p) for p in model.parameters()) != parameter_ids
                            or tuple(model.state_dict()) != state_keys)
        for module, saved in states:
            for name in ('refresh_quant', 'forward', _MARKER):
                _restore_attribute(module, name, saved[name])
            for name in _CACHE_FIELDS:
                _restore_attribute(module, name, None if changed or identity_changed else saved[name])
        model._quant_frozen = False if changed or identity_changed else frozen
        # This opt-in cache is unsupported even if it was opened accidentally
        # inside the context. Never leave its detached leaves/flag armed.
        model._p102a_quant_update = None
        if anneal_value is not None:
            with torch.no_grad():anneal.copy_(anneal_value)
        if cfg_anneal is not _MISSING:
            model.cfg.quant_anneal = cfg_anneal
        for name, value in cfg_flags.items():
            _restore_attribute(model.cfg, name, value)
        for module, training in training_modes:
            module.training = training
        _restore_attribute(model, _MARKER, model_marker)
        route.cache_invalidated = changed or identity_changed
        route.cache_restored = not route.cache_invalidated
        if identity_changed:
            raise RuntimeError('parameter/state identity changed inside the route; caches invalidated')


def load_routed_state(model, payload, expected_mode):
    """Strict in-memory load under an explicitly restored route; no file I/O.

    Metadata, all keys/shapes/dtypes are checked before copying any weights.
    Loading does not install a route implicitly and never selects a mode from
    a missing/legacy default. Recipe, tokenizer, SHA and optimizer validation
    remain driver-owned. Always construct the ordinary matching model first.
    """
    expected_mode = _mode(expected_mode)
    route = assert_route_active(model, expected_mode)
    if not isinstance(payload, Mapping):
        raise ValueError('checkpoint mapping required')
    validate_route_metadata(payload.get('quantization_route'), expected_mode)
    supplied = payload.get('model')
    current = model.state_dict()
    if not isinstance(supplied, Mapping) or set(supplied) != set(current):
        raise ValueError('exact uncompiled state_dict keys required before load')
    for key, value in current.items():
        other = supplied[key]
        if (not isinstance(other, torch.Tensor) or other.shape != value.shape
                or other.dtype != value.dtype or other.layout != value.layout):
            raise ValueError('strict state shape/dtype/layout mismatch: ' + key)
    aliases = {}
    for name, parameter in model.named_parameters(remove_duplicate=False):
        if name in current:
            aliases.setdefault(id(parameter), []).append(name)
    for names in aliases.values():
        first = supplied[names[0]]
        for name in names[1:]:
            other = supplied[name]
            same_view = (other.device == first.device and other.data_ptr() == first.data_ptr()
                         and other.stride() == first.stride())
            if not same_view and not torch.equal(other, first):
                raise ValueError('conflicting checkpoint values for one shared Parameter: ' + name)
    result = model.load_state_dict(supplied, strict=True)
    model.clear_quant()
    route._versions.clear()
    return result
