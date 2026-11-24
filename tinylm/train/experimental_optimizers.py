"""Explicit matrix optimizer routes with shared roles and resume identity.

The legacy Muon/AdamW route remains in trainer.py. These are experimental
matched controls, not adopted recipes or complete official distributed ports.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Real

import torch

from ..training_defaults import EXPERIMENTAL_MATRIX_OPTIMIZERS, effective_matrix_weight_decay

SCHEMA = "TINYLM_EXPERIMENTAL_MATRIX_OPTIMIZER_V1"
CHECKPOINT_KEY = "experimental_matrix_optimizer"


def validate_options(method, matrix_lr_mult, *, opt_dtype="fp32", muon_scale="rms"):
    if method not in EXPERIMENTAL_MATRIX_OPTIMIZERS:
        raise ValueError("explicit experimental matrix optimizer required")
    if (isinstance(matrix_lr_mult, bool) or not isinstance(matrix_lr_mult, Real)
            or not math.isfinite(matrix_lr_mult) or matrix_lr_mult <= 0):
        raise ValueError("experimental optimizer requires positive finite --matrix-lr-mult")
    if opt_dtype != "fp32":
        raise ValueError("experimental optimizer requires --opt-dtype fp32")
    if muon_scale not in ("rms", "jordan"):
        raise ValueError("unknown matrix scale")
    if method.startswith("adamuon_") and muon_scale != "rms":
        raise ValueError("AdaMuon owns normalization; --muon-scale jordan does not apply")
    if method == "normuon_author_fp32" and muon_scale != "rms":
        raise ValueError("NorMuon author owns its shape scale; legacy --muon-scale override does not apply")


def _excluded_ids(model):
    excluded = {id(p) for module in model.modules() if isinstance(module, torch.nn.Embedding)
                for p in module.parameters()}
    outputs = [getattr(model, "lm_head", None), getattr(model, "emb_up", None)]
    getter = getattr(model, "get_output_embeddings", None)
    if callable(getter):
        outputs.append(getter())
    for output in outputs:
        if isinstance(output, torch.nn.Module):
            excluded.update(id(p) for p in output.parameters())
        elif isinstance(output, torch.Tensor):
            excluded.add(id(output))
    return excluded


def _role(name, parameter, excluded):
    parts = name.lower().split(".")
    leaf = parts[-1]
    if id(parameter) in excluded or parameter.ndim != 2:
        return "adamw"
    if (leaf.startswith("mtp_up") or any(p.startswith("lrm") for p in parts)
            or any(word in name.lower() for word in ("scale", "shift", "gates", "gain", "bias"))
            or leaf in ("code_logits", "selection_logits", "code_selection_logits", "logits")
            or ("gsq" in name.lower() and "logit" in name.lower())):
        return "adamw"
    return "matrix"


@dataclass
class ExperimentalOptimizers:
    adamw: torch.optim.Optimizer
    matrix: torch.optim.Optimizer
    matrices: list
    manifest: dict

    def validate_before_step(self):
        # Apply each author's input policy before AdamW writes. NorMuon allows
        # None momentum tails; AdaMuon rejects None gradients.
        # Arithmetic failures after this check still have no global rollback.
        if self.manifest["method"] == "adamuon_author_bf16":
            self.matrix._validate(gradients=True)
        elif self.manifest["method"] == "normuon_author_fp32":
            self.matrix.validate_before_step()


def build_experimental_optimizers(model, method, *, lr, matrix_lr_mult,
                                  matrix_weight_decay=None, muon_scale="rms",
                                  opt_dtype="fp32"):
    validate_options(method, matrix_lr_mult, opt_dtype=opt_dtype, muon_scale=muon_scale)
    if isinstance(lr, bool) or not isinstance(lr, Real) or not math.isfinite(lr) or lr <= 0:
        raise ValueError("positive finite base learning rate required")
    if matrix_weight_decay is not None and (isinstance(matrix_weight_decay, bool)
            or not isinstance(matrix_weight_decay, Real) or not math.isfinite(matrix_weight_decay)
            or matrix_weight_decay < 0):
        raise ValueError("finite nonnegative matrix weight decay required")
    wd = effective_matrix_weight_decay(method, matrix_weight_decay)
    named = [(name, p) for name, p in model.named_parameters() if p.requires_grad]
    excluded = _excluded_ids(model)
    roles = {id(p): _role(name, p, excluded) for name, p in named}
    matrices = [p for _, p in named if roles[id(p)] == "matrix"]
    if not matrices or any(p.dtype != torch.float32 for p in matrices):
        raise ValueError("nonempty FP32 master matrix set required")
    matrix_ids = {id(p) for p in matrices}
    names = {id(p): name for name, p in named}
    base_groups = model.param_groups(lr)
    listed = [id(p) for g in base_groups for p in g["params"]]
    if len(set(listed)) != len(listed) or set(listed) != set(names):
        raise ValueError("model groups must cover every trainable physical parameter once")
    groups = [dict(g, params=[p for p in g["params"] if id(p) not in matrix_ids])
              for g in base_groups]
    if not any(g["params"] for g in groups):
        raise ValueError("matched model must have a nonempty AdamW role")
    matrix_lr = float(lr * matrix_lr_mult)
    if not math.isfinite(matrix_lr) or matrix_lr <= 0:
        raise ValueError("effective matrix LR must be positive and finite")
    common = dict(lr=matrix_lr, weight_decay=float(wd))
    if method == "muon_matched":
        from .muon import Muon
        matrix = Muon(matrices, scale_mode=muon_scale, **common)
        state_rule = "FP32_MOMENTUM;LEGACY_NS5"
    elif method == "normuon_tinylm":
        from .normuon import NorMuon
        matrix = NorMuon(matrices, scale_mode=muon_scale, **common)
        state_rule = "TINYLM_ADAPTED;FP32_MOMENTUM_AND_ROW_V;NOT_OFFICIAL_EXACT"
    elif method == "adamuon_fp32v":
        from .adamuon import AdaMuon
        matrix = AdaMuon(matrices, **common)
        state_rule = "TINYLM_ADAPTED;FP32_MOMENTUM_AND_FULL_V;OWN_RMS_NORMALIZATION"
    elif method == "normuon_author_fp32":
        from .normuon_author import SingleDeviceNorMuonAuthor
        matrix = SingleDeviceNorMuonAuthor(matrices, **common)
        state_rule = "AUTHOR99F2AC72_ALIGNED;FP32_EMA_AND_LAST_AXIS_V;BF16_NS_FP32_POST;MATRIX_SINGLE;NONE_CONTINUES;GRAD_INPLACE"
    else:
        from .adamuon_author import AdaMuonAuthor
        matrix = AdaMuonAuthor(matrices, rank=0, world_size=1, **common)
        state_rule = "AUTHOR9C1BA5BE_ALIGNED;FP32_MOMENTUM_BF16_FLAT_V;WORLD1;SCRATCH_NOT_SERIALIZED"
    adamw = torch.optim.AdamW(groups, betas=(0.9, 0.95), eps=1e-8)
    entries = [dict(name=name, shape=list(p.shape), dtype=str(p.dtype),
                    role=roles[id(p)]) for name, p in named]
    group_entries = [dict(metadata={k: v for k, v in g.items() if k != "params"},
                          names=[names[id(p)] for p in g["params"]]) for g in groups]
    manifest = dict(schema=SCHEMA, method=method, state_rule=state_rule,
                    matrix_lr_mult=float(matrix_lr_mult), nominal_lr=float(lr),
                    matrix_weight_decay=float(wd), matrix_scale=(muon_scale if
                        method in ("muon_matched", "normuon_tinylm") else "OWN_NORMALIZATION"),
                    parameters=entries, adamw_groups=group_entries,
                    matrix_groups=[[names[id(p)] for p in g["params"]] for g in matrix.param_groups],
                    matrix_parameters=sum(p.numel() for p in matrices),
                    matrix_count=len(matrices), distributed_trainer=False)
    if method == "normuon_author_fp32":
        manifest.update(matrix_scale="AUTHOR_JORDAN;LEGACY_MUON_SCALE_NOT_APPLIED",
            matrix_none_gradient="ZERO_AND_MOMENTUM_TAIL;NO_CURRENT_WEIGHT_DECAY",
            matrix_gradient_mutation=True,
            auxiliary_reference="TINYLM_MATCHED_TORCH_ADAMW_EPS_1E-8;NOT_AUTHOR_AUX_ADAM_EPS_1E-10")
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    manifest["contract_sha256"] = hashlib.sha256(encoded).hexdigest().upper()
    return ExperimentalOptimizers(adamw, matrix, matrices, manifest)


def validate_optimizer_checkpoint(checkpoint, expected_manifest, *, route=None):
    saved = checkpoint.get(CHECKPOINT_KEY)
    if expected_manifest is None:
        if saved is not None:
            raise ValueError("experimental optimizer checkpoint cannot resume as legacy optimizer")
        return
    if saved != expected_manifest:
        raise ValueError("experimental optimizer method/roles/LR/WD contract differs")
    if "opt_muon" not in checkpoint or "opt" not in checkpoint:
        raise ValueError("both experimental matrix and AdamW states required for exact resume")
    if expected_manifest["method"] == "normuon_author_fp32":
        if route is None or route.manifest != expected_manifest:
            raise ValueError("NorMuon author checkpoint requires its constructed matched route")
        # This only validates the new matrix payload, not every AdamW tensor.
        route.matrix.validate_checkpoint(checkpoint["opt_muon"])


def checkpoint_manifest(route):
    return copy.deepcopy(route.manifest)
