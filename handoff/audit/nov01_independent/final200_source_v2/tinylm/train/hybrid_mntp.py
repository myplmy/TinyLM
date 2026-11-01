"""Independent causal/MNTP tensors and objective accounting, not a trainer.

MNTP predicts the original selected token j from output j-1, using a corrupted
bidirectional input. Documents are explicit; no corpus boundaries are inferred.
The initial adaptation uses 100% reserved-token replacement, not BERT 80/10/10.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import torch
import torch.nn.functional as F

IGNORE_INDEX = -100


@dataclass(frozen=True)
class ObjectiveBatch:
    inputs: torch.Tensor
    targets: torch.Tensor
    attention_mask: torch.Tensor
    objective: str
    selected_positions: torch.Tensor

    @property
    def target_count(self):
        return int((self.targets != IGNORE_INDEX).sum().item())

    @property
    def executed_input_tokens(self):
        # Includes PAD positions actually sent through the model, not unique text.
        return self.inputs.numel()


def _documents(document_ids):
    if (not isinstance(document_ids, torch.Tensor) or document_ids.dtype != torch.long
            or document_ids.ndim != 2 or min(document_ids.shape) < 1
            or bool((document_ids < -1).any())):
        raise ValueError("document_ids must be positive-shape int64 [B,T], with -1 for trailing PAD")
    valid = document_ids >= 0
    if document_ids.shape[1] > 1 and bool((~valid[:, :-1] & valid[:, 1:]).any()):
        raise ValueError("document padding must be trailing")
    for row in document_ids:
        values = row[row >= 0]
        segments = torch.unique_consecutive(values)
        if segments.unique().numel() != segments.numel():
            raise ValueError("one document ID cannot reappear in a later segment")
    return valid


def document_visibility(document_ids, *, bidirectional):
    """Block documents and PAD keys; PAD query sees its own diagonal only."""
    if not isinstance(bidirectional, bool):
        raise ValueError("bidirectional must be an explicit bool")
    valid = _documents(document_ids)
    batch, length = document_ids.shape
    identity = torch.eye(length, dtype=torch.bool, device=document_ids.device)
    same_doc = document_ids[:, :, None] == document_ids[:, None, :]
    allowed = same_doc & valid[:, :, None] & valid[:, None, :]
    if not bidirectional:
        allowed = allowed & identity.new_ones(length, length).tril()
    allowed = allowed | ((~valid)[:, :, None] & identity)
    return allowed[:, None, :, :]


def _full_inputs(tokens, document_ids, vocab_size):
    if (not isinstance(tokens, torch.Tensor) or not isinstance(document_ids, torch.Tensor)
            or tokens.dtype != torch.long
            or tokens.ndim != 2 or tokens.shape[0] < 1 or tokens.shape[1] < 3
            or tokens.shape != document_ids.shape or tokens.device != document_ids.device
            or isinstance(vocab_size, bool) or not isinstance(vocab_size, int)
            or vocab_size < 2 or bool((tokens < 0).any())
            or bool((tokens >= vocab_size).any())):
        raise ValueError("full token/doc tensors must match [B,T+1], int64, device and vocabulary")
    valid = _documents(document_ids)
    same = valid[:, :-1] & valid[:, 1:] & (document_ids[:, :-1] == document_ids[:, 1:])
    return same


def eligible_mntp(tokens, document_ids, *, vocab_size, special_max=34, mask_id=13):
    """A selected token must be in the actual input, with a same-doc predictor."""
    same = _full_inputs(tokens, document_ids, vocab_size)
    if (isinstance(mask_id, bool) or not isinstance(mask_id, int)
            or isinstance(special_max, bool) or not isinstance(special_max, int)
            or not 0 <= mask_id <= special_max < vocab_size):
        raise ValueError("reserved mask ID and protected special range must be explicit and valid")
    if bool(((tokens == mask_id) & (document_ids >= 0)).any()):
        raise ValueError("original source already contains the reserved mask token")
    eligible = torch.zeros_like(tokens, dtype=torch.bool)
    # Exclude the last full token: it is a causal target, but is not an input.
    eligible[:, 1:-1] = same[:, :-1] & (tokens[:, 1:-1] > special_max)
    return eligible


def causal_batch(tokens, document_ids, *, vocab_size):
    same = _full_inputs(tokens, document_ids, vocab_size)
    targets = tokens[:, 1:].clone().masked_fill_(~same, IGNORE_INDEX)
    return ObjectiveBatch(tokens[:, :-1].clone(), targets,
                          document_visibility(document_ids[:, :-1], bidirectional=False),
                          "CAUSAL", torch.zeros_like(tokens, dtype=torch.bool))


def mntp_batch(tokens, document_ids, selected, *, vocab_size, special_max=34, mask_id=13):
    eligible = eligible_mntp(tokens, document_ids, vocab_size=vocab_size,
                             special_max=special_max, mask_id=mask_id)
    if (not isinstance(selected, torch.Tensor) or selected.dtype is not torch.bool
            or selected.shape != tokens.shape or selected.device != tokens.device
            or bool((selected & ~eligible).any())):
        raise ValueError("selected positions must be boolean, same shape/device, and strictly eligible")
    selected = selected.detach().clone()
    inputs = tokens[:, :-1].clone()
    inputs.masked_fill_(selected[:, :-1], mask_id)
    targets = tokens[:, 1:].clone().masked_fill_(~selected[:, 1:], IGNORE_INDEX)
    return ObjectiveBatch(inputs, targets,
                          document_visibility(document_ids[:, :-1], bidirectional=True),
                          "MNTP_RESERVED_100_PERCENT", selected)


def uniform_mntp_selection(tokens, document_ids, *, vocab_size, probability,
                           generator, special_max=34, mask_id=13):
    """Independent uniform control; do not force a target or call it adaptive masking."""
    if (isinstance(probability, bool) or not isinstance(probability, (int, float))
            or not math.isfinite(probability) or not 0 < probability <= 1):
        raise ValueError("mask probability must be finite in (0,1]")
    eligible = eligible_mntp(tokens, document_ids, vocab_size=vocab_size,
                             special_max=special_max, mask_id=mask_id)
    draws = torch.rand(tokens.shape, device=tokens.device, generator=generator)
    return (draws < probability) & eligible


def objective_mean(logits, targets):
    if (logits.ndim != 3 or logits.shape[:2] != targets.shape
            or targets.dtype != torch.long or targets.device != logits.device):
        raise ValueError("objective logits/targets must match [B,T,V] and [B,T]")
    count = int((targets != IGNORE_INDEX).sum().item())
    if count < 1:
        raise ValueError("objective has zero supervised targets")
    loss = F.cross_entropy(logits.float().reshape(-1, logits.shape[-1]),
                           targets.reshape(-1), ignore_index=IGNORE_INDEX, reduction="sum") / count
    return loss, count


def hybrid_backward(model, causal, masked, *, masked_weight):
    """Accumulate separate target means with each fresh forward/backward paired.

    TinyLM refreshes STE weights on each forward. Retaining a first checkpointed
    graph while a second forward replaces those weights is unsafe. Backpropagate
    immediately per branch; never clear accumulated gradients or step an optimizer.
    Caller owns discarding partial gradients on error. Returned losses are detached.
    """
    if (isinstance(masked_weight, bool) or not isinstance(masked_weight, (int, float))
            or not math.isfinite(masked_weight) or not 0 <= masked_weight <= 1):
        raise ValueError("masked_weight must be finite in [0,1]")
    branches = ((1 - masked_weight, causal, "causal"), (masked_weight, masked, "masked"))
    for weight, batch, name in branches:
        if weight > 0 and (batch is None or batch.target_count == 0):
            raise ValueError(name + " branch needs nonempty targets before any model call")
    total = 0.0
    counts = dict(executed_input_tokens=0, supervised_targets=0, model_forwards=0,
                  causal_targets=0, masked_targets=0, normalization="SEPARATE_OBJECTIVE_MEANS")
    for weight, batch, name in branches:
        if weight == 0:
            continue
        logits = model(batch.inputs, attention_mask=batch.attention_mask)
        loss, count = objective_mean(logits, batch.targets)
        weighted = weight * loss
        weighted.backward()
        detached_loss = float(loss.detach().item())
        total += weight * detached_loss
        counts[name + "_mean_loss"] = detached_loss
        counts[name + "_targets"] = count
        counts["executed_input_tokens"] += batch.executed_input_tokens
        counts["supervised_targets"] += count
        counts["model_forwards"] += 1
        del logits, loss, weighted
    return total, counts
