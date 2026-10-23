"""Opt-in ALM binary-divergence core, not the complete paper recipe.

Native tokenizer/byte alignment belongs to the caller. No model, data, device,
checkpoint, or external asset is opened by importing this module.
"""
from __future__ import annotations

import math
import torch
import torch.nn.functional as F

IGNORE = -100


class StudentProbabilityBoundary(FloatingPointError):
    """Exact or rounded student q=1 is distinct from malformed teacher input."""


def target_nll(model, hidden, targets, *, chunk=64, checkpoint_head=True):
    """Differentiable per-position NLL using the model's original tied head.

    Targets are already next-token shifted; do not shift them a second time.
    Positions excluded by the assistant mask have exactly zero loss/gradient.
    Vocabulary logits are bounded by the number of valid positions per chunk.
    """
    if hidden.ndim != 3 or tuple(hidden.shape[:2]) != tuple(targets.shape):
        raise ValueError("hidden[B,T,D] and already shifted target[B,T] required")
    if targets.dtype != torch.long or type(chunk) is not int or chunk < 1:
        raise ValueError("long targets and positive integer head chunk required")
    if hidden.device != targets.device:
        raise ValueError("hidden/targets must share the device")
    valid = targets.ne(IGNORE)
    positions = valid.reshape(-1).nonzero(as_tuple=True)[0]
    # Keep the no-target result differentiable without evaluating the head.
    flat = hidden[..., 0].reshape(-1).float() * 0.
    if positions.numel() == 0:
        return flat.reshape_as(targets), valid
    features = hidden.reshape(-1, hidden.shape[-1]).index_select(0, positions)
    labels = targets.reshape(-1).index_select(0, positions)

    def head_nll(h, y):
        logits = model._head_logits(h.unsqueeze(0))[0].float()
        if logits.ndim != 2 or logits.shape[0] != y.numel():
            raise ValueError("original main head returned an invalid shape")
        return F.cross_entropy(logits, y, reduction="none")

    blocks = []
    for start in range(0, positions.numel(), chunk):
        h, y = features[start:start+chunk], labels[start:start+chunk]
        if checkpoint_head and torch.is_grad_enabled() and h.requires_grad:
            from torch.utils.checkpoint import checkpoint
            block = checkpoint(head_nll, h, y, use_reentrant=False,
                               preserve_rng_state=False)
        else:
            block = head_nll(h, y)
        blocks.append(block)
    flat = flat.scatter(0, positions, torch.cat(blocks))
    return flat.reshape_as(targets), valid


def log1mexp(log_value):
    """Stable log(1-exp(x)) for finite x<0; never compute an unsafe branch."""
    if not log_value.is_floating_point() or not bool(torch.isfinite(log_value).all()):
        raise ValueError("finite floating-point log probability required")
    if bool(log_value.ge(0).any()):
        raise ValueError("log1mexp requires a strictly negative argument")
    lower = log_value < -math.log(2.)
    result = torch.empty_like(log_value)
    result[lower] = torch.log1p(-torch.exp(log_value[lower]))
    result[~lower] = torch.log(-torch.expm1(log_value[~lower]))
    return result


def binary_kl_logq(log_q_student, log_q_teacher):
    """KL(Bernoulli(qT) || Bernoulli(qS)), with a frozen teacher.

    The inputs are chunk log probabilities divided by temperature. Float64 is
    used only for these small scalar vectors, never for the model/head. Teacher
    q=1 is handled explicitly; student q=1 with qT<1 is an infinite-divergence
    event and fails rather than silently clipping/changing the objective.
    """
    if (log_q_student.shape != log_q_teacher.shape
            or log_q_student.device != log_q_teacher.device
            or not log_q_student.is_floating_point()
            or not log_q_teacher.is_floating_point()):
        raise ValueError("aligned floating-point chunk log probabilities required")
    s, t = log_q_student.double(), log_q_teacher.detach().double()
    if (not bool(torch.isfinite(s).all()) or not bool(torch.isfinite(t).all())
            or bool(s.gt(0).any()) or bool(t.gt(0).any())):
        raise ValueError("finite nonpositive chunk log probabilities required")
    qt = torch.exp(t)
    teacher_one = t.eq(0)
    if bool((s.eq(0) & ~teacher_one).any()):
        raise StudentProbabilityBoundary(
            "ROUNDED_OR_EXACT_STUDENT_Q1: qS=1, qT<1; infinite KL, no clipping")
    # Mask before calling log1mexp, not after an undefined derivative is made.
    active = ~teacher_one
    negative = torch.zeros_like(s)
    if bool(active.any()):
        negative[active] = (-torch.expm1(t[active])) * (
            log1mexp(t[active]) - log1mexp(s[active]))
    result = qt * (t-s) + negative
    if not bool(torch.isfinite(result).all()):
        raise FloatingPointError("nonfinite binary KL; no automatic clipping")
    return result


def chunk_kl(nll, supervised, chunks, *, temperature=100.):
    """Return summed KL and chunk count for explicit shifted target positions.

    Each chunk is {row, positions, teacher_logprob}; byte alignment and source
    provenance are caller responsibilities. Overlapping or unmasked positions
    fail. CE target and KD chunk denominators must remain distinct upstream.
    """
    if (nll.ndim != 2 or supervised.shape != nll.shape
            or supervised.dtype != torch.bool or supervised.device != nll.device
            or not math.isfinite(temperature) or temperature <= 0):
        raise ValueError("NLL/mask shape and positive finite temperature required")
    student, teacher, seen = [], [], set()
    for chunk in chunks:
        row, positions, value = chunk.get("row"), chunk.get("positions"), chunk.get("teacher_logprob")
        if (type(row) is not int or not 0 <= row < nll.shape[0]
                or not isinstance(positions, (list, tuple)) or not positions
                or any(type(p) is not int or not 0 <= p < nll.shape[1] for p in positions)
                or len(set(positions)) != len(positions)
                or list(positions) != list(range(positions[0], positions[0]+len(positions)))
                or isinstance(value, bool) or not isinstance(value, (float, int))
                or not math.isfinite(value) or not -1e30 < value <= 0):
            raise ValueError("explicit bounded target indices and teacher logprob required")
        if any((row, p) in seen for p in positions):
            raise ValueError("overlapping KD chunks")
        if not bool(supervised[row, list(positions)].all()):
            raise ValueError("KD chunk crosses an unsupervised target")
        seen.update((row, p) for p in positions)
        student.append(-nll[row, list(positions)].double().sum()/temperature)
        teacher.append(float(value)/temperature)
    if not student:
        return nll.sum().double()*0., 0
    values = binary_kl_logq(torch.stack(student), nll.new_tensor(teacher, dtype=torch.float64))
    return values.sum(), len(chunks)


def normalized_loss(ce_sum, ce_targets, kl_sum, kl_chunks, *, weight):
    """Whole optimizer-update denominators, not averages of micro means."""
    if (type(ce_targets) is not int or ce_targets < 1 or type(kl_chunks) is not int
            or kl_chunks < 0 or not math.isfinite(weight) or weight < 0):
        raise ValueError("whole-update target/chunk counts and nonnegative weight required")
    if kl_chunks == 0:
        if weight:
            raise ValueError("nonzero KD weight but no aligned chunks in update")
        return ce_sum/ce_targets
    return ce_sum/ce_targets + weight*kl_sum/kl_chunks
