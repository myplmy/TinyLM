"""Report exact change numbers/counts; never alter or fuzzy-apply an anchor."""
from pathlib import Path
import json
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_text_edits_v2 as edits
from scripts import p106b_hold_resolution_inventory as inv

AUDIT=Path(__file__).resolve().parent
BASE=inv.BASE
snapshot=max((AUDIT/"legacy_progress_v3").glob("*.json"))
document=inv.cache.read(snapshot)
sources={row["id"]:row for row in inv.cache.read(BASE/"legacy_span_review_v2/manifest.json")["rows"]}
results=[]
for row in document["records"]:
    if row.get("status")!="EDIT_RECIPE" or not row.get("mechanical_error"):
        continue
    prefix=row["id"].replace(":","_")
    names=set(re.findall(re.escape(prefix)+r"(?:_v[0-9]+)?[.]edits[.]md",row["output_references"]))
    if len(names)!=1:
        continue
    path=BASE/"agents"/row["role"]/"legacy_span_review_v2"/next(iter(names))
    recipe=path.read_bytes().decode("utf-8")
    record=dict(id=row["id"],role=row["role"],recipe=str(path.relative_to(ROOT)),recipe_sha256=inv.file_sha(path))
    try:
        match=re.search(r"(?m)^base:\s*(original|candidate)\s*$",recipe)
        if not match:
            raise ValueError("RECIPE_BASE_HEADER_MISSING")
        base=match[1]
        info=sources[row["id"]]["paths"][base]
        source=ROOT/info["path"]
        inv.require(inv.file_sha(source)==info["sha256"],"source pin differs")
        raw=source.read_bytes().decode("utf-8")
        _,changes=edits.parse_recipe(recipe,source_id=row["id"],base=base,base_sha256=info["sha256"])
        counts=[dict(change=i,count=raw.count(before),trimmed_count=raw.count(before.strip()),
                     anchor_characters=len(before),left_whitespace=len(before)-len(before.lstrip()),
                     right_whitespace=len(before)-len(before.rstrip())) for i,(before,after) in enumerate(changes,1)]
        spans=[(raw.index(before),raw.index(before)+len(before),i) for i,(before,after) in enumerate(changes,1) if raw.count(before)==1]
        spans.sort()
        record.update(changes=counts,overlaps=[dict(first=a[2],second=b[2]) for a,b in zip(spans,spans[1:]) if a[1]>b[0]])
    except (ValueError,OSError) as exc:
        record["error"]=str(exc)
    results.append(record)
out=AUDIT/"legacy_anchor_diagnostics_v1"
out.mkdir(exist_ok=True)
path=out/(str(time.time_ns())+".json")
inv.write_json(path,dict(snapshot=str(snapshot.relative_to(ROOT)),snapshot_sha256=inv.file_sha(snapshot),rows=results,
                         status="ANCHOR_DIAGNOSIS_ONLY_NO_EDITS_APPLIED",source_sha256=inv.file_sha(Path(__file__))))
print(path.relative_to(ROOT))
print(json.dumps([dict(id=row["id"],recipe=Path(row["recipe"]).name,error=row.get("error"),
                      bad_changes=[item for item in row.get("changes",[]) if item["count"]!=1],
                      overlaps=row.get("overlaps",[])) for row in results if row.get("changes")],ensure_ascii=False))
