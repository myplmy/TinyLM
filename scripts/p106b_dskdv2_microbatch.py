"""Single-use causal microbatch frames for an unchanged row CE/KD consumer.

No model, tokenizer, dataset, checkpoint or optimizer is constructed or loaded.
Only fresh tiny CPU fixtures have exercised this adapter; actual Native
compatibility/cost and complete training/checkpoint ownership are not certified.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re

import torch

from scripts.p106b_dskdv2_training import CEKDGroup
from scripts.p106b_dskdv2_window import StudentFrame
from tinylm.train.mtp_sft import Record, pad_records


SCHEMA = 'P106B_CAUSAL_MICROBATCH_FRAME_ADAPTER_V1'
SHA = re.compile('[0-9A-F]{64}')


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest().upper()


def _integer(value, label, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('microbatch bounded integer required: ' + label)


class CausalMicrobatchFrames:
    """Preserve one fixed-size forward through its final real row/chunk.

    Consume only once, through consume(group, backward). The caller owns actual
    backward/optimizer/source transactions, model/private RNG and provenance.
    Failure drops this object's references, not partial gradients or model state.
    No provider checkpoint/resume or automatic ScaledFeatureTrainer hookup.
    """
    def __init__(self, model, ce_rows, packed_students, *, student_width,
                 batch_size, pad_id, autocast_dtype=None, max_hidden_values=33554432):
        _integer(student_width, 'student_width', 2, 4096)
        _integer(batch_size, 'batch_size', 1, 128)
        _integer(max_hidden_values, 'max_hidden_values', 1, 33554432)
        if (not isinstance(model, torch.nn.Module) or not model.training
                or not callable(getattr(model, '_emb_w', None))
                or not callable(getattr(model, '_emb_up_w', None))
                or not callable(getattr(model, '_head_logits', None))
                or autocast_dtype not in (None, torch.bfloat16)):
            raise ValueError('explicit training factored-head model and autocast policy required')
        self.model = model
        self.embedding, self.up = model._emb_w(), model._emb_up_w()
        if (any(not isinstance(p, torch.Tensor) or p.ndim != 2 or not p.requires_grad
                or not p.is_leaf or p.dtype not in (torch.float32, torch.float64)
                or p.layout != torch.strided for p in (self.embedding, self.up))
                or self.embedding.shape[1] != self.up.shape[1]
                or self.embedding.device != self.up.device):
            raise ValueError('same-device original floating factored leaf masters required')
        self.device = self.up.device
        self.hidden_width, self.vocab = self.up.shape[0], len(self.embedding)
        _integer(pad_id, 'pad_id', 0, self.vocab - 1)
        if batch_size * student_width * self.hidden_width > max_hidden_values:
            raise ValueError('microbatch hidden-value quota exceeded')
        if (type(ce_rows) not in (list, tuple) or not 0 < len(ce_rows) <= 1024
                or type(packed_students) not in (list, tuple) or len(packed_students) != len(ce_rows)):
            raise ValueError('exact bounded ordered original CE rows and packed students required')
        raw = _canonical(ce_rows)
        if len(raw) > 1024**2:
            raise ValueError('microbatch CE metadata quota exceeded')
        self._rows = json.loads(raw)
        self._packed = []
        seen = set()
        for row, packed in zip(self._rows, packed_students):
            if (type(row) is not dict or row.get('split') != 'train'
                    or any(type(row.get(k)) is not str or not 0 < len(row[k]) <= 256
                           for k in ('row_id', 'semantic_root_id'))
                    or row['row_id'] in seen
                    or any(type(row.get(k)) is not str or SHA.fullmatch(row[k]) is None
                           for k in ('record_sha256', 'source_row_sha256'))
                    or type(packed) is not dict or set(packed) != {'ids', 'labels', 'turn_ids'}):
                raise ValueError('exact original TRAIN identity and explicit raw packed token fields required')
            seen.add(row['row_id'])
            ids, labels, owners = (packed[k] for k in ('ids', 'labels', 'turn_ids'))
            if (any(type(values) not in (list, tuple) for values in (ids, labels, owners))
                    or not len(ids) == len(labels) == len(owners)
                    or type(row.get('student_tokens')) is not int
                    or len(ids) != row['student_tokens'] or not 2 <= len(ids) <= student_width
                    or labels[0] != -100 or owners[0] != 0):
                raise ValueError('student_tokens means raw tokens; exactly one causal shift and ignored first target required')
            for token, label, owner in zip(ids, labels, owners):
                if (type(token) is not int or not 0 <= token < self.vocab
                        or type(label) is not int or label not in (-100, token)
                        or type(owner) is not int or not 0 <= owner <= 2**31 - 1
                        or ((label == -100) != (owner == 0))):
                    raise ValueError('raw target identity, supervised owner or token vocabulary differs')
            targets = sum(value != -100 for value in labels[1:])
            if type(row.get('ce_targets')) is not int or not 0 < targets == row['ce_targets']:
                raise ValueError('original once-shifted CE population/count differs')
            detached = {k: tuple(packed[k]) for k in ('ids', 'labels', 'turn_ids')}
            self._packed.append(detached)
        self.student_width, self.batch_size, self.pad_id = student_width, batch_size, pad_id
        self.autocast_dtype = autocast_dtype
        self._parameters = tuple(model.parameters())
        self._parameter_versions = tuple(p._version for p in self._parameters)
        if any(p.device != self.device for p in self._parameters):
            raise ValueError('single-device original student parameters required')
        self._quant_modules = tuple(m for m in model.modules() if hasattr(m, '_wq'))
        self._contract = dict(schema=SCHEMA, rows=len(self._rows), row_metadata_sha256=_digest(self._rows),
            packed_token_values_sha256=_digest(self._packed),
            student_tokens_policy='RAW_TOKEN_COUNT_X_IDS_MINUS_LAST_Y_LABELS_FROM_ONE_V1',
            student_width=student_width, batch_size=batch_size, pad_id=pad_id,
            hidden_width=self.hidden_width, vocab=self.vocab, device=str(self.device),
            body_autocast=None if autocast_dtype is None else str(autocast_dtype),
            forward_policy='RETURN_HIDDEN_FULL_BATCH_NO_CACHE_NO_PAST_V1',
            backward_policy='RETAIN_SHARED_GRAPH_THROUGH_LAST_REAL_ROW_FINAL_CHUNK_V1',
            no_private_adapter_RNG=True, single_use=True, actual_model_provenance='CALLER_OWNED_NOT_CERTIFIED')
        self.phase = 'READY'
        self._provided = self._completed = self._backwards = 0
        self._retained = self._released = self._forwards = 0
        self._active = self._current = self._frame_pins = self._cache_pins = None
        self._microbatches = []
        self._check_binding()

    @property
    def contract(self):
        return copy.deepcopy(self._contract)

    def _check_binding(self):
        current = tuple(self.model.parameters())
        if (not self.model.training or not torch.is_grad_enabled()
                or len(current) != len(self._parameters)
                or any(a is not b for a, b in zip(current, self._parameters))
                or tuple(p._version for p in self._parameters) != self._parameter_versions
                or self.model._emb_w() is not self.embedding or self.model._emb_up_w() is not self.up
                or _digest(self._rows) != self._contract['row_metadata_sha256']
                or _digest(self._packed) != self._contract['packed_token_values_sha256']):
            raise ValueError('microbatch original mode/parameters/ordered token binding changed')
        if (getattr(self.model, '_quant_frozen', False)
                or getattr(self.model, '_p102a_quant_update', None) is not None
                or getattr(self.model, '_unpack_cache', False)):
            raise ValueError('frozen/update/unpack quant cache requires a different adapter contract')
        for module in self._quant_modules:
            if any(getattr(module, key, None) is not None for key in ('_i8', '_lut_codes', '_i8_cache')):
                raise ValueError('packed/deployment cache requires a different adapter contract')
        if self._active is not None:
            if any(t._version != version for t, version in self._frame_pins):
                raise ValueError('microbatch full hidden/input/target/owner frame was mutated')
            for module, tensor, version in self._cache_pins:
                if module._wq is not tensor or (tensor is not None and tensor._version != version):
                    raise ValueError('microbatch quant graph/cache changed before final backward')

    def _drop_owned_graph(self):
        self._active = self._current = self._frame_pins = self._cache_pins = None

    def _forward(self):
        if self._active is not None or self._provided != self._completed:
            raise RuntimeError('cannot replace a microbatch graph before all prior rows complete')
        start = self._provided
        stop = min(start + self.batch_size, len(self._rows))
        records = [Record(list(row['ids'][:-1]), list(row['labels'][1:]), list(row['turn_ids'][1:]))
                   for row in self._packed[start:stop]]
        x, y, owners = pad_records(records, self.pad_id, self.device,
            fixed_width=self.student_width, batch_size=self.batch_size)
        with torch.autocast(self.device.type, dtype=self.autocast_dtype or torch.bfloat16,
                            enabled=self.autocast_dtype is not None):
            hidden = self.model(x, return_hidden=True, use_cache=False, past_kv=None)
        if (not isinstance(hidden, torch.Tensor)
                or hidden.shape != (self.batch_size, self.student_width, self.hidden_width)
                or hidden.device != self.device or not hidden.requires_grad or hidden.grad_fn is None
                or hidden.dtype not in (torch.float16, torch.bfloat16, torch.float32, torch.float64)
                or not bool(torch.isfinite(hidden).all())):
            raise ValueError('exact finite differentiable fixed-size original hidden batch required')
        if (bool(y[stop-start:].ne(-100).any()) or bool(owners[stop-start:].ne(0).any())
                or bool(x[stop-start:].ne(self.pad_id).any())):
            raise ValueError('fixed final microbatch dummy rows must be zero-loss padding')
        self._active = (start, stop, x, y, owners, hidden)
        self._frame_pins = tuple((t, t._version) for t in (x, y, owners, hidden))
        self._cache_pins = tuple((m, m._wq, None if m._wq is None else m._wq._version)
                                 for m in self._quant_modules)
        self._forwards += 1
        self._microbatches.append(dict(index=self._forwards-1, start_row=start, stop_row=stop,
            real_rows=stop-start, dummy_rows=self.batch_size-(stop-start),
            shape=list(x.shape), row_ids=[r['row_id'] for r in self._rows[start:stop]],
            completed=False))
        self._check_binding()

    def _provide(self, metadata):
        self._check_binding()
        if (self.phase != 'RUNNING' or self._provided != self._completed
                or self._current is not None or self._provided >= len(self._rows)
                or metadata != self._rows[self._provided]):
            raise ValueError('one exact ordered original CE row frame required')
        if self._active is None:
            self._forward()
        start, stop, _x, y, owners, hidden = self._active
        if not start <= self._provided < stop:
            raise ValueError('original CE row outside its retained microbatch')
        local = self._provided-start
        row = self._rows[self._provided]
        self._current = row['row_id']
        self._provided += 1
        return StudentFrame(row['row_id'], row['semantic_root_id'], row['record_sha256'],
                            hidden[local], y[local], owners[local])

    def _backward(self, loss, context, backward):
        self._check_binding()
        if (self._active is None or self._current is None or type(context) is not dict
                or context.get('row_id') != self._current
                or type(context.get('row_complete')) is not bool
                or type(context.get('retain_graph')) is not bool
                or context['retain_graph'] == context['row_complete']
                or self._provided != self._completed+1):
            raise ValueError('exact original row/chunk completion and graph context required')
        start, stop, *_ = self._active
        last = self._completed+1 == stop
        retain = not (last and context['row_complete'])
        owned = dict(context, row_retain_graph=context['retain_graph'], retain_graph=retain,
            microbatch_index=self._forwards-1, microbatch_row_index=self._completed-start,
            microbatch_last_real_row=last, forward_batch_size=self.batch_size,
            forward_width=self.student_width)
        backward(loss, owned)
        self._check_binding()
        self._backwards += 1
        self._retained += int(retain)
        self._released += int(not retain)
        if context['row_complete']:
            self._completed += 1
            self._current = None
            if last:
                self._microbatches[-1]['completed'] = True
                self._drop_owned_graph()

    def consume(self, group, backward):
        if self.phase != 'READY':
            raise RuntimeError('microbatch adapter already consumed/failed; discard partial state')
        if (type(group) is not CEKDGroup or group.model is not self.model
                or group.student_width != self.student_width or group.up is not self.up
                or group.embedding is not self.embedding or group._rows != self._rows
                or group.phase != 'READY' or not callable(backward)):
            raise ValueError('exact unchanged fresh original CEKDGroup and backward required')
        self._check_binding()
        self.phase = 'RUNNING'
        try:
            report = group.consume(self._provide, lambda loss, context:self._backward(loss, context, backward))
            expected = math.ceil(len(self._rows)/self.batch_size)
            if (self._active is not None or self._current is not None
                    or self._provided != self._completed or self._completed != len(self._rows)
                    or self._forwards != expected or self._released != expected
                    or self._backwards != group.expected_backward_calls
                    or not all(value['completed'] for value in self._microbatches)):
                raise ValueError('complete original microbatch/CE/KD/graph accounting differs')
            self._check_binding()
            self.phase = 'CLOSED'
            return dict(schema=SCHEMA, contract=self.contract, group=report,
                microbatches=copy.deepcopy(self._microbatches), forward_calls=self._forwards,
                provider_rows=self._provided, completed_rows=self._completed,
                backward_callback_calls=self._backwards, retained_callbacks=self._retained,
                released_microbatch_callbacks=self._released, owned_active_graphs=0,
                maximum_owned_active_microbatches=1,
                hidden_values_per_forward=self.batch_size*self.student_width*self.hidden_width,
                full_training_resume_or_scaler_optimizer_integration=False,
                original_model_or_source_authentication=False, language_quality='NOT_EVALUATED')
        except BaseException:
            self.phase = 'FAILED'
            raise
        finally:
            self._drop_owned_graph()
