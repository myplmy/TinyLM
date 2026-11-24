"""Sample physical GPU memory for three already evaluated local HF models."""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
import os
import resource
import subprocess
import sys
import time

from scripts import diag_p013_native_matched_training as io
from scripts import diag_p106b_hf_resources as hf
from scripts.diag_p014e_native_sampled_memory import samples
from scripts.p106b_nvml_probe import NvmlClient


TAG = "p106b_hf_sampled_generation_v1_20261118"
OUT = io.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
PREVIOUS = io.ROOT / "test_result/evidence" / hf.TAG
MODELS = ("falcon90m", "gemma270", "qwen06")
WORKLOADS = ("en128", "en512")
CAP, DECODE, REPEATS = 120, 8, 4
SOURCES = (
    "scripts/diag_p106b_hf_sampled_memory.py", "scripts/diag_p106b_hf_resources.py",
    "scripts/diag_p106b_external_core6.py", "scripts/diag_p106b_official_core6.py",
    "scripts/diag_p106b_resource_matrix.py", "scripts/prepare_p106b_official_eval.py",
    "scripts/diag_p013_native_matched_training.py", "scripts/diag_p014e_native_sampled_memory.py",
    "scripts/p106b_nvml_probe.py", "scripts/interactive_research_infer.py",
)


def pins():
    return {name: io.digest(io.ROOT / name) for name in SOURCES}


def read(path):
    return json.loads(path.read_bytes())


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
    locked = {}
    for model in MODELS:
        path = PREVIOUS / (model + "_cuda") / "report.json"
        prior = read(path)
        assert prior["status"] == "HF_RESOURCE_LANE_COMPLETE_NOT_QUALITY" and prior["returncode"] == 0
        assert prior["model"] == model and prior["device"] == "cuda" and prior["originals_unchanged"]
        assert prior["torch_version"] == version("torch")
        proven = prior["model_proof"]["strict_loader"]
        assert proven["initial_core_sha256"] == proven["final_core_sha256"]
        cases = {}
        for name in WORKLOADS:
            records = [row for row in prior["records"] if row["workload"] == name]
            answer = records[0]["unobserved"]["generated_ids"][:DECODE]
            assert len(records) == 4 and len(answer) == DECODE
            assert all(row["unobserved"]["generated_ids"][:DECODE] == answer for row in records)
            cases[name] = dict(ids=records[0]["prompt_ids"], expected=answer)
        locked[model] = dict(report=str(path.relative_to(io.ROOT)), report_sha256=io.digest(path),
            core=proven["initial_core_sha256"], assets=prior["assets"], model_source=prior["validation_model_source_sha256"],
            cases=cases)
    OUT.mkdir()
    io.write(PROFILE, dict(tag=TAG, python=sys.executable, sources=pins(), model_order=MODELS, models=locked,
        torch=version("torch"), transformers=version("transformers"), decode=DECODE, repeats=REPEATS,
        device_metric="persistent NVML device-wide samples; no continuous exact maximum",
        new_evaluated_questions=0, checkpoints=0, training_updates=0))
    print("HF_SAMPLED_READY", io.digest(PROFILE), flush=True)


def verify():
    p = read(PROFILE)
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0" and p["sources"] == pins()
    assert p["python"] == sys.executable and p["model_order"] == list(MODELS)
    assert p["torch"] == version("torch") and p["transformers"] == version("transformers")
    return p


def measure(torch, lm, case, budget):
    body = lm.model
    budget.check()
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    before = torch.cuda.memory_allocated()
    since = time.monotonic_ns()
    result = hf.generate(body, lm.tokenizer, case["ids"], "cuda", DECODE, False, budget, False)
    until = time.monotonic_ns()
    return dict(start_ns=since, end_ns=until, prompt_tokens=len(case["ids"]), new_tokens=result["generated_tokens"],
        agrees=result["generated_ids"] == case["expected"],
        returned_cache_bytes=result["returned_cache"]["unique_storage_bytes"],
        before_allocated_bytes=before, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_reserved_bytes=torch.cuda.max_memory_reserved())


def worker(model):
    import torch

    p = verify()
    frozen = p["models"][model]
    assert io.digest(io.ROOT / frozen["report"]) == frozen["report_sha256"]
    entry = io.reserve_device()
    budget = hf.common.Budget(CAP - 15, datetime.fromtimestamp(io.CUTOFF - 18, tz=timezone.utc))
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    print("HF_SAMPLED_WORKER", model, "pid="+str(os.getpid()), flush=True)
    assets = hf.assets_for(model)
    assert assets == frozen["assets"]
    started = time.monotonic_ns()
    proof, workloads = {}, []
    with hf.runtime(model, torch, assets, proof) as lm:
        strict = proof["strict_loader"]
        assert strict["initial_core_sha256"] == frozen["core"]
        assert strict["model_source_sha256"] == frozen["model_source"]
        loaded = time.monotonic_ns()
        for name in WORKLOADS:
            for rep in range(REPEATS):
                if (OUT / "STOP").exists():
                    raise TimeoutError("owned STOP")
                row = measure(torch, lm, frozen["cases"][name], budget)
                workloads.append(dict(workload=name, rep=rep, **row))
            print("HF_SAMPLED_GENERATION", model, name, REPEATS, flush=True)
        storage = hf.common.model_storage(lm.model)
    assert strict["final_core_sha256"] == frozen["core"] and strict["source_assets_unchanged"]
    io.write(OUT / f"{model}.json", dict(model=model, entry=entry, model_storage=storage,
        process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        workloads=workloads, load=[started, loaded], exit=0, profile_sha256=io.digest(PROFILE),
        originals_unchanged=True))


def run():
    verify()
    assert time.time() + len(MODELS) * (CAP + 22) + 40 < io.CUTOFF
    client = NvmlClient(timeout=3)
    rows = []
    try:
        for model in MODELS:
            if (OUT / "STOP").exists():
                break
            entry = io.reserve_device()
            idle = [samples(client) for _ in range(7)]
            observed = []
            command = ["timeout", "--signal=INT", "--kill-after=12s", f"{CAP}s", sys.executable,
                "-B", "-u", "-m", "scripts.diag_p106b_hf_sampled_memory", "worker", model]
            with subprocess.Popen(command, cwd=io.ROOT) as child:
                while child.poll() is None:
                    try:
                        observed.append(samples(client))
                    except (RuntimeError, TimeoutError, ValueError, OSError):
                        break
                    time.sleep(.025)
                rc = child.wait()
            release = io.reserve_device()
            io.write(OUT / f"{model}_nvml.json", dict(idle=idle, samples=observed, entry=entry, release=release))
            rows.append(dict(model=model, exit=rc, samples=len(observed)))
            print("HF_SAMPLED_TERMINAL", model, rc, len(observed), flush=True)
    finally:
        health = client.close()
        complete = len(rows) == len(MODELS) and not health["query_errors"] and all(
            row["exit"] == 0 and row["samples"] >= 20 for row in rows)
        io.write(OUT / "terminal.json", dict(complete=complete, exit=0 if complete else 8,
            rows=rows, client=health, profile_sha256=io.digest(PROFILE), new_evaluated_questions=0))
    return 0 if complete else 8


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "worker"))
    parser.add_argument("model", nargs="?", choices=MODELS)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "worker":
        worker(args.model)
    else:
        raise SystemExit(run())
