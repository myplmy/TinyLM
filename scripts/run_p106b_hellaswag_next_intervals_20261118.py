"""Continue the same cached HellaSwag task after the first exact intervals close."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts import diag_p106b_bonsai_hellaswag_exact_intervals as intervals


FIRST = intervals.OUT
FIRST_PROFILE = intervals.PROFILE
FIRST_RAW = intervals.io.ROOT / "test_result/101_log_20261118_P106B_Stage8pr6Wj_bonsai_hellaswag_exact_intervals_GPU.txt"
FIRST_EXPECTED = intervals.RANGES
SAVED_FINGERPRINT = intervals.fingerprint
TAG = "p106b_bonsai_hellaswag_exact_prefix_continue_v1_20261118"
NAME = "P106B_Stage8pr6Wk_bonsai_hellaswag_exact_continuation_GPU"
RAW = intervals.io.ROOT / f"test_result/101_log_20261118_{NAME}.txt"
AUDIT = intervals.io.ROOT / "handoff/audit/research_20261118_01a1e647"
QUEUE_END = AUDIT / "BONSAI_HELLASWAG_CONTINUATION_TERMINAL_v1.json"
RANGE_SIZE, CAP = 256, 610
NEXT_TOTAL = 8
intervals.TAG = TAG
intervals.OUT = FIRST.parent / TAG
intervals.PROFILE = intervals.OUT / "profile.json"
intervals.RANGES = tuple((768 + i*RANGE_SIZE, 768 + (i+1)*RANGE_SIZE) for i in range(NEXT_TOTAL))
intervals.CAP = CAP


def fingerprint():
    candidate, original, native = SAVED_FINGERPRINT()
    first = intervals.core.PRISM.read(FIRST_PROFILE)
    assert first["ranges"] == [list(pair) for pair in FIRST_EXPECTED]
    for key in ("previous_tasks_reused", "official", "rows_total", "route"):
        assert first[key] == candidate[key]
    candidate["first_profile_sha256"] = intervals.io.digest(FIRST_PROFILE)
    candidate["launcher_sha256"] = intervals.io.digest(Path(__file__).resolve())
    return candidate, original, native


intervals.fingerprint = fingerprint


def ready_to_continue(profile):
    done = json.loads((FIRST / "terminal.json").read_bytes())
    assert done["exit"] == 0 and done["complete_intervals"] and done["handles_closed"]
    assert done["exact_rows"] == 768 and done["profile_sha256"] == profile["first_profile_sha256"]
    assert done["release"]["competing_compute_pids"] == []
    kept = [(row["first"], row["end_exclusive"], row["rows"]) for row in done["intervals"]]
    assert kept == [(first,end,end-first) for first,end in FIRST_EXPECTED]
    for row in done["intervals"]:
        directory = FIRST / f"rows_{row['first']:05}_{row['end_exclusive']:05}"
        assert intervals.core.PRISM.read(directory / "interval.json") == row
        intervals.core.verify_shards(directory, row["manifest"])
    return intervals.io.digest(FIRST / "terminal.json")


def queue():
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    assert not QUEUE_END.exists() and not RAW.exists()
    p, _, native = fingerprint()
    assert intervals.core.PRISM.read(intervals.PROFILE) == p
    assert os.environ["LD_LIBRARY_PATH"] == native["bundle"]
    print("BONSAI_HELLASWAG_CONTINUATION_WAITING", os.getpid(), flush=True)
    bound = intervals.core.CUTOFF - CAP - 120
    first_terminal = FIRST / "terminal.json"
    first_sha = None
    error = None
    rc = 8
    try:
        while time.time() < bound:
            if (intervals.OUT/"STOP").exists():
                raise RuntimeError("owned STOP")
            if first_terminal.is_file() and "[runlog] 종료코드 " in FIRST_RAW.read_text(encoding="utf-8"):
                first_sha = ready_to_continue(p)
                break
            time.sleep(1.)
        if first_sha is None:
            raise TimeoutError("the prior intervals did not close with time for continuation")
        entry = intervals.io.reserve_device()
        timeout = int(intervals.core.CUTOFF - 5 - time.time())
        assert timeout > CAP + 70
        command = [sys.executable, "-B", "-X", "utf8", "scripts/runlog.py", "--num", "101", "--name", NAME,
            "--", "timeout", "--signal=INT", "--kill-after=20s", f"{timeout}s", sys.executable,
            "-B", "-u", "-X", "utf8", "-m", "scripts.run_p106b_hellaswag_next_intervals_20261118", "actual"]
        print("BONSAI_HELLASWAG_CONTINUATION_AUTOSTART", first_sha, entry["free_MiB"], flush=True)
        rc = subprocess.run(command, cwd=intervals.io.ROOT).returncode
    except (AssertionError, OSError, ValueError, RuntimeError, KeyboardInterrupt) as exc:
        error = dict(type=type(exc).__name__, message=str(exc))
    intervals.io.write(QUEUE_END, dict(exit=rc, error=error, previous_terminal_sha256=first_sha,
        profile_sha256=intervals.io.digest(intervals.PROFILE), exact_new_raw=str(RAW.relative_to(intervals.io.ROOT)),
        official_full_task_score=None))
    return rc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "queue", "actual"))
    action = parser.parse_args().action
    if action == "prepare":
        intervals.prepare()
    elif action == "queue":
        raise SystemExit(queue())
    else:
        ready_to_continue(intervals.core.PRISM.read(intervals.PROFILE))
        raise SystemExit(intervals.actual())
