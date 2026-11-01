"""Persist the full lexical assignment, exact reuse, and current input integrity."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

AUDIT, BASE = Path(__file__).resolve().parent, inv.BASE
manifest_path = BASE / "root_selected_lexical_counter_v1/manifest.json"
views_path = BASE / "root_selected_lexical_counter_v1/reading_views_manifest_v1.json"
manifest, views = inv.cache.read(manifest_path), inv.cache.read(views_path)
inv.require(len(manifest["rows"]) == 579 and len(manifest["reused_exact_contexts"]) == 57, "lexical scope differs")
missing, changed, checked, reconstructed = [], [], 0, 0
by_id = {r["id"]: r for r in views["rows"]}
for row in manifest["rows"]:
    view = by_id[row["id"]]
    for kind, parts in view["views"].items():
        chunks = []
        for part in parts:
            path = ROOT / part["path"]
            inv.require(path.resolve().is_relative_to((BASE / "root_selected_lexical_counter_v1/reading_views_v1").resolve()),
                        "view escapes this exact source packet")
            checked += 1
            if not path.is_file():
                missing.append(part["path"])
                continue
            blob = path.read_bytes()
            if hashlib.sha256(blob).hexdigest().upper() != part["sha256"]:
                changed.append(part["path"])
            chunks.append(blob)
        if kind in {"original", "candidate"}:
            raw = (ROOT / row[kind]["path"]).read_bytes()
            inv.require(hashlib.sha256(raw).hexdigest().upper() == row[kind]["sha256"], "neutral source/body input changed")
            inv.require(b"".join(chunks) == raw, "actual view bytes do not reconstruct the current raw input")
            reconstructed += 1
inv.require(checked == 2937 and reconstructed == 1158 and not missing and not changed, "reading-view integrity failed")
source7986 = next(r for r in manifest["rows"] if r["id"] == "expanded_train:7986")
raw = (ROOT / source7986["original"]["path"]).read_bytes()
inv.require(raw.count(b"\n") == 92 and not raw.endswith(b"\n")
            and raw.endswith(b"Paper Works, Articles and links to specialized web sites."), "actual non-LF EOF counter changed")
result = dict(status="LEXICAL_636_ALL_EXACTLY_REUSED_OR_ASSIGNED_NOT_ADMISSION",
    signal_sources=636, assigned_current_pairs=579, reused_exact_independent_accepts=57,
    source_characters_by_role=manifest["source_characters_by_role"],
    assignments={role: len(ids) for role, ids in manifest["assignments"].items()},
    current_raw_pairs_verified=579, reconstructed_current_raw_inputs=1158, actual_view_files_verified=2937,
    missing_views=missing, changed_views=changed,
    observed_nonlf_eof_example=dict(id="expanded_train:7986", newline_bytes=92, actual_lf_records=93,
        last_source_record="Paper Works, Articles and links to specialized web sites.",
        source_views_match_exact_current_raw=True, prior_reader_mismatch_claim_retracted=True),
    reported_32474_initial_failure=dict(status="INITIAL_FAILED_COMMAND_NOT_RECOVERED_FROM_AGENT_CONTEXT",
        originally_claimed_exact_command_was_unverified_reconstruction=True,
        subsequent_reads_succeeded=True, current_views_match_expected_hashes=True,
        historical_file_absence_or_deletion_not_established=True),
    all_five_roles_in_progress=True, assignment_is_not_completion=True,
    producer_sha256=inv.file_sha(Path(__file__)),
    input_pins={str(p.relative_to(ROOT)): inv.file_sha(p) for p in [
        manifest_path, views_path, AUDIT / "root_selected_body_literals_v5.json",
        AUDIT / "ROOT_AUTHORED_SELECTIONS_V9.json"]},
    cache_admitted=0, goal_complete=False, training_authorized=False)
output = AUDIT / "LEXICAL_FULL_ASSIGNMENT_AND_VIEW_INTEGRITY_V1.json"
inv.require(not output.exists(), "checkpoint is immutable")
inv.write_json(output, result)
print(json.dumps(dict(signal_sources=636, assigned_current_pairs=579, reused_exact_independent_accepts=57,
    verified_views=checked, reconstructed_inputs=reconstructed, missing=missing, changed=changed,
    cache_admitted=0)))
