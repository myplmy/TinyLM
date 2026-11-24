"""Check two CUDA packed-group reductions against frozen CPU vectors."""

import argparse
import os
import time

from scripts import diag_p014e_stored_dot_error as io
from scripts import diag_p013_native_matched_training as device_contract


TAG = "p014e_cuda_group_scale_numeric_v1_20261118"
OUT = io.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
SELECT = ("model0_matrix002", "model1_matrix000", "model1_embedding")
ASSETS = (io.PACKED, "runs/deploy/p014e_g270_large_vocab_v2_20261027/ternary5_existing_twn.pt")


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
    prior = io.read(io.OLD / "profile.json")
    old = io.read(io.OLD / "cpu_v1/profile.json")
    cases = {row["id"]: row for row in old["cases"] if row["id"] in SELECT}
    rows = [row for row in io.read(io.OLD / "cpu_v1/actual/report.json")["rows"]
            if row["case"] in cases and row["operator"].startswith("linear_m")]
    assert len(rows) == 6
    specs = [old["activations"], *(row["vectors"] for row in rows)]
    pins = {path: prior["inputs"][path]["sha256"] for path in ASSETS}
    pins.update({spec["path"]: spec["sha256"] for spec in specs})
    name = "scripts/diag_p014e_group_scale_cuda.py"
    pins[name] = io.sha(io.ROOT / name)
    assert all(io.sha(io.ROOT / name) == digest for name,digest in pins.items())
    OUT.mkdir()
    io.write(PROFILE, dict(tag=TAG, cases=cases, rows=rows, pins=pins, assets=ASSETS,
        activations=old["activations"]["path"], rtol=old["linear_rtol"], atol=old["linear_atol"],
        prior_model_forwards=0, prior_kernel_execution=0, model_loads=0,
        gpu_calls=0, candidates=("group_FP32", "group_FP64"), cap_seconds=150))
    print("P014E_GROUP_CUDA_PREPARED", io.sha(PROFILE), flush=True)


def run():
    import numpy as np
    import torch
    import triton
    import triton.language as tl

    @triton.jit
    def group_scale(x, codes, scales, y, N:tl.constexpr, K:tl.constexpr, G:tl.constexpr,
                    NG:tl.constexpr, BLOCK_GROUPS:tl.constexpr, FP64:tl.constexpr):
        row, batch = tl.program_id(0), tl.program_id(1)
        packed_width:tl.constexpr = (G+4)//5
        group = tl.arange(0, BLOCK_GROUPS)
        position = tl.arange(0, G)
        raw = tl.load(codes + (row*NG+group[:,None])*packed_width + position[None,:]//5,
                      group[:,None] < NG, other=0).to(tl.int32)
        place = position % 5
        power = tl.where(place==0, 1, tl.where(place==1, 3, tl.where(place==2, 9, tl.where(place==3, 27, 81))))
        trit = raw // power[None,:] % 3 - 1
        values = tl.load(x + batch*K + group[:,None]*G + position[None,:], group[:,None] < NG, other=0)
        precision:tl.constexpr = tl.float64 if FP64 else tl.float32
        dot = tl.sum(values.to(precision) * trit.to(precision), axis=1)
        scaling = tl.load(scales + row*NG + group, group < NG, other=0)
        total = tl.sum(dot * scaling.to(precision), axis=0)
        tl.store(y + batch*N + row, total.to(tl.float32))

    p = io.read(PROFILE)
    assert all(io.sha(io.ROOT / name) == digest for name,digest in p["pins"].items())
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0" and not (OUT / "terminal.json").exists()
    assert time.time() + p["cap_seconds"] + 30 < device_contract.CUTOFF
    assert not (OUT / "STOP").exists()
    print(f"P014E_GROUP_CUDA_WORKER pid={os.getpid()}", flush=True)
    entry = device_contract.reserve_device()
    torch.cuda.reset_peak_memory_stats()
    results = []
    with np.load(io.ROOT / p["activations"], allow_pickle=False) as activations:
        for name, case in p["cases"].items():
            assert not (OUT / "STOP").exists()
            payload = torch.load(io.ROOT / p["assets"][case["model_index"]], map_location="cpu", mmap=True, weights_only=True)
            key = case["record_id"]
            record = payload["embedding"] if key=="embedding" else payload["matrices"][int(key.removeprefix("matrix"))]["weight"]
            codes, scales = record["codes"].cuda(),record["scales"].cuda()
            n, k, g = (case["signature"][key] for key in ("out_features","in_features","group"))
            assert k % g == 0 and tuple(codes.shape) == (n,k//g,(g+4)//5)
            for previous in (row for row in p["rows"] if row["case"] == name):
                batch = int(previous["operator"].removeprefix("linear_m"))
                x = torch.from_numpy(activations[name][:batch].copy()).cuda()
                output = torch.empty((batch,n), device="cuda", dtype=torch.float32)
                with np.load(io.ROOT / previous["vectors"]["path"], allow_pickle=False) as saved:
                    old_c, old_ref = saved["actual"], saved["reference"]
                old_gate = ~np.isclose(old_c,old_ref,rtol=p["rtol"],atol=p["atol"])
                for wide in (False, True):
                    elapsed = []
                    for iteration in range(3):
                        begin,end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
                        begin.record()
                        group_scale[(n,batch)](x,codes,scales,output,n,k,g,k//g,triton.next_power_of_2(k//g),wide)
                        end.record()
                        end.synchronize()
                        if iteration:
                            elapsed.append(begin.elapsed_time(end))
                    y = output.cpu().numpy()
                    assert np.isfinite(y).all()
                    gate = ~np.isclose(y,old_ref,rtol=p["rtol"],atol=p["atol"])
                    row = dict(case=name, batch=batch, outputs=y.size, fp64=wide,
                        bit_different=int((y.view(np.uint32)!=old_c.view(np.uint32)).sum()),
                        max_abs=float(np.abs(y.astype(np.float64)-old_c).max()),
                        old_FP32_gate_failures=int(old_gate.sum()), current_FP32_gate_failures=int(gate.sum()),
                        same_gate_coordinates=bool(np.array_equal(old_gate,gate)), cuda_event_ms=elapsed)
                    results.append(row)
                    print("P014E_GROUP_CUDA", name, batch, wide, row["bit_different"],row["current_FP32_gate_failures"],flush=True)
    assert len(results) == 12
    io.write(OUT / "terminal.json", dict(complete=True, exit=0, rows=results, gpu_entry=entry,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(), prior_kernel_executions=0,
        GPU_model_calls=0, profile_sha256=io.sha(PROFILE)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    if parser.parse_args().action == "prepare":
        prepare()
    else:
        run()
