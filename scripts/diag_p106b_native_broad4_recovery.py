#!/usr/bin/env python3
"""원 native Q/F 부모에서 동결 Broad 두 pass를 같은 optimizer로 두 번 소비한다.

원352회 수치 본문은 private namespace에서 보존한다. 이 도구의704회는
자료·길이·감독량·native replay가 함께 바뀐 자료 패키지이며 양의 품질 판정이 아니다.
실물 준비/모델/GPU/원문 판독/Git은 root 소유다. check-only는 코드만 읽는다.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
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
SCRIPT, TEST = 'scripts/diag_p106b_native_broad4_recovery.py', 'scripts/test_p106b_native_broad4_recovery.py'
F4 = ROOT / 'handoff/audit/WIP_20261021_NATIVE_BROAD4_RECOVERY_F4.json'
NATIVE, BROAD, CORE, UTILITY = ('scripts/diag_p106b_native_weight_route.py',
    'scripts/diag_p106b_broad_resume.py', 'scripts/diag_p106b_broad_curriculum.py',
    'scripts/diag_p106b_route_cross_resume.py')
SOURCE_PINS = {
    NATIVE: 'E51B68024CA0DC24A4994FFF51C733C05BA2773E3038A2B1CC5C127F6C736FAE',
    BROAD: '54D0EA12CFA2E359D9E1D14250CB02B2894AD1B0581568AE9C768B50CDA8F8BF',
    CORE: '5DBA344FAE2D64A096B83D2161FB28C4E9EE6161B1042DBE0045CF0B4545E454',
    UTILITY: '1229A9033589BB17086747231AE5E6D9544A97BCA52A33FBE90CC4D1C0082C1D',
    'scripts/diag_p106b_relation_bind.py': 'CB02DBE956EE7858316A20339059DAD2F27F27E97E23C32B884633E54A455609',
    'scripts/p106b_weight_route.py': 'C2E77B6E8B3CD3338F853B0E5364BD41C9E3650091A11F652479494C55616187',
    'tinylm/train/muon.py': 'F2D81EF9903DC4BD2F9298BD65D3B210B1DE21141D22361A85A46F1DDE5F4676',
}
TAG, SCHEMA = 'p106b_native_broad4_recovery_v2_s1337', 'P106B_NATIVE_BROAD4_RECOVERY_V2'
END, TRAIN_STOP = datetime(2026, 10, 21, 8, tzinfo=timezone.utc), datetime(2026, 10, 21, 5, tzinfo=timezone.utc)
ARMS = ('ternary', 'float')
MODES = ('source', 'prepare', 'preflight', 'cost', 'budget', 'train', 'evaluate', 'readback')
ACTIVE_LIMIT, EVAL_RESERVE, RECORD_RESERVE, WORKER_LIMIT = 14400, 1200, 600, 7200
CYCLE_UPDATES, CYCLE_WINDOWS, UPDATES, WINDOWS, WIDTH = 352, 2816, 704, 5632, 1025
TOTAL_KEYS = ('positive_rows', 'x_tokens', 'assistant_targets', 'content_targets', 'eot_targets', 'native_targets')
EXPECTED = dict(positive_rows=90112, x_tokens=21621776, assistant_targets=2210436,
    content_targets=2092212, eot_targets=118224, native_targets=5767168)
EXPECTED_LANG = dict(ko=319808, en=1890628)
PARENTS = {
    'ternary': dict(sha256='AF3644F5AA515AC1C5E02154582396D080B77E7CD7827F0D32A9EB947ECE747C',
        core='68F8E780623C7699A411A6E35EDB9809C0911CD03AF719E60DBE4DA6582B6A6D'),
    'float': dict(sha256='FBC0AF70CDD9BAFD2011825B404BF336B138B21CBC137C0086833D7A1FDD9508',
        core='BE1DB16875AF5316EEB47167E6FD44CCCD0FF67F957DF05525748AC0FE4A6A6D')}
BODY_NAMES = ('train_updates', 'expected_group', 'dev_probe', 'emit_dialogue', 'run_dialogue',
    'dialogue_summary', 'validate_dialogues', 'show_monitor', 'show_dialogue')
CORE_BINDINGS = frozenset(('TAG', 'authority'))
IDLE_DIRECTORY = 'handoff/audit/' + TAG


def canonical(value):
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def finite(value, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def checked_sources():
    result = {}
    for name, expected in SOURCE_PINS.items():
        path = ROOT / name
        if path.is_symlink() or not path.is_file(): raise ValueError('동결 코드가 필요하다: ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest().upper() != expected: raise ValueError('import 전 source SHA가 다르다: ' + name)
        result[name] = data
    return result


def validate_offsets(offsets, pool_tokens, *, count=None, width=WIDTH):
    ordered = sorted(offsets)
    if (type(pool_tokens) is not int or pool_tokens < width or not ordered
            or count is not None and len(ordered) != count
            or any(type(i) is not int or not 0 <= i <= pool_tokens - width for i in ordered)
            or any(b - a < width for a, b in zip(ordered, ordered[1:]))):
        raise ValueError('완전한 in-bounds/disjoint next-target 창이 필요하다')
    return ordered


def expand_offsets(existing, pool_tokens, *, extra=CYCLE_WINDOWS, seed=1337, width=WIDTH):
    """원 순서를 유지하고 seed1337의 완전1025-block 순열에서 비중첩 창만 추가한다."""
    import numpy as np
    old = list(existing); ordered = validate_offsets(old, pool_tokens, width=width)
    if type(extra) is not int or extra <= 0 or type(seed) is not int or seed < 0 or type(width) is not int or width <= 1:
        raise ValueError('명시한 양의 추가창·seed·next-target 폭이 필요하다')
    added, overlaps = [], 0
    for block in np.random.default_rng(seed).permutation(pool_tokens // width):
        start = int(block) * width; i = bisect_right(ordered, start)
        if (i and ordered[i - 1] + width > start) or (i < len(ordered) and ordered[i] < start + width):
            overlaps += 1; continue
        added.append(start)
        if len(added) == extra: break
    if len(added) != extra: raise ValueError('고정 TRAIN의 비중첩 추가창이 부족하다; 축소·복제하지 않는다')
    vector = old + added; validate_offsets(vector, pool_tokens, width=width)
    return vector, dict(seed=seed, width=width, old_windows=len(old), added_windows=len(added),
        candidates_examined=len(added) + overlaps, overlapping_old_blocks_excluded=overlaps,
        complete_blocks=pool_tokens // width, incomplete_tail_ids=pool_tokens % width,
        original_offsets_sha256=sha(old), added_offsets_sha256=sha(added), offsets_sha256=sha(vector),
        policy='old order then seeded complete-block permutation; interval overlap including next-target excluded',
        unique_knowledge='NOT_MEASURED; native windows are not document provenance')


def update_mapping(cycle, local_update):
    if type(cycle) is not int or cycle not in (0, 1) or type(local_update) is not int or not 0 <= local_update < CYCLE_UPDATES:
        raise ValueError('cycle0/1과 local update0..351이 필요하다')
    local = list(range(local_update * 8, (local_update + 1) * 8))
    return dict(cycle=cycle, source_epoch=local_update // 176, absolute_pass=cycle * 2 + local_update // 176,
        local_update=local_update, absolute_update=cycle * CYCLE_UPDATES + local_update,
        local_native_indices=local, absolute_native_indices=[cycle * CYCLE_WINDOWS + v for v in local])


def ids_sha(window):
    return sha([int(v) for v in window])


class CycleWindows:
    def __init__(self, all_windows, offsets, cycle):
        update_mapping(cycle, 0)
        if len(all_windows) != WINDOWS or len(offsets) != WINDOWS: raise ValueError('동결5632창이 필요하다')
        self.windows, self.offsets, self.cycle, self.accesses = all_windows, offsets, cycle, []

    def __len__(self): return CYCLE_WINDOWS

    def __getitem__(self, index):
        if type(index) is not int or not 0 <= index < CYCLE_WINDOWS: raise ValueError('cycle view의 local index가 다르다')
        absolute = self.cycle * CYCLE_WINDOWS + index
        values = self.windows[absolute]
        if len(values) != WIDTH: raise ValueError('완전1025-ID window가 필요하다')
        self.accesses.append(dict(local_index=index, absolute_index=absolute,
            offset=self.offsets[absolute], input_ids_sha256=ids_sha(values)))
        return values


def idle_path(value, *, root=None):
    """읽기 전 경계: 자기 tag의 root 감사 디렉터리만 허용한다. 보호 경로를 열지 않는다."""
    root = ROOT if root is None else Path(root)
    text = str(value) if isinstance(value, Path) else value
    if (not isinstance(text, str) or not text or '\\' in text or ':' in text or '\x00' in text
            or text.startswith('/') or text != Path(text).as_posix()
            or any(part in ('', '.', '..', 'TinyDataset', '.aws', '.claude', '.codex', '.agents')
                for part in text.split('/'))
            or not text.startswith(IDLE_DIRECTORY + '/')
            or Path(text).suffix not in ('.json', '.jsonl', '.txt', '.log')):
        raise ValueError('유휴 근거는 자기 tag 감사 경로의 정규 상대경로만 허용한다')
    path = root / text
    for current in (path, *path.parents):
        if current.is_symlink(): raise ValueError('유휴 proof/evidence의 symlink는 읽기 전에 거부한다')
        if current == root: break
    return path


def idle_receipt(value, code, arm, *, now=None, monotonic=None):
    now = datetime.now(timezone.utc) if now is None else now
    monotonic = time.monotonic() if monotonic is None else monotonic
    if arm not in ARMS: raise ValueError('cost route가 필요하다')
    start, end = (datetime.fromisoformat(value[k]) for k in ('start_utc', 'end_utc'))
    ms, me = value.get('start_monotonic'), value.get('end_monotonic')
    if (value.get('schema') != 'P106B_ROOT_IDLE_V1' or value.get('tag') != TAG
            or value.get('key') != 'cost_' + arm or value.get('arm') != arm or value.get('code_sha256') != code
            or now.tzinfo is None or start.tzinfo is None or end.tzinfo is None
            or (end - start).total_seconds() < 300 or not 0 <= (now - end).total_seconds() <= 600
            or any(not finite(v) for v in (ms, me, monotonic)) or me - ms < 300
            or not 0 <= monotonic - me <= 600 or value.get('no_gpu_work') is not True
            or value.get('no_heavy_cpu') is not True or not isinstance(value.get('evidence'), list)
            or not value['evidence']):
        raise ValueError('각 cost의 새 tag/code/arm/key와 UTC·monotonic5분 유휴·600초 fresh 근거가 필요하다')
    for item in value['evidence']:
        if (not isinstance(item, dict) or not isinstance(item.get('path'), str)
                or not isinstance(item.get('sha256'), str) or len(item['sha256']) != 64
                or any(ch not in '0123456789ABCDEF' for ch in item['sha256'])):
            raise ValueError('root 실제 조회의 경로/SHA가 필요하다')
        idle_path(item['path'])
    return canonical(value)


def read_idle_proof(p, relative, arm):
    path = idle_path(relative)
    if path.name != 'idle_' + arm + '.json': raise ValueError('route별 정확한 idle_<arm>.json이 필요하다')
    # 모든 evidence 경로 검산이 끝나기 전에는 어느 evidence도 hash하지 않는다.
    proof = idle_receipt(p.n.required(path), p.info()['code_sha256'], arm)
    for evidence in proof['evidence']:
        target = idle_path(evidence['path'])
        if target == path or target.stat().st_size >= 20_000_000:
            raise ValueError('자기참조/20MB이상 유휴 근거는 거부한다')
        if file_sha(target) != evidence['sha256']: raise ValueError('root 유휴 조회 근거 바이트가 다르다')
    return proof


def optimizer_snapshot(model, optimizers):
    names = {id(p): name for name, p in model.named_parameters()}
    result = []
    for opt in optimizers[:2]:
        states = []
        for parameter, state in opt.state.items():
            states.append(dict(name=names[id(parameter)], state_id=id(state),
                tensors={k: dict(identity=id(v), shape=list(v.shape), dtype=str(v.dtype))
                    for k, v in state.items() if hasattr(v, 'shape')},
                steps={k: float(v) for k, v in state.items() if k == 'step'}))
        result.append(dict(identity=id(opt), state_identity=id(opt.state), states=states))
    return result


def validate_optimizers(model, optimizers, original_validator):
    import torch
    from tinylm.train.muon import Muon
    if not isinstance(optimizers, tuple) or len(optimizers) != 3: raise ValueError('정확한 lowercase3tuple factory가 필요하다')
    adam, muon, groups = optimizers
    if type(adam) is not torch.optim.AdamW or type(muon) is not Muon:
        raise ValueError('실제 AdamW와 원 Muon 클래스만 사용한다')
    original_validator(groups)
    ids = [id(p) for opt in (adam, muon) for group in opt.param_groups for p in group['params']]
    if len(ids) != len(set(ids)) or set(ids) != {id(p) for p in model.parameters() if p.requires_grad}:
        raise ValueError('모든 학습 Parameter는 정확히 한 optimizer group 소유여야 한다')
    actual = []
    for label, opt in (('adamw', adam), ('muon', muon)):
        for index, group in enumerate(opt.param_groups):
            row = dict(optimizer=label, group=index, lr=group['lr'], weight_decay=group.get('weight_decay', 0.),
                tensors=len(group['params']), parameters=sum(p.numel() for p in group['params']))
            actual.append(dict(row, actual_class=type(opt).__module__ + '.' + type(opt).__qualname__,
                momentum=group.get('momentum'), nesterov=group.get('nesterov'), ns_steps=group.get('ns_steps'),
                scale_mode=group.get('scale_mode', getattr(opt, 'scale_mode', None))))
            if row != groups[len(actual) - 1]: raise ValueError('보고용 lowercase group과 실제 optimizer group이 다르다')
            if label == 'muon' and (actual[-1]['momentum'], actual[-1]['nesterov'], actual[-1]['ns_steps'], actual[-1]['scale_mode']) != (.95, True, 5, 'rms'):
                raise ValueError('원 Muon momentum/Nesterov/5NS/RMS를 보존해야 한다')
    return actual


class Runtime:
    def __init__(self, native, broad, core, utility, guards, parity):
        self.n, self.b, self.core, self.utility = native, broad, core, utility
        self.guards, self.parity = guards, parity
        self.CACHE, self.RAW, self.EVIDENCE = (ROOT / p / TAG for p in ('data_cache', 'runs/eval', 'test_result/evidence'))
        self.Pending = native.Pending

    def check(self):
        for guard in self.guards: guard.check()
        self.b._resume_assert_unchanged()
        if any(self.utility.body_sha(getattr(self.core, name)) != value for name, value in self.parity.items()):
            raise ValueError('보존한 Broad 계산 본문이 바뀌었다')

    def info(self):
        self.check()
        code = dict(self.n.info()['code_sha256'], **self.b.info()['code_sha256'])
        for name, expected in SOURCE_PINS.items():
            actual = file_sha(ROOT / name)
            if actual != expected: raise ValueError('import 뒤 동결 source 바이트가 바뀌었다: ' + name)
            code[name] = actual
        code.update({name: file_sha(ROOT / name) if (ROOT / name).is_file() else 'NOT_CREATED' for name in (SCRIPT, TEST)})
        return canonical(dict(schema=SCHEMA, tag=TAG, code_sha256=code, code_complete='NOT_CREATED' not in code.values(),
            frozen_source_pins=SOURCE_PINS, f4_sha256=file_sha(F4), arms=list(ARMS),
            native_parent_tag=self.n.TAG, native_parents=PARENTS, broad_provider_tag=self.b.TAG,
            broad_payload_parent_is_initializer=False, planned_cycles=2, passes=4, planned_updates=704, rows_per_pass=22528,
            groups_per_pass=176, schedule='mixed source pass0/1 repeated twice; order not retuned',
            micro_bs=8, accum=16, seq=1024, grad_checkpoint=True, amp='bf16', compile='default', tf32=False,
            objective='L0_TOKEN_MEAN_OVER_WHOLE_UPDATE', adam_lr=5e-5, muon_lr=2e-4, weight_decay=0., clip=1.,
            seed=1337, optimizer_factory='relation_bind.make_optimizers lower-case3tuple once per route',
            optimizer_reset_between_cycles=False, native_windows=5632, native_targets_per_update=8192,
            tokenizer_sha256=self.n.TOKENIZER_SHA, native_train_sha256=self.n.TRAIN_SHA,
            native_val_sha256=self.n.VAL_SHA,
            native_draw_scope='5632 disjoint replay windows only; not disjoint from historical parent crops or new knowledge',
            expected_four_pass_totals=EXPECTED, expected_language_assistant_targets=EXPECTED_LANG,
            authority_end_utc=END.isoformat(), training_stop_utc=TRAIN_STOP.isoformat(),
            actual_worker_active_limit_seconds=ACTIVE_LIMIT, evaluation_reserve_seconds=EVAL_RESERVE,
            record_reserve_seconds=RECORD_RESERVE, max_worker_seconds=WORKER_LIMIT, forecast_factor=1.35,
            activity_scope='own actual worker wall including failures once; readonly/verify/regression/wrapper/root idle excluded',
            idle_path_policy=IDLE_DIRECTORY + '/idle_<arm>.json plus evidence below same directory; relative/no symlink/no protected path',
            prior_activity_scope='original native/Broad source references only, not own active seconds',
            computational_body_sha256=self.parity, private_core_binding_allowlist=sorted(CORE_BINDINGS),
            model_parent_loader='original native.routed_runtime(arm,native); full active route context',
            child_loader='strict native_broad4 route-aware metadata; no generic float load',
            comparison='QT vsBroad changes data/length/targets/704/native jointly; package not amount-only causal',
            monitor_scope='same repeatedly observed1694; not a blind/unseen benchmark',
            dialogue_history='actual model answers only; context shortage is NOT_RUN not PASS',
            termination_scope='own SIGTERM ->130 finally; SIGKILL cannot guarantee activity',
            new_corpus=False, source_quality='original public pseudo labels; human rights/quality review remains',
            teacher_calls=0, mtp=False, headwise=False, thinking=False, orpo=False,
            total75m_complete=False, quality_scope='NOT_ESTABLISHED'))

    def authority(self, training=False, now=None):
        now = datetime.now(timezone.utc) if now is None else now
        if now.tzinfo is None: raise ValueError('실제 aware UTC가 필요하다')
        remaining = ((TRAIN_STOP if training else END) - now).total_seconds() - (0 if training else RECORD_RESERVE)
        if remaining <= 0: raise self.Pending('명시한 학습 종료/권한/기록600초에 도달했다')
        return remaining

    def path(self, mode, arm=None): return self.EVIDENCE / key(mode, arm) / 'report.json'

    def checkpoint(self, arm):
        key('train', arm)
        return self.n.safe(ROOT / 'runs/ckpt' / ('m100s10_ko-en_broad4_' + TAG + '_' + arm + '.pt'))

    def write(self, path, value):
        path = self.n.safe(path)
        if not any(path.is_relative_to(base) for base in (self.CACHE, self.RAW, self.EVIDENCE)):
            raise ValueError('새 namespace 밖에는 쓸 수 없다')
        payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
        if len(payload) >= 20_000_000: raise ValueError('공개 JSON은20MB 미만이어야 한다')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(payload)

    def completed(self, mode, arm=None):
        name = key(mode, arm); path = self.EVIDENCE / ('activity_' + name + '.json')
        value = self.n.required(path); validate_activity(self, value, mode, arm)
        if value['complete'] is not True or value['returncode'] != 0: raise ValueError('실패/부분 activity는 완료가 아니다')
        if value['result_sha256'] != file_sha(self.path(mode, arm)):
            raise ValueError('실제 report SHA와 닫힌 activity를 결합해야 한다')
        return value

    def spent(self):
        total = 0.
        for path in sorted(self.EVIDENCE.glob('activity_*.json')) if self.EVIDENCE.exists() else ():
            value = self.n.required(path); mode, arm = selector(value.get('key'))
            if path.name != 'activity_' + key(mode, arm) + '.json': raise ValueError('activity 경로/키가 다르다')
            validate_activity(self, value, mode, arm); total += value['seconds']
        return total


def build_runtime():
    sources = checked_sources()
    u = importlib.import_module(UTILITY[:-3].replace('/', '.'))
    n = importlib.import_module(NATIVE[:-3].replace('/', '.'))
    bmodule = importlib.import_module(BROAD[:-3].replace('/', '.'))
    original = importlib.import_module(CORE[:-3].replace('/', '.'))
    guards = [u.ModuleGuard(module) for module in (u, n, bmodule, original)]
    broad = bmodule.build_runtime()
    private = types.ModuleType('_p106b_native_broad4_recovery_' + uuid.uuid4().hex)
    private.__file__ = str(ROOT / CORE)
    exec(compile(sources[CORE], str(ROOT / CORE), 'exec', dont_inherit=True), vars(private))
    before = dict(vars(private))
    parity = {name: u.body_sha(getattr(original, name)) for name in BODY_NAMES}
    if any(u.body_sha(getattr(private, name)) != value for name, value in parity.items()):
        raise ValueError('private Broad 원 수치 본문과 다르다')
    p = Runtime(n, broad, private, u, guards, parity)
    private.TAG, private.authority = TAG, p.authority
    expected = dict(vars(private)); values = u._json_values(expected)

    class PrivateGuard:
        def check(self):
            now = vars(private)
            if (set(now) != set(before) or any(now[k] is not v for k, v in expected.items())
                    or any(canonical(now[k]) != v for k, v in values.items())):
                raise ValueError('private core는 TAG·authority 외에는 binding을 바꾸지 않는다')
            if any(now[k] is not v for k, v in before.items() if k not in CORE_BINDINGS):
                raise ValueError('private core allowlist 밖 객체가 달라졌다')
    p.guards.extend((PrivateGuard(), u.ModuleGuard(sys.modules[__name__]))); p.check()
    return p


def key(mode, arm=None):
    if mode not in MODES or (arm not in ARMS if mode in ('cost', 'train', 'evaluate') else arm is not None):
        raise ValueError('단계별 정확한 route 인자가 필요하며 unused arm은 거부한다')
    return mode + ('_' + arm if arm else '')


def selector(name):
    for mode in MODES:
        for arm in ARMS if mode in ('cost', 'train', 'evaluate') else (None,):
            if name == key(mode, arm): return mode, arm
    raise ValueError('등록되지 않은 activity key다')


def parent_report(p, arm):
    report = p.n.train_report('train', arm)
    p.utility.validate_training_header(p.n, report, 'native', arm)
    if (report['checkpoint_sha256'] != PARENTS[arm]['sha256']
            or report['final_core_sha256'] != PARENTS[arm]['core']):
        raise ValueError('원 native의 고정된 각 Q/F 부모가 필요하다')
    return report


def materialized_exposure(p, bundle):
    totals, language = Counter(), Counter()
    for cycle in range(2):
        for local in range(CYCLE_UPDATES):
            epoch, slot, group, expected = p.core.expected_group(bundle, 'mixed', local)
            micros = p.core.builder.materialize_group(bundle['course'], 'mixed', epoch, slot)
            if len(micros) != 16 or any(len(micro) != 8 for micro in micros): raise ValueError('원16micro8 geometry가 다르다')
            records = [r for micro in micros for r in micro]
            plan = p.core.objective.make_weights(records, policy='token')
            observed = dict(x_tokens=sum(r.x_tokens for r in records), assistant_targets=plan.targets,
                content_targets=plan.content_targets, eot_targets=plan.eot_targets)
            if any(observed[k] != expected[k] for k in observed): raise ValueError('완전한4pass token/owner/mask 분모가 다르다')
            totals.update(positive_rows=128, native_targets=8192, **observed)
            for cell in bundle['course'].report['groups'][group]['lane_language']:
                language[cell['language']] += cell['assistant_targets']
    if dict(totals) != EXPECTED or dict(language) != EXPECTED_LANG:
        raise ValueError('원22528×4 노출/언어별 감독량이 계획과 다르다')
    return dict(totals=dict(totals), assistant_targets_by_language=dict(language),
        scope='CPU materialization of all masks/targets; NOT actual GPU training consumption')


def source_state(p):
    p.check(); bundle = p.b.prepared()
    bridge = p.n.required(p.b.CACHE / 'frozen.json')
    if (p.b.TAG != 'p106b_broad_resume_v3_s1337' or bridge.get('status') != 'BROAD_RESUME_BRIDGE_PREPARED'
            or bridge.get('tag') != p.b.TAG or bridge.get('expected_parent_core') != p.n.PARENT_CORE
            or bridge.get('updates') != 352 or bridge.get('rows_per_pass') != 22528
            or len(bundle['monitor']) != 1694 or len(bundle['dialogues']) != 16):
        raise ValueError('정확한 v3 bridge/원P090B source 이력/22528 payload가 필요하다')
    old = bundle['contract']['native_train_offsets']
    validate_offsets(old, p.n.TRAIN_TOKENS, count=CYCLE_WINDOWS)
    if (p.n.safe(p.n.TRAIN).stat().st_size != 2 * p.n.TRAIN_TOKENS or file_sha(p.n.TRAIN) != p.n.TRAIN_SHA):
        raise ValueError('같은 고정 chat32 TRAIN 원본이 필요하다')
    offsets, selection = expand_offsets(old, p.n.TRAIN_TOKENS)
    parents = {}
    for arm in ARMS:
        report = parent_report(p, arm)
        path = p.n.result_path(p.n.phase_key('train', arm))
        activity = p.n.EVIDENCE / ('activity_train_' + arm + '.json')
        parents[arm] = dict(checkpoint=str(p.n.checkpoint(arm, 'native').relative_to(ROOT)),
            checkpoint_sha256=report['checkpoint_sha256'], core_sha256=report['final_core_sha256'],
            scratch_core_sha256=report['scratch_core_sha256'], report=str(path.relative_to(ROOT)),
            report_sha256=file_sha(path), activity=str(activity.relative_to(ROOT)), activity_sha256=file_sha(activity),
            original_tag=p.n.TAG, original_training_updates=report['updates'])
    exposure = materialized_exposure(p, bundle)
    samples = sorted((row for row in bundle['course'].rows if row['lane'] == 'general'),
        key=lambda row: sha([TAG, 'SOURCE_ROOT_REVIEW_ONLY', row['id']]))[:16]
    binding = dict(provider_tag=p.b.TAG, provider_frozen=str((p.b.CACHE / 'frozen.json').relative_to(ROOT)),
        provider_frozen_sha256=file_sha(p.b.CACHE / 'frozen.json'),
        provider_prepare_activity_sha256=file_sha(p.b.EVIDENCE / 'activity_prepare.json'),
        original_binding=bridge['binding'], original_contract_sha256=sha(bundle['contract']),
        ordered_records_sha256=bundle['course'].report['ordered_record_hashes_sha256'],
        original_schedules_sha256=bundle['course'].report['schedules_sha256'], schedule='mixed',
        parents=parents, native_train_file=str(p.n.TRAIN.relative_to(ROOT)), native_train_sha256=p.n.TRAIN_SHA,
        native_pool_ids=p.n.TRAIN_TOKENS, native_train_offsets=offsets, native_selection=selection,
        four_pass_cpu_materialization=exposure, monitor_cases_sha256=sha(bundle['monitor']),
        dialogue_cases_sha256=sha(bundle['dialogues']), dev_rows=len(bundle['dev']),
        dev_targets=sum(r.targets for r in bundle['dev']),
        root_review_samples=[{k: row[k] for k in ('id', 'root', 'source', 'language', 'messages_sha256')} for row in samples],
        root_review_scope='source/root/rights/leakage post-review only; no semantic blacklist or automatic quality gate',
        no_source_copy=True, no_source_retag=True, original_payload_passes=2, own_cycles=2)
    p.check(); return bundle, canonical(binding)


def prepare(p):
    if any(path.exists() for path in (p.CACHE, p.RAW, p.EVIDENCE)):
        raise FileExistsError('원형/부분 namespace를 보존하며 자동 재시도하지 않는다')
    began = time.perf_counter(); bundle, binding = source_state(p)
    value = dict(p.info(), status='NATIVE_BROAD4_SOURCE_BRIDGE_PREPARED', binding=binding,
        cpu_consumer_seconds=time.perf_counter() - began, actual_training='NOT_RUN', models_loaded=0,
        checkpoint_tensor_loads=0, checkpoints_written=0)
    p.write(p.CACHE / 'frozen_reference.json', value)
    p.write(p.EVIDENCE / 'cpu_contract.json', dict(value, reference_sha256=file_sha(p.CACHE / 'frozen_reference.json')))
    p.write(p.path('prepare'), dict(p.info(), status='CPU_BRIDGE_COMPLETE', reference_sha256=file_sha(p.CACHE / 'frozen_reference.json')))
    prepared(p, completed=False, state=(bundle, binding))
    return 0


def prepared(p, *, completed=True, state=None):
    bundle, binding = source_state(p) if state is None else state
    value = p.n.required(p.CACHE / 'frozen_reference.json'); public = p.n.required(p.EVIDENCE / 'cpu_contract.json')
    if (value.get('status') != 'NATIVE_BROAD4_SOURCE_BRIDGE_PREPARED' or value.get('binding') != binding
            or any(value.get(k) != v for k, v in p.info().items()) or not finite(value.get('cpu_consumer_seconds'), True)
            or value.get('models_loaded') != 0 or value.get('checkpoint_tensor_loads') != 0
            or value.get('checkpoints_written') != 0 or value.get('actual_training') != 'NOT_RUN'
            or public != dict(value, reference_sha256=file_sha(p.CACHE / 'frozen_reference.json'))):
        raise ValueError('완전한 같은 info/source/mask/선택/부모 SHA bridge가 필요하다')
    if completed: p.completed('prepare')
    return bundle, value


def validate_activity(p, value, mode, arm=None):
    name = key(mode, arm)
    start, end = (datetime.fromisoformat(value[k]) for k in ('started_at', 'ended_at'))
    if (mode in ('source', 'preflight') or value.get('schema') != SCHEMA or value.get('tag') != TAG
            or value.get('key') != name or value.get('mode') != mode or value.get('arm') != arm
            or value.get('code_sha256') != p.info()['code_sha256'] or not finite(value.get('seconds'))
            or type(value.get('max_wall_sec')) is not int or not 60 <= value['max_wall_sec'] <= WORKER_LIMIT
            or value['seconds'] > value['max_wall_sec'] + 30
            or type(value.get('complete')) is not bool or start.tzinfo is None or end.tzinfo is None or start > end
            or type(value.get('worker_pid')) is not int or value['worker_pid'] <= 0
            or value.get('worker_pgid') != value['worker_pid']
            or type(value.get('returncode')) is not int or value['complete'] != (value['returncode'] == 0)
            or value['complete'] and value.get('error_type') is not None
            or not value['complete'] and not isinstance(value.get('error_type'), str)):
        raise ValueError('정확한 own-PGID 실제 완료/실패 activity가 필요하다')
    stop = TRAIN_STOP if mode in ('prepare', 'cost', 'train') else END
    if start >= stop or end > stop + timedelta(seconds=30):
        raise ValueError('원 activity 정책의 절대 기한과30초 정리여유를 넘었다')
    reference = p.CACHE / 'frozen_reference.json'
    if value.get('reference_sha256') != (file_sha(reference) if reference.is_file() else None):
        raise ValueError('activity의 현재 source reference가 다르다')
    result = p.path(mode, arm)
    if value.get('result_sha256') != (file_sha(result) if result.is_file() else None):
        raise ValueError('activity의 부분/완료 report SHA가 다르다')


def core_rows(p, directory, manifest, count):
    if p.n.required(directory / 'updates_shards_manifest.json') != manifest: raise ValueError('원 core manifest 내용이 다르다')
    return p.core.monitor.read_rows(directory, manifest, 'updates', count)


def validate_core_result(p, bundle, cycle, result, events, *, cost=False):
    count = 8 if cost else CYCLE_UPDATES
    if result.get('actual_updates') != count or len(events) != count: raise ValueError('닫힌 core의 전체 실제 update가 필요하다')
    if result.get('event_manifest', {}).get('lineage') != dict(tag=TAG, arm='mixed', cost=cost):
        raise ValueError('원 core의 mixed schedule/tag/cost 계보가 다르다')
    for local, event in enumerate(events):
        epoch, _, group, expected = p.core.expected_group(bundle, 'mixed', local, cost)
        if (event.get('update') != local + 1 or event.get('epoch') != epoch + 1 or event.get('group') != group
                or event.get('lane') != bundle['course'].report['groups'][group]['lane']
                or event.get('native_indices') != update_mapping(cycle, local)['local_native_indices']
                or event.get('positive_rows') != 128 or event.get('native_targets') != 8192
                or event.get('assistant_targets') != event.get('content_targets', 0) + event.get('eot_targets', 0)
                or any(event.get(k) != expected[k] for k in TOTAL_KEYS[1:-1])
                or any(not finite(event.get(k)) for k in ('assistant_ce', 'content_ce', 'eot_ce', 'native_ce', 'gradient_norm'))
                or not finite(event.get('step_seconds'), True) or event.get('clipped') is not (event['gradient_norm'] > 1)):
            raise ValueError('원 whole128 분모/그룹/CE/gradient/native local순서가 다르다')
    if (result.get('step_seconds') != [e['step_seconds'] for e in events]
            or result.get('grad_max') != max(e['gradient_norm'] for e in events)
            or result.get('clip_events') != sum(e['clipped'] for e in events)
            or any(result.get('totals', {}).get(k) != sum(e[k] for e in events) for k in TOTAL_KEYS)
            or not finite(result.get('update_core_seconds'), True)):
        raise ValueError('원 core raw와 보고의 합계/시간/gradient가 다르다')
    p.core.monitor.original.validate_groups(result['actual_optimizer_groups'])


def run_cycles(p, model, cfg, tok, bundle, windows, offsets, directory, optimizers, *, forward=None, cost=False, probe=None, fingerprint=None):
    """두 호출은 같은 객체/원본문을 공유한다. 중간 실패는 원 raw와 완료 cycle을 보존한다."""
    from scripts.p106b_shards import ShardWriter
    if fingerprint is None: fingerprint = p.n.modules()[0].state_fingerprint
    identities = (id(model), id(optimizers), id(optimizers[0]), id(optimizers[1]))
    parameters = [(name, id(value)) for name, value in model.named_parameters()]
    completed, results = [], []
    view = None; cycle = 0
    try:
        for cycle in range(1 if cost else 2):
            p.authority(training=True)
            if identities != (id(model), id(optimizers), id(optimizers[0]), id(optimizers[1])) or parameters != [(n, id(v)) for n, v in model.named_parameters()]:
                raise ValueError('모델/Parameter/optimizer 객체를 cycle 사이 교체할 수 없다')
            before_state, before_core = optimizer_snapshot(model, optimizers), fingerprint(model)
            if completed and (completed[-1]['optimizer_after'] != before_state or completed[-1]['core_after'] != before_core):
                raise ValueError('둘째 cycle은 첫 cycle의 실제 모델/optimizer state에서 연속해야 한다')
            view = CycleWindows(windows, offsets, cycle)
            output = directory / ('cycle' + str(cycle))
            result = p.core.train_updates(model, cfg, tok, bundle, 'mixed', output, cost=cost,
                forward=forward, native_windows=view, optimizers=optimizers, probe=probe)
            events = core_rows(p, output, result['event_manifest'], 8 if cost else CYCLE_UPDATES)
            validate_core_result(p, bundle, cycle, result, events, cost=cost)
            if [v['local_index'] for v in view.accesses] != list(range((8 if cost else CYCLE_UPDATES) * 8)):
                raise ValueError('core의 실제 native 접근은 cycle view의 순서와 정확히 같아야 한다')
            writer = ShardWriter(output, 'absolute_updates', limit=19_999_999)
            for local, event in enumerate(events):
                writer.append(dict(update_mapping(cycle, local), source_group=event['group'],
                    source_event_sha256=sha(event), native_accesses=view.accesses[local * 8:(local + 1) * 8]))
            lineage = dict(tag=TAG, cycle=cycle, cost=cost,
                reference_sha256=file_sha(p.CACHE / 'frozen_reference.json'), core_manifest_sha256=sha(result['event_manifest']))
            absolute = writer.close(lineage=lineage)
            receipt = dict(cycle=cycle, core_result=result, absolute_manifest=absolute,
                core_before=before_core, core_after=fingerprint(model), optimizer_before=before_state,
                optimizer_after=optimizer_snapshot(model, optimizers), identities=list(identities),
                native_view_offsets_sha256=sha(offsets[cycle * CYCLE_WINDOWS:(cycle + 1) * CYCLE_WINDOWS]))
            p.write(output / 'cycle_receipt.json', receipt); completed.append(receipt); results.append(result)
        return completed
    except BaseException as exc:
        p.write(directory / 'partial_failure.json', dict(tag=TAG, error_type=type(exc).__name__, error=str(exc)[:2000],
            attempted_cycle=cycle, completed_cycles=len(completed), completed_update_lower_bound=sum(r['actual_updates'] for r in results),
            current_cycle_native_windows_attempted=len(view.accesses) if view else 0,
            current_cycle_optimizer_updates='UNKNOWN_UNLESS_CLOSED_CORE_MANIFEST', checkpoint_writes=0,
            raw_preserved=True, status='PARTIAL_NOT_TRAIN_COMPLETE'))
        raise


def cp_experiment(report):
    return {k: report[k] for k in ('tag', 'arm', 'updates', 'passes', 'objective', 'reference_sha256',
        'parent_checkpoint_sha256', 'parent_core_sha256', 'scratch_core_sha256', 'final_core_sha256',
        'native_offsets_sha256', 'ordered_records_sha256', 'original_schedules_sha256', 'endpoint')}


def validate_payload(p, payload, cfg, arm, report):
    _, _, method = p.n.modules()
    method.validate_route_metadata(payload.get('quantization_route'), arm)
    if (set(payload) != {'model', 'cfg', 'step', 'tokenizer_sha256', 'tokenizer_lineage', 'quantization_route', 'experiment'}
            or payload.get('step') != 704 or payload.get('cfg') != asdict(cfg)
            or payload.get('tokenizer_sha256') != p.n.TOKENIZER_SHA or payload.get('tokenizer_lineage') != 'chat32'
            or payload.get('experiment') != cp_experiment(report) or report.get('tag') != TAG
            or report.get('endpoint') != 'native_broad4'
            or report.get('arm') != arm or report.get('passes') != 4 or report.get('updates') != 704
            or report.get('parent_checkpoint_sha256') != PARENTS[arm]['sha256']
            or report.get('parent_core_sha256') != PARENTS[arm]['core']):
        raise ValueError('새704/4pass/원 native부모/source/route 전용 CP만 허용한다')


def read_training(p, arm, *, cost, state=None):
    mode = 'cost' if cost else 'train'; p.completed(mode, arm)
    bundle, frozen = prepared(p) if state is None else state
    if p.n.required(p.CACHE / 'frozen_reference.json') != frozen:
        raise ValueError('재사용 state도 실제 자기 frozen reference와 완전히 같아야 한다')
    report = p.n.required(p.path(mode, arm)); binding = frozen['binding']; parent = binding['parents'][arm]
    if (any(report.get(k) != v for k, v in p.info().items()) or report.get('status') != ('COST8_COMPLETE' if cost else 'TRAIN_COMPLETE')
            or report.get('arm') != arm or report.get('cost') is not cost or report.get('updates') != (8 if cost else 704)
            or report.get('endpoint') != 'native_broad4'
            or report.get('reference_sha256') != file_sha(p.CACHE / 'frozen_reference.json')
            or report.get('parent_checkpoint_sha256') != parent['checkpoint_sha256']
            or report.get('parent_core_sha256') != parent['core_sha256'] or report.get('initial_core_sha256') != parent['core_sha256']
            or report.get('parent_report_sha256') != parent['report_sha256']
            or report.get('scratch_core_sha256') != parent['scratch_core_sha256']
            or report.get('checkpoint_writes') != (0 if cost else 1) or report.get('optimizer_saved') is not False
            or report.get('native_offsets_sha256') != binding['native_selection']['offsets_sha256']
            or report.get('ordered_records_sha256') != binding['ordered_records_sha256']
            or report.get('original_schedules_sha256') != binding['original_schedules_sha256']
            or not p.n.fingerprint(report.get('final_core_sha256'))):
        raise ValueError('같은 실제 부모/source/704 또는cost8의 완료 보고서가 필요하다')
    p.n.validate_route_receipt(report['route'], arm)
    p.n.modules()[2].validate_route_metadata(report['quantization_route'], arm)
    receipts = report.get('cycles', [])
    if len(receipts) != (1 if cost else 2): raise ValueError('cost1/train2의 닫힌 cycle이 필요하다')
    from scripts.p106b_native_windows import reader
    windows = reader(ROOT, dict(native_access='INDEXED_TRAIN_ONLY', native_train_file=binding['native_train_file'],
        native_train_offsets=binding['native_train_offsets']))
    all_events = []; initial = parent['core_sha256']
    for cycle, receipt in enumerate(receipts):
        directory = p.RAW / key(mode, arm) / ('cycle' + str(cycle))
        if p.n.required(directory / 'cycle_receipt.json') != receipt or receipt.get('cycle') != cycle:
            raise ValueError('실제 cycle 영수증 내용/순서가 다르다')
        result = receipt['core_result']; count = 8 if cost else CYCLE_UPDATES
        events = core_rows(p, directory, result['event_manifest'], count)
        validate_core_result(p, bundle, cycle, result, events, cost=cost)
        lineage = dict(tag=TAG, cycle=cycle, cost=cost, reference_sha256=report['reference_sha256'], core_manifest_sha256=sha(result['event_manifest']))
        manifest = receipt['absolute_manifest']
        if manifest.get('lineage') != lineage or p.n.required(directory / 'absolute_updates_shards_manifest.json') != manifest:
            raise ValueError('절대 update/native map의 닫힌 계보가 다르다')
        maps = p.core.monitor.read_rows(directory, manifest, 'absolute_updates', count)
        offsets = binding['native_train_offsets']
        for local, (event, mapping) in enumerate(zip(events, maps)):
            expected = update_mapping(cycle, local)
            accesses = [dict(local_index=i, absolute_index=cycle * CYCLE_WINDOWS + i,
                offset=offsets[cycle * CYCLE_WINDOWS + i], input_ids_sha256=ids_sha(windows[cycle * CYCLE_WINDOWS + i]))
                for i in expected['local_native_indices']]
            if mapping != dict(expected, source_group=event['group'], source_event_sha256=sha(event), native_accesses=accesses):
                raise ValueError('실제 absolute update/offset/소비 IDs와 원 event의 결합이 다르다')
        if (receipt['core_before'] != initial
                or not p.n.fingerprint(receipt.get('core_after'))
                or not isinstance(receipt.get('identities'), list) or len(receipt['identities']) != 4
                or any(type(v) is not int or v <= 0 for v in receipt['identities'])
                or len(set(receipt['identities'])) != 4
                or cycle and (receipt['identities'] != receipts[0]['identities']
                    or receipt['optimizer_before'] != receipts[cycle - 1]['optimizer_after'])
                or receipt['native_view_offsets_sha256'] != sha(offsets[cycle * CYCLE_WINDOWS:(cycle + 1) * CYCLE_WINDOWS])):
            raise ValueError('모델/optimizer 연속성 또는 각2816 view 계보가 다르다')
        initial = receipt['core_after']; all_events.extend(events)
    totals = {k: sum(e[k] for e in all_events) for k in TOTAL_KEYS}
    if (report.get('totals') != totals or not cost and totals != EXPECTED
            or report.get('step_seconds') != [e['step_seconds'] for e in all_events]
            or report.get('grad_max') != max(e['gradient_norm'] for e in all_events)
            or report.get('clip_events') != sum(e['clipped'] for e in all_events)
            or report.get('final_core_sha256') != initial):
        raise ValueError('4pass 실제 raw 합계/시간/gradient/마지막모델이 다르다')
    language = language_exposure(bundle, all_events)
    if report.get('language_assistant_targets') != language or not cost and language != EXPECTED_LANG:
        raise ValueError('실제 원 group 노출에 귀속한 언어별 target 분모가 다르다')
    validate_group_receipts(p, report, receipts)
    if not cost:
        if report.get('checkpoint') != str(p.checkpoint(arm).relative_to(ROOT)) or file_sha(p.checkpoint(arm)) != report.get('checkpoint_sha256'):
            raise ValueError('새 자식 CP 바이트와 경로가 다르다')
        validate_probes(p, bundle, report)
    return report


def validate_group_receipts(p, report, receipts):
    groups = report.get('actual_optimizer_groups'); p.core.monitor.original.validate_groups(groups)
    actual = report.get('actual_optimizer_classes')
    if not isinstance(actual, list) or len(actual) != len(groups): raise ValueError('실제 class/group 영수증이 필요하다')
    for row, group in zip(actual, groups):
        expected = 'torch.optim.adamw.AdamW' if group['optimizer'] == 'adamw' else 'tinylm.train.muon.Muon'
        if any(row.get(k) != v for k, v in group.items()) or row.get('actual_class') != expected:
            raise ValueError('진짜 원 AdamW/Muon과 lowercase group을 구분해야 한다')
        if group.get('lr') != (5e-5 if group['optimizer'] == 'adamw' else 2e-4):
            raise ValueError('원 Adam5e-5/Muon2e-4 constant LR이 필요하다')
        if group['optimizer'] == 'muon' and tuple(row.get(k) for k in ('momentum', 'nesterov', 'ns_steps', 'scale_mode')) != (.95, True, 5, 'rms'):
            raise ValueError('원 Muon 계수/NS/RMS가 다르다')
    if any(r['core_result']['actual_optimizer_groups'] != groups for r in receipts):
        raise ValueError('두cycle의 실제 optimizer groups가 다르다')
    first = receipts[0].get('optimizer_before')
    if not isinstance(first, list) or len(first) != 2 or any(v.get('states') != [] for v in first):
        raise ValueError('첫 cycle 전에만 fresh optimizer reset을 해야 한다')


def language_exposure(bundle, events):
    result = Counter()
    for event in events:
        for cell in bundle['course'].report['groups'][event['group']]['lane_language']:
            result[cell['language']] += cell['assistant_targets']
    return dict(result)


def validate_probes(p, bundle, report):
    probes = [report['before']]
    for cycle in report['cycles']:
        history = cycle['core_result']['history']
        if len(history) != 2 or [(v['epoch'], v['updates']) for v in history] != [(1, 176), (2, 352)]:
            raise ValueError('원 epoch 경계의 네 DEV/native probe를 보존해야 한다')
        probes.extend(history)
    for value in probes:
        p.n.validate_native32(value['native']); dev = value['dev']
        if (dev.get('rows') != len(bundle['dev']) or dev.get('targets') != sum(r.targets for r in bundle['dev'])
                or not finite(dev.get('ce'), True) or not finite(dev.get('content_ce')) or not finite(dev.get('eot_ce'))):
            raise ValueError('완전한 원 DEV target/행/유한 TF loss가 필요하다')


def budget(p, *, record=False):
    state = prepared(p); estimates = {}
    for arm in ARMS:
        cost = read_training(p, arm, cost=True, state=state); times = cost['step_seconds']
        estimate = times[0] + max(times[1:]) * (704 - 1) * 1.35 + 300
        if p.path('train', arm).exists(): read_training(p, arm, cost=False, state=state); estimate = 0.
        estimates[arm] = estimate
    readback_reserve = state[1]['cpu_consumer_seconds'] * 1.35 + 30
    elapsed = p.spent(); train = sum(estimates.values())
    whole = elapsed + train + EVAL_RESERVE + readback_reserve + RECORD_RESERVE
    value = dict(p.info(), status='MEASURED_BUDGET', fits=whole <= ACTIVE_LIMIT and train <= p.authority(True)
        and train + EVAL_RESERVE + readback_reserve <= p.authority(), estimated_training_seconds=estimates,
        spent_actual_worker_seconds=elapsed, predicted_readback_seconds=readback_reserve,
        total_reserved_seconds=whole, cost_first_and_warm_separated=True,
        uncertainty='first + max7warm*703*1.35 + original300 probe/overhead; prediction not late-step guarantee',
        worker_cap_scope='fixed cap admission is separate from forecast; neither is a continuous peak guarantee')
    if record: p.write(p.path('budget'), value)
    return value


def train(p, arm, *, cost=False, idle_proof=None, max_wall_sec=600):
    state = prepared(p); bundle, frozen = state; binding = frozen['binding']; parent = parent_report(p, arm)
    mode, name = ('cost' if cost else 'train'), key('cost' if cost else 'train', arm)
    directory = p.RAW / name
    if directory.exists() or p.path(mode, arm).exists() or not cost and p.checkpoint(arm).exists():
        raise FileExistsError('기존 완료/부분 raw/CP를 보존한다')
    reservation = None
    if not cost:
        p.completed('budget'); reservation = budget(p)
        if not reservation['fits'] or reservation['estimated_training_seconds'][arm] > max_wall_sec:
            raise p.Pending('실측 budget/worker cap 안에704회가 들어가야 한다')
    proof = None
    if cost:
        if idle_proof is None: raise p.Pending('root의 route별 새5분 유휴 proof가 필요하다')
        proof = read_idle_proof(p, idle_proof, arm)
        other = 'float' if arm == 'ternary' else 'ternary'
        if p.path('cost', other).exists():
            other_proof = read_training(p, other, cost=True, state=state)['idle_proof']
            if datetime.fromisoformat(proof['start_utc']) < datetime.fromisoformat(other_proof['end_utc']):
                raise ValueError('두 cost가 같은 유휴 구간을 재사용할 수 없다')
    from scripts.p106b_gate_runtime import idle_before_gpu
    from scripts.p106b_native_windows import reader
    windows = reader(ROOT, dict(native_access='INDEXED_TRAIN_ONLY', native_train_file=binding['native_train_file'],
        native_train_offsets=binding['native_train_offsets']))
    idle_before_gpu(); p.authority(training=True)
    if proof: idle_receipt(proof, p.info()['code_sha256'], arm)
    directory.mkdir(parents=True, exist_ok=False); began = time.perf_counter()
    runtime, _, _ = p.n.modules()
    with p.n.routed_runtime(arm, 'native') as (torch, model, cfg, tok, scratch, route):
        initial = runtime.state_fingerprint(model)
        if initial != PARENTS[arm]['core'] or scratch != parent['scratch_core_sha256']:
            raise ValueError('학습 직전 실제 원 native 부모/scratch fingerprint가 다르다')
        model.clear_quant(); model.train(); model.set_anneal(1.); route.assert_active()
        optimizers = p.core.monitor.base.make_optimizers(model)
        classes = validate_optimizers(model, optimizers, p.core.monitor.original.validate_groups)
        if any(opt.state for opt in optimizers[:2]): raise ValueError('각 arm 시작은 fresh optimizer reset이어야 한다')
        if not cost:
            cost_report = read_training(p, arm, cost=True, state=state)
            if (cost_report['actual_optimizer_groups'] != optimizers[2]
                    or cost_report['actual_optimizer_classes'] != classes): raise ValueError('cost/train 실제 optimizer 경로가 다르다')
        def probe():
            route.assert_active()
            try: return dict(dev=p.core.dev_probe(model, bundle['dev']), native=p.core.monitor.base.native_probe(model))
            finally: model.clear_quant(); model.train(); model.set_anneal(1.); route.assert_active()
        before = None if cost else probe()
        os.environ['TORCHINDUCTOR_CACHE_DIR'] = str(p.CACHE / ('compile_' + name))
        forward = torch.compile(model, mode='default'); torch.cuda.reset_peak_memory_stats()
        try:
            cycles = run_cycles(p, model, cfg, tok, bundle, windows, binding['native_train_offsets'], directory,
                optimizers, forward=forward, cost=cost, probe=probe, fingerprint=runtime.state_fingerprint)
            model.clear_quant(); model.eval(); model.set_anneal(1.)
            with torch.no_grad(): model.freeze_quant()
            route_receipt = p.n.route_receipt(model, route); p.n.validate_route_receipt(route_receipt, arm)
            final = runtime.state_fingerprint(model)
            results = [v['core_result'] for v in cycles]
            events = [event for index, result in enumerate(results)
                for event in core_rows(p, directory / ('cycle' + str(index)), result['event_manifest'], 8 if cost else 352)]
            report = dict(p.info(), status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE', arm=arm, cost=cost, endpoint='native_broad4',
                updates=8 if cost else 704, reference_sha256=file_sha(p.CACHE / 'frozen_reference.json'),
                parent_checkpoint_sha256=parent['checkpoint_sha256'], parent_core_sha256=parent['final_core_sha256'],
                parent_report_sha256=binding['parents'][arm]['report_sha256'], scratch_core_sha256=scratch,
                initial_core_sha256=initial, final_core_sha256=final, native_offsets_sha256=binding['native_selection']['offsets_sha256'],
                ordered_records_sha256=binding['ordered_records_sha256'], original_schedules_sha256=binding['original_schedules_sha256'],
                cycles=cycles, totals={k: sum(r['totals'][k] for r in results) for k in TOTAL_KEYS},
                language_assistant_targets=language_exposure(bundle, events),
                step_seconds=[v for r in results for v in r['step_seconds']], grad_max=max(r['grad_max'] for r in results),
                clip_events=sum(r['clip_events'] for r in results), actual_optimizer_groups=optimizers[2],
                actual_optimizer_classes=classes, before=before, route=route_receipt, quantization_route=route.metadata,
                optimizer_saved=False, checkpoint_writes=0 if cost else 1, reservation=reservation, idle_proof=proof,
                peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20, peak_scope='torch allocator only; not whole device',
                whole_seconds=time.perf_counter() - began, actual_quality='NOT_EVALUATED')
            if not cost:
                path = p.checkpoint(arm); path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as stream:
                    torch.save(dict(model=model.state_dict(), cfg=asdict(cfg), step=704,
                        tokenizer_sha256=p.n.TOKENIZER_SHA, tokenizer_lineage='chat32',
                        quantization_route=route.metadata, experiment=cp_experiment(report)), stream)
                report.update(checkpoint=str(path.relative_to(ROOT)), checkpoint_sha256=file_sha(path))
            p.write(p.path(mode, arm), report)
            # strict reader는 worker finally의 activity가 닫힌 뒤 VERIFY child에서만 실행한다.
        finally:
            del forward; model.clear_quant()
    return 0


@contextmanager
def child_runtime(p, arm, report):
    runtime, _, method = p.n.modules()
    with p.n.routed_runtime(arm, 'native') as (torch, model, cfg, tok, scratch, route):
        if scratch != report['scratch_core_sha256']: raise ValueError('원 초기화 계보가 다르다')
        payload = torch.load(p.checkpoint(arm), map_location='cpu', weights_only=True)
        validate_payload(p, payload, cfg, arm, report); p.n.validate_cpu_state(model, payload, torch)
        method.load_routed_state(model, payload, arm); del payload
        if runtime.state_fingerprint(model) != report['final_core_sha256']: raise ValueError('엄격 자식 loader의 실제 본체가 다르다')
        model.clear_quant(); model.eval(); model.set_anneal(1.)
        with torch.no_grad(): model.freeze_quant()
        route.assert_active()
        yield torch, model, cfg, tok, route


def evaluate(p, arm):
    from scripts.p106b_shards import ShardWriter
    from scripts.p106b_gate_runtime import idle_before_gpu
    state = prepared(p); bundle, frozen = state; trained = read_training(p, arm, cost=False, state=state)
    directory = p.RAW / key('evaluate', arm)
    if directory.exists() or p.path('evaluate', arm).exists(): raise FileExistsError('실제 자유답 원형을 보존한다')
    idle_before_gpu(); p.authority(); directory.mkdir(parents=True, exist_ok=False)
    lineage = evaluation_lineage(p, arm, trained); monitor = p.core.monitor; began = time.perf_counter()
    with child_runtime(p, arm, trained) as (torch, model, cfg, tok, route):
        before = p.n.modules()[0].state_fingerprint(model); events, dialogues = [], []
        with torch.no_grad():
            writer = ShardWriter(directory, 'monitor_answers', limit=19_999_999)
            for index, case in enumerate(bundle['monitor']):
                p.authority(); route.assert_active()
                if monitor.case_encoding(case, tok) != case['encoding']: raise ValueError('같은 전체 monitor encoding이 필요하다')
                answer, generation = monitor.emit64(model, cfg, tok, case['messages'])
                event = dict(id=case['id'], case_sha256=sha(case), answer=answer, generation=generation,
                    metrics=monitor.classify_case(case, answer), lineage=lineage)
                writer.append(event); events.append(event)
                if case['id'] in bundle['contract']['monitor_display_ids']:
                    p.core.show_monitor(case, event, arm, 'NEW_NATIVE_BROAD4', lambda line: print(line, flush=True))
                if (index + 1) % 256 == 0: print('[NATIVE_BROAD4_MONITOR] ' + arm + ' ' + str(index + 1) + '/1694', flush=True)
            manifest = writer.close(lineage=lineage)
            writer = ShardWriter(directory, 'dialogue_answers', limit=19_999_999)
            for case in bundle['dialogues']:
                event = p.core.run_dialogue(case, lambda messages: p.core.emit_dialogue(model, cfg, tok, messages), tok)
                event['lineage'] = lineage; writer.append(event); dialogues.append(event)
                p.core.show_dialogue(event, case, arm, lambda line: print(line, flush=True))
            dialogue_manifest = writer.close(lineage=lineage)
        model.clear_quant(); after = p.n.modules()[0].state_fingerprint(model)
        if before != after: raise ValueError('평가가 학습 가중치를 변경했다')
        native = p.core.monitor.base.native_probe(model); p.n.validate_native32(native)
        p.write(p.path('evaluate', arm), dict(p.info(), status='ACTUAL_MONITOR_AND_DIALOGUES_RECORDED', arm=arm,
            lineage=lineage, training_report_sha256=file_sha(p.path('train', arm)), core_before=before, core_after=after,
            monitor_manifest=manifest, dialogue_manifest=dialogue_manifest,
            monitor_summary=monitor.recount(events, bundle['monitor'], tokenizer=tok),
            dialogue_summary=p.core.dialogue_summary(dialogues), native32_fp32=native,
            monitor_cases_sha256=sha(bundle['monitor']), dialogue_cases_sha256=sha(bundle['dialogues']),
            whole_seconds=time.perf_counter() - began, weights_changed=False, checkpoints_written=0,
            quality='HUMAN_REVIEW_REQUIRED_NO_AUTOMATIC_PASS',
            generation_budgets=dict(monitor_first_answer=64, dialogue_actual_history_per_turn=128)))
    return 0


def evaluation_lineage(p, arm, trained):
    return dict(tag=TAG, arm=arm, endpoint='native_broad4', checkpoint=str(p.checkpoint(arm).relative_to(ROOT)),
        checkpoint_sha256=trained['checkpoint_sha256'], expected_core_sha256=trained['final_core_sha256'],
        reference_sha256=trained['reference_sha256'], parent_checkpoint_sha256=trained['parent_checkpoint_sha256'])


def read_evaluation(p, arm, state, tok):
    p.completed('evaluate', arm); bundle, _ = state; trained = read_training(p, arm, cost=False, state=state)
    report = p.n.required(p.path('evaluate', arm)); lineage = evaluation_lineage(p, arm, trained)
    if (any(report.get(k) != v for k, v in p.info().items()) or report.get('status') != 'ACTUAL_MONITOR_AND_DIALOGUES_RECORDED'
            or report.get('arm') != arm or report.get('lineage') != lineage
            or report.get('training_report_sha256') != file_sha(p.path('train', arm))
            or report.get('core_before') != trained['final_core_sha256'] or report.get('core_after') != trained['final_core_sha256']
            or report.get('monitor_cases_sha256') != sha(bundle['monitor']) or report.get('dialogue_cases_sha256') != sha(bundle['dialogues'])
            or report.get('weights_changed') is not False or report.get('checkpoints_written') != 0):
        raise ValueError('같은 새704CP/전체case/route의 평가가 필요하다')
    directory = p.RAW / key('evaluate', arm); rows = []
    for stem, count in (('monitor_answers', 1694), ('dialogue_answers', 16)):
        manifest = report['monitor_manifest' if stem == 'monitor_answers' else 'dialogue_manifest']
        if p.n.required(directory / (stem + '_shards_manifest.json')) != manifest or manifest.get('lineage') != lineage:
            raise ValueError('실제 답 manifest/계보가 다르다')
        events = p.core.monitor.read_rows(directory, manifest, stem, count)
        if any(e.get('lineage') != lineage for e in events): raise ValueError('실제 답의 각case 계보가 다르다')
        rows.append(events)
    summary = p.core.monitor.recount(rows[0], bundle['monitor'], tokenizer=tok)
    p.core.validate_dialogues(rows[1], bundle['dialogues'], tok, lineage)
    if summary != report['monitor_summary'] or p.core.dialogue_summary(rows[1]) != report['dialogue_summary']:
        raise ValueError('전체 실제 답 재집계가 다르다')
    p.n.validate_native32(report['native32_fp32'])
    return report


def readback(p):
    from tokenizers import Tokenizer
    state = prepared(p); tok = Tokenizer.from_file(str(p.n.TOKENIZER))
    reports = {arm: read_evaluation(p, arm, state, tok) for arm in ARMS}
    p.write(p.path('readback'), dict(p.info(), status='CLOSED_RAW_RECOUNTED',
        evaluate_report_sha256={arm: file_sha(p.path('evaluate', arm)) for arm in ARMS},
        monitor={arm: report['monitor_summary'] for arm, report in reports.items()},
        dialogues={arm: report['dialogue_summary'] for arm, report in reports.items()},
        models_loaded=0, checkpoint_tensor_loads=0, checkpoints_written=0,
        scope='same Q/F source/exposure, route/parent both differ; QT descriptive package comparison only'))
    return 0


def phase_commands(mode, arm, cap, idle_proof=None):
    key(mode, arm)
    if type(cap) is not int or not 60 <= cap <= WORKER_LIMIT or idle_proof is not None and mode != 'cost':
        raise ValueError('60..7200초와 cost 전용 idle proof만 허용한다')
    if idle_proof is not None:
        path = idle_path(idle_proof)
        if path.name != 'idle_' + arm + '.json': raise ValueError('route별 exact idle proof 이름이 필요하다')
    py = [sys.executable, '-B', '-X', 'utf8']; base = py + [SCRIPT]
    command = base + ['--mode', mode, '--max-wall-sec', str(cap), '--worker', '--execute']
    if arm: command += ['--arm', arm]
    if idle_proof is not None: command += ['--idle-proof', str(idle_proof)]
    prior = 'source' if mode in ('source', 'prepare') else 'preflight'
    return [('REGRESSION', py + ['-m', 'unittest', TEST[:-3].replace('/', '.'), '-v']),
        ('PREFLIGHT', base + ['--mode', prior, '--max-wall-sec', '600', '--worker', '--execute']), ('EXECUTE', command)]


def worker(p, mode, arm, cap, idle_proof=None):
    phase_commands(mode, arm, cap, idle_proof); p.check()
    pid, pgid = os.getpid(), os.getpgid(0)
    if pid != pgid: raise ValueError('worker는 자기 PGID와 stdin0이 필요하다')
    readonly = mode in ('source', 'preflight'); training = mode in ('prepare', 'cost', 'train')
    activity = p.EVIDENCE / ('activity_' + key(mode, arm) + '.json')
    if not readonly and activity.exists(): raise FileExistsError('실패/완료 activity는 write-once다')
    metadata = p.info(); began = time.perf_counter(); start = datetime.now(timezone.utc).isoformat(); code, error = 9, None
    try:
        from scripts.p106b_gate_runtime import wall_limit
        with p.n.termination_guard(), wall_limit(cap):
            remaining = p.authority(training)
            if not readonly: remaining = min(remaining, ACTIVE_LIMIT - p.spent() - RECORD_RESERVE - (EVAL_RESERVE if training else 0))
            if cap > remaining: raise p.Pending('고정 worker cap이 절대UTC 또는 실제활동/예비 안에 들어가야 한다')
            if mode == 'source': source_state(p); result = 0
            elif mode == 'preflight': prepared(p); result = 0
            elif mode == 'prepare': result = prepare(p)
            elif mode in ('cost', 'train'): result = train(p, arm, cost=mode == 'cost', idle_proof=idle_proof, max_wall_sec=cap)
            elif mode == 'budget':
                result = 0 if budget(p, record=True)['fits'] else 8
                if result: raise p.Pending('양팔704회/평가/기록/재검산 예측이 예산을 넘는다')
            elif mode == 'evaluate': result = evaluate(p, arm)
            elif mode == 'readback': result = readback(p)
            if result != 0 or not readonly and not p.path(mode, arm).is_file(): raise ValueError('종료0에는 닫힌 실제 report가 필요하다')
            if metadata != p.info(): raise ValueError('worker 실행 중 전체 info/source/F4가 바뀌었다')
            code = 0
        return code
    except BaseException as exc:
        error = type(exc).__name__
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (p.Pending, FileNotFoundError, FileExistsError)) else 9
        raise
    finally:
        if not readonly:
            report, reference = p.path(mode, arm), p.CACHE / 'frozen_reference.json'
            p.write(activity, dict(schema=SCHEMA, tag=TAG, key=key(mode, arm), mode=mode, arm=arm,
                seconds=time.perf_counter() - began, started_at=start, ended_at=datetime.now(timezone.utc).isoformat(),
                worker_pid=pid, worker_pgid=pgid, returncode=code, complete=code == 0, error_type=error,
                max_wall_sec=cap, code_sha256=metadata['code_sha256'], result_sha256=file_sha(report) if report.is_file() else None,
                reference_sha256=file_sha(reference) if reference.is_file() else None))
        p.check()


def verify_training(p, mode, arm, cap):
    try:
        phase_commands(mode, arm, cap)
        if mode not in ('cost', 'train') or os.getpgid(0) != os.getpid(): raise ValueError('자기 PGID의 readonly cost/train verifier만 허용한다')
        if cap > p.authority(): raise ValueError('readonly verifier의 절대UTC cap이 부족하다')
        from scripts.p106b_gate_runtime import wall_limit
        with p.n.termination_guard(), wall_limit(cap):
            report = read_training(p, arm, cost=mode == 'cost')
        print('[NATIVE_BROAD4_VERIFY] ' + json.dumps(dict(mode=mode, arm=arm, updates=report['updates'],
            status='CLOSED_WORKER_STRICTLY_RECOUNTED', activity_sha256=file_sha(p.EVIDENCE / ('activity_' + key(mode, arm) + '.json'))), ensure_ascii=False), flush=True)
        return 0
    except KeyboardInterrupt: raise
    except Exception as exc:
        raise VerificationError('worker 실행 원형 보존; 후행 strict 검산 실패: ' + str(exc)) from exc
    finally: p.check()


class VerificationError(RuntimeError): pass


def launch_stage(p, command, fallback_cap):
    cap = int(command[command.index('--max-wall-sec') + 1]) if '--max-wall-sec' in command else fallback_cap
    rc = p.n.launch(command, min(cap + 120, p.authority()))
    actual = '--worker' in command and '--mode' in command and command[command.index('--mode') + 1] in ('cost', 'train')
    if not actual: return rc
    verification = None
    if rc == 0:
        mode, arm = command[command.index('--mode') + 1], command[command.index('--arm') + 1]
        print('[VERIFY_BEGIN] ' + key(mode, arm), flush=True)
        try:
            limit = min(600, cap, int(p.authority()))
            if limit < 60: raise VerificationError('후행 readonly UTC 여유가 부족하다')
            child = [sys.executable, '-B', '-X', 'utf8', SCRIPT, '--mode', mode, '--arm', arm,
                '--max-wall-sec', str(limit), '--verify-only', '--execute']
            verification = p.n.launch(child, min(limit + 120, p.authority()))
        except KeyboardInterrupt: verification = 130
        except Exception: verification = 9
        print('[VERIFY_END] rc=' + str(verification), flush=True)
    final = rc if rc else 0 if verification == 0 else 130 if verification == 130 else 9
    print('[NATIVE_BROAD4_EXECUTE_FINAL] ' + json.dumps(dict(worker_returncode=rc,
        worker_invoked=True, verification_invoked=verification is not None, verification_returncode=verification,
        status='EXECUTED_AND_VERIFIED' if final == 0 else 'WORKER_FAILED' if rc else 'EXECUTED_VERIFY_FAILED', returncode=final)), flush=True)
    return final


def main(argv=None):
    p = None
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--mode', choices=MODES, required=True); parser.add_argument('--arm', choices=ARMS)
        parser.add_argument('--max-wall-sec', type=int, default=600); parser.add_argument('--idle-proof')
        parser.add_argument('--worker', action='store_true'); parser.add_argument('--verify-only', action='store_true')
        action = parser.add_mutually_exclusive_group(required=True)
        action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
        args = parser.parse_args(argv); phases = phase_commands(args.mode, args.arm, args.max_wall_sec, args.idle_proof)
        if args.verify_only and (not args.execute or args.worker or args.mode not in ('cost', 'train') or args.idle_proof):
            raise ValueError('후행 readonly verifier 인자가 다르다')
        p = build_runtime()
        if args.check_only:
            print('[NATIVE_BROAD4_CHECK_ONLY] ' + json.dumps(p.info(), ensure_ascii=False), flush=True); return 0
        if args.verify_only: return verify_training(p, args.mode, args.arm, args.max_wall_sec)
        if args.worker: return worker(p, args.mode, args.arm, args.max_wall_sec, args.idle_proof)
        return p.n.pipeline(phases, lambda cmd: launch_stage(p, cmd, args.max_wall_sec),
            lambda line: print(line, flush=True), experiment='P106B_NATIVE_BROAD4_' + key(args.mode, args.arm))['returncode']
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if (isinstance(exc, (FileNotFoundError, FileExistsError))
            or p is not None and isinstance(exc, p.Pending)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[NATIVE_BROAD4_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True); return code
    finally:
        if p is not None: p.check()


if __name__ == '__main__': raise SystemExit(main())
