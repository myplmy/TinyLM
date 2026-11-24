"""Check G4 at 8x16 and resume one real recomputed-CE checkpoint."""

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shutil
from statistics import median
import subprocess
import sys
import time
from unittest.mock import patch

import torch

from scripts import diag_p102a_g4_native_recomputed_ce as previous


BASE = previous.BASE
ROOT = previous.ROOT
TAG = "p102a_g4_recompute_operating_v1_20261119"
OUT = previous.OUT.with_name(TAG)
POOL_ROOT = previous.OUT.with_name("p013_native_synthetic_source_cpu_v1_20261118")
CACHE = POOL_ROOT / "data_cache/synthetic_5000000"
POOL, ACCUM, STEPS, SPLIT, ROWS = 5_000_000, 16, 6, 3, 1024
PHASES = ("reference", "continuous", "boundary", "resume")
TARGETS = BASE.MICRO * BASE.WIDTH * ACCUM * STEPS
DIGEST = previous.shapes.LOSS.TRACE.precision.digest


class SavedBoundary(Exception):
    """Stop after writing the trainer's exact split checkpoint."""


def paths_for(phase):
    suffix = "split" if phase in ("boundary", "resume") else phase
    tag = f"{TAG}_{suffix}"
    name = f"m100s12_g4_synthetic_5M_{tag}"
    return tag, OUT / "ckpt" / f"{name}.pt", OUT / "logs" / f"{name}.json"


def argv_for(phase):
    tag, _, _ = paths_for(phase)
    argv = BASE.cli_args("reference")
    replacements = {"--tag": tag, "--tokens": "5M", "--pool-tokens": "5M", "--accum": str(ACCUM),
                    "--eval-every": str(SPLIT), "--save-every": str(SPLIT)}
    for flag, value in replacements.items():
        argv[argv.index(flag) + 1] = value
    argv.extend(("--context-curriculum", "6:1024"))
    if phase != "reference":
        argv.extend(("--ce-recompute-rows", str(ROWS)))
    if phase == "resume":
        argv.append("--resume")
    return argv


def check_call(phase, args, kwargs):
    assert args[:8] == ("m100s12_g4", "tied", "synthetic", POOL, STEPS, 8, BASE.WIDTH, ACCUM)
    assert args[8:13] == (1e-3, SPLIT, phase == "resume", True, False)
    assert kwargs["ce_recompute_rows"] == (0 if phase == "reference" else ROWS)
    assert kwargs["tag"] == paths_for(phase)[0] and kwargs["save_every"] == SPLIT
    assert kwargs["context_curriculum"] == "6:1024" and kwargs["train_repeat"] == 2
    assert kwargs["exact_cache"] and kwargs["pool_tokens"] == POOL and not kwargs["kd"]


def identity():
    files = (Path(__file__).resolve(), POOL_ROOT / "report.json", CACHE / "train.bin",
             CACHE / "val.bin", CACHE / "meta.json", previous.OUT / "terminal_readback.json")
    return previous.identity() | {str(f.relative_to(ROOT)): DIGEST(f) for f in files}


def prepare():
    from tinylm import cli
    from tinylm.data import Loader
    import tinylm.train as train_package
    from tinylm.train.context_micro_tokens import MicroTokensCursor, parse_context_plan
    from tinylm.train.context_training_state import cache_identity

    source = previous.read(POOL_ROOT / "report.json")
    cache = cache_identity(CACHE)
    meta = previous.read(CACHE / "meta.json")
    assert cache == source["cache"] and meta["dir"] == str(CACHE) and meta["data"] == "synthetic"
    assert meta["vocab"] == 32768 and meta["train"] >= TARGETS * 2 and meta["tokens"] == POOL
    plan = parse_context_plan("6:1024", micro_bs=8, accum=ACCUM, seq=1024, steps=STEPS)
    loader = Loader("train", 8, BASE.WIDTH, "cpu", CACHE)
    cursor = MicroTokensCursor(plan, loader, source_sha256=cache["identity_sha256"])
    source_steps = {}
    for index in range(1, STEPS + 1):
        update = cursor.prepare()
        assert len(update.batches) == ACCUM and update.accounting["ntp_targets"] == TARGETS // STEPS
        cursor.finish(optimizer_applied=True)
        if index in (SPLIT, STEPS):
            source_steps[str(index)] = cursor.state_dict()
    commands = {phase: argv_for(phase) for phase in PHASES}
    for phase, argv in commands.items():
        with patch.object(sys, "argv", argv), patch.object(train_package, "train") as stub:
            cli.main()
        stub.assert_called_once()
        check_call(phase, *stub.call_args)
    assert not torch.cuda.is_initialized()
    BASE.write_new(OUT / "profile.json", dict(identity=identity(), cache=cache, data=meta, commands=commands,
                   targets=TARGETS, source_steps=source_steps))
    print("P102A_RECOMPUTE_OPERATING_READY", TARGETS, meta["train"], flush=True)


def worker(phase, profile):
    from tinylm import cli
    from tinylm.train import muon, trainer
    import tinylm.train as train_package

    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * (1 << 30)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.set_float32_matmul_precision("high")
    tag, checkpoint, log = paths_for(phase)
    assert argv_for(phase) == profile["commands"][phase]
    if phase == "resume":
        boundary = previous.read(OUT / "boundary.json")
        assert checkpoint.is_file() and DIGEST(checkpoint) == boundary["published"]["sha256"]
    else:
        assert not checkpoint.exists() and not log.exists()
    train = train_package.train
    evaluate, model, muon_step = trainer.evaluate, trainer.TiedMLPTransformer, muon.Muon.step
    stats, real_save = trainer._step_stats, torch.save
    hash_state = previous.shapes.previous.state_sha
    states, peaks, times = {}, [], []
    initial = None
    started = time.monotonic()

    def make_model(cfg):
        nonlocal initial
        instance = model(cfg)
        assert (cfg.vocab_size, cfg.mlp_group, cfg.cla_group) == (32768, 4, 2)
        assert cfg.grad_checkpoint and len(instance.visit_schedule()) == 28
        initial = hash_state(instance.state_dict())
        return instance

    def cache(data, tokens, *, exact, doc_filter, hf_tok, chat32, **_):
        assert data == "synthetic" and tokens == POOL and exact and not (doc_filter or hf_tok or chat32)
        return dict(profile["data"])

    def evaluate_short(instance, loader, _count, device, **kwargs):
        value = evaluate(instance, loader, 2, device, **kwargs)
        torch.cuda.reset_peak_memory_stats()
        return value

    def applied(opt, *args, **kwargs):
        value = muon_step(opt, *args, **kwargs)
        torch.cuda.synchronize()
        peaks.append((torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved()))
        return value

    def save(blob, destination):
        assert destination.parent == checkpoint.parent
        step = str(blob["step"])
        assert step in profile["source_steps"] and blob.get("ce_recompute_rows", 0) == (
            0 if phase == "reference" else ROWS)
        cursor = blob[trainer.CONTEXT_STATE_KEY]
        assert cursor["cursor"] == profile["source_steps"][step]
        assert ("recomputed_ce.py" in cursor["binding"]["sources"]) == (phase != "reference")
        if step not in states:
            names = ("cursor", "validation_rng", "cpu_rng", "cuda_rng")
            states[step] = dict(weights=hash_state(blob["model"]), adamw=hash_state(blob["opt"]),
                muon=hash_state(blob["opt_muon"]), rng=hash_state({name: cursor[name] for name in names}),
                control=hash_state(cursor["control"]))
        if phase == "boundary":
            assert blob["step"] == SPLIT and destination == checkpoint and not checkpoint.exists()
            real_save(blob, destination)
            raise SavedBoundary

    def observed_stats(values):
        times.extend(values)
        return stats(values)

    def checked_train(*args, **kwargs):
        check_call(phase, args, kwargs)
        return train(*args, **kwargs)

    print("P102A_OPERATING_PHASE", phase, os.getpid(), flush=True)
    with (patch.object(sys, "argv", profile["commands"][phase]),
          patch.object(train_package, "train", checked_train),
          patch.object(trainer, "prepare", cache), patch.object(trainer, "TiedMLPTransformer", make_model),
          patch.object(trainer, "CKPT", checkpoint.parent), patch.object(trainer, "LOGS", log.parent),
          patch.object(trainer, "evaluate", evaluate_short), patch.object(trainer, "_step_stats", observed_stats),
          patch.object(muon.Muon, "step", applied), patch.object(torch, "save", save)):
        try:
            cli.main()
        except SavedBoundary:
            assert phase == "boundary"
    expected = SPLIT if phase in ("boundary", "resume") else STEPS
    assert len(peaks) == expected
    if phase == "boundary":
        assert set(states) == {str(SPLIT)} and not log.exists()
        size = checkpoint.stat().st_size
        assert 0 < size < (1 << 30)
        published = dict(path=str(checkpoint.relative_to(ROOT)), bytes=size, sha256=DIGEST(checkpoint))
        native = None
    else:
        assert len(times) == expected
        raw = previous.read(log)
        assert raw["n_skip"] == 0 and raw["tokens"] == TARGETS
        assert raw["context_resume_start_step"] == (SPLIT if phase == "resume" else 0)
        assert raw.get("ce_recompute_rows", 0) == (0 if phase == "reference" else ROWS)
        assert set(states) == ({str(STEPS)} if phase == "resume" else {str(SPLIT), str(STEPS)})
        native = dict(path=str(log.relative_to(ROOT)), sha256=DIGEST(log),
                      history=raw["history"], final=raw["final"], step_times_ms=times,
                      median_after_first_ms=median(times[1:]))
        published = None
    if phase == "resume":
        assert DIGEST(checkpoint) == boundary["published"]["sha256"]
    BASE.write_new(OUT / f"{phase}.json", dict(phase=phase, tag=tag, updates=expected, states=states,
        initial=initial, peak_allocated=max(x[0] for x in peaks), peak_reserved=max(x[1] for x in peaks),
        seconds=time.monotonic() - started, native=native, published=published))
    print("P102A_OPERATING_PHASE_RESULT", phase, expected, flush=True)
    return 0


def actual(profile):
    assert previous.shapes.idle() and shutil.disk_usage(OUT).free >= (1 << 30)
    BASE.write_new(OUT / "active.json", dict(tag=TAG, pid=os.getpid(), phases=PHASES))
    print("P102A_OPERATING_ACTIVE", os.getpid(), flush=True)
    exits = {}
    for phase in PHASES:
        if phase == "resume" and exits.get("boundary") != 0:
            exits[phase] = None
            break
        assert previous.shapes.idle(), "GPU was acquired by another process"
        args = ["timeout", "--kill-after=6s", "100s", sys.executable, "-B", "-X", "utf8", "-m",
                "scripts.diag_p102a_g4_recompute_operating", "worker", phase]
        exits[phase] = subprocess.run(args, cwd=ROOT).returncode
        print("P102A_OPERATING_EXIT", phase, exits[phase], flush=True)
    assert previous.shapes.idle() and profile["identity"] == identity()
    results = {phase: previous.read(OUT / f"{phase}.json") for phase, code in exits.items() if code == 0}
    checks = {}
    if all(phase in results for phase in PHASES):
        ref, full, boundary, tail = (results[phase] for phase in PHASES)
        checks = dict(reference_states=ref["states"] == full["states"],
                      same_start=len({result["initial"] for result in results.values()}) == 1,
                      boundary_states=full["states"][str(SPLIT)] == boundary["states"][str(SPLIT)],
                      resumed_states=full["states"][str(STEPS)] == tail["states"][str(STEPS)],
                      same_losses=all(ref["native"][key] == full["native"][key] == tail["native"][key]
                                      for key in ("history", "final")))
    saved = list((OUT / "ckpt").glob("*.pt"))
    if "boundary" in results:
        path = ROOT / results["boundary"]["published"]["path"]
        assert saved == [path] and DIGEST(path) == results["boundary"]["published"]["sha256"]
    BASE.write_new(OUT / "report.json", dict(exits=exits, phases=results, checks=checks,
        device_returned=True, actual_updates=sum(result["updates"] for result in results.values())))
    return 0 if checks and all(checks.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "actual", "worker"))
    parser.add_argument("arm", nargs="?", choices=PHASES)
    args = parser.parse_args()
    assert datetime.now(BASE.CUTOFF.tzinfo) + timedelta(minutes=8) < BASE.CUTOFF
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if args.phase == "prepare" else "0")
    os.environ.update(TINYLM_DIR=str(OUT / "scratch"), TINYLM_HF=str(OUT / "scratch" / "HF"))
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if args.phase == "prepare":
        OUT.mkdir(exist_ok=False)
        return prepare()
    profile = previous.read(OUT / "profile.json")
    assert profile["identity"] == identity()
    assert os.environ["CUBLAS_WORKSPACE_CONFIG"] == previous.shapes.LOSS.STRICT.WORKSPACE
    return actual(profile) if args.phase == "actual" else worker(args.arm, profile)


if __name__ == "__main__":
    sys.exit(main())
