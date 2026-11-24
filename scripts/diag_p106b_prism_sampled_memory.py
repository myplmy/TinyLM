"""Observe packed Bonsai device memory across two fresh context allocations."""

import argparse
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

from scripts import diag_p013_native_matched_training as io
from scripts import diag_p106b_prism_native_raw as known
from scripts.diag_p014e_native_sampled_memory import samples
from scripts.p106b_nvml_probe import NvmlClient


TAG="p106b_prism_context_sampled_vram_v1_20261118"
OUT=io.ROOT/"test_result/evidence"/TAG
PROFILE=OUT/"profile.json"
CONTEXTS=(512,1024)
LENGTHS=(128,384)
REPEATS=4
CAP=150


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"]==""
    old=known.verify()
    a=old["prompts"]["A"]["plain_ids"]
    assert a and all(0<=v<old["vocab"] for v in a)
    frozen_ids=[a[i%len(a)] for i in range(max(LENGTHS))]
    paths=("scripts/diag_p106b_prism_sampled_memory.py","scripts/diag_p014e_native_sampled_memory.py",
           "scripts/p106b_nvml_probe.py","scripts/diag_p013_native_matched_training.py")
    OUT.mkdir()
    io.write(PROFILE,dict(tag=TAG,source_sha={p:io.digest(io.ROOT/p) for p in paths},
        earlier_prism_sha256=io.digest(known.PROFILE),bundle=old["bundle"],model=old["model"],
        model_sha256=old["pins"][old["model"]],context_caps=CONTEXTS,lengths=LENGTHS,
        same_synthetic_prompt_ids=frozen_ids,repeats=REPEATS,worker_timeout_seconds=CAP,
        official_evaluation=0,measure_tag="DEVICE_WIDE_NVML_SAMPLING",training_updates=0))
    print("PRISM_SAMPLED_READY",io.digest(PROFILE),flush=True)


def verify():
    p=known.read(PROFILE)
    assert p["earlier_prism_sha256"]==io.digest(known.PROFILE)
    assert all(io.digest(io.ROOT/f)==sha for f,sha in p["source_sha"].items())
    assert os.environ["CUDA_VISIBLE_DEVICES"]=="0"
    assert tuple(p["context_caps"])==CONTEXTS and tuple(p["lengths"])==LENGTHS
    return p


def worker(ctx):
    import hashlib

    p=verify()
    assert os.environ["LD_LIBRARY_PATH"]==p["bundle"]
    assert not any(key.startswith(("LLAMA_ARG_","GGML_")) for key in os.environ)
    path=io.ROOT/p["model"]
    assert io.digest(path)==p["model_sha256"]
    entry=io.reserve_device()
    print(f"PRISM_SAMPLED_WORKER ctx={ctx} pid={os.getpid()}",flush=True)
    cases=[]
    def check():
        if (OUT/"STOP").exists() or time.time()>=io.CUTOFF-30:
            raise TimeoutError("Prism owned stop or cutoff")
    start=time.monotonic_ns()
    with known.native.NativeModel(p["bundle"],path,n_ctx=ctx,check=check) as engine:
        loaded=time.monotonic_ns()
        for length in LENGTHS:
            for rep in range(REPEATS):
                begun=time.monotonic_ns()
                logits=engine.logits(p["same_synthetic_prompt_ids"][:length])
                ended=time.monotonic_ns()
                cases.append(dict(length=length,rep=rep,start_ns=begun,end_ns=ended,
                    logits_sha256=hashlib.sha256(logits.tobytes()).hexdigest().upper(),
                    top1=int(logits.argmax()),tokens=len(logits)))
            print("PRISM_SAMPLED_ACTIVE",ctx,length,REPEATS,flush=True)
        counters=dict(calls=engine.calls,clears=engine.clears,processed=engine.processed_tokens,
                      effective_context=engine.context_limit,batch_limit=engine.batch_limit)
    assert counters["calls"]==counters["clears"]==len(LENGTHS)*REPEATS
    assert io.digest(path)==p["model_sha256"]
    io.write(OUT/f"context_{ctx}.json",dict(context=ctx,entry=entry,model_bytes=path.stat().st_size,
                process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                load=[start,loaded],cases=cases,counters=counters,exit=0,profile_sha256=io.digest(PROFILE)))


def run():
    p=verify()
    assert time.time()+len(CONTEXTS)*(CAP+25)+40<io.CUTOFF
    records=[]
    client=NvmlClient(timeout=3)
    try:
        for ctx in CONTEXTS:
            if (OUT/"STOP").exists():
                break
            entry=io.reserve_device()
            idle=[samples(client) for _ in range(7)]
            env=dict(os.environ,LD_LIBRARY_PATH=p["bundle"])
            command=["timeout","--signal=INT","--kill-after=15s",f"{CAP}s",
                sys.executable,"-B","-u","-m","scripts.diag_p106b_prism_sampled_memory","worker",str(ctx)]
            observed=[]
            with subprocess.Popen(command,cwd=io.ROOT,env=env) as child:
                while child.poll() is None:
                    try:
                        observed.append(samples(client))
                    except (RuntimeError,TimeoutError,OSError,ValueError):
                        break
                    time.sleep(.03)
                code=child.wait()
            release=io.reserve_device()
            io.write(OUT/f"context_{ctx}_nvml.json",dict(context=ctx,idle=idle,samples=observed,entry=entry,release=release))
            records.append(dict(ctx=ctx,exit=code,samples=len(observed)))
            print("PRISM_SAMPLED_TERMINAL",ctx,code,len(observed),flush=True)
    finally:
        metrics=client.close()
        done=len(records)==len(CONTEXTS) and not metrics["query_errors"] and all(
             r["exit"]==0 and r["samples"]>=20 for r in records)
        io.write(OUT/"terminal.json",dict(complete=done,exit=0 if done else 8,rows=records,client=metrics,
                profile_sha256=io.digest(PROFILE),official_evaluation=0))
    return 0 if done else 8


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","run","worker"))
    parser.add_argument("ctx",type=int,nargs="?",choices=CONTEXTS)
    a=parser.parse_args()
    if a.action=="prepare":
        prepare()
    elif a.action=="worker":
        worker(a.ctx)
    else:
        raise SystemExit(run())
