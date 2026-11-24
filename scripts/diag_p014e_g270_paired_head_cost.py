"""Measure the original and table heads on the same real CUDA activations."""

import argparse
import os
from pathlib import Path
import statistics
import time

from scripts import diag_p014e_g270_table_head_native as table


io = table.io
TAG = "p014e_g270_paired_head_cost_v1_20261118"
OUT = table.OUT.parent / TAG
PROFILE = OUT / "profile.json"
ORDER = ("original","table","table","original","table","original","original","table")
CALLS = 16


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
    prior = io.read(table.PROFILE)
    report = io.read(table.OUT / "terminal.json")
    assert report["complete"] and report["passed_original_tolerance_and_ids"]
    assert report["profile_sha256"] == io.sha(table.PROFILE)
    pins = dict(prior["pins"])
    for path in (Path(__file__).resolve(),table.PROFILE,table.OUT/"terminal.json"):
        pins[str(path.relative_to(io.ROOT))] = io.sha(path)
    assert all(io.sha(io.ROOT/name)==digest for name,digest in pins.items())
    OUT.mkdir()
    io.write(PROFILE,dict(tag=TAG,pins=pins,model=prior["model"],core_sha256=prior["original_core_sha256"],
        atol=prior["atol"],rtol=prior["rtol"],order=ORDER,block_calls=CALLS,scope="HEAD_ONLY_CUDA_EVENTS",
        old_native_requests=0,official_eval_rows=0,maximum_seconds=150,gpu_calls=0))
    print("P014E_G270_PAIRED_READY",io.sha(PROFILE),flush=True)


def run():
    import torch
    from scripts import diag_p014e_decode_native as old

    p=io.read(PROFILE)
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    assert all(io.sha(io.ROOT/name)==digest for name,digest in p["pins"].items())
    assert time.time()+p["maximum_seconds"]+30<table.table_test.previous.device_contract.CUTOFF
    print(f"P014E_G270_PAIRED_WORKER pid={os.getpid()}",flush=True)
    entry=table.table_test.previous.device_contract.reserve_device()
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    spec=p["model"]
    payload=old.owner.load(io.ROOT/spec["payload"])
    model=old.owner.direct.reference.load_payload(payload,device="cuda",tile_rows=4096)
    original,body=old.operators(model,payload)
    candidate=table.table_head(original)
    assert old.native.identity.state_fingerprint(model)==p["core_sha256"]
    features=[]

    class Capture:
        packed_codes=original.packed_codes
        group_scales=original.group_scales
        lookup=staticmethod(original.lookup)

        def __call__(self, x):
            assert x.numel()==table.table_test.K and x.dtype==torch.float32
            features.append(x.detach().clone())
            return x.new_zeros((*x.shape[:-1],table.table_test.N))

    budget=table.Budget()
    sample_names=[]
    with torch.no_grad(),old.route(model,Capture(),body,table.SCOPE) as proof:
        for work in spec["workloads"]:
            budget.check()
            f=old.native.CountingForward(model)
            prefill=torch.tensor([work["ids"]],device="cuda")
            _,past=f(prefill,use_cache=True,logits_last_only=True)
            decode=torch.tensor([[work["teacher_ids"][0]]],device="cuda")
            _,_=f(decode,past_kv=past,use_cache=True,logits_last_only=True)
            sample_names.extend((work["id"]+"_prefill",work["id"]+"_decode1"))
    assert len(features)==len(sample_names)==8 and proof["head"]["restored"] and proof["body"]["restored"]

    arms={"original":original,"table":candidate}
    rows=[]
    with torch.no_grad():
        for name,x in zip(sample_names,features,strict=True):
            budget.check()
            a,b=original(x),candidate(x)
            finite=bool(torch.isfinite(a).all() and torch.isfinite(b).all())
            mismatch=int((~torch.isclose(a,b,atol=p["atol"],rtol=p["rtol"])).sum())
            argmax=bool(torch.equal(a.argmax(-1),b.argmax(-1)))
            samples={key:[] for key in arms}
            for key in p["order"]:
                operation=arms[key]
                operation(x)
                start,finish=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
                start.record()
                for _ in range(p["block_calls"]):
                    operation(x)
                finish.record()
                finish.synchronize()
                samples[key].append(start.elapsed_time(finish)/p["block_calls"])
            medians={key:statistics.median(value) for key,value in samples.items()}
            row=dict(case=name,outputs=a.numel(),finite=finite,tolerance_failures=mismatch,
                argmax_equal=argmax,event_ms_per_block=samples,median_ms=medians,
                old_over_table=medians["original"]/medians["table"])
            rows.append(row)
            print("P014E_G270_PAIRED",name,mismatch,argmax,row["old_over_table"],flush=True)
    assert old.native.identity.state_fingerprint(model)==p["core_sha256"]
    assert all(io.sha(io.ROOT/name)==digest for name,digest in p["pins"].items())
    valid=all(row["finite"] and row["tolerance_failures"]==0 and row["argmax_equal"] for row in rows)
    io.write(OUT/"terminal.json",dict(complete=True,exit=0 if valid else 8,rows=rows,gpu_entry=entry,
        generation_runs=0,body_forwards_for_activations=8,head_calls_per_block=p["block_calls"],
        same_GPU_process_same_activations=True,scope=p["scope"],profile_sha256=io.sha(PROFILE)))
    return 0 if valid else 8


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","run"))
    if parser.parse_args().action=="prepare":
        prepare()
    else:
        raise SystemExit(run())
