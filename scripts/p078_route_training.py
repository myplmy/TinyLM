"""P078 research-only train-time routes; reuse P070B's atomic schedule/model.

Net-new: per-update decisions, balanced visit counts, backward lifetime leases,
session/model-bound cached decoding, and actual assistant-only update receipts.
No assets/model/torch on import. A learned prefix router is NOT_IMPLEMENTED.
"""
from __future__ import annotations
from collections.abc import Mapping
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
SCHEMA = 'P078_ROUTE_TRAINING_V1'
ARMS = ('uniform_r2', 'fixed_shuffle_r2', 'update_shuffle_r2', 'balanced_count')


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def import_guard(root=ROOT):
    root = Path(root)
    if not root.is_absolute() or root.is_symlink(): raise ValueError('fixed nonsymlink ROOT required')
    for name, expected in (('TINYLM_DIR', str(root)), ('TINYLM_HF', str(root / 'HF'))):
        if name in os.environ and os.environ[name] != expected: raise ValueError('invalid import environment: ' + name)
    for relative in ('HF', 'HF/hub', 'data_cache', 'runs', 'runs/ckpt', 'runs/logs'):
        mode = (root / relative).lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode): raise ValueError('existing nonsymlink project/cache directories required')


def backend():
    import_guard()
    from scripts import p070b_cla_routes
    return p070b_cla_routes


@dataclass(frozen=True)
class Policy:
    arm: str
    seed: int = 1337
    def __post_init__(self):
        if self.arm not in ARMS or type(self.seed) is not int: raise ValueError('registered arm and integer seed required')
    @property
    def cap(self): return 3 if self.arm == 'balanced_count' else 2


def bounded_count(policy, index, total, phase):
    if type(index) is not int or type(total) is not int or not 0 <= index < total: raise ValueError('declared complete schedule index/total required')
    if policy.arm != 'balanced_count': return 2
    r = backend(); start = (index // 4) * 4; size = min(4, total - start)
    # Every complete block AND the fixed remainder have exact mean R2.
    values = {1: [2], 2: [1, 3], 3: [1, 2, 3], 4: [1, 2, 2, 3]}[size][:]
    seed = int(sha([SCHEMA, policy.seed, phase, start, 'counts'])[:16], 16); result = []
    while values:
        choice = r.repeat_draw(len(values), seed, len(result)) - 1
        result.append(values.pop(choice))
    return result[index - start]


def plan(cfg, owners, policy, index, total, phase='train'):
    if phase not in ('train', 'val', 'probe', 'secondary'): raise ValueError('explicit train/val/probe/secondary phase required')
    r = backend(); repeats = bounded_count(policy, index, total, phase)
    order = 'shuffle' if policy.arm in ('fixed_shuffle_r2', 'update_shuffle_r2') else 'uniform'
    seed = 0 if policy.arm == 'fixed_shuffle_r2' else int(sha([SCHEMA, policy.seed, phase, index, 'order'])[:16], 16)
    route = r.schedule(cfg, owners, order, repeats, seed); trace = r.trace(cfg, owners, route)
    identity = r.route_sha(cfg, owners, route)
    uniform = r.schedule(cfg, owners, 'uniform', repeats)
    if policy.arm == 'fixed_shuffle_r2' and route == uniform: raise ValueError('registered fixed seed0 must be nonidentity for this geometry')
    value = dict(schema=SCHEMA, arm=policy.arm, seed=policy.seed, index=index, total=total, phase=phase,
        configured_repeat_cap=policy.cap, actual_repeats=repeats, route=route, route_sha256=identity,
        visits=trace['visits'], kv_entries=trace['kv_entries'], identity_order=route == uniform,
        atomic_trace=trace, schedule_source='scripts/p070b_cla_routes.py')
    value['receipt_sha256'] = sha(value)
    return value


@dataclass(frozen=True)
class QuestionPrefix:
    token_ids: tuple
    def __post_init__(self):
        if not self.token_ids or any(type(i) is not int or i < 0 for i in self.token_ids): raise ValueError('question-prefix IDs only')
    @property
    def sha256(self): return sha(self.token_ids)


def question_prefix(record):
    if not len(record.x) == len(record.y) == len(record.segments): raise ValueError('aligned record required')
    first = next((i for i, y in enumerate(record.y) if y != -100), None)
    if first is None or record.segments[first] != 1 or any(record.segments[:first]): raise ValueError('first assistant target boundary required')
    # y[t] predicts x[t+1]; x[:first+1] includes the generation header, not an answer token.
    return QuestionPrefix(tuple(record.x[:first + 1]))


def learned_router(*_args, **_kwargs):
    raise NotImplementedError('LEARNED_ROUTER_NOT_IMPLEMENTED: prefix feature/label/objective/compute policy needs a separate approved contract')


def build_model(cfg, policy):
    """Fresh experimental subclass; product and P070B source/class stay intact."""
    r = backend()
    @dataclass(frozen=True)
    class SessionCache(Mapping):
        owner: str
        session: int
        receipt_sha256: str
        bank: object
        def __getitem__(self, key): return self.bank[key]
        def __iter__(self): return iter(self.bank)
        def __len__(self): return len(self.bank)
    class TrainRouteTransformer(r.FixedRouteTransformer):
        def __init__(self, config):
            if not config.grad_checkpoint or config.mtp_aux: raise ValueError('checkpointON/MTPoff required')
            self._lease = None; self._plan = None; self._session = 0; self._instance = uuid.uuid4().hex
            self.policy = policy
            super().__init__(config, 'uniform', policy.cap, policy.seed)
        def set_route(self, route):
            if getattr(self, '_lease', None) is not None: raise RuntimeError('route frozen through whole backward or generation session')
            checked = r.trace(self.cfg, self.owner, route)
            if checked['middle_repeats'] > policy.cap: raise ValueError('route exceeds declared training repeat cap')
            self._fixed_route = tuple(route); self.route_sha256 = r.route_sha(self.cfg, self.owner, route); self.route_trace = checked
        def _assert_route(self):
            if self._plan is None or self.route_sha256 != self._plan['route_sha256'] or r.route_sha(self.cfg, self.owner, self._fixed_route) != self.route_sha256:
                raise RuntimeError('active route/receipt mutated')
        @contextmanager
        def route_scope(self, index, total, phase='train', prefix=None, secondary=False):
            if self._lease is not None: raise RuntimeError('nested/overlapping route scope refused')
            selected = Policy('uniform_r2', policy.seed) if secondary else policy
            receipt = plan(self.cfg, self.owner, selected, index, total, phase)
            self.set_route(receipt['route']); self._plan = receipt; self._session += 1
            self._lease = ('train' if phase == 'train' else 'inference', self._session, prefix)
            try:
                yield json.loads(json.dumps(receipt)); self._assert_route()
            finally:
                self.clear_quant(); self._lease = None
        def forward(self, *args, past_kv=None, use_cache=False, **kwargs):
            if self._lease is None: raise RuntimeError('explicit update/session scope required')
            self._assert_route()
            if self.training and self._lease[0] != 'train': raise RuntimeError('inference scope cannot train')
            if use_cache or past_kv is not None:
                if self.training or self._lease[0] != 'inference': raise RuntimeError('training cache forbidden')
                prefix = self._lease[2]
                if not isinstance(prefix, QuestionPrefix): raise ValueError('cache session requires question prefix only')
                if past_kv is None:
                    tokens = args[0]
                    if tokens.shape[0] != 1 or tuple(tokens[0].tolist()) != prefix.token_ids: raise ValueError('first cached prefill must equal frozen question prefix')
                elif (not isinstance(past_kv, SessionCache) or past_kv.owner != self._instance or past_kv.session != self._session
                        or past_kv.receipt_sha256 != self._plan['receipt_sha256']):
                    raise ValueError('foreign/stale session cache refused even for identical route')
                if past_kv is not None: past_kv = past_kv.bank
            result = super().forward(*args, past_kv=past_kv, use_cache=use_cache, **kwargs)
            if use_cache:
                logits, bank = result
                return logits, SessionCache(self._instance, self._session, self._plan['receipt_sha256'], bank)
            return result
    return TrainRouteTransformer(cfg)


def sft_update(model, records, optimizers, index, total, *, pad_id=0, width=1024, device='cpu', amp=False):
    """Real eager SFT update,16 full micro8 including neutral tail padding.

    Corpus order, parent loading, LR/optimizer creation and authorization belong
    to the driver. No compile/router/teacher/native-bin side path is hidden here.
    """
    import_guard(); import torch
    from tinylm.train import mtp_sft as core
    records = list(records)
    if not 1 <= len(records) <= 128 or width > model.cfg.max_seq_len or not model.cfg.grad_checkpoint or model.cfg.mtp_aux:
        raise ValueError('one at-most128 real-row update/checkpointON/MTPoff required')
    targets = sum(r.targets for r in records); actual_x = sum(r.x_tokens for r in records)
    if targets <= 0 or any(r.targets <= 0 for r in records): raise ValueError('positive actual assistant targets on every real row required')
    ids = [id(p) for opt in optimizers for group in opt.param_groups for p in group['params']]
    if len(ids) != len(set(ids)) or set(ids) != {id(p) for p in model.parameters() if p.requires_grad}: raise ValueError('complete nonduplicated optimizer parameter ownership required')
    before = sha([dict(x=r.x, y=r.y, segments=r.segments) for r in records]); started = time.perf_counter()
    for opt in optimizers: opt.zero_grad(set_to_none=True)
    model.clear_quant(); model.train(); model.set_anneal(1.)
    observed = x_count = 0; nll = 0.; dummy_rows = 128 - len(records)
    padded = records + [core.Record([pad_id], [-100], [0]) for _ in range(dummy_rows)]
    with model.route_scope(index, total, 'train') as route:
        for start in range(0, 128, 8):
            micro = padded[start:start + 8]
            x, y, segments = core.pad_records(micro, pad_id, device, fixed_width=width, batch_size=8)
            with (torch.autocast('cuda', dtype=torch.bfloat16) if amp else nullcontext()):
                sums, valid = core.components(model, model(x, return_hidden=True), y, segments, horizons=())
                loss = sums[1] / targets
            if not bool(torch.isfinite(loss)): raise ValueError('nonfinite assistant CE')
            loss.backward(); model._assert_route(); observed += valid[1]; nll += float(sums[1].detach())
        if observed != targets: raise ValueError('actual16-micro assistant denominator differs')
        grads = [p.grad for p in model.parameters() if p.grad is not None]
        if not grads or not all(bool(torch.isfinite(g).all()) for g in grads): raise ValueError('missing/nonfinite gradient')
        grad_max = max(float(g.abs().max()) for g in grads)
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
        if not math.isfinite(float(norm)): raise ValueError('nonfinite actual gradient norm')
        for opt in optimizers: opt.step()
        if device == 'cuda': torch.cuda.synchronize()
        model._assert_route()
    if before != sha([dict(x=r.x, y=r.y, segments=r.segments) for r in records]): raise ValueError('input records mutated')
    return dict(route=route, actual_rows=len(records), dummy_rows=dummy_rows, actual_x_tokens=actual_x,
        assistant_targets=observed, ce=nll / observed, gradient_max=grad_max, gradient_norm=float(norm),
        micro_bs=8, accum=16, padded_slots=128 * width, layer_visit_slots=128 * width * route['visits'],
        optimizer_ids=[id(opt) for opt in optimizers], model_id=id(model), seconds=time.perf_counter() - started)
