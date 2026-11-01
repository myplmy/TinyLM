"""Compare new context drafts on existing, source-pinned purpose packets."""
from collections import Counter
from pathlib import Path
import json
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v9 as policy
from scripts.p106b_hold_resolution_refinement import ordered_deletion

BASE=inv.BASE
AUDIT=Path(__file__).resolve().parent
out=AUDIT/"policy_v9_purpose_probe_v1.json"
inv.require(not out.exists(),"probe must use new output")
paths=[BASE/"draft_proposals_v7b/review_packets/manifest.json",BASE/"pending_materialized_v6_v1/review_packets/manifest.json"]
rows={}
for path in paths:
    for row in inv.cache.read(path)["rows"]:
        if row["decision"]!="PENDING":
            continue
        if any("PRIOR_INDIVIDUAL" in reason for reason in row["reasons"]):
            continue
        rows.setdefault(row["id"],row)
counts=Counter()
changes=Counter()
records=[]
started=time.monotonic()
for row in rows.values():
    info=row["paths"]["original"]
    path=ROOT/info["path"]
    inv.require(inv.file_sha(path)==info["sha256"],"pinned original differs")
    text=path.read_bytes().decode("utf-8")
    value=policy.propose(dict(row,text=text,complete_eos=True,valid_utf8=True))
    final=value.get("candidate",value["text"])
    counts.update([value["decision"]])
    changes.update(change["reason"] for change in value["changes"])
    tokens=re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[\u3400-\u9fff]+")
    additions=dict(Counter(tokens.findall(final))-Counter(tokens.findall(text)))
    records.append(dict(id=row["id"],previous_decision=row["decision"],decision=value["decision"],
                        source=info,clean_text_sha256=inv.sha(final),reasons=value["reasons"],
                        changes=value["changes"],lexical_additions=additions,
                        code_guard=policy.code_preserved(text,final),unicode_guard=policy.unicode_examples_preserved(text,final),
                        ordered_deletion=ordered_deletion(text,final)))
result=dict(status="PURPOSE_PROBE_NOT_CACHE_OR_SEMANTIC_ADMISSION",root_adopted=0,
            pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in paths},
            source_sha256=inv.file_sha(Path(__file__)),policy_sha256=inv.file_sha(ROOT/"scripts/p106b_hold_resolution_policy_v9.py"),
            counts=dict(counts),changes=dict(changes),rows=records,seconds=time.monotonic()-started)
inv.write_json(out,result)
print(json.dumps(dict(counts=result["counts"],changes=result["changes"],seconds=result["seconds"],
                      admissions_with_guard_flags=[row["id"] for row in records if row["decision"]in{"KEEP","EDIT"} and
                                                   not(row["code_guard"]and row["unicode_guard"])],
                      ordered_flags=[row["id"] for row in records if row["decision"]in{"KEEP","EDIT"} and not row["ordered_deletion"]],
                      lexical_addition_rows=[row["id"] for row in records if row["lexical_additions"]]),ensure_ascii=False))
