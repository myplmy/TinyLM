"""Explicit packed-token microbatches in the complete scheduled CPU owner.

Only fresh tiny numerical fixtures exercise this path. No Native model,
checkpoint asset, tokenizer, real corpus or GPU is loaded by this module.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from scripts.p106b_dskdv2_training import FeatureTrainingUpdate, _same
from scripts.p106b_dskdv2_scheduled_training import ScheduledFeatureTrainer
from scripts.p106b_dskdv2_microbatch import CausalMicrobatchFrames, _integer


UPDATE_SCHEMA = 'P106B_PACKED_FEATURE_TRAINING_UPDATE_V1'
POLICY_SCHEMA = 'P106B_BATCHED_SCHEDULED_CPU_POLICY_V1'
ENVELOPE_SCHEMA = 'P106B_BATCHED_SCHEDULED_CPU_BOUNDARY_V1'
RAW_POLICY = 'RAW_TOKEN_COUNT_X_IDS_MINUS_LAST_Y_LABELS_FROM_ONE_V1'


@dataclass(frozen=True)
class PackedFeatureTrainingUpdate(FeatureTrainingUpdate):
    packed_students: tuple | list


def _unused_row_provider(_model, _metadata):
    raise RuntimeError('explicit batched CPU owner cannot fall back to a per-row forward')


class BatchedScheduledFeatureTrainer(ScheduledFeatureTrainer):
    """Separate opt-in CPU owner; no persistent adapter graph at a boundary.

    Source owns its typed raw packed values, metadata, exact cursor/private RNG
    and pure validator. Parent owners keep complete model/optimizer/scaler/LR/
    global RNG restoration. Source declarations do not authenticate real data.
    """
    def __init__(self, model, optimizers, source, *, schedule, batch_size,
                 pad_id, max_hidden_values=33554432, **kwargs):
        _integer(batch_size, 'batch_size', 1, 128)
        _integer(pad_id, 'pad_id', 0, 2**31-1)
        _integer(max_hidden_values, 'max_hidden_values', 1, 33554432)
        contract = getattr(source, 'contract', None)
        if (type(contract) is not dict or contract.get('packed_update_schema') != UPDATE_SCHEMA
                or contract.get('student_tokens_policy') != RAW_POLICY):
            raise ValueError('explicit packed update source and raw one-shift policy required')
        self._batch_size, self._pad_id = batch_size, pad_id
        self._max_hidden_values = max_hidden_values
        self._microbatch_policy = None
        super().__init__(model, optimizers, source, _unused_row_provider,
                         schedule=schedule, **kwargs)
        if (not 0 <= pad_id < len(self.embedding)
                or batch_size*self._group_options['student_width']*self.up.shape[0] > max_hidden_values):
            raise ValueError('batched CPU pad vocabulary or hidden-value quota differs')
        self._microbatch_policy = self._current_batch_policy()
        self.contract = copy.deepcopy(self.contract)
        self.contract['microbatch_control'] = copy.deepcopy(self._microbatch_policy)
        self.contract['scope'] = 'CPU_COMPLETE_BATCHED_SCHEDULED_NUMERICAL_BOUNDARY_NOT_NATIVE_OR_CORPUS_CERTIFICATION'
        self._binding()

    def _current_batch_policy(self):
        return dict(schema=POLICY_SCHEMA, packed_update_schema=UPDATE_SCHEMA,
            student_tokens_policy=RAW_POLICY, batch_size=self._batch_size, pad_id=self._pad_id,
            student_width=self._group_options['student_width'], max_hidden_values=self._max_hidden_values,
            body_autocast='OFF_CPU_FP32_ONLY',
            graph_policy='RETAIN_SHARED_GRAPH_THROUGH_LAST_REAL_ROW_FINAL_CHUNK_V1',
            provider_state='SINGLE_USE_PER_GROUP_NO_PERSISTENT_GRAPH_OR_PRIVATE_ADAPTER_RNG')

    def _binding(self, *, restoring=False):
        super()._binding(restoring=restoring)
        if self._microbatch_policy is not None:
            if (not _same(self._current_batch_policy(), self._microbatch_policy)
                    or self.provider is not _unused_row_provider
                    or not _same(self.contract.get('microbatch_control'), self._microbatch_policy)):
                raise ValueError('complete batched CPU policy/provider binding changed')

    def _group_consumer(self, group, update):
        # This factory is called before the inherited LR/controller setup.
        if type(update) is not PackedFeatureTrainingUpdate:
            raise ValueError('explicit typed original packed-token update required')
        adapter = CausalMicrobatchFrames(self.model, update.ce_rows, update.packed_students,
            student_width=self._group_options['student_width'], batch_size=self._batch_size,
            pad_id=self._pad_id, max_hidden_values=self._max_hidden_values)
        def consume(controller):
            full = adapter.consume(group,
                lambda loss, context:controller.backward(loss, retain_graph=context['retain_graph']))
            report = dict(full['group'])
            report['microbatch_frames'] = {k:v for k,v in full.items() if k != 'group'}
            return report
        return consume

    def state_dict(self):
        boundary = super().state_dict()
        return dict(schema=ENVELOPE_SCHEMA, policy=copy.deepcopy(self._microbatch_policy),
                    scheduled_boundary=boundary)

    def load_state_dict(self, state):
        if (type(state) is not dict or set(state) != {'schema', 'policy', 'scheduled_boundary'}
                or state['schema'] != ENVELOPE_SCHEMA
                or not _same(state['policy'], self._microbatch_policy)):
            raise ValueError('exact distinct batched scheduled CPU checkpoint envelope required')
        super().load_state_dict(state['scheduled_boundary'])
