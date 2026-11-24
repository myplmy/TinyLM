"""Run the matched visit-count arm after the higher-priority P109C evaluations."""

import argparse
from datetime import datetime, timedelta
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts import run_p109c_mixed_visit_count as visits
from scripts import wait_p109_cuda_return as returned


def read(path):
    return json.loads(path.read_bytes())


def partial_ko_return(path, receipt, profile, model_sha, deadline):
    device = receipt.get("card_after_exit") or {}
    planned = receipt["stop_reason"] == "AUTHORIZED_CUTOFF"
    if receipt["stop_reason"] is None and receipt["returncode"] == 1:
        lines = (path / "stdout.txt").read_text(encoding="utf-8").splitlines()
        planned = "TimeoutError: the approved Korean response window ended" in lines
    if (receipt["returncode"] == 0 or not planned
            or device.get("compute_pids") != [] or not isinstance(device.get("free_mib"), int)
            or device["sampled_at"] < receipt["ended"]):
        raise ValueError("the Korean reply job has no planned partial return receipt")
    parts = sorted(path.glob("part_*.json"))
    rows = 0
    for index, part in enumerate(parts):
        item = read(part)
        if (part.name != f"part_{index:04d}.json" or item["profile_sha256"] != profile
                or item["model_sha256"] != model_sha or not item["rows"]):
            raise ValueError("the preserved Korean reply groups are incomplete or from another model")
        rows += len(item["rows"])
    if not 0 < rows <= 841:
        raise ValueError("a planned interruption must leave usable Korean replies")
    lock = os.open(returned.ROOT / "runs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        while time.time() < deadline.timestamp():
            try:
                fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                time.sleep(.5)
            else:
                return dict(ko_resume_groups=len(parts), ko_resume_rows=rows, preceding_pid=receipt["pid"])
    finally:
        os.close(lock)
    raise TimeoutError("the planned interruption did not release its GPU lease")


def remaining_budget(paths, manifest, deadline, partial_ko_profile=None):
    """Use the measured complete uniform run to estimate one more full arm."""
    uniform, after = paths
    terminal = uniform / "supervisor.json"
    while time.time() < deadline.timestamp():
        if terminal.is_file():
            base = read(terminal)
            report = read(uniform / "report.json")
            if (base["returncode"] != 0 or base["stop_reason"] is not None
                    or report["status"] != "FULL_SCRATCH_MIXED_COMPLETE"
                    or report["input_manifest_sha256"] != manifest):
                raise ValueError("this experiment requires the completed matched uniform arm")
            reference_seconds = float(base["ended"] - base["started"])
            if reference_seconds <= 0:
                raise ValueError("the uniform arm has no positive measured training duration")
            estimate = reference_seconds * 1.12 + 900
            remaining = deadline.timestamp() - time.time()
            budget = dict(reference_training_seconds=reference_seconds, reserved_training_seconds=estimate,
                          seconds_until_training_cutoff=remaining)
            if remaining < estimate:
                return dict(budget, status="INCOMPLETE_BUDGET_HOLD")
            preceding = after / "supervisor.json"
            if preceding.is_file():
                receipt = read(preceding)
                if partial_ko_profile:
                    if receipt["returncode"] == 0 and receipt["stop_reason"] is None:
                        return dict(budget, status="NORMAL_QUEUE_OWNS_HANDOFF")
                    partial = partial_ko_return(after, receipt, partial_ko_profile,
                                                report["evaluation_sha256"], deadline)
                    return dict(budget, status="READY", **partial)
                returned.wait_for_return(preceding, receipt["pid"], deadline)
                if read(after / "report.json")["status"] != "REPLIES_COMPLETE":
                    raise ValueError("the preceding Ko-IFEval reply run must be complete")
                return dict(budget, status="READY")
        time.sleep(min(5., max(0., deadline.timestamp() - time.time())))
    return dict(status="AUTHORIZED_WINDOW_ENDED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("uniform", "after", "manifest", "visit-plan", "probe-record", "record", "receipt",
                "eval-python", "eval-profile", "eval-record"):
        parser.add_argument("--" + key, required=True, type=Path)
    for key in ("manifest-sha256", "visit-plan-sha256", "eval-profile-sha256"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--training-until", required=True, type=datetime.fromisoformat)
    parser.add_argument("--eval-until", required=True, type=datetime.fromisoformat)
    parser.add_argument("--partial-ko-profile-sha256", help="stand by only for the planned Korean reply cutoff")
    args = parser.parse_args()
    uniform, after = args.uniform.absolute(), args.after.absolute()
    outputs = tuple(path.absolute() for path in (args.probe_record, args.record, args.eval_record))
    if (args.training_until.tzinfo is None or args.eval_until.tzinfo is None
            or args.eval_until <= args.training_until or len(set(outputs)) != 3
            or any(path.parent != returned.EVIDENCE for path in (uniform, after, *outputs))
            or any(path.exists() or path.is_symlink() for path in outputs)):
        parser.error("the serial queue requires owned P109C records and absolute authorized deadlines")
    manifest = visits.mixed.native.digest(args.manifest_sha256)
    partial_ko = visits.mixed.native.digest(args.partial_ko_profile_sha256) if args.partial_ko_profile_sha256 else None
    profile = visits.read_profile(args.visit_plan.absolute(), args.visit_plan_sha256, manifest)
    print("P109C_VISIT_COUNT_QUEUE_WAIT", uniform, after, flush=True)
    budget = remaining_budget((uniform, after), manifest, args.training_until, partial_ko)
    with args.receipt.open("x", encoding="utf-8") as output:
        print(json.dumps(budget, indent=2), file=output)
    print("P109C_VISIT_COUNT_QUEUE_BUDGET", json.dumps(budget), flush=True)
    if budget["status"] != "READY":
        return 0
    common = ("--manifest", str(args.manifest.absolute()), "--manifest-sha256", manifest,
              "--visit-plan", str(args.visit_plan.absolute()), "--visit-plan-sha256", args.visit_plan_sha256)

    def train(mode, output, cutoff):
        print("P109C_VISIT_COUNT_QUEUE_START", mode, datetime.now(cutoff.tzinfo).isoformat(), output, flush=True)
        return subprocess.run((sys.executable, "-X", "utf8", "-B", "-m", "scripts.run_p109c_mixed_visit_count",
                               mode, *common, "--record", str(output), "--stop-by", cutoff.isoformat()),
                              cwd=returned.ROOT, check=False).returncode

    probe, training, evaluation = outputs
    probe_until = min(args.training_until, datetime.now(args.training_until.tzinfo) + timedelta(minutes=4))
    if code := train("probe", probe, probe_until):
        return code
    terminal = read(probe / "supervisor.json")
    returned.wait_for_return(probe / "supervisor.json", terminal["pid"], args.training_until)
    route_receipt = read(probe / "visit_execution.json")
    proof = read(probe / "report.json")
    if (proof["status"] != "TECHNICAL_PROBE_COMPLETE" or proof["input_manifest_sha256"] != manifest
            or route_receipt["sha256"] != args.visit_plan_sha256.upper()
            or route_receipt["counts"] != {"16": 1, "28": 1, "40": 1}):
        raise ValueError("the three GPU visit routes have no exact technical receipt")
    if code := train("run", training, args.training_until):
        return code
    runs = read(training / "visit_execution.json")
    if runs["actual_visits_sha256"] != profile["visits_sha256"]:
        raise ValueError("applied visits differ from the common-compute plan")
    return subprocess.run((str(args.eval_python.absolute()), "-X", "utf8", "-B", "-m",
                           "scripts.resume_p109c_v2_common_eval", "--fresh", "--visit-count", "--profile",
                           str(args.eval_profile.absolute()),
                           "--profile-sha256", args.eval_profile_sha256, "--record", str(evaluation),
                           "--stop-by", args.eval_until.isoformat()), cwd=returned.ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
