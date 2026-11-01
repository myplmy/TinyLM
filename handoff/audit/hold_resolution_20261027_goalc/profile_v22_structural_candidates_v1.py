"""Census new structure proofs on every v21 diagnostic candidate, not raw text."""
from collections import Counter
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v22 as policy
from scripts import p106b_hold_resolution_structure_v2 as structure
from scripts import p106b_hold_resolution_revision_v22 as revision

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / "structural_candidate_profile_v22_v1"
inv.require(not OUT.exists(), "structural profile namespace must be new")
draft_path = BASE / "draft_proposals_v21/complete.json"
draft = inv.cache.read(draft_path)
pins = {name: inv.file_sha(ROOT / name) for name in revision.CODE}
for name, key in draft["lineage"]["source_code_sha256"].items():
    inv.require(inv.file_sha(ROOT / name) == key, "frozen v21 producer changed")
inv.verify(BASE / "draft_proposals_v21/unique", draft["unique_manifest"])
writer = inv.ShardWriter(OUT / "matches", "structure_matches", limit=19_999_999)
counts, types, by_language = Counter(), Counter(), Counter()
started = time.monotonic()
for row in inv.cache.rows(BASE / "draft_proposals_v21/unique", draft["unique_manifest"]):
    if row["decision"] != "PENDING":
        continue
    counts.update(unique_pending=1, occurrences=row["occurrences"])
    body = row.get("diagnostic_candidate")
    if any("PRIOR_INDIVIDUAL_OR_SPAN" in reason for reason in row["reasons"]):
        counts.update(individual_metadata_only=1)
        continue
    if not isinstance(body, str) or not body.strip():
        counts.update(no_diagnostic_metadata_only=1)
        continue
    counts.update(diagnostic_candidates_checked=1, diagnostic_characters=len(body))
    kinds = []
    if structure.complete_source_program(body):
        kinds.append("PROVED_WHOLE_PROGRAM_DIAGNOSTIC")
    if (structure.complete_tables_with_explicit_blanks(body)
            and not structure.ORIGINAL_TABLE_COVER(body)):
        kinds.append("EXPLICIT_SPARSE_TABLE_AXES_DIAGNOSTIC")
    prepared, aliases = policy.typed_initial_alias(body)
    if aliases:
        kinds.extend("TYPED_EMPTY_ALIAS_" + change["explicit_kind"] for change in aliases)
    if not kinds:
        continue
    counts.update(matched_source_keys=1, matched_occurrences=row["occurrences"])
    types.update(kinds)
    by_language.update([row["language_bucket"]])
    record = {key: row[key] for key in ["id", "original_text_sha256", "source", "split", "source_ids",
              "source_ids_sha256", "input_ids", "language_bucket", "occurrences"]}
    record.update(proof_kinds=kinds, prior_reasons=row["reasons"], diagnostic_candidate=body,
        diagnostic_candidate_sha256=inv.sha(body), original_has_not_been_redecoded_here=True,
        candidate_proof_is_not_an_original_source_or_cache_admission=True)
    writer.append(record)
counts["metadata_only"] = counts["individual_metadata_only"] + counts["no_diagnostic_metadata_only"]
inv.require(counts["unique_pending"] == 78102 and counts["occurrences"] == 123212,
            "v21 whole pending census differs")
inv.require(counts["diagnostic_candidates_checked"] + counts["metadata_only"] == counts["unique_pending"],
            "structural diagnostic census omits pending sources")
inv.require(pins == {name: inv.file_sha(ROOT / name) for name in revision.CODE},
            "v22 code changed while structural census ran")
manifest = writer.close(lineage=dict(draft_path=str(draft_path.relative_to(ROOT)),
    draft_sha256=inv.file_sha(draft_path), source_code_pins=pins))
result = dict(status="ALL_V21_PENDING_DIAGNOSTICS_STRUCTURALLY_PROFILED_NOT_ADMISSION", counts=dict(counts),
    proof_kinds=dict(types), language_character_presence_buckets=dict(by_language), matches_manifest=manifest,
    source_code_pins=pins, input_pins={str(draft_path.relative_to(ROOT)): inv.file_sha(draft_path),
        str(Path(__file__).relative_to(ROOT)): inv.file_sha(Path(__file__))},
    seconds=time.monotonic() - started, original_streams_opened=False, model_loads=0, gpu_calls=0,
    root_adopted=0, goal_complete=False, training_authorized=False)
inv.write_json(OUT / "complete.json", result)
print(json.dumps({key: result[key] for key in ["status", "counts", "proof_kinds", "seconds"]}, ensure_ascii=False))
