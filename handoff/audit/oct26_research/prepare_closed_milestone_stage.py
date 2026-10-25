#!/usr/bin/env python3
"""Build an explicit closed-work allowlist; do not touch Git's index."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
EXACT = {
    ".gitignore", "experiments.tsv", "scripts/flag_whitelist.tsv",
    "ai_dev_tool/Codex/08_AI-미보고-내역-자백원장.md",
    "docs/EXPERIMENT_BASELINES.md", "docs/METHODS.md", "docs/methods/03_knowledge_quality.md",
    "handoff/COMPASS.md", "handoff/WIP_20261022_작업원장.md",
    "test_plan/P005b_Muon-레시피-정렬과-QK-norm-상한.md",
    "test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md", "test_plan/실험계획목록.md",
    "test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md",
    "test_result/093_20260925_P102A-기능통과-T1-단일순서-속도관측.md",
    "test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md", "test_result/실험목록.md",
    "scripts/diag_p106b_native_format_official.py", "scripts/diag_p106b_native_format_training.py",
    "scripts/p106b_native_format_pair.py", "scripts/test_normuon.py", "scripts/test_p106b_capacity_resume.py",
    "scripts/test_p106b_gemma_capacity_probe.py", "scripts/test_p106b_native_format_official.py",
    "scripts/test_p106b_native_format_pair.py", "scripts/test_p106b_native_format_training.py", "tinylm/train/normuon.py",
    "smoketest_logs/20261025205941_smoke_codex_oct26_after_normuon_v2_ab21d36.txt",
}
PREFIXES = (
    "handoff/audit/oct26_research/", "test_result/evidence/codex_smoke/oct26_after_normuon_v2/",
    "test_result/evidence/p106b_gemma_capacity_v1_20261026_roota/",
    "test_result/evidence/p106b_gemma_capacity_resume_v1_20261026_roota/",
)
LOGS = ("078_log_20261026_P005b_Stage15W_", "101_log_20261026_P106B_Stage10aW",
    "101_log_20261026_P106B_Stage10bW_", "101_log_20261026_P106B_Stage10e0W_",
    "101_log_20261026_P106B_Stage4fsYW_", "101_log_20261026_P106B_Stage6fW_",
    "101_log_20261026_P106B_Stage9pWm_")

def main():
    exclusion = ["--", ".", ":(exclude)datasets/TinyDataset/**", ":(exclude).agents/**",
                 ":(exclude).codex/**", ":(exclude).aws/**"]
    changed = subprocess.check_output(["git", "diff", "--name-only", "-z", *exclusion], cwd=ROOT).split(b"\0")
    fresh = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z", *exclusion], cwd=ROOT).split(b"\0")
    candidates = sorted({row.decode() for row in changed + fresh if row})
    archived = json.loads((BASE / "launcher_deletion_receipt_v1.json").read_text())
    deletion_names = set()
    def collect(value):
        if isinstance(value, str):
            if value.startswith("run_") and value.endswith("-done.sh"):
                deletion_names.add(value)
        elif isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, str) and child.startswith("run_") and child.endswith("-done.sh"):
                    deletion_names.add(child)
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect(archived)
    rows, skipped = [], []
    for name in candidates:
        if name == "handoff/audit/oct26_research/stage_allowlist.paths":
            skipped.append(name); continue
        permitted = (name in EXACT or name.startswith(PREFIXES) or name in deletion_names
            or (name.startswith("test_result/") and Path(name).name.startswith(LOGS))
            or (name.startswith("run_P106B_Stage10") and name.endswith(".sh"))
            or name == "run_P106B_Stage4fsYW_capacity_profile_resume5h-done.sh")
        if name.startswith("test_result/evidence/p106b_native_format_training_v1_20261026_format_muon_cost/"):
            permitted = (ROOT / "test_result/evidence/p106b_native_format_training_v1_20261026_format_muon_cost/root_closed_ref.json").is_file()
        if name == "test_result/101_log_20261026_P106B_Stage10cWb_format_muon_cost.txt":
            permitted = (ROOT / "test_result/evidence/p106b_native_format_training_v1_20261026_format_muon_cost/root_closed_ref.json").is_file()
        if not permitted:
            skipped.append(name); continue
        path = ROOT / name
        if path.is_symlink() or any(part in name for part in (".env", "datasets/TinyDataset/", "runs/ckpt/")):
            raise ValueError("protected or link: " + name)
        if path.exists():
            size = path.stat().st_size
            if not path.is_file() or size >= 20_000_000:
                raise ValueError("non-file or oversized: " + name)
            content = path.read_bytes()
            rows.append({"path": name, "bytes": size, "sha256": hashlib.sha256(content).hexdigest().upper()})
        else:
            if name not in deletion_names:
                raise ValueError("unverified deletion: " + name)
            rows.append({"path": name, "deleted_after_source_archive": True})
    destination = BASE / "closed_milestone_stage_v2.json"
    payload = {"schema": "TINYLM_EXPLICIT_CLOSED_STAGE_V1", "files": rows, "excluded_live_or_unrelated": skipped,
               "protected_access": False, "gpu_quality_claim": False}
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps({"files": len(rows), "bytes": sum(row.get("bytes", 0) for row in rows),
                      "excluded": skipped, "manifest": str(destination.relative_to(ROOT))}, ensure_ascii=False))

if __name__ == "__main__":
    main()
