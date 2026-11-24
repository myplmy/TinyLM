"""Evaluate the missing Bonsai Core6 with a causally checked native output path."""

import argparse
import ctypes as C
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sysconfig
import time
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from scripts import diag_p106b_bonsai_native_mc as mc
from scripts import diag_p106b_official_core6 as core
from scripts import p106b_official_tasks as official
from scripts.p106b_official_lm_adapter import canonical, plan_tokens, prepare_harness
from scripts.p106b_prism_likelihood import PrismLikelihood
from scripts.p106b_prism_selected_logits import SelectedLogits, batches
from scripts.p106b_shards import ShardWriter, verify as verify_shards


ROOT = mc.ROOT
PRISM = mc.prism
TAG = "p106b_bonsai_native_core6_v1_20261118"
OUT = ROOT/"test_result/evidence"/TAG
PROFILE = OUT/"profile.json"
CUTOFF = mc.lambada.CUTOFF
MAX_SECONDS = 4800
TOTAL_LIMIT = 256_000_000
SOURCES = ("scripts/diag_p106b_bonsai_native_core6.py", "scripts/p106b_prism_selected_logits.py",
    "scripts/p106b_official_tasks.py", "scripts/p106b_prism_likelihood.py", "scripts/diag_p106b_bonsai_native_mc.py",
    "scripts/diag_p106b_official_core6.py")
PRIMARY = {name:"acc_norm" if name in ("arc_easy","arc_challenge","hellaswag") else "acc" for name in core.TASK_COUNTS}


def inputs():
    os.environ.update(core.OFFLINE,HF_EVALUATE_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
    with patch.object(official,"CACHE",OUT/"task_cache"):
        tasks, specs, proof = official.load_tasks()
    assert {name:len(task.eval_docs) for name,task in tasks.items()}==core.TASK_COUNTS
    items, prepared = mc.prepare_items(tasks)
    assert sum(len(item["arguments"]) for rows in items.values() for item in rows)==67_106
    return tasks, items, dict(specs=specs,framework=proof,items=prepared)


def source_pins():
    return {name:PRISM.digest(ROOT/name) for name in SOURCES}


def check_output_route():
    class Api:
        def __init__(self):
            self.tokens = []
            self.outputs = {}

        def llama_get_memory(self,_):
            return 1

        def llama_memory_clear(self,_memory,_data):
            self.tokens.clear()

        def llama_synchronize(self,_context):
            pass

        def llama_batch_get_one(self,tokens,count):
            return SimpleNamespace(tokens=tokens,count=count,logits=None)

        def llama_decode(self,_context,batch):
            self.outputs.clear()
            for i in range(batch.count):
                self.tokens.append(int(batch.tokens[i]))
                if batch.logits[i]:
                    logits = (C.c_float*7)(*[-5.]*7)
                    logits[(sum(self.tokens)+len(self.tokens))%7] = 3.
                    self.outputs[i] = logits
            return 0

        def llama_get_logits_ith(self,_context,index):
            return self.outputs[index]

    api = Api()
    actual = SelectedLogits(SimpleNamespace(api=api,context=1,batch_limit=4,context_limit=16,vocab_size=7,
        check=lambda:None,clears=0))
    ctx, response = [2,1,3,3], [6,6,6,6]
    plan = plan_tokens(ctx,response,7,16)
    read = actual.score_plan(plan)
    expected = [(sum(plan.input_ids[:i+1])+i+1)%7 for i in range(plan.target_start,len(plan.input_ids))]
    assert read["greedy_ids"]==expected and read["response"][1]==(expected==response)
    matching = SimpleNamespace(input_ids=(3,),continuation_ids=(4,),target_start=0)
    assert actual.score_plan(matching)["response"][1] and actual.native.clears==2 and actual.decode_calls==3


def prep():
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==""
    check_output_route()
    mc.prior_proof()
    OUT.mkdir(exist_ok=False)
    _, _, exact = inputs()
    for length,indices in ((19,[0,2,18]), (913,list(range(488,667))), (1024,[0,511,512,997,1023])):
        parts = list(batches(length,indices,512))
        assert [i for _,_,positions in parts for i in positions]==indices
        assert sum(stop-start for start,stop,_ in parts)==length
        assert all(len(positions)<=64 for _,_,positions in parts)
    PRISM.write(PROFILE,dict(schema="P106B_BONSAI_CORE6_PROFILE_V1",tag=TAG,source_pins=source_pins(),
        fixed_raw_profile_sha=PRISM.digest(PRISM.PROFILE),tasks=exact,primary=PRIMARY,max_seconds=MAX_SECONDS,
        output_limit=TOTAL_LIMIT,model_loads=0, cuda_calls=0,cpu_requested_row_and_reset_check=True))
    print("BONSAI_CORE6_PREPARED",PRISM.digest(PROFILE),core.TASK_COUNTS,flush=True)


def verify():
    profile = PRISM.read(PROFILE)
    assert profile["source_pins"]==source_pins() and profile["fixed_raw_profile_sha"]==PRISM.digest(PRISM.PROFILE)
    assert profile["primary"]==PRIMARY and profile["max_seconds"]==MAX_SECONDS and profile["output_limit"]==TOTAL_LIMIT
    _, native = mc.prior_proof()
    return profile,native


def verify_match(reference, bulk, name, plans):
    serial = reference.score(plans)
    observed = bulk.score(plans)
    outcome = []
    for index, (left,right) in enumerate(zip(serial,observed,strict=True)):
        a = np.asarray(left["position_logprob"])
        b = np.asarray(right["position_logprob"])
        same_argmax = left["greedy_ids"]==right["greedy_ids"]
        close = bool(np.all(np.abs(a-b)<=np.maximum(core.ATOL,core.RTOL*np.maximum(abs(a),abs(b)))))
        outcome.append(dict(case=name,candidate=index,max_abs_logprob=float(max(abs(a-b))),
            positions=len(a),greedy_equal=same_argmax,pass_oracle=close and same_argmax))
    return outcome


def canary(reference, bulk):
    seed = reference.tok_encode(" causal token sequence 4 9 12 34.")
    chorus = (seed*128)[:1024]
    assert len(chorus)>=670
    def plan(prefix,targets):
        return plan_tokens(chorus[:prefix], targets,reference.vocab,1024)
    multicases = [
        reference.plan("Question: one plus one?\nAnswer:"," two more"),
        reference.plan("질문: 둘 더하기 둘은?\n답:"," 네 개입니다."),
        plan(509,chorus[509:521]),
        plan(498,chorus[498:570]),
        plan(660,chorus[660:667]),
    ]
    match = verify_match(reference,bulk,"fixed_multitoken_and_batch_boundary",multicases)
    changed = list(chorus[509:521])
    changed[-2] = (changed[-2]+17)%reference.vocab
    proof_a,proof_b = bulk.score([multicases[2],plan(509,changed)])
    common = len(changed)-2
    causality = (proof_a["greedy_ids"][:common] == proof_b["greedy_ids"][:common]
        and np.allclose(proof_a["position_logprob"][:common],proof_b["position_logprob"][:common],atol=core.ATOL,rtol=core.RTOL))
    return dict(pair_oracles=match,future_invariance=bool(causality),
        eligible=bool(causality) and all(row["pass_oracle"] for row in match))


def evaluate(reference, bulk, name, task, items, check, remaining, directory, total):
    plans, _, examples, rejected = mc.token_jobs(reference,items,check)
    if rejected:
        return dict(status="TOKEN_BOUNDARY_HOLD",rows=0,rejected=rejected,examples=examples)
    work = [sum(len(plan.input_ids)+len(plan.continuation_ids)*24 for plan in item) for item in plans]
    largest = max(range(len(items)),key=work.__getitem__)
    close = verify_match(reference,bulk,name,plans[largest]) if bulk else []
    use_bulk = bulk is not None and all(x["pass_oracle"] for x in close)
    selected = bulk if use_bulk else reference
    indices = sorted({i*(len(items)-1)//31 for i in range(32)}|{largest})
    tick = time.monotonic()
    pilot = {i:selected.score(plans[i]) for i in indices}
    elapsed = time.monotonic()-tick
    forecast = 1.5*elapsed*max(len(items)/len(indices),sum(work)/sum(work[i] for i in indices))+120
    cost = dict(sample_indices=indices,seconds=elapsed,forecast_seconds=forecast,remaining_seconds=remaining())
    print("BONSAI_CORE6_COST",name,cost,flush=True)
    route = "SELECTED_NATIVE_POSITIONS" if use_bulk else "QUALIFIED_LAST_LOGIT_PREFIXES"
    if forecast > cost["remaining_seconds"]:
        return dict(status="COST_HOLD",route=route,rows=0,cost=cost,match=close)
    writer = ShardWriter(directory,name,limit=19_999_999)
    rows = []
    complete = False
    tick = time.monotonic()
    try:
        for i,(item,candidates) in enumerate(zip(items,plans,strict=True)):
            check()
            score = pilot[i] if i in pilot else selected.score(candidates)
            responses = [v["response"] for v in score]
            pred,norm,metrics = mc.item_score(task,item,responses)
            row = dict(**item,pred=pred,pred_norm=norm,metrics=metrics,responses=responses,
                token_proof=[dict(**mc.lambada.task_plan(p),position_logprob=v["position_logprob"],
                    continuation=list(p.continuation_ids),greedy=v["greedy_ids"]) for p,v in zip(candidates,score,strict=True)])
            n = len(canonical(row))+1
            if n+total[0]>TOTAL_LIMIT:
                raise mc.lambada.Hold("sealed raw output limit")
            writer.append(row)
            total[0]+=n
            rows.append(row)
            if len(rows)%250==0:
                print("BONSAI_CORE6_PROGRESS",name,len(rows),len(items),flush=True)
        result = mc.aggregate(task,rows)
        complete=True
    finally:
        if rows:
            manifest = writer.close(lineage=dict(tag=TAG,task=name,complete=complete,evaluation_only=True,route=route))
        else:
            writer._finish()
    verify_shards(directory,manifest)
    return dict(status="COMPLETE",route=route,rows=len(rows),cost=cost,match=close,manifest=manifest,
        seconds=time.monotonic()-tick,context_truncated_candidates=sum(p.truncated_context_tokens>0 for i in plans for p in i),**result)


def actual():
    import signal
    from scripts.interactive_research_infer import require_idle_gpu

    assert time.time()+MAX_SECONDS+90<CUTOFF
    profile, native = verify()
    assert os.environ.get("LD_LIBRARY_PATH")==native["bundle"]
    assert not any(key.startswith(("LLAMA_ARG_","GGML_")) for key in os.environ)
    stage = OUT/"actual"
    stage.mkdir(exist_ok=False)
    report = dict(tag=TAG,PID=os.getpid(),profile_sha256=PRISM.digest(PROFILE),tasks={},training_steps=0,checkpoint_writes=0)
    started = time.monotonic()
    def remaining():
        return min(MAX_SECONDS-(time.monotonic()-started),CUTOFF-time.time()-45)
    def check():
        if remaining()<=0 or (OUT/"STOP").exists():
            raise mc.lambada.Hold("declared budget or owned STOP")
    def interrupt(_sig,_frame):
        raise mc.lambada.Hold("owned interrupt")
    handler = signal.signal(signal.SIGINT,interrupt)
    try:
        report["gpu_entry"] = require_idle_gpu()
        free = subprocess.check_output(["nvidia-smi","--query-gpu=memory.free","--format=csv,noheader,nounits"],text=True,timeout=10)
        report["gpu_entry"]["free_MiB"] = int(free.strip())
        if report["gpu_entry"]["free_MiB"]<8192:
            raise mc.lambada.Hold("minimum free GPU policy")
        tasks, items, meta = inputs()
        assert canonical(meta)==canonical(profile["tasks"])
        template,_ = prepare_harness(runtime_root=Path(sysconfig.get_paths()["purelib"]))
        total = [0]
        with PRISM.native.NativeModel(native["bundle"],ROOT/native["model"],check=check) as model:
            witness = np.load(PRISM.OUT/"actual/A0_logits_fp32.npy",allow_pickle=False)
            exact = model.logits(native["prompts"]["A"]["native_ids"])
            assert np.array_equal(witness.view(np.uint32),exact.view(np.uint32)) and model.piece(mc.lambada.EOT)==b"<|im_end|>"
            reference = PrismLikelihood(model,template,mc.lambada.EOT,check=check)
            bulk = SelectedLogits(model)
            report["bulk_oracle"] = canary(reference,bulk)
            if not report["bulk_oracle"]["eligible"]:
                bulk = None
            order = sorted(tasks,key=lambda name:(name=="hellaswag",name))
            for name in order:
                state = evaluate(reference,bulk,name,tasks[name],items[name],check,remaining,stage,total)
                report["tasks"][name] = state
                print("BONSAI_CORE6_TASK",name,state["status"],state.get("metrics"),flush=True)
        assert not model.context and not model.model and not model.backend
        report["handles_closed"] = True
        complete = set(report["tasks"])==set(PRIMARY) and all(x["status"]=="COMPLETE" for x in report["tasks"].values())
        report.update(status="COMPLETE" if complete else "PARTIAL_HOLD",exit=0 if complete else 8,raw_bytes=total[0])
        if complete:
            report["equal_task_primary_mean"] = sum(report["tasks"][n]["metrics"][key] for n,key in PRIMARY.items())/len(PRIMARY)
    except Exception as error:
        report.update(status="HOLD" if isinstance(error,mc.lambada.Hold) else "ERROR",
            exit=8 if isinstance(error,mc.lambada.Hold) else 1,error=dict(type=type(error).__name__,message=str(error)[:1400]))
    finally:
        signal.signal(signal.SIGINT,handler)
        report["wall_seconds"] = time.monotonic()-started
        verify()
        report["sources_unchanged"] = True
        PRISM.write(stage/"report.json",report)
    print("BONSAI_CORE6_TERMINAL",report["status"],report["exit"],flush=True)
    return report["exit"]


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("prepare","check","actual"))
    stage = parser.parse_args().stage
    if stage=="prepare":
        prep()
    elif stage=="check":
        print("BONSAI_CORE6_CHECK",len(verify()[0]["primary"]),PRISM.digest(PROFILE),flush=True)
    else:
        raise SystemExit(actual())
