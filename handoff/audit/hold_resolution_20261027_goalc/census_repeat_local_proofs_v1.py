"""Try the new layout proof on every repeat diagnostic; no source is admitted."""
from collections import Counter
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_repeat_context_v1 as context

SOURCE = inv.BASE / "draft_proposals_v26_delta_v1"
OUT = inv.BASE / "repeat_local_proof_candidates_v1"
inv.require(not OUT.exists(), "new immutable proof census required")
path = SOURCE / "complete.json"
report = inv.cache.read(path)
inv.verify(SOURCE / "unique", report["unique_manifest"])
writer = inv.ShardWriter(OUT / "rows", "local_repeat_proofs", limit=19_999_999)
counts, roles, strata = Counter(), Counter(), Counter()
examples = []
started = time.monotonic()
restricted = {"expanded_train:" + str(n) for n in [14760, 756966, 15695, 1216576, 1250821, 20624, 6030]}
for row in inv.cache.rows(SOURCE / "unique", report["unique_manifest"]):
    if row["decision"] != "PENDING" or "MAIN_BODY_REPETITION_REQUIRES_CONTEXT" not in row["reasons"]:
        continue
    counts["all_repeat_reason_sources"] += 1
    if row["id"] in restricted:
        counts["restricted_metadata_only"] += 1
        continue
    candidate = row.get("diagnostic_candidate", "")
    proof = context.prove(candidate)
    if proof is None:
        counts["not_proven"] += 1
        continue
    counts.update(candidate_proofs=1, candidate_occurrences=row["occurrences"])
    record_roles = sorted({record["role"] for record in proof["records"]})
    roles.update(record_roles)
    if len(row["reasons"]) == 1:
        counts.update(sole_repeat_reason_proofs=1, sole_repeat_reason_occurrences=row["occurrences"])
    signature = (row["source"], row["language_bucket"], tuple(record_roles),
        "ONLY_REPEAT" if len(row["reasons"]) == 1 else "OTHER_REASONS_REMAIN")
    strata[str(signature)] += 1
    if len(examples) < 20:
        lines = candidate.splitlines()
        examples.append(dict(id=row["id"], roles=record_roles, previous_reasons=row["reasons"],
            repeated_values=[lines[record["contexts"][0]["source_line"] - 1] for record in proof["records"]]))
    writer.append(dict({key: row[key] for key in ["id", "source", "split", "source_ids", "source_ids_sha256",
        "original_text_sha256", "input_ids", "occurrences", "language_bucket"]},
        candidate_sha256=inv.sha(candidate), previous_reasons=row["reasons"], proof=proof,
        strata_signature=list(signature[:2]) + [record_roles, signature[3]],
        native_source_freshly_decoded=False, body_changed=False,
        root_approved=False, cache_admitted=False))
inv.require(counts["all_repeat_reason_sources"] == 21891, "all repeat sources must be considered")
pins = {str(file.relative_to(ROOT)): inv.file_sha(file) for file in [path,
    ROOT / "scripts/p106b_hold_resolution_repeat_context_v1.py",
    ROOT / "scripts/test_p106b_hold_resolution_repeat_context_v1.py", Path(__file__)]}
manifest = writer.close(lineage=pins)
result = dict(status="ALL_REPEAT_SOURCES_TRIED_LOCAL_CONTEXT_CANDIDATES_NOT_NATIVE_OR_ADMISSION",
    counts=dict(counts), roles=dict(roles), strata=dict(strata), rows=manifest,
    examples=examples, input_pins=pins, native_source_freshly_decoded=False,
    body_changed=0, cache_admitted=0, goal_complete=False,
    training_authorized=False, seconds=time.monotonic() - started)
inv.write_json(OUT / "complete.json", result)
print(json.dumps({key: result[key] for key in ["status", "counts", "roles", "strata", "seconds"]}))
