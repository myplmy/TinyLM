"""Frozen-payload operator admission and ABBA timing; no model/quality claim."""
import argparse
import gc
import json
import os
from pathlib import Path
import shutil
import time
import traceback
import unittest
import numpy as np
import torch
import triton
from scripts import p014e_direct_cuda as direct
from scripts import diag_p108c_scope as io
from scripts import p108c_limits as clock
from scripts import p108_weight_space as identity
from scripts import diag_p108b_value_library as cleanup_owner

BASE=io.ROOT/"test_result/evidence/p014e_direct_packed_v1_s1337"
PROFILE=BASE/"profile.json"
INPUTS=("runs/deploy/p014e_native595_g128_v1_20261027/ternary5_existing_twn.pt",
        "runs/deploy/p014e_g270_large_vocab_v2_20261027/ternary5_existing_twn.pt")
CODE=("scripts/p014e_direct_cuda.py","scripts/diag_p014e_direct_cuda.py","scripts/test_p014e_direct_cuda.py",
      "scripts/p014e_packed_g128.py","tinylm/model/lut.py","scripts/p108c_limits.py")
PLAN=io.ROOT/"test_plan/P014E_회전삼진-민감도와-직접패킹-단계게이트.md"


class Budget(clock.Budget):
    def __init__(self,seconds=1800):super().__init__(seconds);self.last_disk=0.
    def check(self,**kwargs):
        result=super().check(**kwargs);now=time.monotonic()
        if now-self.last_disk>5:
            self.last_disk=now
            if shutil.disk_usage(io.ROOT).free<5_000_000_000:raise RuntimeError("less than5GB free;no cleanup authorized")
            if BASE.exists() and sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())>=950_000_000:
                raise RuntimeError("direct packed namespace reached950MB internal cap")
        return result


def load(path):
    payload=torch.load(path,map_location="cpu",weights_only=True)
    if(payload["schema"]!=direct.reference.SCHEMA or payload["embedding_format"]!="ternary5_existing_twn"
       or payload["embedding"] is None):raise ValueError("closed original-scale TWN payload required")
    return payload


def records(payload):
    result=[dict(id="embedding",kind="table",record=payload["embedding"],owners=["packed_embedding"])]
    seen=set()
    for index,row in enumerate(payload["matrices"]):
        record=row["weight"];shape=(record["in_features"],record["out_features"],record["group"])
        if shape not in seen:
            seen.add(shape);result.append(dict(id="matrix"+str(index).zfill(3),kind="matrix",record=record,owners=row["paths"]))
    if not 1<=len(seen)<=8:raise ValueError("bounded complete unique operator-shape set required")
    return result


def record_signature(record):
    return dict(in_features=record["in_features"],out_features=record["out_features"],group=record["group"],
                code_sha256=identity.tensor_sha(record["codes"]),scale_sha256=identity.tensor_sha(record["scales"]))


def synthetic_record():
    # Every legal byte at the first digit block of two distinct128-trit groups.
    trits=torch.zeros(244,256);powers=torch.tensor([1,3,9,27,81])
    digits=((torch.arange(243)[:,None]//powers)%3-1).float()
    trits[:243,:5]=digits;trits[:243,128:133]=digits.flip(-1)
    scale=(torch.arange(244).remainder(7)+1).float()*.03125
    return direct.reference.pack_weight(trits*scale[:,None],128)


def prepare():
    Budget().check(admission=True)
    if BASE.exists():raise FileExistsError("preserve direct packed namespace")
    suite=unittest.defaultTestLoader.loadTestsFromName("scripts.test_p014e_direct_cuda")
    checked=unittest.TextTestRunner(verbosity=2).run(suite)
    if not checked.wasSuccessful() or checked.testsRun!=5:raise RuntimeError("five CPU admission contracts required")
    generator=torch.Generator().manual_seed(1337);cases=[];arrays={};inputs={}
    for model_index,name in enumerate(INPUTS):
        path=io.ROOT/name;before=io.sha(path);payload=load(path)
        for entry in records(payload):
            record=entry["record"];direct.reference.validate_record(record)
            caseid="model"+str(model_index)+"_"+entry["id"]
            arrays[caseid]=torch.randn(8,record["in_features"],generator=generator).numpy()
            ids=[0,1,record["out_features"]-1,record["out_features"]//2,5,record["out_features"]-2]
            cases.append(dict(id=caseid,model_index=model_index,record_id=entry["id"],kind=entry["kind"],
                              owners=entry["owners"],signature=record_signature(record),lookup_ids=ids,
                              reference_tile_rows=1024 if entry["kind"]=="table" else record["out_features"]))
        if before!=io.sha(path):raise RuntimeError("source payload changed during CPU admission")
        inputs[name]=dict(sha256=before,bytes=path.stat().st_size,original_parameters=payload["original_parameters"],
                          vocab_size=payload["cfg"]["vocab_size"],embedding_rank=payload["cfg"]["emb_rank"])
        payload=None
    synthetic=synthetic_record();direct.reference.validate_record(synthetic)
    arrays["synthetic"]=torch.randn(8,256,generator=generator).numpy()
    BASE.mkdir()
    with (BASE/"initial_plan.md").open("xb") as stream:stream.write(PLAN.read_bytes())
    fixture=io.save_arrays(BASE/"activations.npz",**arrays)
    io.write_new(PROFILE,dict(schema="P014E_DIRECT_FIVE_TRIT_OPERATORS_V1",authority_directive=142,
        authority_end=clock.AUTHORITY_END.isoformat(),cleanup_seconds=clock.CLEANUP_SECONDS,max_seconds=1800,
        initial_plan_sha256=io.sha(BASE/"initial_plan.md"),sources={name:io.sha(io.ROOT/name) for name in CODE},
        inputs=inputs,cases=cases,activations=fixture,synthetic_signature=record_signature(synthetic),
        CPU_contracts=checked.testsRun,torch_version=torch.__version__,triton_version=triton.__version__,
        arithmetic="FP32 product and reduction; fusion disabled; no TF32, autocast or unpacked matrix cache",
        matrix_batches=[1,8],lookup_bit_exact=True,linear_rtol=.00002,linear_atol=.000002,
        timing_order=["REFERENCE","DIRECT","DIRECT","REFERENCE"],warmups_per_block=1,measured_per_block=3,
        cache_environment=dict(TRITON_CACHE_DIR=str(BASE/"runtime_cache/triton"),CUDA_CACHE_PATH=str(BASE/"runtime_cache/cuda")),
        owned_total_cap_bytes=1_000_000_000,owned_internal_cap_bytes=950_000_000,one_file_limit=20_000_000,
        synthetic_activations_not_model_features=True,new_model_loads=0,optimizer_updates=0,
        checkpoint_writes=0,original_checkpoint_reads=0,quality_adoption=False))
    if torch.cuda.is_initialized():raise RuntimeError("CPU operator admission initialized CUDA")
    print("[DIRECT_PACKED_PREPARED]"+json.dumps(dict(cases=len(cases),CPU_contracts=checked.testsRun,
        payload_vocabs=[v["vocab_size"] for v in inputs.values()],new_model_loads=0)),flush=True)


def verify():
    Budget().check(admission=True);p=io.read(PROFILE)
    if(p["authority_directive"]!=142 or p["authority_end"]!=clock.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=clock.CLEANUP_SECONDS or p["initial_plan_sha256"]!=io.sha(BASE/"initial_plan.md")):
        raise ValueError("exact new authority/clock/initial plan required")
    for name,digest in p["sources"].items():
        if io.sha(io.ROOT/name)!=digest:raise ValueError("frozen operator source changed: "+name)
    for name,pin in p["inputs"].items():
        if io.sha(io.ROOT/name)!=pin["sha256"]:raise ValueError("closed payload changed")
    if torch.__version__!=p["torch_version"] or triton.__version__!=p["triton_version"]:
        raise ValueError("reuse the frozen installed versions")
    for name,path in p["cache_environment"].items():
        if os.environ.get(name)!=path:raise ValueError("compile caches must stay in owned namespace")
    if io.sha(io.ROOT/p["activations"]["path"])!=p["activations"]["sha256"]:
        raise ValueError("fixed synthetic activations changed")
    return p


def timed(call,budget):
    budget.check();torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats()
    start=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
    start.record();wall=time.perf_counter();value=call();end.record();end.synchronize()
    result=dict(wall_seconds=time.perf_counter()-wall,cuda_event_ms=start.elapsed_time(end),
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                final_allocated_bytes=torch.cuda.memory_allocated(),final_reserved_bytes=torch.cuda.memory_reserved())
    value=None;return result


def compare_case(op,record,activation,case,out,p,budget):
    reference=direct.reference.PackedGroupLinear(record,tile_rows=case["reference_tile_rows"])
    reference.packed_codes=op.packed_codes;reference.group_scales=op.group_scales
    rows=[]
    calls=[]
    if case["kind"]=="table" or case["id"]=="synthetic":
        ids=torch.tensor(case["lookup_ids"],dtype=torch.long,device="cuda")
        if case["kind"]=="table":
            table=direct.reference.PackedTernaryTable(record,head_rows=min(1024,record["out_features"]-1))
            table.packed_codes=op.packed_codes;table.group_scales=op.group_scales
            lookup_reference=lambda:table.rows(ids)
        else:
            # The historical table intentionally supports per-row scales only.
            # Its group-linear row decoder supplies the exhaustive G128 control.
            lookup_reference=lambda:reference.unpack_rows(0,record["out_features"])[ids]
        calls.append(("lookup",lambda:op.lookup(ids),lookup_reference))
    for batch in p["matrix_batches"]:
        x=torch.from_numpy(activation[:batch]).to("cuda")
        calls.append(("linear_m"+str(batch),lambda x=x:op(x),lambda x=x:reference(x)))
    for name,fast,ref in calls:
        budget.check();reference_start=time.perf_counter();expected=ref();torch.cuda.synchronize()
        reference_first_seconds=time.perf_counter()-reference_start
        start=time.perf_counter();actual=fast();torch.cuda.synchronize();first_seconds=time.perf_counter()-start
        left=expected.detach().cpu().numpy().copy();right=actual.detach().cpu().numpy().copy()
        expected=actual=None
        difference=np.abs(right.astype(np.float64)-left.astype(np.float64))
        exact=bool(np.array_equal(left.view(np.uint32),right.view(np.uint32)))
        close=bool(np.allclose(right,left,rtol=p["linear_rtol"],atol=p["linear_atol"]))
        vectors=io.save_arrays(out/(case["id"]+"_"+name+".npz"),reference=left,actual=right)
        blocks=[]
        for index,policy in enumerate(p["timing_order"]):
            call=ref if policy=="REFERENCE" else fast
            for _ in range(p["warmups_per_block"]):value=call();torch.cuda.synchronize();value=None
            samples=[timed(call,budget) for _ in range(p["measured_per_block"])]
            blocks.append(dict(index=index,policy=policy,samples=samples))
        ref_times=[s["wall_seconds"] for b in blocks if b["policy"]=="REFERENCE" for s in b["samples"]]
        fast_times=[s["wall_seconds"] for b in blocks if b["policy"]=="DIRECT" for s in b["samples"]]
        row=dict(case=case["id"],operator=name,kind=case["kind"],shape=list(left.shape),vectors=vectors,
            bit_exact=exact,within_original_linear_tolerance=close,
            maximum_absolute_error=float(difference.max()),mean_absolute_error=float(difference.mean()),
            changed_scalar_count=int(np.count_nonzero(left.view(np.uint32)!=right.view(np.uint32))),
            argmax_mismatches=None if name=="lookup" else int(np.sum(left.argmax(-1)!=right.argmax(-1))),
            original_gate=exact if name=="lookup" else close,
            direct_first_call_seconds=first_seconds,reference_first_call_seconds=reference_first_seconds,
            ABBA=blocks,reference_median_wall_seconds=float(np.median(ref_times)),
            direct_median_wall_seconds=float(np.median(fast_times)),
            steady_wall_speedup=float(np.median(ref_times)/np.median(fast_times)),
            same_gpu_packed_buffers_for_both=True,packed_storage_bytes=op.storage_bytes(),unpacked_weight_cache=False)
        rows.append(row);print("[DIRECT_PACKED_OPERATOR]"+json.dumps({k:row[k] for k in(
            "case","operator","original_gate","maximum_absolute_error","argmax_mismatches","steady_wall_speedup")}),flush=True)
    return rows


def actual():
    p=verify();budget=Budget();budget.check(admission=True);out=BASE/"actual"
    if out.exists():raise FileExistsError("preserve direct packed actual")
    out.mkdir();started=time.monotonic();report=dict(schema=p["schema"],status="STARTED",rows=[],
        profile_sha256=io.sha(PROFILE),entry_resources=cleanup_owner.resources(),new_model_loads=0,
        original_checkpoint_reads=0,new_generated_answers=0,optimizer_updates=0,checkpoint_writes=0,quality_adoption=False)
    payload=op=record=activation=fixtures=None;failure=None
    try:
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        fixtures=io.load_arrays(io.ROOT/p["activations"]["path"])
        with torch.no_grad():
            for model_index,name in enumerate(INPUTS):
                payload=load(io.ROOT/name);available={r["id"]:r for r in records(payload)}
                for case in [c for c in p["cases"] if c["model_index"]==model_index]:
                    budget.check();record=available[case["record_id"]]["record"]
                    if record_signature(record)!=case["signature"]:raise ValueError("selected real operator changed")
                    op=direct.DirectPackedOperator(record,device="cuda");activation=fixtures[case["id"]]
                    report["rows"].extend(compare_case(op,record,activation,case,out,p,budget))
                    op=record=activation=None;gc.collect();torch.cuda.empty_cache()
                payload=available=None
            record=synthetic_record()
            if record_signature(record)!=p["synthetic_signature"]:raise ValueError("exhaustive byte fixture changed")
            op=direct.DirectPackedOperator(record,device="cuda")
            case=dict(id="synthetic",kind="synthetic",lookup_ids=list(range(244)),reference_tile_rows=244)
            report["rows"].extend(compare_case(op,record,fixtures["synthetic"],case,out,p,budget))
            op=record=None
        report["numerical_gate_failures"]=sum(not r["original_gate"] for r in report["rows"])
        report["status"]="DIRECT_PACKED_OPERATOR_COMPLETE" if not report["numerical_gate_failures"] else "DIRECT_PACKED_OPERATOR_NUMERICAL_NEGATIVE"
        report["source_payloads_unchanged"]=all(io.sha(io.ROOT/name)==pin["sha256"] for name,pin in p["inputs"].items())
        if not report["source_payloads_unchanged"]:raise RuntimeError("source payload bytes changed")
    except BaseException as error:
        failure=str(error);report.update(status="DIRECT_PACKED_OPERATOR_ERROR",error=failure,traceback=traceback.format_exc());error.__traceback__=None
    finally:
        payload=op=record=activation=fixtures=None;gc.collect()
        cleanup_error=cleanup_owner.cleanup(report)
        if cleanup_error is not None:failure=failure or str(cleanup_error)
        report["wall_seconds"]=time.monotonic()-started;io.write_new(out/"report.json",report)
    print("[DIRECT_PACKED_END]"+json.dumps(dict(status=report["status"],rows=len(report["rows"]),error=failure)),flush=True)
    if failure:raise RuntimeError(failure)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","check","actual"));args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="check":verify();print("[DIRECT_PACKED_CHECK]frozen original scales/shapes,cache path and clock",flush=True)
    else:actual()


if __name__=="__main__":main()
