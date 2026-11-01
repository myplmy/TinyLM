"""Verify the completed draft artifacts after the old tool handle expired.

This is an artifact readback, not a reconstructed process exit status, semantic
approval, cache build, or authorization to train. Original text is not copied.
"""
from collections import Counter
from pathlib import Path
import datetime
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
out = AUDIT / "DRAFT_V14_ARTIFACT_RECOVERY_V1.json"
inv.require(not out.exists(), "new artifact recovery receipt required")
started = time.monotonic()
path = BASE / "draft_proposals_v14/complete.json"
report = inv.cache.read(path)
log = AUDIT / "draft_proposals_v14.log"
last = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
for key in ["status", "schema", "unique_counts", "occurrence_counts", "unprocessed", "seconds"]:
    inv.require(report[key] == last[key], "final stdout disagrees with completed artifact")
codes = report["lineage"]["source_code_sha256"]
inv.require(len(codes) == 30, "unexpected frozen production source count")
for name, digest in codes.items():
    inv.require(inv.file_sha(ROOT / name) == digest, "frozen production source changed")
for label in ["unique", "occurrences"]:
    manifest = report["unique_manifest" if label == "unique" else "occurrence_manifest"]
    inv.verify(path.parent / label, manifest)

unique, occurrences = Counter(), Counter()
seen = set()
for row in inv.cache.rows(path.parent / "unique", report["unique_manifest"]):
    key = row["original_text_sha256"]
    inv.require(key not in seen, "unique source SHA repeated")
    seen.add(key)
    unique.update([row["decision"]])
    inv.require(row.get("root_approved") is False, "draft was silently promoted")
for row in inv.cache.rows(path.parent / "occurrences", report["occurrence_manifest"]):
    inv.require(row["original_text_sha256"] in seen, "occurrence source is outside unique draft")
    decision = row["resolution"]
    occurrences.update(documents=1, input_ids=row["input_ids"], **{decision: 1})
    occurrences[decision + "_input_ids"] += row["input_ids"]
inv.require(dict(unique) == report["unique_counts"] and len(seen) == 297539,
            "unique conservation differs")
inv.require(dict(occurrences) == report["occurrence_counts"] and occurrences["documents"] == 460695,
            "occurrence conservation differs")
inv.require(report["unprocessed"] == occurrences["PENDING"] == 137656,
            "draft unresolved count differs")
inv.require(report["root_adopted"] == 0 and report["training_authorized"] is False,
            "draft authority differs")
inv.write_json(out, dict(status="CPU_COMPLETE_DRAFT_ARTIFACTS_VERIFIED_NOT_CACHE_ADMISSION",
    recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    original_tool_session=47516, original_process_exit_code=None,
    original_process_observation="UNKNOWN_PROCESS_ID_ON_RESUME_DO_NOT_INFER_EXIT_ZERO",
    completed_artifact=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)),
    final_stdout=dict(path=str(log.relative_to(ROOT)), sha256=inv.file_sha(log)),
    unique_counts=dict(unique), occurrence_counts=dict(occurrences),
    draft_seconds=report["seconds"], artifact_verification_seconds=time.monotonic() - started,
    production_sources_unchanged=codes, verifier_sha256=inv.file_sha(Path(__file__)),
    root_adopted=0, remaining_draft_pending=137656, verified_partial_cache_remaining_hold=160219,
    goal_complete=False, training_authorized=False))
print(json.dumps(dict(status="CPU_COMPLETE_DRAFT_ARTIFACTS_VERIFIED_NOT_CACHE_ADMISSION",
    unique_counts=dict(unique), occurrence_counts=dict(occurrences),
    original_process_exit_code=None, verification_seconds=time.monotonic() - started)), flush=True)
