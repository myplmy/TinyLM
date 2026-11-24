"""Same short rows and source RNG, regrouped to preserve microbatch tokens.

This is a separate experimental layout. Source cursor resume is not
model/optimizer/Torch RNG resume; that state belongs to the trainer bridge.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import torch

from .context_curriculum import ContextCursor, ContextPlan, ContextUpdate, split_update

SCHEMA = "P013_MICRO_TOKENS_CONSTANT_CURSOR_V1"
LAYOUT = "MICRO_TOKENS_CONSTANT"
RESUME_SCOPE = "SOURCE_RNG_AND_ACCOUNTING_ONLY_NOT_FULL_TRAINING"


def parse_context_plan(text, *, micro_bs, accum, seq, steps):
    if type(steps) is not int or steps < 1:
        raise ValueError("positive integer training steps required")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("explicit comma-separated end_update:length stages required")
    stages = []
    for part in text.split(","):
        pieces = part.strip().split(":")
        if len(pieces) != 2 or any(not value.strip().isascii() or not value.strip().isdigit()
                                   for value in pieces):
            raise ValueError("context stages require positive integer end_update:length")
        stages.append(tuple(int(value.strip()) for value in pieces))
    plan = ContextPlan(tuple(stages), micro_bs=micro_bs, base_accum=accum, full_length=seq)
    if plan.steps != steps:
        raise ValueError("context final end_update must equal the full training steps")
    return plan


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest().upper()


def _regroup(update, plan):
    parts = plan.full_length // update.length
    if len(update.batches) != plan.base_accum * parts:
        raise ValueError("complete original split update required")
    batches = []
    copied_bytes = 0
    for draw in range(plan.base_accum):
        original = update.batches[draw * parts:(draw + 1) * parts]
        if parts == 1:
            pair = original[0]
        else:
            pair = tuple(torch.cat([batch[side] for batch in original], dim=0)
                         for side in (0, 1))
            copied_bytes += sum(t.numel() * t.element_size() for t in pair)
        expected = (plan.micro_bs * parts, update.length)
        if pair[0].shape != expected or pair[1].shape != expected:
            raise ValueError("same-token regrouped shape differs")
        batches.append(pair)
    total = sum(y.numel() for _, y in batches)
    if total != plan.tokens_per_update:
        raise ValueError("regrouping lost original targets")
    accounting = dict(update.accounting, layout=LAYOUT,
                      reference_split_micro_batches=len(update.batches),
                      active_micro_batches=len(batches), active_micro_bs=plan.micro_bs * parts,
                      active_micro_tokens=plan.micro_bs * plan.full_length,
                      additional_regroup_copy_bytes=copied_bytes,
                      old_split_and_snapshot_cost_not_omitted=True)
    return ContextUpdate(update.update, update.length, tuple(batches), update.origins, accounting)


def regroup_update(source_batches, plan, length, *, update=0):
    """Use the unchanged source/shift/mask validator before changing layout."""
    if not isinstance(plan, ContextPlan):
        raise ValueError("explicit context plan required")
    original = split_update(source_batches, plan, length, update=update)
    return _regroup(original, plan)


def layout_summary(plan):
    if not isinstance(plan, ContextPlan):
        raise ValueError("explicit context plan required")
    rows = []
    for original in plan.summary()["stages"]:
        row = dict(original)
        row.update(reference_split_accum=original["active_accum"],
                   active_accum=plan.base_accum,
                   active_micro_bs=plan.micro_bs * plan.full_length // row["train_length"],
                   active_micro_tokens=plan.micro_bs * plan.full_length)
        rows.append(row)
    return dict(schema=SCHEMA, layout=LAYOUT, original_plan=plan.contract(), stages=rows,
                quality_claim=False, measured_model_speed=False)


class MicroTokensCursor:
    def __init__(self, plan, sampler, *, source_sha256):
        self.plan = plan
        self._fixed = ContextCursor(plan, sampler, source_sha256=source_sha256)
        self._pending = None

    @property
    def next_update(self):
        return self._fixed.next_update

    @property
    def optimizer_updates(self):
        return self._fixed.optimizer_updates

    def prepare(self):
        if self._pending is not None:
            raise RuntimeError("finish the complete current update first")
        original = self._fixed.prepare()
        self._pending = _regroup(original, self.plan)
        return self._pending

    def finish(self, *, optimizer_applied):
        if self._pending is None:
            raise RuntimeError("one complete prepared update required")
        self._fixed.finish(optimizer_applied=optimizer_applied)
        row = dict(self._pending.accounting, update=self._pending.update,
                   train_length=self._pending.length, optimizer_applied=optimizer_applied)
        self._pending = None
        return row

    def state_dict(self):
        if self._pending is not None:
            raise RuntimeError("mid-update layout state is not resumable")
        result = dict(schema=SCHEMA, layout=LAYOUT, cursor=self._fixed.state_dict(),
                      resume_scope=RESUME_SCOPE)
        result["state_sha256"] = _sha(result)
        return result

    def load_state_dict(self, value):
        if self._pending is not None or self.next_update:
            raise RuntimeError("restore requires a fresh layout cursor")
        value = deepcopy(value)
        if set(value) != {"schema", "layout", "cursor", "resume_scope", "state_sha256"}:
            raise ValueError("explicit micro-token layout schema required")
        checksum = value.pop("state_sha256")
        if (checksum != _sha(value) or value["schema"] != SCHEMA
                or value["layout"] != LAYOUT or value["resume_scope"] != RESUME_SCOPE):
            raise ValueError("micro-token layout identity differs")
        self._fixed.load_state_dict(value["cursor"])
