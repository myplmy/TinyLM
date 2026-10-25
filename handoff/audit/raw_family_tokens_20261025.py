#!/usr/bin/env python3
"""Bounded raw-token upper inventory for two already-held source families."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,os,signal,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts import p106b_capability_corpus as c
from scripts.p106b_public_refill import english_rows
from scripts.p106b_mixed_scale import digest,TOKENIZER,TOK_SHA
from tinylm.data.sft import encode_conversation,sft_targets
from tokenizers import Tokenizer
START=time.monotonic()
TARGET=ROOT/"handoff/audit/WIP_20261025_DOLLY_MINTAKA_RAW_TOKEN_INVENTORY.json"
PIN="1C40536A05F349303BE780AF0FE714D59587B4CE17FEA974CC115CCB67F0AE94"
SOURCE=ROOT/"HF/sft_ready/p106b_capability_source_inventory_v1/report.json"
CAP=1500
class WindowEnd(Exception):pass
def budget():
 if time.monotonic()-START>CAP-30:raise WindowEnd("bounded CPU census pause; not full")
def expired(*args):raise WindowEnd("bounded CPU census alarm")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
assert not TARGET.exists() and sha(SOURCE)==PIN and digest(TOKENIZER)==TOK_SHA
inventory=json.loads(SOURCE.read_text())
families={"Dolly-v2","Mintaka-inst"}
groups=[g for g in inventory["groups"] if g["family"] in families]
expected={g["language"]+":"+g["family"]:g["original_rows"] for g in groups}
wanted_paths={p for g in groups for p in g["source_paths"]}
specs=[s for s in inventory["input"]["sources"] if s["path"] in wanted_paths]
assert len(specs)==9 and len(expected)==4
source_pins={}
for s in specs:
 assert s["path"].startswith("HF/") and not (ROOT/s["path"]).is_symlink()
 budget();assert digest(ROOT/s["path"])==s["sha256"];source_pins[s["path"]]=s["sha256"]
tokenizer=Tokenizer.from_file(str(TOKENIZER))
counts=defaultdict(Counter);completed=[];scanned=0;code=9;error=None
signal.signal(signal.SIGALRM,expired)
signal.setitimer(signal.ITIMER_REAL,max(1,CAP-(time.monotonic()-START)))
try:
 for spec in specs:
  file_rows=0;budget()
  for row in english_rows(spec):
   scanned+=1;file_rows+=1
   if scanned%512==0:budget()
   family=c.engine.family_bucket(row["meta"]["source_family"])
   if family not in families:continue
   key=row["meta"]["language"]+":"+family
   assert key in expected
   cnt=counts[key];cnt["normalized_rows"]+=1
   try:
    ids,labels,_=encode_conversation(row,tokenizer);x,y=sft_targets(ids,labels)
   except (ValueError,TypeError,KeyError):
    cnt["serialization_rejected"]+=1;continue
   target=sum(v>=0 for v in y)
   cnt["all_input_tokens"]+=len(x);cnt["all_assistant_targets"]+=target
   if len(x)<=1024 and target>0:
    cnt["technical_fit_rows"]+=1;cnt["technical_fit_input_tokens"]+=len(x);cnt["technical_fit_assistant_targets"]+=target
   else:cnt["over1024_or_zero_target"]+=1
  assert digest(ROOT/spec["path"])==source_pins[spec["path"]]
  completed.append(spec["path"])
  print(json.dumps({"file":spec["path"],"normalized_rows":file_rows,"cumulative_scanned":scanned,
   "selected_rows":sum(v["normalized_rows"] for v in counts.values()),"seconds":time.monotonic()-START}),flush=True)
 assert {k:v["normalized_rows"] for k,v in counts.items()}==expected
 assert len(completed)==len(specs)
 code=0
except WindowEnd as e:code=8;error=str(e)
except BaseException as e:code=9;error=type(e).__name__+": "+str(e)
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
unchanged=sha(SOURCE)==PIN and digest(TOKENIZER)==TOK_SHA
for name in completed:unchanged=unchanged and digest(ROOT/name)==source_pins[name]
if not unchanged:code=9
report={"schema":"P106B_EXISTING_FAMILY_RAW_TOKEN_UPPER_INVENTORY_V1","returncode":code,
 "status":"RAW_FAMILY_CENSUS_COMPLETE_NOT_ADMITTED" if code==0 else "PARTIAL_NOT_WHOLE" if code==8 else "ERROR_PARTIAL_PRESERVED",
 "source_report_sha256":PIN,"source_pins":source_pins,"completed_files":completed,
 "expected_normalized_rows":expected,"scanned_normalized_rows":scanned,"counts":{k:dict(v) for k,v in counts.items()},
 "inputs_unchanged":unchanged,"error":error,"operation_sha256":sha(Path(__file__)),
 "scope":"Exact raw serialization counts only; not unique source token count, QA-only, verified facts, rights approval, split-safe source reconstruction or usable supply. No family alias or corpus policy changed.",
 "max_sequence":1024,"tokenizer_sha256":TOK_SHA,"full_usable_tokens":"NOT_MEASURED","new_admission_tokens":0,
 "model_loading":False,"gpu_calls":0,"teacher_calls":0,"checkpoint_writes":0,"internal_wall_seconds":time.monotonic()-START}
raw=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False).encode()+bytes([10])
assert len(raw)<20_000_000
with TARGET.open("xb") as f:f.write(raw)
print(json.dumps({k:report[k] for k in ("status","returncode","counts","inputs_unchanged","internal_wall_seconds")},ensure_ascii=False),flush=True)
raise SystemExit(code)
