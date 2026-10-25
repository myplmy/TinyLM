#!/usr/bin/env python3
"""기존 supported V3 생산기 앞의 Linux 소유 감독기.

원 생산기·pilot·입력·배치·STOP은 바꾸지 않는다. check-only는 표준
라이브러리로 소스와 작은 원형 메타데이터만 검산한다. 실행은 생산기를 직접
자식으로 시작하고, 별도 세션 교사·계측도 회수한다. 외부 OS timeout과 실제
supervisor 종료 회수는 별도로 필요하며, 후보의 의미 품질을 승인하지 않는다.
"""
from __future__ import annotations

import time
STARTED = time.monotonic()

import argparse
import ast
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import secrets
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import codex_smoke as smoke
from scripts import p106b_native_iq2_worker_window as proc
from scripts import p106b_shards as shards

SCHEMA = 'P106B_SUPPORTED_SUPERVISOR_20261025_V1'
PREFIX = 'p106b_supported_supervisor_v1_20261025_'
SCRIPT = 'scripts/diag_p106b_supported_supervisor.py'
TEST = 'scripts/test_p106b_supported_supervisor.py'
PRODUCER = 'scripts/diag_p106b_supported_production8h.py'
PREFLIGHT = 'handoff/audit/WIP_20261025_SUPPORTED_RESUME_PREFLIGHT.json'
OUTPUT = 'HF/sft_ready/p106b_supported_production8h_v3_s1337'
VERSION = 'GEMMA_SUPPORTED_SOURCE_8H_V3'
OWNER_KEY = 'TINYLM_SUPPORTED_SUPERVISOR_OWNER'
MAX_BYTES = 20_000_000
PRODUCTION_STOP = datetime(2026, 10, 25, 3, 40, tzinfo=timezone.utc)
AUTHORIZED_STOP = datetime(2026, 10, 25, 4, tzinfo=timezone.utc)
RESERVE = 120


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def identity(value):
    return hashlib.sha256(canonical(value)).hexdigest().upper()


def safe(name, root=ROOT):
    name = Path(name)
    proc.require(not name.is_absolute() and '..' not in name.parts and name.parts
        and name.parts[:2] != ('datasets', 'TinyDataset'), '허용된 저장소 상대 경로가 필요하다')
    path = Path(root)
    for part in name.parts:
        path /= part
        proc.require(not path.is_symlink(), '심볼릭 링크는 허용하지 않는다: ' + str(name))
    return path


def finite_json(item):
    if isinstance(item, float):
        return math.isfinite(item)
    if isinstance(item, dict):
        return all(finite_json(child) for child in item.values())
    if isinstance(item, list):
        return all(finite_json(child) for child in item)
    return True


def read_json(path):
    value = proc.read_json(path)
    proc.require(finite_json(value), '비유한 JSON 수치를 허용하지 않는다')
    return value


def bounded_file(path):
    path = Path(path)
    proc.require(path.is_file() and not path.is_symlink() and not any(parent.is_symlink() for parent in path.parents)
        and path.stat().st_size <= MAX_BYTES, '원 shard의 일반 파일·20MB 이하 계약이 필요하다')
    return path


def error_record(error, stage, token=''):
    message = str(error).replace(token, '[소유 토큰 생략]') if token else str(error)
    record = dict(type=type(error).__name__, message=message, stage=stage)
    if getattr(error, 'supported_cleanup_errors', None):
        record['cleanup_errors'] = error.supported_cleanup_errors
    return record


def write_once(path, value, budget):
    budget.check('새 파일 저장 전')
    proc.write_once(path, value)
    proc.require(read_json(path) == value, '새 파일 저장 후 재읽기가 다르다')
    budget.check('새 파일 저장과 재읽기 후')


def append_terminal(directory, event):
    path = Path(directory) / 'terminal.jsonl'
    proc.require(not path.is_symlink(), '종결 원장의 링크를 허용하지 않는다')
    raw = canonical(event) + b'\n'
    proc.require((path.stat().st_size if path.exists() else 0) + len(raw) < MAX_BYTES,
        '종결 원장 20MB 상한을 넘었다')
    with path.open('ab') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


class Budget:
    def __init__(self, seconds, deadline_epoch, *, started=None, reserve=RESERVE):
        self.started = STARTED if started is None else started
        proc.require(math.isfinite(self.started) and self.started <= time.monotonic()
            and 0 <= reserve < seconds, '유효한 부모 시작 시각과 종결 예약이 필요하다')
        self.end = min(self.started + seconds, time.monotonic() + deadline_epoch - time.time())
        self.reserve = reserve
        proc.require(self.remaining() > reserve, '전체 시간창 안에 종결 예약이 들어가지 않는다')

    def remaining(self):
        return self.end - time.monotonic()

    def check(self, stage):
        if self.remaining() <= 0:
            raise TimeoutError('부모 전체 시간창을 넘었다: ' + stage)


@contextmanager
def total_budget(budget):
    proc.require(signal.getitimer(signal.ITIMER_REAL) == (0., 0.), '기존 타이머를 바꾸지 않는다')
    previous = signal.getsignal(signal.SIGALRM)
    def expired(*_):
        raise TimeoutError('준비·검산·게시·정리·출력 전체 시간창이 끝났다')
    primary, cleanup = None, []
    try:
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, max(.001, budget.remaining()))
        yield
    except BaseException as error:
        primary = error
        raise
    finally:
        for stage, action in (('전체 타이머 해제', lambda: signal.setitimer(signal.ITIMER_REAL, 0)),
                              ('전체 타이머 handler 복구', lambda: signal.signal(signal.SIGALRM, previous))):
            try:
                action()
            except BaseException as error:
                cleanup.append(dict(type=type(error).__name__, message=str(error), stage=stage))
        if cleanup:
            owner = primary if primary is not None else OSError('전체 타이머 복구가 불완전하다')
            owner.supported_cleanup_errors = [*getattr(owner, 'supported_cleanup_errors', []), *cleanup]
            if primary is None:
                raise owner


@contextmanager
def termination_guard():
    """생산기 회수 뒤의 검산·저장·출력도 TERM을 종결 거부로 기록한다."""
    handlers, primary, cleanup = {}, None, []
    def interrupted(signum, frame):
        raise InterruptedError('감독 준비 또는 종결 중 신호: ' + str(signum))
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            handlers[sig] = signal.getsignal(sig)
            if handlers[sig] != signal.SIG_IGN:
                signal.signal(sig, interrupted)
        yield
    except BaseException as error:
        primary = error
        raise
    finally:
        for sig, handler in handlers.items():
            try:
                signal.signal(sig, handler)
            except BaseException as error:
                cleanup.append(dict(type=type(error).__name__, message=str(error), stage='외곽 신호 복구'))
        if cleanup:
            owner = primary if primary is not None else OSError('외곽 신호 handler 복구가 불완전하다')
            owner.supported_cleanup_errors = [*getattr(owner, 'supported_cleanup_errors', []), *cleanup]
            if primary is None:
                raise owner


def executable_paths():
    smi = shutil.which('nvidia-smi')
    proc.require(smi is not None, '기존 nvidia-smi 실행파일이 필요하다')
    paths = dict(producer=str(Path(sys.executable).resolve(strict=True)),
        teacher=str(Path('/home/uranus/llama-b11396/llama-server').resolve(strict=True)),
        memory=str(Path(smi).resolve(strict=True)))
    for path in paths.values():
        proc.require(Path(path).is_file() and os.access(path, os.X_OK), '정확한 실행파일이 필요하다')
    return paths


def source_receipt(root=ROOT):
    """원천·모델·전량 quota 재생 없이 현재 코드와 runtime inputs를 고정한다."""
    preflight_path = safe(PREFLIGHT, root)
    preflight = read_json(preflight_path)
    proc.require(preflight.get('status') == 'CPU_REPLAY_COMPLETE_NOT_QUALITY_OR_MODEL_PASS'
        and preflight.get('current_info_exact') is True and preflight.get('unchanged') is True,
        '총괄의 원형 재생 영수증이 필요하다')
    inputs_path = safe(OUTPUT + '/inputs.json', root)
    inputs = read_json(inputs_path)
    proc.require(proc.digest(inputs_path) == preflight['inputs_sha256'] and inputs == preflight['info'],
        '원 생산 입력이 달라졌다')
    originals = dict(inputs['code_sha256'])
    originals[PRODUCER] = inputs['runtime_code_sha256']
    for name, digest in originals.items():
        proc.require(Path(name).parts[0] in ('scripts', 'tinylm') and name.endswith('.py'), '원 코드 경로만 허용한다')
        proc.require(proc.digest(proc.regular(safe(name, root))) == digest, '원 생산 코드가 달라졌다: ' + name)
    runtime_inputs = {PREFLIGHT: proc.digest(preflight_path), OUTPUT + '/inputs.json': proc.digest(inputs_path)}
    for name, wanted in preflight['immutable_before'].items():
        relative = str(Path(name).relative_to(ROOT)) if Path(name).is_absolute() else name
        path = safe(relative, root)
        proc.require(proc.digest(proc.regular(path)) == wanted, '원형 메타데이터가 달라졌다: ' + relative)
        runtime_inputs[relative] = wanted
    pending = [SCRIPT, TEST, PRODUCER, 'scripts/test_p106b_supported_production8h.py',
        'scripts/codex_smoke.py', 'scripts/smoke_module.py', 'scripts/smoke_execution_contract.py',
        'scripts/p106b_native_iq2_worker_window.py', 'scripts/p106b_shards.py', *originals]
    found = {}
    while pending:
        name = pending.pop()
        if name in found:
            continue
        path = proc.regular(safe(name, root))
        found[name] = proc.digest(path)
        tree = ast.parse(path.read_text(encoding='utf-8'))
        package = list(Path(name).parts[:-1])
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.Import):
                modules = [item.name.split('.') for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                prefix = package[:len(package) - node.level + 1] if node.level else []
                base = prefix + (node.module.split('.') if node.module else [])
                modules = [base, *(base + item.name.split('.') for item in node.names if item.name != '*')]
            for module in modules:
                if not module or module[0] not in ('scripts', 'tinylm'):
                    continue
                for end in range(1, len(module) + 1):
                    for candidate in (str(Path(*module[:end])) + '.py', str(Path(*module[:end]) / '__init__.py')):
                        if candidate not in found and safe(candidate, root).is_file():
                            pending.append(candidate)
        proc.require(len(found) < 2000, '소스 의존성 상한을 넘었다')
    executables = executable_paths()
    executable_metadata = {}
    for role, path in executables.items():
        stat = Path(path).stat()
        executable_metadata[role] = dict(path=path, device=stat.st_dev, inode=stat.st_ino,
            bytes=stat.st_size, mtime_ns=stat.st_mtime_ns, sha256=proc.digest(Path(path)))
    material = dict(sources=dict(sorted(found.items())), runtime_inputs=dict(sorted(runtime_inputs.items())),
        executables=executable_metadata, original_producer_sha256=originals[PRODUCER],
        original_inputs_sha256=preflight['inputs_sha256'])
    return dict(**material, source_sha256=identity(material))


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


class OwnedSessions:
    """정확 exe 대조 뒤에만 해당 프로세스의 token을 읽는다."""
    def __init__(self, executables, token, *, query_roles=('memory',)):
        self.executables = {role: str(Path(path).resolve(strict=True)) for role, path in executables.items()}
        self.token = token
        self.query_roles = set(query_roles)
        self.before, self.known, self.queries = {}, {}, {}
        self.controller = None
        self.parent_witness_errors = []
        # 이 단계에서는 어떤 프로세스의 environ도 읽지 않는다.
        for entry in Path('/proc').iterdir():
            if not entry.name.isdecimal():
                continue
            try:
                if os.readlink(entry / 'exe') in self.executables.values():
                    row = proc.proc_stat(int(entry.name))
                    self.before[row['pid']] = row['starttime']
            except (PermissionError, FileNotFoundError, ProcessLookupError):
                continue

    def scan(self):
        if self.controller is None:
            return {}
        found = {}
        for entry in Path('/proc').iterdir():
            if not entry.name.isdecimal():
                continue
            matched = False
            try:
                executable = os.readlink(entry / 'exe')
                roles = [role for role, path in self.executables.items() if path == executable]
                if not roles:
                    continue
                matched = True
                row = proc.proc_stat(int(entry.name))
                pid = row['pid']
                if pid == self.controller['pid'] or pid == os.getpid():
                    continue
                if pid in self.before:
                    proc.require(row['starttime'] == self.before[pid], '기존 PID가 재사용되어 소유로 간주하지 않는다')
                    continue
                if row['starttime'] < self.controller['starttime']:
                    continue
                # 정확한 실행파일 및 이전 PID 보호 이후에만 소유 token 존재를 읽는다.
                payload = (entry / 'environ').read_bytes()
                owned = (OWNER_KEY + '=' + self.token).encode() in payload.split(b'\0')
                del payload
                if not owned:
                    continue
                old = self.known.get(pid)
                proc.require(old is None or old['starttime'] == row['starttime'], '소유 PID가 재사용되었다')
                role = roles[0]
                if (set(roles) & self.query_roles and row['ppid'] == self.controller['pid']
                        and row['pgid'] == self.controller['pgid'] and row['session'] == self.controller['session']):
                    self.queries[pid] = dict(row, role='controller_group_query')
                    continue
                witnessed = old.get('direct_parent_verified', False) if old else row['ppid'] == self.controller['pid']
                if row['ppid'] not in (self.controller['pid'], os.getpid()) and old is None:
                    self.parent_witness_errors.append(dict(pid=pid, starttime=row['starttime'], reason='직접 부모 불일치'))
                if not witnessed and old is None:
                    self.parent_witness_errors.append(dict(pid=pid, starttime=row['starttime'], reason='고아의 최초 부모 미관측'))
                proc.require(row['pgid'] == row['session'] and row['pgid'] > 1
                    and row['pgid'] not in (os.getpgrp(), self.controller['pgid']),
                    '허용된 별도 세션의 그룹이 아니다')
                if row['pid'] != row['pgid']:
                    # leader가 먼저 사라져도 token을 가진 생존 구성원으로 그 세션을 회수한다.
                    row['orphan_group_member'] = True
                row.update(role=role, direct_parent_verified=witnessed, executable=executable)
                self.known[pid] = row
                found[pid] = row
            except PermissionError:
                if matched:
                    raise PermissionError('정확 실행파일의 소유 token을 읽지 못했다')
            except (FileNotFoundError, ProcessLookupError):
                continue
        return found

    def assert_identity(self, saved):
        try:
            row = proc.proc_stat(saved['pid'])
        except (FileNotFoundError, ProcessLookupError):
            return None
        proc.require(row['starttime'] == saved['starttime'] and row['pgid'] == saved['pgid']
            and row['session'] == saved['session'], '종료 직전 PID·그룹·시작 시각이 달라졌다')
        return row

    def live_group_member(self, pgid, session, *, controller_group=False):
        """숫자 PGID 대신 현재 생존하는 정확 exe·token 구성원을 다시 확인한다."""
        executables = set(self.executables.values())
        if controller_group:
            executables.add(self.controller['executable'])
        for entry in Path('/proc').iterdir():
            if not entry.name.isdecimal():
                continue
            matched = False
            try:
                executable = os.readlink(entry / 'exe')
                if executable not in executables:
                    continue
                matched = True
                row = proc.proc_stat(int(entry.name))
                if (row['pgid'] != pgid or row['session'] != session or row['state'] == 'Z'
                        or row['pid'] == os.getpid() or row['starttime'] < self.controller['starttime']):
                    continue
                if row['pid'] in self.before:
                    proc.require(row['starttime'] == self.before[row['pid']], '기존 구성원 PID가 재사용되었다')
                    continue
                old = self.known.get(row['pid']) or self.queries.get(row['pid'])
                if row['pid'] == self.controller['pid']:
                    old = self.controller
                proc.require(old is None or old['starttime'] == row['starttime'], '생존 구성원 PID가 재사용되었다')
                payload = (entry / 'environ').read_bytes()
                owned = (OWNER_KEY + '=' + self.token).encode() in payload.split(b'\0')
                del payload
                if not owned:
                    continue
                proc.require(row['ppid'] in (self.controller['pid'], os.getpid()) or old is not None,
                    '생존 소유 구성원의 부모를 확인하지 못했다')
                return dict(row, executable=executable)
            except PermissionError:
                if matched:
                    raise PermissionError('정확 실행파일의 현재 소유 token을 읽지 못했다')
            except (FileNotFoundError, ProcessLookupError):
                continue
        return None

    def residual(self):
        self.scan()
        return [saved for saved in self.known.values()
                if self.assert_identity(saved) is not None or group_alive(saved['pgid'])]


def group_members(pgid):
    result = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            row = proc.proc_stat(int(entry.name))
            if row['pgid'] == pgid and row['ppid'] == os.getpid():
                result.append(row)
        except (PermissionError, FileNotFoundError, ProcessLookupError):
            continue
    return result


def reap_group(pgid, expires):
    reaped = []
    while True:
        for row in group_members(pgid):
            try:
                current = proc.proc_stat(row['pid'])
                proc.require(current['starttime'] == row['starttime'], '회수 직전 PID가 재사용되었다')
                waited, status = os.waitpid(row['pid'], os.WNOHANG)
                if waited:
                    reaped.append(dict(pid=waited, starttime=row['starttime'], wait_status=status))
            except (ChildProcessError, FileNotFoundError, ProcessLookupError):
                continue
        if not group_alive(pgid):
            return reaped
        if time.monotonic() >= expires:
            raise TimeoutError('소유 그룹의 회수와 소멸을 확인하지 못했다')
        time.sleep(.02)


def cleanup_sessions(tracker, expires):
    tracker.scan()
    rows = []
    for saved in list(tracker.known.values()):
        notes, reaped = [], []
        for sig in (signal.SIGTERM, signal.SIGKILL):
            current = tracker.assert_identity(saved)
            if not group_alive(saved['pgid']):
                break
            anchor = tracker.live_group_member(saved['pgid'], saved['session'])
            if anchor is not None:
                os.killpg(saved['pgid'], sig)
                notes.append(signal.Signals(sig).name)
            else:
                proc.require(current is not None and current['state'] == 'Z',
                    '현재 생존 소유 구성원 검산 없이 과거 PGID에 신호를 보내지 않는다')
            until = min(expires, time.monotonic() + (.15 if sig == signal.SIGTERM else .5))
            try:
                reaped.extend(reap_group(saved['pgid'], until))
                break
            except TimeoutError:
                if sig == signal.SIGKILL:
                    raise
        proc.require(not group_alive(saved['pgid']), '종료 후 소유 별도 세션이 남았다')
        rows.append(dict(pid=saved['pid'], starttime=saved['starttime'], signals=notes,
            reaped=reaped, group_quiescent=True))
    proc.require(not tracker.residual(), '소유 별도 세션의 최종 재검산이 다르다')
    return rows


def child_limits(owner):
    # fork로 상속한 지연 기록 handler가 exec 전 부모 사망 신호를 소비하지 못하게 한다.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_BYTES, MAX_BYTES))
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), '부모 사망 시 생산기 종료 설정 실패')
    if os.getppid() != owner:
        os.kill(os.getpid(), signal.SIGTERM)


def supervise_process(argv, directory, stop_file, executables, budget, *, factory=subprocess.Popen):
    """원 생산기의 실제 0·8·9를 보존하며 별도 세션을 함께 회수한다."""
    token = secrets.token_hex(32)
    tracker = OwnedSessions(executables, token)
    result = dict(schema=SCHEMA, actual_producer_exit=None, original_error=None, cleanup_errors=[],
        forced_cleanup=False, stop_published=False, termination_requested=False, deferred_signals=[],
        owner_token_sha256=hashlib.sha256(token.encode()).hexdigest().upper(),
        external_os_timeout_required=True, process_started=False, launch_state='NOT_STARTED')
    process = None
    previous_subreaper = None
    handlers = {}
    log_path = Path(directory) / 'producer.log'
    stop_at = budget.end - budget.reserve
    term_at = budget.end - budget.reserve / 2
    cleanup_at = budget.end - min(30., budget.reserve / 4)
    def publish(reason):
        if not result['stop_published']:
            write_once(stop_file, dict(schema=SCHEMA, reason=reason, at=datetime.now(timezone.utc).isoformat(),
                owner_token_sha256=result['owner_token_sha256']), budget)
            result['stop_published'] = True
            result['stop_reason'] = reason
    try:
        previous_subreaper = proc.set_subreaper(1)
        for sig in (signal.SIGINT, signal.SIGTERM):
            handlers[sig] = signal.getsignal(sig)
            if handlers[sig] != signal.SIG_IGN:
                signal.signal(sig, lambda signum, frame: result['deferred_signals'].append(int(signum)))
        budget.check('생산기 생성 전')
        proc.require(time.monotonic() < stop_at, '정상 STOP 예약 전에 생산기를 시작할 시간이 부족하다')
        with log_path.open('xb') as log:
            result['launch_state'] = 'PENDING'
            process = factory(list(argv), cwd=ROOT, env=dict(os.environ, **{OWNER_KEY: token}, PYTHONDONTWRITEBYTECODE='1'),
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                preexec_fn=lambda owner=os.getpid(): child_limits(owner))
            result.update(process_started=True, launch_state='OWNED')
            smoke._register_owned(process, start_new_session=True)
            tracker.controller = proc.proc_stat(process.pid)
            proc.require(os.readlink(Path('/proc') / str(process.pid) / 'exe')
                == str(Path(argv[0]).resolve(strict=True)), '생산기 실제 실행파일이 다르다')
            tracker.controller['executable'] = str(Path(argv[0]).resolve(strict=True))
            proc.require(tracker.controller['ppid'] == os.getpid() and tracker.controller['pid'] == tracker.controller['session']
                == tracker.controller['pgid'], '생산기가 감독자의 직접 자식·새 세션이 아니다')
            result['controller_identity'] = tracker.controller
            while True:
                tracker.scan()
                rc = process.poll()
                if rc is not None:
                    result['actual_producer_exit'] = rc
                    residual = tracker.residual()
                    result['residual_at_producer_exit'] = residual
                    assert_controller(process, tracker.controller)
                    result['forced_cleanup'] |= bool(residual) or smoke.owned_group_alive(process)
                    break
                budget.check('생산기와 별도 세션 감독')
                proc.require(log_path.stat().st_size < MAX_BYTES, '생산기 원로그가 20MB 상한에 도달했다')
                now = time.monotonic()
                if result['deferred_signals'] or now >= stop_at:
                    publish('외부 종료 신호' if result['deferred_signals'] else '종결 예약 시작')
                if result['stop_published'] and now >= term_at and not result['termination_requested']:
                    current = proc.proc_stat(process.pid)
                    proc.require(current['starttime'] == tracker.controller['starttime'], 'TERM 전 생산기 PID가 재사용되었다')
                    os.kill(process.pid, signal.SIGTERM)
                    result['termination_requested'] = True
                    result['forced_cleanup'] = True
                if now >= cleanup_at:
                    raise TimeoutError('STOP·TERM 유예 뒤에도 생산기가 닫히지 않았다')
                time.sleep(.03)
    except BaseException as error:
        result['original_error'] = error_record(error, '생산기 감독', token)
        if process is None and result['launch_state'] == 'PENDING':
            result.update(process_started=None, launch_state='UNKNOWN')
    finally:
        if process is not None:
            try:
                assert_controller(process, tracker.controller)
                if process.poll() is None:
                    try:
                        publish('오류 뒤 정상 증분 게시 요청')
                    except BaseException as error:
                        result['cleanup_errors'].append(error_record(error, '오류 뒤 STOP 게시', token))
                    result['forced_cleanup'] = True
                if process.poll() is None or smoke.owned_group_alive(process):
                    result['forced_cleanup'] = True
                notes = stop_controller_group(process, tracker, budget, result)
                result['controller_group_cleanup'] = notes
                record_cleanup_notes(result, notes)
                process.wait(timeout=max(.01, min(1., budget.remaining())))
                result['actual_producer_exit'] = process.returncode
                result['controller_group_reaped'] = reap_group(process.pid, min(budget.end, time.monotonic() + 1.))
                result['controller_group_quiescent'] = not smoke.owned_group_alive(process)
                proc.require(result['controller_group_quiescent'], '생산기 소유 그룹이 남았다')
            except BaseException as error:
                result['cleanup_errors'].append(error_record(error, '생산기 그룹 회수', token))
            try:
                result['owned_session_cleanup'] = cleanup_sessions(tracker, budget.end)
                result['forced_cleanup'] |= any(row['signals'] or row['reaped']
                    for row in result['owned_session_cleanup'])
            except BaseException as error:
                result['cleanup_errors'].append(error_record(error, '별도 세션 회수', token))
            smoke._forget_owned(process)
        result.update(owned_sessions=list(tracker.known.values()), synchronous_queries=list(tracker.queries.values()),
            parent_witness_errors=tracker.parent_witness_errors)
        if previous_subreaper is not None:
            try:
                proc.set_subreaper(previous_subreaper)
                result['subreaper_restored'] = True
            except BaseException as error:
                result['cleanup_errors'].append(error_record(error, 'subreaper 복구', token))
        for sig, handler in handlers.items():
            try:
                signal.signal(sig, handler)
            except BaseException as error:
                result['cleanup_errors'].append(error_record(error, '신호 handler 복구', token))
        try:
            budget.check('소유 프로세스 최종 정리 후')
        except BaseException as error:
            result['cleanup_errors'].append(error_record(error, '최종 정리 시각', token))
    return result


def assert_controller(process, saved):
    proc.require(saved is not None, '생산기 생성 신원을 확보하지 못했다')
    try:
        row = proc.proc_stat(process.pid)
    except (FileNotFoundError, ProcessLookupError):
        return
    proc.require(row['starttime'] == saved['starttime'] and row['ppid'] == saved['ppid']
        and row['pgid'] == saved['pgid'] and row['session'] == saved['session'],
        '생산기 PID·직접 부모·그룹·시작 시각이 달라졌다')


def stop_controller_group(process, tracker, budget, result):
    assert_controller(process, tracker.controller)
    if not smoke.owned_group_alive(process):
        # 신호를 보내는 공용 함수를 이미 소멸한 숫자 PGID에 호출하지 않는다.
        return ['GROUP_QUIESCENT']
    anchor = tracker.live_group_member(process.pid, tracker.controller['session'], controller_group=True)
    proc.require(anchor is not None,
        '현재 생존 소유 구성원 검산 없이 과거 controller PGID를 종료하지 않는다')
    result['controller_cleanup_anchor'] = anchor
    result['forced_cleanup'] = True
    return smoke.stop_process_group(process, min(budget.end, time.monotonic() + 1.), time.monotonic)


def cleanup_note_state(notes):
    if not isinstance(notes, list) or any(not isinstance(note, str) for note in notes):
        return dict(complete=False, forced=False, errors=['정리 반환 형식 미확인'])
    forced = any(note in ('SIGINT_PROCESS_GROUP', 'SIGKILL_PROCESS_GROUP') for note in notes)
    errors = [note for note in notes if note not in
        ('GROUP_QUIESCENT', 'SIGINT_PROCESS_GROUP', 'SIGKILL_PROCESS_GROUP')]
    if 'GROUP_QUIESCENT' not in notes:
        errors.append('GROUP_QUIESCENT 미확인')
    return dict(complete=not errors, forced=forced, errors=errors)


def record_cleanup_notes(result, notes):
    audit = cleanup_note_state(notes)
    result['controller_group_cleanup_audit'] = audit
    result['forced_cleanup'] |= audit['forced']
    if audit['errors']:
        result.setdefault('cleanup_errors', []).append(dict(type='CleanupAuditError',
            stage='공용 그룹 정리 반환 감사', message='공용 정리의 오류·복구 미확인 표지를 보존한다',
            notes=audit['errors']))


def batch_files(directory, budget):
    result = {}
    for path in directory.iterdir():
        budget.check('닫힌 batch 파일 검산')
        result[path.name] = proc.digest(bounded_file(path))
    return result


def closed_manifest(directory, report, key, inputs, expected, budget):
    """내장 명세와 실제 닫힌 명세·정확한 stem·모든 shard를 함께 대조한다."""
    manifest = report.get(key)
    if manifest is None:
        return None
    stem = 'raw' if key == 'raw_manifest' else 'candidates'
    proc.require(isinstance(manifest, dict) and type(manifest.get('rows')) is int and manifest['rows'] > 0
        and manifest.get('shards') and manifest.get('lineage') == inputs,
        '닫힌 원응답·후보 명세와 원 입력 lineage가 필요하다')
    name = stem + '_shards_manifest.json'
    proc.require(read_json(directory / name) == manifest, '디스크 명세와 report 내장 명세가 다르다: ' + key)
    expected.add(name)
    for index, spec in enumerate(manifest['shards']):
        proc.require(spec.get('path') == '%s_%06d.jsonl' % (stem, index), '원응답·후보 shard stem 또는 순서가 다르다')
        bounded_file(directory / spec['path'])
        expected.add(spec['path'])
    budget.check('닫힌 명세 shard 검산 전')
    shards.verify(directory, manifest)
    budget.check('닫힌 명세 shard 검산 후')
    return manifest


def raw_response_index(directory, manifest, budget):
    """원응답은 재생하지 않고 원래 행 번호·구조·사고 참조 SHA만 검산한다."""
    result = {}
    if manifest is None:
        return result
    for spec in manifest['shards']:
        with (directory / spec['path']).open(encoding='utf-8') as stream:
            for line in stream:
                budget.check('원응답 행 구조와 참조 범위 검산')
                row = json.loads(line)
                proc.require(isinstance(row, dict) and finite_json(row), '원응답 JSON 구조 또는 수치가 유효하지 않다')
                number = len(result) + 1
                if 'reply' not in row:
                    proc.require(isinstance(row.get('source_ref'), dict) and isinstance(row.get('structural_stop'), str)
                        and row.get('semantic_truth') == 'PSEUDO_UNVERIFIED', '원응답 또는 원래 structural_stop 행이 필요하다')
                    result[number] = dict(kind='structural_stop')
                    continue
                source = row.get('source', {}).get('meta', {})
                proc.require(isinstance(source.get('source_id'), str) and source['source_id']
                    and row.get('language') in ('ko', 'en') and row.get('task') in ('qa', 'json', 'multiturn')
                    and type(row.get('turn')) is int and row['turn'] > 0
                    and type(row.get('attempt')) is int and row['attempt'] > 0
                    and isinstance(row.get('payload'), dict) and isinstance(row.get('reply'), dict)
                    and isinstance(row.get('parsed'), dict) and 'producer_learner_turn' in row
                    and type(row.get('input_tokens')) is int and row['input_tokens'] >= 0
                    and isinstance(row.get('request_sec'), (int, float)) and row['request_sec'] >= 0,
                    '실제 원응답·payload·parsed·입력·시간 명세가 필요하다')
                thought = row['parsed'].get('teacher_reasoning_content', '')
                result[number] = dict(kind='response', source_id=source['source_id'],
                    language=row['language'], task=row['task'], turn=row['turn'],
                    accepted=isinstance(row['producer_learner_turn'], dict),
                    reasoning_sha256=hashlib.sha256(thought.encode()).hexdigest().upper() if isinstance(thought, str) else None)
    proc.require(len(result) == manifest['rows'], '원응답 명세의 실제 행 범위가 다르다')
    return result


def candidate_raw_refs(meta, profile, raw_rows, referenced):
    refs = meta.get('teacher_reasoning_refs')
    proc.require(isinstance(refs, list) and len(refs) == (3 if profile == 'multiturn' else 1),
        '후보의 원래 turn별 원응답 참조가 필요하다')
    for turn, ref in enumerate(refs, 1):
        number = ref.get('raw_row_1based')
        proc.require(type(number) is int and number in raw_rows and number not in referenced,
            '원응답 참조가 현재 닫힌 batch의 행 범위를 벗어나거나 재사용되었다')
        raw = raw_rows[number]
        proc.require(raw['kind'] == 'response' and raw['accepted'] is True
            and raw['source_id'] == meta.get('source_id') and raw['language'] == meta['language']
            and raw['task'] == profile and raw['turn'] == turn and ref.get('in_student') is False
            and ref.get('sha256') == raw['reasoning_sha256'] and raw['reasoning_sha256'] is not None,
            '후보와 실제 원응답의 source·turn·사고 참조 SHA가 다르다')
        referenced.add(number)


def production_snapshot(destination, budget):
    """기존 닫힌 배치의 파일을 보존하되 원천·토큰 quota를 재생하지 않는다."""
    found, reports = {}, []
    for index, directory in enumerate(sorted(destination.glob('batch_*'))):
        budget.check('기존 배치 검산')
        proc.require(directory.name == 'batch_%06d' % index and not directory.is_symlink(), '기존 배치 순서가 다르다')
        report = read_json(directory / 'report.json')
        reports.append(report)
        for path in directory.iterdir():
            proc.require(path.is_file() and not path.is_symlink(), '기존 배치의 일반 파일만 허용한다')
            bounded_file(path)
            found[str(path.relative_to(destination))] = proc.digest(path)
        for key in ('raw_manifest', 'candidate_manifest'):
            if key in report:
                shards.verify(directory, report[key])
    return dict(files=found, reports=reports, batches=len(reports))


def verify_production(destination, before, inputs, actual_exit, log_path, budget):
    """닫힌 새 batch의 manifest·증분 계수·cursor를 대조한다."""
    for name, wanted in before['files'].items():
        budget.check('이전 배치 불변 감사')
        proc.require(proc.digest(bounded_file(destination / name)) == wanted, '기존 배치가 바뀌었다: ' + name)
    directories = sorted(destination.glob('batch_*'))
    proc.require([path.name for path in directories] == ['batch_%06d' % i for i in range(len(directories))], '새 배치 순서가 다르다')
    count = len(directories) - before['batches']
    proc.require(count in (0, 1), '동시에 다른 생산기가 게시했거나 새 배치 수가 다르다')
    previous = before['reports'][-1]
    if count == 0:
        if actual_exit == 0 and previous.get('token_target_ready') is True:
            return dict(status='ALREADY_TARGET_READY', new_batches=0)
        text = proc.regular(log_path).read_text(encoding='utf-8', errors='replace')
        proc.require(actual_exit == 8 and '[HOLD] ' in text and '[DEFICIT_FINAL]' not in text,
            '닫힌 새 배치 또는 모델 시작 전 HOLD가 필요하다')
        return dict(status='PRE_MODEL_HOLD', new_batches=0)
    directory = directories[-1]
    files_before = batch_files(directory, budget)
    report = read_json(directory / 'report.json')
    proc.require(report.get('input') == inputs and report.get('returncode') == actual_exit
        and report.get('schema') == 'P106B_GEMMA_DEFICIT_BATCH_V1', '새 배치 원형 입력·종료가 다르다')
    proc.require(actual_exit in (0, 8), '생산기 실제 오류는 성공이나 pause로 승격하지 않는다')
    if actual_exit == 0:
        proc.require(report.get('status') == 'PRODUCTION_READY' and report.get('token_target_ready') is True
            and all(report.get(key) and set(report[key]) == set(previous.get(key, {}))
                and not any(report[key].values()) for key in
                ('teacher_deficit_tokens', 'task_deficit_tokens', 'validation_deficit_tokens')), '실제 목표 충족이 확인되지 않았다')
    else:
        proc.require(report.get('status') == 'PRODUCTION_PAUSED' and report.get('error_type') in (None, 'ProductionBudgetPause'),
            '정상 닫힌 PRODUCTION_PAUSED/ProductionBudgetPause만 pause8이다')
    cursor = report.get('cursor')
    proc.require(isinstance(cursor, list) and len(cursor) == 2 and all(type(v) is int and v >= 0 for v in cursor)
        and tuple(cursor) >= tuple(previous['cursor']), '새 cursor가 이전보다 뒤로 갔다')
    totals = dict(previous['nonpadding_tokens'])
    targets = dict(previous.get('assistant_targets', {}))
    row_counts = dict(previous.get('rows', {}))
    family_counts = dict(previous['family_tokens'])
    task_counts = dict(previous['task_tokens'])
    accepted = report.get('accepted_groups')
    proc.require(type(accepted) is int and accepted >= 0, '새 accepted_groups가 유효하지 않다')
    candidate = report.get('candidate_manifest')
    proc.require(bool(candidate) == bool(accepted), 'candidate manifest와 accepted_groups가 다르다')
    proc.require(not accepted or bool(report.get('raw_manifest')), 'accepted 후보가 있으면 실제 원응답 manifest가 필요하다')
    expected_files = {'report.json'}
    manifests = {}
    for key in ('raw_manifest', 'candidate_manifest'):
        manifests[key] = closed_manifest(directory, report, key, inputs, expected_files, budget)
    proc.require(set(files_before) == expected_files, '원응답·후보 명세에 없는 파일 또는 미완 shard가 남았다')
    raw_rows = raw_response_index(directory, manifests['raw_manifest'], budget)
    proc.require(len(raw_rows) >= accepted, 'accepted 후보를 뒷받침할 원응답 행이 부족하다')
    referenced = set()
    if candidate:
        proc.require(candidate['rows'] == accepted, '새 candidate 행 수와 계수가 다르다')
        for spec in candidate['shards']:
            budget.check('새 candidate 증분 계수 검산')
            with (directory / spec['path']).open(encoding='utf-8') as stream:
                for line in stream:
                    meta = json.loads(line)['meta']
                    proc.require(meta.get('visible_source_contract') == VERSION and meta.get('teacher_batch') == directory.name,
                        '새 candidate의 가시 원천·배치 계보가 다르다')
                    lane = meta['source_split'] + ':' + meta['language']
                    proc.require(lane in ('train:ko', 'train:en', 'val:ko', 'val:en'), '새 candidate lane이 유효하지 않다')
                    size, target = meta['processed_x_tokens'], meta['assistant_targets']
                    proc.require(type(size) is int and type(target) is int and 0 < target <= size <= 1024, '새 candidate 토큰 계수가 유효하지 않다')
                    totals[lane] = totals.get(lane, 0) + size
                    targets[lane] = targets.get(lane, 0) + target
                    row_counts[lane] = row_counts.get(lane, 0) + 1
                    family, profile = meta['selection_family'], meta['capability_profile']
                    proc.require(isinstance(family, str) and family and profile in ('qa', 'json', 'multiturn'),
                        '새 candidate의 원 family·task 계수가 유효하지 않다')
                    candidate_raw_refs(meta, profile, raw_rows, referenced)
                    family_key, task_key = lane + ':' + family, lane + ':' + profile
                    family_counts[family_key] = family_counts.get(family_key, 0) + size
                    task_counts[task_key] = task_counts.get(task_key, 0) + size
    proc.require(totals == report['nonpadding_tokens'] and targets == report['assistant_targets']
        and row_counts == report['rows'] and family_counts == report['family_tokens']
        and task_counts == report['task_tokens'], '새 manifest의 실제 증분과 누적 계수가 다르다')
    delta = sum(totals.get('train:' + language, 0) - previous['nonpadding_tokens'].get('train:' + language, 0)
                for language in ('ko', 'en'))
    proc.require(report.get('new_train_x_tokens') == delta, '새 TRAIN 증분이 다르다')
    files_after = batch_files(directory, budget)
    proc.require(files_after == files_before and read_json(directory / 'report.json') == report,
        '원응답·후보 manifest와 shard가 검산 전후에 바뀌었다')
    budget.check('새 batch 게시 최종 검산')
    return dict(status='TARGET_READY' if actual_exit == 0 else 'CLOSED_PRODUCTION_PAUSED',
        new_batches=1, report_sha256=proc.digest(directory / 'report.json'), accepted_groups=accepted,
        cursor=cursor, nonpadding_tokens=totals, new_train_x_tokens=delta,
        manifest_verification=dict(files_before=files_before, files_after=files_after,
            raw_rows=len(raw_rows), candidate_rows=accepted, referenced_raw_rows=len(referenced),
            disk_manifests_equal_reports=True, exact_closed_file_set=True),
        semantic_quality='NOT_REVIEWED', formal_train_ready=False)


def validate_args(args, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    proc.require(sys.platform == 'linux' and args.execute and not args.check_only, '명시적인 Linux 실행만 허용한다')
    proc.require(type(args.max_wall_sec) is int and 300 <= args.max_wall_sec <= 7200, '전체 시간창은 300..7200초다')
    deadline = datetime.fromisoformat(str(args.deadline_utc).replace('Z', '+00:00'))
    proc.require(deadline.tzinfo is not None and now < deadline <= PRODUCTION_STOP < AUTHORIZED_STOP,
        '생산 마감은 미래이면서 2026-10-25 12:40 KST 이하여야 한다')
    proc.require((deadline - now).total_seconds() >= args.max_wall_sec, '전체 시간창과 120초 종결 예약이 마감 전에 들어가야 한다')
    proc.require(re.fullmatch(re.escape(PREFIX) + r'[a-z0-9][a-z0-9_]{0,47}', args.tag or '') is not None,
        '새 감독 namespace 태그가 필요하다')
    proc.require(re.fullmatch(r'[0-9A-F]{64}', args.source_sha256 or '') is not None, '현재 source SHA256이 필요하다')
    return deadline


def disposition(result):
    notes = cleanup_note_state(result.get('controller_group_cleanup'))
    proc.require(result.get('process_started') is True and result.get('actual_producer_exit') in (0, 8)
        and result.get('original_error') is None and not result.get('cleanup_errors')
        and not result.get('forced_cleanup') and not result.get('parent_witness_errors')
        and result.get('subreaper_restored') is True and not result.get('audit_errors')
        and result.get('source_inputs_unchanged') is True and notes['complete'] and not notes['forced'],
        '생산기 실제 종료 또는 소유 정리가 불완전하다')
    verification = result.get('production_verification', {})
    status, code = verification.get('status'), result['actual_producer_exit']
    proc.require((code == 0 and status in ('TARGET_READY', 'ALREADY_TARGET_READY'))
        or (code == 8 and status in ('CLOSED_PRODUCTION_PAUSED', 'PRE_MODEL_HOLD')),
        '실제 종료와 게시 상태의 대응이 다르다')
    proc.require(not (status == 'PRE_MODEL_HOLD'
        and any(row['role'] == 'teacher' for row in result.get('owned_sessions', []))),
        '교사 입장 뒤의 HOLD를 모델 시작 전 HOLD로 승격하지 않는다')
    return status, code


def run(args, budget):
    receipt = source_receipt()
    budget.check('원형 소스와 입력 검산 후')
    proc.require(receipt['source_sha256'] == args.source_sha256, '현재 소스·runtime inputs 영수증이 다르다')
    target = safe('test_result/evidence/' + args.tag)
    stop_file = safe(OUTPUT + '/STOP_CODEX_SUPERVISOR_' + args.tag)
    proc.require(not target.exists() and not stop_file.exists(), '기존 감독 namespace와 STOP은 보존한다')
    destination = safe(OUTPUT)
    preflight = read_json(safe(PREFLIGHT))
    inputs = read_json(destination / 'inputs.json')
    before = production_snapshot(destination, budget)
    proc.require(before['batches'] == preflight['closed_batches'] and before['reports'][-1]['cursor'] == preflight['cursor']
        and before['reports'][-1]['nonpadding_tokens'] == preflight['nonpadding_tokens'], '원형 배치·cursor·계수가 달라졌다')
    target.mkdir()
    args._owned_target = target
    write_once(target / 'admission.json', dict(schema=SCHEMA, sources=receipt, tag=args.tag,
        max_wall_sec=args.max_wall_sec, deadline_utc=args.deadline_utc, reserve_seconds=RESERVE,
        started_monotonic=budget.started, stop_file=str(stop_file), source_replay='NOT_RUN_BY_SUPERVISOR',
        external_os_timeout_required=True, supervisor_sigkill_descendant_guarantee=False), budget)
    child_cap = max(60, int(budget.remaining()) - RESERVE // 2)
    command = [sys.executable, '-B', '-X', 'utf8', str(safe(PRODUCER)), '--mode', 'resume',
        '--max-wall-sec', str(child_cap), '--deadline-utc', args.deadline_utc,
        '--stop-file', str(stop_file), '--execute']
    executables = {role: metadata['path'] for role, metadata in receipt['executables'].items() if role != 'producer'}
    result = supervise_process(command, target, stop_file, executables, budget)
    args._runtime_result = result
    result.update(tag=args.tag, source_sha256=receipt['source_sha256'], checkpoint_writes=0,
        quality_claim=False, formal_train_ready=False, student_training='NOT_RUN')
    code = 9
    audit_errors = result.setdefault('audit_errors', [])
    try:
        result['production_verification'] = verify_production(destination, before, inputs,
            result['actual_producer_exit'], target / 'producer.log', budget)
    except BaseException as error:
        audit_errors.append(error_record(error, '생산 게시 감사'))
    try:
        proc.require(source_receipt() == receipt, '종결 시 원 코드·입력·pilot이 바뀌었다')
        result['source_inputs_unchanged'] = True
        budget.check('최종 원형 감사 후')
    except BaseException as error:
        audit_errors.append(error_record(error, '원형 최종 감사'))
    try:
        result['status'], code = disposition(result)
    except BaseException as error:
        if result['original_error'] is None:
            result['original_error'] = error_record(error, '생산 게시와 원형 최종 감사')
        else:
            result.setdefault('audit_errors', []).append(error_record(error, '생산 게시와 원형 최종 감사'))
        result['status'] = 'ERROR_PARTIAL_PRESERVED'
    result.update(intended_supervisor_exit=code, actual_supervisor_exit='PENDING_EXTERNAL_CALLER',
        elapsed_seconds=time.monotonic() - budget.started)
    try:
        write_once(target / 'supervisor_receipt.json', result, budget)
        print(json.dumps(dict(schema=SCHEMA, tag=args.tag, status=result['status'],
            actual_producer_exit=result['actual_producer_exit'], intended_supervisor_exit=code,
            forced_cleanup=result['forced_cleanup'], external_os_timeout_required=True,
            actual_supervisor_exit='PENDING_EXTERNAL_CALLER', output=str(target)), ensure_ascii=False), flush=True)
        budget.check('감독 stdout 후')
        append_terminal(target, dict(event='FINAL_DISPOSITION' if code in (0, 8) else 'TERMINAL_VETO',
            intended_supervisor_exit=code, actual_producer_exit=result['actual_producer_exit'],
            receipt_sha256=identity(result), at=datetime.now(timezone.utc).isoformat()))
        budget.check('감독 종결 표지 후')
    except BaseException as error:
        append_terminal(target, dict(event='TERMINAL_VETO', intended_supervisor_exit=9,
            original_error=result['original_error'], cleanup_errors=result['cleanup_errors'],
            terminal_error=error_record(error, '감독 저장 또는 출력')))
        code = 9
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check-only', action='store_true')
    modes.add_argument('--execute', action='store_true')
    parser.add_argument('--tag')
    parser.add_argument('--source-sha256')
    parser.add_argument('--max-wall-sec', type=int)
    parser.add_argument('--deadline-utc')
    args = parser.parse_args(argv)
    try:
        if args.check_only:
            receipt = source_receipt()
            print(json.dumps(dict(schema=SCHEMA, evidence='STATIC_ONLY_NOT_PRODUCTION_OR_QUALITY_PASS',
                source_sha256=receipt['source_sha256'], source_count=len(receipt['sources']),
                original_producer_sha256=receipt['original_producer_sha256'],
                original_inputs_sha256=receipt['original_inputs_sha256'], prefix=PREFIX,
                production_stop=PRODUCTION_STOP.isoformat(), authorized_stop=AUTHORIZED_STOP.isoformat(),
                max_wall_sec=7200, reserve_seconds=RESERVE, max_file_bytes=MAX_BYTES,
                torch_imported='torch' in sys.modules, model_calls=0, gpu_calls=0,
                source_replay_calls=0, files_written=0, external_os_timeout_required=True), ensure_ascii=False), flush=True)
            return 0
        with termination_guard():
            deadline = validate_args(args)
            budget = Budget(args.max_wall_sec, deadline.timestamp())
            with total_budget(budget):
                code = run(args, budget)
            budget.check('전체 타이머 복구 후 반환 직전')
        return code
    except BaseException as error:
        event = dict(event='TERMINAL_VETO', intended_supervisor_exit=9, error=error_record(error, '진입 또는 전체 시간창'))
        if getattr(args, '_runtime_result', None) is not None:
            event.update(actual_producer_exit=args._runtime_result.get('actual_producer_exit'),
                original_error=args._runtime_result.get('original_error'),
                cleanup_errors=args._runtime_result.get('cleanup_errors', []))
        try:
            if getattr(args, '_owned_target', None) is not None:
                append_terminal(args._owned_target, event)
        except BaseException as extra:
            event['terminal_storage_error'] = error_record(extra, '종결 거부 저장')
        print(json.dumps(event, ensure_ascii=False), file=sys.stderr, flush=True)
        return 9


if __name__ == '__main__':
    raise SystemExit(main())
