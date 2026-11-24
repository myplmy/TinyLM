"""Own the two WIP 182 GPU runs and the 17:00 KST authorization boundary."""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test_result/evidence/p109b_firstpass_chat32_scratch_pair_20261120"
POOL = ROOT / "data_cache/ko-en_1069117324_chat32"
PILOT = ROOT / "data_cache/20261120_정제데이터셋1차"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768-chat32.json"
PROBE = ROOT / "test_result/evidence/p109b_gpu_preflight_chat32_v4_20261120/report.json"
POOL_ARGUMENT = "1069.117324M"
POOL_TOKENS = 1069117324
CUTOFF = datetime.fromisoformat("2026-11-20T16:56:00+09:00").timestamp()
CARD_LIMIT_MIB = 12390
STEPS, MICRO, ACCUM, SEQ = 2289, 4, 32, 1024
ARMS = {
    "uniform_r2": "p109b_scratch300_firstpass_chat32_r2_ce_s1337",
    "second_shuffle_r2": "p109b_scratch300_firstpass_chat32_second_shuffle_s1337",
}
EXTRA_SOURCES = (
    "scripts/run_p109b_scratch_pair_20261120.py", "tinylm/data/prepare.py",
    "tinylm/train/trainer.py", "tinylm/train/context_micro_tokens.py",
    "tinylm/train/context_training_state.py",
)


def file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def publish(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))


def gpu_status():
    reading = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=memory.total,memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
        text=True, timeout=8,
    )
    total, used, utilization = map(int, reading.strip().split(","))
    return total, used, utilization


def idle_gpu():
    total, used, _ = gpu_status()
    processes = subprocess.check_output(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"], text=True, timeout=8,
    )
    if processes.strip() or used > 2300 or total < CARD_LIMIT_MIB:
        raise RuntimeError("GPU already has another compute workload or insufficient available memory")
    return total, used


def commands(policy):
    return [
        "train", "--preset", "m100s12_g4", "--arch", "tied", "--data", "ko-en", "--tokens", "300M",
        "--pool-tokens", POOL_ARGUMENT, "--chat32-tokenizer", "--exact-cache", "--seed", "1337",
        "--steps", str(STEPS), "--micro-bs", str(MICRO), "--accum", str(ACCUM), "--seq", str(SEQ),
        "--optimizer", "muon", "--muon-scale", "rms", "--muon-lr-mult", "4",
        "--lr", "1e-3", "--sched", "wsd", "--anneal-end", "0.60", "--decay-frac", "0.2",
        "--train-repeat", "2", "--ce-recompute-rows", "1024", "--no-ckpt",
        "--eval-every", "572", "--save-every", "572", "--tag", ARMS[policy],
    ]


def input_pins():
    from scripts.p109_train_visit_policy import SOURCES
    from tinylm.cli import _tok

    meta = json.loads((POOL / "meta.json").read_bytes())
    if (_tok(POOL_ARGUMENT) != POOL_TOKENS or meta["tokens"] != POOL_TOKENS
            or meta.get("authorization") != "WIP182 matched-pair experiment only" or meta["train"] < 2 * STEPS * MICRO * ACCUM * SEQ
            or meta["tokenizer_sha256"] != file_sha(TOKENIZER).upper()):
        raise ValueError("the authorized chat32 pool or tokenizer changed")
    pins = {name: file_sha(ROOT / name) for name in (*SOURCES, *EXTRA_SOURCES)}
    paths = (POOL / "meta.json", TOKENIZER, *(POOL / f"{split}.bin" for split in ("train", "val")))
    for path in paths:
        pins[str(path.relative_to(ROOT))] = file_sha(path)
    for split in ("train", "val"):
        path = POOL / f"{split}.bin"
        if (not path.samefile(PILOT / path.name)
                or pins[str(path.relative_to(ROOT))] != meta["split_receipts"][split]["sha256"]):
            raise ValueError("the exact cache no longer matches the fixed pilot")
    return pins


def bound_prepare(standard_prepare):
    def prepare(name, count, *args, **kwargs):
        if (name != "ko-en" or count != POOL_TOKENS or not kwargs.get("exact") or not kwargs.get("chat32")
                or any(not (POOL / leaf).is_file() for leaf in ("meta.json", "train.bin", "val.bin"))):
            raise ValueError("refusing cache creation or substitution in the matched experiment")
        result = standard_prepare(name, count, *args, **kwargs)
        if Path(result["dir"]).resolve() != POOL:
            raise ValueError("resolved cache differs from the sealed pilot")
        return result
    return prepare


def initial_hash(model):
    import torch

    digest = hashlib.sha256()
    for name, value in model.state_dict().items():
        digest.update(name.encode())
        digest.update(value.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def worker(policy):
    import torch
    from scripts import p109_train_visit_policy as route
    from tinylm.train import trainer
    from tinylm.train import context_training_state

    profile = json.loads((OUT / "profile.json").read_bytes())
    if profile["pins"] != input_pins() or time.time() >= CUTOFF:
        raise RuntimeError("inputs changed or training authorization window ended")
    total, used = idle_gpu()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable in the authorized execution environment")
    torch.cuda.set_per_process_memory_fraction((CARD_LIMIT_MIB - used - 512) / total)
    arm = OUT / policy
    old_init = route.RoutedG4.__init__
    old_torch_save = torch.save
    old_evaluate = trainer.evaluate

    def observed_init(instance, cfg):
        old_init(instance, cfg)
        publish(arm / "initial.json", {"state_dict_sha256": initial_hash(instance)})

    def common_r2_eval(model, *args, **kwargs):
        with patch.object(model.cfg, "infer_repeat", 2.0):
            return old_evaluate(model, *args, **kwargs)

    def saved_checkpoint(value, destination, *args, **kwargs):
        old_torch_save(value, destination, *args, **kwargs)
        # Keep the normal checkpoint writer and archive only three intermediate model states.
        if not isinstance(value, dict) or value.get("step") not in (572, 1144, 1716) or "model" not in value:
            return
        if not isinstance(destination, (str, os.PathLike)):
            return
        path = Path(destination)
        if path.parent != trainer.CKPT:
            return
        snapshot = arm / f"aoa_step_{value['step']}.pt"
        if snapshot.exists():
            return
        with snapshot.open("xb") as stream:
            old_torch_save({key: value[key] for key in ("model", "cfg", "step", "tokenizer_sha256") if key in value}, stream)

    with (patch.object(route.RoutedG4, "__init__", observed_init),
          patch.object(trainer, "prepare", bound_prepare(trainer.prepare)),
          patch.object(trainer, "evaluate", common_r2_eval), patch.object(torch, "save", saved_checkpoint)):
        receipt = route.run_native(policy, commands(policy))
    if (len(receipt["updates"]) != STEPS or any(not value["optimizer_applied"] for value in receipt["updates"])
            or receipt["layer_token_visits"] != STEPS * MICRO * ACCUM * SEQ * 28):
        raise RuntimeError("a training update or equal visit accounting is incomplete")
    receipt.update(peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                   peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
    publish(arm / "worker.json", receipt)


def supervise(policy, telemetry):
    arm = OUT / policy
    arm.mkdir(exist_ok=False)
    before = time.time()
    peak = 0
    reasons = []
    with (arm / "stdout.txt").open("x", encoding="utf-8") as log:
        child = subprocess.Popen([sys.executable, "-B", "-u", "-m", "scripts.run_p109b_scratch_pair_20261120",
                                  "worker", policy], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                instant = time.time()
                if instant >= CUTOFF:
                    reasons.append("TRAINING_CUTOFF")
                    break
                _, used, utilization = gpu_status()
                peak = max(used, peak)
                telemetry.write(f"{instant:.3f},{policy},{child.pid},{used},{utilization}{chr(10)}")
                telemetry.flush()
                if used > CARD_LIMIT_MIB:
                    reasons.append("CARD_MEMORY_LIMIT")
                    break
                time.sleep(2)
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
            code = child.wait()
    report = dict(policy=policy, tag=ARMS[policy], pid=child.pid, started=before, ended=time.time(),
                  returncode=code, peak_card_mib=peak, stop_reasons=reasons)
    publish(arm / "supervisor.json", report)
    return report


def queue():
    probe = json.loads(PROBE.read_bytes())
    if probe["route"] != [28] * 4 or probe["reserved_mib"] + probe["background_mib"] + 512 >= CARD_LIMIT_MIB:
        raise ValueError("GPU memory preflight did not pass")
    if time.time() + 2 * STEPS * probe["median_after_first_ms"] / 1000 + 420 >= CUTOFF:
        raise TimeoutError("the observed training rate does not fit two full arms")
    idle_gpu()
    pins = input_pins()
    OUT.mkdir(exist_ok=False)
    publish(OUT / "profile.json", {"pins": pins, "commands": {arm: commands(arm) for arm in ARMS},
                                    "approval": "WIP 182", "cutoff": CUTOFF, "probe_sha256": file_sha(PROBE)})
    results = []
    with (OUT / "device.csv").open("x", encoding="utf-8") as samples:
        samples.write("epoch,policy,worker_pid,card_used_mib,utilization" + chr(10))
        for policy in ARMS:
            print("START", policy, flush=True)
            result = supervise(policy, samples)
            results.append(result)
            print("TERMINAL", result, flush=True)
            if result["returncode"] != 0:
                break
    complete = len(results) == len(ARMS) and all(not result["returncode"] for result in results)
    if complete:
        initials = [json.loads((OUT / arm / "initial.json").read_bytes()) for arm in ARMS]
        complete = initials[0] == initials[1] and pins == input_pins()
    publish(OUT / "queue.json", {"complete": complete, "arms": results})
    if not complete:
        raise RuntimeError("the matched experiment has no certified paired result")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("queue", "worker"))
    parser.add_argument("policy", choices=tuple(ARMS), nargs="?")
    args = parser.parse_args()
    if args.phase == "queue":
        queue()
    elif args.policy:
        worker(args.policy)
    else:
        parser.error("worker requires a policy")
