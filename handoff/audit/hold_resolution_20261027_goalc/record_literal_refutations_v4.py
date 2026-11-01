"""Pin complete literal comparisons before accepting semantic loss claims."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
BASE=ROOT/"data_cache/p106b_hold_resolution_v1_20261027_goalc"
manifest=BASE/"legacy_span_review_v2/manifest.json"
sources={r["id"]:r for r in json.loads(manifest.read_bytes())["rows"]}
claims={7230:["안영부"],29128:["20세기 대한민국 사람"],28720:[],
        4482:["The Mathematical Achievements","Article examining"]}
records=[]
sha=lambda data:hashlib.sha256(data).hexdigest().upper()
for ident,terms in claims.items():
    row=sources["expanded_train:"+str(ident)]
    bodies={};pins={}
    for label in ("original","candidate"):
        info=row["paths"][label];payload=(ROOT/info["path"]).read_bytes()
        assert sha(payload)==info["sha256"]
        bodies[label]=payload.decode("utf-8");pins[label]=info
    a,b=bodies["original"],bodies["candidate"]
    records.append(dict(id=row["id"],pins=pins,term_counts={term:{label:text.count(term) for label,text in bodies.items()}
        for term in terms},complete_literal_diff="".join(difflib.unified_diff(a.splitlines(True),b.splitlines(True))),
        status="PINNED_COMPLETE_LITERAL_COMPARISON_NOT_FACT_VERIFICATION"))
out=AUDIT/"counter_literal_refutations_v4.json"
with out.open("x",encoding="utf-8") as stream:
    json.dump(dict(source_sha256=sha(Path(__file__).read_bytes()),manifest_sha256=sha(manifest.read_bytes()),rows=records),stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(out.relative_to(ROOT))
