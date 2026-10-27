"""Experimental NTP window splitting; production trainer defaults are untouched.

Always draw the same full-length windows. Split x AND pre-shifted y together,
preserving every original target once. Context/position resets are intentional;
this is not equivalent to fixed-length gradients, padding crop, or unique-data
epochs. Cursor state restores source NumPy RNG at complete-update boundaries,
not model/optimizer/Torch RNG or a full training checkpoint.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re

import numpy as np
import torch

SCHEMA = 'P013_NTP_WINDOW_CURRICULUM_CURSOR_V1'


def _integer(value, label, *, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError('invalid curriculum integer: '+label)
    return value


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest().upper()


@dataclass(frozen=True)
class ContextPlan:
    # end_update is exclusive. Length changes never change source draws/update.
    stages: tuple
    micro_bs: int = 8
    base_accum: int = 16
    full_length: int = 1024

    def __post_init__(self):
        for key in ('micro_bs', 'base_accum', 'full_length'):
            _integer(getattr(self, key), key)
        if type(self.stages) is not tuple or not self.stages:
            raise ValueError('explicit immutable nonempty curriculum stages required')
        previous_end = previous_length = 0
        for row in self.stages:
            if type(row) is not tuple or len(row) != 2:
                raise ValueError('stage needs (exclusive integer end_update, length)')
            end, length = row
            _integer(end, 'end_update'); _integer(length, 'length')
            if (end <= previous_end or length < previous_length
                    or length > self.full_length or self.full_length % length):
                raise ValueError('strict stage ends and nondecreasing divisor lengths required')
            previous_end, previous_length = end, length
        if previous_length != self.full_length:
            raise ValueError('last stage must use full validation/model length')

    @property
    def steps(self):
        return self.stages[-1][0]

    @property
    def tokens_per_update(self):
        return self.micro_bs*self.base_accum*self.full_length

    def length_at(self, update):
        _integer(update, 'next_update', minimum=0)
        if update >= self.steps:
            raise StopIteration('curriculum complete')
        return next(length for end, length in self.stages if update < end)

    def contract(self):
        return dict(stages=[list(row) for row in self.stages], micro_bs=self.micro_bs,
            base_accum=self.base_accum, full_length=self.full_length,
            tokens_per_update=self.tokens_per_update, steps=self.steps,
            draw_tokens=self.steps*self.tokens_per_update,
            sampler='ORIGINAL_FULL_WINDOWS_WITH_REPLACEMENT', objective='NTP_ONLY',
            unique_epoch_claim=False, validation_length=self.full_length)

    def summary(self):
        previous = 0; rows = []
        for end, length in self.stages:
            count = end-previous
            rows.append(dict(start_update=previous, end_update=end, updates=count, train_length=length,
                active_accum=self.base_accum*(self.full_length//length),
                source_calls=count*self.base_accum, draw_tokens=count*self.tokens_per_update,
                ntp_targets=count*self.tokens_per_update))
            previous = end
        return dict(contract=self.contract(), stages=rows)


@dataclass(frozen=True)
class ContextUpdate:
    update: int
    length: int
    batches: tuple
    # Each output row: source microbatch, source row, start, exclusive end.
    origins: tuple
    accounting: dict


def snapshot_batches(sampler, count):
    """Preserve each draw before an otherwise-valid sampler reuses scratch."""
    _integer(count, 'source_calls')
    source=[]
    for _ in range(count):
        pair=sampler()
        if not isinstance(pair,(tuple,list)) or len(pair)!=2 or not all(isinstance(t,torch.Tensor) for t in pair):
            raise ValueError('two source tensors required before snapshot')
        source.append(tuple(t.clone() for t in pair))
    return tuple(source)


def split_update(source_batches, plan, length, *, update=0):
    """No labels are reconstructed from cropped x; chunk-final y is retained."""
    _integer(length, 'length')
    if length > plan.full_length or plan.full_length % length:
        raise ValueError('active length must divide original full window')
    if len(source_batches) != plan.base_accum:
        raise ValueError('exact full-window source call count required')
    batches, origins = [], []
    parts = plan.full_length//length
    for draw, pair in enumerate(source_batches):
        if len(pair) != 2:
            raise ValueError('NTP x/y pairs only; SFT/KD/mask payloads are unsupported')
        x, y = pair
        if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)
                and x.shape == y.shape == (plan.micro_bs, plan.full_length)
                and x.dtype == y.dtype == torch.long and x.device == y.device):
            raise ValueError('complete original integer full windows required')
        if (bool((x < 0).any()) or bool((y < 0).any())
                or not torch.equal(x[:, 1:], y[:, :-1])):
            raise ValueError('unmasked correctly shifted NTP targets required')
        if parts == 1:
            batches.append((x, y))
        else:
            # Noncontiguous Loader views may allocate here; include this in cost.
            xx = x.reshape(plan.micro_bs, parts, length).reshape(-1, length)
            yy = y.reshape(plan.micro_bs, parts, length).reshape(-1, length)
            batches.extend((xx[i:i+plan.micro_bs], yy[i:i+plan.micro_bs])
                           for i in range(0, plan.micro_bs*parts, plan.micro_bs))
        origins.extend((draw, row, start, start+length)
                       for row in range(plan.micro_bs) for start in range(0, plan.full_length, length))
    total = sum(y.numel() for _, y in batches)
    if total != plan.tokens_per_update or len(batches) != plan.base_accum*parts:
        raise RuntimeError('curriculum lost target positions')
    accounting = dict(source_calls=plan.base_accum, source_windows=plan.micro_bs*plan.base_accum,
        source_input_tokens=plan.tokens_per_update, executed_input_tokens=total, ntp_targets=total,
        active_micro_batches=len(batches), origin_ranges_sha256=_sha(origins),
        added_context_resets=plan.micro_bs*plan.base_accum*(parts-1),
        target_positions_preserved=True, source_documents_not_inferred=True,
        full_training_or_quality_claim=False)
    return ContextUpdate(update, length, tuple(batches), tuple(origins), accounting)


class ContextCursor:
    """Accounting/RNG only. Caller owns forward/backward, skipped updates, rollback."""
    def __init__(self, plan, sampler, *, source_sha256):
        if not isinstance(plan, ContextPlan) or not re.fullmatch('[0-9A-F]{64}', source_sha256):
            raise ValueError('exact plan and explicit source identity required')
        if (getattr(sampler, 'bs', None) != plan.micro_bs
                or getattr(sampler, 'seq', None) != plan.full_length
                or not isinstance(getattr(sampler, 'rng', None), np.random.Generator)
                or not isinstance(sampler.rng.bit_generator, np.random.PCG64)):
            raise ValueError('existing full-window PCG64 sampler interface required')
        self.plan, self.sampler, self.source_sha256 = plan, sampler, source_sha256
        self.next_update = self.optimizer_updates = 0
        self._pending = None
        self._broken = False

    def prepare(self):
        if self._broken or self._pending is not None:
            raise RuntimeError('finish current update or restore a complete checkpoint in a fresh cursor')
        length = self.plan.length_at(self.next_update)
        try:
            source = snapshot_batches(self.sampler,self.plan.base_accum)
            self._pending = split_update(source, self.plan, length, update=self.next_update)
            self._pending.accounting['source_snapshot_bytes'] = sum(t.numel()*t.element_size() for pair in source for t in pair)
        except BaseException:
            self._broken = True
            raise
        return self._pending

    def finish(self, *, optimizer_applied):
        if self._broken or self._pending is None or type(optimizer_applied) is not bool:
            raise RuntimeError('one complete prepared update and explicit optimizer outcome required')
        row = dict(self._pending.accounting, update=self.next_update, train_length=self._pending.length,
                   optimizer_applied=optimizer_applied)
        self.next_update += 1
        self.optimizer_updates += int(optimizer_applied)
        self._pending = None
        return row

    def state_dict(self):
        if self._broken or self._pending is not None:
            raise RuntimeError('mid-update or failed source state is not resumable')
        result = dict(schema=SCHEMA, plan=self.plan.contract(), source_sha256=self.source_sha256,
            next_update=self.next_update, optimizer_updates=self.optimizer_updates,
            source_calls=self.next_update*self.plan.base_accum,
            draw_tokens=self.next_update*self.plan.tokens_per_update,
            ntp_targets=self.next_update*self.plan.tokens_per_update,
            rng=deepcopy(self.sampler.rng.bit_generator.state),
            resume_scope='SOURCE_RNG_AND_ACCOUNTING_ONLY_NOT_FULL_TRAINING')
        result['state_sha256'] = _sha(result)
        return result

    def load_state_dict(self, value):
        if self._broken or self._pending is not None or self.next_update:
            raise RuntimeError('restore is allowed only in a fresh cursor')
        value = deepcopy(value)
        checksum = value.pop('state_sha256', None)
        if checksum != _sha(value) or value.get('schema') != SCHEMA:
            raise ValueError('cursor state identity changed')
        if value.get('plan') != self.plan.contract() or value.get('source_sha256') != self.source_sha256:
            raise ValueError('plan/source mismatch; old checkpoint cannot silently initialize curriculum')
        nxt, applied = value.get('next_update'), value.get('optimizer_updates')
        _integer(nxt, 'next_update', minimum=0); _integer(applied, 'optimizer_updates', minimum=0)
        if not (applied <= nxt <= self.plan.steps):
            raise ValueError('invalid draw/optimizer update counters')
        if (value.get('source_calls') != nxt*self.plan.base_accum
                or value.get('draw_tokens') != nxt*self.plan.tokens_per_update
                or value.get('ntp_targets') != nxt*self.plan.tokens_per_update
                or value.get('resume_scope') != 'SOURCE_RNG_AND_ACCOUNTING_ONLY_NOT_FULL_TRAINING'):
            raise ValueError('cursor accounting is inconsistent')
        # Validate on a disposable generator before mutating the caller's RNG.
        probe = np.random.Generator(np.random.PCG64(0))
        probe.bit_generator.state = value['rng']
        self.sampler.rng.bit_generator.state = deepcopy(probe.bit_generator.state)
        self.next_update, self.optimizer_updates = nxt, applied
