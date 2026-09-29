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

DIRECTORY = ROOT / "HF/sft_ready/p106b_teacher_sft/v22_parallel_abba_low"
PER_SLOT, MAX_OUTPUT = 3072, 2048
ORDER = (1, 2, 2, 1)


def speed_gate(arms):
    if len(arms) != 4 or tuple(a["slots"] for a in arms) != ORDER:
        raise ValueError("ABBA comparison incomplete")
    gains = []
    for one, two in ((arms[0], arms[1]), (arms[3], arms[2])):
        if one["valid_student_tok_per_sec"] <= 0:
            return False, [0.0]
        gains.append(two["valid_student_tok_per_sec"] / one["valid_student_tok_per_sec"])
    passed = (min(gains) > 1.05 and all(min(a["accepted_groups"].get("ko", 0),
                a["accepted_groups"].get("en", 0)) >= 3 for a in arms)
              and all(arms[b]["canonical_rows"] >= arms[a]["canonical_rows"] for a, b in ((0, 1), (3, 2))))
    return passed, gains


def check():
    jobs, source = fixed_jobs()
    student = student_inputs()
    read_v17()
    new_directory(DIRECTORY)
    return jobs, {**student, **teacher_inputs(), "code_sha256": code_contract("diag_p106b_parallel_gate.py"),
        "source": source, "order": list(ORDER), "jobs_per_arm": len(jobs),
        "per_slot_context": PER_SLOT, "max_output": MAX_OUTPUT,
        "speed_threshold": "both order-paired valid student tok/s ratios >1.05; no fewer accepted rows",
        "student_micro": 8, "student_accum_limit": 16, "student_checkpoint_on": True,
        "teacher_copies": 1, "quality": "NOT_RUN", "formal_train_ready": False}


def execute(jobs, inputs):
    idle_before_gpu()
    DIRECTORY.mkdir(parents=True, exist_ok=False)
    arms, resource = [], None
    status, rc, reason = "PARTIAL", 9, "not started"
    started = time.monotonic()
    student = None
    try:
        with wall_limit(7200):
            student = StudentAccumulator()
            rows = read_v17()[0]
            for index, slots in enumerate(ORDER):
                path = DIRECTORY / f"arm{index+1}_slots{slots}"
                path.mkdir(exist_ok=False)
                writer = CandidateWriter(path, inputs)
                session = None
                request_wall = None
                try:
                    with TeacherSession(PER_SLOT * slots, slots) as session:
                        begin = time.monotonic()
                        with ThreadPoolExecutor(max_workers=slots) as pool:
                            futures = [pool.submit(writer.request, session, job,
                                f"a1_{index}_{j:02d}", 20260930+j,
                                per_slot=PER_SLOT, maximum=MAX_OUTPUT) for j, job in enumerate(jobs)]
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
            path = DIRECTORY / "active_resource_probe"
            path.mkdir(exist_ok=False)
            probe = CandidateWriter(path, inputs)
            session = None
            try:
                with TeacherSession(PER_SLOT * 2, 2) as session, ThreadPoolExecutor(max_workers=2) as pool:
                    student.monitor = session.check_monitor
                    pending = [pool.submit(probe.request, session, jobs[j], f"a1_resource_{j}",
                        20260930+j, per_slot=PER_SLOT, maximum=MAX_OUTPUT) for j in range(2)]
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
            okay, gains = speed_gate(arms)
            if not resource:
                raise GateNegative("no active student co-resident resource evidence")
            status, rc = ("SPEED_RESOURCE_GATE_PASSED", 0) if okay else ("GATE_NEGATIVE", 8)
            reason = "A1 only; 1.05 is pilot noise margin, not model quality or long-run safety"
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        reason = f"{type(exc).__name__}: {str(exc)[:250]}"
    report = {"schema": "P106B_PARALLEL_GATE_V1", "status": status, "exit_code": rc,
        "reason": reason, "input": inputs, "arms": arms, "student_active_resource": resource,
        "valid_rate_ratios": speed_gate(arms)[1] if len(arms) == 4 else [],
        "wall_sec": round(time.monotonic()-started, 3), "checkpoint_saved": False,
        "scope": "same prompts/seeds, one weight copy; per-slot context fixed, total allocation differs"}
    write_report(DIRECTORY / "gate_manifest.json", report)
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
    print("[PASS] A1 paired order/speed/format gate; GPU NOT_RUN")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    modes = ap.add_mutually_exclusive_group(required=True)
    for name in ("self-test", "check-only", "execute"):
        modes.add_argument("--" + name, action="store_true")
    args = ap.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        jobs, info = check()
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
