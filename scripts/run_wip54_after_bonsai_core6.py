"""Run the prepared WIP 54 update test when the exact Bonsai GPU run releases."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from scripts import diag_p102a_tiled_bonsai_exact_kd as kd
from scripts import run_p106b_hellaswag_exact_suffix as suffix


KD_RUN = "P102A_Stage2icW_bonsai_exact_KD_GPU"


def process_exit(path):
    if not path.is_file():
        return None
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 8192))
        ends = re.findall(rb"\[runlog\] " + "종료코드".encode() + rb" (\d+) ", stream.read())
    return int(ends[-1]) if ends else None


def run(run_id, raw):
    suffix.require(os.environ.get("CUDA_VISIBLE_DEVICES") == "0", "queue requires the one approved GPU")
    suffix.require(re.fullmatch(r"[a-z0-9][a-z0-9_]{0,31}", run_id), "invalid predecessor ID")
    raw = raw.absolute()
    suffix.require(raw.parent == kd.io.ROOT / "test_result" and raw.name.startswith("101_log_")
                   and not raw.is_symlink(), "an exact Bonsai runlog is required")
    out = suffix.EVIDENCE / (suffix.TAG_PREFIX + run_id)
    target = out / "terminal.json"
    prepared_sha = kd.io.digest(kd.PROFILE)
    entry = kd.OUT / f"queue_after_{run_id}.json"
    kd.io.write(entry, dict(predecessor=out.name, raw=str(raw.relative_to(kd.io.ROOT)),
                            profile_sha256=prepared_sha, cutoff_KST=kd.CUTOFF.isoformat()))
    print("WIP54_QUEUE_WAIT", out.name, flush=True)
    while time.time() + 200 < kd.CUTOFF.timestamp() and not (kd.OUT / "STOP").exists():
        code = process_exit(raw)
        if code is not None:
            break
        time.sleep(2.)
    else:
        print("WIP54_QUEUE_HOLD cutoff or STOP", flush=True)
        return 8
    if code != 0 or not target.is_file():
        print("WIP54_QUEUE_HOLD predecessor ended before completion", code, flush=True)
        return 8
    fixed, cursor, closed = suffix.history()
    suffix.require(cursor == fixed["rows_total"] and out.name in closed, "official rows still incomplete")
    suffix.require(kd.io.digest(kd.PROFILE) == prepared_sha and not (kd.OUT / "terminal.json").exists()
                   and not any((kd.io.ROOT / "test_result").glob(f"093_log_*_{KD_RUN}.txt")),
                   "training profile changed or experiment already started")
    kd.io.reserve_device()
    print("WIP54_QUEUE_START", out.name, cursor, closed[out.name], flush=True)
    command = [sys.executable, "-B", "-X", "utf8", "scripts/runlog.py", "--num", "093", "--name", KD_RUN,
               "--", "timeout", "--signal=INT", "--kill-after=10s", "180s", sys.executable,
               "-B", "-u", "-X", "utf8", "-m", "scripts.diag_p102a_tiled_bonsai_exact_kd", "actual"]
    return subprocess.run(command, cwd=kd.io.ROOT).returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--after", required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.after, args.log))
