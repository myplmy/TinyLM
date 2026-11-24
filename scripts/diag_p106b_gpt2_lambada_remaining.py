"""Finish the one cost-held GPT-2 Q4 task with the original GGUF evaluator."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

from scripts import diag_p106b_native_gguf_followups as original


ROOT = original.ROOT
TAG = "p106b_gpt2_lambada_remaining_v1_20261118"
OUT = ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
TASK = original.OFFICIAL.TASK
MODEL = "gpt2_q4km"
MODEL_CAP = 1260
SUPERVISOR_CAP = MODEL_CAP + 120
BYTE_LIMIT = 128_000_000
PARENT_PROFILE_SHA = "C8BC238555B3A02DCB82605346483B9FCC11DCA80D2CEFD1267B46241AE36C11"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def parent_evidence():
    profile, build = original.verify()
    profile_sha = original.native.digest(original.PROFILE)
    need(profile_sha == PARENT_PROFILE_SHA, "Original GGUF profile drifted")
    case = original.OUT / MODEL
    report = original.mc.prism.read(case / "report.json")
    states = {name: task["status"] for name, task in report["tasks"].items()}
    need(report["model"] == MODEL and report["status"] == "TASK_HOLD", "GPT-2 hold evidence differs")
    need(set(states) == set(profile["tasks"]["proof"]), "Prior task coverage differs")
    need(states.pop(TASK) == "COST_HOLD" and set(states.values()) == {"COMPLETE"},
         "Only the GPT-2 LAMBADA cost hold may be scheduled")
    hold = report["tasks"][TASK]
    need(hold["scored_rows"] == 0 and not list(case.glob(f"{TASK}*")), "LAMBADA already has scored rows")
    need(report["worker"]["worker_returncode"] == 0 and report["worker"]["worker_cleanup_complete"],
         "Original GPT-2 worker cleanup was not confirmed")
    need(hold["cost"]["forecast_seconds"] < MODEL_CAP - 90, "Selective job has an insufficient cost budget")
    inherited = dict(original_profile_sha256=profile_sha,
                     original_gpt2_report_sha256=original.native.digest(case / "report.json"),
                     reused_completed={name: report["tasks"][name]["manifest"]["concat_sha256"] for name in states},
                     prior_cost=hold["cost"], model_asset=profile["assets"][MODEL],
                     worker_sha256=build["worker_sha256"], request_proof=profile["tasks"]["proof"][TASK])
    return inherited, build


def input_rows(proof):
    official = original.OFFICIAL
    with patch.object(official, "CACHE", OUT / "lambada_task_cache"):
        task, _ = official.load_task()
    items = []
    requests = hashlib.sha256()
    for index, doc in enumerate(task.eval_docs):
        args = list(official.request_for(task, doc, index).args)
        requests.update(original.canonical(args) + b"\n")
        items.append(dict(doc_id=index, doc=doc, arguments=[args]))
    actual = dict(rows=len(items), ordered_request_sha256=requests.hexdigest().upper())
    need(actual == proof and actual["rows"] == 5153, "Selective LAMBADA inputs differ")
    return task, items


def own_config(inherited):
    return dict(tag=TAG, source_sha256=original.native.digest(Path(__file__)),
                model_seconds=MODEL_CAP, parent_seconds=SUPERVISOR_CAP, byte_limit=BYTE_LIMIT,
                planned_model=MODEL, planned_task=TASK, original=inherited)


def prepare():
    need(os.environ.get("CUDA_VISIBLE_DEVICES") == "", "Use the CPU-only preparation")
    inherited, _ = parent_evidence()
    OUT.mkdir(exist_ok=False)
    input_rows(inherited["request_proof"])
    original.mc.prism.write(PROFILE, own_config(inherited))
    print("GPT2_LAMBADA_ONLY_PREPARED", original.native.digest(PROFILE), inherited["prior_cost"], flush=True)


def check():
    inherited, build = parent_evidence()
    need(original.mc.prism.read(PROFILE) == own_config(inherited), "Selective run profile drifted")
    return inherited, build


def terminal_predecessor():
    receipt = original.mc.prism.read(original.OUT / "supervisor/supervisor_receipt.json")
    terminal = original.mc.prism.read(original.OUT / "actual.json")
    need(receipt["actual_controller_exit_observed"] and not receipt["cleanup_errors"],
         "Original GGUF process tree has not closed cleanly")
    need(terminal["models"][MODEL] == "TASK_HOLD" and terminal["profile_sha256"] == PARENT_PROFILE_SHA,
         "Original terminal proof differs")
    need(time.time() + SUPERVISOR_CAP + 75 < original.CUTOFF, "Selective window does not fit")


def actual():
    need(bool(os.environ.get(original.supervision.OWNER_KEY)), "Run the bounded owned controller")
    terminal_predecessor()
    inherited, build = check()
    task, items = input_rows(inherited["request_proof"])
    with patch.multiple(original, OUT=OUT, TAG=TAG, MODEL_CAPS={MODEL: MODEL_CAP}, BYTE_LIMIT=BYTE_LIMIT):
        status = original.run_model(MODEL, inherited["model_asset"], build, {TASK: task}, {TASK: items})
    check()
    original.mc.prism.write(OUT / "actual.json", dict(tag=TAG, profile_sha256=original.native.digest(PROFILE),
        model=MODEL, task=TASK, complete=status == "COMPLETE", status=status,
        ended_UTC=datetime.now(timezone.utc).isoformat(), other_tasks_reexecuted=0))
    return 0 if status == "COMPLETE" else 8


def supervise():
    terminal_predecessor()
    check()
    argv = [sys.executable, "-B", "-u", "-m", "scripts.diag_p106b_gpt2_lambada_remaining", "actual"]
    record = original.supervision.supervise_process(
        argv, worker_binary=original.BINARY, directory=OUT / "supervisor",
        deadline_epoch=original.CUTOFF, cap=SUPERVISOR_CAP, reserve=60,
        verify_success=lambda: original.mc.prism.read(OUT / "actual.json"),
    )
    print("GPT2_LAMBADA_ONLY_SUPERVISOR", record["returncode"], record["controller_returncode"], flush=True)
    return record["returncode"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "supervise", "actual"))
    command = parser.parse_args().action
    if command == "prepare":
        prepare()
    elif command == "check":
        check()
        print("GPT2_LAMBADA_ONLY_CHECK", original.native.digest(PROFILE), flush=True)
    else:
        raise SystemExit(supervise() if command == "supervise" else actual())
