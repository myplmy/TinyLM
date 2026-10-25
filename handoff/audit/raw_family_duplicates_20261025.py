#!/usr/bin/env python3
"""Exact visible-message duplicate census; no source deletion or admission."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,sys,time
import pyarrow.parquet as pq,pyarrow.compute as pc
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.p106b_mixed_scale import attach,digest,TOKENIZER,TOK_SHA
from scripts.p106b_capability_corpus import engine
from tinylm.data.sft import encode_conversation,sft_targets,conversation_split_key
from tokenizers import Tokenizer
START=time.monotonic()
PARENT=ROOT/"handoff/audit/WIP_20261025_DOLLY_MINTAKA_RAW_TOKEN_INVENTORY_V2.json"
META=ROOT/"handoff/audit/WIP_20261025_DOLLY_MINTAKA_RAW_METADATA.json"
OUT=ROOT/"handoff/audit/WIP_20261025_DOLLY_MINTAKA_EXACT_DUPLICATES.json"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert not OUT.exists()
before={str(p):sha(p) for p in (PARENT,META)}
parent=json.loads(PARENT.read_text());assert parent["returncode"]==0 and json.loads(META.read_text())["source_unchanged"]
inventory=json.loads((ROOT/"HF/sft_ready/p106b_capability_source_inventory_v1/report.json").read_text())
specs={s["path"]:s for s in inventory["input"]["sources"]}
assert digest(TOKENIZER)==TOK_SHA
tok=Tokenizer.from_file(str(TOKENIZER))
counts=defaultdict(Counter);pairs=defaultdict(dict);questions=defaultdict(lambda:defaultdict(set));examples=defaultdict(list)
for rel,pin in parent["source_pins"].items():
 p=ROOT/rel;assert rel.startswith("HF/") and sha(p)==pin
 lang="en" if "/english/" in rel else "ko"
 for batch in pq.ParquetFile(p).iter_batches(batch_size=8192,columns=["id","inputs","targets","dataset_name","template_id"],use_threads=False):
  if time.monotonic()-START>300:raise TimeoutError("duplicate census CPU window")
  family=batch.column("dataset_name")
  mask=pc.or_(pc.starts_with(family,"Dolly-v2"),pc.starts_with(family,"Mintaka-inst"))
  for r in batch.filter(mask).to_pylist():
   f=engine.family_bucket(r["dataset_name"])
   if f not in ("Dolly-v2","Mintaka-inst"):continue
   q,a=r["inputs"],r["targets"]
   if not isinstance(q,str) or not isinstance(a,str) or not q.strip() or not a.strip():continue
   row=attach([{"role":"user","content":q.strip()},{"role":"assistant","content":a.strip()}],specs[rel],r["id"],lang,r["dataset_name"])
   key=lang+":"+f;cnt=counts[key];cnt["rows"]+=1
   payload=json.dumps(row["messages"],ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
   pair=hashlib.sha256(payload).hexdigest().upper()
   question=conversation_split_key(row).hex().upper()
   answer=hashlib.sha256(a.strip().encode()).hexdigest().upper()
   questions[key][question].add(answer)
   if pair in pairs[key]:
    cnt["exact_duplicate_rows"]+=1
    if len(examples[key])<8:examples[key].append({"id":r["id"],"template_id":r["template_id"],"messages_sha256":pair,"question_split_key":question})
    continue
   cnt["distinct_message_pairs"]+=1
   ids,labels,_=encode_conversation(row,tok);x,y=sft_targets(ids,labels)
   target=sum(v>=0 for v in y)
   pairs[key][pair]=(len(x),target)
   if len(x)<=1024 and target>0:
    cnt["distinct_technical_fit_rows"]+=1;cnt["distinct_fit_input_tokens"]+=len(x);cnt["distinct_fit_assistant_targets"]+=target
 assert sha(p)==pin
assert {k:v["rows"] for k,v in counts.items()}==parent["expected_normalized_rows"]
for k,v in counts.items():
 v["distinct_first_user_split_keys"]=len(questions[k])
 v["first_user_keys_with_multiple_answer_texts"]=sum(len(a)>1 for a in questions[k].values())
assert all(sha(Path(p))==s for p,s in before.items()) and digest(TOKENIZER)==TOK_SHA
result={"schema":"VISIBLE_SOURCE_EXACT_DUPLICATE_CENSUS_V1","status":"EXACT_DUPLICATES_COUNTED_NOT_ADMITTED",
 "parents":before,"source_pins":parent["source_pins"],"source_unchanged":True,
 "counts":{k:dict(v) for k,v in counts.items()},"duplicate_id_examples":dict(examples),
 "contract":"Full normalized visible user+assistant messages, role order and case preserved; original conversation_split_key separately counts first-user groups. Different replies to same user are warnings, not semantic contradictions.",
 "scope":"No nonidentical paraphrase/concept dedup; no source-instance recovery, split-safety or quality certification. No duplicate source was deleted.",
 "new_admission":0,"model_loading":False,"gpu_calls":0,"tokenizer_sha256":TOK_SHA,
 "internal_wall_seconds":time.monotonic()-START,"operation_sha256":sha(Path(__file__))}
raw=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False).encode()+bytes([10])
assert len(raw)<20_000_000
with OUT.open("xb") as f:f.write(raw)
print(json.dumps({"output":str(OUT),"seconds":result["internal_wall_seconds"],"counts":result["counts"]},ensure_ascii=False))
