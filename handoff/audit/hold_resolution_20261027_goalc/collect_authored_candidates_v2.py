"""Pin current curated authored bodies, including independent repair cohorts.

This snapshot does not approve them. CRLF and code bytes are read literally.
Only assigned canonical author paths are considered; wrong-role copies stay out.
"""
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v6 as policy

BASE=inv.BASE
AUDIT=Path(__file__).resolve().parent
out=AUDIT/"authored_candidates_snapshot_v2.json"
inv.require(not out.exists(),"new snapshot version required")


def version(path):
    match=re.search(r"_v([0-9]+)[.]",path.name)
    return int(match[1])if match else 1


def subsequence(original,cleaned):
    source=iter(c for c in original if not c.isspace())
    return all(any(a==b for a in source)for b in cleaned if not b.isspace())


def choices(directory,expected):
    found={}
    pins=[]
    for path in sorted(directory.glob("review*.md"),key=lambda p:(version(p),p.name)):
        payload=path.read_bytes()
        digest=inv.sha(payload.decode("utf-8"))
        pins.append(dict(path=str(path.relative_to(ROOT)),sha256=digest))
        for number,line in enumerate(payload.decode("utf-8").splitlines(),1):
            if not line.startswith("|"):
                continue
            cells=[cell.strip().strip("`*")for cell in line.split("|")[1:-1]]
            if not cells or not re.fullmatch(r"(?:expanded_train:)?[0-9]+",cells[0]):
                continue
            ident=cells[0]if":"in cells[0]else"expanded_train:"+cells[0]
            if ident in expected:
                found[ident]=dict(decision=cells[1],review=str(path.relative_to(ROOT)),review_sha256=digest,
                                  review_line=number,review_text=line)
    return found,pins


cohorts=[]
manual=inv.cache.read(AUDIT/"manual_residual_assignments_v1.json")["roles"]
family=inv.cache.read(AUDIT/"family_assignments_v1.json")
profiles=inv.cache.read(AUDIT/"profile_assignments_v1.json")
for role,assigned in manual.items():
    cohorts.append((role,"manual_residual_v1",{row["id"]:ROOT/row["original_path"]for row in assigned}))
for role,assigned in family.items():
    cohorts.append((role,"family_resolution_v1",{ident:BASE/"inventory_v1/review_packets"/(ident.replace(":","_")+".txt")for ident in assigned["ids"]}))
for role,assigned in profiles.items():
    cohorts.append((role,"profile_resolution_v1",{row["id"]:ROOT/row["path"]for row in assigned["rows"]}))
extra=inv.cache.read(BASE/"draft_proposals_v3/review_packets/manifest.json")["rows"]
source=next(row["paths"]["original"]["path"]for row in extra if row["id"]=="expanded_train:495513")
cohorts.append(("context_hangul","extra_draft_repairs_v1",{"expanded_train:495513":ROOT/source}))
records=[]
errors=[]
all_pins=[]
for role,group,expected in cohorts:
    directory=BASE/"agents"/role/group
    decisions,pins=choices(directory,set(expected))
    all_pins.extend(pins)
    for ident,source in expected.items():
        if ident not in decisions:
            errors.append(dict(id=ident,role=role,error="NO_SAVED_AUTHOR_DECISION"))
            continue
        choice=decisions[ident]
        row=dict(id=ident,author=role,author_group=group,source=str(source.relative_to(ROOT)),
                 original_text_sha256=inv.file_sha(source),**choice,root_approved=False)
        if choice["decision"]not in{"KEEP","EDIT","EXCLUDE"}:
            errors.append(dict(id=ident,role=role,error="AUTHOR_STATUS_NOT_FINAL",status=choice["decision"]))
        elif choice["decision"]=="EDIT":
            prefix=ident.replace(":","_")
            candidates=[p for p in directory.glob(prefix+"*.txt")if re.fullmatch(re.escape(prefix)+r"(?:_v[0-9]+)?[.]txt",p.name)]
            if not candidates:
                errors.append(dict(id=ident,role=role,error="AUTHOR_BODY_MISSING"))
            else:
                body=max(candidates,key=version)
                raw=source.read_bytes().decode("utf-8")
                clean=body.read_bytes().decode("utf-8")
                words=re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[\u3400-\u9fff]+")
                row.update(body=str(body.relative_to(ROOT)),clean_text_sha256=inv.file_sha(body),
                           source_characters=len(raw),clean_characters=len(clean),
                           deletion_only_ignoring_whitespace=subsequence(raw,clean),
                           added_lexical_counts=dict(Counter(words.findall(clean))-Counter(words.findall(raw))),
                           code_guard=policy.code_preserved(raw,clean),unicode_guard=policy.unicode_examples_preserved(raw,clean))
        records.append(row)
inv.require(len(records)==len({row["id"]for row in records}),"curated cohorts overlap")
value=dict(status="CURATED_AUTHOR_SNAPSHOT_NOT_ROOT_ADOPTION",rows=records,counts=dict(Counter(row["decision"]for row in records)),
           review_pins=all_pins,errors=errors,source_sha256=inv.file_sha(Path(__file__)),
           policy_sha256=inv.file_sha(ROOT/"scripts/p106b_hold_resolution_policy_v6.py"))
inv.write_json(out,value)
print(json.dumps(dict(rows=len(records),counts=value["counts"],errors=errors,
                      code_flags=[row["id"]for row in records if row.get("code_guard")is False],
                      unicode_flags=[row["id"]for row in records if row.get("unicode_guard")is False],
                      order_flags=[row["id"]for row in records if row.get("deletion_only_ignoring_whitespace")is False]),ensure_ascii=False))
