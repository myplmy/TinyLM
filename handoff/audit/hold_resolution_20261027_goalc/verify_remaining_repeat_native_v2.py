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
SOURCE = BASE / "repeat_remaining_named_strata_v2"
OUT = BASE / "repeat_remaining_native_proofs_v2"
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
sys.path.insert(0,str(AUDIT))
import guarded_scan_metadata_v1 as byte_metadata
protected=inv.cache.read(AUDIT/"GUARDED_SOURCE_METADATA_CONTRACT_V1.json")
blocked_ids=set(protected["restricted_ids"])
blocked_hashes=set(protected["restricted_hashes"])
target_ids={row["id"] for row in targets.values()}
inv.require(not(target_ids&blocked_ids) and not(set(targets)&blocked_hashes),"restricted originals must never be assigned")
sources={}
for shard in draft["unique_manifest"]["shards"]:
    with (draft_path.parent/"unique"/shard["path"]).open("rb") as stream:
        for line in stream:
            match=byte_metadata.IDENT.search(line)
            inv.require(match is not None,"draft byte ID missing")
            ident=match[1].decode("ascii")
            if ident not in target_ids:
                continue  # Every other candidate/body remains opaque bytes.
            row=json.loads(line)
            key=row["original_text_sha256"]
            inv.require(row["id"]==ident and key in targets and key not in blocked_hashes,"named target identity differs")
            inv.require(key not in sources,"named source repeats")
            sources[key]=row
inv.require(set(sources) == set(targets) and len(sources) == 732, "all732 named-stratum sources must be available")
prepared, counts = [], Counter()
started = time.monotonic()
with ExitStack() as stack:
    reader = inv.OriginalReader(scope, stack)
    for number, (key, row) in enumerate(sources.items(),1):
        if number%100==0:
            print(json.dumps(dict(phase="fresh_native_named_strata",unique_done=number,unique_total=732)),flush=True)
        raw, eos, valid = reader.text(row)
        inv.require(eos and valid and inv.sha(raw) == key, "fresh native source proof differs")
        result = policy.propose(dict(row, text=raw, complete_eos=True, valid_utf8=True,
                                     previous_holds=row.get("previous_holds", [])), False)
        clean = result.get("candidate", result["text"])
        proof = dict(named_review_strata=targets[key]["named_review_strata"], classification_only=True)
        agrees = inv.sha(clean) == targets[key]["candidate_sha256"] and result["decision"] == "PENDING" and result["reasons"] == targets[key]["previous_reasons"]
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
            candidate_decision="CONTEXT_REVIEW_REQUIRED"))
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
    row.update(named_review_strata=value["proof"]["named_review_strata"], **pins, native_proof_agrees=value["native_proof_agrees"], proof=value["proof"],
        remaining_reasons=value["remaining_reasons"], guards=value["guards"],
        candidate_decision=value["candidate_decision"], complete_eos=True, valid_utf8=True,
        root_approved=False, cache_admitted=False)
    rows.append(row)
report = dict(status="ALL732_FRESH_NATIVE_AND_REGENERATION_CHECKED_REVIEW_STILL_REQUIRED", counts=dict(counts), rows=rows,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [candidate_path, draft_path,
        scope_path, ROOT / "scripts/p106b_hold_resolution_repeat_context_v1.py", Path(__file__)]},
    source_code_pins=draft["lineage"]["source_code_sha256"], native_source_freshly_decoded=True,
    cache_admitted=0, goal_complete=False, training_authorized=False, seconds=time.monotonic() - started)
inv.write_json(OUT / "complete.json", report)
print(json.dumps({key: report[key] for key in ["status", "counts", "seconds"]}))
