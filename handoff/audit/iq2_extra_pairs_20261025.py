#!/usr/bin/env python3
"""Posthoc extra IQ2 Core6 pairs; reuses closed evidence and original statistics."""
from pathlib import Path
import hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts import summarize_p106b_native_core6_pairs as native
from scripts import summarize_p106b_core6_pairs as common
from scripts.p106b_official_tasks import task_requests
START=time.monotonic()
TARGET=ROOT/"test_result/evidence/p106b_iq2_extra_pairs_20261025"
ROOT_RECEIPT="handoff/audit/WIP_20261025_IQ2_FULL_ROOT_CLOSURE.json"
PIN="87637692817FDF6BB6252DBC1CE36EAE948A4F5F119D3C1CDAC9CF4478D0050F"
MODEL="qwen35_08b_iq2xxs"
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def need(ok,text):
 if not ok:raise ValueError(text)
need(not TARGET.exists(),"preserve existing output")
with common.cpu_wall_limit(120):
 source=native.source_identity()
 evidence=native.Evidence()
 audit=evidence.json(ROOT/ROOT_RECEIPT,PIN)
 need(audit["schema"]=="ROOT_IQ2_FULL_CLOSURE_20261025_V1"
  and audit["actual_root_exit"]==audit["actual_controller_exit"]==audit["worker_returncode"]==0
  and audit["actual_supervisor_exit_observed_by_root"] is True
  and audit["raw_recount"] is True and audit["counts"]==common.COUNTS
  and audit["worker_cleanup_complete"] is True and audit["source_and_assets_unchanged"] is True,
  "exact closed root execution is required")
 path=ROOT/audit["report_path"]
 report=evidence.json(path,audit["report_sha256"])
 terminal=evidence.json(path.parent/"terminal_receipt.json",audit["terminal_sha256"])
 evidence.json(path.parent.parent/"supervisor/supervisor_receipt.json",audit["supervisor_sha256"])
 need(report["returncode"]==9 and report["candidate_returncode"]==0
  and report["status"]==audit["primary_report_status"]
  and terminal["returncode"]==0 and terminal["status"]==audit["terminal_status"]
  and terminal["report_sha256"]==audit["report_sha256"]
  and report["actual_counts"]==common.COUNTS and report["choice_likelihoods"]==67106
  and report["raw_independent_recount"] is True and report["training"] is False
  and report["source_identity"]["sha256"]==audit["source_sha256"],
  "native pending report and terminal/root closure must stay distinct")
 for name in ("terminal_failure_receipt.json","report_closure_failure.json"):
  evidence.no_file(path.parent/name)
 gpt_path,gpt_report,gpt_closure=native.native_bundle(source,evidence)
 reports={}
 for peer in common.MODELS:
  p=common.report_path(peer)
  r=evidence.json(p)
  common.admit_report(peer,r)
  reports[peer]=(p,r)
 reports[native.MODEL]=(gpt_path,gpt_report)
 reports[MODEL]=(path,report)
 tasks,task_proof=common.load_readonly_tasks(evidence.inputs)
 contracts={n:common.CaseContracts(tasks[n],common.COUNTS[n],task_requests) for n in common.PRIMARY}
 counted,correspondence={},None
 for peer,(p,r) in reports.items():
  row=common.recount_model(peer,p,r,tasks,evidence.inputs,task_requests,contracts)
  if correspondence is None:correspondence=row["correspondence"]
  need(row["correspondence"]==correspondence,"ordered case correspondence mismatch")
  counted[peer]=row
 pairs={peer+"__"+MODEL:dict(left_model=peer,right_model=MODEL,
  **common.paired_intervals(row["values"],counted[MODEL]["values"],draws=100000,seed=20261024))
  for peer,row in counted.items() if peer!=MODEL}
 evidence.unchanged()
 need(native.source_identity()==source,"shared statistical source changed")
 for row in counted.values():row.pop("values")
 result={"schema":"ROOT_IQ2_EXTRA_CORE6_PAIRED_READBACK_V1",
  "status":"CPU_COMPLETE_PENDING_ROOT_ACTUAL_EXIT","input_root_receipt_sha256":PIN,
  "source_identity":source,"operation_sha256":sha(Path(__file__)),
  "tasks":task_proof,"models":counted,"new_pairs":pairs,"preserved_prior_pairs":28,
  "new_pair_count":8,"total_pair_count":36,"inputs_unchanged":True,
  "input_files":evidence.inputs.files,"model_loading":False,"gpu_calls":0,"checkpoint_writes":0,
  "statistical_scope":"Posthoc case-paired percentile95 within fixed6tasks;100000draws;seed20261024;equal-task mean;multiple comparisons uncorrected;not training-seed uncertainty or model-adoption proof",
  "internal_wall_seconds":time.monotonic()-START}
 raw=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False).encode()+bytes([10])
 need(len(raw)<20_000_000,"individual output must be below20MB")
 TARGET.mkdir()
 with (TARGET/"report.json").open("xb") as stream:stream.write(raw)
 evidence.unchanged()
 print(json.dumps({"pairs":8,"total_pairs":36,"report":str(TARGET/"report.json"),
  "sha256":sha(TARGET/"report.json"),"seconds":time.monotonic()-START,
  "mean6":{k:v["mean6"] for k,v in pairs.items()}},ensure_ascii=False))
