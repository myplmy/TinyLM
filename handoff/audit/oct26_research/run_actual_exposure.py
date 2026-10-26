"""Root-owned CPU pipeline using the existing P106B phase receipt helper."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BASE))
import audit_actual_exposure as audit
from scripts.p106b_stage_receipt import pipeline


def main():
    py = [sys.executable, "-B", "-X", "utf8"]
    script = str(BASE / "audit_actual_exposure.py")
    if sys.argv[1:] == ["--check-only"]:
        cap = int(min(180, audit.DEADLINE - time.time() - 10))
        if cap < 1:
            return 8
        return subprocess.run(["timeout", "--signal=TERM", "--kill-after=5s", str(cap) + "s", *py, script, "--check-only"],
            cwd=ROOT, stdin=subprocess.DEVNULL).returncode
    audit.require(not sys.argv[1:] and not audit.OUTPUT.exists(), "fresh CPU audit root is required")
    began = time.monotonic()
    phases = [
        ("REGRESSION", py + [str(BASE / "test_actual_exposure.py")]),
        ("PREFLIGHT", py + [script, "--check-only"]),
        ("EXECUTE", py + [script, "--execute"]),
    ]
    observed = []

    def note(line):
        print(line.replace("[EXPERIMENT_FINAL]", "[PHASE_PIPELINE_FINAL]", 1), flush=True)

    def launch(command):
        remaining = min(1100 - (time.monotonic() - began), audit.DEADLINE - time.time()) - 10
        if remaining < 30:
            return 8
        tick = time.monotonic()
        value = subprocess.run(["timeout", "--signal=TERM", "--kill-after=5s", str(int(remaining)) + "s", *command],
                               cwd=ROOT, stdin=subprocess.DEVNULL)
        observed.append(dict(command=command, actual_child_exit=value.returncode,
                             actual_child_wall_seconds=time.monotonic() - tick))
        return value.returncode

    receipt = pipeline(phases, launch, note, experiment="P106B_Stage10hWc_code_masked_exposure_cpu")
    code = receipt["returncode"]
    if audit.OUTPUT.is_dir():
        audit.write_json(audit.OUTPUT / "root_observation.json", dict(phases=observed,
            actual_pipeline_exit=code, actual_parent_seconds=time.monotonic() - began,
            actual_root_exit="EXTERNAL_AGENT_MUST_COLLECT"))
    if code == 0:
        report = audit.read(audit.OUTPUT / "report.json")
        audit.require(len(observed) == 3 and all(row["actual_child_exit"] == 0 for row in observed)
            and report["returncode"] == 0 and report["exact_targets_covered"] is True
            and report["counts"]["target_windows"] == 292992
            and report["counts"]["target_tokens"] == 300023808
            and report["models_loaded"] == report["gpu_calls"] == report["source_files_changed"] == 0,
            "root readback requires actual full CPU coverage and zero model mutations")
        audit.publication_budget()
        audit.write_json(audit.OUTPUT / "child_closed_ref.json", dict(
            path=str((audit.OUTPUT / "report.json").relative_to(ROOT)),
            sha256=audit.file_sha(audit.OUTPUT / "report.json"), actual_cpu_exit=observed[-1]["actual_child_exit"],
            observed_parent_elapsed_before_exit=time.monotonic() - began, status="CHILD_CLOSED_ROOT_EXIT_PENDING"))
    print("[EXPERIMENT_FINAL] " + json.dumps(dict(status="CPU_CANDIDATE_COMPLETE_ROOT_EXIT_REQUIRED" if code == 0 else receipt["status"],
        returncode=code, raw_report=str((audit.OUTPUT / "report.json").relative_to(ROOT)),
        model_quality_claim=False)), flush=True)
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("[EXPERIMENT_FINAL] " + json.dumps(dict(status="ROOT_ERROR", returncode=9,
            error_type=type(error).__name__, error=str(error))), flush=True)
        raise SystemExit(9)
