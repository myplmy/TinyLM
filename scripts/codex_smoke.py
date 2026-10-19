#!/usr/bin/env python3
"""Reusable, explicitly authorized POSIX smoke runner with isolated outputs.

``check`` only parses/pins source code. ``contract`` calls the unchanged field
checker against this session's isolated JSON logs. Only ``full --execute`` can
start canonical children; it additionally needs a future aware UTC deadline.
This module never imports a model or changes a canonical training argument.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.smoke_module import parse_smoke_module
from scripts.smoke_execution_contract import (
    CANONICAL_SOURCE, CONTRACT_MODULE, NEW_DRIVER, NEW_PROFILE_ID, NEW_SCHEMA,
    adapt_actions, destinations, execution_source_pins,
)

MAX_LOG_BYTES = 20_000_000
MAX_WALL_SECONDS = 1800
DEFAULT_WALL_SECONDS = 1200
POLL_SECONDS = .2
CLEANUP_RESERVE_SECONDS = 5.
# Registry paths now follow TINYLM_DIR; temporary-root regressions cover the
# actual registration call without touching source-checkout records.
FULL_EXECUTION_DEPENDENCY_HOLD = None
SLEEP_CHUNK_SECONDS = 1.
_OWNED_GROUPS = {}
ENVIRONMENT_KEYS = (
    'TINYLM_DIR', 'TINYLM_HF', 'HF_HOME', 'TL_OUTDIR', 'TL_LOGNAME', 'TL_STAMP',
    'TL_NOPAUSE', 'TL_WANDB_AUTO', 'WANDB_MODE', 'WANDB_DISABLED',
    'HF_HUB_OFFLINE', 'HF_DATASETS_OFFLINE', 'TRANSFORMERS_OFFLINE',
    'HF_HUB_DISABLE_TELEMETRY', 'DO_NOT_TRACK', 'PYTHONIOENCODING',
    'PYTHONUNBUFFERED', 'PYTHONDONTWRITEBYTECODE', 'TZ',
    'CUDA_VISIBLE_DEVICES', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
    'OPENBLAS_NUM_THREADS',
)


class BudgetExpired(TimeoutError):
    """The explicit wall/deadline budget has been consumed."""


class SafetyError(ValueError):
    """An isolated path, raw-log bound, or output identity was violated."""


def utcnow():
    return datetime.now(timezone.utc)


def aware_deadline(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (AttributeError, ValueError) as exc:
        raise argparse.ArgumentTypeError('an ISO timezone-aware deadline is required') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError('deadline must include its timezone')
    return parsed.astimezone(timezone.utc)


def wall_seconds(value):
    try:
        seconds = float(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError('finite positive wall seconds required') from exc
    if not math.isfinite(seconds) or not 0 < seconds <= MAX_WALL_SECONDS:
        raise argparse.ArgumentTypeError('wall seconds must be >0 and <=1800')
    return seconds


def safe_path(root, path):
    """Reject traversal and links before opening or enumerating a path."""
    root = Path(root).absolute()
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    if '..' in path.parts or '\\' in str(path):
        raise SafetyError('parent/backslash path components are forbidden')
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SafetyError('smoke path leaves the repository') from exc
    items = [root]
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        items.append(current)
    for item in items:
        if item.is_symlink():
            raise SafetyError('linked smoke path is forbidden: ' + str(item))
    return path


def remaining(expires, clock):
    value = expires - clock()
    if value <= 0:
        raise BudgetExpired('explicit smoke wall/deadline budget exhausted')
    return value


def digest(path, *, expires=None, clock=None, guard=None):
    """Stream bytes without following the final link; never load a tensor."""
    clock = time.monotonic if clock is None else clock
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise SafetyError('regular nonlinked smoke file required')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    value = hashlib.sha256()
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        while True:
            if guard is not None:
                guard()
            if expires is not None:
                remaining(expires, clock)
            block = stream.read(1024 * 1024)
            if not block:
                break
            value.update(block)
    return value.hexdigest().upper()


def original_snapshot(root=ROOT, *, expires=None, clock=None, guard=None):
    """Only pre-existing SYNTHETIC smoke files, never arbitrary runs/data."""
    root = Path(root).absolute()
    clock = time.monotonic if clock is None else clock
    if guard is not None:
        guard()
    if expires is not None:
        remaining(expires, clock)
    paths = []
    for directory, pattern in (('runs/ckpt', 'tiny_synthetic_*.pt'),
                               ('runs/logs', 'tiny_synthetic_*.json')):
        if guard is not None:
            guard()
        base = safe_path(root, root / directory)
        if base.exists():
            paths.extend(base.glob(pattern))
    cache = safe_path(root, root / 'data_cache')
    if cache.exists():
        for base in sorted(cache.glob('synthetic_*')):
            if guard is not None:
                guard()
            safe_path(root, base)
            if not base.is_dir():
                raise SafetyError('synthetic cache namespace must be a directory')
            for name in ('train.bin', 'val.bin', 'meta.json'):
                path = safe_path(root, base / name)
                if path.exists():
                    paths.append(path)
    result = {}
    for path in sorted(paths):
        safe_path(root, path)
        result[path.relative_to(root).as_posix()] = digest(
            path, expires=expires, clock=clock, guard=guard)
    if expires is not None:
        remaining(expires, clock)
    return result


def environment(runtime, log_name, stamp, environ=None):
    env = dict(os.environ if environ is None else environ)
    env.update(
        TINYLM_DIR=str(runtime), TINYLM_HF=str(runtime / 'HF'),
        HF_HOME=str(runtime / 'HF'), TL_OUTDIR='smoketest_logs',
        TL_LOGNAME=log_name, TL_STAMP=stamp, TL_NOPAUSE='1',
        TL_WANDB_AUTO='0', WANDB_MODE='disabled', WANDB_DISABLED='true',
        HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
        HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1',
        PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1',
        PYTHONDONTWRITEBYTECODE='1', TZ='Asia/Seoul',
    )
    return env


def public_environment(env):
    return {key: env[key] for key in ENVIRONMENT_KEYS if key in env}


def build_plan(root, session_id, *, guard=None):
    root = Path(root).absolute()
    if guard is not None:
        guard()
    target = destinations(root, session_id)
    source = safe_path(root, root / CANONICAL_SOURCE)
    actions = parse_smoke_module(source, log_name=target['log_name'])
    if guard is not None:
        guard()
    changed, edits = adapt_actions(
        actions, driver=NEW_DRIVER,
        contract_args=['--mode', 'contract', '--session-id', session_id])
    if len(actions) != len(changed):
        raise SafetyError('canonical action count changed')
    for original, actual in zip(actions, changed):
        if (actual.kind not in ('run', 'sleep') or original.kind != actual.kind
                or original.line != actual.line or original.seconds != actual.seconds):
            raise SafetyError('canonical action topology changed')
    return target, actions, changed, edits


def metadata(root, session_id, target, actions, changed, edits):
    child = [a for a in actions if a.kind == 'run' and '--' in a.argv]
    return dict(
        schema=NEW_SCHEMA, profile_id=NEW_PROFILE_ID, session_id=session_id,
        source=CANONICAL_SOURCE, source_sha256=None, driver=NEW_DRIVER,
        driver_sha256=None, contract_module_sha256=None,
        runtime=target['runtime'].relative_to(root).as_posix(),
        log_name=target['log_name'], raw_log_directory='smoketest_logs',
        log=None, log_sha256=None, action_count=len(actions),
        child_count=len(child),
        training_count=sum('run100m.py' in a.argv for a in child),
        action_manifest=[asdict(a) for a in changed], substitutions=edits,
        interpretation='same canonical dynamic arms; two explicit Codex adaptations',
    )


def bind_pins(report, pins):
    report.update(source_sha256=pins[CANONICAL_SOURCE],
                  driver_sha256=pins[NEW_DRIVER],
                  contract_module_sha256=pins[CONTRACT_MODULE])


def raw_logs(root, log_name):
    directory = safe_path(root, Path(root) / 'smoketest_logs')
    if not directory.exists():
        return []
    result = sorted(directory.glob('*_' + log_name + '_*.txt'))
    for path in result:
        safe_path(root, path)
        if not path.is_file():
            raise SafetyError('smoke raw log must be a regular file')
    return result


def monitor_logs(root, log_name):
    paths = raw_logs(root, log_name)
    if len(paths) > 1:
        raise SafetyError('multiple raw logs for this exclusive session')
    if paths and paths[0].stat().st_size >= MAX_LOG_BYTES:
        raise SafetyError('raw log reached20MB; preserved without truncation')
    return paths


def _safe_pgid(process):
    pgid = process.pid
    if (type(pgid) is not int or pgid <= 1 or pgid == os.getpid()
            or pgid == os.getpgrp()):
        raise SafetyError('refusing unsafe/self/current process-group identifier')
    return pgid


def _register_owned(process, *, start_new_session):
    """Only a result of this runner's new-session Popen may be supervised."""
    if start_new_session is not True:
        raise SafetyError('owned smoke process requires start_new_session=True')
    pgid = _safe_pgid(process)
    if pgid in _OWNED_GROUPS and _OWNED_GROUPS[pgid] is not process:
        raise SafetyError('owned process-group identity collision')
    _OWNED_GROUPS[pgid] = process
    return pgid


def _owned_pgid(process):
    pgid = _safe_pgid(process)
    if _OWNED_GROUPS.get(pgid) is not process:
        raise SafetyError('unregistered process group must never be signalled')
    return pgid


def _forget_owned(process):
    for pgid, owner in list(_OWNED_GROUPS.items()):
        if owner is process:
            del _OWNED_GROUPS[pgid]


def owned_group_alive(process):
    """Signal zero is a quiescence observation, never a success inference."""
    pgid = _owned_pgid(process)
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_process_group(process, expires, clock):
    """Best-effort <=5s owned-only teardown, resistant to repeated interrupts.

    SIGINT/SIGTERM are blocked only on this thread during cleanup. Prior masks
    and handlers are preserved; pending/delivered interrupts are reported, not
    used as permission to skip SIGKILL/reaping. Numeric PGID ownership follows
    the new-session Popen registration, not an assertion about PID reuse.
    """
    pgid = _owned_pgid(process)  # Guard before ANY probe, signal or mask change.
    notes = []
    end = min(expires, clock() + CLEANUP_RESERVE_SECONDS)
    interrupts = {signal.SIGINT, signal.SIGTERM}
    old_mask = None

    def interrupted(stage):
        notes.append('INTERRUPT_DURING_CLEANUP:' + stage)

    def send(sig):
        # Bounded retries also cover mocked KeyboardInterrupt despite masking.
        for _ in range(2):
            try:
                _owned_pgid(process)
                os.killpg(pgid, sig)
                notes.append(('SIGINT' if sig == signal.SIGINT else 'SIGKILL')
                             + '_PROCESS_GROUP')
                return True
            except KeyboardInterrupt:
                interrupted('SIGNAL_' + str(int(sig)))
            except ProcessLookupError:
                notes.append('GROUP_QUIESCENT')
                return False
            except Exception as exc:
                notes.append('CLEANUP_ERROR:' + type(exc).__name__)
                return None
        return None

    try:
        try:
            # Query first: even an interrupt raised just AFTER SIG_BLOCK has
            # taken effect must leave a known prior mask for the finally arm.
            old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
            signal.pthread_sigmask(signal.SIG_BLOCK, interrupts)
        except KeyboardInterrupt:
            interrupted('MASK_BLOCK')
        except Exception as exc:
            notes.append('MASK_BLOCK_ERROR:' + type(exc).__name__)
        if send(signal.SIGINT) is False:
            return notes
        try:
            left = end - clock()
            if process.poll() is None and left > 0:
                process.wait(timeout=min(.5, left))
        except KeyboardInterrupt:
            interrupted('GRACE_WAIT')
        except subprocess.TimeoutExpired:
            pass
        except Exception as exc:
            notes.append('CLEANUP_ERROR:' + type(exc).__name__)
        # A leader can have exited while its inner child remains alive.
        if send(signal.SIGKILL) is False:
            return notes
        try:
            left = end - clock()
            if process.poll() is None and left > 0:
                process.wait(timeout=left)
        except KeyboardInterrupt:
            interrupted('REAP_WAIT')
        except subprocess.TimeoutExpired:
            notes.append('CLEANUP_ERROR:LEADER_REAP_TIMEOUT')
        except Exception as exc:
            notes.append('CLEANUP_ERROR:' + type(exc).__name__)
        for _ in range(100):
            try:
                if not owned_group_alive(process):
                    if 'GROUP_QUIESCENT' not in notes:
                        notes.append('GROUP_QUIESCENT')
                    break
            except KeyboardInterrupt:
                interrupted('QUIESCENCE_PROBE')
            except Exception as exc:
                notes.append('CLEANUP_ERROR:' + type(exc).__name__)
                break
            left = end - clock()
            if left <= 0:
                break
            try:
                time.sleep(min(.02, left))
            except KeyboardInterrupt:
                interrupted('QUIESCENCE_WAIT')
        if 'GROUP_QUIESCENT' not in notes:
            notes.append('CLEANUP_ERROR:GROUP_STATE_UNRESOLVED')
    finally:
        if old_mask is not None:
            try:
                for sig in sorted(signal.sigpending() & interrupts, key=int):
                    notes.append('PENDING_INTERRUPT:' + str(int(sig)))
            except KeyboardInterrupt:
                interrupted('PENDING_INSPECTION')
            except Exception as exc:
                notes.append('MASK_PENDING_ERROR:' + type(exc).__name__)
            restored = False
            for _ in range(3):
                try:
                    signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
                    restored = True
                    break
                except KeyboardInterrupt:
                    # Python can deliver a pending interrupt AFTER restoring
                    # the mask. Catch it here so the started receipt survives.
                    interrupted('MASK_RESTORE_DELIVERY')
                except Exception as exc:
                    notes.append('MASK_RESTORE_ERROR:' + type(exc).__name__)
                    break
            if not restored:
                notes.append('MASK_RESTORE_ERROR:UNCONFIRMED')
    return notes


def run_child(argv, *, root, env, work_expires, expires, clock, monitor,
              process_factory=None, state_sink=None):
    """Inherit full runlog console output, close stdin, supervise one group."""
    factory = subprocess.Popen if process_factory is None else process_factory
    began = clock()
    result = {} if state_sink is None else state_sink
    result.update(status='NOT_RUN', returncode=None, duration_sec=0., error=None,
                  termination=[], process_started=False, unsafe_process_state=False,
                  interrupted_during_cleanup=False, cleanup_duration_sec=0.,
                  launch_state='NOT_STARTED', creation_attempted=False,
                  deferred_launch_signals=[], launch_handler_errors=[],
                  launch_restore_interrupted=False,
                  preserved_ignored_launch_signals=[])
    process = None
    try:
        remaining(work_expires, clock)
        monitor()
        # Defer only parent handler delivery, NOT the OS signal mask. A blocked
        # mask here would be inherited by the child across Popen/exec.
        handlers = {}
        restore_interrupted = False

        def defer(signum, frame):
            result['deferred_launch_signals'].append(int(signum))

        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                old_handler = signal.getsignal(sig)
                if old_handler == signal.SIG_IGN:
                    # POSIX exec preserves ignored dispositions but resets
                    # caught handlers. Do not change child semantics merely
                    # to defer a signal the caller already chose to ignore.
                    result['preserved_ignored_launch_signals'].append(int(sig))
                    continue
                handlers[sig] = old_handler
                signal.signal(sig, defer)
            result.update(creation_attempted=True, launch_state='PENDING')
            try:
                process = factory(list(argv), cwd=root, env=env,
                                  stdin=subprocess.DEVNULL, start_new_session=True)
            except BaseException:
                # A constructor/factory can spawn and then raise before handing
                # back a process object. No PID is invented and no "no child"
                # assertion or safe continuation is made in that situation.
                result.update(launch_state='UNKNOWN', process_started=None,
                              unsafe_process_state=True)
                raise
            result.update(process_started=True, status='RUNNING')
            _register_owned(process, start_new_session=True)
            result['launch_state'] = 'OWNED'
        except BaseException:
            if result['creation_attempted'] and result['launch_state'] != 'OWNED':
                result.update(launch_state='UNKNOWN', unsafe_process_state=True)
                if process is None:
                    result['process_started'] = None
            raise
        finally:
            # The factory call has ended now, so masking this parent thread
            # while restoring handlers cannot be inherited by that child.
            # Keep both old handlers from raising between restoration steps.
            restore_mask = None
            try:
                restore_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
                signal.pthread_sigmask(signal.SIG_BLOCK,
                                       {signal.SIGINT, signal.SIGTERM})
            except KeyboardInterrupt:
                restore_interrupted = True
                result['launch_restore_interrupted'] = True
            except Exception as exc:
                result['launch_handler_errors'].append('restore-mask:' + type(exc).__name__)
            for sig, old_handler in reversed(list(handlers.items())):
                restored = False
                for _ in range(3):
                    try:
                        signal.signal(sig, old_handler)
                        restored = True
                        break
                    except KeyboardInterrupt:
                        restore_interrupted = True
                        result['launch_restore_interrupted'] = True
                    except Exception as exc:
                        result['launch_handler_errors'].append(type(exc).__name__ + ': ' + str(exc))
                        break
                if not restored:
                    result['launch_handler_errors'].append('handler restore unconfirmed:' + str(int(sig)))
            if restore_mask is not None:
                try:
                    result['deferred_launch_signals'].extend(
                        int(sig) for sig in sorted(
                            signal.sigpending() & {signal.SIGINT, signal.SIGTERM}, key=int))
                except KeyboardInterrupt:
                    restore_interrupted = True
                    result['launch_restore_interrupted'] = True
                except Exception as exc:
                    result['launch_handler_errors'].append('restore-pending:' + type(exc).__name__)
                restored = False
                for _ in range(3):
                    try:
                        signal.pthread_sigmask(signal.SIG_SETMASK, restore_mask)
                        restored = True
                        break
                    except KeyboardInterrupt:
                        restore_interrupted = True
                        result['launch_restore_interrupted'] = True
                    except Exception as exc:
                        result['launch_handler_errors'].append('restore-mask:' + type(exc).__name__)
                        break
                if not restored:
                    result['launch_handler_errors'].append('launch mask restore unconfirmed')
            if result['launch_handler_errors']:
                result['unsafe_process_state'] = True
        if result['deferred_launch_signals'] or restore_interrupted:
            raise KeyboardInterrupt('deferred parent interruption after launch ownership')
        if result['launch_handler_errors']:
            raise SafetyError('parent launch handlers could not be restored')
        while True:
            monitor()
            try:
                result['returncode'] = process.wait(
                    timeout=min(POLL_SECONDS, remaining(work_expires, clock)))
                if result['returncode'] in (
                        130, 143, -int(signal.SIGINT), -int(signal.SIGTERM)):
                    result.update(status='INTERRUPTED', error='interrupt-like leader returncode')
                elif result['returncode'] == 0 and owned_group_alive(process):
                    result.update(status='TOOL_ERROR', error='leader exited0 with surviving owned group')
                else:
                    result['status'] = 'COMPLETE'
                break
            except subprocess.TimeoutExpired:
                continue
    except BudgetExpired as exc:
        result.update(status='TIMED_OUT', error=str(exc))
    except KeyboardInterrupt:
        result.update(status='INTERRUPTED', error='KeyboardInterrupt/SIGTERM')
    except Exception as exc:
        result.update(status='TOOL_ERROR', error=type(exc).__name__ + ': ' + str(exc))
        if result.get('deferred_launch_signals') or result.get('launch_restore_interrupted'):
            result['status'] = 'INTERRUPTED'
    finally:
        if process is not None and (result['status'] != 'COMPLETE'
                                    or result['returncode'] != 0):
            cleanup_end = min(expires, clock() + CLEANUP_RESERVE_SECONDS)
            cleanup_started = clock()
            try:
                result['termination'] = stop_process_group(process, cleanup_end, clock)
            except KeyboardInterrupt:
                result['interrupted_during_cleanup'] = True
                result['termination'].append('INTERRUPT_DURING_CLEANUP:UNEXPECTED_ESCAPE')
                # Defensive fallback: helper replacement or a signal delivered
                # at its return boundary must not erase the original receipt.
                try:
                    result['termination'].extend(stop_process_group(process, cleanup_end, clock))
                except BaseException as exc:
                    result['termination'].append('CLEANUP_ERROR:' + type(exc).__name__)
            except Exception as exc:
                result['termination'].append('CLEANUP_ERROR:' + type(exc).__name__)
            try:
                result['returncode'] = process.poll()
            except KeyboardInterrupt:
                result['interrupted_during_cleanup'] = True
                result['termination'].append('INTERRUPT_DURING_CLEANUP:FINAL_POLL')
            except Exception as exc:
                result['termination'].append('POLL_ERROR:' + type(exc).__name__)
            result['unsafe_process_state'] |= (
                result['returncode'] is None
                or 'GROUP_QUIESCENT' not in result['termination']
                or any('ERROR:' in note for note in result['termination']))
            result['interrupted_during_cleanup'] |= any(
                note.startswith(('INTERRUPT_DURING_CLEANUP:', 'PENDING_INTERRUPT:'))
                for note in result['termination'])
            if (result['interrupted_during_cleanup']
                    and result['status'] not in ('INTERRUPTED', 'TIMED_OUT')):
                result.update(status='INTERRUPTED', error='interruption during owned cleanup')
            result['cleanup_duration_sec'] = max(0., clock() - cleanup_started)
        if process is not None:
            _forget_owned(process)
        result['duration_sec'] = max(0., clock() - began)
    return result


def bounded_pause(seconds, *, work_expires, clock, guard, sleep):
    """Preserve the canonical pause normally, with live UTC/budget checks."""
    if not math.isfinite(seconds) or seconds < 0:
        raise SafetyError('canonical pause must be finite and nonnegative')
    guard()
    left_pause = float(seconds)
    while left_pause > 0:
        guard()
        chunk = min(SLEEP_CHUNK_SECONDS, left_pause, remaining(work_expires, clock))
        sleep(chunk)
        left_pause -= chunk
    guard()


def write_report(root, path, data):
    path = safe_path(root, path)
    payload = (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
               + '\n').encode('utf-8')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags, 0o600), 'wb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def contract(root, session_id, environ=None):
    """Only the log directory changes; the field checker/predicates do not."""
    env = os.environ if environ is None else environ
    target = destinations(root, session_id)
    runtime = safe_path(root, target['runtime'])
    if env.get('TINYLM_DIR') != str(runtime):
        raise SafetyError('field checker requires the exact isolated TINYLM_DIR')
    logs = safe_path(root, runtime / 'runs/logs')
    if not logs.is_dir():
        raise SafetyError('isolated field JSON directory is missing')
    for path in logs.glob('tiny_*sm_*.json'):
        safe_path(root, path)
        if not path.is_file():
            raise SafetyError('nonregular isolated field JSON')
    from scripts import check_smoke
    old_logs, old_argv = check_smoke.LOGS, sys.argv
    try:
        check_smoke.LOGS = logs
        sys.argv = [NEW_DRIVER]
        return check_smoke.main()
    finally:
        check_smoke.LOGS, sys.argv = old_logs, old_argv


def check(root, session_id, max_wall_sec):
    target, actions, changed, edits = build_plan(root, session_id)
    report = metadata(root, session_id, target, actions, changed, edits)
    pins = execution_source_pins(root)
    bind_pins(report, pins)
    report.update(mode='check', execute=False, source_pins=pins,
                  max_wall_sec=max_wall_sec, model_execution='NOT_RUN',
                  full_execution_ready=not bool(FULL_EXECUTION_DEPENDENCY_HOLD),
                  full_execution_dependency_hold=FULL_EXECUTION_DEPENDENCY_HOLD)
    print('[CODEX_SMOKE_CHECK] ' + json.dumps(report, ensure_ascii=False), flush=True)
    return 0


def full(root, session_id, deadline, max_wall_sec, *, clock=None, now=None,
         sleep=None, process_factory=None):
    """Execute once; retain a negative receipt for bounded partial execution."""
    root = Path(root).absolute()
    clock = time.monotonic if clock is None else clock
    now = utcnow if now is None else now
    sleep = time.sleep if sleep is None else sleep
    began = clock()  # Includes planning, path checks and namespace reservation.
    max_wall_sec = wall_seconds(max_wall_sec)
    if deadline.tzinfo is None or deadline.utcoffset() is None:
        raise ValueError('full execution requires an aware deadline')
    if FULL_EXECUTION_DEPENDENCY_HOLD:
        print('[CODEX_SMOKE_HOLD] ' + FULL_EXECUTION_DEPENDENCY_HOLD
              + '; no namespace or child started', flush=True)
        return 8
    started_at = now()
    available = (deadline - started_at).total_seconds()
    if available <= 0:
        print('[CODEX_SMOKE_HOLD] explicit deadline has expired', flush=True)
        return 8
    if os.name != 'posix':
        raise SafetyError('full process-tree supervision currently requires POSIX')
    expires = began + min(max_wall_sec, available)
    reserve = min(CLEANUP_RESERVE_SECONDS, min(max_wall_sec, available) / 10.)
    work_expires = expires - reserve

    def final_guard():
        remaining(expires, clock)
        if now() >= deadline:
            raise BudgetExpired('explicit absolute smoke deadline exhausted')

    def work_guard():
        remaining(work_expires, clock)
        if (deadline - now()).total_seconds() <= reserve:
            raise BudgetExpired('absolute deadline cleanup reserve reached')

    try:
        target, actions, changed, edits = build_plan(root, session_id, guard=work_guard)
        for path in (target['runtime'], target['evidence'], target['report']):
            work_guard()
            safe_path(root, path)
            if path.exists():
                raise FileExistsError('existing smoke namespace preserved: ' + str(path))
        if raw_logs(root, target['log_name']):
            raise FileExistsError('existing session raw log preserved; choose a new session')
        # These reservations are exclusive. Any partial reservation is retained.
        work_guard()
        target['runtime'].mkdir(parents=True, exist_ok=False)
        safe_path(root, target['runtime'])
        work_guard()
        target['evidence'].mkdir(parents=True, exist_ok=False)
        safe_path(root, target['evidence'])
        work_guard()
        safe_path(root, root / 'smoketest_logs').mkdir(parents=True, exist_ok=True)
    except BudgetExpired as exc:
        print('[CODEX_SMOKE_HOLD] setup budget exhausted; any partial namespace '
              'is retained, no child/report: ' + str(exc), flush=True)
        return 124
    stamp = started_at.astimezone(timezone.utc).strftime('%Y%m%d%H%M%S')
    env = environment(target['runtime'], target['log_name'], stamp)
    report = metadata(root, session_id, target, actions, changed, edits)
    report.update(
        started_at=started_at.isoformat(), deadline_utc=deadline.isoformat(),
        max_wall_sec=max_wall_sec, cleanup_reserve_sec=reserve,
        setup_sec=max(0., clock() - began),
        environment=public_environment(env), receipts=[], summary_command=[],
        environment_scope=('allowlisted receipt only; child inherits the full '
                           'parent environment plus declared overrides; not a '
                           'security sandbox or proof of credential absence'),
        summary_returncode=None, summary_status='NOT_RUN', summary_receipt=None,
        source_pins_before={}, source_pins_after={}, original_synthetic_before={},
        original_synthetic_after={}, original_synthetic_unchanged=False,
        source_pins_unchanged=False, snapshot_errors=[], safety_errors=[],
        original_synthetic_before_complete=False,
        original_synthetic_after_complete=False,
    )
    stop_reason = None
    interrupted = False
    timed_out = False
    old_term = signal.getsignal(signal.SIGTERM)

    def interrupt(signum, frame):
        raise KeyboardInterrupt('termination requested')

    term_installed = False
    def monitor():
        work_guard()
        return monitor_logs(root, target['log_name'])
    try:
        if old_term != signal.SIG_IGN:
            signal.signal(signal.SIGTERM, interrupt)
            term_installed = True
        report['source_pins_before'] = execution_source_pins(root, guard=work_guard)
        bind_pins(report, report['source_pins_before'])
        report['original_synthetic_before'] = original_snapshot(
            root, expires=work_expires, clock=clock, guard=work_guard)
        report['original_synthetic_before_complete'] = True
        for index, (original, actual) in enumerate(zip(actions, changed)):
            receipt = dict(index=index, kind=actual.kind, line=actual.line,
                           original_argv=list(original.argv),
                           executed_argv=list(actual.argv), seconds=actual.seconds,
                           status='NOT_RUN', returncode=None,
                           child=actual.kind == 'run' and '--' in actual.argv,
                           duration_sec=0., error=None, termination=[])
            report['receipts'].append(receipt)
            if stop_reason:
                receipt['error'] = stop_reason
                continue
            if actual.kind == 'sleep':
                tick = clock()
                try:
                    bounded_pause(actual.seconds, work_expires=work_expires,
                                  clock=clock, guard=work_guard, sleep=sleep)
                    receipt.update(status='COMPLETE', returncode=0)
                except BudgetExpired as exc:
                    receipt.update(status='TIMED_OUT', error=str(exc))
                except KeyboardInterrupt:
                    receipt.update(status='INTERRUPTED', error='KeyboardInterrupt/SIGTERM')
                except Exception as exc:
                    receipt.update(status='TOOL_ERROR', error=type(exc).__name__ + ': ' + str(exc))
                receipt['duration_sec'] = max(0., clock() - tick)
            else:
                receipt.update(run_child(
                    actual.argv, root=root, env=env, work_expires=work_expires,
                    expires=expires, clock=clock, monitor=monitor,
                    process_factory=process_factory, state_sink=receipt))
            if receipt['status'] in ('TIMED_OUT', 'INTERRUPTED'):
                stop_reason = receipt['status']
                timed_out |= receipt['status'] == 'TIMED_OUT'
                interrupted |= receipt['status'] == 'INTERRUPTED'
            if receipt.get('unsafe_process_state'):
                stop_reason = 'PROCESS_CLEANUP_UNRESOLVED'
            if receipt.get('interrupted_during_cleanup'):
                interrupted = True
                stop_reason = 'INTERRUPTED'
            try:
                monitor()
            except Exception as exc:
                report['safety_errors'].append(type(exc).__name__ + ': ' + str(exc))
                stop_reason = 'RAW_LOG_SAFETY'
        logs = monitor()
        if not stop_reason and len(logs) == 1:
            command = [sys.executable, 'scripts/runlog.py', '--name', target['log_name'],
                       '--', sys.executable, 'scripts/summarize_smoke.py', '--log', str(logs[0])]
            report['summary_command'] = command
            report['summary_receipt'] = {}
            summary = run_child(command, root=root, env=env,
                                work_expires=work_expires, expires=expires,
                                clock=clock, monitor=monitor,
                                process_factory=process_factory,
                                state_sink=report['summary_receipt'])
            report.update(summary_returncode=summary['returncode'],
                          summary_status=summary['status'], summary_receipt=summary)
            interrupted |= summary['status'] == 'INTERRUPTED'
            interrupted |= summary.get('interrupted_during_cleanup', False)
            timed_out |= summary['status'] == 'TIMED_OUT'
        elif not logs:
            report['safety_errors'].append('exactly one complete raw log is required')
    except KeyboardInterrupt:
        interrupted = True
        stop_reason = 'INTERRUPTED'
    except BudgetExpired as exc:
        timed_out = True
        stop_reason = 'TIMED_OUT'
        report['safety_errors'].append(str(exc))
    except Exception as exc:
        stop_reason = 'TOOL_ERROR'
        report['safety_errors'].append(type(exc).__name__ + ': ' + str(exc))
    finally:
        # A signal at a helper's return boundary must not turn an already
        # launched action back into NOT_RUN while finalizing the caller.
        active = list(report['receipts'])
        if report['summary_receipt'] is not None:
            active.append(report['summary_receipt'])
        for receipt in active:
            if receipt.get('status') == 'RUNNING':
                receipt.update(status='INTERRUPTED' if interrupted else 'TOOL_ERROR',
                               error='caller finalized an interrupted started child',
                               unsafe_process_state=True)
        if report['summary_receipt'] is not None:
            report['summary_status'] = report['summary_receipt'].get('status', 'NOT_RUN')
            report['summary_returncode'] = report['summary_receipt'].get('returncode')
        for index in range(len(report['receipts']), len(changed)):
            actual, original = changed[index], actions[index]
            report['receipts'].append(dict(
                index=index, kind=actual.kind, line=actual.line,
                original_argv=list(original.argv), executed_argv=list(actual.argv),
                seconds=actual.seconds, status='NOT_RUN', returncode=None,
                child=actual.kind == 'run' and '--' in actual.argv,
                duration_sec=0., error=stop_reason or 'PREPARATION_INCOMPLETE',
                termination=[]))
        try:
            final_guard()
            report['source_pins_after'] = execution_source_pins(root, guard=final_guard)
            report['source_pins_unchanged'] = (
                bool(report['source_pins_before'])
                and report['source_pins_before'] == report['source_pins_after'])
        except BaseException as exc:
            interrupted |= isinstance(exc, KeyboardInterrupt)
            timed_out |= isinstance(exc, BudgetExpired)
            report['snapshot_errors'].append('source-after:' + type(exc).__name__ + ': ' + str(exc))
        try:
            report['original_synthetic_after'] = original_snapshot(
                root, expires=expires, clock=clock, guard=final_guard)
            report['original_synthetic_after_complete'] = True
            report['original_synthetic_unchanged'] = (
                report['original_synthetic_before_complete']
                and report['original_synthetic_before'] == report['original_synthetic_after'])
        except BaseException as exc:
            interrupted |= isinstance(exc, KeyboardInterrupt)
            timed_out |= isinstance(exc, BudgetExpired)
            report['snapshot_errors'].append('synthetic-after:' + type(exc).__name__ + ': ' + str(exc))
        try:
            logs = raw_logs(root, target['log_name'])
            report['raw_logs'] = [p.relative_to(root).as_posix() for p in logs]
            if len(logs) == 1:
                path = logs[0]
                report.update(log=path.relative_to(root).as_posix(),
                              log_bytes=path.stat().st_size)
                if report['log_bytes'] >= MAX_LOG_BYTES:
                    report['safety_errors'].append('raw log20MB guard; full bytes retained')
                # Path/observed size remain honest even if the hash cannot
                # finish within budget; a missing SHA is never a complete log.
                report['log_sha256'] = digest(path, expires=expires, clock=clock,
                                             guard=final_guard)
            else:
                report['safety_errors'].append('raw-log count is not exactly one')
        except BaseException as exc:
            interrupted |= isinstance(exc, KeyboardInterrupt)
            timed_out |= isinstance(exc, BudgetExpired)
            report['safety_errors'].append('raw-after:' + type(exc).__name__ + ': ' + str(exc))
        report.update(
            complete=(all(r['status'] == 'COMPLETE' for r in report['receipts'])
                      and report['summary_status'] == 'COMPLETE'),
            failed_calls=sum(r['status'] != 'COMPLETE' or r['returncode'] != 0
                             for r in report['receipts']),
            failed_run_calls=sum((r['status'] != 'COMPLETE' or r['returncode'] != 0)
                                 and r['kind'] == 'run' for r in report['receipts']),
            interrupted=interrupted, timed_out=timed_out,
            whole_sec=max(0., clock() - began), finished_at=now().isoformat(),
        )
        success = (report['complete'] and report['failed_calls'] == 0
                   and report['summary_returncode'] == 0
                   and report['source_pins_unchanged']
                   and report['original_synthetic_unchanged']
                   and not report['snapshot_errors'] and not report['safety_errors'])
        code = (130 if interrupted else 124 if timed_out else 0 if success else 1)
        report['returncode'] = code
        try:
            write_report(root, target['report'], report)
        finally:
            if term_installed:
                signal.signal(signal.SIGTERM, old_term)
    print('[CODEX_SMOKE_FINISHED] ' + str(target['report'].relative_to(root)), flush=True)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('check', 'full', 'contract'), default='check')
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--deadline-utc', type=aware_deadline)
    parser.add_argument('--max-wall-sec', type=wall_seconds, default=DEFAULT_WALL_SECONDS)
    args = parser.parse_args(argv)
    if args.mode == 'full' and (not args.execute or args.deadline_utc is None):
        parser.error('full requires --execute and an aware --deadline-utc')
    if args.mode != 'full' and args.execute:
        parser.error('--execute is only valid for full mode')
    try:
        if args.mode == 'check':
            return check(ROOT, args.session_id, args.max_wall_sec)
        if args.mode == 'contract':
            return contract(ROOT, args.session_id)
        return full(ROOT, args.session_id, args.deadline_utc, args.max_wall_sec)
    except (OSError, ValueError) as exc:
        print('[CODEX_SMOKE_ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        return 9


if __name__ == '__main__':
    raise SystemExit(main())
