"""Matched assistant CE and same-student symmetric KL for paired QA wrappers.

No source data, model, checkpoint or CUDA operation is opened on import.
This is a scoped research loss, not a change to TinyLM's default trainer.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class Micro:
    kind: str
    indices: tuple


def schedule(pair_count, replay_count, epoch, seed=1337):
    """Both arms consume the same two views, replay, micro shapes and order."""
    if pair_count <= 0 or replay_count <= 0 or pair_count % 4 or replay_count % 8:
        raise ValueError('whole natural four-pair and replay eight-row micros required')
    rng = random.Random(seed + epoch)
    natural = list(range(pair_count)); replay = list(range(replay_count))
    rng.shuffle(natural); rng.shuffle(replay)
    micros = [Micro('natural', tuple(natural[i:i + 4])) for i in range(0, pair_count, 4)]
    micros += [Micro('replay', tuple(replay[i:i + 8])) for i in range(0, replay_count, 8)]
    rng.shuffle(micros)
    if len(micros) % 16:
        raise ValueError('exact sixteen full microbatches per optimizer update required')
    return [micros[i:i + 16] for i in range(0, len(micros), 16)]


def paired_positions(records, eot):
    """Align each view's own shifted predictor positions by gold token order."""
    if not records or len(records) % 2:
        raise ValueError('interleaved complete pairs required')
    answer = []
    for i in range(0, len(records), 2):
        left, right = records[i:i + 2]
        p = [j for j, y in enumerate(left.y) if y != -100]
        q = [j for j, y in enumerate(right.y) if y != -100]
        a = [left.y[j] for j in p]; b = [right.y[j] for j in q]
        if (a != b or len(a) < 2 or a[-1] != eot or eot in a[:-1]
                or any(left.segments[j] != 1 for j in p)
                or any(right.segments[j] != 1 for j in q)):
            raise ValueError('one assistant, identical nonempty content + terminal EOT required')
        answer.append((i, p, i + 1, q, a))
    return answer


def symmetric_kl(logits0, logits1):
    """Vocabulary SUM at each token; never dilute by vocab or padded mass.

    Both distributions carry gradients. The result is symmetric KL / 2,
    before the caller's whole-update content-token normalization.
    """
    if logits0.shape != logits1.shape or logits0.ndim != 2:
        raise ValueError('aligned token x vocabulary logits required')
    l0 = F.log_softmax(logits0.float(), dim=-1)
    l1 = F.log_softmax(logits1.float(), dim=-1)
    return .5 * ((l0.exp() - l1.exp()) * (l0 - l1)).sum(dim=-1)


def pair_statistics(logits0, logits1, targets):
    if (targets.ndim != 1 or logits0.shape != logits1.shape
            or logits0.shape[0] != targets.numel() or targets.numel() < 2):
        raise ValueError('same content + EOT target vector required')
    ce = (F.cross_entropy(logits0.float(), targets, reduction='sum')
          + F.cross_entropy(logits1.float(), targets, reduction='sum'))
    # EOT is part of CE, but is not allowed to dominate consistency.
    kl = symmetric_kl(logits0[:-1], logits1[:-1])
    return torch.stack((ce, kl.sum(), kl[0], kl[1:].sum()))


def natural_sums(model, hidden, records, eot, checkpoint_heads=True):
    """Gather only assistant predictors, then recompute small output heads.

    The tuple is CE sum, symmetric-KL sum, first-content-token KL sum and
    remaining-content-token KL sum. Lambda0 and lambda.05 use this same path.
    """
    positions = paired_positions(records, eot)
    if hidden.ndim != 3 or hidden.shape[0] != len(records):
        raise ValueError('micro hidden states and real pair rows differ')
    result = hidden.sum() * 0. + torch.zeros(4, device=hidden.device)
    for i, p, j, q, targets in positions:
        a = hidden[i, p]; b = hidden[j, q]
        target = torch.tensor(targets, dtype=torch.long, device=hidden.device)

        def loss_block(first, second, gold):
            la = model._head_logits(first.unsqueeze(0)).squeeze(0)
            lb = model._head_logits(second.unsqueeze(0)).squeeze(0)
            return pair_statistics(la, lb, gold)

        if checkpoint_heads and torch.is_grad_enabled() and a.requires_grad:
            from torch.utils.checkpoint import checkpoint
            values = checkpoint(loss_block, a, b, target, use_reentrant=False,
                                preserve_rng_state=False)
        else:
            values = loss_block(a, b, target)
        result = result + values
    return result, sum(len(t) - 1 for _, _, _, _, t in positions), len(positions)


def update_loss(word_sum, word_targets, kl_sum, content_targets, weight):
    """Normalize over the WHOLE optimizer update, including mixed replay."""
    if word_targets <= 0 or content_targets < 0 or weight not in (0., .05):
        raise ValueError('pre-registered word/content denominator and weight required')
    if content_targets == 0:
        if weight and bool(kl_sum.detach().ne(0)):
            raise ValueError('KL mass without natural content denominator')
        return word_sum / word_targets + kl_sum * 0.
    return word_sum / word_targets + weight * kl_sum / content_targets


def norm_text(value, language):
    """Scoped extractive-QA normalization, not a universal truth verifier."""
    import re
    import unicodedata
    value = unicodedata.normalize('NFKC', value).casefold()
    # Do not turn -5 into 5, or 1.5 into 15. This is deliberately a local
    # extractive metric, not a claim of the official SQuAD/KorQuAD scorer.
    kept = []
    for i, ch in enumerate(value):
        before = i > 0 and value[i - 1].isdigit()
        after = i + 1 < len(value) and value[i + 1].isdigit()
        numeric = (ch in '-+' and after) or (ch in '.,:/%' and (before or after))
        if numeric or not unicodedata.category(ch).startswith('P'):
            kept.append(ch)
    value = ''.join(kept)
    if language == 'en':
        value = re.sub(r'\b(a|an|the)\b', ' ', value)
    if language == 'ko':
        # Whitespace-insensitive character score is separately named in reports.
        return ''.join(value.split())
    if language != 'en':
        raise ValueError('declared bilingual metric required')
    return ' '.join(value.split())


def qa_scores(prediction, aliases, language):
    from collections import Counter
    if not aliases:
        raise ValueError('source aliases required')
    p = norm_text(prediction, language)
    scores = []
    for answer in aliases:
        a = norm_text(answer, language)
        pt = list(p) if language == 'ko' else p.split()
        at = list(a) if language == 'ko' else a.split()
        overlap = sum((Counter(pt) & Counter(at)).values())
        f1 = 2 * overlap / (len(pt) + len(at)) if pt and at else float(pt == at)
        scores.append((float(p == a), f1))
    return dict(em=max(x[0] for x in scores), f1=max(x[1] for x in scores),
                raw_exact=float(prediction in aliases))
