"""Opt-in official linear+CE adapters; never selected by the default trainer.

Labels are already shifted. The caller owns turn masks and update denominators.
No package import patches a model; missing/unsupported backends fail explicitly.
"""
from __future__ import annotations

from functools import lru_cache
import importlib.metadata

import torch
import torch.nn.functional as F

BACKENDS = ("reference", "liger", "cce_exact")
PACKAGES = {"liger": ("liger-kernel", "0.8.5"),
            "cce_exact": ("cut-cross-entropy", "25.9.3")}


def validate_backend(backend):
    if backend not in BACKENDS:
        raise ValueError("explicit reference, liger or cce_exact backend required")
    return backend


def package_metadata():
    """Distribution metadata only, not a kernel execution/compatibility receipt."""
    result = {}
    for backend, (name, version) in PACKAGES.items():
        try:
            dist = importlib.metadata.distribution(name)
            result[backend] = dict(package=name, expected_version=version,
                installed_version=dist.version, version_matches=dist.version == version,
                path=str(dist.locate_file("")))
        except importlib.metadata.PackageNotFoundError:
            result[backend] = dict(package=name, expected_version=version,
                installed_version=None, version_matches=False, path=None)
    return result


def _check_version(backend):
    name, expected = PACKAGES[backend]
    try:
        actual = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError("requested acceleration package is not installed: " + name) from error
    if actual != expected:
        raise RuntimeError("uninspected package version: " + name + " " + actual)


@lru_cache(maxsize=2)
def _external_function(backend):
    _check_version(backend)
    if backend == "liger":
        from liger_kernel.transformers.fused_linear_cross_entropy import LigerFusedLinearCrossEntropyLoss

        def compute(projected, table, labels, reduction):
            loss = LigerFusedLinearCrossEntropyLoss(ignore_index=-100,
                lse_square_scale=0., label_smoothing=0., reduction=reduction,
                softcap=None, return_z_loss=False, accum_dtype=torch.float32,
                use_token_scaling=False, return_token_accuracy=False,
                return_predicted_tokens=False)
            return loss(table, projected, labels)
        return compute
    if backend == "cce_exact":
        from cut_cross_entropy import linear_cross_entropy

        def compute(projected, table, labels, reduction):
            return linear_cross_entropy(projected, table, labels,
                ignore_index=-100, softcap=None, reduction=reduction, shift=0,
                return_lse=False, filter_eps=None, accum_e_fp32=True,
                accum_c_fp32=True, filter_e_grad=False, filter_c_grad=False,
                impl="cce_exact")
        return compute
    raise ValueError("external backend required")


def _require_cuda(projected):
    if projected.device.type != "cuda":
        raise ValueError("official fused kernels require CUDA; no automatic CPU fallback")


def linear_ce(projected, table, labels, *, backend="reference", reduction="sum"):
    """Aligned [N,E] x [V,E] CE; no detach, extra shift, mean or loss scaling.

The optional per-row result preserves the path needed for weighted losses.
Full-vocabulary logits/KL/top-k remain separate APIs, not scalar-CE substitutes.
"""
    validate_backend(backend)
    if reduction not in ("sum", "none"):
        raise ValueError("use sum/none and the existing whole-update denominator")
    if (projected.ndim != 2 or table.ndim != 2 or labels.ndim != 1
            or projected.shape[0] != labels.numel()
            or projected.shape[1] != table.shape[1] or table.shape[0] < 1
            or labels.dtype != torch.long
            or projected.device != table.device or projected.device != labels.device):
        raise ValueError("aligned projected/table matrices and shifted long labels required")
    if not projected.is_floating_point() or not table.is_floating_point():
        raise ValueError("floating-point head tensors required")
    valid = labels.ne(-100)
    has_valid = bool(valid.any())
    if has_valid and (bool(labels[valid].lt(0).any())
                              or bool(labels[valid].ge(table.shape[0]).any())):
        raise ValueError("label outside vocabulary; only -100 is ignored")
    if backend != "reference":
        _require_cuda(projected)
        if projected.dtype not in (torch.float32, torch.bfloat16, torch.float16) or table.dtype not in (
                torch.float32, torch.bfloat16, torch.float16):
            raise ValueError("unregistered fused dtype")
        # Liger 0.8.5 sum path couples classifier dW to input.requires_grad.
        # Reject frozen-feature/table-only training rather than dropping dW.
        if (backend == "liger" and reduction == "sum" and torch.is_grad_enabled()
                and table.requires_grad and not projected.requires_grad):
            raise ValueError("Liger frozen-feature classifier-only gradient is unsupported")
    if not has_valid:
        zero = projected.reshape(-1)[:1].sum() * 0. + table.reshape(-1)[:1].sum() * 0.
        return zero if reduction == "sum" else zero.expand(labels.shape)
    if backend == "reference":
        return F.cross_entropy(F.linear(projected, table).float(), labels,
                               ignore_index=-100, reduction=reduction)
    return _external_function(backend)(projected, table, labels, reduction)


def model_head_ce(model, hidden, targets, *, horizon=1, backend="reference", reduction="sum"):
    """Use the original tied table and original NTP/MTP projection direction."""
    validate_backend(backend)
    if (hidden.ndim < 2 or tuple(hidden.shape[:-1]) != tuple(targets.shape)
            or targets.dtype != torch.long or hidden.device != targets.device
            or type(horizon) is not int or horizon not in (1, 2, 3, 4)):
        raise ValueError("aligned hidden/shifted targets and horizon1..4 required")
    if getattr(model, "_emb_fmt", None) not in (None, "fp16", "bf16"):
        raise ValueError("packed/storage-quantized head is outside fused training contract")
    if horizon == 1:
        projected = F.linear(hidden, model._emb_up_w().t()) if model.emb_up is not None else hidden
    else:
        if (not getattr(model.cfg, "mtp_aux", False)
                or horizon not in model.cfg.mtp_horizons):
            raise ValueError("MTP auxiliary head is disabled or horizon is invalid")
        projection = getattr(model, f"mtp_up{horizon}", None)
        if projection is None:
            raise ValueError("requested MTP projection is absent")
        projected = F.linear(hidden.float(), projection.float().t())
    table = model._emb_w()
    loss = linear_ce(projected.reshape(-1, projected.shape[-1]), table,
                     targets.reshape(-1), backend=backend, reduction=reduction)
    return loss.reshape_as(targets) if reduction == "none" else loss
