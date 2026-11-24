"""Local C build, CPU ABI contracts and same-payload direct operator comparison."""
import argparse
import gc
import json
import os
import platform
import resource
import shutil
import subprocess
import threading
import time
import traceback
import unittest
import numpy as np
import torch
from scripts import diag_p014e_direct_cuda as owner
from scripts import p014e_direct_cpu as direct

io=owner.io
BASE=owner.BASE/"cpu_v1"
PROFILE=BASE/"profile.json"
CODE=("scripts/p014e_direct_cpu.c","scripts/p014e_direct_cpu.py","scripts/diag_p014e_direct_cpu.py",
      "scripts/test_p014e_direct_cpu.py","scripts/p014e_packed_g128.py","tinylm/model/lut.py")


def prepare():
    owner.Budget().check(admission=True);old=owner.verify()
    if BASE.exists():raise FileExistsError("preserve direct CPU build/admission namespace")
    compiler=shutil.which("cc")
    if compiler is None:raise RuntimeError("existing compiler unavailable;installation not authorized")
    BASE.mkdir();runtime=BASE/"runtime";runtime.mkdir();library=runtime/"libp014e_five_trit_cpu.so"
    version=subprocess.run([compiler,"--version"],capture_output=True,text=True,timeout=10,check=True).stdout
    argv=[compiler,"-O3","-std=c11","-fPIC","-shared","-ffp-contract=off","-fno-fast-math",
          str(io.ROOT/"scripts/p014e_direct_cpu.c"),"-o",str(library)]
    with (BASE/"initial_plan.md").open("xb") as stream:stream.write(owner.PLAN.read_bytes())
    io.write_new(BASE/"SOURCE_SNAPSHOT_BEFORE_BUILD.json",dict(
        sources={n:dict(sha256=io.sha(io.ROOT/n),text=(io.ROOT/n).read_text()) for n in CODE},
        compiler_argv=argv,compiler_version=version,authority_directive=142,initial_plan_sha256=io.sha(BASE/"initial_plan.md")))
    started=time.monotonic();built=subprocess.run(argv,cwd=io.ROOT,capture_output=True,text=True,timeout=120,check=False)
    io.write_new(BASE/"compiler_report.json",dict(argv=argv,version=version,returncode=built.returncode,
        stdout=built.stdout,stderr=built.stderr,seconds=time.monotonic()-started,
        packages_installed=0,system_libraries_modified=0,OpenMP_linked=False))
    if built.returncode:raise RuntimeError("local C build failed;preserve source snapshot and compiler report")
    digest=io.sha(library);os.environ.update(P014E_CPU_LIBRARY_PATH=str(library),P014E_CPU_LIBRARY_SHA256=digest)
    torch.set_num_threads(4)
    checked=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName("scripts.test_p014e_direct_cpu"))
    if not checked.wasSuccessful() or checked.testsRun!=6:raise RuntimeError("six CPU ABI/group/digit/lifetime contracts required")
    if any(t.name.startswith("p014e-cpu") for t in threading.enumerate()):raise RuntimeError("ABI test workers remain")
    io.write_new(PROFILE,dict(schema="P014E_DIRECT_CPU_OPERATORS_V1",authority_directive=142,
        authority_end=owner.clock.AUTHORITY_END.isoformat(),cleanup_seconds=owner.clock.CLEANUP_SECONDS,max_seconds=1800,
        initial_plan_sha256=io.sha(BASE/"initial_plan.md"),sources={n:io.sha(io.ROOT/n) for n in CODE},
        references={str(owner.PROFILE.relative_to(io.ROOT)):io.sha(owner.PROFILE)},
        library=dict(path=str(library.relative_to(io.ROOT)),sha256=digest,bytes=library.stat().st_size,ABI=direct.ABI),
        compiler_argv=argv,compiler_version=version,ABI_contracts=checked.testsRun,workers=4,torch_threads=4,
        torch_version=torch.__version__,platform=platform.platform(),cpu_affinity=sorted(os.sched_getaffinity(0)),
        cases=old["cases"],activations=old["activations"],matrix_batches=old["matrix_batches"],
        linear_rtol=old["linear_rtol"],linear_atol=old["linear_atol"],lookup_bit_exact=True,
        timing_order=old["timing_order"],warmups_per_block=1,measured_per_block=3,
        memory_scope="PROCESS_RSS_HIGH_WATER_IS_MONOTONIC_NOT_A_PAIRED_PER_OPERATOR_PEAK",
        full_weight_cache=False,weights_changed=False,original_checkpoint_reads=0,
        new_model_loads=0,optimizer_updates=0,checkpoint_writes=0,quality_adoption=False))
    if torch.cuda.is_initialized():raise RuntimeError("CPU C build/tests initialized CUDA")
    print("[CPU_PACKED_PREPARED]six ABI contracts;existing compiler;new local library;no CUDA",flush=True)


def verify():
    owner.verify();p=io.read(PROFILE)
    if(p["authority_directive"]!=142 or p["authority_end"]!=owner.clock.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=owner.clock.CLEANUP_SECONDS or p["initial_plan_sha256"]!=io.sha(BASE/"initial_plan.md")):
        raise ValueError("exact current CPU authority and source plan required")
    for n,d in {**p["sources"],**p["references"]}.items():
        if io.sha(io.ROOT/n)!=d:raise ValueError("CPU source/input changed: "+n)
    if io.sha(io.ROOT/p["library"]["path"])!=p["library"]["sha256"]:raise ValueError("local ABI library changed")
    if torch.__version__!=p["torch_version"]:raise ValueError("same installed torch version required")
    return p


def run_case(operator,record,x,case,folder,p,budget):
    reference=owner.direct.reference.PackedGroupLinear(record,tile_rows=case["reference_tile_rows"])
    calls=[]
    if case["kind"]=="table" or case["id"]=="synthetic":
        ids=torch.tensor(case["lookup_ids"],dtype=torch.long)
        if case["kind"]=="table":
            table=owner.direct.reference.PackedTernaryTable(record,head_rows=min(1024,record["out_features"]-1))
            lookup=lambda:table.rows(ids)
        else:lookup=lambda:reference.unpack_rows(0,record["out_features"])[ids]
        calls.append(("lookup",lambda:operator.lookup(ids),lookup))
    for size in p["matrix_batches"]:
        value=torch.from_numpy(x[:size]).contiguous()
        calls.append(("linear_m"+str(size),lambda value=value:operator(value),lambda value=value:reference(value)))
    rows=[]
    for name,fast,ref in calls:
        budget.check();start=time.perf_counter();a=ref();reference_first=time.perf_counter()-start
        start=time.perf_counter();b=fast();direct_first=time.perf_counter()-start
        left=a.numpy().copy();right=b.numpy().copy();a=b=None
        delta=np.abs(right.astype(np.float64)-left.astype(np.float64))
        exact=bool(np.array_equal(left.view(np.uint32),right.view(np.uint32)))
        close=bool(np.allclose(right,left,rtol=p["linear_rtol"],atol=p["linear_atol"]))
        packet=io.save_arrays(folder/(case["id"]+"_"+name+".npz"),reference=left,actual=right)
        blocks=[]
        for i,arm in enumerate(p["timing_order"]):
            call=ref if arm=="REFERENCE" else fast
            warm=call();warm=None;samples=[]
            for _ in range(3):
                budget.check();start=time.perf_counter();value=call();seconds=time.perf_counter()-start;value=None
                samples.append(dict(wall_seconds=seconds))
            blocks.append(dict(index=i,arm=arm,samples=samples))
        old=[s["wall_seconds"] for b in blocks if b["arm"]=="REFERENCE" for s in b["samples"]]
        new=[s["wall_seconds"] for b in blocks if b["arm"]=="DIRECT" for s in b["samples"]]
        row=dict(case=case["id"],operator=name,kind=case["kind"],shape=list(left.shape),vectors=packet,
            bit_exact=exact,within_original_linear_tolerance=close,original_gate=exact if name=="lookup" else close,
            maximum_absolute_error=float(delta.max()),mean_absolute_error=float(delta.mean()),
            argmax_mismatches=None if name=="lookup" else int(np.sum(left.argmax(-1)!=right.argmax(-1))),
            reference_first_seconds=reference_first,direct_first_seconds=direct_first,ABBA=blocks,
            reference_median_seconds=float(np.median(old)),direct_median_seconds=float(np.median(new)),
            speedup=float(np.median(old)/np.median(new)),packed_storage_bytes=operator.storage_bytes(),
            same_cpu_packed_buffers=True,unpacked_weight_cache=False)
        rows.append(row);print("[CPU_PACKED_OPERATOR]"+json.dumps({k:row[k] for k in(
            "case","operator","original_gate","maximum_absolute_error","argmax_mismatches","speedup")}),flush=True)
    return rows


def actual():
    p=verify();budget=owner.Budget();budget.check(admission=True);out=BASE/"actual"
    if out.exists():raise FileExistsError("preserve CPU operator actual")
    out.mkdir();started=time.monotonic();report=dict(schema=p["schema"],status="STARTED",rows=[],
        profile_sha256=io.sha(PROFILE),new_model_loads=0,original_checkpoint_reads=0,
        optimizer_updates=0,checkpoint_writes=0,quality_adoption=False,CUDA_initialized=False)
    runtime=payload=available=record=operator=fixtures=None;failure=None
    try:
        torch.set_num_threads(p["torch_threads"])
        runtime=direct.KernelRuntime(io.ROOT/p["library"]["path"],p["library"]["sha256"],workers=p["workers"])
        fixtures=io.load_arrays(io.ROOT/p["activations"]["path"])
        with torch.no_grad():
            for index,name in enumerate(owner.INPUTS):
                payload=owner.load(io.ROOT/name);available={r["id"]:r for r in owner.records(payload)}
                for case in [c for c in p["cases"] if c["model_index"]==index]:
                    record=available[case["record_id"]]["record"]
                    if owner.record_signature(record)!=case["signature"]:raise ValueError("original CPU record changed")
                    operator=direct.PackedCPUOperator(record,runtime)
                    report["rows"].extend(run_case(operator,record,fixtures[case["id"]],case,out,p,budget))
                    operator=record=None
                payload=available=None;gc.collect()
            record=owner.synthetic_record();operator=direct.PackedCPUOperator(record,runtime)
            case=dict(id="synthetic",kind="synthetic",lookup_ids=list(range(244)),reference_tile_rows=244)
            report["rows"].extend(run_case(operator,record,fixtures["synthetic"],case,out,p,budget))
        if len(report["rows"])!=25:raise RuntimeError("same25 CPU operator cases required")
        failures=sum(not r["original_gate"] for r in report["rows"])
        report.update(numerical_gate_failures=failures,status="CPU_DIRECT_OPERATORS_COMPLETE" if failures==0 else "CPU_DIRECT_OPERATORS_NUMERICAL_NEGATIVE",
            process_RSS_high_water_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            original_payloads_unchanged=all(io.sha(io.ROOT/n)==pin["sha256"] for n,pin in io.read(owner.PROFILE)["inputs"].items()))
        if not report["original_payloads_unchanged"]:raise RuntimeError("original payload bytes changed")
    except BaseException as error:
        failure=str(error);report.update(status="CPU_DIRECT_OPERATORS_ERROR",error=failure,traceback=traceback.format_exc());error.__traceback__=None
    finally:
        payload=available=record=operator=fixtures=None
        if runtime is not None:runtime.close()
        runtime=None;gc.collect();report["worker_threads_released"]=not any(t.name.startswith("p014e-cpu") for t in threading.enumerate())
        report["CUDA_initialized"]=torch.cuda.is_initialized()
        if report["CUDA_initialized"] or not report["worker_threads_released"]:failure=failure or "CPU resource closure failed"
        report["wall_seconds"]=time.monotonic()-started;io.write_new(out/"report.json",report)
    print("[CPU_PACKED_END]"+json.dumps(dict(status=report["status"],rows=len(report["rows"]),error=failure)),flush=True)
    if failure:raise RuntimeError(failure)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","check","actual"));args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="check":verify();print("[CPU_PACKED_CHECK]owned ABI/source,old payloads and clock",flush=True)
    else:actual()


if __name__=="__main__":main()
