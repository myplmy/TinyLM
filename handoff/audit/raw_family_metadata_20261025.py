#!/usr/bin/env python3
"""Read existing raw source provenance columns without changing normalization."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,sys,time
import pyarrow.parquet as pq
import pyarrow.compute as pc
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.p106b_capability_corpus import engine
START=time.monotonic()
TARGET=ROOT/"handoff/audit/WIP_20261025_DOLLY_MINTAKA_RAW_METADATA.json"
PARENT=ROOT/"handoff/audit/WIP_20261025_DOLLY_MINTAKA_RAW_TOKEN_INVENTORY_V2.json"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert not TARGET.exists()
parent=json.loads(PARENT.read_text())
assert parent["returncode"]==0 and parent["inputs_unchanged"]
records=defaultdict(lambda:{"rows":0,"fields":{k:Counter() for k in ("split","sub_dataset_name","task_type","template_id","language")},"sample_ids":[]})
pins=parent["source_pins"]
for rel,pin in pins.items():
 p=ROOT/rel;assert rel.startswith("HF/") and not p.is_symlink() and sha(p)==pin
 lang="en" if "/english/" in rel else "ko"
 for batch in pq.ParquetFile(p).iter_batches(batch_size=16384,columns=["id","dataset_name","split","sub_dataset_name","task_type","template_id","language"],use_threads=False):
  if time.monotonic()-START>300:raise TimeoutError("metadata audit CPU window")
  col=batch.column("dataset_name")
  mask=pc.or_(pc.starts_with(col,"Dolly-v2"),pc.starts_with(col,"Mintaka-inst"))
  for row in batch.filter(mask).to_pylist():
   family=engine.family_bucket(row["dataset_name"])
   if family not in ("Dolly-v2","Mintaka-inst"):continue
   key=lang+":"+family;r=records[key];r["rows"]+=1
   for k,c in r["fields"].items():c[json.dumps(row[k],ensure_ascii=False,sort_keys=True)]+=1
   if len(r["sample_ids"])<8:r["sample_ids"].append(row["id"])
 assert sha(p)==pin
assert {k:r["rows"] for k,r in records.items()}==parent["expected_normalized_rows"]
output={}
for k,r in records.items():
 output[k]={"rows":r["rows"],"sample_ids":r["sample_ids"],
  "fields":{f:{"distinct":len(c),"counts":dict(c.most_common(32)),"all_values_shown":len(c)<=32} for f,c in r["fields"].items()}}
result={"schema":"EXISTING_RAW_PROVENANCE_COLUMN_AUDIT_V1","status":"RAW_METADATA_OBSERVED_NOT_ADMITTED",
 "parent_sha256":sha(PARENT),"source_pins":pins,"source_unchanged":True,"groups":output,
 "scope":"Raw parquet split/template/task columns only. Container train, original split and model exposure are distinct. Does not reconstruct missing original instance IDs or certify split safety.",
 "new_admission":0,"model_loading":False,"gpu_calls":0,"internal_wall_seconds":time.monotonic()-START,
 "operation_sha256":sha(Path(__file__))}
raw=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False).encode()+bytes([10])
assert len(raw)<20_000_000
with TARGET.open("xb") as f:f.write(raw)
print(json.dumps({"output":str(TARGET),"seconds":result["internal_wall_seconds"],"groups":output},ensure_ascii=False))
