"""CPU hard-accuracy masking policy, independent of any production trainer.

AMLM-inspired token-type weights are adapted to shifted MNTP targets. This is
not GPT-BERT's per-document exposure counter and not a model quality verdict.
Caller owns model/optimizer/data-position resume. Only policy state is saved.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re

import torch

from .hybrid_mntp import IGNORE_INDEX, ObjectiveBatch, eligible_mntp

SCHEMA = 'P107_HARD_MNTP_MASK_POLICY_V1'
VECTORS = ('weights', 'total', 'correct', 'lifetime_total', 'last_seen')


@dataclass(frozen=True)
class PolicyConfig:
    vocab_size: int
    mask_rate: float
    ema: float
    refresh_updates: int
    unseen_policy: str
    seed: int
    special_max: int
    mask_id: int
    corpus_sha256: str
    run_sha256: str

    def __post_init__(self):
        ints = (self.vocab_size, self.refresh_updates, self.seed, self.special_max, self.mask_id)
        if any(type(x) is not int for x in ints) or not (0 <= self.mask_id <= self.special_max < self.vocab_size):
            raise ValueError('explicit vocabulary and reserved-token configuration required')
        if self.refresh_updates < 1 or not 0 <= self.seed < 2**63:
            raise ValueError('positive refresh updates and nonnegative seed required')
        if (type(self.mask_rate) not in (int,float) or not math.isfinite(self.mask_rate)
                or not 0 < self.mask_rate <= 1 or type(self.ema) not in (int,float)
                or not math.isfinite(self.ema) or not 0 <= self.ema < 1):
            raise ValueError('finite rate in (0,1] and EMA in [0,1) required')
        if self.unseen_policy not in ('keep','prior'):
            raise ValueError('unobserved token policy must be explicit keep or prior')
        if any(not isinstance(x,str) or re.fullmatch('[0-9A-F]{64}',x) is None
               for x in (self.corpus_sha256,self.run_sha256)):
            raise ValueError('explicit uppercase corpus/run SHA required')


def capped_probabilities(weights, rate):
    """Positive CPU weights -> [0,1] probabilities with exact expected mean rate.

    Row normalization is intentional. A sorted water-fill uses suffix sums to
    avoid subtracting almost equal totals when weights have very different sizes.
    It preserves an expected Bernoulli budget, not a fixed number of targets.
    """
    if (not isinstance(weights,torch.Tensor) or weights.device.type != 'cpu'
            or weights.ndim != 1 or not weights.is_floating_point()
            or not bool(torch.isfinite(weights).all()) or bool((weights <= 0).any())
            or type(rate) not in (int,float) or not math.isfinite(rate) or not 0 < rate <= 1):
        raise ValueError('finite positive one-dimensional CPU weights and rate required')
    weights = weights.to(torch.float64)
    n = weights.numel()
    if n == 0:
        return weights.clone()
    if rate == 1 or bool((weights == weights[0]).all()):
        return torch.full_like(weights,float(rate))
    ordered = weights.sort(descending=True).values
    tail = ordered.flip(0).cumsum(0).flip(0)
    k = torch.arange(n,dtype=torch.float64)
    scale = (float(rate) * n - k) / tail
    next_ok = (scale >= 0) & (scale * ordered <= 1 + 1e-12)
    previous = torch.cat((torch.tensor([float('inf')]),ordered[:-1]))
    previous_ok = (k == 0) | (scale * previous >= 1 - 1e-12)
    valid = torch.nonzero(next_ok & previous_ok).flatten()
    if valid.numel() == 0:
        raise ValueError('bounded probability normalization has no stable solution')
    probabilities = (weights * scale[int(valid[0])]).clamp(0,1)
    if not torch.isclose(probabilities.sum(),torch.tensor(float(rate)*n,dtype=torch.float64),atol=1e-9,rtol=1e-12):
        raise ValueError('expected masking budget drift')
    return probabilities


def state_fingerprint(state):
    fields = {k:v for k,v in state.items() if k not in (*VECTORS,'rng','fingerprint')}
    digest = hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
    for name in (*VECTORS,'rng'):
        value = state[name]
        if not isinstance(value,torch.Tensor) or value.device.type != 'cpu':
            raise ValueError('policy state tensors must be explicit CPU values')
        digest.update(name.encode()); digest.update(str(value.dtype).encode())
        digest.update(str(tuple(value.shape)).encode()); digest.update(value.detach().contiguous().numpy().tobytes())
    return digest.hexdigest().upper()


class HardMaskPolicy:
    def __init__(self, config):
        if not isinstance(config,PolicyConfig):
            raise ValueError('explicit PolicyConfig required')
        self.config = config
        self.weights = torch.ones(config.vocab_size,dtype=torch.float64)
        self.total = torch.zeros(config.vocab_size,dtype=torch.int64)
        self.correct = torch.zeros_like(self.total)
        self.lifetime_total = torch.zeros_like(self.total)
        self.last_seen = torch.full_like(self.total,-1)
        self.generator = torch.Generator(device='cpu').manual_seed(config.seed)
        self.draw_dtype = torch.get_default_dtype()
        self.next_update = self.observed_micro_batches = 0
        self._pending = None

    def begin_update(self, update, *, split, expected_observations):
        if (self._pending is not None or type(update) is not int or update != self.next_update
                or split != 'train' or type(expected_observations) is not int or expected_observations < 1):
            raise ValueError('fresh exact TRAIN update boundary required')
        self._pending = dict(total=torch.zeros_like(self.total),correct=torch.zeros_like(self.correct),
                             observations=0,expected_observations=expected_observations,
                             rng=self.generator.get_state().clone())

    def _active(self):
        if self._pending is None:
            raise ValueError('begin_update required')

    def probabilities(self, tokens, document_ids, *, adaptive):
        self._active()
        if type(adaptive) is not bool or tokens.device.type != 'cpu' or document_ids.device.type != 'cpu':
            raise ValueError('CPU tensors and an explicit adaptive bool required')
        c = self.config
        eligible = eligible_mntp(tokens,document_ids,vocab_size=c.vocab_size,
                                 special_max=c.special_max,mask_id=c.mask_id)
        probabilities = torch.zeros_like(tokens,dtype=torch.float64)
        for row in range(tokens.shape[0]):
            ids = tokens[row,eligible[row]]
            if adaptive:
                probabilities[row,eligible[row]] = capped_probabilities(self.weights[ids],c.mask_rate)
            else:
                probabilities[row,eligible[row]] = c.mask_rate
        return eligible, probabilities

    def select(self, tokens, document_ids, *, adaptive):
        eligible, probabilities = self.probabilities(tokens,document_ids,adaptive=adaptive)
        # Exactly the original full shape/ordering, including protected positions.
        draws = torch.rand(tokens.shape,generator=self.generator,dtype=self.draw_dtype)
        # The original function compares a rand tensor with a Python scalar,
        # rounded to that tensor's dtype. Preserve boundary draws such as .7.
        thresholds = probabilities.to(draws.dtype)
        return (draws < thresholds) & eligible, probabilities

    @staticmethod
    def _add(base, delta):
        if bool((base > torch.iinfo(torch.int64).max - delta).any()):
            raise ValueError('stat counter would overflow int64')
        return base + delta

    def observe(self, batch, prediction_ids, *, observation_index):
        self._active(); c = self.config
        if (type(observation_index) is not int or observation_index != self._pending['observations']
                or observation_index >= self._pending['expected_observations']):
            raise ValueError('each masked observation ticket must occur once in declared order')
        if (not isinstance(batch,ObjectiveBatch) or batch.objective != 'MNTP_RESERVED_100_PERCENT'
                or not isinstance(prediction_ids,torch.Tensor) or prediction_ids.device.type != 'cpu'
                or prediction_ids.dtype != torch.long or prediction_ids.shape != batch.targets.shape
                or batch.targets.device.type != 'cpu' or batch.targets.dtype != torch.long
                or batch.inputs.device.type != 'cpu' or batch.inputs.dtype != torch.long
                or batch.inputs.shape != batch.targets.shape or batch.selected_positions.device.type != 'cpu'
                or batch.selected_positions.dtype != torch.bool
                or batch.selected_positions.shape != (batch.targets.shape[0],batch.targets.shape[1]+1)):
            raise ValueError('closed CPU MNTP batch and shifted-position argmax IDs required')
        selected = batch.targets != IGNORE_INDEX
        if (not torch.equal(selected,batch.selected_positions[:,1:]) or not bool(selected.any())
                or bool((batch.selected_positions[:,0] | batch.selected_positions[:,-1]).any())
                or bool((prediction_ids < 0).any()) or bool((prediction_ids >= c.vocab_size).any())
                or bool((batch.inputs[batch.selected_positions[:,:-1]] != c.mask_id).any())):
            raise ValueError('MNTP shift/corruption or nonempty selection contract differs')
        gold = batch.targets[selected]
        if bool((gold <= c.special_max).any()) or bool((gold >= c.vocab_size).any()):
            raise ValueError('protected/out-of-range gold cannot update adaptive statistics')
        count = torch.bincount(gold,minlength=c.vocab_size)
        correct = torch.bincount(gold[prediction_ids[selected] == gold],minlength=c.vocab_size)
        total_next = self._add(self._pending['total'],count)
        correct_next = self._add(self._pending['correct'],correct)
        self._pending.update(total=total_next,correct=correct_next,
                              observations=self._pending['observations']+1)

    def finish_update(self, *, accepted):
        self._active()
        if type(accepted) is not bool:
            raise ValueError('explicit accepted update decision required')
        pending = self._pending
        if not accepted:
            self.generator.set_state(pending['rng'])
            self._pending = None
            return dict(accepted=False,next_update=self.next_update,statistics_discarded=True,rng_restored=True)
        if (pending['observations'] != pending['expected_observations']
                or self.next_update >= torch.iinfo(torch.int64).max):
            raise ValueError('an accepted complete update must include observations and valid cursor')
        total = self._add(self.total,pending['total'])
        correct = self._add(self.correct,pending['correct'])
        lifetime = self._add(self.lifetime_total,pending['total'])
        last_seen = self.last_seen.clone(); last_seen[pending['total'] > 0] = self.next_update
        next_update = self.next_update + 1
        weights = self.weights.clone()
        refreshed = next_update % self.config.refresh_updates == 0
        if refreshed:
            # Algebraically 1-smoothed_accuracy, without cancellation near 1.
            error = ((total-correct).double()+.5) / (total.double()+1.)
            update = total > 0 if self.config.unseen_policy == 'keep' else torch.ones_like(total,dtype=torch.bool)
            weights[update] = self.config.ema*weights[update] + (1-self.config.ema)*error[update]
            if not bool(torch.isfinite(weights).all()) or bool((weights <= 0).any()) or bool((weights > 1).any()):
                raise ValueError('adaptive weights must remain positive and bounded')
            total,correct = torch.zeros_like(total),torch.zeros_like(correct)
        self.total,self.correct,self.lifetime_total,self.last_seen,self.weights = total,correct,lifetime,last_seen,weights
        self.next_update = next_update
        self.observed_micro_batches += pending['observations']
        self._pending = None
        return dict(accepted=True,next_update=next_update,weights_refreshed=refreshed,
                     supervised_observations=int(pending['total'].sum()))

    def state_dict(self):
        if self._pending is not None:
            raise ValueError('policy resume is only defined at a complete update boundary')
        result = dict(schema=SCHEMA,config=asdict(self.config),next_update=self.next_update,
                       observed_micro_batches=self.observed_micro_batches,draw_dtype=str(self.draw_dtype),
                       rng=self.generator.get_state().clone())
        result.update({name:getattr(self,name).clone() for name in VECTORS})
        result['fingerprint'] = state_fingerprint(result)
        return result

    def load_state_dict(self, state):
        if self._pending is not None or set(state) != {'schema','config','next_update','observed_micro_batches','draw_dtype','rng','fingerprint',*VECTORS}:
            raise ValueError('fresh exact boundary policy state required')
        if (state['schema'] != SCHEMA or state['config'] != asdict(self.config)
                or state['draw_dtype'] != str(self.draw_dtype)
                or type(state['next_update']) is not int or not 0 <= state['next_update'] < 2**63
                or type(state['observed_micro_batches']) is not int or state['observed_micro_batches'] < state['next_update']
                or state_fingerprint(state) != state['fingerprint']):
            raise ValueError('policy schema/config/cursor/fingerprint differs')
        for name in VECTORS:
            value = state[name]; dtype = torch.float64 if name == 'weights' else torch.int64
            if (value.dtype != dtype or value.shape != (self.config.vocab_size,)
                    or value.device.type != 'cpu' or value.requires_grad):
                raise ValueError('policy vector dtype/shape/device differs')
        w,t,c,l,s = (state[name] for name in VECTORS)
        if (not bool(torch.isfinite(w).all()) or bool(((w <= 0)|(w > 1)).any())
                or bool(((t < 0)|(c < 0)|(c > t)|(l < t)|(s < -1)|(s >= state['next_update'])).any())
                or not torch.equal(l == 0,s == -1)):
            raise ValueError('policy statistics violate invariants')
        rng = state['rng']
        if rng.dtype != torch.uint8 or rng.ndim != 1:
            raise ValueError('CPU generator byte state required')
        candidate = torch.Generator(device='cpu'); candidate.set_state(rng.clone())
        copied = {name:state[name].clone() for name in VECTORS}
        for name in VECTORS:
            setattr(self,name,copied[name])
        self.generator = candidate
        self.next_update,self.observed_micro_batches = state['next_update'],state['observed_micro_batches']

    def storage_audit(self):
        values = [getattr(self,name) for name in VECTORS]
        if self._pending is not None:
            values += [self._pending[name] for name in ('total','correct','rng')]
        seen, size = set(), 0
        for value in values:
            storage = value.untyped_storage(); key=(storage.data_ptr(),storage.nbytes())
            if key not in seen:
                seen.add(key); size += storage.nbytes()
        rng_export = self.generator.get_state().untyped_storage().nbytes()
        return dict(owned_tensor_storage_bytes=size,rng_export_bytes=rng_export,
                    state_representation_bytes=size+rng_export,native_generator_bytes=None,
                    scope='OWNED_TENSOR_STORAGE_PLUS_EXPORTED_RNG;NOT_NATIVE_GENERATOR_RSS_OR_PEAK')


def audit_selection(eligible, selected, probabilities, groups, *, comparison_dtype=None):
    if (eligible.dtype != torch.bool or selected.dtype != torch.bool
            or eligible.shape != selected.shape or probabilities.shape != eligible.shape
            or bool((selected & ~eligible).any()) or not bool(torch.isfinite(probabilities).all())
            or bool(((probabilities < 0)|(probabilities > 1)).any())
            or bool((probabilities[~eligible] != 0).any())):
        raise ValueError('valid eligible/selection/probability audit tensors required')
    result = {}
    for name,group in groups.items():
        if group.dtype != torch.bool or group.shape != eligible.shape:
            raise ValueError('explicit group labels must match positions')
        subset = group & eligible
        count = int(subset.sum()); actual = int((selected & subset).sum())
        expected = float(probabilities[subset].sum())
        represented = probabilities.to(comparison_dtype).double() if comparison_dtype is not None else probabilities
        represented_expected = float(represented[subset].sum())
        result[name] = dict(eligible=count,selected=actual,expected=expected,
                           represented_threshold_sum=represented_expected,
                           comparison_dtype=str(comparison_dtype) if comparison_dtype is not None else 'ANALYTICAL_ONLY',
                           expected_rate=expected/count if count else None,
                           realized_rate=actual/count if count else None)
    return result
