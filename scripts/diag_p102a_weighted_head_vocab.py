"""Compare weighted per-token CE and real tied-head optimizer steps at two vocabulary sizes."""

import argparse
import gc
from importlib.metadata import version
import os
import sys
import subprocess
import time

from scripts import diag_p013_native_matched_training as io


TAG = "p102a_tied_head_fused_weighted_vocab_v1_20261118"
OUT = io.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
BACKENDS = ("reference", "liger", "cce_exact", "vocab_tiled")
CASES = ((32768,"fp32"),(248320,"fp32"),(32768,"bf16"),(248320,"bf16"))
ROWS, RANK, HIDDEN, STEPS = 512, 256, 768, 3
SEED, CAP = 311123, 210
SOURCES = (
    "scripts/diag_p102a_weighted_head_vocab.py","scripts/diag_p013_native_matched_training.py",
    "tinylm/train/fused_ce.py","tinylm/train/streaming_head.py","tinylm/train/muon.py",
)
PACKAGES = {"torch":"2.10.0+cu130","triton":"3.6.0","liger-kernel":"0.8.5","cut-cross-entropy":"25.9.3"}


def read(path):
    import json
    return json.loads(path.read_bytes())


def signature():
    return {name:io.digest(io.ROOT/name) for name in SOURCES}


def check_packages():
    assert all(version(name)==expected for name,expected in PACKAGES.items())


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"]==""
    check_packages()
    OUT.mkdir()
    io.write(PROFILE,dict(tag=TAG, source_sha=signature(), packages=PACKAGES, interpreter=sys.executable,
        cases=CASES, backends=BACKENDS, shape=dict(rows=ROWS, rank=RANK, hidden=HIDDEN), steps=STEPS,
        targets_per_step=ROWS-len(range(0,ROWS,9)), loss="weighted per-token CE, -100 mask and index shift",
        seed=SEED, torch_autocast_dtype="match each case", grad_atol=2e-6,grad_rtol=1e-5,
        loss_atol=1e-5,loss_rtol=1e-4, gpu_calls=0,
        ordered_child_timeout_seconds=CAP, generated_fixture=True, checkpoint_writes=0))
    print("P102A_WEIGHTED_HEAD_READY",io.digest(PROFILE),len(CASES),len(BACKENDS),flush=True)


def verify():
    p=read(PROFILE)
    assert p["source_sha"]==signature() and p["interpreter"]==sys.executable
    assert p["cases"]==[list(x) for x in CASES] and p["backends"]==list(BACKENDS)
    check_packages()
    return p


def fixture(torch,vocab):
    gen=torch.Generator(device="cpu").manual_seed(SEED)
    weights=(torch.empty((vocab,RANK)).normal_(0,.025,generator=gen),
             torch.empty((HIDDEN,RANK)).normal_(0,.018,generator=gen))
    dense,vectors=[],[]
    for step in range(STEPS):
        sequence=torch.randint(0,vocab,(ROWS+1,),generator=gen)
        labels=sequence[1:].clone()
        labels[::9]=-100
        weights_i=torch.linspace(.25,1.75,ROWS).roll(step*73)
        dense.append((sequence[:-1].cuda(),labels.cuda(),weights_i.cuda()))
        vectors.append(float(weights_i[labels!=-100].sum()))
    return weights,dense,vectors


def cpu_compare(torch, base, now, atol, rtol):
    mismatch=0
    peak=0.
    for left,right in zip(base.reshape(-1).split(262144),now.reshape(-1).split(262144),strict=True):
        mismatch+=int((~torch.isclose(left,right,atol=atol,rtol=rtol)).sum())
        peak=max(peak,float((left-right).abs().max()))
    return dict(elements=base.numel(),mismatch=mismatch,max_abs=peak)


def arm(torch, name, dtype, setup):
    import torch.nn.functional as F
    from tinylm.train.fused_ce import linear_ce
    from tinylm.train.muon import Muon
    from tinylm.train.streaming_head import vocab_nll

    init, inputs, denominators=setup
    table,projection=[torch.nn.Parameter(t.cuda()) for t in init]
    adam=torch.optim.AdamW([table],lr=5e-5,weight_decay=0.)
    muon=Muon([projection],lr=2e-4,scale_mode="rms")
    rows=[]
    receipt=None
    for step,(ids,labels,weights) in enumerate(inputs):
        assert not (OUT/"STOP").exists()
        adam.zero_grad(set_to_none=True)
        muon.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        before=torch.cuda.memory_allocated()
        started=time.perf_counter()
        with torch.autocast("cuda",dtype=torch.bfloat16,enabled=dtype=="bf16"):
            hidden=F.layer_norm(F.linear(F.embedding(ids,table),projection),(HIDDEN,))
            projected=F.linear(hidden,projection.t())
            logits_table=table.to(projected.dtype)
            if name=="vocab_tiled":
                valid=labels.ne(-100)
                kept=vocab_nll(projected[valid],logits_table,labels[valid],tile=8192)
                nll=torch.zeros_like(weights).masked_scatter(valid,kept.float())
            else:
                nll=linear_ce(projected,logits_table,labels,backend=name,reduction="none")
            loss=(nll*weights).sum()/denominators[step]
        loss.backward()
        raw=(table.grad,projection.grad)
        torch.cuda.synchronize()
        backward_done=time.perf_counter()
        assert nll.shape==labels.shape and bool((nll[labels==-100]==0).all())
        assert all(t is not None and bool(torch.isfinite(t).all()) and bool(torch.count_nonzero(t)>0) for t in raw)
        cpu_raw=[t.detach().cpu() for t in raw] if step==0 else None
        norm=torch.nn.utils.clip_grad_norm_([table,projection],1.,error_if_nonfinite=True)
        adam.step()
        muon.step()
        torch.cuda.synchronize()
        rows.append(dict(step=step+1, weighted_loss=float(loss.detach()), targets=int(labels.ne(-100).sum()),
            grad_norm=float(norm),forward_backward_seconds=backward_done-started, before_allocated=before,
            peak_allocated=torch.cuda.max_memory_allocated(), peak_reserved=torch.cuda.max_memory_reserved()))
        if step==0:
            receipt={"nll":nll.detach().float().cpu(),"table_grad":cpu_raw[0],"projection_grad":cpu_raw[1],
                "table_after":table.detach().cpu(),"projection_after":projection.detach().cpu()}
    return rows,receipt


def worker(vocab,precision):
    import torch
    p=verify()
    assert (vocab,precision) in CASES and os.environ["CUDA_VISIBLE_DEVICES"]=="0"
    entry=io.reserve_device()
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    setup=fixture(torch,vocab)
    print(f"P102A_WEIGHTED_WORKER {vocab}/{precision} pid={os.getpid()}",flush=True)
    reports={}
    base=None
    for name in BACKENDS:
        try:
            rows,state=arm(torch,name,precision,setup)
            comparisons={}
            if name=="reference":
                base=state
            elif base is not None:
                for key,value in state.items():
                    kind="loss" if key=="nll" else "grad"
                    comparisons[key]=cpu_compare(torch,base[key],value,p[kind+"_atol"],p[kind+"_rtol"])
            reports[name]=dict(status="COMPLETE",updates=len(rows),rows=rows,first_step=comparisons)
            print("P102A_WEIGHTED_ARM",vocab,precision,name,len(rows),
                  sum(v["mismatch"] for v in comparisons.values()),flush=True)
            del state
        except Exception as exc:
            reports[name]=dict(status="ERROR",type=type(exc).__name__,message=str(exc)[:900])
            print("P102A_WEIGHTED_ARM_ERROR",vocab,precision,name,type(exc).__name__,str(exc)[:300],flush=True)
        gc.collect()
        torch.cuda.empty_cache()
    complete=all(value["status"]=="COMPLETE" for value in reports.values())
    io.write(OUT/f"{vocab}_{precision}.json",dict(vocab=vocab,precision=precision,entry=entry,
        profile_sha256=io.digest(PROFILE),reports=reports,exit=0 if complete else 8))
    return 0 if complete else 8


def run():
    assert os.environ["CUDA_VISIBLE_DEVICES"]=="0"
    verify()
    assert time.time()+len(CASES)*(CAP+25)+40 < io.CUTOFF
    cases=[]
    for vocab,precision in CASES:
        if (OUT/"STOP").exists():
            break
        if time.time()+CAP+45>=io.CUTOFF:
            break
        io.reserve_device()
        path=OUT/f"{vocab}_{precision}.json"
        assert not path.exists()
        command=["timeout","--signal=INT","--kill-after=15s",f"{CAP}s",sys.executable,"-B","-u","-m",
                 "scripts.diag_p102a_weighted_head_vocab","worker",str(vocab),precision]
        start=time.monotonic()
        result=subprocess.run(command,cwd=io.ROOT)
        cases.append(dict(vocab=vocab,precision=precision,exit=result.returncode,
            report=path.name,seconds=time.monotonic()-start))
        print("P102A_WEIGHTED_TERMINAL",vocab,precision,result.returncode,flush=True)
    release=io.reserve_device()
    complete=len(cases)==len(CASES)
    status=0 if complete and all(c["exit"]==0 for c in cases) else 8
    io.write(OUT/"terminal.json",dict(complete=complete,exit=status,cases=cases,release=release,
        profile_sha256=io.digest(PROFILE),replays=0,checkpoint_writes=0))
    return status


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run","worker"))
    p.add_argument("vocab",nargs="?",type=int)
    p.add_argument("precision",nargs="?")
    a=p.parse_args()
    if a.action=="prepare":
        prepare()
    elif a.action=="run":
        raise SystemExit(run())
    else:
        raise SystemExit(worker(a.vocab,a.precision))
