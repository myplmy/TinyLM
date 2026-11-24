"""Document-isolated context regrouping for the existing P013/P107 objectives."""

from contextlib import nullcontext
from dataclasses import dataclass

import torch
from torch.nn import functional as F

from .context_curriculum import ContextPlan
from .hybrid_mntp import IGNORE_INDEX, ObjectiveBatch, _full_inputs, causal_batch


@dataclass(frozen=True)
class DocumentContextUpdate:
    length: int
    batches: tuple[ObjectiveBatch, ...]
    input_slots: int
    target_count: int
    excluded_targets: int
    # Valid targets at the last input position of each regrouped chunk.
    retained_chunk_final_targets: int


def regroup_document_context(source_batches, plan, length, *, vocab_size):
    """Regroup explicit token/doc pairs while retaining the original target positions.

    Source rows contain full_length + 1 tokens and document IDs. Each chunk
    receives its original immediate continuation for labels only. Attention
    stays within the chunk and the originating document.
    """
    if (not isinstance(plan, ContextPlan) or type(length) is not int or length < 2
            or length > plan.full_length or plan.full_length % length
            or len(source_batches) != plan.base_accum):
        raise ValueError("A complete plan and a supported dividing context length are required")
    pieces = plan.full_length // length
    shape = (plan.micro_bs, plan.full_length + 1)
    result = []
    counts = retained = slots = 0
    for tokens, docs in source_batches:
        if (not isinstance(tokens, torch.Tensor) or not isinstance(docs, torch.Tensor)
                or tokens.shape != shape or docs.shape != shape):
            raise ValueError("Each original draw needs tokens and document IDs including its last target")
        allowed_targets = _full_inputs(tokens, docs, vocab_size)

        def crop(rows):
            initial = rows[:, :-1].reshape(plan.micro_bs, pieces, length)
            last_target = rows[:,length::length].unsqueeze(-1)
            return torch.cat((initial,last_target), dim=-1).reshape(plan.micro_bs*pieces,length+1)

        batch = causal_batch(crop(tokens), crop(docs), vocab_size=vocab_size)
        expected = tokens[:, 1:].masked_fill(~allowed_targets, IGNORE_INDEX)
        if not torch.equal(batch.targets, expected.reshape_as(batch.targets)):
            raise RuntimeError("Original document target identity was lost during regrouping")
        counts += batch.target_count
        retained += int(batch.targets[:, -1].ne(IGNORE_INDEX).sum())
        slots += batch.executed_input_tokens
        result.append(batch)
    if slots != plan.tokens_per_update or not counts:
        raise ValueError("The exact input budget and nonempty global document target denominator are required")
    return DocumentContextUpdate(length, tuple(result), slots, counts, slots-counts, retained)


def backward_document_context(model, update, *, autocast_dtype=None):
    """Accumulate causal gradients for a prepared update. The caller owns the optimizer."""
    if not isinstance(update, DocumentContextUpdate) or not model.training:
        raise ValueError("A prepared document update and a model in training mode are required")
    counts = tuple(batch.target_count for batch in update.batches)
    if (not update.target_count or sum(counts) != update.target_count
            or any(batch.objective != "CAUSAL" for batch in update.batches)):
        raise ValueError("A causal update must have its complete, nonempty target denominator")
    device = next(model.parameters()).device
    total_loss = torch.zeros((), device=device, dtype=torch.float32)
    for batch, count in zip(update.batches, counts, strict=True):
        if not count:
            continue
        loss = causal_loss_sum(model, batch, device, autocast_dtype=autocast_dtype) / update.target_count
        loss.backward()
        total_loss += loss.detach()
        del loss
    return float(total_loss)


def causal_loss_sum(model, batch, device, *, autocast_dtype=None):
    """Sum the supervised document CE in FP32 for a caller-owned denominator."""
    device = torch.device(device)
    autocast = nullcontext() if autocast_dtype is None else torch.autocast(device.type, dtype=autocast_dtype)
    inputs, targets, mask = (value.to(device) for value in (batch.inputs, batch.targets, batch.attention_mask))
    with autocast:
        logits = model(inputs, attention_mask=mask, allow_fixed_g4_r2=True)
    return F.cross_entropy(logits.flatten(0, 1).float(), targets.flatten(),
                           ignore_index=IGNORE_INDEX, reduction="sum")
