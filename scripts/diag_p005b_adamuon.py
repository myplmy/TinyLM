#!/usr/bin/env python3
"""Bounded AdaMuon equations/state/GPU cost, never body training or quality.

Capture one FP32 microbatch gradient from an immutable completed model, then
update disposable parameter copies. No model/checkpoint weights are updated or
saved. The common gradient is one microbatch, not an accum16 training update.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diag_p106b_resource_matrix as support

SCHEMA = "P005B_ADAMUON_GPU_COST_V1"
PROFILE = "P005B_ADAMUON_GPU_PROFILE_V1"
TAG = "p005b_adamuon_gradient_cost_v1_20261027"
OWN = ("scripts/diag_p005b_adamuon.py", "scripts/test_p005b_adamuon.py",
    "scripts/test_adamuon.py", "tinylm/train/adamuon.py", "tinylm/train/muon.py",
    "tinylm/train/normuon.py", "tinylm/train/mtp_sft.py")
need = support.need


def identity():
    files = dict(support.identity()["files"])
    files.update({name: support.digest(support.safe(name)) for name in OWN})
    return dict(files=files, sha256=support.sha(files))


def tensor_signature(values):
    h = hashlib.sha256()
    for name, value in values:
        h.update(name.encode())
        if value is None:
            h.update(b"NONE")
        else:
            cpu = value.detach().cpu().contiguous()
            h.update(str((tuple(cpu.shape), str(cpu.dtype))).encode())
            h.update(cpu.view(-1).view(__import__("torch").uint8).numpy().tobytes())
    return h.hexdigest().upper()


def catalog(model):
    from tinylm.train.adamuon import parameter_groups
    from tinylm.train.muon import split_params
    matrix, other_groups = parameter_groups(model, weight_decay=.1)
    baseline, _ = split_params(model)
    need({id(p) for p in matrix} == {id(p) for p in baseline}, "matched native model matrix grouping differs")
    matrix_ids = {id(p) for p in matrix}
    decay = {id(p): group["weight_decay"] for group in other_groups for p in group["params"]}
    rows = []
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            rows.append(dict(name=name, shape=list(parameter.shape), elements=parameter.numel(),
                matrix=id(parameter) in matrix_ids, adamw_decay=decay.get(id(parameter))))
    need(sum(r["matrix"] for r in rows) == len(matrix)
        and len({r["name"] for r in rows}) == len(rows), "unique full parameter catalog required")
    return rows


def capture(spec, profile, budget, proof):
    import numpy as np
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from tinylm.train.mtp_sft import ce_sum
    old = support.read_ref(profile["gradient_source_profile"])
    ref = old["corpus"]
    corpus = support.safe(ref["path"])
    need(support.digest(corpus) == ref["sha256"], "original read-only corpus bytes differ")
    updates = support.safe(old["models"][0]["updates_file"]["path"])
    need(support.digest(updates) == old["models"][0]["updates_file"]["sha256"], "closed real update offsets differ")
    with updates.open() as stream:
        first = json.loads(next(stream))
    offsets = first["offsets"][:8]
    need(len(offsets) == 8 and all(type(x) is int and x >= 0 for x in offsets), "eight original microbatch offsets required")
    tokens = np.memmap(corpus, dtype=np.uint16, mode="r")
    values = np.stack([tokens[offset:offset + 1025].astype(np.int64) for offset in offsets])
    need(values.shape == (8, 1025) and int(values.max()) < 32768, "exact8x1024 next-token batch required")
    del tokens
    loaded_proof = proof["original_model"] = {}
    before = time.perf_counter()
    model = cfg = tok = route = logits = loss = x = y = None
    try:
        with support.frozen_model(spec, profile["tokenizer"], "cuda", budget, loaded_proof) as (model, cfg, tok, route):
            rows = catalog(model)
            # Rebuild the existing STE graph without applying an optimizer to
            # the original model. Cached frozen tensors have no STE graph.
            model.clear_quant()
            model.train()
            model.zero_grad(set_to_none=True)
            x = torch.from_numpy(values[:, :-1].copy()).cuda()
            y = torch.from_numpy(values[:, 1:].copy()).cuda()
            torch.cuda.synchronize()
            tick = time.perf_counter()
            with torch.enable_grad(), torch.autocast("cuda", enabled=False), sdpa_kernel(SDPBackend.MATH):
                logits = model(x, use_cache=False)
                loss = ce_sum(logits, y) / y.numel()
                need(bool(torch.isfinite(loss)), "finite capture loss required")
                loss.backward()
            torch.cuda.synchronize()
            proof.update(capture_forward_backward_seconds=time.perf_counter() - tick,
                microbatch=8, seq=1024, targets=8192, accumulated_microbatches=1,
                not_a_complete_accum16_gradient=True, loss_for_finiteness_only=float(loss.detach()), offsets=offsets,
                input_ids_sha256=hashlib.sha256(values.astype("<i8").tobytes()).hexdigest().upper())
            named = dict(model.named_parameters())
            weights, gradients = [], []
            for row in rows:
                p = named[row["name"]]
                g = p.grad
                if row["matrix"]:
                    need(g is not None, "matrix gradient absent; do not replace with zeros")
                if g is not None:
                    need(g.dtype == torch.float32 and bool(torch.isfinite(g).all()), "finite FP32 gradient required")
                weights.append(p.detach().cpu().clone())
                gradients.append(None if g is None else g.detach().cpu().clone())
                row["gradient_present"] = g is not None
            proof.update(parameters=rows, original_body_optimizer_steps=0,
                capture_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                capture_peak_reserved_bytes=torch.cuda.max_memory_reserved())
            model.zero_grad(set_to_none=True)
            model.clear_quant()
            model.eval()
            logits = loss = x = y = named = p = g = None
            with torch.no_grad():
                model.freeze_quant()
        proof["capture_including_validation_seconds"] = time.perf_counter() - before
    finally:
        model = cfg = tok = route = logits = loss = x = y = None
        gc.collect()
    proof["original_corpus_unchanged"] = support.digest(corpus) == ref["sha256"]
    need(proof["original_corpus_unchanged"], "read-only original corpus changed")
    return rows, weights, gradients


def make_optimizers(rows, parameters, arm):
    import torch
    from tinylm.train.muon import Muon
    from tinylm.train.normuon import NorMuon
    from tinylm.train.adamuon import AdaMuon
    matrix = [p for row, p in zip(rows, parameters) if row["matrix"]]
    groups = []
    for decay in (.1, 0.):
        values = [p for row, p in zip(rows, parameters) if not row["matrix"] and row["adamw_decay"] == decay]
        if values:
            groups.append(dict(params=values, weight_decay=decay))
    need(len(matrix) + sum(len(g["params"]) for g in groups) == len(parameters), "complete matched optimizer groups required")
    cls = {"muon": Muon, "normuon": NorMuon, "adamuon_fp32v": AdaMuon}[arm]
    extra = {} if arm == "adamuon_fp32v" else dict(scale_mode="rms")
    optimizer = cls(matrix, lr=.001, momentum=.95, nesterov=True, ns_steps=5, weight_decay=0., **extra)
    adam = torch.optim.AdamW(groups, lr=.001, betas=(.9, .95), eps=1e-8, fused=False)
    return optimizer, adam


def state_storage(optimizer):
    return support.storage_audit(("optimizer_state", t) for state in optimizer.state.values()
        for t in support.nested_tensors(state))


def benchmark_arm(rows, weights, gradients, arm, steps, budget):
    import torch
    parameters = []
    optimizer = adam = p = None
    try:
        for w, g in zip(weights, gradients):
            p = torch.nn.Parameter(w.cuda())
            p.grad = None if g is None else g.cuda()
            parameters.append(p)
        optimizer, adam = make_optimizers(rows, parameters, arm)
        torch.cuda.reset_peak_memory_stats()
        records = []
        for step in range(steps):
            budget.check()
            torch.cuda.synchronize()
            started = time.perf_counter()
            optimizer.step()
            torch.cuda.synchronize()
            middle = time.perf_counter()
            adam.step()
            torch.cuda.synchronize()
            ended = time.perf_counter()
            records.append(dict(step=step + 1, matrix_seconds=middle - started,
                adamw_seconds=ended - middle, total_optimizer_seconds=ended - started,
                first_state_creation=step == 0))
        states = state_storage(optimizer)
        elements = sum(row["elements"] for row in rows if row["matrix"] and row["gradient_present"])
        output_rows = sum(row["shape"][0] for row in rows if row["matrix"] and row["gradient_present"])
        expected = elements * (8 if arm == "adamuon_fp32v" else 4) + (4 * output_rows if arm == "normuon" else 0)
        need(states["unique_storage_bytes"] == expected, "actual matrix state byte count differs from predeclared formula")
        need(all(bool(torch.isfinite(p).all()) for p in parameters), "temporary weight became nonfinite")
        gradients_unchanged = tensor_signature((row["name"], p.grad) for row, p in zip(rows, parameters)) == tensor_signature(
            (row["name"], g) for row, g in zip(rows, gradients))
        need(gradients_unchanged, "optimizer modified the common actual gradient")
        return dict(arm=arm, steps=records, matrix_state=states, adamw_state=state_storage(adam),
            matrix_state_expected_bytes=expected, active_matrix_elements=elements,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            original_model_updates=0, temporary_parameter_updates=steps,
            gpu_gradients_unchanged=gradients_unchanged,
            timing_scope="IMPLEMENTATION_INCLUDING_ITS_VALIDATION; ADAMW_SEPARATE; NOT_FULL_TRAINING_WALL_CLOCK",
            common_lr=.001, muon_scale="rms" if arm != "adamuon_fp32v" else "FINAL_RMS_POINT2_NO_EXTRA_SCALE")
    finally:
        for p in parameters:
            p.grad = None
        optimizer = adam = p = None
        parameters.clear()
        gc.collect()


def numerical(rows, weights, gradients, budget):
    import torch
    from tinylm.train.adamuon import AdaMuon
    from scripts.test_adamuon import oracle
    shapes, result = set(), []
    for row, w, g in zip(rows, weights, gradients):
        shape = tuple(row["shape"])
        if not row["matrix"] or shape in shapes or g is None:
            continue
        shapes.add(shape)
        budget.check()
        p = torch.nn.Parameter(w.cuda())
        expected = w.cuda()
        m, v = torch.zeros_like(expected), torch.zeros_like(expected)
        gradient = g.cuda()
        optimizer = AdaMuon([p], lr=.001)
        maximum = 0.
        passed = True
        for _ in range(3):
            p.grad = gradient.clone()
            expected, m, v = oracle(expected, gradient, m, v, lr=.001)
            optimizer.step()
            for a, b in ((p, expected), (optimizer.state[p]["momentum_buffer"], m), (optimizer.state[p]["v_buffer"], v)):
                maximum = max(maximum, float((a - b).abs().max()))
                passed = passed and bool(torch.allclose(a, b, atol=1e-5, rtol=1e-4))
        result.append(dict(name=row["name"], shape=list(shape), steps=3, max_abs=maximum,
            close=passed, atol=1e-5, rtol=1e-4, oracle="INDEPENDENT_GPU_ALGEBRA_FROM_CPU_TEST; SAME_DEVICE_BF16_NS"))
        p = optimizer = expected = m = v = gradient = a = b = None
        gc.collect()
    need(result, "zero numerical shape comparisons is not completion")
    return result


def metadata(args):
    profile = support.read_ref(dict(path=args.profile, sha256=args.profile_sha256))
    own = identity()
    need(profile.get("schema") == PROFILE and profile.get("root_approved") is True
        and profile.get("source_sha256") == own["sha256"] == args.source_sha256
        and profile.get("deadline") == support.DEADLINE.isoformat()
        and profile.get("tag") == TAG and profile.get("cost_steps") == 6
        and args.max_wall_sec == profile.get("max_wall_sec") == 900,
        "exact current independent AdaMuon cost profile required")
    output = support.safe(profile["output"])
    need(str(output.relative_to(ROOT)) == "test_result/evidence/" + TAG and not output.exists(), "new exact cost namespace required")
    selected = support.read_ref(profile["resource_profile"])
    specs = [r for r in selected["models"] if r["id"] == "format_muon"]
    need(len(specs) == 1 and specs[0]["updates"] == 2289 and specs[0]["route"] == "ternary", "completed exact Muon model required")
    need(profile["tokenizer"] == selected["tokenizer"], "same source tokenizer required")
    return profile, specs[0], output, own


def execute(args, profile, spec, output, own):
    import torch
    from scripts.interactive_research_infer import require_idle_gpu
    from scripts.diag_p102a_logit_margin import memory_point
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    budget = support.Budget(args.max_wall_sec)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema=SCHEMA, tag=TAG, source=own, profile_sha256=args.profile_sha256,
        status="STARTED", body_optimizer_steps=0, checkpoint_writes=0, quality_claim=False,
        source_cleanup_changes=0, observations=[], numerical=[], capture={}, torch_version=torch.__version__)
    weights = gradients = rows = None
    code = 9
    try:
        with support.wall(args.max_wall_sec):
            report["idle"] = require_idle_gpu()
            point = memory_point()
            need(point["free_mib"] >= 10240, "capture requires at least10GiB currently free")
            report["gpu_entry"] = point
            torch.cuda.init()
            total = torch.cuda.get_device_properties(0).total_memory
            cap = min(int(total * .8), (point["free_mib"] - 1024) * 2**20)
            torch.cuda.set_per_process_memory_fraction(cap / total, 0)
            report["allocator_cap_bytes"] = cap
            torch.cuda.reset_peak_memory_stats()
            rows, weights, gradients = capture(spec, profile, budget, report["capture"])
            gradient_sha = tensor_signature((r["name"], g) for r, g in zip(rows, gradients))
            report["gradient_sha256"] = gradient_sha
            report["gpu_after_capture"] = memory_point()
            report["numerical"] = numerical(rows, weights, gradients, budget)
            report["peak_through_numerical_allocated_bytes"] = torch.cuda.max_memory_allocated()
            report["peak_through_numerical_reserved_bytes"] = torch.cuda.max_memory_reserved()
            orders = (("muon", "normuon", "adamuon_fp32v"), ("adamuon_fp32v", "normuon", "muon"))
            for order_id, order in enumerate(orders, 1):
                for arm in order:
                    observation = benchmark_arm(rows, weights, gradients, arm, profile["cost_steps"], budget)
                    observation.update(order=order_id, order_arms=list(order))
                    report["observations"].append(observation)
                    print(json.dumps(dict(phase="OPTIMIZER_COST", order=order_id, arm=arm,
                        matrix_state_bytes=observation["matrix_state_expected_bytes"])), flush=True)
            need(gradient_sha == tensor_signature((r["name"], g) for r, g in zip(rows, gradients)), "shared read-only gradient changed")
            need(identity() == own, "cost or model source changed during execution")
            need(support.digest(support.safe(spec["checkpoint"]["path"])) == spec["checkpoint"]["sha256"], "original checkpoint changed after temporary steps")
            need(len(report["observations"]) == 6, "all six ordered cost arms required")
            close = all(row["close"] for row in report["numerical"])
            report["status"] = "ADAMUON_COST_COMPLETE_NOT_QUALITY" if close else "ADAMUON_NUMERICAL_NEGATIVE_NOT_ADOPTED"
            code = 0 if close else 8
    except BaseException as exc:
        report["status"] = "ADAMUON_DIAGNOSTIC_ERROR"
        report["error"] = dict(type=type(exc).__name__, message=str(exc)[:2000])
        print(json.dumps(dict(original_error=report["error"])), flush=True)
        code = 130 if isinstance(exc, KeyboardInterrupt) else 9
    finally:
        weights = gradients = rows = None
        gc.collect()
        if torch.cuda.is_initialized():
            report["cleanup"] = {}
            try:
                support.close_cuda(torch, report["cleanup"])
                need(report["cleanup"]["allocated_bytes"] == report["cleanup"]["reserved_bytes"] == 0, "owned CUDA remains")
            except Exception as exc:
                report["cleanup_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                code = 9
        report.update(returncode=code, seconds=time.monotonic() - budget.started)
        support.write_new(output / "report.json", report)
        print(json.dumps(dict(status=report["status"], returncode=code, seconds=report["seconds"])), flush=True)
    return code


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", required=True)
    p.add_argument("--profile-sha256", required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--max-wall-sec", type=int, default=900)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-only", action="store_true")
    action.add_argument("--execute", action="store_true")
    args = p.parse_args(argv)
    try:
        profile, spec, output, own = metadata(args)
        if args.check_only:
            print(json.dumps(dict(status="STATIC_ONLY", source_sha256=own["sha256"], model_loads=0,
                checkpoint_tensor_loads=0, gpu_calls=0, output=str(output.relative_to(ROOT)))))
            return 0
        need(time.time() + args.max_wall_sec + 120 < support.DEADLINE.timestamp(), "whole cost experiment must fit current deadline")
        return execute(args, profile, spec, output, own)
    except Exception as exc:
        print(json.dumps(dict(status="ENTRY_OR_CLOSURE_ERROR", type=type(exc).__name__, message=str(exc))), file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
