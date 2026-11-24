"""Fill only the missing official KoBEST runs for three fixed comparison models."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import json
import math
import os
from pathlib import Path
import subprocess
import time

from scripts import diag_p106b_bonsai_native_mc as mc
from scripts import diag_p106b_external_core6 as external
from scripts import diag_p106b_official_core6 as native
from scripts import diag_p106b_qwen35_fixedshape as qwen
from scripts import p106b_qwen35_fixedshape as fixed
from scripts.p106b_official_lm_adapter import canonical
from scripts.p106b_shards import ShardWriter, verify as verify_shards


ROOT = mc.ROOT
TAG = "p106b_kobest_exact_followups_v2_20261118"
OUT = ROOT/"test_result/evidence"/TAG
PROFILE = OUT/"profile.json"
CUTOFF = mc.lambada.CUTOFF
MODELS = {"native595-q": 1200, "gemma1b": 1200, "qwen3508": 2000}
MAX_SECONDS = sum(MODELS.values())+180
NATIVE_REPORT = ROOT/"test_result/evidence/p106b_official_core6_v2/native595-q/full/report.json"
SOURCE_PINS = ("scripts/diag_p106b_kobest_exact_followups.py",
    "scripts/diag_p106b_official_core6.py","scripts/diag_p106b_external_core6.py",
    "scripts/diag_p106b_qwen35_fixedshape.py","scripts/p106b_qwen35_fixedshape.py")


def inputs():
    tasks, files, definition = mc.load_tasks(kobest_only=True)
    items, proof = mc.prepare_items(tasks)
    return tasks, items, dict(files=files,definition=definition,proof=proof)


def references():
    report = mc.prism.read(NATIVE_REPORT)
    assert report["returncode"]==0
    provenance = report["model_proof"]["provenance"]
    checkpoint = provenance["checkpoint"]
    pinned = provenance["checkpoint_sha256"]
    assert native.digest(ROOT/checkpoint)==pinned
    wp = qwen.verify()
    qwen.prerequisite("full",qwen.q.digest(qwen.BASE/"profile.json"))
    return dict(native=dict(report=native.digest(NATIVE_REPORT),path=checkpoint,sha256=pinned),
        gemma=external.asset_identity("gemma1b"),
        qwen_profile_sha256=qwen.q.digest(qwen.BASE/"profile.json")), wp


def prepare():
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==""
    models,_ = references()
    _, _, meta = inputs()
    sources = dict(mc.source_pins(), **{name:native.digest(ROOT/name) for name in SOURCE_PINS})
    OUT.mkdir(exist_ok=False)
    mc.prism.write(PROFILE,dict(schema="P106B_EXACT_KOBEST_PROFILE_V1",tag=TAG,refs=models,
        tasks=meta,sources=sources,model_caps=MODELS,max_seconds=MAX_SECONDS,model_loads=0))
    print("EXACT_KOBEST_PREPARED",native.digest(PROFILE),list(MODELS),flush=True)


def verify():
    profile = mc.prism.read(PROFILE)
    refs, qp = references()
    assert profile["refs"] == refs
    assert profile["model_caps"] == MODELS and profile["max_seconds"] == MAX_SECONDS
    assert all(native.digest(ROOT/name)==sha for name,sha in profile["sources"].items())
    assert all(native.digest(ROOT/name)==sha for name,sha in profile["tasks"]["files"].items())
    return profile,qp


@contextmanager
def runtime(name, torch, profile, qp, directory, check, report):
    if name=="native595-q":
        with native.model_runtime(name,torch) as (lm, proof):
            report["model_proof"] = proof
            report["numerical_canary"] = native.numerical_canary(lm,torch)
            yield lm
    elif name=="gemma1b":
        proof = report["model_proof"] = {}
        with external.model_runtime(name,torch,profile["refs"]["gemma"],proof=proof) as (lm,_):
            report["numerical_canary"] = external.numerical_canary(lm,torch)
            yield lm
    else:
        proof = report["model_proof"] = {}
        lengths = ShardWriter(directory,"qwen_token_lengths")
        try:
            with qwen.q.model_runtime(torch,qp["assets"],lengths,check,proof,qp["source_identity"]) as lm:
                stats = report["fixed_calls"] = {}
                with fixed.fixed_calls(lm,width=1024,pad_id=248044,check=check,stats=stats):
                    report["numerical_canary"] = {}
                    qwen.numerical_canary(lm,torch,check,report["numerical_canary"])
                    yield lm
        finally:
            if lengths._total_rows:
                manifest = lengths.close(lineage=dict(tag=TAG,model=name,evaluation_only=True))
                verify_shards(directory,manifest)
                report["qwen_lengths_manifest"] = manifest


def score(lm, name, items):
    from lm_eval.api.instance import Instance

    requests = [Instance(request_type="loglikelihood",doc=item["doc"],arguments=tuple(args),idx=i,
        metadata=(name,item["doc_id"],1)) for item in items for i,args in enumerate(item["arguments"])]
    values = lm.loglikelihood(requests,disable_tqdm=True)
    assert len(values)==len(requests)
    offset = 0
    rows = []
    for item in items:
        n = len(item["arguments"])
        responses = [mc.lambada.official.valid_response(r) for r in values[offset:offset+n]]
        rows.append(responses)
        offset += n
    return rows


def evaluate(lm, name, task, items, directory, check, stop):
    lengths = [sum(len((a+b).encode()) for a,b in row["arguments"]) for row in items]
    indices = sorted({i*(len(items)-1)//15 for i in range(16)}|{max(range(len(items)),key=lengths.__getitem__)})
    tick = time.monotonic()
    pilot = dict(zip(indices,score(lm,name,[items[i] for i in indices]),strict=True))
    dt = time.monotonic()-tick
    forecast = 1.5*dt*max(len(items)/len(indices),sum(lengths)/sum(lengths[i] for i in indices))+90
    cost = dict(indices=indices,seconds=dt,forecast_seconds=forecast,remaining_seconds=stop-time.time())
    if forecast>cost["remaining_seconds"]:
        return dict(status="COST_HOLD",cost=cost,rows=0)
    writer = ShardWriter(directory,name)
    rows = []
    complete = False
    tick = time.monotonic()
    try:
        for begin in range(0,len(items),8):
            check()
            indices = list(range(begin,min(begin+8,len(items))))
            need = [i for i in indices if i not in pilot]
            current = dict(zip(need,score(lm,name,[items[i] for i in need]),strict=True)) if need else {}
            for index in indices:
                item = items[index]
                responses = pilot[index] if index in pilot else current[index]
                pred, norm, metrics = mc.item_score(task,item,responses)
                record = dict(**item,pred=pred,pred_norm=norm,metrics=metrics,responses=responses)
                rows.append(record)
                writer.append(record)
            if len(rows)%256==0:
                print("EXACT_KOBEST_PROGRESS",directory.name,name,len(rows),len(items),flush=True)
        result = mc.aggregate(task,rows)
        complete = True
    finally:
        if rows:
            manifest = writer.close(lineage=dict(tag=TAG,task=name,model=directory.name,complete=complete,evaluation_only=True))
        else:
            writer._finish()
    verify_shards(directory,manifest)
    return dict(status="COMPLETE",rows=len(rows),seconds=time.monotonic()-tick,cost=cost,manifest=manifest,**result)


def actual():
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from scripts.interactive_research_infer import require_idle_gpu

    assert time.time()+MAX_SECONDS+90<CUTOFF
    profile,qp = verify()
    tasks, items, meta = inputs()
    assert canonical(meta)==canonical(profile["tasks"])
    stage = OUT/"actual"
    stage.mkdir(exist_ok=False)
    reports = {}
    torch.set_num_threads(4)
    torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    for name,cap in MODELS.items():
        directory = stage/name
        directory.mkdir(exist_ok=False)
        stop = min(time.time()+cap,CUTOFF-45)
        def check():
            if time.time()+18>=stop or (OUT/"STOP").exists():
                raise TimeoutError("approved time or owned STOP")
        start = time.monotonic()
        report = dict(model=name,tasks={},training_steps=0,checkpoint_writes=0)
        lm = None
        try:
            check()
            report["gpu_entry"] = require_idle_gpu()
            out = subprocess.check_output(["nvidia-smi","--query-gpu=memory.free","--format=csv,noheader,nounits"],
                text=True,timeout=10)
            report["gpu_entry"]["free_MiB"] = int(out.strip())
            minimum = 12288 if name=="qwen3508" else 8192
            if report["gpu_entry"]["free_MiB"] < minimum:
                raise MemoryError("less free VRAM than the declared model budget")
            torch.cuda.reset_peak_memory_stats()
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH),runtime(name,torch,profile,qp,directory,check,report) as lm:
                for task_name,task in tasks.items():
                    check()
                    state = evaluate(lm,task_name,task,items[task_name],directory,check,stop)
                    report["tasks"][task_name] = state
                    print("EXACT_KOBEST_TASK",name,task_name,state["status"],state.get("metrics"),flush=True)
            report["status"] = "COMPLETE" if all(r["status"]=="COMPLETE" for r in report["tasks"].values()) else "TASK_HOLD"
            if report["status"]=="COMPLETE":
                report["equal_task_macro_F1"] = math.fsum(t["metrics"]["f1"] for t in report["tasks"].values())/5
        except Exception as error:
            report.update(status="ERROR",error=dict(type=type(error).__name__,message=str(error)[:1400]))
        finally:
            initialized = torch.cuda.is_initialized()
            report["peak_alloc_MiB"] = torch.cuda.max_memory_allocated()/1024**2 if initialized else 0
            report["peak_reserved_MiB"] = torch.cuda.max_memory_reserved()/1024**2 if initialized else 0
            lm = None
            gc.collect()
            if initialized:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            report["cuda_final_allocated"] = torch.cuda.memory_allocated() if initialized else 0
            report["cuda_final_reserved"] = torch.cuda.memory_reserved() if initialized else 0
            report["wall_seconds"] = time.monotonic()-start
            if report["cuda_final_allocated"] or report["cuda_final_reserved"]:
                report["status"]="RESOURCE_HOLD"
            mc.prism.write(directory/"report.json",report)
            reports[name] = report["status"]
        if report["status"]=="RESOURCE_HOLD":
            break
    verify()
    complete = set(reports)==set(MODELS) and all(r=="COMPLETE" for r in reports.values())
    mc.prism.write(stage/"report.json",dict(tag=TAG,models=reports,complete=complete,PID=os.getpid(),
        original_inputs_unchanged=True,ended_UTC=datetime.now(timezone.utc).isoformat()))
    print("EXACT_KOBEST_TERMINAL",reports,flush=True)
    return 0 if complete else 8


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("prepare","check","actual"))
    stage = parser.parse_args().stage
    if stage=="prepare":
        prepare()
    elif stage=="check":
        profile,_=verify()
        print("EXACT_KOBEST_CHECK",native.digest(PROFILE),len(profile["tasks"]["proof"]),flush=True)
    else:
        raise SystemExit(actual())
