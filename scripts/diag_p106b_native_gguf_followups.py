"""Run the remaining official tasks on the two pinned b11396 GGUFs."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import time
from unittest.mock import patch

from scripts import diag_p106b_bonsai_native_mc as mc
from scripts import p106b_native_core6 as native
from scripts import p106b_native_iq2_worker_window as supervision
from scripts.p106b_official_lm_adapter import canonical, plan_tokens, prepare_harness
from scripts.p106b_shards import ShardWriter, verify as verify_shards


ROOT = native.ROOT
TAG = "p106b_native_gguf_followups_v2_20261118"
OUT = ROOT/"test_result/evidence"/TAG
PROFILE = OUT/"profile.json"
SOURCE = ROOT/"scripts/p106b_native_llama_worker.cpp"
CPP = OUT/"build/worker_nov18.cpp"
BINARY = OUT/"build/worker_nov18"
CUTOFF = mc.lambada.CUTOFF
MODEL_CAPS = {"gpt2_q4km":6000, "qwen35_08b_iq2xxs":12000}
CAP = sum(MODEL_CAPS.values())+180
BYTE_LIMIT = 384_000_000
DEADLINE_TEXT = "deadline exceeds authorized 16:30 KST 18Nov window"
OLD_DEADLINE = str(supervision.OLD_EPOCH).encode()
NEW_DEADLINE = str(int(CUTOFF)).encode()
OLD_MESSAGE = supervision.OLD_TEXT.encode()
NEW_MESSAGE = DEADLINE_TEXT.encode()
OFFICIAL = mc.lambada.official
HISTORIC = ROOT/"test_result/evidence/p106b_native_window10800_v2_s1337/gpt2_q4km/full/report.json"
HISTORIC_SHA = "5848997902688F3CA561419A28AD71031C1FCB864AEB6397E0EEDAEAD114020A"
UPDATED = "scripts/interactive_research_infer.py"


def compatible_identity():
    current = native.identity()
    assert native.digest(HISTORIC) == HISTORIC_SHA
    original = mc.prism.read(HISTORIC)["source_identity"]["native_source_identity"]
    assert original["sha256"] == "42713A9E7A181896DAD0A10D0359BFA193264D9DAEF3445A05E970404995D2AD"
    assert original["build"] == current["build"] and original["files"].keys() == current["files"].keys()
    assert [name for name,value in current["files"].items() if original["files"][name] != value] == [UPDATED]
    raw = (ROOT/UPDATED).read_bytes()
    new_manifest = b"MANIFEST = 'handoff/audit/oct27_independent/research_infer_manifest_mntp_v1.json'"
    old_manifest = b"MANIFEST = 'handoff/audit/WIP_20261021_RESEARCH_INFER_MANIFEST.json'"
    visibility = b"    'tinylm/model/visibility.py'," + bytes((10,))
    assert raw.count(new_manifest) == raw.count(visibility) == 1
    old_raw = raw.replace(new_manifest,old_manifest).replace(visibility,b"")
    assert hashlib.sha256(old_raw).hexdigest().upper() == original["files"][UPDATED]
    return current


def derive_cpp():
    raw = SOURCE.read_bytes()
    assert raw.count(OLD_DEADLINE) == raw.count(OLD_MESSAGE) == 1
    assert raw.index(b"if(argc!=5") < raw.index(OLD_DEADLINE) < raw.index(b"Runtime runtime(argv[2],architecture)")
    assert raw.index(b"if(argv[2]!=allowed)") < raw.index(b"Runtime runtime(argv[2],architecture)")
    derived = raw.replace(OLD_DEADLINE,NEW_DEADLINE).replace(OLD_MESSAGE,NEW_MESSAGE)
    assert derived.replace(NEW_DEADLINE,OLD_DEADLINE).replace(NEW_MESSAGE,OLD_MESSAGE) == raw
    return derived


def compile_worker(frozen):
    CPP.parent.mkdir(exist_ok=False)
    with CPP.open("xb") as stream:
        stream.write(derive_cpp())
    build = frozen["build"]
    command = [build["compiler_resolved_path"], *build["compile_flags"], "-I"+str(native.HEADERS/"include"),
        "-I"+str(native.HEADERS/"ggml/include"), str(CPP), *build["link_flags"], "-o", str(BINARY)]
    subprocess.run(command, check=True, timeout=120)
    original = native.HEADERS/build["worker"]
    absent = "/__tinylm_unregistered_nov18_followup_probe__"
    probes = [
        ([str(original),"--self-test"],0,"CPU_ONLY; backend_init=0; model_loads=0"),
        ([str(BINARY),"--self-test"],0,"CPU_ONLY; backend_init=0; model_loads=0"),
        ([str(original),"--execute",absent,"gpt2",str(int(CUTOFF)-1)],9,supervision.OLD_TEXT),
        ([str(BINARY),"--execute",absent,"gpt2",str(int(CUTOFF)+1)],9,DEADLINE_TEXT),
        ([str(BINARY),"--execute",absent,"qwen35",str(int(CUTOFF)-1)],9,"unregistered model path; no backend initialized"),
    ]
    receipts = []
    env = dict(os.environ, LD_LIBRARY_PATH=str(native.ENGINE))
    for argv, exit_code, message in probes:
        proc = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=20)
        assert proc.returncode == exit_code and message in proc.stdout+proc.stderr
        receipts.append(dict(argv=argv, exit=exit_code, message=message))
    assert native.identity() == frozen
    return dict(worker=str(BINARY), worker_sha256=native.digest(BINARY), cpp_sha256=native.digest(CPP),
        deadline_epoch=int(CUTOFF), probes=receipts, compiler_command=command, changed_date_literals_only=True)


def inputs():
    tasks, pins, definition = mc.load_tasks()
    items, proof = mc.prepare_items(tasks)
    asset = OFFICIAL.asset_proof()
    with patch.object(OFFICIAL,"CACHE",OUT/"lambada_task_cache"):
        task, task_definition = OFFICIAL.load_task()
    tasks[OFFICIAL.TASK] = task
    sha = hashlib.sha256()
    items[OFFICIAL.TASK] = []
    for i, doc in enumerate(task.eval_docs):
        request = OFFICIAL.request_for(task,doc,i)
        args = list(request.args)
        sha.update(canonical(args)+bytes((10,)))
        items[OFFICIAL.TASK].append(dict(doc_id=i,doc=doc,arguments=[args]))
    data = asset["local_relative_path"]
    pins[data] = asset["local_sha256"]
    proof[OFFICIAL.TASK] = dict(rows=len(items[OFFICIAL.TASK]), ordered_request_sha256=sha.hexdigest().upper())
    assert len(items[OFFICIAL.TASK]) == 5153
    assert proof[OFFICIAL.TASK]["ordered_request_sha256"] == mc.lambada.prism.read(mc.lambada.PROFILE)["official_request_sha256"]
    metadata = dict(mc=definition,lambada=task_definition,assets=pins,proof=proof)
    return tasks, items, metadata


def sources():
    return dict(**mc.source_pins(), **{"scripts/diag_p106b_native_gguf_followups.py":native.digest(Path(__file__))})


def prepare():
    assert os.environ.get("CUDA_VISIBLE_DEVICES")=="" and time.time()+CAP+90<CUTOFF
    frozen = compatible_identity()
    assets = {model:native.asset_identity(model) for model in MODEL_CAPS}
    OUT.mkdir(exist_ok=False)
    derived = compile_worker(frozen)
    _, _, task_metadata = inputs()
    mc.prism.write(PROFILE,dict(schema="P106B_GGUF_FOLLOWUP_PROFILE_V1",tag=TAG, native_sha256=frozen["sha256"],
        source_pins=sources(), derived=derived, assets=assets, tasks=task_metadata,
        model_caps=MODEL_CAPS, parent_cap=CAP, output_cap_per_model=BYTE_LIMIT, model_loads=0))
    print("GGUF_FOLLOWUPS_PREPARED",native.digest(PROFILE),{k:v["rows"] for k,v in task_metadata["proof"].items()},flush=True)


def verify():
    profile = mc.prism.read(PROFILE)
    frozen = compatible_identity()
    build = profile["derived"]
    assert profile["native_sha256"]==frozen["sha256"] and profile["source_pins"]==sources()
    assert profile["model_caps"]==MODEL_CAPS and profile["parent_cap"]==CAP and profile["output_cap_per_model"]==BYTE_LIMIT
    assert build["changed_date_literals_only"] and len(build["probes"])==5 and build["deadline_epoch"]==int(CUTOFF)
    assert build["worker"]==str(BINARY) and not BINARY.is_symlink() and native.digest(BINARY)==build["worker_sha256"]
    assert CPP.read_bytes()==derive_cpp() and native.digest(CPP)==build["cpp_sha256"]
    assert all(native.digest(ROOT/name)==digest for name,digest in profile["tasks"]["assets"].items())
    assert all(native.asset_identity(model)==profile["assets"][model] for model in MODEL_CAPS)
    return profile, dict(frozen["build"], worker=str(BINARY), worker_sha256=build["worker_sha256"])


class BoundedWriter:
    def __init__(self, path, name, counts):
        self.writer = ShardWriter(path,name,limit=19_999_999)
        self.counts = counts
        self.rows = 0

    def append(self,row):
        size = len(canonical(row))+1
        if self.counts[0] + size > BYTE_LIMIT:
            raise native.AdmissionHold("combined sample and wire byte limit")
        self.writer.append(row)
        self.counts[0] += size
        self.rows += 1

    def close(self, **lineage):
        if self.rows == 0:
            self.writer._finish()
            return None
        manifest = self.writer.close(lineage=lineage)
        verify_shards(self.writer.directory, manifest)
        return manifest


def tokenize(lm, arguments):
    context,target = arguments
    if context:
        ctx, cont = lm._encode_pair(context,target)
    else:
        cont = lm.tok_encode(target,add_special_tokens=False)
        ctx,cont = ([lm.prefix_token_id],cont) if cont[0]!=lm.prefix_token_id else (cont[:1],cont[1:])
    return plan_tokens(ctx,cont,lm.vocab_size,1024)


def evaluate_task(lm, name, task, items, directory, stop, counts):
    def check():
        if time.time()+18>=stop or (OUT/"STOP").exists():
            raise native.AdmissionHold("worker budget or owned STOP reached")

    plans = []
    for item in items:
        check()
        plans.append([tokenize(lm,args) for args in item["arguments"]])
    work = [sum(len(p.input_ids) for p in item) for item in plans]
    largest = max(range(len(items)), key=work.__getitem__)
    indices = sorted({i*(len(items)-1)//15 for i in range(16)}|{largest})
    tick = time.monotonic()
    pilot = {i:[lm.worker.score(p) for p in plans[i]] for i in indices}
    sample_wall = time.monotonic()-tick
    forecast = 1.5*sample_wall*max(len(items)/len(indices),sum(work)/sum(work[i] for i in indices))+120
    cost = dict(indices=indices, measured_seconds=sample_wall, forecast_seconds=forecast, remaining_seconds=stop-time.time(),
        planned_context_positions=sum(work))
    print("GGUF_FOLLOWUP_COST",directory.name,name,json.dumps(cost),flush=True)
    if forecast > cost["remaining_seconds"]:
        return dict(status="COST_HOLD", scored_rows=0, cost=cost)
    writer = BoundedWriter(directory,name,counts)
    rows = []
    completed = False
    tick = time.monotonic()
    try:
        for i, (item, candidate) in enumerate(zip(items,plans,strict=True)):
            check()
            values = pilot[i] if i in pilot else [lm.worker.score(p) for p in candidate]
            responses = [v[0] for v in values]
            if name==OFFICIAL.TASK:
                metrics = task.process_results(item["doc"], responses)
                assert metrics == dict(acc=int(responses[0][1]),perplexity=responses[0][0])
                row = dict(**item, response=responses[0], official_metrics=metrics)
            else:
                pred,norm,metrics = mc.item_score(task,item,responses)
                row = dict(**item,pred=pred,pred_norm=norm,metrics=metrics,responses=responses)
            row["native_tokens"] = [dict(**mc.lambada.task_plan(p), input_ids=list(p.input_ids),
                continuation_ids=list(p.continuation_ids), target_logp_greedy=meta)
                for p,(_,meta) in zip(candidate,values,strict=True)]
            writer.append(row)
            rows.append(row)
            if (i+1)%250==0:
                print("GGUF_FOLLOWUP_PROGRESS",directory.name,name,i+1,len(items),flush=True)
        result = dict(metrics=OFFICIAL.aggregate(task,rows)) if name==OFFICIAL.TASK else mc.aggregate(task,rows)
        completed = True
    finally:
        manifest = writer.close(tag=TAG,task=name,evaluation_only=True,complete=completed)
    return dict(status="COMPLETE",scored_rows=len(rows),manifest=manifest,cost=cost,
        decoding_seconds=time.monotonic()-tick,context_truncated_requests=sum(p.truncated_context_tokens>0 for item in plans for p in item),
        **result)


def run_model(model, assets, build, tasks, items):
    from scripts.interactive_research_infer import require_idle_gpu
    import torch

    directory = OUT/model
    directory.mkdir(exist_ok=False)
    started = time.monotonic()
    stop = min(CUTOFF-90,time.time()+MODEL_CAPS[model])
    counts = [0]
    raw = BoundedWriter(directory,"native_wire",counts)
    proof = {}
    report = dict(status="STARTED",model=model,assets=assets,tasks={},worker=proof,training_steps=0,checkpoint_writes=0)
    try:
        report["gpu_entry"] = require_idle_gpu()
        template,_ = prepare_harness(runtime_root=Path(sysconfig.get_paths()["purelib"]))
        with native.Worker(assets,build,stop,raw,proof) as worker:
            lm = native.adapter_type(template)(worker)
            report["numerical_canary"] = {}
            native.numerical_canary(lm,torch,report["numerical_canary"])
            for name,task in tasks.items():
                state = evaluate_task(lm,name,task,items[name],directory,stop,counts)
                report["tasks"][name] = state
                print("GGUF_FOLLOWUP_TASK",model,name,state["status"],state.get("metrics"),flush=True)
        assert proof["worker_cleanup_complete"] and proof["worker_returncode"] == 0 and not proof["telemetry_errors"]
        report["gpu_after"] = require_idle_gpu()
        report["status"] = "COMPLETE" if all(r["status"]=="COMPLETE" for r in report["tasks"].values()) else "TASK_HOLD"
    except Exception as error:
        report.update(status="HOLD" if isinstance(error,native.AdmissionHold) else "ERROR",
            error=dict(type=type(error).__name__,message=str(error)[:1200]))
    finally:
        report["wall_seconds"] = time.monotonic()-started
        report["wire_manifest"] = raw.close(tag=TAG, model=model, evaluation_only=True)
        report["output_bytes"] = counts[0]
        mc.prism.write(directory/"report.json",report)
    print("GGUF_FOLLOWUP_MODEL",model,report["status"],report["wall_seconds"],report.get("error"),flush=True)
    return report["status"]


def actual():
    assert os.environ.get(supervision.OWNER_KEY) and time.time()+CAP<CUTOFF
    profile, build = verify()
    tasks, items, metadata = inputs()
    assert canonical(metadata)==canonical(profile["tasks"])
    results = {name:run_model(name,profile["assets"][name],build,tasks,items) for name in MODEL_CAPS}
    verify()
    mc.prism.write(OUT/"actual.json",dict(tag=TAG,profile_sha256=native.digest(PROFILE),
        complete=all(status=="COMPLETE" for status in results.values()),models=results,
        ended_UTC=datetime.now(timezone.utc).isoformat(),frozen_inputs_unchanged=True))
    print("GGUF_FOLLOWUP_TERMINAL",results,flush=True)
    return 0 if all(status=="COMPLETE" for status in results.values()) else 8


def supervise():
    verify()
    assert time.time()+CAP+90<CUTOFF
    argv = [sys.executable,"-B","-u","-m","scripts.diag_p106b_native_gguf_followups","actual"]
    report = supervision.supervise_process(argv, worker_binary=BINARY, directory=OUT/"supervisor",
        deadline_epoch=CUTOFF,cap=CAP,reserve=60,verify_success=lambda:mc.prism.read(OUT/"actual.json"))
    print("GGUF_FOLLOWUP_SUPERVISOR",report["returncode"],report["controller_returncode"],report["original_error"],flush=True)
    return report["returncode"]


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","check","supervise","actual"))
    action = parser.parse_args().action
    if action=="prepare":
        prepare()
    elif action=="check":
        profile, _ = verify()
        print("GGUF_FOLLOWUP_CHECK",len(profile["tasks"]["proof"]),native.digest(PROFILE),flush=True)
    else:
        raise SystemExit(supervise() if action=="supervise" else actual())
