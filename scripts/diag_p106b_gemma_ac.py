#!/usr/bin/env python3
"""User-run teacher-only context capacity then batch x thinking factorial.

Uses eight original-public QA jobs from the immutable successful family64 pilot.
No student/training/download. Teacher content remains pseudo-label unverified.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_gemma_ac as core
from scripts import p106b_gemma_teacher as teacher
from scripts import diag_p106b_gemma_telemetry_resume as telemetry
from scripts.diag_p106d_views import request_with_evidence
from scripts.p106b_mixed_scale import digest,TOKENIZER,TOK_SHA
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit,disposition

CODE=("scripts/p106b_gemma_ac.py","scripts/diag_p106b_gemma_ac.py",
      "scripts/test_p106b_gemma_ac.py","scripts/p106b_gemma_teacher.py",
      "scripts/p106d_teacher_views.py","scripts/diag_p106d_views.py",
      "scripts/p106b_teacher_wrapper.py","tinylm/chat/canonical.py","tinylm/data/sft.py")
FAMILY64=ROOT/"HF/sft_ready/p106b_gemma_task_family64_v3"
FAMILY_SHA="D8C7211799208081CF4DE1D624E3E8A5A3223E8ACAF7ED9D1A0A266B5960874B"

def directory(tag,mode):
    if not re.fullmatch(r"[a-z0-9_]+",tag):raise ValueError("safe fresh tag required")
    p=ROOT/"test_result/evidence"/tag/mode
    if any(x.is_symlink() for x in (p,*p.parents)):raise ValueError("linked output")
    return p

def write(path,report):
    body=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    if len(body.encode())>20_000_000:raise ValueError("report exceeds20MB")
    with path.open("x",encoding="utf-8") as f:f.write(body)

def info(a):
    return {"schema":core.VERSION,"mode":a.mode,"tag":a.tag,
        "code_sha256":{n:digest(ROOT/n) for n in CODE},"logical_requests":56,
        "maximum_attempts_per_batch":3,"maximum_physical_requests":168,
        "context":core.CONTEXT,"max_output":core.MAX_OUTPUT,"thinking":list(core.THINKING),
        "sizes":list(core.SIZES),"card_sampler":teacher.SAMPLER,"mtp":False,
        "model_loading":"NOT_RUN","student_training":"NOT_RUN","formal_train_ready":False}

def require_contract(a,metadata):
    report=json.loads((directory(a.tag,"contract")/"report.json").read_text())
    if report.get("status")!="CPU_CONTRACT_PASS" or report["input"]["code_sha256"]!=metadata["code_sha256"]:
        raise FileNotFoundError("current CPU contract absent/stale")

def jobs_and_tokenizer():
    from tokenizers import Tokenizer
    p=FAMILY64/"report.json"
    if p.is_symlink() or digest(p)!=FAMILY_SHA:raise ValueError("pinned family64 report changed")
    report=json.loads(p.read_text())
    if report.get("status")!="TASK_PILOT_COMPLETE" or report.get("accepted_groups")!=64:
        raise FileNotFoundError("successful exact family64 source proof required")
    manifest=report["raw_manifest"];verify(FAMILY64,manifest)
    jobs={}
    for part in manifest["shards"]:
        for line in (FAMILY64/part["path"]).read_text().splitlines():
            rec=json.loads(line);job=rec.get("job")
            if isinstance(job,dict) and job.get("task")=="qa":
                key=job["source_group_id"]
                if key in jobs and jobs[key]!=job:raise ValueError("conflicting original source job")
                jobs[key]=job
    chosen=[]
    for lang in ("ko","en"):
        candidates=[j for k,j in sorted(jobs.items()) if j["language"]==lang
            and len(json.dumps(j["original"]["messages"],ensure_ascii=False))<=3000]
        if len(candidates)<4:raise FileNotFoundError("four bounded distinct QA sources per language missing")
        chosen.extend(candidates[:4])
    if TOKENIZER.is_symlink() or digest(TOKENIZER)!=TOK_SHA:raise ValueError("chat32 identity differs")
    core.plan(chosen)
    return chosen,Tokenizer.from_file(str(TOKENIZER)),{
        "family64_sha256":FAMILY_SHA,"tokenizer_sha256":TOK_SHA,
        "source_group_ids":[j["source_group_id"] for j in chosen],
        "source_hash":hashlib.sha256(json.dumps(chosen,sort_keys=True,ensure_ascii=False).encode()).hexdigest().upper(),
        "source_scope":"original public QA from family64; not old OASST1-only deck or repeated filler"}

@contextmanager
def profile(context,maximum,thought):
    with patch.object(teacher,"CONTEXT",context),patch.object(teacher,"MAX_OUTPUT",maximum),patch.object(teacher,"THINKING",thought):
        yield

def sampled_resource_ok(memory,proof):
    free=memory.get("sampled_gpu_min_free_mib")
    return (type(free) in (int,float) and free>=2048
        and proof.get("measurement_coverage")=="SAMPLED_ONLY"
        and proof.get("successful_queries",0)>0 and proof.get("fatal_calls",0)==0)

def capacity(a,metadata,output):
    assets=teacher.assets(True);rows=[];deadline=time.monotonic()+a.max_wall_sec
    from scripts.p106d_teacher_views import cases
    case=cases()[0]
    for context,maximum,thought in core.CAPACITY:
        if time.monotonic()>=deadline:raise TimeoutError("capacity wall budget")
        reader=telemetry.RetryingMemoryReader(telemetry.memory_source.read_memory,emit=lambda l:print(l,flush=True))
        idle_before_gpu();row={"context":context,"max_output":maximum,"thinking":thought,"passed":False}
        session=None
        try:
            with profile(context,maximum,thought),telemetry.telemetry_scope(reader),teacher.GemmaSession(False) as session:
                metadata["model_loading"]="MEASURED"
                from scripts.p106d_teacher_views import payload
                request=payload(case,1,1337);request["max_tokens"]=maximum
                session.count_prompt(request["messages"],context,maximum)
                reply=request_with_evidence(session,request,lambda record:None,"capacity",timeout=300)
                memory=session.memory();free=memory.get("sampled_gpu_min_free_mib")
                row.update(memory=memory,server_props=session.props,usage=reply.get("usage",{}),
                    finish_reason=reply["choices"][0].get("finish_reason"),reply=reply,telemetry=reader.snapshot())
                row["passed"]=sampled_resource_ok(memory,reader.snapshot())
        except BaseException as e:
            if isinstance(e,KeyboardInterrupt):raise
            row.update(error_type=type(e).__name__,reason=str(e),partial_telemetry=reader.snapshot())
        rows.append(row);print("[CAPACITY_PROFILE] "+json.dumps(row,ensure_ascii=False),flush=True)
    ready=any(r["context"]==core.CONTEXT and r["passed"] for r in rows)
    return {"input":metadata,"status":"CAPACITY_MEASURED","profiles":rows,"panel_resource_ready":ready,
        "assets":assets,"scope":"teacher-only sampled memory; no long-production/OOM guarantee"},0 if ready else 8

def panel(a,metadata,output):
    from tinylm.data.sft import encode_conversation,sft_targets
    cap=json.loads((directory(a.tag,"capacity")/"report.json").read_text())
    if not cap.get("panel_resource_ready") or cap["input"]["code_sha256"]!=metadata["code_sha256"]:
        raise FileNotFoundError("matching16k/6144 teacher-only capacity proof required")
    jobs,tok,source=jobs_and_tokenizer();assets=teacher.assets(True)
    metadata.update(source,assets=assets)
    raw=ShardWriter(output,"teacher_raw");saved=ShardWriter(output,"teacher_canonical")
    arms=[];started=time.perf_counter();deadline=time.monotonic()+a.max_wall_sec
    try:
        for repeat,size,thought in core.plan(jobs):
            idle_before_gpu();reader=telemetry.RetryingMemoryReader(telemetry.memory_source.read_memory,emit=lambda l:print(l,flush=True))
            accepted=set();xmass=targets=0;seconds=completion=attempts=0
            with profile(core.CONTEXT,core.MAX_OUTPUT,thought),telemetry.telemetry_scope(reader),teacher.GemmaSession(False) as session:
                metadata["model_loading"]="MEASURED"
                for batch_index,block in enumerate(core.blocks(jobs,size)):
                    retained={}
                    for attempt in range(1,4):
                        if time.monotonic()>=deadline:raise TimeoutError("factorial wall budget")
                        seed=int(hashlib.sha256((str(repeat)+":"+str(size)+":"+
                            ":".join(j["source_group_id"] for j in block)).encode()).hexdigest()[:8],16)&0x7fffffff
                        request=core.payload(block,thought,seed+attempt-1,
                            "" if attempt==1 else "STRUCTURE RETRY: repair missing/empty/order fields only.")
                        generation=f"r{repeat}_n{size}_t{thought}_b{batch_index}_a{attempt}"
                        began=time.perf_counter();reply=None
                        record={"generation_id":generation,"repeat":repeat,"size":size,"thinking":thought,
                            "source_group_ids":[j["source_group_id"] for j in block],"request":request,"attempt":attempt}
                        try:
                            record["input_budget"]=session.count_prompt(request["messages"],core.CONTEXT,core.MAX_OUTPUT)
                            reply=request_with_evidence(session,request,raw.append,generation,
                                timeout=min(300,max(1,int(deadline-time.monotonic()))))
                            parsed=core.parse(reply,len(block));record.update(reply=reply,parsed=parsed)
                            for i,pair in parsed["slots"].items():
                                if i in retained:continue
                                row=core.canonical(block[i],pair,assets["model_sha256"],generation,
                                    parsed["thinking"],"teacher_raw:"+generation)
                                ids,labels,_=encode_conversation(row,tok,"chatml");xx,yy=sft_targets(ids,labels)
                                count=sum(v>=0 for v in yy)
                                if not 0<len(xx)<=1024 or not count:continue
                                row["meta"].update(batch_concepts=size,thinking_budget=thought,repeat=repeat)
                                retained[i]=(row,len(xx),count)
                        except ValueError as e:
                            record.update(status="WIRE_OR_MASK_REJECT",reason=str(e))
                        finally:
                            dt=time.perf_counter()-began;seconds+=dt;attempts+=1
                            usage=(reply or {}).get("usage",{}).get("completion_tokens",0)
                            if type(usage)==int:completion+=usage
                            record["request_wall_sec"]=dt;raw.append(record)
                        if len(retained)==len(block):break
                    for i,(row,x,y) in retained.items():
                        saved.append(row);xmass+=x;targets+=y
                        accepted.add(block[i]["language"]+":"+block[i]["source_group_id"])
                memory=session.memory()
            arm={"repeat":repeat,"size":size,"thinking":thought,"accepted_keys":sorted(accepted),
                "candidate_x_tokens":xmass,"candidate_targets":targets,"request_sum_sec":seconds,
                "candidate_x_per_sec":xmass/seconds if seconds else None,"completion_tokens":completion,
                "physical_requests":attempts,"memory":memory,"telemetry":reader.snapshot()}
            arm["resource_ok"]=sampled_resource_ok(memory,reader.snapshot())
            arms.append(arm);print("[AC_ARM] "+json.dumps(arm,ensure_ascii=False),flush=True)
    finally:
        manifests={}
        for name,writer in (("raw_manifest",raw),("candidate_manifest",saved)):
            if writer._total_rows:
                m=writer.close(lineage=metadata);verify(output,m);manifests[name]=m
        write(output/"partial.json",{"input":metadata,"arms":arms,"manifests":manifests,
            "whole_wall_sec":time.perf_counter()-started,"student_training":"NOT_RUN"})
    summary=core.summarize(arms)
    summary["resource_all_measured_safe"]=all(a["resource_ok"] for a in arms)
    complete=summary["same_completed_source_sets"] and summary["resource_all_measured_safe"]
    return {"input":metadata,"status":"FACTORIAL_COMPLETE" if complete else "FACTORIAL_GATE_NEGATIVE",
        "arms":arms,"summary":summary,"manifests":manifests,"whole_wall_sec":time.perf_counter()-started},0 if complete else 8

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--mode",choices=("contract","capacity","panel"),required=True)
    p.add_argument("--tag",default="p106b_gemma_ac_v1_s1337");p.add_argument("--max-wall-sec",type=int,default=3600)
    p.add_argument("--execute",action="store_true");p.add_argument("--check-only",action="store_true");a=p.parse_args()
    if not 60<=a.max_wall_sec<=7200:p.error("bounded wall60..7200 required")
    metadata=info(a);output=directory(a.tag,a.mode)
    if a.check_only or not a.execute:print("[PREFLIGHT] "+json.dumps(metadata));return 0
    if output.exists():print("[HOLD] preserve evidence; use new stage");return 8
    output.mkdir(parents=True)
    try:
        if a.mode=="contract":
            r=subprocess.run([sys.executable,"-B","-X","utf8","-m","unittest","scripts.test_p106b_gemma_ac","-v"],cwd=ROOT,timeout=600)
            if r.returncode:raise ValueError("CPU contracts failed")
            report={"input":metadata,"status":"CPU_CONTRACT_PASS"};rc=0
        else:
            require_contract(a,metadata)
            with wall_limit(a.max_wall_sec):
                report,rc=capacity(a,metadata,output) if a.mode=="capacity" else panel(a,metadata,output)
    except BaseException as e:
        status,rc=disposition(e);report={"input":metadata,"status":status,"error_type":type(e).__name__,"reason":str(e)}
        if isinstance(e,(FileNotFoundError,FileExistsError)):report["status"]="PREREQUISITE_HOLD";rc=8
    write(output/"report.json",report)
    print("[EXPERIMENT_FINAL] "+json.dumps({"mode":a.mode,"status":report["status"],"exit_code":rc,
        "student_training":"NOT_RUN","evidence":str(output.relative_to(ROOT))}));return rc

if __name__=="__main__":raise SystemExit(main())
