#!/usr/bin/env python3
"""원 Broad v2 자료와 P090B 부모를 보존하는 독립 기한 재개 경계.

원 모듈의 globals는 바꾸지 않는다. v2 읽기 provider와 v3 실행 모듈을
각각 private namespace에 두고, 준비는 기존 wire/course를 복제하지 않는
SHA bridge만 작성한다. 계산 본문·부모·선택·352회 조건은 원본 그대로다.
실제 자료/모델/GPU 실행과 Git은 root 소유이며 check-only는 코드만 읽는다.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
import math
import os
from pathlib import Path
import signal
import sys
import time
import traceback
import types
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT = 'scripts/diag_p106b_broad_resume.py'
TEST = 'scripts/test_p106b_broad_resume.py'
F4 = ROOT / 'handoff/audit/WIP_20261020_BROAD_RESUME_F4.json'
LEGACY = 'scripts/diag_p106b_broad_curriculum.py'
RECOVERY = 'scripts/diag_p106b_broad_recovery.py'
TAG, SCHEMA = 'p106b_broad_resume_v3_s1337', 'P106B_BROAD_RESUME_V1'
ORIGINAL_TAG = 'p106b_broad_curriculum_v2_s1337'
SELECTION_TAG = 'p106b_broad_curriculum_v1_s1337'
END = datetime(2026, 10, 21, 8, tzinfo=timezone.utc)
TRAIN_STOP = datetime(2026, 10, 21, 5, tzinfo=timezone.utc)
PARENT_CORE = 'E854AB4EC2E505DDC581CE08C94F9C8B4A8081E456AFBA193DF28A877E34A193'
PARENT_SHA = '12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950'
SOURCE_PINS = {
    LEGACY: '5DBA344FAE2D64A096B83D2161FB28C4E9EE6161B1042DBE0045CF0B4545E454',
    RECOVERY: '451B38A660D55C43E1656A1B0A7ED0464BAC6148F88876DF6DE7FF5E04D27E06',
    'scripts/p106b_broad_course.py': '9ACD5129CF73DE296C9003FE4392603409969909FF061174C3B29600276BAE7E',
    'scripts/test_p106b_broad_course.py': '5072020B67F4D655EDD602207D94A9AE79D8F0FE12F03557E86102E5CE3CAB73',
    'scripts/test_p106b_broad_curriculum.py': '3ABFA84E23B48390E95A98483E8A3D719FBDE17AE50CE7E4B31DE7572D5E89AC',
    'scripts/test_p106b_broad_recovery.py': '7A7C2738B38C23C8A7EE54AC43F77B4042FC19F81201B56FBEC3511BA47CF8CD',
}
BODY_NAMES = ('train_updates', 'train', 'dev_probe', 'expected_group', 'cost_group_ids',
    'read_training', 'emit_dialogue', 'run_dialogue', 'reused_parent_monitor', 'evaluate',
    'dialogue_summary', 'validate_dialogues', '_read_eval', 'readback', 'authority',
    'checkpoint', 'write', 'required', 'completion_binding', 'completion_report_path',
    'activity_key', 'launch', 'main', 'dialogue_turns', 'show_monitor', 'show_dialogue',
    'overlap_audit', '_wire', '_unwire', '_put', '_read', '_lines', 'public_contract',
    'validate_public_contract')
CAPTURED_NAMES = ('info', 'phase_commands', 'completed_activity', 'budget', 'worker', 'prepared')
CONSTANT_BINDINGS = ('ROOT', 'TAG', 'SCHEMA', 'CACHE', 'RAW', 'EVIDENCE', 'END', 'TRAIN_STOP',
                     'CODE', 'OWN_CODE')
FUNCTION_BINDINGS = ('info', 'source_pins', 'source_state', 'prepare', 'prepared',
    'completed_activity', 'spent_seconds', 'budget', 'worker', 'phase_commands',
    'select_dialogues', 'monitor_display_ids')
BINDING_ALLOWLIST = frozenset(CONSTANT_BINDINGS + FUNCTION_BINDINGS)
RECOVERY_BINDINGS = frozenset(('legacy', '_INFO', '_PHASES', '_DIALOGUES', '_DISPLAY'))
AUDIT_ATTRIBUTES = frozenset(('_resume_assert_unchanged', '_resume_captured',
    '_resume_provider', '_resume_recovery', '_resume_binding_names', '_resume_originals'))
WORKER_SCOPE = 'actual worker wall including full input verification; regression/wrapper excluded'


def canonical(value):
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest().upper()


def body_sha(function):
    """실행 중 달라질 수 있는 marshal intern 상태 대신 code 구조를 비교한다."""
    def normalized(value):
        if isinstance(value, types.CodeType):
            return dict(code=value.co_code.hex(), constants=[normalized(v) for v in value.co_consts],
                names=list(value.co_names), variables=list(value.co_varnames), free=list(value.co_freevars),
                cells=list(value.co_cellvars), args=value.co_argcount, posonly=value.co_posonlyargcount,
                kwonly=value.co_kwonlyargcount, locals=value.co_nlocals, stack=value.co_stacksize,
                flags=value.co_flags, name=value.co_name, file=value.co_filename, firstline=value.co_firstlineno,
                lines=value.co_lnotab.hex(), exceptions=getattr(value, 'co_exceptiontable', b'').hex())
        if isinstance(value, bytes):
            return ['bytes', value.hex()]
        if isinstance(value, tuple):
            return ['tuple', [normalized(v) for v in value]]
        if isinstance(value, frozenset):
            return ['frozenset', sorted((normalized(v) for v in value), key=repr)]
        return [type(value).__name__, repr(value)]
    return sha(normalized(inspect.unwrap(function).__code__))


class OriginalGuard:
    """원 두 모듈의 객체와 전체 info를 전후 대조한다."""
    def __init__(self, module):
        self.module, self.namespace = module, dict(vars(module))
        self.metadata = canonical(module.info())
        self.values = {k: canonical(v) for k, v in self.namespace.items()
            if k != '__builtins__' and isinstance(v, (dict, list, tuple))
            and _jsonable(v)}

    def check(self):
        now = vars(self.module)
        if set(now) != set(self.namespace) or any(now[k] is not v for k, v in self.namespace.items()):
            raise ValueError('원 Broad 모듈 globals 객체가 바뀌었다')
        if any(canonical(now[k]) != v for k, v in self.values.items()):
            raise ValueError('원 Broad 모듈의 중첩 메타데이터가 바뀌었다')
        if canonical(self.module.info()) != self.metadata:
            raise ValueError('원 Broad info/코드/부모/기한이 바뀌었다')


def _jsonable(value):
    try:
        canonical(value)
        return True
    except (TypeError, ValueError):
        return False


def checked_sources():
    """원 import 전에 작은 코드 여섯 개의 동결 SHA를 먼저 검산한다."""
    result = {}
    for relative, expected in SOURCE_PINS.items():
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError('동결 source가 없거나 연결 파일이다: ' + relative)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest().upper() != expected:
            raise ValueError('원 import 전 source SHA가 다르다: ' + relative)
        result[relative] = data
    return result


def _private_module(relative, data):
    module = types.ModuleType('_p106b_broad_resume_' + uuid.uuid4().hex)
    module.__file__ = str(ROOT / relative)
    exec(compile(data, str(ROOT / relative), 'exec', dont_inherit=True), vars(module))
    return module


def _namespace_same(module, expected):
    return set(vars(module)) == set(expected) and all(getattr(module, k) is v for k, v in expected.items())


def _json_values(namespace, excluded=()):
    return {k: canonical(v) for k, v in namespace.items()
            if k != '__builtins__' and k not in excluded and isinstance(v, (dict, list, tuple)) and _jsonable(v)}


def _values_same(module, expected):
    return all(canonical(getattr(module, k)) == v for k, v in expected.items())


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _activity_selector(key):
    if key in ('prepare', 'readback'):
        return key, None
    for mode in ('cost', 'train', 'evaluate'):
        for label in ('mixed', 'staged', 'parent'):
            if key == mode + '_' + label and (label != 'parent' or mode == 'evaluate'):
                return mode, None if label == 'parent' else label
    raise ValueError('등록되지 않은 Broad activity key다: ' + str(key))


def validate_activity(module, value, key, *, own=False):
    """원 완료/실패 벽시간을 새 실행 결과로 바꾸지 않고 검산한다."""
    if (value.get('schema') != module.SCHEMA or value.get('tag') != module.TAG
            or value.get('key') != key or not _finite(value.get('seconds'))
            or type(value.get('complete')) is not bool
            or type(value.get('max_wall_sec')) is not int or not 60 <= value['max_wall_sec'] <= 7200
            or value.get('code_sha256') != module.info()['code_sha256']):
        raise ValueError('동일 코드/namespace의 유효한 activity가 필요하다')
    code = value.get('returncode')
    if ((value['complete'] and (type(code) is not int or code != 0))
            or (not value['complete'] and code is not None and (type(code) is not int or code == 0))):
        raise ValueError('실패 activity를 완료로 승격할 수 없다')
    stamp = datetime.fromisoformat(value['recorded_at'])
    if stamp.tzinfo is None:
        raise ValueError('activity의 실제 aware UTC 기록이 필요하다')
    if key == 'recovery_equivalence':
        if own:
            raise ValueError('새 namespace에 원 recovery activity를 복제할 수 없다')
        return
    mode, arm = _activity_selector(key)
    if (value.get('mode') != mode or value.get('arm') != arm or value.get('scope') != WORKER_SCOPE
            or any(value.get(k) != v for k, v in module.completion_binding(mode, arm,
                required_report=value['complete']).items())):
        raise ValueError('activity와 실제 완료/부분 report SHA의 계보가 다르다')
    if own:
        started, ended = (datetime.fromisoformat(value[name]) for name in ('started_at', 'ended_at'))
        if (started.tzinfo is None or ended.tzinfo is None or started > ended or stamp != ended
                or type(value.get('pid')) is not int or value['pid'] <= 0
                or value.get('pgid') != value['pid']
                or (value['complete'] and value.get('error_type') is not None)
                or (not value['complete'] and not isinstance(value.get('error_type'), str))):
            raise ValueError('새 own-PGID worker의 실제 시작/종료/오류 기록이 필요하다')


def activity_ledger(module, *, recovery=None, own=False):
    entries, seen = [], set()
    if not module.EVIDENCE.exists():
        return entries
    for path in sorted(module.EVIDENCE.glob('activity_*.json')):
        path = module.safe(path)
        resolved = path.resolve()
        if resolved in seen:
            raise ValueError('activity를 두 번 합산할 수 없다')
        seen.add(resolved)
        key = path.stem[len('activity_'):]
        value = module.required(path)
        if key == 'recovery_equivalence':
            if recovery is None:
                raise ValueError('원 recovery reader가 필요하다')
            recovery.validate_equivalence()
            # 이 activity만 별도 recovery schema/scope를 갖는다.
            if value.get('complete') is not True or value.get('returncode') != 0 or not _finite(value.get('seconds')):
                raise ValueError('완료한 원 recovery wall만 계승한다')
        else:
            validate_activity(module, value, key, own=own)
            if value['complete']:
                mode, arm = _activity_selector(key)
                module.completed_activity(mode, arm)
        entries.append(dict(path=str(path.relative_to(module.ROOT)), sha256=module.digest(path),
            tag=value['tag'], key=key, seconds=value['seconds'], complete=value['complete'],
            scope='PRIOR_ACTUAL_WALL_ONLY_NOT_NEW_OUTPUT' if not own else 'OWN_ACTUAL_WORKER_WALL'))
    return entries


def bridge_value(metadata, binding):
    return dict(metadata, status='BROAD_RESUME_BRIDGE_PREPARED', binding=binding,
        original_payload_copied=False, original_source_changed=False, model_loaded=False,
        optimizer_updates=0, checkpoints_written=0, semantic_quality='NOT_RUN')


def bridge_contract(value, frozen_sha):
    return dict(value, frozen_sha256=frozen_sha)


def validate_bridge(value, public, expected, frozen_sha):
    if value != expected or public != bridge_contract(expected, frozen_sha):
        raise ValueError('완전한 새 info/원 frozen/CPU contract SHA bridge가 필요하다')


@contextmanager
def termination_guard():
    """bounded own worker의 TERM만 정리 가능한 130으로 바꾸고 handler를 복구한다."""
    previous, stopped = signal.getsignal(signal.SIGTERM), False
    def terminate(*_):
        nonlocal stopped
        if not stopped:
            stopped = True
            raise KeyboardInterrupt('Broad resume worker SIGTERM 정리')
    signal.signal(signal.SIGTERM, terminate)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def failure_code(module, exc):
    if isinstance(exc, KeyboardInterrupt):
        return 130
    return module.monitor.base.failure_status(exc)[1]


def run_worker(module, mode, arm, max_wall_sec):
    """계산 본문 밖의 시간·활동·정리 경계. fixture는 이 함수만 사용 가능하다."""
    module.phase_commands(mode, arm, max_wall_sec)
    module.authority()
    if os.getpgid(0) != os.getpid():
        raise ValueError('worker는 자기 PGID와 비대화식 stdin으로 실행해야 한다')
    from scripts.p106b_gate_runtime import wall_limit
    readonly = mode in ('source', 'preflight', 'budget')
    training = mode in ('prepare', 'cost', 'train')
    reserve = module.EVAL_RESERVE + module.RECORD_RESERVE if training else module.RECORD_RESERVE
    metadata = module.info()
    key = module.activity_key(mode, arm)
    path = module.safe(module.EVIDENCE / ('activity_' + key + '.json'))
    if not readonly and path.exists():
        raise FileExistsError('기존 완료/부분 worker activity를 보존한다')
    began, started, code, error = time.perf_counter(), datetime.now(timezone.utc), None, None
    try:
        with termination_guard(), wall_limit(max_wall_sec):
            absolute = module.authority(training=training) - (0 if training else module.RECORD_RESERVE)
            if max_wall_sec > min(absolute, module.ACTIVE_LIMIT - module.spent_seconds() - reserve):
                raise module.Pending('worker 상한과 기존 stage/deadline 예비를 함께 만족해야 한다')
            if mode == 'source':
                module.source_pins(); returned = 0
            elif mode == 'preflight':
                module.prepared(); returned = 0
            elif mode == 'budget':
                print('[BROAD_RESUME_BUDGET] ' + json.dumps(module.budget()), flush=True); returned = 0
            elif mode == 'prepare':
                returned = module.prepare()
            elif mode in ('cost', 'train'):
                returned = module.train(arm, cost=mode == 'cost')
            elif mode == 'evaluate':
                returned = module.evaluate(arm)
            elif mode == 'readback':
                returned = module.readback()
            else:
                raise ValueError('등록된 worker mode가 필요하다')
            if type(returned) is not int or returned != 0:
                raise ValueError('성공한 worker는 정확히0을 반환해야 한다')
            if not readonly:
                module.completion_binding(mode, arm, required_report=True)
            code = 0
        return code
    except BaseException as exc:
        code, error = failure_code(module, exc), exc
        raise
    finally:
        ended = datetime.now(timezone.utc)
        result = dict(schema=module.SCHEMA, tag=module.TAG, key=key, mode=mode, arm=arm,
            seconds=time.perf_counter() - began, returncode=code, complete=code == 0,
            max_wall_sec=max_wall_sec, code_sha256=metadata['code_sha256'],
            started_at=started.isoformat(), ended_at=ended.isoformat(), recorded_at=ended.isoformat(),
            pid=os.getpid(), pgid=os.getpgid(0), error_type=type(error).__name__ if error else None,
            error_message=str(error)[:2000] if error else None, scope=WORKER_SCOPE)
        if not readonly:
            result.update(module.completion_binding(mode, arm, required_report=False))
            module.write(path, result)
        # source/preflight/budget는 원 규약대로 무쓰기이며 stdout에도 실패 원형을 남긴다.
        print('[BROAD_RESUME_WORKER_FINAL] ' + json.dumps(result, ensure_ascii=False), flush=True)


def _build_runtime(original_legacy, original_recovery, sources):
    for relative, expected in SOURCE_PINS.items():
        if hashlib.sha256(sources[relative]).hexdigest().upper() != expected:
            raise ValueError('private 실행 전에 동결 source를 다시 검산해야 한다')
    guards = [OriginalGuard(original_legacy), OriginalGuard(original_recovery)]
    baseline, recovery_info = (g.metadata for g in guards)
    if (baseline.get('tag') != SELECTION_TAG or recovery_info.get('tag') != ORIGINAL_TAG
            or baseline.get('authority_end_utc') != '2026-10-20T08:00:00+00:00'
            or baseline.get('training_stop_utc') != '2026-10-20T05:00:00+00:00'
            or recovery_info.get('expected_parent_core') != PARENT_CORE
            or recovery_info.get('parent_sha256') != PARENT_SHA
            or recovery_info.get('selection_tag') != SELECTION_TAG
            or recovery_info.get('updates') != 352 or recovery_info.get('rows_per_pass') != 22528
            or recovery_info.get('groups_per_pass') != 176
            or (recovery_info.get('active_limit_seconds'), recovery_info.get('evaluation_reserve_seconds'),
                recovery_info.get('record_reserve_seconds')) != (10800, 1200, 600)
            or any(recovery_info['code_sha256'].get(k) != v for k, v in SOURCE_PINS.items())):
        raise ValueError('원 v2/P090B/선택/기한/352회/자원 조건을 바꿀 수 없다')
    provider = _private_module(LEGACY, sources[LEGACY])
    recovery = _private_module(RECOVERY, sources[RECOVERY])
    recovery_before = dict(vars(recovery))
    recapture = dict(legacy=provider, _INFO=provider.info, _PHASES=provider.phase_commands,
        _DIALOGUES=provider.select_dialogues, _DISPLAY=provider.monitor_display_ids)
    if set(recapture) != RECOVERY_BINDINGS:
        raise ValueError('private recovery의 명시한 참조만 다시 연결한다')
    for name, value in recapture.items():
        setattr(recovery, name, value)
    if any(getattr(recovery, k) is not v for k, v in recovery_before.items() if k not in RECOVERY_BINDINGS):
        raise ValueError('private recovery allowlist 밖 binding이 달라졌다')
    provider_pristine, recovery_pristine = dict(vars(provider)), dict(vars(recovery))
    provider_values, recovery_values = _json_values(provider_pristine), _json_values(recovery_pristine)
    p = _private_module(LEGACY, sources[LEGACY])
    pristine = dict(vars(p))
    pristine_values = _json_values(pristine, BINDING_ALLOWLIST)
    captured = {name: getattr(p, name) for name in CAPTURED_NAMES}
    captured_identity = dict(captured)
    parity = {name: body_sha(getattr(p, name)) for name in BODY_NAMES}
    captured_parity = {name: body_sha(value) for name, value in captured.items()}
    for name in BODY_NAMES:
        if body_sha(getattr(original_legacy, name)) != parity[name]:
            raise ValueError('원 계산 본문의 bytecode가 다르다: ' + name)
    recovery_parity = {name: body_sha(getattr(recovery, name)) for name, value in vars(original_recovery).items()
        if inspect.isfunction(value) and value.__module__ == original_recovery.__name__}
    for name, expected in recovery_parity.items():
        if body_sha(getattr(original_recovery, name)) != expected:
            raise ValueError('원 recovery 본문이 다르다: ' + name)
    expected_bindings, audit_bindings = {}, {}

    def originals_unchanged():
        for guard in guards:
            guard.check()
        if not _namespace_same(provider, provider_pristine) or not _namespace_same(recovery, recovery_pristine):
            raise ValueError('private v2 provider를 새 실행 namespace로 바꿀 수 없다')
        if not _values_same(provider, provider_values) or not _values_same(recovery, recovery_values):
            raise ValueError('private v2 provider의 중첩 메타데이터가 바뀌었다')
        for name, expected in recovery_parity.items():
            if body_sha(getattr(recovery, name)) != expected:
                raise ValueError('private recovery 본문이 달라졌다: ' + name)

    def assert_unchanged():
        originals_unchanged()
        if set(vars(p)) - set(pristine) != AUDIT_ATTRIBUTES | {'source_state'}:
            raise ValueError('미등록 private 전역이 추가되거나 감사 참조가 사라졌다')
        if any(getattr(p, k) is not v for k, v in pristine.items() if k not in BINDING_ALLOWLIST):
            raise ValueError('private 실행 allowlist 밖 객체가 바뀌었다')
        if not _values_same(p, pristine_values):
            raise ValueError('private 실행의 중첩 메타데이터가 바뀌었다')
        if any(getattr(p, k) is not v for k, v in expected_bindings.items()):
            raise ValueError('허용한 private binding 객체가 바뀌었다')
        for name, expected in parity.items():
            if body_sha(getattr(p, name)) != expected:
                raise ValueError('원 계산 본문이 달라졌다: ' + name)
        for name, expected in captured_parity.items():
            if (captured[name] is not captured_identity[name] or body_sha(captured[name]) != expected
                    or inspect.unwrap(captured[name]).__globals__ is not vars(p)):
                raise ValueError('보존한 private 참조/globals가 달라졌다: ' + name)
        if any(getattr(p, k) is not v for k, v in audit_bindings.items()):
            raise ValueError('감사 참조가 바뀌었다')

    @contextmanager
    def provider_scope():
        originals_unchanged()
        try:
            # 이 scope가 바꾸는 것은 private provider뿐이다. 원 모듈은 읽기도중에도 불변이다.
            with recovery.runtime_scope():
                yield provider
        finally:
            originals_unchanged()

    def info():
        originals_unchanged()
        value = canonical(recovery_info)
        pins = dict(value['code_sha256'])
        for path in (SCRIPT, TEST):
            target = Path(__file__).resolve().parents[1] / path
            pins[path] = file_sha(target) if target.is_file() else 'NOT_CREATED'
        value.update(schema=p.SCHEMA, tag=p.TAG, code_sha256=pins,
            code_complete='NOT_CREATED' not in pins.values(),
            authority_end_utc=p.END.isoformat(), training_stop_utc=p.TRAIN_STOP.isoformat(),
            resume_schema=SCHEMA, frozen_source_pins=SOURCE_PINS,
            original_tag=ORIGINAL_TAG, original_info_sha256=sha(recovery_info),
            original_authority_end_utc=recovery_info['authority_end_utc'],
            original_training_stop_utc=recovery_info['training_stop_utc'],
            original_payload_policy='EXACT_V2_PREPARED_AND_RECOVERY_EQUIVALENCE_NO_COPY',
            original_parent_policy='ORIGINAL_P090B_E854_NOT_NATIVE_RESUME',
            parent_initialization_changed=False, new_corpus=False, new_native_training=False,
            binding_allowlist=sorted(BINDING_ALLOWLIST), recovery_binding_allowlist=sorted(RECOVERY_BINDINGS),
            computational_body_sha256=parity, captured_body_sha256=captured_parity,
            prior_activity_accounting='ORIGINAL_V2_AND_OWN_VALIDATED_ACTUAL_ACTIVITIES_EACH_ONCE',
            readonly_activity_scope='source/preflight/budget stdout only; original regression/wrapper exclusion retained',
            termination_scope='OWN_WORKER_SIGTERM_TO_130_FINALLY; SIGKILL_CANNOT_GUARANTEE_ACTIVITY',
            raw_scope='NEW_ACTUAL_ANSWERS_IN_OWN_RAW; ORIGINAL_WIRE_AND_RAW_UNCHANGED',
            f4_sha256=file_sha(F4))
        if set(pins) != set(p.CODE):
            raise ValueError('원 CODE와 새 두 파일만 pin해야 한다')
        return canonical(value)

    def source_state():
        assert_unchanged()
        with provider_scope() as old:
            receipt = recovery.validate_equivalence()
            bundle = old.prepared()
            frozen, course = bundle['contract'], bundle['course'].report
            ledger = activity_ledger(old, recovery=recovery)
            if (len(bundle['course'].records) != 22528 or course['groups_per_pass'] != 176
                    or course['updates'] != 352 or len(frozen['native_train_offsets']) != 2816
                    or len(bundle['monitor']) != 1694 or len(bundle['dialogues']) != 16
                    or frozen['expected_parent_core'] != PARENT_CORE):
                raise ValueError('원 payload/부모/전체 소비 geometry가 다르다')
            paths = dict(frozen=old.CACHE / 'frozen.json', course=old.CACHE / 'course.json',
                cpu_contract=old.EVIDENCE / 'cpu_contract.json',
                equivalence=recovery.equivalence_path(), equivalence_activity=recovery.equivalence_activity_path())
            binding = dict(original_tag=ORIGINAL_TAG, selection_tag=SELECTION_TAG,
                original_info_sha256=sha(recovery_info),
                files={k: dict(path=str(v.relative_to(ROOT)), sha256=old.digest(v)) for k, v in paths.items()},
                original_wire_directory=str((old.CACHE / 'wire').relative_to(ROOT)),
                original_manifest_sha256=sha(frozen['manifests']),
                source_pins_sha256=sha(frozen['source_pins']),
                course_report_sha256=frozen['course_report_sha256'],
                ordered_record_hashes_sha256=course['ordered_record_hashes_sha256'],
                schedules_sha256=course['schedules_sha256'],
                rows_per_pass=22528, groups_per_pass=176, passes=2, updates=352,
                monitor_cases_sha256=frozen['monitor_cases_sha256'],
                dialogue_cases_sha256=frozen['dialogue_cases_sha256'],
                dialogue_selection=frozen['dialogue_selection'],
                monitor_display_ids=frozen['monitor_display_ids'],
                monitor_display_selection_sha256=frozen['monitor_display_selection_sha256'],
                dev_rows=frozen['dev_rows'], dev_targets=frozen['dev_targets'],
                dialogue_source_turns=frozen['dialogue_source_turns'],
                native_train_offsets_sha256=sha(frozen['native_train_offsets']), native_windows=2816,
                per_pass_totals=course['per_pass']['totals'], two_pass_totals=course['two_pass_totals'],
                original_equivalence_sha256=sha(receipt), prior_activities=ledger,
                parent=dict(path=recovery_info['parent'], sha256=PARENT_SHA, core_sha256=PARENT_CORE),
                source_admission_policy=recovery_info['source_admission_policy'],
                source_admission_sha256=sha(frozen['source_admission']),
                original_raw_directory=str(old.RAW.relative_to(ROOT)), new_payload_rows=0)
        assert_unchanged()
        return bundle, canonical(binding)

    def source_pins():
        _, binding = source_state()
        return binding

    def prepare():
        p.authority(training=True)
        if any(p.safe(path).exists() for path in (p.CACHE, p.RAW, p.EVIDENCE)):
            raise FileExistsError('기존 완료/부분 resume namespace를 보존한다')
        _, binding = source_state()
        expected = bridge_value(info(), binding)
        for path in (p.CACHE, p.RAW, p.EVIDENCE):
            path.mkdir(parents=True, exist_ok=False)
        p.write(p.CACHE / 'frozen.json', expected)
        contract = bridge_contract(expected, p.digest(p.CACHE / 'frozen.json'))
        p.write(p.EVIDENCE / 'cpu_contract.json', contract)
        validate_bridge(p.required(p.CACHE / 'frozen.json'), p.required(p.EVIDENCE / 'cpu_contract.json'),
            expected, p.digest(p.CACHE / 'frozen.json'))
        print('[BROAD_RESUME_PREPARED] exact original v2 payload/P090B; model/GPU NOT_RUN', flush=True)
        return 0

    def prepared(*, completed=True):
        bundle, binding = source_state()
        expected = bridge_value(info(), binding)
        validate_bridge(p.required(p.CACHE / 'frozen.json'), p.required(p.EVIDENCE / 'cpu_contract.json'),
            expected, p.digest(p.CACHE / 'frozen.json'))
        if completed:
            p.completed_activity('prepare')
        return bundle

    def completed_activity(mode, arm=None):
        value = captured['completed_activity'](mode, arm)
        validate_activity(p, value, p.activity_key(mode, arm), own=True)
        assert_unchanged()
        return value

    def spent_seconds():
        with provider_scope() as old:
            prior = activity_ledger(old, recovery=recovery)
        current = activity_ledger(p, own=True)
        paths = [v['path'] for v in (*prior, *current)]
        if len(paths) != len(set(paths)):
            raise ValueError('원/새 activity 경로가 겹쳐 이중 합산된다')
        return sum(v['seconds'] for v in (*prior, *current))

    def budget():
        assert_unchanged()
        value = captured['budget']()
        # 식/계수/예비는 원 budget 그대로다. 계보만 명시한다.
        value.update(original_active_limit_preserved=True, prior_activity_included_once=True,
            original_parent_core_sha256=PARENT_CORE, training_stop_utc=p.TRAIN_STOP.isoformat())
        assert_unchanged()
        return value

    def worker(mode, arm, max_wall_sec):
        assert_unchanged()
        try:
            return run_worker(p, mode, arm, max_wall_sec)
        finally:
            assert_unchanged()

    def phase_commands(mode, arm, max_wall_sec):
        phases = captured['phase_commands'](mode, arm, max_wall_sec)
        result = []
        for label, old in phases:
            command = [SCRIPT if part == LEGACY else part for part in old]
            if label == 'REGRESSION':
                for test in ('scripts.test_p106b_broad_recovery', TEST[:-3].replace('/', '.')):
                    if test not in command:
                        command.insert(command.index('-v'), test)
            elif command.count(SCRIPT) != 1 or LEGACY in command or RECOVERY in command:
                raise ValueError('모든 child는 새 resume driver만 호출해야 한다')
            result.append((label, command))
        return result

    bindings = dict(ROOT=ROOT, TAG=TAG, SCHEMA=SCHEMA, CACHE=ROOT / 'data_cache' / TAG,
        RAW=ROOT / 'runs/eval' / TAG, EVIDENCE=ROOT / 'test_result/evidence' / TAG,
        END=END, TRAIN_STOP=TRAIN_STOP,
        CODE=tuple(sorted(set((*recovery_info['code_sha256'], SCRIPT, TEST)))),
        OWN_CODE=tuple(dict.fromkeys((*pristine['OWN_CODE'], *original_recovery.OWN_CODE, SCRIPT, TEST))),
        info=info, source_pins=source_pins, source_state=source_state, prepare=prepare, prepared=prepared,
        completed_activity=completed_activity, spent_seconds=spent_seconds, budget=budget, worker=worker,
        phase_commands=phase_commands, select_dialogues=recovery.select_dialogues,
        monitor_display_ids=recovery.monitor_display_ids)
    if set(bindings) != BINDING_ALLOWLIST:
        raise ValueError('정확한 binding allowlist만 적용해야 한다')
    for name, value in bindings.items():
        setattr(p, name, value)
    expected_bindings.update(bindings)
    p._resume_assert_unchanged = assert_unchanged
    p._resume_captured = captured
    p._resume_provider = provider
    p._resume_recovery = recovery
    p._resume_binding_names = tuple(sorted(BINDING_ALLOWLIST))
    p._resume_originals = (original_legacy, original_recovery)
    audit_bindings.update({name: getattr(p, name) for name in AUDIT_ATTRIBUTES})
    assert_unchanged()
    return p


def build_runtime():
    sources = checked_sources()
    # 두 원 import도 private exec도 위의 SHA 검사 뒤에만 수행한다.
    original_legacy = importlib.import_module('scripts.diag_p106b_broad_curriculum')
    original_recovery = importlib.import_module('scripts.diag_p106b_broad_recovery')
    return _build_runtime(original_legacy, original_recovery, sources)


def main(argv=None):
    runtime = None
    try:
        runtime = build_runtime()
        try:
            return runtime.main(argv)
        finally:
            runtime._resume_assert_unchanged()
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        code = (failure_code(runtime, exc) if runtime is not None else
                130 if isinstance(exc, KeyboardInterrupt) else 9)
        if code == 9:
            traceback.print_exc(file=sys.stderr)
        print('[BROAD_RESUME_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
