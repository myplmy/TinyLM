"""Run one owned CUDA child and record its final device return."""

import fcntl
import multiprocessing
import os
import signal
import time

from scripts import run_p109b_scratch_pair_20261120 as gpu
from scripts.run_p109c_scratch330 import CARD_LIMIT_MIB, observe_card_return


def supervise(worker, args, output, deadline, *, authorization_end, min_seconds):
    if (deadline.tzinfo is None or deadline > authorization_end
            or deadline.timestamp() - time.time() < min_seconds):
        raise ValueError("insufficient time in the authorized CUDA window")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or output.exists():
        raise ValueError("requires a fresh output and exactly one authorized CUDA device")
    cutoff = deadline.timestamp() - 35
    lock = os.open(gpu.ROOT / "runs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        total, used = gpu.idle_gpu()
        output.mkdir()
        fraction = (CARD_LIMIT_MIB - used - 512) / total
        process = multiprocessing.get_context("spawn").Process(target=worker, args=(*args, fraction))
        start, peak, reason = time.time(), 0, None

        def stop_on_signal(signum, _):
            raise KeyboardInterrupt(signal.Signals(signum).name)

        previous = signal.signal(signal.SIGTERM, stop_on_signal)
        try:
            process.start()
            print(f"SUPERVISOR child={process.pid} stop={output / 'STOP'}", flush=True)
            with (output / "gpu.csv").open("x", encoding="utf-8", buffering=1) as stream:
                stream.write("unix_seconds,pid,card_used_mib,gpu_util_percent\n")
                while process.is_alive():
                    now = time.time()
                    if now >= cutoff or (output / "STOP").exists():
                        reason = "DEADLINE_OR_STOP"
                        break
                    _, used, utilization = gpu.gpu_status()
                    peak = max(peak, used)
                    stream.write(f"{now:.3f},{process.pid},{used},{utilization}\n")
                    if used > CARD_LIMIT_MIB:
                        reason = "CARD_MEMORY_LIMIT"
                        break
                    process.join(timeout=2)
        except BaseException as error:
            reason = repr(error)
            raise
        finally:
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=8)
                    if process.is_alive():
                        process.kill()
                process.join()
            signal.signal(signal.SIGTERM, previous)
            end = time.time()
            gpu.publish(output / "supervisor.json", dict(pid=process.pid, started=start, ended=end,
                        returncode=process.exitcode, stop_reason=reason, peak_card_mib=peak,
                        card_after_exit=observe_card_return()))
    finally:
        os.close(lock)
    return 0 if process.exitcode == 0 and reason is None else 1
