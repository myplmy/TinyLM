"""Pin only the seven root-adjudicated literal guard false positives."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v10 as policy

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
snapshot = AUDIT / "authored_candidates_snapshot_v5.json"
rows = {row["id"]: row for row in inv.cache.read(snapshot)["rows"]}
evidence = AUDIT / "LITERAL_GUARD_ADJUDICATIONS_V1.md"
evidence_pin = dict(path=str(evidence.relative_to(ROOT)), sha256=inv.file_sha(evidence))
approved = [1174021, 1242413, 1081376, 1091850, 410074, 634479, 5639]
records = []
for number in approved:
    row = rows["expanded_train:" + str(number)]
    source = ROOT / row["source"]
    body = ROOT / row["body"]
    if number == 1242413:
        body = BASE / "agents/context_controls/literal_guard_recheck_v1/expanded_train_1242413_recheck_v2.txt"
    original, clean = source.read_bytes().decode("utf-8"), body.read_bytes().decode("utf-8")
    inv.require(inv.file_sha(source) == row["original_text_sha256"], "curated source changed")
    inv.require(policy.unicode_examples_preserved(original, clean), "literal Unicode example changed")
    inv.require(not policy.code_preserved(original, clean), "case does not require a literal exception")
    segments = []
    if number == 1242413:
        segments = [line for line in original.splitlines() if re.match(r"^[ \t]*%", line)]
        segments += ["cohere(x,y,M)", "cxyN = cohere(x,y,N);"]
        inv.require(len(segments) >= 3, "actual Matlab source examples missing")
        for text in segments:
            inv.require(text in original and clean.count(text) >= 1, "an actual source program segment was lost")
    review_paths = [ROOT / row["review"]]
    if number in {1242413, 634479}:
        review_paths.append(BASE / "agents/context_controls/literal_guard_recheck_v1" / ("review_v2.md" if number == 1242413 else "review.md"))
    if number == 1174021:
        review_paths.append(BASE / "agents/historical_review/literal_guard_recheck_v1/review.md")
    records.append(dict(id=row["id"], original_text_sha256=inv.file_sha(source), clean_text_sha256=inv.file_sha(body),
                        original=str(source.relative_to(ROOT)), body=str(body.relative_to(ROOT)), root_approved=True,
                        kind="EXACT_REVIEWED_NONPROGRAM_DELIMITER_PAIR", evidence=evidence_pin,
                        required_literal_segments=segments,
                        review_inputs=[dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)) for path in review_paths]))
out = AUDIT / "LITERAL_GUARD_APPROVALS_V1.json"
inv.write_json(out, dict(schema="P106B_EXACT_LITERAL_GUARD_APPROVALS_V1", status="ROOT_REVIEWED_EXACT_SOURCE_BODY_PAIRS",
                        rows=records, producer_sha256=inv.file_sha(Path(__file__)), snapshot_sha256=inv.file_sha(snapshot),
                        global_code_guard_waiver=False, training_authorized=False, goal_complete=False))
print(json.dumps(dict(cases=len(records), code_segment_requirements={row["id"]: len(row["required_literal_segments"]) for row in records})))
