"""Supervise an allocator-bounded evaluation through temporary NVML timeouts."""

import fcntl
import multiprocessing
import os
from queue import Empty, SimpleQueue
import signal
import subprocess
from threading import Event, Thread
import time

from scripts import p109_gpu_supervisor as telemetry
from scripts import run_p109c_scratch330 as native
from tinylm import paths


def sample_card(output, stop):
    while not stop.is_set():
        try:
            values = subprocess.check_output(telemetry.QUERY, text=True, stderr=subprocess.STDOUT, timeout=3.)
            total, used, utilization = map(int, values.strip().split(","))
            if not 0 <= used <= total or not 0 <= utilization <= 100:
                raise ValueError("an NVML sample is outside its bounds")
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            output.put((time.time(), repr(error), None))
        else:
            output.put((time.time(), used, utilization))
        stop.wait(2.)


def wait_return():
    for _ in range(5):
        sample = native.observe_card_return()
        if sample.get("compute_pids") == [] and isinstance(sample.get("free_mib"), int):
            return sample
        time.sleep(1.)
    return sample


def supervise(worker, profile, sha, record, stop_by):
    cutoff = stop_by.timestamp() - 35
    if stop_by.tzinfo is None or cutoff <= time.time():
        raise ValueError("evaluation requires a future approved cutoff")
    native.manifest_bytes(profile, sha)
    lock = os.open(paths.RUNS, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        native.idle_gpu()
        record.mkdir(exist_ok=False)
        child = multiprocessing.get_context("spawn").Process(target=worker,
                         args=(profile, sha, False, record, cutoff))
        started, peak, reason = time.time(), 0, None
        updates, stop = SimpleQueue(), Event()
        heartbeat = record / "progress.jsonl"

        def interrupted(value, frame):
            raise KeyboardInterrupt(signal.Signals(value).name)

        previous = signal.signal(signal.SIGTERM, interrupted)
        try:
            child.start()
            Thread(target=sample_card, args=(updates, stop), daemon=True).start()
            with ((record / "gpu.csv").open("x", encoding="utf-8", buffering=1) as log,
                  (record / "telemetry_gaps.txt").open("x", encoding="utf-8", buffering=1) as failures):
                log.write("unix_seconds,pid,card_used_mib,gpu_util_percent\n")
                while child.is_alive():
                    instant = time.time()
                    if instant >= cutoff:
                        reason = "AUTHORIZED_CUTOFF"
                        break
                    activity = heartbeat.stat().st_mtime if heartbeat.is_file() else started
                    if instant - activity > 180:
                        reason = "NO_EVALUATION_PROGRESS_IN_180_SECONDS"
                        break
                    try:
                        seen, used, utilization = updates.get_nowait()
                    except Empty:
                        pass
                    else:
                        if utilization is None:
                            failures.write(f"{seen:.3f} {str(used)[:500]}\n")
                        else:
                            log.write(f"{seen:.3f},{child.pid},{used},{utilization}\n")
                            peak = max(peak, used)
                            if used > native.CARD_LIMIT_MIB:
                                reason = "CARD_MEMORY_LIMIT"
                                break
                    child.join(timeout=1.)
        except BaseException as error:
            reason = repr(error)
            raise
        finally:
            stop.set()
            try:
                if child.pid is not None:
                    if child.is_alive():
                        child.terminate()
                        child.join(timeout=8.)
                        if child.is_alive():
                            child.kill()
                    child.join()
                ended = time.time()
                native.publish(record / "supervisor.json", dict(pid=child.pid, started=started,
                               ended=ended, returncode=child.exitcode, peak_card_mib=peak,
                               stop_reason=reason, card_after_exit=wait_return()))
            finally:
                signal.signal(signal.SIGTERM, previous)
    finally:
        os.close(lock)
    return 0 if child.exitcode == 0 and reason is None else 1
