#!/usr/bin/env python3
"""P078 V2 검산 규약: JSON 표현만 정규화하며 원 학습은 바꾸지 않는다.

고정한 V1 driver/helper, 입력 서명, namespace, 권한·시간·가족 상한은 그대로다.
cost_receipt/budget/readback 안에서만 예상 계획을 JSON 표현으로 비교한다.
실제 학습·생성은 원 plan 객체를 유지한다. check-only는 실제 자산·자료·CP·
모델·Torch·GPU에 접근하지 않는다.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from functools import wraps
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
SCRIPT = 'scripts/diag_p078_route_protocol.py'
TEST = 'scripts/test_p078_route_protocol.py'
TAG = 'p078_route_protocol_v2_s1337'
SCHEMA = 'P078_ROUTE_JSON_VERIFICATION_PROTOCOL_V2'
PINS = {
    'scripts/diag_p078_route_training.py': '1794CF5E446E1F931D70038C229E0758319CF63E11B69892186D5050961EFC45',
    'scripts/p078_route_training.py': '934C065C9B11CFA208F9DA1C47C8CD4B49B1860612CCC9FDEF349C691FF57FFC',
}
MAX_METADATA = 20_000_000


def safe(relative, root=None):
    root = ROOT if root is None else Path(root)
    item = Path(relative)
    if (not root.is_absolute() or root.is_symlink() or item.is_absolute()
            or not item.parts or '..' in item.parts or '\\' in str(relative)
            or any(p in {'TinyDataset', '.claude', '.codex', '.agents', '.aws'} for p in item.parts)):
        raise ValueError('명시한 비연결 소스·검산 메타데이터 경로만 허용한다')
    result = root
    for part in item.parts:
        result = result / part
        if result.is_symlink(): raise ValueError('읽기·쓰기 전에 연결 경로를 거부한다')
    return result


def identity(relative, root=None):
    target = safe(relative, root)
    with target.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size >= MAX_METADATA:
            raise ValueError('상한 이내의 일반 소스·메타데이터 파일만 허용한다')
        raw = stream.read(MAX_METADATA)
        after = os.fstat(stream.fileno())
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or len(raw) != after.st_size:
        raise ValueError('읽는 동안 소스·메타데이터가 바뀌었다')
    return dict(path=str(relative), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest().upper())


def source_identity():
    result = {name: identity(name) for name in (*PINS, SCRIPT, TEST)}
    for name, expected in PINS.items():
        if result[name]['sha256'] != expected: raise ValueError('고정한 원 소스가 바뀌었다: ' + name)
    return result


def load_driver():
    source_identity()  # 원 모듈을 import하기 전에 소스 고정을 검산한다.
    module = importlib.import_module('scripts.diag_p078_route_training')
    if (Path(module.__file__).resolve() != safe('scripts/diag_p078_route_training.py')
            or Path(module.route.__file__).resolve() != safe('scripts/p078_route_training.py')):
        raise ValueError('import한 모듈이 고정한 원 파일과 다르다')
    source_identity()
    return module


def json_plan(value):
    """값·순서·해시는 유지하고 JSON의 tuple→list 표현 변환만 적용한다."""
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


@contextmanager
def normalized_plans(route):
    original = route.plan
    @wraps(original)
    def expected(*args, **kwargs): return json_plan(original(*args, **kwargs))
    with patch.object(route, 'plan', expected): yield


@contextmanager
def verification_scope(driver):
    """검산 호출만 감싸며 모델 실행 전체에 plan 변환을 적용하지 않는다."""
    def wrapped(original):
        @wraps(original)
        def verify(*args, **kwargs):
            with normalized_plans(driver.route): return original(*args, **kwargs)
        return verify
    with ExitStack() as stack:
        for name in ('cost_receipt', 'budget', 'readback'):
            stack.enter_context(patch.object(driver, name, wrapped(getattr(driver, name))))
        yield


def original_metadata(driver, args):
    namespace = driver.namespace(args)
    if namespace not in ('p078_route_training_v1_s1337_cleanv3', 'p078_route_training_v1_s1337_old8m'):
        raise ValueError('정확한 원 namespace만 허용한다')
    result = {}
    for mode in ('cost', 'train', 'budget', 'readback'):
        for arm in driver.route.ARMS:
            for name in (driver.report_name(mode, arm, args), driver.activity_name(mode, arm, args)):
                if not name.startswith('test_result/evidence/' + namespace + '/') or not name.endswith('.json'):
                    raise ValueError('원 report/activity 메타데이터만 허용하며 CP·원천 자산은 읽지 않는다')
                target = safe(name)
                if target.exists(): result[name] = identity(name)
    return result


def unchanged(before, after):
    if any(after.get(name) != value for name, value in before.items()):
        raise ValueError('기존 원 report/activity가 바뀌었다; 원형을 덮어 수리하지 않는다')


def write_receipt(value):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    relative = 'test_result/evidence/' + TAG + '/' + stamp + '_' + str(os.getpid()) + '_' + uuid.uuid4().hex + '.json'
    target = safe(relative)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(raw) >= MAX_METADATA: raise ValueError('검산 영수증은20MB 미만이어야 한다')
    target.parent.mkdir(parents=True, exist_ok=True)
    target = safe(relative)
    with target.open('xb') as stream: stream.write(raw)
    print('[P078_ROUTE_PROTOCOL_RECEIPT] ' + relative, flush=True)
    return relative


def recorded(driver, args, argv, action, role, details=None):
    sources = source_identity(); before = original_metadata(driver, args)
    code = 9; error = None; original_code = None
    try:
        original_code = action()
        if type(original_code) is not int: raise ValueError('원 returncode는 정수여야 한다')
        code = original_code
    except KeyboardInterrupt:
        code = 130; error = 'KeyboardInterrupt'
    except Exception as exc:
        code = 9; error = type(exc).__name__ + ': ' + str(exc)
        print('[PROTOCOL_ERROR] ' + error, flush=True)
    finally:
        after = {}
        try:
            after = original_metadata(driver, args)
            unchanged(before, after)
            if source_identity() != sources: raise ValueError('호출 중 새 검산 소스 또는 원 소스가 바뀌었다')
        except Exception as exc:
            code = 9; error = type(exc).__name__ + ': ' + str(exc)
        write_receipt(dict(schema=SCHEMA, tag=TAG, role=role,
            original_namespace=driver.namespace(args), original_input_signature_sha256=driver.route.sha(driver.signature(args)),
            argv=list(argv), source_files=sources, original_metadata_before=before, original_metadata_after=after,
            original_returncode=original_code, returncode=code, error=error,
            original_existing_metadata_unchanged=all(after.get(k) == v for k, v in before.items()),
            normalization='JSON_ROUNDTRIP_EXPECTED_PLAN_ONLY_INSIDE_COST_RECEIPT_BUDGET_READBACK',
            original_training_plan_changed=False, original_authority_override=False,
            details=details,
            scope='PROTOCOL_ONLY; 독립 모델 실행이나 과학·의미 품질 채택을 뜻하지 않는다'))
    return code


def parser_for(driver):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=(*driver.MODES, 'budget-preview'), required=True)
    parser.add_argument('--arm', choices=driver.route.ARMS, default='uniform_r2')
    parser.add_argument('--corpus-sha256'); parser.add_argument('--corpus', choices=driver.CORPORA, default=driver.CLEAN_CORPUS)
    parser.add_argument('--adam-lr', type=float, default=5e-5); parser.add_argument('--muon-lr', type=float, default=2e-4)
    parser.add_argument('--authorization'); parser.add_argument('--authorization-sha256')
    parser.add_argument('--max-wall-sec', type=int, default=1800); parser.add_argument('--worker', action='store_true')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check-only', action='store_true'); action.add_argument('--execute', action='store_true')
    return parser


def budget_preview(args, driver=None, argv=()):
    """원 예측만 읽으며 driver.main/worker/write 또는 모델을 실행하지 않는다.

    예측 음성은 미리보기 HOLD이지 원 가족의 실제 실행 실패가 아니다.
    나중에 별도 승인받아 실행해도 원 fresh gate를 다시 통과해야 한다.
    """
    driver = load_driver() if driver is None else driver
    details = dict(status='PREVIEW_NOT_RUN', model_loads=0, optimizer_updates=0,
                   original_activity_writes=0, original_report_writes=0)
    def action():
        if (not 60 <= args.max_wall_sec <= 144000
                or any(not math.isfinite(v) or v <= 0 for v in (args.adam_lr, args.muon_lr))):
            raise ValueError('원 양의 LR·worker 상한 조건을 지켜야 한다')
        try:
            if not driver.READY: raise driver.Hold('원 구현 준비 승인이 필요하다')
            if not isinstance(args.corpus_sha256, str) or len(args.corpus_sha256) != 64:
                raise driver.Hold('원 frozen corpus report의 정확한 SHA가 필요하다')
            with verification_scope(driver): result = driver.budget(args)
        except driver.Hold as exc:
            details.update(status='PREVIEW_HOLD_NOT_EXECUTED', error=str(exc))
            print('[P078_BUDGET_PREVIEW] ' + json.dumps(details, ensure_ascii=False), flush=True)
            return 8
        details.update(status='PREVIEW_READY_NOT_EXECUTED' if result['fits'] else 'PREVIEW_HOLD_NOT_EXECUTED', forecast=result)
        print('[P078_BUDGET_PREVIEW] ' + json.dumps(details, ensure_ascii=False), flush=True)
        return 0 if result['fits'] else 8
    code = recorded(driver, args, argv, action, 'READ_ONLY_BUDGET_PREVIEW', details)
    return dict(details, returncode=code)


def launch(argv, seconds):
    command = [sys.executable, '-B', '-X', 'utf8', str(safe(SCRIPT)), *argv, '--worker']
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
    try: return process.wait(timeout=seconds)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        try: os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()
        return 130


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        driver = load_driver(); args = parser_for(driver).parse_args(argv)
        if args.check_only:
            forwarded = list(argv)
            if args.mode == 'budget-preview':
                for i, value in enumerate(forwarded):
                    option = value.split('=', 1)[0]
                    if option.startswith('--') and '--mode'.startswith(option):
                        if '=' in value: forwarded[i] = option + '=budget'
                        else: forwarded[i + 1] = 'budget'
                        break
            with verification_scope(driver): return driver.main(forwarded)
        if args.mode == 'budget-preview': return budget_preview(args, driver, argv)['returncode']
        # 원래 모델을 시작하지 않는 경로의 기존 거부 조건도 그대로 유지한다.
        if (args.mode in ('toy', 'router', 'evaluate') or not driver.READY
                or not isinstance(args.corpus_sha256, str) or len(args.corpus_sha256) != 64
                or not 60 <= args.max_wall_sec <= 144000
                or any(not math.isfinite(v) or v <= 0 for v in (args.adam_lr, args.muon_lr))):
            with verification_scope(driver): return driver.main([*argv, '--worker'])
        if args.worker:
            def action():
                with verification_scope(driver): return driver.main(argv)
            return recorded(driver, args, argv, action, 'OWNED_WORKER')
        return recorded(driver, args, argv, lambda: launch(argv, args.max_wall_sec), 'PARENT_LAUNCH')
    except Exception as exc:
        print('[PROTOCOL_ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True)
        return 9


if __name__ == '__main__': raise SystemExit(main())
