#!/usr/bin/env python3
"""동결 교차 평가 본문에 endpoint별 출처와 새 기한만 연결한다.

native CP/report는 원 연구, SFT CP/report와 네 diagonal은 native_resume_v2다.
보고서 TAG를 바꾸지 않으며 n facade도 private cross globals에만 연결한다.
실제 준비는 네 diagonal 완료 뒤 root가 수행한다. 학습/CP 저장 경로는 없다.
"""
from __future__ import annotations

from datetime import datetime, timezone
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT, TEST = 'scripts/diag_p106b_route_cross_resume.py', 'scripts/test_p106b_route_cross_resume.py'
F4 = ROOT / 'handoff/audit/WIP_20261020_ROUTE_CROSS_RESUME_F4.json'
SOURCE = 'scripts/diag_p106b_route_cross_readout.py'
NATIVE = 'scripts/diag_p106b_native_weight_route.py'
RESUME = 'scripts/diag_p106b_native_resume.py'
SOURCE_PINS = {
    SOURCE: '2162B620A66641137399647F185E92F37419E21586B0C6C14FFD71748692355B',
    NATIVE: 'E51B68024CA0DC24A4994FFF51C733C05BA2773E3038A2B1CC5C127F6C736FAE',
    RESUME: 'DD4FD5F76192BA35D6FB95A8D7384BC4E23996404686AB6932B0A25CFCB56ECC',
    'scripts/test_p106b_route_cross_readout.py':
        '84A9B935ED5B991B00E17D7B3B34757EF31E8800745F96EC0352D1E451AD3457',
}
TAG, SCHEMA = 'p106b_route_cross_resume_v2_s1337', 'P106B_ROUTE_CROSS_RESUME_V1'
ORIGINAL_TAG, NATIVE_TAG, SFT_TAG = ('p106b_route_cross_v1_s1337',
    'p106b_native_weight_route_v1_s1337', 'p106b_native_resume_v2_s1337')
END = datetime(2026, 10, 21, 8, tzinfo=timezone.utc)
FAMILY_LIMIT = 8400
BINDING_ALLOWLIST = frozenset(('ROOT', 'TAG', 'SCHEMA', 'CACHE', 'RAW', 'EVIDENCE', 'END',
    'CODE', 'OWN_CODE', 'n', 'info', 'authority', 'source_state', 'cross_lineage', 'worker',
    'phase_commands', 'spent_seconds', 'FAMILY_LIMIT'))
BODY_NAMES = ('safe', 'exists', 'digest', 'raw_bytes', 'required', 'write', 'phase_key', 'slot',
    'result_path', 'tokenizer', 'read_answers', 'prefix_case', 'validate_event', 'diagonal',
    'prepare', 'prepared', 'cross_runtime', 'evaluate', 'validate_cross_report', 'paired',
    'readback', 'validate_activity', 'completed_activity', 'launch_phase', 'main')
CAPTURED_NAMES = ('info', 'source_state', 'cross_lineage', 'worker', 'phase_commands')
AUDIT_ATTRIBUTES = frozenset(('_resume_assert_unchanged', '_resume_captured',
    '_resume_original', '_resume_native', '_resume_sft', '_resume_facade'))
FACADE_BINDINGS = frozenset(('ROOT', 'TAG', 'CODE', 'CACHE', 'RAW', 'EVIDENCE', 'TOKENIZER',
    'TOKENIZER_SHA', 'PARENT_CORE', 'info', 'prepared', 'phase_key', 'result_path', 'required',
    'completed_activity', 'modules', 'validate_route_receipt', 'validate_native32', 'native_probe',
    'route_receipt', 'validate_payload', 'validate_cpu_state', 'fingerprint', 'finite',
    'termination_guard', 'launch', 'checkpoint', 'train_report', 'cp_experiment'))


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


def _json_values(namespace, excluded=()):
    result = {}
    for key, value in namespace.items():
        if key == '__builtins__' or key in excluded or not isinstance(value, (dict, list, tuple)):
            continue
        try: result[key] = canonical(value)
        except (TypeError, ValueError): pass
    return result


class ModuleGuard:
    def __init__(self, module):
        self.module, self.namespace = module, dict(vars(module))
        self.values = _json_values(self.namespace)
        self.bodies = {k: body_sha(v) for k, v in self.namespace.items() if inspect.isfunction(v)}
        self.metadata = canonical(module.info()) if hasattr(module, 'info') else None

    def check(self):
        current = vars(self.module)
        if (set(current) != set(self.namespace) or any(current[k] is not v for k, v in self.namespace.items())
                or any(canonical(current[k]) != v for k, v in self.values.items())):
            raise ValueError('원 provider/cross globals 객체나 중첩 값이 바뀌었다')
        if self.metadata is not None and canonical(self.module.info()) != self.metadata:
            raise ValueError('원 provider/cross 전체 info와 기한이 바뀌었다')
        if any(body_sha(current[k]) != value for k, value in self.bodies.items()):
            raise ValueError('원 provider/cross 함수 본문이 메모리에서 바뀌었다')


class FrozenFacade:
    __slots__ = ('_bindings',)
    def __init__(self, bindings):
        if set(bindings) != FACADE_BINDINGS:
            raise ValueError('명시한 n facade binding과 정확히 같아야 한다')
        object.__setattr__(self, '_bindings', types.MappingProxyType(dict(bindings)))

    def __getattr__(self, name):
        try: return self._bindings[name]
        except KeyError: raise AttributeError(name) from None

    def __setattr__(self, name, value):
        raise AttributeError('고정한 provider facade는 변경할 수 없다')


def training_provider(native, resume, endpoint):
    if endpoint == 'native': return native
    if endpoint == 'sft': return resume
    raise ValueError('native 또는 sft endpoint를 정확히 지정해야 한다')


def validate_training_header(provider, report, endpoint, arm=None):
    """실물 reader 검산을 대체하지 않는 추가 계보 경계다. 보고서를 정규화하지 않는다."""
    expected_tag = NATIVE_TAG if endpoint == 'native' else SFT_TAG if endpoint == 'sft' else None
    arm = report.get('arm') if arm is None else arm
    if (expected_tag is None or provider.TAG != expected_tag or arm not in ('ternary', 'float')
            or report.get('tag') != provider.TAG or report.get('arm') != arm or report.get('endpoint') != endpoint
            or report.get('status') != 'TRAIN_COMPLETE' or report.get('cost') is not False
            or report.get('updates') != (2281 if endpoint == 'native' else 384)
            or report.get('checkpoint_writes') != 1 or report.get('optimizer_saved') is not False
            or any(report.get(k) != v for k, v in provider.info().items())
            or any(not provider.fingerprint(report.get(k)) for k in
                   ('checkpoint_sha256', 'scratch_core_sha256', 'initial_core_sha256', 'final_core_sha256', 'reference_sha256'))
            or report['scratch_core_sha256'] == provider.PARENT_CORE):
        raise ValueError('endpoint별 원 tag/부모/기한/core의 완료 학습 보고서가 필요하다')
    if endpoint == 'native':
        if (report['initial_core_sha256'] != report['scratch_core_sha256']
                or report.get('parent_core_sha256') is not None or report.get('parent_checkpoint_sha256') is not None):
            raise ValueError('native는 원 scratch 부모 정책을 보존해야 한다')
    elif (not provider.fingerprint(report.get('parent_core_sha256'))
            or not provider.fingerprint(report.get('parent_checkpoint_sha256'))
            or report['initial_core_sha256'] != report['parent_core_sha256']):
        raise ValueError('SFT의 정확한 자기 native 부모 필드가 필요하다')
    return report


def make_facade(native, resume):
    def checkpoint(arm, endpoint):
        if arm not in ('ternary', 'float'): raise ValueError('정확한 훈련 route가 필요하다')
        return training_provider(native, resume, endpoint).checkpoint(arm, endpoint)

    def train_report(mode, arm):
        if mode not in ('train', 'sft'): raise ValueError('완료 학습 report만 읽는다')
        endpoint = 'native' if mode == 'train' else 'sft'
        provider = training_provider(native, resume, endpoint)
        return validate_training_header(provider, provider.train_report(mode, arm), endpoint, arm)

    def cp_experiment(report):
        endpoint = report.get('endpoint')
        provider = training_provider(native, resume, endpoint)
        validate_training_header(provider, report, endpoint)
        return provider.cp_experiment(report)

    values = {name: getattr(native, name) for name in ('TOKENIZER', 'TOKENIZER_SHA', 'PARENT_CORE',
        'modules', 'validate_route_receipt', 'validate_native32', 'native_probe', 'route_receipt',
        'validate_payload', 'validate_cpu_state', 'fingerprint', 'finite', 'termination_guard', 'launch')}
    values.update({name: getattr(resume, name) for name in ('ROOT', 'TAG', 'CODE', 'CACHE', 'RAW',
        'EVIDENCE', 'info', 'prepared', 'phase_key', 'result_path', 'required', 'completed_activity')})
    values.update(checkpoint=checkpoint, train_report=train_report, cp_experiment=cp_experiment)
    return FrozenFacade(values)


def case_bridge(native, resume, reference, cases):
    """이름이 다른 두 binding 키를 원 metadata와 실제 ordered cases에 각각 대조한다."""
    old_path = native.CACHE / 'frozen_reference.json'
    old = native.required(old_path)
    binding = reference.get('binding', {})
    actual = sha(cases)
    if (reference.get('tag') != SFT_TAG or reference.get('status') != 'NATIVE_RESUME_BRIDGE_PREPARED'
            or len(cases) != 1694 or len({c['id'] for c in cases}) != 1694
            or old.get('tag') != NATIVE_TAG or binding.get('original_tag') != NATIVE_TAG
            or old.get('binding', {}).get('source_cases_sha256') != actual
            or binding.get('cases_sha256') != actual
            or binding.get('original_reference_sha256') != native.digest(old_path)
            or binding.get('original_source_binding_sha256') != sha(old['binding'])):
        raise ValueError('원 source_cases_sha256와 새 cases_sha256가 실제 ordered1694와 각각 같아야 한다')
    return dict(original_key='source_cases_sha256', resume_key='cases_sha256',
        original_value=old['binding']['source_cases_sha256'], resume_value=binding['cases_sha256'],
        actual_ordered_cases_sha256=actual, original_reference_sha256=native.digest(old_path),
        resume_reference_sha256=resume.digest(resume.CACHE / 'frozen_reference.json'))


def source_state_for(p, native, resume):
    """원천 선택·점수식 없이 provider/경로/보고서 계보만 연결한다."""
    if not p.info()['code_complete']: raise ValueError('새 코드와 회귀가 완전해야 한다')
    reference, _, cases, _ = resume.prepared()
    key_bridge = case_bridge(native, resume, reference, cases)
    tok = p.tokenizer()
    for case in cases: p.prefix_case(case, tok)
    reports, diagonals, links = {}, {}, {}
    for endpoint in p.ENDPOINTS:
        provider = training_provider(native, resume, endpoint)
        mode = 'train' if endpoint == 'native' else 'sft'
        for trained in p.ROUTES:
            training = validate_training_header(provider, provider.train_report(mode, trained), endpoint, trained)
            training_key = provider.phase_key(mode, trained)
            provider.completed_activity(mode, trained)
            report, events, summary = p.diagonal(trained, endpoint, training, cases, tok)
            diagonal_key = resume.phase_key('evaluate', trained, endpoint)
            slot = p.slot(endpoint, trained)
            reports[slot], diagonals[slot] = training, events
            training_path = provider.result_path(training_key)
            links[slot] = dict(training_tag=provider.TAG, diagonal_tag=resume.TAG,
                checkpoint=str(provider.checkpoint(trained, endpoint).relative_to(p.ROOT)),
                checkpoint_sha256=training['checkpoint_sha256'], core_sha256=training['final_core_sha256'],
                scratch_core_sha256=training['scratch_core_sha256'],
                training_report_path=str(training_path.relative_to(p.ROOT)),
                training_report_sha256=p.digest(training_path),
                training_activity_path=str((provider.EVIDENCE / ('activity_' + training_key + '.json')).relative_to(p.ROOT)),
                training_activity_sha256=p.digest(provider.EVIDENCE / ('activity_' + training_key + '.json')),
                diagonal_report_path=str(resume.result_path(diagonal_key).relative_to(p.ROOT)),
                diagonal_report_sha256=p.digest(resume.result_path(diagonal_key)),
                diagonal_activity_sha256=p.digest(resume.EVIDENCE / ('activity_' + diagonal_key + '.json')),
                diagonal_manifest_path=str((resume.RAW / diagonal_key / 'answers_shards_manifest.json').relative_to(p.ROOT)),
                diagonal_manifest_sha256=p.digest(resume.RAW / diagonal_key / 'answers_shards_manifest.json'),
                diagonal_raw_manifest=report['raw_manifest'], summary=summary, native32_fp32=report['native32_fp32'])
    if len({r['scratch_core_sha256'] for r in reports.values()}) != 1:
        raise ValueError('네 종점의 원 scratch core가 같아야 한다')
    for arm in p.ROUTES:
        parent, child = reports[p.slot('native', arm)], reports[p.slot('sft', arm)]
        if (child['parent_core_sha256'] != parent['final_core_sha256']
                or child['parent_checkpoint_sha256'] != parent['checkpoint_sha256']):
            raise ValueError('새 SFT는 같은 원 native CP에서 시작해야 한다')
    if len([c for c in cases if c['lane'] == 'user_seen']) != p.USER_CASES:
        raise ValueError('기존 사용자6 문항을 모두 유지해야 한다')
    binding = dict(source_reference_sha256=p.digest(resume.CACHE / 'frozen_reference.json'),
        source_cpu_contract_sha256=p.digest(resume.EVIDENCE / 'cpu_contract.json'),
        source_code_sha256=resume.info()['code_sha256'], cases_sha256=p.sha(cases),
        case_key_bridge=key_bridge, native_training_tag=native.TAG, sft_training_tag=resume.TAG,
        diagonal_provider_tag=resume.TAG, endpoints=links)
    return cases, reports, binding, diagonals, tok


def spent_seconds_for(p):
    total = 0.
    if not p.EVIDENCE.exists(): return total
    seen = set()
    for path in sorted(p.EVIDENCE.glob('activity_*.json')):
        path = p.safe(path)
        if path.resolve() in seen: raise ValueError('한 worker 활동은 한 번만 합산한다')
        seen.add(path.resolve())
        value = p.required(path); key = value.get('key')
        if path.name != 'activity_' + str(key) + '.json': raise ValueError('activity 파일명/key가 다르다')
        p.validate_activity(value, key)
        if value['complete']:
            p.completed_activity(value['mode'], value.get('trained_mode'), value.get('inference_mode'), value.get('endpoint'))
        elif (value.get('result_sha256') != (p.digest(p.result_path(key)) if p.exists(p.result_path(key)) else None)
                or value.get('reference_sha256') != (p.digest(p.CACHE / 'frozen_reference.json')
                    if p.exists(p.CACHE / 'frozen_reference.json') else None)):
            raise ValueError('실패 worker의 실제 부분 result/reference SHA가 다르다')
        total += value['seconds']
    return total


def require_family_budget(p, max_wall_sec):
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= p.MAX_WORKER:
        raise ValueError('원60..7200초 worker 상한이 필요하다')
    spent = spent_seconds_for(p)
    if max_wall_sec + p.RECORD_RESERVE > p.FAMILY_LIMIT - spent:
        raise p.Pending('새 교차 family8400의 실제 활동과 기록600초 예비를 함께 보존해야 한다')
    return spent


def checked_sources():
    result = {}
    for relative, expected in SOURCE_PINS.items():
        path = ROOT / relative
        if path.is_symlink() or not path.is_file(): raise ValueError('원 source가 없거나 연결 파일이다')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest().upper() != expected:
            raise ValueError('원 import 전 동결 source SHA가 다르다: ' + relative)
        result[relative] = data
    return result


def _build_runtime(original, native, resume, source_bytes, resume_module=None):
    if hashlib.sha256(source_bytes).hexdigest().upper() != SOURCE_PINS[SOURCE]:
        raise ValueError('private cross 실행 전 정확한 source SHA가 필요하다')
    guarded = [ModuleGuard(m) for m in (original, native, resume)]
    if resume_module is not None: guarded.append(ModuleGuard(resume_module))
    if (original.TAG != ORIGINAL_TAG or native.TAG != NATIVE_TAG or resume.TAG != SFT_TAG
            or original.END.isoformat() != '2026-10-20T08:00:00+00:00'
            or native.END.isoformat() != '2026-10-20T08:00:00+00:00' or resume.END != END
            or original.RECORD_RESERVE != 600 or original.MAX_WORKER != 7200):
        raise ValueError('원 provider의 tag/날짜/기록 예비를 바꿀 수 없다')
    p = types.ModuleType('_p106b_route_cross_resume_' + uuid.uuid4().hex)
    p.__file__ = str(ROOT / SOURCE)
    exec(compile(source_bytes, str(ROOT / SOURCE), 'exec', dont_inherit=True), vars(p))
    pristine = dict(vars(p)); values = _json_values(pristine, BINDING_ALLOWLIST)
    captured = {name: getattr(p, name) for name in CAPTURED_NAMES}
    captured_ids = dict(captured)
    parity = {name: body_sha(getattr(p, name)) for name in BODY_NAMES}
    captured_parity = {name: body_sha(value) for name, value in captured.items()}
    if any(body_sha(getattr(original, name)) != value for name, value in parity.items()):
        raise ValueError('원 cross 계산 본문과 private bytecode가 다르다')
    facade = make_facade(native, resume)
    expected_bindings, audit = {}, {}

    def assert_unchanged():
        for guard in guarded: guard.check()
        resume._resume_assert_unchanged()
        if set(vars(p)) - set(pristine) != AUDIT_ATTRIBUTES | {'spent_seconds', 'FAMILY_LIMIT'}:
            raise ValueError('명시한 private 전역만 추가할 수 있다')
        if any(getattr(p, k) is not v for k, v in pristine.items() if k not in BINDING_ALLOWLIST):
            raise ValueError('private cross allowlist 밖 객체가 바뀌었다')
        if any(canonical(getattr(p, k)) != v for k, v in values.items()):
            raise ValueError('private cross의 중첩 값이 바뀌었다')
        if any(getattr(p, k) is not v for k, v in expected_bindings.items()):
            raise ValueError('허용한 private binding 객체가 바뀌었다')
        for name, expected in parity.items():
            if body_sha(getattr(p, name)) != expected: raise ValueError('계산 본문이 바뀌었다: ' + name)
        for name, expected in captured_parity.items():
            if (captured[name] is not captured_ids[name] or body_sha(captured[name]) != expected
                    or inspect.unwrap(captured[name]).__globals__ is not vars(p)):
                raise ValueError('캡처한 private 본문/참조/globals가 바뀌었다')
        if any(getattr(p, k) is not v for k, v in audit.items()): raise ValueError('감사 참조가 바뀌었다')

    def info():
        for guard in guarded: guard.check()
        resume._resume_assert_unchanged()
        value = canonical(guarded[0].metadata)
        pins = {path: p.digest(ROOT / path) if p.safe(ROOT / path).is_file() else 'NOT_CREATED' for path in p.CODE}
        value.update(schema=p.SCHEMA, tag=p.TAG, source_tag=resume.TAG, code_sha256=pins,
            code_complete='NOT_CREATED' not in pins.values(), authority_end_utc=p.END.isoformat(),
            original_tag=ORIGINAL_TAG, original_info_sha256=sha(guarded[0].metadata),
            original_authority_end_utc=guarded[0].metadata['authority_end_utc'],
            native_training_tag=native.TAG, sft_training_tag=resume.TAG, diagonal_provider_tag=resume.TAG,
            source_tag_role='CASES_AND_DIAGONAL_PROVIDER_NOT_NATIVE_TRAIN_TAG',
            case_key_policy='EXPLICIT_ORIGINAL_source_cases_sha256_EQUALS_RESUME_cases_sha256_EQUALS_ORDERED_CASES',
            provider_info_sha256=dict(native=sha(native.info()), sft_and_diagonal=sha(resume.info())),
            frozen_source_pins=SOURCE_PINS, binding_allowlist=sorted(BINDING_ALLOWLIST),
            facade_binding_allowlist=sorted(FACADE_BINDINGS), computational_body_sha256=parity,
            captured_body_sha256=captured_parity, family_active_limit_seconds=p.FAMILY_LIMIT,
            family_accounting='OWN_ACTUAL_WORKERS_ONCE_NO_NATIVE_SFT_WALL_RECOUNT',
            readonly_scope='source/preflight stdout only; no activity file as original',
            checkpoint_metadata_policy='ORIGINAL_NATIVE_TAG_OR_RESUME_SFT_TAG_NO_RETAG',
            raw_policy='OWN_OFF_DIAGONAL_RAW_AND_EXACT_RESUME_DIAGONAL_RAW',
            f4_sha256=file_sha(F4), training_allowed=False, automatic_adoption=False)
        return canonical(value)

    def authority(now=None):
        now = datetime.now(timezone.utc) if now is None else now
        if now.tzinfo is None: raise ValueError('시간대가 있는 시각이 필요하다')
        remaining = (p.END - now).total_seconds() - p.RECORD_RESERVE
        if remaining <= 0: raise p.Pending('21일17시 전 최종 기록600초 예비에 도달했다')
        return remaining

    def source_state():
        assert_unchanged()
        try: return source_state_for(p, native, resume)
        finally: assert_unchanged()

    def cross_lineage(training, trained, inference, endpoint, cases):
        provider = training_provider(native, resume, endpoint)
        validate_training_header(provider, training, endpoint, trained)
        value = captured['cross_lineage'](training, trained, inference, endpoint, cases)
        value.update(training_tag=provider.TAG, cases_provider_tag=resume.TAG, diagonal_provider_tag=resume.TAG)
        return value

    def spent_seconds():
        return spent_seconds_for(p)

    def worker(mode, trained_mode, inference_mode, endpoint, max_wall_sec):
        assert_unchanged()
        p.phase_key(mode, trained_mode, inference_mode, endpoint)
        if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= p.MAX_WORKER:
            raise ValueError('원60..7200초 worker 상한이 필요하다')
        with facade.termination_guard():
            require_family_budget(p, max_wall_sec)
            try: return captured['worker'](mode, trained_mode, inference_mode, endpoint, max_wall_sec)
            finally: assert_unchanged()

    def phase_commands(mode, trained_mode, inference_mode, endpoint, max_wall_sec):
        phases = captured['phase_commands'](mode, trained_mode, inference_mode, endpoint, max_wall_sec)
        result = []
        for name, old in phases:
            command = [SCRIPT if part == SOURCE else part for part in old]
            if name == 'REGRESSION':
                command.insert(command.index('-v'), TEST[:-3].replace('/', '.'))
            elif command.count(SCRIPT) != 1 or SOURCE in command:
                raise ValueError('모든 child는 새 cross resume driver를 호출해야 한다')
            result.append((name, command))
        return result

    bindings = dict(ROOT=ROOT, TAG=TAG, SCHEMA=SCHEMA, CACHE=ROOT / 'data_cache' / TAG,
        RAW=ROOT / 'runs/eval' / TAG, EVIDENCE=ROOT / 'test_result/evidence' / TAG,
        END=END, FAMILY_LIMIT=FAMILY_LIMIT, n=facade,
        CODE=tuple(sorted(set((*original.CODE, *resume.CODE, SCRIPT, TEST)))),
        OWN_CODE=tuple(dict.fromkeys((*original.OWN_CODE, SCRIPT, TEST))),
        info=info, authority=authority, source_state=source_state, cross_lineage=cross_lineage,
        worker=worker, phase_commands=phase_commands, spent_seconds=spent_seconds)
    if set(bindings) != BINDING_ALLOWLIST: raise ValueError('정확한 private binding allowlist가 필요하다')
    for key, value in bindings.items(): setattr(p, key, value)
    expected_bindings.update(bindings)
    p._resume_assert_unchanged = assert_unchanged
    p._resume_captured, p._resume_original = captured, original
    p._resume_native, p._resume_sft, p._resume_facade = native, resume, facade
    audit.update({name: getattr(p, name) for name in AUDIT_ATTRIBUTES})
    assert_unchanged()
    return p


def build_runtime():
    sources = checked_sources()
    original = importlib.import_module('scripts.diag_p106b_route_cross_readout')
    native = importlib.import_module('scripts.diag_p106b_native_weight_route')
    resume_module = importlib.import_module('scripts.diag_p106b_native_resume')
    resume = resume_module.build_runtime()
    return _build_runtime(original, native, resume, sources[SOURCE], resume_module)


def main(argv=None):
    runtime = None
    try:
        runtime = build_runtime()
        try: return runtime.main(argv)
        finally: runtime._resume_assert_unchanged()
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if (
            isinstance(exc, (FileNotFoundError, FileExistsError)) or runtime is not None and isinstance(exc, runtime.Pending)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[ROUTE_CROSS_RESUME_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
