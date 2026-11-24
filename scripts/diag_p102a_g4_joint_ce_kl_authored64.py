"""Compare 248K CE/KL backward on the same authored P109 training stream."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch
from zoneinfo import ZoneInfo

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_qwen35_248k_cached_kl as cached
from scripts.diag_p102a_g4_full_delta_train import state_sha
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from scripts.p102a_joint_ce_kl_bounded import BoundedJointHead


online, ce = cached.online, cached.ce
joint = online.joint
TAG = "p102a_g4_joint_ce_kl_authored64_v1_20261119"
OUT = ce.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
SEALED_PLAN = OUT / "plan_at_execution.md"
PLAN = ce.ROOT / "test_plan/P102A_T1-S1-S2-S3-학습시간-기능계약.md"
ORIGINAL = cached.OUT / "report.json"
BATCH, PASSES, UPDATES = 64, 4, 22
LIMIT = 240
CUTOFF = datetime(2026, 11, 20, 16, 58, tzinfo=ZoneInfo("Asia/Seoul"))


def gate(seconds=0):
    if (OUT / "STOP").exists() or datetime.now(CUTOFF.tzinfo) + timedelta(seconds=seconds) >= CUTOFF:
        raise RuntimeError("owned STOP or deadline")


def guard():
    gate()
    free, total = torch.cuda.mem_get_info()
    if total - free > online.DEVICE_BUDGET:
        raise RuntimeError("device occupancy exceeded 13 GB")


def load_inputs():
    with np.load(ce.DATA, allow_pickle=False) as bundle:
        return tuple(torch.from_numpy(bundle[k]) for k in ("x", "y", "draws", "held"))


def verify(profile):
    assert profile["tag"] == TAG and profile["approval"] == "WIP177"
    for path, digest in profile["pins"].items():
        assert ce.qwen.digest(ce.ROOT / path) == digest, path


def prepare():
    prior = ce.qwen.load(cached.PROFILE)
    teacher = ce.qwen.load(online.PROFILE)
    parent = ce.qwen.load(ce.PROFILE)
    assert prior["teacher"] == teacher["teacher"] and prior["teacher_hidden"] == 1024
    saved = ce.qwen.load(ORIGINAL)
    assert saved["profile_sha256"] == ce.qwen.digest(cached.PROFILE)
    assert saved["source_preserved"] and saved["quality_kept"] and len(saved["history"]) == ce.UPDATES
    assert saved["cache"]["selected"] == "batch4_width96_exact"
    x, y, draws, held = load_inputs()
    assert x.shape == y.shape and x.shape[1] == ce.WIDTH and draws.shape == (ce.UPDATES, ce.BATCH)
    assert torch.unique(draws).numel() == draws.numel() and not torch.isin(held, draws).any()
    valid = y.ge(0)
    assert torch.equal(valid, torch.arange(ce.WIDTH) < valid.sum(1, keepdim=True))
    assert torch.equal(x[:, 1:][valid[:, 1:]], y[:, :-1][valid[:, 1:]])
    assert int(x.min()) >= 0 and int(x.max()) < ce.ASSIGNED and int(y.max()) < ce.ASSIGNED
    assert y[~valid].eq(-100).all() and int(valid[draws].sum()) == 12417
    counts = valid[draws.repeat((PASSES, 1)).reshape(UPDATES, BATCH)].sum((1, 2)).tolist()
    assert min(counts) > 2000 and max(counts) < 2300
    assert valid[held].sum((1, 2)).tolist() == [660, 888]
    plan = PLAN.read_text(encoding="utf-8").split("### Stage2izW ", 1)
    assert len(plan) == 2 and TAG in plan[1]
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    SEALED_PLAN.write_text("### Stage2izW " + plan[1], encoding="utf-8")
    paths = (Path(__file__), Path(sys.modules[BoundedJointHead.__module__].__file__),
             ce.parent.PARENT, ce.PROFILE, cached.PROFILE, ORIGINAL, SEALED_PLAN)
    pins = {**parent["pins"], **teacher["pins"], **prior["pins"]}
    pins.update({str(path.relative_to(ce.ROOT)): ce.qwen.digest(path) for path in paths})
    assert pins[str(ce.parent.PARENT.relative_to(ce.ROOT))] == parent["parent_sha256"]
    profile = dict(tag=TAG, approval="WIP177", teacher=prior["teacher"], pins=pins,
                   micro_bs=BATCH, accum=1, width=ce.WIDTH, teacher_batch=ce.BATCH,
                   temperature=online.TEMPERATURE, alpha=online.ALPHA, tile=online.TILE,
                   passes=PASSES, slots=UPDATES*BATCH*ce.WIDTH, targets=sum(counts),
                   targets_per_step=counts, initial_held_from_prior=saved["held_by_update"]["0"])
    verify(profile)
    ce.qwen.write(PROFILE, profile)
    print("AUTHORED64_CPU", profile["slots"], profile["targets"], min(counts), max(counts), flush=True)


@contextmanager
def sample_gpu(path):
    with path.open("xb") as stream:
        sampler = subprocess.Popen((*ce.DEVICE, f"--loop-ms={ce.INTERVAL_MS}"), stdout=stream)
        try:
            yield
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)


@torch.no_grad()
def teacher_features(profile, x, y, draws):
    teacher = online.load_teacher(ce.ROOT / profile["teacher"])
    features = []
    for ids in draws:
        guard()
        hidden = teacher.model.language_model(input_ids=x[ids], use_cache=False).last_hidden_state
        features.append(hidden[y[ids].ge(0)])
        del hidden
    assert sum(len(block) for block in features) == profile["targets"] // PASSES
    assert all(block.dtype == torch.bfloat16 and block.shape[1] == 1024 for block in features)
    return teacher.lm_head, features


@torch.no_grad()
def teacher_batch(head, features, indexes, targets):
    values = torch.empty((targets, ce.ASSIGNED), device=head.weight.device, dtype=torch.bfloat16)
    offset = 0
    for index in indexes:
        block = features[index]
        size = len(block)
        values[offset:offset + size].copy_(head(block)[:, :ce.ASSIGNED])
        offset += size
    assert offset == targets
    return values


def train(name, head, profile, teacher, x, y, draws, held):
    torch.manual_seed(ce.SEED)
    model = ce.initialize()
    initial = state_sha(model.state_dict())
    route = ce.build_experimental_optimizers(model, "muon_matched", lr=ce.LR, matrix_lr_mult=ce.MATRIX_MULT)
    optimizers = (route.adamw, route.matrix)
    ce.keep_active_groups(optimizers)
    rates = [[group["lr"] for group in opt.param_groups] for opt in optimizers]
    chunks = torch.arange(len(draws)).repeat(PASSES).reshape(UPDATES, BATCH // ce.BATCH)
    draws = draws.repeat((PASSES, 1)).reshape(UPDATES, BATCH)
    history = []
    raw = OUT / f"{name}_device_100ms.csv"
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    with sample_gpu(raw), patch.object(joint, "_JointHead", head):
        for step, (ids, indexes, targets) in enumerate(zip(draws, chunks, profile["targets_per_step"], strict=True)):
            guard()
            factor = ce.lr_factor(step, ce.WARMUP, UPDATES, "cosine")
            for optimizer, base in zip(optimizers, rates, strict=True):
                for group, rate in zip(optimizer.param_groups, base, strict=True):
                    group["lr"] = rate * factor
            xb, yb = x[ids], y[ids]
            mask = yb.ge(0)
            torch.cuda.synchronize()
            start = perf_counter()
            distributions = teacher_batch(*teacher, indexes.tolist(), targets)
            torch.cuda.synchronize()
            teacher_seconds = perf_counter() - start
            with torch.autocast("cuda", dtype=torch.bfloat16):
                hidden = model(xb, return_hidden=True)[mask]
                primary, kd = online.tiled_loss(model, hidden, yb[mask], distributions)
            loss = primary + online.ALPHA * kd
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            if step == 0:
                first = dict(grad=state_sha({n: p.grad for n, p in model.named_parameters()}),
                             teacher_first_tile=state_sha(distributions[:online.TILE]))
            for optimizer in optimizers:
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
            model.clear_quant()
            torch.cuda.synchronize()
            history.append(dict(step=step + 1, targets=targets, ce=float(primary.detach()),
                                kl=float(kd.detach()), gradient_norm=float(norm), teacher_seconds=teacher_seconds,
                                seconds=perf_counter() - start))
            del distributions, hidden, loss, primary, kd, norm
            if step == 0 or (step + 1) % 4 == 0 or step + 1 == UPDATES:
                print("AUTHORED64_TRAIN", name, history[-1], flush=True)
            guard()
    peak = dict(allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved())
    samples = ce.read_samples(raw)
    assert samples and sum(row["targets"] for row in history) == profile["targets"]
    final = ce.frozen_scores(model, x, y, held)
    result = dict(initial=initial, first=first, history=history, held=final, peak=peak,
                  median_seconds_after_first=median(row["seconds"] for row in history[1:]),
                  device_peak=max(samples, key=lambda row: row["occupied_mib"]), device_samples=len(samples),
                  final=dict(model=state_sha(model.state_dict()), adamw=state_sha(optimizers[0].state_dict()),
                             muon=state_sha(optimizers[1].state_dict())))
    ce.qwen.write(OUT / f"{name}.json", result)
    return result


def worker(profile):
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 13000*2**20
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    x, y, draws, held = load_inputs()
    x, y = x.cuda(), y.cuda()
    with sdpa_kernel(SDPBackend.MATH):
        cache_started = perf_counter()
        teacher = teacher_features(profile, x, y, draws)
        cache_seconds = perf_counter() - cache_started
        cache = dict(seconds=cache_seconds, features_sha256=state_sha(teacher[1]),
                     bytes=sum(block.numel()*block.element_size() for block in teacher[1]))
        print("AUTHORED64_FEATURES", cache, flush=True)
        results = {}
        for name, head in (("standard", joint._JointHead), ("bounded", BoundedJointHead)):
            torch.cuda.empty_cache()
            results[name] = train(name, head, profile, teacher, x, y, draws, held)
    del teacher, x, y
    a, b = results["standard"], results["bounded"]
    assert a["initial"] == b["initial"]
    assert a["first"]["teacher_first_tile"] == b["first"]["teacher_first_tile"]
    delta = {lang: b["held"][lang]["nll"] - a["held"][lang]["nll"] for lang in ("en", "ko")}
    top = sum(b["held"][lang]["correct"] - a["held"][lang]["correct"] for lang in delta)
    saved = a["peak"]["allocated"] - b["peak"]["allocated"]
    slower = b["median_seconds_after_first"] / a["median_seconds_after_first"] - 1
    first_loss = all(a["history"][0][key] == b["history"][0][key] for key in ("ce", "kl"))
    result = dict(cache=cache, nll_bounded_minus_standard=delta, top1_delta=top,
                  same_first_losses=first_loss, same_first_grad=a["first"]["grad"] == b["first"]["grad"],
                  same_final={key: a["final"][key] == b["final"][key] for key in a["final"]},
                  allocated_saved_bytes=saved, median_seconds_relative=slower,
                  small_held_gate=max(delta.values()) <= .015 and top >= -2,
                  memory_time_gate=first_loss and saved >= 512*2**20 and slower <= .30,
                  checkpoint_writes=0)
    close_owned_cuda(torch, result)
    ce.qwen.write(OUT / "comparison.json", result)
    print("AUTHORED64_COMPARISON", result, flush=True)


def run(profile):
    assert ce.idle(), "GPU has another compute process"
    before = subprocess.check_output(ce.DEVICE, text=True, timeout=8).strip()
    args = ["timeout", "--kill-after=5s", f"{LIMIT}s", sys.executable, "-B", "-u", "-m", __spec__.name, "worker"]
    process = subprocess.Popen(args, cwd=ce.ROOT)
    ce.qwen.write(OUT / "active.json", dict(tag=TAG, pid=os.getpid(), child=process.pid))
    code = process.wait()
    after = subprocess.check_output(ce.DEVICE, text=True, timeout=8).strip()
    returned = ce.idle()
    verify(profile)
    ce.qwen.write(OUT / "report.json", dict(tag=TAG, exit=code, before=before, after=after,
                                           device_returned=returned, sources_preserved=True,
                                           profile_sha256=ce.qwen.digest(PROFILE)))
    print("AUTHORED64_RELEASE", code, returned, after, flush=True)
    if code or not returned:
        raise SystemExit(code or 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "worker"))
    phase = parser.parse_args().phase
    gate(LIMIT if phase == "run" else 0)
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if phase == "prepare" else "0")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if phase == "prepare":
        prepare()
    else:
        profile = ce.qwen.load(PROFILE)
        if phase == "run":
            verify(profile)
            run(profile)
        else:
            worker(profile)


if __name__ == "__main__":
    main()
