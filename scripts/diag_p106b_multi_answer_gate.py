#!/usr/bin/env python3
"""P106B B2/B4: one question -> multiple final answers, user GPU only."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_gate_runtime import (TeacherSession, fixed_jobs, new_directory,
    student_inputs, idle_before_gpu, write_report, disposition, MODEL_SHA256,
    TOKENIZER, TOKENIZER_SHA256, PrerequisiteHold, ToolFailure, wall_limit, code_contract, teacher_inputs)
from scripts.p106b_multi_answer import multi_prompt, parse_multi, wrap_multi, self_test
from scripts.p106b_http_errors import capture_http_error
from scripts.p106b_shards import ShardWriter, verify
from scripts.diag_p106_bonsai_assets import regular, sha256_file
from scripts.train_sft_p090 import encode_records


def output(count: int) -> Path:
    return ROOT / f"HF/sft_ready/p106b_teacher_sft/v{20 if count == 2 else 21}_multi_answer{count}_low"


def check(count: int) -> tuple[list[dict], dict]:
    jobs, source = fixed_jobs()
    student = student_inputs()
    new_directory(output(count))
    if count == 4:
        path = output(2) / "gate_manifest.json"
        if not regular(path):
            raise PrerequisiteHold("B2 multi-answer2 user result required before B4")
        prior = json.loads(path.read_text(encoding="utf-8"))
        if (prior.get("status") != "FORMAT_GATE_PASSED"
                or prior.get("source", {}).get("job_deck_sha256") != source["job_deck_sha256"]):
            raise PrerequisiteHold("B2 format/source gate not passed")
        for name in ("raw", "canonical"):
            manifest_path = output(2) / f"{name}_shards_manifest.json"
            if not regular(manifest_path):
                raise ValueError("B2 shard manifest absent/linked")
            verify(output(2), json.loads(manifest_path.read_text(encoding="utf-8")))
    return jobs, {**student, **teacher_inputs(), "code_sha256": code_contract("diag_p106b_multi_answer_gate.py"),
        "source": source, "jobs": len(jobs), "variants_per_question": count,
        "context": 6144 if count == 2 else 12288,
        "max_output": 4096 if count == 2 else 8192,
        "effort": "low", "teacher_gpu": "NOT_RUN", "student_training": "NOT_RUN",
        "semantic_consistency": "NOT_RUN", "formal_train_ready": False}


def execute(count: int, jobs: list[dict], inputs: dict) -> int:
    from tokenizers import Tokenizer
    idle_before_gpu()
    directory = output(count)
    directory.mkdir(parents=True, exist_ok=False)
    raw = ShardWriter(directory, "raw")
    canonical = ShardWriter(directory, "canonical")
    accepted = Counter()
    raw_count = rows_written = tokens = targets = completion = 0
    wall = 0.0
    status, rc, reason = "PARTIAL", 9, "not started"
    session = None
    started = time.monotonic()
    tok = Tokenizer.from_file(str(TOKENIZER))
    try:
        with wall_limit(3600), TeacherSession(inputs["context"]) as session:
            for index, job in enumerate(jobs):
                messages = multi_prompt(job, count)
                admission = session.count_prompt(messages, inputs["context"], inputs["max_output"])
                record = {"job_id": job["job_id"], "source": job, "admission": admission,
                          "generation_id": f"multi{count}_{index:02d}", "accepted_for_training": False}
                if admission["decision"] == "DIRECT":
                    t0 = time.monotonic()
                    try:
                        reply = session.complete(messages, 20260930 + index, inputs["max_output"])
                        parsed = parse_multi(reply, count, job["target_language"])
                        record["teacher"] = parsed
                        record["screen_status"] = parsed["status"]
                        completion += parsed["usage"].get("completion_tokens", 0) or 0
                        if parsed["parsed"] is not None:
                            rows = wrap_multi(job, parsed, record["generation_id"], MODEL_SHA256,
                                f"{directory.relative_to(ROOT)}/raw_shards_manifest.json#{record['generation_id']}")
                            try:
                                encoded = encode_records(rows, tok, 1024, 32768)
                            except ValueError as exc:
                                record["screen_status"] = "STUDENT_CONTEXT_REJECT"
                                record["screen_error"] = str(exc)[:180]
                            else:
                                for row in rows:
                                    canonical.append(row)
                                    rows_written += 1
                                tokens += sum(len(item[0]) for item in encoded)
                                targets += sum(item[2] for item in encoded)
                                accepted[job["target_language"]] += 1
                    except HTTPError as exc:
                        error = capture_http_error(exc, session.key)
                        record.update(backend_error=error, screen_status=error["classification"])
                        if error["classification"] != "PEG_NATIVE_MISMATCH":
                            raw.append(record)
                            raw_count += 1
                            raise ToolFailure("unknown teacher backend error") from exc
                    wall += time.monotonic() - t0
                else:
                    record["screen_status"] = admission["decision"]
                raw.append(record)
                raw_count += 1
                print("[MULTI_ITEM] " + json.dumps({"index": index, "answers": count,
                    "language": job["target_language"], "status": record["screen_status"],
                    "accepted_question_groups": dict(accepted), "student_rows": rows_written}), flush=True)
            session.require_valid_resources()
            status = "FORMAT_GATE_PASSED" if min(accepted.get("ko", 0), accepted.get("en", 0)) >= 3 else "GATE_NEGATIVE"
            rc = 0 if status == "FORMAT_GATE_PASSED" else 8
            reason = "same-question variants are not independent knowledge; semantic/contradiction review still required"
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        reason = f"{type(exc).__name__}: {str(exc)[:250]}"
    finally:
        if raw_count:
            verify(directory, raw.close(lineage=inputs))
        if rows_written:
            verify(directory, canonical.close(lineage=inputs))
        report = {"schema": "P106B_MULTI_ANSWER_GATE_V1", "status": status, "exit_code": rc,
            "reason": reason, **inputs, "source": inputs["source"], "accepted_groups": dict(accepted),
            "canonical_rows": rows_written, "processed_student_tokens": tokens,
            "assistant_targets": targets, "teacher_completion_tokens": completion,
            "teacher_request_wall_sec": round(wall, 3), "whole_wall_sec": round(time.monotonic() - started, 3),
            "server": session.evidence() if session else None, "student_updates": 0,
            "teacher_gpu": "EXECUTED_USER_GATE" if session is not None else "NOT_RUN",
            "claims": "FORMAT/WRAPPING ONLY; teacher truth and learner quality NOT_RUN"}
        write_report(directory / "gate_manifest.json", report)
        print("[MULTI_SUMMARY] " + json.dumps(report, sort_keys=True), flush=True)
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--mode", choices=("answers2", "answers4"), default="answers2")
    args = parser.parse_args()
    count = 2 if args.mode == "answers2" else 4
    try:
        if args.self_test:
            self_test()
            print("[PASS] 2/4 exact teacher fields, truncation/extra-field rejection; GPU NOT_RUN")
            return 0
        jobs, inputs = check(count)
        if args.check_only:
            print(json.dumps(inputs, sort_keys=True))
            return 0
        return execute(count, jobs, inputs)
    except (Exception, KeyboardInterrupt) as exc:
        status, code = disposition(exc)
        print(f"[{status}] {type(exc).__name__}: {str(exc)[:250]}", file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
