#!/usr/bin/env python3
"""After independent A1/A2/B2/B4/C4: combined pipeline, exactly one optimizer update.

C's epoch reader is at epoch1 only. This gate is not four completed epochs,
300M training, or verified teacher truth. User owns all model execution.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import queue
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_gate_runtime import (TeacherSession, require_report, new_directory,
    student_inputs, read_v17, write_report, idle_before_gpu, disposition, wall_limit,
    code_contract, ToolFailure, GateNegative, teacher_inputs)
from scripts.diag_p106b_online_rate5 import public_source_jobs
from scripts.diag_p106_bonsai_assets import sha256_file, regular
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_pipeline import StudentAccumulator, CandidateWriter
from scripts.diag_p106b_overlap_gate import BoundedRows
from scripts.p106b_repeat4_gate import group_split

DIRECTORY = ROOT / "HF/sft_ready/p106b_teacher_sft/v24_integrated1_low"
GATES = (
    ("v22_parallel_abba_low", "gate_manifest.json", "P106B_PARALLEL_GATE_V1", "SPEED_RESOURCE_GATE_PASSED", "diag_p106b_parallel_gate.py"),
    ("v23_overlap_low", "gate_manifest.json", "P106B_OVERLAP_GATE_V1", "OVERLAP_FUNCTION_GATE_PASSED", "diag_p106b_overlap_gate.py"),
    ("v20_multi_answer2_low", "gate_manifest.json", "P106B_MULTI_ANSWER_GATE_V1", "FORMAT_GATE_PASSED", "diag_p106b_multi_answer_gate.py"),
    ("v21_multi_answer4_low", "gate_manifest.json", "P106B_MULTI_ANSWER_GATE_V1", "FORMAT_GATE_PASSED", "diag_p106b_multi_answer_gate.py"),
    ("v19_repeat4_v17_pilot", "repeat4_result.json", "P106B_REPEAT4_RESULT_V1", "PILOT_SAFETY_PASSED", "p106b_repeat4_gate.py"),
)


def evidence_contract(report, spec, student, deck_sha):
    # Four reports have different layouts, but the prerequisite identities agree.
    info = report if spec[2] == "P106B_MULTI_ANSWER_GATE_V1" else report["input"]
    if any(info.get(key) != value for key, value in student.items()):
        raise GateNegative("independent gate parent/tokenizer differs")
    if info.get("code_sha256") != code_contract(spec[4]):
        raise GateNegative("independent gate code source changed; historical PASS not transferable")
    if spec[2] != "P106B_REPEAT4_RESULT_V1" and info.get("source", {}).get("job_deck_sha256") != deck_sha:
        raise GateNegative("independent gate source deck differs")


def check():
    student = student_inputs()
    all_jobs, source = public_source_jobs()
    prior_rows, _ = read_v17()
    train, val = group_split(prior_rows)
    stored = []
    for language in ("ko", "en"):
        candidates = [row for row in train if row["meta"]["language"] == language]
        if len(candidates) < 32:
            raise GateNegative("C4 train split lacks32 replay rows per language")
        stored.extend(candidates[:32])
    blocked = {r["meta"]["parent_concept_id"].upper() for r in prior_rows}
    jobs = {lang: [job for job in all_jobs[lang] if job["parent_concept_id"].upper() not in blocked]
            for lang in ("ko", "en")}
    if min(map(len, jobs.values())) < 64:
        raise GateNegative("too few unused public train concepts for finite fresh generation")
    prerequisites = {}
    for spec in GATES:
        path = ROOT / "HF/sft_ready/p106b_teacher_sft" / spec[0] / spec[1]
        report = require_report(path, spec[2], spec[3])
        evidence_contract(report, spec, student, source["job_deck_sha256"])
        if spec[2] != "P106B_REPEAT4_RESULT_V1":
            gate_input = report if spec[2] == "P106B_MULTI_ANSWER_GATE_V1" else report["input"]
            if any(gate_input.get(k) != v for k, v in teacher_inputs().items()):
                raise GateNegative("independent gate teacher binary/model changed")
        prerequisites[path.relative_to(ROOT).as_posix()] = sha256_file(path)
        if spec[2] == "P106B_REPEAT4_RESULT_V1":
            from scripts.p106b_repeat4_gate import CHECKPOINT
            ckpt = CHECKPOINT
            if report["checkpoint"] != ckpt.relative_to(ROOT).as_posix():
                raise GateNegative("C4 checkpoint target differs from exact namespace")
            if not regular(ckpt) or sha256_file(ckpt) != report["checkpoint_sha256"]:
                raise GateNegative("C4 checkpoint evidence absent/changed")
            from scripts.p106b_repeat4_gate import BASE_CACHE
            if sha256_file(BASE_CACHE / "val.bin") != report["input"]["base_val_sha256"]:
                raise GateNegative("C4 forgetting base validation changed")
    new_directory(DIRECTORY)
    return stored, jobs, {**student, **teacher_inputs(), "source": source,
        "code_sha256": code_contract("diag_p106b_integrated_gate.py"), "prerequisites": prerequisites,
        "stored_rows": 64, "fresh_variant_rows": 64, "variants_per_question": 2,
        "teacher_slots": 2, "context_total": 12288, "per_slot_context": 6144, "max_output": 4096,
        "micro": 8, "accum": 16, "checkpoint_on": True, "optimizer_updates": 1,
        "C_epoch_reader": "epoch1 of maximum4; this gate does not complete4epoch",
        "formal_train_ready": False, "student_quality": "NOT_RUN"}


def execute(stored, jobs, inputs):
    idle_before_gpu()
    DIRECTORY.mkdir(parents=True, exist_ok=False)
    writer = CandidateWriter(DIRECTORY, inputs)
    training = ShardWriter(DIRECTORY, "training")
    stop, done = threading.Event(), threading.Event()
    buffer = BoundedRows(stop)
    errors, fresh = [], []
    counts = {"ko": 0, "en": 0}
    next_index = {"ko": 0, "en": 0}
    student, session, producer, update = None, None, None, None
    status, rc, reason = "PARTIAL", 9, "not started"
    started = time.monotonic()
    training_count = 0
    try:
        with wall_limit(7200):
            student = StudentAccumulator()
            with TeacherSession(12288, 2) as session:
                student.monitor = session.check_monitor
                def produce():
                    try:
                        with ThreadPoolExecutor(max_workers=2) as pool:
                            while min(counts.values()) < 32 and not stop.is_set():
                                requests = []
                                for lang in ("ko", "en"):
                                    if counts[lang] >= 32:
                                        continue
                                    index = next_index[lang]
                                    if index >= 64:
                                        raise GateNegative(f"fresh {lang}64-source cap exhausted; no refill with old/rejected rows")
                                    next_index[lang] += 1
                                    requests.append((lang, pool.submit(writer.request, session, jobs[lang][index],
                                        f"integrated1_{lang}_{index:03d}", 20261001+index,
                                        count=2, per_slot=6144, maximum=4096)))
                                for lang, future in requests:
                                    rows = future.result()
                                    for row in rows:
                                        fresh.append(row)
                                        buffer.put(row)
                                        counts[lang] += 1
                    except Exception as exc:
                        errors.append(exc)
                    finally:
                        done.set()
                producer = threading.Thread(target=produce, name="p106b-integrated-producer", daemon=True)
                producer.start()
                # Consume stored C-reader epoch1 while the two teacher slots work.
                for start in range(0, len(stored), 8):
                    rows = stored[start:start+8]
                    student.add(rows)
                    for row in rows:
                        training.append(row)
                        training_count += 1
                batch = []
                while not done.is_set() or not buffer.queue.empty():
                    if errors:
                        raise errors[0]
                    try:
                        batch.append(buffer.get())
                    except queue.Empty:
                        continue
                    if len(batch) == 8:
                        student.add(batch)
                        for row in batch:
                            training.append(row)
                            training_count += 1
                        batch = []
                if errors:
                    raise errors[0]
                if batch or counts != {"ko": 32, "en": 32}:
                    raise GateNegative("fresh128 accumulation incomplete; optimizer not applied")
                update = student.finish(require_full=True)
                session.require_valid_resources()
            status, rc = "INTEGRATED_ONE_UPDATE_PASSED", 0
            reason = "pipeline resource/mask/provenance only; exact4epoch completed only by independent C4"
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        reason = f"{type(exc).__name__}: {str(exc)[:250]}"
    finally:
        stop.set()
        if producer is not None:
            producer.join(timeout=250)
        if producer is not None and producer.is_alive():
            status, rc, reason = "TOOL_FAILURE", 9, "producer still alive; not a complete evidence artifact"
        metrics = writer.close()
        if training_count:
            spec = training.close(lineage=inputs)
            verify(DIRECTORY, spec)
            metrics["training_concat_sha256"] = spec["concat_sha256"]
        report = {"schema": "P106B_INTEGRATED_GATE_V1", "status": status, "exit_code": rc,
            "reason": reason, "input": inputs, **metrics, "student": update,
            "actually_trained_rows": 128 if update else 0, "replay_rows": 64 if update else 0,
            "backprop_rows": student.rows if student is not None else 0,
            "unique_parent_concepts": len({row["meta"]["parent_concept_id"] for row in stored + fresh}),
            "fresh_rows": len(fresh), "fresh_counts": counts, "source_visits": next_index,
            "queue_peak_bytes": buffer.peak, "server": session.evidence() if session else None,
            "whole_wall_sec": time.monotonic()-started, "checkpoint_saved": False,
            "quality": "NOT_RUN", "formal_train_ready": False}
        write_report(DIRECTORY / "gate_manifest.json", report)
        print("[INTEGRATED_SUMMARY] " + json.dumps(report, sort_keys=True), flush=True)
    return rc


def self_test():
    assert len(GATES) == 5 and all("medium" not in spec[0] for spec in GATES)
    info = {"parent_sha256": "A", "tokenizer_sha256": "B", "code_sha256": code_contract(GATES[0][4]),
            "source": {"job_deck_sha256": "C"}}
    evidence_contract({"input": info}, GATES[0], {"parent_sha256": "A", "tokenizer_sha256": "B"}, "C")
    try:
        evidence_contract({"input": info}, GATES[0], {"parent_sha256": "WRONG"}, "C")
    except GateNegative:
        pass
    else:
        raise AssertionError("changed parent admitted")
    print("[PASS] integration five evidence artifacts/four methods/one-update semantics; GPU NOT_RUN")


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
        stored, jobs, info = check()
        if args.check_only:
            print(json.dumps(info, sort_keys=True))
            return 0
        return execute(stored, jobs, info)
    except (Exception, KeyboardInterrupt) as exc:
        status, code = disposition(exc)
        print(f"[{status}] {type(exc).__name__}: {str(exc)[:250]}", file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
