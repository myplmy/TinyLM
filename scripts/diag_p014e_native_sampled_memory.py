"""Measure device-wide sampled VRAM and exact allocator/storage for packed inference."""

import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

from scripts import diag_p013_native_matched_training as gpu
from scripts import diag_p014e_stored_dot_error as io
from scripts.p106b_nvml_probe import NvmlClient


TAG = "p014e_native_packed_sampled_vram_v1_20261118"
OUT = gpu.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
BASE = io.OLD / "decode_native_v1"
MODE = "HEAD_AND_DECODE64"
MODELS = ("native32k", "student_g270_vocab")
INPUTS = ("ko128", "ko512")
REPEATS = 4
SAMPLE_SECONDS = 0.025
WORKER_SECONDS = 105


def read(path):
    return json.loads(path.read_bytes())


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
    previous = read(BASE / "profile.json")
    paths = dict(previous["sources"])
    references = [BASE / "profile.json", Path(__file__),
                  gpu.ROOT / "scripts/p106b_nvml_probe.py", gpu.ROOT / "scripts/diag_p106b_resource_matrix.py",
                  gpu.ROOT / "scripts/diag_p013_native_matched_training.py",
                  gpu.ROOT / "scripts/diag_p014e_stored_dot_error.py"]
    models = {}
    for model_id in MODELS:
        model, = [m for m in previous["models"] if m["id"] == model_id]
        closed = BASE / f"actual/{model_id}/report.json"
        z = read(closed)
        assert z["physical_state_unchanged"] and z["model_released"]
        specs = {row["workload"]: row["actual_packet"] for row in z["numeric"]
                 if row["arm"] == MODE and row["workload"] in INPUTS}
        works = [w for w in model["workloads"] if w["id"] in INPUTS]
        assert len(specs) == len(works) == 2
        for each in specs.values():
            paths[each["path"]] = each["sha256"]
        paths[model["payload"]] = model["payload_sha256"]
        references.append(closed)
        models[model_id] = dict(payload=model["payload"], expected_state=z["initial_state_sha256"],
            works=works, reference=specs, vocab=model["expected_vocab"])
    paths.update({str(p.resolve().relative_to(gpu.ROOT)): gpu.digest(p) for p in references})
    assert all(gpu.digest(gpu.ROOT / name) == digest for name,digest in paths.items())
    OUT.mkdir()
    gpu.write(PROFILE, dict(tag=TAG, models=models, pins=paths, mode=MODE,
        repeats=REPEATS, sample_seconds=SAMPLE_SECONDS, worker_seconds=WORKER_SECONDS,
        arithmetic="FP32_MATH_TF32_OFF", logical_steps=["prefill", "first_fixed_token"],
        disk_budget_bytes=20_000_000, GPU_measurement_scope="DEVICE_WIDE_NVML_SAMPLED_NOT_PER_PID",
        training_updates=0, official_eval_rows=0))
    print("P014E_SAMPLED_VRAM_PREPARED", gpu.digest(PROFILE), flush=True)


def verify():
    p = read(PROFILE)
    assert p["tag"] == TAG and p["mode"] == MODE and set(p["models"]) == set(MODELS)
    assert p["repeats"] == REPEATS and p["sample_seconds"] == SAMPLE_SECONDS
    assert all(gpu.digest(gpu.ROOT / name) == digest for name,digest in p["pins"].items())
    return p


def worker(model_id):
    import numpy as np
    import torch
    from scripts import diag_p014e_decode_native as closed
    from scripts import diag_p106b_resource_matrix as stats

    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0" and not (OUT / "STOP").exists()
    p = verify()
    spec = p["models"][model_id]
    entry = gpu.reserve_device()
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    phases = []

    def measured(label, call):
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        start = time.monotonic_ns()
        value = call()
        torch.cuda.synchronize()
        end = time.monotonic_ns()
        row = dict(phase=label, start_ns=start, end_ns=end, elapsed_seconds=(end-start)/1e9,
            allocated_peak=torch.cuda.max_memory_allocated(), reserved_peak=torch.cuda.max_memory_reserved(),
            live_allocated_end=torch.cuda.memory_allocated())
        phases.append(row)
        return value

    print(f"P014E_SAMPLED_VRAM_WORKER {model_id} pid={os.getpid()}", flush=True)
    path = gpu.ROOT / spec["payload"]
    payload = closed.owner.load(path)
    model = measured("cuda_model_load",
        lambda: closed.owner.direct.reference.load_payload(payload,device="cuda",tile_rows=4096))
    table,body = closed.operators(model,payload)
    model_stat = stats.model_storage(model)
    assert closed.native.identity.state_fingerprint(model) == spec["expected_state"]
    results = []
    with torch.no_grad(), closed.route(model,table,body,MODE) as restore:
        fwd = closed.native.CountingForward(model)
        for work in spec["works"]:
            saved = spec["reference"][work["id"]]
            with np.load(gpu.ROOT/saved["path"],allow_pickle=False) as archive:
                reference = archive["actual"][:2].copy()
            tokens = torch.tensor([work["ids"]],device="cuda")
            continuation = torch.tensor([[work["teacher_ids"][0]]],device="cuda")
            for rep in range(REPEATS):
                assert not (OUT/"STOP").exists()
                prefix = f"{work['id']}/{rep}"
                first,kv = measured(prefix+"/prefill",lambda:fwd(tokens,use_cache=True,logits_last_only=True))
                second,next_kv = measured(prefix+"/decode1",
                    lambda:fwd(continuation,past_kv=kv,use_cache=True,logits_last_only=True))
                exact = all(np.array_equal(tensor.cpu().numpy().view(np.uint32),target.view(np.uint32))
                            for tensor,target in zip((first,second),reference,strict=True))
                row = dict(case=work["id"],repeat=rep,shape=list(second.shape),bit_exact=exact,
                    prefix_bytes=stats.storage_audit(("kv",v) for v in stats.nested_tensors(kv))["unique_storage_bytes"],
                    returned_bytes=stats.storage_audit(("kv",v) for v in stats.nested_tensors(next_kv))["unique_storage_bytes"],
                    joint_bytes=stats.storage_audit(
                        ("kv",v) for v in stats.nested_tensors([kv,next_kv]))["unique_storage_bytes"])
                results.append(row)
                del first,second,kv,next_kv
            print("P014E_SAMPLED_PHASE",model_id,work["id"],REPEATS,flush=True)
    assert restore["head"]["restored"] and restore["body"]["restored"]
    assert gpu.digest(path) == p["pins"][spec["payload"]]
    correct = all(row["bit_exact"] for row in results)
    gpu.write(OUT / f"{model_id}.json",dict(model=model_id,profile_sha256=gpu.digest(PROFILE),
        asset=str(path.relative_to(gpu.ROOT)),asset_bytes=path.stat().st_size,device=entry,
        model_storage=model_stat,worker_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        phases=phases,requests=results,restore=restore,exit=0 if correct else 8))
    return 0 if correct else 8


def samples(client):
    start = time.monotonic_ns()
    data = client.memory()
    end = time.monotonic_ns()
    return dict(start_ns=start,end_ns=end,**data)


def run():
    p = verify()
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    assert time.time()+2*(WORKER_SECONDS+24)+40 < gpu.CUTOFF
    assert not (OUT/"terminal.json").exists()
    client = NvmlClient(timeout=3)
    rows = []
    try:
        for model in MODELS:
            if (OUT/"STOP").exists():
                break
            entry = gpu.reserve_device()
            idle = [samples(client) for _ in range(7)]
            command = ["timeout","--signal=INT","--kill-after=12s",f"{WORKER_SECONDS}s",
                       sys.executable,"-B","-u","-m","scripts.diag_p014e_native_sampled_memory","worker",model]
            observed = []
            with subprocess.Popen(command,cwd=gpu.ROOT) as process:
                while process.poll() is None:
                    try:
                        observed.append(samples(client))
                    except (RuntimeError,TimeoutError,ValueError,OSError):
                        break
                    time.sleep(SAMPLE_SECONDS)
                exit_code = process.wait()
            release = gpu.reserve_device()
            samples_path = OUT / f"{model}_nvml.json"
            gpu.write(samples_path,dict(idle=idle,samples=observed,entry=entry,release=release,
                      measurement="device-wide NVML samples; timestamps bracket each query"))
            rows.append(dict(model=model,exit=exit_code,samples=len(observed),trace=str(samples_path.relative_to(gpu.ROOT))))
            print("P014E_SAMPLED_TERMINAL",model,exit_code,len(observed),flush=True)
    finally:
        metrics = client.close()
        complete = len(rows)==len(MODELS) and not metrics["query_errors"] and all(
            r["exit"]==0 and r["samples"]>=20 for r in rows)
        gpu.write(OUT/"terminal.json",dict(complete=complete,exit=0 if complete else 8,rows=rows,client=metrics,
            pid=os.getpid(),profile_sha256=gpu.digest(PROFILE),multiple_gpu_models_live=0,timing_claim=False))
    return 0 if complete else 8


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","run","worker"))
    parser.add_argument("model",nargs="?",choices=MODELS)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "run":
        raise SystemExit(run())
    else:
        raise SystemExit(worker(args.model))
