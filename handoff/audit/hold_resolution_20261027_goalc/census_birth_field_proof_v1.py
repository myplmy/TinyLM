"""Apply the new literal proof to every verified26 birth diagnostic candidate."""
from collections import Counter
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_birth_conflicts_v1 as recovery

BASE = inv.BASE
SOURCE = BASE / "draft_proposals_v26_delta_v1"
OUT = BASE / "birth_field_proof_v1"
inv.require(not OUT.exists(), "new immutable proof census required")
report_path = SOURCE / "complete.json"
report = inv.cache.read(report_path)
pins = report["lineage"]["source_code_sha256"]
for name, digest in pins.items():
    inv.require(inv.file_sha(ROOT / name) == digest, "production source changed")
inv.verify(SOURCE / "unique", report["unique_manifest"])
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:15695", "expanded_train:1216576",
              "expanded_train:1250821", "expanded_train:20624", "expanded_train:6030"}
started = time.monotonic()
counts, roles, matches = Counter(), Counter(), {}
writer = inv.ShardWriter(OUT / "matches", "birth_proofs", limit=19_999_999)
rejected = inv.ShardWriter(OUT / "unproven", "source_ids", limit=19_999_999)
for row in inv.cache.rows(SOURCE / "unique", report["unique_manifest"]):
    if row["decision"] != "PENDING" or "INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED" not in row["reasons"]:
        continue
    counts["birth_reason_unique"] += 1
    if row["id"] in restricted or row.get("previous_holds") or "PRIOR_INDIVIDUAL_OR_SPAN_REVIEW_REQUIRES_ROOT_ADOPTION" in row["reasons"]:
        counts["restricted_or_individual_metadata_only"] += 1
        continue
    before = row.get("diagnostic_candidate", "")
    proof = recovery.prove(before) if before else None
    metadata = {key: row[key] for key in ["id", "source", "split", "source_ids", "source_ids_sha256", "original_text_sha256", "input_ids", "occurrences", "language_bucket"]}
    if proof is None:
        counts["unproven_candidate_unique"] += 1
        rejected.append(dict(metadata, previous_reasons=row["reasons"], disposition="NO_ROLE_PROOF_NOT_AN_EXCLUSION"))
        continue
    counts["candidate_proof_unique"] += 1
    counts["candidate_proof_occurrences"] += row["occurrences"]
    roles.update([row["source"]])
    inv.require(row["original_text_sha256"] not in matches, "duplicate unique source")
    matches[row["original_text_sha256"]] = row["id"]
    writer.append(dict(metadata, previous_reasons=row["reasons"], diagnostic_candidate_before_sha256=inv.sha(before),
        proposed_body=proof["candidate"], changes=proof["changes"], proof=proof["proof"],
        native_original_proof_not_yet_checked=True, root_approved=False, cache_admitted=False))
inv.require(counts["birth_reason_unique"] == 3541, "verified26 birth census differs")
weighted = Counter()
inv.verify(SOURCE / "occurrences", report["occurrence_manifest"])
for row in inv.cache.rows(SOURCE / "occurrences", report["occurrence_manifest"]):
    if row["original_text_sha256"] in matches:
        weighted.update(occurrences=1, input_ids=row["input_ids"])
inv.require(weighted["occurrences"] == counts["candidate_proof_occurrences"], "candidate occurrence scope differs")
lineage = {str(path.relative_to(ROOT)): inv.file_sha(path) for path in [report_path,
    ROOT / "scripts/p106b_hold_resolution_birth_conflicts_v1.py", ROOT / "scripts/test_p106b_hold_resolution_birth_conflicts_v1.py", Path(__file__)]}
match_manifest, unproven_manifest = writer.close(lineage=lineage), rejected.close(lineage=lineage)
result = dict(status="ALL_BIRTH_REASON_CANDIDATE_PROOFS_COUNTED_NOT_NATIVE_OR_CACHE_APPROVAL", counts=dict(counts),
    matched_source_counts=dict(roles), matched_occurrence_input_ids=dict(weighted), matches=match_manifest,
    unproven=unproven_manifest, input_pins=lineage, native_source_freshly_decoded=False,
    old_source_pins_unchanged=len(pins), source_code_pins=pins, cache_admitted=0,
    goal_complete=False, training_authorized=False, seconds=time.monotonic() - started)
inv.write_json(OUT / "complete.json", result)
print(json.dumps({key: result[key] for key in ["status", "counts", "matched_occurrence_input_ids", "seconds"]}, ensure_ascii=False))
