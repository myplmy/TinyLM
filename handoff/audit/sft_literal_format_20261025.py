#!/usr/bin/env python3
"""One-time format-only operation on44 explicitly reviewed snapshot candidates."""
from pathlib import Path
import copy, hashlib, json, re, time
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"data_cache/p106b_text_work_20261022"
PACKET=BASE/"root_semantic_followup_20261025/literal47"
TARGET=BASE/"root_closed_full/literal_format_20261025"
AUDIT=ROOT/"handoff/audit/WIP_20261025_SFT_LITERAL_FORMAT_REPAIR.json"
START=time.monotonic()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def write_once(path,raw):
    assert len(raw)<20_000_000 and not path.exists()
    with path.open("xb") as f: assert f.write(raw)==len(raw)
receipt_path=PACKET/"packet_receipt.json"
receipt=json.loads(receipt_path.read_text())
notes=PACKET/"luna_literal_notes.md"
assert digest(PACKET/"source_and_warning_candidates.md")=="824C539BBABDB3A7C8F1324CA983CD158AE5BEBCA792BEC8D037D7E9485AF761"
assert digest(notes)=="81CDF0E9197BF25B2CB9A57F0614509CFEBD4299ACA47E531139F19FF71B2755"
assert not TARGET.exists() and not AUDIT.exists()
paths={ROOT/p["source_file"] for p in receipt["candidate_pins"]}
pins={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
raws={p:[json.loads(line) for line in p.read_text().splitlines()] for p in paths}
literal=chr(92)+"n"
rows,changes,skipped=[],[],[]
for pin in receipt["candidate_pins"]:
    path=ROOT/pin["source_file"]
    candidates=[r for r in raws[path] if r["source_index"]==pin["source_index"] and r["variant_kind"]==pin["kind"]
        and hashlib.sha256(canonical(r["messages"])).hexdigest().upper()==pin["publication_messages_sha256"]]
    assert len(candidates)==1
    original=candidates[0]
    if pin["source_index"]==1273:
        skipped.append({"source_index":1273,"kind":pin["kind"],"reason":"Existing separate revision preserved; no duplicate revision"})
        continue
    revised=copy.deepcopy(original)
    edits=[]
    for turn,message in enumerate(original["messages"]):
        s=message["content"]
        fences=[m.start() for m in re.finditer(chr(96)*3,s)]
        assert len(fences)%2==0
        protected=[(fences[j],fences[j+1]+3) for j in range(0,len(fences),2)]
        indices=[j for j in range(len(s)-1) if s[j:j+2]==literal]
        assert not any(a<=j<b for j in indices for a,b in protected)
        if fences: assert pin["source_index"]==1219
        parts,last=[],0
        for j in indices:
            parts.extend([s[last:j],chr(10)])
            last=j+2
            edits.append({"turn":turn,"old_start":j,"old_end":j+2,"replacement":"LF"})
        parts.append(s[last:])
        new="".join(parts)
        assert new==s.replace(literal,chr(10))
        for a,b in protected:
            before_count=sum(j<a for j in indices)
            after_count=sum(j<b for j in indices)
            assert s[a:b]==new[a-before_count:b-after_count]
        revised["messages"][turn]["content"]=new
    assert len(edits)==pin["literal_count"] and edits
    assert {k:v for k,v in revised.items() if k!="messages"}=={k:v for k,v in original.items() if k!="messages"}
    revised["format_only_revision"]={
        "parent_source_file":pin["source_file"],"parent_messages_sha256":pin["publication_messages_sha256"],
        "operation":"Only reviewed literal newline positions outside fenced code become actual LF",
        "root_review":"Every516 warning context and complete Luna notes read; not full semantic review",
        "semantic_admission":"NOT_ADMITTED","training_performed":False,"edits":edits}
    rows.append(revised)
    changes.append({"source_index":pin["source_index"],"kind":pin["kind"],
        "parent_messages_sha256":pin["publication_messages_sha256"],
        "revised_messages_sha256":hashlib.sha256(canonical(revised["messages"])).hexdigest().upper(),
        "replacements":len(edits),"protected_fences":sum(m["content"].count(chr(96)*3)//2 for m in original["messages"])})
assert len(rows)==44 and len(skipped)==3 and sum(r["replacements"] for r in changes)==481
TARGET.mkdir()
raw=b"".join(canonical(r)+bytes([10]) for r in rows)
write_once(TARGET/"candidates_000000.jsonl",raw)
assert len([json.loads(line) for line in raw.splitlines()])==44
assert all(digest(ROOT/name)==sha for name,sha in pins.items())
report={"schema":"P106B_EXPLICIT_LITERAL_FORMAT_REPAIR_V1","status":"FORMAT_REVISED_NOT_ADMITTED",
    "parent_receipt_sha256":digest(receipt_path),"notes_sha256":digest(notes),
    "root_review_scope":"All516 literal occurrence contexts and complete notes; source1219 code preview; not full semantic acceptance",
    "luna_note_correction":"Notes for2936 cited2968; root actual contexts show vanity/hubris definitions. Actual contexts govern.",
    "source_files_before_after_unchanged":True,"source_files":pins,
    "snapshot_warnings":47,"revised":44,"skipped_already_revised":skipped,"replacements":481,
    "changes":changes,"output":str(TARGET.relative_to(ROOT))+"/candidates_000000.jsonl",
    "output_sha256":hashlib.sha256(raw).hexdigest().upper(),"output_bytes":len(raw),
    "new_training_admission":0,"model_loading":False,"gpu":False,"checkpoint_writes":0,
    "internal_wall_seconds":time.monotonic()-START}
write_once(AUDIT,json.dumps(report,ensure_ascii=False,indent=2).encode()+bytes([10]))
print(json.dumps({k:report[k] for k in ("status","snapshot_warnings","revised","replacements","output","output_bytes","output_sha256","internal_wall_seconds")},ensure_ascii=False))
