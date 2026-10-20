#!/usr/bin/env python3
"""고정 공개팩 evaluator를 보존하고 여섯 완료 가중치의 출처만 연결한다.

원 native, 새 SFT, 원 P090B를 유지한 새 Broad를 서로 다른 provider로 읽는다.
공유 recovery scope를 호출하지 않으며 공개팩/Falcon 원형·점수식·분모는 불변이다.
실물 준비/모델/GPU/Git은 root 소유다. check-only는 코드만 읽는다.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import gc
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
SCRIPT = 'scripts/diag_p106b_current_benchmark_resume.py'
TEST = 'scripts/test_p106b_current_benchmark_resume.py'
F4 = ROOT / 'handoff/audit/WIP_20261020_CURRENT_BENCHMARK_RESUME_F4.json'
SOURCE = 'scripts/diag_p106b_current_benchmark.py'
NATIVE, RESUME = 'scripts/diag_p106b_native_weight_route.py', 'scripts/diag_p106b_native_resume.py'
BROAD, UTILITY = 'scripts/diag_p106b_broad_resume.py', 'scripts/diag_p106b_route_cross_resume.py'
SOURCE_PINS = {
    SOURCE: '9D44B42F59987B5980C45C2309615D133D7713E079CFC343F317B643BE9DE73B',
    'scripts/test_p106b_current_benchmark.py': '4F7F2A6578E4E840E287649A9EC0F797B15048AE1A17A17DC1FA04853A842B3D',
    NATIVE: 'E51B68024CA0DC24A4994FFF51C733C05BA2773E3038A2B1CC5C127F6C736FAE',
    RESUME: 'DD4FD5F76192BA35D6FB95A8D7384BC4E23996404686AB6932B0A25CFCB56ECC',
    BROAD: '54D0EA12CFA2E359D9E1D14250CB02B2894AD1B0581568AE9C768B50CDA8F8BF',
    UTILITY: '1229A9033589BB17086747231AE5E6D9544A97BCA52A33FBE90CC4D1C0082C1D',
}
TAG, SCHEMA = 'p106b_current_benchmark_resume_v2_s1337', 'P106B_CURRENT_BENCHMARK_RESUME_V1'
END = datetime(2026, 10, 21, 8, tzinfo=timezone.utc)
NATIVE_TAG, SFT_TAG, BROAD_TAG = ('p106b_native_weight_route_v1_s1337',
    'p106b_native_resume_v2_s1337', 'p106b_broad_resume_v3_s1337')
PARENT_CORE = 'E854AB4EC2E505DDC581CE08C94F9C8B4A8081E456AFBA193DF28A877E34A193'
PARENT_SHA = '12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950'
BINDING_ALLOWLIST = frozenset(('ROOT', 'TAG', 'SCHEMA', 'CACHE', 'RAW', 'EVIDENCE', 'END', 'n',
    'recovery', 'CODE', 'OWN_CODE', 'info', 'authority', 'model_reference', 'model_runtime', 'phase_commands'))
BODY_NAMES = ('safe', 'exists', 'digest', 'raw_bytes', 'required', 'write', 'read_shards', 'phase_key',
    'result_path', 'tokenizer', 'row_id', 'cohort', 'eligibility', 'read_public', 'validate_cached_mc',
    'cached_falcon', 'display_ids', 'source_state', 'prepare', 'prepared', 'validate_broad_payload',
    'mc_encoding', 'emit_public', 'validate_generation', 'score_free', 'event_base', 'validate_event',
    'recount', 'show', 'evaluate', 'read_model', 'readback', 'validate_activity', 'completed_activity',
    'spent_seconds', 'remaining_activity', 'worker', 'launch_phase', 'stage_note', 'main')
CAPTURED_NAMES = ('info', 'model_reference', 'model_runtime', 'phase_commands')
AUDIT_ATTRIBUTES = frozenset(('_resume_assert_unchanged', '_resume_captured', '_resume_original',
    '_resume_native', '_resume_sft', '_resume_broad'))


def canonical(value):
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


@dataclass(frozen=True)
class BroadMetadata:
    # 보존한 strict payload 본문이 요구하는 TAG 하나뿐이다. 공유 runtime_scope는 없다.
    TAG: str = BROAD_TAG


class DependencyGuard:
    """Falcon.info()는 자산을 읽으므로 호출하지 않고 globals/본문만 보존한다."""
    def __init__(self, module, utility):
        self.module, self.utility, self.namespace = module, utility, dict(vars(module))
        self.values = utility._json_values(self.namespace)
        self.bodies = {k: utility.body_sha(v) for k, v in self.namespace.items() if inspect.isfunction(v)}

    def check(self):
        current = vars(self.module)
        if (set(current) != set(self.namespace) or any(current[k] is not v for k, v in self.namespace.items())
                or any(canonical(current[k]) != v for k, v in self.values.items())
                or any(self.utility.body_sha(current[k]) != v for k, v in self.bodies.items())):
            raise ValueError('원 공개팩/scorer/provider의 globals 또는 본문이 바뀌었다')


def validate_spec(p, native, resume, broad, model_id, spec):
    p.phase_key('evaluate', model_id)
    if (spec.get('model_id') != model_id or spec.get('tokenizer_sha256') != p.public.TOKENIZER_SHA
            or any(not native.fingerprint(spec.get(k)) for k in
                ('checkpoint_sha256', 'core_sha256', 'training_report_sha256', 'source_reference_sha256'))):
        raise ValueError('동일 model-id/tokenizer/CP/core/source의 완전한 참조가 필요하다')
    if model_id.startswith('broad_'):
        arm = model_id.removeprefix('broad_')
        if (spec.get('family') != 'broad_v2' or spec.get('endpoint') != 'sft' or spec.get('arm') != arm
                or spec.get('route') != 'PRODUCT_TERNARY' or spec.get('trained_tag') != BROAD_TAG
                or spec.get('parent_core_sha256') != PARENT_CORE or spec.get('parent_checkpoint_sha256') != PARENT_SHA
                or spec.get('updates') != 352 or spec.get('passes') != 2 or spec.get('objective') != 'token'
                or spec.get('checkpoint') != str(broad.checkpoint(arm).relative_to(p.ROOT))
                or spec.get('training_report') != str((broad.EVIDENCE / ('train_' + arm) / 'report.json').relative_to(p.ROOT))):
            raise ValueError('새 Broad는 원 P090B E854/352/token/2pass strict child만 허용한다')
    else:
        endpoint, arm = model_id.split('_')
        provider = native if endpoint == 'native' else resume
        _, _, route = native.modules()
        if (spec.get('family') != 'native_weight_route' or spec.get('endpoint') != endpoint or spec.get('arm') != arm
                or spec.get('trained_tag') != (NATIVE_TAG if endpoint == 'native' else SFT_TAG)
                or spec.get('route') != route.route_metadata(arm)
                or spec.get('checkpoint') != str(provider.checkpoint(arm, endpoint).relative_to(p.ROOT))
                or spec.get('training_report') != str(provider.result_path(provider.phase_key(
                    'train' if endpoint == 'native' else 'sft', arm)).relative_to(p.ROOT))):
            raise ValueError('native/SFT 각각의 원 훈련 route/tag/CP 경로가 필요하다')
    return spec


def model_reference_for(p, native, resume, broad, utility, model_id):
    p.phase_key('evaluate', model_id)
    if not model_id.startswith('broad_'):
        endpoint, arm = model_id.split('_')
        provider = native if endpoint == 'native' else resume
        mode = 'train' if endpoint == 'native' else 'sft'
        report = utility.validate_training_header(provider, provider.train_report(mode, arm), endpoint, arm)
        checkpoint = provider.checkpoint(arm, endpoint)
        path = provider.result_path(provider.phase_key(mode, arm))
        metadata = dict(family='native_weight_route', endpoint=endpoint, arm=arm,
            route=report['quantization_route'], trained_tag=provider.TAG,
            training_report=str(path.relative_to(p.ROOT)), source_reference_sha256=report['reference_sha256'],
            cp_experiment_sha256=p.sha(provider.cp_experiment(report)))
    else:
        arm = model_id.removeprefix('broad_')
        bundle = broad.prepared()
        bridge = broad.required(broad.CACHE / 'frozen.json')
        course = bundle['course'].report
        if (broad.TAG != BROAD_TAG or broad.UPDATES != 352 or course.get('updates') != 352
                or course.get('groups_per_pass') != 176 or bridge.get('status') != 'BROAD_RESUME_BRIDGE_PREPARED'
                or any(bridge.get(k) != v for k, v in broad.info().items())
                or bridge['binding']['parent'] != dict(path=broad.info()['parent'], sha256=PARENT_SHA, core_sha256=PARENT_CORE)):
            raise ValueError('완전한 새 Broad bridge/원 P090B/352회 실제 course가 필요하다')
        borrowed = bridge['binding']['files']['course']
        if (p.digest(p.ROOT / borrowed['path']) != borrowed['sha256']
                or borrowed['sha256'] != bundle['contract']['course_report_sha256']):
            raise ValueError('실제 prepared bundle과 원 borrowed course SHA가 다르다')
        broad.completed_activity('train', arm)
        report = broad.read_training(arm, cost=False, bundle=bundle)
        if (report.get('initial_core_sha256') != PARENT_CORE or report.get('actual_updates') != 352
                or any(report.get(k) != v for k, v in broad.info().items())):
            raise ValueError('새 Broad의 완전한 원 부모/학습 report가 필요하다')
        checkpoint = broad.checkpoint(arm)
        if p.digest(broad.monitor.base.PARENT) != PARENT_SHA:
            raise ValueError('원 Broad P090B 부모 바이트가 바뀌었다')
        path = broad.EVIDENCE / ('train_' + arm) / 'report.json'
        metadata = dict(family='broad_v2', endpoint='sft', arm=arm, route='PRODUCT_TERNARY',
            trained_tag=broad.TAG, parent_checkpoint_sha256=PARENT_SHA, parent_core_sha256=PARENT_CORE,
            training_report=str(path.relative_to(p.ROOT)), source_reference_sha256=p.digest(broad.CACHE / 'frozen.json'),
            course_report_path=borrowed['path'], course_report_sha256=borrowed['sha256'],
            updates=352, passes=2, objective='token',
            family_role='PRESERVED_PRODUCT_LOADER_CONTRACT_NOT_OLD_V2_CHECKPOINT')
    if p.digest(checkpoint) != report['checkpoint_sha256']:
        raise ValueError('정확한 완료 CP 바이트가 다르다')
    spec = dict(metadata, model_id=model_id, checkpoint=str(checkpoint.relative_to(p.ROOT)),
        checkpoint_sha256=report['checkpoint_sha256'], core_sha256=report['final_core_sha256'],
        training_report_sha256=p.digest(path), tokenizer_sha256=p.public.TOKENIZER_SHA)
    return validate_spec(p, native, resume, broad, model_id, spec)


@contextmanager
def load_model_for(p, native, resume, broad, model_id, spec):
    """검산한 참조만 받는 로더 경계. evaluator의 수치 계산은 이 밖에 있다."""
    from scripts.diag_p101a_sft_mtp import state_fingerprint
    validate_spec(p, native, resume, broad, model_id, spec)
    if p.digest(p.ROOT / spec['checkpoint']) != spec['checkpoint_sha256']:
        raise ValueError('모델 로드 직전 CP SHA가 다르다')
    p.authority()
    if spec['family'] == 'native_weight_route':
        provider = native if spec['endpoint'] == 'native' else resume
        with provider.routed_runtime(spec['arm'], spec['endpoint']) as (torch, model, cfg, tok, _, route):
            model.eval(); model.set_anneal(1.); model.freeze_quant(); route.assert_active()
            if state_fingerprint(model) != spec['core_sha256']: raise ValueError('정식 trained route 본체가 다르다')
            yield torch, model, cfg, tok, route
    else:
        torch, model, cfg, tok, initial = broad.monitor.base.load_parent()
        try:
            if initial != PARENT_CORE: raise ValueError('정확한 원 P090B 부모가 필요하다')
            saved = torch.load(p.safe(p.ROOT / spec['checkpoint']), map_location='cpu', weights_only=True)
            p.validate_broad_payload(saved, model, cfg, spec['arm'], torch)
            del saved
            if state_fingerprint(model) != spec['core_sha256']: raise ValueError('strict Broad 본체가 다르다')
            model = model.cuda(); model.eval(); model.freeze_quant()
            torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
            yield torch, model, cfg, tok, None
        finally:
            model.clear_quant()
            del model
            gc.collect()
            torch.cuda.empty_cache()


def checked_sources():
    result = {}
    for relative, expected in SOURCE_PINS.items():
        path = ROOT / relative
        if path.is_symlink() or not path.is_file(): raise ValueError('정확한 동결 source가 필요하다')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest().upper() != expected:
            raise ValueError('원 import 전 source SHA가 다르다: ' + relative)
        result[relative] = data
    return result


def _build_runtime(original, native, resume, broad, utility, source_bytes, modules=()):
    if hashlib.sha256(source_bytes).hexdigest().upper() != SOURCE_PINS[SOURCE]:
        raise ValueError('private evaluator 실행 전 source SHA가 다르다')
    guards = [utility.ModuleGuard(m) for m in (original, native, resume, broad)]
    dependencies = [DependencyGuard(m, utility) for m in (*modules, original.public, original.falcon,
        original.audit, original.suite, original.recovery, original.recovery.legacy)]
    if (native.TAG != NATIVE_TAG or resume.TAG != SFT_TAG or broad.TAG != BROAD_TAG
            or original.END.isoformat() != '2026-10-20T08:00:00+00:00'
            or (original.ACTIVE_LIMIT, original.RECORD_RESERVE) != (3600, 600)):
        raise ValueError('정확한 원 provider/날짜/3600·600 경계가 필요하다')
    p = types.ModuleType('_p106b_benchmark_resume_' + uuid.uuid4().hex)
    p.__file__ = str(ROOT / SOURCE)
    exec(compile(source_bytes, str(ROOT / SOURCE), 'exec', dont_inherit=True), vars(p))
    pristine = dict(vars(p)); values = utility._json_values(pristine, BINDING_ALLOWLIST)
    fixed = {str(k): v for k, v in p.FIXED.items()}
    captured = {name: getattr(p, name) for name in CAPTURED_NAMES}; captured_ids = dict(captured)
    parity = {name: utility.body_sha(getattr(p, name)) for name in BODY_NAMES}
    captured_parity = {name: utility.body_sha(value) for name, value in captured.items()}
    class_parity = {name: utility.body_sha(getattr(p.FP32Forward, name)) for name in ('__init__', '__getattr__', '__call__')}
    if any(utility.body_sha(getattr(original, k)) != v for k, v in parity.items()):
        raise ValueError('원 evaluator/scorer와 private bytecode가 다르다')
    admitted, expected_bindings, audit_bindings = {}, {}, {}

    def assert_unchanged():
        for guard in (*guards, *dependencies): guard.check()
        resume._resume_assert_unchanged(); broad._resume_assert_unchanged()
        if set(vars(p)) - set(pristine) != AUDIT_ATTRIBUTES: raise ValueError('명시한 감사 전역만 추가한다')
        if (any(getattr(p, k) is not v for k, v in pristine.items() if k not in BINDING_ALLOWLIST)
                or any(canonical(getattr(p, k)) != v for k, v in values.items())
                or any(getattr(p, k) is not v for k, v in expected_bindings.items())
                or any(getattr(p, k) is not v for k, v in audit_bindings.items())):
            raise ValueError('private evaluator의 allowlist/참조/중첩 값이 바뀌었다')
        if {str(k): v for k, v in p.FIXED.items()} != fixed or {str(k): v for k, v in original.FIXED.items()} != fixed:
            raise ValueError('고정 공개팩/Falcon SHA를 바꿀 수 없다')
        for name, value in parity.items():
            if utility.body_sha(getattr(p, name)) != value: raise ValueError('계산 본문이 바뀌었다: ' + name)
        for name, value in class_parity.items():
            if utility.body_sha(getattr(p.FP32Forward, name)) != value: raise ValueError('FP32 wrapper 본문이 바뀌었다')
        for name, value in captured_parity.items():
            if (captured[name] is not captured_ids[name] or utility.body_sha(captured[name]) != value
                    or inspect.unwrap(captured[name]).__globals__ is not vars(p)):
                raise ValueError('캡처한 private 본문/참조/globals가 바뀌었다')

    def info():
        for guard in (*guards, *dependencies): guard.check()
        value = canonical(guards[0].metadata)
        pins = {path: p.digest(ROOT / path) if p.exists(ROOT / path) else 'NOT_CREATED' for path in p.CODE}
        value.update(schema=p.SCHEMA, tag=p.TAG, code_sha256=pins, code_complete='NOT_CREATED' not in pins.values(),
            authority_end_utc=p.END.isoformat(), original_info_sha256=sha(guards[0].metadata),
            original_authority_end_utc=guards[0].metadata['authority_end_utc'], frozen_source_pins=SOURCE_PINS,
            binding_allowlist=sorted(BINDING_ALLOWLIST), computational_body_sha256=parity,
            captured_body_sha256=captured_parity, fp32_wrapper_body_sha256=class_parity,
            native_training_tag=NATIVE_TAG, sft_training_tag=SFT_TAG, broad_training_tag=BROAD_TAG,
            broad_parent_core_sha256=PARENT_CORE, broad_parent_checkpoint_sha256=PARENT_SHA,
            broad_course_policy='ACTUAL_PREPARED_BUNDLE_AND_BRIDGE_BORROWED_COURSE_NOT_OWN_CACHE_COURSE',
            broad_v2_label_scope='NUMERICAL_READER_COMPATIBILITY_NOT_OLD_V2_CHECKPOINT',
            admitted_reference_policy='PROCESS_LOCAL_EXACT_STRICT_MODEL_REFERENCE_REQUIRED_BEFORE_LOAD',
            gsm_scope='64_ORIGINAL_PROBLEMS_TWO_FORMATS_NOT128_INDEPENDENT',
            activity_accounting='ORIGINAL_AUX_WORKER_SHA_LINK_DEDUP_UNCHANGED_OWN_NAMESPACE_ONLY',
            f4_sha256=utility.file_sha(F4), automatic_adoption=False)
        return canonical(value)

    def authority(now=None):
        now = datetime.now(timezone.utc) if now is None else now
        if now.tzinfo is None: raise ValueError('시간대 있는 시각이 필요하다')
        remaining = (p.END - now).total_seconds() - p.RECORD_RESERVE
        if remaining <= 0: raise p.Pending('21일17시 전 기록600초 예비에 도달했다')
        return remaining

    def model_reference(model_id):
        assert_unchanged()
        value = model_reference_for(p, native, resume, broad, utility, model_id)
        admitted[model_id] = canonical(value)
        assert_unchanged()
        return value

    @contextmanager
    def model_runtime(model_id, reference):
        assert_unchanged()
        validate_spec(p, native, resume, broad, model_id, reference)
        if admitted.get(model_id) != canonical(reference):
            raise ValueError('실제 strict model_reference를 먼저 검산한 동일 참조만 로드한다')
        try:
            with load_model_for(p, native, resume, broad, model_id, reference) as value:
                yield value
        finally: assert_unchanged()

    def phase_commands(mode, model_id, max_wall_sec):
        phases = captured['phase_commands'](mode, model_id, max_wall_sec)
        result = []
        for label, old in phases:
            command = [SCRIPT if part == SOURCE else part for part in old]
            if label == 'REGRESSION': command.insert(command.index('-v'), TEST[:-3].replace('/', '.'))
            elif command.count(SCRIPT) != 1 or SOURCE in command:
                raise ValueError('모든 child는 새 benchmark resume driver만 호출한다')
            result.append((label, command))
        return result

    bindings = dict(ROOT=ROOT, TAG=TAG, SCHEMA=SCHEMA, CACHE=ROOT / 'data_cache' / TAG,
        RAW=ROOT / 'runs/eval' / TAG, EVIDENCE=ROOT / 'test_result/evidence' / TAG, END=END,
        n=resume, recovery=BroadMetadata(), CODE=tuple(sorted(set((*original.CODE, *resume.CODE,
            *broad.CODE, UTILITY, SCRIPT, TEST)))), OWN_CODE=(SCRIPT, TEST), info=info, authority=authority,
        model_reference=model_reference, model_runtime=model_runtime, phase_commands=phase_commands)
    if set(bindings) != BINDING_ALLOWLIST: raise ValueError('명시한 binding allowlist와 같아야 한다')
    for name, value in bindings.items(): setattr(p, name, value)
    expected_bindings.update(bindings)
    p._resume_assert_unchanged, p._resume_captured, p._resume_original = assert_unchanged, captured, original
    p._resume_native, p._resume_sft, p._resume_broad = native, resume, broad
    audit_bindings.update({name: getattr(p, name) for name in AUDIT_ATTRIBUTES})
    assert_unchanged()
    return p


def build_runtime():
    sources = checked_sources()
    utility = importlib.import_module('scripts.diag_p106b_route_cross_resume')
    broad_module = importlib.import_module('scripts.diag_p106b_broad_resume')
    broad_module.checked_sources()  # 원 legacy/recovery도 original evaluator import 전 고정한다.
    native_module = importlib.import_module('scripts.diag_p106b_native_resume')
    native = importlib.import_module('scripts.diag_p106b_native_weight_route')
    resume, broad = native_module.build_runtime(), broad_module.build_runtime()
    original = importlib.import_module('scripts.diag_p106b_current_benchmark')
    return _build_runtime(original, native, resume, broad, utility, sources[SOURCE],
        (utility, broad_module, native_module))


def main(argv=None):
    runtime = None
    try:
        runtime = build_runtime()
        try: return runtime.main(argv)
        finally: runtime._resume_assert_unchanged()
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if (isinstance(exc, (FileNotFoundError, FileExistsError))
            or runtime is not None and isinstance(exc, runtime.Pending)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[CURRENT_BENCHMARK_RESUME_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
