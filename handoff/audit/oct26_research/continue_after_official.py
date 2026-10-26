#!/usr/bin/env python3
"""Run only the fixed, preapproved post-full sequence; no automatic retry."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
END=datetime(2026,10,26,7,45,tzinfo=timezone.utc).timestamp()
SOURCE="6E08116657927517C1A8FE6C616902DA2794996D3E6934AD21125E4F317BAA22"
STEPS=(
 "run_P106B_Stage10fWe_format_muon_dialogue_json_recovery.sh",
 "run_P106B_Stage10fWf_format_normuon_dialogue_json_recovery.sh",
 "run_P106B_Stage10gWc_native_format_pair_stats_json_recovery.sh",
 "run_P106B_Stage4fsZbW_capacity_after_eval_resume.sh")

def digest(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def publish(path,value):
 raw=json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True).encode()
 if len(raw)>=20_000_000: raise ValueError("metadata size limit")
 with Path(path).open("xb") as stream: stream.write(raw)

def prepare():
 marker=BASE/"official_pair_actual_tool_exit_v3.json"
 if not marker.is_file(): raise FileNotFoundError("both actual official launcher exits are absent")
 proof=json.loads(marker.read_text())
 if proof.get("schema")!="TINYLM_OFFICIAL_PAIR_ACTUAL_EXIT_V3" or proof.get("actual_tool_exits")!=[0,0] \
    or any(type(code) is not int for code in proof["actual_tool_exits"]) \
    or set(proof.get("roots",{}))!={"format_muon","format_normuon"} or proof.get("official_source_sha256")!=SOURCE:
  raise ValueError("actual official exit proof differs")
 for ref in proof["roots"].values():
  path=ROOT/ref["path"]
  if digest(path)!=ref["sha256"]: raise ValueError("full closure reference changed")
  closed=json.loads(path.read_text())
  if type(closed.get("actual_supervisor_exit")) is not int or closed["actual_supervisor_exit"]!=0:
   raise ValueError("official full parent did not close")
  report=ROOT/closed["path"]
  if digest(report)!=closed["sha256"]: raise ValueError("official full report changed")
  value=json.loads(report.read_text())
  if value.get("returncode")!=0 or value.get("source_sha256")!=SOURCE or value.get("mode")!="full" \
     or value.get("worker",{}).get("status")!="OFFICIAL_CORE6_FULL_COMPLETE":
   raise ValueError("official full source or status differs")
 for name in STEPS:
  path=ROOT/name
  if path.is_symlink() or not path.is_file(): raise ValueError("exact regular launcher required")
 return {name:digest(ROOT/name) for name in STEPS}

def run_steps(steps,launch,remaining,record):
 for index,name in enumerate(steps):
  if remaining()<=120:
   record(dict(index=index,launcher=name,status="TIME_HOLD_NOT_RUN",actual_exit=8))
   return 8
  began=time.monotonic(); started_epoch=time.time()
  code=launch(name,max(1,int(remaining()-120)))
  if type(code) is not int: code=9
  record(dict(index=index,launcher=name,actual_exit=code,actual_wall_sec=time.monotonic()-began,
              started_epoch=started_epoch,ended_epoch=time.time()))
  if code!=0: return code
 return 0

def main():
 parser=argparse.ArgumentParser()
 group=parser.add_mutually_exclusive_group(required=True)
 group.add_argument("--check-only",action="store_true")
 group.add_argument("--execute",action="store_true")
 args=parser.parse_args()
 try: pins=prepare()
 except FileNotFoundError:
  print(json.dumps(dict(status="OFFICIAL_PAIR_NOT_CLOSED",returncode=8,files_written=0)))
  return 8
 if args.check_only:
  print(json.dumps(dict(status="FIXED_SEQUENCE_PREPARED",steps=list(STEPS),models_loaded=0,files_written=0)))
  return 0
 output=BASE/"postfull_async_v1"
 output.mkdir(exist_ok=False)
 publish(output/"inputs.json",dict(launcher_sha256=pins,source_sha256=digest(__file__),deadline_epoch=END))
 def launch(name,cap):
  if digest(ROOT/name)!=pins[name]: raise ValueError("launcher changed before execution")
  code=subprocess.run(["timeout","--signal=TERM","--kill-after=10s",str(cap)+"s","bash",name],
                      cwd=ROOT,stdin=subprocess.DEVNULL).returncode
  if digest(ROOT/name)!=pins[name]: raise ValueError("launcher changed during execution")
  return code
 def record(row):
  publish(output/("step_"+str(row["index"]).zfill(2)+".json"),row)
  print(json.dumps(row),flush=True)
 code=run_steps(STEPS,launch,lambda:END-time.time(),record)
 publish(output/"terminal.json",dict(actual_sequence_exit=code,normal_production_pause_requires_root_readback=True))
 return code

if __name__=="__main__":
 raise SystemExit(main())
