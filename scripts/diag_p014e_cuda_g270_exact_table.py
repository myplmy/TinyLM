"""Benchmark a CUDA five-trit activation table for the frozen g256 output head."""

import argparse
import os
from pathlib import Path
import statistics
import time

from scripts import diag_p014e_group_scale_cuda as previous


io = previous.io
TAG = "p014e_cuda_g270_exact_table_v1_20261118"
OUT = previous.OUT.parent / TAG
PROFILE = OUT / "profile.json"
CASE = "model1_embedding"
N, K, WIDTH, CODE_COUNT = 262144, 256, 52, 243
ORDER = (1, 8, 8, 1)


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
    p = io.read(previous.PROFILE)
    prior = io.read(previous.OUT / "terminal.json")
    assert prior["complete"] and prior["profile_sha256"] == io.sha(previous.PROFILE)
    rows = {str(r["batch"]):r for r in prior["rows"] if r["case"]==CASE and r["fp64"]}
    vectors = {r["operator"].removeprefix("linear_m"):r["vectors"]["path"]
               for r in p["rows"] if r["case"]==CASE}
    asset = p["assets"][1]
    assert set(rows) == set(vectors) == {"1","8"} and not any(r["bit_different"] for r in rows.values())
    pin_paths = (asset,p["activations"],*vectors.values())
    pins = {name:p["pins"][name] for name in pin_paths}
    pins[str(Path(__file__).resolve().relative_to(io.ROOT))] = io.sha(Path(__file__))
    pins[str((previous.OUT / "terminal.json").relative_to(io.ROOT))] = io.sha(previous.OUT / "terminal.json")
    assert all(io.sha(io.ROOT/name)==digest for name,digest in pins.items())
    OUT.mkdir()
    io.write(PROFILE,dict(tag=TAG,pins=pins,asset=asset,activations=p["activations"],vectors=vectors,
        previous_fp64=rows, order=ORDER, warmup=2, repetitions=8, batch_tokens=[1,8],
        cases=[CASE], shape=[N,K], group=K, extra_table_dtype="FP64", old_GPU_calls=0, cap_seconds=150))
    print("P014E_G270_EXACT_TABLE_PREPARED",io.sha(PROFILE),flush=True)


def run():
    import numpy as np
    import torch
    import triton
    import triton.language as tl

    @triton.jit
    def build_table(x, table, K:tl.constexpr, W:tl.constexpr, C:tl.constexpr):
        group, batch = tl.program_id(0), tl.program_id(1)
        code = tl.arange(0,256)
        total = tl.full((256,), 0, tl.float64)
        for place in tl.static_range(5):
            offset = group*5+place
            activation = tl.load(x+batch*K+offset, offset<K, other=0).to(tl.float64)
            trit = code//(3**place)%3-1
            total = total + activation*trit.to(tl.float64)
        tl.store(table+(batch*W+group)*C+code,total,code<C)

    @triton.jit
    def head(codes, scales, table, output, N:tl.constexpr, W:tl.constexpr, C:tl.constexpr):
        row, batch = tl.program_id(0),tl.program_id(1)
        plane = tl.arange(0,64)
        code = tl.load(codes+row*W+plane,plane<W,other=0).to(tl.int32)
        dots = tl.load(table+(batch*W+plane)*C+code,plane<W,other=0)
        scale = tl.load(scales+row).to(tl.float64)
        summed = tl.sum(dots,axis=0) * scale
        tl.store(output+batch*N+row,summed.to(tl.float32))

    p = io.read(PROFILE)
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0" and not (OUT/"terminal.json").exists()
    assert all(io.sha(io.ROOT/name)==digest for name,digest in p["pins"].items())
    assert time.time()+p["cap_seconds"]+30 < previous.device_contract.CUTOFF
    print(f"P014E_G270_TABLE_WORKER pid={os.getpid()}",flush=True)
    entry = previous.device_contract.reserve_device()
    torch.cuda.reset_peak_memory_stats()
    record = torch.load(io.ROOT/p["asset"],map_location="cpu",weights_only=True,mmap=True)["embedding"]
    assert record["codes"].shape == (N,1,WIDTH) and record["scales"].shape == (N,1)
    codes,scales=record["codes"].cuda(),record["scales"].cuda()
    with np.load(io.ROOT/p["activations"],allow_pickle=False) as archive:
        activations = archive[CASE].copy()
    rows = []
    for batch in p["order"]:
        assert not (OUT/"STOP").exists()
        x = torch.from_numpy(activations[:batch]).cuda()
        table = torch.empty((batch,WIDTH,CODE_COUNT),dtype=torch.float64,device="cuda")
        output = torch.empty((batch,N),dtype=torch.float32,device="cuda")
        times=[]
        for index in range(p["warmup"]+p["repetitions"]):
            start,finish = torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
            start.record()
            build_table[(WIDTH,batch)](x,table,K,WIDTH,CODE_COUNT,enable_fp_fusion=False)
            head[(N,batch)](codes,scales,table,output,N,WIDTH,CODE_COUNT,num_warps=2,enable_fp_fusion=False)
            finish.record()
            finish.synchronize()
            if index>=p["warmup"]:
                times.append(start.elapsed_time(finish))
        with np.load(io.ROOT/p["vectors"][str(batch)],allow_pickle=False) as archive:
            expected=archive["actual"]
        observed=output.cpu().numpy()
        differences=int((expected.view(np.uint32)!=observed.view(np.uint32)).sum())
        row=dict(batch=batch, outputs=observed.size, bit_different=differences,
            table_bytes=table.numel()*table.element_size(), cuda_including_table_ms=times,
            median_ms=statistics.median(times),
            previous_fp64_event_ms=p["previous_fp64"][str(batch)]["cuda_event_ms"])
        rows.append(row)
        print("P014E_G270_TABLE",batch,differences,row["median_ms"],flush=True)
    assert all(io.sha(io.ROOT/name)==digest for name,digest in p["pins"].items())
    exact=all(row["bit_different"]==0 for row in rows)
    io.write(OUT/"terminal.json",dict(complete=True,exit=0 if exact else 8,bitwise_exact=exact,
        rows=rows,gpu_entry=entry,old_GPU_calls=0,profile_sha256=io.sha(PROFILE),
        peak_allocated_bytes=torch.cuda.max_memory_allocated()))
    return 0 if exact else 8


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","run"))
    if parser.parse_args().action=="prepare":
        prepare()
    else:
        raise SystemExit(run())
