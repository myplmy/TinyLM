"""Differentiable answer ranking for verified two-question relation bundles.

This module opens no source assets, tokenizer, weights, model or CUDA context.
The caller supplies ordinary output-head features and owns candidate validity.
Crossed candidates are scoring inputs, never positive CE targets. Both arms
must execute their identical crossed path and count that extra work separately.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import random

import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class Micro:
    kind: str
    indices: tuple


def _count(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(name + ' must be a declared integer >= ' + str(minimum))
    return value


def _vector(value, name):
    if (not isinstance(value, torch.Tensor) or value.ndim != 1 or not value.numel()
            or not value.is_floating_point() or not bool(torch.isfinite(value).all())):
        raise ValueError(name + ' must be a nonempty finite floating vector')


def _scalar(value, name):
    if (not isinstance(value, torch.Tensor) or value.ndim != 0
            or not value.is_floating_point() or not bool(torch.isfinite(value))):
        raise ValueError(name + ' must be a finite floating scalar')


def _positions(record, eot):
    x, y, segments = record.x, record.y, record.segments
    if (not isinstance(x, list) or not isinstance(y, list) or not isinstance(segments, list)
            or not 1 <= len(x) <= 1024 or len(x) != len(y) or len(x) != len(segments)
            or any(type(v) is not int or v < 0 for v in x)
            or any(type(v) is not int or (v < 0 and v != -100) for v in y)
            or any(type(v) is not int for v in segments)):
        raise ValueError('complete shifted Record lists of length1..1024 required')
    positions = [i for i, target in enumerate(y) if target != -100]
    targets = [y[i] for i in positions]
    if (len(targets) < 2 or targets[-1] != eot or eot in targets[:-1]
            or positions != list(range(positions[0], positions[-1] + 1))
            or any(segments[i] != (1 if y[i] != -100 else 0) for i in range(len(y)))
            or any(y[i] != x[i + 1] for i in positions if i + 1 < len(x))):
        raise ValueError('one contiguous nonempty assistant content and terminal EOT required')
    return positions, targets


def sequence_terms(model, hidden, records, eot, checkpoint_heads=True):
    """Return differentiable content sums, separate EOT logp and content counts.

    ``hidden`` is [B,T,H]. Only each record's own shifted assistant predictors
    reach the existing ``model._head_logits``; prompt/header/PAD have no direct
    loss. Gradients through a real model's earlier causal states still belong
    to the caller's ordinary forward graph. No extra output head is created.
    """
    _count(eot, 'EOT token')
    if (not isinstance(records, (list, tuple)) or not records
            or not isinstance(hidden, torch.Tensor) or hidden.ndim != 3
            or hidden.shape[0] != len(records) or min(hidden.shape[1:]) < 1
            or not hidden.is_floating_point() or type(checkpoint_heads) is not bool
            or not callable(getattr(model, '_head_logits', None))):
        raise ValueError('real micro [B,T,H], complete records and callable output head required')
    selected = [_positions(record, eot) for record in records]
    if any(len(record.x) > hidden.shape[1] for record in records):
        raise ValueError('hidden sequence must include every complete record')
    rows, counts = [], []
    for i, (positions, targets) in enumerate(selected):
        features = hidden[i, positions]
        gold = torch.tensor(targets, dtype=torch.long, device=hidden.device)

        def loss_block(features, gold):
            logits = model._head_logits(features.unsqueeze(0))
            if (not isinstance(logits, torch.Tensor) or logits.ndim != 3
                    or logits.shape[:2] != (1, gold.numel()) or logits.shape[2] < 2
                    or not logits.is_floating_point()
                    or not bool(torch.isfinite(logits).all())
                    or bool(gold.ge(logits.shape[2]).any())):
                raise ValueError('finite selected [1,N,V] logits and in-vocabulary targets required')
            logp = F.log_softmax(logits[0].float(), dim=-1).gather(1, gold[:, None]).squeeze(1)
            return torch.stack((logp[:-1].sum(), logp[-1]))

        if checkpoint_heads and torch.is_grad_enabled() and features.requires_grad:
            from torch.utils.checkpoint import checkpoint
            terms = checkpoint(loss_block, features, gold, use_reentrant=False,
                               preserve_rng_state=False)
        else:
            terms = loss_block(features, gold)
        rows.append(terms)
        counts.append(len(targets) - 1)
    values = torch.stack(rows)
    return values[:, 0], values[:, 1], counts


def content_means(content_sums, content_counts):
    """Normalize each complete candidate by its own non-EOT content length.

    This does not eliminate length preference. A shared answer prefix cancels
    exactly between two candidate means only when their content counts match;
    the data/controller owns length matching or an explicit stratified report.
    """
    _vector(content_sums, 'content sums')
    if (not isinstance(content_counts, (list, tuple)) or len(content_counts) != content_sums.numel()
            or any(type(v) is not int or v <= 0 for v in content_counts)):
        raise ValueError('one positive content-token count per score required')
    return content_sums / content_sums.new_tensor(content_counts)


def score_matrix(positive_means, crossed_means):
    """Interleaved positive[q0a0,q1a1], cross[q0a1,q1a0] -> [N,2,2]."""
    _vector(positive_means, 'positive scores'); _vector(crossed_means, 'crossed scores')
    if (positive_means.shape != crossed_means.shape or positive_means.numel() % 2
            or positive_means.device != crossed_means.device):
        raise ValueError('complete two-question positive/crossed vectors on one device required')
    return torch.stack((positive_means[0::2], crossed_means[0::2],
                        crossed_means[1::2], positive_means[1::2]), dim=-1).reshape(-1, 2, 2)


def row_contrast_sum(scores, temperature=1., margin=0.):
    """Sum two answer-ranking softplus edges per bundle; exclude EOT upstream.

    Each row fixes one question and ranks its own answer above its verified
    crossed answer. Column/question gaps and one double-difference are not
    substitutes: either can look positive while one row still answers wrongly.
    """
    if (not isinstance(scores, torch.Tensor) or scores.ndim != 3 or not scores.shape[0]
            or tuple(scores.shape[1:]) != (2, 2) or not scores.is_floating_point()
            or not bool(torch.isfinite(scores).all())):
        raise ValueError('finite nonempty bundle x2questions x2answers scores required')
    if (type(temperature) not in (int, float) or not math.isfinite(temperature) or temperature <= 0
            or type(margin) not in (int, float) or not math.isfinite(margin) or margin < 0):
        raise ValueError('finite positive temperature and nonnegative margin required')
    gaps = torch.stack((scores[:, 0, 0] - scores[:, 0, 1],
                        scores[:, 1, 1] - scores[:, 1, 0]), dim=-1)
    return F.softplus((margin - gaps.float()) / temperature).sum()


def normalized_loss(correct_ce_sum, whole_update_correct_targets, relation_sum,
                    whole_update_relation_question_count, weight):
    """Whole-update correct CE mean plus lambda times mean relation-question loss.

    Correct CE includes terminal EOT. The relation denominator counts questions
    (two per bundle), not candidate tokens, padded slots or microbatches.
    A micro with no relation keeps a zero-valued graph on the same path.
    """
    _scalar(correct_ce_sum, 'correct CE sum'); _scalar(relation_sum, 'relation sum')
    _count(whole_update_correct_targets, 'whole-update correct targets', 1)
    _count(whole_update_relation_question_count, 'whole-update relation questions')
    if type(weight) not in (int, float) or weight not in (0., .1):
        raise ValueError('pre-registered lambda0 or lambda.1 required')
    if correct_ce_sum.device != relation_sum.device:
        raise ValueError('CE and relation sums must share a device')
    if whole_update_relation_question_count == 0:
        if bool(relation_sum.ne(0)):
            raise ValueError('relation mass without a whole-update relation denominator')
        return correct_ce_sum / whole_update_correct_targets + relation_sum * 0.
    return (correct_ce_sum / whole_update_correct_targets
            + weight * relation_sum / whole_update_relation_question_count)


def schedule(natural_pairs, relation_bundles, replay_rows, epoch, seed=1337):
    """Shuffle atomic eight-positive-row micros into sixteen-micro updates.

    A natural micro has4 two-wrapper pairs. A relation micro has4 bundles,
    eight positive rows and a separate forward of eight crossed candidate rows.
    A replay micro has8 ordinary positive rows. Native replay is caller-owned.
    """
    for value, name in ((natural_pairs, 'natural pairs'), (relation_bundles, 'relation bundles'),
                        (replay_rows, 'replay rows'), (epoch, 'epoch')):
        _count(value, name)
    if (type(seed) is not int or natural_pairs % 4 or relation_bundles % 4 or replay_rows % 8):
        raise ValueError('whole natural4/relation4/replay8 micros and integer seed required')
    rng = random.Random(seed + epoch)
    micros = []
    for kind, count, width in (('natural', natural_pairs, 4), ('relation', relation_bundles, 4),
                               ('replay', replay_rows, 8)):
        indices = list(range(count)); rng.shuffle(indices)
        micros.extend(Micro(kind, tuple(indices[i:i + width])) for i in range(0, count, width))
    if not micros or len(micros) % 16:
        raise ValueError('nonempty exact sixteen full positive micros per optimizer update required')
    rng.shuffle(micros)
    return [micros[i:i + 16] for i in range(0, len(micros), 16)]
