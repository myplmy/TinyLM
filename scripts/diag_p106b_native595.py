#!/usr/bin/env python3
"""명시 recipe의 fresh native595 Q/F 대조. 원 controller/globals는 변경하지 않는다.

모델/GPU/실물 source 준비는 root 실행 전용이다. check-only는 코드/F4만 읽는다.
원 수치 helper를 그대로 호출하며 source·기한·CP·reader는 이 새 family가 소유한다.
Broad/SFT/public benchmark는 구현하지 않는다. weight-only CP는 resume가 아니다.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
SCRIPT, TEST = 'scripts/diag_p106b_native595.py', 'scripts/test_p106b_native595.py'
F4 = ROOT / 'handoff/audit/WIP_20261021_NATIVE595_F4.json'
TAG, SCHEMA = 'p106b_native595_v1_s1337', 'P106B_NATIVE595_V1'
NATIVE, AUDITOR, UTILITY = ('scripts/diag_p106b_native_weight_route.py',
    'scripts/diag_p106b_expansion_val_audit.py', 'scripts/diag_p106b_route_cross_resume.py')
PINS = {
    NATIVE: 'E51B68024CA0DC24A4994FFF51C733C05BA2773E3038A2B1CC5C127F6C736FAE',
    AUDITOR: 'CDE32A565DE664CAAF827819CC37B71F9D48149783594E5DA025EB4CED020F28',
    'scripts/test_p106b_expansion_val_audit.py': '99D9BAFF12B4E09A03829C66631F371DBB640AAD81B3090E73E7AADDA69D66DB',
    UTILITY: '1229A9033589BB17086747231AE5E6D9544A97BCA52A33FBE90CC4D1C0082C1D',
    'scripts/diag_p101a_sft_mtp.py': 'D7AC53E981E957C3C3A38417D19F1F3C01CE38DA736607FB6FC2B60E535A44DC',
    'scripts/p106b_weight_route.py': 'C2E77B6E8B3CD3338F853B0E5364BD41C9E3650091A11F652479494C55616187',
    'tinylm/train/muon.py': 'F2D81EF9903DC4BD2F9298BD65D3B210B1DE21141D22361A85A46F1DDE5F4676'}
AUDIT_REPORT = ROOT / 'test_result/evidence/p106b_expansion_val_audit_v1_s1337/report.json'
AUDIT_SHA = '3301C835C25ECCFD5C08D78EACFA5A67883E088F22572778B30D3C18800B0D40'
TRAIN = ROOT / 'data_cache/p106b_native_expansion_v1_s1337/train.bin'
META = TRAIN.parent / 'meta.json'
VAL = ROOT / 'data_cache/ko-en_601000000_chat32/val.bin'
TOKENIZER = ROOT / 'data_cache/tok-ko-en-32768-chat32.json'
END = datetime(2026, 10, 21, 8, tzinfo=timezone.utc)
NATIVE_STOP, TRAIN_STOP = datetime(2026, 10, 21, 2, 30, tzinfo=timezone.utc), datetime(2026, 10, 21, 5, tzinfo=timezone.utc)
ACTIVE, NATIVE_CAP, COST_CAP, EVAL_RESERVE, RECORD, FOLLOWUP = 43200, 18000, 900, 1200, 600, 7200
ARMS = ('ternary', 'float')
MODES = ('source', 'prepare', 'preflight', 'cost', 'budget', 'train', 'evaluate', 'readback')
IDLE_DIR = 'handoff/audit/' + TAG
BODY_NAMES = ('schedule', 'make_offsets', 'native_records', 'backward_micro', 'make_optimizers',
    'optimizer_receipt', 'actual_lrs', 'validate_optimizer_groups', 'route_receipt', 'validate_route_receipt',
    'native_probe', 'validate_native32', 'late_probe', 'cache_audit', 'validate_cpu_state')


@dataclass(frozen=True)
class NativeRecipe:
    updates: int = 4543
    micro: int = 8
    accum: int = 16
    seq: int = 1024
    seed: int = 1337
    pool_train_ids: int = 1191116192
    external_val_ids: int = 3005000
    scratch_core_sha256: str = '028C46B232D6D4C5205CAF15A7C259E3B1687347FC4838D00B3F3CB938C0D1C5'
    pool_sha256: str = '6DB291329CB1562E127A2D753F879C8ED8D3AB46789A3EF2B4BC3C4258846138'
    val_sha256: str = 'AD7EFB0DBD0D830A216B4D21A91C8ACB3FC41DAE2B23A3A55999AE8727AA374C'
    tokenizer_sha256: str = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'

    @property
    def targets(self): return self.micro * self.accum * self.seq
    @property
    def crops(self): return self.updates * self.micro * self.accum
    @property
    def draw(self): return self.updates * self.targets

    def schedule(self, native, step): return native.schedule(step, updates=self.updates)

    def offsets(self, native):
        return native.make_offsets(pool_tokens=self.pool_train_ids, updates=self.updates,
            micro=self.micro, accum=self.accum, seq=self.seq, seed=self.seed)

    def update(self, native, step):
        return dict(targets=self.targets, x_tokens=self.targets, native_replay_targets=0,
            crop_start=step * self.micro * self.accum, schedule=self.schedule(native, step))


RECIPE = NativeRecipe()


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def finite(value, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def safe(path, root=ROOT):
    path = Path(path)
    if (not path.is_absolute() or not path.is_relative_to(root) or '..' in path.parts
            or any(p in ('TinyDataset', '.aws', '.claude', '.codex', '.agents') for p in path.relative_to(root).parts)):
        raise ValueError('보호 경로가 아닌 정확한 저장소 경로만 허용한다')
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink(): raise ValueError('symlink 조상은 읽기 전에 거부한다')
        if ancestor == root: break
    return path


def required(path):
    path = safe(path)
    if not path.is_file(): raise FileNotFoundError(str(path))
    if path.stat().st_size >= 20_000_000: raise ValueError('작은 JSON은20MB 미만이어야 한다')
    return json.loads(path.read_text(encoding='utf-8'))


def key(mode, arm=None):
    if mode not in MODES or (arm not in ARMS if mode in ('cost', 'train', 'evaluate') else arm is not None):
        raise ValueError('단계별 실제 사용하는 route만 명시한다')
    return mode + ('_' + arm if arm else '')


class Runtime:
    def __init__(self, native, auditor, utility, guards, root=ROOT):
        self.n, self.audit, self.utility, self.guards, self.root = native, auditor, utility, guards, root
        self.CACHE, self.RAW, self.EVIDENCE = (root / p / TAG for p in ('data_cache', 'runs/eval', 'test_result/evidence'))
        self.Pending = native.Pending

    def check(self):
        for guard in self.guards: guard.check()

    def info(self):
        self.check(); contract = required(F4)
        limits = dict(authority_end_utc=END.isoformat(), native_training_stop_utc=NATIVE_STOP.isoformat(),
            final_training_stop_utc=TRAIN_STOP.isoformat(), family_actual_worker_seconds=ACTIVE,
            maximum_native_worker_seconds=NATIVE_CAP, eval_reserve_seconds=EVAL_RESERVE, record_reserve_seconds=RECORD,
            followup_training_reserved_seconds=FOLLOWUP, cost_worker_seconds=COST_CAP, forecast_factor=1.35,
            idle_min_seconds=300, idle_fresh_seconds=600)
        expected_recipe = dict(asdict(RECIPE), crops=RECIPE.crops, actual_targets=RECIPE.draw,
            pool_twice_margin_ids=RECIPE.pool_train_ids - 2 * RECIPE.draw, arms=list(ARMS),
            native_max_adam_lr=.001, native_max_muon_lr=.004, warmup_updates=100, decay_fraction=.2,
            quant_ramp_start='100/4543+0.05', quant_linear_end=.8, muon='original2D RMS/momentum.95/Nesterov/NS5',
            matrix_weight_decay=0, other_weight_decay='preserve original native AdamW groups; not global0', clip=1,
            grad_checkpoint=True, compile='default', train_amp='bf16', eval_math='fp32', mtp=False, headwise=False, orpo=False, thinking=False)
        if (contract.get('schema') != 'P106B_NATIVE595_F4_V1' or contract.get('tag') != TAG or contract.get('allowed_agent_new_sources') != [SCRIPT, TEST]
                or contract.get('limits') != limits or contract.get('recipe') != expected_recipe
                or AUDIT_SHA not in contract.get('source_bridge', '')): raise ValueError('정확한 root F4/recipe/상한이 필요하다')
        code = dict(self.n.info()['code_sha256'])
        for name, expected in PINS.items():
            actual = file_sha(safe(ROOT / name))
            if actual != expected: raise ValueError('동결 코드 SHA가 다르다: ' + name)
            code[name] = actual
        code.update({name: file_sha(ROOT / name) for name in (SCRIPT, TEST)})
        return dict(schema=SCHEMA, tag=TAG, code_sha256=code, code_complete=True, f4_sha256=file_sha(F4),
            native_recipe=asdict(RECIPE), planned_targets=RECIPE.draw, planned_crops=RECIPE.crops,
            pool_twice_margin=RECIPE.pool_train_ids - 2 * RECIPE.draw, limits=limits,
            helper_body_sha256={name: self.utility.body_sha(getattr(self.n, name)) for name in BODY_NAMES},
            original_globals_changed=False, original_controller_called=False,
            native_optimizer='original AdamW/Muon; matrixWD0 and original otherWD; no headwise',
            train_amp='bf16', compile='default', checkpoint_on=True, tf32=False, mtp=False,
            followup_broad_implemented=False, optimizer_checkpoint_saved=False,
            comparison='pool/source/crops/draw/WSD/anneal package vs299M; not tokens-only causal',
            source_scope='same-rule/32 exact-window audit, not arbitrary/semantic decontamination',
            activity_scope='own actual workers including failures once; readonly/verify/regression/wrapper/root idle excluded',
            quality='NOT_ESTABLISHED')

    def authority(self, training=False, now=None):
        now = datetime.now(timezone.utc) if now is None else now
        if now.tzinfo is None: raise ValueError('aware 실제 UTC가 필요하다')
        left = ((NATIVE_STOP if training else END) - now).total_seconds() - (0 if training else RECORD)
        if left <= 0: raise self.Pending('native02:30Z/권한08Z/기록600초 경계에 도달했다')
        return left

    def path(self, mode, arm=None): return self.EVIDENCE / key(mode, arm) / 'report.json'
    def checkpoint(self, arm):
        key('train', arm)
        return self.root / 'runs/ckpt' / ('m100s10_ko-en_' + TAG + '_' + arm + '_native.pt')

    def write(self, path, value):
        path = safe(path, self.root)
        if not any(path.is_relative_to(base) for base in (self.CACHE, self.RAW, self.EVIDENCE)): raise ValueError('자기 산출물 경계만 쓴다')
        data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
        if len(data) >= 20_000_000: raise ValueError('보고서는20MB 미만이어야 한다')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(data)

    def completed(self, mode, arm=None):
        value = required(self.EVIDENCE / ('activity_' + key(mode, arm) + '.json'))
        validate_activity(self, value, mode, arm)
        if value['returncode'] != 0 or not value['complete']: raise ValueError('실패 activity는 완료가 아니다')
        return value

    def spent(self):
        total = 0.
        for path in sorted(self.EVIDENCE.glob('activity_*.json')) if self.EVIDENCE.exists() else ():
            value = required(path); mode, arm = selector(value['key'])
            if path.name != 'activity_' + key(mode, arm) + '.json': raise ValueError('activity 경로가 다르다')
            validate_activity(self, value, mode, arm); total += value['seconds']
        return total


def build_runtime():
    for name, expected in PINS.items():
        if file_sha(safe(ROOT / name)) != expected: raise ValueError('import 전 source pin이 다르다')
    u = importlib.import_module(UTILITY[:-3].replace('/', '.'))
    n = importlib.import_module(NATIVE[:-3].replace('/', '.')); a = importlib.import_module(AUDITOR[:-3].replace('/', '.'))
    return Runtime(n, a, u, [u.ModuleGuard(v) for v in (n, a)])


def source_state(p):
    report = required(AUDIT_REPORT)
    if file_sha(AUDIT_REPORT) != AUDIT_SHA or p.audit.closed_result(report['info']) != 0: raise ValueError('완료한 독립0-hit 감사가 필요하다')
    p.audit.preflight_after_claim()  # 원 완료 보고/입력 meta만 읽으며 원 bin/기한은 재실행하지 않는다.
    meta = required(META)
    if (meta.get('train') != RECIPE.pool_train_ids or meta.get('val') != 0 or meta.get('train_sha256') != RECIPE.pool_sha256
            or meta.get('tokenizer_sha256') != RECIPE.tokenizer_sha256 or meta.get('current_val_sha256') != RECIPE.val_sha256):
        raise ValueError('변환meta의val0과 외부VAL을 분리해야 한다')
    fixed = ((TRAIN, RECIPE.pool_sha256, 2 * RECIPE.pool_train_ids), (VAL, RECIPE.val_sha256, 2 * RECIPE.external_val_ids),
        (TOKENIZER, RECIPE.tokenizer_sha256, None), (p.n.PARENT, p.n.PARENT_SHA, None))
    for path, expected, size in fixed:
        if size is not None and safe(path).stat().st_size != size or file_sha(safe(path)) != expected:
            raise ValueError('고정 TRAIN/외부VAL/tokenizer/geometry cfg 출처가 다르다')
    binding = dict(train=dict(path=str(TRAIN.relative_to(ROOT)), ids=RECIPE.pool_train_ids, sha256=RECIPE.pool_sha256),
        external_val=dict(path=str(VAL.relative_to(ROOT)), ids=RECIPE.external_val_ids, sha256=RECIPE.val_sha256),
        tokenizer=dict(path=str(TOKENIZER.relative_to(ROOT)), sha256=RECIPE.tokenizer_sha256), meta_sha256=file_sha(META),
        audit_report_sha256=AUDIT_SHA, audit_activity_sha256=file_sha(AUDIT_REPORT.parent / 'activity.json'),
        geometry_cfg_only=dict(path=str(p.n.PARENT.relative_to(ROOT)), sha256=p.n.PARENT_SHA, learned_weights_copied=False),
        direct_parent=None, fresh_scratch_sha256=RECIPE.scratch_core_sha256, audit_scope=report['info']['scan_scope'])
    p.check(); return binding


def prepare(p):
    if any(v.exists() for v in (p.CACHE, p.RAW, p.EVIDENCE)): raise FileExistsError('원/부분 namespace를 보존한다')
    started = time.perf_counter(); binding = source_state(p); offsets, description = RECIPE.offsets(p.n)
    import numpy as np
    p.CACHE.mkdir(parents=True, exist_ok=False)
    with (p.CACHE / 'offsets.npy').open('xb') as stream: np.save(stream, offsets, allow_pickle=False)
    reference = dict(p.info(), status='NATIVE595_CPU_PREPARED', binding=binding, offsets=description,
        offsets_sha256=file_sha(p.CACHE / 'offsets.npy'), cpu_consumer_seconds=time.perf_counter() - started,
        models_loaded=0, checkpoint_tensor_loads=0, optimizer_updates=0)
    p.write(p.CACHE / 'reference.json', reference)
    p.write(p.path('prepare'), dict(p.info(), status='CPU_BRIDGE_COMPLETE', reference_sha256=file_sha(p.CACHE / 'reference.json')))
    prepared(p, completed=False, binding=binding); return 0


def prepared(p, *, completed=True, binding=None):
    import numpy as np
    binding = source_state(p) if binding is None else binding; value = required(p.CACHE / 'reference.json')
    if (value.get('status') != 'NATIVE595_CPU_PREPARED' or value.get('binding') != binding
            or any(value.get(k) != v for k, v in p.info().items()) or not finite(value.get('cpu_consumer_seconds'), True)
            or file_sha(p.CACHE / 'offsets.npy') != value.get('offsets_sha256')): raise ValueError('완전한 동일 source/recipe/crop CPU bridge가 필요하다')
    offsets = np.load(p.CACHE / 'offsets.npy', allow_pickle=False); expected, desc = RECIPE.offsets(p.n)
    if offsets.dtype != np.int64 or not np.array_equal(offsets, expected) or value['offsets'] != desc: raise ValueError('명시 seed/581504 crop 전체가 다르다')
    if completed: p.completed('prepare')
    return value, offsets


def selector(value):
    for mode in MODES:
        for arm in ARMS if mode in ('cost', 'train', 'evaluate') else (None,):
            if value == key(mode, arm): return mode, arm
    raise ValueError('알 수 없는 activity key')


def validate_activity(p, value, mode, arm=None):
    begin, end = (datetime.fromisoformat(value[k]) for k in ('started_at', 'ended_at'))
    stop = NATIVE_STOP if mode in ('prepare', 'cost', 'train') else END
    if (mode in ('source', 'preflight') or value.get('tag') != TAG or value.get('schema') != SCHEMA
            or value.get('key') != key(mode, arm) or value.get('mode') != mode or value.get('arm') != arm
            or value.get('code_sha256') != p.info()['code_sha256'] or not finite(value.get('seconds'))
            or type(value.get('max_wall_sec')) is not int or not 60 <= value['max_wall_sec'] <= phase_cap(mode)
            or value['seconds'] > value['max_wall_sec'] + 30 or type(value.get('returncode')) is not int
            or type(value.get('complete')) is not bool or value['complete'] != (value['returncode'] == 0)
            or value['complete'] and value.get('error_type') is not None
            or not value['complete'] and not isinstance(value.get('error_type'), str)
            or begin.tzinfo is None or end.tzinfo is None or begin > end or begin >= stop or end > stop + timedelta(seconds=30)
            or type(value.get('pid')) is not int or value['pid'] <= 0 or value.get('pgid') != value['pid']):
        raise ValueError('같은 실제 worker의 닫힌 시간/오류 activity가 필요하다')
    for field, path in (('result_sha256', p.path(mode, arm)), ('reference_sha256', p.CACHE / 'reference.json')):
        if value.get(field) != (file_sha(path) if path.is_file() else None): raise ValueError('activity/report/reference SHA가 다르다')


def idle_path(value):
    if (not isinstance(value, str) or not value.startswith(IDLE_DIR + '/') or value.startswith('/')
            or '\\' in value or ':' in value or '\x00' in value
            or value != Path(value).as_posix() or any(p in ('', '.', '..') for p in value.split('/'))):
        raise ValueError('자기 tag의 상대 감사 경로만 허용한다')
    return safe(ROOT / value)


def idle_proof(p, relative, arm, *, now=None, monotonic=None):
    path = idle_path(relative)
    if path.name != 'idle_' + arm + '.json': raise ValueError('route별 proof가 필요하다')
    value = required(path); now = datetime.now(timezone.utc) if now is None else now
    monotonic = time.monotonic() if monotonic is None else monotonic
    begin, end = (datetime.fromisoformat(value[k]) for k in ('start_utc', 'end_utc'))
    a, b = value.get('start_monotonic'), value.get('end_monotonic')
    if (value.get('schema') != 'P106B_ROOT_IDLE_V1' or value.get('tag') != TAG or value.get('arm') != arm
            or value.get('key') != 'cost_' + arm or value.get('code_sha256') != p.info()['code_sha256']
            or now.tzinfo is None or begin.tzinfo is None or end.tzinfo is None or (end - begin).total_seconds() < 300
            or not 0 <= (now - end).total_seconds() <= 600 or not all(finite(v) for v in (a, b, monotonic))
            or b - a < 300 or not 0 <= monotonic - b <= 600 or value.get('no_gpu_work') is not True
            or value.get('no_heavy_cpu') is not True or not isinstance(value.get('evidence'), list) or not value['evidence']):
        raise ValueError('현재 전체 code map/UTC·monotonic300초/600초fresh 유휴 proof가 필요하다')
    paths = [idle_path(v['path']) for v in value['evidence']]
    for item, evidence in zip(value['evidence'], paths):
        if evidence == path or evidence.stat().st_size >= 20_000_000 or file_sha(evidence) != item.get('sha256'):
            raise ValueError('root 유휴 실제 근거 SHA가 다르다')
    return value


def train_updates(p, torch, model, forward, tokens, offsets, optimizers, route, output, *, cost=False):
    from scripts.p106b_shards import ShardWriter
    writer = ShardWriter(output, 'updates', limit=19_999_999); totals = Counter(); times = []; gmax = 0.; clips = 0
    try:
        for step in range(8 if cost else RECIPE.updates):
            p.authority(True); route.assert_active(); tick = time.perf_counter()
            for opt in optimizers: opt.zero_grad(set_to_none=True)
            policy = RECIPE.schedule(p.n, step)
            for opt, rates in zip(optimizers, p.base_lrs):
                for group, base in zip(opt.param_groups, rates): group['lr'] = base * policy['lr_factor']
            model.set_anneal(policy['anneal']); start = step * RECIPE.micro * RECIPE.accum
            chosen = offsets[start:start + RECIPE.micro * RECIPE.accum]
            micros = [p.n.native_records(tokens, chosen[i:i + RECIPE.micro]) for i in range(0, len(chosen), RECIPE.micro)]
            if len(micros) != 16: raise ValueError('전체16micro가 필요하다')
            observed = used = 0; numerator = 0.
            for batch in micros:
                total, count, x = p.n.backward_micro(model, forward, batch, RECIPE.targets, torch)
                numerator += total; observed += count; used += x
            if observed != RECIPE.targets or used != RECIPE.targets: raise ValueError('전체131072 target/input 분모가 다르다')
            grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            if not bool(torch.isfinite(grad)): raise ValueError('비유한 gradient는 step하지 않는다')
            for opt in optimizers: opt.step()
            torch.cuda.synchronize(); elapsed = time.perf_counter() - tick; times.append(elapsed)
            gmax = max(gmax, float(grad)); clips += int(grad > 1.)
            event = dict(update=step + 1, **RECIPE.update(p.n, step), ce=numerator / observed,
                crop_offsets_sha256=sha([int(v) for v in chosen]), actual_lrs=[[float(g['lr']) for g in opt.param_groups] for opt in optimizers],
                gradient_norm=float(grad), clipped=bool(grad > 1.), step_seconds=elapsed)
            writer.append(event); totals.update(targets=observed, x_tokens=used)
            if cost or (step + 1) % 100 == 0: print('[NATIVE595_UPDATE] ' + json.dumps(dict(arm=route.mode, **event)), flush=True)
        manifest = writer.close(lineage=dict(tag=TAG, arm=route.mode, cost=cost,
            reference_sha256=file_sha(p.CACHE / 'reference.json')))
        return dict(updates=len(times), totals=dict(totals), step_seconds=times, grad_max=gmax, clip_events=clips, event_manifest=manifest)
    finally: writer._finish()  # 실패 shard를 보존하되 성공 manifest를 만들지 않는다.


def optimizer_classes(optimizers): return [type(o).__module__ + '.' + type(o).__qualname__ for o in optimizers]


def finish_auxiliary(p, torch, model, forward, optimizers, tokens, offsets, route, *, cost):
    late = p.n.late_probe(torch, model, forward, optimizers, tokens, offsets) if cost else None
    model.clear_quant(); model.set_anneal(1.); final = p.n.modules()[0].state_fingerprint(model)
    native32 = None if cost else p.n.native_probe(torch, model)
    cache = p.n.cache_audit(torch, model, route) if cost else None
    return late, final, native32, cache


def cp_experiment(report):
    return dict(tag=TAG, arm=report['arm'], endpoint='native595', updates=4543, recipe_sha256=sha(asdict(RECIPE)),
        reference_sha256=report['reference_sha256'], scratch_core_sha256=RECIPE.scratch_core_sha256,
        parent_checkpoint_sha256=None, parent_core_sha256=None, core_sha256=report['final_core_sha256'])


def validate_payload(p, payload, cfg, arm, report):
    p.n.modules()[2].validate_route_metadata(payload.get('quantization_route'), arm)
    if (set(payload) != {'model', 'cfg', 'step', 'tokenizer_sha256', 'tokenizer_lineage', 'quantization_route', 'experiment'}
            or payload.get('cfg') != asdict(cfg) or payload.get('step') != 4543
            or payload.get('tokenizer_sha256') != RECIPE.tokenizer_sha256 or payload.get('tokenizer_lineage') != 'chat32'
            or payload.get('experiment') != cp_experiment(report) or report.get('tag') != TAG
            or report.get('updates') != 4543 or report.get('arm') != arm
            or report.get('initial_core_sha256') != RECIPE.scratch_core_sha256
            or report.get('parent_checkpoint_sha256') is not None or report.get('parent_core_sha256') is not None
            or report.get('optimizer_saved') is not False): raise ValueError('새4543/source/route 전용 weight-only CP가 필요하다')


def read_training(p, arm, *, cost=False, state=None):
    mode = 'cost' if cost else 'train'; p.completed(mode, arm)
    ref, offsets = prepared(p) if state is None else state
    if required(p.CACHE / 'reference.json') != ref: raise ValueError('실제 자기 reference가 필요하다')
    report = required(p.path(mode, arm)); count = 8 if cost else 4543
    if (any(report.get(k) != v for k, v in p.info().items()) or report.get('status') != ('COST8_COMPLETE' if cost else 'TRAIN_COMPLETE')
            or report.get('cost') is not cost or report.get('arm') != arm or report.get('updates') != count
            or report.get('reference_sha256') != file_sha(p.CACHE / 'reference.json')
            or report.get('initial_core_sha256') != RECIPE.scratch_core_sha256 or report.get('parent_checkpoint_sha256') is not None
            or report.get('parent_core_sha256') is not None or report.get('checkpoint_writes') != (0 if cost else 1)
            or report.get('optimizer_saved') is not False or not p.n.fingerprint(report.get('final_core_sha256'))):
        raise ValueError('같은 fresh recipe/source/전체 update의 닫힌 report가 필요하다')
    directory = p.RAW / key(mode, arm); manifest = report['event_manifest']
    if manifest.get('lineage') != dict(tag=TAG, arm=arm, cost=cost, reference_sha256=report['reference_sha256']): raise ValueError('raw 계보가 다르다')
    events = p.n.read_events(directory, manifest, count); groups = report['actual_optimizer_groups']
    p.n.validate_optimizer_groups(groups, 'native')
    if report.get('actual_optimizer_classes') != ['torch.optim.adamw.AdamW', 'tinylm.train.muon.Muon']: raise ValueError('원 실제 optimizer 클래스가 필요하다')
    for step, event in enumerate(events):
        if (event.get('update') != step + 1 or any(event.get(k) != v for k, v in RECIPE.update(p.n, step).items())
                or event.get('crop_offsets_sha256') != sha([int(v) for v in offsets[step * 128:(step + 1) * 128]])
                or event.get('actual_lrs') != p.n.actual_lrs(groups, event['schedule']['lr_factor'])
                or any(not finite(event.get(k)) for k in ('ce', 'gradient_norm')) or not finite(event.get('step_seconds'), True)
                or event.get('clipped') is not (event['gradient_norm'] > 1.)): raise ValueError('실제crop/4543지평/분모/gradient/LR가 다르다')
    if (report['step_seconds'] != [e['step_seconds'] for e in events] or report['grad_max'] != max(e['gradient_norm'] for e in events)
            or report['clip_events'] != sum(e['clipped'] for e in events)
            or report['totals'] != dict(targets=count * RECIPE.targets, x_tokens=count * RECIPE.targets)): raise ValueError('전량raw합계가 다르다')
    p.n.validate_route_receipt(report['route'], arm); p.n.modules()[2].validate_route_metadata(report['quantization_route'], arm)
    if cost: validate_auxiliary(p, report, offsets)
    else:
        p.n.validate_native32(report['native32_fp32'])
        if report.get('late_probe') is not None or report.get('cache_audit') is not None: raise ValueError('cost 보조계산과 실제train을 분리한다')
        if report.get('checkpoint') != str(p.checkpoint(arm).relative_to(p.root)) or file_sha(p.checkpoint(arm)) != report.get('checkpoint_sha256'): raise ValueError('새 CP 경로/바이트가 다르다')
    return report


def validate_auxiliary(p, report, offsets):
    late, cache, core = report.get('late_probe', {}), report.get('cache_audit', {}), report['final_core_sha256']
    if (late.get('optimizer_updates') != 0 or late.get('micro_batches') != 1 or late.get('targets') != 8192 or late.get('anneal') != 1.
            or late.get('core_before') != core or late.get('core_after') != core or late.get('finite') is not True
            or late.get('source_offsets_sha256') != sha([int(v) for v in offsets[:8]])
            or not finite(late.get('gradient_norm')) or not finite(late.get('seconds'), True)
            or cache.get('optimizer_updates') != 0 or cache.get('quality_forwards') != 0 or cache.get('finite') is not True
            or cache.get('core_before') != core or cache.get('core_after') != core or cache.get('route') != report['route']
            or cache.get('cache_tensors') != report['route']['tlinear_instances'] or not finite(cache.get('seconds'), True)
            or not finite(cache.get('cache_nominal_bytes'), True) or not finite(cache.get('extra_cache_storage_bytes'))): raise ValueError('cost8와분리한 late8192/무갱신/core/캐시 검산이 필요하다')
    for value in (late, cache):
        if any(not finite(value.get(k), True) for k in ('peak_allocated_mib', 'peak_reserved_mib')): raise ValueError('각 보조계산의 별도 peak가 필요하다')
    if report.get('checkpoint') is not None or report.get('checkpoint_sha256') is not None or report.get('native32_fp32') is not None:
        raise ValueError('cost는CP/품질평가를 저장하지 않는다')


def budget(p, *, record=False):
    state = prepared(p); estimates = {}
    for arm in ARMS:
        cost = read_training(p, arm, cost=True, state=state); times = cost['step_seconds']
        estimate = times[0] + max(times[1:]) * 4542 * 1.35 + cost['late_probe']['seconds'] + cost['cache_audit']['seconds'] + 300
        if p.path('train', arm).exists(): read_training(p, arm, state=state); estimate = 0.
        estimates[arm] = estimate
    pending = sum(estimates.values()); readonly_reserve = state[0]['cpu_consumer_seconds'] * 1.35 + 60
    total = p.spent() + pending + FOLLOWUP + EVAL_RESERVE + RECORD + readonly_reserve
    now = datetime.now(timezone.utc)
    fits = (total <= ACTIVE and pending <= p.authority(True)
        and pending + FOLLOWUP <= (TRAIN_STOP - now).total_seconds()
        and pending + FOLLOWUP + EVAL_RESERVE + readonly_reserve <= p.authority()
        and all(v <= NATIVE_CAP for v in estimates.values()))
    result = dict(p.info(), status='MEASURED_BUDGET', fits=fits, estimates_seconds=estimates,
        spent_actual_worker_seconds=p.spent(), predicted_readback_seconds=readonly_reserve, total_reserved_seconds=total,
        uncertainty='first+max7warm*4542*1.35+late/cache+300; not late-step guarantee or continuous peak safety')
    if record: p.write(p.path('budget'), result)
    return result


def train(p, arm, *, cost=False, proof=None, cap=900):
    state = prepared(p); ref, offsets = state; mode = 'cost' if cost else 'train'; directory = p.RAW / key(mode, arm)
    if directory.exists() or p.path(mode, arm).exists() or not cost and p.checkpoint(arm).exists(): raise FileExistsError('완료/부분 raw/CP를 보존한다')
    reservation = None
    if not cost:
        p.completed('budget'); reservation = budget(p)
        if not reservation['fits'] or reservation['estimates_seconds'][arm] > cap: raise p.Pending('실측 예산/현재 native 종료/worker cap이 부족하다')
    if cost and proof is None: raise p.Pending('root의 새5분 유휴 proof가 필요하다')
    receipt = idle_proof(p, proof, arm) if cost else None
    if cost:
        other = 'float' if arm == 'ternary' else 'ternary'
        if p.path('cost', other).exists():
            old = read_training(p, other, cost=True, state=state)['idle_proof']
            if datetime.fromisoformat(receipt['start_utc']) < datetime.fromisoformat(old['end_utc']): raise ValueError('같은 유휴 구간을 양팔에 재사용하지 않는다')
    from scripts.p106b_gate_runtime import idle_before_gpu
    import numpy as np
    tokens = np.memmap(TRAIN, dtype='<u2', mode='r')
    if len(tokens) != RECIPE.pool_train_ids: raise ValueError('전체 확장TRAIN만 사용한다')
    p.authority(True); idle_before_gpu()
    if cost: receipt = idle_proof(p, proof, arm)
    runtime, _, _ = p.n.modules(); directory.mkdir(parents=True, exist_ok=False)
    with p.n.routed_runtime(arm, None) as (torch, model, cfg, tok, scratch, route):
        if scratch != RECIPE.scratch_core_sha256 or runtime.state_fingerprint(model) != scratch: raise ValueError('같은028C46 fresh 초기화가 필요하다')
        model.clear_quant(); model.train(); model.set_anneal(0.)
        optimizers, groups = p.n.make_optimizers(model, 'native'); classes = optimizer_classes(optimizers)
        if classes != ['torch.optim.adamw.AdamW', 'tinylm.train.muon.Muon'] or any(opt.state for opt in optimizers): raise ValueError('원 fresh optimizer 클래스가 필요하다')
        if not cost:
            measured = read_training(p, arm, cost=True, state=state)
            if groups != measured['actual_optimizer_groups']: raise ValueError('cost/train 실제group이 다르다')
        p.base_lrs = [[g['lr'] for g in opt.param_groups] for opt in optimizers]
        os.environ['TORCHINDUCTOR_CACHE_DIR'] = str(p.CACHE / ('compile_' + key(mode, arm)))
        forward = torch.compile(model, mode='default'); torch.cuda.reset_peak_memory_stats(); began = time.perf_counter()
        try:
            result = train_updates(p, torch, model, forward, tokens, offsets, optimizers, route, directory, cost=cost)
            primary = dict(allocated_mib=torch.cuda.max_memory_allocated() / 2**20, reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
            late, final, native32, cache = finish_auxiliary(p, torch, model, forward, optimizers, tokens, offsets, route, cost=cost)
            result.update(p.info(), status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE', arm=arm, cost=cost,
                reference_sha256=file_sha(p.CACHE / 'reference.json'), initial_core_sha256=scratch, final_core_sha256=final,
                parent_checkpoint_sha256=None, parent_core_sha256=None, actual_optimizer_groups=groups,
                actual_optimizer_classes=classes, optimizer_saved=False, checkpoint_writes=0 if cost else 1,
                route=cache['route'] if cost else p.n.route_receipt(model, route), quantization_route=route.metadata,
                late_probe=late, cache_audit=cache, primary_peak=primary, native32_fp32=native32, idle_proof=receipt,
                reservation=reservation, whole_seconds=time.perf_counter() - began)
            if not cost:
                target = safe(p.checkpoint(arm)); target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    torch.save(dict(model=model.state_dict(), cfg=asdict(cfg), step=4543, tokenizer_sha256=RECIPE.tokenizer_sha256,
                        tokenizer_lineage='chat32', quantization_route=route.metadata, experiment=cp_experiment(result)), stream)
                result.update(checkpoint=str(target.relative_to(ROOT)), checkpoint_sha256=file_sha(target))
            p.write(p.path(mode, arm), result)
        except BaseException as exc:
            p.write(directory / 'partial_failure.json', dict(error_type=type(exc).__name__, error=str(exc)[:1500],
                actual_closed_updates='see closed manifest; unclosed shard is partial', checkpoint_may_be_partial=p.checkpoint(arm).exists(),
                status='PARTIAL_NOT_TRAIN_COMPLETE'))
            raise
        finally: del forward; model.clear_quant()
    return 0


@contextmanager
def loaded_runtime(p, arm, report):
    runtime, _, method = p.n.modules(); torch, model, cfg, tok, scratch = runtime.load_runtime('scratch_ntp')
    if scratch != RECIPE.scratch_core_sha256: raise ValueError('원 seed/cfg 초기화가 다르다')
    payload = torch.load(p.checkpoint(arm), map_location='cpu', weights_only=True)
    validate_payload(p, payload, cfg, arm, report); p.n.validate_cpu_state(model, payload, torch)
    with method.weight_route(model, arm) as check: check.assert_active()
    model = model.cuda(); torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    with method.weight_route(model, arm) as route:
        method.load_routed_state(model, payload, arm); del payload
        if runtime.state_fingerprint(model) != report['final_core_sha256']: raise ValueError('불러온 실제595 CP core가 다르다')
        try: yield torch, model, route
        finally: model.clear_quant()
    del model
    import gc
    gc.collect(); torch.cuda.empty_cache()


def evaluate(p, arm):
    state = prepared(p); report = read_training(p, arm, state=state)
    if p.path('evaluate', arm).exists(): raise FileExistsError('원 평가를 보존한다')
    from scripts.p106b_gate_runtime import idle_before_gpu
    p.authority(); idle_before_gpu()
    with loaded_runtime(p, arm, report) as (torch, model, route):
        before = p.n.modules()[0].state_fingerprint(model); value = p.n.native_probe(torch, model)
        after = p.n.modules()[0].state_fingerprint(model)
        if before != after: raise ValueError('native32 평가가 본체를 바꿨다')
        p.write(p.path('evaluate', arm), dict(p.info(), status='FIXED_NATIVE32_RECORDED', arm=arm, native32_fp32=value,
            checkpoint_sha256=report['checkpoint_sha256'], core_before=before, core_after=after, weights_changed=False))
    return 0


def readback(p):
    state = prepared(p); reports = {}
    for arm in ARMS:
        trained = read_training(p, arm, state=state); p.completed('evaluate', arm); value = required(p.path('evaluate', arm))
        if (any(value.get(k) != v for k, v in p.info().items()) or value.get('status') != 'FIXED_NATIVE32_RECORDED'
                or value.get('arm') != arm or value.get('checkpoint_sha256') != trained['checkpoint_sha256']
                or value.get('core_before') != trained['final_core_sha256'] or value.get('core_after') != trained['final_core_sha256']
                or value.get('weights_changed') is not False): raise ValueError('같은 arm/CP의 실제 고정32 평가가 필요하다')
        p.n.validate_native32(value['native32_fp32']); reports[arm] = value['native32_fp32']
    p.write(p.path('readback'), dict(p.info(), status='NATIVE595_RAW_RECOUNTED', native32=reports,
        evaluation_scope='fixed32 TF only; QA/dialogue/public benchmark NOT_RUN', models_loaded=0, checkpoint_tensor_loads=0))
    return 0


def phase_cap(mode): return NATIVE_CAP if mode == 'train' else EVAL_RESERVE if mode == 'evaluate' else COST_CAP


def commands(mode, arm, cap, proof=None):
    key(mode, arm)
    if type(cap) is not int or not 60 <= cap <= phase_cap(mode) or proof is not None and mode != 'cost': raise ValueError('단계별cap/proof가 다르다')
    if proof is not None: idle_path(proof)
    py = [sys.executable, '-B', '-X', 'utf8']; base = py + [SCRIPT]
    actual = base + ['--mode', mode, '--max-wall-sec', str(cap), '--worker', '--execute']
    if arm: actual += ['--arm', arm]
    if proof: actual += ['--idle-proof', proof]
    return [('REGRESSION', py + ['-m', 'unittest', TEST[:-3].replace('/', '.'), '-v']),
        ('PREFLIGHT', base + ['--mode', 'source' if mode in ('source', 'prepare') else 'preflight', '--max-wall-sec', '900', '--worker', '--execute']), ('EXECUTE', actual)]


def worker(p, mode, arm, cap, proof=None):
    commands(mode, arm, cap, proof); p.check()
    if os.getpid() != os.getpgid(0): raise ValueError('자기 PGID worker가 필요하다')
    readonly = mode in ('source', 'preflight'); training = mode in ('prepare', 'cost', 'train')
    activity = p.EVIDENCE / ('activity_' + key(mode, arm) + '.json')
    if not readonly and activity.exists(): raise FileExistsError('실패/완료 activity를 보존한다')
    metadata = p.info(); start = datetime.now(timezone.utc).isoformat(); began = time.perf_counter(); code, error = 9, None
    try:
        from scripts.p106b_gate_runtime import wall_limit
        with p.n.termination_guard(), wall_limit(cap):
            available = p.authority(training)
            if not readonly: available = min(available, ACTIVE - p.spent() - RECORD - (FOLLOWUP + EVAL_RESERVE if training else 0))
            if cap > available: raise p.Pending('worker cap/실제활동/후속·평가·기록 및절대종료가 부족하다')
            if mode == 'source': source_state(p); result = 0
            elif mode == 'preflight': prepared(p); result = 0
            elif mode == 'prepare': result = prepare(p)
            elif mode in ('cost', 'train'): result = train(p, arm, cost=mode == 'cost', proof=proof, cap=cap)
            elif mode == 'budget':
                if not budget(p, record=True)['fits']: raise p.Pending('현재 실측/시간으로 양 native+후속7200이 들어가지 않는다')
                result = 0
            elif mode == 'evaluate': result = evaluate(p, arm)
            elif mode == 'readback': result = readback(p)
            if result != 0 or not readonly and not p.path(mode, arm).is_file(): raise ValueError('종료0에 실제닫힌 report가 필요하다')
            if p.info() != metadata: raise ValueError('worker 중 code/F4가 바뀌었다')
            code = 0
        return 0
    except BaseException as exc:
        error = type(exc).__name__; code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (p.Pending, FileExistsError, FileNotFoundError)) else 9
        raise
    finally:
        if not readonly:
            result, ref = p.path(mode, arm), p.CACHE / 'reference.json'
            p.write(activity, dict(schema=SCHEMA, tag=TAG, key=key(mode, arm), mode=mode, arm=arm,
                seconds=time.perf_counter() - began, started_at=start, ended_at=datetime.now(timezone.utc).isoformat(), pid=os.getpid(), pgid=os.getpgid(0),
                max_wall_sec=cap, returncode=code, complete=code == 0, error_type=error, code_sha256=metadata['code_sha256'],
                result_sha256=file_sha(result) if result.is_file() else None, reference_sha256=file_sha(ref) if ref.is_file() else None))
        p.check()


class VerificationError(RuntimeError): pass


def verify(p, mode, arm, cap):
    try:
        commands(mode, arm, cap)
        if mode not in ('cost', 'train') or os.getpid() != os.getpgid(0) or cap > p.authority(): raise ValueError('자기 PGID/절대UTC의 readonly verifier만 허용한다')
        from scripts.p106b_gate_runtime import wall_limit
        with p.n.termination_guard(), wall_limit(cap): report = read_training(p, arm, cost=mode == 'cost')
        print('[NATIVE595_VERIFY] ' + json.dumps(dict(mode=mode, arm=arm, updates=report['updates'], status='CLOSED_WORKER_VERIFIED')), flush=True)
        return 0
    except KeyboardInterrupt: raise
    except Exception as exc: raise VerificationError('이미 실행한 worker의 후행 검산 실패: ' + str(exc)) from exc
    finally: p.check()


def launch_stage(p, command, cap):
    limit = int(command[command.index('--max-wall-sec') + 1]) if '--max-wall-sec' in command else cap
    result = p.n.launch(command, min(limit + 120, p.authority()))
    actual = '--worker' in command and '--mode' in command and command[command.index('--mode') + 1] in ('cost', 'train')
    if result or not actual: return result
    mode, arm = command[command.index('--mode') + 1], command[command.index('--arm') + 1]
    print('[VERIFY_BEGIN] ' + key(mode, arm), flush=True)
    try:
        check_cap = min(900, int(p.authority()))
        if check_cap < 60: raise VerificationError('후행 검산 UTC여유가 없다')
        rc = p.n.launch([sys.executable, '-B', '-X', 'utf8', SCRIPT, '--mode', mode, '--arm', arm,
            '--max-wall-sec', str(check_cap), '--verify-only', '--execute'], min(check_cap + 120, p.authority()))
    except KeyboardInterrupt: rc = 130
    except Exception: rc = 9
    print('[VERIFY_END] ' + key(mode, arm) + ' rc=' + str(rc) + '; worker already executed', flush=True)
    return 0 if rc == 0 else 130 if rc == 130 else 9


def main(argv=None):
    p = None
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--mode', choices=MODES, required=True); parser.add_argument('--arm', choices=ARMS)
        parser.add_argument('--max-wall-sec', type=int, default=900); parser.add_argument('--idle-proof')
        parser.add_argument('--worker', action='store_true'); parser.add_argument('--verify-only', action='store_true')
        action = parser.add_mutually_exclusive_group(required=True); action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
        args = parser.parse_args(argv); phases = commands(args.mode, args.arm, args.max_wall_sec, args.idle_proof); p = build_runtime()
        if args.check_only:
            print('[NATIVE595_CHECK_ONLY] ' + json.dumps(p.info(), ensure_ascii=False), flush=True); return 0
        if args.verify_only:
            if args.worker or args.idle_proof: raise ValueError('readonly verify 인자가 다르다')
            return verify(p, args.mode, args.arm, args.max_wall_sec)
        if args.worker: return worker(p, args.mode, args.arm, args.max_wall_sec, args.idle_proof)
        return p.n.pipeline(phases, lambda command: launch_stage(p, command, args.max_wall_sec),
            lambda line: print(line, flush=True), experiment='P106B_NATIVE595_' + key(args.mode, args.arm))['returncode']
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if (isinstance(exc, (FileExistsError, FileNotFoundError))
            or p is not None and isinstance(exc, p.Pending)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[NATIVE595_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True); return code
    finally:
        if p is not None: p.check()


if __name__ == '__main__': raise SystemExit(main())
