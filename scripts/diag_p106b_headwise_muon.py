#!/usr/bin/env python3
"""원 float native에서 Q/K NS 단위만 head별로 바꾸는 전용 SFT384 대조.

제품/기존 driver의 globals는 바꾸지 않는다. clip1·원 L0/backward/train/eval을
private 동결 namespace에서 유지한다. 기존 float SFT는 기준선으로만 읽는다.
실물 prepare/CP/모델/GPU/유휴관측/Git은 root 소유이며 check-only는 코드만 읽는다.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
import types
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
SCRIPT, TEST = 'scripts/diag_p106b_headwise_muon.py', 'scripts/test_p106b_headwise_muon.py'
F4 = ROOT / 'handoff/audit/WIP_20261020_HEADWISE_MUON_F4.json'
SOURCE = 'scripts/diag_p106b_native_weight_route.py'
RESUME = 'scripts/diag_p106b_native_resume.py'
UTILITY = 'scripts/diag_p106b_route_cross_resume.py'
CROSS = 'scripts/diag_p106b_route_cross_readout.py'
CODE_PINS = {
    SOURCE: 'E51B68024CA0DC24A4994FFF51C733C05BA2773E3038A2B1CC5C127F6C736FAE',
    RESUME: 'DD4FD5F76192BA35D6FB95A8D7384BC4E23996404686AB6932B0A25CFCB56ECC',
    UTILITY: '1229A9033589BB17086747231AE5E6D9544A97BCA52A33FBE90CC4D1C0082C1D',
    CROSS: '2162B620A66641137399647F185E92F37419E21586B0C6C14FFD71748692355B',
    'tinylm/train/muon.py': 'F2D81EF9903DC4BD2F9298BD65D3B210B1DE21141D22361A85A46F1DDE5F4676',
    'scripts/diag_p101a_sft_mtp.py': 'D7AC53E981E957C3C3A38417D19F1F3C01CE38DA736607FB6FC2B60E535A44DC',
    'scripts/p106b_weight_route.py': 'C2E77B6E8B3CD3338F853B0E5364BD41C9E3650091A11F652479494C55616187',
}
TAG, SCHEMA = 'p106b_headwise_muon_v1_s1337', 'P106B_HEADWISE_MUON_V1'
END, TRAIN_STOP = datetime(2026, 10, 21, 8, tzinfo=timezone.utc), datetime(2026, 10, 21, 5, tzinfo=timezone.utc)
ACTIVE_LIMIT, RECORD_RESERVE, UPDATES = 3600, 600, 384
MODES = ('source', 'prepare', 'preflight', 'cost', 'budget', 'train', 'evaluate', 'readback')
PARENT_REPORT = 'test_result/evidence/p106b_native_weight_route_v1_s1337/train_float/report.json'
BASELINE_REPORT = 'test_result/evidence/p106b_native_resume_v2_s1337/sft_float/report.json'
REPORT_PINS = {PARENT_REPORT: '4AEC0FA5C4983CF89D0CEB7829341CE00245DC4760C4BDF3B06C29B6ADC536E2',
    BASELINE_REPORT: '2E2C778DA12A3B6880972B8001F1F4F4086DDBC3802DC2CDED961DB510EB6C7E'}
PARENT_SHA = 'FBC0AF70CDD9BAFD2011825B404BF336B138B21CBC137C0086833D7A1FDD9508'
PARENT_CORE = 'BE1DB16875AF5316EEB47167E6FD44CCCD0FF67F957DF05525748AC0FE4A6A6D'
BASELINE_SHA = '4B47B1195FB96C5ED44963A9A33012D1FDEDFF55FDF81416E319DCD8F2F89AE3'
BASELINE_CORE = '352A66D97D362DC412DC04407615D5E17F366C6938E9A6BEC3C9683874358267'
TOTALS = dict(x_tokens=8208652, targets=302656, native_replay_targets=3145728)
GROUP_PINS = [(8388608, '0D23683DE7C029690FD8B41A5F6A9052660308EA4A20ADDE01712F2FE8C6B356'),
    (43804, '972054F3008F95F99D57BD8D3DF2DDD01D418161D8835D83EA084A3F58EFE68A'),
    (84836352, '539F9CE9424195BF8C968FF3DF20172EF9F8DD7C780C96FD406609E636074EE7')]


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def checked_code():
    result = {}
    for name, expected in CODE_PINS.items():
        path = ROOT / name
        if path.is_symlink() or not path.is_file(): raise ValueError('정확한 원 코드가 필요하다')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest().upper() != expected: raise ValueError('import 전 원 code SHA가 다르다: ' + name)
        result[name] = data
    return result


# 실제 클래스 정의에 필요한 torch/Muon도 작은 코드 pin 검산 뒤에만 import한다.
checked_code()
import torch
from tinylm.train.muon import Muon, _newton_schulz as original_ns, update_scale
from tinylm.model.ternary import TLinear


@dataclass(frozen=True)
class HeadSpec:
    name: str
    parameter: object
    heads: int
    head_dim: int
    width: int


@dataclass(frozen=True)
class RuntimeAudit:
    check: object
    original: object
    baseline: object
    captured: object
    state: object
    execution_stats: object
    own_reader: object
    baseline_reader: object


def target_geometry():
    return [dict(name=f'layers.{i}.attn.{kind}_proj.weight', kind=kind,
        shape=[768 if kind == 'q' else 192, 768], heads=12 if kind == 'q' else 3,
        head_dim=64, owner=i)
        for i in range(14) for kind in (('q', 'k') if i % 2 == 0 else ('q',))]


def collect_targets(model):
    cfg = model.cfg
    expected = dict(dim=768, n_layers=14, n_q_heads=12, n_kv_heads=3, head_dim=64,
        kv_dim=192, cla_group=2, cla_edges=True, attn_group=1, tie_mlp=False)
    if any(getattr(cfg, k, None) != v for k, v in expected.items()):
        raise ValueError('정확한 d768/L14/Q12/KV3/hd64/CLA2 edges/attn1 cfg가 필요하다')
    if len(model.layers) != 14 or list(model.owner) != [i - i % 2 for i in range(14)]:
        raise ValueError('실제 CLA owner7개가 선언 cfg와 다르다')
    registered = list(model.named_parameters(remove_duplicate=False)); specs, seen = [], set()
    for row in target_geometry():
        index, kind = row['owner'], row['kind']
        attention = model.layers[index].attn
        if bool(attention.owns_kv) != (index % 2 == 0): raise ValueError('실제 attention 소유자가 다르다')
        module = getattr(attention, kind + '_proj', None)
        if (type(module) is not TLinear or module.cfg is not cfg
                or not isinstance(module.weight, torch.nn.Parameter) or not module.weight.requires_grad
                or module.weight.dtype != torch.float32 or list(module.weight.shape) != row['shape']):
            raise ValueError('등록 Q/K의 실제 TLinear/Parameter identity/cfg/shape가 다르다')
        names = [name for name, parameter in registered if parameter is module.weight]
        if names != [row['name']] or id(module.weight) in seen:
            raise ValueError('Q/K 소유권은 정확한 등록명과 한 Parameter identity여야 한다')
        seen.add(id(module.weight))
        specs.append(HeadSpec(row['name'], module.weight, row['heads'], 64, 768))
    for index, layer in enumerate(model.layers):
        if index % 2 and hasattr(layer.attn, 'k_proj'):
            raise ValueError('K 비소유층에 별도 K projection이 있으면 안 된다')
    return specs


@torch.no_grad()
def headwise_ns(gradient, heads, head_dim=64, steps=5, eps=1e-7):
    if (gradient.ndim != 2 or type(heads) is not int or type(head_dim) is not int
            or min(heads, head_dim) <= 0 or gradient.shape[0] != heads * head_dim
            or gradient.shape[1] <= 0 or steps != 5 or eps != 1e-7):
        raise ValueError('원 2D 행렬에서 명시한 head별5NS/eps1e-7만 허용한다')
    a, b, c = 3.4445, -4.7750, 2.0315
    x = gradient.bfloat16().reshape(heads, head_dim, gradient.shape[1])
    transposed = x.size(-2) > x.size(-1)
    if transposed: x = x.mT
    x = x / (x.norm(dim=(-2, -1), keepdim=True) + eps)
    for _ in range(steps):
        aa = x @ x.mT
        bb = b * aa + c * (aa @ aa)
        x = a * x + bb @ x
    if transposed: x = x.mT
    return x.reshape_as(gradient).to(gradient.dtype)


class HeadwiseMuon(Muon):
    """진짜 별도 클래스. 비대상은 원 NS, 대상만 독립 head norm/.mT를 사용한다."""
    def __init__(self, params, targets, **kwargs):
        params = list(params)
        flattened = [parameter for item in params for parameter in (item['params'] if isinstance(item, dict) else [item])]
        if len({id(p) for p in flattened}) != len(flattened): raise ValueError('optimizer 소유권이 중복됐다')
        super().__init__(params, **kwargs)
        self.targets = {id(spec.parameter): spec for spec in targets}
        if len(self.targets) != len(targets): raise ValueError('중복 target Parameter identity다')
        if len({spec.name for spec in targets}) != len(targets): raise ValueError('등록 target 이름이 중복됐다')
        parameters = [p for group in self.param_groups for p in group['params']]
        if len({id(p) for p in parameters}) != len(parameters): raise ValueError('optimizer 소유권이 중복됐다')
        if any(key not in {id(p) for p in parameters} for key in self.targets): raise ValueError('target이 optimizer에 없다')
        if any(p.dtype != torch.float32 for p in parameters): raise ValueError('FP32 master 행렬만 사용한다')
        if any(tuple(spec.parameter.shape) != (spec.heads * spec.head_dim, spec.width) for spec in targets):
            raise ValueError('target 등록 shape/head 단위가 다르다')
        self.headwise_counts = {spec.name: 0 for spec in targets}; self.actual_steps = 0

    @torch.no_grad()
    def step(self, closure=None):
        loss = closure() if closure is not None else None
        for group in self.param_groups:
            momentum, ns, wd = group['momentum'], group['ns_steps'], group['weight_decay']
            for parameter in group['params']:
                if parameter.grad is None: continue
                state = self.state[parameter]
                if 'buf' not in state: state['buf'] = torch.zeros_like(parameter.grad)
                buf = state['buf']; buf.mul_(momentum).add_(parameter.grad)
                update = parameter.grad.add(buf, alpha=momentum) if group['nesterov'] else buf
                spec = self.targets.get(id(parameter))
                if spec is None: update = original_ns(update, steps=ns)
                else:
                    update = headwise_ns(update, spec.heads, spec.head_dim, steps=ns)
                    self.headwise_counts[spec.name] += 1
                scale = update_scale(parameter.size(0), parameter.size(1), group.get('scale_mode', 'jordan'))
                if wd: parameter.mul_(1 - group['lr'] * wd)
                parameter.add_(update, alpha=-group['lr'] * scale)
        self.actual_steps += 1
        return loss


def validate_headwise_groups(groups):
    if not isinstance(groups, list) or len(groups) != 3: raise ValueError('실제 AdamW2+HeadwiseMuon1 group이 필요하다')
    for index, (group, pin) in enumerate(zip(groups, GROUP_PINS)):
        name = 'AdamW' if index < 2 else 'HeadwiseMuon'
        classes = ({torch.optim.AdamW.__module__ + '.' + torch.optim.AdamW.__qualname__} if index < 2 else
            {'__main__.HeadwiseMuon', 'scripts.diag_p106b_headwise_muon.HeadwiseMuon'})
        if (group.get('optimizer') != name or group.get('group') != (index if index < 2 else 0)
                or (group.get('parameters'), group.get('names_sha256')) != pin
                or group.get('lr') != (5e-5 if index < 2 else 2e-4)
                or group.get('runtime_lr') != (1e-4 if index < 2 else 4e-4)
                or group.get('lr_multiplier') != .5 or group.get('weight_decay') != 0.
                or group.get('runtime_weight_decay') != (.1 if index == 0 else 0.)
                or group.get('scale_mode') != (None if index < 2 else 'rms')
                or group.get('actual_class') not in classes):
            raise ValueError('실제 클래스/원 group 소유권/LR/WD/RMS가 다르다')


def idle_receipt(value, code_sha256, *, now=None, monotonic=None):
    now = datetime.now(timezone.utc) if now is None else now
    monotonic = time.monotonic() if monotonic is None else monotonic
    if now.tzinfo is None: raise ValueError('현재 UTC 시각도 aware여야 한다')
    start, end = (datetime.fromisoformat(value[k]) for k in ('start_utc', 'end_utc'))
    ms, me = value.get('start_monotonic'), value.get('end_monotonic')
    if (value.get('schema') != 'P106B_ROOT_IDLE_V1' or value.get('tag') != TAG
            or value.get('code_sha256') != code_sha256 or start.tzinfo is None or end.tzinfo is None
            or (end - start).total_seconds() < 300 or not 0 <= (now - end).total_seconds() <= 600
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in (ms, me, monotonic))
            or me - ms < 300 or not 0 <= monotonic - me <= 600
            or value.get('no_gpu_work') is not True or value.get('no_heavy_cpu') is not True
            or not isinstance(value.get('evidence'), list) or not value['evidence']):
        raise ValueError('동일 source/tag와 root의 UTC·monotonic5분 유휴/끝600초이내 근거가 필요하다')
    for item in value['evidence']:
        if (not isinstance(item, dict) or not isinstance(item.get('path'), str)
                or not isinstance(item.get('sha256'), str) or len(item['sha256']) != 64
                or any(ch not in '0123456789ABCDEF' for ch in item['sha256'])):
            raise ValueError('root 실제 조회 근거 경로/SHA가 필요하다')
        candidate = Path(item['path'])
        candidate = candidate if candidate.is_absolute() else ROOT / candidate
        if ('..' in candidate.parts or not candidate.is_relative_to(ROOT)
                or candidate.is_relative_to(ROOT / 'datasets/TinyDataset')
                or any(part in ('.aws', '.claude') for part in candidate.relative_to(ROOT).parts)):
            raise ValueError('유휴 근거도 보호 데이터/외부 경로를 읽지 않는다')
    return dict(value, scope='ROOT_OBSERVED_IDLE_DECLARATION_NOT_CONTINUOUS_PEAK_SAFETY')


def validate_locked_reports(parent, control):
    if (parent.get('checkpoint_sha256') != PARENT_SHA or parent.get('final_core_sha256') != PARENT_CORE
            or control.get('checkpoint_sha256') != BASELINE_SHA or control.get('final_core_sha256') != BASELINE_CORE
            or control.get('parent_checkpoint_sha256') != PARENT_SHA or control.get('initial_core_sha256') != PARENT_CORE
            or control.get('totals') != TOTALS or parent.get('clip') != 1. or control.get('clip') != 1.):
        raise ValueError('잠긴 원 float 부모/기준선/clip1/실제 분모가 다르다')


def source_contract(frozen, cases, source_arm='varied_balanced'):
    exposure = frozen['exposure'][source_arm]
    if (len(exposure) != 4 or sum(x['counts']['x_tokens'] for x in exposure) != TOTALS['x_tokens']
            or sum(x['counts']['assistant_targets'] for x in exposure) != TOTALS['targets']
            or any(len(x['update_target_denominators']) != 96 or sum(x['update_target_denominators']) != x['counts']['assistant_targets'] for x in exposure)
            or len(frozen['native_train_offsets']) != 3072 or len(cases) != 1694
            or len({case['id'] for case in cases}) != 1694):
        raise ValueError('원4pass 입력/target/native/cases 전체를 유지해야 한다')
    return dict(source_exposure_sha256=sha(exposure), native_offsets_sha256=sha(frozen['native_train_offsets']),
        cases_sha256=sha(cases), totals=TOTALS)


def resource_forecast(times, baseline_eval_seconds, prepare_seconds, spent, training_remaining, total_remaining, completed=False):
    if (len(times) != 8 or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in times)
            or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in
                   (baseline_eval_seconds, prepare_seconds, spent, training_remaining, total_remaining))):
        raise ValueError('실제 cost8/기준선평가/CPU준비의 유한한 초 단위가 필요하다')
    prediction = 0. if completed else times[0] + max(times[1:]) * 383 * 1.35 + 300
    evaluation, readback = baseline_eval_seconds * 1.35, prepare_seconds * 1.35
    needed = prediction + evaluation + readback + 600
    return dict(estimates_seconds={'float_sft': prediction}, baseline_eval_resource_seconds=baseline_eval_seconds,
        evaluation_reserve_seconds=evaluation, readback_reserve_seconds=readback,
        final_record_reserve_seconds=600, spent_seconds=spent, needed_seconds=needed,
        fits=spent + needed <= 3600 and prediction <= training_remaining and needed <= total_remaining)


BODY_NAMES = ('train', 'evaluate', 'backward_micro', 'native_records', 'native_probe', 'cache_audit',
    'update_contract', 'read_events', 'validate_cpu_state', 'validate_payload', 'route_receipt',
    'optimizer_receipt', 'actual_lrs', 'validate_route_receipt', 'validate_native32')
BINDINGS = frozenset(('TAG', 'SCHEMA', 'CACHE', 'RAW', 'EVIDENCE', 'END', 'TRAIN_STOP', 'ACTIVE_LIMIT',
    'ARMS', 'ENDPOINTS', 'CODE', 'OWN_CODE', 'info', 'phase_key', 'source_state', 'prepare', 'prepared',
    'checkpoint', 'train_report', 'routed_runtime', 'make_optimizers', 'validate_optimizer_groups',
    'cp_experiment', 'budget', 'spent_seconds', 'validate_activity'))


def _private(relative, data):
    module = types.ModuleType('_p106b_headwise_' + uuid.uuid4().hex); module.__file__ = str(ROOT / relative)
    exec(compile(data, str(ROOT / relative), 'exec', dont_inherit=True), vars(module))
    return module


def build_runtime():
    code = checked_code()
    utility = importlib.import_module('scripts.diag_p106b_route_cross_resume')
    original = importlib.import_module('scripts.diag_p106b_native_weight_route')
    resume_module = importlib.import_module('scripts.diag_p106b_native_resume')
    baseline = resume_module.build_runtime()
    p = _private(SOURCE, code[SOURCE])
    guards = [utility.ModuleGuard(m) for m in (original, baseline, resume_module)]
    pristine = dict(vars(p)); captured = types.MappingProxyType({name: getattr(p, name) for name in
        (*BODY_NAMES, 'train_report', 'make_optimizers', 'routed_runtime', 'cp_experiment', 'validate_activity')})
    captured_identity = dict(captured)
    captured_parity = {name: utility.body_sha(function) for name, function in captured.items()}
    parity = {name: utility.body_sha(getattr(p, name)) for name in BODY_NAMES}
    scientific_functions = {'headwise_ns': headwise_ns, 'HeadwiseMuon.step': HeadwiseMuon.step,
        'collect_targets': collect_targets, 'original_ns': original_ns, 'Muon.step': Muon.step}
    scientific_parity = {name: utility.body_sha(function) for name, function in scientific_functions.items()}
    expected, audit = {}, {}
    state = dict(optimizers=None, idle_proof=None, mode=None)
    readers = []

    def unchanged():
        for guard in guards: guard.check()
        baseline._resume_assert_unchanged()
        if any(getattr(p, k) is not v for k, v in pristine.items() if k not in BINDINGS):
            raise ValueError('private native의 변경 allowlist 밖 전역이 바뀌었다')
        if any(getattr(p, k) is not v for k, v in expected.items()): raise ValueError('허용 binding 객체가 바뀌었다')
        if set(vars(p)) - set(pristine) != set(audit): raise ValueError('미등록 감사 전역이다')
        if any(getattr(p, k) is not v for k, v in audit.items()): raise ValueError('감사 참조가 바뀌었다')
        if any(utility.body_sha(getattr(p, k)) != v for k, v in parity.items()): raise ValueError('원 수치본문이 바뀌었다')
        for name, function in captured.items():
            if (function is not captured_identity[name] or utility.body_sha(function) != captured_parity[name]
                    or inspect.unwrap(function).__globals__ is not vars(p)):
                raise ValueError('동결 본문/captured 참조/globals가 바뀌었다')
        current_scientific = {'headwise_ns': headwise_ns, 'HeadwiseMuon.step': HeadwiseMuon.step,
            'collect_targets': collect_targets, 'original_ns': original_ns, 'Muon.step': Muon.step}
        for name, function in current_scientific.items():
            if (inspect.unwrap(function) is not inspect.unwrap(scientific_functions[name])
                    or utility.body_sha(function) != scientific_parity[name]):
                raise ValueError('NS/optimizer 과학 본문 또는 참조가 바뀌었다')
        for reader, snapshot, bodies in readers:
            if set(vars(reader)) != set(snapshot) or any(getattr(reader, k) is not v for k, v in snapshot.items()):
                raise ValueError('독립 평가 reader의 globals가 바뀌었다')
            if any(utility.body_sha(getattr(reader, name)) != value for name, value in bodies.items()):
                raise ValueError('독립 평가 reader의 본문이 바뀌었다')

    def info():
        for guard in guards: guard.check()
        value = dict(original.info())
        pins = {name: file_sha(ROOT / name) if (ROOT / name).is_file() else 'NOT_CREATED' for name in p.CODE}
        value.update(schema=SCHEMA, tag=TAG, arms=['float'], code_sha256=pins, code_complete='NOT_CREATED' not in pins.values(),
            authority_end_utc=END.isoformat(), training_stop_utc=TRAIN_STOP.isoformat(), stage_active_limit_seconds=3600,
            parent_sha256_role='OLD_P090B_GEOMETRY_ONLY_NOT_CURRENT_INITIAL_WEIGHTS',
            actual_parent_checkpoint_sha256=PARENT_SHA, actual_parent_core_sha256=PARENT_CORE,
            actual_baseline_checkpoint_sha256=BASELINE_SHA, actual_baseline_core_sha256=BASELINE_CORE,
            parent_training_weights_copied=True, initializer='EXACT_COMPLETED_FLOAT_NATIVE_PARENT',
            baseline_policy='READ_ONLY_ORIGINAL_RESUME_V2_NOT_RETRAINED_NOT_RETAGGED',
            headwise_targets=target_geometry(), headwise_targets_sha256=sha(target_geometry()),
            headwise_class='HeadwiseMuon', ns_steps=5, momentum=.95, nesterov=True, ns_eps=1e-7,
            rms_scale_policy='ORIGINAL_2D_PARAMETER_SHAPE', clip=1.,
            sft_actual_totals=TOTALS, sft_padded_slots=384 * 128 * 1024,
            binding_allowlist=sorted(BINDINGS), computational_body_sha256=parity, pinned_code=CODE_PINS,
            captured_body_sha256=captured_parity, scientific_body_sha256=scientific_parity,
            pinned_reports=REPORT_PINS, f4_sha256=file_sha(F4),
            idle_policy='ROOT_UTC_AND_MONOTONIC300S_END_FRESH600S_RECHECK_BEFORE_PARENT_MODEL',
            active_accounting='OWN_ACTUAL_WORKERS_ONCE_BASELINE_RESOURCE_ONLY',
            comparison='SAME_FLOAT_NATIVE_SFT384_ONLY_QK_NS_UNIT_DIFFERS', new_corpus=False)
        value.update(new_native_updates=0, native_training_fields_scope='PRIOR_PARENT_HISTORY_NOT_NEW_TRAINING',
            new_sft_updates=384, total75m_complete=False, native_worker_limit_seconds=None,
            headwise_worker_limit_seconds=3600, unmeasured_sft_reserve_seconds=0., finish_reserve_seconds=None,
            finish_reserve_policy='BASELINE_EVAL_WALLx1.35_PLUS_OWN_PREPARE_WALLx1.35_PLUS_RECORD600',
            active_excludes=['wrapper', 'regression', 'readonly_source_preflight', 'readonly_post_verify', 'root_idle'],
            wall_scope='INDIVIDUAL_WORKER_NOT_WRAPPER_TOTAL', torch_version=str(torch.__version__),
            completion_policy='WORKER_CLOSE_THEN_READONLY_VERIFY_CHILD_BEFORE_PIPELINE_COMPLETE',
            readonly_budget_policy='ABSOLUTE_UTC_AND_DECLARED_CAP_ONLY_NOT_FAMILY_BALANCE',
            query_strata_policy='LANE_SPLIT_LANGUAGE_FAMILY_SOURCE_QUERY_ID_CANONICAL_QUERY_ARITHMETIC_OP')
        return value

    def phase_key(mode, arm=None, endpoint=None):
        if mode in ('source', 'prepare', 'preflight', 'readback') and arm is None and endpoint is None: return mode
        if mode in ('sft_cost', 'sft') and arm == 'float' and endpoint is None: return 'cost' if mode == 'sft_cost' else 'train'
        if mode == 'budget' and arm is None and endpoint == 'sft': return 'budget'
        if mode == 'evaluate' and arm == 'float' and endpoint == 'sft': return 'evaluate'
        raise ValueError('전용 float-SFT384 외의 native 재학습/다른 경로를 허용하지 않는다')

    def parent_and_baseline():
        for name, expected_sha in REPORT_PINS.items():
            if p.digest(ROOT / name) != expected_sha: raise ValueError('원 부모/기준선 report bytes가 다르다')
        parent, control = original.train_report('train', 'float'), baseline.train_report('sft', 'float')
        validate_locked_reports(parent, control)
        return parent, control

    def source_state():
        unchanged()
        reference, frozen, cases, offsets = baseline.prepared()
        parent, control = parent_and_baseline()
        exposure = frozen['exposure'][p.SOURCE_ARM]
        consumer = source_contract(frozen, cases, p.SOURCE_ARM)
        binding = dict(source_tag=baseline.TAG, source_reference_sha256=p.digest(baseline.CACHE / 'frozen_reference.json'),
            source_cpu_contract_sha256=p.digest(baseline.EVIDENCE / 'cpu_contract.json'),
            source_binding_sha256=p.sha(reference['binding']), frozen_manifests_sha256=p.sha(frozen['manifests']),
            source_exposure_sha256=p.sha(exposure), native_offsets_sha256=p.sha(frozen['native_train_offsets']),
            cases_sha256=p.sha(cases), totals=TOTALS, parent_report_sha256=REPORT_PINS[PARENT_REPORT],
            baseline_report_sha256=REPORT_PINS[BASELINE_REPORT], parent_checkpoint_sha256=parent['checkpoint_sha256'],
            parent_core_sha256=parent['final_core_sha256'], baseline_checkpoint_sha256=control['checkpoint_sha256'])
        if any(binding[k] != v for k, v in consumer.items()): raise ValueError('source consumer hash가 다르다')
        return reference, frozen, cases, offsets, binding

    def prepare():
        p.authority(True)
        if any(p.safe(path).exists() for path in (p.CACHE, p.RAW, p.EVIDENCE)):
            raise FileExistsError('완료/부분 headwise namespace를 보존한다')
        reference, _, cases, _, binding = source_state()
        value = dict(info(), status='HEADWISE_CPU_BRIDGE_PREPARED', binding=binding, display_ids=reference['display_ids'],
            models_loaded=0, checkpoint_tensor_loads=0, optimizer_updates=0, checkpoint_writes=0)
        for path in (p.CACHE, p.RAW, p.EVIDENCE): path.mkdir(parents=True, exist_ok=False)
        p.write(p.CACHE / 'frozen_reference.json', value)
        p.write(p.EVIDENCE / 'cpu_contract.json', dict(value, reference_sha256=p.digest(p.CACHE / 'frozen_reference.json')))
        return 0

    def prepared():
        reference, frozen, cases, offsets, binding = source_state()
        own = p.required(p.CACHE / 'frozen_reference.json')
        value = dict(info(), status='HEADWISE_CPU_BRIDGE_PREPARED', binding=binding, display_ids=reference['display_ids'],
            models_loaded=0, checkpoint_tensor_loads=0, optimizer_updates=0, checkpoint_writes=0)
        if own != value or p.required(p.EVIDENCE / 'cpu_contract.json') != dict(value, reference_sha256=p.digest(p.CACHE / 'frozen_reference.json')):
            raise ValueError('전체 info/동결원천/코드 bridge가 다르다')
        p.completed_activity('prepare')
        return own, frozen, cases, offsets

    def checkpoint(arm, endpoint):
        if arm != 'float' or endpoint != 'sft': raise ValueError('자기 float-SFT CP만 지정한다')
        return ROOT / 'runs/ckpt' / ('m100s10_ko-en_' + TAG + '_float_sft.pt')

    def make_optimizers(model, endpoint):
        if endpoint != 'sft': raise ValueError('native optimizer는 만들지 않는다')
        targets = collect_targets(model)
        (adam, old_muon), control_groups = original.make_optimizers(model, endpoint)
        if any(old_muon.state.values()) or any(adam.state.values()): raise ValueError('동일 fresh optimizer reset이 필요하다')
        cloned_groups = [dict(group, params=list(group['params'])) for group in old_muon.param_groups]
        muon = HeadwiseMuon(cloned_groups, targets, lr=2e-4, momentum=.95, nesterov=True,
            ns_steps=5, weight_decay=0., scale_mode='rms')
        groups = p.optimizer_receipt(model, (adam, muon))
        groups = [dict(current, runtime_lr=control['runtime_lr'], runtime_weight_decay=control['runtime_weight_decay'],
            lr_multiplier=.5, actual_class=type(opt).__module__ + '.' + type(opt).__qualname__)
            for current, control, opt in zip(groups, control_groups, (adam, adam, muon))]
        validate_headwise_groups(groups)
        if any(group.get('momentum') != .95 or group.get('nesterov') is not True or group.get('ns_steps') != 5 for group in muon.param_groups):
            raise ValueError('원 momentum/Nesterov/5NS를 유지해야 한다')
        state['optimizers'] = (adam, muon)
        return (adam, muon), groups

    def validate_optimizer_groups(groups, endpoint):
        if endpoint != 'sft': raise ValueError('새 HeadwiseMuon은 SFT 전용이다')
        validate_headwise_groups(groups)
        return p.actual_lrs(groups)

    def execution_stats(count):
        if state['optimizers'] is None: raise ValueError('실제 optimizer 객체가 없다')
        opt = state['optimizers'][1]
        if (type(opt) is not HeadwiseMuon or opt.actual_steps != count
                or opt.headwise_counts != {row['name']: count for row in target_geometry()}):
            raise ValueError('모든 Q14/K7 실제 headwise update가 완료되어야 한다')
        return dict(optimizer=type(opt).__name__, actual_class=type(opt).__module__ + '.' + type(opt).__qualname__,
            steps=opt.actual_steps, target_counts=opt.headwise_counts, target_geometry_sha256=sha(target_geometry()),
            non_target_ns='ORIGINAL_2D_FUNCTION', all_target_updates_verified=True)

    def cp_experiment(report):
        if report['endpoint'] != 'sft' or report['arm'] != 'float': raise ValueError('headwise float SFT metadata만 저장한다')
        if state['optimizers'] is not None: execution_stats(report['updates'])
        return dict(captured['cp_experiment'](report), headwise_method_sha256=sha(target_geometry()),
            optimizer_method='HeadwiseMuon_QK_NS5_ONLY_CLIP1')

    def train_report(mode, arm):
        if arm != 'float': raise ValueError('실수 경로만 읽는다')
        if mode == 'train': return parent_and_baseline()[0]
        if mode not in ('sft_cost', 'sft'): raise ValueError('등록된 headwise cost/train report가 필요하다')
        report = captured['train_report'](mode, arm)
        audit_path = p.EVIDENCE / ('headwise_' + phase_key(mode, arm) + '.json')
        stats = p.required(audit_path); expected_count = 8 if mode == 'sft_cost' else 384
        if (stats.get('tag') != TAG or stats.get('report_sha256') != p.digest(p.result_path(phase_key(mode, arm)))
                or stats.get('code_sha256') != info()['code_sha256'] or stats.get('steps') != expected_count
                or stats.get('target_counts') != {row['name']: expected_count for row in target_geometry()}
                or stats.get('all_target_updates_verified') is not True or stats.get('optimizer') != 'HeadwiseMuon'
                or not isinstance(stats.get('actual_class'), str) or stats['actual_class'].split('.')[-1] != 'HeadwiseMuon'
                or stats.get('target_geometry_sha256') != sha(target_geometry())):
            raise ValueError('실제 HeadwiseMuon 업데이트/보고서 결합이 다르다')
        if mode == 'sft' and report['totals'] != TOTALS: raise ValueError('전체 실제 노출 분모가 다르다')
        return report

    @contextmanager
    def routed_runtime(arm, endpoint=None):
        if arm != 'float' or endpoint not in ('native', 'sft'): raise ValueError('정확한 float 부모/자식 경로가 필요하다')
        if endpoint == 'native':
            if state['mode'] not in ('cost', 'train'): raise ValueError('원 부모는 새 SFT 초기화에만 쓴다')
            if state['mode'] == 'cost':
                proof_path = state['idle_proof']
                if proof_path is None: raise ValueError('모델 전 root idle-proof가 필요하다')
                proof_path = p._headwise.own_reader.safe(ROOT / proof_path)
                proof = idle_receipt(p.required(proof_path), info()['code_sha256'])
                for evidence in proof['evidence']:
                    path = p._headwise.own_reader.safe(ROOT / evidence['path'])
                    if p.digest(path) != evidence['sha256']: raise ValueError('유휴 actual 조회 근거 SHA가 다르다')
                p.write(p.EVIDENCE / 'cost_idle_receipt.json', dict(proof, proof_sha256=p.digest(proof_path)))
            loader = original.routed_runtime
        else: loader = captured['routed_runtime']
        p.execution_remaining(state['mode'] in ('cost', 'train'))
        try:
            with loader(arm, endpoint) as values: yield values
        finally: unchanged()

    def validate_activity(value, key, complete=False):
        result = captured['validate_activity'](value, key, complete)
        if (type(value.get('worker_pid')) is not int or value['worker_pid'] <= 0
                or value.get('worker_pgid') != value['worker_pid'] or value['max_wall_sec'] > 3600):
            raise ValueError('자기 PGID와 headwise family3600 상한이 필요하다')
        return result

    def spent_seconds():
        total = 0.
        if p.EVIDENCE.exists():
            for path in p.EVIDENCE.glob('activity_*.json'):
                value = p.required(path); key = value.get('key')
                if path.name != 'activity_' + str(key) + '.json': raise ValueError('activity 식별자가 다르다')
                p.validate_activity(value, key)
                if value['complete']: p.completed_activity(value['mode'], value.get('arm'), value.get('endpoint'))
                result, reference = p.result_path(key), p.CACHE / 'frozen_reference.json'
                if (value.get('result_sha256') != (p.digest(result) if result.is_file() else None)
                        or value.get('reference_sha256') != (p.digest(reference) if reference.is_file() else None)):
                    raise ValueError('실패/완료 activity의 실제 report/reference SHA가 다르다')
                total += value['seconds']
        return total

    def budget(endpoint, record=False):
        if endpoint != 'sft': raise ValueError('SFT 예산만 편성한다')
        prepared(); cost = train_report('sft_cost', 'float')
        activity = baseline.completed_activity('evaluate', 'float', 'sft')
        eval_path = baseline.result_path(baseline.phase_key('evaluate', 'float', 'sft'))
        evaluation = baseline.required(eval_path)
        if (evaluation.get('status') != 'ACTUAL_ANSWERS_COLLECTED' or evaluation.get('actual_cases') != 1694
                or evaluation.get('checkpoint_sha256') != BASELINE_SHA or evaluation.get('core_before') != BASELINE_CORE
                or evaluation.get('core_after') != BASELINE_CORE):
            raise ValueError('예산에도 정확한 기존 float SFT1694 실제 평가를 참조해야 한다')
        completed = p.result_path('train').exists()
        if completed: train_report('sft', 'float')
        forecast = resource_forecast(cost['step_seconds'], activity['seconds'], p.completed_activity('prepare')['seconds'],
            spent_seconds(), p.authority(True), p.authority(), completed)
        value = dict(info(), status='HEADWISE_RESOURCE_FORECAST', endpoint='sft', **forecast,
            baseline_eval_activity_sha256=p.digest(baseline.EVIDENCE / 'activity_evaluate_float_sft.json'),
            baseline_eval_report_sha256=p.digest(eval_path),
            scope='baseline timing is resource-only; same-day speed or quality is not inferred')
        if record: p.write(p.result_path('budget'), value)
        return value

    bindings = dict(TAG=TAG, SCHEMA=SCHEMA, CACHE=ROOT / 'data_cache' / TAG, RAW=ROOT / 'runs/eval' / TAG,
        EVIDENCE=ROOT / 'test_result/evidence' / TAG, END=END, TRAIN_STOP=TRAIN_STOP, ACTIVE_LIMIT=3600,
        ARMS=('float',), ENDPOINTS=('sft',), CODE=tuple(sorted(set((*original.CODE, *baseline.CODE, *CODE_PINS, SCRIPT, TEST)))),
        OWN_CODE=(SCRIPT, TEST), info=info, phase_key=phase_key, source_state=source_state, prepare=prepare,
        prepared=prepared, checkpoint=checkpoint, train_report=train_report, routed_runtime=routed_runtime,
        make_optimizers=make_optimizers, validate_optimizer_groups=validate_optimizer_groups,
        cp_experiment=cp_experiment, budget=budget, spent_seconds=spent_seconds, validate_activity=validate_activity)
    if set(bindings) != BINDINGS: raise ValueError('정확한 private binding allowlist가 필요하다')
    for name, value in bindings.items(): setattr(p, name, value)
    expected.update(bindings)
    own_reader, baseline_reader = _private(CROSS, code[CROSS]), _private(CROSS, code[CROSS])
    own_reader.n, baseline_reader.n = p, baseline
    readers.extend((reader, dict(vars(reader)), {name: utility.body_sha(value) for name, value in vars(reader).items()
        if inspect.isfunction(value)}) for reader in (own_reader, baseline_reader))
    p._headwise = RuntimeAudit(check=unchanged, original=original, baseline=baseline, captured=captured,
        state=state, execution_stats=execution_stats, own_reader=own_reader, baseline_reader=baseline_reader)
    audit['_headwise'] = p._headwise
    unchanged()
    return p


def finish_training(p, *, cost, max_wall_sec):
    key = 'cost' if cost else 'train'
    audit = p.EVIDENCE / ('headwise_' + key + '.json')
    if audit.exists(): raise FileExistsError('기존 실제 optimizer receipt를 보존한다')
    try:
        code = p.train('float', 'sft', cost, max_wall_sec)
        if code != 0: raise ValueError('완료한 원 train 본문의 종료0이 필요하다')
        receipt = p._headwise.execution_stats(8 if cost else 384)
        p.write(audit, dict(receipt, tag=TAG, code_sha256=p.info()['code_sha256'],
            report_sha256=p.digest(p.result_path(key))))
        # strict reader는 현재 worker의 완료 activity를 요구한다. finally가 닫은 뒤
        # 별도 readonly VERIFY child만 호출한다. 성공 activity를 앞당겨 만들지 않는다.
        return 0
    finally:
        p._headwise.state['optimizers'] = None


def query_strata(cases, baseline_answers, headwise_answers):
    if ([row['id'] for row in baseline_answers] != [case['id'] for case in cases]
            or [row['id'] for row in headwise_answers] != [case['id'] for case in cases]):
        raise ValueError('query 보조표도 같은 ordered 문항 원형이어야 한다')
    cells = {}
    for case, left, right in zip(cases, baseline_answers, headwise_answers):
        problem = case.get('problem') or {}
        query = json.loads(json.dumps(problem.get('query', {}), ensure_ascii=False, sort_keys=True, allow_nan=False))
        query_id = case.get('query_id')
        if query_id is None: query_id = problem.get('query_id')
        split = case.get('split')
        if split is None: split = problem.get('split', 'NOT_DECLARED')
        operation = (problem.get('state') or {}).get('op')
        identity = query_id if query_id is not None else dict(fallback_case_id=case['id'])
        labels = (case['lane'], split, case['language'], case['family'])
        key = (*[json.dumps(label, ensure_ascii=False, sort_keys=True) for label in labels],
            json.dumps(identity, sort_keys=True, ensure_ascii=False),
            json.dumps(query, sort_keys=True, ensure_ascii=False), json.dumps(operation))
        cell = cells.setdefault(key, dict(lane=case['lane'], split=split, language=case['language'],
            family=case['family'], query_id=query_id, fallback_case_id=case['id'] if query_id is None else None,
            canonical_query=query, arithmetic_op=operation,
            n=0, scored=0, baseline=0, headwise=0, baseline_only=0, headwise_only=0))
        cell['n'] += 1
        a, b = left['metrics']['correct'], right['metrics']['correct']
        if type(a) is bool and type(b) is bool:
            cell['scored'] += 1; cell['baseline'] += a; cell['headwise'] += b
            cell['baseline_only'] += a and not b; cell['headwise_only'] += b and not a
    return [cells[key] for key in sorted(cells)]


def paired_readback(p):
    reference, _, cases, _ = p.prepared()
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(p.TOKENIZER))
    baseline = p._headwise.baseline
    old_training = baseline.train_report('sft', 'float')
    new_training = p.train_report('sft', 'float')
    old_report, old_answers, old_summary = p._headwise.baseline_reader.diagonal(
        'float', 'sft', old_training, cases, tok)
    new_report, new_answers, new_summary = p._headwise.own_reader.diagonal(
        'float', 'sft', new_training, cases, tok)
    contrasts = p._headwise.own_reader.paired(old_answers, new_answers, cases)
    queries = query_strata(cases, old_answers, new_answers)
    users = [case['id'] for case in cases if case['lane'] == 'user_seen']
    shown = set(reference['display_ids'][:8]) | set(users)
    for case, left, right in zip(cases, old_answers, new_answers):
        if case['id'] in shown:
            print('[HEADWISE_PAIRED_SAMPLE] ' + json.dumps(dict(id=case['id'], language=case['language'],
                family=case['family'], messages=case['messages'], baseline=left['answer'], headwise=right['answer'],
                baseline_finish=left['generation']['finish_reason'], headwise_finish=right['generation']['finish_reason']),
                ensure_ascii=False), flush=True)
    p.write(p.result_path('readback'), dict(p.info(), status='HEADWISE_BASELINE_PAIRED_RAW_RECOUNTED',
        actual_cases=len(cases), baseline_origin='EXACT_OLD_RESUME_V2_NOT_RETAGGED',
        baseline_evaluate_report_sha256=p.digest(baseline.result_path(baseline.phase_key('evaluate', 'float', 'sft'))),
        own_evaluate_report_sha256=p.digest(p.result_path('evaluate')), baseline_summary=old_summary,
        headwise_summary=new_summary, paired=contrasts, query_strata=queries, display_ids=sorted(shown),
        baseline_native32=old_report['native32_fp32'], headwise_native32=new_report['native32_fp32'],
        models_loaded=0, checkpoint_tensor_loads=0, checkpoints_written=0,
        scope='single-seed same-parent SFT NS-unit observation; not general intelligence or full DeepSeek reproduction'))
    return 0


def phase_commands(mode, max_wall_sec, idle_proof=None):
    if mode not in MODES or type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 3600:
        raise ValueError('등록 mode와60..3600초 상한이 필요하다')
    if idle_proof is not None and mode != 'cost': raise ValueError('idle-proof는 실제 cost에서만 사용한다')
    py = [sys.executable, '-B', '-X', 'utf8']; base = py + [SCRIPT]
    execute = base + ['--mode', mode, '--max-wall-sec', str(max_wall_sec), '--worker', '--execute']
    if idle_proof is not None: execute += ['--idle-proof', str(idle_proof)]
    return [('REGRESSION', py + ['-m', 'unittest', TEST[:-3].replace('/', '.'), '-v']),
        ('PREFLIGHT', base + ['--mode', 'source' if mode in ('source', 'prepare') else 'preflight',
            '--worker', '--execute', '--max-wall-sec', '600']), ('EXECUTE', execute)]


def worker(p, mode, max_wall_sec, idle_proof=None):
    phase_commands(mode, max_wall_sec, idle_proof)
    pid, pgid = os.getpid(), os.getpgid(os.getpid())
    if pid != pgid: raise ValueError('자기 PGID worker가 필요하다')
    p._headwise.check()
    p._headwise.state.update(mode=mode, idle_proof=idle_proof)
    readonly = mode in ('source', 'preflight')
    training = mode in ('prepare', 'cost', 'train')
    key = mode
    internal = 'sft_cost' if mode == 'cost' else 'sft' if mode == 'train' else mode
    arm = 'float' if mode in ('cost', 'train', 'evaluate') else None
    endpoint = 'sft' if mode in ('budget', 'evaluate') else None
    activity = p.EVIDENCE / ('activity_' + key + '.json')
    if not readonly and activity.exists(): raise FileExistsError('완료/실패 activity를 보존한다')
    metadata = p.info(); start = datetime.now(timezone.utc).isoformat(); began = time.perf_counter()
    code, error = 9, None
    try:
        from scripts.p106b_gate_runtime import wall_limit
        with p.termination_guard(), wall_limit(max_wall_sec):
            available = p.execution_remaining(training)
            if not readonly: available = min(available, 3600 - p.spent_seconds() - 600)
            if max_wall_sec > available:
                raise p.Pending('readonly cap이 절대UTC/기록 예비를 넘는다' if readonly else
                    '전체 family3600/기록600 및 절대 권한에 worker가 들어가야 한다')
            if mode == 'source': p.source_state(); code = 0
            elif mode == 'preflight': p.prepared(); code = 0
            elif mode == 'prepare':
                code = p.prepare()
                p.write(p.result_path(key), dict(status='HEADWISE_CPU_BRIDGE_COMPLETE',
                    reference_sha256=p.digest(p.CACHE / 'frozen_reference.json')))
            elif mode in ('cost', 'train'): code = finish_training(p, cost=mode == 'cost', max_wall_sec=max_wall_sec)
            elif mode == 'budget':
                forecast = p.budget('sft', record=True)
                if not forecast['fits']: raise p.Pending('실측 기반 train/eval/readback/기록 예비가 예산을 넘는다')
                code = 0
            elif mode == 'evaluate': code = p.evaluate('float', 'sft')
            elif mode == 'readback': code = paired_readback(p)
            if code != 0 or (not readonly and not p.result_path(key).is_file()):
                raise ValueError('성공에는 실제 종료0과 닫힌 자기 report가 필요하다')
            if metadata['code_sha256'] != p.info()['code_sha256']:
                raise ValueError('worker 시작/종료 사이 source SHA가 바뀌었다')
        return 0
    except BaseException as exc:
        error = type(exc).__name__
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (p.Pending, FileNotFoundError, FileExistsError)) else 9
        raise
    finally:
        if not readonly:
            result, reference = p.result_path(key), p.CACHE / 'frozen_reference.json'
            p.write(activity, dict(schema=p.SCHEMA, tag=p.TAG, key=key, mode=internal, cli_mode=mode, arm=arm, endpoint=endpoint,
                seconds=time.perf_counter() - began, started_at=start, ended_at=datetime.now(timezone.utc).isoformat(),
                max_wall_sec=max_wall_sec, worker_pid=pid, worker_pgid=pgid, returncode=code, complete=code == 0,
                error_type=error, code_sha256=metadata['code_sha256'], result_sha256=p.digest(result) if result.is_file() else None,
                reference_sha256=p.digest(reference) if reference.is_file() else None))
        p._headwise.state.update(mode=None, idle_proof=None, optimizers=None)
        p._headwise.check()


class VerificationError(RuntimeError):
    """이미 종료한 worker의 후행 검산 실패. 새 학습 미실행/HOLD로 바꾸지 않는다."""


def verify_training(p, mode, max_wall_sec):
    if mode not in ('cost', 'train') or type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 3600:
        raise VerificationError('bounded cost/train 후행 검산만 허용한다')
    stage = 'VERIFY_' + mode.upper()
    try:
        p._headwise.check()
        if os.getpgid(os.getpid()) != os.getpid(): raise ValueError('readonly verifier도 자기 PGID가 필요하다')
        if max_wall_sec > p.execution_remaining(): raise ValueError('readonly 검산 cap이 절대UTC/기록 예비를 넘는다')
        from scripts.p106b_gate_runtime import wall_limit
        with p.termination_guard(), wall_limit(max_wall_sec):
            report = p.train_report('sft_cost' if mode == 'cost' else 'sft', 'float')
            p.execution_remaining()
        value = dict(stage=stage, status='VERIFIED_CLOSED_WORKER', returncode=0, read_only=True,
            updates=report['updates'], report_sha256=p.digest(p.result_path(mode)),
            activity_sha256=p.digest(p.EVIDENCE / ('activity_' + mode + '.json')),
            scope='strict completed_activity/read_events/optimizer receipt; not model quality')
        print('[HEADWISE_VERIFY_RECEIPT] ' + json.dumps(value, ensure_ascii=False), flush=True)
        return 0
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)): raise
        print('[HEADWISE_VERIFY_RECEIPT] ' + json.dumps(dict(stage=stage, status='ERROR', returncode=9,
            read_only=True, original_error_type=type(exc).__name__, original_error=str(exc),
            scope='worker execution evidence preserved; post-execution strict verification failed'), ensure_ascii=False), flush=True)
        raise VerificationError(stage + ' failed after worker execution: ' + str(exc)) from exc
    finally:
        p._headwise.check()


def launch_stage(p, command, fallback_limit):
    """원3phase의 EXECUTE 안에서만 종료한 학습 worker와 readonly verifier를 직렬화한다."""
    cap = int(command[command.index('--max-wall-sec') + 1]) if '--max-wall-sec' in command else fallback_limit
    # execution_remaining은 절대UTC/기록 예비만 읽는다. 제외된 readonly에 family 잔량을 적용하지 않는다.
    result = p.launch(command, min(cap + 120, p.execution_remaining()))
    training_worker = ('--worker' in command and '--execute' in command and '--mode' in command
        and command[command.index('--mode') + 1] in ('cost', 'train'))
    if not training_worker: return result
    mode = command[command.index('--mode') + 1]
    verification_code, verification_invoked, error = None, False, None
    if result == 0:
        stage = 'VERIFY_' + mode.upper()
        print('[VERIFY_BEGIN] ' + stage + '; actual worker rc=0, closed activity required', flush=True)
        try:
            verify_cap = min(600, cap, int(p.execution_remaining()))
            if verify_cap < 60: raise VerificationError('종료 worker 뒤 readonly 검산의 절대UTC 여유가 부족하다')
            verify_command = [sys.executable, '-B', '-X', 'utf8', SCRIPT, '--mode', mode,
                '--verify-only', '--execute', '--max-wall-sec', str(verify_cap)]
            verification_invoked = True
            verification_code = p.launch(verify_command, min(verify_cap + 120, p.execution_remaining()))
        except KeyboardInterrupt:
            verification_code, error = 130, 'KeyboardInterrupt'
        except Exception as exc:
            verification_code, error = 9, type(exc).__name__ + ': ' + str(exc)
        print('[VERIFY_END] ' + stage + '; rc=' + str(verification_code), flush=True)
    final = result if result != 0 else 0 if verification_code == 0 else 130 if verification_code == 130 else 9
    print('[HEADWISE_EXECUTE_VERIFY_FINAL] ' + json.dumps(dict(mode=mode,
        worker_process_invoked=True, worker_returncode=result, worker_completed=result == 0,
        verification_invoked=verification_invoked, verification_returncode=verification_code,
        verification_error=error, returncode=final,
        status='EXECUTED_AND_VERIFIED' if final == 0 else 'WORKER_FAILED' if result != 0 else 'EXECUTED_VERIFY_FAILED',
        scope='actual worker execution and post-verification are separate; no scientific quality PASS'), ensure_ascii=False), flush=True)
    return final


def main(argv=None):
    p = None
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--mode', choices=MODES, required=True)
        parser.add_argument('--max-wall-sec', type=int, default=600)
        parser.add_argument('--worker', action='store_true'); parser.add_argument('--idle-proof', type=Path)
        parser.add_argument('--verify-only', action='store_true')
        action = parser.add_mutually_exclusive_group(required=True)
        action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
        args = parser.parse_args(argv)
        if args.verify_only and (not args.execute or args.worker or args.mode not in ('cost', 'train') or args.idle_proof is not None):
            raise ValueError('verify-only는 cost/train readonly child의 execute에만 쓴다')
        phases = phase_commands(args.mode, args.max_wall_sec, args.idle_proof)
        p = build_runtime()
        if args.check_only:
            print('[HEADWISE_CHECK_ONLY] ' + json.dumps(p.info(), ensure_ascii=False), flush=True); return 0
        if args.verify_only: return verify_training(p, args.mode, args.max_wall_sec)
        if args.worker: return worker(p, args.mode, args.max_wall_sec, args.idle_proof)
        return p.pipeline(phases, lambda command: launch_stage(p, command, args.max_wall_sec),
            lambda line: print(line, flush=True), experiment='P106B_HEADWISE_' + args.mode)['returncode']
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if (isinstance(exc, (FileNotFoundError, FileExistsError))
            or p is not None and isinstance(exc, p.Pending)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[HEADWISE_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
        return code
    finally:
        if p is not None: p._headwise.check()


if __name__ == '__main__':
    raise SystemExit(main())
