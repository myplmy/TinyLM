"""Whole-update token/content objectives for the existing next-token head.

This module opens no assets and adds no model parameters. ``weighted`` already
contains the whole-update denominator: sum microbatch scalars without another
division by the number of micros. Native CE remains the caller's separate term.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real
from pathlib import Path
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
import torch.nn.functional as F

from tinylm.data.sft import IGNORE
from tinylm.train.mtp_sft import Record


@dataclass(frozen=True)
class WeightPlan:
    weights: list[list[float]]
    targets: int
    content_targets: int
    eot_targets: int
    content_rows: int
    row_content_counts: list[int]
    policy: str


def _integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return int(value)


def make_weights(records: Sequence[Record], eot_id=4, policy='token') -> WeightPlan:
    """Freeze L0/P weights over every conversation of one optimizer update.

    L0: every supervised position has weight 1/N. P: content in conversation i
    has weight Nc/(N * Bplus * ci); every EOT still has weight 1/N. Multiple
    assistant turns remain one conversation. An ignored label never contributes,
    including an old wrong answer whose positive turn owner remains in context.
    """
    eot_id = _integer(eot_id, 'eot_id')
    if policy not in ('token', 'content'):
        raise ValueError('policy must be token or content')
    rows = list(records)
    content_counts, eot_counts = [], []
    for record in rows:
        if not isinstance(record, Record):
            raise ValueError('records must contain assistant-turn Records')
        if not (len(record.x) == len(record.y) == len(record.segments)):
            raise ValueError('record x/y/segments lengths must agree')
        content = eot = 0
        for token, target, owner in zip(record.x, record.y, record.segments):
            _integer(token, 'input token')
            owner = _integer(owner, 'assistant owner')
            if isinstance(target, bool) or not isinstance(target, Integral):
                raise ValueError('target must be an integer token or IGNORE')
            if target == IGNORE:
                continue
            _integer(target, 'supervised target')
            if owner == 0:
                raise ValueError('supervised target must have a positive assistant owner')
            eot += int(target == eot_id)
            content += int(target != eot_id)
        content_counts.append(content)
        eot_counts.append(eot)
    nc, ne = sum(content_counts), sum(eot_counts)
    total, positive_rows = nc + ne, sum(count > 0 for count in content_counts)
    if total == 0:
        raise ValueError('whole optimizer update has no supervised targets')
    token_weight = 1.0 / total
    weights = []
    for record, count in zip(rows, content_counts):
        content_weight = (nc / (total * positive_rows * count)
                          if policy == 'content' and count else token_weight)
        weights.append([0.0 if target == IGNORE else
                        token_weight if target == eot_id else content_weight
                        for target in record.y])
    return WeightPlan(weights=weights, targets=total, content_targets=nc,
                      eot_targets=ne, content_rows=positive_rows,
                      row_content_counts=content_counts, policy=policy)


def make_tensor(plan: WeightPlan, indices, width=1024, device='cpu',
                dtype=torch.float32):
    """Select frozen row weights in microbatch order and zero-pad their suffixes."""
    if not isinstance(plan, WeightPlan):
        raise ValueError('a whole-update WeightPlan is required')
    width = _integer(width, 'width', 1)
    if not isinstance(dtype, torch.dtype) or not dtype.is_floating_point:
        raise ValueError('weight tensor dtype must be floating point')
    selected = list(indices)
    if not selected:
        raise ValueError('weight microbatch must not be empty')
    padded = []
    for index in selected:
        index = _integer(index, 'record index')
        if index >= len(plan.weights):
            raise ValueError('record index lies outside the whole-update plan')
        row = plan.weights[index]
        if len(row) > width:
            raise ValueError('weight width cannot truncate a real record')
        if any(isinstance(value, bool) or not isinstance(value, Real)
               or not math.isfinite(value) or value < 0 for value in row):
            raise ValueError('planned weights must be finite nonnegative numbers')
        padded.append([float(value) for value in row] + [0.0] * (width - len(row)))
    return torch.tensor(padded, dtype=dtype, device=device)


def components(model, hidden, y, segments, weights, eot_id=4, chunk=2048,
               checkpoint_heads=True):
    """Reduce selected-head FP32 CE in bounded chunks to four scalar sums.

    The return is ``(sums, counts)``. Sum keys are weighted/raw/content/eot;
    count keys are targets/content/eot. Only weighted is globally normalized.
    Raw/content/eot keep their unweighted CE sums for comparable reporting.
    An entirely ignored micro is allowed because its update may contain other
    supervised micros; ``make_weights`` rejects an entirely ignored update.
    """
    eot_id = _integer(eot_id, 'eot_id')
    chunk = _integer(chunk, 'chunk', 1)
    tensors = (hidden, y, segments, weights)
    if not all(isinstance(value, torch.Tensor) for value in tensors):
        raise ValueError('hidden/targets/owners/weights must be tensors')
    if (hidden.ndim != 3 or y.ndim != 2 or hidden.shape[:2] != y.shape
            or segments.shape != y.shape or weights.shape != y.shape
            or hidden.shape[0] == 0 or hidden.shape[2] == 0):
        raise ValueError('aligned nonempty batch/hidden and target/owner/weight shapes required')
    integer_dtypes = (torch.uint8, torch.int8, torch.int16, torch.int32, torch.int64)
    if (not hidden.is_floating_point() or y.dtype not in integer_dtypes
            or segments.dtype not in integer_dtypes or not weights.is_floating_point()):
        raise ValueError('floating hidden/weights and integer targets/owners required')
    if any(value.device != hidden.device for value in (y, segments, weights)):
        raise ValueError('hidden/targets/owners/weights must share a device')
    if weights.requires_grad:
        raise ValueError('objective weights must be detached constants')
    if bool(segments.lt(0).any()) or bool((y.lt(0) & y.ne(IGNORE)).any()):
        raise ValueError('negative owner or non-IGNORE negative target')
    supervised = y.ne(IGNORE)
    if bool((supervised & segments.eq(0)).any()):
        raise ValueError('supervised target must have a positive assistant owner')
    valid = supervised & segments.gt(0)
    if (not bool(torch.isfinite(weights).all()) or bool(weights.lt(0).any())
            or bool(weights[~valid].ne(0).any()) or bool(weights[valid].le(0).any())):
        raise ValueError('finite positive valid weights and zero ignored weights required')
    target_count = int(valid.sum())
    content_count = int((valid & y.ne(eot_id)).sum())
    counts = dict(targets=target_count, content=content_count,
                  eot=target_count - content_count)
    # A zero scalar retains a hidden gradient even for an entirely masked micro.
    zero = hidden.reshape(-1)[:1].float().sum() * 0.0
    total = torch.stack((zero, zero, zero, zero))

    def head_ce(features, targets, position_weights):
        # All changing tensors are explicit checkpoint arguments. No loop target
        # or weight is captured for delayed backward recomputation.
        logits = model._head_logits(features)
        if logits.shape[:-1] != targets.shape or logits.shape[-1] < 1:
            raise ValueError('existing head must return aligned vocabulary logits')
        ce = F.cross_entropy(logits.reshape(-1, logits.shape[-1]).float(),
                             targets.reshape(-1).long(), reduction='none')
        eot = targets.reshape(-1).eq(eot_id)
        return torch.stack(((ce * position_weights.reshape(-1).float()).sum(),
                            ce.sum(), ce[~eot].sum(), ce[eot].sum()))

    # Match mtp_sft.components' positional chunks under the production geometry.
    # The inner split also bounds head positions when chunk < microbatch size.
    position_chunk = max(1, chunk // hidden.shape[0])
    for start in range(0, y.shape[1], position_chunk):
        end = min(start + position_chunk, y.shape[1])
        keep = valid[:, start:end]
        if not bool(keep.any()):
            continue
        features = hidden[:, start:end][keep].unsqueeze(0)
        targets = y[:, start:end][keep].unsqueeze(0)
        selected_weights = weights[:, start:end][keep].unsqueeze(0)
        for offset in range(0, targets.shape[1], chunk):
            args = (features[:, offset:offset + chunk],
                    targets[:, offset:offset + chunk],
                    selected_weights[:, offset:offset + chunk])
            if checkpoint_heads and torch.is_grad_enabled() and args[0].requires_grad:
                from torch.utils.checkpoint import checkpoint
                part = checkpoint(head_ce, *args, use_reentrant=False,
                                  preserve_rng_state=False)
            else:
                part = head_ce(*args)
            total = total + part
    return dict(zip(('weighted', 'raw', 'content', 'eot'), total.unbind())), counts
