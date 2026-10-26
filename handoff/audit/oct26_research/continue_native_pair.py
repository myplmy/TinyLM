#!/usr/bin/env python3
"""Wait for the first closed full arm, re-admit time, then run the second."""
from pathlib import Path
from types import SimpleNamespace
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
OLD_BUDGET = "7C750438ED14630F8DCC77AE4FF589290AEEE8362B7A29007D5D5810F8E1C8C7"

def publish(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if len(data) >= 20_000_000:
        raise ValueError("small root metadata limit")
    with path.open("xb") as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())

def admit_second(args, state, first_spec, started, report_path):
    try:
        return train.budget_admission(args, state)
    except train.Hold as error:
        result = {"schema": "TINYLM_NATIVE_PAIR_FOLLOWTHROUGH_V1", "status": "SECOND_ARM_TIME_HOLD",
            "returncode": 8, "actual_second_launcher_exit": None, "second_model_started": False,
            "first_closed_train": first_spec, "budget_v2_sha256": args.budget_sha256,
            "reason": str(error), "elapsed_sec": time.monotonic() - started}
        publish(report_path, result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return None

def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-only", action="store_true")
    action.add_argument("--execute", action="store_true")
    options = parser.parse_args()
    inputs, _ = train.read(str((BASE / "native_training_inputs_v1.json").relative_to(ROOT)),
        "850EA5767D568C58907C085A9053E8343F6FC3D5B309E81813CB89462B7A411F")
    prior, _ = train.read(str((BASE / "native_training_cost_admission_v1.json").relative_to(ROOT)), OLD_BUDGET)
    args = SimpleNamespace(mode="train", arm="format_normuon", profile=inputs["profile"]["path"],
        profile_sha256=inputs["profile"]["sha256"], f4=inputs["f4"]["path"], f4_sha256=inputs["f4"]["sha256"])
    state = train.metadata(args)
    for arm, spec in prior["cost_reports"].items():
        train.read_closed(spec, state, arm, "cost")
    first = ROOT / "test_result/evidence" / (train.PREFIX + "format_muon_train") / "root_closed_ref.json"
    if options.check_only:
        print(json.dumps({"input_pins_verified": True, "first_arm_closed": first.is_file(),
            "model_loaded": False, "gpu_calls": 0, "files_written": 0}))
        return 0
    report_path = BASE / "native_pair_followthrough_v1.json"
    if report_path.exists() or (BASE / "native_training_cost_admission_v2.json").exists():
        raise FileExistsError("preserve the prior followthrough")
    started = time.monotonic()
    while not first.is_file():
        if time.time() >= train.TRAIN_END.timestamp() - prior["conservative_seconds_by_arm"]["format_normuon"] - 120:
            publish(report_path, {"status": "SECOND_ARM_TIME_HOLD", "actual_second_launcher_exit": None,
                "first_arm_closed": False, "elapsed_sec": time.monotonic() - started})
            return 8
        time.sleep(5)
    for attempt in range(3):
        try:
            first_spec = json.loads(first.read_text())
            break
        except json.JSONDecodeError:
            if attempt == 2:
                raise
            time.sleep(1)
    first_closed = train.read_closed(first_spec, state, "format_muon", "train")
    if first_closed["worker"]["status"] != "TRAIN2289_COMPLETE":
        raise ValueError("the first full arm is incomplete")
    next_budget = dict(prior)
    next_budget.update(completed_train_reports={"format_muon": first_spec},
        updated_epoch=time.time(), first_full_arm_root_validated=True,
        previous_budget_sha256=OLD_BUDGET)
    path = BASE / "native_training_cost_admission_v2.json"
    publish(path, next_budget)
    args.budget, args.budget_sha256 = str(path.relative_to(ROOT)), train.pair.file_sha(path)
    admitted = admit_second(args, state, first_spec, started, report_path)
    if admitted is None:
        return 8
    command = ["bash", "run_P106B_Stage10dWc_format_normuon_train.sh", "--budget", args.budget,
        "--budget-sha256", args.budget_sha256]
    print(json.dumps({"first_full_arm_closed": True, "second_budget_sha256": args.budget_sha256,
        "remaining_forecast_seconds": admitted["pending_forecast_seconds"], "second_command": command}), flush=True)
    tick = time.monotonic()
    actual = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL)
    result = {"schema": "TINYLM_NATIVE_PAIR_FOLLOWTHROUGH_V1", "first_closed_train": first_spec,
        "budget_v2_sha256": args.budget_sha256, "actual_second_launcher_exit": actual.returncode,
        "second_launcher_wall_sec": time.monotonic() - tick, "elapsed_sec": time.monotonic() - started,
        "quality_decision": "AFTER_BOTH_FULL_ARMS_ONLY", "command": command}
    second = ROOT / "test_result/evidence" / (train.PREFIX + "format_normuon_train") / "root_closed_ref.json"
    if actual.returncode == 0:
        spec = json.loads(second.read_text())
        closed = train.read_closed(spec, state, "format_normuon", "train")
        result.update(second_closed_train=spec, status="BOTH_FULL300M_CLOSED",
            second_actual_targets=closed["worker"]["totals"]["targets"])
    else:
        result["status"] = "SECOND_LAUNCHER_NONZERO"
    publish(report_path, result)
    print(json.dumps({"status": result["status"], "actual_second_launcher_exit": actual.returncode}), flush=True)
    return actual.returncode

if __name__ == "__main__":
    raise SystemExit(main())
