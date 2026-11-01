"""Cross-check earlier admitted source keys against later conservative guards.

This metadata join does not modify or rebuild either cache and does not infer
that every conservative retraction is a confirmed defective body.
"""
from collections import Counter
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

AUDIT, BASE = Path(__file__).resolve().parent, inv.BASE
out = AUDIT / "PARTIAL_V1_V21_RETRACTION_INTERSECTION_V1.json"
inv.require(not out.exists(), "intersection receipt is write-once")
started = time.monotonic()
stable_path = BASE / "roster_stable_partial_v1/complete.json"
draft_path = BASE / "draft_proposals_v21/complete.json"
verified_path = BASE / "cache_partial_v1/partial_resolution_verified.json"
stable, draft, verified = (inv.cache.read(path) for path in [stable_path, draft_path, verified_path])
inv.require(verified["remaining_hold"] == 160219 and verified["goal_complete"] is False,
            "partial verification identity differs")
inv.verify(BASE / "roster_stable_partial_v1/records", stable["manifest"])
inv.verify(BASE / "draft_proposals_v21/unique", draft["unique_manifest"])
accepted = {}
for row in inv.cache.rows(BASE / "roster_stable_partial_v1/records", stable["manifest"]):
    if row["decision"] in {"KEEP", "EDIT"}:
        key = row["original_text_sha256"]
        inv.require(key not in accepted and row["root_approved"] is True, "stable source identity differs")
        accepted[key] = row
counts, reasons, records = Counter(), Counter(), []
seen = set()
for row in inv.cache.rows(BASE / "draft_proposals_v21/unique", draft["unique_manifest"]):
    key = row["original_text_sha256"]
    if key not in accepted:
        continue
    earlier = accepted[key]
    inv.require(key not in seen, "repeated earlier admitted source key")
    seen.add(key)
    counts.update(earlier_terminal_unique=1)
    counts["earlier_terminal_occurrences"] += earlier["occurrences"]
    same = row.get("clean_text_sha256") == earlier.get("clean_text_sha256", key)
    if row["decision"] in {"KEEP", "EDIT"} and same:
        counts.update(unchanged_terminal_unique=1)
        counts["unchanged_terminal_occurrences"] += earlier["occurrences"]
        continue
    kind = "LATER_CONSERVATIVE_PENDING_REQUIRES_REVIEW" if row["decision"] == "PENDING" else "LATER_TERMINAL_BODY_DIFFERS_REQUIRES_REVIEW"
    counts[kind + "_unique"] += 1
    counts[kind + "_occurrences"] += earlier["occurrences"]
    reasons.update(row["reasons"])
    records.append(dict(id=earlier["id"], original_text_sha256=key, earlier_decision=earlier["decision"],
        earlier_clean_text_sha256=earlier.get("clean_text_sha256", key), source_occurrences=earlier["occurrences"],
        later_decision=row["decision"], later_clean_text_sha256=row.get("clean_text_sha256"),
        later_reasons=row["reasons"], status=kind, later_id=row["id"],
        earlier_occurrence_count_is_not_final_deduplicated_admission_count=True))
inv.require(seen == set(accepted), "new draft omitted a prior accepted source key")
paths = [stable_path, draft_path, verified_path, Path(__file__)]
result = dict(status="EARLIER_PARTIAL_CACHE_IS_NOT_FINAL_SEMANTIC_APPROVAL", counts=dict(counts),
    recheck_reasons=dict(reasons), records=records, seconds=time.monotonic() - started,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
    old_cache_modified=False, later_pending_is_not_confirmed_defect=True,
    cache_admitted=0, goal_complete=False, training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000,
            "intersection receipt needs sharding")
inv.write_json(out, result)
print(json.dumps(dict(counts=result["counts"], reasons=result["recheck_reasons"],
    seconds=result["seconds"], output=str(out.relative_to(ROOT))), ensure_ascii=False))
