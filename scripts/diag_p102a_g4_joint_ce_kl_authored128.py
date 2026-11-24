"""Check whether a 128-document microbatch improves bounded 248K G4 training."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p102a_g4_joint_ce_kl_authored64 as base
from scripts.diag_p102a_g4_full_delta_train import state_sha
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from scripts.p102a_joint_ce_kl_bounded import BoundedJointHead


ce, online, joint = base.ce, base.online, base.joint
TAG = "p102a_g4_joint_ce_kl_authored128_v1_20261119"
OUT = base.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
PLAN = OUT / "plan_at_execution.md"
STEPS, DOCUMENTS, LIMIT, SHUFFLE = 11, 128, 300, 2039
ARMS = (("ordered", 64), ("ordered", 128), ("shuffled", 128), ("shuffled", 64))
TRANSFORMER = "tinylm/model/transformer.py"
CURRENT_TRANSFORMER_SHA = "75F305C23CB7C5E0D03926F8D1B81A06A7FFE7F5738ACF002D24160E76E374A9"


class CardBudgetExceeded(RuntimeError):
    pass


def gate(reserve=0):
    if (OUT / "STOP").exists() or datetime.now(base.CUTOFF.tzinfo) + timedelta(seconds=reserve) >= base.CUTOFF:
        raise RuntimeError("owned STOP or deadline")


def guard():
    gate()
    free, total = torch.cuda.mem_get_info()
    if total - free > online.DEVICE_BUDGET:
        raise CardBudgetExceeded("card occupancy exceeded 13 GB")


def arm_name(order, micro):
    return f"{order}_{micro}"


def schedule(draws, order, micro):
    blocks = torch.arange(len(draws))
    if order == "shuffled":
        blocks = torch.randperm(len(draws), generator=torch.Generator().manual_seed(SHUFFLE))
    chunks = blocks.repeat(base.PASSES).reshape(STEPS, DOCUMENTS // micro, micro // ce.BATCH)
    docs = draws[chunks].reshape(STEPS, DOCUMENTS // micro, micro)
    return chunks, docs


def verify(profile):
    assert profile["tag"] == TAG and profile["approval"] == "WIP177"
    for name, digest in profile["pins"].items():
        assert ce.qwen.digest(ce.ROOT / name) == digest, name


def prepare():
    prior = ce.qwen.load(base.PROFILE)
    run = ce.qwen.load(base.OUT / "report.json")
    result = ce.qwen.load(base.OUT / "comparison.json")
    assert run["exit"] == 0 and run["device_returned"] and result["small_held_gate"] and result["memory_time_gate"]
    assert run["profile_sha256"] == ce.qwen.digest(base.PROFILE)
    assert prior["passes"] == base.PASSES and prior["slots"] == STEPS * DOCUMENTS * ce.WIDTH
    x, y, draws, held = base.load_inputs()
    assert x.shape == y.shape and draws.shape == (ce.UPDATES, ce.BATCH)
    assert torch.unique(draws).numel() == draws.numel() and not torch.isin(held, draws).any()
    valid = y.ge(0)
    assert valid[held].sum((1, 2)).tolist() == [660, 888] and valid[draws].sum().item() == 12417
    arms = {}
    for order, micro in ARMS:
        chunks, docs = schedule(draws, order, micro)
        counts = valid[docs].sum((2, 3))
        assert counts.sum().item() == prior["targets"] and torch.all(counts > 0)
        arms[arm_name(order, micro)] = dict(ids_sha256=state_sha(docs.reshape(STEPS, DOCUMENTS)),
                                            step_targets=counts.sum(1).tolist(), micro_targets=counts.tolist())
    for order in ("ordered", "shuffled"):
        left, right = [arms[arm_name(order, batch)] for batch in (64, 128)]
        assert left["ids_sha256"] == right["ids_sha256"] and left["step_targets"] == right["step_targets"]
    assert arms["ordered_64"]["ids_sha256"] != arms["shuffled_64"]["ids_sha256"]
    current = ce.qwen.digest(ce.ROOT / TRANSFORMER)
    assert current == CURRENT_TRANSFORMER_SHA and current != prior["pins"][TRANSFORMER]
    assert not torch.cuda.is_initialized()
    heading = "### Stage2izX "
    plan = base.PLAN.read_text(encoding="utf8").split(heading, 1)
    assert len(plan) == 2 and TAG in plan[1]
    OUT.mkdir()
    PLAN.write_text(heading + plan[1], encoding="utf8")
    pins = dict(prior["pins"])
    pins[TRANSFORMER] = current
    paths = (Path(__file__).resolve(), base.PROFILE, base.OUT / "report.json", base.OUT / "comparison.json", PLAN)
    pins.update({str(path.relative_to(ce.ROOT)): ce.qwen.digest(path) for path in paths})
    profile = dict(tag=TAG, approval="WIP177", teacher=prior["teacher"], targets=prior["targets"],
                   slots=prior["slots"], feature_sha256=result["cache"]["features_sha256"], arms=arms, pins=pins,
                   prior_transformer_sha256=prior["pins"][TRANSFORMER], reference64=run["profile_sha256"])
    verify(profile)
    ce.qwen.write(PROFILE, profile)
    print("AUTHORED128_CPU", profile["slots"], profile["targets"], arms, flush=True)


def train(order, micro, profile, teacher, x, y, draws, held, history):
    name = arm_name(order, micro)
    contract = profile["arms"][name]
    chunks, docs = schedule(draws, order, micro)
    assert state_sha(docs.reshape(STEPS, DOCUMENTS)) == contract["ids_sha256"]
    torch.manual_seed(ce.SEED)
    model = ce.initialize()
    initial = state_sha(model.state_dict())
    route = ce.build_experimental_optimizers(model, "muon_matched", lr=ce.LR, matrix_lr_mult=ce.MATRIX_MULT)
    optimizers = (route.adamw, route.matrix)
    ce.keep_active_groups(optimizers)
    rates = [[group["lr"] for group in opt.param_groups] for opt in optimizers]
    raw = OUT / f"{name}_device_100ms.csv"
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    with base.sample_gpu(raw), patch.object(joint, "_JointHead", BoundedJointHead):
        for step, total in enumerate(contract["step_targets"]):
            guard()
            factor = ce.lr_factor(step, ce.WARMUP, STEPS, "cosine")
            for optimizer, rates_for_optimizer in zip(optimizers, rates, strict=True):
                for group, rate in zip(optimizer.param_groups, rates_for_optimizer, strict=True):
                    group["lr"] = rate * factor
            start = perf_counter()
            sum_ce, sum_kl = 0.0, 0.0
            for ids, indexes, count in zip(docs[step], chunks[step], contract["micro_targets"][step], strict=True):
                xb, yb = x[ids], y[ids]
                valid = yb.ge(0)
                distribution = base.teacher_batch(*teacher, indexes.tolist(), count)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    hidden = model(xb, return_hidden=True)[valid]
                    primary, kd = online.tiled_loss(model, hidden, yb[valid], distribution)
                weight = count / total
                ((primary + online.ALPHA * kd) * weight).backward()
                sum_ce += primary.detach() * weight
                sum_kl += kd.detach() * weight
                model.clear_quant()
                del distribution, hidden, primary, kd
                guard()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            for optimizer in optimizers:
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
            torch.cuda.synchronize()
            history.append(dict(step=step + 1, targets=total, ce=float(sum_ce), kl=float(sum_kl),
                                gradient_norm=float(norm), seconds=perf_counter() - start))
            guard()
            if step in (0, 3, 7, STEPS - 1):
                print("AUTHORED128_TRAIN", name, history[-1], flush=True)
    samples = ce.read_samples(raw)
    peak = dict(allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved(),
                card=max(samples, key=lambda row: row["occupied_mib"]), samples=len(samples))
    assert sum(row["targets"] for row in history) == profile["targets"]
    torch.cuda.empty_cache()
    held_scores = ce.frozen_scores(model, x, y, held)
    guard()
    return dict(status="COMPLETE", initial=initial, history=history, held=held_scores, peak=peak,
                targets_per_sec=sum(row["targets"] for row in history[1:])/sum(row["seconds"] for row in history[1:]),
                final=dict(model=state_sha(model.state_dict()), adamw=state_sha(optimizers[0].state_dict()),
                           muon=state_sha(optimizers[1].state_dict())))


def compare(results, order):
    a, b = [results[arm_name(order, batch)] for batch in (64, 128)]
    if a["status"] != "COMPLETE" or b["status"] != "COMPLETE":
        return dict(capacity_and_held_gate=False, speed_gate=False, arms=[a["status"], b["status"]])
    assert a["initial"] == b["initial"] and len(a["history"]) == len(b["history"]) == STEPS
    delta = {lang: b["held"][lang]["nll"] - a["held"][lang]["nll"] for lang in ("en", "ko")}
    top = sum(b["held"][lang]["correct"] - a["held"][lang]["correct"] for lang in delta)
    speed = b["targets_per_sec"] / a["targets_per_sec"] - 1
    card_ok = all(arm["peak"]["card"]["occupied_mib"] * 2**20 <= online.DEVICE_BUDGET for arm in (a, b))
    return dict(capacity_and_held_gate=card_ok and max(delta.values()) <= .015 and top >= -2,
                speed_gate=speed >= .05, throughput_delta=speed, held_nll_delta=delta, top1_delta=top,
                same_final={key: a["final"][key] == b["final"][key] for key in a["final"]})


def worker(profile):
    assert torch.cuda.device_count() == 1
    free, total = torch.cuda.mem_get_info()
    limit = online.DEVICE_BUDGET - (total - free) - 384 * 2**20
    assert free >= 12500 * 2**20 and limit > 8 * 2**30
    torch.cuda.set_per_process_memory_fraction(limit / total)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    x, y, draws, held = base.load_inputs()
    x, y = x.cuda(), y.cuda()
    results, capped = {}, set()
    with sdpa_kernel(SDPBackend.MATH):
        with patch.object(base, "guard", guard):
            teacher = base.teacher_features(profile, x, y, draws)
        feature_hash = state_sha(teacher[1])
        assert feature_hash == profile["feature_sha256"], feature_hash
        print("AUTHORED128_FEATURES", feature_hash, "allocator_limit_bytes", limit, flush=True)
        for order, micro in ARMS:
            name = arm_name(order, micro)
            gate()
            if micro in capped:
                result = dict(status="SKIPPED_SAME_CAP")
            else:
                torch.cuda.empty_cache()
                history = []
                try:
                    result = train(order, micro, profile, teacher, x, y, draws, held, history)
                except (torch.OutOfMemoryError, CardBudgetExceeded) as error:
                    capped.add(micro)
                    result = dict(status="MEMORY_CAP", history=history, detail=str(error), allocated=torch.cuda.max_memory_allocated(),
                                  reserved=torch.cuda.max_memory_reserved())
            results[name] = result
            ce.qwen.write(OUT / f"{name}.json", result)
            print("AUTHORED128_ARM", name, result["status"], flush=True)
    del teacher, x, y
    proof = dict(pairs={order: compare(results, order) for order in ("ordered", "shuffled")},
                 actual_updates=sum(len(row.get("history", ())) for row in results.values()),
                 first_and_later_arms={name: row["status"] for name, row in results.items()},
                 feature_sha256=feature_hash, allocator_limit_bytes=limit, checkpoint_writes=0)
    close_owned_cuda(torch, proof)
    ce.qwen.write(OUT / "comparison.json", proof)
    print("AUTHORED128_COMPARE", proof, flush=True)


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
    print("AUTHORED128_RELEASE", code, returned, after, flush=True)
    if code or not returned:
        raise SystemExit(code or 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "worker"))
    phase = parser.parse_args().phase
    gate(LIMIT + 10 if phase == "run" else 0)
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
