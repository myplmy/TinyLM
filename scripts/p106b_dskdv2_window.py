"""Bounded feature-to-native-DSKD consumption; no model or optimizer is loaded.

The caller owns actual frame provenance, CE, backward/GradScaler and optimizer
transactions. An error invalidates the whole update and all partial gradients.
Only source/accounting completion is reported, never full training resume.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import math
import re

import numpy as np
import torch

from scripts import p106b_dskdv2_bridge as bridge
from scripts.p106b_feature_window import FeatureWindow


@dataclass(frozen=True)
class StudentFrame:
    row_id: str
    semantic_root_id: str
    record_sha256: str
    hidden: torch.Tensor
    targets: torch.Tensor
    owners: torch.Tensor


def _integer(value, label, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError('DSKD window invalid integer: ' + label)


class NativeFeatureUpdate:
    """Consume one complete admitted window as one KD accumulation group.

    One caller-supplied original student frame is retained until that row ends.
    All teacher calls use the original-position fixed frame and full vocabulary.
    The feature reader, caller and allocator have separate memory ownership.
    This object performs no step, checkpoint save or model/state restoration.
    """
    def __init__(self, reader, *, window_sha256, global_positions, student_width,
                 teacher_width, student_vocab, teacher_vocab, mapping, mapping_modes,
                 chunk_positions=8, max_teacher_frame_values=260000000, kd_rate=1.):
        if not isinstance(reader, FeatureWindow) or window_sha256 != reader.window_sha256:
            raise ValueError('DSKD window exact FeatureWindow identity required')
        for name, value in dict(global_positions=global_positions, student_width=student_width,
                teacher_width=teacher_width, student_vocab=student_vocab, teacher_vocab=teacher_vocab,
                chunk_positions=chunk_positions, max_teacher_frame_values=max_teacher_frame_values).items():
            _integer(value, name, 2 if name.endswith('_vocab') else 1)
        if (type(kd_rate) not in (int, float) or not math.isfinite(kd_rate) or kd_rate < 0
                or teacher_width * teacher_vocab > max_teacher_frame_values):
            raise ValueError('DSKD window finite nonnegative rate and full-frame output quota required')
        if (not isinstance(mapping, (list, tuple)) or not isinstance(mapping_modes, (list, tuple))
                or len(mapping) != teacher_vocab or len(mapping_modes) != teacher_vocab):
            raise ValueError('DSKD window complete declared full-vocabulary mapping required')
        state = reader.state_dict()
        contract = reader.contract
        if state['next_position'] or state['committed_batches']:
            raise ValueError('DSKD window fresh whole-update source required; cursor alone cannot restore gradients')
        if global_positions != contract['selected_positions']:
            raise ValueError('DSKD window denominator must equal complete selected-position count')
        self.reader = reader
        self.window_sha256 = window_sha256
        self.global_positions = global_positions
        self.student_width, self.teacher_width = student_width, teacher_width
        self.student_vocab, self.teacher_vocab = student_vocab, teacher_vocab
        self.chunk_positions, self.kd_rate = chunk_positions, float(kd_rate)
        self._metadata, self._expected, self._row_ends = {}, [], {}
        for row in contract['records']:
            for name in ('record_sha256', 'source_row_sha256'):
                if not isinstance(row.get(name), str) or re.fullmatch('[0-9A-F]{64}', row[name]) is None:
                    raise ValueError('DSKD window explicit declared record/source identity required')
            _integer(row.get('student_tokens'), 'student_tokens')
            if row['student_tokens'] > student_width or row['teacher_tokens'] > teacher_width:
                raise ValueError('DSKD window original row must fit explicit student/teacher frames')
            teacher_seen, student_seen = set(), set()
            for position in row['positions']:
                for name in ('student_predictor_raw_index', 'teacher_predictor_raw_index',
                             'student_target_raw_index', 'teacher_target_raw_index',
                             'student_target_id', 'teacher_native_argmax', 'mapped_student_argmax'):
                    _integer(position.get(name), name, 0)
                _integer(position.get('owner'), 'owner')
                si, ti = position['student_predictor_raw_index'], position['teacher_predictor_raw_index']
                native_id = position['teacher_native_argmax']
                mapped = position['mapped_student_argmax']
                if (position.get('accepted') is not True or position.get('lookahead_bytes') != 0
                        or type(position.get('lookahead_bytes')) is not int
                        or si >= row['student_tokens'] or ti >= row['teacher_tokens']
                        or position['student_target_raw_index'] != si + 1
                        or position['teacher_target_raw_index'] != ti + 1
                        or position['student_target_id'] >= student_vocab or native_id >= teacher_vocab
                        or not 0 <= mapped < student_vocab
                        or type(position.get('mapping_mode')) is not int
                        or position['mapping_mode'] not in (1, 3)
                        or type(mapping[native_id]) is not int or mapping[native_id] != mapped
                        or type(mapping_modes[native_id]) is not int
                        or mapping_modes[native_id] != position['mapping_mode']
                        or si in student_seen or ti in teacher_seen):
                    raise ValueError('DSKD window exact unique causal positions, mapped top1 and owner required')
                student_seen.add(si); teacher_seen.add(ti)
                self._expected.append((row['row_id'], copy.deepcopy(position)))
            self._metadata[row['row_id']] = {k:copy.deepcopy(v) for k,v in row.items() if k != 'positions'}
            self._row_ends[row['row_id']] = len(self._expected)
        self._hidden_width = contract['options']['hidden_width']
        self._active_frame = self._frame_versions = self._parameters = self._parameter_versions = None
        self._broken = self._closed = False
        self._seen = self._batches = self._callbacks = self._frames = 0
        self._max_chunk = 0
        self._sums = {key:0. for key in ('student_kd_sum', 'teacher_kd_sum', 'projector_ce_sum', 'total_sum')}

    def _parameters_for(self, up, embedding, teacher_head, t2s, s2t):
        values = (up, embedding, teacher_head, t2s, s2t)
        if self._parameters is not None:
            if any(a is not b for a,b in zip(values, self._parameters)):
                raise ValueError('DSKD window fixed parameter objects required throughout the update')
            if tuple(t._version for t in values) != self._parameter_versions:
                raise ValueError('DSKD window parameter changed before complete update')
            return values
        if any(not isinstance(t, torch.Tensor) or t.ndim != 2
               or t.dtype not in (torch.float16, torch.bfloat16, torch.float32, torch.float64)
               or not bool(torch.isfinite(t).all()) for t in values):
            raise ValueError('DSKD window finite floating matrices required')
        # Reusing a trainable nonleaf conversion across rows can retain a shared
        # graph already freed by a prior row's final backward. Callers must pass
        # leaf master matrices; native_sums owns per-call precision conversions.
        if any(t.requires_grad and not t.is_leaf for t in (up, embedding, t2s)):
            raise ValueError('DSKD window reusable trainable head/projector inputs must be leaf master matrices')
        ds, rank = up.shape
        if (min(ds, rank) < 1 or embedding.shape != (self.student_vocab, rank)
                or teacher_head.shape != (self.teacher_vocab, self._hidden_width)
                or t2s.shape != (self._hidden_width, ds) or s2t.shape != (ds, self._hidden_width)
                or len({t.device for t in values}) != 1):
            raise ValueError('DSKD window declared full vocabularies and projector geometry required')
        self._parameters = values
        self._parameter_versions = tuple(t._version for t in values)
        return values

    def _frame_for(self, row_id, provider, ds, device):
        if self._active_frame is None:
            frame = provider(copy.deepcopy(self._metadata[row_id]))
            metadata = self._metadata[row_id]
            if (not isinstance(frame, StudentFrame) or frame.row_id != row_id
                    or frame.semantic_root_id != metadata['semantic_root_id']
                    or frame.record_sha256 != metadata['record_sha256']
                    or not isinstance(frame.hidden, torch.Tensor)
                    or frame.hidden.shape != (self.student_width, ds)
                    or frame.hidden.device != device
                    or frame.hidden.dtype not in (torch.float16, torch.bfloat16, torch.float32, torch.float64)
                    or not bool(torch.isfinite(frame.hidden).all())):
                raise ValueError('DSKD window exact original student frame and declared record identity required')
            for value in (frame.targets, frame.owners):
                if (not isinstance(value, torch.Tensor) or value.dtype != torch.long
                        or value.shape != (self.student_width,) or value.device != device):
                    raise ValueError('DSKD window original full-frame labels and owners required')
            self._active_frame = frame
            self._frame_versions = tuple(t._version for t in (frame.hidden, frame.targets, frame.owners))
            self._frames += 1
        frame = self._active_frame
        if (frame.row_id != row_id
                or tuple(t._version for t in (frame.hidden, frame.targets, frame.owners)) != self._frame_versions):
            raise ValueError('DSKD window original row frame changed before its final backward')
        return frame

    def consume_next(self, provider, backward, *, up, embedding, teacher_head, t2s, s2t):
        if self._broken or self._closed:
            raise RuntimeError('DSKD window update is closed or failed; discard partial gradients')
        if self._seen == self.global_positions:
            raise StopIteration('DSKD window whole source consumed; close accounting separately')
        if not callable(provider) or not callable(backward):
            raise ValueError('DSKD window explicit frame and backward callbacks required')
        try:
            values = self._parameters_for(up, embedding, teacher_head, t2s, s2t)
            batch = self.reader.prepare()
            n = len(batch.values)
            if (n < 1 or batch.start != self._seen or batch.stop != self._seen+n
                    or batch.values.shape != (n, self._hidden_width) or batch.values.dtype != np.float32
                    or batch.stop > self.global_positions
                    or len(batch.row_ids) != n or len(batch.positions) != n
                    or list(zip(batch.row_ids, batch.positions)) != self._expected[batch.start:batch.stop]
                    or batch.rows != {name:self._metadata[name] for name in set(batch.row_ids)}):
                raise ValueError('DSKD window prepared batch differs from original ordered window')
            local = 0
            while local < n:
                row_id = batch.row_ids[local]
                stop = local + 1
                while stop < n and batch.row_ids[stop] == row_id and stop-local < self.chunk_positions:
                    stop += 1
                positions = batch.positions[local:stop]
                frame = self._frame_for(row_id, provider, up.shape[0], up.device)
                for position in positions:
                    si = position['student_predictor_raw_index']
                    if (int(frame.targets[si]) != position['student_target_id']
                            or int(frame.owners[si]) != position['owner']):
                        raise ValueError('DSKD window original CE target or owner differs')
                sj = torch.tensor([p['student_predictor_raw_index'] for p in positions], device=up.device)
                tj = torch.tensor([p['teacher_predictor_raw_index'] for p in positions], device=up.device)
                labels = torch.tensor([p['mapped_student_argmax'] for p in positions], device=up.device)
                dtype = torch.float64 if all(t.dtype == torch.float64 for t in values+(frame.hidden,)) else torch.float32
                ht = torch.tensor(batch.values[local:stop], device=up.device, dtype=dtype)
                terms = bridge.native_sums(frame.hidden.index_select(0, sj), ht, *values, labels,
                                           teacher_indices=tj, teacher_width=self.teacher_width)
                if (terms['positions'] != stop-local
                        or any(not bool(torch.isfinite(terms[key])) for key in self._sums)):
                    raise ValueError('DSKD window finite original loss sums and position count required')
                context = dict(row_id=row_id, semantic_root_id=frame.semantic_root_id,
                    global_start=batch.start+local, global_stop=batch.start+stop,
                    row_complete=batch.start+stop == self._row_ends[row_id],
                    batch_complete=stop == n, global_positions=self.global_positions,
                    student_indices=tuple(int(i) for i in sj), teacher_indices=tuple(int(i) for i in tj))
                backward(self.kd_rate*terms['total_sum']/self.global_positions, context)
                if tuple(t._version for t in values) != self._parameter_versions:
                    raise ValueError('DSKD window backward callback changed parameters before update closure')
                for key in self._sums:
                    self._sums[key] += float(terms[key].detach())
                self._seen += stop-local; self._callbacks += 1
                self._max_chunk = max(self._max_chunk, stop-local)
                if context['row_complete']:
                    self._active_frame = self._frame_versions = None
                local = stop
                del frame, terms, ht, labels, sj, tj
            self.reader.finish()
            self._batches += 1
            return dict(committed_source_batches=self._batches, positions_consumed=self._seen)
        except BaseException:
            self._broken = True
            self._active_frame = self._frame_versions = None
            raise

    def close_accounting(self):
        if (self._broken or self._seen != self.global_positions or self._active_frame is not None
                or self.reader.state_dict()['next_position'] != self.global_positions
                or self._parameters is None
                or tuple(t._version for t in self._parameters) != self._parameter_versions):
            raise RuntimeError('DSKD window whole healthy update required; discard all partial gradients on failure')
        self._closed = True
        return dict(schema='DSKD_FEATURE_WINDOW_ACCOUNTING_V1', window_sha256=self.window_sha256,
            positions=self._seen, global_positions=self.global_positions, source_batches=self._batches,
            frame_provider_calls=self._frames, backward_callback_calls=self._callbacks,
            maximum_chunk_positions=self._max_chunk, full_teacher_frame_values=self.teacher_width*self.teacher_vocab,
            sums=copy.deepcopy(self._sums), kd_rate=self.kd_rate,
            normalized_loss=self.kd_rate*self._sums['total_sum']/self.global_positions,
            teacher_head_policy='ORIGINAL_POSITION_FIXED_FRAME_FULL_VOCABULARY',
            actual_model_provenance='CALLER_OWNED_NOT_CERTIFIED',
            optimizer_steps=0, full_training_checkpoint_or_resume=False,
            source_state=self.reader.state_dict())
