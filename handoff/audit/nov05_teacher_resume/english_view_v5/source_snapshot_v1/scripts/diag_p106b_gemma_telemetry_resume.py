#!/usr/bin/env python3
"""User-only continuation of literal V3 production with separate telemetry proof.

Generation inputs/code, raw/canonical batches and cursor replay remain pinned.
Only the memory reader is process-locally wrapped; old runtime files are not edited.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_gemma_literal_recovery as literal
from scripts import diag_p106_vram_sample as memory_source
from scripts import diag_p106b_mtp_teacher as lifecycle
from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader, POLICY
from scripts.p106b_mixed_scale import digest, safe_repo_path
from scripts.p106b_stage_receipt import pipeline

CODE_PATHS = ("scripts/p106b_gemma_telemetry_resume.py",
              "scripts/diag_p106b_gemma_telemetry_resume.py",
              "scripts/diag_p106b_qwen_coload.py",
              "scripts/diag_p106b_mtp_teacher.py",
              "scripts/diag_p106_vram_sample.py",
              "scripts/diag_p106b_online_rate5.py")


@contextmanager
def telemetry_scope(reader):
    original = lifecycle.Session.memory

    def measured(session):
        result = original(session)  # Persistent errors and low-free still fail.
        return dict(result, telemetry_recovery=reader.snapshot(),
                    resource_safety="NOT_ESTABLISHED")

    with patch.object(memory_source, "read_memory", reader), \
            patch.object(lifecycle.Session, "memory", measured):
        yield


def run_resume(args, *, execute):
    if args.mode != "resume":
        raise ValueError("only continuation of pinned literal production is authorized")
    # Literal/V2/V1 namespaces are restored even if a preflight raises.
    with literal.literal_scope():
        return literal.previous.guarded_dispatch(args, execute=execute)


def execute_resume(args):
    # A unique new evidence file never overwrites any teacher batch/report.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = safe_repo_path(ROOT/"test_result/evidence"/
        ("101_P106B_Stage4jWg_telemetry_resume_"+stamp+"_"+uuid.uuid4().hex[:12]+".json"))
    if evidence.exists() or evidence.is_symlink():
        raise FileExistsError("telemetry receipt already exists")
    reader = RetryingMemoryReader(memory_source.read_memory,
                                   emit=lambda line: print(line, flush=True))
    proof = dict(schema="P106B_GEMMA_TELEMETRY_RESUME_V1", policy=POLICY,
                 generation_inputs_sha256=digest(safe_repo_path(literal.PATHS["OUTPUT"]/"inputs.json")),
                 runtime_code_sha256={name: digest(ROOT/name) for name in CODE_PATHS},
                 max_wall_sec=args.max_wall_sec, student_training="NOT_RUN",
                 gpu_reset_recovery="NOT_IMPLEMENTED", generation_contract_changed=False,
                 original_reports_mutated=False)
    rc = 9
    try:
        with telemetry_scope(reader):
            rc = run_resume(args, execute=True)
        return rc
    finally:
        proof.update(returncode=rc, telemetry=reader.snapshot())
        encoded = json.dumps(proof, ensure_ascii=False, indent=2)+"\n"
        if len(encoded.encode("utf-8")) > 20_000_000:
            raise ValueError("telemetry receipt exceeds20MB")
        evidence.parent.mkdir(parents=True, exist_ok=True)
        with evidence.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
        print("[TELEMETRY_EVIDENCE] "+str(evidence.relative_to(ROOT)), flush=True)
        print("[TELEMETRY_FINAL] "+json.dumps(reader.snapshot(), ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("resume",), required=True)
    parser.add_argument("--max-wall-sec", type=int, default=21600)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute", action="store_true")
    group.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if not 60 <= args.max_wall_sec <= 21600:
        parser.error("wall limit must be60..21600 seconds")
    if args.check_only:
        return run_resume(args, execute=False)  # No reader call or new evidence.
    print("[RESUME_POLICY] "+json.dumps(dict(policy=POLICY, maximum_attempts=3,
        failed_query_timeout_sec=5, persistent_error_stop=True,
        missing_peak_is_not_safe=True, old_generation_sha_preserved=True)), flush=True)

    def launch(command):
        if command[0] == "CHECK_ONLY":
            return run_resume(args, execute=False)
        if command[0] == "EXECUTE":
            return execute_resume(args)
        return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL).returncode

    phases = [("REGRESSION", [sys.executable, "-B", "-X", "utf8", "-m", "unittest"]+
               literal.REGRESSION+["scripts.test_p106b_gemma_telemetry_resume"]),
              ("PREFLIGHT", ["CHECK_ONLY"]), ("EXECUTE", ["EXECUTE"])]
    return pipeline(phases, launch, lambda line: print(line, flush=True),
                    experiment="P106B_GEMMA_TELEMETRY_V1_resume")["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
