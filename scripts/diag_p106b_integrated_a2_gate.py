#!/usr/bin/env python3
"""P106B Stage3fWb: A2 one-slot producer/consumer plus B2 and C-reader, one update.

This is a bounded technical wiring gate, not an SFT quality or A1 speed adoption.
The old two-slot Stage3fW and all historical output directories remain untouched.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import queue
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106b_integrated_gate import evidence_contract
from scripts.diag_p106b_online_rate5 import public_source_jobs
from scripts.diag_p106_bonsai_assets import regular, sha256_file
from scripts.diag_p106b_overlap_gate import BoundedRows
from scripts.p106b_gate_runtime import (GateNegative, TeacherSession, ToolFailure,
    code_contract, disposition, idle_before_gpu, new_directory, read_v17,
    require_report, student_inputs, teacher_inputs, wall_limit, write_report,
    THINKING_SAMPLER)
from scripts.p106b_pipeline import CandidateWriter, StudentAccumulator
from scripts.p106b_repeat4_gate import BASE_CACHE, CHECKPOINT, group_split
from scripts.p106b_shards import ShardWriter, verify

DIRECTORY = ROOT / "HF/sft_ready/p106b_teacher_sft/v28_integrated_a2_one_slot_low"
MAX_TEACHER_ATTEMPTS = 3
RETRYABLE = {"INCOMPLETE", "PARSE_ERROR", "EMPTY_DUPLICATE_OR_NESTED_FIELDS",
             "WRONG_LANGUAGE_SCREEN", "PEG_NATIVE_MISMATCH", "STUDENT_CONTEXT_REJECT",
             "EXACT_DUPLICATE"}
CARD_SAMPLER = {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                "min_p": 0.05, "presence_penalty": 0.0,
                "repeat_penalty": 1.0}
GATES = (
    ("v27_overlap_budget_recovery_low", "gate_manifest.json", "P106B_OVERLAP_GATE_V1",
     "OVERLAP_FUNCTION_GATE_PASSED", "diag_p106b_overlap_gate.py"),
    ("v20_multi_answer2_low", "gate_manifest.json", "P106B_MULTI_ANSWER_GATE_V1",
     "FORMAT_GATE_PASSED", "diag_p106b_multi_answer_gate.py"),
    ("v21_multi_answer4_low", "gate_manifest.json", "P106B_MULTI_ANSWER_GATE_V1",
     "FORMAT_GATE_PASSED", "diag_p106b_multi_answer_gate.py"),
    ("v19_repeat4_v17_pilot", "repeat4_result.json", "P106B_REPEAT4_RESULT_V1",
     "PILOT_SAFETY_PASSED", "p106b_repeat4_gate.py"),
)


def take_to_target(rows: list[dict], accepted: int, target: int = 32) -> tuple[list[dict], int]:
    """A two-answer response may cross the exact per-language row target."""
    chosen = rows[:max(0, target - accepted)]
    return chosen, len(rows) - len(chosen)


def interval_overlap(teacher: list[tuple[float, float]], student: list[tuple[float, float]]) -> bool:
    return any(a < d and c < b for a, b in teacher for c, d in student)


def retry_hint(status: str) -> str:
    if status == "INCOMPLETE":
        return ("Your previous attempt reached the output limit. Keep private reasoning and final "
                "answers concise enough to close every labeled field. Preserve facts and uncertainty.")
    return ("Your previous attempt did not yield a usable labeled pair (" + status + "). "
            "Write only the exact QUESTION, ANSWER_1 and ANSWER_2 fields. "
            "Keep distinct answers consistent with the source; do not emit JSON or ChatML.")


class RetryTeacherSession:
    """Per-attempt prompt feedback without changing historical shared writer code."""
    def __init__(self, base, feedback: str):
        self.base, self.feedback, self.key = base, feedback, base.key

    def _messages(self, messages: list[dict]) -> list[dict]:
        updated = [dict(message) for message in messages]
        if self.feedback:
            updated[0]["content"] = "Retry guidance: " + self.feedback + "\n" + updated[0]["content"]
        return updated

    def count_prompt(self, messages, per_slot, maximum):
        return self.base.count_prompt(self._messages(messages), per_slot, maximum)

    def complete(self, messages, seed, maximum):
        return self.base.complete(self._messages(messages), seed, maximum)


def request_with_retries(writer, session, job, ident: str, seed: int, journal,
                         *, per_slot: int = 6144, maximum: int = 4096) -> list[dict]:
    """Preserve each rejected attempt; never claim a retry established semantic truth."""
    feedback = ""
    for attempt in range(1, MAX_TEACHER_ATTEMPTS + 1):
        attempt_id = f"{ident}_try{attempt}"
        before = Counter(writer.counts)
        rows = writer.request(RetryTeacherSession(session, feedback), job, attempt_id,
            seed + attempt - 1, count=2, per_slot=per_slot, maximum=maximum)
        changed = [name for name, total in writer.counts.items()
                   if total - before[name] == 1]
        if len(changed) != 1:
            raise ToolFailure("retry attempt did not record exactly one raw screen status")
        status = changed[0]
        journal.append({"generation_id": attempt_id, "attempt": attempt,
            "parent_concept_id": job["parent_concept_id"],
            "status": status, "accepted_rows": len(rows),
            "prompt_feedback": feedback,
            "semantic_truth": "PSEUDO_UNVERIFIED"})
        if rows:
            return rows
        if status not in RETRYABLE:
            break
        feedback = retry_hint(status)
    return []


def check() -> tuple[list[dict], dict[str, list[dict]], dict]:
    if any(THINKING_SAMPLER.get(key) != value for key, value in CARD_SAMPLER.items()):
        raise GateNegative("teacher thinking sampler differs from pinned Bonsai model card")
    student = student_inputs()
    all_jobs, source = public_source_jobs()
    prior_rows, _ = read_v17()
    train, _val = group_split(prior_rows)
    stored = []
    for language in ("ko", "en"):
        candidates = [row for row in train if row["meta"]["language"] == language]
        if len(candidates) < 32:
            raise GateNegative("C4 train split lacks 32 replay rows per language")
        stored.extend(candidates[:32])
    blocked = {r["meta"]["parent_concept_id"].upper() for r in prior_rows}
    jobs = {language: [j for j in all_jobs[language]
            if j["parent_concept_id"].upper() not in blocked]
            for language in ("ko", "en")}
    if min(map(len, jobs.values())) < 64:
        raise GateNegative("fewer than 64 unused public jobs per language")

    prerequisites = {}
    for spec in GATES:
        path = ROOT / "HF/sft_ready/p106b_teacher_sft" / spec[0] / spec[1]
        report = require_report(path, spec[2], spec[3])
        evidence_contract(report, spec, student, source["job_deck_sha256"])
        if spec[2] != "P106B_REPEAT4_RESULT_V1":
            info = report if spec[2] == "P106B_MULTI_ANSWER_GATE_V1" else report["input"]
            if any(info.get(key) != value for key, value in teacher_inputs().items()):
                raise GateNegative("independent gate teacher binary/model changed")
        if spec[2] == "P106B_OVERLAP_GATE_V1":
            if (len(report.get("arms", [])) != 2 or not report.get("identical_generated_text")
                    or not report["arms"][1].get("actual_teacher_student_interval_overlap")):
                raise GateNegative("A2b functional/identical-text evidence absent")
        if spec[2] == "P106B_REPEAT4_RESULT_V1":
            if (report.get("checkpoint") != CHECKPOINT.relative_to(ROOT).as_posix()
                    or not regular(CHECKPOINT)
                    or sha256_file(CHECKPOINT) != report.get("checkpoint_sha256")):
                raise GateNegative("C4 checkpoint evidence absent/changed")
            if sha256_file(BASE_CACHE / "val.bin") != report["input"]["base_val_sha256"]:
                raise GateNegative("C4 base validation source changed")
        prerequisites[path.relative_to(ROOT).as_posix()] = sha256_file(path)

    new_directory(DIRECTORY)
    return stored, jobs, {**student, **teacher_inputs(), "source": source,
        "code_sha256": code_contract("diag_p106b_integrated_a2_gate.py",
                                     "diag_p106b_integrated_gate.py"),
        "prerequisites": prerequisites, "A1_two_slot_speed": "GATE_NEGATIVE_NOT_REQUIRED",
        "stored_rows": 64, "fresh_rows": 64, "teacher_slots": 1,
        "context_total": 6144, "max_output": 4096, "variants_per_question": 2,
        "source_cap_per_language": 64, "micro": 8, "accum": 16,
        "exact_full_128_update": True, "checkpoint_on": True,
        "optimizer_updates": 1, "C_epoch_reader": "epoch1 only; not four completed epochs",
        "teacher_sampler": {**THINKING_SAMPLER, "reasoning_effort": "low"},
        "teacher_retry": {"max_attempts_per_concept": MAX_TEACHER_ATTEMPTS,
            "retryable_statuses": sorted(RETRYABLE), "preserve_every_attempt": True},
        "teacher_output_contract": "tagged QUESTION/ANSWER_1/ANSWER_2 only; parser and canonical ChatML owned by code",
        "quality": "NOT_RUN", "formal_train_ready": False}


def execute(stored: list[dict], jobs: dict[str, list[dict]], inputs: dict) -> int:
    idle_before_gpu()
    DIRECTORY.mkdir(parents=True, exist_ok=False)
    writer = CandidateWriter(DIRECTORY, inputs)
    training = ShardWriter(DIRECTORY, "training")
    retry_journal = ShardWriter(DIRECTORY, "retry_journal")
    stop, done = threading.Event(), threading.Event()
    buffer = BoundedRows(stop)
    counts, next_index = {"ko": 0, "en": 0}, {"ko": 0, "en": 0}
    errors, fresh, teacher_windows, student_windows = [], [], [], []
    dropped_surplus = 0
    student = session = producer = update = None
    status, rc, reason = "PARTIAL", 9, "not started"
    started, training_count = time.monotonic(), 0
    try:
        with wall_limit(7200):
            student = StudentAccumulator()
            with TeacherSession(6144, 1) as session:
                student.monitor = session.check_monitor

                def produce() -> None:
                    nonlocal dropped_surplus
                    try:
                        while min(counts.values()) < 32 and not stop.is_set():
                            for language in ("ko", "en"):
                                if counts[language] >= 32 or stop.is_set():
                                    continue
                                index = next_index[language]
                                if index >= 64:
                                    raise GateNegative(f"fresh {language} source cap64 exhausted")
                                next_index[language] += 1
                                t0 = time.monotonic()
                                rows = request_with_retries(writer, session, jobs[language][index],
                                    f"integrated_a2_{language}_{index:03d}", 20261030 + index,
                                    retry_journal, per_slot=6144, maximum=4096)
                                teacher_windows.append((t0, time.monotonic()))
                                chosen, surplus = take_to_target(rows, counts[language])
                                dropped_surplus += surplus
                                for row in chosen:
                                    fresh.append(row)
                                    buffer.put(row)
                                    counts[language] += 1
                    except Exception as exc:
                        errors.append(exc)
                    finally:
                        done.set()

                producer = threading.Thread(target=produce,
                    name="p106b-a2-integrated-producer", daemon=True)
                producer.start()

                def consume(block: list[dict]) -> None:
                    nonlocal training_count
                    t0 = time.monotonic()
                    student.add(block)
                    student_windows.append((t0, time.monotonic()))
                    for row in block:
                        training.append(row)
                        training_count += 1

                # C-reader epoch1. The teacher concurrently creates fresh public rows.
                for start in range(0, len(stored), 8):
                    consume(stored[start:start + 8])
                block = []
                while not done.is_set() or not buffer.queue.empty():
                    if errors:
                        raise errors[0]
                    try:
                        block.append(buffer.get())
                    except queue.Empty:
                        continue
                    if len(block) == 8:
                        consume(block)
                        block = []
                if errors:
                    raise errors[0]
                if block or counts != {"ko": 32, "en": 32} or training_count != 128:
                    raise GateNegative("fresh64/replay64 exact accumulation incomplete")
                if not interval_overlap(teacher_windows, student_windows):
                    raise GateNegative("A2 single-slot teacher/student intervals did not overlap")
                update = student.finish(require_full=True)
                session.require_valid_resources()
            status, rc = "A2_INTEGRATED_ONE_UPDATE_PASSED", 0
            reason = "one-slot resource/mask/provenance gate only; student answer quality not evaluated"
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        reason = f"{type(exc).__name__}: {str(exc)[:250]}"
    finally:
        stop.set()
        if producer is not None:
            producer.join(timeout=250)
        if producer is not None and producer.is_alive():
            status, rc, reason = "TOOL_FAILURE", 9, "owned producer did not stop"
        metrics = writer.close()
        if retry_journal._total_rows:
            retry_spec = retry_journal.close(lineage=inputs)
            verify(DIRECTORY, retry_spec)
            metrics["retry_journal_concat_sha256"] = retry_spec["concat_sha256"]
            metrics["teacher_attempts"] = retry_spec["rows"]
        if training_count:
            spec = training.close(lineage=inputs)
            verify(DIRECTORY, spec)
            metrics["training_concat_sha256"] = spec["concat_sha256"]
        report = {"schema": "P106B_INTEGRATED_A2_GATE_V1", "status": status,
            "exit_code": rc, "reason": reason, "input": inputs, **metrics,
            "student": update, "actually_trained_rows": 128 if update else 0,
            "backprop_rows": student.rows if student is not None else 0,
            "replay_rows": 64 if update else 0, "fresh_rows": len(fresh),
            "fresh_counts": counts, "source_visits": next_index,
            "dropped_surplus_rows": dropped_surplus,
            "unique_parent_concepts": len({r["meta"]["parent_concept_id"]
                for r in stored + fresh}),
            "actual_teacher_student_interval_overlap": interval_overlap(
                teacher_windows, student_windows),
            "queue_peak_bytes": buffer.peak, "server": session.evidence() if session else None,
            "whole_wall_sec": time.monotonic() - started, "checkpoint_saved": False,
            "quality": "NOT_RUN", "formal_train_ready": False}
        write_report(DIRECTORY / "gate_manifest.json", report)
        print("[INTEGRATED_A2_SUMMARY] " + json.dumps(report, sort_keys=True), flush=True)
    return rc


def self_test() -> None:
    assert len(GATES) == 4 and GATES[0][0] == "v27_overlap_budget_recovery_low"
    assert all("parallel" not in spec[0] for spec in GATES)
    assert take_to_target([1, 2], 31) == ([1], 1)
    assert take_to_target([1, 2], 32) == ([], 2)
    assert interval_overlap([(1.0, 3.0)], [(2.0, 4.0)])
    assert not interval_overlap([(1.0, 2.0)], [(2.0, 3.0)])
    assert MAX_TEACHER_ATTEMPTS == 3 and "INCOMPLETE" in RETRYABLE
    assert all(THINKING_SAMPLER.get(key) == value for key, value in CARD_SAMPLER.items())
    assert "close every labeled field" in retry_hint("INCOMPLETE")
    class FakeSession:
        key = "fixture"
        def __init__(self):
            self.prompts = []
        def count_prompt(self, messages, _slot, _maximum):
            self.prompts.append(messages[0]["content"])
            return {"decision": "DIRECT"}
        def complete(self, _messages, _seed, _maximum):
            return {}
    class FakeWriter:
        def __init__(self):
            self.counts = Counter()
        def request(self, session, _job, _ident, _seed, **_kwargs):
            session.count_prompt([{"role": "system", "content": "fields"}], 6144, 4096)
            status = "INCOMPLETE" if not self.counts else "MULTI_FORMAT_READY"
            self.counts[status] += 1
            return [] if status == "INCOMPLETE" else [{"fixture": True}]
    fixture = FakeSession()
    attempts = []
    assert request_with_retries(FakeWriter(), fixture,
        {"parent_concept_id": "A" * 64}, "fixture", 10, attempts) == [{"fixture": True}]
    assert len(attempts) == 2 and attempts[0]["status"] == "INCOMPLETE"
    assert "Retry guidance" in fixture.prompts[1]
    print("[PASS] A2-only integration exact128/one-slot/overlap contract; GPU NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for name in ("self-test", "check-only", "execute"):
        modes.add_argument("--" + name, action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        stored, jobs, inputs = check()
        if args.check_only:
            print(json.dumps(inputs, sort_keys=True))
            return 0
        return execute(stored, jobs, inputs)
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        print(f"[{status}] {type(exc).__name__}: {str(exc)[:250]}", file=sys.stderr)
        return rc


if __name__ == "__main__":
    raise SystemExit(main())
