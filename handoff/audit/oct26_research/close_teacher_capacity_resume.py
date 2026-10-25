#!/usr/bin/env python3
"""Independently close the completed, voluntarily paused teacher window."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.p106b_shards import verify

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def main():
    base = Path(__file__).resolve().parent
    out = ROOT / "test_result/evidence/p106b_gemma_capacity_resume_v1_20261026_roota"
    report_path = out / "report.json"
    report = json.loads(report_path.read_text())
    assert report["returncode"] == 8 and report["status"] == "CLOSED_PRODUCTION_PAUSED"
    assert report["original_error"] is None and not report["cleanup_errors"]
    observed = report["supervision"]
    assert observed["actual_producer_exit"] == 8 and observed["controller_group_quiescent"]
    assert not observed["forced_cleanup"] and not observed["original_error"] and not observed["cleanup_errors"]
    assert not observed["residual_at_producer_exit"] and not report["after_cleanup"]["compute_apps"]
    terminal = [json.loads(row) for row in (out / "terminal.jsonl").read_text().splitlines()]
    assert len(terminal) == 1 and terminal[0]["returncode"] == 8 and terminal[0]["event"] == "OBSERVATION"
    spec = importlib.util.spec_from_file_location("root_capacity_resume", base / "resume_gemma_capacity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.source_identity()["sha256"] == report["source_sha256"]
    data = ROOT / module.PRODUCTION
    for name, wanted in report["before"]["files"].items():
        assert sha(data / name) == wanted, name
    batch_path = data / "batch_000004/report.json"
    batch = json.loads(batch_path.read_text())
    assert sha(batch_path) == report["production"]["report_sha256"]
    for key in ("raw_manifest", "candidate_manifest"):
        verify(batch_path.parent, batch[key])
    input_tokens = sum(value for key, value in batch["nonpadding_tokens"].items() if key.startswith("train:"))
    targets = sum(value for key, value in batch["assistant_targets"].items() if key.startswith("train:"))
    receipt = {
        "schema": "TINYLM_GEMMA_CAPACITY_RESUME_ROOT_CLOSURE_V1", "actual_root_session_exit": 8,
        "report_sha256": sha(report_path), "terminal_sha256": sha(out / "terminal.jsonl"),
        "status": report["status"], "new_train_x_tokens": batch["new_train_x_tokens"],
        "accepted_groups": batch["accepted_groups"], "raw_rows": batch["raw_manifest"]["rows"],
        "cumulative_train_input_tokens": input_tokens, "cumulative_assistant_targets": targets,
        "strict_75m_input_deficit": 75_000_000 - input_tokens, "cursor": batch["cursor"],
        "source_unchanged": True, "prior_closed_files_unchanged": True,
        "candidate_and_raw_manifests_verified": True, "forced_cleanup": False,
        "memory": report["worker"]["memory_readers"],
        "controller_elapsed_sec": report["elapsed_sec"], "runlog_minutes_rounded": 92.9,
        "outer_wall_precise_measurement": "NOT_CAPTURED", "semantic_quality": "NOT_REVIEWED",
        "formal_train_ready": False, "student_training": "NOT_RUN",
    }
    destination = base / "teacher_capacity_resume_root_closure.json"
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps({k:v for k,v in receipt.items() if k != "memory"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
