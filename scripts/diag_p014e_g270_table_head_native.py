"""Run the saved native G270 probes with an exact-table CUDA output head."""

import argparse
import os
from pathlib import Path
import statistics
import time

from scripts import diag_p014e_cuda_g270_exact_table as table_test


TAG = "p014e_g270_table_head_native_v1_20261118"
io = table_test.io
OUT = table_test.OUT.parent / TAG
PROFILE = OUT / "profile.json"
BASE = io.OLD / "decode_native_v1"
SCOPE = "HEAD_AND_DECODE64"
SECONDS = 150


class Budget:
    def __init__(self):
        self.end = time.monotonic()+SECONDS

    def check(self):
        if time.monotonic() >= self.end or (OUT / "STOP").exists():
            raise TimeoutError("P014E native table budget or owned STOP")


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
    old = io.read(BASE/"profile.json")
    table_result = io.read(table_test.OUT/"terminal.json")
    assert table_result["complete"] and table_result["bitwise_exact"]
    model, = [m for m in old["models"] if m["id"]=="student_g270_vocab"]
    result_path = BASE/"actual/student_g270_vocab/report.json"
    result = io.read(result_path)
    assert result["numeric_failures"]==0 and result["argmax_mismatches"]==0
    assert result["physical_state_unchanged"] and result["model_released"]
    numeric = {row["workload"]:row["actual_packet"] for row in result["numeric"] if row["arm"]==SCOPE}
    timings = {row["workload"]:row["head_decode64_median_seconds"] for row in result["timing"]}
    pins = {model["payload"]:model["payload_sha256"],model["tokenizer"]["path"]:model["tokenizer"]["sha256"]}
    pins.update({row["path"]:row["sha256"] for row in numeric.values()})
    for name in (*old["sources"], "scripts/diag_p014e_g270_table_head_native.py",
                 "scripts/diag_p014e_cuda_g270_exact_table.py",
                 str((table_test.OUT/"terminal.json").relative_to(io.ROOT)),
                 str((BASE/"profile.json").relative_to(io.ROOT)),str(result_path.relative_to(io.ROOT))):
        pins[name] = io.sha(io.ROOT / name)
    assert all(io.sha(io.ROOT/name)==digest for name,digest in pins.items())
    OUT.mkdir()
    io.write(PROFILE,dict(tag=TAG,model=model,same_body_policy=old["body_policy"],pins=pins,
        numeric=numeric,original_timings=timings,original_core_sha256=result["initial_state_sha256"],
        atol=old["linear_atol"],rtol=old["linear_rtol"],seconds=SECONDS,warmup=1,measured=3,
        fixed_new_tokens=16, existing_arm_reexecuted=False, model_loads=0,gpu_calls=0))
    print("P014E_G270_TABLE_NATIVE_PREPARED",io.sha(PROFILE),flush=True)


def table_head(original):
    import torch
    import triton
    import triton.language as tl

    # The corresponding kernels are frozen in the standalone numeric result.
    @triton.jit
    def make_table(x, table, K:tl.constexpr, W:tl.constexpr, C:tl.constexpr):
        group, batch = tl.program_id(0),tl.program_id(1)
        code = tl.arange(0,256)
        total = tl.full((256,),0,tl.float64)
        for place in tl.static_range(5):
            offset = group*5+place
            activation = tl.load(x+batch*K+offset,offset<K,other=0).to(tl.float64)
            trit = code//(3**place)%3-1
            total = total+activation*trit.to(tl.float64)
        tl.store(table+(batch*W+group)*C+code,total,code<C)

    @triton.jit
    def project(codes, scales, table, output, N:tl.constexpr, W:tl.constexpr, C:tl.constexpr):
        row, batch = tl.program_id(0),tl.program_id(1)
        plane = tl.arange(0,64)
        code = tl.load(codes+row*W+plane,plane<W,other=0).to(tl.int32)
        dots = tl.load(table+(batch*W+plane)*C+code,plane<W,other=0)
        scale = tl.load(scales+row).to(tl.float64)
        summed = tl.sum(dots,axis=0)*scale
        tl.store(output+batch*N+row,summed.to(tl.float32))

    class ExactHead:
        packed_codes = original.packed_codes
        group_scales = original.group_scales
        lookup = staticmethod(original.lookup)

        def __call__(self, x):
            n,k,w,c = table_test.N,table_test.K,table_test.WIDTH,table_test.CODE_COUNT
            assert x.is_cuda and x.dtype==torch.float32 and x.numel()==k and x.shape[-1]==k
            x = x.contiguous()
            table = torch.empty((w,c),dtype=torch.float64,device=x.device)
            output = torch.empty((*x.shape[:-1],n),dtype=x.dtype,device=x.device)
            make_table[(w,1)](x,table,k,w,c,enable_fp_fusion=False)
            project[(n,1)](self.packed_codes,self.group_scales,table,output,n,w,c,
                            num_warps=2,enable_fp_fusion=False)
            return output

    return ExactHead()


def numeric(model, work, p, budget, native):
    import numpy as np
    import torch

    f = native.CountingForward(model)
    packet = p["numeric"][work["id"]]
    with np.load(io.ROOT/packet["path"],allow_pickle=False) as archive:
        reference = archive["actual"]
    token = torch.tensor([work["ids"]],device="cuda")
    past = None
    rows = []
    for index in range(len(reference)):
        budget.check()
        logits,past = f(token,past_kv=past,use_cache=True,logits_last_only=True)
        a,b = logits.cpu().numpy(),reference[index]
        assert a.shape == b.shape and np.isfinite(a).all()
        delta = np.abs(a.astype(np.float64)-b)
        rows.append(dict(step=index,outputs=a.size,bit_mismatch=int((a.view(np.uint32)!=b.view(np.uint32)).sum()),
            numeric_failures=int((~np.isclose(a,b,rtol=p["rtol"],atol=p["atol"])).sum()),
            argmax_equal=bool(np.array_equal(a.argmax(-1),b.argmax(-1))),max_abs=float(delta.max())))
        token = torch.tensor([[work["teacher_ids"][index]]],device="cuda")
    return rows


def run():
    import torch
    from tokenizers import Tokenizer
    from scripts import diag_p014e_decode_native as old

    p = io.read(PROFILE)
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    assert all(io.sha(io.ROOT/name)==digest for name,digest in p["pins"].items())
    assert time.time()+SECONDS+30 < table_test.previous.device_contract.CUTOFF
    print(f"P014E_G270_NATIVE_WORKER pid={os.getpid()}",flush=True)
    entry = table_test.previous.device_contract.reserve_device()
    budget = Budget()
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    spec = p["model"]
    payload = old.owner.load(io.ROOT/spec["payload"])
    model = old.owner.direct.reference.load_payload(payload,device="cuda",tile_rows=4096)
    direct, body = old.operators(model,payload)
    tok = Tokenizer.from_file(str(io.ROOT/spec["tokenizer"]["path"]))
    assert old.native.identity.state_fingerprint(model)==p["original_core_sha256"]
    results = []
    with torch.no_grad(), old.route(model,table_head(direct),body,SCOPE) as proof:
        for work in spec["workloads"]:
            observed = numeric(model,work,p,budget,old.native)
            seen = [old.native.generation(model,model.cfg,tok,work["ids"],p["fixed_new_tokens"],
                        spec["eos_id"],False,False,budget) for _ in range(p["warmup"]+p["measured"])]
            same = all(row["generated_ids"]==work["old_generated_ids"] and row["metadata"]==work["old_metadata"]
                       for row in seen)
            timing = seen[p["warmup"]:]
            result = dict(work=work["id"],observed=observed,same_ids_and_metadata=same,
                fresh_median_seconds=statistics.median(row["seconds"] for row in timing),
                fresh_peak_allocated_bytes=max(row["peak_allocated_bytes"] for row in timing),
                prior_median_seconds=p["original_timings"][work["id"]], samples=timing)
            results.append(result)
            print("P014E_G270_NATIVE",work["id"],same,result["fresh_median_seconds"],flush=True)
    exact = all(r["same_ids_and_metadata"] and
                all(x["numeric_failures"]==0 and x["argmax_equal"] for x in r["observed"]) for r in results)
    assert all(io.sha(io.ROOT/name)==digest for name,digest in p["pins"].items())
    io.write(OUT/"terminal.json",dict(complete=True,exit=0 if exact else 8,
        rows=results,restore_proof=proof,gpu_entry=entry,rerun_baseline_GPU_calls=0,model_loads=1,
        passed_original_tolerance_and_ids=exact,profile_sha256=io.sha(PROFILE)))
    return 0 if exact else 8


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","run"))
    if parser.parse_args().action=="prepare":
        prepare()
    else:
        raise SystemExit(run())
