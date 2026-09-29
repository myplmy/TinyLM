#!/usr/bin/env python3
"""A2: serial vs durable producer/consumer overlap, one teacher/one student."""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
from pathlib import Path
import queue
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_gate_runtime import (TeacherSession, fixed_jobs, student_inputs, new_directory,
    idle_before_gpu, write_report, wall_limit, disposition, GateNegative, ToolFailure, code_contract, teacher_inputs)
from scripts.p106b_pipeline import CandidateWriter, StudentAccumulator

DIRECTORY = ROOT / "HF/sft_ready/p106b_teacher_sft/v23_overlap_low"


class BoundedRows:
    """Backpressure: at most32 rows/20MB, far below the approved10GB RAM ceiling."""
    def __init__(self, stop, max_bytes=20_000_000):
        self.stop, self.max_bytes = stop, max_bytes
        self.queue = queue.Queue(maxsize=32)
        self.lock = threading.Lock()
        self.bytes = self.peak = 0

    def put(self, row):
        size = len(json.dumps(row, ensure_ascii=False).encode())
        if size > self.max_bytes:
            raise ValueError("single queued row exceeds RAM budget")
        while not self.stop.is_set():
            reserved = False
            with self.lock:
                if self.bytes + size <= self.max_bytes:
                    self.bytes += size
                    self.peak = max(self.peak, self.bytes)
                    reserved = True
            if reserved:
                try:
                    self.queue.put((row, size), timeout=.2)
                    return
                except queue.Full:
                    with self.lock:
                        self.bytes -= size
            self.stop.wait(.05)
        raise ToolFailure("producer stopped; partial corpus preserved")

    def get(self, timeout=.2):
        row, size = self.queue.get(timeout=timeout)
        with self.lock:
            self.bytes -= size
        return row


def content_sha(rows):
    # Ignore generation/arm IDs; compare same actual text in source order.
    return hashlib.sha256(json.dumps([row["messages"] for row in rows],
        ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper()


def run_arm(path, jobs, inputs, overlap):
    path.mkdir(exist_ok=False)
    writer = CandidateWriter(path, inputs)
    student = StudentAccumulator()
    stop, finished = threading.Event(), threading.Event()
    buffer = BoundedRows(stop)
    errors, accepted, teacher_windows, student_windows = [], [], [], []
    update, session, producer = None, None, None
    timer = phase_wall = None
    def consume_block(block):
        t0 = time.monotonic()
        student.add(block)
        student_windows.append((t0, time.monotonic()))
    try:
        with TeacherSession(3072) as session:
            student.monitor = session.check_monitor
            def produce():
                try:
                    for index, job in enumerate(jobs):
                        if stop.is_set():
                            break
                        t0 = time.monotonic()
                        rows = writer.request(session, job, f"a2_{'overlap' if overlap else 'serial'}_{index:02d}",
                            20260930+index)
                        teacher_windows.append((t0, time.monotonic()))
                        accepted.extend(rows)
                        if overlap:
                            for row in rows:
                                buffer.put(row)
                except Exception as exc:
                    errors.append(exc)
                finally:
                    finished.set()
            timer = time.monotonic()
            if overlap:
                producer = threading.Thread(target=produce, name="p106b-owned-producer", daemon=True)
                producer.start()
                block = []
                while not finished.is_set() or not buffer.queue.empty():
                    if errors:
                        raise errors[0]
                    try:
                        block.append(buffer.get())
                    except queue.Empty:
                        continue
                    if len(block) == 8:
                        consume_block(block)
                        block = []
                if block:
                    consume_block(block)
            else:
                produce()
                for start in range(0, len(accepted), 8):
                    consume_block(accepted[start:start+8])
            if errors:
                raise errors[0]
            if min(writer.accepted.get("ko", 0), writer.accepted.get("en", 0)) < 6:
                raise GateNegative("A2 fewer than6/8 question groups in either language")
            update = student.finish()
            phase_wall = time.monotonic() - timer
            session.require_valid_resources()
    finally:
        stop.set()
        if producer is not None:
            producer.join(timeout=250)
        if producer is not None and producer.is_alive():
            raise ToolFailure("owned producer did not stop; no completed arm evidence")
        metrics = writer.close()
        overlaps = any(a < d and c < b for a, b in teacher_windows for c, d in student_windows)
        result = {"overlap": overlap, **metrics, "student": update,
            "phase_wall_sec": phase_wall if phase_wall is not None else (time.monotonic()-timer if timer is not None else None),
            "actual_teacher_student_interval_overlap": overlaps,
            "queue_peak_bytes": buffer.peak, "queue_max_bytes": buffer.max_bytes,
            "text_sha256": content_sha(accepted), "accepted_rows": len(accepted),
            "server": session.evidence() if session else None,
            "timer_scope": "health to optimizer; cold compile included, startup excluded"}
        write_report(path / "arm_manifest.json", result)
        torch = student.torch
        del student
        gc.collect()
        torch.cuda.empty_cache()
    return result


def check():
    jobs, source = fixed_jobs(8)
    student = student_inputs()
    new_directory(DIRECTORY)
    return jobs, {**student, **teacher_inputs(), "code_sha256": code_contract("diag_p106b_overlap_gate.py"),
        "source": source, "question_groups": 16, "teacher_slots": 1,
        "student_micro": 8, "accum_limit": 16, "exact_full_128_update": False,
        "limit": "partial up-to16-row resource update per arm, no row refill; effective targets reported",
        "student_quality": "NOT_RUN", "formal_train_ready": False}


def execute(jobs, inputs):
    idle_before_gpu()
    DIRECTORY.mkdir(parents=True, exist_ok=False)
    arms = []
    status, rc, reason = "PARTIAL", 9, "not started"
    started = time.monotonic()
    try:
        with wall_limit(7200):
            for name, overlap in (("serial", False), ("overlap", True)):
                arms.append(run_arm(DIRECTORY / name, jobs, inputs, overlap))
            if not arms[1]["actual_teacher_student_interval_overlap"]:
                raise GateNegative("A2 did not actually overlap intervals")
            status, rc, reason = "OVERLAP_FUNCTION_GATE_PASSED", 0, "actual overlapping durable queue verified; not speed/quality adoption"
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        reason = f"{type(exc).__name__}: {str(exc)[:250]}"
    comparable = len(arms) == 2 and arms[0]["text_sha256"] == arms[1]["text_sha256"]
    ratio = arms[0]["phase_wall_sec"] / arms[1]["phase_wall_sec"] if comparable else None
    report = {"schema": "P106B_OVERLAP_GATE_V1", "status": status, "exit_code": rc,
        "reason": reason, "input": inputs, "arms": arms, "identical_generated_text": comparable,
        "serial_over_overlap_wall_ratio": ratio, "causal_speed_claim": False,
        "wall_sec": time.monotonic()-started, "limit": "fixed serial-first order/cold compile remain; functional gate only"}
    write_report(DIRECTORY / "gate_manifest.json", report)
    print("[OVERLAP_SUMMARY] " + json.dumps(report, sort_keys=True), flush=True)
    return rc


def self_test():
    stop = threading.Event()
    buffer = BoundedRows(stop, 128)
    row = {"text": "한국어 English"}
    buffer.put(row)
    assert buffer.peak <= 128 and buffer.get() == row and buffer.bytes == 0
    assert content_sha([{"messages": [row], "meta": {"id": 1}}]) == content_sha([{"messages": [row], "meta": {"id": 2}}])
    stop.set()
    try:
        buffer.put(row)
    except ToolFailure:
        pass
    else:
        raise AssertionError("stopped queue accepted a row")
    print("[PASS] A2 bounded queue/stop/content comparison; model/GPU NOT_RUN")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    modes = ap.add_mutually_exclusive_group(required=True)
    for name in ("self-test", "check-only", "execute"):
        modes.add_argument("--"+name, action="store_true")
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
        status, code = disposition(exc)
        print(f"[{status}] {type(exc).__name__}: {str(exc)[:250]}", file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
