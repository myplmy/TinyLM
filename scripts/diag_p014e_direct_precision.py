"""A bounded accumulator-only comparison, preserving all old negative evidence."""
import argparse
import gc
import json
import time
import traceback
import unittest
import torch
from scripts import diag_p014e_direct_cuda as owner
from scripts import p014e_direct_cuda_fp64 as precise

io=owner.io
BASE=owner.BASE/"precision_v1"
PROFILE=BASE/"profile.json"
CODE=("scripts/p014e_direct_cuda_fp64.py","scripts/diag_p014e_direct_precision.py",
      "scripts/p014e_direct_cuda.py","scripts/diag_p014e_direct_cuda.py","scripts/p014e_packed_g128.py")


def prepare():
    old=owner.verify();owner.Budget().check(admission=True)
    if BASE.exists():raise FileExistsError("preserve the accumulator-only namespace")
    checked=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName("scripts.test_p014e_direct_cuda"))
    if not checked.wasSuccessful() or checked.testsRun!=5:raise RuntimeError("reuse the five unchanged admission contracts")
    previous=io.read(owner.BASE/"actual/report.json")
    if previous["status"]!="DIRECT_PACKED_OPERATOR_NUMERICAL_NEGATIVE" or previous["numerical_gate_failures"]!=2:
        raise ValueError("preserve the original two numerical negatives")
    cases=[c for c in old["cases"] if c["kind"]=="matrix"]
    if len(cases)!=8 or any(c["signature"]["group"]!=128 for c in cases):raise ValueError("same eight real body shapes required")
    BASE.mkdir()
    with (BASE/"initial_plan.md").open("xb") as stream:stream.write(owner.PLAN.read_bytes())
    io.write_new(PROFILE,dict(schema="P014E_BODY_FP64_ACCUMULATOR_V1",authority_directive=142,
        authority_end=owner.clock.AUTHORITY_END.isoformat(),cleanup_seconds=owner.clock.CLEANUP_SECONDS,max_seconds=1800,
        initial_plan_sha256=io.sha(BASE/"initial_plan.md"),sources={name:io.sha(io.ROOT/name) for name in CODE},
        references={str(owner.PROFILE.relative_to(io.ROOT)):io.sha(owner.PROFILE),
                    str((owner.BASE/"actual/report.json").relative_to(io.ROOT)):io.sha(owner.BASE/"actual/report.json")},
        cases=cases,activations=old["activations"],reused_CPU_admission_tests=5,
        arithmetic="Original FP32 decoded weight times original FP32 input, promoted to FP64 product/sum; FP32 output",
        original_gate_unchanged=True,matrix_batches=old["matrix_batches"],linear_rtol=old["linear_rtol"],linear_atol=old["linear_atol"],
        timing_order=old["timing_order"],warmups_per_block=old["warmups_per_block"],measured_per_block=old["measured_per_block"],
        full_body_native_NOT_RUN=True,weights_changed=False,optimizer_updates=0,checkpoint_writes=0,
        original_checkpoint_reads=0,new_model_loads=0,quality_adoption=False))
    if torch.cuda.is_initialized():raise RuntimeError("CPU accumulator admission initialized CUDA")
    print("[FP64_BODY_PREPARED]same eight shapes/sixteen cases;five reused CPU guards;no model",flush=True)


def verify():
    owner.verify();p=io.read(PROFILE)
    if(p["authority_end"]!=owner.clock.AUTHORITY_END.isoformat() or p["authority_directive"]!=142
       or p["cleanup_seconds"]!=owner.clock.CLEANUP_SECONDS or p["initial_plan_sha256"]!=io.sha(BASE/"initial_plan.md")):
        raise ValueError("same current authority and fresh initial plan required")
    for name,digest in {**p["sources"],**p["references"]}.items():
        if io.sha(io.ROOT/name)!=digest:raise ValueError("sealed accumulator source/input changed: "+name)
    return p


def actual():
    p=verify();budget=owner.Budget();budget.check(admission=True);out=BASE/"actual"
    if out.exists():raise FileExistsError("preserve accumulator actual")
    out.mkdir();started=time.monotonic();report=dict(schema=p["schema"],status="STARTED",rows=[],
        profile_sha256=io.sha(PROFILE),direct_kernel_calls=0,weights_changed=False,
        original_FP32_negative_preserved=True,new_model_loads=0,optimizer_updates=0,
        original_checkpoint_reads=0,checkpoint_writes=0,quality_adoption=False)
    payload=available=record=operator=fixtures=None;failure=None
    try:
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        fixtures=io.load_arrays(io.ROOT/p["activations"]["path"])
        with torch.no_grad():
            for index,name in enumerate(owner.INPUTS):
                payload=owner.load(io.ROOT/name);available={r["id"]:r for r in owner.records(payload)}
                for case in [c for c in p["cases"] if c["model_index"]==index]:
                    record=available[case["record_id"]]["record"]
                    if owner.record_signature(record)!=case["signature"]:raise ValueError("old actual body record changed")
                    operator=precise.FP64DirectBodyOperator(record,device="cuda")
                    report["rows"].extend(owner.compare_case(operator,record,fixtures[case["id"]],case,out,p,budget))
                    report["direct_kernel_calls"]+=operator.forward_calls
                    operator=record=None;gc.collect();torch.cuda.empty_cache()
                payload=available=None
        if len(report["rows"])!=16 or report["direct_kernel_calls"]!=144:
            raise RuntimeError("same sixteen cases and144 direct calls required")
        failures=sum(not row["original_gate"] for row in report["rows"])
        report.update(numerical_gate_failures=failures,status="FP64_BODY_OPERATORS_COMPLETE" if failures==0 else "FP64_BODY_OPERATORS_NUMERICAL_NEGATIVE")
    except BaseException as error:
        failure=str(error);report.update(status="FP64_BODY_OPERATOR_ERROR",error=failure,traceback=traceback.format_exc());error.__traceback__=None
    finally:
        payload=available=record=operator=fixtures=None;gc.collect()
        cleanup_error=owner.cleanup_owner.cleanup(report)
        if cleanup_error is not None:failure=failure or str(cleanup_error)
        report["wall_seconds"]=time.monotonic()-started;io.write_new(out/"report.json",report)
    print("[FP64_BODY_END]"+json.dumps(dict(status=report["status"],cases=len(report["rows"]),error=failure)),flush=True)
    if failure:raise RuntimeError(failure)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","check","actual"));args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="check":verify();print("[FP64_BODY_CHECK]same old codes/scales and unchanged gate",flush=True)
    else:actual()


if __name__=="__main__":main()
