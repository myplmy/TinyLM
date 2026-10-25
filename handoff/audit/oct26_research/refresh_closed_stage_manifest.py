#!/usr/bin/env python3
"""Preserve the first allowlist and record a narrow staging-audit correction."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def main():
    previous = BASE / "closed_milestone_stage_v2.json"
    data = json.loads(previous.read_text())
    changes = []
    for row in data["files"]:
        if row.get("deleted_after_source_archive"):
            assert not (ROOT / row["path"]).exists()
            continue
        actual = sha(ROOT / row["path"])
        if actual != row["sha256"]:
            assert row["path"] == "handoff/audit/oct26_research/prepare_closed_milestone_stage.py"
            changes.append({"path": row["path"], "before": row["sha256"], "after": actual,
                            "reason": "remove one newly authored trailing space"})
            row["sha256"] = actual
            row["bytes"] = (ROOT / row["path"]).stat().st_size
    extra = [previous, BASE / "stage_closed_milestone.py", BASE / "closed_index_verification_v1.json",
             Path(__file__).resolve(), BASE / "seal_native_cost_admission.py", BASE / "native_training_cost_admission_v1.json"]
    cost = ROOT / "test_result/evidence/p106b_native_format_training_v1_20261026_format_normuon_cost"
    spec = json.loads((cost / "root_closed_ref.json").read_text())
    assert spec["actual_supervisor_exit"] == 0 and sha(cost / "report.json") == spec["sha256"]
    extra.extend(path for path in cost.rglob("*") if path.is_file())
    extra.append(ROOT / "test_result/101_log_20261026_P106B_Stage10cWc_format_normuon_cost.txt")
    existing = {row["path"] for row in data["files"]}
    for path in extra:
        name = str(path.relative_to(ROOT))
        if name in existing:
            continue
        assert path.is_file() and not path.is_symlink() and path.stat().st_size < 20_000_000
        data["files"].append({"path": name, "bytes": path.stat().st_size, "sha256": sha(path)})
        existing.add(name)
    data["previous_manifest"] = {"path": str(previous.relative_to(ROOT)), "sha256": sha(previous)}
    data["narrow_corrections"] = changes
    data["prior_staging_guard_failures"] = ["rename inference changed name-only display",
        "already staged deleted path cannot be added twice", "EOF blanks retained in frozen source"]
    data["excluded_live_or_unrelated"] = ["test_result/evidence/p106b_native_format_training_v1_20261026_format_muon_train/",
        "test_result/101_log_20261026_P106B_Stage10dWb_format_muon_train.txt"]
    target = BASE / "closed_milestone_stage_v3.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps({"files": len(data["files"]), "changed": changes, "manifest": str(target.relative_to(ROOT))}))

if __name__ == "__main__":
    main()
