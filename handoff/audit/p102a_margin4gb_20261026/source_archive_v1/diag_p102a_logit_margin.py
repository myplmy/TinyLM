#!/usr/bin/env python3
"""Frozen CPU model observations and bounded CUDA CE, never model training."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "P102A_FROZEN_MARGIN_4GB_V1"
SOURCE_FILES = (
    "scripts/diag_p102a_logit_margin.py", "scripts/test_p102a_logit_margin.py",
    "scripts/p106b_weight_route.py", "scripts/interactive_research_infer.py",
    "tinylm/config.py", "tinylm/model/__init__.py", "tinylm/model/transformer.py",
    "tinylm/model/modules.py", "tinylm/model/ternary.py", "tinylm/train/mtp_sft.py",
)


class ResourceHold(RuntimeError):
    pass


def need(value, message):
    if not value:
        raise ValueError(message)


def safe(name):
    p = ROOT / name
    need(not Path(name).is_absolute() and ".." not in Path(name).parts, "relative owned path required")
    need(not name.startswith(("datasets/TinyDataset/", ".codex/", ".agents/", ".aws/")), "protected input")
    need(not any(q.is_symlink() for q in (p, *p.parents)), "symlink path")
    return p


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def identity():
    files = {name: digest(safe(name)) for name in SOURCE_FILES}
    raw = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return dict(files=files, sha256=hashlib.sha256(raw).hexdigest().upper())


def write_new(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + chr(10)).encode()
    need(len(raw) < 20_000_000 and not path.exists(), "fresh evidence below 20MB required")
    with path.open("xb") as stream:
        stream.write(raw)


class Budget:
    def __init__(self, seconds):
        self.start = time.monotonic()
        self.seconds = seconds

    def check(self):
        if time.monotonic() - self.start > self.seconds:
            raise TimeoutError("internal diagnostic time budget exhausted")


def choose_updates(count, total):
    need(type(count) is int and 1 < count <= total, "at least two nonduplicate crops required")
    return [i * (total - 1) // (count - 1) for i in range(count)]


def choose_probes(margins):
    order = sorted(range(len(margins)), key=lambda i: (margins[i], i))
    need(len(order) >= 32, "probe needs at least32 positions")
    middle = len(order) // 2
    chosen = order[:4] + order[middle - 2:middle + 2] + order[-8:]
    need(len(set(chosen)) == 16, "probe positions overlap")
    return chosen


def reference_rows(logits, labels):
    """Target-excluded FP64 reference for exactly the supplied stored logits."""
    import torch
    import torch.nn.functional as F
    z = logits.detach().double().cpu().clone()
    y = labels.detach().long().cpu()
    need(z.ndim == 2 and y.shape == z.shape[:1] and z.shape[1] > 1, "shape mismatch")
    need(bool(torch.isfinite(z).all()) and bool(((y >= 0) & (y < z.shape[1])).all()), "invalid logits/labels")
    target = z.gather(1, y[:, None]).squeeze(1)
    z.scatter_(1, y[:, None], -torch.inf)
    margin = target - torch.logsumexp(z, dim=1)
    return margin, F.softplus(-margin), -torch.sigmoid(-margin)


def observe_ce(logits, labels):
    import torch
    import torch.nn.functional as F
    from tinylm.train.mtp_sft import ce_sum
    z = logits.detach().clone().requires_grad_(True)
    value = ce_sum(z, labels)
    gradient = torch.autograd.grad(value, z)[0]
    target_grad = gradient.gather(1, labels[:, None]).squeeze(1).double().cpu()
    margin, reference_loss, reference_grad = reference_rows(logits, labels)
    stock_loss = F.cross_entropy(logits.detach().float(), labels, reduction="none").double().cpu()
    need(bool(torch.isfinite(target_grad).all()) and math.isfinite(float(value.detach())), "nonfinite CE")
    return dict(targets=len(labels), margin=margin.tolist(), target_grad=target_grad.tolist(),
        zero_target_gradient_with_nonzero_reference=int(((target_grad == 0) & (reference_grad != 0)).sum()),
        zero_forward_loss_with_nonzero_reference=int(((stock_loss == 0) & (reference_loss != 0)).sum()),
        fp64_reference_underflow_positions=int((reference_grad == 0).sum()),
        target_grad_abs_error_max=float((target_grad - reference_grad).abs().max()),
        forward_abs_error_max=float((stock_loss - reference_loss).abs().max()),
        stock_loss_sum=float(value.detach()), reference_loss_sum=float(reference_loss.sum()),
        dtype=str(logits.dtype), gradient_dtype=str(gradient.dtype), vocab=logits.shape[1])


def summarize(rows):
    margins = sorted(x for row in rows for x in row["margin"])
    need(bool(margins), "zero observed targets is not completion")
    points = {str(q): margins[min(len(margins) - 1, int(q * (len(margins) - 1)))]
              for q in (0, .5, .9, .99, 1)}
    return dict(targets=sum(r["targets"] for r in rows), margin_quantiles=points,
        margin_at_least_log2pow24=sum(m >= 24 * math.log(2) for m in margins),
        zero_target_gradient_with_nonzero_reference=sum(r["zero_target_gradient_with_nonzero_reference"] for r in rows),
        zero_forward_loss_with_nonzero_reference=sum(r["zero_forward_loss_with_nonzero_reference"] for r in rows),
        fp64_reference_underflow_positions=sum(r["fp64_reference_underflow_positions"] for r in rows),
        target_grad_abs_error_max=max(r["target_grad_abs_error_max"] for r in rows),
        forward_abs_error_max=max(r["forward_abs_error_max"] for r in rows))


def memory_point():
    call = subprocess.run(["/usr/lib/wsl/lib/nvidia-smi", "--id=0",
        "--query-gpu=memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5)
    if call.returncode:
        raise ResourceHold("NVML memory query unavailable: " + call.stderr[:200])
    try:
        total, used, free = [int(x.strip()) for x in call.stdout.strip().split(",")]
    except ValueError as error:
        raise ResourceHold("NVML numeric memory fields unavailable") from error
    return dict(total_mib=total, used_mib=used, free_mib=free)


def admit_point(point, cap_bytes, reserve_mib=0):
    if (point["used_mib"] + reserve_mib) * 2**20 >= cap_bytes:
        raise ResourceHold("conservative global VRAM cap or context reserve exceeded")


def check_refs(spec, budget, *, full_corpus):
    for ref in [spec["tokenizer"], *(m["checkpoint"] for m in spec["models"]),
                *(m["closed_report"] for m in spec["models"]),
                *(m["updates_file"] for m in spec["models"])]:
        need(digest(safe(ref["path"])) == ref["sha256"], "immutable input SHA changed: " + ref["path"])
        budget.check()
    corpus = spec["corpus"]
    need(safe(corpus["path"]).stat().st_size == corpus["tokens"] * 2 == corpus["bytes"], "uint16 pool shape")
    if full_corpus:
        need(digest(safe(corpus["path"])) == corpus["sha256"], "frozen corpus SHA changed")
        budget.check()


def cpu_observations(spec, output, budget):
    import numpy as np
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from scripts import p106b_weight_route as route_module
    from scripts.interactive_research_infer import state_fingerprint
    torch.set_num_threads(spec["cpu_threads"])
    tokens = np.memmap(safe(spec["corpus"]["path"]), dtype=np.uint16, mode="r")
    selected = choose_updates(spec["crops"], 2289)
    offsets = []
    for model in spec["models"]:
        with safe(model["updates_file"]["path"]).open() as stream:
            updates = [json.loads(line) for line in stream]
        need(len(updates) == 2289, "closed complete update ledger required")
        current = [updates[i]["offsets"][0] for i in selected]
        need(not offsets or current == offsets, "matched models saw different selected offsets")
        offsets = current
    proofs, probes = [], []
    for item in spec["models"]:
        began = time.monotonic()
        payload = torch.load(safe(item["checkpoint"]["path"]), map_location="cpu", weights_only=True)
        need(payload["cfg"] == item["cfg"] and payload["step"] == 2289
             and payload["tokenizer_sha256"] == spec["tokenizer"]["sha256"], "closed checkpoint metadata")
        cfg = TMTConfig(**payload["cfg"])
        need(cfg.n_layers == 14 and cfg.vocab_size == 32768 and cfg.max_seq_len == 1024
             and not cfg.mtp_aux and not cfg.tie_mlp and cfg.infer_repeat == cfg.train_repeat == 1, "fixed native route")
        model = TiedMLPTransformer(cfg)
        model_rows = []
        try:
            with route_module.weight_route(model, "ternary") as route:
                route_module.load_routed_state(model, payload, "ternary")
                payload = None
                model.eval()
                model.set_anneal(1.)
                with torch.no_grad():
                    model.freeze_quant()
                before = state_fingerprint(model)
                need(before == item["final_core_sha256"], "loaded CPU core differs")
                for index, offset in enumerate(offsets):
                    budget.check()
                    ids = tokens[offset:offset + spec["seq"] + 1].astype(np.int64)
                    need(len(ids) == 1025 and int(ids.max()) < cfg.vocab_size, "exact full crop required")
                    x = torch.from_numpy(ids[:-1].copy())[None]
                    y = torch.from_numpy(ids[1:].copy())
                    with torch.no_grad(), sdpa_kernel(SDPBackend.MATH):
                        logits = model(x, use_cache=False)[0]
                    need(logits.shape == (1024, 32768) and logits.dtype == torch.float32, "CPU full FP32 logits")
                    parts = []
                    for start in range(0, 1024, 32):
                        parts.append(observe_ce(logits[start:start + 32], y[start:start + 32]))
                        budget.check()
                    row = dict(model=item["id"], crop=index, update=selected[index] + 1,
                        offset=offset, ids_sha256=hashlib.sha256(ids.astype("<i8").tobytes()).hexdigest().upper(),
                        summary=summarize(parts), targets=1024,
                        margin=[v for p in parts for v in p["margin"]],
                        zero_target_gradient_with_nonzero_reference=sum(p["zero_target_gradient_with_nonzero_reference"] for p in parts),
                        zero_forward_loss_with_nonzero_reference=sum(p["zero_forward_loss_with_nonzero_reference"] for p in parts),
                        fp64_reference_underflow_positions=sum(p["fp64_reference_underflow_positions"] for p in parts),
                        target_grad_abs_error_max=max(p["target_grad_abs_error_max"] for p in parts),
                        forward_abs_error_max=max(p["forward_abs_error_max"] for p in parts))
                    chosen = choose_probes(row["margin"])
                    probes.append(dict(model=item["id"], crop=index, positions=chosen,
                        logits=logits[chosen].clone(), labels=y[chosen].clone()))
                    model_rows.append(row)
                    write_new(output / (item["id"] + "_crop_%02d.json" % index), row)
                    print(json.dumps(dict(phase="CPU_CROP", model=item["id"], crop=index,
                                         max_margin=row["summary"]["margin_quantiles"]["1"])), flush=True)
                    del logits, x, y, parts
                route.assert_active()
                need(state_fingerprint(model) == before
                     and all(p.grad is None and p.device.type == "cpu" for p in model.parameters()),
                     "frozen model weights or gradients changed")
                proofs.append(dict(model=item["id"], core_sha256=before, unchanged=True,
                    model_device="cpu", optimizer_steps=0, summary=summarize(model_rows),
                    wall_sec=time.monotonic() - began))
                model.clear_quant()
        finally:
            model = payload = None
            gc.collect()
    del tokens
    return proofs, probes


def gpu_observations(spec, probes, budget):
    import torch
    result = dict(status="NOT_RUN", points=[], rows=[], allocator_cap_bytes=spec["gpu_allocator_cap_bytes"],
                  global_observed_cap_bytes=spec["gpu_global_observed_cap_bytes"], model_runs=0)
    point = memory_point()
    admit_point(point, spec["gpu_global_observed_cap_bytes"], spec["gpu_context_reserve_mib"])
    result["points"].append(point)
    need(torch.cuda.is_available(), "CUDA unavailable")
    torch.cuda.set_per_process_memory_fraction(spec["gpu_allocator_cap_bytes"] / (point["total_mib"] * 2**20), 0)
    torch.cuda.reset_peak_memory_stats()
    z = y = None
    try:
        for probe in probes:
            budget.check()
            point = memory_point()
            result["points"].append(point)
            admit_point(point, spec["gpu_global_observed_cap_bytes"])
            z = probe["logits"].to("cuda")
            y = probe["labels"].to("cuda")
            observed = observe_ce(z, y)
            torch.cuda.synchronize()
            observed.update(model=probe["model"], crop=probe["crop"], positions=probe["positions"],
                            selected_probe_not_population=True)
            result["rows"].append(observed)
            z = y = None
            point = memory_point()
            result["points"].append(point)
            admit_point(point, spec["gpu_global_observed_cap_bytes"])
        result.update(status="COMPLETE", selected_rows=sum(row["targets"] for row in result["rows"]),
            peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            whole_device_sampled_peak_mib=max(p["used_mib"] for p in result["points"]),
            continuous_device_peak_verified=False, process_total_memory_verified=False)
        need(result["peak_reserved_bytes"] <= spec["gpu_allocator_cap_bytes"], "allocator cap violated")
        return result
    finally:
        z = y = None
        gc.collect()
        torch.cuda.empty_cache()
        result["cleanup_allocated_bytes"] = torch.cuda.memory_allocated()
        result["cleanup_reserved_bytes"] = torch.cuda.memory_reserved()
        need(result["cleanup_allocated_bytes"] == result["cleanup_reserved_bytes"] == 0,
             "owned CUDA tensors remain after numerical phase")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--source-sha256")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    profile_path = safe(args.profile)
    need(digest(profile_path) == args.profile_sha256.upper(), "profile pin mismatch")
    spec = json.loads(profile_path.read_text())
    need(spec["schema"] == "P102A_FROZEN_MARGIN_4GB_PROFILE_V1"
         and spec["gpu_allocator_cap_bytes"] == 134217728
         and spec["gpu_global_observed_cap_bytes"] == 4_000_000_000
         and spec["crops"] == 16 and spec["seq"] == 1024 and spec["updates"] == 0
         and len(spec["models"]) == 2 and spec["max_wall_sec"] == 900, "fixed diagnostic policy differs")
    source = identity()
    if not args.execute:
        print(json.dumps(dict(schema=SCHEMA, status="CHECK_ONLY_NO_MODEL", source=source,
                              profile_sha256=args.profile_sha256), indent=2))
        return 0
    need(args.source_sha256 == source["sha256"], "current source pin required")
    output = safe(spec["output"])
    need(output.parts[-1] == spec["tag"] and not output.exists(), "fresh exact output required")
    output.mkdir(parents=True)
    budget = Budget(spec["max_wall_sec"])
    report = dict(schema=SCHEMA, status="STARTED", source=source, profile_sha256=args.profile_sha256,
        cpu=[], gpu=dict(status="NOT_RUN"), optimizer_steps=0, checkpoint_writes=0,
        model_training=0, model_quality_claim=False, historical_training_margin_measured=False,
        full_corpus_coverage=False)
    code = 1
    try:
        check_refs(spec, budget, full_corpus=True)
        report["cpu"], probes = cpu_observations(spec, output, budget)
        report["gpu"] = gpu_observations(spec, probes, budget)
        check_refs(spec, budget, full_corpus=True)
        need(identity() == source and digest(profile_path) == args.profile_sha256.upper(), "source/profile changed")
        budget.check()
        report.update(status="NUMERIC_OBSERVATION_COMPLETE", inputs_and_sources_unchanged=True)
        code = 0
    except ResourceHold as error:
        report.update(status="RESOURCE_HOLD", error=str(error))
        code = 8
    except Exception as error:
        report.update(status="ERROR", error_type=type(error).__name__, error=str(error))
    finally:
        report.update(returncode=code, wall_sec=time.monotonic() - budget.start)
        write_new(output / "report.json", report)
    print(json.dumps(dict(status=report["status"], returncode=code, output=str(output.relative_to(ROOT)))), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
