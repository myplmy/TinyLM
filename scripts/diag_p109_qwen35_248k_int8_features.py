"""Train the existing warm G4 arm with an INT8 cache for frozen teacher features."""

import argparse
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from statistics import median
import subprocess
from time import perf_counter, time
from unittest.mock import patch

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_qwen35_248k_cached_kl as baseline


online, ce = baseline.online, baseline.ce
ROOT, io = ce.ROOT, ce.qwen
TAG = "p109_qwen35_248k_int8_features_v1_20261119"
OUT = ce.OUT.with_name(TAG)
OUT_OUTLIERS = ce.OUT.with_name("p109_qwen35_248k_int8_outliers8_v1_20261119")
PLAN = ROOT / "test_plan/P109_16층-공유-재귀-프리셋-통합.md"
REFERENCE = baseline.OUT / "report.json"
CUTOFF = datetime.fromisoformat("2026-11-20T16:58:00+09:00").timestamp()


def authority(out, reserve=0):
    if time() + reserve >= CUTOFF or (out / "STOP").exists():
        raise RuntimeError("outside the approved INT8 teacher-cache experiment or stopped")


def identity(path):
    st = path.stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def prepare():
    authority(OUT, 330)
    teacher_profile = io.load(online.PROFILE)
    ce_profile = io.load(ce.PROFILE)
    reference = io.load(REFERENCE)
    if (reference["cache"]["selected"] != "batch4_width96_exact" or
            reference["profile_sha256"] != io.digest(baseline.PROFILE) or len(reference["history"]) != ce.UPDATES):
        raise ValueError("previous BF16-cache result does not match the original shape")
    expected = {}
    for previous in (teacher_profile, ce_profile, io.load(baseline.PROFILE)):
        for name, digest in previous["pins"].items():
            if name in expected and expected[name] != digest:
                raise ValueError(f"previous source receipts disagree for {name}")
            expected[name] = digest
    expected[str(ce.parent.PARENT.relative_to(ROOT))] = ce_profile["parent_sha256"]
    expected[str(ce.MAPPING.relative_to(ROOT))] = ce_profile["mapping_sha256"]
    expected[str(ce.DATA.relative_to(ROOT))] = ce_profile["tokens_sha256"]
    inputs = (Path(__file__), PLAN, REFERENCE, baseline.PROFILE, online.PROFILE, ce.PROFILE, Path(ce.__file__))
    for path in inputs:
        name = str(path.relative_to(ROOT))
        if name not in expected:
            expected[name] = io.digest(path)
    sealed = {}
    for name, digest in expected.items():
        path = ROOT / name
        before = identity(path)
        if io.digest(path) != digest or identity(path) != before:
            raise ValueError(f"the pinned experimental source changed: {name}")
        sealed[name] = dict(sha256=digest, identity=before)
    with np.load(ce.DATA, allow_pickle=False) as data:
        x, y, draws, held = (data[k] for k in ("x", "y", "draws", "held"))
    if (x.shape != y.shape or draws.shape != (ce.UPDATES, ce.BATCH) or x.shape[1] != ce.WIDTH
            or held.shape != (2, 24) or np.unique(draws).size != draws.size
            or np.intersect1d(draws, held).size or int((y[draws] >= 0).sum()) != teacher_profile["targets"]
            or np.any((x < 0) | (x >= ce.ASSIGNED)) or np.any(y >= ce.ASSIGNED)):
        raise ValueError("frozen sample order, targets, or held-out split changed")
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU preparation initialized CUDA")
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(PLAN.read_bytes())
    io.write(OUT / "profile.json", dict(tag=TAG, approval="WIP177", sources=sealed,
             teacher=teacher_profile["teacher"], targets=teacher_profile["targets"], hidden=1024,
             updates=ce.UPDATES, batch=ce.BATCH, width=ce.WIDTH, temperature=online.TEMPERATURE,
             alpha=online.ALPHA, outliers=0, mode="SYMMETRIC_INT8_PER_TARGET_FP32_SCALE"))
    print("P109_INT8_PREFLIGHT", draws.size, teacher_profile["targets"], len(sealed), flush=True)


def check_sources(profile):
    for path, record in profile["sources"].items():
        if identity(ROOT / path) != record["identity"]:
            raise ValueError(f"source identity changed during the experiment: {path}")


def prepare_outliers():
    authority(OUT_OUTLIERS, 330)
    original_profile = OUT / "profile.json"
    original_result = OUT / "report.json"
    profile = io.load(original_profile)
    measured = io.load(original_result)
    if (measured["quality_kept"] or not measured["source_preserved"] or
            len(measured["history"]) != ce.UPDATES or measured["profile_sha256"] != io.digest(original_profile)):
        raise ValueError("the plain INT8 result is not the expected negative control")
    for current, snapshot in ((Path(__file__), OUT/"runner_at_execution.py"), (PLAN, OUT/"plan_at_execution.md")):
        key = str(current.relative_to(ROOT))
        if io.digest(snapshot) != profile["sources"][key]["sha256"]:
            raise ValueError(f"previous source snapshot differs: {key}")
        profile["sources"][key] = dict(sha256=io.digest(current), identity=identity(current))
    for source in (original_profile, original_result, OUT/"plan_at_execution.md", OUT/"runner_at_execution.py"):
        profile["sources"][str(source.relative_to(ROOT))] = dict(sha256=io.digest(source), identity=identity(source))
    profile.update(tag=OUT_OUTLIERS.name, outliers=8, mode="INT8_WITH_EIGHT_EXACT_BF16_OUTLIERS")
    check_sources(profile)
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU preparation initialized CUDA")
    OUT_OUTLIERS.mkdir()
    (OUT_OUTLIERS / "plan_at_execution.md").write_bytes(PLAN.read_bytes())
    io.write(OUT_OUTLIERS / "profile.json", profile)
    print("P109_INT8_OUTLIER_PREFLIGHT", profile["targets"], profile["outliers"], flush=True)


def device_gate(out):
    authority(out, 5)
    free, total = torch.cuda.mem_get_info()
    if total - free > online.DEVICE_BUDGET:
        raise RuntimeError("device occupancy beyond the existing 13GB bound")


def unpack(codes, scales, indices, exact):
    restored = (codes.float() * scales).to(torch.bfloat16)
    if indices.shape[1]:
        restored.scatter_(1, indices.to(torch.long), exact)
    return restored


@dataclass
class QuantizedTeacherCache:
    head: torch.nn.Module
    x: torch.Tensor
    mask: torch.Tensor
    codes: torch.Tensor
    scales: torch.Tensor
    indices: torch.Tensor
    exact: torch.Tensor
    offsets: tuple[int, ...]
    step: int = 0

    @torch.no_grad()
    def logits(self, x, mask):
        index = self.step
        if (index >= len(self.offsets) - 1 or not torch.equal(x, self.x[index])
                or not torch.equal(mask, self.mask[index])):
            raise ValueError("student and cached teacher have different training positions")
        block = slice(self.offsets[index], self.offsets[index + 1])
        features = unpack(self.codes[block], self.scales[block], self.indices[block], self.exact[block])
        logits = self.head(features)[:, :ce.ASSIGNED].contiguous()
        if logits.dtype != torch.bfloat16 or not torch.isfinite(logits).all():
            raise ValueError("compact teacher logits were nonfinite or changed dtype")
        self.step += 1
        return logits


@torch.no_grad()
def collect(out, profile, x, y, draws):
    teacher = online.load_teacher(ROOT / profile["teacher"])
    inputs, mask = x[draws], y[draws] >= 0
    flat_mask = mask.flatten(1)
    counts = flat_mask.sum(dim=1).cpu().tolist()
    offsets = tuple(np.cumsum([0, *counts]).tolist())
    if offsets[-1] != profile["targets"] or teacher.lm_head.in_features != profile["hidden"]:
        raise ValueError("teacher feature geometry changed")
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    start = perf_counter()
    codes = torch.empty((offsets[-1], profile["hidden"]), device=x.device, dtype=torch.int8)
    scales = torch.empty((offsets[-1], 1), device=x.device, dtype=torch.float32)
    outliers = profile.get("outliers", 0)
    indices = torch.empty((offsets[-1], outliers), device=x.device, dtype=torch.int16)
    exact = torch.empty((offsets[-1], outliers), device=x.device, dtype=torch.bfloat16)
    squares = torch.zeros(2, device=x.device)
    maximum = torch.zeros((), device=x.device)
    first = None
    for step, (left, right) in enumerate(zip(offsets, offsets[1:]), 0):
        device_gate(out)
        valid = teacher.model.language_model(input_ids=inputs[step], use_cache=False).last_hidden_state[mask[step]]
        if valid.shape[0] != right - left or valid.dtype != torch.bfloat16:
            raise ValueError("teacher hidden positions or dtype changed")
        values = valid.float()
        quantized_values = values
        if outliers:
            kept = values.abs().topk(outliers, dim=1, sorted=False).indices
            indices[left:right].copy_(kept)
            exact[left:right].copy_(valid.gather(1, kept))
            quantized_values = values.scatter(1, kept, 0.)
        scale = (quantized_values.abs().amax(dim=1, keepdim=True) / 127).clamp_min(torch.finfo(torch.float32).tiny)
        codes[left:right].copy_((quantized_values / scale).round().clamp(-127, 127).to(torch.int8))
        scales[left:right].copy_(scale)
        restored = unpack(codes[left:right], scales[left:right], indices[left:right], exact[left:right])
        delta = values - restored.float()
        squares[0] += values.square().sum()
        squares[1] += delta.square().sum()
        maximum = torch.maximum(maximum, delta.abs().max())
        if step == 0:
            first = valid.clone()
    torch.cuda.synchronize()
    stored_bytes = sum(t.numel()*t.element_size() for t in (codes, scales, indices, exact))
    audit = dict(seconds=perf_counter()-start, bytes=stored_bytes, outliers=outliers,
                 targets=offsets[-1], per_target_bytes=stored_bytes//offsets[-1],
                 feature_relative_l2=float((squares[1] / squares[0]).sqrt()), max_abs=float(maximum),
                 peak_allocated=torch.cuda.max_memory_allocated(), peak_reserved=torch.cuda.max_memory_reserved())
    detect_start = perf_counter()
    original = teacher.lm_head(first)[:, :ce.ASSIGNED]
    first_block = slice(0, counts[0])
    compact = teacher.lm_head(unpack(codes[first_block], scales[first_block],
                                     indices[first_block], exact[first_block]))[:, :ce.ASSIGNED]
    audit.update(first_targets=counts[0], first_teacher_same_top1=int(original.argmax(1).eq(compact.argmax(1)).sum()),
                 first_logits_max_abs=float((original.float()-compact.float()).abs().max()),
                 first_head_audit_seconds=perf_counter()-detect_start)
    if not np.isfinite(audit["feature_relative_l2"]):
        raise ValueError("teacher quantization features were nonfinite")
    io.write(out / "cache.json", audit)
    print("P109_INT8_CACHE", audit, flush=True)
    return QuantizedTeacherCache(teacher.lm_head, inputs, mask, codes, scales, indices, exact, offsets), audit


def train(out, cache, x, y, draws, held, reference):
    model = ce.initialize()
    metrics = {"0": ce.frozen_scores(model, x, y, held)}
    if metrics["0"] != reference["held_by_update"]["0"]:
        raise ValueError("initial student scores do not reproduce the existing reference")
    before = model.emb_up.weight.detach()[:16, :16].clone()
    route = ce.build_experimental_optimizers(model, "muon_matched", lr=ce.LR, matrix_lr_mult=ce.MATRIX_MULT)
    optimizers = (route.adamw, route.matrix)
    ce.keep_active_groups(optimizers)
    rates = [[group["lr"] for group in opt.param_groups] for opt in optimizers]
    history = []
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    for step, rows in enumerate(draws, 1):
        device_gate(out)
        factor = ce.lr_factor(step-1, ce.WARMUP, ce.UPDATES, "cosine")
        for opt, base in zip(optimizers, rates, strict=True):
            for group, rate in zip(opt.param_groups, base, strict=True):
                group["lr"] = rate * factor
        xb, yb = x[rows], y[rows]
        mask = yb >= 0
        start = perf_counter()
        teacher = cache.logits(xb, mask)
        torch.cuda.synchronize()
        head_seconds = perf_counter()-start
        if step == 1:
            with patch.object(online, "OUT", out):
                online.check_head(model, xb, yb, teacher)
            torch.cuda.reset_peak_memory_stats()
        start = perf_counter()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            hidden = model(xb, return_hidden=True)[mask]
            primary, kd = online.tiled_loss(model, hidden, yb[mask], teacher)
        loss = primary + online.ALPHA*kd
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
        for opt in optimizers:
            opt.step()
            opt.zero_grad(set_to_none=True)
        model.clear_quant()
        torch.cuda.synchronize()
        history.append(dict(step=step, ce=float(primary.detach()), kl=float(kd.detach()), gradient_norm=float(norm),
                            targets=len(teacher), teacher_seconds=head_seconds, seconds=head_seconds+perf_counter()-start))
        del teacher, hidden, primary, kd, loss, norm
        if step in (16, 32, 64, ce.UPDATES):
            metrics[str(step)] = ce.frozen_scores(model, x, y, held)
            print("P109_INT8_TRAIN", step, metrics[str(step)], flush=True)
    changed = int(torch.count_nonzero(before != model.emb_up.weight.detach()[:16, :16]))
    if cache.step != ce.UPDATES or not changed:
        raise ValueError("student training or feature schedule did not advance")
    return dict(history=history, held_by_update=metrics, projection_sample_cells_changed=changed,
                training_peak_allocated=torch.cuda.max_memory_allocated(),
                training_peak_reserved=torch.cuda.max_memory_reserved())


def run(out):
    authority(out, 310)
    profile = io.load(out / "profile.json")
    check_sources(profile)
    reference = io.load(REFERENCE)
    if not ce.idle() or torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 13000*2**20:
        raise RuntimeError("the single approved GPU is not free")
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    device = out / "device_100ms.csv"
    io.write(out / "active.json", dict(tag=profile["tag"], pid=os.getpid()))
    with device.open("xb") as stream:
        monitor = subprocess.Popen((*ce.DEVICE, f"--loop-ms={ce.INTERVAL_MS}"), stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH), np.load(ce.DATA, allow_pickle=False) as pool:
                x, y, draws, held = (torch.from_numpy(pool[k]).cuda() for k in ("x", "y", "draws", "held"))
                cache, audit = collect(out, profile, x, y, draws)
                torch.cuda.empty_cache()
                report = train(out, cache, x, y, draws, held, reference)
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    check_sources(profile)
    if sum(row["targets"] for row in report["history"]) != profile["targets"]:
        raise ValueError("the measured updates use a different set of target positions")
    old = reference["held_by_update"][str(ce.UPDATES)]
    final = report["held_by_update"][str(ce.UPDATES)]
    nll = {lang: final[lang]["nll"]-old[lang]["nll"] for lang in old}
    top1 = sum(final[lang]["correct"]-old[lang]["correct"] for lang in old)
    samples = ce.read_samples(device)
    report.update(cache=audit, baseline_bf16_bytes=reference["cache"]["bytes"],
                  baseline_final=old, nll_delta_vs_bf16=nll, top1_delta_vs_bf16=top1,
                  quality_kept=max(nll.values()) <= .015 and top1 >= -2,
                  update_seconds=sum(row["seconds"] for row in report["history"]),
                  median_update_seconds=median(row["seconds"] for row in report["history"][ce.WARMUP:]),
                  device_peak=max(samples, key=lambda row: row["occupied_mib"]), source_preserved=True,
                  device_samples=len(samples), checkpoint_writes=0, profile_sha256=io.digest(out / "profile.json"))
    io.write(out / "report.json", report)
    print("P109_INT8_RESULT", nll, top1, report["quality_kept"], report["device_peak"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    parser.add_argument("--outliers", choices=(0, 8), type=int, default=0)
    args = parser.parse_args()
    phase = args.phase
    if os.environ.get("CUDA_VISIBLE_DEVICES") != ("" if phase == "prepare" else "0"):
        parser.error("the explicitly isolated CPU or single GPU is required")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if phase == "prepare":
        (prepare_outliers if args.outliers else prepare)()
    else:
        run(OUT_OUTLIERS if args.outliers else OUT)


if __name__ == "__main__":
    main()
