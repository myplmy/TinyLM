"""Decode every candidate match and require the same literal birth roles in raw source."""
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_birth_conflicts_v1 as recovery
from scripts import p106b_hold_resolution_policy_v26 as baseline

BASE = inv.BASE
SOURCE = BASE / "birth_field_proof_v1"
OUT = BASE / "birth_field_native_proof_v1"
inv.require(not OUT.exists(), "new immutable native proof output required")
source_path = SOURCE / "complete.json"
source = inv.cache.read(source_path)
for name, digest in source["input_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == digest, "candidate proof input changed")
for name, digest in source["source_code_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == digest, "frozen production source changed")
inv.verify(SOURCE / "matches", source["matches"])
scope_path = BASE / "scope.json"
scope = inv.cache.read(scope_path)
inv.require(all(spec["path"].startswith("data_cache/") and "TinyDataset" not in spec["path"] for spec in scope["inputs"]),
            "only previously authorized native sources may be decoded")
writer = inv.ShardWriter(OUT / "rows", "native_birth_proofs", limit=19_999_999)
counts, reasons, samples = Counter(), Counter(), []
started = time.monotonic()
with ExitStack() as stack:
    reader = inv.OriginalReader(scope, stack)
    for row in inv.cache.rows(SOURCE / "matches", source["matches"]):
        counts["candidate_matches_checked"] += 1
        raw, eos, valid = reader.text(row)
        inv.require(eos and valid, "source decode/EOS/UTF-8 differs")
        before = row["proposed_body"]
        for change in row["changes"]:
            lo, hi = change["prepared_candidate_characters"]
            inv.require(hi - lo == len(change["original"]), "source-coordinate insertion length differs")
            before = before[:lo] + change["original"] + before[lo:]
        inv.require(inv.sha(before) == row["diagnostic_candidate_before_sha256"], "prepared input cannot be reconstructed")
        prepared_proof, native_proof = recovery.prove(before), recovery.prove(raw)
        inv.require(prepared_proof is not None and prepared_proof["proof"] == row["proof"]
                    and prepared_proof["candidate"] == row["proposed_body"], "independently repeated candidate proof differs")
        record = {key: row[key] for key in ["id", "source", "split", "source_ids", "source_ids_sha256", "original_text_sha256", "input_ids", "occurrences", "language_bucket", "previous_reasons"]}
        record.update(complete_eos=True, valid_utf8=True, root_approved=False, cache_admitted=False)
        if native_proof is None:
            record.update(status="NATIVE_ROLE_PROOF_NOT_ESTABLISHED_NO_RELEASE", decision="PENDING")
            counts["native_role_unproven_unique"] += 1
            writer.append(record)
            continue
        keys = ["subject", "lead_birth_year", "category_birth_year", "exact_month_day"]
        agrees = all(native_proof["proof"][key] == prepared_proof["proof"][key] for key in keys)
        if not agrees:
            record.update(status="NATIVE_PREPARED_ROLE_MISMATCH_NO_RELEASE", decision="PENDING",
                          native_proof=native_proof["proof"], prepared_proof=prepared_proof["proof"])
            counts["native_role_mismatch_unique"] += 1
            writer.append(record)
            continue
        counts["native_prepared_role_match_unique"] += 1
        counts["native_prepared_role_match_occurrences"] += row["occurrences"]
        # Re-run inherited content checks after field quarantine. A proof of
        # two fields never silently clears another rule or a broken suffix.
        result = baseline.propose(dict(record, text=prepared_proof["candidate"], previous_holds=[]), False)
        clean = result.get("candidate", result["text"])
        risks = set(result["reasons"]) if result["decision"] == "PENDING" else set()
        if not baseline.code_preserved(raw, clean) or not baseline.unicode_examples_preserved(raw, clean):
            risks.add("CODE_OR_UNICODE_GUARD")
        if not baseline.semantic_style_preserved(raw, clean):
            risks.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
        if not baseline.ordered_deletion(raw, clean):
            risks.add("NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW")
        if risks:
            decision = "PENDING"
            counts["other_checks_still_pending_unique"] += 1
            reasons.update(risks)
        else:
            decision = "EDIT"
            counts["all_inherited_checks_terminal_unique"] += 1
            counts["all_inherited_checks_terminal_occurrences"] += row["occurrences"]
        record.update(status="RAW_AND_PREPARED_ROLE_PROVEN_NOT_ADMISSION", decision=decision,
            proposed_body=clean, clean_text_sha256=inv.sha(clean), native_proof=native_proof,
            prepared_proof=prepared_proof["proof"], prepared_changes=prepared_proof["changes"],
            inherited_recheck_reasons=sorted(risks), inherited_changes=result["changes"])
        writer.append(record)
        if len(samples) < 12:
            samples.append(dict(id=row["id"], decision=decision, reasons=sorted(risks)))
inv.require(counts["candidate_matches_checked"] == source["counts"]["candidate_proof_unique"] == 774,
            "all candidate proofs must be checked against actual source")
pins = {str(path.relative_to(ROOT)): inv.file_sha(path) for path in [source_path, scope_path, Path(__file__),
    ROOT / "scripts/p106b_hold_resolution_birth_conflicts_v1.py", ROOT / "scripts/p106b_hold_resolution_policy_v26.py"]}
manifest = writer.close(lineage=pins)
report = dict(status="ALL774_CANDIDATE_MATCHES_FRESH_NATIVE_ROLE_CHECKED_NOT_ADMISSION", counts=dict(counts),
    remaining_reasons=dict(reasons), rows=manifest, samples=samples, input_pins=pins,
    source_code_pins=source["source_code_pins"], native_source_freshly_decoded=True,
    cache_admitted=0, goal_complete=False, training_authorized=False, seconds=time.monotonic() - started)
inv.write_json(OUT / "complete.json", report)
print(json.dumps({key: report[key] for key in ["status", "counts", "remaining_reasons", "samples", "seconds"]}, ensure_ascii=False))
