"""Start the prepared P109 visit test after the WIP 54 GPU process exits."""

import os
import subprocess
import sys
import time

from scripts import diag_p109_warm_visit_routes as warm
from scripts.run_wip54_after_bonsai_core6 import KD_RUN, process_exit


RUN = "P109_Stage3Wa_G4_warm_routes_GPU"


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("queue requires the one approved GPU")
    profile_sha = warm.io.digest(warm.PROFILE)
    warm.io.write(warm.OUT / "queue_after_wip54.json", dict(profile_sha256=profile_sha, cutoff_KST=warm.CUTOFF.isoformat()))
    raw_dir = warm.io.ROOT / "test_result"
    print("P109_VISIT_QUEUE_WAIT", KD_RUN, flush=True)
    while time.time() + 330 < warm.CUTOFF.timestamp() and not (warm.OUT / "STOP").exists():
        paths = sorted(raw_dir.glob(f"093_log_*_{KD_RUN}.txt"))
        if len(paths) > 1 or any(path.is_symlink() for path in paths):
            raise ValueError("one explicit predecessor runlog required")
        if paths and (exit_code := process_exit(paths[0])) is not None:
            break
        time.sleep(2.)
    else:
        print("P109_VISIT_QUEUE_HOLD cutoff or STOP", flush=True)
        return 8
    if (warm.io.digest(warm.PROFILE) != profile_sha or (warm.OUT / "terminal.json").exists()
            or any(raw_dir.glob(f"109_log_*_{RUN}.txt"))):
        raise ValueError("prepared profile changed or visit test already started")
    warm.io.reserve_device()
    print("P109_VISIT_QUEUE_START", paths[0].name, exit_code, flush=True)
    # The second job uses no result or asset written by the first one.
    command = [sys.executable, "-B", "-X", "utf8", "scripts/runlog.py", "--num", "109", "--name", RUN,
               "--", "timeout", "--signal=INT", "--kill-after=15s", "300s", sys.executable,
               "-B", "-u", "-X", "utf8", "-m", "scripts.diag_p109_warm_visit_routes", "actual"]
    return subprocess.run(command, cwd=warm.io.ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
