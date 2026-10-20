#!/usr/bin/env python3
"""동일 공개팩과 원 evaluator를 여섯 완료 weight-route provider에만 연결한다.

Native595 두 개는 영어 MC768, 두 Broad 계열의 네 개는 원1920 요청을 소비한다.
원문·모델·CP·GPU 준비는 root 소유이며 check-only는 코드/F4만 읽는다.
원 evaluator/global/report를 수정하거나 아직 없는 CP 해시를 추측하지 않는다.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
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
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
SCRIPT, TEST = 'scripts/diag_p106b_native595_public.py', 'scripts/test_p106b_native595_public.py'
F4 = ROOT / 'handoff/audit/WIP_20261021_NATIVE595_PUBLIC_F4.json'
SOURCE, PATTERN = 'scripts/diag_p106b_current_benchmark.py', 'scripts/diag_p106b_current_benchmark_resume.py'
NATIVE, OLDBROAD, NEWBROAD = ('scripts/diag_p106b_native595.py',
    'scripts/diag_p106b_native_broad4_recovery.py', 'scripts/diag_p106b_native595_broad.py')
UTILITY = 'scripts/diag_p106b_route_cross_resume.py'
F4_PINS = {
    SOURCE: '9D44B42F59987B5980C45C2309615D133D7713E079CFC343F317B643BE9DE73B',
    'scripts/test_p106b_current_benchmark.py': '4F7F2A6578E4E840E287649A9EC0F797B15048AE1A17A17DC1FA04853A842B3D',
    PATTERN: 'B75BA699B427EF703B60E5AA306F12C4666FDC9E6D1355290A4E6B8883558BD9',
    NATIVE: '0995C650D5FF0CEDC841F0C5C3CAC8BC55E78A63E8A0FB6C6B1BCBBBBF8BF7B3',
    'scripts/test_p106b_native595.py': '2D21EF2E0CB5E830F57B7A454DBC749826444BC7B86A48269F1923B5C3AB4F8A',
    OLDBROAD: '2292EDFFEBCCF3DA46EB97773EAB3FD68FE4AE6BA0DE3961A3431EA610B9F74C',
    'scripts/test_p106b_native_broad4_recovery.py': 'B4A535FACC42BFD89630C8B4C2FC13D99CE7DD6A5A70B45B1916FE2D55A76151',
    NEWBROAD: '8155767CB3D56E551A224C27F11F42F194E5D663B25847009F92DB8B930A80BB',
    'scripts/test_p106b_native595_broad.py': '951C57ED222C5358FEF8B31CBF60562CA012EF8D01D21D675339444808485925'}
SOURCE_PINS = dict(F4_PINS, **{
    UTILITY: '1229A9033589BB17086747231AE5E6D9544A97BCA52A33FBE90CC4D1C0082C1D',
    'scripts/diag_p106b_native_weight_route.py': 'E51B68024CA0DC24A4994FFF51C733C05BA2773E3038A2B1CC5C127F6C736FAE'})
TAG, SCHEMA = 'p106b_native595_public_v1_s1337', 'P106B_NATIVE595_PUBLIC_V1'
END = datetime(2026, 10, 21, 8, tzinfo=timezone.utc)
WORKER_LIMIT = 1800
PROVIDER_TAGS = dict(native595='p106b_native595_v1_s1337',
    oldbroad='p106b_native_broad4_recovery_v2_s1337', newbroad='p106b_native595_broad_v1_s1337')
MODELS = ('native595_ternary', 'native595_float', 'oldbroad_ternary', 'oldbroad_float', 'newbroad_ternary', 'newbroad_float')
STUDENTS = MODELS[2:]
MODEL_TABLE = tuple(dict(model_id=name, provider=PROVIDER_TAGS[role], arm=arm,
    cohort='ENGLISH_MC768' if role == 'native595' else 'FULL_PUBLIC1919_scored_requested1920')
    for name, role, arm in zip(MODELS, ('native595', 'native595', 'oldbroad', 'oldbroad', 'newbroad', 'newbroad'),
        ('ternary', 'float', 'ternary', 'float', 'ternary', 'float')))
BINDING_ALLOWLIST = frozenset(('ROOT', 'TAG', 'SCHEMA', 'CACHE', 'RAW', 'EVIDENCE', 'END', 'MODELS', 'STUDENTS',
    'recovery', 'CODE', 'OWN_CODE', 'info', 'authority', 'model_reference', 'model_runtime', 'phase_commands', 'worker', 'validate_activity'))
BODY_NAMES = ('safe', 'exists', 'digest', 'raw_bytes', 'required', 'write', 'read_shards', 'phase_key',
    'result_path', 'tokenizer', 'row_id', 'cohort', 'eligibility', 'read_public', 'validate_cached_mc',
    'cached_falcon', 'display_ids', 'source_state', 'prepare', 'prepared', 'validate_broad_payload',
    'mc_encoding', 'emit_public', 'validate_generation', 'score_free', 'event_base', 'validate_event',
    'recount', 'show', 'evaluate', 'read_model', 'readback', 'completed_activity',
    'spent_seconds', 'remaining_activity', 'launch_phase', 'stage_note', 'main')
CAPTURED_NAMES = ('info', 'model_reference', 'model_runtime', 'phase_commands', 'worker', 'validate_activity')
AUDIT_ATTRIBUTES = frozenset(('_public_assert_unchanged', '_public_captured', '_public_original', '_public_providers'))


def canonical(value): return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


@dataclass(frozen=True)
class Provider:
    role: str
    module: object
    runtime: object


@dataclass(frozen=True)
class UnusedProductBroad:
    # 원 product Broad validator 본문만 보존한다. 실제 여섯 로더는 모두 trained-route provider다.
    TAG: str = 'NO_PRODUCT_BROAD_IN_THIS_FAMILY'


def checked_sources():
    values = {}
    for name, expected in SOURCE_PINS.items():
        path = ROOT / name
        for parent in (path, *path.parents):
            if parent.is_symlink(): raise ValueError('source symlink 조상은 import 전에 거부한다')
            if parent == ROOT: break
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest().upper() != expected: raise ValueError('import 전 동결 source SHA가 다르다: ' + name)
        values[name] = data
    return values


def validate_f4(p, providers):
    value = p.required(F4)
    if (value.get('schema') != 'P106B_NATIVE595_PUBLIC_F4_V1' or value.get('tag') != TAG
            or value.get('allowed_agent_new_sources') != [SCRIPT, TEST] or value.get('source_pins') != F4_PINS
            or value.get('models') != list(MODEL_TABLE)
            or value.get('counts') != dict(requested=9216, scored=9212, native_each=768,
                student_requested_each=1920, student_scored_each=1919, length_excluded_total=4)
            or value.get('limits') != dict(active_seconds=3600, record_reserve_seconds=600,
                max_worker_seconds=1800, authority_end_utc=END.isoformat())
            or value.get('evaluation') != dict(precision='FP32_MATH', tf32=False, kv=True, mtp=False,
                greedy=True, context=1024, max_new_tokens=128, mc_primary='SUM_NLL',
                mc_secondary='CHAR_NORMALIZED_DIAGNOSTIC', pmi=False,
                gsm='same64problems/twoformats,not128independent',
                cached_falcon='398/768 prior score/raw reused only; no freshFalcon/download/API')
            or set(providers) != set(PROVIDER_TAGS)
            or any(owner.role != role or owner.module.TAG != PROVIDER_TAGS[role]
                or owner.runtime.info().get('tag') != PROVIDER_TAGS[role] for role, owner in providers.items())):
        raise ValueError('정확한 여섯 provider/코호트/원분모/자원 F4가 필요하다')


def owner_for(p, providers, model_id):
    p.phase_key('evaluate', model_id)
    for cell in MODEL_TABLE:
        if cell['model_id'] == model_id:
            role = next(role for role, tag in PROVIDER_TAGS.items() if tag == cell['provider'])
            return providers[role], cell['arm']
    raise ValueError('정확한 여섯 model-id만 허용한다')


def validate_report(p, owner, arm, report):
    meta = owner.runtime.info(); native = owner.role == 'native595'
    if (any(report.get(k) != v for k, v in meta.items()) or report.get('tag') != PROVIDER_TAGS[owner.role]
            or report.get('status') != 'TRAIN_COMPLETE' or report.get('arm') != arm or report.get('cost') is not False
            or report.get('updates') != (4543 if native else 704) or report.get('checkpoint_writes') != 1
            or report.get('optimizer_saved') is not False
            or any(not p.n.fingerprint(report.get(k)) for k in ('checkpoint_sha256', 'final_core_sha256', 'initial_core_sha256'))
            or report.get('quantization_route') != p.n.modules()[2].route_metadata(arm)):
        raise ValueError('같은 source/tag/arm의 닫힌 실제4543 또는704 훈련이 필요하다')
    if native:
        if (meta.get('native_recipe', {}).get('pool_train_ids') != 1191116192
                or report.get('totals') != dict(targets=595460096, x_tokens=595460096)
                or report.get('initial_core_sha256') != owner.module.RECIPE.scratch_core_sha256
                or report.get('parent_checkpoint_sha256') is not None or report.get('parent_core_sha256') is not None):
            raise ValueError('비용8/구299M/자식CP를 native595로 바꾸어 부를 수 없다')
    elif (report.get('endpoint') != 'native_broad4' or report.get('passes') != 4
            or report.get('objective') != 'L0_TOKEN_MEAN_OVER_WHOLE_UPDATE'
            or report.get('totals') != owner.module.EXPECTED
            or report.get('initial_core_sha256') != report.get('parent_core_sha256')):
        raise ValueError('원22528/704/4pass/L0의 실제 부모에서 학습한 Broad가 필요하다')


def validate_spec(p, providers, model_id, spec):
    owner, arm = owner_for(p, providers, model_id); native = owner.role == 'native595'
    reference_path = owner.runtime.CACHE / ('reference.json' if native else 'frozen_reference.json')
    expected = dict(model_id=model_id, family='native_weight_route', provider_role=owner.role,
        trained_tag=PROVIDER_TAGS[owner.role], endpoint='native595' if native else 'native_broad4', arm=arm,
        route=p.n.modules()[2].route_metadata(arm), updates=4543 if native else 704, passes=None if native else 4,
        objective='NTP_FULL_UPDATE' if native else 'L0_TOKEN_MEAN_OVER_WHOLE_UPDATE',
        checkpoint=str(owner.runtime.checkpoint(arm).relative_to(p.ROOT)),
        training_report=str(owner.runtime.path('train', arm).relative_to(p.ROOT)),
        training_activity=str((owner.runtime.EVIDENCE / ('activity_train_' + arm + '.json')).relative_to(p.ROOT)),
        source_reference=str(reference_path.relative_to(p.ROOT)), tokenizer_sha256=p.public.TOKENIZER_SHA,
        provider_info_sha256=sha(owner.runtime.info()))
    digests = ('checkpoint_sha256', 'core_sha256', 'training_report_sha256', 'training_activity_sha256',
        'source_reference_sha256', 'cp_experiment_sha256', 'initial_core_sha256', 'scratch_core_sha256')
    parent_fields = ('parent_checkpoint_sha256', 'parent_core_sha256', 'parent_report_sha256')
    if (set(spec) != set(expected) | set(digests) | set(parent_fields)
            or any(spec.get(k) != v for k, v in expected.items())
            or any(not p.n.fingerprint(spec.get(k)) for k in digests)
            or native and any(spec.get(k) is not None for k in parent_fields)
            or native and (spec.get('initial_core_sha256') != owner.module.RECIPE.scratch_core_sha256
                or spec.get('scratch_core_sha256') != owner.module.RECIPE.scratch_core_sha256)
            or not native and any(not p.n.fingerprint(spec.get(k)) for k in parent_fields)
            or not native and spec.get('initial_core_sha256') != spec.get('parent_core_sha256')):
        raise ValueError('완전한 현재 model-id/실제 provider/tag/route/CP/source 참조가 필요하다')
    if owner.role == 'oldbroad':
        parent = owner.module.PARENTS[arm]
        if spec['parent_checkpoint_sha256'] != parent['sha256'] or spec['parent_core_sha256'] != parent['core']:
            raise ValueError('oldbroad의 원299M 부모를 바꿀 수 없다')
    return spec


def model_reference_for(p, providers, model_id):
    owner, arm = owner_for(p, providers, model_id); module, runtime = owner.module, owner.runtime
    activity_path = runtime.EVIDENCE / ('activity_train_' + arm + '.json')
    upstream_activity = p.required(activity_path)
    module.validate_activity(runtime, upstream_activity, 'train', arm)
    if upstream_activity['complete'] is not True or upstream_activity['returncode'] != 0:
        raise p.Pending('유효한 원 upstream 실패/미완료를 공개평가 실행으로 승격하지 않는다: ' + model_id)
    state = module.prepared(runtime)
    report = module.read_training(runtime, arm, cost=False, state=state)
    validate_report(p, owner, arm, report); closed = runtime.completed('train', arm)
    if owner.role != 'native595':
        parent = state[1]['binding']['parents'][arm]
        if owner.role == 'newbroad': module.validate_parent_descriptor(parent, arm)
        expected_parent_tag = 'p106b_native595_v1_s1337' if owner.role == 'newbroad' else 'p106b_native_weight_route_v1_s1337'
        if (parent.get('original_tag') != expected_parent_tag
                or parent.get('original_training_updates') != (4543 if owner.role == 'newbroad' else 2281)
                or report.get('parent_checkpoint_sha256') != parent.get('checkpoint_sha256')
                or report.get('parent_core_sha256') != parent.get('core_sha256')
                or report.get('parent_report_sha256') != parent.get('report_sha256')):
            raise ValueError('Broad 자식과 실제 직접 부모 descriptor의 출처가 다르다')
    checkpoint, path = runtime.checkpoint(arm), runtime.path('train', arm)
    native = owner.role == 'native595'; source = runtime.CACHE / ('reference.json' if native else 'frozen_reference.json')
    if (closed.get('complete') is not True or closed.get('returncode') != 0
            or closed.get('result_sha256') != p.digest(path) or closed.get('reference_sha256') != p.digest(source)
            or closed.get('tag') != PROVIDER_TAGS[owner.role]
            or closed.get('code_sha256') != runtime.info()['code_sha256']
            or p.digest(checkpoint) != report['checkpoint_sha256'] or report.get('reference_sha256') != p.digest(source)):
        raise ValueError('원 보고/원 완료activity/CP/source SHA를 그대로 보존해야 한다')
    spec = dict(model_id=model_id, family='native_weight_route', provider_role=owner.role,
        trained_tag=module.TAG, endpoint='native595' if native else 'native_broad4', arm=arm,
        route=report['quantization_route'], updates=report['updates'], passes=None if native else report['passes'],
        objective='NTP_FULL_UPDATE' if native else report['objective'], checkpoint=str(checkpoint.relative_to(p.ROOT)),
        checkpoint_sha256=report['checkpoint_sha256'], core_sha256=report['final_core_sha256'],
        training_report=str(path.relative_to(p.ROOT)), training_report_sha256=p.digest(path),
        training_activity=str((runtime.EVIDENCE / ('activity_train_' + arm + '.json')).relative_to(p.ROOT)),
        training_activity_sha256=p.digest(activity_path),
        source_reference=str(source.relative_to(p.ROOT)), source_reference_sha256=p.digest(source),
        tokenizer_sha256=p.public.TOKENIZER_SHA, provider_info_sha256=sha(runtime.info()),
        cp_experiment_sha256=sha(module.cp_experiment(report)), initial_core_sha256=report['initial_core_sha256'],
        scratch_core_sha256=report['initial_core_sha256'] if native else report['scratch_core_sha256'],
        parent_checkpoint_sha256=report.get('parent_checkpoint_sha256'), parent_core_sha256=report.get('parent_core_sha256'),
        parent_report_sha256=None if native else report['parent_report_sha256'])
    return validate_spec(p, providers, model_id, spec)


@contextmanager
def load_model_for(p, providers, model_id, spec):
    validate_spec(p, providers, model_id, spec); owner, arm = owner_for(p, providers, model_id)
    p.authority()
    if model_reference_for(p, providers, model_id) != spec: raise ValueError('모델 로드 직전 원 완료 참조가 달라졌다')
    report = owner.module.read_training(owner.runtime, arm, cost=False); p.authority()
    if p.digest(owner.runtime.path('train', arm)) != spec['training_report_sha256']: raise ValueError('원 보고 SHA가 달라졌다')
    if owner.role == 'native595':
        context = owner.module.loaded_runtime(owner.runtime, arm, report)
    else: context = owner.module.child_runtime(owner.runtime, arm, report)
    with context as values:
        if owner.role == 'native595':
            torch, model, route = values; cfg, tok = model.cfg, p.tokenizer()
        else: torch, model, cfg, tok, route = values
        p.authority(); route.assert_active()
        if route.mode != arm or route.metadata != spec['route']: raise ValueError('실제 훈련 route가 다르다')
        model.clear_quant(); model.eval(); model.set_anneal(1.)
        with torch.no_grad(): model.freeze_quant()
        if (p.n.modules()[0].state_fingerprint(model) != spec['core_sha256']
                or cfg.max_seq_len != 1024 or cfg.mtp_aux): raise ValueError('엄격 본체/cfg/문맥/MTPoff가 다르다')
        try: yield torch, model, cfg, tok, route
        finally: model.clear_quant()


def _build_runtime(original, providers, utility, pattern, source_bytes, modules=()):
    if hashlib.sha256(source_bytes).hexdigest().upper() != SOURCE_PINS[SOURCE]: raise ValueError('private source SHA가 다르다')
    guards = [utility.ModuleGuard(m) for m in (original, *(o.module for o in providers.values()))]
    dependencies = [pattern.DependencyGuard(m, utility) for m in (*modules, original.public,
        original.falcon, original.audit, original.suite, original.recovery, original.recovery.legacy)]
    if original.END.isoformat() != '2026-10-20T08:00:00+00:00' or (original.ACTIVE_LIMIT, original.RECORD_RESERVE) != (3600, 600):
        raise ValueError('원 날짜/3600·600 경계를 보존해야 한다')
    p = types.ModuleType('_p106b_native595_public_' + uuid.uuid4().hex); p.__file__ = str(ROOT / SOURCE)
    exec(compile(source_bytes, str(ROOT / SOURCE), 'exec', dont_inherit=True), vars(p))
    pristine = dict(vars(p)); values = utility._json_values(pristine, BINDING_ALLOWLIST)
    fixed = canonical({str(k): v for k, v in p.FIXED.items()})
    captured = {name: getattr(p, name) for name in CAPTURED_NAMES}; captured_ids = dict(captured)
    parity = {name: utility.body_sha(getattr(p, name)) for name in BODY_NAMES}
    captured_parity = {name: utility.body_sha(value) for name, value in captured.items()}
    class_parity = {name: utility.body_sha(getattr(p.FP32Forward, name)) for name in ('__init__', '__getattr__', '__call__')}
    if any(utility.body_sha(getattr(original, k)) != v for k, v in parity.items()): raise ValueError('private evaluator 수치 본문이 다르다')
    validate_f4(p, providers)
    admitted, expected_bindings, audit_bindings = {}, {}, {}

    def configuration():
        return canonical(dict(models=MODELS, students=STUDENTS, model_table=MODEL_TABLE, tags=PROVIDER_TAGS,
            source_pins=SOURCE_PINS, f4_pins=F4_PINS, worker_limit=WORKER_LIMIT, end=END.isoformat(),
            bindings=sorted(BINDING_ALLOWLIST), bodies=BODY_NAMES, captured=CAPTURED_NAMES))

    config_snapshot = configuration()

    def check_sources_and_configuration():
        if configuration() != config_snapshot: raise ValueError('새 adapter의 모델/provider/기한/상한 선언이 바뀌었다')
        for name, pin in config_snapshot['source_pins'].items():
            if p.digest(ROOT / name) != pin: raise ValueError('동결 source가 import 뒤 바뀌었다: ' + name)

    def assert_unchanged():
        check_sources_and_configuration()
        for guard in (*guards, *dependencies): guard.check()
        for owner in providers.values(): owner.runtime.check()
        if set(vars(p)) - set(pristine) != AUDIT_ATTRIBUTES: raise ValueError('명시한 감사 속성 외에는 전역을 추가하지 않는다')
        if (any(getattr(p, k) is not v for k, v in pristine.items() if k not in BINDING_ALLOWLIST)
                or any(canonical(getattr(p, k)) != v for k, v in values.items())
                or any(getattr(p, k) is not v for k, v in expected_bindings.items())
                or any(getattr(p, k) is not v for k, v in audit_bindings.items())):
            raise ValueError('private allowlist/참조/중첩 값이 달라졌다')
        if canonical({str(k): v for k, v in p.FIXED.items()}) != fixed or canonical({str(k): v for k, v in original.FIXED.items()}) != fixed:
            raise ValueError('원 공개팩/Falcon SHA는 바꿀 수 없다')
        for name, body in parity.items():
            if utility.body_sha(getattr(p, name)) != body: raise ValueError('원 수치 본문 변경: ' + name)
        for name, body in class_parity.items():
            if utility.body_sha(getattr(p.FP32Forward, name)) != body: raise ValueError('원 FP32 wrapper 본문이 바뀌었다')
        for name, body in captured_parity.items():
            if (captured[name] is not captured_ids[name] or utility.body_sha(captured[name]) != body
                    or inspect.unwrap(captured[name]).__globals__ is not vars(p)):
                raise ValueError('캡처한 원 본문/참조/globals가 바뀌었다')

    def info():
        check_sources_and_configuration()
        for guard in (*guards, *dependencies): guard.check()
        value = canonical(guards[0].metadata)
        pins = {path: p.digest(ROOT / path) if p.exists(ROOT / path) else 'NOT_CREATED' for path in p.CODE}
        value.update(schema=p.SCHEMA, tag=p.TAG, code_sha256=pins, code_complete='NOT_CREATED' not in pins.values(),
            models=list(MODELS), students=list(STUDENTS), authority_end_utc=p.END.isoformat(),
            original_info_sha256=sha(guards[0].metadata), original_authority_end_utc=guards[0].metadata['authority_end_utc'],
            frozen_source_pins=SOURCE_PINS, binding_allowlist=sorted(BINDING_ALLOWLIST), computational_body_sha256=parity,
            captured_body_sha256=captured_parity, fp32_wrapper_body_sha256=class_parity, model_table=MODEL_TABLE,
            trained_provider_tags=PROVIDER_TAGS, actual_model_references='ONLY_CPU_PREPARE_AFTER_ALL_SIX_COMPLETED',
            model_family_field_scope='TRAINED_WEIGHT_ROUTE_LOADER_CONTRACT; provider_role records actual curriculum',
            native_cfg_tokenizer_bridge='Native5953tuple plus actual model.cfg and identical pinned public tokenizer',
            maximum_worker_seconds=WORKER_LIMIT, product_broad_loader_used=False,
            activity_accounting='ORIGINAL_AUX_WORKER_SHA_LINK_DEDUP_UNCHANGED_OWN_NAMESPACE_ONLY',
            gsm_scope='64_ORIGINAL_PROBLEMS_TWO_FORMATS_NOT128_INDEPENDENT',
            admitted_reference_policy='PROCESS_LOCAL_EXACT_STRICT_REFERENCE_REQUIRED_BEFORE_LOAD',
            f4_sha256=p.digest(F4), automatic_adoption=False)
        return canonical(value)

    def authority(now=None):
        now = datetime.now(timezone.utc) if now is None else now
        if now.tzinfo is None: raise ValueError('시간대 있는 실제 시각이 필요하다')
        remaining = (p.END - now).total_seconds() - p.RECORD_RESERVE
        if remaining <= 0: raise p.Pending('21일17시 전 기록600초 예비에 도달했다')
        return remaining

    def model_reference(model_id):
        assert_unchanged(); result = model_reference_for(p, providers, model_id)
        admitted[model_id] = canonical(result); assert_unchanged(); return result

    @contextmanager
    def model_runtime(model_id, spec):
        assert_unchanged(); validate_spec(p, providers, model_id, spec)
        if admitted.get(model_id) != canonical(spec): raise ValueError('실제 strict 참조와 동일한 검산을 먼저 해야 한다')
        try:
            with load_model_for(p, providers, model_id, spec) as values: yield values
        finally: assert_unchanged()

    def phase_commands(mode, model_id, cap):
        if type(cap) is not int or not 60 <= cap <= WORKER_LIMIT: raise ValueError('새 worker의60..1800초 상한이 필요하다')
        result = captured['phase_commands'](mode, model_id, cap)
        for label, command in result:
            if label == 'REGRESSION': command.insert(command.index('-v'), TEST[:-3].replace('/', '.'))
            elif command.count(SCRIPT) != 1 or SOURCE in command: raise ValueError('모든 child는 새 driver만 호출한다')
        return result

    def worker(mode, model_id, cap):
        if type(cap) is not int or not 60 <= cap <= WORKER_LIMIT: raise ValueError('실제 worker상한1800초를 넘을 수 없다')
        return captured['worker'](mode, model_id, cap)

    def validate_activity(value, key, complete=False):
        if type(value.get('max_wall_sec')) is not int or value['max_wall_sec'] > WORKER_LIMIT:
            raise ValueError('원 영수증도 자기 worker상한1800초 안이어야 한다')
        return captured['validate_activity'](value, key, complete)

    codes = set((*original.CODE, *SOURCE_PINS, SCRIPT, TEST))
    for owner in providers.values(): codes.update(owner.runtime.info()['code_sha256'])
    bindings = dict(ROOT=ROOT, TAG=TAG, SCHEMA=SCHEMA, CACHE=ROOT / 'data_cache' / TAG,
        RAW=ROOT / 'runs/eval' / TAG, EVIDENCE=ROOT / 'test_result/evidence' / TAG, END=END,
        MODELS=MODELS, STUDENTS=STUDENTS, recovery=UnusedProductBroad(), CODE=tuple(sorted(codes)), OWN_CODE=(SCRIPT, TEST),
        info=info, authority=authority, model_reference=model_reference, model_runtime=model_runtime,
        phase_commands=phase_commands, worker=worker, validate_activity=validate_activity)
    if set(bindings) != BINDING_ALLOWLIST: raise ValueError('정확한 binding allowlist가 필요하다')
    for name, value in bindings.items(): setattr(p, name, value)
    expected_bindings.update(bindings)
    p._public_assert_unchanged, p._public_captured = assert_unchanged, captured
    p._public_original, p._public_providers = original, types.MappingProxyType(dict(providers))
    audit_bindings.update({name: getattr(p, name) for name in AUDIT_ATTRIBUTES})
    assert_unchanged(); return p


def build_runtime():
    sources = checked_sources(); utility = importlib.import_module(UTILITY[:-3].replace('/', '.'))
    pattern = importlib.import_module(PATTERN[:-3].replace('/', '.'))
    providers = {}
    for role, source in (('native595', NATIVE), ('oldbroad', OLDBROAD), ('newbroad', NEWBROAD)):
        module = importlib.import_module(source[:-3].replace('/', '.'))
        providers[role] = Provider(role, module, module.build_runtime())
    original = importlib.import_module(SOURCE[:-3].replace('/', '.'))
    return _build_runtime(original, types.MappingProxyType(providers), utility, pattern, sources[SOURCE], (utility, pattern))


def main(argv=None):
    runtime = None
    try:
        runtime = build_runtime()
        try: return runtime.main(argv)
        finally: runtime._public_assert_unchanged()
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if (isinstance(exc, (FileNotFoundError, FileExistsError))
            or runtime is not None and isinstance(exc, runtime.Pending)) else 9
        if code == 9: traceback.print_exc(file=sys.stderr)
        print('[NATIVE595_PUBLIC_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__': raise SystemExit(main())
