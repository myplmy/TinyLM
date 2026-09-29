#!/usr/bin/env python3
"""A1 user gate: one teacher weight copy, 1/2 active slots ABBA, student resident."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_gate_runtime import (TeacherSession, fixed_jobs, read_v17, student_inputs,
    new_directory, idle_before_gpu, write_report, disposition, wall_limit, GateNegative, code_contract, teacher_inputs)
from scripts.p106b_pipeline import CandidateWriter, StudentAccumulator

ORIGINAL_DIRECTORY = ROOT / "HF/sft_ready/p106b_teacher_sft/v22_parallel_abba_low"
RECOVERY_DIRECTORY = ROOT / "HF/sft_ready/p106b_teacher_sft/v26_parallel_abba_budget_recovery_low"
ORDER = (1, 2, 2, 1)


def settings(mode):
    if mode == "original":
        return {"directory": ORIGINAL_DIRECTORY, "concepts_per_language": 4,
                "per_slot_context": 3072, "max_output": 2048, "minimum_complete_per_language": 3}
    if mode == "recovery":
        return {"directory": RECOVERY_DIRECTORY, "concepts_per_language": 16,
                "per_slot_context": 6144, "max_output": 4096, "minimum_complete_per_language": 12}
    raise ValueError("unknown A1 mode")


def speed_gate(arms, minimum_complete_per_language=3):
    if len(arms) != 4 or tuple(a["slots"] for a in arms) != ORDER:
        raise ValueError("ABBA comparison incomplete")
    gains = []
    for one, two in ((arms[0], arms[1]), (arms[3], arms[2])):
        if one["valid_student_tok_per_sec"] <= 0:
            return False, [0.0]
        gains.append(two["valid_student_tok_per_sec"] / one["valid_student_tok_per_sec"])
    passed = (min(gains) > 1.05 and all(min(a["accepted_groups"].get("ko", 0),
                a["accepted_groups"].get("en", 0)) >= minimum_complete_per_language for a in arms)
              and all(arms[b]["canonical_rows"] >= arms[a]["canonical_rows"] for a, b in ((0, 1), (3, 2))))
    return passed, gains


def check(mode="original"):
    cfg = settings(mode)
    jobs, source = fixed_jobs(cfg["concepts_per_language"])
    student = student_inputs()
    read_v17()
    new_directory(cfg["directory"])
    return jobs, {**student, **teacher_inputs(), "code_sha256": code_contract("diag_p106b_parallel_gate.py"),
        "source": source, "mode": mode, "order": list(ORDER), "jobs_per_arm": len(jobs),
        "per_slot_context": cfg["per_slot_context"], "max_output": cfg["max_output"],
        "minimum_complete_per_language": cfg["minimum_complete_per_language"],
        "speed_threshold": "both order-paired valid student tok/s ratios >1.05; no fewer accepted rows; fixed per-mode format threshold",
        "student_micro": 8, "student_accum_limit": 16, "student_checkpoint_on": True,
        "teacher_copies": 1, "quality": "NOT_RUN", "formal_train_ready": False}


def execute(jobs, inputs):
    idle_before_gpu()
    cfg = settings(inputs["mode"])
    directory = cfg["directory"]
    per_slot, maximum = cfg["per_slot_context"], cfg["max_output"]
    directory.mkdir(parents=True, exist_ok=False)
    arms, resource = [], None
    status, rc, reason = "PARTIAL", 9, "not started"
    started = time.monotonic()
    student = None
    try:
        with wall_limit(7200):
            student = StudentAccumulator()
            rows = read_v17()[0]
            for index, slots in enumerate(ORDER):
                path = directory / f"arm{index+1}_slots{slots}"
                path.mkdir(exist_ok=False)
                writer = CandidateWriter(path, inputs)
                session = None
                request_wall = None
                try:
                    with TeacherSession(per_slot * slots, slots) as session:
                        begin = time.monotonic()
                        with ThreadPoolExecutor(max_workers=slots) as pool:
                            futures = [pool.submit(writer.request, session, job,
                                f"a1_{index}_{j:02d}", 20260930+j,
                                per_slot=per_slot, maximum=maximum) for j, job in enumerate(jobs)]
                            for future in futures:
                                future.result()
                        request_wall = time.monotonic() - begin
                        session.require_valid_resources()
                finally:
                    metrics = writer.close()
                    entry = {"slots": slots, "request_phase_wall_sec": request_wall,
                        **metrics, "server": session.evidence() if session else None,
                        "valid_student_tok_per_sec": metrics["student_conversation_tokens"] / request_wall if request_wall else 0.0}
                    arms.append(entry)
                    write_report(path / "arm_manifest.json", entry)
                    print("[PARALLEL_ARM] " + json.dumps(entry, sort_keys=True), flush=True)
            # Only after ABBA: no optimizer/activation-allocation order confound.
            path = directory / "active_resource_probe"
            path.mkdir(exist_ok=False)
            probe = CandidateWriter(path, inputs)
            session = None
            try:
                with TeacherSession(per_slot * 2, 2) as session, ThreadPoolExecutor(max_workers=2) as pool:
                    student.monitor = session.check_monitor
                    pending = [pool.submit(probe.request, session, jobs[j], f"a1_resource_{j}",
                        20260930+j, per_slot=per_slot, maximum=maximum) for j in range(2)]
                    student.add(rows[:8])
                    student.add(rows[8:16])
                    resource = student.finish()
                    for future in pending:
                        future.result()
                    session.require_valid_resources()
            finally:
                evidence = {**probe.close(), "server": session.evidence() if session else None}
                write_report(path / "probe_manifest.json", evidence)
                if resource is not None:
                    resource["teacher_probe"] = evidence
            okay, gains = speed_gate(arms, cfg["minimum_complete_per_language"])
            if not resource:
                raise GateNegative("no active student co-resident resource evidence")
            status, rc = ("SPEED_RESOURCE_GATE_PASSED", 0) if okay else ("GATE_NEGATIVE", 8)
            reason = "A1 only; 1.05 is pilot noise margin, not model quality or long-run safety"
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        reason = f"{type(exc).__name__}: {str(exc)[:250]}"
    report = {"schema": "P106B_PARALLEL_GATE_V1", "status": status, "exit_code": rc,
        "reason": reason, "input": inputs, "arms": arms, "student_active_resource": resource,
        "valid_rate_ratios": speed_gate(arms, cfg["minimum_complete_per_language"])[1] if len(arms) == 4 else [],
        "wall_sec": round(time.monotonic()-started, 3), "checkpoint_saved": False,
        "scope": "same prompts/seeds, one weight copy; per-slot context fixed, total allocation differs"}
    write_report(directory / "gate_manifest.json", report)
    print("[PARALLEL_SUMMARY] " + json.dumps(report, sort_keys=True), flush=True)
    return rc


def self_test():
    arms = [{"slots": s, "valid_student_tok_per_sec": 6 if s == 1 else 7,
             "accepted_groups": {"ko": 4, "en": 4}, "canonical_rows": 8} for s in ORDER]
    assert speed_gate(arms)[0]
    arms[2]["valid_student_tok_per_sec"] = 6.1
    assert not speed_gate(arms)[0]
    arms[2]["valid_student_tok_per_sec"] = 10
    arms[2]["canonical_rows"] = 7
    assert not speed_gate(arms)[0]
    assert settings("original")["directory"] != settings("recovery")["directory"]
    assert settings("recovery")["max_output"] == 4096
    recovered = [{**arm, "accepted_groups": {"ko": 12, "en": 12}, "canonical_rows": 24}
                 for arm in arms]
    recovered[2]["canonical_rows"] = 24
    assert speed_gate(recovered, 12)[0]
    recovered[1]["accepted_groups"]["ko"] = 11
    assert not speed_gate(recovered, 12)[0]
    print("[PASS] A1 paired order/speed/format gate; GPU NOT_RUN")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    modes = ap.add_mutually_exclusive_group(required=True)
    for name in ("self-test", "check-only", "execute"):
        modes.add_argument("--" + name, action="store_true")
    ap.add_argument("--mode", choices=("original", "recovery"), default="original")
    args = ap.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        jobs, info = check(args.mode)
        if args.check_only:
            print(json.dumps(info, sort_keys=True))
            return 0
        return execute(jobs, info)
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        print(f"[{status}] {type(exc).__name__}: {str(exc)[:250]}", file=sys.stderr)
        return rc


if __name__ == "__main__":
    raise SystemExit(main())
