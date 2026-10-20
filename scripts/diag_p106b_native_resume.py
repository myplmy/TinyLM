#!/usr/bin/env python3
"""동결 native 부모와 원천을 연결하는 독립 기한 재개 경계.

원 모듈·제품의 전역을 고치지 않는다. 정확한 source를 새 private namespace에
평가하고 명시한 경계 binding만 교체한다. 학습/eval/gradient/optimizer 본문은
그대로이며 native 재학습은 허용하지 않는다. 실제 자산/모델/GPU는 root 소유다.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
import traceback
import types
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
SCRIPT = 'scripts/diag_p106b_native_resume.py'
TEST = 'scripts/test_p106b_native_resume.py'
F4 = ROOT / 'handoff/audit/WIP_20261020_NATIVE_RESUME_DEADLINE_F4.json'
SOURCE = ROOT / 'scripts/diag_p106b_native_weight_route.py'
SOURCE_SHA = 'E51B68024CA0DC24A4994FFF51C733C05BA2773E3038A2B1CC5C127F6C736FAE'
TAG, SCHEMA = 'p106b_native_resume_v2_s1337', 'P106B_NATIVE_RESUME_V2'
END = datetime(2026, 10, 21, 8, tzinfo=timezone.utc)
TRAIN_STOP = END - timedelta(hours=3)
MODES = ('prepare', 'source', 'preflight', 'sft_cost', 'budget', 'sft', 'evaluate', 'readback')
BODY_NAMES = ('train', 'evaluate', 'readback', 'backward_micro', 'native_records',
    'make_optimizers', 'optimizer_receipt', 'route_receipt', 'native_probe', 'cache_audit',
    'validate_payload', 'validate_cpu_state', 'cp_experiment', 'update_contract',
    'read_events', 'validate_route_receipt', 'validate_optimizer_groups', 'actual_lrs', 'validate_native32')
CAPTURED_NAMES = ('info', 'train_report', 'routed_runtime', 'spent_seconds', 'worker')
CONSTANT_BINDINGS = ('ROOT', 'TAG', 'SCHEMA', 'CACHE', 'RAW', 'EVIDENCE', 'END', 'TRAIN_STOP',
                     'MODES', 'CODE', 'OWN_CODE', 'Pending')
FUNCTION_BINDINGS = ('info', 'source_state', 'prepare', 'prepared', 'phase_key', 'checkpoint',
    'train_report', 'routed_runtime', 'spent_seconds', 'budget', 'worker', 'phase_commands',
    'termination_guard')
BINDING_ALLOWLIST = frozenset(CONSTANT_BINDINGS + FUNCTION_BINDINGS)
AUDIT_ATTRIBUTES = frozenset(('_resume_assert_unchanged', '_resume_captured', '_resume_original', '_resume_binding_names'))


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def canonical(value):
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def body_sha(function):
    # marshal의문자열intern표지는실행뒤달라질수있어알고리즘이아닌직렬화상태를비교하게된다.
    def normalized(value):
        if isinstance(value, types.CodeType):
            return dict(code=value.co_code.hex(), constants=[normalized(v) for v in value.co_consts],
                names=list(value.co_names), variables=list(value.co_varnames), free=list(value.co_freevars),
                cells=list(value.co_cellvars), args=value.co_argcount, posonly=value.co_posonlyargcount,
                kwonly=value.co_kwonlyargcount, locals=value.co_nlocals, stack=value.co_stacksize,
                flags=value.co_flags, name=value.co_name, file=value.co_filename, firstline=value.co_firstlineno,
                lines=value.co_lnotab.hex(), exceptions=getattr(value, 'co_exceptiontable', b'').hex())
        if isinstance(value, bytes): return ['bytes', value.hex()]
        if isinstance(value, tuple): return ['tuple', [normalized(v) for v in value]]
        if isinstance(value, frozenset): return ['frozenset', sorted((normalized(v) for v in value), key=repr)]
        return [type(value).__name__, repr(value)]
    return sha(normalized(inspect.unwrap(function).__code__))


def sft_estimates(costs, updates=384, factor=1.35):
    """실제 source reader와 분리한 자원 계산식. 시간 단위는 초다."""
    estimates = {}
    if set(costs) != {'ternary', 'float'} or type(updates) is not int or updates != 384 or factor != 1.35:
        raise ValueError('같은 두 팔·384회·사전계수1.35가 필요하다')
    for arm, value in costs.items():
        times = value.get('step_seconds', [])
        if len(times) != 8 or any(type(v) not in (int, float) or not 0 < v < float('inf') for v in times):
            raise ValueError('유한한 양수 SFTcost8 시간이 필요하다')
        estimates[arm + '_sft'] = times[0] + max(times[1:]) * (updates - 1) * factor + 300
    return estimates


def original_module():
    return importlib.import_module('scripts.diag_p106b_native_weight_route')


class OriginalGuard:
    """새 namespace 동작 전후에 원 모듈의 객체·값·info를 그대로 대조한다."""
    def __init__(self, original):
        self.original = original
        self.namespace = dict(vars(original))
        self.metadata = canonical(original.info())

    def check(self):
        now = vars(self.original)
        if set(now) != set(self.namespace) or any(now[k] is not v for k, v in self.namespace.items()):
            raise ValueError('원 native 모듈 전역 객체가 바뀌었다')
        if canonical(self.original.info()) != self.metadata:
            raise ValueError('원 native info/코드/기한 메타데이터가 바뀌었다')


def _build_runtime(original, source_bytes):
    """내부 factory. 테스트는 합성 original 경계를 주며 CLI는 정확한 원 모듈만 쓴다."""
    if hashlib.sha256(source_bytes).hexdigest().upper() != SOURCE_SHA:
        raise ValueError('동결 native source SHA가 다르므로 실행하지 않는다')
    guard = OriginalGuard(original)
    if (guard.metadata.get('tag') != 'p106b_native_weight_route_v1_s1337'
            or guard.metadata.get('authority_end_utc') != '2026-10-20T08:00:00+00:00'
            or guard.metadata.get('training_stop_utc') != '2026-10-20T05:00:00+00:00'
            or guard.metadata.get('code_sha256', {}).get('scripts/diag_p106b_native_weight_route.py') != SOURCE_SHA):
        raise ValueError('원 tag/기한/source pin을 새 값으로 고칠 수 없다')
    private = types.ModuleType('_p106b_native_resume_' + uuid.uuid4().hex)
    private.__file__ = str(SOURCE)
    exec(compile(source_bytes, str(SOURCE), 'exec', dont_inherit=True), vars(private))
    pristine = dict(vars(private))
    captured = {name: getattr(private, name) for name in CAPTURED_NAMES}
    captured_identity = dict(captured)
    parity = {name: body_sha(getattr(private, name)) for name in BODY_NAMES}
    for name in BODY_NAMES:
        if body_sha(getattr(original, name)) != parity[name]:
            raise ValueError('원 계산 함수와 동결 본문이 다르다: ' + name)
    captured_parity = {name: body_sha(function) for name, function in captured.items()}
    # 함수 본문은 private globals를 보며, 원 native loader는 original globals를 본다.
    p = private
    bindings = dict(ROOT=ROOT, TAG=TAG, SCHEMA=SCHEMA, CACHE=ROOT / 'data_cache' / TAG,
        RAW=ROOT / 'runs/eval' / TAG, EVIDENCE=ROOT / 'test_result/evidence' / TAG,
        END=END, TRAIN_STOP=TRAIN_STOP, MODES=MODES, Pending=original.Pending,
        OWN_CODE=tuple(dict.fromkeys((*pristine['OWN_CODE'], SCRIPT, TEST))),
        CODE=tuple(dict.fromkeys((*pristine['CODE'], SCRIPT, TEST))))
    for name, value in bindings.items(): setattr(p, name, value)
    active_mode = [None]
    expected_bindings = {}
    expected_audit = {}

    def assert_unchanged():
        guard.check()
        if set(vars(p)) - set(pristine) - AUDIT_ATTRIBUTES:
            raise ValueError('미등록 private 전역이 추가되었다')
        for name, expected in pristine.items():
            if name not in BINDING_ALLOWLIST and getattr(p, name) is not expected:
                raise ValueError('allowlist 밖 private 전역이 바뀌었다: ' + name)
        for name, expected in expected_bindings.items():
            if getattr(p, name) is not expected: raise ValueError('허용 binding 객체가 바뀌었다: ' + name)
        for name, expected in parity.items():
            if body_sha(getattr(p, name)) != expected: raise ValueError('계산 본문이 바뀌었다: ' + name)
        for name, expected in captured_parity.items():
            if (captured[name] is not captured_identity[name] or body_sha(captured[name]) != expected
                    or inspect.unwrap(captured[name]).__globals__ is not vars(p)):
                raise ValueError('보존한 private 본문/참조/globals가 바뀌었다: ' + name)
        for name, expected in expected_audit.items():
            if getattr(p, name) is not expected: raise ValueError('감사 참조가 바뀌었다: ' + name)

    def info():
        guard.check()
        # 원 scientific 메타데이터는 원 info 그대로 보존하고 새 경계 필드만 더한다.
        value = dict(guard.metadata)
        code_root = Path(__file__).resolve().parents[1]
        pins = dict(value['code_sha256'])
        for path in (SCRIPT, TEST):
            source = code_root / path
            pins[path] = file_sha(source) if source.is_file() else 'NOT_CREATED'
        if set(pins) != set(p.CODE): raise ValueError('원 CODE와 새 두 파일만 pin해야 한다')
        value.update(schema=p.SCHEMA, tag=p.TAG, code_sha256=pins,
            code_complete=all(v != 'NOT_CREATED' for v in pins.values()),
            authority_end_utc=p.END.isoformat(), training_stop_utc=p.TRAIN_STOP.isoformat())
        value.update(resume_schema=SCHEMA, adapter_version=2,
            frozen_source_sha256=SOURCE_SHA, original_info_sha256=sha(guard.metadata),
            original_tag=original.TAG, original_authority_end_utc=guard.metadata['authority_end_utc'],
            original_training_stop_utc=guard.metadata['training_stop_utc'],
            new_native_updates=0, native_updates_are_prior_history=True,
            initializer='EXACT_ORIGINAL_SAME_ARM_COMPLETED_NATIVE_CP',
            parent_training_weights_copied=True,
            initialization_fields_scope='DECLARED_SFT_PARENT_POLICY; prepare/source remain models_loaded0, actual execution is reported per stage',
            original_native_initializer=guard.metadata.get('initializer'),
            parent_sha256_role='PRIOR_P090B_GEOMETRY_ONLY_NOT_CURRENT_SFT_PARENT',
            actual_sft_parent='PER_ARM_ORIGINAL_NATIVE_BRIDGE_AND_PARENT_CHECKPOINT_SHA256',
            own_sft_initial_state='EACH_ORIGINAL_SAME_ARM_NATIVE_CORE_NOT_SHARED_SCRATCH',
            original_native_comparison=guard.metadata.get('comparison'),
            comparison='새 SFT는 각 원 native 부모에서 시작한다. 원 native의동일scratch비교와현재SFT부모초기값을혼동하지않는다.',
            binding_allowlist=sorted(BINDING_ALLOWLIST), computational_body_sha256=parity,
            audit_attributes=sorted(AUDIT_ATTRIBUTES),
            preserved_private_body_sha256=captured_parity,
            native_checkpoint_metadata='ORIGINAL_TAG_AND_ORIGINAL_STRICT_LOADER',
            sft_checkpoint_metadata='OWN_TAG_AND_PRIVATE_STRICT_LOADER',
            reused_ternary_cost='ORIGINAL_STRICT_READER_RESOURCE_ONLY_NOT_CURRENT_DAY_SPEED',
            prior_activity_accounting='original.spent_seconds plus own validated activities, each once',
            readonly_preflight_time='source/preflight are read-only; no duplicate training activity is synthesized',
            f4_sha256=file_sha(F4), new_corpus=False, native_pretraining_allowed=False)
        return canonical(value)

    def phase_key(mode, arm=None, endpoint=None):
        if mode not in MODES: raise ValueError('native 재학습/cost 모드는 재개 범위 밖이다')
        needs_arm = mode in ('sft_cost', 'sft', 'evaluate')
        if needs_arm != (arm in p.ARMS) or (not needs_arm and arm is not None):
            raise ValueError('사용할 arm만 정확히 명시해야 한다')
        needs_endpoint = mode in ('budget', 'evaluate')
        if needs_endpoint != (endpoint in p.ENDPOINTS) or (not needs_endpoint and endpoint is not None):
            raise ValueError('사용할 endpoint만 정확히 명시해야 한다')
        if mode == 'budget' and endpoint != 'sft': raise ValueError('재개 예산은 SFT만 계산한다')
        if mode == 'sft_cost' and arm != 'float': raise ValueError('Qcost8은 원 resource만 계승하며 다시 실행하지 않는다')
        return '_'.join(x for x in (mode, arm, endpoint) if x)

    def checkpoint(arm, endpoint):
        if arm not in p.ARMS or endpoint not in p.ENDPOINTS: raise ValueError('정확한 arm/endpoint가 필요하다')
        if endpoint == 'native': return original.checkpoint(arm, endpoint)
        return p.ROOT / 'runs/ckpt' / ('m100s10_ko-en_' + p.TAG + '_' + arm + '_sft.pt')

    def original_report(mode, arm):
        guard.check()
        if mode != 'train' and (mode, arm) != ('sft_cost', 'ternary'):
            raise ValueError('원 native 부모 또는 명시한 원 Qcost만 연결한다')
        result = original.train_report(mode, arm)
        if any(result.get(k) != v for k, v in guard.metadata.items()):
            raise ValueError('원 report의 코드·원 기한·원 조건이 다르다')
        if (result.get('tag') != original.TAG or result.get('arm') != arm
                or result.get('endpoint') != ('native' if mode == 'train' else 'sft')
                or result.get('updates') != (p.UPDATES if mode == 'train' else 8)):
            raise ValueError('원 부모/cost report를 새 계보로 바꿀 수 없다')
        guard.check()
        return result

    def bridge_data():
        guard.check()
        reference, frozen, cases, offsets = original.prepared()
        parents = {arm: original_report('train', arm) for arm in p.ARMS}
        qcost = original_report('sft_cost', 'ternary')
        if (parents['ternary']['scratch_core_sha256'] != parents['float']['scratch_core_sha256']
                or qcost['initial_core_sha256'] != parents['ternary']['final_core_sha256']
                or qcost['parent_checkpoint_sha256'] != parents['ternary']['checkpoint_sha256']):
            raise ValueError('같은 초기화와 정확한 자기 native 부모/cost 계보가 필요하다')
        report_bindings = {}
        for mode, arm in (('train', 'ternary'), ('train', 'float'), ('sft_cost', 'ternary')):
            key = original.phase_key(mode, arm)
            activity = original.completed_activity(mode, arm)
            path = original.result_path(key)
            report_bindings[key] = dict(tag=original.TAG, report_path=str(path.relative_to(original.ROOT)),
                report_sha256=original.digest(path), activity_sha256=original.digest(original.EVIDENCE / ('activity_' + key + '.json')),
                started_at=activity['started_at'], ended_at=activity['ended_at'], seconds=activity['seconds'],
                scope='ORIGINAL_NATIVE_PARENT' if mode == 'train' else 'RESOURCE_ONLY_ORIGINAL_QCOST8')
        binding = dict(original_info_sha256=sha(guard.metadata), original_tag=original.TAG,
            original_reference_sha256=original.digest(original.CACHE / 'frozen_reference.json'),
            original_cpu_contract_sha256=original.digest(original.EVIDENCE / 'cpu_contract.json'),
            original_offsets_sha256=original.digest(original.CACHE / 'native_offsets.npy'),
            original_offsets_path=str((original.CACHE / 'native_offsets.npy').relative_to(original.ROOT)),
            original_source_binding_sha256=sha(reference['binding']), original_offsets_description=reference['offsets'],
            cases_sha256=p.sha(cases), frozen_manifests_sha256=p.sha(frozen['manifests']),
            source_exposure_sha256=p.sha(frozen['exposure'][p.SOURCE_ARM]),
            native_parent_reports=report_bindings,
            native_parent_cores={arm: parents[arm]['final_core_sha256'] for arm in p.ARMS},
            native_parent_checkpoints={arm: parents[arm]['checkpoint_sha256'] for arm in p.ARMS},
            copied_new_corpus=False, new_native_training=False, qcost_quality_claim=False)
        guard.check()
        return reference, frozen, cases, offsets, binding

    def source_state():
        _, frozen, cases, _, binding = bridge_data()
        return frozen, cases, binding

    def prepare():
        p.authority(training=True)
        if any(p.safe(path).exists() for path in (p.CACHE, p.RAW, p.EVIDENCE)):
            raise FileExistsError('기존 완료/부분 재개 namespace를 보존한다')
        reference, _, _, _, binding = bridge_data()
        for path in (p.CACHE, p.RAW, p.EVIDENCE): path.mkdir(parents=True, exist_ok=False)
        result = dict(info(), status='NATIVE_RESUME_BRIDGE_PREPARED', binding=binding,
            display_ids=reference['display_ids'], offsets=reference['offsets'],
            offsets_file_sha256=reference['offsets_file_sha256'], native_schedule=reference['native_schedule'],
            actual_model_initialization='NOT_RUN', models_loaded=0, optimizer_updates=0, checkpoint_writes=0)
        p.write(p.CACHE / 'frozen_reference.json', result)
        p.write(p.EVIDENCE / 'cpu_contract.json', dict(result, frozen_reference_sha256=p.digest(p.CACHE / 'frozen_reference.json')))
        return 0

    def prepared():
        reference, frozen, cases, offsets, binding = bridge_data()
        own = p.required(p.CACHE / 'frozen_reference.json')
        expected = dict(info(), status='NATIVE_RESUME_BRIDGE_PREPARED', binding=binding,
            display_ids=reference['display_ids'], offsets=reference['offsets'],
            offsets_file_sha256=reference['offsets_file_sha256'], native_schedule=reference['native_schedule'],
            actual_model_initialization='NOT_RUN', models_loaded=0, optimizer_updates=0, checkpoint_writes=0)
        if (own != expected or p.required(p.EVIDENCE / 'cpu_contract.json') !=
                dict(own, frozen_reference_sha256=p.digest(p.CACHE / 'frozen_reference.json'))):
            raise ValueError('새 bridge와 원 prepared/mask/crops/cases의 계보가 다르다')
        p.completed_activity('prepare'); guard.check()
        return own, frozen, cases, offsets

    def train_report(mode, arm):
        if arm not in p.ARMS: raise ValueError('정확한 arm이 필요하다')
        if mode == 'train' or (mode, arm) == ('sft_cost', 'ternary'): return original_report(mode, arm)
        if mode not in ('sft', 'sft_cost'): raise ValueError('native 재학습/cost reader를 새 namespace에 만들지 않는다')
        assert_unchanged()
        result = captured['train_report'](mode, arm)
        guard.check()
        return result

    @contextmanager
    def routed_runtime(arm, endpoint=None):
        if arm not in p.ARMS or endpoint not in p.ENDPOINTS:
            raise ValueError('native 무작위 실행 없이 명시한 완료 종점만 읽는다')
        p.execution_remaining(active_mode[0] in ('prepare', 'sft_cost', 'sft'))
        assert_unchanged()
        # 원 native loader는 원 cp_experiment/reader/globals 전체를 유지한다.
        loader = original.routed_runtime if endpoint == 'native' else captured['routed_runtime']
        try:
            with loader(arm, endpoint) as value:
                p.execution_remaining(active_mode[0] in ('prepare', 'sft_cost', 'sft'))
                yield value
        finally: guard.check()

    def spent_seconds():
        prior = original.spent_seconds()
        current = captured['spent_seconds']()
        if not p.finite(prior) or not p.finite(current): raise ValueError('유한한 원/새 activity 합계가 필요하다')
        guard.check()
        return prior + current

    def budget(endpoint, record=False):
        if endpoint != 'sft': raise ValueError('완료한 native를 다시 예산에 편성하지 않는다')
        prepared(); spent = spent_seconds()
        parents = {arm: original_report('train', arm) for arm in p.ARMS}
        costs = {arm: train_report('sft_cost', arm) for arm in p.ARMS}
        estimates, completed = sft_estimates(costs, p.SFT_UPDATES, p.FORECAST_FACTOR), []
        for arm in p.ARMS:
            r = costs[arm]; times = r['step_seconds']
            if (len(times) != 8 or any(not p.finite(v, True) for v in times)
                    or r['initial_core_sha256'] != parents[arm]['final_core_sha256']):
                raise ValueError('각 원 native 부모에서 측정한 SFTcost8이 필요하다')
            if p.result_path(phase_key('sft', arm)).exists(): train_report('sft', arm); completed.append(arm + '_sft')
        pending = sum(value for key, value in estimates.items() if key not in completed)
        needed = pending + p.FINISH_RESERVE
        value = dict(info(), status='RESOURCE_FORECAST', endpoint='sft', spent_seconds=spent,
            estimates_seconds=estimates, completed=completed, remaining_training_seconds=p.authority(True),
            remaining_total_seconds=p.authority(), needed_seconds=needed,
            unmeasured_sft_reserve_seconds=0.,
            evaluation_and_record_reserve_seconds=p.FINISH_RESERVE,
            fits=(spent + needed <= p.ACTIVE_LIMIT and pending <= p.authority(True) and needed <= p.authority()),
            reused_qcost_report_sha256=original.digest(original.result_path(original.phase_key('sft_cost', 'ternary'))),
            uncertainty='원 Qcost는당시resource만계승하며새floatcost와날짜별속도우열을주장하지않는다')
        if record: p.write(p.result_path(phase_key('budget', endpoint='sft')), value)
        return value

    @contextmanager
    def termination_guard():
        import signal
        previous, stopped = signal.getsignal(signal.SIGTERM), False
        def terminate(*_):
            nonlocal stopped
            if not stopped: stopped = True; raise KeyboardInterrupt('재개 worker SIGTERM 정리')
        signal.signal(signal.SIGTERM, terminate)
        try: yield
        finally: signal.signal(signal.SIGTERM, previous)

    def worker(mode, arm, endpoint, max_wall_sec):
        phase_key(mode, arm, endpoint)
        if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 21600:
            raise ValueError('정확한60..21600초 worker 상한이 필요하다')
        assert_unchanged(); active_mode[0] = mode
        try:
            if mode in ('source', 'preflight'):
                from scripts.p106b_gate_runtime import wall_limit
                if max_wall_sec > min(p.execution_remaining(), p.ACTIVE_LIMIT - spent_seconds()):
                    raise p.Pending('읽기 검산 상한이 새 기한/활동 예산을 넘는다')
                with termination_guard(), wall_limit(max_wall_sec):
                    source_state() if mode == 'source' else prepared()
                return 0
            return captured['worker'](mode, arm, endpoint, max_wall_sec)
        finally:
            active_mode[0] = None; assert_unchanged()

    def phase_commands(mode, arm, endpoint, max_wall_sec):
        phase_key(mode, arm, endpoint)
        if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 21600:
            raise ValueError('정확한60..21600초 worker 상한이 필요하다')
        py = [sys.executable, '-B', '-X', 'utf8']; base = py + [SCRIPT]
        actual = base + ['--mode', mode, '--worker', '--execute', '--max-wall-sec', str(max_wall_sec)]
        if arm: actual += ['--arm', arm]
        if endpoint: actual += ['--endpoint', endpoint]
        prior = 'source' if mode in ('source', 'prepare') else 'preflight'
        return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_native_resume', '-v']),
            ('PREFLIGHT', base + ['--mode', prior, '--worker', '--execute', '--max-wall-sec', '600']),
            ('EXECUTE', actual)]

    replacements = dict(info=info, phase_key=phase_key, checkpoint=checkpoint, source_state=source_state,
        prepare=prepare, prepared=prepared, train_report=train_report, routed_runtime=routed_runtime,
        spent_seconds=spent_seconds, budget=budget, worker=worker, phase_commands=phase_commands,
        termination_guard=termination_guard)
    if set(bindings) | set(replacements) != BINDING_ALLOWLIST:
        raise ValueError('명시한 binding allowlist와 정확히 일치해야 한다')
    for name, value in replacements.items(): setattr(p, name, value)
    expected_bindings.update({name: getattr(p, name) for name in BINDING_ALLOWLIST})
    # underscore 속성은 감사용이며 실행 본문이 읽는 scientific binding이 아니다.
    p._resume_assert_unchanged = assert_unchanged
    p._resume_captured = captured
    p._resume_original = original
    p._resume_binding_names = tuple(sorted(BINDING_ALLOWLIST))
    expected_audit.update({name: getattr(p, name) for name in AUDIT_ATTRIBUTES})
    assert_unchanged()
    return p


def build_runtime():
    source_bytes = SOURCE.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest().upper() != SOURCE_SHA:
        raise ValueError('원 모듈 import 전에 동결 source SHA부터 확인해야 한다')
    original = original_module()
    runtime = _build_runtime(original, source_bytes)
    for name, function in runtime._resume_captured.items():
        if body_sha(getattr(original, name)) != body_sha(function):
            raise ValueError('실제 원 모듈의 경계 함수가 동결 source와 다르다: ' + name)
    return runtime


def main(argv=None):
    runtime = None
    try:
        runtime = build_runtime()
        try: return runtime.main(argv)
        finally: runtime._resume_assert_unchanged()
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        pending = runtime is not None and isinstance(exc, runtime.Pending)
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if pending or isinstance(exc, (FileNotFoundError, FileExistsError)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[NATIVE_RESUME_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__': raise SystemExit(main())
