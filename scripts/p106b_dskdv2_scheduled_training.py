"""Explicit consumed-group LR ownership around the unchanged CPU CE/KD owner.

Only new tiny numerical fixtures have exercised this class. It neither loads a
Native/pretrained model nor authenticates source/teacher assets or a corpus.
"""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import math

from scripts.p106b_dskdv2_training import ScaledFeatureTrainer, _same
from tinylm.train.anneal_schedule import lr_factor
from tinylm.train.adaptive_training import cpu_copy


PLAN_SCHEMA = 'P106B_CONSUMED_GROUP_LR_PLAN_V1'
STATE_SCHEMA = 'P106B_CONSUMED_GROUP_LR_STATE_V1'
ENVELOPE_SCHEMA = 'P106B_SCHEDULED_FEATURE_CPU_BOUNDARY_V1'
CLOCK = 'CONSUMED_ORIGINAL_GROUPS_INCLUDING_OVERFLOW_V1'


@dataclass(frozen=True)
class ConsumedGroupSchedule:
    steps: int
    warm: int = 0
    sched: str = 'cosine'
    decay_frac: float = .2

    def __post_init__(self):
        if (type(self.steps) is not int or not 1 <= self.steps < 2**31
                or type(self.warm) is not int or not 0 <= self.warm < self.steps
                or type(self.sched) is not str or self.sched not in ('cosine', 'wsd', 'stable', 'decay')
                or type(self.decay_frac) not in (float, int)
                or not math.isfinite(self.decay_frac) or not 0 < self.decay_frac <= 1):
            raise ValueError('explicit bounded consumed-group LR schedule required')
        object.__setattr__(self, 'decay_frac', float(self.decay_frac))

    def factor(self, ordinal):
        if type(ordinal) is not int or not 0 <= ordinal < self.steps:
            raise ValueError('consumed-group LR ordinal outside planned budget')
        value = lr_factor(ordinal, self.warm, self.steps, self.sched, self.decay_frac)
        if not math.isfinite(value) or not 0 < value <= 1:
            raise ValueError('canonical LR factor outside declared positive range')
        return float(value)

    def contract(self):
        return dict(schema=PLAN_SCHEMA, clock=CLOCK, **asdict(self),
                    formula_owner='tinylm/train/anneal_schedule.py:lr_factor')


class ScheduledFeatureTrainer(ScaledFeatureTrainer):
    """Opt-in CPU numerical LR owner with a distinct checkpoint envelope.

Every student optimizer follows the consumed group ordinal, including overflow.
The dedicated projector follows the same clock only when that group has KD;
otherwise its full optimizer state, including its previous LR, is unchanged.
    """
    def __init__(self, *args, schedule, **kwargs):
        if type(schedule) is not ConsumedGroupSchedule:
            raise ValueError('explicit ConsumedGroupSchedule required')
        self.schedule = schedule
        self._base_rates = None
        self._resume_rates = None
        self._last_rate_event = None
        super().__init__(*args, **kwargs)
        rates = self._read_rates()
        self._base_rates = tuple(tuple(row) for row in rates)
        self._last_active_ordinals = [-1] * len(self.optimizers)
        self._schedule_policy = dict(plan=schedule.contract(), base_lrs=copy.deepcopy(rates),
            inactive_projector='PRESERVE_PREVIOUS_LR_AND_ALL_OPTIMIZER_STATE_V1')
        self.contract = copy.deepcopy(self.contract)
        self.contract['scheduled_control'] = copy.deepcopy(self._schedule_policy)
        self.contract['scope'] = 'CPU_SCHEDULED_COMPLETE_BOUNDARY_FIXED_TEACHER_DECLARATION_NOT_CERTIFIED'
        self._binding()

    def _read_rates(self):
        rates = [[group.get('lr') for group in opt.param_groups] for opt in self.optimizers]
        if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0
               for row in rates for value in row):
            raise ValueError('finite positive scalar optimizer LR required')
        return [[float(value) for value in row] for row in rates]

    def _rates_for(self, ordinals):
        return [[base * (1. if ordinal == -1 else self.schedule.factor(ordinal)) for base in row]
                for ordinal, row in zip(ordinals, self._base_rates)]

    def _optimizer_binding(self):
        layout = super()._optimizer_binding()
        if self._base_rates is not None:
            if (len(layout) != len(self._base_rates)
                    or any(len(item['groups']) != len(rates)
                           for item, rates in zip(layout, self._base_rates))):
                raise ValueError('scheduled optimizer group count changed')
            for item, rates in zip(layout, self._base_rates):
                for group, base in zip(item['groups'], rates):
                    group['settings']['lr'] = base
        return layout

    def _binding(self, *, restoring=False):
        super()._binding(restoring=restoring)
        if self._base_rates is not None:
            if not _same(self.schedule.contract(), self._schedule_policy['plan']):
                raise ValueError('consumed-group LR plan changed')
            if not restoring and not _same(self._read_rates(), self._rates_for(self._last_active_ordinals)):
                raise ValueError('live optimizer LR differs from consumed-group control')

    def _fresh_bound_controller(self, parameters, optimizers, backwards):
        controller, migration = super()._fresh_bound_controller(parameters, optimizers, backwards)
        ordinal = self.completed_groups
        factor = self.schedule.factor(ordinal)
        before = self._read_rates()
        for index in optimizers:
            for group, base in zip(self.optimizers[index].param_groups, self._base_rates[index]):
                group['lr'] = base * factor
            self._last_active_ordinals[index] = ordinal
        self._last_rate_event = dict(clock=CLOCK, consumed_ordinal=ordinal, factor=factor,
            active_optimizer_indices=list(optimizers), before_lrs=before, current_lrs=self._read_rates())
        return controller, migration

    def _schedule_state(self):
        return dict(schema=STATE_SCHEMA, next_ordinal=self.completed_groups,
            last_active_ordinals=list(self._last_active_ordinals), current_lrs=self._read_rates())

    def _checked_schedule_state(self, state, boundary):
        fields = {'schema', 'next_ordinal', 'last_active_ordinals', 'current_lrs'}
        if type(state) is not dict or set(state) != fields or state['schema'] != STATE_SCHEMA:
            raise ValueError('exact consumed-group LR state schema required')
        if type(boundary) is not dict:
            raise ValueError('complete underlying CPU boundary required')
        completed = boundary.get('completed_groups')
        if (type(completed) is not int or not 0 <= completed <= self.schedule.steps
                or type(state['next_ordinal']) is not int or state['next_ordinal'] != completed):
            raise ValueError('LR/source consumed group counters differ')
        last = state['last_active_ordinals']
        if (type(last) is not list or len(last) != len(self.optimizers)
                or any(type(value) is not int or not -1 <= value < completed for value in last)
                or any(last[index] != completed - 1 for index in self._student_optimizers)):
            raise ValueError('last-active LR ordinals differ')
        carry = boundary.get('scaler_carry')
        if not completed:
            if carry is not None or any(value != -1 for value in last):
                raise ValueError('initial LR control must precede every group')
        else:
            if type(carry) is not dict:
                raise ValueError('completed LR control requires underlying scaler carry')
            active = carry.get('optimizer_indices')
            if active == list(range(len(self.optimizers))):
                if last[self._projector_optimizer] != completed - 1:
                    raise ValueError('last KD group and projector LR ordinal differ')
            elif active == self._student_optimizers:
                if last[self._projector_optimizer] >= completed - 1:
                    raise ValueError('inactive projector LR ordinal advanced')
            else:
                raise ValueError('LR and scaler active optimizer sets differ')
        expected = self._rates_for(last)
        if not _same(state['current_lrs'], expected):
            raise ValueError('checkpoint LR values differ from declared control')
        return copy.deepcopy(state)

    def step(self):
        if self.active or self.dirty:
            raise RuntimeError('scheduled CPU trainer active/dirty; complete restore required')
        self._binding()
        self._checked_schedule_state(self._schedule_state(),
            dict(completed_groups=self.completed_groups, scaler_carry=self._carry))
        if self.completed_groups == self.schedule.steps:
            raise StopIteration('planned consumed-group LR budget exhausted')
        self._last_rate_event = None
        report = super().step()
        event = copy.deepcopy(self._last_rate_event)
        if event is None:
            self.dirty = True
            raise RuntimeError('completed original group lacks LR event')
        report['lr_schedule'] = dict(event, next_ordinal=self.completed_groups,
            applied_groups=self.applied_groups, skipped_groups=self.skipped_groups,
            budget_groups=self.schedule.steps, actual_language_quality='NOT_EVALUATED')
        return report

    def state_dict(self):
        boundary = super().state_dict()
        state = self._checked_schedule_state(self._schedule_state(), boundary)
        return dict(schema=ENVELOPE_SCHEMA, policy=copy.deepcopy(self._schedule_policy),
                    lr_schedule=state, boundary=boundary)

    def _validate_optimizer_state(self, index, value):
        if self._resume_rates is None:
            raise RuntimeError('scheduled optimizer validation needs checked LR envelope')
        if (type(value) is not dict or type(value.get('param_groups')) is not list
                or len(value['param_groups']) != len(self._base_rates[index])):
            raise ValueError('scheduled optimizer snapshot group layout differs')
        normalized = cpu_copy(value)
        for group, base, expected in zip(normalized['param_groups'], self._base_rates[index], self._resume_rates[index]):
            if (type(group) is not dict or type(group.get('lr')) not in (float, int)
                    or not math.isfinite(group['lr']) or float(group['lr']) != expected):
                raise ValueError('saved optimizer LR and checked schedule differ')
            group['lr'] = base
        super()._validate_optimizer_state(index, normalized)

    def load_state_dict(self, state):
        if self.active:
            raise RuntimeError('cannot restore an active scheduled CPU update')
        if (type(state) is not dict or set(state) != {'schema', 'policy', 'lr_schedule', 'boundary'}
                or state['schema'] != ENVELOPE_SCHEMA or not _same(state['policy'], self._schedule_policy)):
            raise ValueError('exact explicit scheduled CPU checkpoint envelope required')
        checked = self._checked_schedule_state(state['lr_schedule'], state['boundary'])
        self._resume_rates = copy.deepcopy(checked['current_lrs'])
        try:
            super().load_state_dict(state['boundary'])
        finally:
            self._resume_rates = None
        try:
            self._last_active_ordinals = list(checked['last_active_ordinals'])
            self._last_rate_event = None
            self._binding()
        except BaseException:
            self.dirty = True
            raise
