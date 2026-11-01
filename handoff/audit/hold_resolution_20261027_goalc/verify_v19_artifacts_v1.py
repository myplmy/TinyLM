"""Verify full v19 artifacts after observing actual session 90166 exit zero.

This readback is independent of the producer's printed counts. It does not
admit draft text to a cache or change unresolved positions into exclusions.
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
out = AUDIT / "DRAFT_V19_EXECUTION_RECEIPT_V1.json"
inv.require(not out.exists(), "new immutable execution receipt required")
started = time.monotonic()
path = BASE / "draft_proposals_v19/complete.json"
report = inv.cache.read(path)
log = AUDIT / "draft_proposals_v19.log"
last = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
for key in ["status", "schema", "unique_counts", "occurrence_counts", "unprocessed", "seconds"]:
    inv.require(report[key] == last[key], "final stdout disagrees with completed artifact")
codes = report["lineage"]["source_code_sha256"]
inv.require(len(codes) == 43, "unexpected frozen production source count")
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
    inv.require(row["original_text_sha256"] in seen, "occurrence source outside unique draft")
    decision = row["resolution"]
    occurrences.update(documents=1, input_ids=row["input_ids"], **{decision: 1})
    occurrences[decision + "_input_ids"] += row["input_ids"]
inv.require(dict(unique) == report["unique_counts"] and len(seen) == 297539,
            "unique conservation differs")
inv.require(dict(occurrences) == report["occurrence_counts"] and occurrences["documents"] == 460695,
            "occurrence conservation differs")
inv.require(occurrences["input_ids"] == 462874291, "input ID conservation differs")
inv.require(report["unprocessed"] == occurrences["PENDING"] == report["occurrence_counts"]["PENDING"],
            "draft unresolved count differs")
inv.require(report["root_adopted"] == 0 and report["training_authorized"] is False,
            "draft authority differs")
inv.write_json(out, dict(status="CPU_COMPLETE_DRAFT_ARTIFACTS_VERIFIED_NOT_CACHE_ADMISSION",
    recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    original_tool_session=90166, original_process_exit_code=0,
    original_process_observation="ACTUAL_EXIT_ZERO_RETURNED_BY_WRITE_STDIN",
    completed_artifact=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)),
    final_stdout=dict(path=str(log.relative_to(ROOT)), sha256=inv.file_sha(log)),
    unique_counts=dict(unique), occurrence_counts=dict(occurrences),
    draft_seconds=report["seconds"], artifact_verification_seconds=time.monotonic() - started,
    production_sources_unchanged=codes, verifier_sha256=inv.file_sha(Path(__file__)),
    root_adopted=0, remaining_draft_pending=report["occurrence_counts"]["PENDING"],
    verified_partial_cache_remaining_hold=160219,
    goal_complete=False, training_authorized=False))
print(json.dumps(dict(status="CPU_COMPLETE_DRAFT_ARTIFACTS_VERIFIED_NOT_CACHE_ADMISSION",
    unique_counts=dict(unique), occurrence_counts=dict(occurrences),
    original_process_exit_code=0, verification_seconds=time.monotonic() - started)), flush=True)
