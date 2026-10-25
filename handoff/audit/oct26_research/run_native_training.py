#!/usr/bin/env python3
"""Run an exact frozen native arm and collect the actual parent exit."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native_format_training as train

BASE = Path(__file__).resolve().parent
INPUT_SHA = "850EA5767D568C58907C085A9053E8343F6FC3D5B309E81813CB89462B7A411F"

def write_once(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if len(raw) >= 20_000_000:
        raise ValueError("small root receipt limit")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("cost", "train"), required=True)
    parser.add_argument("--arm", choices=("format_muon", "format_normuon"), required=True)
    parser.add_argument("--budget")
    parser.add_argument("--budget-sha256")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-only", action="store_true")
    action.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    inputs, _ = train.read(str((BASE / "native_training_inputs_v1.json").relative_to(ROOT)), INPUT_SHA)
    mode, arm = args.mode, args.arm
    stage = ("10cWb" if arm == "format_muon" else "10cWc") if mode == "cost" else (
        "10dWb" if arm == "format_muon" else "10dWc")
    state_args = argparse.Namespace(mode=mode, arm=arm,
        profile=inputs["profile"]["path"], profile_sha256=inputs["profile"]["sha256"],
        f4=inputs["f4"]["path"], f4_sha256=inputs["f4"]["sha256"],
        budget=args.budget, budget_sha256=args.budget_sha256)
    state = train.metadata(state_args)
    if inputs["source"] != state["source_identity"]:
        raise ValueError("training source differs from root seal")
    cap = 1200 if mode == "cost" else 14400
    destination = ROOT / "test_result/evidence" / (train.PREFIX + arm + "_" + mode)
    command = [sys.executable, "-I", "-B", "-X", "utf8", str(ROOT / "scripts/diag_p106b_native_format_training.py"),
        "--mode", mode, "--arm", arm, "--profile", state_args.profile,
        "--profile-sha256", state_args.profile_sha256, "--f4", state_args.f4,
        "--f4-sha256", state_args.f4_sha256, "--max-wall-sec", str(cap),
        "--deadline", train.END.isoformat()]
    if mode == "train":
        if args.budget is None or args.budget_sha256 is None:
            raise ValueError("explicit paired budget is required")
        command += ["--budget", args.budget, "--budget-sha256", args.budget_sha256]
    if args.check_only:
        return subprocess.run(command + ["--check-only"], cwd=ROOT, stdin=subprocess.DEVNULL).returncode
    if destination.exists():
        raise FileExistsError(destination)
    regression = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", "-W", "error",
        "scripts/test_p106b_native_format_training.py"], cwd=ROOT, stdin=subprocess.DEVNULL)
    if regression.returncode:
        return regression.returncode
    check = subprocess.run(command + ["--check-only"], cwd=ROOT, stdin=subprocess.DEVNULL)
    if check.returncode:
        return check.returncode
    command += ["--output", str(destination.relative_to(ROOT)), "--execute"]
    started = time.monotonic()
    actual = subprocess.run(["timeout", "--signal=TERM", "--kill-after=10s", str(cap + 30) + "s", *command],
        cwd=ROOT, stdin=subprocess.DEVNULL)
    elapsed = time.monotonic() - started
    observation = {"schema": "P106B_NATIVE_FORMAT_ROOT_EXIT_V1", "stage": stage,
        "mode": mode, "arm": arm, "actual_supervisor_exit": actual.returncode,
        "actual_parent_wall_sec": elapsed, "command": command, "outer_timeout_sec": cap + 30,
        "source_sha256": inputs["source"]["sha256"], "output": str(destination.relative_to(ROOT)),
        "new_gpu_quality_claim": False}
    if destination.is_dir():
        write_once(destination / "root_observation.json", observation)
        if actual.returncode == 0:
            report = destination / "report.json"
            terminal = destination / "terminal.jsonl"
            spec = {"path": str(report.relative_to(ROOT)), "sha256": train.pair.file_sha(report),
                "terminal_sha256": train.pair.file_sha(terminal),
                "actual_supervisor_exit": actual.returncode, "actual_parent_wall_sec": elapsed}
            train.read_closed(spec, state, arm, mode)
            write_once(destination / "root_closed_ref.json", spec)
    print(json.dumps(observation, ensure_ascii=False), flush=True)
    return actual.returncode

if __name__ == "__main__":
    raise SystemExit(main())
