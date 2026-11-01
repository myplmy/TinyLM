"""Count actual post-dedup partial-cache positions requiring renewed review."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

AUDIT, BASE = Path(__file__).resolve().parent, inv.BASE
OUT = AUDIT / "PARTIAL_V1_ACTUAL_ADMISSION_RECHECKS_V1.json"
inv.require(not OUT.exists(), "actual admission recheck receipt is write-once")
source_path = AUDIT / "PARTIAL_V1_V21_RETRACTION_INTERSECTION_V1.json"
built_path = BASE / "cache_partial_v1/built.json"
source, built = inv.cache.read(source_path), inv.cache.read(built_path)
lookup = {row["original_text_sha256"]: row for row in source["records"]}
inv.require(len(lookup) == len(source["records"]), "recheck source keys repeat")
counts, accepted, seen = Counter(), [], set()
started = time.monotonic()
ledger = built["manifests"]["ledger"]
concatenated = hashlib.sha256()
for shard in ledger["shards"]:
    path = built_path.parent / "ledger" / shard["path"]
    digest, size, rows = hashlib.sha256(), 0, 0
    with path.open("rb") as stream:
        for payload in stream:
            digest.update(payload)
            concatenated.update(payload)
            size += len(payload)
            rows += 1
            row = json.loads(payload)
            counts["whole_ledger_positions_checked"] += 1
            key = row["original_text_sha256"]
            if key not in lookup or row["parent_decision"] != "HOLD":
                continue
            original = lookup[key]
            seen.add(key)
            counts["matching_original_hold_positions"] += 1
            counts["matching_position_outcome_" + row["decision"]] += 1
            if row["decision"] not in {"KEEP", "EDIT"}:
                continue
            inv.require(row["clean_text_sha256"] == original["earlier_clean_text_sha256"],
                        "actual earlier admitted body differs from the metadata intersection")
            counts["actual_admitted_positions_requiring_review"] += 1
            counts["actual_admitted_" + row["split"] + "_positions"] += 1
            counts[original["status"] + "_admitted_positions"] += 1
            accepted.append(dict(id=row["id"], original_text_sha256=key, split=row["split"],
                source_ids=row["source_ids"], clean_text_sha256=row["clean_text_sha256"],
                old_outcome=row["decision"], later_decision=original["later_decision"],
                later_reasons=original["later_reasons"], conservative_recheck_status=original["status"],
                confirmed_defect=False))
    inv.require(size == shard["bytes"] and rows == shard["rows"] and digest.hexdigest().upper() == shard["sha256"],
                "actual partial ledger shard integrity differs")
inv.require(concatenated.hexdigest().upper() == ledger["concat_sha256"], "partial whole ledger hash differs")
inv.require(counts["whole_ledger_positions_checked"] == built["counts"]["documents"] == 2154912,
            "actual partial ledger scope differs")
inv.require(seen == set(lookup), "some recheck source key has no original-HOLD occurrence in the actual partial ledger")
paths = [source_path, built_path, Path(__file__)]
result = dict(status="ACTUAL_PARTIAL_ADMISSIONS_REQUIRING_FRESH_SEMANTIC_REVIEW", counts=dict(counts),
    rows=accepted, seconds=time.monotonic() - started,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
    old_cache_modified=False, later_pending_is_not_confirmed_defect=True,
    prior_technical_integrity_receipt_preserved=True, cache_admitted=0, goal_complete=False,
    training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000,
            "actual recheck receipt needs sharding")
inv.write_json(OUT, result)
print(json.dumps(dict(counts=result["counts"], seconds=result["seconds"], output=str(OUT.relative_to(ROOT))), ensure_ascii=False))
