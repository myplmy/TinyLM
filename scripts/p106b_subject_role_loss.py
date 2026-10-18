"""Four-query subject/role ranking; pure tensors and schedules only.

Rows/candidates0..3 are subject0-role0, subject0-role1, subject1-role0,
subject1-role1 in the caller's declared role order. The caller certifies all
three off-diagonal answers against the fictional fact table. This module
does not turn natural QA string differences into negative labels.

All arms receive the full16 scored sequences per graph. Every mode computes
the same full softplus tensor before masking; unused edges keep zero-valued
autograd paths. Positive CE and native CE remain caller-owned, separate sums.
No assets, tokenizers, learned weights, models or CUDA context are opened here.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import random
import sys

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reuse the frozen A implementation without changing its source or semantics.
from scripts.p106b_relation_bind_loss import (  # noqa: E402
    content_means, normalized_loss, sequence_terms,
)

MODES = ('CE', 'ROLE_ONLY', 'ALL_AXES')
WEIGHTS = dict(CE=0., ROLE_ONLY=.1, ALL_AXES=.1)


@dataclass(frozen=True)
class Micro:
    kind: str
    indices: tuple


def _mode(mode):
    if type(mode) is not str or mode not in MODES:
        raise ValueError('explicit CE, ROLE_ONLY or ALL_AXES mode required')
    return mode


def _vector(value, name):
    if (not isinstance(value, torch.Tensor) or value.ndim != 1
            or not value.numel() or not value.is_floating_point()
            or not bool(torch.isfinite(value).all())):
        raise ValueError(name + ' must be a nonempty finite floating vector')


def _scores(value):
    if (not isinstance(value, torch.Tensor) or value.ndim != 3
            or not value.shape[0] or tuple(value.shape[1:]) != (4, 4)
            or not value.is_floating_point() or not bool(torch.isfinite(value).all())):
        raise ValueError('finite nonempty graph x4queries x4answers scores required')


def score_matrix(positive_means, crossed_means):
    """Graph-major diag4 and cross12 -> differentiable [N,4,4].

    Positive order is q0a0,q1a1,q2a2,q3a3. Cross order is graph-major,
    then question0..3, then candidate0..3 excluding its diagonal, in ascending
    candidate order. Two graphs therefore supply8 positive and24 cross scores.
    Candidate length normalization belongs to content_means upstream; there
    is no equal-length or shared-prefix-cancellation assumption here.
    """
    _vector(positive_means, 'positive means')
    _vector(crossed_means, 'crossed means')
    if (positive_means.numel() % 4 or crossed_means.numel() != 3 * positive_means.numel()
            or positive_means.device != crossed_means.device
            or positive_means.dtype != crossed_means.dtype):
        raise ValueError('complete diag4/cross12 graph vectors on one device/dtype required')
    positive = positive_means.reshape(-1, 4)
    cross = crossed_means.reshape(-1, 4, 3)
    values = [positive[:, q] if q == a else cross[:, q, a if a < q else a - 1]
              for q in range(4) for a in range(4)]
    return torch.stack(values, dim=-1).reshape(-1, 4, 4)


def negative_mask(mode, *, device=None):
    """Canonical bool4x4 policy; rows and columns share the declared order.

    ROLE_ONLY chooses i^1, same-role/other-subject is i^2, and both axes
    differ at i^3. CE keeps the same graph with no selected negative edges.
    """
    mode = _mode(mode)
    mask = torch.zeros((4, 4), dtype=torch.bool, device=device)
    if mode == 'ROLE_ONLY':
        rows = torch.arange(4, device=device)
        mask[rows, rows ^ 1] = True
    elif mode == 'ALL_AXES':
        mask = ~torch.eye(4, dtype=torch.bool, device=device)
    return mask


def masked_row_contrast_sum(scores, mask, temperature=1., margin=0.):
    """Sum row-wise mean negative softplus, never sum3 negatives as3 questions.

    This pure explicit-mask interface also supports a jointly permuted
    row/candidate/mask fixture. Production modes should use row_contrast_sum.
    A row with zero selected edges contributes a differentiable zero. It does
    not invent relation questions; the caller supplies the whole-update count.
    The diagonal is never a valid negative. All16 penalties are evaluated in
    FP32 even for CE or unused edges, after requiring every score to be finite.
    """
    _scores(scores)
    if (not isinstance(mask, torch.Tensor) or mask.dtype != torch.bool
            or tuple(mask.shape) != (4, 4) or bool(mask.diagonal().any())):
        raise ValueError('bool4x4 negative mask with an empty diagonal required')
    if (type(temperature) not in (int, float) or not math.isfinite(temperature) or temperature <= 0
            or type(margin) not in (int, float) or not math.isfinite(margin) or margin < 0):
        raise ValueError('finite positive temperature and nonnegative margin required')
    values = scores.float()
    gold = values.diagonal(dim1=-2, dim2=-1)
    penalties = F.softplus((values - gold.unsqueeze(-1) + margin) / temperature)
    active = mask.to(device=scores.device)
    counts = active.sum(-1).clamp_min(1).to(dtype=penalties.dtype)
    return ((penalties * active.to(dtype=penalties.dtype)).sum(-1) / counts).sum()


def row_contrast_sum(scores, mode='ALL_AXES', temperature=1., margin=0.):
    """Canonical full-compute CE/one-negative/three-negative row policy."""
    mode = _mode(mode)
    # Validate scores before consulting a device so bad inputs fail consistently.
    _scores(scores)
    return masked_row_contrast_sum(scores, negative_mask(mode, device=scores.device),
                                   temperature, margin)


def schedule(natural_pairs, relation_bundles, replay_rows, epoch, seed=1337):
    """Shuffle whole micro8 positives into exact sixteen-micro updates.

    natural micro:4 pairs x2 positives. Relation micro:2 graphs x4 positives;
    its24 additional cross rows are computed separately by the controller in
    physical micro8 chunks. Replay micro:8 positives. No incomplete micro or
    update is repeated/padded to fill a source deficit. Counts are mandatory.

    Registered full pass:8192 natural pairs,2048 relation graphs,4096 replay
    rows ->28672 positive rows ->224 updates, or896 over four passes. Native
    TRAIN8x1024 targets per update are a separate caller-owned loss and source.
    """
    for value, name in ((natural_pairs, 'natural pairs'), (relation_bundles, 'relation graphs'),
                        (replay_rows, 'replay rows'), (epoch, 'epoch')):
        if type(value) is not int or value < 0:
            raise ValueError(name + ' must be a declared nonnegative integer')
    if (type(seed) is not int or natural_pairs % 4 or relation_bundles % 2 or replay_rows % 8):
        raise ValueError('complete natural4/relation2/replay8 micros and integer seed required')
    rng = random.Random(seed + epoch)
    micros = []
    for kind, count, width in (('natural', natural_pairs, 4), ('relation', relation_bundles, 2),
                               ('replay', replay_rows, 8)):
        indices = list(range(count))
        rng.shuffle(indices)
        micros.extend(Micro(kind, tuple(indices[i:i + width])) for i in range(0, count, width))
    if not micros or len(micros) % 16:
        raise ValueError('nonempty exact sixteen full positive micros per update required')
    rng.shuffle(micros)
    return [micros[i:i + 16] for i in range(0, len(micros), 16)]
