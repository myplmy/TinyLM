"""Fresh source decode and baseline regeneration for every local-repeat match."""
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
from scripts import p106b_hold_resolution_policy_v26 as policy
from scripts import p106b_hold_resolution_repeat_context_v1 as context

BASE = inv.BASE
SOURCE = BASE / "repeat_local_proof_candidates_v1"
OUT = BASE / "repeat_local_native_proofs_v1"
inv.require(not OUT.exists(), "new immutable native proof output required")
candidate_path = SOURCE / "complete.json"
draft_path = BASE / "draft_proposals_v26_delta_v1/complete.json"
scope_path = BASE / "scope.json"
census, draft, scope = map(inv.cache.read, [candidate_path, draft_path, scope_path])
for name, digest in census["input_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == digest, "candidate proof input changed")
for name, digest in draft["lineage"]["source_code_sha256"].items():
    inv.require(inv.file_sha(ROOT / name) == digest, "frozen production source changed")
inv.verify(SOURCE / "rows", census["rows"])
targets = {row["original_text_sha256"]: row for row in inv.cache.rows(SOURCE / "rows", census["rows"])}
inv.verify(draft_path.parent / "unique", draft["unique_manifest"])
sources = {row["original_text_sha256"]: row for row in inv.cache.rows(draft_path.parent / "unique", draft["unique_manifest"])
           if row["original_text_sha256"] in targets}
inv.require(set(sources) == set(targets) and len(sources) == 40, "all40 proof sources must be available")
prepared, counts = [], Counter()
started = time.monotonic()
with ExitStack() as stack:
    reader = inv.OriginalReader(scope, stack)
    for key, row in sources.items():
        raw, eos, valid = reader.text(row)
        inv.require(eos and valid and inv.sha(raw) == key, "fresh native source proof differs")
        result = policy.propose(dict(row, text=raw, complete_eos=True, valid_utf8=True,
                                     previous_holds=row.get("previous_holds", [])), False)
        clean = result.get("candidate", result["text"])
        proof = context.prove(clean)
        agrees = inv.sha(clean) == targets[key]["candidate_sha256"] and proof == targets[key]["proof"]
        counts.update(fresh_native_sources=1, occurrences=row["occurrences"])
        if not agrees:
            counts["regeneration_or_proof_mismatch_not_released"] += 1
        else:
            counts["fresh_regeneration_and_proof_match"] += 1
        remaining = set(result["reasons"]) if result["decision"] == "PENDING" else set()
        remaining.discard("MAIN_BODY_REPETITION_REQUIRES_CONTEXT")
        guards = dict(code=policy.code_preserved(raw, clean), unicode=policy.unicode_examples_preserved(raw, clean),
            style=policy.semantic_style_preserved(raw, clean), ordered=policy.ordered_deletion(raw, clean))
        terminal = agrees and not remaining and all(guards.values())
        if terminal:
            counts.update(all_other_checks_clear=1, clear_occurrences=row["occurrences"])
        prepared.append(dict(source=row, raw=raw, candidate=clean, proof=proof,
            native_proof_agrees=agrees, remaining_reasons=sorted(remaining), guards=guards,
            candidate_decision="EDIT" if terminal and raw != clean else "KEEP" if terminal else "PENDING"))
(OUT / "inputs").mkdir(parents=True)
rows = []
for value in prepared:
    source = value["source"]
    stem = source["id"].replace(":", "_")
    pins = {}
    for label in ["original", "candidate"]:
        text = value["raw"] if label == "original" else value["candidate"]
        path = OUT / "inputs" / (stem + "_" + label + ".txt")
        payload = text.encode("utf-8")
        inv.require(0 < len(payload) < 20_000_000, "input needs explicit splitting")
        with path.open("xb") as stream:
            stream.write(payload)
        pins[label] = dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path))
    row = {name: source[name] for name in ["id", "source", "split", "source_ids", "source_ids_sha256",
        "original_text_sha256", "input_ids", "occurrences", "language_bucket"]}
    row.update(**pins, native_proof_agrees=value["native_proof_agrees"], proof=value["proof"],
        remaining_reasons=value["remaining_reasons"], guards=value["guards"],
        candidate_decision=value["candidate_decision"], complete_eos=True, valid_utf8=True,
        root_approved=False, cache_admitted=False)
    rows.append(row)
report = dict(status="ALL40_FRESH_NATIVE_AND_REGENERATION_CHECKED_REVIEW_STILL_REQUIRED", counts=dict(counts), rows=rows,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [candidate_path, draft_path,
        scope_path, ROOT / "scripts/p106b_hold_resolution_repeat_context_v1.py", Path(__file__)]},
    source_code_pins=draft["lineage"]["source_code_sha256"], native_source_freshly_decoded=True,
    cache_admitted=0, goal_complete=False, training_authorized=False, seconds=time.monotonic() - started)
inv.write_json(OUT / "complete.json", report)
print(json.dumps({key: report[key] for key in ["status", "counts", "seconds"]}))
