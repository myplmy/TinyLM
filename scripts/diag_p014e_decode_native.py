"""Head-only versus head plus explicit one-token FP64 packed body dispatch."""
import argparse
from contextlib import contextmanager,nullcontext
import gc
import json
import time
import traceback
import unittest
import weakref
import numpy as np
import torch
from tokenizers import Tokenizer
from scripts import diag_p014e_direct_native as native
from scripts import diag_p014e_direct_precision as precision
from scripts import p014e_direct_decode_adapter as adapter

owner=native.owner
io=owner.io
BASE=owner.BASE/"decode_native_v1"
PROFILE=BASE/"profile.json"
ARMS=("HEAD_ONLY","HEAD_AND_DECODE64")
CODE=("scripts/diag_p014e_decode_native.py","scripts/p014e_direct_decode_adapter.py",
      "scripts/test_p014e_direct_decode_adapter.py","scripts/p014e_direct_cuda_fp64.py",
      "scripts/diag_p014e_direct_native.py","scripts/p014e_direct_head_adapter.py")


def prepare():
    owner.Budget().check(admission=True);old=native.verify();precision.verify()
    if BASE.exists():raise FileExistsError("preserve explicit decode-only native namespace")
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in(
        "scripts.test_p014e_direct_decode_adapter","scripts.test_p014e_direct_head_adapter"))
    checked=unittest.TextTestRunner(verbosity=2).run(suite)
    if not checked.wasSuccessful() or checked.testsRun!=8:raise RuntimeError("eight combined alias/dispatch/rollback contracts required")
    numeric_path=precision.BASE/"actual/report.json";numeric=io.read(numeric_path)
    old_path=native.BASE/"actual/report.json";closed=io.read(old_path)
    if(numeric["status"]!="FP64_BODY_OPERATORS_COMPLETE" or numeric["numerical_gate_failures"]
       or closed["status"]!="DIRECT_HEAD_NATIVE_COMPLETE" or closed["changed_generation_records"]):
        raise ValueError("closed same-gate FP64 operators and successful head-only native required")
    refs={native.PROFILE,old_path,precision.PROFILE,numeric_path}
    prior_numeric={m["id"]:{b["workload"]:b["actual_packet"] for b in m["numeric"] if b["arm"]=="DIRECT"} for m in closed["models"]}
    refs.update(io.ROOT/pin["path"] for model in prior_numeric.values() for pin in model.values())
    BASE.mkdir()
    with (BASE/"initial_plan.md").open("xb") as stream:stream.write(owner.PLAN.read_bytes())
    io.write_new(PROFILE,dict(schema="P014E_NATIVE_HEAD_AND_DECODE64_V1",authority_directive=142,
        authority_end=owner.clock.AUTHORITY_END.isoformat(),cleanup_seconds=owner.clock.CLEANUP_SECONDS,max_seconds=1800,
        initial_plan_sha256=io.sha(BASE/"initial_plan.md"),sources={name:io.sha(io.ROOT/name) for name in CODE},
        references={str(path.relative_to(io.ROOT)):io.sha(path) for path in sorted(refs)},models=old["models"],
        previous_head_native_numeric=prior_numeric,CPU_contracts=checked.testsRun,arms=list(ARMS),
        linear_rtol=old["linear_rtol"],linear_atol=old["linear_atol"],timing_order=[ARMS[0],ARMS[1],ARMS[1],ARMS[0]],
        warmup_requests_per_block=1,measured_requests_per_block=3,max_fixed=16,max_natural=32,
        head_same_in_both_arms=True,body_policy="M_EQ1_FP64_DIRECT;M_GT1_ORIGINAL_ROW4096_REFERENCE;NO_ERROR_FALLBACK",
        native_probe_workloads=["ko128","ko512"],expected_added_probe_forwards=16,maximum_total_forwards=2640,
        memory_scope="CUDA_ALLOCATOR_PEAK;PREFILL_AND_ONE_DECODE_SEPARATE;NOT_DEVICE_PHYSICAL_PEAK",
        original_FP32_negative_preserved=True,optimizer_updates=0,checkpoint_writes=0,
        original_checkpoint_reads=0,quality_adoption=False))
    if torch.cuda.is_initialized():raise RuntimeError("CPU decode-only admission initialized CUDA")
    print("[DECODE_NATIVE_PREPARED]eight CPU contracts;same head;explicit one-row body only",flush=True)


def verify():
    native.verify();precision.verify();p=io.read(PROFILE)
    if(p["authority_directive"]!=142 or p["authority_end"]!=owner.clock.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=owner.clock.CLEANUP_SECONDS or p["initial_plan_sha256"]!=io.sha(BASE/"initial_plan.md")):
        raise ValueError("exact current clock and new decode-only initial plan required")
    for name,digest in {**p["sources"],**p["references"]}.items():
        if io.sha(io.ROOT/name)!=digest:raise ValueError("sealed decode-only source/input changed: "+name)
    return p


def operators(model,payload):
    table=owner.direct.DirectPackedOperator(payload["embedding"],device="cpu")
    table.packed_codes=model.packed_embedding.packed_codes;table.group_scales=model.packed_embedding.group_scales
    pairs=[]
    for row in payload["matrices"]:
        modules=[]
        for path in row["paths"]:
            parent,name=owner.direct.reference._slot(model,path);modules.append(parent._modules[name])
        if not modules or any(m is not modules[0] for m in modules):raise ValueError("source shared-owner aliases differ")
        module=modules[0];operator=precision.precise.FP64DirectBodyOperator(row["weight"],device="cpu")
        operator.packed_codes=module.packed_codes;operator.group_scales=module.group_scales
        pairs.append((module,operator))
    return table,pairs


@contextmanager
def route(model,table,pairs,arm):
    with native.adapter.direct_head(model,table) as head:
        context=nullcontext(None) if arm==ARMS[0] else adapter.one_row_body(model,pairs)
        with context as body:yield dict(arm=arm,head=head,body=body)


def probe(model,work,packet,budget):
    budget.check();forward=native.CountingForward(model);token=torch.tensor([work["ids"]],device="cuda")
    torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
    logits,kv=forward(token,use_cache=True,logits_last_only=True);torch.cuda.synchronize()
    prefill_seconds=time.perf_counter()-start;prefill_peak=torch.cuda.max_memory_allocated()
    kv_bytes=native.runtime.storage_audit(("kv",t) for t in native.runtime.nested_tensors(kv))["unique_storage_bytes"]
    torch.cuda.reset_peak_memory_stats();live_before=torch.cuda.memory_allocated();start=time.perf_counter()
    changed,newkv=forward(torch.tensor([[work["teacher_ids"][0]]],device="cuda"),past_kv=kv,use_cache=True,logits_last_only=True)
    torch.cuda.synchronize();decode_seconds=time.perf_counter()-start;decode_peak=torch.cuda.max_memory_allocated()
    saved=io.load_arrays(io.ROOT/packet["path"])["actual"][1]
    if not np.array_equal(changed.detach().cpu().numpy().view(np.uint32),saved.view(np.uint32)):
        raise RuntimeError("memory probe differed from its already-saved numeric step1")
    result=dict(workload=work["id"],prefill_seconds=prefill_seconds,one_decode_seconds=decode_seconds,
        prefill_peak_allocated_bytes=prefill_peak,one_decode_peak_allocated_bytes=decode_peak,
        live_allocated_before_decode_bytes=live_before,kv_returned_storage_bytes=kv_bytes,
        forward_calls=forward.calls,numeric_packet_step1=packet,logits_bitexact_to_existing_step1=True,
        scope="ALLOCATOR_ONLY;prefill/reset-with-KV-live/decode;both prior and returned KV coexist at return")
    token=logits=kv=changed=newkv=forward=None;return result


def actual():
    p=verify();budget=owner.Budget();budget.check(admission=True);out=BASE/"actual"
    if out.exists():raise FileExistsError("preserve decode-only native actual")
    out.mkdir();started=time.monotonic();report=dict(schema=p["schema"],status="STARTED",models=[],
        profile_sha256=io.sha(PROFILE),head_same_in_both_arms=True,body_prefill_reference=True,
        new_model_loads=0,original_checkpoint_reads=0,optimizer_updates=0,checkpoint_writes=0,quality_adoption=False)
    model=payload=table=pairs=tok=cfg=None;failure=None
    try:
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        for spec in p["models"]:
            budget.check();folder=out/spec["id"];folder.mkdir();payload=owner.load(io.ROOT/spec["payload"])
            model=owner.direct.reference.load_payload(payload,device="cuda",tile_rows=4096)
            ref=weakref.ref(model);report["new_model_loads"]+=1;cfg=model.cfg
            table,pairs=operators(model,payload);payload=None
            tok=Tokenizer.from_file(str(io.ROOT/spec["tokenizer"]["path"]))
            initial=native.identity.state_fingerprint(model);result=dict(id=spec["id"],numeric=[],timing=[],answers=[],contexts=[],probes=[],
                initial_state_sha256=initial,storage=native.runtime.model_storage(model),extra_GPU_weight_storage_bytes=0,
                physical_body_owners=len(pairs));report["models"].append(result)
            with torch.no_grad():
                for arm in ARMS:
                    with route(model,table,pairs,arm) as proof:
                        for work in spec["workloads"]:
                            block=native.numeric(model,work,folder,arm,p,budget)
                            if arm==ARMS[0]:
                                prior=io.load_arrays(io.ROOT/p["previous_head_native_numeric"][spec["id"]][work["id"]]["path"])["actual"]
                                fresh=io.load_arrays(io.ROOT/block["actual_packet"]["path"])["actual"]
                                block["bit_exact_previous_head_native"]=bool(np.array_equal(prior.view(np.uint32),fresh.view(np.uint32)))
                                if not block["bit_exact_previous_head_native"]:raise RuntimeError("head-only control no longer matches closed native")
                            result["numeric"].append(block)
                    result["contexts"].append(proof)
                for work in spec["workloads"]:
                    blocks=[]
                    for index,arm in enumerate(p["timing_order"]):
                        with route(model,table,pairs,arm) as proof:
                            warm=native.generation(model,cfg,tok,work["ids"],16,spec["eos_id"],False,False,budget)
                            samples=[native.generation(model,cfg,tok,work["ids"],16,spec["eos_id"],False,False,budget) for _ in range(3)]
                        result["contexts"].append(proof)
                        same=all(s["generated_ids"]==work["old_generated_ids"] and s["metadata"]==work["old_metadata"] for s in [warm,*samples])
                        blocks.append(dict(block=index,arm=arm,warmup=warm,samples=samples,all_old_fixed_ids_and_metadata_equal=same))
                    left=[s["seconds"] for b in blocks if b["arm"]==ARMS[0] for s in b["samples"]]
                    right=[s["seconds"] for b in blocks if b["arm"]==ARMS[1] for s in b["samples"]]
                    result["timing"].append(dict(workload=work["id"],blocks=blocks,head_median_seconds=float(np.median(left)),
                        head_decode64_median_seconds=float(np.median(right)),speedup=float(np.median(left)/np.median(right))))
                    print("[DECODE_NATIVE_WORKLOAD]"+spec["id"]+"/"+work["id"],flush=True)
                for arm in ARMS:
                    with route(model,table,pairs,arm) as proof:
                        for case in spec["natural_questions"]:
                            seen=native.generation(model,cfg,tok,case["ids"],32,spec["eos_id"],True,case["case"]["mode"]=="chatml",budget)
                            result["answers"].append(dict(arm=arm,case=case["case"],generation=seen,old_answer=case["old_answer"],
                                old_generated_ids_equal=seen["generated_ids"]==case["old_generated_ids"],old_metadata_equal=seen["metadata"]==case["old_metadata"]))
                        for work in [w for w in spec["workloads"] if w["id"] in p["native_probe_workloads"]]:
                            saved=next(b["actual_packet"] for b in result["numeric"] if b["arm"]==arm and b["workload"]==work["id"])
                            result["probes"].append(dict(arm=arm,**probe(model,work,saved,budget)))
                    result["contexts"].append(proof)
            result.update(final_state_sha256=native.identity.state_fingerprint(model),
                physical_state_unchanged=native.identity.state_fingerprint(model)==initial,
                numeric_failures=sum(not row["within_original_tolerance"] for block in result["numeric"] for row in block["rows"]),
                argmax_mismatches=sum(not row["argmax_equal"] for block in result["numeric"] for row in block["rows"]))
            if not result["physical_state_unchanged"]:raise RuntimeError("packed physical state changed")
            model.to("cpu");model=payload=table=pairs=tok=cfg=None;gc.collect();torch.cuda.empty_cache()
            result["model_released"]=ref() is None
            if not result["model_released"]:raise RuntimeError("decode-only model remains referenced")
            io.write_new(folder/"report.json",result)
        failures=sum(m["numeric_failures"] for m in report["models"])
        changed=sum(not b["all_old_fixed_ids_and_metadata_equal"] for m in report["models"] for w in m["timing"] for b in w["blocks"])
        changed+=sum(not a["old_generated_ids_equal"] or not a["old_metadata_equal"] for m in report["models"] for a in m["answers"])
        report.update(numerical_gate_failures=failures,changed_generation_records=changed,
            status="DECODE64_NATIVE_COMPLETE" if failures==0 and changed==0 else "DECODE64_NATIVE_NUMERICAL_OR_ID_NEGATIVE",
            source_payloads_unchanged=all(io.sha(io.ROOT/s["payload"])==s["payload_sha256"] for s in p["models"]))
        if not report["source_payloads_unchanged"]:raise RuntimeError("source payload changed")
    except BaseException as error:
        failure=str(error);report.update(status="DECODE64_NATIVE_ERROR",error=failure,traceback=traceback.format_exc());error.__traceback__=None
    finally:
        model=payload=table=pairs=tok=cfg=None;gc.collect()
        cleanup_error=owner.cleanup_owner.cleanup(report)
        if cleanup_error is not None:failure=failure or str(cleanup_error)
        report["wall_seconds"]=time.monotonic()-started;io.write_new(out/"report.json",report)
    print("[DECODE_NATIVE_END]"+json.dumps(dict(status=report["status"],models=len(report["models"]),error=failure)),flush=True)
    if failure:raise RuntimeError(failure)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","check","actual"));args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="check":verify();print("[DECODE_NATIVE_CHECK]one-row policy,closed controls and clock",flush=True)
    else:actual()


if __name__=="__main__":main()
