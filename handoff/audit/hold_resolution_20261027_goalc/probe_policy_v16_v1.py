"""Evaluate the new context policy on old and newly stratified source packets.

No source body is admitted. Previously individualized and restricted sources
stay outside general packets, and every source/body change remains pinned.
"""
from collections import Counter
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v16 as policy
from scripts import p106b_hold_resolution_revision_v14 as revision
from scripts.p106b_hold_resolution_refinement import ordered_deletion

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
out = AUDIT / "policy_v16_purpose_probe_v1.json"
inv.require(not out.exists(), "new immutable probe receipt required")
paths = [BASE / "draft_proposals_v7b/review_packets/manifest.json",
         BASE / "pending_materialized_v6_v1/review_packets/manifest.json",
         BASE / "draft_proposals_v11/review_packets/manifest.json",
         BASE / "remaining_profile_v11_v1/review_packets/manifest.json",
         BASE / "contextual_residual_v11_v1/manifest.json",
         BASE / "remaining_profile_v14_v1/review_packets/manifest.json"]
rows, excluded = {}, []
for path in paths:
    for row in inv.cache.read(path)["rows"]:
        if row["decision"] != "PENDING":
            continue
        if (any("PRIOR_INDIVIDUAL" in reason for reason in row["reasons"])
                or row["id"] in {"expanded_train:1250821", "expanded_train:756966", "expanded_train:14760"}):
            excluded.append(row["id"])
            continue
        source = row["paths"]["original"] if "paths" in row else dict(path=row["path"], sha256=row["sha256"])
        if row["id"] in rows:
            inv.require(rows[row["id"]]["source"]["sha256"] == source["sha256"], "one ID has different source bodies")
        rows[row["id"]] = dict(row, source=source)
started = time.monotonic()
counts, changes = Counter(), Counter()
records = []
for row in rows.values():
    pin = row["source"]
    path = ROOT / pin["path"]
    inv.require(inv.file_sha(path) == pin["sha256"], "purpose original changed")
    raw = path.read_bytes().decode("utf-8")
    value = policy.propose(dict(row, text=raw, complete_eos=True, valid_utf8=True))
    final = value.get("candidate", value["text"])
    counts.update([value["decision"]])
    changes.update(change["reason"] for change in value["changes"])
    records.append(dict(id=row["id"], source=pin, previous_decision="PENDING", decision=value["decision"],
                        clean_text_sha256=inv.sha(final), reasons=value["reasons"], changes=value["changes"],
                        code_guard=policy.code_preserved(raw, final), unicode_guard=policy.unicode_examples_preserved(raw, final),
                        semantic_style_guard=policy.semantic_style_preserved(raw, final),
                        ordered_deletion=ordered_deletion(raw, final)))
result = dict(status="PURPOSED_POLICY_PROBE_NOT_ADMISSION", rows=records, counts=dict(counts), changes=dict(changes),
              input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
              source_code_pins={name: inv.file_sha(ROOT / name) for name in revision.CODE +
                                ["scripts/p106b_hold_resolution_policy_v15.py", "scripts/p106b_hold_resolution_policy_v16.py", str(Path(__file__).relative_to(ROOT))]},
              excluded_individual_ids=sorted(set(excluded)), root_adopted=0,
              seconds=time.monotonic() - started, goal_complete=False, training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "probe receipt needs sharding")
inv.write_json(out, result)
terminal = [row for row in records if row["decision"] in {"KEEP", "EDIT"}]
print(json.dumps(dict(counts=result["counts"], rows=len(records), seconds=result["seconds"],
                      terminal_code_flags=[row["id"] for row in terminal if not row["code_guard"]],
                      terminal_unicode_flags=[row["id"] for row in terminal if not row["unicode_guard"]],
                      terminal_style_flags=[row["id"] for row in terminal if not row["semantic_style_guard"]],
                      terminal_ordered_flags=[row["id"] for row in terminal if not row["ordered_deletion"]]), ensure_ascii=False))

