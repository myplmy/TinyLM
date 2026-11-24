"""Replay the admitted P109 warm G4 inputs with aligned Qwen3.5 teacher KL."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
from statistics import median
import subprocess
from time import perf_counter

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_qwen_248k_warm_ce as ce
from scripts import p102a_joint_ce_kl as joint
from scripts.p102a_full_kl_recompute import _kl


TAG = "p109_qwen35_248k_warm_kl_v1_20261119"
OUT = ce.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
BASELINE = ce.OUT / "report.json"
TEMPERATURE, ALPHA, TILE = 2.0, 0.3, 64
DEVICE_BUDGET = 13_000_000_000


def teacher_folder():
    source = ce.qwen.load(ce.qwen.ASSET)["assets"]["qwen35_hf"]
    return (ce.ROOT / source["path"]).parent


def verify(profile):
    for path, digest in profile["pins"].items():
        assert ce.qwen.digest(ce.ROOT / path) == digest, path
    baseline = ce.qwen.load(BASELINE)
    assert baseline["source_preserved"] and len(baseline["history"]) == ce.UPDATES
    assert baseline["profile_sha256"] == ce.qwen.digest(ce.PROFILE)
    ce.verify(ce.qwen.load(ce.PROFILE))
    return baseline


def prepare():
    teacher = teacher_folder()
    cfg, index = [ce.qwen.load(teacher / name) for name in ("config.json", "model.safetensors.index.json")]
    assert cfg["architectures"] == ["Qwen3_5ForConditionalGeneration"]
    assert cfg["text_config"]["vocab_size"] == ce.VOCAB
    shards = sorted(set(index["weight_map"].values()))
    assert len(shards) == 1 and Path(shards[0]).name == shards[0]
    assert index["weight_map"]["model.language_model.embed_tokens.weight"] == shards[0]
    assert ce.qwen.digest(teacher / "tokenizer.json") == ce.qwen.load(ce.qwen.OUT / "profile.json")["original_sha256"]
    with np.load(ce.DATA, allow_pickle=False) as bundle:
        x, y, draws, held = [bundle[k] for k in ("x", "y", "draws", "held")]
    assert draws.shape == (ce.UPDATES, ce.BATCH) and held.shape == (2, 24)
    assert x.shape == y.shape and x.shape[1] == ce.WIDTH and len(set(draws.flat)) == draws.size
    assert not set(draws.flat).intersection(held.flat) and 0 <= x.min() <= x.max() < ce.ASSIGNED
    mask = y >= 0
    assert (x[:, 1:][mask[:, 1:]] == y[:, :-1][mask[:, 1:]]).all()
    assert (y[~mask] == -100).all() and y[mask].max() < ce.ASSIGNED
    assert int(mask[draws].sum()) == 12417
    paths = [Path(__file__), Path(joint.__file__), ce.ROOT / "scripts/p102a_full_kl_recompute.py",
             ce.PROFILE, ce.DATA, ce.MAPPING, BASELINE, ce.qwen.ASSET,
             *(teacher / name for name in ("config.json", "tokenizer.json", "model.safetensors.index.json", *shards))]
    profile = dict(tag=TAG, approval="WIP176", pins={str(p.relative_to(ce.ROOT)): ce.qwen.digest(p) for p in paths},
                   teacher=str(teacher.relative_to(ce.ROOT)), teacher_vocab=ce.VOCAB, assigned=ce.ASSIGNED,
                   same_input=True, t=TEMPERATURE, alpha=ALPHA, target_tile=TILE, updates=ce.UPDATES,
                   held_targets=[int(mask[group].sum()) for group in held], targets=int(mask[draws].sum()))
    verify(profile)
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    ce.qwen.write(PROFILE, profile)
    print("P109_REAL_KL_CPU", profile["targets"], profile["held_targets"], profile["teacher"], flush=True)


def load_teacher(path):
    from transformers import Qwen3_5ForConditionalGeneration

    model, loading = Qwen3_5ForConditionalGeneration.from_pretrained(
        path, local_files_only=True, dtype=torch.bfloat16, attn_implementation="eager",
        output_loading_info=True,
    )
    assert not any(loading.get(k) for k in ("missing_keys", "mismatched_keys", "error_msgs")), loading
    model = model.eval().requires_grad_(False).cuda()
    assert model.lm_head.weight.shape[0] == ce.VOCAB and model.lm_head.weight.dtype == torch.bfloat16
    assert model.lm_head.weight.data_ptr() == model.model.language_model.embed_tokens.weight.data_ptr()
    return model


@torch.no_grad()
def teacher_logits(teacher, x, mask, inspect_padding=False):
    hidden = teacher.model.language_model(input_ids=x, use_cache=False).last_hidden_state
    full = teacher.lm_head(hidden[mask])
    assigned = full[:, :ce.ASSIGNED].contiguous()
    assert assigned.dtype == torch.bfloat16 and torch.isfinite(assigned).all()
    coverage = None
    if inspect_padding:
        total = full.float() / TEMPERATURE
        excluded = (total[:, ce.ASSIGNED:].logsumexp(1) - total.logsumexp(1)).exp()
        alternate = torch.where(mask, x, 0)
        other = teacher.model.language_model(input_ids=alternate, use_cache=False).last_hidden_state
        assert torch.equal(hidden[mask], other[mask]), "teacher valid positions depend on right padding"
        coverage = dict(padding_invariant=True, excluded_mass_max=float(excluded.max()),
                        excluded_mass_mean=float(excluded.mean()), first_targets=len(assigned))
    return assigned, coverage


def tiled_loss(model, h, y, teacher):
    return joint.joint_ce_kl(model, h.unsqueeze(0), y.unsqueeze(0), teacher, temperature=TEMPERATURE,
                             rows=TILE, full_sum=False, assigned_rows=ce.ASSIGNED, fp32_ce=True)


def check_head(model, x, y, distribution):
    mask = y >= 0
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        h = model(x, return_hidden=True)[mask]
    h = h.detach().requires_grad_()
    labels = y[mask]
    params = (h, model.emb.weight, model.emb_up.weight)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        scores = model._head_logits(h)[:, :ce.ASSIGNED].float()
        a = F.cross_entropy(scores, labels)
        b = _kl(scores, distribution, TEMPERATURE, "batchmean") * TEMPERATURE**2
    dense = torch.autograd.grad(a + ALPHA*b, params)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        c, d = tiled_loss(model, h, labels, distribution)
    sliced = torch.autograd.grad(c + ALPHA*d, params)
    receipt = dict(ce_native=float(a.detach()), ce_tiled=float(c.detach()),
                   kl_native=float(b.detach()), kl_tiled=float(d.detach()))
    limits = []
    for name, left, right in zip(("hidden", "embedding", "projection"), dense, sliced, strict=True):
        delta = right.float() - left.float()
        rel = float(torch.linalg.vector_norm(delta) / torch.linalg.vector_norm(left.float()).clamp_min(1e-20))
        limits.append(rel)
        receipt[name] = dict(relative_l2=rel, max_abs=float(delta.abs().max()), exact=torch.equal(left, right))
    receipt["pass"] = abs(receipt["ce_native"] - receipt["ce_tiled"]) <= .001 and abs(
        receipt["kl_native"] - receipt["kl_tiled"]) <= .001 and all(v <= .01 for v in limits)
    ce.qwen.write(OUT / "first_head.json", receipt)
    print("P109_REAL_KL_HEAD", receipt, flush=True)
    model.clear_quant()
    assert receipt["pass"], "first actual batch failed the head comparison"
    return receipt


def train(profile, baseline):
    model = ce.initialize()
    with np.load(ce.DATA, allow_pickle=False) as bundle:
        x, y, draws, held = [torch.from_numpy(bundle[k]).cuda() for k in ("x", "y", "draws", "held")]
    metrics = {"0": ce.frozen_scores(model, x, y, held)}
    assert metrics["0"] == baseline["held_by_update"]["0"]
    teacher = load_teacher(ce.ROOT / profile["teacher"])
    route = ce.build_experimental_optimizers(model, "muon_matched", lr=ce.LR, matrix_lr_mult=ce.MATRIX_MULT)
    optimizers = (route.adamw, route.matrix)
    ce.keep_active_groups(optimizers)
    rates = [[g["lr"] for g in opt.param_groups] for opt in optimizers]
    first, first_support = None, None
    history = []
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    for step, ids in enumerate(draws, 1):
        free, total = torch.cuda.mem_get_info()
        if total-free > DEVICE_BUDGET or (OUT / "STOP").exists() or datetime.now(ce.parent.CUTOFF.tzinfo) >= ce.parent.CUTOFF:
            raise RuntimeError(f"execution bound before update {step}")
        factor = ce.lr_factor(step - 1, ce.WARMUP, ce.UPDATES, "cosine")
        for opt, base in zip(optimizers, rates, strict=True):
            for group, rate in zip(opt.param_groups, base, strict=True):
                group["lr"] = rate*factor
        xb, yb = x[ids], y[ids]
        mask = yb >= 0
        start = perf_counter()
        teacher_rows, coverage = teacher_logits(teacher, xb, mask, inspect_padding=step==1)
        torch.cuda.synchronize()
        teacher_seconds = perf_counter() - start
        if step == 1:
            first_support = coverage
            first = check_head(model, xb, yb, teacher_rows)
            torch.cuda.reset_peak_memory_stats()
        start = perf_counter()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            h = model(xb, return_hidden=True)[mask]
            primary, kd = tiled_loss(model, h, yb[mask], teacher_rows)
        loss = primary + ALPHA*kd
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
        for opt in optimizers:
            opt.step()
            opt.zero_grad(set_to_none=True)
        model.clear_quant()
        torch.cuda.synchronize()
        history.append(dict(step=step, ce=float(primary.detach()), kl=float(kd.detach()),
                            gradient_norm=float(norm), targets=len(teacher_rows), teacher_seconds=teacher_seconds,
                            seconds=teacher_seconds + perf_counter() - start))
        del teacher_rows, h, primary, kd, loss, norm
        if step in (16, 32, 64, ce.UPDATES):
            metrics[str(step)] = ce.frozen_scores(model, x, y, held)
            print("P109_REAL_KL_TRAIN", step, metrics[str(step)], flush=True)
    assert sum(row["targets"] for row in history) == profile["targets"]
    old, new = baseline["held_by_update"][str(ce.UPDATES)], metrics[str(ce.UPDATES)]
    delta = {lang: new[lang]["nll"] - old[lang]["nll"] for lang in old}
    count = sum(new[lang]["correct"] - old[lang]["correct"] for lang in old)
    return dict(history=history, held_by_update=metrics, baseline_final=old, held_nll_delta=delta,
                held_top1_delta=count, candidate=all(v<0 for v in delta.values()) and count>=0, first_head=first,
                teacher_support=first_support, training_peak_allocated=torch.cuda.max_memory_allocated(),
                training_peak_reserved=torch.cuda.max_memory_reserved(), checkpoint_writes=0,
                median_update_seconds=median(r["seconds"] for r in history[ce.WARMUP:]),
                median_teacher_seconds=median(r["teacher_seconds"] for r in history[ce.WARMUP:]))


def run():
    assert ce.idle() and torch.cuda.device_count() == 1
    free, _ = torch.cuda.mem_get_info()
    assert free >= 13_000*2**20
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    profile = ce.qwen.load(PROFILE)
    baseline = verify(profile)
    samples = OUT / "device_100ms.csv"
    ce.qwen.write(OUT / "active.json", dict(tag=TAG, pid=os.getpid()))
    with samples.open("xb") as stream:
        monitor = subprocess.Popen((*ce.DEVICE, f"--loop-ms={ce.INTERVAL_MS}"), stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                result = train(profile, baseline)
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    verify(profile)
    observed = ce.read_samples(samples)
    assert observed
    result.update(device_peak=max(observed, key=lambda row: row["occupied_mib"]),
                  device_samples=len(observed), source_preserved=True, profile_sha256=ce.qwen.digest(PROFILE))
    ce.qwen.write(OUT / "report.json", result)
    print("P109_REAL_KL_RESULT", result["held_nll_delta"], result["held_top1_delta"], result["device_peak"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if phase == "prepare" else "0")
    assert datetime.now(ce.parent.CUTOFF.tzinfo) + timedelta(seconds=400) < ce.parent.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (prepare if phase == "prepare" else run)()
