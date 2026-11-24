"""Fresh CPU4 ABBA processes; only the admitted direct vocabulary table varies."""
import argparse
from contextlib import nullcontext
from datetime import datetime,timezone
import gc
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import threading
import time
import traceback
import unittest
import weakref
import numpy as np
import torch
from tokenizers import Tokenizer
from scripts import diag_p014e_direct_cpu as cpu
from scripts import p014e_direct_head_adapter as adapter
from scripts import diag_p106b_resource_matrix as common
from scripts import diag_p014e_large_vocab_deploy as large
from scripts import interactive_research_infer as identity

owner=cpu.owner
io=owner.io
BASE=owner.BASE/"cpu_native_v1"
PROFILE=BASE/"profile.json"
ORDER=("REFERENCE","CPU_DIRECT_TABLE","CPU_DIRECT_TABLE","REFERENCE")
REPORTS=("test_result/evidence/p014e_native595_g128_v1_20261027/baseline-cpu.json",
         "test_result/evidence/p014e_g270_large_vocab_v2_20261027_safe_loader_v1/deploy-cpu/report.json")
CODE=("scripts/diag_p014e_cpu_native.py","scripts/p014e_direct_cpu.py","scripts/p014e_direct_head_adapter.py",
      "scripts/test_p014e_direct_head_adapter.py","scripts/p014e_packed_g128.py","scripts/diag_p106b_resource_matrix.py",
      "scripts/diag_p014e_large_vocab_deploy.py","tinylm/model/transformer.py","tinylm/model/modules.py",
      "tinylm/model/ternary.py","tinylm/config.py","tinylm/infer/generate.py","tinylm/infer/dialogue.py")


def old_oracle(work):
    value=torch.load(io.ROOT/work["oracle"]["path"],map_location="cpu",weights_only=True)
    if "work_index" in work["oracle"]:return value["ternary5_existing_twn"][work["oracle"]["work_index"]]
    return dict(id=value["input"]["id"],ids=value["input"]["ids"],teacher_ids=value["teacher_ids"],logits=value["logits"])


def folder(ordinal,p):
    spec=p["models"][ordinal//4];arm=p["order"][ordinal%4]
    return BASE/"actual"/("child"+str(ordinal).zfill(2)+"_"+spec["id"]+"_"+arm)


def prepare():
    owner.Budget(7200).check(admission=True);old=cpu.verify()
    if BASE.exists():raise FileExistsError("preserve fresh CPU4 native namespace")
    checked=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName("scripts.test_p014e_direct_head_adapter"))
    if not checked.wasSuccessful() or checked.testsRun!=4:raise RuntimeError("four reused CPU head/alias/restoration contracts required")
    numeric_path=cpu.BASE/"actual/report.json";numeric=io.read(numeric_path)
    tables=[r for r in numeric["rows"] if r["kind"]=="table"]
    if len(tables)!=6 or any(not r["original_gate"] for r in tables):raise ValueError("six real CPU table operations required")
    refs={cpu.PROFILE,numeric_path};models=[]
    for index,(payload_name,report_name) in enumerate(zip(owner.INPUTS,REPORTS)):
        payload=owner.load(io.ROOT/payload_name);path=io.ROOT/report_name;closed=io.read(path)
        result=next(v["result"] for v in closed["variants"] if v["variant"]=="ternary5_existing_twn")
        if closed["exit_code"]!=0 or result["status"]!="FULL_TECHNICAL_SUITE_NOT_QUALITY":raise ValueError("closed historical CPU reference required")
        tokenizer=payload["provenance"]["tokenizer"]
        if io.sha(io.ROOT/tokenizer["path"])!=tokenizer["sha256"]:raise ValueError("explicit historical tokenizer changed")
        refs.update((path,io.ROOT/payload_name,io.ROOT/tokenizer["path"]));works=[]
        for wi,row in enumerate(result["records"]):
            name=row["workload"]
            pin=dict(path="runs/deploy/p014e_native595_g128_v1_20261027/baseline_cpu_oracle.pt",work_index=wi) if index==0 else dict(
                path="runs/deploy/p014e_g270_large_vocab_v2_20261027/oracle/cpu/ternary5_existing_twn/"+name+".pt")
            pin["sha256"]=io.sha(io.ROOT/pin["path"]);refs.add(io.ROOT/pin["path"])
            work=dict(id=name,oracle=pin);saved=old_oracle(work)
            if saved["id"]!=name or saved["ids"]!=row["observed"]["prompt_ids"] or len(saved["logits"])!=4:
                raise ValueError("same historical CPU prompt/prefix required")
            work.update(ids=saved["ids"],teacher_ids=saved["teacher_ids"],old_generated_ids=row["observed"]["generated_ids"],old_metadata=row["observed"]["metadata"]);works.append(work)
        answers=[dict(case=a["case"],ids=a["generation"]["prompt_ids"],old_answer=a["generation"]["answer"],
                      old_generated_ids=a["generation"]["generated_ids"],old_metadata=a["generation"]["metadata"]) for a in result["answers"]]
        if len(works)!=4 or len(answers)!=4 or [len(w["ids"]) for w in works]!=[128,128,512,512]:
            raise ValueError("four complete native workloads/questions required")
        models.append(dict(id="native32k" if index==0 else "student_g270_vocab",payload=payload_name,payload_sha256=io.sha(io.ROOT/payload_name),
            tokenizer=tokenizer,expected_vocab=payload["cfg"]["vocab_size"],eos_id=2 if index==0 else 1,
            historical_CPU_threads=closed.get("cpu_threads","NOT_RECORDED"),workloads=works,natural_questions=answers))
        payload=None
    BASE.mkdir()
    with (BASE/"initial_plan.md").open("xb") as stream:stream.write(owner.PLAN.read_bytes())
    io.write_new(PROFILE,dict(schema="P014E_FRESH_CPU4_DIRECT_TABLE_NATIVE_V1",authority_directive=142,
        authority_end=owner.clock.AUTHORITY_END.isoformat(),cleanup_seconds=owner.clock.CLEANUP_SECONDS,
        parent_cap_seconds=7200,child_cap_seconds=1800,initial_plan_sha256=io.sha(BASE/"initial_plan.md"),
        sources={n:io.sha(io.ROOT/n) for n in CODE},references={str(path.relative_to(io.ROOT)):io.sha(path) for path in sorted(refs)},
        models=models,library=old["library"],workers=4,torch_threads=4,torch_version=torch.__version__,order=list(ORDER),
        CPU_head_contracts=checked.testsRun,earlier_C_ABI_contracts=old["ABI_contracts"],linear_rtol=.00002,linear_atol=.000002,
        primary_numerical_reference="FIRST_FRESH_CPU4_REFERENCE;SAME_CPU4_BOTH_ARMS",
        anchor_ordinals=[0,4],historical_CPU_oracle="DIAGNOSTIC_ONLY;THREAD_SETTING_DIFFERS_OR_UNRECORDED",
        warmup_requests_per_workload=1,measured_requests_per_workload=3,fixed_max_new=16,natural_max_new=32,
        forecast="3*(24*max_prefill_seconds+376*max_decode_seconds)+60",
        expected_max_forwards_per_child=404,expected_models=8,CUDA_must_remain_uninitialized=True,
        original_checkpoint_reads=0,optimizer_updates=0,checkpoint_writes=0,quality_adoption=False))
    if torch.cuda.is_initialized():raise RuntimeError("CPU native preparation initialized CUDA")
    print("[CPU_NATIVE_PREPARED]fresh CPU4 reference anchors;four process ABBA per model;no CUDA",flush=True)


def verify():
    cpu.verify();p=io.read(PROFILE)
    if(p["authority_directive"]!=142 or p["authority_end"]!=owner.clock.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=owner.clock.CLEANUP_SECONDS or p["initial_plan_sha256"]!=io.sha(BASE/"initial_plan.md")):
        raise ValueError("exact CPU native authority/clock/initial plan required")
    for n,d in {**p["sources"],**p["references"]}.items():
        if io.sha(io.ROOT/n)!=d:raise ValueError("CPU native frozen input/source changed: "+n)
    if torch.__version__!=p["torch_version"]:raise ValueError("same installed torch version required")
    return p


def make_generation(model,cfg,tok,spec,ids,count,natural,chatml,budget):
    budget.check()
    if spec["eos_id"]==2:
        result=common.unobserved_generation(model,cfg,tok,ids,"cpu",count,natural=natural,chatml=chatml)
        result["answer"]=tok.decode(result["generated_ids"],skip_special_tokens=False)
    else:result=large.generation(model,cfg,tok,ids,"cpu",count,budget,natural=natural,observed=False)
    result["forward_calls"]=result["metadata"]["generated_tokens"]
    return result


def cost_probe(model,work,budget):
    budget.check();forward=common.FP32Forward(model,"cpu");token=torch.tensor([work["ids"]])
    start=time.perf_counter();logits,kv=forward(token,use_cache=True,logits_last_only=True);prefill=time.perf_counter()-start
    selected=int(logits.argmax(-1).item());start=time.perf_counter()
    value,more=forward(torch.tensor([[selected]]),past_kv=kv,use_cache=True,logits_last_only=True)
    decode=time.perf_counter()-start;token=logits=kv=value=more=forward=None
    return dict(workload=work["id"],prefill_seconds=prefill,decode_seconds=decode,forward_calls=2)


def anchor_for(ordinal,p):
    index=ordinal//4;anchor_ordinal=p["anchor_ordinals"][index]
    if ordinal==anchor_ordinal:return None
    path=BASE/"actual"/("anchor_model"+str(index)+".json");receipt=io.read(path)
    result_path=io.ROOT/receipt["report"]["path"]
    if(receipt["profile_sha256"]!=io.sha(PROFILE) or io.sha(result_path)!=receipt["report"]["sha256"]):
        raise ValueError("first predeclared CPU4 reference receipt changed")
    result=io.read(result_path)
    if result["ordinal"]!=anchor_ordinal or result["arm"]!="REFERENCE" or result["status"]!="CPU_NATIVE_CHILD_COMPLETE":
        raise ValueError("only the declared completed fresh reference is an anchor")
    return result


def numeric(model,work,out,anchor,p,budget):
    saved=old_oracle(work);forward=common.FP32Forward(model,"cpu");values=[];rows=[]
    expected=None if anchor is None else next(x for x in anchor["numeric"] if x["workload"]==work["id"])
    if expected is not None and io.sha(io.ROOT/expected["packet"]["path"])!=expected["packet"]["sha256"]:
        raise ValueError("fresh CPU4 anchor vector changed")
    target=None if expected is None else io.load_arrays(io.ROOT/expected["packet"]["path"])["actual"]
    logits,kv=forward(torch.tensor([work["ids"]]),use_cache=True,logits_last_only=True)
    for i in range(4):
        budget.check();actual=logits.detach().numpy().copy();old=saved["logits"][i].numpy()
        wanted=actual if target is None else target[i]
        rows.append(dict(step=i,primary_allclose=bool(np.allclose(actual,wanted,rtol=p["linear_rtol"],atol=p["linear_atol"])),
            primary_argmax_equal=bool(np.array_equal(actual.argmax(-1),wanted.argmax(-1))),
            primary_bit_exact=bool(np.array_equal(actual.view(np.uint32),wanted.view(np.uint32))),
            primary_maximum_error=float(np.max(np.abs(actual.astype(np.float64)-wanted.astype(np.float64)))),
            historical_allclose=bool(np.allclose(actual,old,rtol=p["linear_rtol"],atol=p["linear_atol"])),
            historical_maximum_error=float(np.max(np.abs(actual.astype(np.float64)-old.astype(np.float64))))))
        values.append(actual)
        if i<3:logits,kv=forward(torch.tensor([[work["teacher_ids"][i]]]),past_kv=kv,use_cache=True,logits_last_only=True)
    packet=io.save_arrays(out/(work["id"]+"_logits.npz"),actual=np.stack(values));logits=kv=forward=None
    return dict(workload=work["id"],rows=rows,packet=packet,forward_calls=4,primary_is_anchor_itself=target is None)


def child(ordinal):
    p=verify()
    if type(ordinal) is not int or not 0<=ordinal<8:raise ValueError("fixed ordinal0..7 required")
    out=folder(ordinal,p);out.mkdir();budget=owner.Budget(p["child_cap_seconds"]);budget.check(admission=True)
    spec=p["models"][ordinal//4];arm=p["order"][ordinal%4];anchor=anchor_for(ordinal,p)
    started=time.monotonic();result=dict(schema=p["schema"],status="STARTED",ordinal=ordinal,arm=arm,model=spec["id"],
        profile_sha256=io.sha(PROFILE),numeric=[],records=[],answers=[],contexts=[],cost_probes=[],
        original_checkpoint_reads=0,optimizer_updates=0,checkpoint_writes=0,quality_adoption=False)
    runtime=model=payload=operator=tok=cfg=None;failure=None;exit_code=0
    def interrupted(_number,_frame):raise TimeoutError("parent requested owned CPU child closure")
    signal.signal(signal.SIGTERM,interrupted)
    try:
        torch.set_num_threads(p["torch_threads"])
        runtime=cpu.direct.KernelRuntime(io.ROOT/p["library"]["path"],p["library"]["sha256"],workers=p["workers"])
        barrier=threading.Barrier(5);warm_workers=[runtime.pool.submit(barrier.wait) for _ in range(4)]
        barrier.wait(timeout=30)
        for future in warm_workers:future.result()
        payload=owner.load(io.ROOT/spec["payload"]);model=owner.direct.reference.load_payload(payload,device="cpu",tile_rows=4096)
        ref=weakref.ref(model);cfg=model.cfg;tok=Tokenizer.from_file(str(io.ROOT/spec["tokenizer"]["path"]))
        if cfg.vocab_size!=spec["expected_vocab"] or cfg.max_seq_len!=1024:raise ValueError("same native vocabulary/context required")
        before=identity.state_fingerprint(model);result["initial_state_sha256"]=before
        operator=cpu.direct.PackedCPUOperator(payload["embedding"],runtime)
        operator.packed_codes=model.packed_embedding.packed_codes;operator.group_scales=model.packed_embedding.group_scales
        payload=None
        result.update(initial_state_sha256=before,storage=common.model_storage(model),torch_threads=torch.get_num_threads(),
                      worker_pool_started_same_in_both_arms=True,extra_weight_storage_bytes=0)
        with torch.no_grad():
            context=nullcontext(None) if arm=="REFERENCE" else adapter.direct_head(model,operator)
            with context as proof:
                probes=[cost_probe(model,spec["workloads"][i],budget) for i in (0,2)]
                prefill=max(x["prefill_seconds"] for x in probes);decode=max(x["decode_seconds"] for x in probes)
                forecast=3*(24*prefill+376*decode)+60
                remaining=min(budget.seconds-(time.monotonic()-budget.started),budget.check())
                result.update(cost_probes=probes,conservative_seconds=forecast,remaining_at_cost_seconds=remaining)
                if forecast>remaining:raise TimeoutError("complete declared CPU child does not fit measured cost")
                for work in spec["workloads"]:
                    result["numeric"].append(numeric(model,work,out,anchor,p,budget))
                    warm=make_generation(model,cfg,tok,spec,work["ids"],16,False,False,budget)
                    repeats=[make_generation(model,cfg,tok,spec,work["ids"],16,False,False,budget) for _ in range(3)]
                    expected=None if anchor is None else next(x for x in anchor["records"] if x["workload"]==work["id"])
                    target=warm if expected is None else expected["warmup"]
                    same=all(g["generated_ids"]==target["generated_ids"] and g["metadata"]==target["metadata"] for g in [warm,*repeats])
                    result["records"].append(dict(workload=work["id"],warmup=warm,repeats=repeats,
                        median_seconds=float(np.median([x["seconds"] for x in repeats])),all_anchor_IDs_and_stops_equal=same,
                        old_IDs_and_stops_equal=all(g["generated_ids"]==work["old_generated_ids"] and g["metadata"]==work["old_metadata"] for g in [warm,*repeats])))
                    print("[CPU_NATIVE_CHILD_WORKLOAD]"+str(ordinal)+"/"+work["id"],flush=True)
                for case in spec["natural_questions"]:
                    seen=make_generation(model,cfg,tok,spec,case["ids"],32,True,case["case"]["mode"]=="chatml",budget)
                    expected=None if anchor is None else next(x for x in anchor["answers"] if x["case"]==case["case"])
                    target=seen if expected is None else expected["generation"]
                    result["answers"].append(dict(case=case["case"],generation=seen,old_answer=case["old_answer"],
                        anchor_IDs_and_stops_equal=seen["generated_ids"]==target["generated_ids"] and seen["metadata"]==target["metadata"],
                        old_IDs_and_stops_equal=seen["generated_ids"]==case["old_generated_ids"] and seen["metadata"]==case["old_metadata"]))
            if proof is not None:result["contexts"].append(proof)
        failures=sum(not row["primary_allclose"] or not row["primary_argmax_equal"] for b in result["numeric"] for row in b["rows"])
        changed=sum(not r["all_anchor_IDs_and_stops_equal"] for r in result["records"])+sum(not a["anchor_IDs_and_stops_equal"] for a in result["answers"])
        result.update(numerical_gate_failures=failures,changed_generation_records=changed,
            status="CPU_NATIVE_CHILD_COMPLETE" if failures==0 and changed==0 else "CPU_NATIVE_CHILD_NUMERICAL_OR_ID_NEGATIVE")
    except TimeoutError as error:
        result.update(status="CPU_NATIVE_CHILD_HOLD",error=str(error));exit_code=8;error.__traceback__=None
    except BaseException as error:
        failure=str(error);result.update(status="CPU_NATIVE_CHILD_ERROR",error=failure,traceback=traceback.format_exc());exit_code=1;error.__traceback__=None
    finally:
        if model is not None and "initial_state_sha256" in result:
            result["physical_state_unchanged"]=identity.state_fingerprint(model)==result["initial_state_sha256"]
            if not result["physical_state_unchanged"]:failure=failure or "CPU original state changed";exit_code=1
        model=payload=operator=tok=cfg=None
        if runtime is not None:runtime.close()
        runtime=None;gc.collect();result.update(model_released=True if "ref" not in locals() else ref() is None,
            worker_threads_released=not any(t.name.startswith("p014e-cpu") for t in threading.enumerate()),
            CUDA_initialized=torch.cuda.is_initialized(),RSS_high_water_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            wall_seconds=time.monotonic()-started,exit_code=exit_code)
        if not result["model_released"] or not result["worker_threads_released"] or result["CUDA_initialized"]:
            failure=failure or "CPU child resource closure failed";result["exit_code"]=exit_code=1
        io.write_new(out/"report.json",result)
    print("[CPU_NATIVE_CHILD_END]"+json.dumps(dict(ordinal=ordinal,status=result["status"],exit_code=exit_code,error=failure)),flush=True)
    return exit_code


def actual():
    p=verify();budget=owner.Budget(p["parent_cap_seconds"]);budget.check(admission=True);out=BASE/"actual"
    if out.exists():raise FileExistsError("preserve all CPU native children")
    out.mkdir();started=time.monotonic();report=dict(schema=p["schema"],status="STARTED",children=[],profile_sha256=io.sha(PROFILE),
        parent_model_loads=0,original_checkpoint_reads=0,optimizer_updates=0,checkpoint_writes=0,quality_adoption=False)
    active=None;failure=None;exit_code=0
    try:
        for ordinal in range(8):
            budget.check()
            if budget.seconds-(time.monotonic()-budget.started)<p["child_cap_seconds"]:
                report["status"]="CPU_NATIVE_PARENT_HOLD";exit_code=8;break
            logfile=out/("child"+str(ordinal).zfill(2)+"_stdout.txt")
            argv=[sys.executable,"-B","-u","-m","scripts.diag_p014e_cpu_native","child","--ordinal",str(ordinal)]
            with logfile.open("xb") as stream:
                active=subprocess.Popen(argv,cwd=io.ROOT,stdout=stream,stderr=subprocess.STDOUT)
                print("[CPU_NATIVE_CHILD_STARTED]"+json.dumps(dict(ordinal=ordinal,pid=active.pid,arm=p["order"][ordinal%4])),flush=True)
                began=time.monotonic()
                while active.poll() is None:
                    budget.check()
                    if time.monotonic()-began>p["child_cap_seconds"]+30:
                        active.terminate()
                        try:active.wait(timeout=20)
                        except subprocess.TimeoutExpired:active.kill();active.wait()
                        break
                    time.sleep(1)
                rc=active.wait();active=None
            path=folder(ordinal,p)/"report.json";value=io.read(path) if path.exists() else None
            report["children"].append(dict(ordinal=ordinal,argv=argv,actual_exit_code=rc,stdout=dict(path=str(logfile.relative_to(io.ROOT)),sha256=io.sha(logfile)),
                report=None if value is None else dict(path=str(path.relative_to(io.ROOT)),sha256=io.sha(path)),
                status=None if value is None else value["status"]))
            print("[CPU_NATIVE_CHILD_CLOSED]"+json.dumps(report["children"][-1]),flush=True)
            if rc!=0 or value is None:
                report["status"]="CPU_NATIVE_PARENT_HOLD" if rc==8 else "CPU_NATIVE_PARENT_ERROR";exit_code=rc or 1;break
            if ordinal in p["anchor_ordinals"]:
                if value["status"]!="CPU_NATIVE_CHILD_COMPLETE":
                    report["status"]="CPU_NATIVE_REFERENCE_ERROR";exit_code=1;break
                io.write_new(out/("anchor_model"+str(ordinal//4)+".json"),dict(profile_sha256=io.sha(PROFILE),
                    report=dict(path=str(path.relative_to(io.ROOT)),sha256=io.sha(path)),selected_before_answers=True))
        else:
            report["status"]="CPU_NATIVE_ABBA_COMPLETE" if all(c["status"]=="CPU_NATIVE_CHILD_COMPLETE" for c in report["children"]) else "CPU_NATIVE_ABBA_NUMERICAL_OR_ID_NEGATIVE"
    except TimeoutError as error:
        report.update(status="CPU_NATIVE_PARENT_HOLD",error=str(error));exit_code=8;error.__traceback__=None
    except BaseException as error:
        failure=str(error);report.update(status="CPU_NATIVE_PARENT_ERROR",error=failure,traceback=traceback.format_exc());exit_code=1;error.__traceback__=None
    finally:
        if active is not None and active.poll() is None:
            active.terminate()
            try:active.wait(timeout=20)
            except subprocess.TimeoutExpired:active.kill();active.wait()
        report.update(wall_seconds=time.monotonic()-started,actual_exit_code=exit_code,CUDA_initialized=torch.cuda.is_initialized())
        io.write_new(out/"batch_report.json",report)
    print("[CPU_NATIVE_PARENT_END]"+json.dumps(dict(status=report["status"],children=len(report["children"]),exit_code=exit_code,error=failure)),flush=True)
    return exit_code


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","check","actual","child"));parser.add_argument("--ordinal",type=int);args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="check":verify();print("[CPU_NATIVE_CHECK]fresh anchors,owned ABI,old CPU inputs and clock",flush=True)
    elif args.action=="child":raise SystemExit(child(args.ordinal))
    else:raise SystemExit(actual())


if __name__=="__main__":main()
