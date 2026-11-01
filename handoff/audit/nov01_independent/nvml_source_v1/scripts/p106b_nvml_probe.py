"""지속 read-only NVML 자식 프로브. timeout 자식만 종료하며 CUDA 모델을 만들지 않는다."""
from __future__ import annotations
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time


def probe_main():
    library = ctypes.CDLL('/usr/lib/wsl/lib/libnvidia-ml.so.1')
    def checked(code):
        if code != 0:
            raise RuntimeError('NVML return code ' + str(code))
    checked(library.nvmlInit_v2())
    try:
        count = ctypes.c_uint()
        checked(library.nvmlDeviceGetCount_v2(ctypes.byref(count)))
        if count.value != 1:
            raise RuntimeError('single GPU only')
        handle = ctypes.c_void_p()
        checked(library.nvmlDeviceGetHandleByIndex_v2(ctypes.c_uint(0), ctypes.byref(handle)))
        class Memory(ctypes.Structure):
            _fields_ = [('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong), ('used', ctypes.c_ulonglong)]
        print(json.dumps(dict(ready=True, backend='PERSISTENT_NVML_C_API', pid=os.getpid())), flush=True)
        for line in sys.stdin:
            if line.strip() == 'quit':
                return 0
            if line.strip() != 'memory':
                raise ValueError('only memory/quit request supported')
            value = Memory()
            checked(library.nvmlDeviceGetMemoryInfo(handle, ctypes.byref(value)))
            print(json.dumps(dict(used_bytes=int(value.used), free_bytes=int(value.free), total_bytes=int(value.total))), flush=True)
    finally:
        library.nvmlShutdown()
    return 0


class NvmlClient:
    """전체 startup+질의를 한 timeout으로 제한한다. command seam은 CPU fixture용이다."""
    def __init__(self, *, timeout=3., command=None):
        if not 0 < timeout <= 3:
            raise ValueError('프로브 deadline은 기존3초 이내')
        self.timeout = float(timeout)
        self.command = command or [sys.executable, '-B', '-u', str(Path(__file__).resolve()), 'probe']
        self.process, self.pending, self.buffer = None, [], b''
        self.stats = dict(launches=0, successful_queries=0, query_errors=0, error_events=[],
                          owned_pids=[], helper_stderr=[], timeout_seconds=timeout)

    def _line(self, deadline):
        while bytes([10]) not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], max(0, remaining))[0]:
                raise TimeoutError('persistent NVML bounded query timeout')
            block = os.read(self.process.stdout.fileno(), 4096)
            if not block:
                raise RuntimeError('persistent NVML helper exited before response')
            self.buffer += block
            if len(self.buffer) > 16384:
                raise ValueError('NVML response size limit')
        line, self.buffer = self.buffer.split(bytes([10]), 1)
        return json.loads(line)

    def _abort(self):
        process, self.process = self.process, None
        self.buffer = b''
        if process is None:
            return
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=.5)
        except subprocess.TimeoutExpired:
            self.pending.append(process)
            return
        if process.stderr is not None:
            error = process.stderr.read(4096).decode('utf-8', errors='replace')
            if error:
                self.stats['helper_stderr'].append(dict(pid=process.pid, text=error))
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()

    def memory(self):
        if self.stats.get('closed'):
            raise RuntimeError('closed NVML client cannot reopen')
        start = time.monotonic()
        utc_start = datetime.now(timezone.utc).isoformat()
        deadline = start + self.timeout
        try:
            if any(process.poll() is None for process in self.pending):
                raise RuntimeError('owned NVML helper did not terminate; do not spawn more')
            if self.process is None:
                self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, bufsize=0)
                self.stats['launches'] += 1
                self.stats['owned_pids'].append(self.process.pid)
                ready = self._line(deadline)
                if ready.get('ready') is not True or ready.get('backend') != 'PERSISTENT_NVML_C_API':
                    raise ValueError('NVML helper handshake differs')
            self.process.stdin.write(b'memory' + bytes([10]))
            value = self._line(deadline)
            if (set(value) != {'used_bytes', 'free_bytes', 'total_bytes'}
                    or any(type(number) is not int or number < 0 for number in value.values())
                    or value['used_bytes'] > value['total_bytes'] or value['free_bytes'] > value['total_bytes']
                    or value['total_bytes'] == 0):
                raise ValueError('NVML memory response shape/range differs')
            self.stats['successful_queries'] += 1
            return value
        except Exception as exc:
            self.stats['query_errors'] += 1
            self.stats['error_events'].append(dict(at_monotonic=start, at_utc=utc_start, seconds=time.monotonic()-start,
                error_type=type(exc).__name__, message=str(exc)[:300]))
            self._abort()
            raise

    def close(self):
        if self.process is not None:
            try:
                self.process.stdin.write(b'quit' + bytes([10]))
                self.process.wait(timeout=.5)
            except (OSError, subprocess.TimeoutExpired):
                pass
            self._abort()
        if any(process.poll() is None for process in self.pending):
            raise RuntimeError('owned NVML helper remains alive')
        self.stats['closed'] = True
        return dict(self.stats)


def watcher_class():
    # 모델/GPU import는 실제 watcher를 요청한 호출자에게만 발생한다.
    from scripts.diag_p107_adaptive_training import VramWatch
    class PersistentVramWatch(VramWatch):
        def __init__(self):
            super().__init__()
            self.client = NvmlClient(timeout=3.)
            self.started = False
        def start(self):
            try:
                super().start()
                self.started = True
            except BaseException:
                self.client.close()
                raise
        def used(self):
            return self.client.memory()['used_bytes']
        def stop(self):
            try:
                if self.started:
                    proof = super().stop()
                else:
                    self.proof['thread_stopped'] = True
                    proof = self.proof
                if not proof['thread_stopped']:
                    raise RuntimeError('owned VRAM watcher did not stop')
                return proof
            finally:
                extra = self.client.close()
                self.proof['backend'] = 'PERSISTENT_NVML_C_API_SUBPROCESS'
                self.proof['client'] = extra
                self.proof['policy'] = dict(query_timeout_seconds=3, interval_seconds=.5,
                    maximum_consecutive_failures=3, shared_increment_limit_bytes=8_000_000_000,
                    failed_query_intervals_are_unmeasured=True)
    return PersistentVramWatch


if __name__ == '__main__':
    if sys.argv[1:] == ['probe']:
        raise SystemExit(probe_main())
    raise SystemExit('private read-only probe mode only')
