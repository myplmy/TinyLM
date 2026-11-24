"""Run only the missing Gemma and Qwen KoBEST scores in isolated GPU processes."""

import argparse
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from scripts import diag_p106b_kobest_exact_followups as original


ROOT = original.ROOT
TAG = "p106b_kobest_gemma_qwen_remaining_v1_20261118"
OUT = ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
CAPS = {"gemma1b": original.MODELS["gemma1b"], "qwen3508": original.MODELS["qwen3508"]}
PARENT_SHA = "B8448A104489500AD20EEE2182647876A539078730838F4829FF6D0F5EB174DB"
ORIGINAL = {name: getattr(original, name) for name in ("OUT", "TAG", "MODELS", "MAX_SECONDS", "verify")}
IO = original.mc.prism


def original_verify():
    # The isolated output scope changes only where results are written. All original pins still apply.
    with patch.multiple(original, **ORIGINAL):
        profile, qwen = ORIGINAL["verify"]()
    if original.native.digest(original.PROFILE) != PARENT_SHA:
        raise ValueError("Expected the pinned original KoBEST profile")
    return profile, qwen


def frozen_inputs():
    profile, _ = original_verify()
    directory = ORIGINAL["OUT"] / "actual"
    root = IO.read(directory / "report.json")
    native_path = directory / "native595-q/report.json"
    native = IO.read(native_path)
    required = set(profile["tasks"]["proof"])
    if (root["models"] != {"native595-q": "RESOURCE_HOLD"} or not root["original_inputs_unchanged"]
            or Path(f"/proc/{root['PID']}").exists() or set(native["tasks"]) != required
            or any(task["status"] != "COMPLETE" for task in native["tasks"].values())
            or sum(task["rows"] for task in native["tasks"].values()) != 4561
            or any((directory / name).exists() for name in CAPS)):
        raise ValueError("Native must be terminal with every KoBEST task saved and both followups unopened")
    return dict(tag=TAG, script_sha256=original.native.digest(Path(__file__)), parent_profile=PARENT_SHA,
        native_report_sha256=original.native.digest(native_path), native_complete_tasks={
            name: task["manifest"]["concat_sha256"] for name, task in native["tasks"].items()},
        model_caps=CAPS, model_loads_for_preparation=0, one_model_per_child=True,
        per_child_reserve_seconds=120, parent_reserve_seconds=240)


def prepare():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("Use the CPU-only preparation")
    profile = frozen_inputs()
    OUT.mkdir(exist_ok=False)
    IO.write(PROFILE, profile)
    print("KOBEST_TWO_PREPARED", original.native.digest(PROFILE), sorted(CAPS), flush=True)


def verify():
    profile = IO.read(PROFILE)
    if profile != frozen_inputs():
        raise ValueError("Remaining KoBEST profile drifted")
    return profile


def worker(name):
    verify()
    output = OUT / name
    output.mkdir(exist_ok=False)
    with patch.multiple(original, OUT=output, TAG=TAG, MODELS={name: CAPS[name]},
                        MAX_SECONDS=CAPS[name], verify=original_verify):
        return original.actual()


def run():
    from scripts.interactive_research_infer import require_idle_gpu

    profile = verify()
    deadline = original.CUTOFF
    if time.time() + sum(CAPS.values()) + 240 >= deadline:
        raise RuntimeError("Remaining KoBEST caps do not fit")
    results = {}
    for name, cap in CAPS.items():
        if (OUT / "STOP").exists():
            break
        entry = require_idle_gpu()
        argv = [sys.executable, "-B", "-u", "-m", "scripts.diag_p106b_kobest_two_remaining", "worker", name]
        try:
            process = subprocess.run(argv, cwd=ROOT, timeout=cap + 120)
            code = process.returncode
        except subprocess.TimeoutExpired:
            code = 124
        freed = require_idle_gpu()
        folder = OUT / name / "actual"
        terminal = folder / "report.json"
        item = dict(exit=code, gpu_entry=entry, gpu_after_process_exit=freed, tasks={})
        if terminal.exists():
            root = IO.read(terminal)
            single_path = folder / name / "report.json"
            report = IO.read(single_path)
            if (Path(f"/proc/{root['PID']}").exists() or not root["original_inputs_unchanged"]
                    or report["model"] != name or root["models"] != {name: report["status"]}):
                raise ValueError(f"Unclosed isolated KoBEST process for {name}")
            complete = {k: v for k, v in report["tasks"].items() if v["status"] == "COMPLETE"}
            all_tasks = (set(complete) == set(profile["native_complete_tasks"])
                         and sum(t["rows"] for t in complete.values()) == 4561)
            accepted = (code == 0 and root["complete"]) or (
                code == 8 and report["status"] == "RESOURCE_HOLD" and all_tasks)
            item.update(status=report["status"], tasks={k: v["rows"] for k, v in complete.items()},
                report_sha256=original.native.digest(single_path), accepted=accepted and all_tasks,
                cuda_before_process_exit=dict(allocated=report["cuda_final_allocated"], reserved=report["cuda_final_reserved"]))
            if item["accepted"]:
                item["equal_task_macro_F1"] = math.fsum(task["metrics"]["f1"] for task in complete.values()) / 5
        results[name] = item
        print("KOBEST_TWO_CHILD", name, code, item.get("status"), item.get("accepted"), flush=True)
    verify()
    complete = set(results) == set(CAPS) and all(item.get("accepted") for item in results.values())
    IO.write(OUT / "actual.json", dict(tag=TAG, complete=complete, models=results,
        ended_UTC=datetime.now(timezone.utc).isoformat(), previous_native_tasks_reexecuted=0))
    return 0 if complete else 8


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "check", "run", "worker"))
    parser.add_argument("model", nargs="?", choices=CAPS)
    args = parser.parse_args()
    if (args.phase == "worker") != (args.model is not None):
        parser.error("Supply one exact model only for worker")
    if args.phase == "prepare":
        prepare()
    elif args.phase == "check":
        verify()
        print("KOBEST_TWO_CHECK", original.native.digest(PROFILE), flush=True)
    else:
        raise SystemExit(worker(args.model) if args.phase == "worker" else run())
