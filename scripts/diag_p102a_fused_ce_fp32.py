#!/usr/bin/env python3
"""공식 CE의 FP32 실제 첫 update를 독립 진단한다.

check-only는 표준 라이브러리로 소스와 설치 영수증만 읽는다. 실행은 별도
소유 프로세스에서 기존 capture/compare/replay를 호출한다. 원 두 정밀도·6팔,
BF16 음성, Muon, 수치 문턱을 바꾸지 않는다. 작은 update는 품질·가속 채택
근거가 아니며, 호출자는 별도 OS timeout과 실제 최종 종료를 회수해야 한다.
"""
from __future__ import annotations

import time
STARTED = time.perf_counter()

import argparse
import copy
import ctypes
from datetime import datetime, timedelta, timezone
import functools
import gc
import importlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p102a_fused_ce as fused

old, trace = fused.old, fused.trace
SCHEMA = 'P102A_OFFICIAL_FUSED_CE_FP32_PARENT_V1'
TAG_PREFIX = 'p102a_fused_ce_fp32_v1_s1337_'
SCRIPT = 'scripts/diag_p102a_fused_ce_fp32.py'
TEST = 'scripts/test_p102a_fused_ce_fp32.py'
PRECISION = 'fp32_math'
HARD_STOP = datetime(2026, 10, 25, 4, tzinfo=timezone.utc)
MAX_BYTES = fused.MAX_BYTES
SUPERVISION = ('scripts/codex_smoke.py', 'scripts/smoke_module.py',
               'scripts/smoke_execution_contract.py')
WORKER_ENV = 'TINYLM_FUSED_CE_FP32_OWNER'


def sources(root=ROOT):
    """기존 원형 및 새 제어기·감독 의존성의 바이트를 함께 고정한다."""
    result = fused.sources(root)
    for name in (SCRIPT, TEST, *SUPERVISION):
        path = old.safe_path(name, root)
        if path.stat().st_size > MAX_BYTES:
            raise ValueError('소스 파일 크기 상한을 넘었다: ' + name)
        result[name] = old.digest(path)
    return dict(sorted(result.items()))


def check_pins(args, guard):
    source_map = sources()
    guard.check('소스 검산 후')
    if old.identity(source_map) != args.source_sha256:
        raise ValueError('소스 영수증이 달라 실행을 허용하지 않는다')
    dependencies = fused.dependency_metadata()
    guard.check('설치 메타데이터 검산 후')
    if old.identity(dependencies) != args.dependency_sha256 or not dependencies['ready']:
        raise ValueError('설치 영수증이 달라졌거나 준비되지 않았다')
    installed = fused.verify_installed_sources(dependencies)
    guard.check('설치된 의존 소스 검산 후')
    return source_map, dependencies, installed


def validate_execution(args, now=None):
    if (bool(getattr(args, 'execute', False)) == bool(getattr(args, '_worker', False))
            or getattr(args, 'check_only', False)):
        raise ValueError('명시적인 단일 실행 모드가 필요하다')
    now = old.utc_now() if now is None else now
    deadline = old.aware(args.deadline)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('현재 시각에 시간대가 필요하다')
    if not now < deadline <= HARD_STOP:
        raise ValueError('마감은 미래이면서 2026-10-25 13:00 KST 이하여야 한다')
    if type(args.max_wall_sec) is not int or not 60 <= args.max_wall_sec <= 900:
        raise ValueError('실행 시간창은 정수 60..900초여야 한다')
    if not getattr(args, '_worker', False) and (deadline - now).total_seconds() < args.max_wall_sec:
        raise ValueError('전체 시간창이 절대 마감 전에 들어가지 않는다')
    validate_tag(args.tag)
    for name in ('source_sha256', 'dependency_sha256'):
        if re.fullmatch(r'[0-9A-F]{64}', str(getattr(args, name, ''))) is None:
            raise ValueError('현재 check-only의 SHA256이 필요하다: ' + name)
    if os.environ.get('TRITON_INTERPRET') not in (None, '', '0'):
        raise ValueError('실제 CUDA 진단에서 Triton CPU 인터프리터 대체를 허용하지 않는다')
    return deadline


def validate_tag(tag):
    if not isinstance(tag, str) or re.fullmatch(re.escape(TAG_PREFIX) + r'[a-z0-9][a-z0-9_]{0,63}', tag) is None:
        raise ValueError('새 FP32 전용 namespace가 필요하다')


def output_path(tag, root=ROOT, *, fresh=True):
    validate_tag(tag)
    target = old.safe_path('test_result/evidence/' + tag, root)
    if fresh and (target.exists() or target.is_symlink()):
        raise FileExistsError('기존 증거 namespace를 보존한다: ' + str(target))
    if not fresh and not target.is_dir():
        raise ValueError('감독자가 만든 namespace가 필요하다')
    return target


class Guard(fused.Guard):
    """원 Guard를 재사용하며 부모 진입부터 쓴 시간을 자식에도 청구한다."""
    def __init__(self, deadline, seconds, *, started=None, reserve=0):
        super().__init__(deadline, seconds)
        started = STARTED if started is None else started
        if not math.isfinite(started) or not 0 <= started <= time.perf_counter():
            raise ValueError('현재 프로세스 계열의 유효한 시작 시각이 필요하다')
        self.started = started
        self.seconds -= reserve
        self.deadline -= timedelta(seconds=reserve)

    def remaining(self):
        return min(self.seconds - (time.perf_counter() - self.started),
                   (self.deadline - old.utc_now()).total_seconds())

    @staticmethod
    def clock():
        return time.perf_counter()


def finite_tree(value):
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return (value.get('finite') is not False and value.get('nonfinite') is not True
                and all(finite_tree(item) for item in value.values()))
    if isinstance(value, (list, tuple)):
        return all(finite_tree(item) for item in value)
    return True


def run_fp32_canaries(torch, tolerances, guard, journal, report):
    """원 커널 함수를 FP32로만 호출한다. 원 run_canaries는 불변이다."""
    generator = torch.Generator(device='cpu').manual_seed(1337)
    table = torch.randn(32768, 256, generator=generator, dtype=torch.float32) * .01
    features = torch.randn(8, 256, generator=generator, dtype=torch.float32) * .1
    labels = torch.tensor([0, 1, -100, 32767, 9, 100, 200, 300], dtype=torch.long)
    rows = {}
    report.update(scope='FP32_ONLY_ORIGINAL_OFFICIAL_KERNEL_CANARY',
        shape=dict(rows=8, projection=256, vocabulary=32768),
        precisions={PRECISION: rows}, complete=False, close=False,
        original_bf16_result='PRESERVED_NOT_RECLASSIFIED')
    reference = None
    for backend in fused.BACKENDS:
        guard.check('독립 FP32 canary 전')
        try:
            value = fused.kernel_canary_arm(torch, features, table, labels, backend, PRECISION, guard)
            if backend == 'reference':
                reference = value
                rows[backend] = dict(status='COMPLETE', loss=value['loss'], close=True)
            else:
                comparisons = dict(loss=old.scalar_difference(reference['loss'], value['loss'],
                    tolerances['loss_and_norm']), gradients=trace.comparison(torch,
                    reference['gradients'], value['gradients'], tolerances['gradients_and_update']))
                rows[backend] = dict(status='COMPLETE', comparisons=comparisons,
                    close=all(item['close'] for item in comparisons.values()))
            if not finite_tree(rows[backend]):
                raise ValueError('비유한 canary 값은 수치 음성이 아닌 실행 오류다')
            del value
        except (TimeoutError, KeyboardInterrupt):
            raise
        except Exception as error:
            rows[backend] = dict(status='ERROR', close=False,
                error=fused.error_record(error, 'FP32 canary'))
        finally:
            trace.release_cuda(torch)
        journal.append(dict(event='fp32_official_kernel_canary', backend=backend,
            precision=PRECISION, **rows[backend], at=old.utc_now().isoformat()))
    report['complete'] = set(rows) == set(fused.BACKENDS) and all(item['status'] == 'COMPLETE' for item in rows.values())
    report['close'] = report['complete'] and all(item['close'] for item in rows.values())
    if not report['complete']:
        raise ValueError('FP32 canary가 불완전하여 부모를 열지 않는다')
    if not report['close']:
        raise fused.NumericalCanaryNegative('FP32 canary의 원 엄격 문턱 음성으로 부모를 열지 않는다')


def execute_three(torch, engine, muon, cls, cfg, initial, initial_sha, pad,
                  groups, plan, guard, journal, result):
    """원 함수로 reference와 후보 하나씩만 보유하며 정확히 3팔을 실행한다."""
    pairs = result['pairs']
    reference = fused.released_capture(torch, engine, muon, cls, cfg, initial,
        initial_sha, pad, 'reference', PRECISION, groups, plan, guard, journal, 0)
    try:
        result['updates'].append(reference['update'])
        for index, backend in enumerate(fused.BACKENDS[1:], 1):
            guard.check('독립 FP32 후보 update 전')
            candidate = fused.released_capture(torch, engine, muon, cls, cfg, initial,
                initial_sha, pad, backend, PRECISION, groups, plan, guard, journal, index)
            try:
                result['updates'].append(candidate['update'])
                measured = fused.capture_bytes(initial, reference, candidate)
                result['max_cpu_captured_tensor_bytes'] = max(result.get('max_cpu_captured_tensor_bytes', 0), measured)
                if measured + trace.CPU_SCRATCH_RESERVE > trace.CPU_CAPTURE_LIMIT:
                    raise MemoryError('원 8GiB CPU 보유 한도를 넘었다. gradient를 버리지 않는다')
                row = pairs[backend] = fused.compare_pair(torch, reference, candidate, result['tolerances'])
                row['replay'] = {}
                old.gpu_admission(torch)
                fused.replay_pair(torch, muon, initial, reference, candidate,
                    result['tolerances']['gradients_and_update'], guard, journal, row['replay'])
                trace.release_cuda(torch)
            finally:
                candidate = None
    finally:
        reference = None


def three_complete(result):
    canaries = result.get('canaries', {})
    if (not canaries.get('complete') or canaries.get('close') is not True
            or set(canaries.get('precisions', {})) != {PRECISION}
            or set(canaries['precisions'][PRECISION]) != set(fused.BACKENDS)
            or not all(row.get('status') == 'COMPLETE' and row.get('close') is True
                       for row in canaries['precisions'][PRECISION].values())
            or [(row.get('precision'), row.get('ce_backend')) for row in result.get('updates', [])]
               != [(PRECISION, backend) for backend in fused.BACKENDS]
            or set(result.get('pairs', {})) != set(fused.BACKENDS[1:])):
        return False
    for row in result['pairs'].values():
        comparisons = row.get('comparisons', {})
        if (type(row.get('close')) is not bool
                or set(comparisons) != set((*fused.FULL_FIELDS, *fused.MATRIX_FIELDS, 'optimizer', 'loss', 'preclip_norm'))):
            return False
        for key in (*fused.FULL_FIELDS, *fused.MATRIX_FIELDS, 'optimizer'):
            count = fused.ALL_COUNT if key in fused.FULL_FIELDS else fused.MATRIX_COUNT
            if key == 'optimizer':
                count = fused.MATRIX_COUNT + 3 * (fused.ALL_COUNT - fused.MATRIX_COUNT)
            table = comparisons[key]
            entries = table.get('per_parameter', ())
            if (type(table.get('close')) is not bool or table.get('tensors') != count or len(entries) != count
                    or len({entry.get('name') for entry in entries}) != count
                    or any(entry.get('finite') is not True or type(entry.get('close')) is not bool for entry in entries)):
                return False
        if any(type(comparisons[key].get('close')) is not bool for key in ('loss', 'preclip_norm')):
            return False
        replay = row.get('replay', {})
        if (not replay.get('complete') or replay.get('matrix_count') != fused.MATRIX_COUNT
                or len(replay.get('matrices', {})) != fused.MATRIX_COUNT
                or replay.get('same_gradient_controls_exact') is not True
                or replay.get('actual_updates_reproduced_exactly') is not True):
            return False
        for matrix in replay['matrices'].values():
            if (matrix.get('identical_gradient_control', {}).get('exact') is not True
                    or set(matrix.get('actual_reproduction', {})) != {'reference', 'candidate'}
                    or not all(value.get('exact') is True for value in matrix['actual_reproduction'].values())
                    or type(matrix.get('original_pair', {}).get('close')) is not bool):
                return False
    return True


def classify(result):
    if result.get('errors') or result.get('cleanup_errors') or not finite_tree(result):
        return 'ERROR_PARTIAL_FP32_NOT_ADOPTED', 9
    canaries = result.get('canaries', {})
    rows = canaries.get('precisions', {}).get(PRECISION, {})
    if (result.get('canary_negative') and canaries.get('complete') and canaries.get('close') is False
            and set(canaries.get('precisions', {})) == {PRECISION} and set(rows) == set(fused.BACKENDS)
            and all(row.get('status') == 'COMPLETE' for row in rows.values())
            and not result.get('updates') and not result.get('pairs') and result.get('assets_before') is None):
        return 'FP32_CANARY_NUMERICAL_NEGATIVE_PARENT_NOT_RUN', 8
    if not three_complete(result):
        return 'ERROR_INCOMPLETE_FP32_NOT_ADOPTED', 9
    close = all(row['close'] and all(value['close'] for value in row['comparisons'].values())
        and all(matrix['original_pair']['close'] for matrix in row['replay']['matrices'].values())
        for row in result['pairs'].values())
    return ('FP32_NUMERICAL_PASS_NOT_ADOPTED', 0) if close else ('FP32_NUMERICAL_NEGATIVE_NOT_ADOPTED', 8)


def runtime(guard, journal, result):
    """원 부모·자료·배치와 모델 수학은 기존 함수에 위임한다."""
    torch = identity = assets = template = initial = None
    try:
        import tinylm
        import torch
        from tinylm.train import muon
        guard.check('원 프레임워크 import 후')
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        result['cpu_control'] = trace.cpu_control(torch, muon)
        identity = trace.GlobalIdentity(muon)
        run_fp32_canaries(torch, result['tolerances'], guard, journal, result['canaries'])
        identity.check()
        guard.check('원 자료와 부모 입장 전')
        from scripts import diag_p101a_sft_mtp as engine
        from scripts import diag_p101a_clean_bilingual as clean
        corpus = engine.corpus_report(old.safe_path(old.CORPUS))
        assets = old.asset_manifest(engine, corpus)
        result['assets_before'] = assets
        guard.check('고정 부모 로딩 전')
        torch, template, cfg, tok, initial_sha = engine.load_runtime('parent_ntp')
        if (cfg.cla_group != 2 or not cfg.grad_checkpoint or cfg.mtp_aux or cfg.train_repeat != 1.
                or any(isinstance(module, torch.nn.Dropout) and module.p for module in template.modules())):
            raise ValueError('원 CLA2·checkpoint-on·MTP-off·R1·dropout0 조건이 필요하다')
        result['cpu_memory_plan'] = fused.memory_plan(template, muon)
        initial = old.cpu_copy(template.state_dict())
        records = clean.encoded(old.safe_path(old.CORPUS), corpus, tok)
        if len(records['train']) != 22528 or len(records['val']) != 512:
            raise ValueError('원 고정 자료 행 수가 필요하다')
        groups = next(iter(engine.batches(records['train'], 0)))
        plan = old.update_plan(groups)
        cls = type(template)
        pad = tok.token_to_id('<|pad|>')
        if pad is None:
            pad = tok.token_to_id('<pad>')
        if type(pad) is not int or not 0 <= pad < 32768:
            raise ValueError('원 PAD ID가 필요하다')
        result.update(initial_core_sha256=initial_sha, parent_sha256=old.PARENT_SHA,
            tokenizer_sha256=old.TOKENIZER_SHA, plan=plan, seed=1337,
            optimizer=dict(factory='diag_p101a_sft_mtp.optimizers', adam_lr=5e-5,
                muon_lr=2e-4, clip=1., fresh_each_arm=True, reclip_in_replay=False))
        template = None
        gc.collect()
        execute_three(torch, engine, muon, cls, cfg, initial, initial_sha, pad,
            groups, plan, guard, journal, result)
        identity.check()
        guard.check('FP32 3팔과 실제 gradient 재생 후')
    except fused.NumericalCanaryNegative as error:
        result['canary_negative'] = fused.error_record(error, 'FP32 canary 수치 음성')
    except (Exception, KeyboardInterrupt) as error:
        result['errors'].append(fused.error_record(error, 'FP32 실제 update 진단'))
    finally:
        template = initial = None
        try:
            original_sources = {name: result['sources'][name] for name in fused.sources()}
            fused.audit_final(torch, identity, original_sources, result['dependencies'], assets, result)
        except (Exception, KeyboardInterrupt) as error:
            result.setdefault('cleanup_errors', []).append(fused.error_record(error, '원형 최종 감사'))
        for name, action in (
            ('wrapper_sources_unchanged', lambda: sources() == result['sources']),
            ('installed_sources_unchanged', lambda: fused.verify_installed_sources(result['dependencies'])
                == result['dependency_source_verification']),
        ):
            try:
                result[name] = action()
                if not result[name]:
                    raise ValueError('실행 중 원천 바이트 변경: ' + name)
            except (Exception, KeyboardInterrupt) as error:
                result.setdefault('cleanup_errors', []).append(fused.error_record(error, name))


def failure(target, result, stage, error):
    result.setdefault('errors', []).append(fused.error_record(error, stage))
    result['status'], result['returncode'] = classify(result)
    event = dict(event='TERMINAL_VETO', stage=stage, returncode=9,
        errors=result['errors'], cleanup_errors=result.get('cleanup_errors', []),
        at=old.utc_now().isoformat())
    try:
        fused.append_terminal(target, event)
    except (Exception, KeyboardInterrupt) as extra:
        result['errors'].append(fused.error_record(extra, '종결 거부 기록'))
        try:
            print(json.dumps(dict(event='TERMINAL_VETO_STORAGE_ERROR', original=event,
                storage_error=fused.error_record(extra, stage)), ensure_ascii=False), file=sys.stderr, flush=True)
        except (Exception, KeyboardInterrupt):
            pass


def terminalize(target, journal, guard, result):
    def attempt(stage, action):
        try:
            value = action()
            guard.check(stage + ' 후')
            return value
        except (Exception, KeyboardInterrupt) as error:
            failure(target, result, stage, error)
            return None
    attempt('사건 원장 닫기', journal.close)
    result['three_complete'] = three_complete(result)
    result['wall_seconds'] = time.perf_counter() - guard.started
    result['finished_at'] = old.utc_now().isoformat()
    result['status'], result['returncode'] = classify(result)
    snapshot = copy.deepcopy(result)
    expected = old.identity(snapshot)
    path = target / 'report.json'
    attempt('수치 보고서 저장', lambda: old.write_new(path, snapshot))
    def reread():
        if path.stat().st_size > MAX_BYTES or path.is_symlink():
            raise ValueError('보고서 크기 또는 파일 경계 위반')
        if old.identity(json.loads(path.read_text(encoding='utf-8'))) != expected:
            raise ValueError('저장 후 재읽은 수치 보고서 바이트가 다르다')
        return True
    roundtrip = attempt('수치 보고서 재읽기', reread)
    result['status'], result['returncode'] = classify(result)
    attempt('worker 출력', lambda: print(json.dumps(dict(schema=SCHEMA, tag=result['tag'],
        provisional_status=result['status'], provisional_returncode=result['returncode'],
        actual_process_exit='PENDING_SUPERVISOR_AND_EXTERNAL_CALLER', quality_claim=False),
        ensure_ascii=False), flush=True))
    result['status'], result['returncode'] = classify(result)
    event = dict(event='TERMINAL_VETO' if result.get('errors') or result.get('cleanup_errors') else 'WORKER_AUDIT_COMPLETE',
        returncode=result['returncode'], report_sha256=expected, report_roundtrip=roundtrip is True,
        errors=result.get('errors', []), cleanup_errors=result.get('cleanup_errors', []),
        at=old.utc_now().isoformat(), actual_process_exit='PENDING_SUPERVISOR_AND_EXTERNAL_CALLER')
    attempt('worker 종결 표지', lambda: fused.append_terminal(target, event))
    try:
        guard.check('worker 반환 직전')
    except (Exception, KeyboardInterrupt) as error:
        failure(target, result, 'worker 최종 시각', error)
    return classify(result)[1]


def worker(args):
    owner = int(os.environ.get(WORKER_ENV, '0'))
    if owner <= 1 or owner != os.getppid() or args._started is None:
        raise ValueError('소유 감독자가 직접 시작한 worker만 허용한다')
    deadline = validate_execution(args)
    # 자식의 준비·감사·저장은 부모 정리와 실제 종료 회수보다 먼저 끝낸다.
    guard = Guard(deadline, args.max_wall_sec, started=float(args._started), reserve=15)
    target = output_path(args.tag, fresh=False)
    state = {}
    try:
        with fused.total_budget(guard):
            source_map, dependencies, installed = check_pins(args, guard)
            admission = json.loads((target / 'admission.json').read_text(encoding='utf-8'))
            if (admission['owner_pid'] != owner or admission['source_sha256'] != args.source_sha256
                    or admission['dependency_sha256'] != args.dependency_sha256):
                raise ValueError('부모 입장 영수증과 worker 신원이 다르다')
            args._owned_target = target
            initial_admission = old.gpu_admission()
            journal = old.Journal(target / 'events.jsonl')
            result = dict(schema=SCHEMA, tag=args.tag, sources=source_map,
                source_sha256=old.identity(source_map), dependencies=dependencies,
                original_source_sha256=old.identity({name: source_map[name] for name in fused.sources()}),
                dependency_sha256=old.identity(dependencies), dependency_source_verification=installed,
                started_at=old.utc_now().isoformat(), deadline=deadline.isoformat(),
                max_wall_sec=args.max_wall_sec, worker_reserve_sec=15, checkpoint_writes=0,
                original_precisions=list(fused.PRECISIONS), original_six_arm_contract='UNCHANGED_NOT_RUN',
                precision_scope=PRECISION, bf16_status='ORIGINAL_NEGATIVE_PRESERVED_NOT_RECLASSIFIED',
                production_adopted=False, quality_claim=False, speed_adoption=False,
                full_training='NOT_RUN', mtp_gpu='NOT_RUN_MAIN_ONLY',
                dataset_quality='KNOWN_V3_SUPERVISION_DEFECTS_NUMERICAL_CONTROL_ONLY_NOT_ADMITTED',
                timing_scope='CANARY_PREWARMED_INSTRUMENTED_FIRST_UPDATE_WITH_CPU_CAPTURES_NOT_STEADY_STATE',
                memory_scope='CUDA_UPDATE_ALLOCATED_RESERVED_PEAKS_AND_SEPARATE_CPU_CAPTURE_BUDGET_NOT_PROCESS_RSS',
                max_wall_scope='PARENT_ENTRY_PREP_IMPORT_COMPILE_RUNTIME_CLEANUP_IO_STDOUT_ACTUAL_CHILD_EXIT',
                external_os_timeout_required=True,
                actual_process_exit='PENDING_SUPERVISOR_AND_EXTERNAL_CALLER',
                tolerances=old.literal_tolerances(), gpu_admission=initial_admission,
                canaries={}, updates=[], pairs={}, assets_before=None, errors=[], cleanup_errors=[])
            state.update(journal=journal, result=result)
            runtime(guard, journal, result)
            return terminalize(target, journal, guard, result)
    except (Exception, KeyboardInterrupt) as error:
        if not state:
            raise
        try:
            state['journal'].close()
        except (Exception, KeyboardInterrupt) as close_error:
            state['result'].setdefault('cleanup_errors', []).append(fused.error_record(close_error, '외곽 원장 닫기'))
        failure(target, state['result'], 'worker 전체 시간창 또는 종결', error)
        return 9


def process_tools():
    return importlib.import_module('scripts.codex_smoke')


def run_owned_worker(command, env, logfile, guard, *, factory=None, tools=None, state=None):
    tools = process_tools() if tools is None else tools
    state = {} if state is None else state
    def monitor():
        guard.check('소유 worker 감독')
        if guard.remaining() <= 8.:
            raise tools.BudgetExpired('종결과 소유 그룹 정리 예약에 도달했다')
        if logfile.stat().st_size > MAX_BYTES:
            raise ValueError('worker 로그 크기 상한을 넘었다')
    previous = signal.getsignal(signal.SIGTERM)
    installed = previous != signal.SIG_IGN
    def interrupted(*_):
        raise KeyboardInterrupt('소유 worker 종료 요청')
    try:
        if installed:
            signal.signal(signal.SIGTERM, interrupted)
        current = guard.clock()
        return tools.run_child(command, root=ROOT, env=env,
            work_expires=current + guard.remaining() - 8.,
            expires=current + guard.remaining() - 3., clock=guard.clock,
            monitor=monitor, process_factory=factory, state_sink=state)
    except BaseException as error:
        state.update(adapter_error=fused.error_record(error, '감독 adapter'), unsafe_process_state=True)
        raise
    finally:
        if installed:
            try:
                signal.signal(signal.SIGTERM, previous)
            except BaseException as error:
                state.update(adapter_cleanup_error=fused.error_record(error, '감독 handler 복구'), unsafe_process_state=True)


def worker_limits(owner_pid):
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_BYTES, MAX_BYTES))
    # 부모 SIGKILL 때 worker 본인만 종료한다. compiler 자손 전체 보장은 아니다.
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), '부모 종료 시 worker 중단 설정 실패')
    if os.getppid() != owner_pid:
        os.kill(os.getpid(), signal.SIGKILL)


def read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError('정상 파일과 파일당 20MB 미만이 필요하다: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def verify_worker(target, args, supervision, guard):
    actual = supervision.get('returncode')
    if (supervision.get('status') != 'COMPLETE' or supervision.get('unsafe_process_state')
            or supervision.get('process_started') is not True or actual not in (0, 8, 9)):
        raise ValueError('소유 프로세스 그룹과 실제 종료를 확인하지 못했다')
    report = read_json(target / 'report.json')
    terminal_path = target / 'terminal.jsonl'
    if terminal_path.is_symlink() or terminal_path.stat().st_size > MAX_BYTES:
        raise ValueError('종결 원장 파일 경계 위반')
    terminal = [json.loads(line) for line in terminal_path.read_text(encoding='utf-8').splitlines()]
    guard.check('자식 보고서와 종결 원장 재읽기 후')
    expected_code = classify(report)[1]
    if (report.get('schema') != SCHEMA or report.get('tag') != args.tag
            or report.get('source_sha256') != args.source_sha256
            or old.identity(report.get('sources', {})) != args.source_sha256
            or old.identity(report.get('dependencies', {})) != args.dependency_sha256
            or report.get('dependency_sha256') != args.dependency_sha256
            or any(event.get('event') == 'TERMINAL_VETO' for event in terminal)
            or not terminal or terminal[-1].get('event') != 'WORKER_AUDIT_COMPLETE'
            or terminal[-1].get('report_roundtrip') is not True
            or terminal[-1].get('report_sha256') != old.identity(report)
            or terminal[-1].get('returncode') != expected_code
            or report.get('returncode') != expected_code or actual != expected_code):
        raise ValueError('수치·영수증·종결 거부·실제 종료가 일치하지 않는다')
    for key in ('sources_unchanged', 'wrapper_sources_unchanged', 'dependencies_unchanged',
                'installed_sources_unchanged', 'original_muon_globals_unchanged'):
        if report.get(key) is not True:
            raise ValueError('최종 감사가 불완전하다: ' + key)
    if report.get('final_allocated_bytes') != 0:
        raise ValueError('CUDA allocated 0 확인이 필요하다')
    return expected_code


def supervise(args, guard):
    source_map, dependencies, installed = check_pins(args, guard)
    target = output_path(args.tag)
    guard.check('새 namespace 생성 전')
    target.mkdir()
    args._owned_target = target
    state, errors = {}, []
    code = 9
    try:
        old.write_new(target / 'admission.json', dict(schema=SCHEMA, tag=args.tag,
            source_sha256=args.source_sha256, dependency_sha256=args.dependency_sha256,
            sources=source_map, dependencies=dependencies, dependency_sources=installed,
            owner_pid=os.getpid(), deadline=args.deadline, max_wall_sec=args.max_wall_sec,
            started_monotonic=guard.started, worker_reserve_sec=15,
            external_os_timeout_required=True, compiler_descendant_sigkill_guarantee=False))
        command = [sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--_worker',
            '--tag', args.tag, '--deadline', args.deadline, '--max-wall-sec', str(args.max_wall_sec),
            '--source-sha256', args.source_sha256, '--dependency-sha256', args.dependency_sha256,
            '--_started', str(guard.started)]
        env = dict(os.environ, **{WORKER_ENV: str(os.getpid())}, PYTHONDONTWRITEBYTECODE='1',
            TRITON_CACHE_DIR=str(target / 'triton_cache'), TORCHINDUCTOR_CACHE_DIR=str(target / 'torch_cache'))
        with (target / 'worker.log').open('xb') as stream:
            def factory(argv, **options):
                return subprocess.Popen(argv, **options, stdout=stream, stderr=subprocess.STDOUT,
                    preexec_fn=functools.partial(worker_limits, os.getpid()))
            run_owned_worker(command, env, target / 'worker.log', guard, factory=factory, state=state)
        code = verify_worker(target, args, state, guard)
        final_sources, final_dependencies, final_installed = check_pins(args, guard)
        if (final_sources != source_map or final_dependencies != dependencies or final_installed != installed):
            raise ValueError('부모의 최종 원천 검산이 달라졌다')
        old.gpu_admission()
        guard.check('실제 worker 종료 후 GPU 소유자 검사')
    except BaseException as error:
        errors.append(dict(**fused.error_record(error, '부모 감독 또는 최종 감사'), original_traceback=traceback.format_exc()))
        code = 9
    event = dict(event='WORKER_ACTUAL_EXIT', actual_worker_exit=state.get('returncode'),
        intended_supervisor_exit=code, supervision=state, errors=errors, at=old.utc_now().isoformat())
    try:
        fused.append_terminal(target, event)
        guard.check('실제 자식 종료 저장 후')
        print(json.dumps(dict(schema=SCHEMA, tag=args.tag, intended_supervisor_exit=code,
            actual_worker_exit=state.get('returncode'), status='FP32_OBSERVATION_NOT_ADOPTED' if code in (0, 8) else 'ERROR_INCOMPLETE',
            output=str(target), errors=errors, actual_supervisor_exit='PENDING_EXTERNAL_CALLER',
            quality_claim=False, full_training='NOT_RUN'), ensure_ascii=False, allow_nan=False), flush=True)
        guard.check('부모 stdout 후')
        fused.append_terminal(target, dict(event='FINAL_DISPOSITION', intended_supervisor_exit=code,
            actual_worker_exit=state.get('returncode'), at=old.utc_now().isoformat()))
        guard.check('부모 최종 표지 후')
    except BaseException as error:
        failure(target, dict(errors=errors), '부모 최종 저장 또는 출력', error)
        code = 9
    return code


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    modes = result.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check-only', action='store_true')
    modes.add_argument('--execute', action='store_true')
    modes.add_argument('--_worker', action='store_true', help=argparse.SUPPRESS)
    for name in ('tag', 'deadline', 'source-sha256', 'dependency-sha256'):
        result.add_argument('--' + name)
    result.add_argument('--max-wall-sec', type=int)
    result.add_argument('--_started', help=argparse.SUPPRESS)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.check_only:
            source_map, dependencies = sources(), fused.dependency_metadata()
            print(json.dumps(dict(schema=SCHEMA, evidence='STATIC_ONLY_NOT_KERNEL_OR_PARENT_PASS',
                tag_prefix=TAG_PREFIX, source_sha256=old.identity(source_map), source_count=len(source_map),
                original_source_sha256=old.identity({name: source_map[name] for name in fused.sources()}),
                dependency_sha256=old.identity(dependencies), dependencies_ready=dependencies['ready'],
                package_versions={name: row['installed_version'] for name, row in dependencies['packages'].items()},
                precisions=[PRECISION], backends=list(fused.BACKENDS), original_precisions=list(fused.PRECISIONS),
                absolute_stop=HARD_STOP.isoformat(), max_wall_sec=900, max_file_bytes=MAX_BYTES,
                torch_imported='torch' in sys.modules, cuda_calls=0, model_calls=0, asset_reads=0, files_written=0,
                external_os_timeout_required=True), ensure_ascii=False, allow_nan=False), flush=True)
            return 0
        deadline = validate_execution(args)
        if args._worker:
            return worker(args)
        guard = Guard(deadline, args.max_wall_sec)
        with fused.total_budget(guard):
            code = supervise(args, guard)
        guard.check('전체 타이머 복구 후 반환 직전')
        return code
    except BaseException as error:
        print(json.dumps(dict(status='ERROR_INCOMPLETE_FP32_NOT_ADOPTED', intended_exit=9,
            error=fused.error_record(error, '진입 또는 전체 시간창')), ensure_ascii=False), file=sys.stderr, flush=True)
        if getattr(args, '_owned_target', None) is not None:
            try:
                fused.append_terminal(args._owned_target, dict(event='TERMINAL_VETO', returncode=9,
                    error=fused.error_record(error, '진입 또는 전체 시간창'), at=old.utc_now().isoformat()))
            except BaseException:
                pass
        return 9


if __name__ == '__main__':
    raise SystemExit(main())
