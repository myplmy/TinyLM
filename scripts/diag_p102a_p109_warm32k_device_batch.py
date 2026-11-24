"""Compare 32K G4 operating batches from the same trained P079 weights."""

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
from unittest.mock import patch

import torch

from scripts import diag_p102a_g4_joint_ce_kl_batch8 as sampler
from scripts import diag_p102a_g4_recompute_operating as operating
from scripts import diag_p109_frozen_g4_routes as frozen
from scripts.diag_p102a_g4_full_delta_train import state_sha


ROOT, PARENT, CUTOFF = frozen.ROOT, frozen.prior.PARENT, frozen.prior.CUTOFF
read, write, sha = sampler.read, sampler.write, sampler.sha
TAG = "p102a_p109_warm32k_device_batch_v1_20261119"
OUT = operating.OUT.with_name(TAG)
STEPS, SEQ, ROWS, CAP = 6, 1024, 1024, 100
LAYOUTS = {"micro8": (8, 16), "micro32": (32, 4), "micro64": (64, 2)}
TARGETS_PER_UPDATE = 131072
SOURCE_FILES = (*operating.BASE.SOURCES, "tinylm/train/recomputed_ce.py",
                "tinylm/train/context_training_state.py", "scripts/diag_p102a_g4_recompute_operating.py",
                "scripts/diag_p102a_g4_joint_ce_kl_batch8.py", "scripts/diag_p109_frozen_g4_routes.py",
                "scripts/diag_p109_warm_visit_routes.py", "scripts/diag_p102a_g4_full_delta_train.py",
                "scripts/diag_p102a_p109_warm32k_device_batch.py")


def arguments(name):
    micro, accum = LAYOUTS[name]
    args = operating.argv_for("continuous")
    index = args.index("--context-curriculum")
    del args[index:index+2]
    values = {"--tag": f"{TAG}_{name}", "--micro-bs": str(micro), "--accum": str(accum), "--lr": "3e-5",
              "--sched": "decay", "--eval-every": str(STEPS), "--save-every": "0"}
    for flag, value in values.items():
        args[args.index(flag) + 1] = value
    return args


def pins():
    return {name: sha(ROOT / name) for name in SOURCE_FILES}


def draw_receipt(micro, accum):
    from tinylm.data import Loader

    loader = Loader("train", micro, SEQ, "cpu", operating.CACHE, seed=1234)
    receipts = []
    for _ in range(STEPS):
        x, y = zip(*(loader() for _ in range(accum)), strict=True)
        tokens, labels = torch.cat(x), torch.cat(y)
        assert tokens.numel() == labels.numel() == TARGETS_PER_UPDATE
        receipts.append(state_sha((tokens, labels)))
    return dict(draws=receipts, rng=loader.rng.bit_generator.state)


def prepare():
    from tinylm import cli
    import tinylm.train as package
    from tinylm.train.context_training_state import cache_identity

    assert sha(PARENT) == frozen.PARENT_SHA
    meta = read(operating.CACHE / "meta.json")
    cache = cache_identity(operating.CACHE)
    assert cache == read(operating.POOL_ROOT / "report.json")["cache"]
    assert meta["data"] == "synthetic" and meta["vocab"] == 32768
    assert meta["train"] >= 2 * STEPS * TARGETS_PER_UPDATE
    receipts = {key: draw_receipt(*shape) for key, shape in LAYOUTS.items()}
    assert all(x == receipts["micro8"] for x in receipts.values())
    for name, (micro, accum) in LAYOUTS.items():
        with patch.object(sys, "argv", arguments(name)), patch.object(package, "train") as stub:
            cli.main()
        stub.assert_called_once()
        args, kwargs = stub.call_args
        assert args[:8] == ("m100s12_g4", "tied", "synthetic", 5_000_000, STEPS, micro, SEQ, accum)
        assert kwargs["ce_recompute_rows"] == ROWS and kwargs["train_repeat"] == 2
        assert kwargs["exact_cache"] and kwargs["sched"] == "decay" and not kwargs["kd"]
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    write(OUT / "profile.json", dict(tag=TAG, source_pins=pins(), parent_sha256=frozen.PARENT_SHA,
          cache=cache, meta=meta, args={name: arguments(name) for name in LAYOUTS},
          draw=receipts["micro8"], sample_ms=sampler.INTERVAL_MS, target_device_gb=[12, 13],
          checkpoint_writes=0, approval="WIP176 + 12~13GB"))
    print("P102A_WARM32K_PREPARED", meta["train"], STEPS*TARGETS_PER_UPDATE, flush=True)
    return 0


def worker(name, profile):
    from tinylm import cli
    from tinylm.train import trainer

    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 13 * (1 << 30)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    cfg_parent, parent, step = frozen.prior.load_parent(torch)
    assert step == 2289
    initial = state_sha(parent)
    factory, loader_class, evaluate, stats = (trainer.TiedMLPTransformer, trainer.Loader,
                                               trainer.evaluate, trainer._step_stats)
    train_loader = None
    validation = None
    final_state = None
    times = []
    arm_dir = OUT / name

    def make_model(cfg):
        fields = ("n_prelude", "n_middle", "n_coda", "dim", "ffn_dim", "emb_rank", "mlp_group",
                  "cla_group", "vocab_size", "micro_group", "n_q_heads", "n_kv_heads", "tie_mlp")
        assert all(getattr(cfg, key) == getattr(cfg_parent, key) for key in fields)
        instance = factory(cfg)
        instance.load_state_dict(parent, strict=True)
        instance.set_anneal(1.)
        assert cfg.grad_checkpoint and len(instance.visit_schedule()) == 28
        return instance

    def cache(data, tokens, *, exact, doc_filter, hf_tok, chat32, **_):
        assert data == "synthetic" and tokens == 5_000_000 and exact and not (doc_filter or hf_tok or chat32)
        return dict(profile["meta"])

    def loader(split, *args, **kwargs):
        nonlocal train_loader
        actual = loader_class(split, *args, **kwargs)
        if split == "train":
            assert train_loader is None
            train_loader = actual
        return actual

    def fixed_eval(model, _loader, _count, device, **kwargs):
        nonlocal validation
        if validation is None:
            val = loader_class("val", 8, SEQ, device, operating.CACHE, seed=99)
            validation = evaluate(model, val, 2, device, **kwargs)
        return dict(validation)

    def observe_stats(values, *args, **kwargs):
        times.extend(values)
        return stats(values, *args, **kwargs)

    def checkpoint(blob, destination):
        nonlocal final_state
        assert Path(destination).parent == arm_dir / "ckpt"
        assert blob["step"] == STEPS and blob["ce_recompute_rows"] == ROWS
        if final_state is None:
            final_state = {key: state_sha(blob[key]) for key in ("model", "opt", "opt_muon")}

    print("P102A_WARM32K_WORKER", name, os.getpid(), flush=True)
    with (patch.object(sys, "argv", profile["args"][name]),
          patch.object(trainer, "prepare", cache), patch.object(trainer, "TiedMLPTransformer", make_model),
          patch.object(trainer, "Loader", loader), patch.object(trainer, "evaluate", fixed_eval),
          patch.object(trainer, "_step_stats", observe_stats),
          patch.object(trainer, "CKPT", arm_dir / "ckpt"), patch.object(trainer, "LOGS", arm_dir / "logs"),
          patch.object(torch, "save", checkpoint)):
        cli.main()
    logs = list((arm_dir / "logs").glob("*.json"))
    assert len(logs) == 1 and not any((arm_dir / "ckpt").iterdir())
    raw = read(logs[0])
    assert raw["n_skip"] == 0 and raw["tokens"] == STEPS*TARGETS_PER_UPDATE and len(times) == STEPS
    assert train_loader.rng.bit_generator.state == profile["draw"]["rng"] and final_state and validation
    rate = 1000*TARGETS_PER_UPDATE/median(times[1:])
    write(OUT / f"{name}.json", dict(arm=name, initial=initial, final=final_state,
          native_log=str(logs[0].relative_to(ROOT)), native_log_sha256=sha(logs[0]), updates=STEPS,
          targets=raw["tokens"], step_ms=times, targets_per_second=rate, val=validation,
          alloc_gib=raw["vram_alloc_gb"], reserve_gib=raw["vram_reserved_gb"], checkpoint_writes=0))
    return 0


def sample_arm(name):
    output = OUT / f"{name}_device_100ms.csv"
    with output.open("xb") as stream:
        watch = subprocess.Popen((*sampler.DEVICE, f"--loop-ms={sampler.INTERVAL_MS}"), stdout=stream)
        try:
            argv = ["timeout", "--kill-after=5s", f"{CAP}s", sys.executable, "-B", "-u", "-X", "utf8", "-m",
                    "scripts.diag_p102a_p109_warm32k_device_batch", "worker", name]
            job = subprocess.run(argv, cwd=ROOT, check=False)
        finally:
            if watch.poll() is None:
                watch.terminate()
            watch.wait(timeout=8)
    return job.returncode, output


def run(profile):
    write(OUT / "active.json", dict(tag=TAG, pid=os.getpid(), arms=list(LAYOUTS)))
    print("P102A_WARM32K_ACTIVE", os.getpid(), flush=True)
    exits, arms, decision = {}, {}, None
    for name in LAYOUTS:
        if (OUT / "STOP").exists() or not operating.previous.shapes.idle():
            exits[name] = None
            break
        if name == "micro64":
            last = arms["micro32"]["device"]["occupied_mib"]
            first = arms["micro8"]["device"]["occupied_mib"]
            estimate = last + (last-first) * (64-32)/(32-8)
            estimate_gb = estimate*(1 << 20)/1e9
            total = arms["micro32"]["device"]["total_mib"]
            decision = dict(estimated_peak_gb=estimate_gb, eligible=estimate_gb <= 13 and estimate+1024 < total)
            print("P102A_WARM32K_MICRO64_ADMISSION", decision, flush=True)
            if not decision["eligible"]:
                exits[name] = None
                break
        code, measurements = sample_arm(name)
        exits[name] = code
        if code != 0:
            print("P102A_WARM32K_EXIT", name, code, flush=True)
            break
        row = read(OUT / f"{name}.json")
        samples = sampler.read_samples(measurements)
        peak = max(samples, key=lambda item: item["occupied_mib"])
        arms[name] = dict(row, device=peak, device_samples=len(samples), device_sha256=sha(measurements))
        print("P102A_WARM32K_EXIT", name, code, peak, row["targets_per_second"], flush=True)
    same = profile["source_pins"] == pins() and sha(PARENT) == profile["parent_sha256"]
    returned = operating.previous.shapes.idle()
    same_start = len({arm["initial"] for arm in arms.values()}) == 1 and len(arms) >= 2
    write(OUT / "report.json", dict(arms=arms, exits=exits, prediction=decision, same_initial=same_start,
          sources_and_parent_unchanged=same, gpu_returned=returned))
    return 0 if returned and same and same_start and not any(code for code in exits.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "worker"))
    parser.add_argument("arm", nargs="?", choices=LAYOUTS)
    args = parser.parse_args()
    assert (args.phase == "worker") == bool(args.arm)
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if args.phase == "prepare" else "0")
    assert datetime.now(CUTOFF.tzinfo) + timedelta(seconds=len(LAYOUTS)*(CAP + 10)) < CUTOFF
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if args.phase == "prepare":
        return prepare()
    profile = read(OUT / "profile.json")
    assert profile["source_pins"] == pins() and sha(PARENT) == profile["parent_sha256"]
    assert profile["args"] == {name: arguments(name) for name in LAYOUTS}
    assert os.environ.get("PYTORCH_CUDA_ALLOC_CONF") == sampler.prior.ALLOCATOR
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8"
    from tinylm.train.context_training_state import cache_identity

    assert profile["cache"] == cache_identity(operating.CACHE)
    return worker(args.arm, profile) if args.phase == "worker" else run(profile)


if __name__ == "__main__":
    sys.exit(main())
