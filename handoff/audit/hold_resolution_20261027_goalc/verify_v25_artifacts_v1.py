"""Independently join every full draft source and occurrence to the inventory.

Run only after the actual producer exit has been observed and recorded.
This is artifact conservation, not cache admission or semantic approval.
"""
from collections import Counter, defaultdict
from itertools import zip_longest
from pathlib import Path
import datetime
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = AUDIT / "DRAFT_V25_EXECUTION_RECEIPT_V1.json"
EXIT = AUDIT / "DRAFT_V25_PROCESS_EXIT_V1.json"
inv.require(not OUT.exists(), "execution receipt is immutable")
observed = inv.cache.read(EXIT)
inv.require(observed["tool_session"] == 46878 and observed["process_exit_code"] == 0
            and observed["observation_method"] == "ACTUAL_EXIT_ZERO_FROM_WRITE_STDIN",
            "the actual producer exit has not been observed")
started = time.monotonic()
path = BASE / "draft_proposals_v25/complete.json"
inventory_path = BASE / "inventory_v1/complete.json"
report, inventory = inv.cache.read(path), inv.cache.read(inventory_path)
inv.require(observed["completed_artifact_sha256"] == inv.file_sha(path), "completed artifact changed after observed exit")
log = AUDIT / "draft_proposals_v25.log"
last = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
for key in ["status", "schema", "unique_counts", "occurrence_counts", "unprocessed", "seconds"]:
    inv.require(report[key] == last[key], "final stdout disagrees with completed artifact")
inv.require(report["lineage"]["inventory_sha256"] == inv.file_sha(inventory_path), "inventory lineage changed")
codes = report["lineage"]["source_code_sha256"]
inv.require(len(codes) == 63, "unexpected frozen source count")
for name, digest in codes.items():
    inv.require(inv.file_sha(ROOT / name) == digest, "frozen production source changed")
for label in ["unique", "occurrences"]:
    name = "unique_manifest" if label == "unique" else "occurrence_manifest"
    inv.verify(path.parent / label, report[name])
    inv.verify(BASE / "inventory_v1" / label, inventory[name])
unique, occurrences = Counter(), Counter()
source_counts = defaultdict(Counter)
decisions, seen = {}, set()
allowed = {"KEEP", "EDIT", "EXCLUDE", "PENDING"}
source_fields = ["id", "source", "split", "source_ids", "source_ids_sha256",
                 "original_text_sha256", "input_ids", "language_bucket", "occurrences"]
sentinel = object()
expected_rows = inv.cache.rows(BASE / "inventory_v1/unique", inventory["unique_manifest"])
actual_rows = inv.cache.rows(path.parent / "unique", report["unique_manifest"])
for expected, actual in zip_longest(expected_rows, actual_rows, fillvalue=sentinel):
    inv.require(expected is not sentinel and actual is not sentinel, "unique inventory rows were added or lost")
    for name in source_fields:
        inv.require(expected[name] == actual[name], "unique source identity, interval or multiplicity changed: " + name)
    key, decision = actual["original_text_sha256"], actual["decision"]
    inv.require(key not in seen and decision in allowed and actual.get("root_approved") is False,
                "duplicate/unknown source or unauthorized draft promotion")
    seen.add(key)
    decisions[key] = decision
    unique.update([decision])
    if decision == "KEEP":
        inv.require(actual["clean_text_sha256"] == key, "KEEP altered the source body")
    elif decision == "EDIT":
        inv.require(isinstance(actual.get("text"), str) and actual["text"].strip()
                    and inv.sha(actual["text"]) == actual["clean_text_sha256"], "edited body hash differs")
    else:
        inv.require(actual.get("clean_text_sha256") is None, "unresolved/excluded draft has an admitted-body hash")
expected_rows = inv.cache.rows(BASE / "inventory_v1/occurrences", inventory["occurrence_manifest"])
actual_rows = inv.cache.rows(path.parent / "occurrences", report["occurrence_manifest"])
for expected, actual in zip_longest(expected_rows, actual_rows, fillvalue=sentinel):
    inv.require(expected is not sentinel and actual is not sentinel, "occurrence inventory rows were added or lost")
    inherited = {key: value for key, value in actual.items() if key not in {"resolution", "resolution_reasons"}}
    inv.require(inherited == expected, "occurrence identity, interval, source or metadata changed")
    key, decision = actual["original_text_sha256"], actual["resolution"]
    inv.require(key in decisions and decisions[key] == decision, "occurrence decision does not match its actual unique source")
    occurrences.update(documents=1, input_ids=actual["input_ids"], **{decision: 1})
    occurrences[decision + "_input_ids"] += actual["input_ids"]
    source_counts[actual["source"]].update([decision])
inv.require(dict(unique) == report["unique_counts"] and len(seen) == 297539, "unique conservation differs")
inv.require(dict(occurrences) == report["occurrence_counts"] and occurrences["documents"] == 460695,
            "occurrence conservation differs")
inv.require(occurrences["input_ids"] == 462874291, "original stored-input-ID conservation differs")
inv.require({k: dict(v) for k, v in source_counts.items()} == report["sources"], "source-level decisions differ")
inv.require(report["unprocessed"] == occurrences["PENDING"]
            and report["root_adopted"] == 0 and report["training_authorized"] is False, "draft authority or unresolved count differs")
receipt = dict(status="CPU_COMPLETE_DRAFT_ARTIFACTS_VERIFIED_NOT_CACHE_ADMISSION",
    recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    original_tool_session=46878, original_process_exit_code=0,
    original_process_observation="ACTUAL_EXIT_ZERO_RETURNED_BY_WRITE_STDIN",
    unique_counts=dict(unique), occurrence_counts=dict(occurrences),
    every_unique_identity_and_multiplicity_matches_inventory=True,
    every_occurrence_identity_interval_and_decision_matches_inventory=True,
    completed_artifact=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)),
    final_stdout=dict(path=str(log.relative_to(ROOT)), sha256=inv.file_sha(log)),
    inventory=dict(path=str(inventory_path.relative_to(ROOT)), sha256=inv.file_sha(inventory_path)),
    actual_exit_receipt=dict(path=str(EXIT.relative_to(ROOT)), sha256=inv.file_sha(EXIT)),
    production_sources_unchanged=codes, verifier_sha256=inv.file_sha(Path(__file__)),
    draft_seconds=report["seconds"], artifact_verification_seconds=time.monotonic() - started,
    root_adopted=0, remaining_draft_pending=occurrences["PENDING"], verified_partial_cache_remaining_hold=160219,
    goal_complete=False, training_authorized=False)
inv.write_json(OUT, receipt)
print(json.dumps({k: receipt[k] for k in [
    "status", "unique_counts", "occurrence_counts", "original_process_exit_code", "artifact_verification_seconds"]}), flush=True)
